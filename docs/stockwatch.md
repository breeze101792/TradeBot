# StockWatch Web UI

A Flask-based web server for viewing the trading bot's open trades and transactions. Exposed on port 5000.

## 1. Module Map

| File              | Purpose                                                          |
|-------------------|------------------------------------------------------------------|
| `server.py`       | `TradeBotServer` — the Flask application.                        |
| `commands.py`     | `register_stockwatch_commands` — registers `server start` in CLI. |
| `notifier.py`     | Empty placeholder for future notification features.              |
| `templates/`      | Jinja2 HTML templates (4 files).                                 |

## 2. `TradeBotServer` (`stockwatch/server.py`)

```python
class TradeBotServer:
    def __init__(port=5000, host='0.0.0.0')
    def run(debug=False, use_reloader=False)
```

### Construction

- Creates a Flask app with the template directory at `stockwatch/templates/`.
- Calls `_register_routes()` to register four routes.

### Routes

| Route                  | Method | Description                                                                          |
|------------------------|--------|--------------------------------------------------------------------------------------|
| `/`                    | GET    | Home page with links to other pages.                                                 |
| `/puretext`            | GET    | Static text placeholder page (used as a template for adding new routes).             |
| `/show_trades`         | GET    | Shows all open trades in a table.                                                    |
| `/show_transactions`   | GET    | Shows transaction summary with duration filter (`day`/`week`/`month`/`year`/`all`).  |

### `/show_trades`

Instantiates a `Recorder`, fetches all open positions, and prepares a dict per position:

```python
{
    'trade_id': '...',
    'symbol': '2330',
    'strategy': 'MovingAverageCrossover',
    'current_size': 1000,
    'is_open': True,
    'transactions_count': 2,
    'profit': ...,
}
```

Renders `show_trades.html`. If there are no open trades, displays "No open trades found."

### `/show_transactions`

Reads the `duration` query parameter (default: `'week'`), calls `BrokerManager().transaction_mgr.get_summary_data(duration)`, and renders `show_transactions.html` with:
- `summary_data` — overall P&L metrics.
- `per_symbol_table_data` — per-symbol breakdown.
- `current_positions_data` — current open positions.
- `period_display` — human-readable period.
- `current_duration` — for the active filter link.

The page handles three display states:
- **No data**: shows "No transactions or relevant initial positions found".
- **Only initial positions**: shows the summary table + a "stock status" table.
- **Full data**: shows the overall summary table + per-symbol detailed table (10 columns: buys, sells, avg prices, cost, revenue, net profit, last trade date).

### `run(debug=False, use_reloader=False)`

Starts the Flask development server. Catches `KeyboardInterrupt` and general exceptions gracefully.

**Note:** `use_reloader=False` is the default to prevent the development server from double-initializing `BrokerManager` and double-starting the order service.

## 3. CLI Integration (`stockwatch/commands.py`)

A thin module with two functions:

```python
def register_stockwatch_commands(cli_instance):
    cli_instance.regist_cmd(
        "server", cmd_server, "Stockwatch server", ["start"], group="tools"
    )

def cmd_server(args):
    # handles "server start" subcommand
    # instantiates TradeBotServer(port=5000, host='0.0.0.0') and calls run()
```

This is registered into the live-trading CLI (`TDCLI`) and the simulate CLI (`SimulateCLI`).

**No "server stop" subcommand** is currently implemented.

## 4. `notifier.py`

Currently empty (1 line). Reserved for future notification features (email, SMS, desktop push).

## 5. Templates

Four Jinja2 HTML templates with simple inline CSS (no framework):

### `index.html`

Home page. Contains links to `/puretext`, `/show_trades`, and `/show_transactions`. Uses minimal CSS with a blue header and card-style containers.

### `puretext.html`

Static text placeholder page with a back link. Serves as an example for adding new routes.

### `show_trades.html`

Displays a table with columns: Trade ID, Symbol, Strategy, Current Qty, Is Open, Transactions, Profit. If no open trades, shows "No open trades found." Uses zebra-striped table styling.

### `show_transactions.html`

The most complex template. Includes:
- A duration filter row linking to `?duration=day`/`week`/`month`/`year`/`all`. The active filter is highlighted via the `current_duration` template variable.
- Three display states (no data, initial positions only, full data — see above).
- A 10-column per-symbol table: Symbol, Buys, Sells, Avg Buy Price, Avg Sell Price, Cost, Revenue, Net Profit, Last Trade Date.

## 6. Usage

```bash
# From the live-trading CLI (TDCLI) or simulate CLI (SIM):
TDCLI> server start
# Server running on http://0.0.0.0:5000

# In a browser:
# http://localhost:5000/                # home
# http://localhost:5000/show_trades     # open trades
# http://localhost:5000/show_transactions  # transaction summary (default: week)
# http://localhost:5000/show_transactions?duration=month  # monthly summary
```

## 7. Important Assumptions

- `BrokerManager.initialize()` **must have been called** before the server starts (typically done by `Core.initialize()` or `Simulate.__init__`).
- The server directly instantiates `Recorder` and `BrokerManager` per-request, so it reflects the current state of the SQLite trade DB and broker JSON state files.
- The Flask development server is **not for production**. Use a WSGI server (gunicorn, uWSGI) for production deployments.
