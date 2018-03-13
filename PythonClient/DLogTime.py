import time
# setup this in the end in controller when all modules are ready
class DLogTime:
    def __init__(self):
        self.min = float('inf')
        self.max = 0
        self.avg = 0
        self.total = 0
        self.iters = 0
        # helper
        self.last_time = None

    def __str__(self):
        return "min={0:.5f} max={1:.5f} avg={2:.5f} total={3:.5f} iters={4}".format(self.min, self.max, 
                                                            self.avg, self.total, self.iters)

class DModLogger:
    def __init__(self, controller):
        self.controller = controller
        self.logging_modules = {}

        for k, m in controller.persistent_modules.items():
            self.logging_modules[k] = DLogTime()

        for k, m in controller.modules.items():
            self.logging_modules[k] = DLogTime()

        for c in controller.instant_command_classes:
            self.logging_modules[c.__name__] = DLogTime()

        for c in controller.buffered_command_classes:
            self.logging_modules[c.__name__] = DLogTime()

    def start(self, name):
        self.logging_modules[name].last_time = time.time()
    
    def stop(self, name):
        mod = self.logging_modules[name]
        t_diff = time.time() - mod.last_time
        if t_diff < mod.min:
            mod.min = t_diff
        elif t_diff > mod.max:
            mod.max = t_diff

        mod.iters += 1
        mod.avg = (mod.avg * (mod.iters - 1) + t_diff)/mod.iters 

        mod.last_time = None
        mod.total += t_diff

    def __str__(self):
        out = ""
        for k, value in self.logging_modules.items():
            out += k + str(value) + "\n"
        return out
