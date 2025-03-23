import subprocess
import math
import numpy as np
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtWidgets
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QApplication, QWidget, QLineEdit, QPushButton, QVBoxLayout, QMessageBox, QComboBox
)
from PyQt6 import QtGui
from wavegen import generateSamples
from connection import Connection
from input_field import Input
from wave_drawer import ICON_SIZE

class WaveSettings():
    """Stores a list of settings about the waveform of a channel"""

    def __init__(self, type, freq, amp, offset =0 , duty = 50, phase = 0, arb = None):
        """ Initializes the WaveSettings class.
        
        type (str): Type of the waveform to generate.
        freq (float): Frequency of wave.
        amp (float): Amplitude of the wave.
        offset (float): DC offset of the wave.
        duty (float): duty cycle of the wave (if wave is square).
        phase (float): phase of the wave
        arb (list of float): A list of samples for the user-defined arbitrary waveforms.
        """
        self.type = type
        self.freq = freq
        self.amp = amp
        self.offset = offset
        self.duty = duty
        self.phase = phase
        self.arb = arb

class Channel:
    """Handles the UI and logic for a single channel"""
    
    def update_dropdown(self):
        """Called when the wavetype dropdown is triggered. enables/disables input boxes as needed by wavetype. Calls generate_waveform()"""
        self.waveform_type = self.dropdown.currentText().lower()
        match self.waveform_type:
            case 'square':
                self.freqInput.setEnabled(True)
                self.ampInput.setEnabled(True)
                self.offsetInput.setEnabled(True)
                self.dutyInput.setEnabled(True)
                self.phaseInput.setEnabled(True)
            case 'dc':
                self.freqInput.setEnabled(False)
                self.ampInput.setEnabled(False)
                self.offsetInput.setEnabled(True)
                self.dutyInput.setEnabled(False)
                self.phaseInput.setEnabled(False)
            case _:
                self.freqInput.setEnabled(True)
                self.ampInput.setEnabled(True)
                self.offsetInput.setEnabled(True)
                self.dutyInput.setEnabled(False)
                self.phaseInput.setEnabled(True)
        self.generate_waveform()

    def updateAWList(self, AWlist, cause, modified = -1):
        """ Updates the list of arbitrary waveforms in the GUI. Calls generate_waveform as needed.
        
        Parameters:
        AWlist (list): The list of arbitrary waveforms.
        cause (str): The cause of the update, either "mod", "del", or "".
        modified (int): The index of the modified waveform, defaults to -1.
        """
        last_ind = self.dropdownArb.currentIndex()
        
        #updates the AW list, updates dropdown of custom waves
        self.listAW = AWlist
        self.dropdownArb.clear()
        ind = 0
        for aw in self.listAW:
            self.dropdownArb.addItem(aw.name)
            if aw.icon:
                self.dropdownArb.setItemIcon(ind, aw.icon)
            ind += 1
        
        #some of the last_ind!= -1 checks might not be needed here but not enough time to check if removing them breaks anything
        
        # if a arbitrary wave was modified, and that wave is currently selected, we need to update if the wavetype is arbitrary
        if cause == "mod" and last_ind != -1 and last_ind == modified:
            self.dropdownArb.setCurrentIndex(last_ind)
            if self.waveform_type == "arbitrary":
                self.generate_waveform()
        elif cause == "del" and last_ind != -1:
            #currently selected arbitrary wave was deleted, we need to change index and update if the wavetype is arbitrary
            if last_ind == modified:
                self.dropdownArb.setCurrentIndex(max(last_ind - 1, 0))
                if self.waveform_type == "arbitrary":
                    self.generate_waveform()
            #decrement dropdown selection index if the deleted wave was prior to the the selected wave
            elif last_ind > modified:
                self.dropdownArb.setCurrentIndex(last_ind - 1)
        #reset the dropdown to the selection that was before the update
        elif last_ind != -1:
            self.dropdownArb.setCurrentIndex(last_ind)

    def setRunningStatus(self, status):
        """Sets the running status, updates the UI of the run/stop button based on the new status. Calls generate_waveform()
        
        Parameters:
        status (bool): The new running status.
        """
        self.running = status
        if self.running:
            self.run_stop.setText("Stop")
            self.run_stop.setIcon(self.icons["stop"])
            #self.run_stop.setStyleSheet("background-color : lightblue")
        else:
            self.run_stop.setText("Run")
            self.run_stop.setIcon(self.icons["run"])
            #self.run_stop.setStyleSheet("background-color : lightgrey")
        self.generate_waveform()
                
    def generate_waveform(self):
        """Updates the waveform on the graph and calls updateWave() in main.py (via self.updateWave) so that the new wave can be sent to the AWG device. Called anytime a relevant setting is changed."""
        #generate_waveform() will be called spuriously while initialization is happening, we want to ignore these calls until the initialization is done.
        if not self.initDone:
            return
        
        #get arbitrary waveform samples from the AW list
        tr = 1 / self.freqInput.value
        if self.dropdownArb.currentIndex() != -1:
            arbitrary_waveform = self.listAW[self.dropdownArb.currentIndex()].samples
        else:
            arbitrary_waveform = None

        #generate the samples for the graph
        samples = generateSamples(self.waveform_type, 1000 if self.waveform_type != "arbitrary" else 4096, self.ampInput.value, arbitrary_waveform, self.dutyInput.value, self.phaseInput.value / 360, offset = self.offsetInput.value, timeRange = tr, clamp = [-10, 10])

        #graphs the samples
        self.plot_data.setData(samples[0], samples[1])
        self.plot_widget.setXRange(0, tr)
        self.plot_widget.setLabel('left', text='', units='V')
        self.plot_widget.setLabel('bottom', text='', units= 's')
        
        #updates the amplitude/offset lines
        self.guide_lines[0].setData([-tr, tr * 2], [self.offsetInput.value, self.offsetInput.value])
        self.guide_lines[1].setData([-tr, tr * 2], [self.offsetInput.value + self.ampInput.value, self.offsetInput.value + self.ampInput.value])
        self.guide_lines[2].setData([-tr, tr * 2], [self.offsetInput.value - self.ampInput.value, self.offsetInput.value - self.ampInput.value])
        self.guide_lines[1].setVisible(self.waveform_type != "dc")
        self.guide_lines[2].setVisible(self.waveform_type != "dc")
        
        #updates the wave settings. The AWG device has no way to turn off output, so "off" is just a DC wave. 
        if self.running:
            self.waveSettings = WaveSettings(type = self.waveform_type, freq = self.freqInput.value, amp = self.ampInput.value, offset = self.offsetInput.value, duty = self.dutyInput.value, phase = self.phaseInput.value / 360, arb = arbitrary_waveform)
        else:
            self.waveSettings = WaveSettings(type = "dc", freq = 1e3, amp = 5)
       
        #we don't want to call main.py's updateWave() until all channels are initialized. allowUpdates is used to accomplish this
        if self.allowUpdates:
            self.updateWave(self.chan_num)
        
        #update the running icon UI
        if self.running:
            self.on_off_label.setText("ON")
            self.on_off_label.setColor((0, 255, 0))
        else:
            self.on_off_label.setText("OFF")
            self.on_off_label.setColor((255, 0, 0))


    def enableUpdates(self):
        """We don't want channel to call main.py's updateWave() until all channels are initialized. This is called when the initialization is done."""
        self.allowUpdates = True
        self.updateWave(self.chan_num)

    def __init__(self, chan_num, grid_layout, icons, updateWave):
        """Initializes the channel.
        
        Parameters:
            chan_num (int): the number of the channel (0 or 1)
            grid_layout (): the grid layout to add UI elements, TODO, replace the grid with a hierarchy of vertical/horizontal layouts 
            icons (dict of str: qticon): dict mapping icon names to the icon
            updateWave (funct): function to call when we want to send the wave to the AWG device (this is just main.py's updateWave())
        """
        self.icons = icons
        self.chan_num = chan_num
        self.updateWave = updateWave
        
        if chan_num == 0:
            GUI_OFFSET = 0
        elif chan_num == 1:
            GUI_OFFSET = 9
            
        self.initDone = False
        self.allowUpdates = False
        #self.arbitrary_waveform = None
        self.waveform_type = "sine"

        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setMouseEnabled(x=False, y=False)
        self.plot_widget.setLabel('left', text='', units='V')
        self.plot_widget.setLabel('bottom', text='', units='s')
        self.plot_widget.setYRange(-10, 10)
        self.plot_widget.hideButtons()

        #initialize the offset/amplitude lines
        self.guide_lines = []
        for i in range(3):
            if chan_num == 0:
                self.guide_lines.append(self.plot_widget.plot(pen=(255, 255, 0, 96)))
                # self.guide_lines.append(self.plot_widget.plot(pen=pg.mkPen(color='y', dash=[5, 5])))
            elif chan_num == 1:
                self.guide_lines.append(self.plot_widget.plot(pen=(0, 255, 255, 96)))
                # self.guide_lines.append(self.plot_widget2.plot(pen=pg.mkPen(color='c', dash=[5, 5])))

        COLORS = ['y', 'c']
        self.plot_data = self.plot_widget.plot(pen=COLORS[chan_num])

        self.on_off_label = pg.TextItem()
        self.on_off_label.setPos(0, 10)
        self.plot_widget.addItem(self.on_off_label)

        self.clabel = QtWidgets.QLabel(f'Channel {chan_num + 1}')

        prefixes_v = {"m": 1e-3}
        prefixes_f = {"K": 1e3, "M": 1e6}

        self.freq_label = QtWidgets.QLabel('Frequency (Hz):')
        self.freqInput = Input(self.generate_waveform, [1, 250e3], float(1000), "hz", prefixes_f)

        self.amp_label = QtWidgets.QLabel('Amplitude:')
        self.ampInput = Input(self.generate_waveform, [-5, 5], float(5), "v", prefixes_v)

        self.offset_label = QtWidgets.QLabel('Offset Voltage:')
        self.offsetInput = Input(self.generate_waveform, [-10, 10], float(0), "v", prefixes_v)

        self.DCLabel = QtWidgets.QLabel("Duty Cycle:")
        self.dutyInput = Input(self.generate_waveform, [0, 100], float(50), "%", [])
        
        self.phaseLabel = QtWidgets.QLabel("Phase (Deg):")
        self.phaseInput = Input(self.generate_waveform, [0, 360], float(0), "deg", [])

        self.run_stop = QtWidgets.QPushButton()
        self.run_stop.clicked.connect(lambda: self.setRunningStatus(not self.running))
        
        self.wavetypeLabel = QtWidgets.QLabel("Wave type")
        self.dropdown = QComboBox()
        self.dropdown.addItem('Sine')
        self.dropdown.addItem('Triangle')
        self.dropdown.addItem('Sawtooth')
        self.dropdown.addItem('Square')
        self.dropdown.addItem('Arbitrary')
        self.dropdown.addItem('DC')
        self.dropdown.setItemIcon(0, icons["sine"])
        self.dropdown.setItemIcon(1, icons["tri"])
        self.dropdown.setItemIcon(2, icons["saw"])
        self.dropdown.setItemIcon(3, icons["square"])
        self.dropdown.setItemIcon(4, icons["arb"])
        self.dropdown.setItemIcon(5, icons["dc"])
        
        self.dropdown.activated.connect(self.update_dropdown)

        self.arbwaveLabel = QtWidgets.QLabel("Arbitrary Wave:")
        self.dropdownArb = QComboBox()
        self.dropdownArb.activated.connect(self.generate_waveform)
        self.dropdownArb.view().setIconSize(QtCore.QSize(ICON_SIZE,ICON_SIZE))

        grid_layout.addWidget(self.plot_widget, GUI_OFFSET + 1, 0, 9, 5)
        grid_layout.addWidget(self.clabel, GUI_OFFSET + 1, 5, 1, 1)

        grid_layout.addWidget(self.freq_label, GUI_OFFSET + 2, 5, 1, 1)
        grid_layout.addWidget(self.freqInput, GUI_OFFSET + 2, 6, 1, 1)

        grid_layout.addWidget(self.amp_label, GUI_OFFSET + 3, 5, 1, 1)
        grid_layout.addWidget(self.ampInput, GUI_OFFSET + 3, 6, 1, 1)

        grid_layout.addWidget(self.offset_label, GUI_OFFSET + 4, 5, 1, 1)
        grid_layout.addWidget(self.offsetInput, GUI_OFFSET + 4, 6, 1, 1)

        grid_layout.addWidget(self.wavetypeLabel, GUI_OFFSET + 7, 5, 1, 1)
        grid_layout.addWidget(self.dropdown, GUI_OFFSET + 7, 6, 1, 1)
        grid_layout.addWidget(self.arbwaveLabel, GUI_OFFSET + 8, 5, 1, 1)
        grid_layout.addWidget(self.dropdownArb, GUI_OFFSET + 8, 6, 1, 1)

        grid_layout.addWidget(self.DCLabel, GUI_OFFSET + 5, 5, 1, 1)
        grid_layout.addWidget(self.dutyInput, GUI_OFFSET + 5, 6, 1, 1)
        grid_layout.addWidget(self.phaseLabel, GUI_OFFSET + 6, 5, 1, 1)
        grid_layout.addWidget(self.phaseInput, GUI_OFFSET + 6, 6, 1, 1)

        grid_layout.addWidget(self.run_stop, GUI_OFFSET + 9, 5, 1, 2)

        self.update_dropdown()
        self.setRunningStatus(False)
        self.initDone = True
        self.generate_waveform()
