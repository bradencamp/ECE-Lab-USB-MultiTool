from input_field import Input
from PyQt6.QtWidgets import QWidget, QLabel, QHBoxLayout


class LabelField(QWidget):
    #properites to ensure that internal field values are always the same as this class
    @property
    def range(self):
        return self._range
    @range.setter
    def range(self,newRange):
        self._range = newRange
        self.input_field.range = newRange

    @property
    def prefixes(self):
        return self._prefixes
    @prefixes.setter
    def prefixes(self,newPre):
        self._prefixes = newPre
        self.input_field.prefixes = newPre

    @property
    def def_unit(self):
        return self._def_unit
    @def_unit.setter
    def def_unit(self,newUnit):
        self._def_unit = newUnit
        self.input_field.def_unit = newUnit 

    @property
    def callback_update(self):
        return self._callback_update       
    @callback_update.setter
    def callback_update(self, new_callback):
        self._callback_update = new_callback
        self.input_field.callback_update = new_callback

    @property
    def numDec(self):
        return self._numDec
    @numDec.setter
    def numDec(self, dec):
        self._numDec = dec
        self.input_field.numDec = dec

    def doNothing():
        return
    def getVal(self):
        return self.input_field.value
    def __init__(self, text:str, range:list[float], init_val:float, precision:int,def_unit:str, prefixes = [], callback_update = doNothing,*args, **kwargs):
        super(LabelField, self).__init__()

        self.input_field = Input(callback_update,range,init_val,precision,def_unit,prefixes,*args, **kwargs)
        self.callback_update = callback_update
        self.range = range
        self.prefixes = prefixes
        self.def_unit = def_unit
        self.numDec = precision
        self.label = QLabel(text)
        layout = QHBoxLayout()
        
        layout.addWidget(self.label)
        layout.addWidget(self.input_field)
        self.setLayout(layout)
        #Input(self.generate_waveform, [1, 250e3], float(1000), "hz", prefixes_f)
    def printVal(self):
        print(self.input_field.value)

#testing function
if __name__ == "__main__":
    print("Hello, World!")
    from PyQt6.QtWidgets import QApplication, QMainWindow
    app = QApplication([])
    window = QMainWindow()
    field = LabelField("hallo",[0,10],5,1,"Hz",{"m": 1e-3,"":1}) 
    field.callback_update = field.printVal
    window.setCentralWidget(field)
    window.show()
    app.exec()

