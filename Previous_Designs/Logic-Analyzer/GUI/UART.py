"""
UART.py

This module defines classes and functionalities related to UART (Universal Asynchronous Receiver/Transmitter) 
communication, data processing, decoding, and graphical display for a Logic Analyzer application. It includes:

- UARTWorker: A QThread subclass that manages UART data reading, decoding, and signal emission.
- UARTChannelButton: A QPushButton subclass that allows for context menu operations like renaming and resetting.
- UARTConfigDialog: A QDialog subclass for configuring UART channel settings.
- FixedYViewBox: A custom PyQtGraph ViewBox that restricts scaling and translation on the Y-axis.
- UARTDisplay: A QWidget subclass that provides the main interface for displaying and interacting with UART data, 
  including plotting, control buttons, and trigger configurations.

Dependencies:
- sys, serial, math, time, numpy, pyqtgraph
- PyQt6.QtWidgets, PyQt6.QtGui, PyQt6.QtCore
- collections.deque
- InterfaceCommands (custom module)
- aesthetic (custom module)
"""

import sys
import serial
import math
import time
import numpy as np
import pyqtgraph as pg
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QInputDialog,
    QMenu,
    QPushButton,
    QLabel,
    QLineEdit,
    QComboBox,
    QDialog,
    QSizePolicy,
)
from PyQt6.QtGui import QFont, QIntValidator
from PyQt6.QtCore import QTimer, QThread, pyqtSignal, Qt
from collections import deque
from InterfaceCommands import (
    get_trigger_edge_command,
    get_trigger_pins_command,
)
from aesthetic import get_icon


