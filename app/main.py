from __future__ import annotations

import re
import json
import sys
import threading
import uuid
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field


ROOT_DIR = Path(__file__).resolve().parents[1]
FINANCIAL_SKILLS_DIR = ROOT_DIR / "Financial Analyst Skills"
KELLY_POSITION_DIR = ROOT_DIR / "Kelly Position Sizing"
EVENT_FOCUS_DIR = ROOT_DIR / "Event Focus"
STATIC_DIR = ROOT_DIR / "app" / "static"
REPORT_DIR = ROOT_DIR / "outputs" / "analysis_reports"

if str(FINANCIAL_SKILLS_DIR) not in sys.path:
    sys.path.insert(0, str(FINANCIAL_SKILLS_DIR))
if str(KELLY_POSITION_DIR) not in sys.path:
    sys.path.insert(0, str(KELLY_POSITION_DIR))
if str(EVENT_FOCUS_DIR) not in sys.path:
    sys.path.insert(0, str(EVENT_FOCUS_DIR))

from api_workflow import run_stock_analysis, save_analysis_bundle  # noqa: E402
from calculator import KellyInput, calculate_position  # noqa: E402
from service import EventFocusService  # noqa: E402


STEP_RE = re.compile(r"\[(\d+)\s*/\s*(\d+)\]")

WORKFLOW_STEPS: list[dict[str, Any]] = [
    {
        "step": 1,
        "title": "任务定义",
        "description": "识别股票、研究范围、分析日期和最终报告目标。",
    },
    {
        "step": 2,
        "title": "分析师数据需求",
        "description": "各分析师声明需要的财务、估值、预期、技术和风险证据。",
    },
    {
        "step": 3,
        "title": "需求汇总",
        "description": "Source Intelligence 汇总证据缺口，形成统一信息采集计划。",
    },
    {
        "step": 4,
        "title": "外部数据采集",
        "description": "调用搜索、行情、财务、用户材料等数据源，构建研究资料包。",
    },
    {
        "step": 5,
        "title": "来源情报标注",
        "description": "评估证据质量、来源覆盖和信息可靠性。",
    },
    {
        "step": 6,
        "title": "基本面与质量并行分析",
        "description": "并行分析业务基本面、报表质量、行业周期和成长赛道。",
    },
    {
        "step": 7,
        "title": "盈利预测修正",
        "description": "检查盈利预期、修正趋势和市场共识变化。",
    },
    {
        "step": 8,
        "title": "估值并行分析",
        "description": "运行 DCF 内在价值和相对估值可比公司分析。",
    },
    {
        "step": 9,
        "title": "预期差与催化剂",
        "description": "识别市场预期缺口、事件催化和定价状态。",
    },
    {
        "step": 10,
        "title": "市场确认",
        "description": "检查技术量价、市场情绪和公众叙事是否支持结论。",
    },
    {
        "step": 11,
        "title": "风险反证",
        "description": "从空头视角验证核心假设，寻找可能推翻结论的证据。",
    },
    {
        "step": 12,
        "title": "最终综合",
        "description": "整合所有分析师输出，形成估值判断和投资建议。",
    },
]


class AnalysisRequest(BaseModel):
    query: str = Field(..., min_length=4, max_length=2000)
    profile: Literal["cheap", "balanced"] = "cheap"
    collection_mode: Literal["fast", "standard", "deep"] = "standard"


class AnalysisStartResponse(BaseModel):
    task_id: str
    status: str


class AnalysisResponse(BaseModel):
    status: str
    task_brief: dict[str, Any] | None = None
    lean_report: dict[str, Any] | None = None
    text_report: str
    long_report: str
    cost_summary: dict[str, Any] | None = None
    saved_files: dict[str, str] = Field(default_factory=dict)


class ProgressEvent(BaseModel):
    message: str
    step: int | None = None
    created_at: str


class WorkflowStep(BaseModel):
    step: int
    title: str
    description: str
    status: Literal["pending", "running", "completed", "failed"] = "pending"
    started_at: str | None = None
    completed_at: str | None = None
    notes: list[str] = Field(default_factory=list)


class AnalysisTaskResponse(BaseModel):
    task_id: str
    status: Literal["queued", "running", "completed", "failed"]
    current_step: int
    total_steps: int
    current_message: str
    steps: list[WorkflowStep]
    progress: list[ProgressEvent]
    result: AnalysisResponse | None = None
    error: str | None = None


class AnalysisTaskSummary(BaseModel):
    task_id: str
    status: Literal["queued", "running", "completed", "failed"]
    current_step: int
    total_steps: int
    current_message: str
    error: str | None = None


