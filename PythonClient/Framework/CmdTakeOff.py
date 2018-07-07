from CmdBase import *
from PersistentModules import *

#Cmd 
# takeoff
class CmdTakeoff(CmdBase):
    def __init__(self, controller, line, engage_object):
        super().__init__(controller, line, engage_object)
    
    def start(self):
        self.get_client().takeoff(8)
    
    def update(self):
        return True
    
    def stop(self):
        pass
    
    def can_process(line):
        if line[0] in ['takeoff']:
            return True
        return False
