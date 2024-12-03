import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget,QGridLayout,QPushButton,QLabel,QCheckBox,QComboBox    
from PyQt6.QtGui import QPalette, QColor, QPen
from PyQt6.QtCore import Qt, QTimer
import pyqtgraph as pg
from labeled_field import LabelField 
import numpy as np

import numpy as np

from random import uniform
from math import isclose,pi, tau
#html standard colors
colors = ["Yellow","Teal","Silver","Red","Purple","Olive","Navy","White",
            "Maroon","Lime","Green","Gray","Fuchsia","Blue","Black","Aqua"]

MAXFREQUENCY = 250e3
MINFREQUENCY = 1
MINAMP = -5
MAXAMP = 5
MINOFF = -10
MAXOFF = 10
NUMPOINTS = 300
NUMDIVS = 10 #based on default we've worked with thus far, scopy uses ~16
NUMPOINTS = 300
NUMDIVS = 10 #based on default we've worked with thus far, scopy uses ~16

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
        self.awgCh1Config = dict(amp=5, off=0,freq = 1,phase = 0, wave = 0, DC = 0.5)  # Dictionary with initial values
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
        self.sampRes = 0
        self.awgPen = pg.mkPen(color=(0, 0, 255), width=5, style=Qt.PenStyle.SolidLine)
        self.awgTime = np.linspace(0,10,NUMPOINTS)
        self.awgData = 5*np.sin(2*pi*self.awgTime)
        
        self.awgLine = self.plot_graph.plot(self.time, self.awgData,pen = self.awgPen)
        self.set_time_div(1.0)
        widget = QWidget()
        widget.setLayout(layout)
        self.setCentralWidget(widget)
        

    def set_awgCh1Amp(self, amp):
        print("new Amp: ", amp)
        self.awgCh1Config["amp"] = amp

    def set_awgCh1Off(self,off):
        print("new Off: ", off)
        self.awgCh1Config["off"] = off

    def set_awgCh1Freq(self,freq):
        print("new Freq: ", freq)
        self.awgCh1Config["freq"] = freq

    def set_awgPhase(self, phase):
        print("new Phase: ", phase)
        self.awgCh1Config["phase"] = phase 

    def set_awgTypeCh1(self, new):
        print("New Type: ",new)
        self.awgCh1Config["wave"] = new

    def set_time_div(self, div):
        try:
            self.plotViewBox.setXRange(self.viewRange[0][0],self.viewRange[0][0]+10*div)
            self.xAxis.setTickSpacing(div,div/2)
        #TODO throws error if current range is too large in comparision to div
            #ie 10s range, 4us divs
            #happens IN pyqtgraph library, so this try does nothoing
            #error only happens if we try to autorange with a low div
        #also idealy we do not change the range much, so implement float div->mult correction
        except:
            return

    def on_range_changed(self,vb, ranges):
        #perhaps include processing to ensure 
        print("Scaling occurred:", ranges)
        #controling x scale
            #look into using an event filter for this
        xconstant = isclose(ranges[0][0],self.viewRange[0][0]) and isclose(ranges[0][1],self.viewRange[0][1])
        if(xconstant):
            #this happens 
            print("\tx close")
        else:
            self.awgTime = np.linspace(ranges[0][0],ranges[0][1],NUMPOINTS)
            print("\t{} : {}".format(self.awgTime[0],self.awgTime[-1]))
            vb.disableAutoRange(pg.ViewBox.XAxis)

        self.viewRange = ranges

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
        ch1WaveSelect.currentIndexChanged.connect(self.set_awgTypeCh1)

        #AWG frequencies
        ch1Freq = LabelField("Frequency:",[MINFREQUENCY, MAXFREQUENCY],float(1), 3,"Hz", prefixes_frequency,BLANK)
        ch1Freq = LabelField("Frequency:",[MINFREQUENCY, MAXFREQUENCY],float(1), 3,"Hz", prefixes_frequency,BLANK)
        awgLayout.addWidget(ch1Freq,0,2)
        ch1Freq.valueChanged.connect(self.set_awgCh1Freq)
        ch1Freq.valueChanged.connect(self.set_awgCh1Freq)
        ch2Freq = LabelField("Frequency:",[MINFREQUENCY, MAXFREQUENCY],float(1000),3, "Hz", prefixes_frequency,BLANK)
        awgLayout.addWidget(ch2Freq,1,2)
            
        #AWG amplitueds
        ch1Amp = LabelField("Amplitude:",[MINAMP,MAXAMP],float(1),2,"V", prefixes_voltage,BLANK)
        ch1Amp.valueChanged.connect(self.set_awgCh1Amp)
        awgLayout.addWidget(ch1Amp,0,3)
        ch2Amp = LabelField("Amplitude:",[MINAMP,MAXAMP],float(5),2,"V", prefixes_voltage,BLANK)
        awgLayout.addWidget(ch2Amp,1,3)

        #AWG offsets
        ch1Off = LabelField("Offset:" ,[MINAMP, MAXAMP],float(0),2,"V", prefixes_voltage,BLANK)
        awgLayout.addWidget(ch1Off,0,4)
        ch2Off = LabelField("Offset:" ,[MINAMP, MAXAMP],float(0),2,"V", prefixes_voltage,BLANK)
        awgLayout.addWidget(ch2Off,1,4)        
        ch1Off.valueChanged.connect(self.set_awgCh1Off)
        awgPhase = LabelField("Phase:" ,[0, 180],float(0),2,"°", {"":1},BLANK)
        awgLayout.addWidget(awgPhase,0,5)
        awgPhase.valueChanged.connect(self.set_awgPhase)
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
        self.timeDiv = LabelField("Time Base", [1/MAXFREQUENCY,1/MINFREQUENCY],1,3,"s/div",{"u":1e-6,"m":1e-3,"":1},BLANK)
        self.timeDiv = LabelField("Time Base", [1/MAXFREQUENCY,1/MINFREQUENCY],1,3,"s/div",{"u":1e-6,"m":1e-3,"":1},BLANK)
        centerSettings.addWidget(self.timeDiv,0,0,1,1)
        self.timeDiv.valueChanged.connect(self.set_time_div)
        self.timeDiv.valueChanged.connect(self.set_time_div)

        centerSettings.addWidget(QLabel("Trigger Settings: "),0,1,1,1)

        trigTypeSelect = QComboBox()
        trigTypeSelect.addItem("Trigger Types")
        trigHoldoffSelect = QComboBox()
        trigHoldoffSelect.addItem("Holdoff (s)")

        centerSettings.addWidget(trigTypeSelect,0,2)
        centerSettings.addWidget(trigHoldoffSelect,0,3)

        logicLayout = QGridLayout()
        logicLayout.addWidget(ColorBox("Fuchsia"),0,0,-1,-1)#background for demonstration. Remove later
        logicCheck = QCheckBox()
        logicLayout.addWidget(logicCheck,0,0)
        logicLayout.addWidget(QLabel("Logic Analyzer"),0,1,alignment = Qt.AlignmentFlag.AlignHCenter)
        
        
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
        logicLayout.setColumnStretch(0,1)
        logicLayout.setColumnStretch(1,4)

        

        dataLayout = QGridLayout()
        dataLayout.addWidget(ColorBox("lime"),0,0,-1,-1)#background for demonstration. Remove later
        dataLayout.addWidget(QLabel("Live Data"),0,0,1,-1,alignment=Qt.AlignmentFlag.AlignHCenter)
        #maybe make a custom plotwidget, this will work for now
        self.plot_graph = pg.PlotWidget()
        self.plot_graph.setBackground("w")
        vb = self.plot_graph.plotItem.getViewBox()
        vb.setMouseMode(pg.ViewBox.RectMode)
        #below line disables a right click menu
        #self.plot_graph.plotItem.setMenuEnabled(False)
        vb.sigRangeChanged.connect(self.on_range_changed)
        self.viewRange = vb.viewRange()
        #if we need to completely disable resizing, uncomment below and set both to false
        self.plot_graph.setMouseEnabled(x=False,y=True)
        #if this is commented, autoranging will grow x axis indefinitely
        vb.disableAutoRange(pg.ViewBox.XAxis)
        vb.setDefaultPadding(0.0)#doesn't help 
        self.plotViewBox = vb
        vb.setLimits(yMax = 20, yMin = -20)
        vb.setXRange(0,10,.01 )
        self.xAxis = self.plot_graph.plotItem.getAxis("bottom")
        self.xAxis.setTickPen(color = "black", width = 2)
        #set y axis as well
        self.plot_graph.plotItem.getAxis("left").setTickPen(color = "black", width = 2)
        self.oscPen = pg.mkPen(color=(255, 0, 0), width=5, style=Qt.PenStyle.DotLine)

        self.time = np.linspace(0,10,NUMPOINTS)
        self.temperature = np.array([uniform(-1*self.awgCh1Config["amp"], self.awgCh1Config["amp"]) for _ in range(NUMPOINTS)])
        self.time = np.linspace(0,10,NUMPOINTS)
        self.temperature = np.array([uniform(-1*self.awgCh1Config["amp"], self.awgCh1Config["amp"]) for _ in range(NUMPOINTS)])
        self.plot_graph.setLabel("left", "Voltage (V)")
        self.plot_graph.setLabel("bottom", "Time (s)",)
        self.plot_graph.showGrid(x=True, y=True)
        self.templine = self.plot_graph.plot(self.time, self.temperature,pen = self.oscPen)
        self.plot_graph.showGrid(x=True, y=True)
        self.templine = self.plot_graph.plot(self.time, self.temperature,pen = self.oscPen)
        dataLayout.addWidget(self.plot_graph,1,0,-1,-1)
        

        oscilloLayout = QGridLayout()
        oscilloLayout.addWidget(ColorBox("Olive"),0,0,-1,-1)#background for demonstration. Remove later
        oscilloCheck = QCheckBox()
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
        #TODO edit all numpy funtions to use the out parameter
        #self.temperature = np.roll(self.temperature,-1)
        #self.temperature[-1] = uniform(-1*self.awgCh1Config["amp"], self.awgCh1Config["amp"])
        #self.templine.setData(self.time, self.temperature)
        #like angular position of awgtime array. To be used for nonsine functions
        self.omega = np.mod(self.awgTime+self.awgCh1Config["phase"]/360,1/self.awgCh1Config["freq"])*self.awgCh1Config["freq"]
        #np.fmod(tau*self.awgCh1Config["freq"]*self.awgTime + pi/180*self.awgCh1Config["phase"],2*tau/self.awgCh1Config["freq"])                
        self.templine.setData(self.awgTime, np.sin(tau*self.awgData))
        match self.awgCh1Config["wave"]:
            case 1:#square
                self.awgData = np.ones(NUMPOINTS)
                self.awgData[self.omega >= self.awgCh1Config["DC"]] = -1
            case 2:#triangle 
                climb = np.where(self.omega < 0.5)
                fall = np.where(self.omega  >= 0.5)
                self.awgData[climb] = 1 - 4 * self.omega[climb]
                self.awgData[fall] = 4 * self.omega[fall] - 3               
            case 3:#sawtooth
                self.awgData = 2*self.omega-1
            case _:#sine
                self.awgData = np.sin(tau*self.omega)
        #scale and offset
        self.awgData = self.awgCh1Config["amp"]*self.awgData + self.awgCh1Config["off"]
        #self.awgData = self.awgCh1Config["amp"]*np.sin(2*pi*self.awgCh1Config["freq"]*self.awgTime+pi/180*self.awgCh1Config["phase"])+self.awgCh1Config["off"]
        self.awgLine.setData(self.awgTime,self.awgData)
app = QApplication(sys.argv)

window = MainWindow()
window.show()

app.exec()