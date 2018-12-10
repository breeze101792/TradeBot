from time import gmtime, strftime

class DebugLevel:
    critical    = 0
    error       = 1
    warning     = 2
    info        = 3
    debug       = 4
    max         = 10
    

class RetValue:
    error = -1
    success = 0
# TODO REMOVE this var
debug_level = DebugLevel.max
def dbg_debug(*args):
    dbgprint("[Debug]", *args)
def dbg_info(*args):
    dbgprint("[Info]", *args)
def dbg_warning(*args):
    dbgprint("[Warnning]", *args)
def dbg_error(*args):
    dbgprint("[Error]", *args)
def dbg_critical(*args):
    dbgprint("[Critical]", *args)

def dbgprint(*args):
    
    timestamp = strftime("%d-%H:%M", gmtime())
    print("[{}]".format(timestamp) + "".join(map(str,args)))