import serial
import serial.tools.list_ports
import time
import logging

log = logging.getLogger("sewbot")

class ArduinoController:
    def __init__(self, baudrate=9600):
        self.baudrate = baudrate
        self.ser = None
        self.port = None
        self.connect()

    def find_port(self):
        # Priority list of ports to try
        priority_ports = ['/dev/serial0', '/dev/ttyAMA0', '/dev/ttyUSB0', '/dev/ttyACM0']
        
        # Get all available ports
        available_ports = [p.device for p in serial.tools.list_ports.comports()]
        log.info(f"Available ports: {available_ports}")

        # Try priority ports first
        for p in priority_ports:
            if p in available_ports:
                return p
        
        # If no priority port found, just pick the first available one if any
        if available_ports:
            return available_ports[0]
        
        return None

    def connect(self):
        self.port = self.find_port()
        if not self.port:
            log.error("No serial ports found!")
            return

        try:
            self.ser = serial.Serial(self.port, self.baudrate, timeout=1)
            log.info(f"Connected to Arduino on {self.port} at {self.baudrate} baud.")
        except Exception as e:
            log.error(f"Failed to connect to Arduino on {self.port}: {e}")
            self.ser = None

    def send_command(self, cmd: str):
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
