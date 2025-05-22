import traceback
from tabulate import tabulate # Import tabulate

from utility.debug import *

class BackResult:
    def __init__(self, result_list):
        """
        Initializes the BackResult object.

        Args:
            result_list (list): A list of dictionaries, where each dictionary
                                contains the analysis results from a backtest run.
        """
        self.def_max_len_a_cell = 72
        self.result_list = result_list if result_list is not None else []

    def _get_formatted_symbol_strategy(self, each_result):
        """
        Extracts and formats symbol and strategy strings from a result item.
        """
        na_string = 'N/A'
        symbol_list = each_result.get('data', [])
        strategy_list = each_result.get('strategy', [])
        symbol = ",".join(map(str, symbol_list)) if symbol_list else na_string
        strategy = ",".join(map(str, strategy_list)) if strategy_list else na_string

        # Basic truncation
        symbol = (symbol[:self.def_max_len_a_cell - 3] + '...') if len(symbol) > self.def_max_len_a_cell else symbol
        strategy = (strategy[:self.def_max_len_a_cell - 3] + '...') if len(strategy) > self.def_max_len_a_cell else strategy
        return symbol, strategy

    def show_analysis(self, mode="all"):
        """
        Displays the main backtest results in a formatted table using tabulate.

        Args:
            mode (str): Defines how results are displayed.
                        "all": Displays all individual backtest results.
                        "average": Displays only the average rows per strategy.
                        "mix": Displays all individual results and their strategy averages.
                        Defaults to "all".

        Returns:
            bool: True if results were displayed (or attempted), False if no
                  results were found.
        """
        if not self.result_list:
            dbg_info("No results found to display.")
            return False

        headers = [
            "Symbol", "Strategy", "Profit %", "Sharpe", "VWR",
            "Max DD %", "SQN", "Buys", "Buy Win %", "Sells", "Sell Win %"
        ]
        
        invalid_number = float('nan') # Use NaN for missing numeric data
        na_string = 'N/A' # String used by tabulate for missing values

        grouped_results = {} # Key: original_strategy_key, Value: dict of lists for rows and metrics

        for i, each_result in enumerate(self.result_list):
            try:
                # Original strategy identifier for grouping
                raw_strategy_list = each_result.get('strategy', [])
                original_strategy_key = ",".join(map(str, raw_strategy_list)) if raw_strategy_list else na_string

                # Formatted symbol and strategy for display in individual rows
                display_symbol, display_strategy = self._get_formatted_symbol_strategy(each_result)

                # Initialize group if it doesn't exist
                if original_strategy_key not in grouped_results:
                    grouped_results[original_strategy_key] = {
                        'rows': [],
                        'profit_pct_values': [], 'sharpe_values': [], 'vwr_values': [],
                        'max_dd_values': [], 'sqn_values': [], 'buy_total_values': [],
                        'buy_win_pct_values': [], 'sell_total_values': [], 'sell_win_pct_values': []
                    }
                
                current_group = grouped_results[original_strategy_key]

                # --- Extract Data ---
                init_cash = each_result.get('init_cash', 0)
                # final_cash = each_result.get('cash', 0)
                # profit_pct = ((final_cash / init_cash - 1) * 100) if init_cash != 0 else 0.0

                sharpe = each_result.get('sharpe', invalid_number)
                if sharpe is None or not isinstance(sharpe, (int, float)): sharpe = invalid_number

                vwr = each_result.get('vwr', invalid_number)
                if vwr is None or not isinstance(vwr, (int, float)): vwr = invalid_number

                drawdown = each_result.get('drawdown', {}).get('max', {}).get('drawdown', invalid_number)
                if drawdown is None or not isinstance(drawdown, (int, float)): drawdown = invalid_number

                sqn = each_result.get('sqn', {}).get('sqn', invalid_number)
                if sqn is None or not isinstance(sqn, (int, float)): sqn = invalid_number

                # Trade Analyzer (Buy side focus)
                trade_analyzer = each_result.get('trade_analyzer', {})
                buy_total = trade_analyzer.get('total', {}).get('total', 0)
                buy_won = trade_analyzer.get('won', {}).get('total', 0)
                buy_winning_rate = (buy_won / buy_total * 100) if buy_total > 0 else 0.0

                # dbg_info(trade_analyzer)
                # profit_pct = trade_analyzer.pnl.gross.total / init_cash * 100
                profit_pct = trade_analyzer.get('pnl', {}).get('gross', {}).get('total', 0) / init_cash * 100

                # Partial Trade Analyzer (Sell side focus - from pta)
                pta_analyzer = each_result.get('pta', {})
                sell_total = pta_analyzer.get('total_trades', 0)
                sell_won = pta_analyzer.get('won', 0)
                sell_winning_rate = (sell_won / sell_total * 100) if sell_total > 0 else 0.0

                # annual_returns = each_result.get('annual_return', {}) # Removed for this method

                # --- Prepare Row Data for Tabulate ---
                row = [
                    display_symbol,
                    display_strategy,
                    profit_pct,
                    sharpe,
                    vwr,
                    drawdown, # Already a percentage
                    sqn,
                    buy_total,
                    buy_winning_rate,
                    sell_total,
                    sell_winning_rate
                ]
                current_group['rows'].append(row)

                # --- Collect data for averaging within the group ---
                if isinstance(profit_pct, (int, float)): current_group['profit_pct_values'].append(profit_pct)
                if isinstance(sharpe, (int, float)): current_group['sharpe_values'].append(sharpe)
                if isinstance(vwr, (int, float)): current_group['vwr_values'].append(vwr)
                if isinstance(drawdown, (int, float)): current_group['max_dd_values'].append(drawdown)
                if isinstance(sqn, (int, float)): current_group['sqn_values'].append(sqn)
                if isinstance(buy_total, (int, float)): current_group['buy_total_values'].append(buy_total)
                if isinstance(buy_winning_rate, (int, float)): current_group['buy_win_pct_values'].append(buy_winning_rate)
                if isinstance(sell_total, (int, float)): current_group['sell_total_values'].append(sell_total)
                if isinstance(sell_winning_rate, (int, float)): current_group['sell_win_pct_values'].append(sell_winning_rate)

            except Exception as e:
                dbg_error(f"Error processing result item index {i}: {e}")
                dbg_error(f"Problematic result item content: {each_result}")
                traceback_output = traceback.format_exc()
                dbg_error(traceback_output)
                # Add an error row to the current group's rows
                # Ensure original_strategy_key is defined even in error to avoid crashing here
                raw_strategy_list_err = each_result.get('strategy', [])
                original_strategy_key_err = ",".join(map(str, raw_strategy_list_err)) if raw_strategy_list_err else na_string
                if original_strategy_key_err not in grouped_results: # Should not happen if init logic is correct
                     grouped_results[original_strategy_key_err] = {
                        'rows': [], 'profit_pct_values': [], 'sharpe_values': [], 'vwr_values': [],
                        'max_dd_values': [], 'sqn_values': [], 'buy_total_values': [],
                        'buy_win_pct_values': [], 'sell_total_values': [], 'sell_win_pct_values': []
                    }
                grouped_results[original_strategy_key_err]['rows'].append([
                    'ERROR', f'Check Logs (Index {i})', None, None, None, None, None, None, None, None, None
                ])
        
        # --- Assemble Final Table Data with Per-Strategy Averages ---
        final_table_data = []
        sorted_strategy_keys = sorted(grouped_results.keys())

        for strategy_key in sorted_strategy_keys:
            data = grouped_results[strategy_key]
            if mode == "all" or mode == "mix":
                final_table_data.extend(data['rows']) # Add all rows for this strategy

            # Calculate averages for this strategy
            if (mode == "average" or mode == "mix") and any(data[metric_list] for metric_list in data if metric_list.endswith('_values')): # Check if any metric data exists
                avg_profit_pct = sum(data['profit_pct_values']) / len(data['profit_pct_values']) if data['profit_pct_values'] else invalid_number
                avg_sharpe = sum(data['sharpe_values']) / len(data['sharpe_values']) if data['sharpe_values'] else invalid_number
                avg_vwr = sum(data['vwr_values']) / len(data['vwr_values']) if data['vwr_values'] else invalid_number
                avg_max_dd = sum(data['max_dd_values']) / len(data['max_dd_values']) if data['max_dd_values'] else invalid_number
                avg_sqn = sum(data['sqn_values']) / len(data['sqn_values']) if data['sqn_values'] else invalid_number
                avg_buy_total = sum(data['buy_total_values']) / len(data['buy_total_values']) if data['buy_total_values'] else invalid_number
                avg_buy_win_pct = sum(data['buy_win_pct_values']) / len(data['buy_win_pct_values']) if data['buy_win_pct_values'] else invalid_number
                avg_sell_total = sum(data['sell_total_values']) / len(data['sell_total_values']) if data['sell_total_values'] else invalid_number
                avg_sell_win_pct = sum(data['sell_win_pct_values']) / len(data['sell_win_pct_values']) if data['sell_win_pct_values'] else invalid_number

                # Truncate strategy_key for display in average row if it's too long
                display_strategy_key_avg = (strategy_key[:self.def_max_len_a_cell - 3] + '...') if len(strategy_key) > self.def_max_len_a_cell else strategy_key

                average_row_for_strategy = [
                    "Average",
                    display_strategy_key_avg, # Use the (potentially truncated) strategy key
                    avg_profit_pct, avg_sharpe, avg_vwr, avg_max_dd, avg_sqn,
                    avg_buy_total, avg_buy_win_pct, avg_sell_total, avg_sell_win_pct
                ]
                final_table_data.append(average_row_for_strategy)

        # --- Generate and Print Table ---
        try:
            # Use tabulate to create the table string
            # 'grid' format provides clear borders
            # 'floatfmt=".2f"' formats floats to 2 decimal places
            # 'stralign="right"' aligns strings to the right (like numbers)
            # 'missingval="N/A"' displays missing data as N/A
            table_str = tabulate(
                final_table_data,
                headers=headers,
                tablefmt="grid",
                floatfmt=".2f",
                stralign="right", # Align string columns right for consistency
                numalign="right", # Align numeric columns right
                missingval=na_string
            )
            print("\n--- Backtest Results Summary ---")
            print(table_str)

        except Exception as e:
            dbg_error(f"Error generating results table with tabulate: {e}")
            print("\nError: Could not generate results summary table.")

        print() # Add a blank line at the end
        return True # Indicate successful display attempt

    def show_annual_return(self, mode="all"):
        """
        Displays the annual returns in a formatted table using tabulate.

        Args:
            mode (str): Defines how results are displayed.
                        "all": Displays all individual annual return results.
                        "average": Displays only the average rows per strategy.
                        "mix": Displays all individual results and their strategy averages.
                        Defaults to "all".

        Returns:
            bool: True if results were displayed, False if no results or
                  annual return data were found.
        """
        if not self.result_list:
            dbg_info("No results found to display annual returns.")
            return False

        na_string = 'N/A' # String used by tabulate for missing values
        annual_returns_data = []

        for each_result in self.result_list:
            try:
                symbol, strategy = self._get_formatted_symbol_strategy(each_result)

                annual_returns = each_result.get('annual_return', {})
                if annual_returns:
                    for year, ret in annual_returns.items():
                        if isinstance(ret, (int, float)):
                            annual_returns_data.append([symbol, strategy, str(year), ret])
            except Exception as e:
                dbg_error(f"Error processing result item for annual returns: {e}")
                # Optionally skip this item or add an error marker to annual_returns_data

        if not annual_returns_data:
            dbg_info("No annual return data found to display.")
            return False

        print("\n--- Annual Returns ---")

        # Step 1: Collect all unique years and restructure data
        all_years = set()
        pivoted_returns_dict = {} # Key: (symbol, strategy), Value: {year: return_val}

        for symbol, strategy, year_str, return_val in annual_returns_data:
            all_years.add(year_str)
            if (symbol, strategy) not in pivoted_returns_dict:
                pivoted_returns_dict[(symbol, strategy)] = {}
            pivoted_returns_dict[(symbol, strategy)][year_str] = return_val

        if not pivoted_returns_dict: # Check if dictionary is empty after population
            dbg_info("No valid annual return data to pivot and display.")
            return False

        sorted_years = sorted(list(all_years))
        annual_headers = ["Symbol", "Strategy"] + sorted_years

        # Step 2: Generate table data with per-strategy averages
        final_table_data_for_tabulate = []
        
        # Get unique formatted strategies for grouping.
        # The 'strategy' in (symbol, strategy) key of pivoted_returns_dict is already formatted/truncated.
        unique_formatted_strategies = sorted(list(set(s_key for _, s_key in pivoted_returns_dict.keys())))

        for current_formatted_strategy in unique_formatted_strategies:
            rows_for_this_strategy_group = [] # Stores actual row lists for tabulate display
            yearly_returns_accumulator_for_avg = {year: [] for year in sorted_years}

            # Collect data for symbols under the current strategy.
            # Create a list of (symbol, year_map) for the current strategy to sort by symbol.
            symbol_data_for_current_strategy = []
            for (p_symbol, p_strategy), year_map in pivoted_returns_dict.items():
                if p_strategy == current_formatted_strategy:
                    symbol_data_for_current_strategy.append((p_symbol, year_map))
            
            # Sort by symbol (p_symbol is the first element of the tuple)
            symbol_data_for_current_strategy.sort(key=lambda x: x[0])

            for p_symbol, year_map in symbol_data_for_current_strategy:
                # p_symbol is formatted_symbol, current_formatted_strategy is formatted_strategy
                row = [p_symbol, current_formatted_strategy] 
                for year in sorted_years:
                    return_val = year_map.get(year, na_string)
                    row.append(return_val)
                    if isinstance(return_val, (int, float)):
                        yearly_returns_accumulator_for_avg[year].append(return_val)
                rows_for_this_strategy_group.append(row)
            
            # Add all symbol rows for this strategy to the final table
            if mode == "all" or mode == "mix":
                final_table_data_for_tabulate.extend(rows_for_this_strategy_group)

            # Calculate and add average row for this strategy, if there were any rows
            if (mode == "average" or mode == "mix") and any(yearly_returns_accumulator_for_avg[year] for year in sorted_years):
                avg_row_for_strategy = ["Average", current_formatted_strategy] # Strategy name is already formatted
                for year in sorted_years:
                    year_specific_values = yearly_returns_accumulator_for_avg[year]
                    if year_specific_values:
                        avg_return = sum(year_specific_values) / len(year_specific_values)
                        avg_row_for_strategy.append(avg_return)
                    else:
                        avg_row_for_strategy.append(na_string)
                final_table_data_for_tabulate.append(avg_row_for_strategy)
        
        # Step 3: Tabulate the final data
        if not final_table_data_for_tabulate:
            dbg_info("No data to tabulate for annual returns after processing.")
            # This might happen if all strategies had no valid annual returns, though pivoted_returns_dict check should catch most.
            return False 

        try:
            annual_table_str = tabulate(
                final_table_data_for_tabulate,
                headers=annual_headers,
                tablefmt="grid",
                floatfmt=".2f",
                stralign="right",
                numalign="right",
                missingval=na_string
            )
            print(annual_table_str)
        except Exception as e:
            dbg_error(f"Error generating annual returns table with tabulate: {e}")
            print("\nError: Could not generate annual returns table.")
        print()
        return True
