import asynchat
import asyncore
import socket
import threading
import cv2
import numpy as np
# Module Base class
class ModBase:
    def __init__(self, controller):
        self.controller = controller
        self.enabled = False
    
    def get_name():
        raise NotImplementedError
    
    def get_client(self):
        return self.controller.get_client()

    def get_module(self, name):
        return self.controller.get_module(name)

    def get_persistent_module(self, name):
        return self.controller.get_persistent_module(name)

    def start(self):
        self.enabled = True
    
    def stop(self):
        self.enabled = False

    def update(self):
        raise NotImplementedError

class EngageObject:
    def __init__(self, id, addr = None):
        self.addr = addr
        self.data = b''
        self.id = id
        self.status = -1
        self.done = False
    
    def mark_done(self, data = b'Done'):
        self.data = data
        self.status = 0
        self.done = True

    def mark_failed(self, data = b'Failed'):
        self.data = data
        self.status = -1
        self.done = True
    
    def mark_cancelled(self, data = b'Cancelled'):
        self.data = data
        self.status = -2
        self.done = True

class ChatHandler(asynchat.async_chat):
    def __init__(self, sock, addr, callback, chat_room):
        asynchat.async_chat.__init__(self, sock=sock, map=chat_room)
        self.addr = addr
        self.set_terminator(b'\r\nDONEPACKET\r\n')
        self.buffer = []
        self.callback = callback
 
    def collect_incoming_data(self, data):
        self.buffer.append(data.decode('ASCII'))
 
    def found_terminator(self):
        msg = ''.join(self.buffer)
        print('Received: %s'% msg)
        msg = msg.split(" ")

        engage_object = EngageObject(msg[0], self.addr)
        #print("engage terminate " + str(engage_object))
        self.callback(msg[1:], engage_object)
        self.buffer = []

class ChatServer(asyncore.dispatcher):
    def __init__(self, host, port, handler, chat_room):
        asyncore.dispatcher.__init__(self, map=chat_room)
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.bind((host, port))
        self.listen(5)
        self.res_handler = handler
        self.chat_room = chat_room
 
    def handle_accept(self):
        pair = self.accept()
        if pair is not None:
            sock, addr = pair
            print('Incoming connection from %s' % repr(addr))
            handler = ChatHandler(sock, addr, self.res_handler, self.chat_room)
            handler.push("Hello".encode("ASCII") + b'\r\nDONEPACKET\r\n')

class ModCommandServer(ModBase):
    def __init__(self, controller):
        super().__init__(controller)
        self.add_command = self.controller.add_command

        self.engage_object_list = []
        self.chat_room = {}
        self.server = None

        # Auto start as will be needing from start
        self.start()
        
    def get_name():
        return 'command_server'

    def start(self):
        super().start()
        if (not self.server):
            self.server = ChatServer('localhost', 5050, self.process, self.chat_room)
            self.comm = threading.Thread(target= lambda: (asyncore.loop(map=self.chat_room)))
            self.comm.daemon = True
            self.comm.start()
        print('Serving command API on localhost:5050')

    def stop(self):
        super().stop()
        # Note that this only stops update and not disable server

    # Only test method
    def later(self, msg, engage_object):
        time.sleep(2)
        engage_object.data = (str(engage_object.id) + ' done').encode('ASCII')
        engage_object.status = 0
        engage_object.done = True

    def process(self, msg, engage_object):
        #print("process " + str(engage_object))
        # if server is disabled return msg with fail
        if (not self.enabled):
            engage_object.data = b"Failed: ModCommandServer disabled"
            engage_object.status = -1
            engage_object.done = True
            return
        
        # else
        print("Processing command " + str(msg))
        self.engage_object_list.append(engage_object)
        # replace here with add_command
        #threading.Thread(target=lambda: self.later(msg, engage_object)).start()
        self.add_command(msg, engage_object)


    def update(self):
        if not self.enabled:
            return
        delete_list = []
        for e in self.engage_object_list:
            if e.done == True:
                #print(str(e.id) + " done" )
                for handler in self.chat_room.values():
                    if hasattr(handler, 'push'):
                        packetstr = e.id + " " + str(e.status) + " "
                        packet = packetstr.encode('ASCII') + e.data + b'\r\nDONEPACKET\r\n'
                        handler.push(packet)
                delete_list.append(e)
        for e in delete_list:
            self.engage_object_list.remove(e)

class BoundingBox:
    def __init__(self, list_):
        self.x = list_[0]
        self.y = list_[1]
        self.w = list_[2]
        self.h = list_[3]

