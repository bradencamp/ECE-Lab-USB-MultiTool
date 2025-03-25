import matplotlib.pyplot as plt
import numpy as np
from numpy.fft import fft, ifft
from scipy.signal import butter,filtfilt
import math
import sys
sys.path.insert(1, 'C:\\Users\\foobar\\Desktop\\AWG\\GUI')
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

def avg(x):
	avg = 0
	for n in x:
		avg += n
	return avg / len(x)
	
def foo(a, b):
	pass
conn = Connection(foo)
conn.tryConnect()

dev = device.open()

samples_x = []
samples_y = [[], [], []]

scope.open(dev, sampling_frequency=5e6, buffer_size=0, offset=0, amplitude_range=10)

offset = -5
while offset <= 5:
	conn.sendWave(0, 1, "testdc", 0, offset)
	time.sleep(1)
	x, t = scope.record(dev, 1)
	samples_y[0] += [avg(x)]
	
	conn.sendWave(0, 1, "testdc", 5, offset)
	time.sleep(0.1)
	x, t = scope.record(dev, 1)
	samples_y[1] += [avg(x)]
	
	conn.sendWave(0, 1, "testdc", -5, offset)
	time.sleep(0.1)
	x, t = scope.record(dev, 1)
	samples_y[2] += [avg(x)]
	
	#x = butter_lowpass_filter(x, 1e6, 5e6, 10)
	
	#plt.plot(t, x, 'r')
	#plt.show()

	samples_x += [offset]
	offset += 2.5

par = np.polyfit(samples_x, samples_y[0], 1, full=True)
slope=par[0][0]
intercept=par[0][1]
plt.subplot(131)
plt.plot(samples_x, samples_y[0], 'r')
plt.plot([0, 0], [-5, 5], '--b')
plt.plot([-5, 5], [0, 0], '--b')
plt.text(-4, 4, "slope: " + str(round(slope, 3)) + "\noffset: " + str(round(intercept, 3)))

par = np.polyfit(samples_x, samples_y[1], 1, full=True)
slope=par[0][0]
intercept=par[0][1]
plt.subplot(132)
plt.plot(samples_x, samples_y[1], 'r')
plt.plot([0, 0], [0, 10], '--b')
plt.plot([-5, 5], [5, 5], '--b')
plt.text(-4, 9, "slope: " + str(round(slope, 3)) + "\noffset: " + str(round(intercept, 3)))

par = np.polyfit(samples_x, samples_y[2], 1, full=True)
slope=par[0][0]
intercept=par[0][1]
plt.subplot(133)
plt.plot(samples_x, samples_y[2], 'r')
plt.plot([0, 0], [0, -10], '--b')
plt.plot([-5, 5], [-5, -5], '--b')
plt.text(-4, -1, "slope: " + str(round(slope, 3)) + "\noffset: " + str(round(intercept, 3)))

#plt.xlabel("requested offset (V)")
#plt.ylabel("offset measured (V)")
plt.show()

