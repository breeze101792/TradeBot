# CLAUDE.md

TradeBot is a Taiwan-stock (TWSE) algorithmic trading platform: live
trading, backtest, time-mocked simulate, in-app test. Entry point is
`investor.py` which dispatches to one of four sub-CLIs by mode flag.
Modules run directly from the repo root — there is no
`pyproject.toml` or `setup.py`. Dependencies in `requirements.txt`.

## Common Commands

```bash
# Install deps (one venv: .venv or .pyvenv — either works)
pip install -r requirements.txt
source .venv/bin/activate

# Run the app (one of four modes)
.venv/bin/python investor.py            # live trade, mock broker
.venv/bin/python investor.py -b         # backtest
.venv/bin/python investor.py -s         # simulate (time-mocked)
.venv/bin/python investor.py -t         # in-app test suite
.venv/bin/python lab/<bench>.py         # experimental bench scripts in lab/
```

CLI flags: `-d` / `--trade-mode {backtest,test,trade,simulate}` /
`-b` / `-t` / `-s` / `--broker {mock,shioaji}` /
`-p <product_ids>` / `--time-frame {day,week}`.
Note: `--develoment` is a typo in the source and intentional.

## Architecture (non-obvious bits)

- `core/Core` spawns 5 long-lived threads for the live-trade mode
  (`datasource_service`, `trading_service`, `selling_service`,
  `broker_service`, `heatbeat_service`); they cooperate via
  `TradingStatus`. `simulate/` runs as a separate `multiprocessing.Process`
  so `freezegun` can mock time. `backtest/` and `test/` are
  single-process.
- Strategies register at three `Level`s in `strategy/strategy.py`:
  `OFFICIAL` (production), `BETA` (active but unproven),
  `TESTING` (only loaded with `test>0`).
- The custom logger in `utility/debug.py` is used everywhere — use
  `dbg_info` / `dbg_warning` / `dbg_error`, never `print`.
  `DebugSetting.setDbgPath()` is called by `investor.py` early.
- Config: `cm.get('key')` / `cm.set('key', val)` (dot-notation),
  not `os.environ`. Paths under `~/.config/investment/`, overridable.

## Domain

TWSE-only. Providers: `FindMind` (FinMind API — marked experimental,
source comment says "not all verified"), `TWSE` (`twstock`),
`Yahoo` (`yfinance`). Brokers: `MockBroker` (default dev) and
`ShioajiBroker` (real, Sinopac). Market hours 09:00–13:30, daily
data finalization 18:00.

## Known issues

README's `FIXME` / `TODO` / `Potential Risk` sections are
canonical. Most-cited: `trading/traderecord.py` size inconsistency
after manual broker intervention; `core.py` typo `args.broker_type
== 'mcok'` (dead branch — actual value is `'mock'`).
