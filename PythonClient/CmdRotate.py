from CmdBase import *
from AirSimClient import *
from PersistentModules import *
# Cmd
# turn left deg
# turn right deg
# turn to deg
# turn rate deg
class CmdRotate(CmdBase):
    def __init__(self, controller, line, engage_object = None):
        super().__init__(controller, line, engage_object)
    
    def start(self):
        self.mystate_module = self.get_persistent_module('mystate')
        self.constants_module = self.get_persistent_module('constants')
        self.intent_provider_module = self.get_persistent_module('intent_provider')
        self.full_rate = 60
        self.low_rate = 10
        # Note here we get yaw in radians but later we set it in deg
        pitch, roll, yaw = AirSimClientBase.toEulerianAngle(self.mystate_module.get_orientation())
        #print("original yaw {0}".format(yaw))
        if yaw < 0:
            yaw = 2 * 3.14 + yaw

        #print("updated yaw {0}".format(yaw))
        if (self.line[1] in ['left', 'right', 'to']):
            delta = float(self.line[2])*3.14/180
            if self.line[1] == 'left':
                self.full_rate *= -1
                self.low_rate *= -1
                yaw -= delta
            elif self.line[1] == 'right':
                yaw += delta
            elif self.line[1] == 'to':
                side = 1 # right side
                if delta > yaw + 3.14 or (yaw - delta < 3.14 and yaw - delta > 0): # left side # consider current yaw is 0 
                    side = -1
                self.full_rate *= side
                self.low_rate *= side
                yaw = delta
            #print("updated 2 yaw {0}".format(yaw))
            if yaw > 3.14:
                yaw = -2 * 3.14 + yaw
            #print("final yaw {0}".format(yaw))
            self.final_yaw = yaw
            self.intent_provider_module.submit_intent(CmdRotate.__name__, 
                            PModHIntents.ROTATE, [pitch, roll, yaw])
        else: # rate
            self.rate = float(self.line[2])
            self.intent_provider_module.submit_intent(CmdRotate.__name__, 
                            PModHIntents.ROTATE, [self.rate])

    def update(self):
        if self.line[1] in ['left', 'right', 'to']:
            yaw = AirSimClientBase.toEulerianAngle(self.mystate_module.get_orientation())[2]
            if yaw < 0:
                yaw = 2 * 3.14 + yaw
            # Check if movement is complete or < 0.1 angle distance, anyway thats offset
            # dist to angle
            dist = min(abs(self.final_yaw - yaw), 2 * 3.14 - abs(self.final_yaw - yaw))
            #print('{0} {1} {2}'.format(self.final_yaw, yaw, dist))
            if abs(dist) < 0.1:
                self.get_client().hover()
                self.intent_provider_module.mark_as_complete(CmdRotate.__name__)
                if self.engage_object != None:
                    self.engage_object.mark_done()
                return True
            # Note that this call is cancellable if other movement related call is called
            if abs(dist) < 0.5:
                self.get_client().rotateByYawRate(self.low_rate, 0.5) # note that this fun uses in degrees (inconsistency)
            else: # on full rate
                self.get_client().rotateByYawRate(self.full_rate, 0.5) # note that this fun uses in degrees (inconsistency)
            return False
        else: # Rate
            self.get_client().rotateByYawRate(self.rate, 0.5)


    # Update other can_process
    def can_process(line):
        try:
            if line[0] in ['turn'] and line[1] in ['left', 'right', 'to', 'rate'] and type(float(line[2])) is float:
                return True
            return False
        except: # some error only if command not proper
            return False