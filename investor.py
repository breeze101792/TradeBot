#!/bin/env python3
from debug import *

def UI_main():
    from UIManager import UIManager
    window = UIManager()        
    window.ui_start()

def main():
    dbg_info("Investor")

if __name__ == '__main__':
    main()
