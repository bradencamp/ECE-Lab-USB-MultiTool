"""
Signal.py

This module defines classes and functionalities related to handling serial communication,
data processing, and graphical display for a Logic Analyzer application. It includes:

- SerialWorker: A QThread subclass that manages serial data reading and triggering mechanisms.
- FixedYViewBox: A custom PyQtGraph ViewBox that restricts scaling and translation on the Y-axis.
- EditableButton: A QPushButton subclass that allows for context menu operations like renaming.
- SignalDisplay: A QWidget subclass that provides the main interface for displaying and interacting
  with signal data, including plotting, control buttons, and trigger configurations.

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
)
from PyQt6.QtGui import QIcon, QIntValidator
from PyQt6 import QtCore
from collections import deque
from typing import List, Optional

from InterfaceCommands import (
    get_trigger_edge_command,
    get_trigger_pins_command,
)
from aesthetic import get_icon


class SerialWorker(QtCore.QThread):
    """
    SerialWorker handles serial communication in a separate thread. It reads incoming data from
    the serial port, processes trigger conditions for multiple channels, and emits signals when
    data is ready for processing.

    Attributes:
        data_ready (pyqtSignal): Signal emitted when new data is ready. Carries a list of integers.
        is_running (bool): Flag indicating whether the worker is active.
        channels (int): Number of channels to monitor for triggers.
        trigger_modes (List[str]): List of trigger modes for each channel.
        bufferSize (int): Maximum size of the data buffer.
        serial (serial.Serial): Serial port instance for communication.
    """

    data_ready = QtCore.pyqtSignal(list)

    def __init__(self, port: str, baudrate: int, bufferSize: int, channels: int = 8) -> None:
        """
        Initializes the SerialWorker thread with the specified serial port parameters.

        Args:
            port (str): The serial port to connect to (e.g., 'COM3', '/dev/ttyUSB0').
            baudrate (int): The baud rate for serial communication.
            bufferSize (int): The maximum number of data points to store in the buffer.
            channels (int, optional): The number of channels to monitor for triggers. Defaults to 8.
        """
        super().__init__()
        self.is_running = True
        self.channels = channels
        self.trigger_modes = ['No Trigger'] * self.channels
        self.bufferSize = bufferSize
        try:
            self.serial = serial.Serial(port, baudrate)
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
        self.trigger_modes[channel_idx] = mode

    def run(self) -> None:
        """
        The main loop of the worker thread. Continuously reads data from the serial port,
        processes trigger conditions, and emits data_ready signals when appropriate.
        """
        data_buffer = deque(maxlen=self.bufferSize - 24)
        triggered = [False] * self.channels

        while self.is_running:
            if self.serial.in_waiting:
                raw_data = self.serial.read(self.serial.in_waiting).splitlines()
                for line in raw_data:
                    try:
                        data_value = int(line.strip())
                        data_buffer.append(data_value)

                        for i in range(self.channels):
                            if not triggered[i] and self.trigger_modes[i] != 'No Trigger':
                                last_value = data_buffer[-2] if len(data_buffer) >= 2 else None
                                if last_value is not None:
                                    current_bit = (data_value >> i) & 1
                                    last_bit = (last_value >> i) & 1

                                    if self.trigger_modes[i] == 'Rising Edge' and last_bit == 0 and current_bit == 1:
                                        triggered[i] = True
                                        print(f"Trigger condition met on channel {i+1}: Rising Edge")
                                    elif self.trigger_modes[i] == 'Falling Edge' and last_bit == 1 and current_bit == 0:
                                        triggered[i] = True
                                        print(f"Trigger condition met on channel {i+1}: Falling Edge")
                        if any(triggered) or all(mode == 'No Trigger' for mode in self.trigger_modes):
                            self.data_ready.emit([data_value])

                    except ValueError:
                        continue

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
        super(FixedYViewBox, self).__init__(*args, **kwargs)

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
                x = s[0]
            else:
                x = s
        super(FixedYViewBox, self).scaleBy(x=x, y=y, center=center)

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
                x = t[0]
            else:
                x = t
        super(FixedYViewBox, self).translateBy(x=x, y=y)


class EditableButton(QPushButton):
    """
    EditableButton is a QPushButton subclass that allows users to rename the button label
    via a context menu and reset it to its default label.
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
            position (Qt.QPoint): The position where the context menu is requested.
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


