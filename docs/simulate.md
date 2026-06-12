# Simulate

The `simulate/` package is a time-mocked market simulator that runs as a separate process so `freezegun` can mock wall time without affecting the CLI process.

## 1. Module Map

| File             | Purpose                                                              |
|------------------|----------------------------------------------------------------------|
| `simulate.py`    | `Simulate` — the `multiprocessing.Process` that drives the simulation. |
| `simulatecli.py` | `SimulateCLI` — the CLI prompt that controls the simulation.         |

## 2. Why a Separate Process?

`freezegun.freeze_time()` mocks the system clock **only in the process that calls it**. If the simulator and the CLI ran in the same process, the CLI would also be frozen, breaking interactivity.

The CLI process talks to the simulator process via:
- **`command_queue`** (`multiprocessing.Queue`) — buy/sell/positions/transactions/report commands.
- **Shared `Value`s and `Event`** — `pause` / `continue` flags and time-advance signals.
- **File-based state** — JSON snapshots under `path.broker = "simulate/<timestamp>"`.

## 3. `Simulate` (`simulate/simulate.py`)

```python
class Simulate(multiprocessing.Process):
    def __init__(self, ...):
        super().__init__(daemon=True)
        # ... set up shared memory, queues, paths
```

### Construction

- Sets up `BrokerManager.initialize(broker_type='mock', simulation=True)`.
- Loads/saves simulation state to `path.broker/simulate/<timestamp>/`.
- Initializes shared memory:
  - `self.pause_value` (`Value('b', True)`) — whether to pause based on real-world hours.
  - `self.command_queue` (`Queue()`) — CLI → simulator command channel.
  - `self.response_queue` (`Queue()`) — simulator → CLI response channel.
  - `self.stop_event` (`Event()`) — kill the simulator.

### `run()`

The process entry point. Starts three threads:

1. **`_time_iteration()`** — the main day-advance loop.
2. **`_command_handler()`** — the CLI command consumer.
3. **`_persist_state()`** — periodic state-saving.

### `_time_iteration()`

The core day-advance loop. Uses `freezegun.freeze_time()` to set the system clock to the simulated date, advances one day per iteration, and has automatic pause/resume logic based on **real-world** trading hours (because the child process shares real wall time until the next freeze).

**Pause windows** (when the simulator auto-pauses to avoid interfering with live trading):
- **Trading hours:** weekdays 8:30–13:30 (paused so live data is not being downloaded).
- **Data update hours:** 17:30–20:00 (paused so `Market.update_data()` is not contending).

`disable_pause_for_duration(hours)` temporarily disables auto-pause.

### `_simulate()`

Runs **one simulated day**:

1. **Buying evaluation** — calls `Trading.trading_eval(args, product_list)`. May use `ParallelProcessor` for concurrent analysis.
2. **Execute buys** — `Trading.buying_exec(buying_list)`.
3. **Selling evaluation** — `Trading.selling_eval(args)`.
4. **Execute sells** — `Trading.selling_exec(candidates)`.
5. **Daily summary** — prints positions and records.

### `_command_handler()`

Background thread that processes commands from the CLI:

| Command        | Wraps in `freeze_time` via `time_machine_eval` | Action                                    |
|----------------|------------------------------------------------|-------------------------------------------|
| `buy`          | Yes                                            | Manually place a buy order.               |
| `sell`         | Yes                                            | Manually place a sell order.              |
| `positions`    | Yes                                            | Print current positions.                  |
| `transactions` | Yes                                            | Print transaction history.                |
| `trade`        | Yes                                            | Print trade records.                      |
| `report`       | Yes                                            | Print P&L report.                         |

Wrapping each command in `freeze_time` ensures the command runs in the simulated time context (e.g., `datetime.now()` returns the simulated date, not real wall time).

### `_config_save()` / `_config_load()`

Persists/restores simulation state to JSON under `path.broker/simulate/<timestamp>/`:
- `start_time` / `end_time` / `simulation_time` — date range and current cursor.
- `product_list` — symbols being simulated.
- `pause_state` — whether auto-pause is currently active.

## 4. `SimulateCLI` (`simulate/simulatecli.py`)

The CLI prompt (`SIM`).

### Commands

| Command         | Description                                                                       |
|-----------------|-----------------------------------------------------------------------------------|
| `start`         | Launch the `Simulate` process.                                                    |
| `stop`          | Terminate the process.                                                            |
| `pause`         | Pause time advancement.                                                           |
| `continue`      | Resume time advancement.                                                          |
| `ignore_pause`  | Temporarily disables automatic pausing for N hours.                               |
| `config`        | Manages broker simulation paths:                                                 |
|                 | • `list` — show timestamped directories.                                          |
|                 | • `load <path>` — load a previous simulation state.                               |
|                 | • `load previous` — load the most recent.                                         |
| `test`          | Quick presets: `single`, `multiple`, `t1`, `t50`, `all`, or a specific year.       |
| `date`          | Set simulation date range.                                                        |
| `product`       | Set the product list.                                                             |
| `buy` / `sell`  | Send manual trading commands to the running simulation.                            |
| `positions`     | Query simulation state.                                                           |
| `transactions`  | Query transaction history.                                                        |
| `trade`         | Query trade records.                                                              |
| `report`        | Query P&L report.                                                                 |
| `update`        | Update local market database.                                                     |

The CLI caches settings (`_cached_start_time`, `_cached_end_time`, `_cached_product_list`) and applies them when `start` is called. On exit (`on_exit`), it stops and terminates the simulation process.

## 5. State Persistence

A typical simulation directory:

```
~/.config/investment/simulate/20250612_143022/
  ├── state.json           # simulation state (start/end/current time, product list)
  ├── positions.json       # MockBroker state
  ├── transaction.csv      # transaction log
  └── trade.db             # SQLite trades/transactions
```

The state can be reloaded with `config load <path>` or `config load previous` to resume an interrupted simulation.

## 6. Usage Example

```bash
# Launch the simulator
$ python investor.py -s

# In the SIM CLI:
SIM> date 2024-01-01 2024-12-31
SIM> product t5
SIM> start
# ... simulator runs, advancing one day per iteration ...
SIM> positions           # check current positions
SIM> report              # see P&L
SIM> pause               # pause time advancement
SIM> buy 2330 1000       # manual buy
SIM> continue            # resume
SIM> stop                # terminate
```

## 7. Cross-Module Dependencies

```
simulate/simulate.py
  ├── trading/trading.py
  ├── trading/traderecord.py (Recorder)
  └── broker/brokermanager.py

simulate/simulatecli.py
  ├── simulate/simulate.py
  ├── trading/trading.py
  ├── trading/traderecord.py
  └── broker/brokermanager.py
```

## 8. Design Trade-offs

- **Time fidelity:** The simulator advances one day per iteration, not in real time. This lets a year of trading complete in seconds, but means intraday events (tick-by-tick, order book depth) are not simulated.
- **Pause windows:** Auto-pause during real trading hours and data update hours prevents the simulator from competing with live data downloads for the same provider (especially FinMind's quota).
- **Process boundary:** Running in a separate process means the CLI stays responsive and `freezegun` only affects the simulator. The cost is IPC overhead and the need to use `multiprocessing.Queue` for commands.
