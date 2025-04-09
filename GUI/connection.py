import serial
import serial.tools.list_ports
import threading
import math
from wavegen import *
from struct import pack, unpack, calcsize
import os
from queue import Queue
import time
from collections import deque 
from numpy import asarray

BUFFERSIZE = 30*1000
class Connection:
    """Handles the connection to the AWG device"""
    
    def sendHandShakePacket(self):
        """ Sends a handshake packet to the device.
        
        This function should be called when the device is first connected to and during keep-alive."""
        if self.status == "Disconnected":
            return
        bytes = pack("B4B59x", 0, ord('I'), ord('N'), ord('I'), ord('T'))
        assert len(bytes) == 64
        self.sendQ.put(bytes)

    def port_disconnect(self):
        if self.status != "Disconnected":
            self.ser.close()
            self.portName = None
            #self.connectLabel.setText("Device Status: Disconnected")
            self.statusCallback.emit("Disconnected", "Connection Closed")
            print("Disconnected")
            #self.status= "disconnected"
            #         
    def read_disconnect(self, msg):
        """ Disconnects the device and emits a disconnected signal to the main UI.
        
        Parameters:
        msg (str): The reason for the disconnect.
        """
        if self.status != "Disconnected":
            self.status = "Disconnected"
            self.statusCallback.emit("Disconnected", msg)
            self.ser.close()
                    
    def read_funct(self):
        """ The function that runs the read thread. This function reads data from the serial port. Detects acknowledgments and disconnects due to timeout, emitted updates to the main UI as needed."""
        timeouts = 0
        #recoverybuff=b'\x059988_3040_3040_3040_3040_1016_1016_1020_1016\x00-\x00\x08\xa8\xff\t \xa8\xff\xff\xff\x01\x00\x00\x00@\x00\x00'
        while self.status != "Disconnected":
            try:
                self.ser.reset_input_buffer()
                buff = self.ser.read(64)
            except:
                buff = None
                self.read_disconnect("Connection Disconnected")
                break
                
            if len(buff) == 0: #timeout 
                #send keep alive packets?
                if timeouts == 0:
                    timeouts = 1
                    self.sendHandShakePacket()
                else:
                    self.read_disconnect("timeout")
                pass
            else:
                #print(buff)
                if(buff[0:9] == bytes("\0STMAWG23", "ascii")): #ack packet
                    #self.recoverybuff=buff
                    timeouts = 0
                    print(buff[0:9])
                    #self.ser.flush()
                    #buff=recoverybuff
                    #print(buff)
                    if self.status == "Connecting":
                        self.statusCallback.emit("Connected", None)
                    self.status = "Connected"
                    while self.ser.in_waiting > 0:  # Check if data is available
                        self.ser.read(self.ser.in_waiting)  # Read and discard
                elif(buff[0:1] == bytes("\5", "ascii")): #got a data packet (ignore all the other stuff, just messing with packet types)
                    #packettype, osc1data, osc2data, logicdata=unpack("<B4H4H4H", buff[0:24])
                    #print(calcsize("<B4H4H4H39x"))
                    #print(unpack("<B4H4H4HH37x", buff))
                    #print(buff)
                    #print()
                    #print(unpack("<BHHHH55x", buff))
                    try:
                        pos, osch1, osch2, logicd, buffpos = unpack("<BHHHH55x", buff)
                        print("Pos {}, Osch1 {}, Osch2 {}, logic {}, Bpos {}\n".format(pos,osch1,osch2,logicd,buffpos))
                        if(buffpos < self.lastPos):
                            self.itteration += 1
                        self.buffPosQueue.append(buffpos+self.itteration*BUFFERSIZE)
                        self.oscCh1Queue.append(osch1)
                        self.lastPos = buffpos
                    #self.dataIn[0], self.dataIn[1], self.dataIn[2], self.dataIn[3], self.dataIn[4] = unpack("<BHHHH55x", buff)
                    #print(self.dataIn[0])
                    #if(self.dataIn[4]<30000):
                       # self.ADCbuff[0][self.dataIn[4]]=self.dataIn[1]
                   # if(self.dataIn[4]>29998):
                        #for i in range (0,30000):
                            #print("Position: ",i, "Data: ",self.ADCbuff[0][i])
                    #print(unpack("<B16s16s16sH13x", buff))
                    #print(packettype)
                    finally:
                        pass  
                else:   #bad reply
                    #print(unpack("<BHHHH55x", buff))
                    print(buff[0:63])
                    print("bad packet")
                    pass
                    #self.status = "Disconnected"
                    #self.sendQ.put(None)
                    #self.statusCallback.emit("Disconnected", "Bad packet")
            #self.ser.reset_input_buffer()
        #causes the write thread to wake up so that it can exit.
        self.sendQ.put(None)
    def returnData(self): #return data. Change this to a full buffer
        return self.dataIn  
    def returnPositions(self):
        return asarray(self.buffPosQueue)      
    def write_funct(self):
        """ The function that runs the write thread. This function writes packets from the sendQ to the serial port."""
        while self.status != "Disconnected":
            packet = self.sendQ.get()
            if packet:
                try:
                    self.ser.write(packet)
                except:
                    pass
        
    def close(self):
        """ Disconnects the device and indirectly shutdowns the read/write threads."""
        if self.status != "Disconnected":
            self.status = "Disconnected"
            self.ser.close()

