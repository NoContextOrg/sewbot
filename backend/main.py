import cv2
import glob
import logging
import os
import select
import shutil
import subprocess
import sys
import threading
import time
import numpy as np
from flask import Flask, Response, send_from_directory, request
from flask_socketio import SocketIO
import paramiko

try:
    from picamera2 import Picamera2  # type: ignore[import-not-found]
except ImportError:
    Picamera2 = None

app = Flask(__name__, static_folder='../frontend/dist', static_url_path='/')

# 1. Initialize SocketIO with gevent here at the top
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='gevent')


class SocketIOLogHandler(logging.Handler):
    def __init__(self, sio):
        super().__init__()
        self._sio = sio

    def emit(self, record):
        try:
            message = self.format(record)
            payload = {
                "text": message,
                "level": record.levelname.lower(),
                "source": "backend",
            }
            self._sio.emit("log", payload)
        except Exception:
            pass


def _setup_logging():
    logger = logging.getLogger("sewbot")
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    logger.propagate = False
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s", "%H:%M:%S")

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    socket_handler = SocketIOLogHandler(socketio)
    socket_handler.setFormatter(formatter)
    logger.addHandler(socket_handler)

    return logger


log = _setup_logging()


def emit_log(text, source="backend", level="info", sid=None):
    payload = {
        "text": text,
        "level": level,
        "source": source,
    }
    if sid:
        socketio.emit("log", payload, to=sid)
    else:
        socketio.emit("log", payload)


SSH_TARGET = os.getenv("SEWBOT_SSH_TARGET", "sewbot@sewbot.local")
SSH_HOST = os.getenv("SEWBOT_SSH_HOST", "").strip()
SSH_PORT = int(os.getenv("SEWBOT_SSH_PORT", "22"))
SSH_USER = os.getenv("SEWBOT_SSH_USER", "").strip()
SSH_KEY_PATH = os.getenv("SEWBOT_SSH_KEY_PATH", os.path.expanduser("~/.ssh/sewbot_webui"))
SSH_PASSWORD = os.getenv("SEWBOT_SSH_PASSWORD", "")
SSH_ALLOW_ANY = os.getenv("SEWBOT_SSH_ALLOW_ANY", "true").lower() in ("1", "true", "yes", "on")
SSH_ALLOWED_COMMANDS = [
    cmd.strip() for cmd in os.getenv("SEWBOT_SSH_ALLOWED_COMMANDS", "").split(",") if cmd.strip()
]
SSH_GENERATE_KEY = os.getenv("SEWBOT_SSH_GENERATE_KEY", "false").lower() in ("1", "true", "yes", "on")
JOURNALCTL_COMMAND = os.getenv("SEWBOT_JOURNALCTL_COMMAND", "journalctl -f -n 200")
POWER_OFF_COMMAND = os.getenv("SEWBOT_POWER_OFF_COMMAND", "sudo shutdown -h now")


def _parse_ssh_target(target):
    value = target.strip()
    if value.startswith("ssh "):
        value = value[4:].strip()

    user = ""
    host_port = value
    if "@" in value:
        user, host_port = value.split("@", 1)

    host = host_port
    port = None
    if host_port.count(":") == 1:
        host, port_str = host_port.rsplit(":", 1)
        if port_str.isdigit():
            port = int(port_str)

    return user, host, port


def _resolve_ssh_config():
    global SSH_HOST, SSH_PORT, SSH_USER
    if SSH_HOST and SSH_USER:
        return

    user, host, port = _parse_ssh_target(SSH_TARGET)
    if not SSH_HOST:
        SSH_HOST = host or "sewbot.local"
    if not SSH_USER:
        SSH_USER = user or "sewbot"
    if port and not os.getenv("SEWBOT_SSH_PORT"):
        SSH_PORT = port


_resolve_ssh_config()
log.info("SSH target: %s@%s:%s", SSH_USER, SSH_HOST, SSH_PORT)

