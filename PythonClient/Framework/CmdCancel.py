from CmdBase import *
import setup_path 
import airsim
from PersistentModules import *

# Cmd
# cancel
# cancel_all
class CmdCancel(CmdBase):
    def __init__(self, controller, line, engage_object):
        super().__init__(controller, line, engage_object)

    def start(self):
        pass
    
    def update(self):
        if self.command == 'cancel':
            self.controller.cancel_current_commands()
        elif self.command == 'cancel_all':
            self.controller.cancel_all_commands()
        if self.engage_object:
            self.engage_object.mark_done()
        return True
    
    def stop(self):
        pass
    
    def can_process(line):
        if line[0] in ['cancel', 'cancel_all']:
            return True
        return False
