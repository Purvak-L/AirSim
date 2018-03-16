from CmdBase import *
from AirSimClient import *
from PersistentModules import *

#Cmd
# reset
class CmdReset(CmdBase):
    def __init__(self, controller, line, engage_object):
        super().__init__(controller, line, engage_object)
    
    def start(self):
        self.mystate_module = self.get_persistent_module('mystate')
        self.constants_module = self.get_persistent_module('constants')
        self.get_client().moveToPosition(0, 0, 0, self.constants_module.standard_speed, 0)
        self.final_location = [0, 0, 0.68]
    
    def update(self):
        locationVec = list(self.mystate_module.get_position())
        if ((self.final_location[0] - locationVec[0])**2 + (self.final_location[1] - locationVec[1])**2
            + (self.final_location[2] - locationVec[2])**2)**(1/2) < 2:
            if self.engage_object != None:
                self.engage_object.mark_done()
            return True
        return False
    
    def stop(self):
        pass
    
    def can_process(line):
        if line[0] in ['reset']:
            return True
        return False