class SignalDisplay(QWidget):
    """
    SignalDisplay provides the main interface for displaying and interacting with signal data.
    It includes graphical plots, control buttons, and configurations for triggers and sampling.

    Attributes:
        period (int): The period for sample timing.
        num_samples (int): Number of samples to capture.
        port (str): Serial port for communication.
        baudrate (int): Baud rate for serial communication.
        channels (int): Number of channels for the logic analyzer.
        bufferSize (int): Size of the data buffer.
        data_buffer (List[deque]): Data buffers for each channel.
        channel_visibility (List[bool]): Visibility status for each channel.
        is_single_capture (bool): Flag indicating if a single capture is active.
        current_trigger_modes (List[str]): Current trigger modes for each channel.
        trigger_mode_indices (List[int]): Indices representing trigger modes for each channel.
        sample_rate (int): Sampling rate in Hz.
        timer (QTimer): Timer for updating the plot.
        is_reading (bool): Flag indicating if data reading is active.
        worker (SerialWorker): Worker thread handling serial communication.
        graph_layout (pg.GraphicsLayoutWidget): Layout widget for graphs.
        plot (pg.PlotItem): Plot item for displaying data.
        colors (List[str]): List of colors for plotting each channel.
        curves (List[pg.PlotDataItem]): Plot curves for each channel.
        channel_buttons (List[EditableButton]): Buttons to toggle channel visibility.
        trigger_mode_buttons (List[QPushButton]): Buttons to toggle trigger modes.
        cursor (pg.InfiniteLine): Cursor for measurement on the plot.
        cursor_label (pg.TextItem): Label displaying cursor position.
    """

    def __init__(self, port: str, baudrate: int, bufferSize: int, channels: int = 8) -> None:
        """
        Initializes the SignalDisplay with the specified serial port parameters and sets up the UI.

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

        self.data_buffer: List[deque] = [deque(maxlen=self.bufferSize) for _ in range(self.channels)]
        self.channel_visibility: List[bool] = [False] * self.channels

        self.is_single_capture = False
        self.current_trigger_modes: List[str] = ['No Trigger'] * self.channels
        self.trigger_mode_indices: List[int] = [0] * self.channels
        self.sample_rate = 1000  # Default sample rate in Hz

        self.setup_ui()
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_plot)

        self.is_reading = False

        self.worker = SerialWorker(self.port, self.baudrate, self.bufferSize, channels=self.channels)
        self.worker.data_ready.connect(self.handle_data)
        self.worker.start()

    def setup_ui(self) -> None:
        """
        Sets up the user interface components, including the graph, control buttons, and input fields.
        """
        main_layout = QHBoxLayout(self)

        self.graph_layout = pg.GraphicsLayoutWidget()
        main_layout.addWidget(self.graph_layout)

        self.plot = self.graph_layout.addPlot(viewBox=FixedYViewBox())
        self.plot.setXRange(0, 200 / self.sample_rate, padding=0)
        self.plot.setLimits(xMin=0, xMax=self.bufferSize / self.sample_rate)
        self.plot.setYRange(-2, 2 * self.channels, padding=0)
        self.plot.enableAutoRange(axis=pg.ViewBox.XAxis, enable=False)
        self.plot.enableAutoRange(axis=pg.ViewBox.YAxis, enable=False)
        self.plot.showGrid(x=True, y=True)
        self.plot.getAxis('left').setTicks([])
        self.plot.getAxis('left').setStyle(showValues=False)
        self.plot.getAxis('left').setPen(None)
        self.plot.setLabel('bottom', 'Time', units='s')

        self.colors = ['#FF6EC7', '#39FF14', '#FF486D', '#BF00FF', '#FFFF33', '#FFA500', '#00F5FF', '#BFFF00']
        self.curves: List[pg.PlotDataItem] = []
        for i in range(self.channels):
            color = self.colors[i % len(self.colors)]
            curve = self.plot.plot(pen=pg.mkPen(color=color, width=4))
            curve.setVisible(self.channel_visibility[i])
            self.curves.append(curve)

        button_layout = QGridLayout()
        main_layout.addLayout(button_layout)

        self.channel_buttons: List[EditableButton] = []
        self.trigger_mode_buttons: List[QPushButton] = []
        self.trigger_mode_options = ['No Trigger', 'Rising Edge', 'Falling Edge']

        for i in range(self.channels):
            label = f"DIO {i+1}"
            button = EditableButton(label)
            button.setCheckable(True)
            button.setChecked(False)
            button.toggled.connect(lambda checked, idx=i: self.toggle_channel(idx, checked))
            button_layout.addWidget(button, i, 0)
            self.channel_buttons.append(button)

            trigger_button = QPushButton(self.trigger_mode_options[self.trigger_mode_indices[i]])
            trigger_button.clicked.connect(lambda _, idx=i: self.toggle_trigger_mode(idx))
            button_layout.addWidget(trigger_button, i, 1)
            self.trigger_mode_buttons.append(trigger_button)

        # Sample Rate input
        self.sample_rate_label = QLabel("Sample Rate (Hz):")
        button_layout.addWidget(self.sample_rate_label, self.channels, 0)

        self.sample_rate_input = QLineEdit()
        self.sample_rate_input.setValidator(QIntValidator(1, 5000000))
        self.sample_rate_input.setText("1000")
        button_layout.addWidget(self.sample_rate_input, self.channels, 1)
        self.sample_rate_input.returnPressed.connect(self.handle_sample_rate_input)

        # Number of Samples input
        self.num_samples_label = QLabel("Number of Samples:")
        button_layout.addWidget(self.num_samples_label, self.channels + 1, 0)

        self.num_samples_input = QLineEdit()
        self.num_samples_input.setValidator(QIntValidator(1, 1023))
        self.num_samples_input.setText("300")
        button_layout.addWidget(self.num_samples_input, self.channels + 1, 1)
        self.num_samples_input.returnPressed.connect(self.send_num_samples_command)

        # Control buttons layout
        control_buttons_layout = QHBoxLayout()
        self.toggle_button = QPushButton("Start")
        self.toggle_button.clicked.connect(self.toggle_reading)
        control_buttons_layout.addWidget(self.toggle_button)

        self.single_button = QPushButton("Single")
        self.single_button.clicked.connect(self.start_single_capture)
        control_buttons_layout.addWidget(self.single_button)
        button_layout.addLayout(control_buttons_layout, self.channels + 2, 0, 1, 2)

        # Cursor for measurement
        self.cursor = pg.InfiniteLine(pos=0, angle=90, movable=True, pen=pg.mkPen(color='y', width=2))
        self.plot.addItem(self.cursor)

        self.cursor_label = pg.TextItem(anchor=(0, 1), color='y')
        self.plot.addItem(self.cursor_label)
        self.update_cursor_position()
        self.cursor.sigPositionChanged.connect(self.update_cursor_position)

    def handle_sample_rate_input(self) -> None:
        """
        Handles the event when the sample rate input field receives a return key press.
        Validates and updates the sample rate, adjusts the plot range and timers accordingly.
        """
        try:
            sample_rate = int(self.sample_rate_input.text())
            if sample_rate <= 0:
                raise ValueError("Sample rate must be positive")
            self.sample_rate = sample_rate
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
            selected_bits = (period16 >> 8) & 0xFF
            self.worker.serial.write(str(selected_bits).encode('utf-8'))
            time.sleep(0.01)
            # Send low byte
            selected_bits = period16 & 0xFF
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

    def toggle_trigger_mode(self, channel_idx: int) -> None:
        """
        Toggles the trigger mode for a specific channel cyclically through predefined options.

        Args:
            channel_idx (int): The index of the channel (0-based).
        """
        self.trigger_mode_indices[channel_idx] = (self.trigger_mode_indices[channel_idx] + 1) % len(self.trigger_mode_options)
        mode = self.trigger_mode_options[self.trigger_mode_indices[channel_idx]]
        self.trigger_mode_buttons[channel_idx].setText(mode)
        self.current_trigger_modes[channel_idx] = mode
        if self.worker:
            self.worker.set_trigger_mode(channel_idx, mode)
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

    def toggle_channel(self, channel_idx: int, is_checked: bool) -> None:
        """
        Toggles the visibility of a specific channel's data on the plot.

        Args:
            channel_idx (int): The index of the channel (0-based).
            is_checked (bool): Whether the channel should be visible.
        """
        self.channel_visibility[channel_idx] = is_checked
        self.curves[channel_idx].setVisible(is_checked)

        button = self.channel_buttons[channel_idx]
        if is_checked:
            color = self.colors[channel_idx % len(self.colors)]
            text_color = 'black' if self.is_light_color(color) else 'white'
            button.setStyleSheet(f"QPushButton {{ background-color: {color}; color: {text_color}; "
                                 f"border: 1px solid #555; border-radius: 5px; padding: 5px; }}")
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
        Clears all data buffers for each channel.
        """
        self.data_buffer = [deque(maxlen=self.bufferSize) for _ in range(self.channels)]

    def handle_data(self, data_list: List[int]) -> None:
        """
        Handles incoming data emitted by the SerialWorker. Appends data to buffers and manages
        single capture logic.

        Args:
            data_list (List[int]): List of incoming data values.
        """
        if self.is_reading:
            for data_value in data_list:
                for i in range(self.channels):
                    bit_value = (data_value >> i) & 1
                    self.data_buffer[i].append(bit_value)
            if self.is_single_capture and all(len(buf) >= self.bufferSize for buf in self.data_buffer):
                self.stop_single_capture()

    def update_plot(self) -> None:
        """
        Updates the graphical plot with the latest data from the buffers.
        """
        for i in range(self.channels):
            if self.channel_visibility[i]:
                inverted_index = self.channels - i - 1
                num_samples = len(self.data_buffer[i])
                if num_samples > 1:
                    t = np.arange(num_samples) / self.sample_rate
                    square_wave_time = []
                    square_wave_data = []
                    for j in range(1, num_samples):
                        square_wave_time.extend([t[j-1], t[j]])
                        level = self.data_buffer[i][j-1] + inverted_index * 2
                        square_wave_data.extend([level, level])
                        if self.data_buffer[i][j] != self.data_buffer[i][j-1]:
                            square_wave_time.append(t[j])
                            level = self.data_buffer[i][j] + inverted_index * 2
                            square_wave_data.append(level)
                    self.curves[i].setData(square_wave_time, square_wave_data)

    def update_cursor_position(self) -> None:
        """
        Updates the position and label of the cursor on the plot based on user interaction.
        """
        cursor_pos = self.cursor.pos().x()
        self.cursor_label.setText(f"Cursor: {cursor_pos:.6f} s")
        self.cursor_label.setPos(cursor_pos, self.channels * 2 - 1)

    def closeEvent(self, event: QtCore.QEvent) -> None:
        """
        Handles the close event of the SignalDisplay widget. Ensures that the worker thread is
        properly stopped before closing.

        Args:
            event (Qt.QEvent): The close event triggered when the widget is being closed.
        """
        self.worker.stop_worker()
        self.worker.quit()
        self.worker.wait()
        event.accept()
