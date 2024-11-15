import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget,QGridLayout,QPushButton,QLabel,QCheckBox,QComboBox    
from PyQt6.QtGui import QPalette, QColor, QPen
from PyQt6.QtCore import Qt, QTimer
import pyqtgraph as pg
import pyqtgraph.exporters
from labeled_field import LabelField 
from pyqtgraph.Qt import QtCore
from random import uniform
import math
from math import isclose,pi
import numpy as np

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
NUMDIVS = 10#based on default we've worked with thus far, scopy uses ~16

#because of a change made to input field, we need to specify a "" unit
prefixes_voltage = {"m": 1e-3,"":1}
prefixes_frequency = {"k": 1e3, "M": 1e6,"":1}

#arbitrary number used in update_plot to check which checkbox is checked, initialize to 0
awgChecked = 0

runStopClicked = 0#holds state of runStopButton
recDataClicked = 0#holds state of recordData button
oscChecked = 0#holds state of scope checkbox
oscCHChecked = 0#holds state of scope channel checkboxes
logicChecked = 0#holds state of logic checkbox
logic_box = [None,]*8#holds state of logic analyzer channel checkboxes
for i in range(0,8):
    logic_box[i] = 0


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
        self.awgCh1Config = dict(amp=5, off=0,freq = 1,phase = 0) # Dictionary with initial values
        self.awgCh2Config = dict(amp=2, off=0,freq = 1,phase = 0) # Dictionary with initial values

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
        self.awgTime = np.linspace(0,10,NUMPOINTS)

        #for i in range(0,10):
         #   self.awgCh1Data[i] = sin(pi/2*self.time[i])

        self.set_time_div(1.0)

        self.time = np.linspace(0,10,NUMPOINTS)
        
        #self.awgPen = pg.mkPen(color=(0, 0, 255), width=5, style=Qt.PenStyle.SolidLine)
        self.pen1 = pg.mkPen(color=(255, 0, 0), width=5, style=Qt.PenStyle.DashLine)
        self.pen2 = pg.mkPen(color=(0, 0, 255), width=5, style=Qt.PenStyle.DotLine)
        self.awgCh1Data = 5*np.sin(2*pi*self.awgTime)
        self.awgCh2Data = 2*np.sin(2*pi*self.awgTime)
        self.awgCh1Line = self.plot_graph.plot(self.time, self.awgCh1Data,pen = self.pen1)
        self.awgCh2Line = self.plot_graph.plot(self.time, self.awgCh2Data,pen = self.pen2)

        self.logicTime = np.linspace(0,10,NUMPOINTS)            
        self.logicWave = ([None])*8 #empty array to hold 8 logic analyzer equations
        self.logicLine = ([None])*8 #empty array to hold 8 logic analyzer plot lines
        for i in range(0,8):
            self.logicPen[i] = pg.mkPen(color=colors[i], width=6, style=Qt.PenStyle.SolidLine)
            # plot a square wave
            self.logicWave[i] = ((-i/2 +2)*2)*np.array([1 if math.floor(2*t) % 2 == 0 else 0 for t in self.logicTime]) # every even index = 0, odd index = 1
            self.logicLine[i] = self.plot_graph.plot(self.time, self.logicWave[i],pen = self.logicPen[i]) # different pen for each logic analyzer channel
    
        widget = QWidget()
        widget.setLayout(layout)
        self.setCentralWidget(widget)
        #self.resize(400,500)

    def set_awgCh1Amp(self, amp1):
        print("new Amp1: ", amp1)
        self.awgCh1Config["amp1"] = amp1

    def set_awgCh1Off(self,off1):
        print("new Off1: ", off1)
        self.awgCh1Config["off1"] = off1

    def set_awgCh1Freq(self,freq1):
        print("new Freq1: ", freq1)
        self.awgCh1Config["freq1"] = freq1

    def set_awgPhase(self, phase):
        print("new Phase: ", phase)
        self.awgCh1Config["phase"] = phase 

    def set_awgCh2Amp(self, amp2):
        print("new Amp2: ", amp2)
        self.awgCh2Config["amp2"] = amp2

    def set_awgCh2Off(self,off2):
        print("new Off2: ", off2)
        self.awgCh2Config["off2"] = off2

    def set_awgCh2Freq(self,freq2):
        print("new Freq2: ", freq2)
        self.awgCh2Config["freq2"] = freq2


    def set_time_div(self, div):
        try:
            self.plotViewBox.setXRange(self.viewRange[0][0],self.viewRange[0][0]+10*div)
            self.xAxis.setTickSpacing(div,div/2)
            #TODO throws error if current range is too large in comparision to div
            #ie 10s range, 4us divs
            #happens IN pyqtgraph library, so this try does nothoing
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

    '''AWG layout setup'''    
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
        ch1Freq = LabelField("Frequency:",[MINFREQUENCY, MAXFREQUENCY],float(1), 3,"Hz", prefixes_frequency,BLANK)        
        awgLayout.addWidget(ch1Freq,0,2)
        ch1Freq.valueChanged.connect(self.set_awgCh1Freq)
        ch2Freq = LabelField("Frequency:",[MINFREQUENCY, MAXFREQUENCY],float(1000), 3, "Hz", prefixes_frequency,BLANK)
        awgLayout.addWidget(ch2Freq,1,2)
            
        #AWG amplitueds
        ch1Amp = LabelField("Amplitude:",[MINAMP,MAXAMP],float(5),2,"V", prefixes_voltage,BLANK)#ColorBox(colors[3])
        ch1Amp.valueChanged.connect(self.set_awgCh1Amp)
        awgLayout.addWidget(ch1Amp,0,3)
        ch2Amp = LabelField("Amplitude:",[MINAMP,MAXAMP],float(2),2,"V", prefixes_voltage,BLANK)#ColorBox(colors[4])
        awgLayout.addWidget(ch2Amp,1,3)

        #AWG offsets
        ch1Off = LabelField("Offset:" ,[MINAMP, MAXAMP],float(0),2,"V", prefixes_voltage,BLANK)#ColorBox(colors[5])        
        awgLayout.addWidget(ch1Off,0,4)
        #awgLayout.addWidget(QLabel("Offset (V):"),0,4)
        ch2Off = LabelField("Offset:" ,[MINAMP, MAXAMP],float(0),2,"V", prefixes_voltage,BLANK)#ColorBox(colors[7])#6 doesn't play nice with black text        
        awgLayout.addWidget(ch2Off,1,4)        
        #awgLayout.addWidget(QLabel("Offset (V):"),1,4)
        ch1Off.valueChanged.connect(self.set_awgCh1Off)
        awgPhase = LabelField("Phase:" ,[0, 180],float(0),2,"°", {"":1},BLANK)##ColorBox(colors[8])
        awgLayout.addWidget(awgPhase,0,5)
        awgPhase.valueChanged.connect(self.set_awgPhase)

        # awgLayout.addWidget(QLabel("Phase (°):"),0,5)
        awgLayout.addWidget(QLabel("Sync Status:"),1,5)

        syncButton = QPushButton("FORCE SYNC")
        buttonPalette = syncButton.palette()
        buttonPalette.setColor(QPalette.ColorRole.ButtonText, QColor("red"))
        syncButton.setPalette(buttonPalette)
        awgLayout.addWidget(syncButton,1,6)
        awgLayout.addWidget(QLabel("Waveform Generator"),0,6)

        return awgLayout

    '''center layout setup'''
    def centerLayoutSetup(self):
        centerLayout = QGridLayout()
        centerLayout.addWidget(ColorBox(colors[1]),0,0, -1,-1)#background for demonstration. Remove later
        self.runStopButton = QPushButton("RUN/STOP", self)
        self.runStopButton.setCheckable(True)
        self.runStopButton.setChecked(False)#default not running
        self.runStopButton.clicked.connect(self.button_was_clicked)
        singleButton = QPushButton("SINGLE")
        self.dataButton = QPushButton("RECORD DATA")
        self.dataButton.setCheckable(True)
        self.dataButton.setChecked(False)#default not clicked
        #connect to method/slot to handle recording data
        self.dataButton.clicked.connect(self.record_data)

        centerSettings = QGridLayout()
        timeSetting = ColorBox("aqua")
        centerSettings.addWidget(timeSetting,0,0,1,1)
        self.timeDiv = LabelField("Time Base", [1/MAXFREQUENCY,1/MINFREQUENCY],1,3,"s/div",{"u":1e-6,"m":1e-3,"":1},BLANK)
        centerSettings.addWidget(self.timeDiv,0,0,1,1)
        self.timeDiv.valueChanged.connect(self.set_time_div)
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


        dataLayout = QGridLayout()
        dataLayout.addWidget(ColorBox("lime"),0,0,-1,-1)#background for demonstration. Remove later
        dataLayout.addWidget(QLabel("Live Data"),0,0,1,-1,alignment=Qt.AlignmentFlag.AlignHCenter) #maybe make a custom plotwidget, this will work for now
        self.plot_graph = pg.PlotWidget()
        pg.setConfigOptions(antialias=True)
        self.plot_graph.setBackground("w")
        vb = self.plot_graph.plotItem.getViewBox()
        self.plot_graph.showGrid(x=True,y=True)

        vb.setMouseMode(pg.ViewBox.RectMode)
        #this line disables a right click menu
        #self.plot_graph.plotItem.setMenuEnabled(False)
        vb.sigRangeChanged.connect(self.on_range_changed)
        self.viewRange = vb.viewRange()
        #if we need to completely disable resizing, uncomment below
        self.plot_graph.setMouseEnabled(x=False,y=True)
        #if this is commented, autoranging will grow x axis indefinitely
        vb.disableAutoRange(pg.ViewBox.XAxis)
        vb.setDefaultPadding(0.0)#doesn't help 
        self.plotViewBox = vb
        vb.setXRange(0,10,.01)
        self.xAxis = self.plot_graph.plotItem.getAxis("bottom")
        self.xAxis.setTickPen(color = "black", width = 2)
        #set y axis as well
        self.plot_graph.plotItem.getAxis("left").setTickPen(color = "black", width = 2)
        self.oscPen = pg.mkPen(color=(255, 0, 0), width=5, style=Qt.PenStyle.DotLine)

        #self.temperature = np.array([uniform(-1*self.awgCh1Config["amp"], self.awgCh1Config["amp"]) for _ in range(NUMPOINTS)])
        
        #when recordData clicked, export plot data to image
        self.exportData = pg.exporters.ImageExporter(self.plot_graph.plotItem)

        logicLayout = QGridLayout()
        logicLayout.addWidget(ColorBox("Fuchsia"),0,0,-1,-1)#background for demonstration. Remove later
        self.logicCheck = QCheckBox()#QLabel("Logic Analyzer",alignment = Qt.AlignmentFlag.AlignTop)#QCheckBox("Logic Analyzer")
        self.logicCheck.setChecked(True) # initially set logic analyzer function to on
        self.logicCheck.clicked.connect(self.logicStateChanged) # connect to slot to handle logic analyzer on/off
        logicLayout.addWidget(self.logicCheck,0,0)
        logicLayout.addWidget(QLabel("Logic Analyzer"),0,1,alignment = Qt.AlignmentFlag.AlignHCenter)
        #logicChannelLayout = QGridLayout()
        
        edges = ["Rising Edge","Falling Edge", "None"]
        self.logic_checks = [None,]*8
        self.logic_edges = [None]*8
        self.logicPen = [None]*8 # to create array of 8 different pen colors using colors array
        
        for i in range(0,8):
            pos = i+1
            self.logic_checks[i] = QCheckBox(f"Channel {pos}")
            self.logic_checks[i].setChecked(True) # initially set all logic analyzer channels to ff
            self.logic_checks[i].clicked.connect(self.logicCH_StateChanged) # connect to slot to handle logic analyzer channels on/off
            self.logic_edges[i] = QComboBox()
            self.logic_edges[i].setPlaceholderText('Trigger Type')
            self.logic_edges[i].addItems(edges)
            logicLayout.addWidget(self.logic_checks[i],i+1,0)
            logicLayout.addWidget(self.logic_edges[i],i+1,1)
        #logicLayout.addLayout(logicChannelLayout,1,0,-1,-1)
        logicLayout.setColumnStretch(0,1)
        logicLayout.setColumnStretch(1,4)

        #self.time = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        #self.temperature = [uniform(-5, 5) for _ in range(10)]
        self.zeros = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0]#array of 0's for when no channel checkbox selected
        self.plot_graph.setLabel("left", "Voltage (V)")
        self.plot_graph.setLabel("bottom", "Time (s)",)
        self.plot_graph.setYRange(-5, 5)

        dataLayout.addWidget(self.plot_graph,1,0,-1,-1)
        self.time = np.linspace(0,10,NUMPOINTS)


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
        centerLayout.addWidget(self.dataButton,0,2)
        centerLayout.addWidget(QLabel("Live Data"),0,9)

        return centerLayout

    '''device layout setup'''
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

    #checks if runStopButton was clicked/unclicked
    def button_was_clicked(self):
        if self.runStopButton.isChecked():#runStopButton clicked to run
            runStopClicked = 1#run
        else:#runStopButton unclicked to stop
            runStopClicked = 0#stop
        return runStopClicked
    
    #tracks state of awg ch1 & ch2 checkboxes
    def awgChStateChanged(self):
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

    #tracks state of oscilloscope checkbox 
    def oscStateChanged(self):
        if self.oscilloCheck.isChecked():
            oscChecked = 1#scope on
            #doesn't work:
            #if self.oscChStateChanged() == 1:
                #self.oscCh1EN.setChecked(True)
            #if self.oscChStateChanged() == 2:
                #self.oscCh2EN.setChecked(True)
        else:
            oscChecked = 0#scope off
            self.oscCh1EN.setChecked(False)
            self.oscCh2EN.setChecked(False)
            #idk yet if this is needed. trying to automatically turn all channels back on after reenabling scope
            if self.oscChStateChanged() == 1:
                oscChecked = 1
                self.oscCh1EN.setChecked(True)
            if self.oscChStateChanged():    
                oscChecked = 1
                self.oscCh2EN.setChecked(True)
        return oscChecked#return scope checkbox state
        
    #tracks state of osc ch1 & ch2 checkboxes
    def oscChStateChanged(self):
        #only ch1 scope checkbox selected
        if self.oscCh1EN.isChecked() and not self.oscCh2EN.isChecked():
            oscCHChecked = 1
        #only ch2 scope checkbox selected
        elif not self.oscCh1EN.isChecked() and self.oscCh2EN.isChecked():
            oscCHChecked = 2
        #both ch1 & ch2 scope checkbox selected
        elif self.oscCh1EN.isChecked() and self.oscCh2EN.isChecked():
            oscCHChecked = 3
        #no scope checkbox selected
        else:
            oscCHChecked = 0
        return oscCHChecked#return which scope checkbox is checked
    
    #tracks state of logic analyzer checkbox
    #automaticaly reenabling all channels works for logic analyzer & not scope, idk why yet
    # opposite of what we want(?):
    #   scope rechecked -> reenable all channels & logic analyzer rechecked -> user individually selects channels to reenable ?
    def logicStateChanged(self):
        #print("in logicStateChanged")
        if self.logicCheck.isChecked():
            #print("self.logicCheck is checked")
            logicChecked = 1#logic analyzer on
            self.logicCheck.setChecked(True)
            for i in range(0,8):
                logic_box[i] = 1
                self.logic_checks[i].setChecked(True)
        else:
            #print("self.logicCheck is not checked")
            logicChecked = 0#logic analyzer off
            self.logicCheck.setChecked(False)
            for i in range(0,8):
                self.logic_checks[i].setChecked(False)
                logic_box[i] = 0
        self.logicCH_StateChanged()
        #for i in range(0,8):
         #   if logic_box[i] == 1:
          #      logic_box[i] = 1
           #     self.logic_checks[i].setChecked(True)
        #    else:
         #       logic_box[i] = 0
          #      self.logic_checks[i].setChecked(False)
            
        return logicChecked
        
    #tracks state of all 8 logic analyzer checkboxes
    def logicCH_StateChanged(self):
        #print("in logicCH_StateChanged")
        for i in range(0,8):
            if self.logic_checks[i].isChecked():
                #print("self.logic_checks[i] is checked")
                logic_box[i] = 1
                self.logic_checks[i].setChecked(True)
            else:
                #print("self.logic_checks[i] is not checked")
                logic_box[i] = 0
                self.logic_checks[i].setChecked(False)
        return logic_box
   
    def configOscPlot(self):
        self.awgTime = self.awgTime[1:]#continuous time, keep counting
        self.awgCh1Data = self.awgCh1Config["amp"]*np.sin(2*pi*self.awgCh1Config["freq"]*self.awgTime+pi/180*self.awgCh1Config["phase"])+self.awgCh1Config["off"]
        self.awgCh2Data = self.awgCh2Config["amp"]*np.sin(2*pi*self.awgCh2Config["freq"]*self.awgTime+pi/180*self.awgCh2Config["phase"])+self.awgCh2Config["off"]

    def configLogicPlot(self):
        self.logicTime = self.logicTime[1:]
        for i in range(0,8):
            self.logicWave[i] = self.logicWave[i]
        return self.logicWave

    def plotOscCh1(self):#plot ch1 data
        self.configOscPlot()
        self.awgCh1Line.setData(self.awgTime, self.awgCh1Data)
        self.awgCh2Line.setData(self.zeros,self.zeros)#plot zeros for ch2, works for now

    def plotOscCh2(self):#plot ch2 data
        self.configOscPlot()
        self.awgCh1Line.setData(self.zeros, self.zeros)#plot zeros for ch1, works for now
        self.awgCh2Line.setData(self.awgTime,self.awgCh2Data)

    def plotOscCh12(self):#plot ch1 & ch2 data
        self.configOscPlot()
        self.awgCh1Line.setData(self.awgTime, self.awgCh1Data)
        self.awgCh2Line.setData(self.awgTime,self.awgCh2Data)
    
    def plotOscZero(self):#no plotting
        self.configOscPlot()
        self.awgCh1Line.setData(self.zeros, self.zeros)#plot zeros for both channels
        self.awgCh2Line.setData(self.zeros, self.zeros)

    def plotLogic(self):
        self.configLogicPlot()
        self.logicCH_StateChanged()
        for i in range(0,8):
            if logic_box[i] == 1: 
                self.logicLine[i].setData(self.time, self.logicWave[i])

    def plotLogicZero(self):
        self.configLogicPlot()
        for i in range(0,8):
            self.logicLine[i].setData(self.zeros, self.zeros)

    def update_plot(self):
        #oscChChecked=1 run/stop button clicked, oscChecked=1, 
        if self.oscChStateChanged() == 1 and self.button_was_clicked() and self.oscStateChanged():
            self.plotOscCh1()#plot only ch1
        #oscChChecked=2 run/stop button clicked, oscChecked=1, 
        elif self.oscChStateChanged() == 2 and self.button_was_clicked() and self.oscStateChanged():
            self.plotOscCh2()#plot only ch2
        #oscChChecked=3 run/stop button clicked, oscChecked=1, 
        elif self.oscChStateChanged() == 3 and self.button_was_clicked() and self.oscStateChanged():
            self.plotOscCh12()#plot both ch1 & ch2
        #oscChChecked=0 run/stop button clicked, oscChecked=1, 
        else:#don't plot anything
            self.plotOscZero()
        if self.button_was_clicked() and self.logicStateChanged():
            logic_box = self.logicCH_StateChanged()
            for i in range(0,8):
                if logic_box[i] == 1:
                    self.plotLogic()
                else:
                    self.plotLogicZero()
        else:
            self.plotLogicZero()

    #handles record data button & exports snapshot of plot to file
    def record_data(self):
        if self.dataButton.isChecked():#recordData clicked 
            recordData = 1#record data
            self.exportData.export()
        else:#do nothing
            recordData = 0
        return recordData
    


app = QApplication(sys.argv)

window = MainWindow()
window.show()

app.exec()
#test