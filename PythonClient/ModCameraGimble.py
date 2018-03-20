from ModBase import *
from AirSimClient import *
import copy

class CameraOrientations:
    def __init__(self, id, pitch = 0, roll = 0, yaw = 0): # wrt body
        self.id = id
        self.pitch = pitch * 3.14/180
        self.roll = roll * 3.14/180
        self.yaw = yaw * 3.14/180
        self.user = None
        self.enabled = False

    def set_gimble_params(self, user, pitch, roll, yaw): # In degrees
        if self.user == None:
            self.user = user
            self.pitch = pitch * 3.14/180
            self.roll = roll * 3.14/180
            self.yaw = yaw * 3.14/180
        else:
            raise ValueError("{0} is controlling gimble on camera {1}".format(self.user, self.id))

    def enable_gimble(self, user):
        if self.user == None:
            raise ValueError("No camera {0} user, please set params first".format(self.id))
        if self.user != user:
            raise ValueError("Other user is controlling gimble on this camera, {0}".format(self.user))
        self.enabled = True

    def disable_gimble(self, user):
        if self.user == None:
            return
        if self.user != user:
            raise ValueError("Other user is controlling gimble on this camera, {0}".format(self.user))
        self.enabled = False
        self.user = None

class ModCameraGimble(ModBase):
    def __init__(self, controller):
        super().__init__(controller)
        self.constant_module = self.get_persistent_module('constants')
        self.cameras = [0 for i in range(self.constant_module.no_of_cameras)]
        self.gimble_max_angle = 30 * 3.14 / 180 # 30 deg
        
        # get orientations
        for i in range(self.constant_module.no_of_cameras):
            camera_info = self.get_client().getCameraInfo(i)
            pitch, roll, yaw = AirSimClientBase.toEulerianAngle(camera_info.pose.orientation)
            self.cameras[i] = CameraOrientations(i, pitch, roll, yaw)
            print("Camera {0} ori ({1:.2f} {2:.2f} {3:.2f})".format(
                i, self.cameras[i].pitch, self.cameras[i].roll,  self.cameras[i].yaw,
            ))

    def get_name():
        return 'camera_gimble'

    def get_camera(self, id):
        return self.cameras[id]

    def set_gimble_max_angle(self, angle): # in degrees
        self.gimble_max_angle = angle * 3.14 / 180

    def start(self):
        super().start()
        self.mystate_module = self.get_persistent_module('mystate')

    def _cap(self, angle):
        return max(min(angle, self.gimble_max_angle), -self.gimble_max_angle)

    def update(self):
        #camera_angles = AirSimClientBase.toEulerianAngle(self.get_client().getCameraInfo(4).pose.orientation)
        drone_angles = AirSimClientBase.toEulerianAngle(self.mystate_module.get_state().kinematics_true.orientation)
        # print("{0}\n{1}\n{2}\n{3}\n{4}\n".format(
        #     camera_angles,
        #     drone_angles,
        #     self.mystate_module.get_state().kinematics_true.orientation,
        #     AirSimClientBase.toQuaternion(drone_angles[0], drone_angles[1], drone_angles[2]),
        #     AirSimClientBase.toEulerianAngle(AirSimClientBase.toQuaternion(-45 * 3.14 / 180, 0, drone_angles[2]))
        # ))
        for cam in self.cameras:
            if cam.enabled:
                self.log("Setting Camera {0} orientation to ({1:.2f} {2:.2f} {3:.2f})".format(
                    cam.id, cam.pitch - self._cap(drone_angles[0]),
                    cam.roll - self._cap(drone_angles[1]), cam.yaw
                ))
                # - self._cap(drone_angles[1])
                self.get_client().setCameraOrientation(cam.id, 
                    AirSimClientBase.toQuaternion(cam.pitch - self._cap(drone_angles[0]), 
                            cam.roll - self._cap(drone_angles[1]), cam.yaw))


    def stop(self):
        super().stop()