class UARTWorker(QThread):
    """
    UARTWorker handles UART communication in a separate thread. It reads incoming data from
    the serial port, decodes UART signals for multiple channels, and emits signals when data 
    or decoded messages are ready for processing.

    Attributes:
        data_ready (pyqtSignal): Signal emitted when new raw data is ready. Carries the data value and sample index.
        decoded_message_ready (pyqtSignal): Signal emitted when a decoded UART message is ready. Carries a dictionary with message details.
    """

    data_ready = pyqtSignal(int, int)  # For raw data values and sample indices
    decoded_message_ready = pyqtSignal(dict)  # For decoded messages

    def __init__(self, port, baudrate, channels=8, uart_configs=None):
        """
        Initializes the UARTWorker thread with the specified UART configurations.

        Args:
            port (str): The serial port to connect to (e.g., 'COM3', '/dev/ttyUSB0').
            baudrate (int): The baud rate for UART communication.
            channels (int, optional): Number of UART channels to monitor. Defaults to 8.
            uart_configs (list of dict, optional): Configuration dictionaries for each UART channel. 
                                                   If None, default configurations are applied.
        """
        super().__init__()
        self.is_running = True
        self.channels = channels
        self.uart_configs = uart_configs if uart_configs else [{} for _ in range(channels)]
        self.trigger_modes = ['No Trigger'] * self.channels

        # Initialize UART decoding variables for each channel
        self.sample_idx = 0  # Initialize sample index
        self.states = ['IDLE'] * self.channels
        self.bit_counts = [0] * self.channels
        self.current_bytes = [0] * self.channels
        self.last_transition_times = [0] * self.channels
        self.decoded_messages = [[] for _ in range(self.channels)]
        self.sample_rates = [0] * self.channels  # Sample rate per channel, derived from baud rate
        self.baud_rates = [9600] * self.channels  # Default baud rate
        self.bit_timing_error = [0.0] * self.channels  # For fractional bit timing
        self.start_bits_detected = [False] * self.channels  # For start bit detection
        self.next_sample_times = [0.0] * self.channels  # Initialize next_sample_times per channel
        self.last_bits = [1] * self.channels  # For edge detection
        self.stop_bit_counters = [0] * self.channels  # Initialize stop_bit_counters per channel

        try:
            self.serial = serial.Serial(port, baudrate)
        except serial.SerialException as e:
            print(f"Failed to open serial port: {str(e)}")
            self.is_running = False

    def set_trigger_mode(self, channel_idx, mode):
        """
        Sets the trigger mode for a specific UART channel.

        Args:
            channel_idx (int): The index of the UART channel (0-based).
            mode (str): The trigger mode to set (e.g., 'No Trigger', 'Rising Edge', 'Falling Edge').
        """
        self.trigger_modes[channel_idx] = mode

    def set_baud_rate(self, channel_idx, baud_rate):
        """
        Sets the baud rate for a specific UART channel.

        Args:
            channel_idx (int): The index of the UART channel (0-based).
            baud_rate (int): The baud rate to set for the channel.
        """
        self.baud_rates[channel_idx] = baud_rate

    def set_sample_rate(self, channel_idx, sample_rate):
        """
        Sets the sample rate for a specific UART channel.

        Args:
            channel_idx (int): The index of the UART channel (0-based).
            sample_rate (int): The sample rate in Hz to set for the channel.
        """
        self.sample_rates[channel_idx] = sample_rate

    def run(self):
        """
        The main loop of the worker thread. Continuously reads data from the serial port,
        processes UART decoding, and emits signals when data or decoded messages are ready.
        """
        data_buffer = deque(maxlen=1000)

        while self.is_running:
            if self.serial.in_waiting:
                raw_data = self.serial.read(self.serial.in_waiting).splitlines()
                for line in raw_data:
                    try:
                        data_value = int(line.strip())
                        data_buffer.append(data_value)
                        self.data_ready.emit(data_value, self.sample_idx)  # Emit data_value and sample_idx
                        self.decode_uart(data_value, self.sample_idx)
                        self.sample_idx += 1  # Increment sample index
                    except ValueError:
                        continue

    def decode_uart(self, data_value, sample_idx):
        """
        Decodes UART data for each enabled channel based on the current state machine.

        Args:
            data_value (int): The raw data value read from the serial port.
            sample_idx (int): The current sample index.
        """
        for ch in range(self.channels):
            # Only decode if the channel is enabled
            uart_config = self.uart_configs[ch]
            if not uart_config.get('enabled', False):
                continue

            # Get the bit for this channel
            data_channel = uart_config.get('data_channel', ch + 1) - 1  # Adjust for zero-based index
            bit = (data_value >> data_channel) & 1

            # Apply polarity
            polarity = uart_config.get('polarity', 'Standard')
            if polarity == 'Inverted':
                bit = 1 - bit

            # Get sample rate and baud rate
            sample_rate = uart_config.get('sample_rate', None)
            baud_rate = uart_config.get('baud_rate', 9600)
            if sample_rate is None or baud_rate == 0:
                continue  # Cannot decode without sample rate and baud rate

            # Calculate number of samples per bit
            samples_per_bit = 16  # Fixed for simplicity; can be adjusted based on sample_rate and baud_rate

            # State machine for UART decoding
            state = self.states[ch]
            bit_count = self.bit_counts[ch]
            current_byte = self.current_bytes[ch]
            next_sample_time = self.next_sample_times[ch]
            stop_bits = uart_config.get('stop_bits', 1)
            data_format = uart_config.get('data_format', 'ASCII')
            stop_bit_counter = self.stop_bit_counters[ch]  # Retrieve stop_bit_counter
            last_bit = self.last_bits[ch]

            if state == 'IDLE':
                if bit == 0 and last_bit == 1:
                    # Start bit detected (falling edge)
                    state = 'START_BIT'
                    bit_count = 0
                    current_byte = 0
                    next_sample_time = sample_idx + (samples_per_bit * 0.5)  # Sample in the middle of first data bit
            elif state == 'START_BIT':
                # Wait for first data bit
                if sample_idx >= next_sample_time - samples_per_bit:
                    state = 'DATA_BITS'
            elif state == 'DATA_BITS':
                if sample_idx >= next_sample_time:
                    # Sample data bit
                    current_byte |= (bit << bit_count)
                    bit_count += 1
                    next_sample_time += samples_per_bit  # Schedule next bit sample time
                    if bit_count >= 8:
                        state = 'STOP_BITS'
                        stop_bit_counter = 0  # Initialize stop_bit_counter
            elif state == 'STOP_BITS':
                if sample_idx >= next_sample_time:
                    # Sample stop bit
                    if bit == 1:
                        # Valid stop bit
                        stop_bit_counter += 1
                        next_sample_time += samples_per_bit
                        if stop_bit_counter >= stop_bits:
                            # Byte is complete
                            # Emit decoded byte
                            self.decoded_message_ready.emit({
                                'channel': ch,
                                'data': current_byte,
                                'sample_idx': sample_idx,
                                'data_format': data_format,
                            })
                            state = 'IDLE'
                    else:
                        # Invalid stop bit
                        state = 'IDLE'
            else:
                state = 'IDLE'

            # Update states
            self.states[ch] = state
            self.bit_counts[ch] = bit_count
            self.current_bytes[ch] = current_byte
            self.next_sample_times[ch] = next_sample_time  # Update next_sample_time
            self.stop_bit_counters[ch] = stop_bit_counter  # Update stop_bit_counter
            self.last_bits[ch] = bit  # Update last_bit

    def reset_decoding_states(self):
        """
        Resets the decoding state machine for all UART channels. Clears sample indices,
        states, bit counts, current bytes, next sample times, decoded messages, and stop bit counters.
        """
        self.sample_idx = 0  # Reset sample index
        self.states = ['IDLE'] * self.channels
        self.bit_counts = [0] * self.channels
        self.current_bytes = [0] * self.channels
        self.next_sample_times = [0.0] * self.channels  # Reset next_sample_times
        self.decoded_messages = [[] for _ in range(self.channels)]
        self.stop_bit_counters = [0] * self.channels
        self.last_bits = [1] * self.channels

    def stop_worker(self):
        """
        Stops the worker thread by setting the running flag to False and closing the serial port if open.
        """
        self.is_running = False
        if self.serial.is_open:
            self.serial.close()


