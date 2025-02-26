"""
I2C.py

This module defines classes and functionalities related to handling I2C communication,
data processing, and graphical display for a Logic Analyzer application. It includes:

- SerialWorker: A QThread subclass that manages serial data reading, I2C decoding, and triggering mechanisms.
- FixedYViewBox: A custom PyQtGraph ViewBox that restricts scaling and translation on the Y-axis.
- EditableButton: A QPushButton subclass that allows for context menu operations like renaming.
- I2CChannelButton: An EditableButton subclass specific to I2C channels, with additional signals for configuration.
- I2CConfigDialog: A QDialog subclass that provides a user interface for configuring I2C channel settings.
- I2CDisplay: A QWidget subclass that provides the main interface for displaying and interacting with I2C data,
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
    QRadioButton,
    QButtonGroup,
    QSizePolicy,
    QTextEdit,
    QGroupBox,
)
from PyQt6.QtGui import QIcon, QIntValidator, QTextCursor, QFont
from PyQt6 import QtCore
from collections import deque
from typing import List, Dict, Optional

from InterfaceCommands import (
    get_trigger_edge_command,
    get_trigger_pins_command,
)
from aesthetic import get_icon


class SerialWorker(QtCore.QThread):
    """
    SerialWorker handles I2C serial communication in a separate thread. It reads incoming data from
    the serial port, decodes I2C messages, processes trigger conditions for multiple I2C groups,
    and emits signals when data or decoded messages are ready for processing.

    Attributes:
        data_ready (pyqtSignal): Signal emitted when new raw data is ready. Carries an integer value and sample index.
        decoded_message_ready (pyqtSignal): Signal emitted when a decoded I2C message is ready. Carries a dictionary with message details.
        is_running (bool): Flag indicating whether the worker is active.
        channels (int): Number of channels to monitor for triggers.
        group_configs (List[Dict]): Configuration settings for each I2C group.
        trigger_modes (List[str]): List of trigger modes for each channel.
        states (List[str]): Current state of the state machine for each I2C group.
        bit_buffers (List[List[int]]): Bit buffers for each I2C group.
        current_bytes (List[int]): Current byte being assembled for each I2C group.
        bit_counts (List[int]): Bit count for the current byte in each I2C group.
        decoded_messages (List[List[Dict]]): Decoded messages for each I2C group.
        scl_last_values (List[int]): Last sampled SCL values for edge detection.
        sda_last_values (List[int]): Last sampled SDA values for edge detection.
        messages (List[List[Dict]]): Accumulated messages for each I2C group.
        error_flags (List[bool]): Error flags for each I2C group.
        sample_idx (int): Global sample index counter.
    """

    data_ready = QtCore.pyqtSignal(int, int)  # For raw data values and sample indices
    decoded_message_ready = QtCore.pyqtSignal(dict)  # For decoded messages

    def __init__(self, port: str, baudrate: int, channels: int = 8, group_configs: Optional[List[Dict]] = None) -> None:
        """
        Initializes the SerialWorker thread with the specified serial port parameters and I2C group configurations.

        Args:
            port (str): The serial port to connect to (e.g., 'COM3', '/dev/ttyUSB0').
            baudrate (int): The baud rate for serial communication.
            channels (int, optional): The number of channels to monitor for triggers. Defaults to 8.
            group_configs (List[Dict], optional): Configuration settings for each I2C group. Defaults to None.
        """
        super().__init__()
        self.is_running = True
        self.channels = channels
        self.group_configs = group_configs if group_configs else [{} for _ in range(4)]
        self.trigger_modes = ['No Trigger'] * self.channels
        # Initialize I2C decoding variables for each group
        self.states = ['IDLE'] * len(self.group_configs)
        self.bit_buffers: List[List[int]] = [[] for _ in range(len(self.group_configs))]
        self.current_bytes = [0] * len(self.group_configs)
        self.bit_counts = [0] * len(self.group_configs)
        self.decoded_messages: List[List[Dict]] = [[] for _ in range(len(self.group_configs))]
        self.scl_last_values = [1] * len(self.group_configs)
        self.sda_last_values = [1] * len(self.group_configs)
        self.messages: List[List[Dict]] = [[] for _ in range(len(self.group_configs))]
        self.error_flags = [False] * len(self.group_configs)
        self.sample_idx = 0  # Initialize sample index

        try:
            self.serial = serial.Serial(port, baudrate)
        except serial.SerialException as e:
            print(f"Failed to open serial port: {str(e)}")
            self.is_running = False

        # Initialize sample index variables for each group
        self.addr_sample_idxs: List[Optional[int]] = [None] * len(self.group_configs)
        self.ack_sample_idxs: List[Optional[int]] = [None] * len(self.group_configs)
        self.data_sample_idxs: List[Optional[int]] = [None] * len(self.group_configs)
        self.stop_sample_idxs: List[Optional[int]] = [None] * len(self.group_configs)

    def set_trigger_mode(self, channel_idx: int, mode: str) -> None:
        """
        Sets the trigger mode for a specific channel.

        Args:
            channel_idx (int): The index of the channel (0-based).
            mode (str): The trigger mode to set (e.g., 'No Trigger', 'Rising Edge', 'Falling Edge').
        """
        self.trigger_modes[channel_idx] = mode

    def run(self) -> None:
        """
        The main loop of the worker thread. Continuously reads data from the serial port,
        processes I2C decoding, and emits data_ready and decoded_message_ready signals when appropriate.
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
                        self.decode_i2c(data_value, self.sample_idx)
                        self.sample_idx += 1  # Increment sample index
                    except ValueError:
                        continue

    def decode_i2c(self, data_value: int, sample_idx: int) -> None:
        """
        Decodes incoming serial data to interpret I2C messages based on configured groups.

        Args:
            data_value (int): The raw data value read from the serial port.
            sample_idx (int): The current sample index.
        """
        for group_idx, group_config in enumerate(self.group_configs):
            scl_channel = group_config.get('clock_channel', 2) - 1
            sda_channel = group_config.get('data_channel', 1) - 1
            address_width = group_config.get('address_width', 8)
            data_format = group_config.get('data_format', 'Hexadecimal')

            # Extract SCL and SDA values
            scl = (data_value >> scl_channel) & 1
            sda = (data_value >> sda_channel) & 1

            # Detect edges on SCL and SDA
            scl_last = self.scl_last_values[group_idx]
            sda_last = self.sda_last_values[group_idx]
            scl_edge = scl != scl_last
            sda_edge = sda != sda_last

            # State machine for I2C decoding
            state = self.states[group_idx]
            current_byte = self.current_bytes[group_idx]
            bit_count = self.bit_counts[group_idx]
            message = self.messages[group_idx]
            error_flag = self.error_flags[group_idx]

            # Retrieve stored sample indices
            addr_sample_idx = self.addr_sample_idxs[group_idx]
            ack_sample_idx = self.ack_sample_idxs[group_idx]
            data_sample_idx = self.data_sample_idxs[group_idx]
            stop_sample_idx = self.stop_sample_idxs[group_idx]

            # Determine the expected number of bits for the address
            if address_width == 7:
                expected_bits = address_width + 1  # Include R/W bit
            else:
                expected_bits = address_width  # 8 bits, no extra bit

            if state == 'IDLE':
                if sda_edge and sda == 0 and scl == 1:
                    # Start condition detected
                    state = 'START'
                    current_byte = 0
                    bit_count = 0
                    message = []
                    error_flag = False
                    # Record the sample index for START
                    start_sample_idx = sample_idx
                    # Emit start condition immediately
                    self.decoded_message_ready.emit({
                        'group_idx': group_idx,
                        'event': 'START',
                        'sample_idx': start_sample_idx,
                    })
            elif state == 'START':
                if scl_edge and scl == 1:
                    if bit_count == 0:
                        # Record sample index at the start of address transmission
                        addr_sample_idx = sample_idx
                        self.addr_sample_idxs[group_idx] = addr_sample_idx
                    # Rising edge of SCL, sample SDA
                    current_byte = (current_byte << 1) | sda
                    bit_count += 1
                    if bit_count == expected_bits:
                        # Address byte received
                        if address_width == 7:
                            address = current_byte >> 1
                            rw_bit = current_byte & 1
                            message.append({'type': 'Address', 'data': address, 'rw': rw_bit})
                        else:
                            address = current_byte
                            rw_bit = None
                            message.append({'type': 'Address', 'data': address})
                        # Emit signal for address
                        self.decoded_message_ready.emit({
                            'group_idx': group_idx,
                            'event': 'ADDRESS',
                            'data': address,
                            'rw_bit': rw_bit,
                            'sample_idx': addr_sample_idx,  # Use recorded sample index
                        })
                        bit_count = 0
                        current_byte = 0
                        state = 'ACK'
                        # Reset address sample index
                        self.addr_sample_idxs[group_idx] = None
            elif state == 'ACK':
                if scl_edge and scl == 1:
                    # Record sample index at the start of ACK bit
                    ack_sample_idx = sample_idx
                    self.ack_sample_idxs[group_idx] = ack_sample_idx
                    # Sample ACK bit
                    ack = sda
                    message.append({'type': 'ACK', 'data': ack})
                    # Emit signal for ACK
                    self.decoded_message_ready.emit({
                        'group_idx': group_idx,
                        'event': 'ACK',
                        'data': ack,
                        'sample_idx': ack_sample_idx,
                    })
                    state = 'DATA'
                    # Reset ACK sample index
                    self.ack_sample_idxs[group_idx] = None
            elif state == 'DATA':
                if scl_edge and scl == 1:
                    if bit_count == 0:
                        # Record sample index at the start of data byte
                        data_sample_idx = sample_idx
                        self.data_sample_idxs[group_idx] = data_sample_idx
                    # Rising edge of SCL, sample SDA
                    current_byte = (current_byte << 1) | sda
                    bit_count += 1
                    if bit_count == 8:
                        # Data byte received
                        message.append({'type': 'Data', 'data': current_byte})
                        # Emit signal for DATA
                        self.decoded_message_ready.emit({
                            'group_idx': group_idx,
                            'event': 'DATA',
                            'data': current_byte,
                            'sample_idx': data_sample_idx,  # Use recorded sample index
                        })
                        bit_count = 0
                        current_byte = 0
                        state = 'ACK2'
                        # Reset data sample index
                        self.data_sample_idxs[group_idx] = None
            elif state == 'ACK2':
                if scl_edge and scl == 1:
                    # Record sample index at the start of ACK bit
                    ack_sample_idx = sample_idx
                    self.ack_sample_idxs[group_idx] = ack_sample_idx
                    # Sample ACK bit
                    ack = sda
                    message.append({'type': 'ACK', 'data': ack})
                    # Emit signal for ACK
                    self.decoded_message_ready.emit({
                        'group_idx': group_idx,
                        'event': 'ACK',
                        'data': ack,
                        'sample_idx': ack_sample_idx,
                    })
                    state = 'DATA'
                    # Reset ACK sample index
                    self.ack_sample_idxs[group_idx] = None
            if sda_edge and sda == 1 and scl == 1:
                # Stop condition detected
                stop_sample_idx = sample_idx  # Record sample index for STOP
                # Emit the decoded message
                self.decoded_message_ready.emit({
                    'group_idx': group_idx,
                    'event': 'STOP',
                    'message': message.copy(),
                    'sample_idx': stop_sample_idx,
                })
                # Reset state
                state = 'IDLE'
                current_byte = 0
                bit_count = 0
                message = []
                error_flag = False
                # Reset sample indices
                self.addr_sample_idxs[group_idx] = None
                self.ack_sample_idxs[group_idx] = None
                self.data_sample_idxs[group_idx] = None
                self.stop_sample_idxs[group_idx] = None

            # Update the stored states
            self.states[group_idx] = state
            self.current_bytes[group_idx] = current_byte
            self.bit_counts[group_idx] = bit_count
            self.messages[group_idx] = message
            self.error_flags[group_idx] = error_flag

            # Update last values
            self.scl_last_values[group_idx] = scl
            self.sda_last_values[group_idx] = sda

    def reset_decoding_states(self) -> None:
        """
        Resets the I2C decoding state machines for all groups, clearing buffers and states.
        """
        # Reset I2C decoding variables for each group
        self.states = ['IDLE'] * len(self.group_configs)
        self.bit_buffers = [[] for _ in range(len(self.group_configs))]
        self.current_bytes = [0] * len(self.group_configs)
        self.bit_counts = [0] * len(self.group_configs)
        self.decoded_messages = [[] for _ in range(len(self.group_configs))]
        self.scl_last_values = [1] * len(self.group_configs)
        self.sda_last_values = [1] * len(self.group_configs)
        self.messages = [[] for _ in range(len(self.group_configs))]
        self.error_flags = [False] * len(self.group_configs)
        self.sample_idx = 0  # Reset sample index


    def stop_worker(self) -> None:
        """
        Stops the worker thread by setting the running flag to False and closing the serial port.
        """
        self.is_running = False
        if self.serial.is_open:
            self.serial.close()


