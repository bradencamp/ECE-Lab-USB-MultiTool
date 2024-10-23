import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget,QGridLayout,QPushButton,QLabel,QCheckBox,QComboBox    
from PyQt6.QtGui import QPalette, QColor
from PyQt6.QtCore import Qt

#html standard colors
colors = ["Yellow","Teal","Silver","Red","Purple","Olive","Navy","White",
            "Maroon","Lime","Green","Gray","Fuchsia","Blue","Black","Aqua"]
class ColorBox(QWidget):

    def __init__(self, color):
        super(ColorBox, self).__init__()
        self.setAutoFillBackground(True)

        palette = self.palette()
        palette.setColor(QPalette.ColorRole.Window, QColor(color))
        self.setPalette(palette)

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


        widget = QWidget()
        widget.setLayout(layout)
        self.setCentralWidget(widget)
        self.resize(400,500)

        
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
        ch1Freq = ColorBox(colors[1])
        awgLayout.addWidget(ch1Freq,0,2)
        awgLayout.addWidget(QLabel("Frequency (Hz):"),0,2)
        ch2Freq = ColorBox(colors[2])
        awgLayout.addWidget(ch2Freq,1,2)
        awgLayout.addWidget(QLabel("Frequency (Hz):"),1,2)
            
        #AWG amplitueds
        ch1Amp = ColorBox(colors[3])
        awgLayout.addWidget(ch1Amp,0,3)
        awgLayout.addWidget(QLabel("Amplitude (V):"),0,3)
        ch2Amp = ColorBox(colors[4])
        awgLayout.addWidget(ch2Amp,1,3)        
        awgLayout.addWidget(QLabel("Amplitude (V):"),1,3)

        #AWG offsets
        ch1Off = ColorBox(colors[5])
        awgLayout.addWidget(ch1Off,0,4)
        awgLayout.addWidget(QLabel("Offset (V):"),0,4)
        ch2Off = ColorBox(colors[7])#6 doesn't play nice with black text
        awgLayout.addWidget(ch2Off,1,4)        
        awgLayout.addWidget(QLabel("Offset (V):"),1,4)

        awgPhase = ColorBox(colors[8])
        awgLayout.addWidget(awgPhase,0,5)
        awgLayout.addWidget(QLabel("Phase (°):"),0,5)
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
        logicCheck = QLabel("Logic Analyzer",alignment = Qt.AlignmentFlag.AlignTop)#QCheckBox("Logic Analyzer")
        logicLayout.addWidget(logicCheck,0,0,0,-1)
        

        dataLayout = QGridLayout()
        dataLayout.addWidget(ColorBox("lime"),0,0,-1,-1)#background for demonstration. Remove later
        dataLayout.addWidget(QLabel("Live Data",alignment = (Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)),0,0,-1,-1)
        

        oscilloLayout = QGridLayout()
        oscilloLayout.addWidget(ColorBox("yellow"),0,0,-1,-1)#background for demonstration. Remove later
        oscilloCheck = QLabel("Oscilloscope",alignment = Qt.AlignmentFlag.AlignTop)#QCheckBox("Oscilloscope")
        oscilloLayout.addWidget(oscilloCheck,0,0,-1,-1)


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


app = QApplication(sys.argv)

window = MainWindow()
window.show()

app.exec()