class UARTChannelButton(QPushButton):
    """
    UARTChannelButton is a QPushButton subclass representing a UART channel button.
    It allows users to rename the button label, reset it to default, and open configuration dialogs 
    via a context menu.

    Signals:
        configure_requested (pyqtSignal): Emitted when a configuration is requested for the channel.
        reset_requested (pyqtSignal): Emitted when a reset to default is requested for the channel.
    """

    configure_requested = pyqtSignal(int)  # Signal to notify when configure is requested
    reset_requested = pyqtSignal(int)      # New signal for reset

    def __init__(self, label, channel_idx, parent=None):
        """
        Initializes the UARTChannelButton with a given label and channel index.

        Args:
            label (str): The initial label of the button.
            channel_idx (int): The index of the UART channel (0-based).
            parent (QWidget, optional): The parent widget. Defaults to None.
        """
        super().__init__(label, parent)
        self.channel_idx = channel_idx  # Store the index of the UART channel
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)
        self.default_label = label

    def show_context_menu(self, position):
        """
        Displays a context menu with options to rename, reset, or configure the UART channel.

        Args:
            position (QPoint): The position where the context menu is requested.
        """
        menu = QMenu()
        rename_action = menu.addAction("Rename")
        reset_action = menu.addAction("Reset to Default")
        configure_action = menu.addAction("Configure")  # Add the Configure option
        action = menu.exec(self.mapToGlobal(position))
        if action == rename_action:
            new_label, ok = QInputDialog.getText(
                self, "Rename Button", "Enter new label:", text=self.text()
            )
            if ok and new_label:
                self.setText(new_label)
        elif action == reset_action:
            self.setText(self.default_label)
            self.reset_requested.emit(self.channel_idx)  # Emit reset signal
        elif action == configure_action:
            self.configure_requested.emit(self.channel_idx)  # Emit signal to open configuration dialog


class UARTConfigDialog(QDialog):
    """
    UARTConfigDialog provides a dialog window for configuring UART channel settings such as 
    data channel, polarity, stop bits, and data format.

    Attributes:
        current_config (dict): The current configuration settings for the UART channel.
    """

    def __init__(self, current_config, parent=None):
        """
        Initializes the UARTConfigDialog with the current configuration.

        Args:
            current_config (dict): The current configuration settings for the UART channel.
            parent (QWidget, optional): The parent widget. Defaults to None.
        """
        super().__init__(parent)
        self.setWindowTitle("UART Configuration")
        self.current_config = current_config  # Dictionary to hold current configurations

        self.init_ui()

    def init_ui(self):
        """
        Sets up the user interface components of the configuration dialog, including 
        input fields for data channel, polarity, stop bits, and data format.
        """
        layout = QVBoxLayout()

        # Data Channel Selection
        data_layout = QHBoxLayout()
        data_label = QLabel("Data Channel:")
        self.data_combo = QComboBox()
        self.data_combo.addItems([f"Channel {i+1}" for i in range(8)])
        self.data_combo.setCurrentIndex(self.current_config.get('data_channel', 1) - 1)
        data_layout.addWidget(data_label)
        data_layout.addWidget(self.data_combo)
        layout.addLayout(data_layout)

        # Polarity Selection
        polarity_layout = QHBoxLayout()
        polarity_label = QLabel("Polarity:")
        self.polarity_combo = QComboBox()
        self.polarity_combo.addItems(["Standard", "Inverted"])
        self.polarity_combo.setCurrentText(self.current_config.get('polarity', 'Standard'))
        polarity_layout.addWidget(polarity_label)
        polarity_layout.addWidget(self.polarity_combo)
        layout.addLayout(polarity_layout)

        # Stop Bits Selection
        stop_bits_layout = QHBoxLayout()
        stop_bits_label = QLabel("Stop Bits:")
        self.stop_bits_combo = QComboBox()
        self.stop_bits_combo.addItems(['0', '1', '2', '3'])
        self.stop_bits_combo.setCurrentText(str(self.current_config.get('stop_bits', 1)))
        stop_bits_layout.addWidget(stop_bits_label)
        stop_bits_layout.addWidget(self.stop_bits_combo)
        layout.addLayout(stop_bits_layout)

        # Data Format Selection
        format_layout = QHBoxLayout()
        format_label = QLabel("Data Format:")
        self.format_combo = QComboBox()
        self.format_combo.addItems(["Binary", "Decimal", "Hex", "ASCII"])
        self.format_combo.setCurrentText(self.current_config.get('data_format', 'ASCII'))
        format_layout.addWidget(format_label)
        format_layout.addWidget(self.format_combo)
        layout.addLayout(format_layout)

        # Buttons
        button_layout = QHBoxLayout()
        ok_button = QPushButton("OK")
        cancel_button = QPushButton("Cancel")
        ok_button.clicked.connect(self.accept)
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)

        self.setLayout(layout)

    def get_configuration(self):
        """
        Retrieves the configuration settings input by the user.

        Returns:
            dict: A dictionary containing the updated UART configuration settings.
        """
        return {
            'data_channel': self.data_combo.currentIndex() + 1,
            'polarity': self.polarity_combo.currentText(),
            'stop_bits': int(self.stop_bits_combo.currentText()),
            'data_format': self.format_combo.currentText(),
        }


