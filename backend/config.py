import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

CAMERA_WIDTH = 640
CAMERA_HEIGHT = 480
CAMERA_FPS = 15
CAMERA_JPEG_QUALITY = int(os.getenv("CAMERA_JPEG_QUALITY", "40"))
CAMERA_BUFFER_GRABS = int(os.getenv("CAMERA_BUFFER_GRABS", "2"))
MAX_READ_RETRIES = 5
CAMERA_KILL_STALE = os.getenv("SEWBOT_CAMERA_KILL_STALE", "true").lower() in ("1", "true", "yes", "on")

JOURNALCTL_COMMAND = os.getenv("SEWBOT_JOURNALCTL_COMMAND", "journalctl -f -n 200")
POWER_OFF_COMMAND = os.getenv("SEWBOT_POWER_OFF_COMMAND", "sudo shutdown -h now")

SUDO_PASSWORD = os.getenv("SEWBOT_SUDO_PASSWORD", "")
SHELL_ALLOW_ANY = os.getenv("SEWBOT_SHELL_ALLOW_ANY", "true").lower() in ("1", "true", "yes", "on")
SHELL_ALLOWED_COMMANDS = [
    cmd.strip() for cmd in os.getenv("SEWBOT_SHELL_ALLOWED_COMMANDS", "").split(",") if cmd.strip()
]

def command_allowed(command):
    if SHELL_ALLOW_ANY:
        return True

    cleaned = command.strip()
    if not cleaned or not SHELL_ALLOWED_COMMANDS:
        return False

    return any(cleaned == allowed or cleaned.startswith(f"{allowed} ") for allowed in SHELL_ALLOWED_COMMANDS)
