import setup_path 
import airsim

from DLogTime import *
from PersistentModules import *
from Modules import *
from Commands import *

import cv2
import time

# Main Controller
class Controller:
    def __init__(self, persistent_module_classes, persistent_module_helper_classes, 
            module_classes, instant_command_classes, buffered_command_classes):
        # Connect Simulator
        self.client = airsim.MultirotorClient()
        self.client.confirmConnection()
        self.client.enableApiControl(True)

        # Persistent Modules
        self.persistent_modules = {}
        
        for c in persistent_module_classes:
            self.persistent_modules[c.get_name()] = c(self)

        # start all persistent modules
        for k, mod in self.persistent_modules.items():
            mod.start()

        # Persistent Module Helpers TODO Do something about this
        self.persistent_module_helpers = {}
        self.persistent_module_helpers['camera_helper'] = PModHCameraHelper(self.persistent_modules)

        # Modules 
        self.modules = {}

        for c in module_classes:
            self.modules[c.get_name()] = c(self)

        # Commands
        self.commands = []
        self.commands_buffer = []

        # Vars
        self._iteration = 0

        # Command Classes
        self.instant_command_classes = instant_command_classes
        self.buffered_command_classes = buffered_command_classes

        # Enable performance logger
        self.perf_logger = DModLogger(self)

        # Keep logger module ready 
        self.logger_module = self.get_persistent_module('logger')

        # Test
        self.persistent_modules['windows_manager'].add_window_by_camera(0, 'scene')
        self.persistent_modules['windows_manager'].add_window_by_camera(0, 'depth')
        self.persistent_modules['windows_manager'].add_window_by_camera(4, 'scene')
        #self.persistent_modules['windows_manager'].add_window_by_camera(0, 'depth_perspective')
        self.commands_buffer.append(self.get_command_object(['up', '5m'], None))
        self.commands_buffer.append(self.get_command_object(['down', '5m'], None))
        # self.get_module('camera_gimble').start()
        # self.get_module('camera_gimble').get_camera(4).set_gimble_params(type(self).get_name(), -10, 0, 180)
        # self.get_module('camera_gimble').get_camera(4).enable_gimble(type(self).get_name())
        #self.commands_buffer.append(self.get_command_object(['up', '3m'], None))
        #self.commands_buffer.append(self.get_command_object(['cancel'], None))

        # End Test
    
    def get_name():
        return "controller"

    def logger(self):
        return self.logger_module

    def log(self, msg):
        self.logger().log(type(self).get_name(), msg)
    
    def log_error(self, msg):
        self.logger().log_error(type(self).get_name(), msg)

    def log_warning(self, msg):
        self.logger().log_warning(type(self).get_name(), msg)

    def get_persistent_module(self, name):
        return self.persistent_modules.get(name)

    def get_module(self, name):
        return self.modules.get(name)
    
    def get_client(self):
        return self.client

    def cancel_all_commands(self):
        for c in self.commands_buffer:
            if c.engage_object != None:
                c.engage_object.mark_cancelled()
        self.commands_buffer = []
        self.log("Cancelled all commands")
        self.cancel_current_commands()
        
    def cancel_current_commands(self):
        for c in self.commands:
            if c.engage_object != None:
                c.engage_object.mark_cancelled()
        self.commands = []
        self.client.hover()
        self.log("Cancelled current commands, putting drone to hover mode")

    def get_command_object(self, line, engage_object):
        cmd = None
        for c in self.instant_command_classes + self.buffered_command_classes:
            if c.can_process(line):
                cmd = c(self, line, engage_object)
        return cmd

    # TODO update this, its a bad practice to assume that it will work -,-, be optimistic though ;)
    def add_command(self, line, engage_object = None):
        cmd = self.get_command_object(line, engage_object)
        if cmd is None:
            engage_object.data = b"Unknown Command"
            engage_object.status = -1
            engage_object.done = True
            self.log("Unknown command : {0} with id = {1}".format(line, engage_object.id 
                        if engage_object else "None"))
            return 
        elif type(cmd) in self.buffered_command_classes:
            print("Detected a move command " + str(line))
            self.commands_buffer.append(cmd)
            self.log("Added new command to command_buffer, {0} with id = {1}".format(line, engage_object.id 
                        if engage_object else "None"))
        else:
            cmd.start() # Start now as it is not a movement command
            self.commands.append(cmd)
            self.log("Added new command to commands array, {0} with id = {1}".format(line, engage_object.id 
                        if engage_object else "None"))
        return True

    def flist_repr(l):
        assert type(l) == list
        ans = '['
        for i in l:
            ans += ' {0:.3f}'.format(i)
        return ans + ']'
    
    def control(self):
        print(list(self.persistent_modules['mystate'].get_position()))
        t_old = time.time()
        t_old_log = time.time()
        self.total_iterations = 0
        while(True):
            self._iteration += 1
            self.total_iterations += 1
            self.log("Iteration : {0}".format(self.total_iterations))

            # Print location every 1 seconds
            d_time = time.time() - t_old
            if d_time > 1:
                msg ='{0:.2f}'.format(self._iteration/d_time) + " " + Controller.flist_repr(list(
                    self.persistent_modules['mystate'].get_position())) + " " + str(
                    self.persistent_modules['intent_provider'])
                print(msg)
                # More verbose
                msg ='FPS = {0:.2f}'.format(self._iteration/d_time) + " Loc = " + Controller.flist_repr(
                    list(self.persistent_modules['mystate'].get_position())) + " Intent =" + str(
                    self.persistent_modules['intent_provider'])
                self.log(msg)
                self._iteration = 00
                t_old = time.time()

            # Print performance log every 5 seconds
            d_time = time.time() - t_old_log
            if d_time > 15:
                msg = str(self.perf_logger)
                print(msg)
                self.log(msg)
                t_old_log = time.time()
            
            # Update persistent modules
            for k in self.persistent_modules.keys():
                self.perf_logger.start(k)
                self.persistent_modules[k].update()
                self.perf_logger.stop(k)

            # Update persistent module helpers
            for k, mod in self.persistent_module_helpers.items():
                #self.perf_logger.start(k)
                mod.update()
                #self.perf_logger.stop(k)
            
            # Update Modues
            for k, mod in self.modules.items():
                if mod.enabled:
                    self.perf_logger.start(k)
                    mod.update()
                    self.perf_logger.stop(k)

            # Update current commands
            cpoplist = []
            for c in self.commands:
                self.perf_logger.start(type(c).__name__)
                ans = c.update()
                self.perf_logger.stop(type(c).__name__)
                if ans == True:
                    # print(list(self.persistent_modules['mystate'].get_position()))
                    cpoplist.append(c)
                    self.log("Completed command, {0} with id = {1}".format(c.line, c.engage_object.id 
                        if c.engage_object else "None"))
            
            for c in cpoplist:
                try:
                    self.commands.remove(c)
                    self.log("Removed a completed command, {0} with id = {1}".format(c.line, c.engage_object.id 
                        if c.engage_object else "None"))
                except ValueError: # Case when command was cancel to clear all commands
                    pass

            # Add new commands if any
            if len(self.commands) == 0:
                cmd = 0
                try:
                    cmd = self.commands_buffer.pop(0)
                except IndexError:
                    pass
                if cmd != 0:
                    print("cmd" + cmd.command)
                    self.log("Starting processing of a new  buffered_command, {0} with id = {1}".format(
                        cmd.line, cmd.engage_object.id if cmd.engage_object else "None"))
                    cmd.start()
                    self.commands.append(cmd)

            # Add for cv2.imshow() to work
            key = cv2.waitKey(1) & 0xFF
            if (key == 27 or key == ord('q') or key == ord('x')):
                break

ctrl = Controller(persistent_module_classes, persistent_module_helper_classes,
     module_classes, instant_command_classes, buffered_command_classes)
ctrl.control()

'''
Controller
HTTPServer

Mystate

CameraFeed
Stabilize
DQN

Debug
ModWindowsManager
Logging
'''
