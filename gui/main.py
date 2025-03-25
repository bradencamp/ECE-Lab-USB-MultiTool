import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget,QGridLayout,QPushButton,QLabel,QCheckBox,QComboBox    
from PyQt6.QtGui import QPalette, QColor, QPen
from PyQt6.QtCore import Qt, QTimer
import pyqtgraph as pg
from labeled_field import LabelField 
from random import uniform
#html standard colors
colors = ["Yellow","Teal","Silver","Red","Purple","Olive","Navy","White",
            "Maroon","Lime","Green","Gray","Fuchsia","Blue","Black","Aqua"]

MAXFREQUENCY = 250e3
MINFREQUENCY = 1
MINAMP = -5
MAXAMP = 5
MINOFF = -10
MAXOFF = 10

#because of a change made to input field, we need to specify a "" unit
prefixes_voltage = {"m": 1e-3,"":1}
prefixes_frequency = {"k": 1e3, "M": 1e6,"":1}

class ColorBox(QWidget):

    def __init__(self, color):
        super(ColorBox, self).__init__()
        self.setAutoFillBackground(True)

        palette = self.palette()
        palette.setColor(QPalette.ColorRole.Window, QColor(color))
        self.setPalette(palette)
#placeholder until other callbacks are written
def BLANK():
    return
