from PersistentModules import *
import math
import asynchat
import asyncore
import socket
import threading
import math
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
    
    # add more? 

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
    def __init__(self, controller, add_command):
        super().__init__(controller)
        self.add_command = add_command

        self.engage_object_list = []
        self.chat_room = {}
        self.server = None
        
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

class ModDenseFlow(ModBase):
    def __init__(self, controller):
        super().__init__(controller)
        self.first_gray = None
        self.second_frame = None
        self.directions = []
        self.vector_image = np.ones([144,256])
        self.vector_x = 0.0
        self.vector_y = 0.0
        self.subscribers = list()

    
    def get_name():
        return "dense_flow" 
    
    def _draw_flow(self,img, flow, step=16):
        self.vector_x = 0.0
        self.vector_y = 0.0
        img_copy = img.copy()
        h, w = img.shape[:2]
        y, x = np.mgrid[step/2:h:step, step/2:w:step].reshape(2,-1).astype(int)
        fx, fy = flow[y,x].T
        lines = np.vstack([x, y, x+fx, y+fy]).T.reshape(-1, 2, 2)
        lines = np.int32(lines + 0.5)
        cv2.polylines(img_copy, lines, True, (0, 255, 0))
        
        
        for (x1, y1), (x2, y2) in lines:
            self.directions.append([x1,y1, math.sqrt((x2-x1)*(x2-x1) + (y2-y1)*(y2-y1))])
            self.vector_x += -1*np.sign(x2-x1)*abs(x2-x1)
            self.vector_y += np.sign(y2-y1)*abs(y2-y1)
            cv2.circle(img_copy, (x1, y1), 1, (0, 0, 255), -1)
            cv2.circle(img_copy, (x2, y2), 1, (255, 0, 0), -1)
        self.vector_x = self.vector_x / len(lines)
        self.vector_y = self.vector_y / len(lines)
        return img_copy
    
    # def subscribe(self, name):
    #     self.subscribers.append(name)
    
    # def unsubscribe(self, name):
    #     self.subscribers.remove(name)

    def start(self):
        super().start()
        self.mystate_module = self.get_persistent_module('mystate')
        self.camera_module = self.get_persistent_module('camera')
        self.camera_module.get_camera(0).add_image_type('scene')
        self.get_persistent_module('windows_manager').add_window("Flow",lambda:self.vector_image)
    
    def _reset_state(self):
        self.first_gray = None
        self.vector_image = np.zeros([144,256])
        self.vector_x = 0.0
        self.vector_y = 0.0
    
    def update(self):
        # if len(self.subscribers) == 0:
        #     return
        l_velocity = self.mystate_module.get_state().kinematics_true.linear_velocity
        a_velocity = self.mystate_module.get_state().kinematics_true.angular_velocity
        v_abs = l_velocity.x_val*l_velocity.x_val + l_velocity.y_val*l_velocity.y_val + l_velocity.z_val*l_velocity.z_val 
        a_abs = a_velocity.x_val*a_velocity.x_val + a_velocity.y_val*a_velocity.y_val + a_velocity.z_val*a_velocity.z_val
        if v_abs < 1:
            self._reset_state()    
        if self.first_gray is None:
            self.first_gray = cv2.cvtColor(self.camera_module.get_image(0,'scene').image_data,cv2.COLOR_BGR2GRAY)
            return 
        self.second_frame = self.camera_module.get_image(0,'scene').image_data
        gray = cv2.cvtColor(self.second_frame,cv2.COLOR_BGR2GRAY)
        #flow = cv2.calcOpticalFlowFarneback(self.first_gray, gray, None, 0.5, 3, 15, 3, 5, 1.2, 0)
        flow = cv2.calcOpticalFlowFarneback(self.first_gray, gray, None, 0.1, 3, 3, 15, 3, 5, 1)
        #flow = cv2.calcOpticalFlowFarneback(prev_gray,gray,0.5,1,3,15,3,5,1)
        self.first_frame = gray
        del self.directions[:]
        self.vector_image = self._draw_flow(self.second_frame,flow)

