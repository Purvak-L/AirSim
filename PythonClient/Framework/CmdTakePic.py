from CmdBase import *
from PersistentModules import *

# Cmd
# camera
class CmdTakePic(CmdBase):
    def __init__(self, controller, line, engage_object):
        super().__init__(controller, line, engage_object)
        
    def start(self):
        # Engage pic camera front for now
        self.camera_module = self.get_persistent_module('camera')
        self.camera_module.get_camera(0).add_image_type('scene')

    def update(self):
        img = self.camera_module.get_image(0, 'scene') # Returns Image Object
        # do something with image
        # TODO

        # Disengage Camera module
        self.camera_module.get_camera(0).remove_image_type('scene')

        # update engage_object
        self.engage_object.mark_done(img)
        return True

    def can_process(line):
        if line[0] in ['camera']:
            return True
        return False
