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

offset_new_x = []
offset_new_y = [[], [], []]

scope.open(dev, sampling_frequency=5e6, buffer_size=0, offset=0, amplitude_range=10)

def slope_inter(x, y):
	par = np.polyfit(x, y, 1, full=True)
	slope=round(par[0][0],3)
	intercept=round(par[0][1],3)
	return (slope, intercept)

def test(sub, gain, samples, dac_offset):
	result = [[], []]
	conn.sendWave(0, 1, "testdc", 0, samples[0], forceGain = gain)
	conn.sendWave(1, 1, "testdc", 0, samples[0], forceGain = gain)
	time.sleep(2)
	for x in samples:
		conn.sendWave(0, 1, "testdc", dac_offset, x,  forceGain = gain)
		conn.sendWave(1, 1, "testdc", dac_offset, x,  forceGain = gain)
		time.sleep(0.25)
		x0, t = scope.record(dev, 1)
		x1, t = scope.record(dev, 2)
		result[0] += [avg(x0)]
		result[1] += [avg(x1)]
				
	plt.subplot(sub)
	plt.plot(samples, result[1], 'y')
	plt.plot(samples, result[0], 'r')
	size5 = 5 
	size05 = 4
	plt.plot([0, 0], [dac_offset -size5, dac_offset + size5], '--b')
	plt.plot([-size5, size5], [dac_offset, dac_offset], '--b')
	
	slope0, inter0 = slope_inter(samples, result[0])
	slope1, inter1 = slope_inter(samples, result[1])	
	plt.legend(["slope: {} \noffset: {}({})".format(slope0, inter0, round(inter0 - dac_offset, 3)), "slope: {} \noffset: {}({})".format(slope1, inter1, round(inter1 - dac_offset, 3))])

	plt.title("offset sweep {}:{} dac={}, gain={}".format(round(min(samples), 3), round(max(samples), 3), dac_offset, "high" if gain == 0 else "low"))
	
offset_new_y = []
offset = -5
while offset <= 5:
	offset_new_y += [offset]
	#offset += 1
	offset += 1
offset = -5

print(offset_new_y)
#(sub, gain, offset_new, dac_samples)
test(231, 0, offset_new_y, 0)
test(232, 0, offset_new_y, 5)
test(233, 0, offset_new_y, -5)
test(234, 1, offset_new_y, 0)
test(235, 1, offset_new_y,.5)
test(236, 1, offset_new_y, -.5)
plt.show()