class ModObstacleAvoidance(ModBase):
    def __init__(self, controller):
        super().__init__(controller)
        self.depth_frame = np.zeros([256,144])
        self.frame = np.zeros([256,144])
        self.collision_box = None
        self.proximity_threshold = 1
        self.emergency_threshold = 0.5
        self.collision_threshold = 0.1
        self.dist_val = 0.0
        self.dense_subscribed = False
        self.destination = [10,10,-10]
        self.current_position = [0,0,-10]
        self.vel_in_x = 0
        self.vel_in_y = 0
        self.vel_in_z = 0
        
    
    def get_name():
        return "obstacle_avoidance"
    
    def start(self):
        super().start()
        self.dense = self.get_module('dense_flow')
        self.intent_provider_module = self.get_persistent_module('intent_provider')
        self.mystate_module = self.get_persistent_module('mystate')
        self.camera_module = self.get_persistent_module('camera')
        self.constants_module = self.get_persistent_module('constants')
        self.camera_module.get_camera(0).add_image_type('depth')
        self.camera_module.get_camera(0).add_image_type('scene')
        self.get_persistent_module('windows_manager').add_window("Depth Map",lambda:self.depth_frame)
        self.get_persistent_module('windows_manager').add_window("Map",lambda:self.frame)
        self.shape_frame = self.frame.shape
        self.collision_box = [ [2*self.shape_frame[0]//5, int(1*self.shape_frame[1]/5)],
                                [3*self.shape_frame[0]//5, int(4*self.shape_frame[1]/5)]]
        

    def update(self):
        if self.intent_provider_module.intent != PModHIntents.MOVE:
            return
        self.destination = self.intent_provider_module.params
        self.current_position = list(self.mystate_module.get_position())
        if self.current_position[2] > -2:
            print(self.current_position)
            self.get_client().moveByVelocity(0,0,-1,0.1)

        # if abs(self.destination[0]-self.current_position[0]) < 0.5 and abs(self.destination[1]-self.current_position[1]) < 0.5 and abs(self.destination[2]-self.current_position[2]) < 0.5:
        #     return
        self.depth_frame = self.camera_module.get_image(0,'depth').image_data
        self.frame = self.camera_module.get_image(0,'scene').image_data

        val = np.min(np.min(self.depth_frame[self.collision_box[0][1]:self.collision_box[1][1], self.collision_box[0][0]:self.collision_box[1][0]], axis = 1))
        self.vel_in_y = self.destination[0] - self.current_position[0]
        self.vel_in_z = np.sign(self.destination[2] - self.current_position[2]) 
        print(self.current_position)
        print("--------------------------------")
        #val = np.average(self.depth_frame[self.collision_box[0][1]:self.collision_box[1][1], self.collision_box[0][0]:self.collision_box[1][0]])
        if val <= self.proximity_threshold and val > self.emergency_threshold: 
            self.vel_in_y = 1*np.sign(self.dense.vector_x)
            self.vel_in_z += 10*np.sign(self.dense.vector_y)
        elif val <= self.emergency_threshold and val > self.collision_threshold:
            self.vel_in_y = 2*np.sign(self.dense.vector_x)
            self.vel_in_z += 20*np.sign(self.dense.vector_y)
        elif val <= self.collision_threshold:
            self.vel_in_y = 10*np.sign(self.dense.vector_x)
            self.vel_in_z += 100*np.sign(self.dense.vector_y)
        # self.vel_in_z *= 3
        print(self.vel_in_x)
        print(self.vel_in_y)
        print(self.vel_in_z)
        self.vel_in_x = np.sign(self.vel_in_x)
        self.vel_in_z = np.sign(self.vel_in_z)
        print("---------------------------------------")
        self.get_client().moveByVelocity(1,self.vel_in_y,self.vel_in_z,0.1)

        img = self.frame.copy()    
        cv2.rectangle(img,(2*self.shape_frame[0]//5,int(1*self.shape_frame[1]//5)),(3*self.shape_frame[0]//5,int(4*self.shape_frame[1]/5)),(0, 0, 255),4)
        cv2.line(img,(int(img.shape[1]/2),int(img.shape[0]/2)), ( int(img.shape[1]//2) + 1*int(self.vel_in_y),int(img.shape[0]//2)), (0,0,255), 3)
        cv2.line(img,(int(img.shape[1]//2),int(img.shape[0]//2)), (int(img.shape[1]//2) ,int(img.shape[0]//2 + 1*self.vel_in_z)) , (0,255,255), 3)
        cv2.putText(img, str(val),(10,50),cv2.FONT_HERSHEY_SIMPLEX,1, (0,0,255),1,cv2.LINE_AA)
        cv2.imshow("bbox",img)
        #print(val)
        # img = self.frame.copy()
        # cv2.putText(img, str(val),(10,50),cv2.FONT_HERSHEY_SIMPLEX,1, (0,0,255),1,cv2.LINE_AA)
        # cv2.rectangle(img,(2*self.shape_frame[0]//5,2*self.shape_frame[1]//5),(3*self.shape_frame[0]//5,3*self.shape_frame[1]//5),(0, 0, 255),4)
        # cv2.line(img,(int(img.shape[1]/2),int(img.shape[0]/2)), ( int(img.shape[1]//2) + int(self.dense.vector_x),int(img.shape[0]//2)), (0,0,255), 3)
        # cv2.line(img,(int(img.shape[1]//2),int(img.shape[0]//2)), (int(img.shape[1]//2) ,int(img.shape[0]//2 + self.dense.vector_y)) , (0,255,255), 3)
        # cv2.imshow("bbox",img)
        # #print(self.mystate_module.get_state())
        #self.controller.client.moveToPosition(self.destination[0],self.destination[1],self.destination[2],3)
# TODO Add new Modules below this line
module_classes = [ModDenseFlow, ModObstacleAvoidance]