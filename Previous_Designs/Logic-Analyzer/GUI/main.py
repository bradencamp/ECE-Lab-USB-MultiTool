"""
main.py

This module serves as the entry point for the application. It initializes the PyQt6
application, applies aesthetic styles, searches for a specific serial device, and
launches the appropriate window based on whether the device is found.

Dependencies:
- sys
- serial.tools.list_ports
- PyQt6.QtWidgets.QApplication
- LogicDisplay from LogicDisplay module
- SerialApp from connection module
- apply_styles from aesthetic module
"""

import sys
import serial.tools.list_ports
from PyQt6.QtWidgets import QApplication
from LogicDisplay import LogicDisplay
from connection import SerialApp
from aesthetic import apply_styles

def main():
    
    """
    The main function initializes the PyQt6 application, applies styles, and attempts
    to connect to a serial device with specified VID and PID. Depending on whether the
    device is found, it either opens the LogicDisplay window or the SerialApp connection
    window.

    Steps:
    1. Initialize the QApplication with command-line arguments.
    2. Apply aesthetic styles to the application (e.g., dark mode, icons).
    3. Search for a serial device with VID=1155 and PID=22336.
    4. If the device is found:
        - Create and display a LogicDisplay window with the device's port.
        - Print a message indicating automatic connection.
    5. If the device is not found:
        - Create and display a SerialApp window to allow user connection.
        - Print a message indicating that the connection window is opening.
    6. Execute the application's event loop and exit when done.
    """
    
    app = QApplication(sys.argv)
    apply_styles(app)

    # Attempt to find the device with vid=1155 and pid=22336
    vid = 1155
    pid = 22336
    ports = serial.tools.list_ports.comports()
    target_port = None
    for port in ports:
        if port.vid == vid and port.pid == pid:
            target_port = port.device
            break

    if target_port:
        # Device found, directly create LogicDisplay
        window = LogicDisplay(port=target_port, baudrate=115200, bufferSize=4096, channels=8)
        window.show()
        print(f"Automatically connected to device on port {target_port}")
    else:
        # Device not found, show SerialApp
        window = SerialApp()
        window.show()
        print("Device not found. Opening connection window.")

    sys.exit(app.exec())

if __name__ == '__main__':
    main()
