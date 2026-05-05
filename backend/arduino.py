import serial
import serial.tools.list_ports
import time
import logging
import threading
import os
from logger import emit_log

log = logging.getLogger("sewbot")

class ArduinoController:
    def __init__(self, baudrate=115200):
        self.baudrate = baudrate
        self.ser = None
        self.port = None
        self.read_thread = None
        self.stop_thread = threading.Event()
        self._last_connect_attempt = 0
        self._connect_cooldown = 5          # seconds between reconnect attempts
        self._failed_ports = set()           # ports that failed (e.g. permission denied)
        self.connect()

    def find_port(self):
        preferred = os.getenv("SEWBOT_ARDUINO_PORT", "").strip()

        port_infos = list(serial.tools.list_ports.comports())
        available_ports = [p.device for p in port_infos]
        log.info(f"Available ports: {available_ports}")

        if preferred:
            if preferred in available_ports or os.path.exists(preferred):
                log.info(f"Using SEWBOT_ARDUINO_PORT={preferred}")
                return preferred
            log.warning(
                "SEWBOT_ARDUINO_PORT was set but not found: %s (available: %s)",
                preferred,
                available_ports,
            )

        # Prefer USB serial devices when present. This avoids Raspberry Pi UART console chatter
        # when /dev/serial0 is enabled, and typically just works for Arduino boards.
        usb_candidates = []
        arduino_named = []
        for p in port_infos:
            dev = p.device
            desc = (getattr(p, "description", "") or "").lower()
            manu = (getattr(p, "manufacturer", "") or "").lower()

            if "arduino" in desc or "arduino" in manu:
                arduino_named.append(dev)

            if (
                dev.startswith("/dev/ttyACM")
                or dev.startswith("/dev/ttyUSB")
                or "usbmodem" in dev
                or "usbserial" in dev
            ):
                usb_candidates.append(dev)

        if arduino_named:
            return arduino_named[0]
        if usb_candidates:
            return usb_candidates[0]

        # Build a ranked candidate list. Prefer ports actually enumerated by
        # pyserial (they are more likely to be accessible) over ports that
        # merely exist on the filesystem (e.g. /dev/serial0 symlink).
        fallback_names = ['/dev/serial0', '/dev/ttyAMA0', '/dev/ttyS0']

        # 1) Enumerated ports that are also in our priority list
        candidates = [p for p in fallback_names if p in available_ports]
        # 2) Enumerated ports NOT in the priority list (catch-all)
        for p in available_ports:
            if p not in candidates:
                candidates.append(p)
        # 3) Priority ports that exist on the filesystem but weren't enumerated
        for p in fallback_names:
            if p not in candidates and os.path.exists(p):
                candidates.append(p)

        # Skip ports that previously failed (e.g. permission denied)
        for p in candidates:
            if p not in self._failed_ports:
                return p

        # If every candidate has failed, clear the failed set and try again
        # (permissions may have been fixed since last attempt)
        if candidates:
            self._failed_ports.clear()
            return candidates[0]

        return None

    def _normalize_outgoing_command(self, cmd: str) -> str:
        cleaned = (cmd or "").strip()
        if not cleaned:
            return ""

        # If caller already provided category:action, pass through.
        if ":" in cleaned:
            return cleaned

        lowered = cleaned.lower()

        # Allow simple debugging shorthands
        if lowered == "stop":
            return "move:stop"

        if 0 < len(lowered) <= 4 and all(c in "wasd" for c in lowered):
            return f"move:{lowered}"

        return cleaned

    def connect(self, force=False):
        """Attempt to connect to the Arduino serial port.

        Enforces a cooldown between attempts to prevent log spam when the
        port is unavailable.  Pass *force=True* to bypass the cooldown
        (used at startup).
        """
        now = time.time()
        if not force and (now - self._last_connect_attempt) < self._connect_cooldown:
            return   # too soon — skip this attempt
        self._last_connect_attempt = now

        try:
            self.stop_thread.set()
            if self.read_thread and self.read_thread.is_alive():
                self.read_thread.join(timeout=1.0)

            if self.ser and self.ser.is_open:
                self.ser.close()

            self.port = self.find_port()
            if not self.port:
                log.error("No serial ports found!")
                return

            try:
                self.ser = serial.Serial(self.port, self.baudrate, timeout=1)
                log.info(f"Connected to Arduino on {self.port} at {self.baudrate} baud.")
                self._failed_ports.discard(self.port)   # it worked, remove from failed set

                self.stop_thread.clear()
                self.read_thread = threading.Thread(target=self._read_serial_loop, daemon=True)
                self.read_thread.start()
            except Exception as e:
                log.error(f"Failed to connect to Arduino on {self.port}: {e}")
                self._failed_ports.add(self.port)       # remember this port failed
                err_text = str(e).lower()
                if "permission denied" in err_text or "errno 13" in err_text:
                    hint = (
                        f"Permission denied opening {self.port}. On Raspberry Pi, add the service user to the "
                        "'dialout' group (e.g. 'sudo usermod -aG dialout <user>') or set "
                        "SupplementaryGroups=dialout in the systemd unit, then restart the service."
                    )
                    emit_log(hint, source="arduino", level="error")
                    log.error(hint)
                    # Immediately retry with next candidate port
                    next_port = self.find_port()
                    if next_port and next_port != self.port:
                        log.info(f"Trying next candidate port: {next_port}")
                        self.port = next_port
                        try:
                            self.ser = serial.Serial(self.port, self.baudrate, timeout=1)
                            log.info(f"Connected to Arduino on {self.port} at {self.baudrate} baud.")
                            self._failed_ports.discard(self.port)
                            self.stop_thread.clear()
                            self.read_thread = threading.Thread(target=self._read_serial_loop, daemon=True)
                            self.read_thread.start()
                            return
                        except Exception as e2:
                            log.error(f"Failed to connect to Arduino on {self.port}: {e2}")
                            self._failed_ports.add(self.port)
                self.ser = None
        except Exception as e:
            log.error(f"Unexpected Arduino connect error: {e}")
            self.ser = None

    def _read_serial_loop(self):
        import threading
        last_alive_log = 0
        while not self.stop_thread.is_set():
            # Log thread health every 2 seconds
            now = time.time()
            if now - last_alive_log > 2:
                log.debug(f"[SERIAL THREAD] alive, thread={threading.current_thread().ident}")
                last_alive_log = now
            if self.ser and self.ser.is_open:
                try:
                    if self.ser.in_waiting > 0:
                        line = self.ser.readline().decode('utf-8', errors='ignore').strip()
                        log.debug(f"[SERIAL READ] {line}")
                        if line:
                            self._handle_incoming_line(line)
                    else:
                        time.sleep(0.01)
                except Exception as e:
                    log.error(f"Serial read error: {e}")
                    time.sleep(1)
            else:
                time.sleep(1)

    def _handle_incoming_line(self, line):
        # Expected format: log:info:message or just raw text
        # On shared Pi miniUART the first bytes can be lost, so we also
        # try to recover truncated "log:" prefixes (e.g. "og:info:..." or
        # "o:info:...").
        parsed = False
        if line.startswith("log:"):
            parsed = self._try_parse_log_line(line[4:])  # strip "log:"
        elif len(line) > 2 and ":" in line:
            # Check if it looks like a truncated log line — the part before
            # the first colon should be a known level or a suffix of one.
            first_colon = line.index(":")
            candidate_level = line[:first_colon].lower()
            known_levels = ["info", "warning", "warn", "error", "debug"]
            is_truncated_log = any(
                lvl.endswith(candidate_level) and len(candidate_level) <= len(lvl)
                for lvl in known_levels
            )
            if is_truncated_log:
                # Reconstruct: treat remaining text as level:message
                parsed = self._try_parse_log_line(line)

        if not parsed:
            # If not formatted as log:, just treat it as debug output
            emit_log(line, source="arduino", level="info")
            log.info(f"[ARDUINO RAW] {line}")

    def _try_parse_log_line(self, payload):
        """Parse 'level:message' payload.  Returns True if parsed successfully."""
        parts = payload.split(":", 1)
        if len(parts) < 2:
            return False
        # Recover partial level names (e.g. "nfo" -> "info")
        raw_level = parts[0].lower()
        level_map = {"info": "info", "nfo": "info", "fo": "info", "o": "info",
                     "warning": "warning", "warn": "warning", "arning": "warning",
                     "error": "error", "rror": "error", "ror": "error",
                     "debug": "debug", "ebug": "debug"}
        level = level_map.get(raw_level)
        if not level:
            return False
        msg = parts[1]
        emit_log(msg, source="arduino", level=level)
        if level == "error":
            log.error(f"[ARDUINO] {msg}")
        elif level in ("warning", "warn"):
            log.warning(f"[ARDUINO] {msg}")
        else:
            log.info(f"[ARDUINO] {msg}")
        return True

    def send_command(self, cmd: str):
        cmd = self._normalize_outgoing_command(cmd)
        if not cmd:
            return

        if not self.ser or not self.ser.is_open:
            log.warning("Serial not connected, trying to reconnect...")
            self.connect()   # cooldown enforced inside connect()

        if self.ser and self.ser.is_open:
            try:
                if not cmd.endswith('\n'):
                    cmd += '\n'
                self.ser.write(cmd.encode('utf-8'))
                self.ser.flush()     # ensure TX buffer is fully drained
                time.sleep(0.01)     # give the line time to settle before Arduino replies
                log.info(f"Sent to Arduino ({self.port}): {cmd.strip()}")
                log.debug(f"[SERIAL WRITE] {cmd.strip()}")
            except Exception as e:
                log.error(f"Error sending command to Arduino: {e}")
                self.ser = None
        else:
            log.warning(f"Arduino not connected. Ignored command: {cmd}")

arduino = ArduinoController()
