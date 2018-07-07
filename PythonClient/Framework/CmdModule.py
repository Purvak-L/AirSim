from CmdBase import *
from PersistentModules import *

# Cmd
# module name on/off
# has some issues maybe with on off command_server
class CmdModule(CmdBase):
    def __init__(self, controller, line, engage_object = None):
        super().__init__(controller, line, engage_object)
        
    def start(self):
        mod = self.get_module(self.line[1])
        if mod == None:
            self.engage_object.mark_failed()
            return
        if self.line[2] == 'on':
            self.engage_object.mark_done(b"Enabled")
            if not mod.enabled:
                mod.start()
        elif self.line[2] == 'off':
            self.engage_object.mark_done(b"Disabled")
            if mod.enabled:
                mod.stop()

    def update(self):
        return True

    def can_process(line):
        try:
            if line[0] in ['module'] and line[2] in ['on', 'off']:
                return True
            return False
        except: # some error only if command not proper
            return False