class KellyPositionRequest(BaseModel):
    available_cash: float = Field(..., gt=0)
    win_probability: float = Field(..., gt=0)
    current_price: float = Field(..., gt=0)
    take_profit_price: float = Field(..., gt=0)
    stop_loss_price: float = Field(..., gt=0)
    kelly_multiplier: float = Field(0.5, ge=0, le=1)


class KellyPositionResponse(BaseModel):
    direction: str
    win_probability: float
    loss_probability: float
    reward_per_unit: float
    risk_per_unit: float
    reward_risk_ratio: float
    full_kelly_fraction: float
    applied_kelly_fraction: float
    risk_capital: float
    raw_position_amount: float
    recommended_position_amount: float
    capped_by_cash: bool
    units: float
    max_loss_amount: float
    expected_profit_amount: float
    stop_loss_pct: float
    take_profit_pct: float
    account_exposure_pct: float
    edge: float
    verdict: str
    notes: list[str]


class EventCard(BaseModel):
    title: str
    market: str
    priority: str
    category: str
    why_it_matters: str
    watch_points: list[str] = Field(default_factory=list)
    source: str = ""
    published_at: str = ""
    url: str = ""


class EventFocusResponse(BaseModel):
    market: str
    market_label: str
    status: str
    generated_at: str
    next_refresh_hint: str
    source_count: int
    cards: list[EventCard]
    summary: str
    error: str = ""


TASKS: dict[str, dict[str, Any]] = {}
TASK_LOCK = threading.Lock()
EVENT_FOCUS = EventFocusService()


app = FastAPI(
    title="Quantitative Decision System",
    description="AI-assisted equity research and valuation workflow.",
    version="0.2.0",
)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/health")
def health() -> dict[str, Any]:
    return {
        "success": True,
        "financial_workflow_loaded": FINANCIAL_SKILLS_DIR.exists(),
        "workflow_path": str(FINANCIAL_SKILLS_DIR),
        "kelly_position_loaded": KELLY_POSITION_DIR.exists(),
        "kelly_position_path": str(KELLY_POSITION_DIR),
        "event_focus_loaded": EVENT_FOCUS_DIR.exists(),
        "event_focus_path": str(EVENT_FOCUS_DIR),
    }


def _now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _new_steps() -> list[dict[str, Any]]:
    steps = deepcopy(WORKFLOW_STEPS)
    for step in steps:
        step["status"] = "pending"
        step["started_at"] = None
        step["completed_at"] = None
        step["notes"] = []
    return steps


def _workflow_step_from_message(message: str) -> int | None:
    match = STEP_RE.search(message)
    if not match:
        return None

    raw_step = int(match.group(1))
    raw_total = int(match.group(2))
    if raw_total == 12 and 1 <= raw_step <= 12:
        return raw_step
    if raw_step == 0:
        return 1
    return None


def _mark_step_running(task: dict[str, Any], step_number: int) -> None:
    now = _now()
    for step in task["steps"]:
        number = step["step"]
        if number < step_number and step["status"] in {"pending", "running"}:
            step["status"] = "completed"
            step["completed_at"] = step["completed_at"] or now
        elif number == step_number:
            if step["status"] == "pending":
                step["started_at"] = now
            step["status"] = "running"
        elif number > step_number and step["status"] != "failed":
            step["status"] = "pending"

    task["current_step"] = max(task["current_step"], step_number)


def _append_progress(task_id: str, message: str) -> None:
    step_number = _workflow_step_from_message(message)
    event = {"message": message, "step": step_number, "created_at": _now()}

    with TASK_LOCK:
        task = TASKS[task_id]
        if step_number is not None:
            _mark_step_running(task, step_number)
            target_step = task["steps"][step_number - 1]
        else:
            target_step = task["steps"][max(task["current_step"], 1) - 1]

        if len(target_step["notes"]) < 8:
            target_step["notes"].append(message)

        task["progress"].append(event)
        task["current_message"] = message


def _analysis_response_from_result(result: dict[str, Any], saved_files: dict[str, str]) -> AnalysisResponse:
    return AnalysisResponse(
        status=str(result.get("status") or "unknown"),
        task_brief=result.get("task_brief"),
        lean_report=result.get("lean_report"),
        text_report=str(result.get("text_report") or ""),
        long_report=str(result.get("long_report") or ""),
        cost_summary=result.get("cost_summary"),
        saved_files=saved_files,
    )


