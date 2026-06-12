# Quantitative Decision-Making System

A local web application for quantitative decision support.

Current modules:

- `Today Recommendations`: explainable A-share multi-factor ranking with direct Tushare and snapshot modes.
- `Stock Detail`: factor scores, recommendation reasons, risks, invalidation conditions, and price trend.
- `Watchlist and Reports`: Demo watchlist plus pre-market and post-market summaries.
- `AI Copilot`: stock-context Q&A with DeepSeek and a rules-based fallback.
- `Notifications`: enterprise WeChat robot integration with simulated fallback.
- `Direct Tushare Data`: configure a backend Token, test it, and refresh recommendations without PostgreSQL.
- `Financial Analyst Skills`: AI equity research and valuation workflow.
- `Kelly Position Sizing`: Kelly-based single-trade position sizing.
- `Event Focus`: market event focus cards generated from news candidates and DeepSeek.
- `app`: FastAPI backend and static frontend.

## Local Setup

```powershell
python -m venv .venv
.\.venv\Scripts\activate
python -m pip install -r requirements.txt
python run.py
```

Open:

```text
http://127.0.0.1:8010
```

If that port is already occupied, set `APP_PORT=8011` in `.env`.

The homepage works without API keys by using an explicitly labeled Demo
snapshot. Configure `TUSHARE_TOKEN` in the backend `.env`, restart the service,
open `AI 问答`, then click `刷新推荐数据`. The Demo fetches about 35 trading days for a fixed
30-stock sample universe and creates up to 10 recommendations in memory.
The frontend never accepts or returns the Token.

## Demo With Docker Compose

Keep `Quantitative-decision-making-system` and `quant-db` in the same parent
directory, then run:

```powershell
Copy-Item .env.example .env
docker compose -f compose.demo.yml up --build
```

Services:

- Web Demo: `http://127.0.0.1:8010`
- Adminer: `http://127.0.0.1:8080`
- PostgreSQL: `127.0.0.1:15432`

The Compose file initializes the base quant database, QuantaAlpha tables, and
the Demo application schema. Actual live recommendations require imported
Tushare/quant-db market and factor data; otherwise the web app stays in snapshot
mode.

## Configuration

Create local `.env` files from the provided examples and fill in real keys locally.

Do not commit real `.env` files.

Important variables:

- `DEEPSEEK_API_KEY`
- `DEMO_CHAT_MODEL`
- `TUSHARE_TOKEN`
- `DATA_SOURCE_MODE` (`tushare_direct` by default)
- `EVENT_FOCUS_MODEL`
- `EVENT_FOCUS_A_SHARE_URLS`
- `EVENT_FOCUS_HK_SHARE_URLS`
- `EVENT_FOCUS_US_SHARE_URLS`
- `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`
- `WECOM_WEBHOOK_URL`

## Test

```powershell
python -m unittest discover -s tests -v
node --check app/static/app.js
```

## Notes

The project currently contains `Financial Analyst Skills` as a directory that also has its own `.git` metadata. If the whole project should be tracked as one GitHub repository, remove or archive that nested `.git` directory first; otherwise Git will treat it as a nested repository instead of normal files.
