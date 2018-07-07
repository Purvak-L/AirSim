import setup_path 
import airsim
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
    
    def logger(self):
        return self.logger_module

    def log(self, msg):
        self.logger().log(type(self).get_name(), msg)
    
    def log_error(self, msg):
        self.logger().log_error(type(self).get_name(), msg)

    def log_warning(self, msg):
        self.logger().log_warning(type(self).get_name(), msg)

    def start(self):
        self.logger_module = self.get_persistent_module('logger')
        self.log("Starting..")

    def update(self):
        raise NotImplementedError
    
    def stop(self):
        self.log("Stopping..")