class FixedYViewBox(pg.ViewBox):
    """
    FixedYViewBox is a custom PyQtGraph ViewBox that restricts scaling and translation
    along the Y-axis, allowing only horizontal scaling and movement.
    """

    def __init__(self, *args, **kwargs) -> None:
        """
        Initializes the FixedYViewBox with the provided arguments.
        """
        super().__init__(*args, **kwargs)

    def scaleBy(self, s=None, center=None, x: Optional[float] = None, y: Optional[float] = None) -> None:
        """
        Overrides the scaleBy method to fix the Y-axis scaling to 1.0, preventing vertical scaling.

        Args:
            s: Scaling factor (unused for Y-axis).
            center: Center point for scaling.
            x (float, optional): Scaling factor for X-axis.
            y (float, optional): Scaling factor for Y-axis (fixed to 1.0).
        """
        y = 1.0
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

    def translateBy(self, t=None, x: Optional[float] = None, y: Optional[float] = None) -> None:
        """
        Overrides the translateBy method to fix the Y-axis translation to 0.0, preventing vertical movement.

        Args:
            t: Translation value (unused for Y-axis).
            x (float, optional): Translation value for X-axis.
            y (float, optional): Translation value for Y-axis (fixed to 0.0).
        """
        y = 0.0
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


class EditableButton(QPushButton):
    """
    EditableButton is a QPushButton subclass that allows users to rename the button label
    or reset it to its default label via a context menu.
    """

    def __init__(self, label: str, parent: Optional[QWidget] = None) -> None:
        """
        Initializes the EditableButton with a given label.

        Args:
            label (str): The initial text label of the button.
            parent (QWidget, optional): The parent widget. Defaults to None.
        """
        super().__init__(label, parent)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)
        self.default_label = label

    def show_context_menu(self, position: QtCore.QPoint) -> None:
        """
        Displays a context menu with options to rename the button or reset it to the default label.

        Args:
            position (QPoint): The position where the context menu is requested.
        """
        menu = QMenu()
        rename_action = menu.addAction("Rename")
        reset_action = menu.addAction("Reset to Default")
        action = menu.exec(self.mapToGlobal(position))
        if action == rename_action:
            new_label, ok = QInputDialog.getText(
                self, "Rename Button", "Enter new label:", text=self.text()
            )
            if ok and new_label:
                self.setText(new_label)
        elif action == reset_action:
            self.setText(self.default_label)


