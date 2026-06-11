# Quantitative Decision-Making System

A local web application for quantitative decision support.

Current modules:

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

## Configuration

Create local `.env` files from the provided examples and fill in real keys locally.

Do not commit real `.env` files.

Important variables:

- `DEEPSEEK_API_KEY`
- `EVENT_FOCUS_MODEL`
- `EVENT_FOCUS_A_SHARE_URLS`
- `EVENT_FOCUS_HK_SHARE_URLS`
- `EVENT_FOCUS_US_SHARE_URLS`

## Notes

The project currently contains `Financial Analyst Skills` as a directory that also has its own `.git` metadata. If the whole project should be tracked as one GitHub repository, remove or archive that nested `.git` directory first; otherwise Git will treat it as a nested repository instead of normal files.
