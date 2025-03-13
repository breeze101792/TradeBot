
# system file
import traceback
import time
import threading

# FIXME, may be remove latter
import backtrader as bt
import pandas as pd
from datetime import datetime
from core.strategy import *

# Local file
from utility.debug import *
from core.database import *
from market.yahoo import *
from market.twse import *

class Core:
    def __init__(self):
        # Defines
        self.def_database_name = "trader.db"

        # Flags
        self.flag_core_running = False
        self.flag_heatbeat_running = False
        self.flag_service_running = False

        # Vars
        self.var_threading_delay = 0.1

        # Threading
        self.service_thread = None
        self.heatbeat_thread = None

        # class
        self.database = None

    def __initcheck(self):
        # Check env setup is okay or not.
        return True
    def __sanitycheck(self):
        # Check sanity check on heart beat okay or not.
        dbg_info('Sanity Check.')
        pass

    def __heatbeat(self):
        dbg_info('Heatbeat Start.')
        self.flag_heatbeat_running = True

        # TODO Impl heatbeat
        heart_beat_interval_time=10
        while self.flag_core_running and self.flag_heatbeat_running:
            try:
                dbg_trace('heart beatting every {}s'.format(heart_beat_interval_time))
                self.__sanitycheck()
                time.sleep(heart_beat_interval_time)
            except KeyboardInterrupt:
                dbg_warning("Keyboard Interupt.")
                break;
            except Exception as e:
                dbg_error(e)

                traceback_output = traceback.format_exc()
                dbg_error(traceback_output)

            finally:
                # Finalize service thread.
                if self.flag_core_running is False or self.flag_service_running is False:
                    dbg_trace('Finalize service thread.')
                    break

                time.sleep(self.var_threading_delay)

        self.flag_heatbeat_running = False
        dbg_warning('Heatbeat End.')
    def get_tracking_list(self):
        tracking_list = []
        database = None

        database = Database(self.def_database_name)
        database.connect()
        tracking_list = [each_item[0].__str__() for each_item in database.get_tracking_product()]
        database.close()

        return tracking_list
    def update_tracking_list(self, productid, tracking = True):
        # If i need to add this, we need to check if produt is corrent or not.
        tracking_list = []
        database = None

        database = Database(self.def_database_name)
        database.connect()
        database.update_tracking_product(productid, tracking)
        database.close()

        return tracking_list
    def insert_product_list(self, df):
        # If i need to add this, we need to check if produt is corrent or not.
        tracking_list = []
        database = None

        database = Database(self.def_database_name)
        database.connect()

        for _, row in df.iterrows():
            try:
                database.add_product(
                    productid=row["code"],
                    producttype=row["type"],
                    name=row["name"],
                    start=row["start"],
                    market=row["market"],
                    country=row["country"],
                    category=row["category"],
                    tracking=False
                )
            except Exception as e:
                dbg_debug(row["code"], " Add failed.")
                # dbg_debug(e)
                #
                # traceback_output = traceback.format_exc()
                # dbg_debug(traceback_output)
                continue

        # self.add_product('2330', 'stock', '台積電', start='1993-09-05', market='listed', country='TW', Category='半導體業', tracking=True)  
        # database.update_tracking_product(productid, tracking)
        database.close()

        return tracking_list

    def __service(self):
        dbg_info('Service Start.')
        self.flag_service_running = True
        # TODO, change it to real life settings.
        service_interval_time=5
        # TODO, Impl it in more general way.
        # market = Yahoo()
        market = TWSE()

        # init list.
        if False:
            df = market.get_data_list()
            self.insert_product_list(df)
        # Add this for temp add product.

        # Adjust list.
        if False:
            # product_list = ['2454.TW', '2330.TW', '2603.TW', '2379.TW', '2303.TW', '3293.TWO', '00731.TW', '00713.TW', '00888.TWO', '8069.TWO' ]
            # product_list = ['2646.TW', '00888.TWO']
            # product_list = ['2454.TW', '2330.TW', '2603.TW', '2379.TW', '2303.TW', '2412.TW']
            # print('df: ', df)
            df = market.get_data_list()
            cnt = 50
            for _, each_product in df.iterrows():
                dbg_debug(each_product["code"])
                self.update_tracking_list(each_product.code, False)
                # self.update_tracking_list(each_product.code, True)
                if cnt == 0:
                    break
                else:
                    cnt -= 1

        self.update_tracking_list('2330', True)
        self.update_tracking_list('2454', True)
        self.update_tracking_list('2303', True)
        self.update_tracking_list('2379', True)
        self.update_tracking_list('2603', False)
        # self.update_tracking_list('00888.TWO', False)
        # self.update_tracking_list('00713.TW', True)
        # self.update_tracking_list('00731.TW', True)
        # do the evaluation on every service_interval_time.
        while True:
            try:
                dbg_trace('Service running in every {}s'.format(service_interval_time))
                # TODO Impl service
                ###############################################################
                init_cash = 1000000
                # Init Backtrader
                cerebro = bt.Cerebro()

                tracking_list = self.get_tracking_list()
                for each_product in tracking_list:
                    dbg_info("Product List: ", each_product.__str__())
                    try:
                        # df = market.get_ticker(each_product, start_date = "2020-01-01", end_date = "2025-01-01")
                        df = market.get_data(each_product)
                        # dbg_debug('{}'.format(df.head()))
                        data = bt.feeds.PandasData(dataname=df, fromdate=datetime(2020, 1, 1), todate=datetime(2025, 1, 1))
                        # bt.feeds.PandasData(dataname=df, fromdate=datetime.datetime(2022, 1, 1), todate=datetime.datetime(2024, 1, 1))

                        # Add data to enginee
                        cerebro.adddata(data, name=each_product)
                    except Exception as e:
                        dbg_error("Disable ticker: ", each_product)
                        self.update_tracking_list(each_product, False)
                        dbg_error(e)

                        traceback_output = traceback.format_exc()
                        dbg_error(traceback_output)
                        continue


                dbg_info("Start running Strategy.")
                # Load strategy
                cerebro.addstrategy(MovingAverageCrossover)
                # cerebro.addstrategy(BreakoutMomentum)
                # cerebro.addstrategy(BreakoutMomentumEn)

                # Setup init cash
                cerebro.broker.set_cash(init_cash)
                # Set commission
                cerebro.broker.setcommission(commission=0.001)
                # set perc
                cerebro.broker.set_slippage_perc(perc=0.001)
                # Add analyzer
                cerebro.addanalyzer(bt.analyzers.AnnualReturn, _name="annual_return")
                cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name="sharpe", riskfreerate=0.02)
                cerebro.addanalyzer(bt.analyzers.DrawDown, _name="drawdown")
                cerebro.addanalyzer(bt.analyzers.SQN, _name="sqn")
                cerebro.addanalyzer(bt.analyzers.VWR, _name="vwr")


                # cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name="TradeAnalyzer")
                # Do backtesting
                results = cerebro.run()
                strat = results[0]  # Get strategy result.

                dbg_info(f"Init cash({init_cash}), Profit: {(cerebro.broker.getvalue() - init_cash):.2f}/({(cerebro.broker.getvalue() - init_cash)/init_cash*100:.2f}%)")
                # Annual return
                dbg_info("Annual return:")
                for year, ret in strat.analyzers.annual_return.get_analysis().items():
                    dbg_info(f"  {year}: {ret:.2%}")

                # Sharpe Ratio
                sharpe_ratio = strat.analyzers.sharpe.get_analysis().get("sharperatio", None)
                dbg_info(f"Sharpe Ratio: {sharpe_ratio:.2f}" if sharpe_ratio else "📈 sharpe_ratio: Can't calculate")

                vwr = strat.analyzers.vwr.get_analysis().get("vwr", None)
                dbg_info(f"VW Ratio: {vwr:.2f}" if vwr else "📈 VWR: sharpe_ratio: Can't calculate")

                # Drawdown
                drawdown = strat.analyzers.drawdown.get_analysis()
                dbg_info(f"Drawdown: {drawdown['max']['drawdown']:.2f}%")

                # Drawdown
                # tradeanalyzer = strat.analyzers.TradeAnalyzer.get_analysis()
                # dbg_info(f"TradeAnalyzer: {tradeanalyzer}")

                # SQN
                sqn = strat.analyzers.sqn.get_analysis()
                dbg_info(f"SQN: {sqn['sqn']:.2f}, Trad: {sqn['trades']}")

                # Do ploting
                # cerebro.plot()
                break
                ###############################################################


                # dbg_info("Tracking List: " + tracking_list.__str__())

                time.sleep(service_interval_time)
            except KeyboardInterrupt:
                dbg_warning("Keyboard Interupt.")
                self.flag_service_running = False
            except Exception as e:
                dbg_error(e)

                traceback_output = traceback.format_exc()
                dbg_error(traceback_output)
                self.flag_service_running = False

            finally:
                # Finalize service thread.
                if self.flag_core_running is False or self.flag_service_running is False:
                    dbg_trace('Finalize service thread.')
                    break

                time.sleep(self.var_threading_delay)

        self.flag_service_running = False
        dbg_warning('Service End.')
    def initialize(self):
        dbg_info('Core start initialize.')
        try:
            # Checking & init database
            self.database = Database(self.def_database_name)
            self.database.connect()
            self.database.setup()
            # self.database.dump_all()
            self.database.close()
        except Exception as e:
            dbg_error(e)
            traceback_output = traceback.format_exc()
            dbg_error(traceback_output)
            raise
        finally:
            pass

        dbg_info('Core initialized.')
    def start(self):
        dbg_info('Core Start.')
        thread_list = []

        if self.__initcheck() is False:
            dbg_error('Init check fail. Start.')
            return False

        self.flag_core_running = True
        try:
            self.service_thread = threading.Thread(target=self.__service)
            self.service_thread.start()
            thread_list.append(self.service_thread)

            # Monitor Thread
            # self.heatbeat_thread = threading.Thread(target=self.__heatbeat, daemon=True)
            self.heatbeat_thread = threading.Thread(target=self.__heatbeat)
            self.heatbeat_thread.start()
            thread_list.append(self.heatbeat_thread)

            # wait for threading.
            for each_thread in thread_list:
                each_thread.join()

        except KeyboardInterrupt:
            dbg_warning("Keyboard Interupt.")
        except Exception as e:
            dbg_error(e)
            traceback_output = traceback.format_exc()
            dbg_error(traceback_output)

            self.flag_core_running = False

        finally:
            if self.flag_service_running and self.service_thread is not None:
                self.flag_service_running = False
                self.service_thread.join()
                self.service_thread = None

            if self.flag_heatbeat_running and self.heatbeat_thread is not None:
                self.flag_heatbeat_running = False
                self.heatbeat_thread.join()
                self.heatbeat_thread = None

            self.flag_core_running = False

        dbg_warning('Core End.')

    def quit(self):
        dbg_info('Core Quit.')
        # TODO, do final check.

        # if self.database is not None:
        #     self.database.close()