class MainWindow(QMainWindow):
    
    def __init__(self):
        super(MainWindow, self).__init__()

        self.setWindowTitle("My App")

        #layout for awg section
        awgLayout = self.awgLayoutSetup()


        #layout for window containing oscilloscope, wave, and logic analyizer
        centerLayout = self.centerLayoutSetup()
        

        #layout for device control
        deviceLayout = self.deviceLayoutSetup()


        #overall layout
        layout = QGridLayout()
        layout.addLayout(awgLayout, 0, 0, 2, -1)#for awg
        layout.addLayout(centerLayout, 2, 0, 7,-1) #for center block
        layout.addLayout(deviceLayout, 9, 0,1,-1) #for connect/disconect


        self.timer = QTimer()
        self.timer.setInterval(300)
        self.timer.timeout.connect(self.update_plot)
        self.timer.start()


        widget = QWidget()
        widget.setLayout(layout)
        self.setCentralWidget(widget)
        #self.resize(400,500)

        
    def awgLayoutSetup(self):
        awgLayout = QGridLayout()
        awgLayout.addWidget(ColorBox(colors[0]),0,0, -1,-1)#background for demonstration. Remove later
        #enable channel
            #to be able to use these outside of init, we'll need to prepend self as in "self.ch1En"
        ch1En = QCheckBox("Channel 1")
        ch2En = QCheckBox("Channel 2")
        awgLayout.addWidget(ch1En,0,0)
        awgLayout.addWidget(ch2En,1,0)

        #wave types available
        waves = ["Sine","Square","Triangle","Sawtooth","Abritrary"]
        ch1WaveSelect = QComboBox()
        ch2WaveSelect = QComboBox() 
        ch1WaveSelect.addItems(waves)
        ch2WaveSelect.addItems(waves)
        awgLayout.addWidget(ch1WaveSelect,0,1)
        awgLayout.addWidget(ch2WaveSelect,1,1)


        #AWG frequencies
        ch1Freq = LabelField("Frequency:",[MINFREQUENCY, MAXFREQUENCY],float(5), 3,"Hz", prefixes_frequency,BLANK)
        awgLayout.addWidget(ch1Freq,0,2)
        ch2Freq = LabelField("Frequency:",[MINFREQUENCY, MAXFREQUENCY],float(1000),3, "Hz", prefixes_frequency,BLANK)
        awgLayout.addWidget(ch2Freq,1,2)
            
        #AWG amplitueds
        ch1Amp = LabelField("Amplitude:",[MINAMP,MAXAMP],float(5),2,"V", prefixes_voltage,BLANK)#ColorBox(colors[3])
        awgLayout.addWidget(ch1Amp,0,3)
        ch2Amp = LabelField("Amplitude:",[MINAMP,MAXAMP],float(5),2,"V", prefixes_voltage,BLANK)#ColorBox(colors[4])
        awgLayout.addWidget(ch2Amp,1,3)

        #AWG offsets
        ch1Off = LabelField("Offset:" ,[MINAMP, MAXAMP],float(5),2,"V", prefixes_voltage,BLANK)#ColorBox(colors[5])
        awgLayout.addWidget(ch1Off,0,4)
        #awgLayout.addWidget(QLabel("Offset (V):"),0,4)
        ch2Off = LabelField("Offset:" ,[MINAMP, MAXAMP],float(5),2,"V", prefixes_voltage,BLANK)#ColorBox(colors[7])#6 doesn't play nice with black text
        awgLayout.addWidget(ch2Off,1,4)        
        #awgLayout.addWidget(QLabel("Offset (V):"),1,4)

        awgPhase = LabelField("Phase:" ,[0, 180],float(0),2,"°", {"":1},BLANK)##ColorBox(colors[8])
        awgLayout.addWidget(awgPhase,0,5)

        # awgLayout.addWidget(QLabel("Phase (°):"),0,5)
        awgLayout.addWidget(QLabel("Sync Status:"),1,5)

        syncButton = QPushButton("FORCE SYNC")
        buttonPalette = syncButton.palette()
        buttonPalette.setColor(QPalette.ColorRole.ButtonText, QColor("red"))
        syncButton.setPalette(buttonPalette)
        awgLayout.addWidget(syncButton,1,6)
        awgLayout.addWidget(QLabel("Waveform Generator"),0,6)

        return awgLayout
    

    def centerLayoutSetup(self):
        centerLayout = QGridLayout()
        centerLayout.addWidget(ColorBox(colors[1]),0,0, -1,-1)#background for demonstration. Remove later
        runStopButton = QPushButton("RUN/STOP")
        singleButton = QPushButton("SINGLE")
        dataButton = QPushButton("RECORD DATA")

        centerSettings = QGridLayout()
        timeSetting = ColorBox("aqua")
        centerSettings.addWidget(timeSetting,0,0,1,1)
        centerSettings.addWidget(QLabel("Time s/div"),0,0,1,1)

        centerSettings.addWidget(QLabel("Trigger Settings: "),0,1,1,1)

        trigTypeSelect = QComboBox()
        trigTypeSelect.addItem("Trigger Types")
        trigHoldoffSelect = QComboBox()
        trigHoldoffSelect.addItem("Holdoff (s)")

        centerSettings.addWidget(trigTypeSelect,0,2)
        centerSettings.addWidget(trigHoldoffSelect,0,3)

        logicLayout = QGridLayout()
        logicLayout.addWidget(ColorBox("Fuchsia"),0,0,-1,-1)#background for demonstration. Remove later
        logicCheck = QCheckBox()#QLabel("Logic Analyzer",alignment = Qt.AlignmentFlag.AlignTop)#QCheckBox("Logic Analyzer")
        logicLayout.addWidget(logicCheck,0,0)
        logicLayout.addWidget(QLabel("Logic Analyzer"),0,1,alignment = Qt.AlignmentFlag.AlignHCenter)
        #logicChannelLayout = QGridLayout()
        
        edges = ["Rising Edge","Falling Edge"]
        self.logic_checks = [None,]*8
        self.logic_edges = [None]*8
        for i in range(0,8):
            pos = i+1
            self.logic_checks[i] = QCheckBox(f"Channel {pos}")
            self.logic_edges[i] = QComboBox()
            self.logic_edges[i].addItems(edges)
            logicLayout.addWidget(self.logic_checks[i],i+1,0)
            logicLayout.addWidget(self.logic_edges[i],i+1,1)
        #logicLayout.addLayout(logicChannelLayout,1,0,-1,-1)
        logicLayout.setColumnStretch(0,1)
        logicLayout.setColumnStretch(1,4)

        

        dataLayout = QGridLayout()
        dataLayout.addWidget(ColorBox("lime"),0,0,-1,-1)#background for demonstration. Remove later
        dataLayout.addWidget(QLabel("Live Data"),0,1,alignment=Qt.AlignmentFlag.AlignHCenter)
        #maybe make a custom plotwidget, this will work for now
        self.plot_graph = pg.PlotWidget()
        self.plot_graph.setBackground("w")


        self.pen1 = pg.mkPen(color=(255, 0, 0), width=5, style=Qt.PenStyle.DashLine)

        self.time = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        self.temperature = [uniform(-5, 5) for _ in range(10)]
        self.plot_graph.setLabel("left", "Voltage (V)")
        self.plot_graph.setLabel("bottom", "Time (s)",)
        self.line = self.plot_graph.plot(self.time, self.temperature,pen = self.pen1)
        dataLayout.addWidget(self.plot_graph,1,1)
        

        oscilloLayout = QGridLayout()
        oscilloLayout.addWidget(ColorBox("Olive"),0,0,-1,-1)#background for demonstration. Remove later
        oscilloCheck = QCheckBox()#QLabel("Logic Analyzer",alignment = Qt.AlignmentFlag.AlignTop)#QCheckBox("Logic Analyzer")
        oscilloLayout.addWidget(oscilloCheck,0,0)
        oscilloLayout.addWidget(QLabel("Oscilloscope"),0,1,alignment = Qt.AlignmentFlag.AlignHCenter)
        
        self.oscCh1EN = QCheckBox("CH1")
        self.oscCh1Trig = QComboBox()
        self.oscCh1Trig.addItems(edges)
        self.oscCh1VDiv = LabelField("Range",[1e-6,20],1.0,2,"V/Div",{"u":1e-6,"m":1e-3,"":1},BLANK)

        self.oscCh2EN = QCheckBox("CH2")
        self.oscCh2Trig = QComboBox()
        self.oscCh2Trig.addItems(edges)
        self.oscCh2VDiv = LabelField("Range",[1e-6,20],1.0,2,"V/Div",{"u":1e-6,"m":1e-3,"":1},BLANK)
        
        oscilloLayout.addWidget(self.oscCh1EN,1,0,2,1)
        oscilloLayout.addWidget(self.oscCh1VDiv,1,1)
        oscilloLayout.addWidget(self.oscCh1Trig,2,1)

        oscilloLayout.addWidget(self.oscCh2EN,3,0,2,1)
        oscilloLayout.addWidget(self.oscCh2VDiv,3,1)
        oscilloLayout.addWidget(self.oscCh2Trig,4,1)

        centerLayout.addLayout(logicLayout,1,0,6,3)
        centerLayout.addLayout(dataLayout,1,3,6,4)
        centerLayout.addLayout(oscilloLayout,1,7,6,3)

        centerLayout.addLayout(centerSettings,0,3,1,6)

        centerLayout.addWidget(runStopButton,0,0)
        centerLayout.addWidget(singleButton,0,1)
        centerLayout.addWidget(dataButton,0,2)
        centerLayout.addWidget(QLabel("Live Data"),0,9)

        return centerLayout

    def deviceLayoutSetup(self):
        deviceLayout = QGridLayout()
        deviceLayout.addWidget(ColorBox(colors[2]),0,0, -1,-1)#background for demonstration. Remove later
        deviceLayout.addWidget(QLabel("Device Status"), 0,0,1,1)
        #specific colored buttons
        connectButton = QPushButton("CONNECT")
        buttonPalette = connectButton.palette()
        
        buttonPalette.setColor(QPalette.ColorRole.Button, QColor("green"))
        buttonPalette.setColor(QPalette.ColorRole.ButtonText, QColor("white"))
        connectButton.setPalette(buttonPalette)

        buttonPalette.setColor(QPalette.ColorRole.Button, QColor("red"))

        disconnectButton = QPushButton("DISCONNECT")
        disconnectButton.setPalette(buttonPalette)



        deviceLayout.addWidget(connectButton,0,1,1,1)
        deviceLayout.addWidget(disconnectButton,0,2,1,1)
        deviceLayout.addWidget(QPushButton("Wave Drawer"),1,0,1,1)
        #Section for button spacing. Will require fine tuning to look as we want it
        deviceLayout.setColumnStretch(3,2) 
        deviceLayout.setColumnStretch(2,1) 
        deviceLayout.setColumnStretch(1,1) 
        deviceLayout.setColumnStretch(0,1) 

        return deviceLayout

    def update_plot(self):
        self.time = self.time[1:]
        self.time.append(self.time[-1] + 1)
        self.temperature = self.temperature[1:]
        self.temperature.append(uniform(-5, 5))
        self.line.setData(self.time, self.temperature)
app = QApplication(sys.argv)

window = MainWindow()
window.show()

app.exec()