CAMERA_WIDTH = 640
CAMERA_HEIGHT = 480
CAMERA_FPS = 15
CAMERA_JPEG_QUALITY = int(os.getenv("CAMERA_JPEG_QUALITY", "40"))
CAMERA_BUFFER_GRABS = int(os.getenv("CAMERA_BUFFER_GRABS", "2"))
MAX_READ_RETRIES = 5

# Shared camera instance used by the video stream generator.
camera = None
_printed_picamera2_hint = False
_printed_runtime_diagnostics = False


class PiCameraAdapter:
    def __init__(self, width, height):
        self._opened = False
        self._cam = Picamera2()
        frame_us = int(1_000_000 / CAMERA_FPS)
        config = self._cam.create_preview_configuration(
            main={"size": (width, height), "format": "BGR888"},
            controls={"FrameDurationLimits": (frame_us, frame_us)},
            buffer_count=2,
        )
        self._cam.configure(config)
        self._cam.start()
        self._opened = True

    def isOpened(self):
        return self._opened

    def read(self):
        if not self._opened:
            return False, None

        try:
            frame = self._cam.capture_array("main")
            if frame is None or frame.size == 0:
                return False, None
            return True, frame
        except Exception as exc:
            log.warning("Picamera2 read failed: %s", exc)
            return False, None

    def release(self):
        if not self._opened:
            return

        self._opened = False
        try:
            self._cam.stop()
        except Exception:
            pass


class RpicamMjpegAdapter:
    def __init__(self, width, height, fps):
        self._opened = False
        self._buffer = b""
        self._proc = None

        cmd = [
            "rpicam-vid",
            "--timeout",
            "0",
            "--nopreview",
            "--codec",
            "mjpeg",
            "--width",
            str(width),
            "--height",
            str(height),
            "--framerate",
            str(fps),
            "--quality",
            "70",
            "-o",
            "-",
        ]

        self._proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            bufsize=0,
        )
        self._opened = self._proc.poll() is None and self._proc.stdout is not None

    def isOpened(self):
        return self._opened

    def _read_jpeg_bytes(self, max_wait_sec=1.5):
        if self._proc is None or self._proc.stdout is None:
            return None

        fd = self._proc.stdout.fileno()
        deadline = time.time() + max_wait_sec

        while time.time() < deadline:
            if self._proc.poll() is not None:
                self._opened = False
                return None

            ready, _, _ = select.select([fd], [], [], 0.15)
            if not ready:
                continue

            chunk = os.read(fd, 8192)
            if not chunk:
                continue

            self._buffer += chunk
            start = self._buffer.find(b"\xff\xd8")
            end = self._buffer.find(b"\xff\xd9", start + 2)
            if start != -1 and end != -1:
                jpeg = self._buffer[start:end + 2]
                self._buffer = self._buffer[end + 2:]
                return jpeg

        return None

    def read(self):
        if not self._opened:
            return False, None

        jpeg = self._read_jpeg_bytes()
        if jpeg is None:
            return False, None

        return True, jpeg

    def release(self):
        if not self._opened:
            return

        self._opened = False
        if self._proc is None:
            return

        try:
            self._proc.terminate()
            self._proc.wait(timeout=1)
        except Exception:
            try:
                self._proc.kill()
            except Exception:
                pass
        try:
            self._cam.close()
        except Exception:
            pass


def _configure_v4l2(cam):
    cam.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
    cam.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
    cam.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)
    cam.set(cv2.CAP_PROP_FPS, CAMERA_FPS)
    cam.set(cv2.CAP_PROP_BUFFERSIZE, 1)


def _drain_camera_buffer(cam, grabs=CAMERA_BUFFER_GRABS):
    if not hasattr(cam, "grab"):
        return

    for _ in range(grabs):
        try:
            cam.grab()
        except Exception:
            break


def _release_camera(cam):
    try:
        cam.release()
    except Exception:
        pass


def _gstreamer_enabled_in_opencv():
    try:
        build_info = cv2.getBuildInformation()
    except Exception:
        return False

    for line in build_info.splitlines():
        if "GStreamer" in line:
            return "YES" in line.upper()
    return False


