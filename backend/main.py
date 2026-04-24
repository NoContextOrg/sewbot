import cv2
import time
from flask import Flask, Response, send_from_directory
from flask_socketio import SocketIO

app = Flask(__name__, static_folder='../frontend/dist', static_url_path='/')

# 1. Initialize SocketIO with gevent here at the top
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='gevent')

# Setup Camera (GStreamer pipe for Debian 13/Trixie)
camera = cv2.VideoCapture("v4l2src device=/dev/video0 ! video/x-raw,width=640,height=480 ! videoconvert ! appsink", cv2.CAP_GSTREAMER)

if not camera.isOpened():
    print("GStreamer failed, falling back to V4L2...")
    camera = cv2.VideoCapture(0, cv2.CAP_V4L2)
    camera.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
    camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

# Warm-up
print("Warming up camera sensor...")
for _ in range(20):
    camera.read()

@app.route('/')
def serve():
    return send_from_directory(app.static_folder, 'index.html')

def gen_frames():
    while True:
        success, frame = camera.read()
        if not success:
            print("Error: Could not read frame.")
            break
        
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