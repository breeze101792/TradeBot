from utility.config import *

class AppConfig(BasicConfig):
    log_level = "Information"
    class about:
        program_name = 'Investment'
        version='0.1.0'
    class debug:
        development = False
    class path:
        root = os.path.expanduser(f"~/.config/ConfigManager")
        config = "config.json"
        data = "data"
        tarding_database = 'tarding.db'
        log = "log"
        key = "key"
        broker = "broker"
        trade_cmd_history = 'trade_cmd.history'

        bt_cmd_history = 'backtrade_cmd.history'
        bt_report = 'backtest/report'
    class stock:
        # We could use this to control which kind of trading we are doing
        lot_unit = 10
        cash_per_trade = 10 * 1000

class AppConfigManager(ConfigManager):
    def __init__(self, *args, **kwargs):
        super().__init__(*args,config=AppConfig, **kwargs)

        # self.config = AppConfig
        # some config could be seeting here.
        # self.config.set_config('investment')
        self.set('path.root', '~/.config/investment', save = False)
