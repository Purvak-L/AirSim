from PModBase import *

class PModConstants(PModBase):
    def __init__(self, controller):
        super().__init__(controller)
        self.standard_speed = 5 # 5m/s
        self.no_of_cameras = 5 

    def get_name():
        return 'constants'

    def start(self):
        super().start()

    def update(self):
        pass

    def stop(self):
        super().stop()
