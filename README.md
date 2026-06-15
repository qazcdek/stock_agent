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

## 개발 및 빌드/배포 가이드 (Setup, Development & Production Build/Run)

이 프로젝트는 백엔드(FastAPI)와 프런트엔드(Vue 3 + Vite)로 구성되어 있습니다. 각각 **uv**와 **yarn**을 사용하여 관리됩니다.

---

### 1. 개발 환경 (Development / Dev)

개발 중에는 백엔드 API 서버와 프런트엔드 HMR(Hot Module Replacement) 서버를 개별적으로 실행하여 개발을 진행합니다.

#### 백엔드 (FastAPI)
1. **환경 설정 파일 작성**:
   ```bash
   cd backend
   cp .env.example .env
   # .env 파일에 필요한 API 키(FMP_API_KEY, DART_API_KEY, LLM 키 등)를 입력합니다.
   ```
2. **의존성 설치**:
   ```bash
   uv sync
   ```
3. **로컬 개발 서버 실행 (Auto-reload 활성화)**:
   ```bash
   uv run uvicorn apps.main:app --port 8000 --reload
   ```

#### 프런트엔드 (Vue 3 / Vite)
1. **의존성 설치**:
   ```bash
   cd frontend
   yarn install
   ```
2. **로컬 개발 서버 실행 (Vite Dev Server)**:
   ```bash
   yarn dev
   ```
   * 브라우저에서 `http://localhost:5173`으로 접속하여 화면 및 실시간 WebSocket 연동을 개발합니다.

---

### 2. 운영 환경 빌드 및 배포 (Production)

운영 환경에서는 프런트엔드 코드를 빌드하여 정적 파일로 컴파일하고, 백엔드 FastAPI 서버를 통해 통합 배포/서빙할 수 있도록 구성되어 있습니다.

#### 프런트엔드 빌드 (Static Asset 컴파일)
1. **프런트엔드 빌드 실행**:
   ```bash
   cd frontend
   yarn build
   ```
   * 빌드가 완료되면 `frontend/dist` 디렉토리에 최적화된 정적 HTML/CSS/JS 리소스가 생성됩니다.

#### 백엔드 통합 실행 (Production Serve)
백엔드 서버는 `frontend/dist`에 빌드된 리소스가 존재할 경우, 이를 자동으로 감지하여 정적 파일로 마운트 및 `/` 경로에서 서빙합니다.

1. **운영용 백엔드 실행**:
   ```bash
   cd backend
   # --reload 옵션을 제외하고 실행하여 성능 최적화 및 안정성을 확보합니다.
   uv run uvicorn apps.main:app --host 0.0.0.0 --port 8000
   ```
   * 서버가 시작되면 `http://localhost:8000`에서 프런트엔드 화면과 백엔드 API가 통합 서빙됩니다.

---

### 3. 기타 유틸리티 실행

* **데이터 수집 워커 실행**:
  ```bash
  cd backend
  uv run python apps/data_worker.py
  ```

* **자동 매매 워커 실행**:
  ```bash
  cd backend
  uv run python apps/trader_worker.py --config configs/paper.yaml
  ```

* **백테스트 시뮬레이션 실행**:
  ```bash
  cd backend
  uv run python apps/backtest_cli.py --ticker 005930 --start 2025-01-01 --end 2026-01-01
  ```

