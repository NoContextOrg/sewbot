import time
import glob
import sys
import shutil
import subprocess
import select
from config import CAMERA_WIDTH, CAMERA_HEIGHT, CAMERA_FPS, CAMERA_BUFFER_GRABS, MAX_READ_RETRIES
import logging

log = logging.getLogger("sewbot")

try:
    import cv2
    import numpy as np
except ImportError as e:
    log.error(f"Critical dependency missing! {e}")
    raise

try:
    from picamera2 import Picamera2  # type: ignore[import-not-found]
except ImportError:
    Picamera2 = None

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
