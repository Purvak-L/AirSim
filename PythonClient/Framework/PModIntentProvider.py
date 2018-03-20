from PModBase import *
from enum import Enum
import time

# Edit to add more intents
class PModHIntents(Enum):
    MOVE = 1,
    ROTATE = 2,
    HOVER = 3,
    UNKNOWN = -1

class PModIntentProvider(PModBase):
    def __init__(self, controller):
        super().__init__(controller)
        self.intent = PModHIntents.UNKNOWN
        self.params = []
        self.intent_controller = None
        self.time = None

    def get_name():
        return "intent_provider"

    def submit_intent(self, name, intent, params):
        assert type(intent) == PModHIntents
        self.intent_controller = name
        self.intent = intent
        self.params = params
        self.time = time.time()
        self.log("Switching to new Intent {0}:{1} by {2} command/module".format(intent, params, name))

    # Only intent submitter can mark as complete
    # Others can override by submitting new intent
    # Note this auto puts drone in HOVER intent state so caller should make 
    # sure that drone is trying to/will try to hover while calling this 
    def mark_as_complete(self, name):
        if self.intent_controller == name:
            self.intent = PModHIntents.HOVER
            self.intent_controller = None
            self.params = []
            self.time = time.time()
            self.log("Marked last intent as complete by {0}, switching to {1}".format(name, self.intent))

    def flist_repr(l):
        assert type(l) == list
        ans = '['
        for i in l:
            ans += ' {0:.3f}'.format(i)
        return ans + ']'

    def __str__(self):
        return "{0} {1} {2}".format(str(self.intent)[13:], PModIntentProvider.flist_repr(self.params), self.intent_controller)

    def start(self):
        super().start()
    
    def update(self):
        pass
    
    def stop(self):
        super().stop()