#!/usr/bin/env python3
# system file
from optparse import OptionParser

# Local file
from utility.debug import *
from core.core import *

def main():
    parser = OptionParser(usage='Usage: aiassistant [options] ......')
    parser.add_option("-d", "--debug", dest="debug",
                    help="debug mode on!!", action="store_true")

    (options, args) = parser.parse_args()

    if options.debug:
        DebugSetting.setDbgLevel("all")
        dbg_info('Enable Debug mode')
    else:
        # DebugSetting.setDbgLevel("information")
        DebugSetting.setDbgLevel("all")
        dbg_info('Enable Debug mode')

    # Start core.
    core = Core()
    try:
        dbg_info("Trade Bot starting .")

        core.initialize()
        core.start()
    except KeyboardInterrupt:
        dbg_error("Keyboard Interupt.")
    except:
        raise
    finally:
        core.quit()

    dbg_info("Trade Bot finished.")

if __name__ == '__main__':
    main()
