from core.config import *

def register_commands(cli_ins):
    cli_ins.regist_cmd("config", cmd_config, description=f"set/get golobal config", arg_list = ['set', 'get', 'dump'], group='system')

def cmd_config(args):
    cm = AppConfigManager()
    if args['#'] == 1:
        if args['1'] == 'dump':
            cm.dump()
            return True
        elif args['1'] == 'load':
            cm.load()
            return True
    elif args['#'] == 2:
        if args['1'] == 'get':
            cm.get(args['2'])
    elif args['#'] == 3:
        if args['1'] == 'set':
            cm.set(args['2'], args['3'])
    return False
