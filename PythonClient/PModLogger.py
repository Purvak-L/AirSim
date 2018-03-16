from PModBase import *
import datetime
import time
import threading
import queue


class PModHWriteThread(threading.Thread):
    def __init__(self, queue, filename):
        threading.Thread.__init__(self, args=(), kwargs=None)
        self.queue = queue
        self.daemon = True
        self.filename = filename

    def run(self):
        print("Logger thread started")
        with open(self.filename, "w") as f:
            while  True:
                val = ""
                try:
                    for i in range(500):
                        val += self.queue.get(False) + "\n"
                    f.write(val)
                except queue.Empty:
                    if val != "":
                        f.write(val)
                    time.sleep(0.5)
                f.flush()

class PModLogger(PModBase):
    def __init__(self, controller):
        super().__init__(controller)
        self.filename = "Log-" + str(datetime.datetime.now())[:-7].replace("-","").replace(":","_") + ".txt" 
        # Note that python Queue is thread-safe
        self.write_buffer = queue.Queue()

    def get_name():
        return 'logger'

    def add_log_message(self, logtype, caller_name, msg):
        log_msg = "[{0}] {1}: {2} => {3}".format(str(datetime.datetime.now())[-15:],
                     logtype, caller_name, msg)
        self.write_buffer.put(log_msg)
        #print(log_msg)

    def log(self, caller_name, msg):
        self.add_log_message("INFO   ", caller_name, msg)

    def log_error(self, caller_name, msg):
        self.add_log_message("ERROR  ", caller_name, msg)
    
    def log_warning(self, caller_name, msg):
        self.add_log_message("WARNING", caller_name, msg)

    def start(self):
        #super().start()
        self.th = PModHWriteThread(self.write_buffer, self.filename)
        self.th.start()

    def update(self):
        pass

    def stop(self):
        super().stop()