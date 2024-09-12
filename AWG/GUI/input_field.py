from PyQt6.QtWidgets import QLineEdit

def findBestPrefix(val, prefixes):
    """ Finds the best prefix for a given value.
    
    Parameters:
    val (float): The value to find the best prefix for.
    prefixes (dict of str:int): dictionary holding prefixes (m for milli, k for kilo, etc) mapped to their value.
    
    Returns: 
    (float, str): The value with the best prefix, and the prefix itself."""
    for p in prefixes:
        n_val = val / prefixes[p]
        if n_val >= 1 and n_val < 1e3:
            return (n_val, p)
    return (val, "")
            
def endsWithLower(s, endsWithStr):
    """ Checks if a string ends with another string, ignoring case.
    
    Parameters:
    s (str): the string to test
    endsWithStr (str):  the ending
    
    Returns: boolean
    """
    return s[-len(endsWithStr):].lower() == endsWithStr.lower()
        
def parseStringToVal(str_in, prefixes, expected_unit):
    """ Parses a string into a value.
    
    Parameters:
    str_in (str): The string to parse.
    prefixes (dict of str:int): dictionary holding prefixes (m for milli, k for kilo, etc) mapped to their value.
    expected_unit (str): The expected unit of the value.
    
    Returns:
    float: The value parsed from the string, or None if the string could not be parsed.
    """
    str_in = str_in.replace(" ", "")
    
    if endsWithLower(str_in, expected_unit):
        str_in = str_in[:-len(expected_unit)]
        
    mag = 1
    for p in prefixes:
        if endsWithLower(str_in, p):
            str_in = str_in[:-len(p)]
            mag = prefixes[p]
    
    try:
        val = float(str_in)
    except Exception as e:
        return None
        
    return val * mag
    
def clamp(val, minVal, maxVal):
    """Clamps a value to a given range.
    
    Parameters:
    val (float): The value to clamp.
    minVal (float): The minimum value of the range.
    maxVal (float): The maximum value of the range.
    
    Returns:
    float: The clamped value.
    """
    return float(min(maxVal, max(minVal, val)))
        
class Input(QLineEdit):
    """Handles a text input box with automatic range clamping, unit display, scrolling"""

    def editFin(self):
        """Function called when the user has finished editing the text box. If invalid value is entered, the text box is reset to the previous value."""
        val = parseStringToVal(self.text(), self.prefixes, self.def_unit)
        if val is None:
            self.undo()
        else:
            self.setVal(val)
            
    def keyPressEvent(self, event):
        """Event handler for key input. If the up or down arrow keys are pressed, the value is incremented or decremented by 1, respectively.

        Parameters:
        event (QKeyEvent): The key event that was triggered.
        """
        if event.key() == 16777235: 
            self.setVal(self.value + 1)
        elif event.key() == 16777237: 
            self.setVal(self.value - 1)
        else:
            QLineEdit.keyPressEvent(self, event)
            
    def wheelEvent(self, event):
        """Event handler for mouse scrolling. The value is incremented or decremented based on the scroll direction.
        
        Parameters:
        event (QKeyEvent): The key event that was triggered.
        """
        self.setVal(self.value + event.angleDelta().y() / 120)
        event.accept()
            
    def setVal(self, val, runCallback = True):
        """ Sets the value of the text box.
        
        Parameters:
        val (float): The value to set the text box to.
        runCallback (bool): Whether or not to run the callback function after setting the value, defaults to True. This can be used to update a textbox when a different textbox is updated (for example have the frequency update when period is changed and viceversa), without causing a infinite loop of updates. But currently this isn't used.
        """
        val = clamp(val, self.range[0], self.range[1])
        self.value = val
        val, prefix = findBestPrefix(val, self.prefixes)
        self.setText(f"{val} {prefix}{self.def_unit}")
        if runCallback:
            self.callback_update()
        
    def __init__(self, callback_update, range, init_val, def_unit, prefixes = [], *args, **kwargs):
        """Initializes the object
        
        Parameters:
        callback_update (funct): function to call when the value is changed
        range (tuple (float, float)): a tuple holding the min and max values the input value can be.
        init_val (float): the initial value of the input box
        def_unit (str): the unit symbol (such as "v" or "hz")
        prefixes (dict of str:float): dictionary holding prefixes (m for milli, k for kilo, etc) mapped to their value.
        *args: extra args
        **kwargs: extra args
        """
        QLineEdit.__init__(self, *args, **kwargs)
        self.editingFinished.connect(self.editFin)
        self.callback_update = callback_update
        self.range = range
        self.prefixes = prefixes
        self.def_unit = def_unit
        self.setVal(init_val)