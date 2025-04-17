#
# TODO 
# - [?] Spacing?
# - [?] AWG checkboxes TODO: (does awg or scope have priority?)
# - [x] AWG waveform plot types
# - [/] AWG frequencies NOTE: works for ch1, TODO ch2
# - [x] AWG amplitudes
# - [x] AWG offsets
# - [ ] Time base
# - [x] Run/Stop button
# - [?] Single run button TODO: (single period? single data capture? etc)
# - [x] Record Data button
# - [x] Scope checkboxes
# - [ ] Scope ranges
# - [ ] Trigger stuff

#AWG barely works


import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget,QGridLayout,QPushButton,QLabel,QCheckBox,QComboBox, QTextEdit    
from PyQt6.QtGui import QPalette, QColor, QPen
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
import pyqtgraph as pg
import pyqtgraph.exporters
from labeled_field import LabelField 
from pyqtgraph.Qt import QtCore
import numpy as np
import serial
import serial.tools.list_ports
from random import uniform
from math import isclose,pi, tau
import os
from connection import Connection
from queue import Queue
from struct import pack
import threading


#html standard colors
colors = ["Yellow","Teal","Silver","Red","Purple","Olive","Navy","White",
            "Maroon","Lime","Green","Gray","Fuchsia","Blue","Black","Aqua"]
'''Html standard colors'''
#Constants
MAXFREQUENCY = 250e3
'''max AWG frequency'''
MINFREQUENCY = 1
'''min AWG frequency'''
MINAMP = -5
MAXAMP = 5
MINOFF = -10
MAXOFF = 10
NUMPOINTS = 300
NUMDIVS = 10 #based on default we've worked with thus far, scopy uses ~16

USE_CSV = False
'''Use CSV file for testing'''
#because of a change made to input field, we need to specify a "" unit
prefixes_voltage = {"m": 1e-3,"":1}
prefixes_frequency = {"k": 1e3, "M": 1e6,"":1}

oscModeFreq = [1000,2000,5000, 10000,20000,50000, 100000,200000,500000, 1000000,2000000]#backwards from actuall oscmode
oscModePeriod = [1/freq for freq in oscModeFreq]
possibleTimeDivs = [0.01, 0.005, 0.002, 0.001, 0.0005, 0.0002, 0.0001, 5e-05, 2e-05, 10e-06, 5e-06]
#[10*T for T in oscModePeriod]#[1, 0.5, 0.2, 0.1, 0.05, 0.02, 0.01, 5/1000, 2/1000, 1/1000 ,5/1000/10, 2/1000/10, 1/1000/10 ,5/1000/100, 2/1000/100, 1/1000/100 ,5/1000/1000, 2/1000/1000, 1/1000/1000]
possibleVoltDivs = [5, 2, 1, .1, .5, .2, .1]
oscBufferShow = 1000

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

def hexStr2bin(hex:str):
    match hex:
        case "1"|"0001":
            return b'0001'
        case "2"|"0010":
            return b'0010'
        case "3"|"0011":
            return b'0011'
        case "4"|"0100":
            return b'0100'
        case "5"|"0101":
            return b'0101'
        case "6"|"0110":
            return b'0110'
        case "7"|"0111":
            return b'0111'
        case "8"|"1000":
            return b'1000'
        case "9"|"1001":
            return b'1001'
        case "A"|"a"|"10"|"1010":
            return b'1010'
        case "B"|"b"|"11"|"1011":
            return b'1011'
        case "C"|"c"|"12"|"1100":
            return b'1100'
        case "D"|"d"|"13"|"1101":
            return b'1101'
        case "E"|"e"|"14"|"1110":
            return b'1110'
        case "F"|"f"|"15"|"1111":
            return b'1111'
        case _:
            return b'0000'

