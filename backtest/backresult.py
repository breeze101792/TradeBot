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

    def show_info(self):
        """
        Displays descriptions of the key indicators shown in the analysis table
        using tabulate for formatting.
        """
        info_data = [
            ["SQN (System Quality Number)", "Measures the quality of a trading system based on the ratio of the average profit per trade to the standard deviation of trade profits. Higher SQN values (e.g., > 2) generally indicate a better system."],
            ["VRW (Volatility Ratio Weighted)", "A metric related to volatility and returns, often used in conjunction with SQN. Higher VRW values are generally preferred."],
            ["Sharpe Ratio", "Measures risk-adjusted return. It is the average return earned in excess of the risk-free rate per unit of volatility (total risk). Higher Sharpe ratio values are better."],
            ["Max DD (Maximum Drawdown)", "The largest peak-to-trough decline in the value of an investment during a specific period. Represents the maximum loss from a peak before a new peak is attained. Lower Max DD is better."],
            ["Profit", "The total profit percentage relative to the initial cash."],
            ["Buys", "The total number of buy trades executed."],
            ["Buy Win%", "The percentage of buy trades that were profitable."],
            ["Sells", "The total number of sell trades executed."],
            ["Sell Win%", "The percentage of sell trades that were profitable."],
            ["Avg Duration", "The average duration (in bars/periods) of trades."]
        ]

        headers = ["Indicator", "Description"]

        print("\n--- Indicator Descriptions ---")
        try:
            table_str = tabulate(
                info_data,
                headers=headers,
                tablefmt="grid", # Use grid format for clear separation
                maxcolwidths=[None, self.def_max_len_a_cell] # Limit description width
            )
            print(table_str)
        except Exception as e:
            dbg_error(f"Error generating info table with tabulate: {e}")
            print("\nError: Could not generate indicator descriptions table.")
        print() # Add a blank line at the end

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

    def _prepare_analysis_data(self, mode="all"):
        """
        Prepares the main backtest results data and headers for display or saving.

        Args:
            mode (str): Defines how results are prepared.
                        "all": Prepares all individual backtest results.
                        "average": Prepares only the average rows per strategy.
                        "mix": Prepares all individual results and their strategy averages.
                        Defaults to "all".

        Returns:
            tuple: A tuple containing (headers, data_rows).
                   headers (list): List of column headers.
                   data_rows (list): List of lists, where each inner list is a row of data.
                   Returns (None, None) if no results are found.
        """
        if not self.result_list:
            return None, None

        self.result_list.sort(key=lambda x: x.get('score', float('-inf')), reverse=True)

        headers = [
            "Symbol", "Strategy", "Score", "Profit", "Sharpe", "VWR",
            "Max DD", "SQN", "Buys", "Buy Win%", "Sells", "Sell Win%", "Avg Duration"
        ]
        
        invalid_number = float('nan')
        na_string = 'N/A'

        grouped_results = {}

        for i, each_result in enumerate(self.result_list):
            try:
                raw_strategy_list = each_result.get('strategy', [])
                original_strategy_key = ",".join(map(str, raw_strategy_list)) if raw_strategy_list else na_string

                display_symbol, display_strategy = self._get_formatted_symbol_strategy(each_result)

                if original_strategy_key not in grouped_results:
                    grouped_results[original_strategy_key] = {
                        'rows': [],
                        'profit_pct_values': [], 'sharpe_values': [], 'vwr_values': [],
                        'max_dd_values': [], 'sqn_values': [], 'score_values': [], 'buy_total_values': [],
                        'buy_win_pct_values': [], 'sell_total_values': [], 'sell_win_pct_values': [],
                        'average_duration_values': []
                    }
                
                current_group = grouped_results[original_strategy_key]


                profit_pct = each_result.get('profit', invalid_number)

                sharpe = each_result.get('sharpe', invalid_number)
                if sharpe is None or not isinstance(sharpe, (int, float)): sharpe = invalid_number

                vwr = each_result.get('vwr', invalid_number)
                if vwr is None or not isinstance(vwr, (int, float)): vwr = invalid_number

                drawdown = each_result.get('drawdown', {}).get('max', {}).get('drawdown', invalid_number)
                if drawdown is None or not isinstance(drawdown, (int, float)): drawdown = invalid_number

                sqn = each_result.get('sqn', {}).get('sqn', invalid_number)
                if sqn is None or not isinstance(sqn, (int, float)): sqn = invalid_number

                trade_analyzer = each_result.get('trade_analyzer', {})
                buy_total = trade_analyzer.get('total', {}).get('total', 0)
                buy_won = trade_analyzer.get('won', {}).get('total', 0)
                buy_winning_rate = (buy_won / buy_total * 100) if buy_total > 0 else 0.0
                average_duration = trade_analyzer.get('len', {}).get('average', 0)

                pta_analyzer = each_result.get('pta', {})
                sell_total = pta_analyzer.get('total_trades', 0)
                sell_won = pta_analyzer.get('won', 0)
                sell_winning_rate = (sell_won / sell_total * 100) if sell_total > 0 else 0.0

                score = each_result.get('score', invalid_number)

                row = [
                    display_symbol,
                    display_strategy,
                    score,
                    profit_pct,
                    sharpe,
                    vwr,
                    drawdown,
                    sqn,
                    buy_total,
                    buy_winning_rate,
                    sell_total,
                    sell_winning_rate,
                    average_duration
                ]
                current_group['rows'].append(row)

                if isinstance(profit_pct, (int, float)): current_group['profit_pct_values'].append(profit_pct)
                if isinstance(score, (int, float)): current_group['score_values'].append(score)
                if isinstance(sharpe, (int, float)): current_group['sharpe_values'].append(sharpe)
                if isinstance(vwr, (int, float)): current_group['vwr_values'].append(vwr)
                if isinstance(drawdown, (int, float)): current_group['max_dd_values'].append(drawdown)
                if isinstance(sqn, (int, float)): current_group['sqn_values'].append(sqn)
                if isinstance(buy_total, (int, float)): current_group['buy_total_values'].append(buy_total)
                if isinstance(buy_winning_rate, (int, float)): current_group['buy_win_pct_values'].append(buy_winning_rate)
                if isinstance(sell_total, (int, float)): current_group['sell_total_values'].append(sell_total)
                if isinstance(sell_winning_rate, (int, float)): current_group['sell_win_pct_values'].append(sell_winning_rate)
                if isinstance(average_duration, (int, float)): current_group['average_duration_values'].append(average_duration)

            except Exception as e:
                dbg_error(f"Error processing result item index {i}: {e}")
                dbg_error(f"Problematic result item content: {each_result}")
                traceback_output = traceback.format_exc()
                dbg_error(traceback_output)
                raw_strategy_list_err = each_result.get('strategy', [])
                original_strategy_key_err = ",".join(map(str, raw_strategy_list_err)) if raw_strategy_list_err else na_string
                if original_strategy_key_err not in grouped_results:
                     grouped_results[original_strategy_key_err] = {
                        'rows': [], 'profit_pct_values': [], 'sharpe_values': [], 'vwr_values': [],
                        'max_dd_values': [], 'sqn_values': [], 'buy_total_values': [],
                        'buy_win_pct_values': [], 'sell_total_values': [], 'sell_win_pct_values': [],
                        'average_duration_values': []
                    }
                grouped_results[original_strategy_key_err]['rows'].append([
                    'ERROR', f'Check Logs (Index {i})', None, None, None, None, None, None, None, None, None, None, None
                ])
        
        final_table_data = []
        sorted_strategy_keys = sorted(grouped_results.keys())

        for strategy_key in sorted_strategy_keys:
            data = grouped_results[strategy_key]
            if mode == "all" or mode == "mix":
                final_table_data.extend(data['rows'])

            if (mode == "average" or mode == "mix") and any(data[metric_list] for metric_list in data if metric_list.endswith('_values')):
                avg_profit_pct = sum(data['profit_pct_values']) / len(data['profit_pct_values']) if data['profit_pct_values'] else invalid_number
                avg_score = sum(data['score_values']) / len(data['score_values']) if data['score_values'] else invalid_number
                avg_sharpe = sum(data['sharpe_values']) / len(data['sharpe_values']) if data['sharpe_values'] else invalid_number
                avg_vwr = sum(data['vwr_values']) / len(data['vwr_values']) if data['vwr_values'] else invalid_number
                avg_max_dd = sum(data['max_dd_values']) / len(data['max_dd_values']) if data['max_dd_values'] else invalid_number
                avg_sqn = sum(data['sqn_values']) / len(data['sqn_values']) if data['sqn_values'] else invalid_number
                avg_buy_total = sum(data['buy_total_values']) / len(data['buy_total_values']) if data['buy_total_values'] else invalid_number
                avg_buy_win_pct = sum(data['buy_win_pct_values']) / len(data['buy_win_pct_values']) if data['buy_win_pct_values'] else invalid_number
                avg_sell_total = sum(data['sell_total_values']) / len(data['sell_total_values']) if data['sell_total_values'] else invalid_number
                avg_sell_win_pct = sum(data['sell_win_pct_values']) / len(data['sell_win_pct_values']) if data['sell_win_pct_values'] else invalid_number
                avg_average_duration = sum(data['average_duration_values']) / len(data['average_duration_values']) if data['average_duration_values'] else invalid_number

                display_strategy_key_avg = (strategy_key[:self.def_max_len_a_cell - 3] + '...') if len(strategy_key) > self.def_max_len_a_cell else strategy_key

                average_row_for_strategy = [
                    "Average",
                    display_strategy_key_avg,
                    avg_score,
                    avg_profit_pct,
                    avg_sharpe, avg_vwr, avg_max_dd, avg_sqn,
                    avg_buy_total, avg_buy_win_pct, avg_sell_total, avg_sell_win_pct,
                    avg_average_duration
                ]
                final_table_data.append(average_row_for_strategy)
        
        return headers, final_table_data

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
        headers, final_table_data = self._prepare_analysis_data(mode)

        if not final_table_data:
            dbg_info("No results found to display.")
            return False

        try:
            table_str = tabulate(
                final_table_data,
                headers=headers,
                tablefmt="grid",
                floatfmt=".2f",
                stralign="right",
                numalign="right",
                missingval='N/A'
            )
            print("\n--- Backtest Results Summary ---")
            print(table_str)

        except Exception as e:
            dbg_error(f"Error generating results table with tabulate: {e}")
            print("\nError: Could not generate results summary table.")

        print()
        return True

    def _prepare_annual_return_data(self, mode="all"):
        """
        Prepares the annual returns data and headers for display or saving.

        Args:
            mode (str): Defines how results are prepared.
                        "all": Prepares all individual annual return results.
                        "average": Prepares only the average rows per strategy.
                        "mix": Prepares all individual results and their strategy averages.
                        Defaults to "all".

        Returns:
            tuple: A tuple containing (headers, data_rows).
                   headers (list): List of column headers.
                   data_rows (list): List of lists, where each inner list is a row of data.
                   Returns (None, None) if no results are found.
        """
        if not self.result_list:
            return None, None

        na_string = 'N/A'
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

        if not annual_returns_data:
            return None, None

        all_years = set()
        pivoted_returns_dict = {}

        for symbol, strategy, year_str, return_val in annual_returns_data:
            all_years.add(year_str)
            if (symbol, strategy) not in pivoted_returns_dict:
                pivoted_returns_dict[(symbol, strategy)] = {}
            pivoted_returns_dict[(symbol, strategy)][year_str] = return_val

        if not pivoted_returns_dict:
            return None, None

        sorted_years = sorted(list(all_years))
        annual_headers = ["Symbol", "Strategy"] + sorted_years

        final_table_data_for_tabulate = []
        
        unique_formatted_strategies = sorted(list(set(s_key for _, s_key in pivoted_returns_dict.keys())))

        for current_formatted_strategy in unique_formatted_strategies:
            rows_for_this_strategy_group = []
            yearly_returns_accumulator_for_avg = {year: [] for year in sorted_years}

            symbol_data_for_current_strategy = []
            for (p_symbol, p_strategy), year_map in pivoted_returns_dict.items():
                if p_strategy == current_formatted_strategy:
                    symbol_data_for_current_strategy.append((p_symbol, year_map))
            
            symbol_data_for_current_strategy.sort(key=lambda x: x[0])

            for p_symbol, year_map in symbol_data_for_current_strategy:
                row = [p_symbol, current_formatted_strategy] 
                for year in sorted_years:
                    return_val = year_map.get(year, na_string)
                    row.append(return_val)
                    if isinstance(return_val, (int, float)):
                        yearly_returns_accumulator_for_avg[year].append(return_val)
                rows_for_this_strategy_group.append(row)
            
            if mode == "all" or mode == "mix":
                final_table_data_for_tabulate.extend(rows_for_this_strategy_group)

            if (mode == "average" or mode == "mix") and any(yearly_returns_accumulator_for_avg[year] for year in sorted_years):
                avg_row_for_strategy = ["Average", current_formatted_strategy]
                for year in sorted_years:
                    year_specific_values = yearly_returns_accumulator_for_avg[year]
                    if year_specific_values:
                        avg_return = sum(year_specific_values) / len(year_specific_values)
                        avg_row_for_strategy.append(avg_return)
                    else:
                        avg_row_for_strategy.append(na_string)
                final_table_data_for_tabulate.append(avg_row_for_strategy)
        
        return annual_headers, final_table_data_for_tabulate

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
        annual_headers, final_table_data_for_tabulate = self._prepare_annual_return_data(mode)

        if not final_table_data_for_tabulate:
            dbg_info("No annual return data found to display.")
            return False

        print("\n--- Annual Returns ---")
        try:
            annual_table_str = tabulate(
                final_table_data_for_tabulate,
                headers=annual_headers,
                tablefmt="grid",
                floatfmt=".2f",
                stralign="right",
                numalign="right",
                missingval='N/A'
            )
            print(annual_table_str)
        except Exception as e:
            dbg_error(f"Error generating annual returns table with tabulate: {e}")
            print("\nError: Could not generate annual returns table.")
        print()
        return True
