from AirSimClient import *
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

# Cmd
# 'forward [float(m/s)]'
# 'backward [float(m/s)]'
# 'up [float(m/s)]'
# 'down [float(m/s)]'
# 'left [float(m/s)]'
# 'right [float(m/s)]'
class CmdMove(CmdBase):
    def __init__(self, controller, line, engage_object = None):
        super().__init__(controller, line, engage_object)
        self.final_location = None
        self.constants_module = self.get_persistent_module('constants')
        # Set default if not specified
        self.distance_param = line[1]
        if self.distance_param == 'null':
            self.distance_param = '1m'
        self.param_mode = self.distance_param[-1] 
        self.distance_param = self.distance_param[:-1]
        if self.param_mode == 's':
            self.distance_param = str(float(self.distance_param) * self.constants_module.standard_speed)
        #print(self.command + " " + self.distance_param)

    def start(self):
        self.mystate_module = self.get_persistent_module('mystate')
        locationVec = list(self.mystate_module.get_position())
        offset = [0, 0, 0]
        #print(locationVec)
        # Process command
        yaw = AirSimClientBase.toEulerianAngle(self.mystate_module.get_orientation())[2]
        if self.command == 'up':
            offset[2] -= float(self.distance_param)
        elif self.command == 'down':
            offset[2] += float(self.distance_param)
        elif self.command == 'forward':
            offset[0] += float(self.distance_param) * math.cos(yaw)
            offset[1] += float(self.distance_param) * math.sin(yaw)
        elif self.command == 'backward':
            offset[0] -= float(self.distance_param) * math.cos(yaw)
            offset[1] -= float(self.distance_param) * math.sin(yaw)
        elif self.command == 'right':
            offset[0] += float(self.distance_param) * math.sin(yaw)
            offset[1] += float(self.distance_param) * math.cos(yaw)
        elif self.command == 'left':
            offset[0] -= float(self.distance_param) * math.sin(yaw)
            offset[1] -= float(self.distance_param) * math.cos(yaw)

        # add to location
        locationVec[0] += offset[0]
        locationVec[1] += offset[1]
        locationVec[2] += offset[2]
        self.final_location = locationVec
        #print(self.final_location)

        # Note that this call is cancellable if other movement related call is called
        self.get_client().moveToPosition(self.final_location[0], self.final_location[1], self.final_location[2],
            self.constants_module.standard_speed, 0)
    
    def update(self):
        locationVec = list(self.mystate_module.get_position())
        # Check if movement is complete or < 0.5 meters distance, anyway thats offset
        if ((self.final_location[0] - locationVec[0])**2 + (self.final_location[1] - locationVec[1])**2
            + (self.final_location[2] - locationVec[2])**2)**(1/2) < 0.5:
            #print("inside " + str(self.engage_object))
            if self.engage_object != None:
                self.engage_object.mark_done()
            return True
        return False
        
    def can_process(line):
        if line[0] in ['forward', 'backward', 'up', 'down', 'left', 'right']:
            return True
        return False

# Cmd
# move float float float
class CmdMoveToPoint(CmdBase):
    def __init__(self, controller, line, engage_object = None):
        super().__init__(controller, line, engage_object)
        self.final_location = None
        # Set default if not specified
        self.final_location = [float(line[1]), float(line[2]), float(line[3])]

    def start(self):
        self.mystate_module = self.get_persistent_module('mystate')
        self.constants_module = self.get_persistent_module('constants')
        # Note that this call is cancellable if other movement related call is called
        self.get_client().moveToPosition(self.final_location[0], self.final_location[1], self.final_location[2],
            self.constants_module.standard_speed, 0)

    def update(self):
        locationVec = list(self.mystate_module.get_position())
        # Check if movement is complete or < 0.5 meters distance, anyway thats offset
        if ((self.final_location[0] - locationVec[0])**2 + (self.final_location[1] - locationVec[1])**2
            + (self.final_location[2] - locationVec[2])**2)**(1/2) < 0.5:
            if self.engage_object != None:
                self.engage_object.mark_done()
            return True
        return False

    def can_process(line):
        if line[0] in ['move'] and type(float(line[1]) + float(line[2]) + float(line[3])) is float:
            return True
        return False

# Cmd
# turn left deg
# turn right deg
# turn to deg
class CmdRotate(CmdBase):
    def __init__(self, controller, line, engage_object = None):
        super().__init__(controller, line, engage_object)
    
    def start(self):
        self.mystate_module = self.get_persistent_module('mystate')
        self.constants_module = self.get_persistent_module('constants')
        self.error_params = False

        yaw = AirSimClientBase.toEulerianAngle(self.mystate_module.get_orientation())[2]
        delta = float(self.line[2])*3.14/180
        if self.line[1] == 'left':
            yaw -= delta
        elif self.line[1] == 'right':
            yaw += delta
        elif self.line[1] == 'to':
            yaw = delta

        self.final_yaw = yaw
        # Note that this call is cancellable if other movement related call is called
        self.get_client().rotateToYaw(self.final_yaw * 180 / 3.14, 0) # note that this fun uses in degrees (inconsistency)

    def update(self):
        yaw = AirSimClientBase.toEulerianAngle(self.mystate_module.get_orientation())[2]
        # Check if movement is complete or < 0.5 meters distance, anyway thats offset
        #print(abs(self.final_yaw - yaw))
        if abs(self.final_yaw - yaw) < 0.1:
            if self.engage_object != None:
                self.engage_object.mark_done()
            return True
        return False

    # Update other can_process
    def can_process(line):
        try:
            if line[0] in ['turn'] and line[1] in ['left', 'right', 'to'] and type(float(line[2])) is float:
                return True
            return False
        except: # some error only if command not proper
            return False

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

# Cmd
# cancel
# cancel_all
class CmdCancel(CmdBase):
    def __init__(self, controller, line, engage_object):
        super().__init__(controller, line, engage_object)

    def start(self):
        pass
    
    def update(self):
        if self.command == 'cancel':
            self.controller.cancel_current_commands()
        elif self.command == 'cancel_all':
            self.controller.cancel_all_commands()
        if self.engage_object:
            self.engage_object.mark_done()
        return True
    
    def stop(self):
        pass
    
    def can_process(line):
        if line[0] in ['cancel', 'cancel_all']:
            return True
        return False

instant_command_classes = [
    CmdReset, CmdTakeoff, CmdTakePic, CmdCancel
]
buffered_command_classes = [
    CmdMove, CmdMoveToPoint, CmdRotate
]
