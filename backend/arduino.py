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

        # Fallback priority list of ports to try
        priority_ports = ['/dev/serial0', '/dev/ttyAMA0', '/dev/ttyS0']

        for p in priority_ports:
            # On Raspberry Pi, /dev/serial0 and /dev/ttyAMA0 are often not listed by list_ports
            if p in available_ports or os.path.exists(p):
                return p

        # If no priority port found, just pick the first available one if any
        if available_ports:
            return available_ports[0]

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

    def connect(self):
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
            
            self.stop_thread.clear()
            self.read_thread = threading.Thread(target=self._read_serial_loop, daemon=True)
            self.read_thread.start()
        except Exception as e:
            log.error(f"Failed to connect to Arduino on {self.port}: {e}")
            self.ser = None

    def _read_serial_loop(self):
        while not self.stop_thread.is_set():
            if self.ser and self.ser.is_open:
                try:
                    if self.ser.in_waiting > 0:
                        line = self.ser.readline().decode('utf-8', errors='ignore').strip()
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
        if line.startswith("log:"):
            parts = line.split(":", 2)
            if len(parts) >= 3:
                level = parts[1].lower()
                msg = parts[2]
                emit_log(msg, source="arduino", level=level)
                
                # Also log to backend terminal
                if level == "error":
                    log.error(f"[ARDUINO] {msg}")
                elif level == "warning" or level == "warn":
                    log.warning(f"[ARDUINO] {msg}")
                else:
                    log.info(f"[ARDUINO] {msg}")
                return

        # If not formatted as log:, just treat it as debug output
        emit_log(line, source="arduino", level="info")
        log.info(f"[ARDUINO RAW] {line}")

    def send_command(self, cmd: str):
        cmd = self._normalize_outgoing_command(cmd)
        if not cmd:
            return

        if not self.ser or not self.ser.is_open:
            log.warning("Serial not connected, trying to reconnect...")
            self.connect()

        if self.ser and self.ser.is_open:
            try:
                if not cmd.endswith('\n'):
                    cmd += '\n'
                self.ser.write(cmd.encode('utf-8'))
                log.info(f"Sent to Arduino ({self.port}): {cmd.strip()}")
            except Exception as e:
                log.error(f"Error sending command to Arduino: {e}")
                self.ser = None
        else:
            log.warning(f"Arduino not connected. Ignored command: {cmd}")

arduino = ArduinoController()
