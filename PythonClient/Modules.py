import asynchat
import asyncore
import socket
import threading

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

# TODO Add new Modules below this line
module_classes = []