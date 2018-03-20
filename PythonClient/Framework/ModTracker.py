from ModBase import *
import cv2
import numpy as np
import threading
from enum import Enum

class BoundingBox:
    def __init__(self, list_):
        self.x = list_[0]
        self.y = list_[1]
        self.w = list_[2]
        self.h = list_[3]

class TrackerStatus(Enum):
    UN_INITIALIZED = 1,
    STARTED = 2, 
    UPDATE_WAITING_BB = 3,
    TRACKING = 4,
    LOST_TRACK = 5,
    STOPPED = 6


class ModTracker(ModBase):
    def __init__(self, controller):
        super().__init__(controller)
        # Status for others to check 
        self.status = TrackerStatus.UN_INITIALIZED

        # Internal Parameters
        self.sent_img_bool = False
        self.bounding_box = None
        self.old_gray = None
        self.old_corners = None
        
        # Parameters for Lucas Kanade
        self.lk_params = dict( winSize  = (15,15),
                  maxLevel = 2,
                  criteria = (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 10, 0.03))
        self.img = np.zeros((144, 256))
        self.original_sent_img = None # Keep track of
        self.original_gray_img = None # Keep track of
        self.original_corners = None # Keep track of 
        

    def get_name():
        return 'tracker'
    

    def test_bounded_box(self, img):
        print("getting roi")
        corners = cv2.selectROI(img, False)
        self.set_bounded_box(corners)

    def set_bounded_box(self, b_box_corners):
        self.bounding_box = BoundingBox(b_box_corners)
        # process initial image
        frameGray = cv2.cvtColor(self.original_sent_img, cv2.COLOR_BGR2GRAY)
        roi = frameGray[self.bounding_box.y:(self.bounding_box.y + self.bounding_box.h), 
                    self.bounding_box.x:(self.bounding_box.x + self.bounding_box.w)]
        new_corners = cv2.goodFeaturesToTrack(roi, 50, 0.01, 10) 
        new_corners[: , 0, 0] = new_corners[:, 0, 0] + int(self.bounding_box.x)
        new_corners[: , 0, 1] = new_corners[:, 0, 1] + int(self.bounding_box.y)
        self.old_gray = frameGray
        self.original_gray_img = frameGray.copy()
        self.old_corners = new_corners
        self.original_corners = new_corners.copy()
        self.status = TrackerStatus.TRACKING
        print("original corners {0}".format(len(self.original_corners)))
        self.log("Set a new bounding box {0} and found {1} features, status = {2}".format(b_box_corners, 
                len(self.original_corners), self.status))

    def find_distance(self, r1, c1, r2, c2):
        d = (r1 - r2)**2 + (c1 - c2)**2
        d = d**0.5
        return d

    def centroids(self, new_corners):
        r_add,c_add = 0,0
        for corner in new_corners:
                r_add = r_add + corner[0][1]
                c_add = c_add + corner[0][0]
        centroid_row = int(1.0 * r_add / len(new_corners))
        centroid_col = int(1.0 * c_add / len(new_corners))
        return centroid_row, centroid_col

    def start(self):
        super().start()
        self.camera_module = self.get_persistent_module('camera')
        self.camera_module.get_camera(0).add_image_type('scene')
        self.window_manager_module = self.get_persistent_module('windows_manager')
        self.window_manager_module.add_window("Tracking", lambda: self.img)
        self.status = TrackerStatus.STARTED
        self.log("Started waiting for input")

    def update(self):
        # init params if just started
        if self.status == TrackerStatus.STARTED:
            # Make thread for getting bounding box #TODO later replace with client call
            self.original_sent_img = self.camera_module.get_image(0, 'scene').image_data
            threading.Thread(target=self.test_bounded_box, args=(self.original_sent_img,)).start()
            # Wait for BoundingBox
            self.status = TrackerStatus.UPDATE_WAITING_BB
            self.log("Sent bounding box request, status = {0}".format(self.status))
            return False

        # wait for input of BoundingBox
        if self.status == TrackerStatus.UPDATE_WAITING_BB:
            self.log("Waiting for bounding box request, status = {0}".format(self.status))
            return False
        
        # current status is tracking
        if self.status == TrackerStatus.TRACKING:
            self.img = self.camera_module.get_image(0, 'scene').image_data
            gray = cv2.cvtColor(self.img, cv2.COLOR_BGR2GRAY)
            new_corners, st, err = cv2.calcOpticalFlowPyrLK(self.old_gray, gray, self.old_corners, 
                                                    None, **self.lk_params)
            #print(self.old_corners)
            centroid_row, centroid_col = self.centroids(new_corners)

            # add only those corners to new_corners_updated which are at a distance of 30 or lesse
            new_corners_updated = new_corners.copy()
            tobedel = []
            
            for index in range(len(new_corners)):
                # Check if outside of circle or image
                if self.find_distance(new_corners[index][0][1], new_corners[index][0][0], 
                    int(centroid_row), int(centroid_col)) > 30  or (
                    new_corners[index][0][1] < 0 or 
                    new_corners[index][0][1] > self.img.shape[0] or 
                    new_corners[index][0][0] < 0 or 
                    new_corners[index][0][0] > self.img.shape[1]):
                    tobedel.append(index)
            new_corners_updated = np.delete(new_corners_updated, tobedel, 0)
            # if (len(new_corners_updated) != len(self.old_corners)):
            #     print(new_corners_updated)
            #     print()
            
            # for index in range(len(new_corners_updated)):
            #     print("{0} {1} {2} {3} {4}".format(new_corners_updated[index][0][0], 
            #         new_corners_updated[index][0][1],
            #         self.img.shape[0],
            #         self.img.shape[1],
            #         self.find_distance(new_corners_updated[index][0][1], 
            #         new_corners_updated[index][0][0], 
            #         int(centroid_row), int(centroid_col))))
            # print()

            # Lost Tracking Condition
            if len(new_corners_updated) < 1:
                self.status = TrackerStatus.LOST_TRACK
                print("OBJECT LOST waiting for tracking again")
                self.log("Object Lost, status = {0}".format(self.status))
                return False
            
            #updating old_corners and old_gray
            self.old_gray = gray.copy()
            self.old_corners = new_corners_updated.copy()

            # Visual Output
            # draw centroid
            self.img = self.img.copy() # Cause it will not fucking work without this -,-
            cv2.circle(self.img, (int(centroid_col), int(centroid_row)), 5, (255,0,0))
            
            # drawing the new points
            for corner in new_corners_updated:
                cv2.circle(self.img, (int(corner[0][0]),int(corner[0][1])) ,5,(0,255,0))
            #finding the min enclosing circle
            ctr , rad = cv2.minEnclosingCircle(new_corners_updated)

            cv2.circle(self.img, (int(ctr[0]),int(ctr[1])) ,int(rad),(0,0,255),thickness = 5)

            return False

        if self.status == TrackerStatus.LOST_TRACK:
            # Compare with original
            self.img = self.camera_module.get_image(0, 'scene').image_data
            gray = cv2.cvtColor(self.img, cv2.COLOR_BGR2GRAY)
            new_corners, st, err = cv2.calcOpticalFlowPyrLK(self.original_gray_img, gray, self.original_corners, 
                                                    None, **self.lk_params)
            # Check if tracking is back with at least half points
            if len(new_corners) > len(self.old_corners) / 1.2:
                print("maybe got tracked again")
                self.old_gray = gray.copy()
                self.old_corners = new_corners.copy()
                self.status = TrackerStatus.TRACKING
            return False

    def stop(self):
        super().stop()
        self.window_manager_module.remove_window("Tracking")

    def reset(self):
        self.bounding_box_found = False
        self.sent_img = None
        self.bounding_box = None
        self.old_corners = None
        self.img = np.zeros((144, 256))