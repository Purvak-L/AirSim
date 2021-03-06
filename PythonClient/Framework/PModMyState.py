from PModBase import *
# Persistent Module
class PModMyState(PModBase):
    def __init__(self, controller):
        super().__init__(controller)
        self._state = MultirotorState()
        self.collided = False
    
    def get_name():
        return 'mystate'

    def start(self):
        super().start()

    def stop(self):
        super().stop()
        
    def update(self):
        self._state = self.get_client().getMultirotorState()
        if self._state.collision.has_collided == True:
            self.collided = True
            print("Collision: with {0}".format(str(self._state.collision.object_name)))
            self.log_warning("Collision: with {0} at {1} with penetration depth of {2}".format(
                str(self._state.collision.object_name), self._state.collision.impact_point, 
                self._state.collision.penetration_depth))
    
    def get_state(self):
        return self._state

    def get_position(self):
        return self._state.kinematics_true.position
    
    def get_orientation(self):
        return self._state.kinematics_true.orientation