class MainWindow(QMainWindow):
    
    def __init__(self):
        #global dataIn
        #dataIn = []
        super(MainWindow, self).__init__()
        self.awgCh1Config = dict(amp=1, off=0,freq = 1,phase = 0, wave = 0, DC = 0.5)  # Dictionary with initial values
        self.awgCh2Config = dict(amp=1, off=0,freq = 1,phase = 0, wave = 0, DC = 0.5)  # Dictionary with initial values
        self.oscCh1Config = dict(mode=0, sampletime=0, offset=0, attn=0, amp=0)
        self.oscCh2Config = dict(mode=0, sampletime=0, offset=0, attn=0, amp=0)
        self.osc1Buffer = []
        self.osc2Buffer = []
        self.setWindowTitle("USB MultiTool")
        self.zeros = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0] #array of 0's for clearing wave -> placeholder for testing


        self.awgPen1 = pg.mkPen(color=(0, 0, 255), width=4, style=Qt.PenStyle.SolidLine) #scope ch1 = blue, solid line
        '''Ch1 pen'''
        self.awgPen2 = pg.mkPen(color=(255, 0, 0), width=4, style=Qt.PenStyle.SolidLine) #scope ch2 = red, dotted line
        '''Ch2 pen'''
        self.awgTime1 = np.linspace(0,10,NUMPOINTS)
        self.awgTime2 = np.linspace(0,10,NUMPOINTS)
        self.awgLine1 = pg.PlotDataItem()
        self.awgLine2 = pg.PlotDataItem()
        self.oscTime1 = np.linspace(0,10,NUMPOINTS)
        self.oscTime2 = np.linspace(0,10,NUMPOINTS)
        self.oscData1 = 1*np.sin(2*pi*self.awgCh1Config["freq"]*self.oscTime1+pi/180*self.awgCh1Config["phase"]) #sine wave ch1
        self.oscData2 = 1*np.sin(2*pi*self.awgCh2Config["freq"]*self.oscTime2) #sine wave ch2
        self.awgData1 = np.ones(NUMPOINTS)
        self.awgData2 = np.ones(NUMPOINTS)

        #layout for device control
        deviceLayout = self.deviceLayoutSetup()

        #layout for awg section
        awgLayout = self.awgLayoutSetup()


        #layout for window containing oscilloscope, wave, and logic analyizer
        centerLayout = self.centerLayoutSetup()


        #overall layout
        layout = QGridLayout()
        layout.addLayout(awgLayout, 0, 0, 2, -1)#for awg
        layout.addLayout(centerLayout, 2, 0, 7,-1) #for center block
        layout.addLayout(deviceLayout, 9, 0,1,-1) #for connect/disconect

        layout.setRowStretch(3,3)
        self.timer = QTimer()
        self.timer.setInterval(300)
        self.timer.timeout.connect(self.update_plot)
        self.timer.start()
        self.sampRes = 0
        
        #self.awgLine1 = self.plot_graph.plot(self.awgTime1, self.awgData1,pen = self.awgPen1)
        #self.awgLine2 = self.plot_graph.plot(self.awgTime2, self.awgData2, pen = self.awgPen2)

        self.oscLine1 = self.plot_graph.plot(self.oscTime1 ,self.osc1Buffer, pen= self.awgPen1)

        self.oscPosInterval = 1/(1000*10)
        self.voltsDivFix()
        self.logicLines = [None]*8

        self.logicLines[0] = self.logic_graph.plot(pen = self.awgPen1)
        self.logicLines[1] = self.logic_graph.plot(pen = self.awgPen2)



        self.set_time_div(0) #1v/div
        widget = QWidget()
        widget.setLayout(layout)
        self.setCentralWidget(widget)

        self.serial = serial.Serial(baudrate=115200)
        self.portName = None
        #self.status= "disconnected" #usb status


        #The below parses a CSV
        #in vscode, need to set "Terminal: Execute In File Dir" true in python extension
        if USE_CSV:
            self.parseCSV()

    def parseCSV(self):
        import csv
        #an example file exported from scopy
        filename = "i2c_EX.csv"
        data = []
        with open(filename, 'r') as csvfile:
            # creating a csv reader object
            csvreader = csv.reader(csvfile)
            
            print("header info\n")
            for i in range (0,7):
                print(next(csvreader))
                print("\n")

            fields = next(csvreader)
            print(fields)

            for row in csvreader:
                if len(row) >= 3:
                    data.append(row)
            self.csvData = np.array(data, dtype=object)
            self.csvData = np.where(self.csvData == '', '0', self.csvData)  # account for empty data
            print(self.csvData)

            #selected_column = self.csvData[:,0]
            #print(selected_column)
        return 
    
    
    #Device callbacks
    ###-------------------------------------------------------------------------------------###
        #TODO: add timeouts to EVERYTHING  
    def getPorts(self): #Lists all the COM ports available for the user to select (first clears, adds a refresh option, gets all com ports, adds them to the port object)
        self.portSelect.clear()
        self.portSelect.addItem("Refresh Ports")
        portCanidates = []
        for port in list(serial.tools.list_ports.comports()):
            if port.vid == 1155:
                portCanidates.append(port)
        ports = [port.name for port in portCanidates]
        self.portSelect.addItems(ports)
        self.portSelect.activated.connect(self.port_currentIndexChanged)

    def port_currentIndexChanged(self, index): #If a com port is selected, check to make sure it isnt the "Refresh Ports" option. If it is, disconnect and refresh ports available
        self.portName = None
        if index == 0:
            self.portSelect.disconnect()
            self.getPorts()
            

    def port_connect(self):
        if self.portName == None:
            if self.portSelect.currentIndex() == 0: #If the "refresh ports" option is selected disconnect and refresh ports available
                self.portSelect.disconnect()
                self.getPorts()
                return
            try: #For any other com port 
                self.serial.close()
                self.portName = self.portSelect.currentText() #selects COM port that the user selected
                self.serial.port = self.portName #sets serial port to COM port
                self.connectLabel.setText("Device Status: Connecting")
                self.conn.tryConnect(self.portName)
                #add the "/dev/" for unix based systems 
                    #currently untested
                if os.name == "posix":
                    self.portName = "/dev/" + self.portName
                #self.serial.open()

                #self.USBconnection = serial.Serial(self.portName, 115200, timeout = 5)
                #self.connectLabel.setText("Device Status: Connecting")
                #self.status="connecting"
                #self.sendQ=Queue()
                #self.sendHandShakePacket()

                #self.write_thread = threading.Thread(target=self.write_funct, args=())
                #self.write_thread.start()
                #This stuff is threaded for some reason
                #self.read_thread = threading.Thread(target=self.read_funct, args=())
                #self.read_thread.start()
                self.plot_graph.autoBtnClicked()
            except:
                self.connectLabel.setText("Device Status: Error")
                return
        else:
            try:
                #bits = hexStr2bin(self.sendline.toPlainText())
                #self.serial.write(bits)
                #buff = self.serial.read(8)
                #self.serial.reset_input_buffer()
                #self.connectLabel.setText(f"Device Status: {buff}")
                #self.serial.reset_input_buffer()
                pass
            except:
                return
    #USB stuff        

    #AWG UI Callbacks    
    ###-------------------------------------------------------------------------------------###
    #channel 1 configs
    def set_awgCh1Amp(self, amp):
        print("new Amp: ", amp)
        self.awgCh1Config["amp"] = amp
        self.awgCh1Click()

    def set_awgCh1Off(self,off):
        print("new Off: ", off)
        self.awgCh1Config["off"] = off
        self.awgCh1Click()

    def set_awgCh1Freq(self,freq):
        print("new Freq: ", freq)
        self.awgCh1Config["freq"] = freq
        self.awgCh1Click()

    def set_awgPhase(self, phase):
        print("new Phase: ", phase)
        self.awgCh1Config["phase"] = phase 
        self.awgCh1Click()

    def set_awgTypeCh1(self, new):
        print("New Type: ",new)
        self.awgCh1Config["wave"] = new
        self.awgCh1Click()

    def on_ch1Show(self):
        if(self.ch1Show.isChecked()):
            self.awgGraphCh1.show()
        else:
            self.awgGraphCh1.hide()

    #channel 2 configs
    def set_awgCh2Amp(self, amp):
        print("new Amp: ", amp)
        self.awgCh2Config["amp"] = amp
        self.awgCh2Click()

    def set_awgCh2Off(self,off):
        print("new Off: ", off)
        self.awgCh2Config["off"] = off
        self.awgCh2Click()

    def set_awgCh2Freq(self,freq):
        print("new Freq: ", freq)
        self.awgCh2Config["freq"] = freq
        self.awgCh2Click()

    def set_awgTypeCh2(self, new): 
        print("New Type: ",new)
        self.awgCh2Config["wave"] = new
        self.awgCh2Click()

    def on_ch2Show(self):
        if(self.ch2Show.isChecked()):
            self.awgGraphCh2.show()
        else:
            self.awgGraphCh2.hide()
    #Logic channel Callbacks

    def onLogicCheck(self):
        if(self.logicCheck.isChecked()):
            self.logic_graph.show()
        else:
            self.logic_graph.hide()
        return

    #Oscilloscope Range Slots
    def oscCh1Div_changed(self, newVal):
        '''Changes Divisions to match new Value'''
        halfNewRange = newVal*5
        axisRange = self.yAxis1.range
        midpoint = (axisRange[0]+axisRange[1])/2
        self.plotViewBox.setYRange(midpoint-halfNewRange,midpoint+halfNewRange)
        self.voltsDivFix()

    def voltsDivFix(self):
        '''Fixes positions of horizontal lines as Constant divs'''
        plotRange = self.yAxis1.range #height of y axis 1
        divSize = (plotRange[1] - plotRange[0])/(10)#0.5 on either side is a smudge to fully show all divs
        #print(str(midpoint)+" , "+ str(divSize)+ str(plotRange))
        for i in range(0,11):
            self.voltsDiv[i].setValue(plotRange[0]+divSize*i)
        self.vDivSize1 = divSize
        self.oscCh1VDiv.input_field.setVal(divSize,False)

    def oscCh2Div_changed(self, newVal):
        '''Slot for text-based V/div change'''
        halfNewRange = newVal*5
        axisRange = self.yAxis2.range
        midpoint = (axisRange[0]+axisRange[1])/2
        self.plot_osc2.setYRange(midpoint-halfNewRange,midpoint+halfNewRange)

    def oscCh2Div_changed_manually(self, vb, newRange):
        '''slot for mouse based V/div change'''
        divSize = (newRange[1] - newRange[0])/(10)
        self.oscCh2VDiv.input_field.setVal(divSize,False)

    def set_time_div(self, div):
        '''Sets left-right range of plots. The range will default to 10 divisions wide. 
        ### Params
        div: index of possible time divisions to switch to.'''
        divT = possibleTimeDivs[div]#convert index into div value
        midpoint = (self.viewRange[0][0]+ self.viewRange[0][1])/2
        #limit l-r span of xaxis to prevent too many tick lines from being drawn if user scrolls manually
        self.plotViewBox.setLimits(maxXRange=divT*20,minXRange = 4*divT)
        self.logicViewBox.setLimits(maxXRange=divT*20,minXRange = 4*divT)
        self.xAxis.setTickSpacing(2*divT,divT )
        self.logic_graph.getAxis("bottom").setTickSpacing(2*divT,divT)
        #5.5 as a fudge to show fifth point
        self.plotViewBox.setXRange(midpoint-5.5*divT, midpoint+5.5*divT)#self.viewRange[0][0],self.viewRange[0][0]+10*div)
        self.viewRange = self.plotViewBox.viewRange()
        print("New Range: "+str(self.viewRange[0][1] - self.viewRange[0][0]))
        self.plot_graph.autoBtnClicked()
        self.oscPosInterval = oscModePeriod[div]
        print("New OSCMODE:\t"+str(11-div))
        self.set_oscmode(11-div)
        #Handle graphing
     

    # handle range scaling
    def on_range_changed(self,vb, ranges):
        '''Slot for user changing range of plot.
        ### Params
        vb: viewbox of view changed

        ranges: new range of view'''
        #perhaps include processing to ensure 
        print("Scaling occurred:", ranges)
        #controlling x scale
            #look into using an event filter for this
        #xconstant = isclose(ranges[0][0],self.viewRange[0][0]) and isclose(ranges[0][1],self.viewRange[0][1])
        #newDiv = (ranges[0][1] - ranges[0][0]) / 10.0 #Latest attempt at out of mem bug squashing
        #self.timeDiv.input_field.setVal(newDiv,runCallback=False)
        #vb.setXRange(self.viewRange[0][0],self.viewRange[0][0]+10*newDiv)
        '''if(xconstant):
            #this happens never from experience
            print("\tx close: ")
        else:'''
        self.oscTime1 = np.linspace(ranges[0][0],ranges[0][1],NUMPOINTS)
        print("\t{} : {}".format(self.oscTime1[0],self.oscTime1[-1]))
        self.oscTime2 = np.linspace(ranges[0][0],ranges[0][1],NUMPOINTS)
        print("\t{} : {}".format(self.oscTime2[0],self.oscTime2[-1]))
        #vb.disableAutoRange(pg.ViewBox.XAxis)
        #print(self.xAxis.tickSpacing(ranges[0][0],ranges[0][1],NUMPOINTS))
        self.viewRange = ranges
        #self.vertLineFix()
        #self.voltsDivFix()


    def on_range_changed_manually(self):
        '''slot for user manually changing range of plot'''
        ranges = self.plotViewBox.viewRange()
        print("Manually CHANGED: ", ranges)
        #newDiv = (ranges[0][1] - ranges[0][0]) / 10.0 #Latest attempt at out of mem bug squashing
        #self.timeDiv.input_field.setVal(newDiv,runCallback=False)
        #self.plotViewBox.setXRange(self.viewRange[0][0],self.viewRange[0][0]+10*newDiv)
        self.oscTime1 = np.linspace(ranges[0][0],ranges[0][1],NUMPOINTS)
        self.oscTime2 = np.linspace(ranges[0][0],ranges[0][1],NUMPOINTS)
        self.viewRange = ranges
        #self.vertLineFix()
        self.voltsDivFix()

    def updateViews(self):
        '''Updates view of second oscilloscope y axis'''
        ## view has resized; update auxiliary views to match
        
        self.plot_osc2.setGeometry(self.plot_graph.vb.sceneBoundingRect())
        
        ## need to re-update linked axes since this was called
        ## incorrectly while views had different shapes.
        ## (probably this should be handled in ViewBox.resizeEvent)
        self.plot_osc2.linkedViewChanged(self.plot_graph.vb, self.plot_osc2.XAxis)



    #Layouts
    ###-------------------------------------------------------------------------------------###
       #sets up central graphs
    def graphSetup(self):
        '''Sets up graphs.
        
        ### Returns 
        a widget containing Graphs'''
        graphLayout =pg.GraphicsLayoutWidget(show=True)
        graphLayout.setBackground("w") 
        graphLayout.addLabel("")

        self.awgGraphCh1 = graphLayout.addPlot(row = 3, col = 0 )#pg.PlotWidget#
        self.awgGraphCh2 = graphLayout.addPlot(row = 3, col = 1)#pg.PlotWidget#

        
        self.awgline1= self.awgGraphCh1.plot([0],[0], pen = self.awgPen1)
        self.awgline2= self.awgGraphCh2.plot([0],[0], pen = self.awgPen2)
        self.awgPeriod1 = [i for i in range(0,NUMPOINTS+1)]
        self.awgPeriod2 = [i for i in range(0,NUMPOINTS+1)]
        self.set_awgCh1Freq(1)
        self.set_awgCh2Freq(1)
        self.awgWave1 = [0]*NUMPOINTS
        self.awgWave2 = [0]*NUMPOINTS

        self.awgGraphCh1.showGrid(True,True)
        self.awgGraphCh2.showGrid(True,True)

        self.awgGraphCh1.setLabel("left", text = "Voltage", units = "V")
        self.awgGraphCh1.setLabel("bottom", text ="Time" ,units = "s")
        
        self.awgGraphCh2.setLabel("left", text = "Voltage", units = "V")
        self.awgGraphCh2.setLabel("bottom", text ="Time" ,units = "s")
        self.awgGraphCh1.hide()
        self.awgGraphCh2.hide()
        #maybe make a custom plotwidget, this will work for now
        self.plot_graph = pg.PlotItem()
        #self.plot_osc2 = pg.ViewBox()
        graphLayout.addItem(self.plot_graph,row = 1, col = 0, colspan = 2) 
        self.plot_osc2 = graphLayout.addViewBox(row = 1, col = 0, colspan = 2)
        self.plot_osc2.setZValue(2)
        vb = self.plot_graph.getViewBox()  
        vb.setBackgroundColor("w")
        vb.setMouseMode(pg.ViewBox.PanMode)
        #below line disables a right click menu
        #self.plot_graph.plotItem.setMenuEnabled(False)
        vb.sigRangeChanged.connect(self.on_range_changed)
        self.viewRange = vb.viewRange()
        #if we need to completely disable resizing, uncomment below and set both to false
            #comment of shame.
        #self.plot_graph.setMouseEnabled(x=False,y=True)
        #if this is commented, autoranging will grow x axis indefinitely, so dont
            #We do actually need this for the oscilloscope proper
        #vb.disableAutoRange(pg.ViewBox.XAxis)
        #vb.setDefaultPadding(0.0)#doesn't help 
        vb.sigRangeChangedManually.connect(self.on_range_changed_manually)
        vb.setLimits(yMax = 20, yMin = -20)
        vb.setXRange(0,10)
        self.plotViewBox = vb
        self.xAxis = self.plot_graph.getAxis("bottom") #USES directly
        self.yAxis1 = self.plot_graph.getAxis("left")
        self.xAxis.setTickPen(color = "black", width = 2)
        #set y axis as well
        self.plot_graph.getAxis("left").setTickPen(color = "black", width = 2)#USES directly

        
        self.plot_graph.setLabel("left", text = "Voltage", units = "V")
        self.plot_graph.setLabel("bottom", text ="Time" ,units = "s")
        self.plot_graph.showGrid(x=True, y=False)
        #add infinte line to graph
            #removed for now
        '''self.plotLine = pg.InfiniteLine(pos=5,movable=True, angle=90, pen={'color':'g', 'width':3},  hoverPen=(0,200,0))
        
        self.plotLine.setZValue(3)
        self.plot_graph.addItem(self.plotLine)

        vb.setLimits(minXRange = 4e-6*5)
        self.plotLine.sigPositionChangeFinished.connect(self.lineMoved)'''


        #Setting second y-axis
        
        self.plot_graph.showAxis('right')
        self.plot_graph.scene().addItem(self.plot_osc2)
        self.plot_graph.getAxis('right').linkToView(self.plot_osc2)
        self.plot_osc2.setXLink(self.plot_graph)
        self.plot_graph.setLabel("right", text = "Voltage", units = "V")

        self.plot_graph.getAxis("right").setGrid(False)
        self.plot_graph.vb.sigResized.connect(self.updateViews)
        self.plot_osc2.sigResized.connect(self.updateViews)

        self.yAxis2 = self.plot_graph.getAxis('right')

        self.oscLine1 = self.plot_graph.plot(pen = self.awgPen1)#self.oscTime1, self.oscData1,
        self.oscLine2 = pg.PlotDataItem( pen = self.awgPen2)#self.oscTime2, self.oscData2,
        self.plot_osc2.addItem(self.oscLine2)#self.plot_graph.plot(self.oscTime2, self.oscData2, pen = self.awgPen2)
        self.plot_osc2.sigYRangeChanged.connect(self.oscCh2Div_changed_manually)
        self.oscLine2.setZValue(2)
        
        #stop auto resizing of base plot
        #vb.disableAutoRange(pg.ViewBox.YAxis)
        #self.plot_graph.hideButtons()
        #self.yAxis1.setScale(2)
        #when recordData clicked, export plot data to image & save
        self.exportData = pg.exporters.ImageExporter(self.plot_graph) #USES directly

        #Logic Analyizer section
            #mostly copied over from plot_graph
        self.logic_graph = graphLayout.addPlot(row = 2, col = 0, colspan = 2)#pg.PlotWidget()
        self.logic_graph.showAxis('right')
        self.logic_graph.setLabel("right", text = "Logic")
        self.logic_graph.getAxis('right').setStyle(showValues= False)
        self.logic_graph.getAxis('left').setStyle(showValues= False)
        vb_l = self.logic_graph.getViewBox() #USES directly
        vb_l.setBackgroundColor("w")
        
        '''self.verticalLines = []
        self.verticalLines.append(self.plotLine)'''

        #below line disables a right click menu
        #self.logic_graph.plotItem.setMenuEnabled(False)
        #vb_l.sigRangeChanged.connect(self.on_range_changed) #TODO:test with this connection
        #self.viewRange = vb.viewRange()
        #if we need to completely disable resizing, uncomment below and set both to false
            #comment of shame.
        #self.logic_graph.setMouseEnabled(x=False,y=True)
        #if this is commented, autoranging will grow x axis indefinitely, so dont
        #vb_l.disableAutoRange(pg.ViewBox.XAxis)
        vb_l.setDefaultPadding(0.0)#doesn't help 
        vb_l.setLimits(yMax = 20, yMin = -20)
        vb_l.setXRange(0,10)
        self.logicViewBox = vb_l
        
        #set y axis as well
        self.logic_graph.getAxis("left").setTickPen(color = "black", width = 2)#Uses Direclty
        self.logic_graph.getAxis("bottom").setTickPen(color = "black", width = 2)#Uses Direclty
        self.logic_graph.setLabel("left", "Logic")
        self.logic_graph.setLabel("bottom", text = "Time",units = "s")
        self.logic_graph.showGrid(x=True, y=True)
        self.logic_graph.setXLink(self.plot_graph)
        ### Removing Vertical Lines for now
        ''' self.logicLine = pg.InfiniteLine(pos= 5, movable=True, angle=90, pen={'color':'g', 'width':3},  hoverPen=(0,200,0))
        self.logicLine.setZValue(2)
        self.logic_graph.addItem(self.logicLine)
        self.verticalLines.append(self.logicLine)
        self.logicLine.sigPositionChangeFinished.connect(self.lineMoved)'''
        ###

        self.logic_graph.hide()
        self.plot_graph.hide()
        self.plot_osc2.hide()
        horizontalLines = [None]*11
        halfGray = QColor("darkGray")
        halfGray.setAlpha(127)
        for i in range(0,11):
            horizontalLines[i] = self.plot_graph.addLine(y=(i-5), pen = pg.mkPen(QColor("darkGray"),width = 2))
            if i % 2 == 1:
                horizontalLines[i].pen.setColor(halfGray)
        self.voltsDiv = horizontalLines  
        self.plotViewBox.setYRange(-5.5,5,5)     
        graphLayout.ci.setSpacing(0)
        return graphLayout


    
    
    def awgLayoutSetup(self):
        awgLayout = QGridLayout()
        awgLayout.addWidget(ColorBox(QColor("#cbc6d3")),0,0, -1,-1)#background for demonstration. Remove later colors[0] 
        #enable channel
            #to be able to use these outside of init, we'll need to prepend self as in "self.ch1En"
        self.AWGch1En = QCheckBox("Channel 1")
        self.AWGch1En.setChecked(False) #default scope channel 1 off
        self.AWGch1En.stateChanged.connect(self.awgCh1Click) #checkbox handler
        #ch1En.setChecked(True) #default awg channel 1 to on
        self.AWGch2En = QCheckBox("Channel 2")
        self.AWGch2En.setChecked(False) #default scope channel 1 off
        self.AWGch2En.stateChanged.connect(self.awgCh2Click) #checkbox handler        
        #ch2En.setChecked(True) #default awg channel 2 to on
        awgLayout.addWidget(self.AWGch1En,0,0)
        awgLayout.addWidget(self.AWGch2En,1,0)

        #wave types available
        self.waves = ["Sine","Square","Triangle","Sawtooth","Abritrary"]
        ch1WaveSelect = QComboBox()
        ch2WaveSelect = QComboBox() 
        ch1WaveSelect.addItems(self.waves)
        ch2WaveSelect.addItems(self.waves)
        awgLayout.addWidget(ch1WaveSelect,0,1)
        awgLayout.addWidget(ch2WaveSelect,1,1)
        ch1WaveSelect.activated.connect(self.set_awgTypeCh1)
        ch2WaveSelect.activated.connect(self.set_awgTypeCh2)


        #AWG frequencies
        #ch 1
        ch1Freq = LabelField("Frequency:",[MINFREQUENCY, MAXFREQUENCY],float(1), 3,"Hz", prefixes_frequency,BLANK)
        awgLayout.addWidget(ch1Freq,0,2)
        ch1Freq.valueChanged.connect(self.set_awgCh1Freq)
        
        #ch 2
        ch2Freq = LabelField("Frequency:",[MINFREQUENCY, MAXFREQUENCY],float(1),3,"Hz", prefixes_frequency,BLANK)
        awgLayout.addWidget(ch2Freq,1,2)
        ch2Freq.valueChanged.connect(self.set_awgCh2Freq)
            
        #AWG amplitudes
        ch1Amp = LabelField("Amplitude:",[MINAMP,MAXAMP],float(1),2,"V", prefixes_voltage,BLANK)
        ch1Amp.valueChanged.connect(self.set_awgCh1Amp)
        awgLayout.addWidget(ch1Amp,0,3)
        ch2Amp = LabelField("Amplitude:",[MINAMP,MAXAMP],float(1),2,"V", prefixes_voltage,BLANK)
        awgLayout.addWidget(ch2Amp,1,3)
        ch2Amp.valueChanged.connect(self.set_awgCh2Amp)

        #AWG offsets
        ch1Off = LabelField("Offset:" ,[MINAMP, MAXAMP],float(0),2,"V", prefixes_voltage,BLANK)
        awgLayout.addWidget(ch1Off,0,4)
        ch2Off = LabelField("Offset:" ,[MINAMP, MAXAMP],float(0),2,"V", prefixes_voltage,BLANK)
        awgLayout.addWidget(ch2Off,1,4)        
        ch1Off.valueChanged.connect(self.set_awgCh1Off)
        ch2Off.valueChanged.connect(self.set_awgCh2Off)
        #display graphs
        self.ch1Show = QCheckBox("Show CH1")
        awgLayout.addWidget(self.ch1Show, 0,5)
        self.ch1Show.stateChanged.connect(self.on_ch1Show)
        self.ch2Show = QCheckBox("Show CH2")
        awgLayout.addWidget(self.ch2Show, 1,5)
        self.ch2Show.stateChanged.connect(self.on_ch2Show)
        
        
        awgPhase = LabelField("Phase:" ,[0, 180],float(0),2,"°", {"":1},BLANK)
        awgLayout.addWidget(awgPhase,1,6),
        awgPhase.valueChanged.connect(self.set_awgPhase)
        '''awgLayout.addWidget(QLabel("Sync Status:"),1,5)

        syncButton = QPushButton("FORCE SYNC")
        syncButton.pressed.connect(self.AWGSYNC)
        buttonPalette = syncButton.palette()
        buttonPalette.setColor(QPalette.ColorRole.ButtonText, QColor("red"))
        syncButton.setPalette(buttonPalette)
        awgLayout.addWidget(syncButton,1,6)'''
        awgLayout.addWidget(QLabel("Waveform Generator"),0,6)

        return awgLayout
    

    def centerLayoutSetup(self):
        centerLayout = QGridLayout()
        centerLayout.addWidget(ColorBox("White"),0,0, -1,-1)#background for demonstration. Remove later [1]
        self.runStopButton = QPushButton("RUN/STOP")
        self.runStopButton.setCheckable(True)
        self.runStopButton.setChecked(False) #default to not clicked/running
        self.runStopButton.clicked.connect(self.runStopClick)
        singleButton = QPushButton("SINGLE")
        self.dataButton = QPushButton("RECORD DATA")
        self.dataButton.setCheckable(True)
        self.dataButton.setChecked(False) #default to not clicked
        #connect to method/slot to handle recording data
        self.dataButton.clicked.connect(self.record_data)

        centerSettings = QGridLayout()
        timeSetting = ColorBox("#e0dde5") 
        centerLayout.addWidget(timeSetting,0,0,1,-1)
        self.timeDiv = QComboBox()
        #LabelField("Time Base", [1/MAXFREQUENCY,1/MINFREQUENCY],1,3,"s/div",{"u":1e-6,"m":1e-3,"":1},BLANK)
        centerSettings.addWidget(self.timeDiv,0,0+1,1,1)
        centerSettings.addWidget(QLabel("Time Div "), 0,0)
        for div in possibleTimeDivs:
            unit = ""
            val = div
            if(div < 1/1000):#us case
                unit = "u"
                val = div*1000*1000
            elif(div < 1):#ms case
                unit = "m"
                val = div*1000
            self.timeDiv.addItem(f"{val} {unit}s/div")
            #possibleTimeDivs = [1, 0.5, 0.2, 0.1, 0.05, 0.02, 0.01, 5/1000, 2/1000, 1/1000 ,5/1000/10, 2/1000/10, 1/1000/10 ,5/1000/100, 2/1000/100, 1/1000/100 ,5/1000/1000, 2/1000/1000, 1/1000/1000]
        
        #self.timeDiv.addItems(["10 s/div",  "5 s/div", "1 s/div","0.5 s/div", "0.1 s/div", "50 ms/div", "10 ms/div","5 ms/div","1 ms/div"])
        self.timeDiv.setCurrentIndex(0)
        self.timeDiv.currentIndexChanged.connect(self.set_time_div)
        
        centerSettings.addWidget(QLabel("Trigger Settings: "),0,1+1,1,1)


        modes = ["Auto","Normal"]
        trigTypeSelect = QComboBox()
        trigTypeSelect.setPlaceholderText('Trigger Mode')
        trigTypeSelect.addItems(modes)
        trigHoldoffSelect = QComboBox()
        trigHoldoffSelect.addItem("Holdoff (s)")

        centerSettings.addWidget(trigTypeSelect,0,2+1)
        centerSettings.addWidget(trigHoldoffSelect,0,3+1)

        logicLayout = QGridLayout()
        logicLayout.addWidget(ColorBox("#c9d4c9"),0,0,-1,-1)#background for demonstration. Remove later
        self.logicCheck = QCheckBox()
        logicLayout.addWidget(self.logicCheck,0,0)
        self.logicCheck.stateChanged.connect(self.onLogicCheck)
        logicLayout.addWidget(QLabel("Logic Analyzer"),0,1,alignment = Qt.AlignmentFlag.AlignHCenter)
        
        
        edges = ["Rising Edge","Falling Edge", "None"]
        self.logic_checks = [None]*8
        self.logic_edges = [None]*8
        for i in range(0,8):
            pos = i+1
            self.logic_checks[i] = QCheckBox(f"CH{pos}")
            self.logic_edges[i] = QComboBox()
            self.logic_edges[i].setPlaceholderText('Trigger Type')
            self.logic_edges[i].addItems(edges)
            #self.logic_edges[i].currentIndexChanged.connect(self.index_changed)
            logicLayout.addWidget(self.logic_checks[i],i+1,0)
            logicLayout.addWidget(self.logic_edges[i],i+1,1)
        logicLayout.setColumnStretch(0,1)
        logicLayout.setColumnStretch(1,4)

        dataLayout = QGridLayout()
        #dataLayout.addWidget(ColorBox("#d0fcde"),0,0,-1,-1)#background for demonstration. Remove later
        dataLayout.addWidget(QLabel("Live Data"),0,0,1,-1,alignment=Qt.AlignmentFlag.AlignHCenter)
        graphWidget = self.graphSetup()
        dataLayout.addWidget(graphWidget)



        oscilloLayout = QGridLayout()
        oscilloLayout.addWidget(ColorBox("#d2dbe5"),0,0,-1,-1)#background for demonstration. Remove later
        self.oscilloCheck = QCheckBox()
        self.oscilloCheck.setChecked(False)#default scope checkbox checked -> scope off
        self.oscilloCheck.stateChanged.connect(self.oscClick) #main scope checkbox handler
        oscilloLayout.addWidget(self.oscilloCheck,0,0)
        oscilloLayout.addWidget(QLabel("Oscilloscope"),0,1,alignment = Qt.AlignmentFlag.AlignHCenter)
        
        self.oscCh1EN = QCheckBox("CH1")
        self.oscCh1EN.setChecked(False) #default scope channel 1 off
        self.oscCh1EN.stateChanged.connect(self.oscCh1Click) #checkbox handler
        self.oscCh1Trig = QComboBox()
        self.oscCh1Trig.setPlaceholderText('Trigger Type')
        self.oscCh1Trig.addItems(edges)
        self.oscCh1VDiv = LabelField("Range",[1e-6,20],1.0,2,"V/Div",{"u":1e-6,"m":1e-3,"":1},BLANK)
        self.oscCh1VDiv.valueChanged.connect(self.oscCh1Div_changed)
        self.oscCh2EN = QCheckBox("CH2")
        self.oscCh2EN.setChecked(False) #default scope channel 2 off
        self.oscCh2EN.stateChanged.connect(self.oscCh2Click) #checkbox handler
        self.oscCh2Trig = QComboBox()
        self.oscCh2Trig.setPlaceholderText('Trigger Type')
        self.oscCh2Trig.addItems(edges)
        self.oscCh2VDiv = LabelField("Range",[1e-6,20],1.0,2,"V/Div",{"u":1e-6,"m":1e-3,"":1},BLANK)
        self.oscCh2VDiv.valueChanged.connect(self.oscCh2Div_changed)
        oscmode = LabelField("oscmode:",[0,12],int(1),0,"", {"u":1e-6,"m":1e-3,"":1},BLANK)
        oscmode.valueChanged.connect(self.set_oscmode)
        oscilloLayout.addWidget(oscmode,0,3)
        
        oscilloLayout.addWidget(self.oscCh1EN,1,0,2,1)
        oscilloLayout.addWidget(self.oscCh1VDiv,1,1,1,-1)
        oscilloLayout.addWidget(self.oscCh1Trig,2,1)

        oscilloLayout.addWidget(self.oscCh2EN,3,0,2,1)
        oscilloLayout.addWidget(self.oscCh2VDiv,3,1,1,-1)
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
    
    
    def set_oscmode(self, oscmode):
        print("new mode: ", oscmode)
        self.oscCh1Config["mode"] = oscmode
        #self.awgCh1Click()
        self.oscCh1Click()
        self.sendline.setText(str(oscmode))
    statusCallbackSignal = pyqtSignal(str, str) 
    """Used to pass signals about connection updates between different threads """
    
    def statusCallback(self, status, message):
        """Callback function for the serial connection. Updates the status label and enables/disables the connect button.
        
        Parameters:
        status (str): The new status of the connection
        message (str): if not null, a popup with this message will be shown
        """
        print(status)
        self.connectLabel.setText("Device Status: " + status)
        #self.connectButton.setEnabled(status == "disconnected")
        if message:
            pg.QtWidgets.QMessageBox.critical(self, 'Error', message)
        if status == "Connected":
            pass
            #reset channels to off when connected
            #for c in self.channels:
               # c.setRunningStatus(False)

    def deviceLayoutSetup(self):
        deviceLayout = QGridLayout()
        deviceLayout.addWidget(ColorBox(colors[2]),0,0, -1,-1)#background for demonstration. Remove later
        self.connectLabel = QLabel("Device Status")
        deviceLayout.addWidget(self.connectLabel, 0,0,1,1)
        #specific colored buttons
        connectButton = QPushButton("CONNECT")
        buttonPalette = connectButton.palette()
        
        buttonPalette.setColor(QPalette.ColorRole.Button, QColor("green"))
        buttonPalette.setColor(QPalette.ColorRole.ButtonText, QColor("white"))
        connectButton.setPalette(buttonPalette)

        buttonPalette.setColor(QPalette.ColorRole.Button, QColor("red"))

        disconnectButton = QPushButton("DISCONNECT")
        disconnectButton.setPalette(buttonPalette)


        self.sendline = QTextEdit()
        self.sendline.setFixedSize(50,30)
        
        
        self.portSelect = QComboBox()
        #self.portSelect.addItems(["Refresh Ports"])
        deviceLayout.addWidget(self.portSelect,0,1)
        self.getPorts()

        #init connection object
        self.statusCallbackSignal.connect(self.statusCallback)
        self.conn = Connection(self.statusCallbackSignal)

        disconnectButton.pressed.connect(self.conn.port_disconnect)
        connectButton.pressed.connect(self.port_connect)
        #connectButton.pressed.connect(self.conn.tryConnect)
        
        deviceLayout.addWidget(connectButton,0,2,1,1)
        deviceLayout.addWidget(disconnectButton,0,3,1,1)
        deviceLayout.addWidget(self.sendline,0,4,1,1)
        deviceLayout.addWidget(QPushButton("Wave Drawer"),1,0,1,1)
        #Section for button spacing. Will require fine tuning to look as we want it
        deviceLayout.setColumnStretch(5,2) 
        deviceLayout.setColumnStretch(3,1) 
        deviceLayout.setColumnStretch(2,1) 
        deviceLayout.setColumnStretch(0,1) 

        return deviceLayout
    

    #Handler Methods
    ###-------------------------------------------------------------------------------------###
    #scope main checkbox handler
    def runStopClick(self):
        if self.runStopButton.isChecked():
            self.runStopButton.setText("Stop")
        else:
            self.runStopButton.setText("Run")
        self.plot_graph.autoBtnClicked()
    ###WAVEFORM GENERATOR--------------------------------------------------------------------------------------------------------
    #awg channel 1 checkbox handler
    def awgCh1Click(self): #If the button is checked, send a wave based on the parameters provided
        '''if self.oscCh1EN.isChecked():
            self.awgLine1.setData(self.awgTime1,self.awgData1) #set ch1 waveform data if checked'''
        if self.AWGch1En.isChecked():
            self.conn.sendWave(0, freq = (self.awgCh1Config["freq"]), wave_type = self.waves[self.awgCh1Config["wave"]], amplitude = self.awgCh1Config["amp"], offset = self.awgCh1Config["off"], arbitrary_waveform = "lol", duty = 50, phase = self.awgCh1Config["phase"] )
            print("Sent wave0")
            pass        
        if not self.AWGch1En.isChecked():
            self.awgLine1.setData(self.zeros,self.zeros) #temp solution -> remove wave
            self.conn.sendWave(0, freq = 0, wave_type = "dc", amplitude = self.awgCh2Config["amp"], offset = self.awgCh2Config["off"], arbitrary_waveform = "lol", duty = 50, phase = self.awgCh2Config["phase"] )

    #awg channel 2 checkbox handler
    def awgCh2Click(self):
        '''if self.oscCh2EN.isChecked():
            self.awgLine2.setData(self.awgTime2,self.awgData2) #set ch2 waveform data if checked'''
        if self.AWGch2En.isChecked():
            self.conn.sendWave(1, freq = (self.awgCh2Config["freq"]), wave_type = self.waves[self.awgCh2Config["wave"]], amplitude = self.awgCh2Config["amp"], offset = self.awgCh2Config["off"], arbitrary_waveform = "lol", duty = 50, phase = self.awgCh2Config["phase"] )
            print("Sent wave1")
            pass
        elif not self.AWGch2En.isChecked():
            self.awgLine2.clear()
            self.conn.sendWave(1, freq = 0, wave_type = "dc", amplitude = self.awgCh2Config["amp"], offset = self.awgCh2Config["off"], arbitrary_waveform = "lol", duty = 50, phase = self.awgCh2Config["phase"] )

    def graphAWGCh1(self):
        match self.awgCh1Config["wave"]:
            case 1:#square
                self.awgData1 = np.ones(NUMPOINTS)
                self.awgData1[self.omega1 >= self.awgCh1Config["DC"]] = -1
            case 2:#triangle 
                climb = np.where(self.omega1 < 0.5)
                fall = np.where(self.omega1  >= 0.5)
                self.awgData1[climb] = 1 - 4 * self.omega1[climb]
                self.awgData1[fall] = 4 * self.omega1[fall] - 3               
            case 3:#sawtooth
                self.awgData1 = 2*self.omega1-1
            case _:#sine
                self.awgData1 = np.sin(tau*self.omega1)
        #scale and offset
        self.awgData1 = self.awgCh1Config["amp"]*self.awgData1 + self.awgCh1Config["off"]
        self.awgLine1.setData(self.awgTime1,self.awgData1)

    def graphAWGCh2(self):
        match self.awgCh2Config["wave"]:
            case 1:#square
                self.awgData2 = np.ones(NUMPOINTS)
                self.awgData2[self.omega2 >= self.awgCh2Config["DC"]] = -1
            case 2:#triangle 
                climb = np.where(self.omega2 < 0.5)
                fall = np.where(self.omega2  >= 0.5)
                self.awgData2[climb] = 1 - 4 * self.omega2[climb]
                self.awgData2[fall] = 4 * self.omega2[fall] - 3               
            case 3:#sawtooth
                self.awgData2 = 2*self.omega2-1
            case _:#sine
                self.awgData2 = np.sin(tau*self.omega2)
        #scale and offset
        self.awgData2 = self.awgCh2Config["amp"]*self.awgData2 + self.awgCh2Config["off"]
        self.awgLine2.setData(self.awgTime2,self.awgData2)
    def AWGSYNC(self):
        if(self.AWGch1En.isChecked() and self.AWGch2En.isChecked()):
            min = None
            for a in range(1, 101):
                for b in range(1, 101):
                    if a/b == self.awgCh1Config["freq"] / self.awgCh2Config["freq"]:
                        if min == None or min[0] * min[1] > a*b:
                            min = (a, b)
            if min == None: #sync is still not possible
                self.conn.sendWave(0, freq = (self.awgCh1Config["freq"]), wave_type = self.waves[self.awgCh1Config["wave"]], amplitude = self.awgCh1Config["amp"], offset = self.awgCh1Config["off"], arbitrary_waveform = "lol", duty = 50, phase = self.awgCh1Config["phase"] )
                self.conn.sendWave(1, freq = (self.awgCh2Config["freq"]), wave_type = self.waves[self.awgCh2Config["wave"]], amplitude = self.awgCh2Config["amp"], offset = self.awgCh2Config["off"], arbitrary_waveform = "lol", duty = 50, phase = self.awgCh2Config["phase"] )
                #self.setSyncStatus(False)
            else:  #send synchronous waves
                a, b = min
                f_comm = self.awgCh1Config["freq"] / a #same as set[1].freq / b
                self.conn.sendWave(0, freq = (self.awgCh1Config["freq"]), wave_type = self.waves[self.awgCh1Config["wave"]], amplitude = self.awgCh1Config["amp"], offset = self.awgCh1Config["off"], arbitrary_waveform = "lol", duty = 50, phase = self.awgCh1Config["phase"], numPeriods = a)
                self.conn.sendWave(1, freq = (self.awgCh2Config["freq"]), wave_type = self.waves[self.awgCh2Config["wave"]], amplitude = self.awgCh2Config["amp"], offset = self.awgCh2Config["off"], arbitrary_waveform = "lol", duty = 50, phase = self.awgCh2Config["phase"], numPeriods = b)
                #self.setSyncStatus(True)            
        pass

    ###END WAVEFORM GENERATOR--------------------------------------------------------------------------------------------------------


    def oscClick(self):
        '''if self.oscilloCheck.isChecked(): #if checked -> check ch1 & ch2 checkboxes
            self.oscCh1Click()
            self.oscCh2Click()'''
        if not self.oscilloCheck.isChecked(): #temp solution -> plot zeros to remove waveforms
            self.oscCh1EN.setChecked(False)
            self.oscCh2EN.setChecked(False)
            self.plot_graph.hide()
            self.plot_osc2.hide()
        else:
            self.plot_graph.show()
            self.plot_osc2.show()
    #scope channel 1 checkbox handler
    def oscCh1Click(self):
        '''if self.oscCh1EN.isChecked():
            self.awgLine1.setData(self.awgTime1,self.awgData1) #set ch1 waveform data if checked'''
        print("clicked")
        self.conn.sendScope(0, mode=self.oscCh1Config["mode"],sampletime=self.oscCh1Config["sampletime"], offset_osc=self.oscCh1Config["offset"], attenuation=self.oscCh1Config["attn"], amp=self.oscCh1Config["amp"])
        if not self.oscCh1EN.isChecked():
            self.awgLine1.setData(self.zeros,self.zeros) #temp solution -> remove wave
        self.plot_graph.autoBtnClicked()

    #scope channel 2 checkbox handler
    def oscCh2Click(self):
        '''if self.oscCh2EN.isChecked():
            self.awgLine2.setData(self.awgTime2,self.awgData2) #set ch2 waveform data if checked'''
        if not self.oscCh2EN.isChecked():
            self.awgLine2.clear()
        self.plot_graph.autoBtnClicked()

    #handles record data button & exports snapshot of plot to file
    def record_data(self):
        if self.dataButton.isChecked():#recordData clicked 
            self.exportData.export()
            self.dataButton.setChecked(False) #reset button


    def graphOscCh1(self):

        
        #self.awgData1 = self.awgCh1Config["amp"]*self.awgData1 + self.awgCh1Config["off"]
        self.oscLine1.setData(self.oscTime1,self.osc1Buffer)

    def graphOscCh2(self):
        match self.awgCh2Config["wave"]:
            case 1:#square
                self.awgData2 = np.ones(NUMPOINTS)
                self.awgData2[self.omega2 >= self.awgCh2Config["DC"]] = -1
            case 2:#triangle 
                climb = np.where(self.omega2 < 0.5)
                fall = np.where(self.omega2  >= 0.5)
                self.awgData2[climb] = 1 - 4 * self.omega2[climb]
                self.awgData2[fall] = 4 * self.omega2[fall] - 3               
            case 3:#sawtooth
                self.awgData2 = 2*self.omega2-1
            case _:#sine
                self.awgData2 = np.sin(tau*self.omega2)
        #scale and offset
        self.awgData2 = self.awgCh2Config["amp"]*self.awgData2 + self.awgCh2Config["off"]
        self.awgLine2.setData(self.awgTime2,self.awgData2)


    #Periodic updates 
    ###-------------------------------------------------------------------------------------###
    def update_plot(self):
        #TODO edit all numpy funtions to use the out parameter



        #TODO REAL: MAKE ALL HIS WORK



        temp_logic_data = [[0,0,0,0,0,1,1,1,0,0],[0,1,0,1,0,1,0,1,0,1]]

        #like angular position of awgtime array. To be used for nonsine functions
        self.omega1 = np.mod(self.awgTime1+self.awgCh1Config["phase"]/(360*self.awgCh1Config["freq"]),
                             1/self.awgCh1Config["freq"])*self.awgCh1Config["freq"]
        self.omega2 = np.mod(self.awgTime2,1/self.awgCh2Config["freq"])*self.awgCh2Config["freq"]
        #np.fmod(tau*self.awgCh1Config["freq"]*self.awgTime + pi/180*self.awgCh1Config["phase"],2*tau/self.awgCh1Config["freq"])                
            #self.templine.setData(self.awgTime, np.sin(tau*self.awgCh1Config["freq"]*self.awgData1))
        self.dataIn=self.conn.returnData()
        #print(self.dataIn)
        #self.osc1Buffer.append(self.dataIn[0]) #This is slow and very inefficient. 
        self.osc1Buffer = np.asarray(self.conn.oscCh1Queue)/4096*3.3
        self.oscTime1 = self.conn.returnPositions() * self.oscPosInterval
            
        if not self.runStopButton.isChecked():
            self.awgLine1.setData(self.zeros,self.zeros)
            self.awgLine2.setData(self.zeros,self.zeros)

            self.logicLines[0].setData(self.zeros,self.zeros)
            self.logicLines[1].setData(self.zeros,self.zeros)
        else:  

            if self.oscilloCheck.isChecked():   
                if self.oscCh1EN.isChecked():
                    if(len(self.osc1Buffer)>=oscBufferShow):
                        #self.graphOscCh1()
                        #change oscPosInterval to change time between two buffer position measuremnts
                        #print("Plotting OSC0")
                        a=1 #dummy op for breakpoint 
                        self.oscLine1.setData(self.oscTime1[-(oscBufferShow-1):],self.osc1Buffer[-(oscBufferShow-1):])
                   #print("Plotting OSC0")
                if self.oscCh2EN.isChecked():
                    pass
                    #self.graphOscCh2()
            else:
                pass
                #self.awgLine1.clear()
                #self.awgLine2.clear()
            if self.logicCheck.isChecked():
                if (USE_CSV):
                    self.sampleValues = self.csvData[:, 0].astype(int)*1E-6     # sample time
                    #logicTime = np.arange(20000) /1E-6
                    self.scl = self.csvData[:, 1].astype(int)                   # clock line
                    self.sda = self.csvData[:, 2].astype(int)                   # data line
                    for i in (0,1):
                        if self.logic_checks[i].isChecked():
                            self.logicLines[i].setData(self.sampleValues,self.csvData[:, 1].astype(int)+i)  
                        else:
                            self.logicLines[i].setData(self.zeros, self.zeros)
                else:
                    for i in (0,1):                
                        if self.logic_checks[i].isChecked():
                            self.logicLines[i].setData(range(0,10),temp_logic_data[i], stepMode = "left")
                        else:
                            self.logicLines[i].setData(self.zeros,self.zeros)

        '''if(self.awgGraphCh1.isVisible()):
            self.omega1AWG = np.mod(self.awgPeriod1+(self.awgCh1Config["phase"]/(360*self.awgCh1Config["freq"])),
                            1/self.awgCh1Config["freq"])*self.awgCh1Config["freq"]
            #TODO: finish graphing
            self.awgWave1 = self.awgCh1Config["amp"]*np.sin(tau*self.omega1AWG) + self.awgCh1Config["off"]
            self.awgline1.setData( self.awgPeriod1,self.awgWave1)
        if(self.awgGraphCh2.isVisible()):
            self.omega2AWG = np.mod(self.awgPeriod2+(self.awgCh2Config["phase"]/(360*self.awgCh2Config["freq"])),
                            1/self.awgCh2Config["freq"])*self.awgCh2Config["freq"]
            #TODO: finish graphing
            self.awgWave2 = self.awgCh2Config["amp"]*np.sin(tau*self.omega2AWG) + self.awgCh2Config["off"]
            self.awgline2.setData( self.awgPeriod2,self.awgWave2)'''             


app = QApplication(sys.argv)

window = MainWindow()
window.show()

app.exec()