import backtrader as bt
from collections import defaultdict

def default_position():
    return {
        'size': 0,
        'cum_cost': 0.0,
        'avg_price': 0.0
    }


class PartialTradeAnalyzer(bt.Analyzer):
    def __init__(self):
        self.positions = defaultdict(default_position)
        self.trades = defaultdict(list)

    def notify_order(self, order):
        if order.status != order.Completed:
            return

        debug_flag = False
        data = order.data
        data_name = data._name if hasattr(data, '_name') else str(data._dataname)

        size = order.executed.size
        price = order.executed.price
        commission = order.executed.comm or 0.0
        isbuy = order.isbuy()
        dt = bt.num2date(order.executed.dt).date()

        pos = self.positions[data_name]

        if isbuy:
            # --- DEBUG LOGGING ---
            if debug_flag:
                print(f"[DEBUG] Analyzer Buy Notify: {data_name} on {dt}")
                print(f"  > Position Before Buy: Size={pos['size']}, AvgPrice={pos['avg_price']:.4f}, CumCost={pos['cum_cost']:.4f}")
                print(f"  > Buy Details: Size={size}, Price={price:.4f}, Commission={commission:.4f}")
            # --- END DEBUG LOGGING ---

            pos['cum_cost'] += size * price + commission
            pos['size'] += size
            pos['avg_price'] = pos['cum_cost'] / pos['size'] if pos['size'] != 0 else 0.0 # Avoid division by zero if size somehow becomes 0

            # --- DEBUG LOGGING ---
            if debug_flag:
                print(f"  > Position After Buy: Size={pos['size']}, AvgPrice={pos['avg_price']:.4f}, CumCost={pos['cum_cost']:.4f}")
            # --- END DEBUG LOGGING ---
        else:
            if pos['size'] == 0:
                # Attempting to sell when position size is already zero according to the analyzer
                if debug_flag:
                    print(f"[DEBUG] Analyzer Sell Notify: {data_name} on {dt} - Attempted sell with zero position size. Ignoring.")
                return

            # on sell, size is negative
            closed_size = -size
            avg_entry_price = pos['avg_price']
            gross_pnl = (price - avg_entry_price) * closed_size
            net_pnl = gross_pnl - commission
            pnl_pct = ((price / avg_entry_price) - 1.0) * 100 if avg_entry_price != 0 else 0 # Avoid division by zero

            # --- DEBUG LOGGING ---
            if debug_flag:
                print(f"[DEBUG] Analyzer Sell Notify: {data_name} on {dt}")
                print(f"  > Position Before Sell: Size={pos['size']}, AvgPrice={pos['avg_price']:.4f}, CumCost={pos['cum_cost']:.4f}")
                print(f"  > Sell Details: Size={closed_size}, Price={price:.4f}, Commission={commission:.4f}")
                print(f"  > PNL Calc: AvgEntry={avg_entry_price:.4f}, GrossPNL={gross_pnl:.4f}, NetPNL={net_pnl:.4f}, PNL%={pnl_pct:.2f}%")
                print(f"  > Recording Trade: {'WIN' if net_pnl > 0 else 'LOSS' if net_pnl < 0 else 'BREAKEVEN'}")
            # --- END DEBUG LOGGING ---

            self.trades[data_name].append({
                'date': dt.isoformat(),
                'size': closed_size,
                'entry_price': avg_entry_price,
                'exit_price': price,
                'commission': commission,
                'pnl': gross_pnl,
                'net_pnl': net_pnl,
                'pnl_pct': pnl_pct
            })

            pos['size'] -= closed_size
            pos['cum_cost'] = pos['avg_price'] * pos['size'] if pos['size'] > 0 else 0.0
            if pos['size'] == 0:
                pos['avg_price'] = 0.0

    def get_analysis(self, summary=True):
        """
        Calculates analysis results.

        Args:
            summary (bool): If True, returns aggregated results across all symbols.
                          If False, returns results broken down by symbol.

        Returns:
            dict: Analysis results. Structure depends on the 'summary' flag.
        """
        if not summary:
            # Return results per symbol
            result_per_symbol = {}
            for data_name, trade_list in self.trades.items():
                num_trades = len(trade_list)
                won = len([t for t in trade_list if t['net_pnl'] > 0])
                lost = num_trades - won
                total_net_pnl = sum(t['net_pnl'] for t in trade_list)
                avg_net_pnl = total_net_pnl / num_trades if num_trades > 0 else 0

                result_per_symbol[data_name] = {
                    'total_trades': num_trades,
                    'won': won,
                    'lost': lost,
                    'total_net_pnl': total_net_pnl,
                    'avg_net_pnl': avg_net_pnl,
                    'trades': trade_list
                }
            return result_per_symbol
        else:
            # Return aggregated results across all symbols
            overall_total_trades = 0
            overall_won = 0
            overall_lost = 0
            overall_total_net_pnl = 0.0
            all_trades = []

            for data_name, trade_list in self.trades.items():
                num_trades = len(trade_list)
                won = len([t for t in trade_list if t['net_pnl'] > 0])
                lost = num_trades - won
                total_net_pnl = sum(t['net_pnl'] for t in trade_list)

                overall_total_trades += num_trades
                overall_won += won
                overall_lost += lost
                overall_total_net_pnl += total_net_pnl
                all_trades.extend(trade_list)

            overall_avg_net_pnl = overall_total_net_pnl / overall_total_trades if overall_total_trades > 0 else 0

            # Sort all trades by date for consistency if needed
            all_trades.sort(key=lambda x: x['date'])

            return {
                'total_trades': overall_total_trades,
                'won': overall_won,
                'lost': overall_lost,
                'total_net_pnl': overall_total_net_pnl,
                'avg_net_pnl': overall_avg_net_pnl,
                'trades': all_trades  # Contains trades from all symbols
            }

    def print_analysis(self, verbose=False):
        # Get per-symbol results
        results_per_symbol = self.get_analysis(summary=False)
        if not results_per_symbol:
            print("\nNo trades executed.")
            return

        print("\n--- Per Symbol Analysis ---")
        for symbol, result in results_per_symbol.items():
            print(f"\n📊 === Analysis for {symbol} ===")
            print(f"Total Trades   : {result['total_trades']}")
            print(f"Winning Trades : {result['won']}")
            print(f"Losing Trades  : {result['lost']}")
            print(f"Total Net PnL  : {result['total_net_pnl']:.2f}")
            print(f"Average Net PnL: {result['avg_net_pnl']:.2f}")

            if verbose:
                for i, trade in enumerate(result['trades']):
                    print(f"  • Trade {i+1} on {trade['date']}")
                    print(f"    Size       : {trade['size']}")
                    print(f"    Entry      : {trade['entry_price']:.2f}")
                    print(f"    Exit       : {trade['exit_price']:.2f}")
                    print(f"    Commission : {trade['commission']:.2f}")
                    print(f"    Net PnL    : {trade['net_pnl']:.2f} ({trade['pnl_pct']:.2f}%)")

        # Get and print overall summary results
        overall_results = self.get_analysis(summary=True)
        print("\n--- Overall Summary ---")
        print(f"\n📈 === Total Analysis Across All Symbols ===")
        print(f"Total Trades   : {overall_results['total_trades']}")
        print(f"Winning Trades : {overall_results['won']}")
        print(f"Losing Trades  : {overall_results['lost']}")
        win_rate = (overall_results['won'] / overall_results['total_trades'] * 100) if overall_results['total_trades'] > 0 else 0
        print(f"Win Rate       : {win_rate:.2f}%")
        print(f"Total Net PnL  : {overall_results['total_net_pnl']:.2f}")
        print(f"Average Net PnL: {overall_results['avg_net_pnl']:.2f}")

        if verbose:
             # Optionally print all trades sorted by date if verbose is True for the summary
             # Note: This might be redundant if already printed per symbol
             print("\n  --- All Trades Chronologically ---")
             for i, trade in enumerate(overall_results['trades']):
                 # Find the symbol for this trade (might be slightly inefficient but clear)
                 symbol = next((s for s, res in results_per_symbol.items() if trade in res['trades']), "Unknown")
                 print(f"  • Trade {i+1} ({symbol}) on {trade['date']}")
                 print(f"    Size       : {trade['size']}")
                 print(f"    Entry      : {trade['entry_price']:.2f}")
                 print(f"    Exit       : {trade['exit_price']:.2f}")
                 print(f"    Commission : {trade['commission']:.2f}")
                 print(f"    Net PnL    : {trade['net_pnl']:.2f} ({trade['pnl_pct']:.2f}%)")