class ModTracker(ModBase):
    def __init__(self, controller):
        super().__init__(controller)
        self.bounding_box_found = False
        self.sent_img = None
        self.sent_img_bool = False
        self.bounding_box = None
        self.old_corners = None
        self.lk_params = dict( winSize  = (15,15),
                  maxLevel = 2,
                  criteria = (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 10, 0.03))
        self.img = np.zeros((144, 256))

    def get_name():
        return 'tracker'

    def test_bounded_box(self, img):
        print("getting roi")
        corners = cv2.selectROI(img, False)
        self.set_bounded_box(corners)

    def set_bounded_box(self, b_box_corners):
        self.bounding_box = BoundingBox(b_box_corners)
        # process initial image
        frameGray = cv2.cvtColor(self.sent_img, cv2.COLOR_BGR2GRAY)
        roi = frameGray[self.bounding_box.y:(self.bounding_box.y + self.bounding_box.h), 
                    self.bounding_box.x:(self.bounding_box.x + self.bounding_box.w)]
        new_corners = cv2.goodFeaturesToTrack(roi, 50, 0.01, 10) 
        new_corners[: , 0, 0] = new_corners[:, 0, 0] + int(self.bounding_box.x)
        new_corners[: , 0, 1] = new_corners[:, 0, 1] + int(self.bounding_box.y)
        self.old_gray = frameGray
        self.old_corners = new_corners
        self.bounding_box_found = True

    def find_distance(self, r1, c1, r2, c2):
        d = (r1 - r2)**2 + (c1 - c2)**2
        d = d**0.5
        return d

    def start(self):
        #super.start()
        self.enabled = True
        self.camera_module = self.get_persistent_module('camera')
        self.camera_module.get_camera(0).add_image_type('scene')
        self.window_manager_module = self.get_persistent_module('windows_manager')
        self.window_manager_module.add_window("Tracking", lambda: self.img)

    def update(self):
        # init algo params
        if self.sent_img_bool == False:
            # Make thread for getting bounding box #TODO later replace with client call
            print("starting thread")
            self.sent_img = self.camera_module.get_image(0, 'scene').image_data
            print(len(self.sent_img))
            threading.Thread(target=self.test_bounded_box, args=(self.sent_img,)).start()
            self.sent_img_bool = True
            return False
        # wait for input
        if not self.bounding_box_found:
            return False
        # else start tracking
        self.img = self.camera_module.get_image(0, 'scene').image_data
        gray = cv2.cvtColor(self.img, cv2.COLOR_BGR2GRAY)
        new_corners, st, err = cv2.calcOpticalFlowPyrLK(self.old_gray, gray, self.old_corners, 
                                                None, **self.lk_params)
        r_add,c_add = 0,0
        for corner in new_corners:
                r_add = r_add + corner[0][1]
                c_add = c_add + corner[0][0]
        centroid_row = int(1.0 * r_add / len(new_corners))
        centroid_col = int(1.0 * c_add / len(new_corners))
        # draw centroid
        #print(img.shape)
        # fix next line error
        self.img = self.img.copy()
        cv2.circle(self.img, (int(centroid_col), int(centroid_row)), 5, (255,0,0))
        # add only those corners to new_corners_updated which are at a distance of 30 or lesse
        new_corners_updated = new_corners.copy()
        tobedel = []
        for index in range(len(new_corners)):
            if self.find_distance(new_corners[index][0][1], new_corners[index][0][0], 
                int(centroid_row), int(centroid_col)) > 90:
                tobedel.append(index)
        new_corners_updated = np.delete(new_corners_updated,tobedel,0)
        #drawing the new points
        for corner in new_corners_updated:
            cv2.circle(self.img, (int(corner[0][0]),int(corner[0][1])) ,5,(0,255,0))
        if len(new_corners_updated) < 1:
            print("OBJECT LOST, Reinitialize for tracking")
            self.stop()
            return
        #finding the min enclosing circle
        ctr , rad = cv2.minEnclosingCircle(new_corners_updated)

        cv2.circle(self.img, (int(ctr[0]),int(ctr[1])) ,int(rad),(0,0,255),thickness = 5)	
        
        #updating old_corners and oldFrameGray 
        self.old_gray = gray.copy()
        self.old_corners = new_corners_updated.copy()
        return False

    def stop(self):
        super().stop()
        self.bounding_box_found = False
        self.sent_img = None
        self.bounding_box = None
        self.old_corners = None
        self.img = np.zeros((144, 256))
        self.window_manager_module.remove_window("Tracking")

# TODO Add new Modules below this line
module_classes = [ModCommandServer, ModTracker]