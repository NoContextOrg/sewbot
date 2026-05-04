import os
import subprocess
import threading
from config import JOURNALCTL_COMMAND, POWER_OFF_COMMAND, SUDO_PASSWORD
from logger import emit_log

shell_cwd = os.getcwd()
journal_stream_lock = threading.Lock()
journal_stream_active = False

def start_journal_stream(sio):
    global journal_stream_active
    with journal_stream_lock:
        if journal_stream_active:
            return
        journal_stream_active = True

    sio.start_background_task(_journal_stream_loop, sio)

def _journal_stream_loop(sio):
    while True:
        try:
            proc = subprocess.Popen(
                JOURNALCTL_COMMAND,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )
            for line in iter(proc.stdout.readline, ""):
                if line:
                    emit_log(line.replace('\r', '').strip(), source="journal", level="info")
            proc.stdout.close()
            proc.wait()
            sio.sleep(2)
        except Exception as exc:
            emit_log(f"Journal stream error: {exc}", source="journal", level="error")
            sio.sleep(5)

def run_cmd(sio, sid, cmd):
    global shell_cwd
    if cmd == "cd" or cmd.startswith("cd "):
        target = cmd[3:].strip() if cmd.startswith("cd ") else "~"
        if not target:
            target = "~"
        try:
            os.chdir(os.path.expanduser(target))
            shell_cwd = os.getcwd()
        except Exception as exc:
            emit_log(str(exc), source="shell", level="error", sid=sid)
        return
        
    try:
        proc = subprocess.Popen(
            cmd,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            cwd=shell_cwd
        )
        for line in iter(proc.stdout.readline, ""):
            if line:
                emit_log(line.replace('\r', '').strip(), source="shell", level="info", sid=sid)
        proc.stdout.close()
        proc.wait()
    except Exception as exc:
        emit_log(str(exc), source="shell", level="error", sid=sid)

def run_power_off(sio, sid):
    emit_log("Power off requested", source="power", level="warning", sid=sid)
    cmd = POWER_OFF_COMMAND
    if SUDO_PASSWORD and "sudo " in cmd:
        cmd = cmd.replace("sudo ", f"echo {SUDO_PASSWORD} | sudo -S ")
        
    try:
        subprocess.run(cmd, shell=True)
        sio.sleep(0.5)
        emit_log("Shutdown command successfully dispatched.", source="power", level="warning", sid=sid)
    except Exception as exc:
        emit_log(f"Shutdown failed: {exc}", source="power", level="error", sid=sid)
