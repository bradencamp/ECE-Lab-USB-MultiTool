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

samples_f = []
samples_a = []

#for a in range(3, 6):
#	curM = pow(10, a)
#	nextM = pow(10, a + 1)
#	f = curM
#	while f < nextM:
#		if f > 300e3:
#			break
#		samples_f += [f]
#		f += nextM / 5
	
f = 1000
while f < 300e3:
	samples_f += [f]
	f += 1000
print(samples_f)
for f in samples_f:
	conn.sendWave(1, f, "sine", 0.5, 0)
	
	fs = f * 2000
	if fs > 25e6:
		fs = 25e6
	scope.open(dev, sampling_frequency=fs, buffer_size=0, offset=0, amplitude_range=2)
	x, t = scope.record(dev, 1)
	
	
	filter = min(fs / 20, 500e3)
	x = butter_lowpass_filter(x, filter, fs, 10)
	
	#plt.plot(t,x)
	#plt.title(f)
	#plt.show()
	
	#print(f, findMinMax(x), len(x), fs, filter)
	
	vmin, vmax = findMinMax(x)
	#amp = (vmax - vmin) / 10
	amp = (vmax - vmin) / 1
	samples_a += [amp]
	#if vmin > - 10 and vmax < 10:
	#	samples_a += [amp]
		
		

plt.plot(samples_f, samples_a, 'r')
plt.show()

#dev = device.open()
#fs = 5e06
#scope.open(dev, sampling_frequency=fs, buffer_size=0, offset=0, amplitude_range=10)
#x, t = scope.record(dev, 1)
#
#
#plt.subplot(131)
#plt.plot(t, x, 'r')
#
#X = butter_lowpass_filter(x, 500e3, fs, 10)
#
#plt.subplot(132)
#plt.plot(t, X, 'r')
#
#print(findMinMax(X))
#
#plt.show()