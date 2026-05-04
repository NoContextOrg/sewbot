import logging
import threading

MAX_LOG_HISTORY = 100
log_history = []
log_history_lock = threading.Lock()
socketio_instance = None

class SocketIOLogHandler(logging.Handler):
    def emit(self, record):
        try:
            message = self.format(record)
            payload = {
                "text": message,
                "level": record.levelname.lower(),
                "source": "backend",
            }
            if socketio_instance:
                socketio_instance.emit("log", payload)
        except Exception:
            pass

def setup_logging(sio):
    global socketio_instance
    socketio_instance = sio
    
    root_logger = logging.getLogger()
    if root_logger.handlers:
        return logging.getLogger("sewbot")

    root_logger.setLevel(logging.INFO)
    
    logging.getLogger("werkzeug").setLevel(logging.WARNING)
    logging.getLogger("engineio").setLevel(logging.WARNING)
    logging.getLogger("socketio").setLevel(logging.WARNING)

    formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s", "%H:%M:%S")

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    root_logger.addHandler(stream_handler)

    socket_handler = SocketIOLogHandler()
    socket_handler.setFormatter(formatter)
    root_logger.addHandler(socket_handler)

    return logging.getLogger("sewbot")


def emit_log(text, source="backend", level="info", sid=None):
    payload = {
        "text": text,
        "level": level,
        "source": source,
    }
    
    with log_history_lock:
        log_history.append(payload)
        if len(log_history) > MAX_LOG_HISTORY:
            log_history.pop(0)

    if not socketio_instance:
        return

    if sid:
        socketio_instance.emit("log", payload, to=sid)
    else:
        socketio_instance.emit("log", payload)
