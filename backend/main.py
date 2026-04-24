import cv2
import time
from flask import Flask, Response, send_from_directory
from flask_socketio import SocketIO

app = Flask(__name__, static_folder='../frontend/dist', static_url_path='/')
# Allow all origins for easier debugging between laptop and Pi
socketio = SocketIO(app, cors_allowed_origins="*")

# 1. Use V4L2 Backend specifically for modern Raspberry Pi OS
camera = cv2.VideoCapture(0, cv2.CAP_V4L2)

# 2. OPTIMIZATION: Force lower resolution and MJPG format
# High resolution will cause the white/laggy screen on Pi Zero 2W
camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
camera.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
camera.set(cv2.CAP_PROP_FPS, 20)

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
    socketio.run(app, host='0.0.0.0', port=5000, debug=False)