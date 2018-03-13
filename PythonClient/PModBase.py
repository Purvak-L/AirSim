from AirSimClient import *
# Persistent ModuleBase
class PModBase:
    def __init__(self, controller):
        self.controller = controller

    def get_name():
        raise NotImplementedError
    
    def get_client(self):
        return self.controller.get_client()

    def get_persistent_module(self, name):
        return self.controller.get_persistent_module(name)

    def start(self):
        raise NotImplementedError

    def update(self):
        raise NotImplementedError
    
    def stop(self):
        raise NotImplementedError