class I2CChannelButton(EditableButton):
    """
    I2CChannelButton is an EditableButton subclass specific to I2C channels. It emits additional
    signals for configuration and reset actions.

    Attributes:
        configure_requested (pyqtSignal): Signal emitted when the configure option is selected.
        reset_requested (pyqtSignal): Signal emitted when the reset to default option is selected.
    """

    configure_requested = QtCore.pyqtSignal(int)  # Signal to notify when configure is requested
    reset_requested = QtCore.pyqtSignal(int)      # Signal to notify when reset is requested

    def __init__(self, label: str, group_idx: int, parent: Optional[QWidget] = None) -> None:
        """
        Initializes the I2CChannelButton with a given label and group index.

        Args:
            label (str): The initial text label of the button.
            group_idx (int): The index of the I2C group this button represents.
            parent (QWidget, optional): The parent widget. Defaults to None.
        """
        super().__init__(label, parent)
        self.group_idx = group_idx  # Store the index of the I2C group

    def show_context_menu(self, position: QtCore.QPoint) -> None:
        """
        Displays a context menu with options to rename the button, reset to default, or configure the group.

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
            self.reset_requested.emit(self.group_idx)  # Emit reset signal
        elif action == configure_action:
            self.configure_requested.emit(self.group_idx)  # Emit signal to open configuration dialog


class I2CConfigDialog(QDialog):
    """
    I2CConfigDialog provides a user interface for configuring I2C group settings, including
    clock channel, data channel, address width, and data format.
    """

    def __init__(self, current_config: Dict, parent: Optional[QWidget] = None) -> None:
        """
        Initializes the I2CConfigDialog with the current configuration.

        Args:
            current_config (Dict): The current configuration settings for the I2C group.
            parent (QWidget, optional): The parent widget. Defaults to None.
        """
        super().__init__(parent)
        self.setWindowTitle("I2C Configuration")
        self.current_config = current_config  # Dictionary to hold current configurations

        self.init_ui()

    def init_ui(self) -> None:
        """
        Sets up the user interface components of the configuration dialog.
        """
        layout = QVBoxLayout()

        # Clock Channel Selection
        clock_layout = QHBoxLayout()
        clock_label = QLabel("Clock Channel:")
        self.clock_combo = QComboBox()
        self.clock_combo.addItems([f"Channel {i+1}" for i in range(8)])
        self.clock_combo.setCurrentIndex(self.current_config.get('clock_channel', 2) - 1)
        clock_layout.addWidget(clock_label)
        clock_layout.addWidget(self.clock_combo)
        layout.addLayout(clock_layout)

        # Data Channel Selection
        data_layout = QHBoxLayout()
        data_label = QLabel("Data Channel:")
        self.data_combo = QComboBox()
        self.data_combo.addItems([f"Channel {i+1}" for i in range(8)])
        self.data_combo.setCurrentIndex(self.current_config.get('data_channel', 1) - 1)
        data_layout.addWidget(data_label)
        data_layout.addWidget(self.data_combo)
        layout.addLayout(data_layout)

        # Address Width Selection
        address_layout = QHBoxLayout()
        address_label = QLabel("Address Width:")
        self.address_group = QButtonGroup(self)
        self.address_7bit = QRadioButton("7 bits")
        self.address_8bit = QRadioButton("8 bits")
        self.address_group.addButton(self.address_7bit)
        self.address_group.addButton(self.address_8bit)
        address_layout.addWidget(address_label)
        address_layout.addWidget(self.address_7bit)
        address_layout.addWidget(self.address_8bit)
        layout.addLayout(address_layout)

        if self.current_config.get('address_width', 8) == 8:
            self.address_8bit.setChecked(True)
        else:
            self.address_7bit.setChecked(True)

        # Data Format Selection
        format_layout = QHBoxLayout()
        format_label = QLabel("Data Format:")
        self.format_combo = QComboBox()
        self.format_combo.addItems(["Binary", "Decimal", "Hexadecimal", "BCD", "ASCII"])
        self.format_combo.setCurrentText(self.current_config.get('data_format', 'Hexadecimal'))
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

    def get_configuration(self) -> Dict:
        """
        Retrieves the updated configuration settings from the dialog.

        Returns:
            Dict: A dictionary containing the updated I2C group configuration.
        """
        return {
            'clock_channel': self.clock_combo.currentIndex() + 1,
            'data_channel': self.data_combo.currentIndex() + 1,
            'address_width': 7 if self.address_7bit.isChecked() else 8,
            'data_format': self.format_combo.currentText(),
        }


class I2CDisplay(QWidget):
    """
    I2CDisplay provides the main interface for displaying and interacting with I2C data.
    It includes graphical plots, control buttons, and configurations for multiple I2C groups.

    Attributes:
        period (int): The period for sample timing.
        num_samples (int): Number of samples to capture.
        port (str): Serial port for communication.
        baudrate (int): Baud rate for serial communication.
        channels (int): Number of channels for the logic analyzer.
        bufferSize (int): Size of the data buffer.
        data_buffer (List[deque]): Data buffers for each channel.
        sample_indices (deque): Sample indices buffer.
        total_samples (int): Total number of samples captured.
        is_single_capture (bool): Flag indicating if a single capture is active.
        current_trigger_modes (List[str]): Current trigger modes for each channel.
        trigger_mode_options (List[str]): Available trigger mode options.
        sample_rate (int): Sampling rate in Hz.
        group_configs (List[Dict]): Configuration settings for each I2C group.
        default_group_configs (List[Dict]): Default configuration settings for each I2C group.
        i2c_group_enabled (List[bool]): Flags indicating whether each I2C group is enabled.
        decoded_messages_per_group (Dict[int, List[str]]): Decoded messages for each I2C group.
        group_cursors (List[List[Dict]]): Cursors for each I2C group.
        setup_ui (method): Method to set up the user interface.
        timer (QTimer): Timer for updating the plot.
        is_reading (bool): Flag indicating if data reading is active.
        decoded_texts (List[QTextEdit]): Text edits for displaying decoded messages.
        worker (SerialWorker): Worker thread handling serial communication.
        group_curves (List[Dict[str, pg.PlotDataItem]]): Plot curves for SDA and SCL of each group.
        colors (List[str]): List of colors for plotting each group.
        channel_buttons (List[I2CChannelButton]): Buttons to toggle I2C group visibility and configuration.
        sda_trigger_mode_buttons (List[QPushButton]): Buttons to toggle trigger modes for SDA of each group.
        scl_trigger_mode_buttons (List[QPushButton]): Buttons to toggle trigger modes for SCL of each group.
        sample_rate_input (QLineEdit): Input field for sample rate.
        num_samples_input (QLineEdit): Input field for number of samples.
        toggle_button (QPushButton): Button to start/stop data acquisition.
        single_button (QPushButton): Button to initiate a single data capture.
    """

    def __init__(self, port: str, baudrate: int, bufferSize: int, channels: int = 8) -> None:
        """
        Initializes the I2CDisplay with the specified serial port parameters and sets up the UI.

        Args:
            port (str): Serial port for communication.
            baudrate (int): Baud rate for serial communication.
            bufferSize (int): Size of the data buffer.
            channels (int, optional): Number of channels for the logic analyzer. Defaults to 8.
        """
        super().__init__()
        self.period = 65454
        self.num_samples = 0
        self.port = port
        self.baudrate = baudrate
        self.channels = channels
        self.bufferSize = bufferSize

        self.data_buffer: List[deque] = [deque(maxlen=self.bufferSize) for _ in range(self.channels)]  # 8 channels
        self.sample_indices: deque = deque(maxlen=self.bufferSize)
        self.total_samples: int = 0

        self.is_single_capture: bool = False

        self.current_trigger_modes: List[str] = ['No Trigger'] * self.channels
        self.trigger_mode_options: List[str] = ['No Trigger', 'Rising Edge', 'Falling Edge']

        self.sample_rate: int = 1000  # Default sample rate in Hz

        # Initialize group configurations with default channels and address width
        self.group_configs: List[Dict] = [
            {'data_channel': 1, 'clock_channel': 2, 'address_width': 8, 'data_format': 'Hexadecimal'},
            {'data_channel': 3, 'clock_channel': 4, 'address_width': 8, 'data_format': 'Hexadecimal'},
            {'data_channel': 5, 'clock_channel': 6, 'address_width': 8, 'data_format': 'Hexadecimal'},
            {'data_channel': 7, 'clock_channel': 8, 'address_width': 8, 'data_format': 'Hexadecimal'},
        ]

        # Default group configurations for resetting
        self.default_group_configs: List[Dict] = [
            {'data_channel': 1, 'clock_channel': 2, 'address_width': 8, 'data_format': 'Hexadecimal'},
            {'data_channel': 3, 'clock_channel': 4, 'address_width': 8, 'data_format': 'Hexadecimal'},
            {'data_channel': 5, 'clock_channel': 6, 'address_width': 8, 'data_format': 'Hexadecimal'},
            {'data_channel': 7, 'clock_channel': 8, 'address_width': 8, 'data_format': 'Hexadecimal'},
        ]

        self.i2c_group_enabled: List[bool] = [False] * 4  # Track which I2C groups are enabled

        # Initialize decoded messages per group
        self.decoded_messages_per_group: Dict[int, List[str]] = {i: [] for i in range(4)}

        self.group_cursors: List[List[Dict]] = [[] for _ in range(4)]  # To store cursors per group

        self.setup_ui()
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_plot)

        self.is_reading: bool = False
        self.decoded_texts: List[QTextEdit] = []

        self.worker = SerialWorker(
            port=self.port,
            baudrate=self.baudrate,
            channels=self.channels,
            group_configs=self.group_configs
        )
        self.worker.data_ready.connect(self.handle_data_value)
        self.worker.decoded_message_ready.connect(self.display_decoded_message)
        self.worker.start()

    def setup_ui(self) -> None:
        """
        Sets up the user interface components, including the graph, control buttons, and input fields.
        """
        main_layout = QVBoxLayout(self)

        plot_layout = QHBoxLayout()
        main_layout.addLayout(plot_layout)

        self.graph_layout = pg.GraphicsLayoutWidget()
        plot_layout.addWidget(self.graph_layout, stretch=3)  # Allocate more space to the graph

        self.plot = self.graph_layout.addPlot(viewBox=FixedYViewBox())

        self.plot.setXRange(0, self.bufferSize / self.sample_rate, padding=0)
        self.plot.setLimits(xMin=0, xMax=self.bufferSize / self.sample_rate)
        self.plot.enableAutoRange(axis=pg.ViewBox.XAxis, enable=False)
        self.plot.setYRange(-2, 2 * self.channels, padding=0)  # 8 channels
        self.plot.enableAutoRange(axis=pg.ViewBox.XAxis, enable=False)
        self.plot.enableAutoRange(axis=pg.ViewBox.YAxis, enable=False)
        self.plot.showGrid(x=True, y=True)
        self.plot.getAxis('left').setTicks([])
        self.plot.getAxis('left').setStyle(showValues=False)
        self.plot.getAxis('left').setPen(None)
        self.plot.setLabel('bottom', 'Time', units='s')

        self.colors: List[str] = ['#FF6EC7', '#39FF14', '#FF486D', '#BF00FF', '#FFFF33', '#FFA500', '#00F5FF', '#BFFF00']
        self.group_curves: List[Dict[str, pg.PlotDataItem]] = []
        for group_idx in range(4):  # Assuming 4 groups
            # Create curves for SDA and SCL for each group
            sda_curve = self.plot.plot(pen=pg.mkPen(color=self.colors[group_idx % len(self.colors)], width=4))
            scl_curve = self.plot.plot(pen=pg.mkPen(color='#DEDEDE', width=4))
            sda_curve.setVisible(False)
            scl_curve.setVisible(False)
            self.group_curves.append({'sda_curve': sda_curve, 'scl_curve': scl_curve})

        button_layout = QGridLayout()
        plot_layout.addLayout(button_layout, stretch=1)  # Allocate less space to the control panel

        button_widget = QWidget()
        button_layout = QGridLayout(button_widget)
        plot_layout.addWidget(button_widget)

        self.channel_buttons: List[I2CChannelButton] = []
        self.sda_trigger_mode_buttons: List[QPushButton] = []
        self.scl_trigger_mode_buttons: List[QPushButton] = []

        for i in range(4):
            row = i * 2  # Increment by 2 for each group
            group_config = self.group_configs[i]
            sda_channel = group_config['data_channel']
            scl_channel = group_config['clock_channel']
            label = f"I2C {i+1}\nCh{sda_channel}:SDA\nCh{scl_channel}:SCL"
            button = I2CChannelButton(label, group_idx=i)

            # Set size policy and fixed width
            button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
            button.setFixedWidth(100)  # Set the fixed width for the button

            button.setCheckable(True)
            button.setChecked(False)
            button.toggled.connect(lambda checked, idx=i: self.toggle_channel_group(idx, checked))
            button.configure_requested.connect(self.open_configuration_dialog)
            button_layout.addWidget(button, row, 0, 2, 1)  # Span 2 rows, 1 column

            # SDA Trigger Mode Button
            sda_trigger_button = QPushButton(f"SDA - {self.current_trigger_modes[sda_channel - 1]}")
            sda_trigger_button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
            sda_trigger_button.setFixedWidth(120)
            sda_trigger_button.clicked.connect(lambda _, idx=i: self.toggle_trigger_mode(idx, 'SDA'))
            button_layout.addWidget(sda_trigger_button, row, 1)

            # SCL Trigger Mode Button
            scl_trigger_button = QPushButton(f"SCL - {self.current_trigger_modes[scl_channel - 1]}")
            scl_trigger_button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
            scl_trigger_button.setFixedWidth(120)
            scl_trigger_button.clicked.connect(lambda _, idx=i: self.toggle_trigger_mode(idx, 'SCL'))
            button_layout.addWidget(scl_trigger_button, row + 1, 1)

            # Set row stretches to distribute space equally
            button_layout.setRowStretch(row, 1)
            button_layout.setRowStretch(row + 1, 1)

            self.channel_buttons.append(button)
            self.sda_trigger_mode_buttons.append(sda_trigger_button)
            self.scl_trigger_mode_buttons.append(scl_trigger_button)

            button.reset_requested.connect(self.reset_group_to_default)

        # Calculate the starting row for the next set of widgets
        next_row = 4 * 2  # 4 groups * 2 rows per group

        # Sample Rate input
        self.sample_rate_label = QLabel("Sample Rate (Hz):")
        button_layout.addWidget(self.sample_rate_label, next_row, 0)

        self.sample_rate_input = QLineEdit()
        self.sample_rate_input.setValidator(QIntValidator(1, 5000000))
        self.sample_rate_input.setText("1000")
        self.sample_rate_input.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
        self.sample_rate_input.setFixedWidth(100)
        button_layout.addWidget(self.sample_rate_input, next_row, 1)
        self.sample_rate_input.returnPressed.connect(self.handle_sample_rate_input)

        # Number of Samples input
        self.num_samples_label = QLabel("Number of Samples:")
        button_layout.addWidget(self.num_samples_label, next_row + 1, 0)

        self.num_samples_input = QLineEdit()
        self.num_samples_input.setValidator(QIntValidator(1, 1023))
        self.num_samples_input.setText("300")
        self.num_samples_input.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
        self.num_samples_input.setFixedWidth(100)
        button_layout.addWidget(self.num_samples_input, next_row + 1, 1)
        self.num_samples_input.returnPressed.connect(self.send_num_samples_command)

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

        # Add control buttons layout to the button_layout
        button_layout.addLayout(control_buttons_layout, next_row + 2, 0, 1, 2)

        # Adjust the stretch factors of the plot_layout
        plot_layout.setStretchFactor(self.graph_layout, 1)  # The plot area should expand
        plot_layout.setStretchFactor(button_widget, 0)      # The button area remains fixed

    def reset_group_to_default(self, group_idx: int) -> None:
        """
        Resets the configuration of a specific I2C group to its default settings.

        Args:
            group_idx (int): The index of the I2C group to reset.
        """
        # Reset the group configuration to default settings
        default_config = self.default_group_configs[group_idx].copy()
        self.group_configs[group_idx] = default_config
        print(f"Group {group_idx + 1} reset to default configuration: {default_config}")

        # Reset the button's label to default
        self.channel_buttons[group_idx].setText(self.channel_buttons[group_idx].default_label)

        # Update trigger mode buttons
        sda_channel = default_config['data_channel']
        scl_channel = default_config['clock_channel']
        sda_idx = sda_channel - 1
        scl_idx = scl_channel - 1

        self.current_trigger_modes[sda_idx] = 'No Trigger'
        self.current_trigger_modes[scl_idx] = 'No Trigger'
        self.sda_trigger_mode_buttons[group_idx].setText(f"SDA - {self.current_trigger_modes[sda_idx]}")
        self.scl_trigger_mode_buttons[group_idx].setText(f"SCL - {self.current_trigger_modes[scl_idx]}")

        # Update worker's group configurations
        self.worker.group_configs[group_idx] = default_config

        # Update curves visibility and colors
        is_checked = self.i2c_group_enabled[group_idx]
        sda_curve = self.group_curves[group_idx]['sda_curve']
        scl_curve = self.group_curves[group_idx]['scl_curve']
        sda_curve.setVisible(is_checked)
        scl_curve.setVisible(is_checked)
        sda_curve.setPen(pg.mkPen(color=self.colors[group_idx % len(self.colors)], width=4))
        scl_curve.setPen(pg.mkPen(color='#DEDEDE', width=4))

        # Clear data buffers
        self.clear_data_buffers()

        # Reset button style to default
        self.channel_buttons[group_idx].setStyleSheet("")

        print(f"Group {group_idx + 1} has been reset to default settings.")

    def handle_sample_rate_input(self) -> None:
        """
        Handles the event when the sample rate input field receives a return key press.
        Validates and updates the sample rate, adjusts the plot range and timers accordingly.
        """
        try:
            sample_rate = int(self.sample_rate_input.text())
            if sample_rate <= 0:
                raise ValueError("Sample rate must be positive")
            self.sample_rate = sample_rate  # Store sample_rate
            period = (72 * 10**6) / sample_rate
            print(f"Sample Rate set to {sample_rate} Hz, Period: {period} ticks")
            self.updateSampleTimer(int(period))
            self.plot.setXRange(0, 200 / self.sample_rate, padding=0)
            self.plot.setLimits(xMin=0, xMax=self.bufferSize / self.sample_rate)
        except ValueError as e:
            print(f"Invalid sample rate: {e}")

    def send_num_samples_command(self) -> None:
        """
        Sends the number of samples command to the serial device based on user input.
        """
        try:
            num_samples = int(self.num_samples_input.text())
            self.num_samples = num_samples
            self.updateTriggerTimer()
        except ValueError as e:
            print(f"Invalid number of samples: {e}")

    def send_trigger_edge_command(self) -> None:
        """
        Sends the trigger edge configuration to the serial device.
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

    def send_trigger_pins_command(self) -> None:
        """
        Sends the trigger pins configuration to the serial device.
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

    def updateSampleTimer(self, period: int) -> None:
        """
        Updates the sample timer configuration on the serial device.

        Args:
            period (int): The period value to set for the sample timer.
        """
        self.period = period
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
            print(f"Failed to update sample timer: {e}")

    def updateTriggerTimer(self) -> None:
        """
        Updates the trigger timer configuration on the serial device based on the number of samples.
        """
        sampling_freq = 72e6 / self.period
        trigger_freq = sampling_freq / self.num_samples
        period16 = 72e6 / trigger_freq
        prescaler = 1
        if period16 > 2**16:
            prescaler = math.ceil(period16 / (2**16))
            period16 = int((72e6 / prescaler) / trigger_freq)
        print(f"Period timer 16 set to {period16}, Timer 16 prescaler is {prescaler}")
        try:
            self.worker.serial.write(b'4')
            time.sleep(0.01)
            # Send high byte
            selected_bits = (int(period16) >> 8) & 0xFF
            self.worker.serial.write(str(selected_bits).encode('utf-8'))
            time.sleep(0.01)
            # Send low byte
            selected_bits = int(period16) & 0xFF
            self.worker.serial.write(str(selected_bits).encode('utf-8'))
            time.sleep(0.01)
            # Update Prescaler
            self.worker.serial.write(b'7')
            time.sleep(0.01)
            # Send high byte
            selected_bits = (prescaler >> 8) & 0xFF
            self.worker.serial.write(str(selected_bits).encode('utf-8'))
            time.sleep(0.01)
            # Send low byte
            selected_bits = prescaler & 0xFF
            self.worker.serial.write(str(selected_bits).encode('utf-8'))
            time.sleep(0.01)
        except Exception as e:
            print(f"Failed to update trigger timer: {e}")

    def toggle_trigger_mode(self, group_idx: int, line: str) -> None:
        """
        Toggles the trigger mode for a specific I2C group and line (SDA/SCL) cyclically through predefined options.

        Args:
            group_idx (int): The index of the I2C group (0-based).
            line (str): The line to toggle trigger mode for ('SDA' or 'SCL').
        """
        group_config = self.group_configs[group_idx]
        if line == 'SDA':
            channel_idx = group_config['data_channel'] - 1  # Adjust index
            button = self.sda_trigger_mode_buttons[group_idx]
        elif line == 'SCL':
            channel_idx = group_config['clock_channel'] - 1  # Adjust index
            button = self.scl_trigger_mode_buttons[group_idx]
        else:
            return

        # Cycle through trigger modes
        current_mode = self.current_trigger_modes[channel_idx]
        current_mode_idx = self.trigger_mode_options.index(current_mode)
        new_mode_idx = (current_mode_idx + 1) % len(self.trigger_mode_options)
        new_mode = self.trigger_mode_options[new_mode_idx]
        self.current_trigger_modes[channel_idx] = new_mode
        button.setText(f"{line} - {new_mode}")
        self.worker.set_trigger_mode(channel_idx, new_mode)
        self.send_trigger_edge_command()
        self.send_trigger_pins_command()

    def is_light_color(self, hex_color: str) -> bool:
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

    def toggle_channel_group(self, group_idx: int, is_checked: bool) -> None:
        """
        Toggles the visibility and activation of a specific I2C group.

        Args:
            group_idx (int): The index of the I2C group (0-based).
            is_checked (bool): Whether the group should be enabled.
        """
        self.i2c_group_enabled[group_idx] = is_checked  # Update the enabled list

        # Update curves visibility
        sda_curve = self.group_curves[group_idx]['sda_curve']
        scl_curve = self.group_curves[group_idx]['scl_curve']
        sda_curve.setVisible(is_checked)
        scl_curve.setVisible(is_checked)

        button = self.channel_buttons[group_idx]
        if is_checked:
            color = self.colors[group_idx % len(self.colors)]
            text_color = 'black' if self.is_light_color(color) else 'white'
            button.setStyleSheet(f"QPushButton {{ background-color: {color}; color: {text_color}; "
                                 f"border: 1px solid #555; border-radius: 5px; padding: 5px; "
                                 f"text-align: left; }}")
        else:
            button.setStyleSheet("")

    def toggle_reading(self) -> None:
        """
        Toggles the data reading state between active and inactive. Starts or stops data acquisition
        and updates the UI accordingly.
        """
        if self.is_reading:
            self.send_stop_message()
            self.stop_reading()
            self.toggle_button.setText("Run")
            self.single_button.setEnabled(True)
            self.toggle_button.setStyleSheet("")
        else:
            self.is_single_capture = False
            self.send_start_message()
            self.start_reading()
            self.toggle_button.setText("Running")
            self.single_button.setEnabled(True)
            self.toggle_button.setStyleSheet("background-color: #00FF77; color: black;")

    def send_start_message(self) -> None:
        """
        Sends a 'start' command to the serial device to begin data acquisition.
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

    def send_stop_message(self) -> None:
        """
        Sends a 'stop' command to the serial device to halt data acquisition.
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

    def start_reading(self) -> None:
        """
        Starts the data reading process by activating the timer.
        """
        if not self.is_reading:
            self.is_reading = True
            self.timer.start(1)

    def stop_reading(self) -> None:
        """
        Stops the data reading process by deactivating the timer.
        """
        if self.is_reading:
            self.is_reading = False
            self.timer.stop()

    def start_single_capture(self) -> None:
        """
        Initiates a single data capture by clearing existing data buffers, sending a start message,
        and starting the reading process. Disables relevant UI buttons during capture.
        """
        if not self.is_reading:
            self.clear_data_buffers()
            self.is_single_capture = True
            self.send_start_message()
            self.start_reading()
            self.single_button.setEnabled(False)
            self.toggle_button.setEnabled(False)
            self.single_button.setStyleSheet("background-color: #00FF77; color: black;")

    def stop_single_capture(self) -> None:
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

    def clear_data_buffers(self) -> None:
        """
        Clears all data buffers for each channel and removes all cursors from the plot.
        Also resets the worker's decoding states.
        """
        self.data_buffer = [deque(maxlen=self.bufferSize) for _ in range(self.channels)]
        self.total_samples = 0  # Reset total samples

        # Remove all cursors
        for group_idx in range(4):
            for cursor_info in self.group_cursors[group_idx]:
                self.plot.removeItem(cursor_info['line'])
                self.plot.removeItem(cursor_info['label'])
            self.group_cursors[group_idx] = []

        # Reset worker's decoding states
        self.worker.reset_decoding_states()

    def handle_data_value(self, data_value: int, sample_idx: int) -> None:
        """
        Handles incoming raw data emitted by the SerialWorker. Appends data to buffers and manages
        single capture logic.

        Args:
            data_value (int): The raw data value.
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
                    # In continuous mode, reset buffers and cursors
                    self.clear_data_buffers()
                    self.clear_decoded_text()

    def display_decoded_message(self, decoded_data: Dict) -> None:
        """
        Displays a decoded I2C message by creating cursors and appending messages to the display.

        Args:
            decoded_data (Dict): A dictionary containing decoded message details.
        """
        group_idx: int = decoded_data.get('group_idx', -1)
        if group_idx == -1 or not self.i2c_group_enabled[group_idx]:
            return  # Do not display if the group is not enabled or invalid

        data_format: str = self.group_configs[group_idx].get('data_format', 'Hexadecimal')
        event: Optional[str] = decoded_data.get('event', None)
        sample_idx: Optional[int] = decoded_data.get('sample_idx', None)

        if event == 'START' and sample_idx is not None:
            # Create cursor for START condition
            self.create_cursor(group_idx, sample_idx, 'Start')
        elif event == 'ADDRESS':
            # Create cursor for Address
            address: int = decoded_data['data']
            rw_bit: Optional[int] = decoded_data.get('rw_bit', None)
            if data_format == 'Binary':
                addr_str = bin(address)
            elif data_format == 'Decimal':
                addr_str = str(address)
            elif data_format == 'Hexadecimal':
                addr_str = hex(address)
            elif data_format == 'ASCII':
                addr_str = chr(address)
            else:
                addr_str = hex(address)
            if rw_bit is not None:
                rw_str = 'Read' if rw_bit else 'Write'
                label_text = f"A:{addr_str} ({rw_str})"
            else:
                label_text = f"A:{addr_str}"
            self.create_cursor(group_idx, sample_idx, label_text)
        elif event == 'ACK':
            # Create cursor for ACK/NACK
            ack: int = decoded_data['data']
            ack_str: str = 'ACK' if ack == 0 else 'NACK'
            self.create_cursor(group_idx, sample_idx, ack_str)
        elif event == 'DATA':
            # Create cursor for Data byte
            data_byte: int = decoded_data['data']
            if data_format == 'Binary':
                data_str = bin(data_byte)
            elif data_format == 'Decimal':
                data_str = str(data_byte)
            elif data_format == 'Hexadecimal':
                data_str = hex(data_byte)
            elif data_format == 'ASCII':
                data_str = chr(data_byte)
            else:
                data_str = hex(data_byte)
            label_text = f"D:{data_str}"
            self.create_cursor(group_idx, sample_idx, label_text)
        elif event == 'STOP':
            # Create cursor for STOP condition
            self.create_cursor(group_idx, sample_idx, 'Stop')

            # Build message string
            message = decoded_data.get('message', [])
            message_str = ""
            for item in message:
                if item['type'] == 'Address':
                    addr: int = item['data']
                    rw_bit: Optional[int] = item.get('rw')
                    if data_format == 'Binary':
                        addr_str = bin(addr)
                    elif data_format == 'Decimal':
                        addr_str = str(addr)
                    elif data_format == 'Hexadecimal':
                        addr_str = hex(addr)
                    elif data_format == 'ASCII':
                        addr_str = chr(addr)
                    else:
                        addr_str = hex(addr)
                    if rw_bit is not None:
                        rw_str = 'Read' if rw_bit else 'Write'
                        message_str += f"Address: {addr_str} ({rw_str})\n"
                    else:
                        message_str += f"Address: {addr_str}\n"
                elif item['type'] == 'Data':
                    data_byte: int = item['data']
                    if data_format == 'Binary':
                        data_str = bin(data_byte)
                    elif data_format == 'Decimal':
                        data_str = str(data_byte)
                    elif data_format == 'Hexadecimal':
                        data_str = hex(data_byte)
                    elif data_format == 'ASCII':
                        data_str = chr(data_byte)
                    else:
                        data_str = hex(data_byte)
                    message_str += f"Data: {data_str}\n"
                elif item['type'] == 'ACK':
                    ack: int = item['data']
                    ack_str: str = 'ACK' if ack == 0 else 'NACK'
                    message_str += f"{ack_str}\n"

            message_str += "-" * 20 + "\n"

            # Append the message to the group's messages
            self.decoded_messages_per_group[group_idx].append(message_str)

    def create_cursor(self, group_idx: int, sample_idx: int, label_text: str) -> None:
        """
        Creates a visual cursor on the plot at the specified sample index with a label.

        Args:
            group_idx (int): The index of the I2C group (0-based).
            sample_idx (int): The sample index where the cursor should be placed.
            label_text (str): The text label to display alongside the cursor.
        """
        # Get base level for this group
        base_level = (4 - group_idx - 1) * 4  # Adjust as needed
        # Cursor color (keeping your tweaks)
        cursor_color = '#00F5FF'  # Use your preferred color
        # Create a vertical line segment between SDA and SCL levels
        y1 = base_level + 1
        y2 = base_level + 2
        x = 0  # Initial x position, will be updated in update_plot
        # Create line data
        line = pg.PlotDataItem([x, x], [y1, y2], pen=pg.mkPen(color=cursor_color, width=2))
        self.plot.addItem(line)
        # Add a label
        label = pg.TextItem(text=label_text, anchor=(0.1, 0.5), color=cursor_color)
        font = QFont("Arial", 12)
        label.setFont(font)
        self.plot.addItem(label)
        # Store the line, label, and sample index
        self.group_cursors[group_idx].append({
            'line': line,
            'label': label,
            'sample_idx': sample_idx,
            'base_level': base_level,
            'y1': y1,
            'y2': y2
        })

    def clear_decoded_text(self) -> None:
        """
        Clears all decoded text boxes and messages per group.
        """
        for idx in range(4):
            self.decoded_messages_per_group[idx].clear()
        # Cursors are already cleared in clear_data_buffers

    def update_plot(self) -> None:
        """
        Updates the graphical plot with the latest data from the buffers and manages cursor positions.
        """
        for group_idx, is_enabled in enumerate(self.i2c_group_enabled):
            if is_enabled:
                group_config = self.group_configs[group_idx]
                sda_channel = group_config['data_channel'] - 1  # Adjust index
                scl_channel = group_config['clock_channel'] - 1  # Adjust index

                # Get the curves for this group
                sda_curve = self.group_curves[group_idx]['sda_curve']
                scl_curve = self.group_curves[group_idx]['scl_curve']

                # Prepare data for plotting
                sda_data = list(self.data_buffer[sda_channel])
                scl_data = list(self.data_buffer[scl_channel])

                num_samples = len(sda_data)
                if num_samples > 1:
                    t = np.arange(num_samples) / self.sample_rate

                    # Offset per group to separate the signals vertically
                    base_level = (4 - group_idx - 1) * 4  # Adjust as needed

                    # --- Plot SDA Signal ---
                    sda_square_wave_time = []
                    sda_square_wave_data = []
                    for j in range(1, num_samples):
                        sda_square_wave_time.extend([t[j - 1], t[j]])
                        level = sda_data[j - 1] + base_level
                        sda_square_wave_data.extend([level, level])
                        if sda_data[j] != sda_data[j - 1]:
                            sda_square_wave_time.append(t[j])
                            level = sda_data[j] + base_level
                            sda_square_wave_data.append(level)
                    sda_curve.setData(sda_square_wave_time, sda_square_wave_data)

                    # --- Plot SCL Signal ---
                    scl_square_wave_time = []
                    scl_square_wave_data = []
                    for j in range(1, num_samples):
                        scl_square_wave_time.extend([t[j - 1], t[j]])
                        level = scl_data[j - 1] + base_level + 2  # Offset by 2 to separate from SDA
                        scl_square_wave_data.extend([level, level])
                        if scl_data[j] != scl_data[j - 1]:
                            scl_square_wave_time.append(t[j])
                            level = scl_data[j] + base_level + 2
                            scl_square_wave_data.append(level)
                    scl_curve.setData(scl_square_wave_time, scl_square_wave_data)

                    # --- Update Cursors ---
                    cursors_to_remove = []
                    for cursor_info in self.group_cursors[group_idx]:
                        sample_idx = cursor_info['sample_idx']
                        idx_in_buffer = sample_idx - (self.total_samples - num_samples)
                        if 0 <= idx_in_buffer < num_samples:
                            cursor_time = t[int(idx_in_buffer)]
                            # Update the line position
                            x = cursor_time
                            y1 = cursor_info['y1']
                            y2 = cursor_info['y2']
                            cursor_info['line'].setData([x, x], [y1, y2])
                            # Update the label position
                            label_offset = (t[1] - t[0]) * 5  # Adjust label offset as needed
                            label = cursor_info['label']
                            label.setPos(x + label_offset, (y1 + y2) / 2)
                            cursor_info['x_pos'] = x + label_offset  # Store x position for overlap checking
                        else:
                            # Cursor is no longer in the buffer, remove it
                            self.plot.removeItem(cursor_info['line'])
                            self.plot.removeItem(cursor_info['label'])
                            cursors_to_remove.append(cursor_info)
                    # Remove cursors that are no longer in buffer
                    for cursor_info in cursors_to_remove:
                        self.group_cursors[group_idx].remove(cursor_info)

                    # --- Hide Overlapping Labels ---
                    # Collect labels and their x positions
                    labels_with_positions = []
                    for cursor_info in self.group_cursors[group_idx]:
                        label = cursor_info['label']
                        x_pos = cursor_info.get('x_pos', None)
                        if x_pos is not None:
                            labels_with_positions.append((x_pos, label))

                    # Sort labels by x position
                    labels_with_positions.sort(key=lambda item: item[0])

                    # Hide labels that overlap
                    min_label_spacing = (t[1] - t[0]) * 10  # Adjust as needed
                    last_label_x = None
                    for x_pos, label in labels_with_positions:
                        if last_label_x is None:
                            label.setVisible(True)
                            last_label_x = x_pos
                        else:
                            if x_pos - last_label_x < min_label_spacing:
                                # Labels are too close, hide this label
                                label.setVisible(False)
                            else:
                                label.setVisible(True)
                                last_label_x = x_pos
                else:
                    # Clear the curves if no data
                    sda_curve.setData([], [])
                    scl_curve.setData([], [])

            else:
                # If group is not enabled, hide curves
                self.group_curves[group_idx]['sda_curve'].setVisible(False)
                self.group_curves[group_idx]['scl_curve'].setVisible(False)

    def closeEvent(self, event: QtCore.QEvent) -> None:
        """
        Handles the close event of the I2CDisplay widget. Ensures that the worker thread is
        properly stopped before closing.

        Args:
            event (Qt.QEvent): The close event triggered when the widget is being closed.
        """
        self.worker.stop_worker()
        self.worker.quit()
        self.worker.wait()
        event.accept()

    def open_configuration_dialog(self, group_idx: int) -> None:
        """
        Opens the configuration dialog for a specific I2C group, allowing the user to update settings.

        Args:
            group_idx (int): The index of the I2C group to configure (0-based).
        """
        current_config = self.group_configs[group_idx]
        dialog = I2CConfigDialog(current_config, parent=self)
        if dialog.exec():
            new_config = dialog.get_configuration()
            self.group_configs[group_idx] = new_config
            print(f"Configuration for group {group_idx + 1} updated: {new_config}")
            # Update labels on the button to reflect new channel assignments
            sda_channel = new_config['data_channel']
            scl_channel = new_config['clock_channel']
            label = f"I2C {group_idx + 1}\nCh{sda_channel}:SDA\nCh{scl_channel}:SCL"
            self.channel_buttons[group_idx].setText(label)
            # Update trigger mode buttons
            self.sda_trigger_mode_buttons[group_idx].setText(f"SDA - {self.current_trigger_modes[sda_channel - 1]}")
            self.scl_trigger_mode_buttons[group_idx].setText(f"SCL - {self.current_trigger_modes[scl_channel - 1]}")
            # Update curves visibility
            is_checked = self.i2c_group_enabled[group_idx]
            sda_curve = self.group_curves[group_idx]['sda_curve']
            scl_curve = self.group_curves[group_idx]['scl_curve']
            sda_curve.setVisible(is_checked)
            scl_curve.setVisible(is_checked)
            # Clear data buffers
            self.clear_data_buffers()
            # Update worker's group configurations
            self.worker.group_configs = self.group_configs
