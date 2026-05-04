import traceback

def run_failsafe(error_msg):
    from flask import Flask, send_from_directory, request
    from flask_socketio import SocketIO
    import logging

    print("--- FATAL ERROR, LAUNCHING FAILSAFE MODE ---")
    print(error_msg)

    app = Flask(__name__, static_folder='../frontend/dist', static_url_path='/')
    socketio = SocketIO(app, cors_allowed_origins="*")

    @app.route('/')
    def serve():
        return send_from_directory(app.static_folder, 'index.html')

    @socketio.on('connect')
    def on_connect():
        payload = {
            "text": f"SYSTEM FAILURE PREVENTED BOOT:\n{error_msg}",
            "level": "error",
            "source": "backend"
        }
        socketio.emit('log', payload, to=request.sid)

    socketio.run(app, host='0.0.0.0', port=5000)


if __name__ == '__main__':
    try:
        try:
            import gevent.monkey
            gevent.monkey.patch_all()
        except ImportError:
            pass

        from flask import Flask
        from flask_socketio import SocketIO
        from logger import setup_logging
        from routes import setup_routes

        app = Flask(__name__, static_folder='../frontend/dist', static_url_path='/')
        socketio = SocketIO(app, cors_allowed_origins="*", async_mode='gevent')

        log = setup_logging(socketio)
        log.info("Starting initial hardware tests and heavy imports...")
        
        setup_routes(app, socketio)

        # Start heavy camera hardware logic in the background so it never blocks port 5000 from opening
        import camera
        def boot_camera():
            if not camera.init_camera():
                log.warning("Camera failed to initialize at startup. Will keep retrying during stream requests.")
        
        socketio.start_background_task(boot_camera)

        log.info("Finished booting! Starting Robot Server on http://0.0.0.0:5000")
        socketio.run(app, host='0.0.0.0', port=5000)

    except Exception as e:
        tb = traceback.format_exc()
        run_failsafe(tb)