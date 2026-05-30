# Stock Trading & Analysis Agent System (`stock_agent`)

A robust, modular, and AI-driven automated trading and analysis system. This application gathers stock market prices, corporate disclosures, and news sentiment, parses them through specialized agent chains (technical, fundamental, and news sentiment), synthesizes trading actions using LLMs, verifies risk gates, and automatically executes orders on virtual or real broker APIs.

## Directory Layout

```
stock_agent/
├── pyproject.toml                  # Dependencies & build configuration
├── README.md                       # Project overview & guide
├── .env.example                    # Environment variable template
├── docker-compose.yml              # PostgreSQL + pgAdmin development stack
│
├── src/stock_agent/                # Main package
│   ├── core/                       # ① Pure Domain layer (0 external dependencies)
│   │   ├── schemas.py              # Pydantic schemas (Bar, Signal, Order, Position)
│   │   ├── interfaces.py           # Broker, DataRepository, LLMClient Protocols
│   │   ├── enums.py                # Action, OrderType, OrderStatus
│   │   └── config.py               # Pydantic settings parsing
│   │
│   ├── agents/                     # ② Multi-Agent Analysis Suite
│   │   ├── base.py                 # Abstract Analyst base
│   │   ├── technical.py            # Technical indicator-based analysis
│   │   ├── fundamental.py          # Key fundamental health analyst
│   │   ├── news.py                 # LLM sentiment analyzer for Naver/DART
│   │   └── synthesizer.py          # Master synthesizer that outputs trade signals
│   │
│   ├── collectors/                 # ② Periodic Data Gathering & Simulation
│   │   ├── price_collector.py      # Historical & real-time pykrx OHLCV
│   │   ├── fundamental_collector.py# Financial sheets parser
│   │   ├── news_collector.py       # DART and Naver News XML parser
│   │   ├── data_collector.py       # Mock stock price & disclosures simulator
│   │   └── scheduler.py            # Cron schedules management via APScheduler
│   │
│   ├── execution/                  # ② Execution & Portfolio Logic
│   │   ├── position_sizer.py       # Order volume allocator based on risk & signal
│   │   ├── risk_gate.py            # Leverage, daily caps, and drawdown validation
│   │   ├── portfolio_manager.py    # Target alignment & holdings tracker
│   │   └── trader.py               # Main trading pipeline daemon
│   │
│   ├── backtesting/                # ② Historical Simulation
│   │   ├── bt_adapter.py           # Backtrader adapter for SQLite data feeds
│   │   └── metrics.py              # Sharpe, Sortino, MDD calculator
│   │
│   ├── monitoring/                 # ② Event Loggers & Alerts
│   │   ├── logger.py               # Structured structlog JSON setup
│   │   ├── events.py               # Event schemas (trade, error, signal, alerts)
│   │   └── notifier.py             # Slack and Telegram alerts multiplexer
│   │
│   └── infra/                      # ③ Concrete Infrastructure Implementations
│       ├── storage/                # SQLite & PostgreSQL database repositories
│       ├── brokers/                # Paper mock, backtesting mock, and KIS APIs
│       ├── llm/                    # Unified LLM provider (chatgpt, claude, gemini, vllm)
│       └── notifiers/              # Slack and Telegram integration modules
│
├── apps/                           # ④ Entrypoints (Daemons & CLI scripts)
│   ├── data_worker.py              # Background price & news data pipeline
│   ├── trader_worker.py            # Live or paper trading agent daemon
│   ├── backtest_cli.py             # Command line backtest execution tool
│   └── api_server.py               # FastAPI service for metrics & control
│
├── configs/                        # Environment-specific configuration files
│   ├── dev.yaml
│   ├── paper.yaml                  # Mock trading
│   └── prod.yaml                   # Production live accounts
│
├── scripts/                        # Database migration & utility scripts
└── tests/                          # Automated tests suite
```

## Setup Instructions

1. **Clone & Setup Environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your OpenAI API keys, KIS credentials, etc.
   ```

2. **Install Dependencies using uv**:
   ```bash
   # Sync dependencies using uv
   uv sync
   ```

3. **Start Development Database**:
   ```bash
   docker-compose up -d
   ```

## Running the Application

* **Start Data Collection Daemon**:
  ```bash
  uv run python apps/data_worker.py
  ```

* **Start Live Trading Daemon**:
  ```bash
  uv run python apps/trader_worker.py --config configs/paper.yaml
  ```

* **Run a Backtest Simulation**:
  ```bash
  uv run python apps/backtest_cli.py --ticker 005930 --start 2025-01-01 --end 2026-01-01
  ```
