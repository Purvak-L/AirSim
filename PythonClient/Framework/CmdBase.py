from AirSimClient import *
from PersistentModules import *
# CmdBase 
class CmdBase:
    def __init__(self, controller, line, engage_object):
        self.controller = controller
        self.line = line
        self.engage_object = engage_object
        self.command = line[0]

    def start(self):
        raise NotImplementedError
    
    def update(self):
        raise NotImplementedError
    
    def get_client(self):
        return self.controller.get_client()

    def get_module(self, name):
        return self.controller.get_module(name)

    def get_persistent_module(self, name):
        return self.controller.get_persistent_module(name)
    
    # Inheritable Static Method
    def can_process(line):
        raise NotImplementedError
