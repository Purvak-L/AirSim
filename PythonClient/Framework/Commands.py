from CmdCancel import *
from CmdModule import *
from CmdMove import *
from CmdReset import *
from CmdRotate import *
from CmdTakeOff import *
from CmdTakePic import *
from CmdTracker import *

instant_command_classes = [
    CmdReset, CmdTakeoff, CmdTakePic, CmdCancel, CmdModule
]
buffered_command_classes = [
    CmdMove, CmdMoveToPoint, CmdRotate
]
