# ./src/serial_controller.py
from dotenv import load_dotenv, get_key
import os
import json
import serial
import threading
import time

class SerialController:
    def __init__(self, port=None, baudrate=115200, timeout=5):
        """Initialize the serial controller"""
        self.port = port  # Serial port number
        self.baudrate = baudrate  # Baud rate
        self.timeout = timeout  # Timeout in seconds
        self.ser = None  # Serial object
        self.is_connected = False  # Connection status

        self.current_cfs_path = ""  # Current CFS file path
        self.current_cfs = {}  # Current CFS data
        self.max = 100  # Maximum position
        self.min = 100  # Minimum position
        self.freq = 0.01  # Frequency
        self.decline_ratio = 0.5  # Decline ratio

    def connect(self, port=None, baudrate=None):
        """Connect to the serial port"""
        if self.is_connected:
            return True
        port = port or self.port
        if not port:
            return False
        baudrate = baudrate or self.baudrate
        try:
            self.ser = serial.Serial(port, baudrate=baudrate, timeout=self.timeout)
            self.port = port
            self.baudrate = baudrate
            self.is_connected = True
            print(f"Successfully connected to serial port {self.port}")
            return True
        except Exception as e:
            print(f"Error connecting to serial port: {e}")
            self.is_connected = False
            return False

    def disconnect(self):
        """Disconnect from the serial port"""
        if not self.is_connected:
            return True   
        try:
            if self.ser and self.ser.is_open:
                self.ser.close()
            self.is_connected = False
            print(f"Disconnected from serial port {self.port}")
            return True
        except Exception as e:
            print(f"Error disconnecting from serial port: {e}")
            return False

    def send_data(self, data):
        """Send data to the serial port"""
        if not self.is_connected:
            return False
        try:
            self.ser.write(data.encode('utf-8'))
            # print(f"[Sent]{self.port}: {data.strip()}")
            return True
        except Exception as e:
            print(f"Error occurred while sending data: {e}")
            return False

    def is_port_available(self, port):
        """Check if the serial port is available"""
        try:
            s = serial.Serial(port, timeout=1)
            s.close()
            return True
        except serial.SerialException:
            return False

    def get_serial_port(self):
        """Get the serial port"""
        return self.port
    
    def get_serial_port_from_env(self):
        """Get the serial port from .env file"""
        load_dotenv()
        serial_port = get_key('.env', 'SERIAL_PORT')
        return serial_port

    def load_cfs(self, cfs_path):
        """Load CFS data"""
        if not os.path.exists(cfs_path):
            self.current_cfs = {}
            return {}
        try:
            with open(cfs_path, 'r', encoding='utf-8') as file:
                content = json.load(file)
            self.current_cfs = content
            self.current_cfs_path = cfs_path
            return content
        except Exception as e:
            self.current_cfs = {}
            self.current_cfs_path = ""
            return {}

    def get_current_cfs(self):
        """Get the current CFS data"""
        return self.current_cfs
    
    def save_cfs(self, output_path=None):
        """Save the CFS data to a specified file"""
        path = output_path or self.current_cfs_path
        if not path or not path.endswith('.cfs'):
            return False
        try:
            with open(path, 'w', encoding='utf-8') as file:
                json.dump(self.current_cfs, file, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"Error saving CFS file: {e}")
            return False
        
    def export_cfs(self, cfs_data, file_path):
        """Export CFS data to a specified path"""
        try:
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(cfs_data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"Error exporting CFS file: {e}")
            return False
    
    def start_loop_send(self):
        """Start the loop sending process"""
        if not self.is_connected:
            return False
        if hasattr(self, '_loop_thread') and self._loop_thread and self._loop_thread.is_alive():
            return False
        self._loop_stop_event = threading.Event()
        self._loop_thread = threading.Thread(target=self._loop_send_worker, daemon=True)
        self._loop_thread.start()
        return True

    def stop_loop_send(self):
        """Stop the loop sending process"""
        if not hasattr(self, '_loop_stop_event'):
            return False
        self._loop_stop_event.set()
        self.send_data("DSTOP\n")
        return True
            
    def _loop_send_worker(self):
        """Worker thread for loop sending"""
        if self.freq == 0:
            return
        index = 1
        while not self._loop_stop_event.is_set() and self.is_connected:
            try:
                msg_type = self.max if index % 2 == 0 else self.min
                duration = (1 - self.decline_ratio) if index % 2 == 0 else self.decline_ratio
                message = f"L0{self.linear_map(msg_type)}I{int(duration * 1000 / self.freq)}\n"
                if not self.send_data(message):
                    break
                time.sleep(duration / self.freq)
                index += 1

                # Check stop event
                if self._loop_stop_event.is_set():
                    return
            except Exception as e:
                print(f"An error occurred during loop sending: {e}")
                break
    
    def linear_map(self, value, in_min=0, in_max=100, out_min=0, out_max=9999):
        """Map an integer value to a new range"""
        if in_min == in_max:
            return value
        value = max(in_min, min(value, in_max))
        return max(out_min, min(out_max, round(((value - in_min) / (in_max - in_min)) * (out_max - out_min) + out_min)))
    
    def new_page(self, page):
        """Switch page"""
        if not page or not self.current_cfs or page not in self.current_cfs:
            self.stop_loop_send()
        else:
            self.max = self.current_cfs[page]['max']
            self.min = self.current_cfs[page]['min']
            self.freq = self.current_cfs[page]['freq']
            self.decline_ratio = self.current_cfs[page]['decline_ratio']
            self.start_loop_send()

if __name__ == "__main__":
    controller = SerialController()
    controller.port = controller.get_serial_port_from_env()

    if controller.connect():
        # Send test data
        controller.send_data("L05000\n")
    
    # Load CFS data
    controller.load_cfs(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "cfs", "test.cfs"))
    # print(controller.get_current_cfs())

    # Switch page
    controller.new_page("1.jpg")
    time.sleep(5)
    controller.new_page("")
    time.sleep(3)
    controller.new_page("2.jpg")
    time.sleep(5)
    controller.stop_loop_send()

    # Disconnect
    controller.disconnect()