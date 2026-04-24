import cv2
import time
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
MAX_READ_RETRIES = 5

# Shared camera instance used by the video stream generator.
camera = None
_printed_picamera2_hint = False


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
        try:
            self._cam.close()
        except Exception:
            pass


def _configure_v4l2(cam):
    cam.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
    cam.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
    cam.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)


def _release_camera(cam):
    try:
        cam.release()
    except Exception:
        pass


def _warmup_camera(cam, frames=20):
    print("Warming up camera sensor...")
    for _ in range(frames):
        cam.read()
        time.sleep(0.02)


def init_camera():
    global camera
    global _printed_picamera2_hint

    if camera is not None:
        _release_camera(camera)

    if Picamera2 is None and not _printed_picamera2_hint:
        print("Picamera2 import unavailable. If using a venv on Raspberry Pi OS, recreate it with --system-site-packages or install picamera2 in that environment.")
        _printed_picamera2_hint = True

    attempts = []

    if Picamera2 is not None:
        attempts.append(("Picamera2", lambda: PiCameraAdapter(CAMERA_WIDTH, CAMERA_HEIGHT)))

    attempts.extend([
        (
            "Libcamera GStreamer",
            lambda: cv2.VideoCapture(
                f"libcamerasrc ! video/x-raw,width={CAMERA_WIDTH},height={CAMERA_HEIGHT},framerate={CAMERA_FPS}/1,format=BGR ! appsink drop=true max-buffers=1 sync=false",
                cv2.CAP_GSTREAMER,
            ),
        ),
        (
            "V4L2 GStreamer",
            lambda: cv2.VideoCapture(
                f"v4l2src device=/dev/video0 ! video/x-raw,width={CAMERA_WIDTH},height={CAMERA_HEIGHT} ! videoconvert ! appsink",
                cv2.CAP_GSTREAMER,
            ),
        ),
        ("V4L2", lambda: cv2.VideoCapture(0, cv2.CAP_V4L2)),
        ("Default", lambda: cv2.VideoCapture(0)),
    ])

    for backend_name, open_camera in attempts:
        cam = open_camera()
        if backend_name == "V4L2":
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
        
        _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 35])
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
        
        time.sleep(0.01)

@app.route('/video_feed')
def video_feed():
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@socketio.on('move')
def handle_move(data):
    if isinstance(data, dict) and 'direction' in data:
        print(f"Command: {data['direction']}")

# THIS IS THE CRUCIAL PART
if __name__ == '__main__':
    print("Starting Robot Server on http://0.0.0.0:5000")
    # You MUST call socketio.run to keep the script alive
    socketio.run(app, host='0.0.0.0', port=5000)