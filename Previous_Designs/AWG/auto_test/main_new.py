import matplotlib.pyplot as plt
import numpy as np
from numpy.fft import fft, ifft
from scipy.signal import butter,filtfilt
import math
import sys
#sys.path.insert(1, 'C:\\Users\\foobar\\Desktop\\AWG\\GUI')
from connection import Connection
import time

import device
import scope

def butter_lowpass_filter(data, cutoff, fs, order):
    normal_cutoff = cutoff / (fs / 2)
    # Get the filter coefficients 
    b, a = butter(order, normal_cutoff, btype='low', analog=False)
    y = filtfilt(b, a, data)
    return y

def findMinMax(data):
    max = -1e9
    min = 1e9
    for d in data:
        if d > max:
            max = d
        if d < min:
            min = d    
    return (min, max)

def foo(a, b):
    pass
conn = Connection(foo)
conn.tryConnect()

dev = device.open()

#conn.sendWave(0, 1, "testac", 0, pwm_off, forceGain = gain)
#conn.sendWave(1, 1, "testac", 0, pwm_off, forceGain = gain)
def test(sub,amp,pwm_off, gain):###################
    samples_f = []

    f = 1000
    while f < 300e3:
        samples_f += [f]
        f += 10000###########herer50000
    print(samples_f)

    result = [[],[]]
    for f in samples_f:
# sendWave(self, chan, freq, wave_type, amplitude, offset,
        conn.sendWave(0, f, "sine", amp, pwm_off)
        conn.sendWave(1, f, "sine", amp, pwm_off)
        time.sleep(0.1)
        fs = f * 2000#changer gere2000
        if fs > 25e6:
            fs = 25e6
                        
        scope.open(dev, sampling_frequency=fs, buffer_size=0, offset=0, amplitude_range=20)
        x0, t = scope.record(dev, 1)
        x1, t = scope.record(dev, 2)
    
        
        divider = 1 if gain == 1 else 10
        
        vmin0, vmax0 = findMinMax(x0)
        #amp = (vmax - vmin) / 10
        amp0 = (vmax0 - vmin0) / divider
        result[0] += [amp0]
        
        vmin1, vmax1 = findMinMax(x1)
        #amp = (vmax - vmin) / 10
        amp1 = (vmax1 - vmin1) / divider
        result[1] += [amp1]
        #if vmin > - 10 and vmax < 10:
        #    samples_a += [amp]
        
    print(samples_f, result)
    plt.subplot(sub)
    plt.plot(samples_f, result[1], 'y')
    plt.plot(samples_f, result[0], 'r')
    #plt.title("test")
   # plt.legend(["slope: {} \noffset: {}({})".format(slope0, inter0, round(inter0 - pwm_off, 3)), "slope: {} \noffset: {}({})".format(slope1, inter1, round(inter1 - pwm_off, 3))])
    plt.title(" pwm_offset={}, gain={}".format(pwm_off, "high" if gain == 1 else "low"))

#plt.title("low gain,offset = 0")


# gain_value\offset
test(231, 5, 0, 0)      # low gain, off = 0
test(232, 5, 5, 0)      # low gain, off = 5
test(233, 5, -5, 0)     # low gain, off = -5
test(234, 0.5, 0, 1)    # high gain, off = 0
test(235, 0.5, 5, 1)    # high gain, off = 5
test(236, 0.5, -5, 1)   # high gain, off = -5
plt.show()




#######################offset he amplitude combitation:高高 高低 底稿 低低
