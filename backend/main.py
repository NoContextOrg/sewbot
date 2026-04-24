import cv2
from flask import Flask, Response, send_from_directory
from flask_socketio import SocketIO

# Note: static_folder points to the 'dist' folder Vite will generate
app = Flask(__name__, static_folder='../frontend/dist', static_url_path='/')
socketio = SocketIO(app, cors_allowed_origins="*")

camera = cv2.VideoCapture(0)

@app.route('/')
def serve():
    return send_from_directory(app.static_folder, 'index.html')

def gen_frames():
    while True:
        success, frame = camera.read()
        if not success: break
        # Low quality (40) is key for Pi Zero 2W stability
        _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 40])
        yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')

@app.route('/video_feed')
def video_feed():
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@socketio.on('move')
def handle_move(data):
    print(f"Moving: {data['direction']}")

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000)