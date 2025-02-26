"""
LogicDisplay.py

This module defines the LogicDisplay class, a PyQt6 QMainWindow that serves as the main interface
for the Logic Analyzer application. It allows users to select between different communication
protocols (Signal, I2C, SPI, UART) and manages the corresponding display modules. The LogicDisplay
handles the initialization of the user interface, loading of selected modules, and management of
serial communication parameters such as baud rate and buffer size.
"""

import sys
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QButtonGroup,
    QPushButton,
)
from PyQt6.QtGui import QAction
from PyQt6 import QtCore

from typing import Optional

from aesthetic import get_icon
from Signal import SignalDisplay
from I2C import I2CDisplay
from SPI import SPIDisplay
from UART import UARTDisplay


class LogicDisplay(QMainWindow):
    """
    LogicDisplay is the main window of the Logic Analyzer application. It provides an interface
    for users to select different communication protocols and displays the corresponding modules.
    
    Attributes:
        port (str): The serial port to which the device is connected.
        default_baudrate (int): The default baud rate for serial communication.
        baudrate (int): The current baud rate for serial communication.
        channels (int): The number of channels used in the logic analyzer.
        bufferSize (int): The size of the buffer for serial communication.
        current_module (Optional[QWidget]): The currently active display module.
    """

    def __init__(self, port: str, baudrate: int, bufferSize: int = 4096, channels: int = 8) -> None:
        """
        Initializes the LogicDisplay window with the specified serial port, baud rate, buffer size,
        and number of channels. It sets up the user interface and loads the default module.

        Args:
            port (str): The serial port to connect to.
            baudrate (int): The baud rate for serial communication.
            bufferSize (int, optional): The size of the buffer for serial communication. Defaults to 4096.
            channels (int, optional): The number of channels for the logic analyzer. Defaults to 8.
        """
        super().__init__()
        self.port = port
        self.default_baudrate = baudrate  # Store default baud rate
        self.baudrate = baudrate
        self.channels = channels
        self.bufferSize = bufferSize

        self.setWindowTitle("Logic Analyzer")
        self.setWindowIcon(get_icon())

        self.current_module: Optional[QWidget] = None
        self.init_ui()

        # Load the default module (Signal)
        self.load_module('Signal')

    def init_ui(self) -> None:
        """
        Initializes the user interface components of the LogicDisplay window, including the
        mode selection buttons and the area where the selected module is displayed.
        """
        # Create a central widget with vertical layout
        central_widget = QWidget()
        central_layout = QVBoxLayout(central_widget)
        central_layout.setContentsMargins(0, 0, 0, 0)
        central_layout.setSpacing(0)

        # Create a widget for the buttons
        button_widget = QWidget()
        button_layout = QHBoxLayout(button_widget)
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.setSpacing(0)

        # Create buttons for each mode
        self.signal_button = QPushButton('Signal')
        self.i2c_button = QPushButton('I2C')
        self.spi_button = QPushButton('SPI')
        self.uart_button = QPushButton('UART')

        # Make buttons checkable
        self.signal_button.setCheckable(True)
        self.i2c_button.setCheckable(True)
        self.spi_button.setCheckable(True)
        self.uart_button.setCheckable(True)

        # Create a button group for exclusive checking
        self.mode_button_group = QButtonGroup()
        self.mode_button_group.setExclusive(True)
        self.mode_button_group.addButton(self.signal_button)
        self.mode_button_group.addButton(self.i2c_button)
        self.mode_button_group.addButton(self.spi_button)
        self.mode_button_group.addButton(self.uart_button)

        # Set the default checked button
        self.signal_button.setChecked(True)

        # Add buttons to the layout
        button_layout.addWidget(self.signal_button)
        button_layout.addWidget(self.i2c_button)
        button_layout.addWidget(self.spi_button)
        button_layout.addWidget(self.uart_button)

        # Connect buttons to the handler
        self.signal_button.clicked.connect(lambda: self.load_module('Signal'))
        self.i2c_button.clicked.connect(lambda: self.load_module('I2C'))
        self.spi_button.clicked.connect(lambda: self.load_module('SPI'))
        self.uart_button.clicked.connect(lambda: self.load_module('UART'))

        # Create a widget to hold the current module
        self.module_widget = QWidget()
        self.module_layout = QVBoxLayout(self.module_widget)
        self.module_layout.setContentsMargins(0, 0, 0, 0)
        self.module_layout.setSpacing(0)

        # Add the button widget and the module widget to the central layout
        central_layout.addWidget(button_widget)
        central_layout.addWidget(self.module_widget)

        # Set the central widget
        self.setCentralWidget(central_widget)

    def load_module(self, module_name: str) -> None:
        """
        Loads the specified module into the LogicDisplay window. It handles the cleanup of
        the existing module and initializes the new module based on the selected communication
        protocol.

        Args:
            module_name (str): The name of the module to load. Expected values are 'Signal',
                               'I2C', 'SPI', or 'UART'.
        """
        # Remove the existing module widget if any
        if self.current_module:
            self.current_module.close()
            self.current_module.deleteLater()
            self.current_module = None

        # Clear the module_layout
        while self.module_layout.count():
            item = self.module_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        # Reset baud rate to default when switching modes
        if module_name != 'UART':
            self.baudrate = self.default_baudrate

        # Load the selected module
        if module_name == 'Signal':
            self.current_module = SignalDisplay(self.port, self.baudrate, self.bufferSize, self.channels)
            self.signal_button.setChecked(True)
        elif module_name == 'I2C':
            self.current_module = I2CDisplay(self.port, self.baudrate, self.bufferSize)
            self.i2c_button.setChecked(True)
        elif module_name == 'SPI':
            self.current_module = SPIDisplay(self.port, self.baudrate, self.bufferSize)
            self.spi_button.setChecked(True)
        elif module_name == 'UART':
            # Update baud rate if changed in UART mode
            self.current_module = UARTDisplay(self.port, self.baudrate, self.bufferSize)
            self.uart_button.setChecked(True)

        if self.current_module:
            self.module_layout.addWidget(self.current_module)
            self.current_module.show()
        else:
            # Placeholder if the module is not implemented
            placeholder_widget = QWidget()
            self.module_layout.addWidget(placeholder_widget)

    def update_baudrate(self, baudrate: int) -> None:
        """
        Updates the baud rate for serial communication. This method can be called to change
        the baud rate dynamically based on user input or other conditions.

        Args:
            baudrate (int): The new baud rate to set.
        """
        self.baudrate = baudrate

    def closeEvent(self, event: QtCore.QEvent) -> None:
        """
        Handles the close event of the LogicDisplay window. Ensures that the currently active
        module is properly closed before the window itself is closed.

        Args:
            event (Qt.QEvent): The close event triggered when the window is being closed.
        """
        if self.current_module:
            self.current_module.close()
        event.accept()