#    def up64(self, bytes):
#        while(len(bytes) % 64 != 0):
#            bytes += [0]
#        return bytes
        
    def getSkips(self, freq, numSamples, fclk):
        """Calculates the sample period in clock cycles for a given frequency, sample number, and MCU clock speed"""
        return fclk / (freq * numSamples)
        
    def calc_val(self, freq):
        """Dynamically picks the best numSamples value, and corresponding values for the ARR/PSC registers."""
        fclk = 250e6
        skipGoal = 25 #minimum sample period target
        max_samples = 1024*4
        numSamples = max_samples
        #get close to the target sample period without going under
        while (skips := self.getSkips(freq, numSamples, fclk)) < skipGoal:     
            numSamples /= 2
            
        numSamples = int(numSamples)
        
        #calculate PSC and ARR from the sample period (skips)
        PSC = 1
        while (ARR := skips / PSC) > 2**16:
            PSC += 1
        PSC -= 1
        ARR = round(ARR - 1)
        
        return numSamples, ARR, PSC
        
        
    def sendWave(self, chan, freq = 1e3, wave_type = "sin", amplitude = 5, offset = 0, arbitrary_waveform = None, duty = 50, phase = 0, numPeriods = 1):
        """ Sends a waveform to the device.
        
        Parameters:
        chan (int): The channel to send the waveform to.
        freq (float): The frequency of the waveform.
        wave_type (str): The type of waveform to send.
        amplitude (float): The amplitude of the waveform.
        offset (float): The offset of the waveform.
        arbitrary_waveform (list of float): A user-defined function for arbitrary waveforms, defaults to None.
        duty (int): Duty cycle for square waves, defaults to 50 percent.
        phase (float): Phase shift for the waveform, defaults to 0.
        numPeriods (int): Number of periods to generate, defaults to 1.
        """
        if self.status == "Disconnected":
            return
    
        #move constants to init or something
        fclk = 250e6
        dac_bits = 12
        pwm_bits = 12
        offset_amp = 5
        PWM_ARR = 2**pwm_bits - 1
        gain_amp = [5, 0.5]
    
        #determines to use high or low gain
        if wave_type == "dc" or offset > 5:
            gain = 0
        else:
            gain = 0 if abs(amplitude) > 0.5 else 1
            
        #calculate offset CCR value for offset
        offset_pwm = max(min(offset, 5), -5)
        CCR_offset = max(min(math.floor((-offset_pwm + offset_amp) / (offset_amp * 2) * PWM_ARR), PWM_ARR), 0)
        offset_dac = offset - offset_pwm

        #determines numSamples, and ARR/PSC values 
        if wave_type == "dc": 
            numSamples, ARR, PSC = (2, int(2**15), 0)    
        else:
            numSamples, ARR, PSC = self.calc_val(freq)
        #skips_act = (PSC+1)*(ARR+1)
        
        
        #determines phase
        #this code is complicated because there are two waves of setting phase:
        #   1) shifting the samples, which has lower resolution but a full 360 deg range
        #   2) shifting the clock cycle on which the output starts, which has a resolution of 13.9 ns (at 72mhz)
        #we want to do both
        #PSC not being 0 makes things complicated and the functionality is not well tested for slow waves. 
        phase_clocks = numSamples * (ARR + 1) * phase
        
        #phase calibration, value (6) is random between devices
        if chan == 1:
            phase_clocks += 6 // (PSC + 1)
        
        phase_samples = int(phase_clocks / (ARR + 1)) / numSamples
        phase_arr = int(phase_clocks / (PSC + 1)) 
        phase_arr = phase_arr % (ARR + 1)
                
        #generate the samples
        dac_scale = (2**dac_bits) / 2
        samples = generateSamples(wavetype = wave_type, numSamples = numSamples, amplitude = amplitude / gain_amp[gain] * dac_scale, arbitrary_waveform = arbitrary_waveform, duty = duty, phase = phase_samples, offset = dac_scale + offset_dac / gain_amp[gain] * dac_scale, clamp = [0, 2**dac_bits - 1], numT = numPeriods)      
        samples = samples[1]
        mode = 1
        if mode == 1:
            #generate the packet
            bytes = pack("<BBBHHHHH51x", 1, chan, gain, PSC, ARR, CCR_offset, numSamples, phase_arr)
            sample_bytes = samplesToBytes(samples)
            assert len(bytes) % 64 == 0
            bytes += sample_bytes
            self.sendQ.put(bytes)
        else:
            #for oscilloscope
            adcclock=1
            sampletime=1
            offset_osc=int(0)
            attenuation=int(0)
            amp10=int(1)
            amp5=int(1)
            amp2_5=int(1)
            amp1=int(1)
            bytes = pack("<BBBBBBBBBB54x", 2, chan, adcclock, sampletime, offset_osc, attenuation, amp10, amp5, amp2_5, amp1)
            #sample_bytes = samplesToBytes(samples)
            #assert len(bytes) % 64 == 0
            #bytes += sample_bytes
            self.sendQ.put(bytes)            
    def sendScope(self, chan, mode, sampletime, offset_osc, attenuation, amp):
        if self.status == "Disconnected":
            return
        if amp==1:
            amp10=1
            amp5=0
            amp2_5=0
            amp1=0
        else:
            amp10=0
            amp5=1
            amp2_5=0
            amp1=0               
        bytes = pack("<10B54x", 2, chan, int(mode), sampletime, offset_osc, attenuation, amp10, amp5, amp2_5, amp1)
        self.sendQ.put(bytes)  
        pass
        
    def tryConnect(self, portName):
        """ Attempts to connect to the device."""
        if self.status != "Disconnected":
            return
            

            
        #add the "/dev/" for unix based systems 
        if os.name == "posix":
            portName = "/dev/" + portName
            
        try:
            self.ser = serial.Serial(portName, 500000, timeout = 5) #BAUD rate Doesnt actually matter
        except Exception as e:
            print(e)
            self.statusCallback.emit("Disconnected", "unable to open port")
            return
        
        self.status = "Connecting"
        
        self.sendQ = Queue()
        self.sendHandShakePacket()
        
        self.write_thread = threading.Thread(target=self.write_funct, args=())
        self.write_thread.start()
        #
        self.read_thread = threading.Thread(target=self.read_funct, args=())
        self.read_thread.start()
        
    def __init__(self, statusCallback):
        """ Initializes the connection object
        
        Parameters:
            statusCallback (pySignal): signal to use to send updates to the main UI
        """
        self.dataIn =[0,0,0,0,0]
        self.ADCbuff = np.zeros((2,30000))
        self.status = "Disconnected"
        self.statusCallback = statusCallback

        self.buffPosQueue = deque([],BUFFERSIZE)
        self.oscCh1Queue = deque([], BUFFERSIZE)
        self.lastPos = -1
        self.itteration = 0
