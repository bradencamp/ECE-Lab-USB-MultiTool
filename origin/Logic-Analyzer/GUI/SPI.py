"""
SPI.py

This module defines classes and functionalities related to handling SPI communication,
data processing, and graphical display for a Logic Analyzer application. It includes:

- SerialWorker: A QThread subclass that manages serial data reading, SPI decoding, and triggering mechanisms.
- FixedYViewBox: A custom PyQtGraph ViewBox that restricts scaling and translation on the Y-axis.
- EditableButton: A QPushButton subclass that allows for context menu operations like renaming and resetting.
- SPIChannelButton: An EditableButton subclass specific to SPI channels, with additional signals for configuration.
- SPIConfigDialog: A QDialog subclass that provides a user interface for configuring SPI channel settings.
- SPIDisplay: A QWidget subclass that provides the main interface for displaying and interacting with SPI data,
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
from typing import List, Dict, Optional, Any

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
)
from PyQt6.QtGui import QIcon, QIntValidator, QFont
from PyQt6.QtCore import QTimer, QThread, pyqtSignal, Qt, QPoint
from collections import deque

from InterfaceCommands import (
    get_trigger_edge_command,
    get_trigger_pins_command,
)
from aesthetic import get_icon


class SerialWorker(QThread):
    """
    SerialWorker handles SPI serial communication in a separate thread. It reads incoming data from
    the serial port, decodes SPI messages, processes trigger conditions for multiple SPI groups,
    and emits signals when data or decoded messages are ready for processing.

    Attributes:
        data_ready (pyqtSignal): Signal emitted when new raw data is ready. Carries an integer value and sample index.
        decoded_message_ready (pyqtSignal): Signal emitted when a decoded SPI message is ready. Carries a dictionary with message details.
        is_running (bool): Flag indicating whether the worker is active.
        channels (int): Number of channels to monitor for triggers.
        group_configs (List[Dict]): Configuration settings for each SPI group.
        trigger_modes (List[str]): List of trigger modes for each channel.
        states (List[str]): Current state of the state machine for each SPI group.
        current_bits_mosi (List[str]): Current bits collected on MOSI for each SPI group.
        current_bits_miso (List[str]): Current bits collected on MISO for each SPI group.
        last_clk_values (List[int]): Last sampled CLK values for edge detection.
        last_ss_values (List[int]): Last sampled SS values for edge detection.
        sample_idx (int): Global sample index counter.
    """

    data_ready = pyqtSignal(int, int)  # For raw data values and sample indices
    decoded_message_ready = pyqtSignal(dict)  # For decoded messages

    def __init__(
        self,
        port: str,
        baudrate: int,
        channels: int = 8,
        group_configs: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        """
        Initializes the SerialWorker thread with the specified serial port parameters and SPI group configurations.

        Args:
            port (str): The serial port to connect to (e.g., 'COM3', '/dev/ttyUSB0').
            baudrate (int): The baud rate for serial communication.
            channels (int, optional): The number of channels to monitor for triggers. Defaults to 8.
            group_configs (List[Dict[str, Any]], optional): Configuration settings for each SPI group. Defaults to None.
        """
        super().__init__()
        self.is_running: bool = True
        self.channels: int = channels
        self.group_configs: List[Dict[str, Any]] = group_configs if group_configs else [{} for _ in range(2)]
        self.trigger_modes: List[str] = ['No Trigger'] * self.channels
        self.sample_idx: int = 0  # Initialize sample index

        # Initialize SPI decoding variables for each group
        self.states: List[str] = ['IDLE'] * len(self.group_configs)
        self.current_bits_mosi: List[str] = [''] * len(self.group_configs)
        self.current_bits_miso: List[str] = [''] * len(self.group_configs)
        self.last_clk_values: List[int] = [0] * len(self.group_configs)
        self.last_ss_values: List[int] = [1] * len(self.group_configs)  # Assuming active low SS

        try:
            self.serial = serial.Serial(port, baudrate, timeout=0.1)
        except serial.SerialException as e:
            print(f"Failed to open serial port: {str(e)}")
            self.is_running = False

    def set_trigger_mode(self, channel_idx: int, mode: str) -> None:
        """
        Sets the trigger mode for a specific channel.

        Args:
            channel_idx (int): The index of the channel (0-based).
            mode (str): The trigger mode to set (e.g., 'No Trigger', 'Rising Edge', 'Falling Edge').
        """
        if 0 <= channel_idx < self.channels:
            self.trigger_modes[channel_idx] = mode
        else:
            print(f"Channel index {channel_idx} out of range.")

    def run(self) -> None:
        """
        The main loop of the worker thread. Continuously reads data from the serial port,
        processes SPI decoding, and emits data_ready and decoded_message_ready signals when appropriate.
        """
        while self.is_running:
            if self.serial.in_waiting:
                raw_data = self.serial.read(self.serial.in_waiting).splitlines()
                for line in raw_data:
                    try:
                        data_value = int(line.strip())
                        self.data_ready.emit(data_value, self.sample_idx)  # Emit data_value and sample_idx
                        self.decode_spi(data_value, self.sample_idx)
                        self.sample_idx += 1  # Increment sample index
                    except ValueError:
                        print(f"Invalid data received: {line.strip()}")
                        continue

    def decode_spi(self, data_value: int, sample_idx: int) -> None:
        """
        Decodes incoming serial data to interpret SPI messages based on configured groups.

        Args:
            data_value (int): The raw data value read from the serial port.
            sample_idx (int): The current sample index.
        """
        for group_idx, group_config in enumerate(self.group_configs):
            # Retrieve channel indices; default to -1 if not set
            ss_channel = group_config.get('ss_channel', 1) - 1
            clk_channel = group_config.get('clock_channel', 2) - 1
            mosi_channel = group_config.get('mosi_channel', 3) - 1
            miso_channel = group_config.get('miso_channel', 4) - 1
            bits = group_config.get('bits', 8)
            first_bit = group_config.get('first_bit', 'MSB')
            ss_active = group_config.get('ss_active', 'Low')
            data_format = group_config.get('data_format', 'Hexadecimal')

            # Extract SS, CLK, MOSI, MISO values
            try:
                ss = (data_value >> ss_channel) & 1
                clk = (data_value >> clk_channel) & 1
                mosi = (data_value >> mosi_channel) & 1
                miso = (data_value >> miso_channel) & 1
            except IndexError:
                print(f"Invalid channel configuration for group {group_idx + 1}.")
                continue

            # Adjust for SS active level
            ss_active_level = 0 if ss_active.lower() == 'low' else 1
            ss_inactive_level = 1 - ss_active_level

            # State machine for SPI decoding
            state = self.states[group_idx]
            current_bits_mosi = self.current_bits_mosi[group_idx]
            current_bits_miso = self.current_bits_miso[group_idx]
            last_clk = self.last_clk_values[group_idx]
            last_ss = self.last_ss_values[group_idx]

            # Detect edges on CLK
            clk_edge = clk != last_clk
            clk_rising = clk_edge and clk == 1
            clk_falling = clk_edge and clk == 0

            # Detect SS activation/deactivation
            ss_edge = ss != last_ss
            ss_active_now = ss == ss_active_level
            ss_inactive_now = ss == ss_inactive_level

            if state == 'IDLE':
                if ss_active_now:
                    # SS went active, start capturing data
                    state = 'RECEIVE'
                    current_bits_mosi = ''
                    current_bits_miso = ''
            elif state == 'RECEIVE':
                if ss_inactive_now:
                    # SS went inactive, end of data
                    if current_bits_mosi or current_bits_miso:
                        # Emit the decoded data
                        self.emit_decoded_data(
                            group_idx,
                            current_bits_mosi,
                            current_bits_miso,
                            sample_idx,
                            data_format
                        )
                        current_bits_mosi = ''
                        current_bits_miso = ''
                    state = 'IDLE'
                else:
                    # Continue receiving data
                    if clk_rising:
                        # Sample data on rising edge
                        if first_bit.upper() == 'MSB':
                            current_bits_mosi += str(mosi)
                            current_bits_miso += str(miso)
                        else:
                            current_bits_mosi = str(mosi) + current_bits_mosi
                            current_bits_miso = str(miso) + current_bits_miso

                        if len(current_bits_mosi) == bits or len(current_bits_miso) == bits:
                            # Full data received
                            self.emit_decoded_data(
                                group_idx,
                                current_bits_mosi,
                                current_bits_miso,
                                sample_idx,
                                data_format
                            )
                            current_bits_mosi = ''
                            current_bits_miso = ''

            # Update the stored states
            self.states[group_idx] = state
            self.current_bits_mosi[group_idx] = current_bits_mosi
            self.current_bits_miso[group_idx] = current_bits_miso
            self.last_clk_values[group_idx] = clk
            self.last_ss_values[group_idx] = ss

    def emit_decoded_data(
        self,
        group_idx: int,
        bits_str_mosi: str,
        bits_str_miso: str,
        sample_idx: int,
        data_format: str
    ) -> None:
        """
        Converts bit strings to formatted data and emits the decoded message.

        Args:
            group_idx (int): The index of the SPI group (0-based).
            bits_str_mosi (str): Bit string collected on MOSI.
            bits_str_miso (str): Bit string collected on MISO.
            sample_idx (int): The sample index where data was captured.
            data_format (str): The format to represent the data (e.g., 'Binary', 'Decimal', 'Hexadecimal', 'ASCII').
        """
        # Convert bits to integer
        data_value_mosi = int(bits_str_mosi, 2) if bits_str_mosi else None
        data_value_miso = int(bits_str_miso, 2) if bits_str_miso else None

        # Format data according to data_format
        data_str_mosi = self.format_data(data_value_mosi, data_format) if data_value_mosi is not None else ''
        data_str_miso = self.format_data(data_value_miso, data_format) if data_value_miso is not None else ''

        # Emit the decoded message
        decoded_message = {
            'group_idx': group_idx,
            'event': 'DATA',
            'data_mosi': data_str_mosi,
            'data_miso': data_str_miso,
            'sample_idx': sample_idx,
        }
        self.decoded_message_ready.emit(decoded_message)

    @staticmethod
    def format_data(data_value: int, data_format: str) -> str:
        """
        Formats the data value based on the specified format.

        Args:
            data_value (int): The data value to format.
            data_format (str): The format to represent the data (e.g., 'Binary', 'Decimal', 'Hexadecimal', 'ASCII').

        Returns:
            str: The formatted data string.
        """
        if data_format.lower() == 'binary':
            return bin(data_value)
        elif data_format.lower() == 'decimal':
            return str(data_value)
        elif data_format.lower() == 'hexadecimal':
            return hex(data_value)
        elif data_format.lower() == 'ascii':
            try:
                return chr(data_value)
            except ValueError:
                return f"\\x{data_value:02x}"
        else:
            return hex(data_value)

    def reset_decoding_states(self) -> None:
        """
        Resets the SPI decoding state machines for all groups, clearing buffers and states.
        """
        self.states = ['IDLE'] * len(self.group_configs)
        self.current_bits_mosi = [''] * len(self.group_configs)
        self.current_bits_miso = [''] * len(self.group_configs)
        self.last_clk_values = [0] * len(self.group_configs)
        self.last_ss_values = [1] * len(self.group_configs)
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

    def translateBy(self, t=None, x: Optional[float] = None, y: Optional[float] = None) -> None:
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
        self.default_label: str = label

    def show_context_menu(self, position: QPoint) -> None:
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


class SPIChannelButton(EditableButton):
    """
    SPIChannelButton is an EditableButton subclass specific to SPI channels. It emits additional
    signals for configuration and reset actions.

    Attributes:
        configure_requested (pyqtSignal): Signal emitted when the configure option is selected.
        reset_requested (pyqtSignal): Signal emitted when the reset to default option is selected.
    """

    configure_requested = pyqtSignal(int)  # Signal to notify when configure is requested
    reset_requested = pyqtSignal(int)       # Signal to notify when reset is requested

    def __init__(self, label: str, group_idx: int, parent: Optional[QWidget] = None) -> None:
        """
        Initializes the SPIChannelButton with a given label and group index.

        Args:
            label (str): The initial text label of the button.
            group_idx (int): The index of the SPI group this button represents.
            parent (QWidget, optional): The parent widget. Defaults to None.
        """
        super().__init__(label, parent)
        self.group_idx: int = group_idx  # Store the index of the SPI group

    def show_context_menu(self, position: QPoint) -> None:
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


class SPIConfigDialog(QDialog):
    """
    SPIConfigDialog provides a user interface for configuring SPI group settings, including
    SS channel, CLK channel, MOSI channel, MISO channel, data bits, first bit order, SS active level, and data format.
    """

    def __init__(self, current_config: Dict[str, Any], parent: Optional[QWidget] = None) -> None:
        """
        Initializes the SPIConfigDialog with the current configuration.

        Args:
            current_config (Dict[str, Any]): The current configuration settings for the SPI group.
            parent (QWidget, optional): The parent widget. Defaults to None.
        """
        super().__init__(parent)
        self.setWindowTitle("SPI Configuration")
        self.current_config: Dict[str, Any] = current_config  # Dictionary to hold current configurations

        self.init_ui()

    def init_ui(self) -> None:
        """
        Sets up the user interface components of the configuration dialog.
        """
        layout = QVBoxLayout()

        # SS Channel Selection
        ss_layout = QHBoxLayout()
        ss_label = QLabel("Slave Select (SS) Channel:")
        self.ss_combo = QComboBox()
        self.ss_combo.addItems([f"Channel {i+1}" for i in range(8)])
        ss_channel = self.current_config.get('ss_channel', 1)
        self.ss_combo.setCurrentIndex(ss_channel - 1)
        ss_layout.addWidget(ss_label)
        ss_layout.addWidget(self.ss_combo)
        layout.addLayout(ss_layout)

        # SS Active Level
        ss_active_layout = QHBoxLayout()
        ss_active_label = QLabel("SS Active Level:")
        self.ss_active_group = QButtonGroup(self)
        self.ss_active_low = QRadioButton("Low")
        self.ss_active_high = QRadioButton("High")
        self.ss_active_group.addButton(self.ss_active_low)
        self.ss_active_group.addButton(self.ss_active_high)
        ss_active_layout.addWidget(ss_active_label)
        ss_active_layout.addWidget(self.ss_active_low)
        ss_active_layout.addWidget(self.ss_active_high)
        layout.addLayout(ss_active_layout)

        ss_active = self.current_config.get('ss_active', 'Low')
        if ss_active.lower() == 'low':
            self.ss_active_low.setChecked(True)
        else:
            self.ss_active_high.setChecked(True)

        # Clock Channel Selection
        clock_layout = QHBoxLayout()
        clock_label = QLabel("Clock (CLK) Channel:")
        self.clock_combo = QComboBox()
        self.clock_combo.addItems([f"Channel {i+1}" for i in range(8)])
        clk_channel = self.current_config.get('clock_channel', 2)
        self.clock_combo.setCurrentIndex(clk_channel - 1)
        clock_layout.addWidget(clock_label)
        clock_layout.addWidget(self.clock_combo)
        layout.addLayout(clock_layout)

        # MOSI Channel Selection
        mosi_layout = QHBoxLayout()
        mosi_label = QLabel("Master Out Slave In (MOSI) Channel:")
        self.mosi_combo = QComboBox()
        self.mosi_combo.addItems([f"Channel {i+1}" for i in range(8)])
        mosi_channel = self.current_config.get('mosi_channel', 3)
        self.mosi_combo.setCurrentIndex(mosi_channel - 1)
        mosi_layout.addWidget(mosi_label)
        mosi_layout.addWidget(self.mosi_combo)
        layout.addLayout(mosi_layout)

        # MISO Channel Selection
        miso_layout = QHBoxLayout()
        miso_label = QLabel("Master In Slave Out (MISO) Channel:")
        self.miso_combo = QComboBox()
        self.miso_combo.addItems([f"Channel {i+1}" for i in range(8)])
        miso_channel = self.current_config.get('miso_channel', 4)
        self.miso_combo.setCurrentIndex(miso_channel - 1)
        miso_layout.addWidget(miso_label)
        miso_layout.addWidget(self.miso_combo)
        layout.addLayout(miso_layout)

        # Bits Selection
        bits_layout = QHBoxLayout()
        bits_label = QLabel("Data Bits:")
        self.bits_input = QLineEdit()
        self.bits_input.setValidator(QIntValidator(1, 32))
        self.bits_input.setText(str(self.current_config.get('bits', 8)))
        bits_layout.addWidget(bits_label)
        bits_layout.addWidget(self.bits_input)
        layout.addLayout(bits_layout)

        # First Bit Selection
        first_bit_layout = QHBoxLayout()
        first_bit_label = QLabel("First Bit Order:")
        self.first_bit_group = QButtonGroup(self)
        self.first_msb = QRadioButton("MSB")
        self.first_lsb = QRadioButton("LSB")
        self.first_bit_group.addButton(self.first_msb)
        self.first_bit_group.addButton(self.first_lsb)
        first_bit_layout.addWidget(first_bit_label)
        first_bit_layout.addWidget(self.first_msb)
        first_bit_layout.addWidget(self.first_lsb)
        layout.addLayout(first_bit_layout)

        first_bit = self.current_config.get('first_bit', 'MSB')
        if first_bit.upper() == 'MSB':
            self.first_msb.setChecked(True)
        else:
            self.first_lsb.setChecked(True)

        # Data Format Selection
        format_layout = QHBoxLayout()
        format_label = QLabel("Data Format:")
        self.format_combo = QComboBox()
        self.format_combo.addItems(["Binary", "Decimal", "Hexadecimal", "ASCII"])
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

    def get_configuration(self) -> Dict[str, Any]:
        """
        Retrieves the updated configuration settings from the dialog.

        Returns:
            Dict[str, Any]: A dictionary containing the updated SPI group configuration.
        """
        return {
            'ss_channel': self.ss_combo.currentIndex() + 1,
            'ss_active': 'Low' if self.ss_active_low.isChecked() else 'High',
            'clock_channel': self.clock_combo.currentIndex() + 1,
            'mosi_channel': self.mosi_combo.currentIndex() + 1,
            'miso_channel': self.miso_combo.currentIndex() + 1,
            'bits': int(self.bits_input.text()),
            'first_bit': 'MSB' if self.first_msb.isChecked() else 'LSB',
            'data_format': self.format_combo.currentText(),
        }


class SPIDisplay(QWidget):
    """
    SPIDisplay provides the main interface for displaying and interacting with SPI data.
    It includes graphical plots, control buttons, and configurations for multiple SPI groups.

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
        group_configs (List[Dict]): Configuration settings for each SPI group.
        default_group_configs (List[Dict]): Default configuration settings for each SPI group.
        spi_group_enabled (List[bool]): Flags indicating whether each SPI group is enabled.
        decoded_messages_per_group (Dict[int, List[str]]): Decoded messages for each SPI group.
        group_cursors (List[List[Dict[str, Any]]]): Cursors for each SPI group.
        timer (QTimer): Timer for updating the plot.
        is_reading (bool): Flag indicating if data reading is active.
        worker (SerialWorker): Worker thread handling serial communication.
        group_curves (List[Dict[str, pg.PlotDataItem]]): Plot curves for SS, CLK, MOSI, and MISO of each group.
        colors (List[str]): List of colors for plotting each group.
        channel_buttons (List[SPIChannelButton]): Buttons to toggle SPI group visibility and configuration.
        ss_trigger_mode_buttons (List[QPushButton]): Buttons to toggle trigger modes for SS of each group.
        clk_trigger_mode_buttons (List[QPushButton]): Buttons to toggle trigger modes for CLK of each group.
        sample_rate_input (QLineEdit): Input field for sample rate.
        num_samples_input (QLineEdit): Input field for number of samples.
        toggle_button (QPushButton): Button to start/stop data acquisition.
        single_button (QPushButton): Button to initiate a single data capture.
    """

    def __init__(self, port: str, baudrate: int, bufferSize: int, channels: int = 8) -> None:
        """
        Initializes the SPIDisplay with the specified serial port parameters and sets up the UI.

        Args:
            port (str): Serial port for communication.
            baudrate (int): Baud rate for serial communication.
            bufferSize (int): Size of the data buffer.
            channels (int, optional): Number of channels for the logic analyzer. Defaults to 8.
        """
        super().__init__()
        self.period: int = 65454
        self.num_samples: int = 0
        self.port: str = port
        self.baudrate: int = baudrate
        self.channels: int = channels
        self.bufferSize: int = bufferSize

        self.data_buffer: List[deque] = [deque(maxlen=self.bufferSize) for _ in range(self.channels)]  # 8 channels
        self.sample_indices: deque = deque(maxlen=self.bufferSize)
        self.total_samples: int = 0

        self.is_single_capture: bool = False

        self.current_trigger_modes: List[str] = ['No Trigger'] * self.channels
        self.trigger_mode_options: List[str] = ['No Trigger', 'Rising Edge', 'Falling Edge']

        self.sample_rate: int = 1000  # Default sample rate in Hz

        # Initialize group configurations with default channels and settings
        self.group_configs: List[Dict[str, Any]] = [
            {
                'ss_channel': 1,
                'clock_channel': 2,
                'mosi_channel': 3,
                'miso_channel': 4,
                'bits': 8,
                'first_bit': 'MSB',
                'ss_active': 'Low',
                'data_format': 'Hexadecimal'
            },
            {
                'ss_channel': 5,
                'clock_channel': 6,
                'mosi_channel': 7,
                'miso_channel': 8,
                'bits': 8,
                'first_bit': 'MSB',
                'ss_active': 'Low',
                'data_format': 'Hexadecimal'
            },
        ]

        # Default group configurations for resetting
        self.default_group_configs: List[Dict[str, Any]] = [
            {
                'ss_channel': 1,
                'clock_channel': 2,
                'mosi_channel': 3,
                'miso_channel': 4,
                'bits': 8,
                'first_bit': 'MSB',
                'ss_active': 'Low',
                'data_format': 'Hexadecimal'
            },
            {
                'ss_channel': 5,
                'clock_channel': 6,
                'mosi_channel': 7,
                'miso_channel': 8,
                'bits': 8,
                'first_bit': 'MSB',
                'ss_active': 'Low',
                'data_format': 'Hexadecimal'
            },
        ]

        self.spi_group_enabled: List[bool] = [False] * 2  # Track which SPI groups are enabled

        # Initialize decoded messages per group
        self.decoded_messages_per_group: Dict[int, List[str]] = {i: [] for i in range(2)}

        self.group_cursors: List[List[Dict[str, Any]]] = [[] for _ in range(2)]  # To store cursors per group

        self.setup_ui()
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_plot)

        self.is_reading: bool = False

        # Initialize worker thread
        self.worker: SerialWorker = SerialWorker(
            port=self.port,
            baudrate=self.baudrate,
            channels=self.channels,
            group_configs=self.group_configs
        )
        self.worker.data_ready.connect(self.handle_data_value)
        self.worker.decoded_message_ready.connect(self.display_decoded_message)
        self.worker.start()

        # Define colors for plotting
        self.colors: List[str] = ['#FF6EC7', '#39FF14', '#FF486D', '#BF00FF', '#FFFF33', '#FFA500', '#00F5FF', '#BFFF00']

        # Initialize group curves for plotting
        self.group_curves: List[Dict[str, pg.PlotDataItem]] = []
        for group_idx in range(2):  # 2 groups
            # Create curves for SS, CLK, MOSI, MISO for each group
            ss_curve = self.plot.plot(pen=pg.mkPen(color='#DEDEDE', width=2), name=f"Group {group_idx+1} SS")
            clk_curve = self.plot.plot(pen=pg.mkPen(color='#DEDEDE', width=2), name=f"Group {group_idx+1} CLK")
            mosi_curve = self.plot.plot(pen=pg.mkPen(color=self.colors[group_idx % len(self.colors)], width=2), name=f"Group {group_idx+1} MOSI")
            miso_curve = self.plot.plot(pen=pg.mkPen(color=self.colors[(group_idx + 1) % len(self.colors)], width=2), name=f"Group {group_idx+1} MISO")
            ss_curve.setVisible(False)
            clk_curve.setVisible(False)
            mosi_curve.setVisible(False)
            miso_curve.setVisible(False)
            self.group_curves.append({
                'ss_curve': ss_curve,
                'clk_curve': clk_curve,
                'mosi_curve': mosi_curve,
                'miso_curve': miso_curve
            })

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

        # Adjusted Y-range to better utilize the plotting area
        total_signals = 8  # 2 groups * 4 signals per group
        signal_spacing = 1.5
        self.plot.setYRange(-2, total_signals * signal_spacing + 2, padding=0)
        self.plot.setLimits(xMin=0, xMax=self.bufferSize / self.sample_rate)
        self.plot.enableAutoRange(axis=pg.ViewBox.XAxis, enable=False)
        self.plot.enableAutoRange(axis=pg.ViewBox.YAxis, enable=False)
        self.plot.showGrid(x=True, y=True)
        self.plot.getAxis('left').setTicks([])
        self.plot.getAxis('left').setStyle(showValues=False)
        self.plot.getAxis('left').setPen(None)
        self.plot.setLabel('bottom', 'Time', units='s')

        button_layout = QGridLayout()
        plot_layout.addLayout(button_layout, stretch=1)  # Allocate less space to the control panel

        button_widget = QWidget()
        button_layout = QGridLayout(button_widget)
        plot_layout.addWidget(button_widget)

        self.channel_buttons: List[SPIChannelButton] = []
        self.ss_trigger_mode_buttons: List[QPushButton] = []
        self.clk_trigger_mode_buttons: List[QPushButton] = []

        for i in range(2):
            row = i * 2  # Increment by 2 for each group
            group_config = self.group_configs[i]
            ss_channel = group_config['ss_channel']
            clk_channel = group_config['clock_channel']
            mosi_channel = group_config['mosi_channel']
            miso_channel = group_config['miso_channel']
            label = (
                f"SPI {i+1}\n"
                f"Ch{ss_channel}:SS\n"
                f"Ch{clk_channel}:SCLK\n"
                f"Ch{mosi_channel}:MOSI\n"
                f"Ch{miso_channel}:MISO"
            )
            button = SPIChannelButton(label, group_idx=i)

            # Set size policy and fixed width
            button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
            button.setFixedWidth(150)  # Set the fixed width for the button

            button.setCheckable(True)
            button.setChecked(False)
            button.toggled.connect(lambda checked, idx=i: self.toggle_channel_group(idx, checked))
            button.configure_requested.connect(self.open_configuration_dialog)
            button_layout.addWidget(button, row, 0, 2, 1)  # Span 2 rows, 1 column

            # SS Trigger Mode Button
            ss_trigger_button = QPushButton(f"SS - {self.current_trigger_modes[group_config['ss_channel'] - 1]}")
            ss_trigger_button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
            ss_trigger_button.setFixedWidth(120)
            ss_trigger_button.clicked.connect(lambda _, idx=i: self.toggle_trigger_mode(idx, 'SS'))
            button_layout.addWidget(ss_trigger_button, row, 1)

            # CLK Trigger Mode Button
            clk_trigger_button = QPushButton(f"SCLK - {self.current_trigger_modes[group_config['clock_channel'] - 1]}")
            clk_trigger_button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
            clk_trigger_button.setFixedWidth(120)
            clk_trigger_button.clicked.connect(lambda _, idx=i: self.toggle_trigger_mode(idx, 'CLK'))
            button_layout.addWidget(clk_trigger_button, row + 1, 1)

            # Set row stretches to distribute space equally
            button_layout.setRowStretch(row, 1)
            button_layout.setRowStretch(row + 1, 1)

            self.channel_buttons.append(button)
            self.ss_trigger_mode_buttons.append(ss_trigger_button)
            self.clk_trigger_mode_buttons.append(clk_trigger_button)

            # Connect reset signal
            button.reset_requested.connect(self.reset_group_to_default)

        # Calculate the starting row for the next set of widgets
        next_row = 2 * 2  # 2 groups * 2 rows per group

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

        # Initialize other components
        self.channel_visibility: List[bool] = [False] * self.channels

    def is_light_color(self, hex_color: str) -> bool:
        """
        Determines if a given hex color is light based on its luminance.

        Args:
            hex_color (str): The hex color string (e.g., '#FF6EC7').

        Returns:
            bool: True if the color is light, False otherwise.
        """
        hex_color = hex_color.lstrip('#')
        if len(hex_color) != 6:
            return False
        r, g, b = tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))
        luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
        return luminance > 0.5

    def reset_group_to_default(self, group_idx: int) -> None:
        """
        Resets the configuration of a specific SPI group to its default settings.

        Args:
            group_idx (int): The index of the SPI group to reset.
        """
        # Reset the group configuration to default settings
        default_config = self.default_group_configs[group_idx].copy()
        self.group_configs[group_idx] = default_config
        print(f"Group {group_idx + 1} reset to default configuration: {default_config}")

        # Reset the button's label to default
        self.channel_buttons[group_idx].setText(self.channel_buttons[group_idx].default_label)

        # Update trigger mode buttons
        ss_channel = default_config['ss_channel']
        clk_channel = default_config['clock_channel']
        ss_idx = ss_channel - 1
        clk_idx = clk_channel - 1

        self.current_trigger_modes[ss_idx] = 'No Trigger'
        self.current_trigger_modes[clk_idx] = 'No Trigger'
        self.ss_trigger_mode_buttons[group_idx].setText(f"SS - {self.current_trigger_modes[ss_idx]}")
        self.clk_trigger_mode_buttons[group_idx].setText(f"SCLK - {self.current_trigger_modes[clk_idx]}")

        # Update worker's group configurations
        self.worker.group_configs[group_idx] = default_config

        # Update curves visibility and colors
        is_checked = self.spi_group_enabled[group_idx]
        curves = self.group_curves[group_idx]
        ss_curve = curves['ss_curve']
        clk_curve = curves['clk_curve']
        mosi_curve = curves['mosi_curve']
        miso_curve = curves['miso_curve']
        ss_curve.setVisible(is_checked)
        clk_curve.setVisible(is_checked)
        mosi_curve.setVisible(is_checked)
        miso_curve.setVisible(is_checked)
        mosi_curve.setPen(pg.mkPen(color=self.colors[group_idx % len(self.colors)], width=2))
        miso_curve.setPen(pg.mkPen(color=self.colors[(group_idx + 1) % len(self.colors)], width=2))

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
            period = int((72 * 10**6) / sample_rate)
            print(f"Sample Rate set to {sample_rate} Hz, Period: {period} ticks")
            self.updateSampleTimer(period)
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
            print("Sent trigger edge command to device.")
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
            time.sleep(0.001)
            print("Sent trigger pins command to device.")
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
            print(f"Sample timer updated with period: {period}")
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
            print(f"Trigger timer updated with period16: {period16} and prescaler: {prescaler}")
        except Exception as e:
            print(f"Failed to update trigger timer: {e}")

    def toggle_trigger_mode(self, group_idx: int, line: str) -> None:
        """
        Toggles the trigger mode for a specific SPI group and line (SS/SCLK) cyclically through predefined options.

        Args:
            group_idx (int): The index of the SPI group (0-based).
            line (str): The line to toggle trigger mode for ('SS' or 'CLK').
        """
        group_config = self.group_configs[group_idx]
        if line == 'SS':
            channel_idx = group_config['ss_channel'] - 1  # Adjust index
            button = self.ss_trigger_mode_buttons[group_idx]
        elif line == 'CLK':
            channel_idx = group_config['clock_channel'] - 1  # Adjust index
            button = self.clk_trigger_mode_buttons[group_idx]
        else:
            print(f"Invalid line type: {line}")
            return

        # Cycle through trigger modes
        try:
            current_mode = self.current_trigger_modes[channel_idx]
            current_mode_idx = self.trigger_mode_options.index(current_mode)
            new_mode_idx = (current_mode_idx + 1) % len(self.trigger_mode_options)
            new_mode = self.trigger_mode_options[new_mode_idx]
            self.current_trigger_modes[channel_idx] = new_mode
            button.setText(f"{line} - {new_mode}")
            self.worker.set_trigger_mode(channel_idx, new_mode)
            self.send_trigger_edge_command()
            self.send_trigger_pins_command()
            print(f"Group {group_idx + 1} {line} trigger mode set to {new_mode}")
        except ValueError:
            print(f"Current trigger mode '{current_mode}' not recognized for channel {channel_idx}.")

    def toggle_channel_group(self, group_idx: int, is_checked: bool) -> None:
        """
        Toggles the visibility and activation of a specific SPI group.

        Args:
            group_idx (int): The index of the SPI group (0-based).
            is_checked (bool): Whether the group should be enabled.
        """
        self.spi_group_enabled[group_idx] = is_checked  # Update the enabled list

        # Update curves visibility
        curves = self.group_curves[group_idx]
        curves['ss_curve'].setVisible(is_checked)
        curves['clk_curve'].setVisible(is_checked)
        curves['mosi_curve'].setVisible(is_checked)
        curves['miso_curve'].setVisible(is_checked)

        button = self.channel_buttons[group_idx]
        if is_checked:
            color = self.colors[group_idx % len(self.colors)]
            text_color = 'black' if self.is_light_color(color) else 'white'
            button.setStyleSheet(
                f"QPushButton {{ background-color: {color}; color: {text_color}; "
                f"border: 1px solid #555; border-radius: 5px; padding: 5px; "
                f"text-align: left; }}"
            )
            print(f"SPI Group {group_idx + 1} enabled.")
        else:
            button.setStyleSheet("")
            print(f"SPI Group {group_idx + 1} disabled.")

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
            print("Data acquisition stopped.")
        else:
            self.is_single_capture = False
            self.send_start_message()
            self.start_reading()
            self.toggle_button.setText("Running")
            self.single_button.setEnabled(True)
            self.toggle_button.setStyleSheet("background-color: #00FF77; color: black;")
            print("Data acquisition started.")

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
                print("Sent 'start' command to device.")
            except serial.SerialException as e:
                print(f"Failed to send 'start' command: {str(e)}")
        else:
            print("Serial connection is not open.")

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
                print("Sent 'stop' command to device.")
            except serial.SerialException as e:
                print(f"Failed to send 'stop' command: {str(e)}")
        else:
            print("Serial connection is not open.")

    def start_reading(self) -> None:
        """
        Starts the data reading process by activating the timer.
        """
        if not self.is_reading:
            self.is_reading = True
            self.timer.start(1)
            print("Started reading data.")

    def stop_reading(self) -> None:
        """
        Stops the data reading process by deactivating the timer.
        """
        if self.is_reading:
            self.is_reading = False
            self.timer.stop()
            print("Stopped reading data.")

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
            print("Single data capture started.")

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
        print("Single data capture stopped.")

    def clear_data_buffers(self) -> None:
        """
        Clears all data buffers for each channel and removes all cursors from the plot.
        Also resets the worker's decoding states.
        """
        self.data_buffer = [deque(maxlen=self.bufferSize) for _ in range(self.channels)]
        self.total_samples = 0  # Reset total samples

        # Remove all cursors
        for group_idx in range(2):
            for cursor_info in self.group_cursors[group_idx]:
                self.plot.removeItem(cursor_info['line'])
                self.plot.removeItem(cursor_info['label'])
            self.group_cursors[group_idx] = []

        # Reset worker's decoding states
        self.worker.reset_decoding_states()
        print("Data buffers and cursors cleared.")

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

    def clear_decoded_text(self) -> None:
        """
        Clears all decoded messages per SPI group.
        """
        for idx in range(len(self.group_configs)):
            self.decoded_messages_per_group[idx] = []
        # Cursors are already cleared in clear_data_buffers
        print("Decoded messages cleared.")

    def display_decoded_message(self, decoded_data: Dict[str, Any]) -> None:
        """
        Displays a decoded SPI message by creating cursors and appending messages to the display.

        Args:
            decoded_data (Dict[str, Any]): A dictionary containing decoded message details.
        """
        group_idx: int = decoded_data.get('group_idx', -1)
        if group_idx == -1 or not self.spi_group_enabled[group_idx]:
            return  # Do not display if the group is not enabled or invalid

        data_format: str = self.group_configs[group_idx].get('data_format', 'Hexadecimal')
        event: Optional[str] = decoded_data.get('event', None)
        sample_idx: Optional[int] = decoded_data.get('sample_idx', None)

        if event == 'DATA':
            data_mosi: str = decoded_data.get('data_mosi', '')
            data_miso: str = decoded_data.get('data_miso', '')
            if data_mosi:
                label_text_mosi = f"MOSI: {data_mosi}"
                self.create_cursor(group_idx, sample_idx, label_text_mosi, signal='MOSI')
            if data_miso:
                label_text_miso = f"MISO: {data_miso}"
                self.create_cursor(group_idx, sample_idx, label_text_miso, signal='MISO')

    def create_cursor(
        self,
        group_idx: int,
        sample_idx: int,
        label_text: str,
        signal: str
    ) -> None:
        """
        Creates a visual cursor on the plot at the specified sample index with a label.

        Args:
            group_idx (int): The index of the SPI group (0-based).
            sample_idx (int): The sample index where the cursor should be placed.
            label_text (str): The text label to display alongside the cursor.
            signal (str): The signal type ('MOSI' or 'MISO') for positioning.
        """
        # Cursor color
        cursor_color: str = '#00F5FF'  # Preferred color

        # Signals per group: SS, CLK, MOSI, MISO
        signals_per_group: int = 4
        total_groups: int = len(self.spi_group_enabled)
        total_signals: int = total_groups * signals_per_group
        signal_spacing: float = 1.5

        # Determine the y-position based on the signal
        if signal == 'MOSI':
            signal_index: int = group_idx * signals_per_group + 2  # MOSI
            label_offset_y: float = -0.5  # Position label below the signal
            label_anchor: tuple = (0.5, 1.0)  # Anchor at the top center of the label
        elif signal == 'MISO':
            signal_index: int = group_idx * signals_per_group + 3  # MISO
            label_offset_y: float = -0.5  # Position label below the signal
            label_anchor: tuple = (0.5, 1.0)  # Anchor at the top center of the label
        else:
            print(f"Invalid signal type: {signal}")
            return  # Invalid signal, do nothing

        # Calculate y-position for the cursor
        y_position: float = (total_signals - signal_index - 1) * signal_spacing

        x: float = 0.0  # Initial x position, will be updated in update_plot

        # Create line data
        line = pg.PlotDataItem([x, x], [y_position, y_position + 1], pen=pg.mkPen(color=cursor_color, width=2))
        self.plot.addItem(line)

        # Add a label
        label = pg.TextItem(text=label_text, anchor=label_anchor, color=cursor_color)
        font = QFont("Arial", 12)
        label.setFont(font)
        self.plot.addItem(label)

        # Store the line, label, sample index, and label offset
        self.group_cursors[group_idx].append({
            'line': line,
            'label': label,
            'sample_idx': sample_idx,
            'y_position': y_position,
            'label_offset_y': label_offset_y
        })

    def update_plot(self) -> None:
        """
        Updates the graphical plot with the latest data from the buffers and manages cursor positions.
        """
        signals_per_group: int = 4
        total_groups: int = len(self.spi_group_enabled)
        total_signals: int = total_groups * signals_per_group
        signal_spacing: float = 1.5

        for group_idx, is_enabled in enumerate(self.spi_group_enabled):
            if is_enabled:
                group_config = self.group_configs[group_idx]
                ss_channel = group_config['ss_channel'] - 1  # Adjust index
                clk_channel = group_config['clock_channel'] - 1  # Adjust index
                mosi_channel = group_config['mosi_channel'] - 1  # Adjust index
                miso_channel = group_config['miso_channel'] - 1  # Adjust index

                # Get the curves for this group
                curves = self.group_curves[group_idx]
                ss_curve = curves['ss_curve']
                clk_curve = curves['clk_curve']
                mosi_curve = curves['mosi_curve']
                miso_curve = curves['miso_curve']

                # Prepare data for plotting
                ss_data = list(self.data_buffer[ss_channel])
                clk_data = list(self.data_buffer[clk_channel])
                mosi_data = list(self.data_buffer[mosi_channel])
                miso_data = list(self.data_buffer[miso_channel])

                num_samples = len(ss_data)
                if num_samples > 1:
                    t = np.arange(num_samples) / self.sample_rate

                    # --- Plot SS Signal ---
                    signal_index = group_idx * signals_per_group + 0  # SS
                    level_offset = (total_signals - signal_index - 1) * signal_spacing
                    ss_square_wave_time: List[float] = []
                    ss_square_wave_data: List[float] = []
                    for j in range(1, num_samples):
                        ss_square_wave_time.extend([t[j - 1], t[j]])
                        level = ss_data[j - 1] + level_offset
                        ss_square_wave_data.extend([level, level])
                        if ss_data[j] != ss_data[j - 1]:
                            ss_square_wave_time.append(t[j])
                            level = ss_data[j] + level_offset
                            ss_square_wave_data.append(level)
                    ss_curve.setData(ss_square_wave_time, ss_square_wave_data)

                    # --- Plot CLK Signal ---
                    signal_index = group_idx * signals_per_group + 1  # CLK
                    level_offset = (total_signals - signal_index - 1) * signal_spacing
                    clk_square_wave_time: List[float] = []
                    clk_square_wave_data: List[float] = []
                    for j in range(1, num_samples):
                        clk_square_wave_time.extend([t[j - 1], t[j]])
                        level = clk_data[j - 1] + level_offset
                        clk_square_wave_data.extend([level, level])
                        if clk_data[j] != clk_data[j - 1]:
                            clk_square_wave_time.append(t[j])
                            level = clk_data[j] + level_offset
                            clk_square_wave_data.append(level)
                    clk_curve.setData(clk_square_wave_time, clk_square_wave_data)

                    # --- Plot MOSI Signal ---
                    signal_index = group_idx * signals_per_group + 2  # MOSI
                    level_offset = (total_signals - signal_index - 1) * signal_spacing
                    mosi_square_wave_time: List[float] = []
                    mosi_square_wave_data: List[float] = []
                    for j in range(1, num_samples):
                        mosi_square_wave_time.extend([t[j - 1], t[j]])
                        level = mosi_data[j - 1] + level_offset
                        mosi_square_wave_data.extend([level, level])
                        if mosi_data[j] != mosi_data[j - 1]:
                            mosi_square_wave_time.append(t[j])
                            level = mosi_data[j] + level_offset
                            mosi_square_wave_data.append(level)
                    mosi_curve.setData(mosi_square_wave_time, mosi_square_wave_data)

                    # --- Plot MISO Signal ---
                    signal_index = group_idx * signals_per_group + 3  # MISO
                    level_offset = (total_signals - signal_index - 1) * signal_spacing
                    miso_square_wave_time: List[float] = []
                    miso_square_wave_data: List[float] = []
                    for j in range(1, num_samples):
                        miso_square_wave_time.extend([t[j - 1], t[j]])
                        level = miso_data[j - 1] + level_offset
                        miso_square_wave_data.extend([level, level])
                        if miso_data[j] != miso_data[j - 1]:
                            miso_square_wave_time.append(t[j])
                            level = miso_data[j] + level_offset
                            miso_square_wave_data.append(level)
                    miso_curve.setData(miso_square_wave_time, miso_square_wave_data)

                    # --- Update Cursors ---
                    cursors_to_remove: List[Dict[str, Any]] = []
                    for cursor_info in self.group_cursors[group_idx]:
                        sample_idx = cursor_info['sample_idx']
                        idx_in_buffer = sample_idx - (self.total_samples - num_samples)
                        if 0 <= idx_in_buffer < num_samples:
                            cursor_time = t[int(idx_in_buffer)]
                            # Update the line position
                            x = cursor_time
                            y_position = cursor_info['y_position']
                            cursor_info['line'].setData([x, x], [y_position - 1, y_position + 1])
                            # Update the label position
                            label_offset = (t[1] - t[0]) * 5  # Adjust label offset as needed
                            cursor_info['label'].setPos(x + label_offset, y_position + 0.7)
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
                    # Collect labels and their positions
                    labels_with_positions: List[tuple] = []
                    for cursor_info in self.group_cursors[group_idx]:
                        label = cursor_info['label']
                        x_pos = cursor_info.get('x_pos', None)
                        y_pos = cursor_info.get('y_position', None)
                        if x_pos is not None and y_pos is not None:
                            labels_with_positions.append((x_pos, y_pos, label))

                    # Sort labels by x and y positions
                    labels_with_positions.sort(key=lambda item: (item[0], item[1]))

                    # Hide labels that overlap in both x and y
                    min_label_spacing_x: float = (t[1] - t[0]) * 10  # Adjust as needed
                    min_label_spacing_y: float = signal_spacing * 0.5  # Adjust as needed
                    last_label_x: Optional[float] = None
                    last_label_y: Optional[float] = None
                    for x_pos, y_pos, label in labels_with_positions:
                        if last_label_x is None:
                            label.setVisible(True)
                            last_label_x = x_pos
                            last_label_y = y_pos
                        else:
                            if (abs(x_pos - last_label_x) < min_label_spacing_x and
                                    abs(y_pos - last_label_y) < min_label_spacing_y):
                                # Labels are too close in both x and y, hide this label
                                label.setVisible(False)
                            else:
                                label.setVisible(True)
                                last_label_x = x_pos
                                last_label_y = y_pos
                else:
                    # Clear the curves if no data
                    curves = self.group_curves[group_idx]
                    curves['ss_curve'].setData([], [])
                    curves['clk_curve'].setData([], [])
                    curves['mosi_curve'].setData([], [])
                    curves['miso_curve'].setData([], [])
            else:
                # If group is not enabled, hide curves
                curves = self.group_curves[group_idx]
                curves['ss_curve'].setVisible(False)
                curves['clk_curve'].setVisible(False)
                curves['mosi_curve'].setVisible(False)
                curves['miso_curve'].setVisible(False)

    def closeEvent(self, event: Any) -> None:
        """
        Handles the close event of the SPIDisplay widget. Ensures that the worker thread is
        properly stopped before closing.

        Args:
            event (Any): The close event triggered when the widget is being closed.
        """
        self.worker.stop_worker()
        self.worker.quit()
        self.worker.wait()
        event.accept()
        print("SPIDisplay closed and worker thread terminated.")

    def open_configuration_dialog(self, group_idx: int) -> None:
        """
        Opens the configuration dialog for a specific SPI group, allowing the user to update settings.

        Args:
            group_idx (int): The index of the SPI group to configure (0-based).
        """
        current_config = self.group_configs[group_idx]
        dialog = SPIConfigDialog(current_config, parent=self)
        if dialog.exec():
            new_config = dialog.get_configuration()
            self.group_configs[group_idx] = new_config
            print(f"Configuration for group {group_idx + 1} updated: {new_config}")
            # Update labels on the button to reflect new channel assignments
            ss_channel = new_config['ss_channel']
            clk_channel = new_config['clock_channel']
            mosi_channel = new_config['mosi_channel']
            miso_channel = new_config['miso_channel']
            label = (
                f"SPI {group_idx + 1}\n"
                f"Ch{ss_channel}:SS\n"
                f"Ch{clk_channel}:SCLK\n"
                f"Ch{mosi_channel}:MOSI\n"
                f"Ch{miso_channel}:MISO"
            )
            self.channel_buttons[group_idx].setText(label)
            # Update trigger mode buttons
            self.ss_trigger_mode_buttons[group_idx].setText(f"SS - {self.current_trigger_modes[ss_channel - 1]}")
            self.clk_trigger_mode_buttons[group_idx].setText(f"SCLK - {self.current_trigger_modes[clk_channel - 1]}")
            # Update curves visibility
            is_checked = self.spi_group_enabled[group_idx]
            curves = self.group_curves[group_idx]
            ss_curve = curves['ss_curve']
            clk_curve = curves['clk_curve']
            mosi_curve = curves['mosi_curve']
            miso_curve = curves['miso_curve']
            ss_curve.setVisible(is_checked)
            clk_curve.setVisible(is_checked)
            mosi_curve.setVisible(is_checked)
            miso_curve.setVisible(is_checked)
            # Clear data buffers
            self.clear_data_buffers()
            # Update worker's group configurations
            self.worker.group_configs = self.group_configs
            print(f"SPI Group {group_idx + 1} configuration applied.")

