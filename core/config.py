from utility.config import *

class AppConfig(BasicConfig):
    log_level = "Information"
    class about:
        program_name = 'Investment'
        version='0.1.0'
    class path:
        root = os.path.expanduser(f"~/.config/ConfigManager")
        config = "config.json"
        data = "data"
        tarding_database = 'tarding.db'
        log = "log"
        broker = "broker"
        bt_cmd_history = 'backtrade_cmd.history'
        trade_cmd_history = 'trade_cmd.history'

class AppConfigManager(ConfigManager):
    def __init__(self):
        self.config = AppConfig
        # some config could be seeting here.
        # self.config.set_config('investment')
        self.set('path.root', '~/.config/investment')