class FixedYViewBox(pg.ViewBox):
    """
    FixedYViewBox is a custom PyQtGraph ViewBox that restricts scaling and translation
    along the Y-axis, allowing only horizontal scaling and movement.
    """

    def __init__(self, *args, **kwargs):
        """
        Initializes the FixedYViewBox with the provided arguments.
        """
        super().__init__(*args, **kwargs)

    def scaleBy(self, s=None, center=None, x=None, y=None):
        """
        Overrides the scaleBy method to fix the Y-axis scaling to 1.0, preventing vertical scaling.

        Args:
            s: Scaling factor (unused for Y-axis).
            center: Center point for scaling.
            x (float, optional): Scaling factor for X-axis.
            y (float, optional): Scaling factor for Y-axis (fixed to 1.0).
        """
        y = 1.0  # Fix y-scaling
        if x is None:
            if s is None:
                x = 1.0
            elif isinstance(s, dict):
                x = s.get('x', 1.0)
            elif isinstance(s, (list, tuple)):
                x = s[0] if len(s) > 0 else 1.0
            else:
                x = s
        super().scaleBy(x=x, y=y, center=center)

    def translateBy(self, t=None, x=None, y=None):
        """
        Overrides the translateBy method to fix the Y-axis translation to 0.0, preventing vertical movement.

        Args:
            t: Translation value (unused for Y-axis).
            x (float, optional): Translation value for X-axis.
            y (float, optional): Translation value for Y-axis (fixed to 0.0).
        """
        y = 0.0  # Fix y-translation
        if x is None:
            if t is None:
                x = 0.0
            elif isinstance(t, dict):
                x = t.get('x', 0.0)
            elif isinstance(t, (list, tuple)):
                x = t[0] if len(t) > 0 else 0.0
            else:
                x = t
        super().translateBy(x=x, y=y)


