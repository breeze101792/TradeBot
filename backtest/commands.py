from core.config import *

def register_backtest_commands(cli_ins):
    cli_ins.regist_cmd("config", cmd_config, description=f"set/get golobal config", arg_list = ['set', 'get', 'dump'], group='backtest')
    cli_ins.regist_cmd("backtest", cmd_backtest, description="Enter the backtesting command-line interface.", group='backtest')

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
def cmd_backtest(args):
    # FIXME, check if it excute by BTCLI, if yes ignore it.
    try:
        btcli = BTCLI()
        btcli.run()
    except Exception as e:
        dbg_error(e)
    
        traceback_output = traceback.format_exc()
        dbg_error(traceback_output)
        return False
    return True
