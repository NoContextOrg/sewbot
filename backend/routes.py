from flask import Response, send_from_directory, request
import time
from logger import emit_log, log_history, log_history_lock
from config import command_allowed, CAMERA_JPEG_QUALITY, POWER_OFF_COMMAND
from shell import start_journal_stream, run_cmd, run_power_off

import logging
log = logging.getLogger("sewbot")

telemetry_state = {
    'fps': 0,
    'bitrate': 0.0,
    'latency': 0.0,
    'active': False
}

def setup_routes(app, socketio):

    def telemetry_loop():
        while True:
            if telemetry_state['active']:
                socketio.emit('telemetry', {
                    'fps': telemetry_state['fps'],
                    'bitrate': telemetry_state['bitrate'],
                    'latency': telemetry_state['latency']
                })
            socketio.sleep(1.0)
            
    socketio.start_background_task(telemetry_loop)

    @app.route('/')
    def serve():
        return send_from_directory(app.static_folder, 'index.html')

    def gen_frames():
        from camera import read_frame_with_retries
        import cv2
        
        frames = 0
        last_time = time.time()
        bytes_sent = 0

        telemetry_state['active'] = True

        try:
            while True:
                t0 = time.time()
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

                frame_len = len(jpeg_bytes)
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n'
                       b'Content-Length: ' + str(frame_len).encode('ascii') + b'\r\n\r\n' + jpeg_bytes + b'\r\n')
                
                t1 = time.time()
                frames += 1
                bytes_sent += frame_len
                
                if t1 - last_time >= 1.0:
                    elapsed = t1 - last_time
                    telemetry_state['fps'] = round(frames / elapsed)
                    telemetry_state['bitrate'] = round((bytes_sent * 8) / elapsed / 1000000, 2)
                    telemetry_state['latency'] = round((t1 - t0) * 1000)
                    
                    frames = 0
                    bytes_sent = 0
                    last_time = t1
        finally:
            telemetry_state['active'] = False


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
        start_journal_stream(socketio)
        
        with log_history_lock:
            for payload in log_history:
                socketio.emit("log", payload, to=request.sid)

        emit_log("Client connected", source="backend", level="info", sid=request.sid)

    @socketio.on("shell_command")
    def handle_shell_command(data):
        command = ""
        if isinstance(data, dict):
            command = str(data.get("command", "")).strip()

        if not command:
            return

        if not command_allowed(command):
            emit_log("Shell command blocked by policy", source="shell", level="error", sid=request.sid)
            return

        socketio.start_background_task(run_cmd, socketio, request.sid, command)

    @socketio.on("power_off")
    def handle_power_off_req():
        if not command_allowed(POWER_OFF_COMMAND):
            emit_log("Power off command blocked by policy", source="power", level="error", sid=request.sid)
            return
        socketio.start_background_task(run_power_off, socketio, request.sid)

    @socketio.on('move')
    def handle_move(data):
        if isinstance(data, dict) and 'direction' in data:
            direction = data["direction"]
            log.info("Command: %s", direction)
            # Send movement command to Arduino (e.g. "move:w")
            try:
                from arduino import arduino
                arduino.send_command(f"move:{direction}")
            except Exception as e:
                log.exception("Failed to send move command to Arduino")
                emit_log(f"Arduino move failed: {e}", source="arduino", level="error", sid=request.sid)

    @socketio.on('action')
    def handle_action(data):
        if isinstance(data, dict):
            action_type = data.get("type")
            action_val = data.get("action")
            log.info(f"Action: {action_type} -> {action_val}")
            # Send auxiliary command to Arduino (e.g. "sideFlap:open")
            try:
                from arduino import arduino
                arduino.send_command(f"{action_type}:{action_val}")
            except Exception as e:
                log.exception("Failed to send action command to Arduino")
                emit_log(f"Arduino action failed: {e}", source="arduino", level="error", sid=request.sid)

    @app.route('/api/action', methods=['POST'])
    def api_action():
        data = request.json or {}
        action_type = data.get("type")
        action_val = data.get("action")
        if action_type and action_val:
            log.info(f"API Action: {action_type} -> {action_val}")
            try:
                from arduino import arduino
                arduino.send_command(f"{action_type}:{action_val}")
                return {"status": "ok", "message": "Command sent"}, 200
            except Exception as e:
                log.exception("Failed to send API action to Arduino")
                emit_log(f"Arduino API action failed: {e}", source="arduino", level="error")
                return {"status": "error", "message": "Arduino send failed"}, 500
        return {"status": "error", "message": "Missing type or action"}, 400