class UARTDisplay(QWidget):
    """
    UARTDisplay provides the main interface for displaying and interacting with UART data.
    It includes graphical plots, control buttons, channel configuration options, and decoded 
    message displays.

    Attributes:
        port (str): Serial port for communication.
        baudrate (int): Baud rate for UART communication.
        bufferSize (int): Size of the data buffer.
        channels (int): Number of UART channels to monitor.
        sample_rate (int): Sampling rate in Hz.
        data_buffer (list of deque): Data buffers for each UART channel.
        is_single_capture (bool): Flag indicating if a single capture is active.
        current_trigger_modes (list of str): Current trigger modes for each UART channel.
        trigger_mode_options (list of str): Available trigger mode options.
        uart_configs (list of dict): Configuration settings for each UART channel.
        available_baud_rates (list of int): List of available baud rates for selection.
        selected_baud_rate (int): Currently selected baud rate.
        uart_channel_enabled (list of bool): Flags indicating if each UART channel is enabled.
        setup_ui (method): Method to set up the user interface components.
        timer (QTimer): Timer for updating the plot periodically.
        is_reading (bool): Flag indicating if data reading is active.
        worker (UARTWorker): Worker thread handling UART communication and decoding.
        channel_curves (list of PlotDataItem): Plot curves for each UART channel.
        decoded_texts (list): Text items for displaying decoded messages.
        decoded_messages_per_channel (list of list): Decoded messages for each UART channel.
    """

    def __init__(self, port, baudrate, bufferSize, channels=8):
        """
        Initializes the UARTDisplay with the specified UART parameters and sets up the UI.

        Args:
            port (str): Serial port for communication.
            baudrate (int): Baud rate for UART communication.
            bufferSize (int): Size of the data buffer.
            channels (int, optional): Number of UART channels to monitor. Defaults to 8.
        """
        super().__init__()
        self.port = port
        self.baudrate = baudrate
        self.channels = channels
        self.bufferSize = bufferSize
        self.sample_rate = None  # Initialize sample_rate

        self.data_buffer = [deque(maxlen=self.bufferSize) for _ in range(self.channels)]  # 8 channels
        self.sample_indices = deque(maxlen=self.bufferSize)
        self.total_samples = 0

        self.is_single_capture = False

        self.current_trigger_modes = ['No Trigger'] * self.channels
        self.trigger_mode_options = ['No Trigger', 'Rising Edge', 'Falling Edge']

        # Initialize UART configurations with default settings per channel
        self.uart_configs = [
            {
                'data_channel': i + 1,
                'polarity': 'Standard',
                'stop_bits': 1,
                'data_format': 'ASCII',
                'baud_rate': 9600,
                'enabled': False,
                'sample_rate': None,  # Will be calculated based on baud rate
            } for i in range(self.channels)
        ]

        # Default baud rates
        self.available_baud_rates = [300, 1200, 2400, 4800, 9600, 19200, 38400, 57600, 74880, 115200]
        self.selected_baud_rate = 9600  # Default baud rate

        self.uart_channel_enabled = [False] * self.channels  # Track which UART channels are enabled

        self.setup_ui()
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_plot)

        self.is_reading = False

        self.worker = UARTWorker(self.port, self.baudrate, channels=self.channels, uart_configs=self.uart_configs)
        self.worker.data_ready.connect(self.handle_data_value)
        self.worker.decoded_message_ready.connect(self.display_decoded_message)
        self.worker.start()

        # Create curves for each channel
        self.channel_curves = []
        for ch in range(self.channels):
            curve = self.plot.plot(pen=pg.mkPen(color=self.colors[ch % len(self.colors)], width=2))
            curve.setVisible(False)
            self.channel_curves.append(curve)

        # For displaying decoded messages
        self.decoded_texts = []
        self.decoded_messages_per_channel = [[] for _ in range(self.channels)]
        
        self.update_sample_rates()

    def setup_ui(self):
        """
        Sets up the user interface components, including the plot area, channel buttons, 
        trigger mode buttons, baud rate selector, and control buttons.
        """
        main_layout = QVBoxLayout(self)

        plot_layout = QHBoxLayout()
        main_layout.addLayout(plot_layout)

        self.graph_layout = pg.GraphicsLayoutWidget()
        plot_layout.addWidget(self.graph_layout, stretch=3)  # Allocate more space to the graph

        self.plot = self.graph_layout.addPlot(viewBox=FixedYViewBox())

        self.plot.setXRange(0, self.bufferSize / 1e6, padding=0)
        self.plot.setLimits(xMin=0, xMax=self.bufferSize / 1e6)
        self.plot.enableAutoRange(axis=pg.ViewBox.XAxis, enable=False)
        self.plot.setYRange(-2, 2 * self.channels, padding=0)  # 8 channels
        self.plot.enableAutoRange(axis=pg.ViewBox.XAxis, enable=False)
        self.plot.enableAutoRange(axis=pg.ViewBox.YAxis, enable=False)
        self.plot.showGrid(x=True, y=True)
        self.plot.getAxis('left').setTicks([])
        self.plot.getAxis('left').setStyle(showValues=False)
        self.plot.getAxis('left').setPen(None)
        self.plot.setLabel('bottom', 'Time', units='s')

        self.colors = ['#FF6EC7', '#39FF14', '#FF486D', '#BF00FF', '#FFFF33', '#FFA500', '#00F5FF', '#BFFF00']

        button_layout = QGridLayout()
        plot_layout.addLayout(button_layout, stretch=1)  # Allocate less space to the control panel

        self.channel_buttons = []
        self.trigger_mode_buttons = []

        for i in range(self.channels):
            row = i
            uart_config = self.uart_configs[i]
            data_channel = uart_config['data_channel']
            label = f"UART {i+1}\nCh{data_channel}"
            button = UARTChannelButton(label, channel_idx=i)

            # Set size policy and fixed width
            button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
            button.setFixedWidth(100)  # Set the fixed width for the button

            button.setCheckable(True)
            button.setChecked(False)
            button.toggled.connect(lambda checked, idx=i: self.toggle_channel(idx, checked))
            button.configure_requested.connect(self.open_configuration_dialog)
            button_layout.addWidget(button, row, 0)

            # Trigger Mode Button
            trigger_button = QPushButton(f"Trigger - {self.current_trigger_modes[i]}")
            trigger_button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
            trigger_button.setFixedWidth(120)
            trigger_button.clicked.connect(lambda _, idx=i: self.toggle_trigger_mode(idx))
            button_layout.addWidget(trigger_button, row, 1)

            self.channel_buttons.append(button)
            self.trigger_mode_buttons.append(trigger_button)

            button.reset_requested.connect(self.reset_channel_to_default)

        # Baud Rate Selection
        baud_rate_layout = QHBoxLayout()
        baud_rate_label = QLabel("Baud Rate:")
        self.baud_rate_combo = QComboBox()
        self.baud_rate_combo.addItems([str(br) for br in self.available_baud_rates])
        self.baud_rate_combo.setCurrentText("9600")
        baud_rate_layout.addWidget(baud_rate_label)
        baud_rate_layout.addWidget(self.baud_rate_combo)
        baud_rate_layout.addStretch()
        main_layout.addLayout(baud_rate_layout)

        # Control buttons layout
        control_buttons_layout = QHBoxLayout()

        self.toggle_button = QPushButton("Start")
        self.toggle_button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
        self.toggle_button.setFixedWidth(80)
        self.toggle_button.clicked.connect(self.toggle_reading)
        control_buttons_layout.addWidget(self.toggle_button)

        self.single_button = QPushButton("Single")
        self.single_button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
        self.single_button.setFixedWidth(80)
        self.single_button.clicked.connect(self.start_single_capture)
        control_buttons_layout.addWidget(self.single_button)

        main_layout.addLayout(control_buttons_layout)

    def toggle_channel(self, channel_idx, is_checked):
        """
        Toggles the visibility and configuration of a specific UART channel.

        Args:
            channel_idx (int): The index of the UART channel (0-based).
            is_checked (bool): Whether the channel is enabled.
        """
        self.uart_channel_enabled[channel_idx] = is_checked  # Update the enabled list
        self.uart_configs[channel_idx]['enabled'] = is_checked

        # Update curve visibility
        curve = self.channel_curves[channel_idx]
        curve.setVisible(is_checked)

        button = self.channel_buttons[channel_idx]
        if is_checked:
            color = self.colors[channel_idx % len(self.colors)]
            text_color = 'black' if self.is_light_color(color) else 'white'
            button.setStyleSheet(f"QPushButton {{ background-color: {color}; color: {text_color}; "
                                 f"border: 1px solid #555; border-radius: 5px; padding: 5px; "
                                 f"text-align: left; }}")
        else:
            button.setStyleSheet("")

    def is_light_color(self, hex_color):
        """
        Determines if a given hex color is light based on its luminance.

        Args:
            hex_color (str): The hex color string (e.g., '#FF6EC7').

        Returns:
            bool: True if the color is light, False otherwise.
        """
        hex_color = hex_color.lstrip('#')
        r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
        return luminance > 0.5

    def reset_channel_to_default(self, channel_idx):
        """
        Resets the configuration of a specific UART channel to its default settings.

        Args:
            channel_idx (int): The index of the UART channel (0-based).
        """
        # Reset the channel configuration to default settings
        default_config = {
            'data_channel': channel_idx + 1,
            'polarity': 'Standard',
            'stop_bits': 1,
            'data_format': 'ASCII',
            'baud_rate': 9600,
            'enabled': False,
            'sample_rate': None,
        }
        self.uart_configs[channel_idx] = default_config
        print(f"Channel {channel_idx+1} reset to default configuration: {default_config}")

        # Reset the button's label to default
        self.channel_buttons[channel_idx].setText(self.channel_buttons[channel_idx].default_label)

        # Update trigger mode button
        self.current_trigger_modes[channel_idx] = 'No Trigger'
        self.trigger_mode_buttons[channel_idx].setText(f"Trigger - {self.current_trigger_modes[channel_idx]}")

        # Update worker's uart configurations
        self.worker.uart_configs[channel_idx] = default_config

        # Update curves visibility and colors
        is_checked = self.uart_channel_enabled[channel_idx]
        curve = self.channel_curves[channel_idx]
        curve.setVisible(is_checked)
        curve.setPen(pg.mkPen(color=self.colors[channel_idx % len(self.colors)], width=2))

        # Clear data buffers
        self.clear_data_buffers()

        # Reset button style to default
        self.channel_buttons[channel_idx].setStyleSheet("")

        print(f"Channel {channel_idx+1} has been reset to default settings.")

    def open_configuration_dialog(self, channel_idx):
        """
        Opens the configuration dialog for a specific UART channel, allowing the user to modify settings.

        Args:
            channel_idx (int): The index of the UART channel (0-based).
        """
        current_config = self.uart_configs[channel_idx]
        dialog = UARTConfigDialog(current_config, parent=self)
        if dialog.exec():
            new_config = dialog.get_configuration()
            self.uart_configs[channel_idx].update(new_config)
            print(f"Configuration for channel {channel_idx+1} updated: {new_config}")
            # Update label on the button to reflect new channel assignment
            data_channel = new_config['data_channel']
            label = f"UART {channel_idx+1}\nCh{data_channel}"
            self.channel_buttons[channel_idx].setText(label)
            # Update trigger mode button
            self.trigger_mode_buttons[channel_idx].setText(f"Trigger - {self.current_trigger_modes[channel_idx]}")
            # Update curves visibility
            is_checked = self.uart_channel_enabled[channel_idx]
            curve = self.channel_curves[channel_idx]
            curve.setVisible(is_checked)
            # Clear data buffers
            self.clear_data_buffers()
            # Update worker's uart configurations
            self.worker.uart_configs = self.uart_configs

    def toggle_trigger_mode(self, channel_idx):
        """
        Cycles through the available trigger modes for a specific UART channel and updates the configuration.

        Args:
            channel_idx (int): The index of the UART channel (0-based).
        """
        # Cycle through trigger modes
        current_mode = self.current_trigger_modes[channel_idx]
        current_mode_idx = self.trigger_mode_options.index(current_mode)
        new_mode_idx = (current_mode_idx + 1) % len(self.trigger_mode_options)
        new_mode = self.trigger_mode_options[new_mode_idx]
        self.current_trigger_modes[channel_idx] = new_mode
        self.trigger_mode_buttons[channel_idx].setText(f"Trigger - {new_mode}")
        self.worker.set_trigger_mode(channel_idx, new_mode)
        # Send trigger configuration to MCU
        self.send_trigger_edge_command()
        self.send_trigger_pins_command()

    def send_trigger_edge_command(self):
        """
        Sends the trigger edge configuration command to the MCU based on current trigger modes.
        """
        command_int = get_trigger_edge_command(self.current_trigger_modes)
        command_str = str(command_int)
        try:
            self.worker.serial.write(b'2')
            time.sleep(0.01)
            self.worker.serial.write(b'0')
            time.sleep(0.01)
            self.worker.serial.write(command_str.encode('utf-8'))
            time.sleep(0.01)
        except serial.SerialException as e:
            print(f"Failed to send trigger edge command: {str(e)}")

    def send_trigger_pins_command(self):
        """
        Sends the trigger pins configuration command to the MCU based on current trigger modes.
        """
        command_int = get_trigger_pins_command(self.current_trigger_modes)
        command_str = str(command_int)
        try:
            self.worker.serial.write(b'3')
            time.sleep(0.001)
            self.worker.serial.write(b'0')
            time.sleep(0.001)
            self.worker.serial.write(command_str.encode('utf-8'))
        except serial.SerialException as e:
            print(f"Failed to send trigger pins command: {str(e)}")

    def handle_data_value(self, data_value, sample_idx):
        """
        Handles incoming raw data values emitted by the UARTWorker. Stores data for plotting 
        and triggers UART decoding.

        Args:
            data_value (int): The raw data value received.
            sample_idx (int): The current sample index.
        """
        if self.is_reading:
            # Store raw data for plotting
            for i in range(self.channels):
                bit = (data_value >> i) & 1
                self.data_buffer[i].append(bit)
            self.total_samples += 1  # Increment total samples

            # Check if buffers are full
            if all(len(buf) >= self.bufferSize for buf in self.data_buffer):
                if self.is_single_capture:
                    # In single capture mode, stop acquisition
                    self.stop_single_capture()
                else:
                    # In continuous mode, reset buffers
                    self.clear_data_buffers()
                    # Optionally clear decoded messages

    def display_decoded_message(self, decoded_data):
        """
        Handles decoded UART messages emitted by the UARTWorker. Converts data bytes to the 
        specified format and displays or logs the messages.

        Args:
            decoded_data (dict): Dictionary containing decoded message details such as channel, data, sample index, and format.
        """
        channel = decoded_data['channel']
        if not self.uart_channel_enabled[channel]:
            return  # Do not display if the channel is not enabled
        data_format = decoded_data.get('data_format', 'ASCII')
        data_byte = decoded_data.get('data')
        sample_idx = decoded_data.get('sample_idx')

        # Convert data_byte to desired format
        if data_format == 'Binary':
            data_str = bin(data_byte)
        elif data_format == 'Decimal':
            data_str = str(data_byte)
        elif data_format == 'Hex':
            data_str = hex(data_byte)
        elif data_format == 'ASCII':
            try:
                data_str = chr(data_byte)
            except ValueError:
                data_str = '?'
        else:
            data_str = str(data_byte)

        # Append to decoded messages
        self.decoded_messages_per_channel[channel].append(data_str)

        # Optionally, display on GUI or print to console
        print(f"Channel {channel + 1} Decoded Data: {data_str}")

    def clear_data_buffers(self):
        """
        Clears all data buffers for each UART channel and resets the worker's decoding states.
        """
        self.data_buffer = [deque(maxlen=self.bufferSize) for _ in range(self.channels)]
        self.total_samples = 0  # Reset total samples

        # Reset worker's decoding states
        self.worker.reset_decoding_states()

    def toggle_reading(self):
        """
        Toggles the data reading state between active and inactive. Starts or stops data acquisition 
        and updates the UI accordingly.
        """
        if self.is_reading:
            self.send_stop_message()
            self.stop_reading()
            self.toggle_button.setText("Start")
            self.single_button.setEnabled(True)
            self.toggle_button.setStyleSheet("")
        else:
            self.is_single_capture = False
            self.send_start_message()
            self.start_reading()
            self.toggle_button.setText("Running")
            self.single_button.setEnabled(True)
            self.toggle_button.setStyleSheet("background-color: #00FF77; color: black;")
            # Update sample rates based on baud rate
            self.update_sample_rates()

    def send_start_message(self):
        """
        Sends a 'start' command to the MCU to begin UART data acquisition.
        """
        if self.worker.serial.is_open:
            try:
                self.worker.serial.write(b'0')
                time.sleep(0.001)
                self.worker.serial.write(b'0')
                time.sleep(0.001)
                self.worker.serial.write(b'0')
                print("Sent 'start' command to device")
            except serial.SerialException as e:
                print(f"Failed to send 'start' command: {str(e)}")
        else:
            print("Serial connection is not open")

    def send_stop_message(self):
        """
        Sends a 'stop' command to the MCU to halt UART data acquisition.
        """
        if self.worker.serial.is_open:
            try:
                self.worker.serial.write(b'1')
                time.sleep(0.001)
                self.worker.serial.write(b'1')
                time.sleep(0.001)
                self.worker.serial.write(b'1')
                print("Sent 'stop' command to device")
            except serial.SerialException as e:
                print(f"Failed to send 'stop' command: {str(e)}")
        else:
            print("Serial connection is not open")

    def start_reading(self):
        """
        Starts the data reading process by activating the timer.
        """
        if not self.is_reading:
            # Update sample rates based on baud rate
            self.update_sample_rates()
            self.is_reading = True
            self.timer.start(1)

    def stop_reading(self):
        """
        Stops the data reading process by deactivating the timer.
        """
        if self.is_reading:
            self.is_reading = False
            self.timer.stop()

    def start_single_capture(self):
        """
        Initiates a single data capture by clearing existing data buffers, sending a start message,
        and starting the reading process. Disables relevant UI buttons during capture.
        """
        if not self.is_reading:
            self.clear_data_buffers()
            self.is_single_capture = True
            # Update sample rates based on baud rate
            self.update_sample_rates()
            self.send_start_message()
            self.start_reading()
            self.single_button.setEnabled(False)
            self.toggle_button.setEnabled(False)
            self.single_button.setStyleSheet("background-color: #00FF77; color: black;")

    def stop_single_capture(self):
        """
        Stops a single data capture by stopping the reading process, sending a stop message,
        and re-enabling relevant UI buttons.
        """
        self.is_single_capture = False
        self.stop_reading()
        self.send_stop_message()
        self.single_button.setEnabled(True)
        self.toggle_button.setEnabled(True)
        self.toggle_button.setText("Start")
        self.single_button.setStyleSheet("")

    def update_plot(self):
        """
        Updates the graphical plot with the latest data from each enabled UART channel.
        """
        # Update the plots for each channel
        for ch in range(self.channels):
            if self.uart_channel_enabled[ch]:
                data = list(self.data_buffer[ch])
                num_samples = len(data)
                if num_samples > 1:
                    sample_rate = self.sample_rate  # Use the stored sample rate
                    t = np.arange(num_samples) / sample_rate
                    base_level = ch * 2  # Adjust as needed

                    # Prepare square wave data
                    square_wave_time = []
                    square_wave_data = []
                    for j in range(1, num_samples):
                        square_wave_time.extend([t[j - 1], t[j]])
                        level = data[j - 1] + base_level
                        square_wave_data.extend([level, level])
                        if data[j] != data[j - 1]:
                            square_wave_time.append(t[j])
                            level = data[j] + base_level
                            square_wave_data.append(level)
                    self.channel_curves[ch].setData(square_wave_time, square_wave_data)
                else:
                    self.channel_curves[ch].setData([], [])
            else:
                self.channel_curves[ch].setVisible(False)

    def update_sample_rates(self):
        """
        Calculates and updates the sample rates based on the selected baud rate to ensure at least 
        40 bytes are captured. Adjusts buffer sizes and communicates the sample rate to the MCU.
        """
        # Calculate sample rate based on selected baud rate to see at least 40 bytes
        baud_rate = int(self.baud_rate_combo.currentText())
        desired_bytes = 40  # We want to capture at least 40 bytes
        bits_per_byte = 10  # 8 data bits + 1 start bit + 1 stop bit
        samples_per_bit = 16  # Less chance for an error
        samples_per_byte = bits_per_byte * samples_per_bit  # Total samples per byte

        total_samples_needed = desired_bytes * samples_per_byte

        # Adjust bufferSize accordingly
        self.bufferSize = total_samples_needed
        self.data_buffer = [deque(maxlen=self.bufferSize) for _ in range(self.channels)]

        # Update the plot's X range based on new bufferSize and sample_rate
        # sample_rate = baud_rate * samples_per_bit
        self.sample_rate = baud_rate * samples_per_bit
        total_time = self.bufferSize / self.sample_rate  # Total time span of the buffer

        # self.plot.setXRange(0, total_time, padding=0)
        # self.plot.setLimits(xMin=0, xMax=total_time)
        
        self.plot.setXRange(0, 200 / self.sample_rate, padding=0)
        self.plot.setLimits(xMin=0, xMax=self.bufferSize / self.sample_rate)

        # Update sample_rate and baud_rate in uart_configs
        for ch in range(self.channels):
            if self.uart_channel_enabled[ch]:
                self.uart_configs[ch]['sample_rate'] = self.sample_rate
                self.worker.set_sample_rate(ch, self.sample_rate)
                self.uart_configs[ch]['baud_rate'] = baud_rate
                self.worker.set_baud_rate(ch, baud_rate)

        # Send sampling rate to MCU
        self.send_sample_rate_to_mcu(self.sample_rate)

        # Store sample_rate for use in plotting
        # self.sample_rate = sample_rate

    def send_sample_rate_to_mcu(self, sample_rate):
        """
        Sends the calculated sample rate to the MCU by converting it to a period and transmitting 
        it in four bytes.

        Args:
            sample_rate (int): The sampling rate in Hz to send to the MCU.
        """
        # Convert sample_rate to period for the MCU
        period = int((72e6) / sample_rate)
        if period < 1:
            period = 1  # Ensure period is at least 1 to prevent division by zero
        try:
            self.worker.serial.write(b'5')
            time.sleep(0.001)
            # Send first byte
            selected_bits = (period >> 24) & 0xFF
            self.worker.serial.write(str(selected_bits).encode('utf-8'))
            time.sleep(0.001)
            # Send second byte
            selected_bits = (period >> 16) & 0xFF
            self.worker.serial.write(str(selected_bits).encode('utf-8'))
            time.sleep(0.001)
            self.worker.serial.write(b'6')
            time.sleep(0.001)
            # Send third byte
            selected_bits = (period >> 8) & 0xFF
            self.worker.serial.write(str(selected_bits).encode('utf-8'))
            time.sleep(0.001)
            # Send fourth byte
            selected_bits = period & 0xFF
            self.worker.serial.write(str(selected_bits).encode('utf-8'))
            time.sleep(0.001)
        except Exception as e:
            print(f"Failed to send sample rate to MCU: {e}")

    def closeEvent(self, event):
        """
        Handles the close event of the UARTDisplay widget. Ensures that the worker thread is 
        properly stopped before closing.

        Args:
            event (QEvent): The close event triggered when the widget is being closed.
        """
        self.worker.stop_worker()
        self.worker.quit()
        self.worker.wait()
        event.accept()
