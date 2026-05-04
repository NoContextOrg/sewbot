import cv2
import glob
import os
import select
import shutil
import subprocess
import sys
import time
import numpy as np
from flask import Flask, Response, send_from_directory
from flask_socketio import SocketIO

try:
    from picamera2 import Picamera2  # type: ignore[import-not-found]
except ImportError:
    Picamera2 = None

app = Flask(__name__, static_folder='../frontend/dist', static_url_path='/')

# 1. Initialize SocketIO with gevent here at the top
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='gevent')

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
            print(f"Picamera2 read failed: {exc}")
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


def _print_runtime_diagnostics_once():
    global _printed_runtime_diagnostics

    if _printed_runtime_diagnostics:
        return

    _printed_runtime_diagnostics = True
    video_nodes = sorted(glob.glob("/dev/video*"))
    print(f"Python version: {sys.version.split()[0]}")
    print(f"OpenCV version: {cv2.__version__}")
    print(f"OpenCV GStreamer support: {_gstreamer_enabled_in_opencv()}")
    print(f"Detected V4L2 nodes: {video_nodes if video_nodes else 'none'}")


def _warmup_camera(cam, frames=20):
    print("Warming up camera sensor...")
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
        print("Picamera2 import unavailable. If using a venv on Raspberry Pi OS, use system Python or recreate it with --system-site-packages.")
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
            print(f"{backend_name} open threw exception: {exc}")
            continue

        if hasattr(cam, "set"):
            cam.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        if backend_name.startswith("V4L2"):
            _configure_v4l2(cam)

        if not cam.isOpened():
            print(f"{backend_name} open failed.")
            _release_camera(cam)
            continue

        _warmup_camera(cam)
        success, _ = cam.read()
        if success:
            camera = cam
            print(f"Camera initialized using {backend_name}.")
            return True

        print(f"{backend_name} opened but did not return frames.")
        _release_camera(cam)

    camera = None
    return False


def read_frame_with_retries(max_retries=MAX_READ_RETRIES):
    global camera

    for attempt in range(1, max_retries + 1):
        if camera is None or not camera.isOpened():
            print("Camera unavailable, attempting reinitialization...")
            if not init_camera():
                time.sleep(0.2)
                continue

        _drain_camera_buffer(camera)
        success, frame = camera.read()
        if success:
            return True, frame

        print(f"Read failed (attempt {attempt}/{max_retries}).")
        time.sleep(0.1)

    print("Read retries exhausted. Reinitializing camera...")
    init_camera()
    return False, None


if not init_camera():
    print("Warning: Camera failed to initialize at startup. Will keep retrying during stream requests.")

@app.route('/')
def serve():
    return send_from_directory(app.static_folder, 'index.html')

def gen_frames():
    while True:
        success, frame = read_frame_with_retries()
        if not success:
            print("Error: Could not read frame.")
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

@socketio.on('move')
def handle_move(data):
    if isinstance(data, dict) and 'direction' in data:
        print(f"Command: {data['direction']}")

# THIS IS THE CRUCIAL PART
if __name__ == '__main__':
    print("Starting Robot Server on http://0.0.0.0:5000")
    # You MUST call socketio.run to keep the script alive
    socketio.run(app, host='0.0.0.0', port=5000)