def _ensure_ssh_key():
    if not SSH_KEY_PATH:
        return
    if os.path.exists(SSH_KEY_PATH):
        return
    if not SSH_GENERATE_KEY:
        return

    directory = os.path.dirname(SSH_KEY_PATH)
    if directory:
        os.makedirs(directory, exist_ok=True)
    key = paramiko.RSAKey.generate(2048)
    key.write_private_key_file(SSH_KEY_PATH)
    pub_path = SSH_KEY_PATH + ".pub"
    with open(pub_path, "w", encoding="utf-8") as handle:
        handle.write(f"{key.get_name()} {key.get_base64()} sewbot-webui\n")

    log.info("Generated SSH key at %s", SSH_KEY_PATH)
    log.info("Add this public key to %s authorized_keys: %s", SSH_HOST, pub_path)


def _load_ssh_key():
    if not SSH_KEY_PATH or not os.path.exists(SSH_KEY_PATH):
        return None

    for key_cls in (paramiko.RSAKey, paramiko.Ed25519Key, paramiko.ECDSAKey):
        try:
            return key_cls.from_private_key_file(SSH_KEY_PATH)
        except Exception:
            continue
    return None


def _create_ssh_client():
    if not SSH_HOST:
        raise RuntimeError("SSH host not configured")

    _ensure_ssh_key()
    pkey = _load_ssh_key()

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(
        hostname=SSH_HOST,
        port=SSH_PORT,
        username=SSH_USER,
        password=SSH_PASSWORD or None,
        pkey=pkey,
        timeout=10,
        allow_agent=True,
        look_for_keys=not bool(pkey),
    )
    return client


def _command_allowed(command):
    if SSH_ALLOW_ANY:
        return True

    cleaned = command.strip()
    if not cleaned or not SSH_ALLOWED_COMMANDS:
        return False

    return any(cleaned == allowed or cleaned.startswith(f"{allowed} ") for allowed in SSH_ALLOWED_COMMANDS)


ssh_sessions = {}
ssh_sessions_lock = threading.Lock()
journal_stream_lock = threading.Lock()
journal_stream_active = False


class SSHShellSession:
    def __init__(self, sid):
        self.sid = sid
        self.client = _create_ssh_client()
        self.channel = self.client.invoke_shell()
        self.channel.settimeout(0.0)
        self.alive = True
        self._buffer = ""
        socketio.start_background_task(self._read_loop)

    def send(self, command):
        if not self.alive:
            return
        data = command.rstrip("\n") + "\n"
        self.channel.send(data)

    def _read_loop(self):
        while self.alive:
            try:
                if self.channel.recv_ready():
                    chunk = self.channel.recv(4096)
                    if not chunk:
                        break
                    text = chunk.decode(errors="ignore")
                    self._buffer += text
                    while "\n" in self._buffer:
                        line, self._buffer = self._buffer.split("\n", 1)
                        if line.strip():
                            emit_log(line.rstrip(), source="ssh", level="info", sid=self.sid)
                else:
                    socketio.sleep(0.05)
            except Exception as exc:
                emit_log(f"SSH stream error: {exc}", source="ssh", level="error", sid=self.sid)
                break

        self.close()

    def close(self):
        self.alive = False
        try:
            if self.channel:
                self.channel.close()
        except Exception:
            pass
        try:
            if self.client:
                self.client.close()
        except Exception:
            pass


def _get_ssh_session(sid):
    with ssh_sessions_lock:
        session = ssh_sessions.get(sid)
        if session and session.alive:
            return session

        try:
            session = SSHShellSession(sid)
        except Exception as exc:
            emit_log(f"SSH connect failed: {exc}", source="ssh", level="error", sid=sid)
            return None

        ssh_sessions[sid] = session
        return session


def _close_ssh_session(sid):
    with ssh_sessions_lock:
        session = ssh_sessions.pop(sid, None)
    if session:
        session.close()


