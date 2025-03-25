# Python libraries needed
- time
- Pyserial
- Serial
- PyQt5
- NumPy
- PyQtGraph
# Instructions

- For the GUI to run, the port and baudrate number needs to match the MCU's serial. 
- The board also needs to be connected for it to work.
- To change the port and baudrate number, change reader = SerialReader(port='COM7', baudrate=12000000) in line 400 of the code.
- COM7 can be changed to COM# depending on the port number in the Device Manager of Windows.
- The main function "def update():" is the main loop that collects the data and plots it.

# Improvments to the code

- Implementing the "time" function as the code is getting the ADC data can be used to set a time function that goes to the x-axis.

- using NumPy's FFT function can be used to show the frequincy number being generated.

- Creating an automatic COM port detector to remove the need of updating it for each new device.

What can suffice is using this example:
```python
	com_number, ok = QtGui.QInputDialog.getText(None, "COM Port", "Enter COM#:")
	if ok:
		ser = serial.Serial(f"COM{com_number}", 12000000)
	else:
		print("Wrong COM port, exiting...")
		exit()
```
This  will prompt a window to input the COM# before opining the GUI.

# FIXME
- add trigger function.
