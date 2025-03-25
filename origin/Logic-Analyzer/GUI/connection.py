"""
connection.py

This module manages serial connections for the application. It provides the
SerialApp class, a PyQt6 QMainWindow that allows users to select, connect,
and disconnect from available serial COM ports. Upon successful connection,
it launches the LogicDisplay window to interact with the connected device.
"""

import sys
import serial.tools.list_ports
from PyQt6.QtWidgets import QMainWindow, QPushButton, QVBoxLayout, QWidget, QComboBox
from PyQt6.QtGui import QIcon
from typing import Optional
from aesthetic import get_icon
from LogicDisplay import LogicDisplay  # Ensure this is the correct file name


class SerialApp(QMainWindow):
    """
    SerialApp is a PyQt6 QMainWindow that provides a user interface for managing
    serial connections. It allows users to refresh available COM ports, connect
    to a selected port, and disconnect from the current connection.

    Attributes:
        logic_display_window (Optional[LogicDisplay]): Reference to the LogicDisplay window.
    """

    def __init__(self) -> None:
        """
        Initializes the SerialApp window, sets up the UI components, and configures
        the window's title and icon.
        """
        super().__init__()
        self.setWindowTitle("Serial Connection Manager")
        self.setWindowIcon(get_icon())
        self.logic_display_window: Optional[LogicDisplay] = None  # Reference to LogicDisplay window
        self.initUI()

    def initUI(self) -> None:
        """
        Sets up the user interface components, including the main widget, layout,
        COM ports dropdown, and control buttons (Refresh, Connect, Disconnect).
        """
        # Main widget and layout
        self.main_widget = QWidget()
        self.setCentralWidget(self.main_widget)
        layout = QVBoxLayout(self.main_widget)

        # Dropdown for COM ports
        self.combo_ports = QComboBox()
        self.refresh_ports()
        layout.addWidget(self.combo_ports)

        # Refresh button
        self.button_refresh = QPushButton("Refresh")
        self.button_refresh.clicked.connect(self.refresh_ports)
        layout.addWidget(self.button_refresh)

        # Connect button
        self.button_connect = QPushButton("Connect")
        self.button_connect.clicked.connect(self.connect_device)
        layout.addWidget(self.button_connect)

        # Disconnect button
        self.button_disconnect = QPushButton("Disconnect")
        self.button_disconnect.clicked.connect(self.disconnect_device)
        self.button_disconnect.setEnabled(False)
        layout.addWidget(self.button_disconnect)

    def refresh_ports(self) -> None:
        """
        Refreshes the list of available serial COM ports by clearing the current
        dropdown and repopulating it with the latest COM port information.
        """
        self.combo_ports.clear()
        ports = serial.tools.list_ports.comports()
        for port in ports:
            self.combo_ports.addItem(port.device)

    def connect_device(self) -> None:
        """
        Attempts to establish a connection to the selected serial COM port.
        If successful, it disables the Connect button, enables the Disconnect
        button, and opens the LogicDisplay window. If a connection is already
        open, it closes the previous LogicDisplay window before opening a new one.
        
        Prints status messages to the console regarding the connection status.
        """
        port_name = self.combo_ports.currentText()
        try:
            self.button_connect.setEnabled(False)
            self.button_disconnect.setEnabled(True)
            print(f"Connected to {port_name}")

            # Close the previous LogicDisplay window if it exists
            if self.logic_display_window:
                self.logic_display_window.close()

            # Create a new LogicDisplay window
            self.logic_display_window = LogicDisplay(port=port_name, baudrate=115200, channels=8)
            self.logic_display_window.show()

        except Exception as e:
            print(f"Failed to connect to {port_name}: {str(e)}")
            self.button_connect.setEnabled(True)
            self.button_disconnect.setEnabled(False)

    def disconnect_device(self) -> None:
        """
        Disconnects from the currently connected serial COM port by closing the
        LogicDisplay window. It also resets the Connect and Disconnect buttons'
        enabled states and prints a status message to the console.
        """
        # Close the LogicDisplay window when disconnecting the device
        if self.logic_display_window:
            self.logic_display_window.close()
            self.logic_display_window = None  # Reset the reference

        self.button_connect.setEnabled(True)
        self.button_disconnect.setEnabled(False)
        print("Disconnected")
