from time import gmtime, strftime
import inspect
import os

class Bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    ERROR = '\033[91m'
    CRITICAL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


class DebugLevel:
    CRITICAL    = 0x1
    ERROR       = 0x2
    WARNING     = 0x4
    INFOMATION  = 0x8
    DEBUG       = 0x10
    TRACE       = 0x20
    MAX         = 0xff

class RetValue:
    ERROR = -1
    SUCCESS = 0
# TODO REMOVE this var
debug_level = DebugLevel.MAX
def dbg_trace(*args):
    if debug_level & DebugLevel.DEBUG > 0:
        dbgprint(Bcolors.ENDC, "[Trace] ", *args, Bcolors.ENDC)
def dbg_debug(*args):
    if debug_level & DebugLevel.DEBUG > 0:
        dbgprint(Bcolors.ENDC, "[Debug] ", *args, Bcolors.ENDC)
def dbg_info(*args):
    if debug_level & DebugLevel.INFOMATION > 0:
        dbgprint(Bcolors.ENDC, "[Info] ", *args, Bcolors.ENDC)
def dbg_warning(*args):
    if debug_level & DebugLevel.WARNING > 0:
        dbgprint(Bcolors.WARNING, "[Warnning] ", *args, Bcolors.ENDC)
def dbg_error(*args):
    if debug_level & DebugLevel.ERROR > 0:
        dbgprint(Bcolors.ERROR, "[Error] ", *args, Bcolors.ENDC)
def dbg_critical(*args):
    if debug_level & DebugLevel.CRITICAL > 0:
        dbgprint(Bcolors.CRITICAL, "[Critical] ", *args, Bcolors.ENDC)

def dbgprint(*args):
    timestamp = strftime("%d-%H:%M", gmtime())
    caller_frame = inspect.stack()[2]

    caller_filename = os.path.splitext(os.path.basename(caller_frame.filename))[0]
    caller_function = caller_frame.function

    # print("[{}]".format(timestamp) + "".join(map(str,args)))
    print("[{}][{}][{}]".format(timestamp, caller_filename, caller_function) + "".join(map(str,args)))