def _start_journal_stream():
    global journal_stream_active
    with journal_stream_lock:
        if journal_stream_active:
            return
        journal_stream_active = True

    socketio.start_background_task(_journal_stream_loop)


def _journal_stream_loop():
    buffer = ""
    while True:
        client = None
        try:
            client = _create_ssh_client()
            channel = client.get_transport().open_session()
            channel.get_pty()
            channel.exec_command(JOURNALCTL_COMMAND)
            channel.settimeout(0.0)

            while True:
                if channel.exit_status_ready():
                    break
                if channel.recv_ready():
                    chunk = channel.recv(4096)
                    if not chunk:
                        break
                    text = chunk.decode(errors="ignore")
                    buffer += text
                    while "\n" in buffer:
                        line, buffer = buffer.split("\n", 1)
                        if line.strip():
                            emit_log(line.rstrip(), source="journal", level="info")
                else:
                    socketio.sleep(0.2)
        except Exception as exc:
            emit_log(f"Journal stream error: {exc}", source="journal", level="error")
            socketio.sleep(2)
        finally:
            try:
                if client:
                    client.close()
            except Exception:
                pass


def _print_runtime_diagnostics_once():
    global _printed_runtime_diagnostics

    if _printed_runtime_diagnostics:
        return

    _printed_runtime_diagnostics = True
    video_nodes = sorted(glob.glob("/dev/video*"))
    log.info("Python version: %s", sys.version.split()[0])
    log.info("OpenCV version: %s", cv2.__version__)
    log.info("OpenCV GStreamer support: %s", _gstreamer_enabled_in_opencv())
    log.info("Detected V4L2 nodes: %s", video_nodes if video_nodes else "none")


def _warmup_camera(cam, frames=20):
    log.info("Warming up camera sensor...")
    for _ in range(frames):
        cam.read()
        time.sleep(0.02)


def init_camera():
    global camera
    global _printed_picamera2_hint

    _print_runtime_diagnostics_once()

    if camera is not None:
        _release_camera(camera)

    if Picamera2 is None and not _printed_picamera2_hint:
        log.warning(
            "Picamera2 import unavailable. If using a venv on Raspberry Pi OS, use system Python or recreate it with --system-site-packages."
        )
        _printed_picamera2_hint = True

    attempts = []

    if Picamera2 is not None:
        attempts.append(("Picamera2", lambda: PiCameraAdapter(CAMERA_WIDTH, CAMERA_HEIGHT)))
    elif shutil.which("rpicam-vid") is not None:
        attempts.append(("Rpicam MJPEG", lambda: RpicamMjpegAdapter(CAMERA_WIDTH, CAMERA_HEIGHT, CAMERA_FPS)))

    attempts.extend([
        (
            "Libcamera GStreamer",
            lambda: cv2.VideoCapture(
                f"libcamerasrc ! video/x-raw,width={CAMERA_WIDTH},height={CAMERA_HEIGHT},framerate={CAMERA_FPS}/1,format=BGR ! appsink drop=true max-buffers=1 sync=false",
                cv2.CAP_GSTREAMER,
            ),
        ),
    ])

    for dev_path in sorted(glob.glob("/dev/video*")):
        dev_index = int(dev_path.replace("/dev/video", ""))
        attempts.append(
            (
                f"V4L2 GStreamer {dev_path}",
                lambda path=dev_path: cv2.VideoCapture(
                    f"v4l2src device={path} ! video/x-raw,width={CAMERA_WIDTH},height={CAMERA_HEIGHT},framerate={CAMERA_FPS}/1 ! videoconvert ! appsink drop=true max-buffers=1 sync=false",
                    cv2.CAP_GSTREAMER,
                ),
            )
        )
        attempts.append((f"V4L2 index{dev_index}", lambda idx=dev_index: cv2.VideoCapture(idx, cv2.CAP_V4L2)))

    attempts.extend([
        ("V4L2 index0", lambda: cv2.VideoCapture(0, cv2.CAP_V4L2)),
        ("Default index0", lambda: cv2.VideoCapture(0)),
    ])

    for backend_name, open_camera in attempts:
        try:
            cam = open_camera()
        except Exception as exc:
            log.warning("%s open threw exception: %s", backend_name, exc)
            continue

        if hasattr(cam, "set"):
            cam.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        if backend_name.startswith("V4L2"):
            _configure_v4l2(cam)

        if not cam.isOpened():
            log.warning("%s open failed.", backend_name)
            _release_camera(cam)
            continue

        _warmup_camera(cam)
        success, _ = cam.read()
        if success:
            camera = cam
            log.info("Camera initialized using %s.", backend_name)
            return True

        log.warning("%s opened but did not return frames.", backend_name)
        _release_camera(cam)

    camera = None
    return False


