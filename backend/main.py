import cv2
import time
from flask import Flask, Response, send_from_directory
from flask_socketio import SocketIO

app = Flask(__name__, static_folder='../frontend/dist', static_url_path='/')

# 1. Initialize SocketIO with gevent here at the top
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='gevent')

CAMERA_WIDTH = 640
CAMERA_HEIGHT = 480
MAX_READ_RETRIES = 5

# Shared camera instance used by the video stream generator.
camera = None


def _configure_v4l2(cam):
    cam.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
    cam.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
    cam.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)


def _warmup_camera(cam, frames=20):
    print("Warming up camera sensor...")
    for _ in range(frames):
        cam.read()
        time.sleep(0.02)


def init_camera():
    global camera

    if camera is not None:
        camera.release()

    attempts = [
        (
            "GStreamer",
            lambda: cv2.VideoCapture(
                f"v4l2src device=/dev/video0 ! video/x-raw,width={CAMERA_WIDTH},height={CAMERA_HEIGHT} ! videoconvert ! appsink",
                cv2.CAP_GSTREAMER,
            ),
        ),
        ("V4L2", lambda: cv2.VideoCapture(0, cv2.CAP_V4L2)),
        ("Default", lambda: cv2.VideoCapture(0)),
    ]

    for backend_name, open_camera in attempts:
        cam = open_camera()
        if backend_name == "V4L2":
            _configure_v4l2(cam)

        if not cam.isOpened():
            print(f"{backend_name} open failed.")
            cam.release()
            continue

        _warmup_camera(cam)
        success, _ = cam.read()
        if success:
            camera = cam
            print(f"Camera initialized using {backend_name}.")
            return True

        print(f"{backend_name} opened but did not return frames.")
        cam.release()

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