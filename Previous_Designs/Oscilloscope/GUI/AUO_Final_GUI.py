import sys
import serial
from PyQt5.QtWidgets import QApplication, QMainWindow, QGridLayout, QLabel, QWidget, QPushButton, QDoubleSpinBox, QComboBox
import pyqtgraph as pg
import numpy as np
import time # This is for "testing" the speed of plotting

class SerialReader(QMainWindow):
    def __init__(self, port, baudrate):
        super().__init__()
        self.port = port
        self.baudrate = baudrate
        self.serial = serial.Serial(port, baudrate)
        self.data = []
        self.timer = pg.QtCore.QTimer()
        self.timer.timeout.connect(self.update)
        self.setup_ui()
        self.is_reading = False
        self.attenuator_data = 0
        self.ad_dc_data = 0
        self.amplifier_data = 0
        self.samplingtime_data = 0
        self.adcclock_data = 0
        self.max = 0
        self.min = 10

    def setup_ui(self):
        self.setWindowTitle("AUO - Affordable USB Oscilloscope")
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        grid_layout = QGridLayout(central_widget)

        self.plot_widget = pg.PlotWidget()
        self.plot_widget.showGrid(x=True, y=True)  # Add this line to show the grid
        grid_layout.addWidget(self.plot_widget, 1, 0)

        # Add QComboBox for Voltages/Div function
        self.voltage_combo = QComboBox()
        self.voltage_combo.addItems(['5V/Div', '2V/Div', '1V/Div', '0.5V/Div', '0.2V/Div'])
        self.voltage_combo.currentTextChanged.connect(self.update_y_range)
        grid_layout.addWidget(QLabel("Voltages/Div"), 2, 0)
        grid_layout.addWidget(self.voltage_combo, 3, 0)

        # Add QComboBox for Time/Div function
        self.time_combo = QComboBox()
        self.time_combo.addItems(['2ms/Div','1ms/Div', '0.5ms/Div', '0.2ms/Div', '0.1ms/Div'])
        self.time_combo.currentIndexChanged.connect(self.update_x_range)
        grid_layout.addWidget(QLabel("Time/Div"), 4, 0)
        grid_layout.addWidget(self.time_combo, 5, 0)

        # Add QDoubleSpinBox for DC Offset function
        self.offset_spinbox = QDoubleSpinBox()
        self.offset_spinbox.setRange(-10, 10)
        self.offset_spinbox.setSingleStep(0.1)
        self.offset_spinbox.setValue(0.0)
        grid_layout.addWidget(QLabel("DC Offset"), 6, 0)
        grid_layout.addWidget(self.offset_spinbox, 7, 0)

        # Add QPushButton for Run function
        self.start_button = QPushButton("Run")
        self.start_button.clicked.connect(self.start_reading)
        grid_layout.addWidget(self.start_button, 8, 0)

        # Add QPushButton for Stop function
        self.stop_button = QPushButton("Stop")
        self.stop_button.clicked.connect(self.stop_reading)
        grid_layout.addWidget(self.stop_button, 8, 1)

        # Set up the data buffer
        self.data_buffer = []
        # Create a curve object for plotting
        self.curve = self.plot_widget.plot(pen=pg.mkPen(color='g'))
        
        # Add cursor to plot widget
        self.cursor = pg.LinearRegionItem(values = [0, 0], orientation = pg.LinearRegionItem.Vertical)
        self.cursor.setRegion([0, 0])
        self.plot_widget.addItem(self.cursor)

        # Add horizontal line to plot widget
        self.hline = pg.InfiniteLine(pos = 0, angle = 0, movable=False)
        self.plot_widget.addItem(self.hline)

        # Add vertical line to plot widget
        self.vline = pg.InfiniteLine(pos = 0, angle = 90, movable=False)
        self.plot_widget.addItem(self.vline)
        
        # Set pen color to red
        pen = pg.mkPen(color='r')
        self.hline.setPen(pen)
        self.vline.setPen(pen)

        # Connect the scene's sigMouseMoved signal to the update_cursor_labels method
        self.plot_widget.getViewBox().scene().sigMouseMoved.connect(self.update_cursor_labels)

        # Add cursor position labels
        self.cursor_x_label = QLabel()
        self.cursor_y_label = QLabel()
        grid_layout.addWidget(QLabel("Cursor X"), 10, 0)
        grid_layout.addWidget(self.cursor_x_label, 11, 0)
        grid_layout.addWidget(QLabel("Cursor Y"), 12, 0)
        grid_layout.addWidget(self.cursor_y_label, 13, 0)
        
        self.update_y_range()  # Set initial y range based on the default voltage value
        self.update_x_range()  # Set initial x range based on the default time value
        self.plot_data()  # Plot the initial data
        
        # Add QPushButton for Single function
        self.single_button = QPushButton("Single")
        self.single_button.clicked.connect(self.plot_200_points)
        grid_layout.addWidget(self.single_button, 9, 0)     

        # Add QComboBox for Attenuator function
        self.attenuator_combo = QComboBox()
        self.attenuator_combo.addItems(['1.25', '12.5'])
        self.attenuator_combo.currentTextChanged.connect(self.send_attenuator_data)
        grid_layout.addWidget(QLabel("Attenuator"), 2, 1)
        grid_layout.addWidget(self.attenuator_combo, 3, 1)
        
        # Add QComboBox for AD/DC function
        self.ad_dc_combo = QComboBox()
        self.ad_dc_combo.addItems(['DC', 'AC'])
        self.ad_dc_combo.currentTextChanged.connect(self.send_ad_dc_data)
        grid_layout.addWidget(QLabel("AD/DC"), 4, 1)
        grid_layout.addWidget(self.ad_dc_combo, 5, 1)

        # Add QComboBox for Amplifier function
        self.amplifier_combo = QComboBox()
        self.amplifier_combo.addItems(['10', '5', '2.5', '1'])
        self.amplifier_combo.currentTextChanged.connect(self.send_amplifier_data)
        grid_layout.addWidget(QLabel("Amplifier"), 6, 1)
        grid_layout.addWidget(self.amplifier_combo, 7, 1)
        
        # Add QComboBox for Sampling time function
        self.samplingtime_combo = QComboBox()
        self.samplingtime_combo.addItems(['1.5', '2.5', '4.5', '7.5', '19.5', '61.5', '601.5'])
        self.samplingtime_combo.currentTextChanged.connect(self.send_samplingtime_data)
        grid_layout.addWidget(QLabel("Sampling Time"), 10, 1)
        grid_layout.addWidget(self.samplingtime_combo, 11, 1)
        
        # Add QComboBox for ADC Clock function
        self.adcclock_combo = QComboBox()
        self.adcclock_combo.addItems(['72', '36', '18', '12', '9', '7.2', '6', '4.5', '2.25', '1.125', '0.5625', '0.28125'])
        self.adcclock_combo.currentTextChanged.connect(self.send_adcclock_data)
        grid_layout.addWidget(QLabel("ADC Clock (MHz)"), 12, 1)
        grid_layout.addWidget(self.adcclock_combo, 13, 1)
        
    def send_data_to_board(self):
        match self.amplifier_data:
            case 0:
                amplifier = "1000"
            case 1:
                amplifier = "0100"
            case 2:
                amplifier = "0010"
            case 3:
                amplifier = "0001"
            case _:
                raise ValueError("Invalid amplifier data value!")
        pwmstring = '0000'
        send = f'1{self.samplingtime_data}{self.adcclock_data:02}{pwmstring}{self.attenuator_data}{self.ad_dc_data}{amplifier}'
        print(f"send: {send}")
        self.serial.write(send.encode())
        
    def send_attenuator_data(self, text):
        if text == '1.25':
            self.attenuator_data = 0
        elif text == '12.5':
            self.attenuator_data = 1

    def send_ad_dc_data(self, text):
        if text == 'DC':
            self.ad_dc_data = 0
        elif text == 'AC':
            self.ad_dc_data = 1

    def send_amplifier_data(self, text):
        match text:
            case '10':
                self.amplifier_data = 0
            case '5':
                self.amplifier_data = 1
            case '2.5':
                self.amplifier_data = 2
            case '1':
                self.amplifier_data = 3
          
    def send_samplingtime_data(self, text):
        match text:
            case '1.5':
                self.samplingtime_data = 0
            case '2.5':
                self.samplingtime_data = 1
            case '4.5':
                self.samplingtime_data = 2
            case '7.5':
                self.samplingtime_data = 3
            case '19.5':
                self.samplingtime_data = 4
            case '61.5':
                self.samplingtime_data = 5
            case '181.5':
                self.samplingtime_data = 6
            case '601.5':
                self.samplingtime_data = 7

    def send_adcclock_data(self, text):
        match text:
            case '72':
                self.adcclock_data = 0
            case '36':
                self.adcclock_data = 1
            case '18':
                self.adcclock_data = 2
            case '12':
                self.adcclock_data = 3
            case '9':
                self.adcclock_data = 4
            case '7.2':
                self.adcclock_data = 5
            case '6':
                self.adcclock_data = 6
            case '4.5':
                self.adcclock_data = 7
            case '2.25':
                self.adcclock_data = 8
            case '1.125':
                self.adcclock_data = 9
            case '0.5625':
                self.adcclock_data = 10
            case '0.28125':
                self.adcclock_data = 11
            
    def plot_300_points(self):
        start_time = time.time()  # Record the start time
        self.send_data_to_board()
        self.stop_reading()  # Stop the timer to avoid interference with the data collection
        self.data = []  # Reset the data buffer
        while len(self.data) < 300:
            line = self.serial.readline().decode().strip()
            try:
                value = float(line) * 3.3 / 4096  # scale a voltage value between 0 and 3.3 volts.
                value += self.offset_spinbox.value()  # add DC offset
                #--------------invert to original voltage------------
                x = 1.25 if self.attenuator_data == 0 else 12.5

                match self.amplifier_data:
                    case 0:
                        y = 10
                    case 1:
                        y = 5
                    case 2:
                        y = 2.5
                    case _:
                        y = 1

                value = (value * x) / y
                if value > self.max:
                    self.max = value
                    print("max: ", self.max)
                if value < self.min:
                    self.min = value
                    print("min: ", self.min)
                average = (self.min + self.max)/2
                value -= average
                self.data.append(value)
            except ValueError:
                pass
        t = np.linspace(-0.008, 0.008, len(self.data))
        self.curve.setData(t, self.data)
        end_time = time.time()  # Record the end time
        elapsed_time = end_time - start_time  # Calculate the elapsed time
        print(f"Elapsed time: {elapsed_time:.2f} seconds")

    def start_reading(self):
        self.send_data_to_board()
        self.is_reading = True
        self.timer.start(1)

    def stop_reading(self):
        self.is_reading = False
        self.timer.stop()  # Stop the timer

    def update(self):
        line = self.serial.readline().decode().strip()
        try:
            value = float(line) * 3.3 / 4096  # scale a voltage value between 0 and 3.3 volts.
            value += self.offset_spinbox.value()  # add DC offset
            #--------------invert to original voltage------------
            x = 1.25 if self.attenuator_data == 0 else 12.5

            match self.amplifier_data:
                case 0:
                    y = 10
                case 1:
                    y = 5
                case 2:
                    y = 2.5
                case _:
                    y = 1

            value = (value * x) / y
            if value > self.max:
                self.max = value
                print("max: ", self.max)
            if value < self.min:
                self.min = value
                print("min: ", self.min)
            average = (self.min + self.max)/2
            value -= average
            self.data_buffer.append(value)
            if len(self.data_buffer) >= 300:
                self.plot_data()
        except ValueError:
            pass

    def plot_data(self):
        # Set the x-axis range based on the time combo selection
        time_range = self.time_combo.currentText()

        match time_range:
            case '2ms/Div':
                x_range = 0.008
            case '1ms/Div':
                x_range = 0.005
            case '0.5ms/Div':
                x_range = 0.0025
            case '0.2ms/Div':
                x_range = 0.001
            case '0.1ms/Div':
                x_range = 0.0005

        t = np.linspace(-x_range, x_range, len(self.data_buffer))
        # Set the x-axis to be the time array
        self.curve.setData(t, self.data_buffer)
        self.data_buffer = []
        
    def update_y_range(self):
        voltage_range = self.voltage_combo.currentText()

        match voltage_range:
            case '5V/Div':
                self.plot_widget.setYRange(-25, 25)
            case '2V/Div':
                self.plot_widget.setYRange(-10, 10)
            case '1V/Div':
                self.plot_widget.setYRange(-5, 5)
            case '0.5V/Div':
                self.plot_widget.setYRange(-2.5, 2.5)
            case '0.2V/Div':
                self.plot_widget.setYRange(-1, 1)

    def update_x_range(self):
        time_range = self.time_combo.currentText()
        match time_range:
            case '2ms/Div':
                self.plot_widget.setXRange(-0.008, 0.008)
            case '1ms/Div':
                self.plot_widget.setXRange(-0.005, 0.005)
            case '0.5ms/Div':
                self.plot_widget.setXRange(-0.0025, 0.0025)
            case '0.2ms/Div':
                self.plot_widget.setXRange(-0.001, 0.001)
            case '0.1ms/Div':
                self.plot_widget.setXRange(-0.0005, 0.0005)

    def update_cursor_labels(self, evt):
        mouse_point = self.plot_widget.getViewBox().mapSceneToView(evt)
        self.cursor_x_label.setText(f"{mouse_point.x():.3f}")
        self.cursor_y_label.setText(f"{mouse_point.y():.3f}")

        # Update the position of the horizontal and vertical lines of the cursor 
        self.hline.setPos(mouse_point.y())
        self.vline.setPos(mouse_point.x())

        # Update the position of the cursor
        cursor_pos = self.cursor.getRegion()
        cursor_pos = (mouse_point.x(), mouse_point.x())
        self.cursor.setRegion(cursor_pos)

    def on_attenuator_changed(self, text):
        send_attenuator_data(self, text)
        self.serial.write(str(self.attenuator_data).encode())

    def on_ad_dc_changed(self, text):
        if text == 'DC':
            self.ad_dc_data = 0
        elif text == 'No DC': # should this be AC?
            self.ad_dc_data = 1
        self.serial.write(str(self.ad_dc_data).encode())

    def on_amplifier_changed(self, text):
        send_amplifier_data(self, text)
        self.serial.write(str(self.amplifier_data).encode())

if __name__ == "__main__":
    app = QApplication(sys.argv)
    reader = SerialReader(port='COM7', baudrate=12000000)
    reader.show()
    sys.exit(app.exec_())