def _run_analysis_task(task_id: str, payload: AnalysisRequest) -> None:
    try:
        with TASK_LOCK:
            task = TASKS[task_id]
            task["status"] = "running"
            task["current_message"] = "任务已启动，正在进入工作流。"
            _mark_step_running(task, 1)

        result = run_stock_analysis(
            payload.query,
            profile=payload.profile,
            collection_mode=payload.collection_mode,
            progress_callback=lambda message: _append_progress(task_id, message),
        )

        ticker = str((result.get("task_brief") or {}).get("ticker") or "analysis").strip()
        safe_name = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in ticker) or "analysis"
        output_path = REPORT_DIR / f"{safe_name}_{task_id[:8]}.json"
        saved_files = save_analysis_bundle(result, output_path)
        response = _analysis_response_from_result(result, saved_files)

        with TASK_LOCK:
            task = TASKS[task_id]
            for step in task["steps"]:
                if step["status"] != "completed":
                    step["status"] = "completed"
                    step["completed_at"] = step["completed_at"] or _now()
            task["status"] = "completed"
            task["current_step"] = 12
            task["current_message"] = "分析完成"
            task["result"] = response.model_dump()
    except Exception as exc:  # noqa: BLE001
        with TASK_LOCK:
            task = TASKS[task_id]
            task["status"] = "failed"
            task["error"] = str(exc)
            task["current_message"] = "分析失败"
            current = max(task["current_step"], 1)
            task["steps"][current - 1]["status"] = "failed"
            task["steps"][current - 1]["notes"].append(str(exc))


@app.post("/api/analyze", response_model=AnalysisStartResponse)
def analyze(payload: AnalysisRequest) -> AnalysisStartResponse:
    task_id = uuid.uuid4().hex
    with TASK_LOCK:
        TASKS[task_id] = {
            "task_id": task_id,
            "status": "queued",
            "current_step": 0,
            "total_steps": 12,
            "current_message": "任务已排队，等待工作流启动。",
            "steps": _new_steps(),
            "progress": [],
            "result": None,
            "error": None,
        }

    thread = threading.Thread(target=_run_analysis_task, args=(task_id, payload), daemon=True)
    thread.start()
    return AnalysisStartResponse(task_id=task_id, status="queued")


@app.get("/api/analysis/{task_id}", response_model=AnalysisTaskResponse)
def get_analysis_task(task_id: str) -> AnalysisTaskResponse:
    with TASK_LOCK:
        task = TASKS.get(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Analysis task not found")
        return AnalysisTaskResponse(**deepcopy(task))


@app.get("/api/analysis", response_model=list[AnalysisTaskSummary])
def list_analysis_tasks() -> list[AnalysisTaskSummary]:
    with TASK_LOCK:
        return [
            AnalysisTaskSummary(
                task_id=task["task_id"],
                status=task["status"],
                current_step=task["current_step"],
                total_steps=task["total_steps"],
                current_message=task["current_message"],
                error=task.get("error"),
            )
            for task in TASKS.values()
        ]


@app.post("/api/position/kelly", response_model=KellyPositionResponse)
def calculate_kelly_position(payload: KellyPositionRequest) -> KellyPositionResponse:
    try:
        result = calculate_position(
            KellyInput(
                available_cash=payload.available_cash,
                win_probability=payload.win_probability,
                current_price=payload.current_price,
                take_profit_price=payload.take_profit_price,
                stop_loss_price=payload.stop_loss_price,
                kelly_multiplier=payload.kelly_multiplier,
            )
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return KellyPositionResponse(**result.to_dict())


@app.get("/api/events/focus", response_model=EventFocusResponse)
def get_event_focus(market: str = "a_share", force: bool = False) -> EventFocusResponse:
    try:
        payload = EVENT_FOCUS.get_focus(market=market, force=force)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return EventFocusResponse(**payload)


@app.get("/api/dev/latest-report", response_model=AnalysisResponse)
def get_latest_report_preview() -> AnalysisResponse:
    if not REPORT_DIR.exists():
        raise HTTPException(status_code=404, detail="No report directory found")

    report_files = sorted(
        REPORT_DIR.glob("*.json"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    if not report_files:
        raise HTTPException(status_code=404, detail="No saved reports found")

    latest_path: Path | None = None
    latest_data: dict[str, Any] | None = None
    fallback_error: Exception | None = None

    for path in report_files:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001
            fallback_error = exc
            continue

        if latest_data is None:
            latest_path = path
            latest_data = data

        if data.get("long_report") or data.get("text_report"):
            latest_path = path
            latest_data = data
            break

    if latest_path is None or latest_data is None:
        detail = f"Saved reports could not be read: {fallback_error}" if fallback_error else "No readable reports found"
        raise HTTPException(status_code=500, detail=detail)

    saved_files = dict(latest_data.get("saved_files") or {})
    saved_files.setdefault("json", str(latest_path))
    return _analysis_response_from_result(latest_data, saved_files)