def read_frame_with_retries(max_retries=MAX_READ_RETRIES):
    global camera

    for attempt in range(1, max_retries + 1):
        if camera is None or not camera.isOpened():
            log.warning("Camera unavailable, attempting reinitialization...")
            if not init_camera():
                time.sleep(0.2)
                continue

        _drain_camera_buffer(camera)
        success, frame = camera.read()
        if success:
            return True, frame

        log.warning("Read failed (attempt %s/%s).", attempt, max_retries)
        time.sleep(0.1)

    log.warning("Read retries exhausted. Reinitializing camera...")
    init_camera()
    return False, None


if not init_camera():
    log.warning("Camera failed to initialize at startup. Will keep retrying during stream requests.")

@app.route('/')
def serve():
    return send_from_directory(app.static_folder, 'index.html')

def gen_frames():
    while True:
        success, frame = read_frame_with_retries()
        if not success:
            log.warning("Could not read frame.")
            time.sleep(0.25)
            continue

        if isinstance(frame, (bytes, bytearray)):
            jpeg_bytes = frame
        else:
            ok, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, CAMERA_JPEG_QUALITY])
            if not ok:
                continue
            jpeg_bytes = buffer.tobytes()

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n'
               b'Content-Length: ' + str(len(jpeg_bytes)).encode('ascii') + b'\r\n\r\n' + jpeg_bytes + b'\r\n')

@app.route('/video_feed')
def video_feed():
    headers = {
        "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
        "Pragma": "no-cache",
        "Expires": "0",
        "X-Accel-Buffering": "no",
    }
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame', headers=headers)


@socketio.on("connect")
def handle_connect():
    _start_journal_stream()
    emit_log("Client connected", source="backend", level="info", sid=request.sid)


@socketio.on("disconnect")
def handle_disconnect():
    _close_ssh_session(request.sid)


@socketio.on("ssh_command")
def handle_ssh_command(data):
    command = ""
    if isinstance(data, dict):
        command = str(data.get("command", "")).strip()

    if not command:
        return

    if not _command_allowed(command):
        emit_log("SSH command blocked by policy", source="ssh", level="error", sid=request.sid)
        return

    session = _get_ssh_session(request.sid)
    if not session:
        return

    emit_log(f"$ {command}", source="ssh", level="info", sid=request.sid)
    session.send(command)


@socketio.on("power_off")
def handle_power_off():
    if not POWER_OFF_COMMAND:
        emit_log("Power off command is not configured", source="power", level="error", sid=request.sid)
        return

    if not _command_allowed(POWER_OFF_COMMAND):
        emit_log("Power off command blocked by policy", source="power", level="error", sid=request.sid)
        return

    session = _get_ssh_session(request.sid)
    if not session:
        return

    emit_log("Power off requested", source="power", level="warning", sid=request.sid)
    session.send(POWER_OFF_COMMAND)

@socketio.on('move')
def handle_move(data):
    if isinstance(data, dict) and 'direction' in data:
        log.info("Command: %s", data["direction"])

# THIS IS THE CRUCIAL PART
if __name__ == '__main__':
    log.info("Starting Robot Server on http://0.0.0.0:5000")
    # You MUST call socketio.run to keep the script alive
    socketio.run(app, host='0.0.0.0', port=5000)