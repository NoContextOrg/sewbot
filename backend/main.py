import cv2
import time
from flask import Flask, Response, send_from_directory
from flask_socketio import SocketIO

app = Flask(__name__, static_folder='../frontend/dist', static_url_path='/')
# Allow all origins for easier debugging between laptop and Pi
socketio = SocketIO(app, cors_allowed_origins="*")

# Try standard first, but with the GStreamer backend which is better on new Debian
camera = cv2.VideoCapture("v4l2src device=/dev/video0 ! video/x-raw,width=640,height=480 ! videoconvert ! appsink", cv2.CAP_GSTREAMER)

# IF THAT FAILS, fallback to the previous V4L2 method but with extra wait time
if not camera.isOpened():
    print("GStreamer failed, falling back to V4L2...")
    camera = cv2.VideoCapture(0, cv2.CAP_V4L2)
    camera.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
    camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

# 3. WARM-UP: Discard the first 20 frames to allow Auto-Exposure to settle
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
        
        # 4. Low quality (30-40) is essential for Zero 2W Wi-Fi stability
        _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 35])
        
        frame_bytes = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        
        # Small sleep to prevent CPU spiking at 100%
        time.sleep(0.01)

@app.route('/video_feed')
def video_feed():
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@socketio.on('move')
def handle_move(data):
    # Ensure data is a dict and has 'direction'
    if isinstance(data, dict) and 'direction' in data:
        print(f"Command: {data['direction']}")
    else:
        print(f"Received raw data: {data}")

if __name__ == '__main__':
    # host='0.0.0.0' allows external access from your laptop
    socketio = SocketIO(app, cors_allowed_origins="*", async_mode='gevent')