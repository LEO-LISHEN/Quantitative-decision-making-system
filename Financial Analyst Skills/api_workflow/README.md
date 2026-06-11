# API Workflow

`api_workflow` is the reusable backend package for the multi-analyst stock research workflow.

It accepts one stock-analysis request and returns:

- full structured JSON
- a lean summary object
- a short markdown report
- a long markdown report

This package is the part you should integrate into a larger backend or web app.

## What to Keep

When moving this project into another root folder, keep:

- `api_workflow/`
- `workflow_specs/analysts/`
- `workflow_specs/global/`
- `.env.example`
- `requirements.txt`

You do not need to keep:

- old files inside `outputs/`
- `__pycache__/`
- local debug artifacts

## Stable Python Entry Points

### 1. Run and get a result dict

```python
from api_workflow import run_stock_analysis

result = run_stock_analysis(
    "请全面分析贵州茅台，重点关注长期估值、基本面质量、市场预期差、催化剂和主要风险",
    profile="cheap",
    collection_mode="standard",
)
```

### 2. Save JSON + markdown artifacts

```python
from api_workflow import save_analysis_bundle

saved_files = save_analysis_bundle(result, "outputs/moutai.json")
```

This writes:

- `outputs/moutai.json`
- `outputs/moutai.md`
- `outputs/moutai_long_report.md`

### 3. Run and save in one call

```python
from api_workflow import run_and_save_stock_analysis

result = run_and_save_stock_analysis(
    "请全面分析贵州茅台，重点关注长期估值、基本面质量、市场预期差、催化剂和主要风险",
    output_path="outputs/moutai.json",
    profile="cheap",
    collection_mode="standard",
)
```

## Function Signatures

### `run_stock_analysis(...)`

Inputs:

- `user_input: str`
- `profile: str = "cheap"`
- `collection_mode: str = "standard"` with `fast | standard | deep`
- `max_workers: int = 4`
- `timeout_seconds: int = 180`
- `progress_callback: Callable[[str], None] | None = None`

Return:

- `dict[str, Any]`

Top-level output fields:

- `status`
- `profile`
- `task_brief`
- `analyst_data_requests`
- `data_requirement_summary`
- `external_data`
- `analyst_outputs`
- `final_report`
- `lean_report`
- `text_report`
- `long_report`
- `cost_summary`

### `save_analysis_bundle(result, output_path)`

Inputs:

- `result: dict`
- `output_path: str | Path`

Return:

- saved file path mapping:
  - `json`
  - `text_report`
  - `long_report`

## CLI Usage

```powershell
python -m api_workflow.run_full_analysis "请全面分析贵州茅台，重点关注长期估值、基本面质量、市场预期差、催化剂和主要风险" --profile cheap --collection-mode standard --output outputs/moutai.json
```

## Collection Modes

### `fast`

Use when you want a quicker pass with fewer searches and fewer document parses.

### `standard`

Default mode. Good balance between speed and evidence coverage.

### `deep`

Use when you want heavier web search, more dynamic research documents, and broader evidence collection.

## Environment Variables

Required for model calls:

```text
DEEPSEEK_API_KEY=
```

Common search/data options:

```text
TAVILY_API_KEY=
BRAVE_SEARCH_API_KEY=
SERPAPI_API_KEY=
TUSHARE_TOKEN=
FUTU_ENABLED=0
FUTU_OPEND_HOST=127.0.0.1
FUTU_OPEND_PORT=11111
```

Optional model overrides:

```text
DEEPSEEK_BASE_URL=
DEEPSEEK_MODEL=
DEEPSEEK_MODEL_DEFAULT=
DEEPSEEK_MODEL_CRITICAL=
DEEPSEEK_MODEL_FINAL=
DEEPSEEK_SSL_NO_VERIFY=0
```

Collection controls:

```text
WEB_SEARCH_MAX_QUERIES=8
WEB_SEARCH_MAX_RESULTS=5
DYNAMIC_RESEARCH_MAX_DOCS=4
DYNAMIC_RESEARCH_RESULTS_PER_QUERY=3
PEER_QUOTE_MAX=4
SENTIMENT_SEARCH_MAX_QUERIES=2
SENTIMENT_SEARCH_RESULTS_PER_QUERY=3
```

User material inputs:

```text
USER_MATERIAL_FILES=
USER_MATERIAL_DIRS=
USER_MATERIAL_MAX_FILES=20
USER_TABLE_MAX_ROWS=200
USER_TABLE_MAX_COLS=40
USER_TEXT_EXCERPT_CHARS=6000
DOCUMENT_MAX_TABLES=6
PDF_TABLE_PARSE_MAX_PAGES=5
```

## Path Behavior

The package already resolves internal analyst resources relative to the module root, not the current shell directory.

That means:

- internal knowledge files are stable after you move the project
- output paths should still be passed in explicitly from the caller

Recommended integration pattern:

- use relative module paths for packaged assets
- use caller-provided absolute or app-relative paths for output files

## Web App Integration Pattern

Recommended layering:

1. web route / controller
2. app service
3. `api_workflow.run_stock_analysis(...)`

Example service wrapper:

```python
from api_workflow import run_and_save_stock_analysis


def run_stock_report_service(user_query: str, output_path: str) -> dict:
    result = run_and_save_stock_analysis(
        user_query,
        output_path=output_path,
        profile="cheap",
        collection_mode="standard",
    )
    return {
        "status": result["status"],
        "lean_report": result["lean_report"],
        "text_report": result["text_report"],
        "long_report": result["long_report"],
        "saved_files": result.get("saved_files", {}),
    }
```

## Failure Behavior

- missing model key: raises `RuntimeError`
- insufficient model balance: raises `RuntimeError`
- individual data sources may fail without stopping the workflow
- source failures are recorded in `external_data.research_data_pack.fetch_errors` or `external_data.errors`
- final report JSON formatting issues are now repaired or salvaged before report generation

## Smoke Test

```powershell
python -m unittest api_workflow.test_model_client api_workflow.test_data_layer api_workflow.test_runner_routing
python -m api_workflow.run_full_analysis "请全面分析贵州茅台，重点关注长期估值、基本面质量、市场预期差、催化剂和主要风险" --profile cheap --collection-mode fast --output outputs/moutai_smoke.json
```
