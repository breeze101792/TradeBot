import traceback
from flask import Flask, render_template, request
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Dict, Any, Optional, List # Added for type hints in helper function

# Import Recorder and OrderAction for trade data
from trading.traderecord import Recorder
from broker.order.constant import OrderAction, OrderPrice # Added OrderPrice
from broker.brokermanager import BrokerManager # Moved to top

class TradeBotServer:
    def __init__(self, port=5000, host='0.0.0.0'):
        self.TEMPLATE_DIR = Path(__file__).resolve().parent / 'templates'
        self.app = Flask(__name__, template_folder=str(self.TEMPLATE_DIR))
        self.port = port
        self.host = host
        self._register_routes()

    def _register_routes(self):
        """Registers all routes for the Flask application."""
        self.app.route('/')(self.home)
        self.app.route('/puretext')(self.pure_text_page)
        self.app.route('/show_trades')(self.page_show_trade) # New route for showing trades
        self.app.route('/show_transactions')(self.page_show_transactions) # New route for showing transactions

    def home(self):
        """Renders the home page with sample results."""
        return render_template('index.html')

    def pure_text_page(self):
        """Renders a page with pure text content."""
        return render_template('puretext.html')

    def page_show_trade(self):
        """Renders a page displaying all open trades."""
        recorder = Recorder() # Initialize the Recorder
        open_trades = recorder.get_open_trades()
        # Prepare data for rendering in the template
        trades_data = []
        for trade in open_trades:
            trades_data.append({
                'trade_id': trade.trade_id,
                'symbol': trade.symbol,
                'strategy': trade.strategy,
                'current_size': trade.current_size,
                'is_open': trade.is_open,
                'transactions_count': len(trade.transactions),
                'profit': f"{trade.calculate_profit():.2f}"
            })
        return render_template('show_trades.html', trades=trades_data)
    def page_show_transactions(self):
        """Renders a page displaying transaction summaries."""
        # Import request here to avoid circular dependency if imported globally
        # This import is already at the top of the file, so it's redundant here.
        # from flask import request 
        duration = request.args.get('duration', 'week') # Default to 'week'

        # Get transaction summary data from BrokerManager
        # BrokerManager.transaction_mgr is initialized in BrokerManager.initialize
        # So we need to get the instance of BrokerManager first.
        bm = BrokerManager()
        summary_results = bm.transaction_mgr.get_summary_data(duration)

        return render_template(
            'show_transactions.html',
            summary_data=summary_results['summary_data'],
            per_symbol_table_data=summary_results['per_symbol_table_data'],
            current_positions_data=summary_results['current_positions_data'],
            period_display=summary_results['period_display'],
            current_duration=summary_results['current_duration']
        )


    def run(self, debug=False, use_reloader = False):
        """Runs the Flask application."""
        try:
            # self.app.run(debug=debug, host=self.host, port=self.port)
            self.app.run(host=self.host, port=self.port, debug=debug, use_reloader=use_reloader)
        except KeyboardInterrupt:
            print(f"Get key board interrupt.")
        except Exception as e:
            print(e)
        
            traceback_output = traceback.format_exc()
            print(traceback_output)

if __name__ == '__main__':
    from core.config import *
    cm = AppConfigManager()
    cm.set('debug.development', True)
    cm.set('path.broker', "broker_development")

    BrokerManager.initialize(broker_type = 'mock')

    server = TradeBotServer(port=5000, host='0.0.0.0') # Default port and host
    server.run()
