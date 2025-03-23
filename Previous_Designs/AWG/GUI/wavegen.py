import numpy as np
from math import floor

def lerp(a, b, f):
    """
    Performs linear interpolation between two values a and b.

    Parameters:
    a (float): The start value.
    b (float): The end value.
    f (float): The interpolation factor between 0 and 1, where 0 yields `a` and 1 yields `b`.

    Returns:
    float: The interpolated value between `a` and `b`.
    """
    return a * (1 - f) + (b * f)

def resample(samples, newNumSamples):
    """
    Resamples a sequence of data points to a new number of samples. (I don't think this is used anywhere but might be needed in the future)

    Parameters:
    samples (list of float): The original sequence of sample points.
    newNumSamples (int): The desired number of sample points in the resampled sequence.

    Returns:
    list of float: The resampled sequence of sample points.
    """
    if len(samples) == newNumSamples:
        return samples
    values = []
    for i in range(newNumSamples):
        pos = i / newNumSamples * len(samples)
        ind = floor(pos)
        ind2 = (ind + 1) % len(samples)
        f = pos - ind
        
        #print(i, pos, ind, ind2, f)
        values += [lerp(samples[ind], samples[ind2], f)]
    return values
        
def sample(samples, x):
    """Samples a list of points with linear interpolation.

    Given a floating-point index `x`, this function calculates the interpolated
    value using the fractional part of `x` to blend between the nearest sample
    points. `x` = 0 maps to the start of the list and `x` = 1 maps to the end of the list.

    Parameters:
    samples (list of float): The list of sample points to sample.
    x (float): A floating-point coordinate of where to sample.

    Returns:
    float: The interpolated value from the `samples` list at the index `x`.
    """
    x *= len(samples)
    ind = floor(x)
    ind2 = (ind + 1) % len(samples)
    f = x - ind
    return lerp(samples[ind], samples[ind2], f)
    
def generateSamples(wavetype = "sine", numSamples = 1024, amplitude = 5, arbitrary_waveform = None, duty = 50, phase = 0, offset = 0,
                    timeRange = 1, clamp = None, numT = 1):
    """Generates a waveform of the given type and parameters.
    
    Parameters:
    wavetype (str): Type of the waveform to generate, defaults to "sine".
    numSamples (int): Number of samples to generate, defaults to 1024.
    amplitude (float): The peak amplitude of the waveform, defaults to 5.
    arbitrary_waveform (list of float): A list of samples for the user-defined arbitrary waveforms, defaults to None.
    duty (int): Duty cycle for square waves, defaults to 50 percent.
    phase (float): Phase shift for the waveform, defaults to 0.
    timeRange (float): The time range over which to generate the waveform, defaults to 1.
    clamp (function or None): An optional function to clamp values, defaults to None (no clamping is done).
    numT (int): Number of periods to generate, defaults to 1.
    
    Returns:
        Tuple of (time, voltage)
    """
    t = np.linspace(0, numT, numSamples, endpoint=False)
    tt = t   
    phase = float(phase)
    t = np.mod(t + phase, 1)

    match wavetype:
        case 'arbitrary':
            y = np.zeros(numSamples)
            for i in range(numSamples):
                y[i] = sample(arbitrary_waveform, t[i])
        case 'sine':
            y = np.sin(2 * np.pi * t)
        case 'triangle':
            t = np.mod(t + 0.25, 1)
            y = (np.mod(t * 2, 1) * -(np.floor(t * 2) * 2 - 1) + np.floor(t * 2)) * 2 - 1
        case 'square':
            y = np.ones(numSamples)
            y[t >= float(duty) / 100] = -1
        case 'sawtooth':
            t = np.mod(t + 0.5, 1)
            y = np.mod(t * 2, 2) - 1
        case 'dc'
            y = np.zeros(numSamples)
        case _:
            print("Illegal wavetype!") # should this be an Exception?

    tt = tt * timeRange
    y = y * amplitude + offset
    if clamp:
        np.clip(y, clamp[0], clamp[1], y)
    return (tt, y)


def samplesToBytes(samples):
    """converts a list of samples to bytes. The samples will be stored in 16 bit (2 byte) little endian. The bytearray's length will be padded to the nearest multiple of 64.

    Parameters:
        samples (list of float): samples to convert to bytes
    
    Returns:
        Bytearray(?) representing the samples.
    
    """
    ns = len(samples)
    if ns % 64 != 0:
        add = 64 - (ns % 64)
        samples = np.pad(samples, (0,add), 'constant', constant_values=(0,))

    return samples.astype(dtype = "<u2", casting='unsafe').tobytes()
