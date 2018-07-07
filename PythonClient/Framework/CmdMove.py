from CmdBase import *
from PersistentModules import *
# Cmd
# 'forward [float(m/s)]'
# 'backward [float(m/s)]'
# 'up [float(m/s)]'
# 'down [float(m/s)]'
# 'left [float(m/s)]'
# 'right [float(m/s)]'
# Uses Intent, assumes that current intent is hover and directly overrides
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
        self.intent_provider_module = self.get_persistent_module('intent_provider')
        locationVec = list(self.mystate_module.get_position())
        offset = [0, 0, 0]
        #print(locationVec)
        # Process command
        yaw = AirSimClientBase.toEulerianAngle(self.mystate_module.get_orientation())[2]
        #print("yaw is {0} {1} {2}".format(yaw, math.sin(yaw), math.cos(yaw)))
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
            offset[0] -= float(self.distance_param) * math.sin(yaw)
            offset[1] += float(self.distance_param) * math.cos(yaw)
        elif self.command == 'left':
            offset[0] += float(self.distance_param) * math.sin(yaw)
            offset[1] -= float(self.distance_param) * math.cos(yaw)

        # add to location
        locationVec[0] += offset[0]
        locationVec[1] += offset[1]
        locationVec[2] += offset[2]
        self.final_location = locationVec
        #print(self.final_location)

        # Update intent
        self.intent_provider_module.submit_intent(CmdMove.__name__, PModHIntents.MOVE, self.final_location)

        # Note that this call is cancellable if other movement related call is called
        self.get_client().moveToPosition(self.final_location[0], self.final_location[1], self.final_location[2],
            self.constants_module.standard_speed, 0)
    
    def update(self):
        locationVec = list(self.mystate_module.get_position())
        # Check if movement is complete or < 0.5 meters distance, anyway thats offset
        if ((self.final_location[0] - locationVec[0])**2 + (self.final_location[1] - locationVec[1])**2
            + (self.final_location[2] - locationVec[2])**2)**(1/2) < 0.5:
            # mark intent as complete
            self.intent_provider_module.mark_as_complete(CmdMove.__name__) 
            #print("inside " + str(self.engage_object))
            if self.engage_object != None:
                self.engage_object.mark_done()
            return True
        return False
        
    def can_process(line):
        try:
            if (line[0] in ['forward', 'backward', 'up', 'down', 'left', 'right'] and 
                line[1][-1] in ['m', 's'] and type(float(line[1][:-1])) is float):
                return True
            return False
        except:
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
        self.intent_provider_module = self.get_persistent_module('intent_provider')

        self.intent_provider_module.submit_intent(CmdMoveToPoint.__name__, PModHIntents.MOVE, self.final_location)
        # Note that this call is cancellable if other movement related call is called
        self.get_client().moveToPosition(self.final_location[0], self.final_location[1], self.final_location[2],
            self.constants_module.standard_speed, 0)

    def update(self):
        locationVec = list(self.mystate_module.get_position())
        # Check if movement is complete or < 0.5 meters distance, anyway thats offset
        if ((self.final_location[0] - locationVec[0])**2 + (self.final_location[1] - locationVec[1])**2
            + (self.final_location[2] - locationVec[2])**2)**(1/2) < 0.5:
            self.intent_provider_module.mark_as_complete(CmdMoveToPoint.__name__)
            if self.engage_object != None:
                self.engage_object.mark_done()
            return True
        return False

    def can_process(line):
        try:
            if line[0] in ['move'] and type(float(line[1]) + float(line[2]) + float(line[3])) is float:
                return True
            return False
        except:
            return False