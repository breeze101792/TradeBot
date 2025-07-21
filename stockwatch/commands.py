import traceback

from utility.debug import *
from stockwatch.server import TradeBotServer

def register_stockwatch_commands(cli_instance):
    cli_instance.regist_cmd("server", cmd_server, description="Manage the TradeBot server (e.g., 'server start').", group='tools')

def cmd_server(args = None):
    """Manages the TradeBot server (e.g., start, stop)."""
    if args and args['#'] == 1:
        subcommand = args['1']
        if subcommand == "start":
            try:
                server = TradeBotServer(port=5000, host='0.0.0.0') # Default port and host
                server.run()
                server = None
            except KeyboardInterrupt:
                dbg_info(f"Get key board interrupt.")
            except Exception as e:
                dbg_error(f"Error starting TradeBot server: {e}")
                traceback_output = traceback.format_exc()
                dbg_error(traceback_output)
        else:
            dbg_error(f"Unknown 'server' subcommand: {subcommand}")
    else:
        dbg_error("Please specify a subcommand for 'server' (e.g., 'server start').")

    return True
