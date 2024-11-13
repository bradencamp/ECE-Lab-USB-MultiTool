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

#arbitrary number used in update_plot to check which checkbox is checked, initialize to 0
awgChecked = 0

runStopClicked = 0#holds state of runStopButton
oscChecked = 0#holds state of scope checkbox
oscCHChecked = 0#holds state of scope channel checkboxes

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
        self.ch1En = QCheckBox("Channel 1",self)
        self.ch2En = QCheckBox("Channel 2",self)
        #initially set ch1 & ch2 checkboxes to selected/on
        self.ch1En.setChecked(True)
        self.ch2En.setChecked(True)
        awgLayout.addWidget(self.ch1En,0,0)
        awgLayout.addWidget(self.ch2En,1,0)
        #connect stateChanged signals for awg ch1 & ch2 from QCheckBox to awgChStateChanged method/slot
        self.ch1En.stateChanged.connect(self.awgChStateChanged)
        self.ch2En.stateChanged.connect(self.awgChStateChanged)

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
        self.runStopButton = QPushButton("RUN/STOP", self)
        self.runStopButton.setCheckable(True)
        self.runStopButton.setChecked(False)
        self.runStopButton.clicked.connect(self.button_was_clicked)
        singleButton = QPushButton("SINGLE")
        dataButton = QPushButton("RECORD DATA")

        centerSettings = QGridLayout()
        timeSetting = ColorBox("aqua")
        centerSettings.addWidget(timeSetting,0,0,1,1)
        centerSettings.addWidget(QLabel("Time s/div"),0,0,1,1)

        centerSettings.addWidget(QLabel("Trigger Settings: "),0,1,1,1)

        trigTypeSelect = QComboBox()
        mode = ["Auto","Normal", "None"]
        #trigTypeSelect.addItem("Trigger Types")
        trigTypeSelect.setPlaceholderText('Trigger Mode')
        trigTypeSelect.addItems(mode)
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
        
        edges = ["Rising Edge","Falling Edge", "None"]
        self.logic_checks = [None,]*8
        self.logic_edges = [None]*8
        for i in range(0,8):
            pos = i+1
            self.logic_checks[i] = QCheckBox(f"Channel {pos}")
            self.logic_edges[i] = QComboBox()
            self.logic_edges[i].setPlaceholderText('Trigger Type')
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
        self.pen2 = pg.mkPen(color=(0, 0, 255), width=5, style=Qt.PenStyle.DotLine)

        self.time = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        self.temperature = [uniform(-5, 5) for _ in range(10)]
        self.zeros = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0]#array of 0's for when no channel checkbox selected
        self.plot_graph.setLabel("left", "Voltage (V)")
        self.plot_graph.setLabel("bottom", "Time (s)",)
        self.plot_graph.setYRange(-5, 5)
        self.ch1Line = self.plot_graph.plot(self.time, self.temperature,pen = self.pen1)
        self.ch2Line = self.plot_graph.plot(self.time, self.temperature,pen = self.pen2)

        dataLayout.addWidget(self.plot_graph,1,1)


        oscilloLayout = QGridLayout()
        oscilloLayout.addWidget(ColorBox("Olive"),0,0,-1,-1)#background for demonstration. Remove later
        self.oscilloCheck = QCheckBox()#QLabel("Logic Analyzer",alignment = Qt.AlignmentFlag.AlignTop)#QCheckBox("Logic Analyzer")
        self.oscilloCheck.setChecked(True)#default scope checkbox checked -> scope on
        self.oscilloCheck.stateChanged.connect(self.oscStateChanged)#method/slot for checking scope checkbox state
        oscilloLayout.addWidget(self.oscilloCheck,0,0)
        oscilloLayout.addWidget(QLabel("Oscilloscope"),0,1,alignment = Qt.AlignmentFlag.AlignHCenter)
        
        self.oscCh1EN = QCheckBox("CH1")
        #initially set scope ch1 checkbox to selected/on
        self.oscCh1EN.setChecked(True)
        #connect stateChanged signal for scope ch1 from QCheckBox to onStateChanged method/slot
        self.oscCh1EN.stateChanged.connect(self.oscChStateChanged)
        self.oscCh1Trig = QComboBox()
        self.oscCh1Trig.setPlaceholderText('Trigger Type')
        self.oscCh1Trig.addItems(edges)
        self.oscCh1VDiv = LabelField("Range",[1e-6,20],1.0,2,"V/Div",{"u":1e-6,"m":1e-3,"":1},BLANK)

        self.oscCh2EN = QCheckBox("CH2")
        self.oscCh2Trig = QComboBox()
        self.oscCh2EN.setChecked(True)#initially set scope ch2 checkbox to selected/on
        #connect stateChanged signal for scope ch2 from QCheckBox to onStateChanged method/slot
        self.oscCh2EN.stateChanged.connect(self.oscChStateChanged)
        self.oscCh2Trig.setPlaceholderText('Trigger Type')
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

        centerLayout.addWidget(self.runStopButton,0,0)
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

    def button_was_clicked(self):#checks if runStopButton was clicked/unclicked
        if self.runStopButton.isChecked():#runStopButton clicked to run
            self.runStopButton.setChecked(True)#set button clicked
            runStopClicked = 1
        else:#runStopButton unclicked to stop
            self.runStopButton.setChecked(False)#set button unclicked
            runStopClicked = 0
        return runStopClicked

    def oscStateChanged(self):#tracks state of oscilloscope checkbox 
        if self.oscilloCheck.isChecked():
            oscChecked = 1#scope on
        else:
            oscChecked = 0#scope off
        return oscChecked#return scope checkbox state

    def awgChStateChanged(self):#tracks state of awg ch1 & ch2 checkboxes
        #only ch1 awg checkbox selected
        if self.ch1En.isChecked() and not self.ch2En.isChecked():
            awgChecked = 1
        #only ch2 awg checkbox selected
        elif not self.ch1En.isChecked() and self.ch2En.isChecked():
            awgChecked = 2
        #both ch1 & ch2 awg checkbox selected
        elif self.ch1En.isChecked() and self.ch2En.isChecked():
            awgChecked = 3
        #no awg checkbox selected
        else:
            awgChecked = 0
        return awgChecked#return which checkbox is checked
    
    def oscChStateChanged(self):#tracks state of osc ch1 & ch2 checkboxes
        #only ch1 scope checkbox selected
        if self.oscCh1EN.isChecked() and not self.oscCh2EN.isChecked():
            self.oscCh1EN.setChecked(True)
            self.oscCh2EN.setChecked(False)
            oscCHChecked = 1
        #only ch2 scope checkbox selected
        elif not self.oscCh1EN.isChecked() and self.oscCh2EN.isChecked():
            self.oscCh1EN.setChecked(False)
            self.oscCh2EN.setChecked(True)
            oscCHChecked = 2
        #both ch1 & ch2 scope checkbox selected
        elif self.oscCh1EN.isChecked() and self.oscCh2EN.isChecked():
            self.oscCh1EN.setChecked(True)
            self.oscCh2EN.setChecked(True)
            oscCHChecked = 3
        #no scope checkbox selected
        else:
            self.oscCh1EN.setChecked(False)
            self.oscCh2EN.setChecked(False)
            oscCHChecked = 0
        return oscCHChecked#return which scope checkbox is checked
   
    def plotCh1(self):#plot ch1 data
        self.ch1Line.setData(self.time, self.temperature)#plot ch1 data
        self.ch2Line.setData(self.zeros, self.zeros)#plot zeros for ch2, works for now

    def plotCh2(self):#plot ch2 data
        self.ch1Line.setData(self.zeros, self.zeros)
        self.ch2Line.setData(self.time, self.temperature)

    def plotCh12(self):#plot ch1 & ch2 data
        self.ch1Line.setData(self.time, self.temperature) 
        self.ch2Line.setData(self.time, self.temperature)
    
    def plotZero(self):#no plotting
        self.ch1Line.setData(self.zeros, self.zeros)
        self.ch2Line.setData(self.zeros, self.zeros)

    def update_plot(self):
        self.time = self.time[1:]
        self.time.append(self.time[-1] + 1)
        self.temperature = self.temperature[1:]
        self.temperature.append(uniform(-5, 5))   
        #awgChecked=1 run/stop button clicked, oscChecked=1, 
        if self.awgChStateChanged() == 1 and self.button_was_clicked() and self.oscStateChanged():
            self.plotCh1()#plot only ch1
        #awgChecked=2 run/stop button clicked, oscChecked=1, 
        elif self.awgChStateChanged() == 2 and self.button_was_clicked() and self.oscStateChanged():
            self.plotCh2()#plot only ch2
        #awgChecked=3 run/stop button clicked, oscChecked=1, 
        elif self.awgChStateChanged() == 3 and self.button_was_clicked() and self.oscStateChanged():
            self.plotCh12()#plot both ch1 & ch2
        #awgChecked=0 run/stop button clicked, oscChecked=1, 
        else:#don't plot anything
            self.plotZero()

app = QApplication(sys.argv)

window = MainWindow()
window.show()

app.exec()
#test