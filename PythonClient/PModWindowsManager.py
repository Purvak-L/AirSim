from PModBase import *
import cv2 

# Dependency Camera Module 
class PModWindowsManager(PModBase):
    def __init__(self, controller):
        super().__init__(controller)
        self.windows = {}
    
    def get_name():
        return 'windows_manager'

    def start(self):
        super().start()
        self.camera_module = self.get_persistent_module('camera')

    def stop(self):
        super().stop()

    def update(self):
        for k, fun in self.windows.copy().items():
            cv2.imshow(k, fun())

    def add_window_by_camera(self, camera_id, image_type):
        name = "Camera_" + str(camera_id) + "_" + image_type
        self.camera_module.get_camera(camera_id).add_image_type(image_type)
        self.add_window(name, lambda: self.camera_module.get_image(camera_id, image_type).image_data)
        self.log("Added a new window for camera view: camera = {0} view = {1}".format(camera_id, image_type))

    def remove_window_by_camera(self, camera_id, image_type):
        name = "Camera_" + str(camera_id) + "_" + image_type
        self.camera_module.cameras[camera_id].remove_image_type(image_type)
        self.remove_window(name)
        self.log("Removed a window for camera view: camera = {0} view = {1}".format(camera_id, image_type))

    def add_window(self, name, image_function):
        if name in self.windows.keys():
            raise KeyError("Window already exists")
        self.windows[name] = image_function
        self.log("Added a new window: window_name = {0}".format(name))

    def remove_window(self, name):
        self.windows.pop(name, None)
        cv2.destroyWindow(name) 
        self.log("Removed a window (if exists): window_name = {0}".format(name))