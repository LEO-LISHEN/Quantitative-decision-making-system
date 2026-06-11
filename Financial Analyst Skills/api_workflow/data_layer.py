from __future__ import annotations

import json
import os
import re
import ssl
import urllib.error
import urllib.parse
import urllib.request
import time
import csv
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime
from datetime import timedelta
from pathlib import Path
from threading import Lock
from typing import Any


_SEARCH_CACHE: dict[str, list[dict[str, Any]]] = {}
_SEARCH_CACHE_LOCK = Lock()

COLLECTION_MODE_PRESETS: dict[str, dict[str, int]] = {
    "fast": {
        "web_search_max_queries": 4,
        "web_search_max_results": 3,
        "dynamic_research_max_docs": 2,
        "dynamic_research_results_per_query": 2,
        "dynamic_research_max_queries": 4,
        "peer_quote_max": 2,
        "sentiment_search_max_queries": 1,
        "sentiment_search_results_per_query": 2,
    },
    "standard": {
        "web_search_max_queries": 8,
        "web_search_max_results": 5,
        "dynamic_research_max_docs": 4,
        "dynamic_research_results_per_query": 3,
        "dynamic_research_max_queries": 8,
        "peer_quote_max": 4,
        "sentiment_search_max_queries": 2,
        "sentiment_search_results_per_query": 3,
    },
    "deep": {
        "web_search_max_queries": 12,
        "web_search_max_results": 6,
        "dynamic_research_max_docs": 6,
        "dynamic_research_results_per_query": 4,
        "dynamic_research_max_queries": 10,
        "peer_quote_max": 6,
        "sentiment_search_max_queries": 3,
        "sentiment_search_results_per_query": 4,
    },
}


def load_dotenv_if_present() -> None:
    env_path = Path(__file__).resolve().parents[1] / ".env"
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def today_iso() -> str:
    return date.today().isoformat()


def normalize_task_dates(task_brief: Any) -> dict[str, Any]:
    if not isinstance(task_brief, dict):
        task_brief = {"raw_task_brief": task_brief}
    current_date = today_iso()
    normalized = dict(task_brief)
    normalized["analysis_date"] = current_date
    normalized["information_cutoff"] = current_date
    normalized["date_source"] = "system_date_forced_by_workflow"
    return normalized


def _collection_limits(collection_mode: str) -> dict[str, int]:
    normalized = str(collection_mode or "standard").strip().lower()
    return COLLECTION_MODE_PRESETS.get(normalized, COLLECTION_MODE_PRESETS["standard"])


def _progress(progress_callback: Any, message: str) -> None:
    if callable(progress_callback):
        progress_callback(message)


def collect_external_data(
    user_input: str,
    task_brief: dict[str, Any],
    data_requirement_summary: dict[str, Any] | None = None,
    analyst_data_requests: dict[str, Any] | None = None,
    collection_mode: str = "standard",
    progress_callback: Any = None,
) -> dict[str, Any]:
    load_dotenv_if_present()
    limits = _collection_limits(collection_mode)
    ticker = str(task_brief.get("ticker") or _extract_ticker(user_input) or "").strip()
    company_name = str(task_brief.get("company_name") or "").strip()
    queries = _build_search_queries(
        company_name=company_name,
        ticker=ticker,
        user_input=user_input,
        data_requirement_summary=data_requirement_summary,
    )[: limits["web_search_max_queries"]]

    result: dict[str, Any] = {
        "collection_time": datetime.now().astimezone().isoformat(),
        "network_enabled": True,
        "ticker": ticker,
        "company_name": company_name,
        "data_requirement_summary": data_requirement_summary or {},
        "queries_executed": queries,
        "quote_snapshot": None,
        "research_data_pack": None,
        "web_search_results": [],
        "errors": [],
        "notes": [
            "联网数据层只作为证据输入，不直接生成投资建议。",
            "所有第三方网页和行情数据都必须由 02_Source_Intelligence_Analyst 再次标注可信度。",
        ],
    }
    _progress(progress_callback, f"    [data] mode={collection_mode}; search_queries={len(queries)}")

    if ticker:
        try:
            _progress(progress_callback, f"    [data] quote start {ticker}")
            result["quote_snapshot"] = fetch_market_quote(ticker)
            _progress(progress_callback, f"    [data] quote done {ticker}")
        except Exception as exc:  # noqa: BLE001
            result["errors"].append({"source": "market_quote", "error": str(exc)})
            _progress(progress_callback, f"    [data] quote error {ticker}: {exc}")

    try:
        _progress(progress_callback, "    [data] research_data_pack start")
        result["research_data_pack"] = collect_research_data_pack(
            user_input=user_input,
            task_brief=task_brief,
            data_requirement_summary=data_requirement_summary,
            analyst_data_requests=analyst_data_requests,
            quote_snapshot=result.get("quote_snapshot"),
            collection_mode=collection_mode,
            progress_callback=progress_callback,
        )
        _progress(progress_callback, "    [data] research_data_pack done")
    except Exception as exc:  # noqa: BLE001
        result["errors"].append({"source": "research_data_pack", "error": str(exc)})
        _progress(progress_callback, f"    [data] research_data_pack error: {exc}")

    max_search_workers = int(os.getenv("WEB_SEARCH_MAX_WORKERS", "4"))
    with ThreadPoolExecutor(max_workers=min(max_search_workers, max(1, len(queries)))) as executor:
        futures = {
            executor.submit(search_web, query, max_results=limits["web_search_max_results"]): query
            for query in queries
        }
        for future in as_completed(futures):
            query = futures[future]
            try:
                results = future.result()
                result["web_search_results"].append(
                    {
                        "query": query,
                        "results": results,
                    }
                )
                _progress(progress_callback, f"    [search] done {query}; results={len(results)}")
            except Exception as exc:  # noqa: BLE001
                result["errors"].append({"source": "web_search", "query": query, "error": str(exc)})
                _progress(progress_callback, f"    [search] error {query}: {exc}")
    result["web_search_results"].sort(
        key=lambda item: queries.index(item.get("query", "")) if item.get("query") in queries else len(queries)
    )

    if not result["web_search_results"]:
        result["notes"].append(
            "未配置搜索 API Key。可配置 TAVILY_API_KEY、BRAVE_SEARCH_API_KEY 或 SERPAPI_API_KEY 开启网页搜索。"
        )
    return result


def collect_research_data_pack(
    *,
    user_input: str,
    task_brief: dict[str, Any],
    data_requirement_summary: dict[str, Any] | None = None,
    analyst_data_requests: dict[str, Any] | None = None,
    quote_snapshot: dict[str, Any] | None = None,
    collection_mode: str = "standard",
    progress_callback: Any = None,
) -> dict[str, Any]:
    limits = _collection_limits(collection_mode)
    ticker = str(task_brief.get("ticker") or _extract_ticker(user_input) or "").strip()
    company_name = str(task_brief.get("company_name") or "").strip()
    market = str(task_brief.get("market") or "").strip()
    exchange = str(task_brief.get("exchange") or "").strip()
    data_requests = normalize_data_requests(
        data_requirement_summary=data_requirement_summary,
        analyst_data_requests=analyst_data_requests,
    )
    pack: dict[str, Any] = {
        "schema_version": "0.1",
        "collection_time": datetime.now().astimezone().isoformat(),
        "company_profile": {
            "company_name": company_name,
            "ticker": ticker,
            "market": market,
            "exchange": exchange,
            "currency": "CNY" if ticker.upper().endswith((".SH", ".SZ", ".BJ")) else None,
            "industry": None,
            "business_segments": [],
        },
        "market_data": {
            "quote": quote_snapshot,
            "daily_kline": None,
            "benchmark_data": {},
            "peer_quotes": [],
            "peer_klines": [],
            "daily_basic": None,
            "moneyflow": None,
        },
        "financial_statements": {
            "key_indicators": None,
            "structured_statements": {},
            "tushare": None,
        },
        "capital_actions": {
            "dividend": None,
            "share_float": None,
        },
        "shareholder_data": {
            "holder_number": None,
        },
        "filings_and_announcements": [],
        "peer_table": [],
        "industry_data": {
            "dynamic_search_queries": _extract_collection_queries(data_requirement_summary),
            "items": [],
        },
        "company_specific_data": {
            "dynamic_requests": data_requests,
            "items": [],
        },
        "user_materials": {
            "files": [],
            "tables": [],
            "text_documents": [],
            "parse_errors": [],
        },
        "dynamic_research": {
            "queries": [],
            "document_corpus": [],
            "consensus_proxy": None,
            "industry_and_company_specific_evidence": [],
            "parse_errors": [],
        },
        "macro_inputs": {
            "risk_free_rate": None,
            "equity_risk_premium": None,
            "beta": None,
        },
        "sentiment_data": {
            "samples": [],
            "search_queries": _sentiment_queries(company_name, ticker),
        },
        "event_timeline": {
            "events": [],
            "event_windows": [],
        },
        "valuation_data": {
            "snapshot": None,
            "peer_snapshot": [],
        },
        "analyst_data_delivery": {},
        "data_need_coverage": [],
        "evidence_ledger": [],
        "missing_data": [],
        "provider_status": provider_status(),
        "data_quality_score": {},
    }

    if not ticker:
        try:
            user_materials = collect_user_materials(user_input=user_input, task_brief=task_brief)
            pack["user_materials"] = user_materials
            attach_user_materials(pack, user_materials)
        except Exception as exc:  # noqa: BLE001
            pack["user_materials"]["parse_errors"].append({"stage": "collect_user_materials", "error": str(exc)})
        pack["missing_data"].append(_missing("security_master", "ticker", "无法识别股票代码，无法执行结构化采集"))
        pack["data_need_coverage"] = build_data_need_coverage(data_requests, pack)
        pack["analyst_data_delivery"] = build_analyst_data_delivery(analyst_data_requests or {}, pack)
        pack["evidence_ledger"] = build_evidence_ledger(pack)
        pack["data_quality_score"] = score_research_pack(pack)
        return pack

    fetch_errors: list[dict[str, Any]] = []

    tasks: dict[str, Any] = {}
    max_workers = int(os.getenv("DATA_LAYER_MAX_WORKERS", "6"))
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        if not pack["market_data"]["quote"]:
            tasks["quote"] = executor.submit(fetch_market_quote, ticker)
        tasks["daily_kline"] = executor.submit(
            fetch_price_history,
            ticker,
            lookback_days=int(os.getenv("PRIMARY_KLINE_LOOKBACK_DAYS", "420")),
        )
        tasks["benchmark_data"] = executor.submit(
            fetch_benchmark_data,
            ticker=ticker,
            company_name=company_name,
            data_requests=data_requests,
            lookback_days=int(os.getenv("BENCHMARK_KLINE_LOOKBACK_DAYS", "420")),
        )
        tasks["risk_free_rate"] = executor.submit(fetch_risk_free_rate)
        tasks["announcements"] = executor.submit(fetch_announcements, ticker, page_size=30)
        tasks["financial_key_indicators"] = executor.submit(fetch_financial_key_indicators, ticker)
        tasks["user_materials"] = executor.submit(collect_user_materials, user_input=user_input, task_brief=task_brief)
        tasks["tushare_pack"] = executor.submit(fetch_tushare_a_share_pack, ticker)
        tasks["business_analysis"] = executor.submit(fetch_business_analysis, ticker)
        tasks["dynamic_research"] = executor.submit(
            collect_dynamic_research,
            company_name=company_name,
            ticker=ticker,
            data_requests=data_requests,
            data_requirement_summary=data_requirement_summary,
            collection_mode=collection_mode,
            progress_callback=progress_callback,
        )
        for name, future in tasks.items():
            try:
                _progress(progress_callback, f"    [pack] waiting {name}")
                value = future.result()
                _progress(progress_callback, f"    [pack] done {name}")
            except Exception as exc:  # noqa: BLE001
                fetch_errors.append({"source": name, "error": str(exc)})
                _progress(progress_callback, f"    [pack] error {name}: {exc}")
                if name == "quote":
                    pack["missing_data"].append(_missing("market_data", "quote", str(exc)))
                elif name == "daily_kline":
                    pack["missing_data"].append(_missing("market_data", "daily_kline", str(exc)))
                elif name == "benchmark_data":
                    pack["missing_data"].append(_missing("market_data", "benchmark_data", str(exc)))
                elif name == "announcements":
                    pack["missing_data"].append(_missing("filings", "announcements", str(exc)))
                elif name == "financial_key_indicators":
                    pack["missing_data"].append(_missing("financials", "key_indicators", str(exc)))
                elif name == "business_analysis":
                    pack["missing_data"].append(_missing("company_profile", "business_segments", str(exc)))
                elif name == "user_materials":
                    pack["user_materials"]["parse_errors"].append({"stage": "collect_user_materials", "error": str(exc)})
                elif name == "dynamic_research":
                    pack["dynamic_research"]["parse_errors"].append({"stage": "collect_dynamic_research", "error": str(exc)})
                continue
            if name == "quote":
                pack["market_data"]["quote"] = value
            elif name == "daily_kline":
                pack["market_data"]["daily_kline"] = value
            elif name == "benchmark_data":
                pack["market_data"]["benchmark_data"] = value
            elif name == "risk_free_rate":
                pack["macro_inputs"]["risk_free_rate"] = value
            elif name == "announcements":
                pack["filings_and_announcements"] = value
            elif name == "financial_key_indicators":
                pack["financial_statements"]["key_indicators"] = value
            elif name == "user_materials":
                pack["user_materials"] = value
                attach_user_materials(pack, value)
            elif name == "tushare_pack" and value:
                pack["financial_statements"]["tushare"] = value.get("financial_statements")
                pack["financial_statements"]["structured_statements"]["tushare"] = value.get("financial_statements")
                pack["market_data"]["daily_basic"] = value.get("daily_basic")
                pack["market_data"]["moneyflow"] = value.get("moneyflow")
                pack["capital_actions"]["dividend"] = value.get("dividend")
                pack["capital_actions"]["share_float"] = value.get("share_float")
                pack["shareholder_data"]["holder_number"] = value.get("holder_number")
            elif name == "business_analysis":
                pack["company_profile"]["business_scope"] = value.get("business_scope")
                pack["company_profile"]["business_segments"] = value.get("segments", [])
                pack["company_specific_data"]["items"].append(value)
            elif name == "dynamic_research":
                pack["dynamic_research"] = value
                pack["industry_data"]["items"].extend(value.get("industry_and_company_specific_evidence", []))
                if value.get("consensus_proxy"):
                    pack["financial_statements"]["consensus_proxy"] = value.get("consensus_proxy")

    peer_candidates = infer_peer_candidates(company_name=company_name, ticker=ticker, data_requests=data_requests)
    pack["peer_table"] = peer_candidates
    max_peers = limits["peer_quote_max"]
    fetch_peer_klines = os.getenv("FETCH_PEER_KLINES", "0").strip().lower() in {"1", "true", "yes"}
    for peer in peer_candidates[:max_peers]:
        peer_ticker = peer.get("ticker")
        if not peer_ticker:
            continue
        try:
            pack["market_data"]["peer_quotes"].append(
                {
                    "ticker": peer_ticker,
                    "company_name": peer.get("company_name"),
                    "reason": peer.get("reason"),
                    "quote": fetch_market_quote(peer_ticker),
                }
            )
        except Exception as exc:  # noqa: BLE001
            fetch_errors.append({"source": "peer_quote", "ticker": peer_ticker, "error": str(exc)})
        if fetch_peer_klines:
            try:
                pack["market_data"]["peer_klines"].append(
                    {
                        "ticker": peer_ticker,
                        "company_name": peer.get("company_name"),
                        "reason": peer.get("reason"),
                        "daily_kline": fetch_price_history(
                            peer_ticker,
                            lookback_days=int(os.getenv("PEER_KLINE_LOOKBACK_DAYS", "180")),
                        ),
                    }
                )
            except Exception as exc:  # noqa: BLE001
                fetch_errors.append({"source": "peer_kline", "ticker": peer_ticker, "error": str(exc)})

    pack["event_timeline"] = build_event_timeline(pack)
    pack["valuation_data"] = build_valuation_data(pack)
    collect_sentiment_samples(pack, collection_mode=collection_mode, progress_callback=progress_callback)

    beta_input = (pack.get("market_data") or {}).get("benchmark_data", {}).get("market_index")
    if pack["market_data"].get("daily_kline") and beta_input:
        pack["macro_inputs"]["beta"] = calculate_beta(
            pack["market_data"]["daily_kline"],
            beta_input,
            benchmark_name=beta_input.get("name") or beta_input.get("ticker") or "market_index",
        )

    fetch_errors.extend(pack.get("fetch_errors") or [])
    pack["fetch_errors"] = fetch_errors
    pack["data_need_coverage"] = build_data_need_coverage(data_requests, pack)
    pack["analyst_data_delivery"] = build_analyst_data_delivery(analyst_data_requests or {}, pack)
    pack["missing_data"].extend(required_missing_from_pack(pack))
    pack["evidence_ledger"] = build_evidence_ledger(pack)
    pack["data_quality_score"] = score_research_pack(pack)
    return pack


def fetch_market_quote(ticker: str) -> dict[str, Any]:
    errors: list[str] = []
    if not _is_a_share_ticker(ticker):
        try:
            return fetch_yahoo_quote(ticker)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"yahoo: {exc}")
    if _futu_should_use():
        try:
            return fetch_futu_quote(ticker)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"futu: {exc}")
    try:
        return fetch_eastmoney_quote(ticker)
    except Exception as exc:  # noqa: BLE001
        errors.append(f"eastmoney: {exc}")
    try:
        quote = fetch_tencent_quote(ticker)
        quote["fallback_errors"] = errors
        return quote
    except Exception as exc:  # noqa: BLE001
        errors.append(f"tencent: {exc}")
    raise RuntimeError("; ".join(errors))


def collect_user_materials(*, user_input: str, task_brief: dict[str, Any]) -> dict[str, Any]:
    files = discover_user_material_files(user_input=user_input, task_brief=task_brief)
    output: dict[str, Any] = {
        "source": "local_user_materials",
        "collection_time": datetime.now().astimezone().isoformat(),
        "files": [],
        "tables": [],
        "text_documents": [],
        "parse_errors": [],
    }
    max_files = int(os.getenv("USER_MATERIAL_MAX_FILES", "20"))
    for file_path in files[:max_files]:
        try:
            parsed = parse_user_material_file(file_path)
            output["files"].append(parsed["file"])
            output["tables"].extend(parsed.get("tables") or [])
            output["text_documents"].extend(parsed.get("text_documents") or [])
        except Exception as exc:  # noqa: BLE001
            output["parse_errors"].append({"path": str(file_path), "error": str(exc)})
    return output


def discover_user_material_files(*, user_input: str, task_brief: dict[str, Any]) -> list[Path]:
    candidates: list[Path] = []
    env_files = os.getenv("USER_MATERIAL_FILES") or os.getenv("DATA_LAYER_INPUT_FILES") or ""
    for raw_path in re.split(r"[;\n]", env_files):
        if raw_path.strip():
            candidates.append(Path(raw_path.strip().strip('"')).expanduser())

    env_dirs = os.getenv("USER_MATERIAL_DIRS") or os.getenv("DATA_LAYER_INPUT_DIRS") or ""
    for raw_dir in re.split(r"[;\n]", env_dirs):
        if not raw_dir.strip():
            continue
        root = Path(raw_dir.strip().strip('"')).expanduser()
        if root.exists() and root.is_dir():
            candidates.extend(iter_material_files(root))

    material_paths = task_brief.get("available_materials") if isinstance(task_brief, dict) else None
    if isinstance(material_paths, list):
        for item in material_paths:
            if isinstance(item, str) and looks_like_local_path(item):
                candidates.append(Path(item.strip().strip('"')).expanduser())
            elif isinstance(item, dict):
                path = item.get("path") or item.get("file") or item.get("filepath")
                if isinstance(path, str) and looks_like_local_path(path):
                    candidates.append(Path(path.strip().strip('"')).expanduser())

    for match in re.finditer(r"(?P<path>(?:[A-Za-z]:\\|\.{1,2}\\|/)[^\s\"'，,；;]+)", user_input):
        candidates.append(Path(match.group("path").strip().strip('"')).expanduser())

    deduped: list[Path] = []
    seen: set[str] = set()
    for candidate in candidates:
        try:
            resolved = candidate.resolve()
        except Exception:  # noqa: BLE001
            resolved = candidate
        if not resolved.exists() or not resolved.is_file() or not is_supported_material_file(resolved):
            continue
        key = str(resolved).lower()
        if key not in seen:
            deduped.append(resolved)
            seen.add(key)
    return deduped


def iter_material_files(root: Path) -> list[Path]:
    max_depth = int(os.getenv("USER_MATERIAL_MAX_DEPTH", "2"))
    root = root.resolve()
    files: list[Path] = []
    for path in root.rglob("*"):
        try:
            if not path.is_file() or not is_supported_material_file(path):
                continue
            depth = len(path.relative_to(root).parts) - 1
            if depth <= max_depth:
                files.append(path)
        except Exception:  # noqa: BLE001
            continue
    return files


def looks_like_local_path(text: str) -> bool:
    return bool(re.search(r"(?:[A-Za-z]:\\|\.{1,2}\\|/).+\.(?:csv|xlsx|xls|json|pdf|html?|txt|md)$", text, flags=re.IGNORECASE))


def is_supported_material_file(path: Path) -> bool:
    return path.suffix.lower() in {".csv", ".xlsx", ".xls", ".json", ".pdf", ".html", ".htm", ".txt", ".md"}


def parse_user_material_file(path: Path) -> dict[str, Any]:
    suffix = path.suffix.lower()
    stat = path.stat()
    max_bytes = int(os.getenv("USER_MATERIAL_MAX_BYTES", str(10 * 1024 * 1024)))
    if stat.st_size > max_bytes:
        raise RuntimeError(f"file exceeds USER_MATERIAL_MAX_BYTES={max_bytes}")
    file_info = {
        "path": str(path),
        "name": path.name,
        "suffix": suffix,
        "size_bytes": stat.st_size,
        "modified_at": datetime.fromtimestamp(stat.st_mtime).astimezone().isoformat(),
        "parsed_at": datetime.now().astimezone().isoformat(),
    }
    if suffix == ".csv":
        tables = parse_csv_file(path)
        return {"file": {**file_info, "parser": "csv"}, "tables": tables, "text_documents": []}
    if suffix in {".xlsx", ".xls"}:
        tables = parse_excel_file(path)
        return {"file": {**file_info, "parser": "pandas.read_excel"}, "tables": tables, "text_documents": []}
    if suffix == ".json":
        tables, text_documents = parse_json_file(path)
        return {"file": {**file_info, "parser": "json"}, "tables": tables, "text_documents": text_documents}
    if suffix == ".pdf":
        content = path.read_bytes()
        text = extract_pdf_text(content)
        tables = extract_pdf_tables(content)
        return {
            "file": {**file_info, "parser": "pypdf+pdfplumber"},
            "tables": annotate_material_tables(tables, path=path),
            "text_documents": [make_text_document(path, text, parser="pypdf")],
        }
    if suffix in {".html", ".htm"}:
        content = path.read_bytes()
        text = extract_html_text(content)
        tables = extract_html_tables(content)
        return {
            "file": {**file_info, "parser": "beautifulsoup+pandas_read_html"},
            "tables": annotate_material_tables(tables, path=path),
            "text_documents": [make_text_document(path, text, parser="beautifulsoup")],
        }
    text = path.read_text(encoding="utf-8", errors="replace")
    return {"file": {**file_info, "parser": "text"}, "tables": [], "text_documents": [make_text_document(path, text, parser="text")]}


def parse_csv_file(path: Path) -> list[dict[str, Any]]:
    max_rows = int(os.getenv("USER_TABLE_MAX_ROWS", "200"))
    max_cols = int(os.getenv("USER_TABLE_MAX_COLS", "40"))
    encodings = ["utf-8-sig", "utf-8", "gb18030"]
    last_error: Exception | None = None
    for encoding in encodings:
        try:
            with path.open("r", encoding=encoding, errors="replace", newline="") as handle:
                sample = handle.read(4096)
                handle.seek(0)
                dialect = csv.Sniffer().sniff(sample) if sample.strip() else csv.excel
                rows = list(csv.reader(handle, dialect))
            table = normalize_table(rows, max_rows=max_rows, max_cols=max_cols)
            table.update(material_table_metadata(path, source_parser=f"csv:{encoding}", table_index=1))
            table["normalized_metrics"] = normalize_table_metrics(table)
            return [table] if table.get("rows") else []
        except Exception as exc:  # noqa: BLE001
            last_error = exc
    raise RuntimeError(str(last_error))


def parse_excel_file(path: Path) -> list[dict[str, Any]]:
    try:
        import pandas as pd
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError("pandas/openpyxl is required for Excel parsing.") from exc
    max_rows = int(os.getenv("USER_TABLE_MAX_ROWS", "200"))
    max_cols = int(os.getenv("USER_TABLE_MAX_COLS", "40"))
    max_sheets = int(os.getenv("USER_EXCEL_MAX_SHEETS", "8"))
    sheets = pd.read_excel(path, sheet_name=None, nrows=max_rows)
    tables: list[dict[str, Any]] = []
    for sheet_index, (sheet_name, df) in enumerate(list(sheets.items())[:max_sheets], start=1):
        records = json.loads(df.where(df.notna(), None).to_json(orient="split", force_ascii=False))
        raw_table = [[flatten_column_name(col) for col in records.get("columns") or []]] + (records.get("data") or [])
        table = normalize_table(raw_table, max_rows=max_rows, max_cols=max_cols)
        if not table.get("rows"):
            continue
        table.update(material_table_metadata(path, source_parser="pandas.read_excel", table_index=sheet_index))
        table["sheet_name"] = str(sheet_name)
        table["normalized_metrics"] = normalize_table_metrics(table)
        tables.append(table)
    return tables


def parse_json_file(path: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    payload = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    tables: list[dict[str, Any]] = []
    if isinstance(payload, list) and all(isinstance(item, dict) for item in payload):
        headers = sorted({str(key) for item in payload for key in item.keys()})
        raw_table = [headers] + [[item.get(header) for header in headers] for item in payload]
        table = normalize_table(raw_table, max_rows=int(os.getenv("USER_TABLE_MAX_ROWS", "200")), max_cols=int(os.getenv("USER_TABLE_MAX_COLS", "40")))
        table.update(material_table_metadata(path, source_parser="json_records", table_index=1))
        table["normalized_metrics"] = normalize_table_metrics(table)
        tables.append(table)
    text = json.dumps(payload, ensure_ascii=False)[: int(os.getenv("USER_TEXT_EXCERPT_CHARS", "6000"))]
    return tables, [make_text_document(path, text, parser="json")]


def annotate_material_tables(tables: list[dict[str, Any]], *, path: Path) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for index, table in enumerate(tables, start=1):
        annotated = dict(table)
        annotated.update(material_table_metadata(path, source_parser=str(table.get("source_parser") or "document"), table_index=index))
        annotated["normalized_metrics"] = normalize_table_metrics(annotated)
        output.append(annotated)
    return output


def material_table_metadata(path: Path, *, source_parser: str, table_index: int) -> dict[str, Any]:
    return {
        "source": "user_material",
        "source_path": str(path),
        "source_name": path.name,
        "source_parser": source_parser,
        "table_index": table_index,
        "data_type": infer_material_data_type(path.name),
    }


def make_text_document(path: Path, text: str, *, parser: str) -> dict[str, Any]:
    excerpt_chars = int(os.getenv("USER_TEXT_EXCERPT_CHARS", "6000"))
    return {
        "source": "user_material",
        "source_path": str(path),
        "source_name": path.name,
        "parser": parser,
        "text_excerpt": text[:excerpt_chars],
        "text_length": len(text),
        "data_type": infer_material_data_type(path.name + " " + text[:500]),
    }


def infer_material_data_type(text: str) -> str:
    return classify_data_need(text)


def attach_user_materials(pack: dict[str, Any], user_materials: dict[str, Any]) -> None:
    tables = user_materials.get("tables") or []
    text_documents = user_materials.get("text_documents") or []
    for table in tables:
        data_type = table.get("data_type") or classify_data_need(" ".join(map(str, table.get("headers") or [])))
        if data_type in {"kline", "quote"}:
            pack["market_data"].setdefault("user_tables", []).append(table)
        elif data_type in {"financials", "consensus"}:
            pack["financial_statements"].setdefault("user_tables", []).append(table)
        elif data_type == "sentiment":
            pack["sentiment_data"].setdefault("user_tables", []).append(table)
        elif data_type == "industry":
            pack["industry_data"]["items"].append({"source": "user_material_table", "table": table, "confidence": "B"})
        else:
            pack["company_specific_data"]["items"].append({"source": "user_material_table", "table": table, "confidence": "B"})
    for document in text_documents:
        data_type = document.get("data_type")
        item = {"source": "user_material_text", **document, "confidence": "B"}
        if data_type == "sentiment":
            pack["sentiment_data"]["samples"].append(item)
        elif data_type == "industry":
            pack["industry_data"]["items"].append(item)
        else:
            pack["company_specific_data"]["items"].append(item)


def normalize_table_metrics(table: dict[str, Any]) -> list[dict[str, Any]]:
    metrics: list[dict[str, Any]] = []
    headers = [str(header) for header in table.get("headers") or []]
    for row_index, row in enumerate(table.get("rows") or [], start=1):
        row_text = " ".join(str(value) for value in row.values())
        metric_type = classify_forecast_metric(row_text) or classify_data_need(row_text)
        for key, value in row.items():
            number = extract_numeric_value(value)
            if number is None:
                continue
            unit = infer_unit(str(key), row_text)
            metrics.append(
                {
                    "metric_type": metric_type,
                    "label": str(key),
                    "year": infer_year_from_text(str(key)) or infer_year_from_text(row_text),
                    "raw_value": clean_cell(value),
                    "value": number,
                    "unit": unit,
                    "normalized_value": normalize_numeric_unit(number, unit),
                    "row_index": row_index,
                    "source_table_index": table.get("table_index"),
                    "source_name": table.get("source_name") or table.get("source_parser"),
                }
            )
    return metrics[: int(os.getenv("NORMALIZED_TABLE_METRICS_MAX", "200"))]


def infer_unit(label: str, context: str) -> str | None:
    text = f"{label} {context}"
    lowered = text.lower()
    if "%" in text or "pct" in lowered or "percent" in lowered or "比例" in text or "率" in text:
        return "percent"
    if "百万" in text or "mn" in lowered or "million" in lowered:
        return "million"
    if "亿" in text or "100mn" in lowered:
        return "hundred_million"
    if "元/股" in text or "每股" in text or "eps" in lowered:
        return "per_share"
    if "元" in text or "cny" in lowered or "rmb" in lowered:
        return "currency"
    return None


def normalize_numeric_unit(value: float, unit: str | None) -> float:
    if unit == "percent":
        return round(value / 100, 8)
    if unit == "million":
        return round(value * 1_000_000, 4)
    if unit == "hundred_million":
        return round(value * 100_000_000, 4)
    return value


def build_event_timeline(pack: dict[str, Any]) -> dict[str, Any]:
    events: list[dict[str, Any]] = []
    for announcement in pack.get("filings_and_announcements") or []:
        title = announcement.get("title")
        date_value = str(announcement.get("notice_date") or announcement.get("display_time") or "")[:10]
        if title and date_value:
            events.append(
                {
                    "date": date_value,
                    "event_type": classify_event_type(title),
                    "title": title,
                    "source": announcement.get("source"),
                    "source_url": announcement.get("source_url"),
                    "confidence": announcement.get("credibility", "B"),
                }
            )
    events = sorted(events, key=lambda item: item.get("date") or "", reverse=True)[: int(os.getenv("EVENT_TIMELINE_MAX_EVENTS", "40"))]
    return {
        "events": events,
        "event_windows": calculate_event_windows(events, (pack.get("market_data") or {}).get("daily_kline") or {}),
    }


def classify_event_type(title: str) -> str:
    rules = [
        ("earnings", ["年报", "季报", "业绩", "利润", "annual", "quarterly", "earnings"]),
        ("capital_action", ["分红", "回购", "增持", "减持", "股权", "dividend", "buyback"]),
        ("risk_regulatory", ["问询", "处罚", "诉讼", "监管", "investigation"]),
        ("corporate_action", ["并购", "投资", "重组", "收购", "acquisition", "restructuring"]),
    ]
    lower = title.lower()
    for event_type, keywords in rules:
        if any(keyword.lower() in lower or keyword in title for keyword in keywords):
            return event_type
    return "announcement"


def calculate_event_windows(events: list[dict[str, Any]], kline: dict[str, Any]) -> list[dict[str, Any]]:
    records = sorted(kline.get("records") or [], key=lambda item: str(item.get("date") or ""))
    if not records:
        return []
    date_to_index = {str(record.get("date"))[:10]: index for index, record in enumerate(records)}
    windows: list[dict[str, Any]] = []
    for event in events[: int(os.getenv("EVENT_WINDOW_MAX_EVENTS", "12"))]:
        event_date = str(event.get("date") or "")[:10]
        index = date_to_index.get(event_date)
        if index is None:
            later = [idx for day, idx in date_to_index.items() if day >= event_date]
            index = min(later) if later else None
        if index is None:
            continue
        close0 = _to_float(records[index].get("close"))
        if close0 is None:
            continue
        window_result = {"event": event, "base_trade_date": records[index].get("date"), "returns": {}}
        for days in [1, 3, 5, 10, 20]:
            end_index = min(index + days, len(records) - 1)
            close1 = _to_float(records[end_index].get("close"))
            if close1 is not None and close0:
                window_result["returns"][f"{days}d"] = round(close1 / close0 - 1, 6)
        windows.append(window_result)
    return windows


def build_valuation_data(pack: dict[str, Any]) -> dict[str, Any]:
    quote = (pack.get("market_data") or {}).get("quote") or {}
    normalized = quote.get("normalized") or {}
    snapshot = {
        "source": quote.get("source"),
        "retrieved_at": quote.get("retrieved_at"),
        "last_price": normalized.get("last_price"),
        "market_cap": normalized.get("market_cap"),
        "float_market_cap": normalized.get("float_market_cap"),
        "pe_ttm": normalized.get("pe_ttm"),
        "pe_dynamic": normalized.get("pe_dynamic"),
        "pe_static": normalized.get("pe_static"),
        "pb": normalized.get("pb"),
        "dividend_yield_ttm_pct": normalized.get("dividend_yield_ttm_pct"),
    }
    peer_snapshot: list[dict[str, Any]] = []
    for item in (pack.get("market_data") or {}).get("peer_quotes") or []:
        peer_quote = item.get("quote") or {}
        peer_norm = peer_quote.get("normalized") or {}
        peer_snapshot.append(
            {
                "ticker": item.get("ticker"),
                "company_name": item.get("company_name"),
                "reason": item.get("reason"),
                "last_price": peer_norm.get("last_price"),
                "market_cap": peer_norm.get("market_cap"),
                "pe_ttm": peer_norm.get("pe_ttm"),
                "pb": peer_norm.get("pb"),
                "source": peer_quote.get("source"),
            }
        )
    return {"snapshot": snapshot, "peer_snapshot": peer_snapshot}


def collect_sentiment_samples(
    pack: dict[str, Any],
    *,
    collection_mode: str = "standard",
    progress_callback: Any = None,
) -> None:
    limits = _collection_limits(collection_mode)
    queries = (pack.get("sentiment_data") or {}).get("search_queries") or []
    samples = pack["sentiment_data"].setdefault("samples", [])
    max_queries = int(os.getenv("SENTIMENT_SEARCH_MAX_QUERIES", str(limits["sentiment_search_max_queries"])))
    max_results = int(
        os.getenv("SENTIMENT_SEARCH_RESULTS_PER_QUERY", str(limits["sentiment_search_results_per_query"]))
    )
    for query in queries[:max_queries]:
        try:
            _progress(progress_callback, f"    [sentiment] start {query}")
            results = search_web(query, max_results=max_results)
            for result in results[:max_results]:
                samples.append(
                    {
                        "source": result.get("source"),
                        "title": result.get("title"),
                        "url": result.get("url"),
                        "content": result.get("content"),
                        "query": query,
                        "retrieved_at": datetime.now().astimezone().isoformat(),
                        "confidence": "C",
                    }
                )
            _progress(progress_callback, f"    [sentiment] done {query}; results={len(results[:max_results])}")
        except Exception as exc:  # noqa: BLE001
            pack.setdefault("fetch_errors", []).append({"source": "sentiment_search", "query": query, "error": str(exc)})
            _progress(progress_callback, f"    [sentiment] error {query}: {exc}")


def build_data_need_coverage(data_requests: list[dict[str, Any]], pack: dict[str, Any]) -> list[dict[str, Any]]:
    coverage: list[dict[str, Any]] = []
    for request in data_requests:
        data_type = str(request.get("data_type") or "other")
        refs = data_refs_for_type(data_type, pack)
        coverage.append(
            {
                "item": request.get("item"),
                "data_type": data_type,
                "priority": request.get("priority"),
                "requested_by": request.get("requested_by"),
                "status": "covered" if refs else "missing_or_partial",
                "available_refs": refs,
                "notes": "Use evidence refs as inputs; if refs are empty, downstream analyst should lower confidence.",
            }
        )
    return coverage


def build_analyst_data_delivery(analyst_data_requests: dict[str, Any], pack: dict[str, Any]) -> dict[str, Any]:
    delivery: dict[str, Any] = {}
    for analyst, payload in analyst_data_requests.items():
        needs = payload.get("required_data") if isinstance(payload, dict) else []
        refs: list[dict[str, Any]] = []
        for need in needs or []:
            if not isinstance(need, dict):
                continue
            data_type = classify_data_need(str(need.get("item") or ""))
            refs.extend(data_refs_for_type(data_type, pack))
        unique_refs: list[dict[str, Any]] = []
        seen: set[str] = set()
        for ref in refs:
            key = json.dumps(ref, ensure_ascii=False, sort_keys=True)
            if key not in seen:
                unique_refs.append(ref)
                seen.add(key)
        delivery[analyst] = {
            "requested_data_count": len(needs or []),
            "delivered_refs": unique_refs,
            "delivery_status": "covered" if unique_refs else "missing_or_partial",
        }
    return delivery


def data_refs_for_type(data_type: str, pack: dict[str, Any]) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    if data_type in {"quote", "kline"}:
        if (pack.get("market_data") or {}).get("quote"):
            refs.append({"path": "research_data_pack.market_data.quote", "kind": "quote"})
        if (pack.get("market_data") or {}).get("daily_kline"):
            refs.append({"path": "research_data_pack.market_data.daily_kline", "kind": "daily_kline"})
        if (pack.get("market_data") or {}).get("benchmark_data"):
            refs.append({"path": "research_data_pack.market_data.benchmark_data", "kind": "benchmark"})
    if data_type in {"financials", "consensus"}:
        financials = pack.get("financial_statements") or {}
        for key in ["key_indicators", "tushare", "consensus_proxy", "user_tables"]:
            if financials.get(key):
                refs.append({"path": f"research_data_pack.financial_statements.{key}", "kind": key})
    if data_type == "filings":
        if pack.get("filings_and_announcements"):
            refs.append({"path": "research_data_pack.filings_and_announcements", "kind": "announcements"})
        if (pack.get("event_timeline") or {}).get("events"):
            refs.append({"path": "research_data_pack.event_timeline", "kind": "event_timeline"})
    if data_type == "macro":
        if (pack.get("macro_inputs") or {}).get("risk_free_rate"):
            refs.append({"path": "research_data_pack.macro_inputs.risk_free_rate", "kind": "risk_free_rate"})
        if (pack.get("macro_inputs") or {}).get("beta"):
            refs.append({"path": "research_data_pack.macro_inputs.beta", "kind": "beta"})
    if data_type == "industry":
        if (pack.get("industry_data") or {}).get("items"):
            refs.append({"path": "research_data_pack.industry_data.items", "kind": "industry_evidence"})
    if data_type == "sentiment":
        if (pack.get("sentiment_data") or {}).get("samples"):
            refs.append({"path": "research_data_pack.sentiment_data.samples", "kind": "sentiment_samples"})
    if data_type == "company_specific":
        if (pack.get("company_specific_data") or {}).get("items"):
            refs.append({"path": "research_data_pack.company_specific_data.items", "kind": "company_specific_evidence"})
    if data_type in {"quote", "financials", "consensus", "company_specific", "industry"}:
        if (pack.get("valuation_data") or {}).get("snapshot"):
            refs.append({"path": "research_data_pack.valuation_data", "kind": "valuation_snapshot"})
        if pack.get("peer_table"):
            refs.append({"path": "research_data_pack.peer_table", "kind": "peer_candidates"})
    if (pack.get("user_materials") or {}).get("files"):
        refs.append({"path": "research_data_pack.user_materials", "kind": "user_materials"})
    if (pack.get("dynamic_research") or {}).get("document_corpus"):
        refs.append({"path": "research_data_pack.dynamic_research.document_corpus", "kind": "dynamic_documents"})
    return refs


def collect_dynamic_research(
    *,
    company_name: str,
    ticker: str,
    data_requests: list[dict[str, Any]],
    data_requirement_summary: dict[str, Any] | None = None,
    collection_mode: str = "standard",
    progress_callback: Any = None,
) -> dict[str, Any]:
    limits = _collection_limits(collection_mode)
    queries = build_dynamic_research_queries(
        company_name=company_name,
        ticker=ticker,
        data_requests=data_requests,
        data_requirement_summary=data_requirement_summary,
    )[: limits["dynamic_research_max_queries"]]
    max_docs = limits["dynamic_research_max_docs"]
    max_results_per_query = limits["dynamic_research_results_per_query"]
    corpus: list[dict[str, Any]] = []
    parse_errors: list[dict[str, Any]] = []
    seen_urls: set[str] = set()

    query_results: dict[str, list[dict[str, Any]]] = {}
    max_search_workers = int(os.getenv("WEB_SEARCH_MAX_WORKERS", "4"))
    _progress(progress_callback, f"    [research] dynamic queries={len(queries)}; max_docs={max_docs}")
    with ThreadPoolExecutor(max_workers=min(max_search_workers, max(1, len(queries)))) as executor:
        futures = {
            executor.submit(
                search_web,
                query_item["query"],
                max_results=max_results_per_query,
            ): query_item["query"]
            for query_item in queries
        }
        for future in as_completed(futures):
            query = futures[future]
            try:
                results = future.result()[:max_results_per_query]
                query_results[query] = results
                _progress(progress_callback, f"    [research] search done {query}; results={len(results)}")
            except Exception as exc:  # noqa: BLE001
                parse_errors.append({"query": query, "stage": "search", "error": str(exc)})
                query_results[query] = []
                _progress(progress_callback, f"    [research] search error {query}: {exc}")
    for query_item in queries:
        query = query_item["query"]
        results = query_results.get(query, [])
        for result in results:
            url = str(result.get("url") or "").strip()
            if not url or url in seen_urls:
                continue
            seen_urls.add(url)
            doc = {
                "query": query,
                "data_type": query_item.get("data_type"),
                "title": result.get("title"),
                "url": url,
                "search_content": result.get("content"),
                "search_source": result.get("source"),
                "search_score": result.get("score"),
                "document_type": classify_document_url(url, str(result.get("title") or "")),
                "retrieved_at": datetime.now().astimezone().isoformat(),
            }
            if should_parse_document(doc) and len(corpus) < max_docs:
                try:
                    _progress(progress_callback, f"    [research] parse start {url}")
                    parsed = fetch_and_parse_document(url)
                    doc.update(parsed)
                    _progress(progress_callback, f"    [research] parse done {url}; tables={doc.get('table_count', 0)}")
                except Exception as exc:  # noqa: BLE001
                    doc["parse_status"] = "failed"
                    doc["parse_error"] = str(exc)
                    parse_errors.append({"url": url, "stage": "parse", "error": str(exc)})
                    _progress(progress_callback, f"    [research] parse error {url}: {exc}")
            else:
                doc["parse_status"] = "snippet_only"
            if not doc.get("text_excerpt"):
                text = str(result.get("content") or "")
                doc.update(
                    {
                        "text_excerpt": text[: int(os.getenv("DOCUMENT_TEXT_EXCERPT_CHARS", "6000"))],
                        "text_length": len(text),
                        "tables": [],
                        "table_count": 0,
                        "table_text_excerpt": "",
                    }
                )
            doc["extracted_signals"] = extract_research_signals_from_document(doc)
            corpus.append(doc)
            if len(corpus) >= max_docs:
                break
        if len(corpus) >= max_docs:
            break

    consensus_proxy = build_consensus_proxy(corpus)
    industry_evidence = build_dynamic_evidence_items(corpus)
    return {
        "queries": queries,
        "document_corpus": corpus,
        "consensus_proxy": consensus_proxy,
        "industry_and_company_specific_evidence": industry_evidence,
        "parse_errors": parse_errors,
        "notes": [
            "This section is a fallback for missing Wind/Choice consensus and industry data.",
            "Numbers extracted from research reports or webpages are proxy evidence, not authoritative consensus.",
        ],
    }


def build_dynamic_research_queries(
    *,
    company_name: str,
    ticker: str,
    data_requests: list[dict[str, Any]],
    data_requirement_summary: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    base = company_name or ticker
    raw_items: list[dict[str, Any]] = []
    if base:
        raw_items.extend(
            [
                {"data_type": "consensus", "query": f"{base} {ticker} 研报 盈利预测 EPS 目标价 PDF"},
                {"data_type": "consensus", "query": f"{base} {ticker} 券商研报 目标价 净利润预测"},
                {"data_type": "industry", "query": f"{base} 行业研究 市场规模 竞争格局 研报"},
            ]
        )
    for request in data_requests:
        item = str(request.get("item") or "").strip()
        data_type = str(request.get("data_type") or "other")
        for query in request.get("suggested_search_queries") or []:
            raw_items.append({"data_type": data_type, "query": str(query)})
        if item and data_type in {"consensus", "industry", "company_specific", "filings", "sentiment"}:
            suffix = "研报 PDF 数据" if data_type in {"consensus", "industry", "company_specific"} else "公告 新闻 数据"
            raw_items.append({"data_type": data_type, "query": f"{base} {item} {suffix}".strip()})

    search_plan = (data_requirement_summary or {}).get("search_plan", {})
    if isinstance(search_plan, dict):
        for query in search_plan.get("queries", []) or []:
            raw_items.append({"data_type": classify_data_need(str(query)), "query": str(query)})

    max_queries = int(os.getenv("DYNAMIC_RESEARCH_MAX_QUERIES", str(COLLECTION_MODE_PRESETS["standard"]["dynamic_research_max_queries"])))
    deduped: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in raw_items:
        query = " ".join(str(item.get("query") or "").split())
        if not query or query in seen:
            continue
        seen.add(query)
        deduped.append({"data_type": item.get("data_type") or classify_data_need(query), "query": query})
        if len(deduped) >= max_queries:
            break
    return deduped


def classify_document_url(url: str, title: str = "") -> str:
    text = f"{url} {title}".lower()
    if ".pdf" in text or "pdf.dfcfw.com" in text:
        return "pdf"
    if any(keyword in text for keyword in ["研报", "研究报告", "research", "target price", "盈利预测"]):
        return "research_report"
    if any(keyword in text for keyword in ["公告", "annual", "report", "sse.com", "cninfo", "moutaichina"]):
        return "filing_or_company_page"
    return "webpage"


def should_parse_document(doc: dict[str, Any]) -> bool:
    doc_type = doc.get("document_type")
    if doc_type in {"pdf", "research_report", "filing_or_company_page"}:
        return True
    data_type = doc.get("data_type")
    return data_type in {"consensus", "industry", "company_specific", "filings"}


def fetch_and_parse_document(url: str) -> dict[str, Any]:
    content, content_type = fetch_binary(url)
    lowered_type = content_type.lower()
    is_pdf = "pdf" in lowered_type or ".pdf" in url.lower()
    if is_pdf:
        text = extract_pdf_text(content)
        tables = extract_pdf_tables(content)
        parser = "pypdf+pdfplumber"
        doc_type = "pdf"
    else:
        text = extract_html_text(content)
        tables = extract_html_tables(content)
        parser = "beautifulsoup+pandas_read_html"
        doc_type = "html"
    excerpt_chars = int(os.getenv("DOCUMENT_TEXT_EXCERPT_CHARS", "6000"))
    table_text = tables_to_text(tables)
    return {
        "parse_status": "parsed",
        "parsed_document_type": doc_type,
        "content_type": content_type,
        "parser": parser,
        "text_excerpt": text[:excerpt_chars],
        "text_length": len(text),
        "tables": tables,
        "table_count": len(tables),
        "table_text_excerpt": table_text[:excerpt_chars],
    }


def fetch_binary(url: str, timeout: int | None = None) -> tuple[bytes, str]:
    if timeout is None:
        timeout = int(os.getenv("DOCUMENT_FETCH_TIMEOUT_SECONDS", "12"))
    max_bytes = int(os.getenv("DOCUMENT_MAX_BYTES", str(4 * 1024 * 1024)))
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 api_workflow/1.0",
            "Accept": "application/pdf,text/html,application/xhtml+xml,text/plain,*/*",
        },
    )
    context = _ssl_context()
    with urllib.request.urlopen(request, timeout=timeout, context=context) as response:
        content_type = response.headers.get("Content-Type", "")
        data = response.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise RuntimeError(f"document exceeds DOCUMENT_MAX_BYTES={max_bytes}")
    return data, content_type


def extract_pdf_text(content: bytes) -> str:
    try:
        from pypdf import PdfReader
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError("pypdf is not installed. Run: python -m pip install pypdf") from exc
    import io

    reader = PdfReader(io.BytesIO(content))
    max_pages = int(os.getenv("PDF_PARSE_MAX_PAGES", "5"))
    texts: list[str] = []
    for page in reader.pages[:max_pages]:
        try:
            texts.append(page.extract_text() or "")
        except Exception:  # noqa: BLE001
            continue
    return "\n".join(texts).strip()


def extract_pdf_tables(content: bytes) -> list[dict[str, Any]]:
    try:
        import pdfplumber
    except Exception:
        return []
    import io

    tables: list[dict[str, Any]] = []
    max_pages = int(os.getenv("PDF_TABLE_PARSE_MAX_PAGES", os.getenv("PDF_PARSE_MAX_PAGES", "5")))
    max_tables = int(os.getenv("DOCUMENT_MAX_TABLES", "6"))
    max_rows = int(os.getenv("DOCUMENT_TABLE_MAX_ROWS", "25"))
    max_cols = int(os.getenv("DOCUMENT_TABLE_MAX_COLS", "12"))
    with pdfplumber.open(io.BytesIO(content)) as pdf:
        for page_index, page in enumerate(pdf.pages[:max_pages], start=1):
            try:
                page_tables = page.extract_tables() or []
            except Exception:  # noqa: BLE001
                continue
            for raw_table in page_tables:
                normalized = normalize_table(raw_table, max_rows=max_rows, max_cols=max_cols)
                if not normalized.get("rows"):
                    continue
                normalized.update(
                    {
                        "source_parser": "pdfplumber",
                        "page": page_index,
                        "table_index": len(tables) + 1,
                    }
                )
                tables.append(normalized)
                if len(tables) >= max_tables:
                    return tables
    return tables


def extract_html_text(content: bytes) -> str:
    charset = "utf-8"
    head = content[:500].decode("ascii", errors="ignore")
    match = re.search(r"charset=['\"]?([A-Za-z0-9_-]+)", head, flags=re.IGNORECASE)
    if match:
        charset = match.group(1)
    html = content.decode(charset, errors="replace")
    try:
        from bs4 import BeautifulSoup
    except Exception:
        return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html)).strip()
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    text = soup.get_text("\n")
    lines = [" ".join(line.split()) for line in text.splitlines()]
    return "\n".join(line for line in lines if line).strip()


def extract_html_tables(content: bytes) -> list[dict[str, Any]]:
    max_tables = int(os.getenv("DOCUMENT_MAX_TABLES", "6"))
    max_rows = int(os.getenv("DOCUMENT_TABLE_MAX_ROWS", "25"))
    max_cols = int(os.getenv("DOCUMENT_TABLE_MAX_COLS", "12"))
    try:
        import io
        import pandas as pd

        dfs = pd.read_html(io.BytesIO(content))
    except Exception:
        dfs = []

    tables: list[dict[str, Any]] = []
    for df in dfs[:max_tables]:
        try:
            records = json.loads(df.where(df.notna(), None).to_json(orient="split", force_ascii=False))
            rows = records.get("data") or []
            columns = [flatten_column_name(col) for col in records.get("columns") or []]
        except Exception:  # noqa: BLE001
            continue
        raw_table = [columns] + rows
        normalized = normalize_table(raw_table, max_rows=max_rows, max_cols=max_cols)
        if not normalized.get("rows"):
            continue
        normalized.update({"source_parser": "pandas.read_html", "table_index": len(tables) + 1})
        tables.append(normalized)
    return tables


def normalize_table(raw_table: Any, *, max_rows: int, max_cols: int) -> dict[str, Any]:
    if not raw_table:
        return {"headers": [], "rows": [], "row_count": 0, "column_count": 0}
    cleaned_rows: list[list[str]] = []
    for row in raw_table:
        if row is None:
            continue
        cells = row if isinstance(row, (list, tuple)) else [row]
        cleaned = [clean_cell(cell) for cell in cells[:max_cols]]
        if any(cell for cell in cleaned):
            cleaned_rows.append(cleaned)
        if len(cleaned_rows) >= max_rows + 1:
            break
    if not cleaned_rows:
        return {"headers": [], "rows": [], "row_count": 0, "column_count": 0}
    header_candidate = cleaned_rows[0]
    has_header = any(re.search(r"[A-Za-z\u4e00-\u9fff]", cell) for cell in header_candidate)
    headers = header_candidate if has_header else [f"col_{index + 1}" for index in range(len(header_candidate))]
    rows = cleaned_rows[1:] if has_header else cleaned_rows
    column_count = max([len(headers)] + [len(row) for row in rows]) if rows or headers else 0
    headers = pad_list(headers, column_count)
    row_dicts: list[dict[str, str]] = []
    for row in rows[:max_rows]:
        padded = pad_list(row, column_count)
        row_dicts.append({headers[index] or f"col_{index + 1}": padded[index] for index in range(column_count)})
    return {
        "headers": headers,
        "rows": row_dicts,
        "row_count": len(row_dicts),
        "column_count": column_count,
    }


def tables_to_text(tables: list[dict[str, Any]]) -> str:
    parts: list[str] = []
    for table in tables:
        header = " | ".join(str(col) for col in table.get("headers", []))
        if header:
            parts.append(f"TABLE {table.get('table_index', '')} HEADER: {header}")
        for row in table.get("rows", [])[: int(os.getenv("DOCUMENT_TABLE_TEXT_MAX_ROWS", "15"))]:
            parts.append(" | ".join(f"{key}: {value}" for key, value in row.items() if value not in {None, ""}))
    return "\n".join(parts)


def clean_cell(value: Any) -> str:
    if value is None:
        return ""
    text = str(value)
    if text.lower() == "nan":
        return ""
    return re.sub(r"\s+", " ", text).strip()


def flatten_column_name(value: Any) -> str:
    if isinstance(value, tuple):
        return " ".join(clean_cell(part) for part in value if clean_cell(part))
    return clean_cell(value)


def pad_list(values: list[str], length: int) -> list[str]:
    return values + [""] * max(0, length - len(values))


def extract_research_signals_from_document(doc: dict[str, Any]) -> dict[str, Any]:
    text = " ".join(
        str(part or "")
        for part in [
            doc.get("title"),
            doc.get("search_content"),
            doc.get("text_excerpt"),
            doc.get("table_text_excerpt"),
        ]
    )
    signals = extract_research_signals(text)
    table_signals = extract_table_forecast_signals(doc.get("tables") or [])
    for key, values in table_signals.items():
        signals.setdefault(key, [])
        signals[key].extend(values)
    return signals


def extract_research_signals(text: str) -> dict[str, Any]:
    normalized = re.sub(r"\s+", " ", text)
    signals: dict[str, Any] = {
        "ratings": [],
        "target_prices": [],
        "eps_forecasts": [],
        "net_profit_forecasts": [],
        "revenue_forecasts": [],
        "snippets": [],
    }
    for rating in ["买入", "增持", "强烈推荐", "推荐", "跑赢行业", "优于大市", "中性", "持有", "卖出"]:
        if rating in normalized:
            signals["ratings"].append(rating)

    for match in re.finditer(r"(?:目标价|目标价格|合理价值|合理价格|合理股价|目标股价)[^0-9]{0,12}([0-9]{2,5}(?:\.[0-9]+)?)\s*(?:元|港元|人民币|HKD|CNY)?", normalized, flags=re.IGNORECASE):
        signals["target_prices"].append({"value": _to_float(match.group(1)), "snippet": _snippet(normalized, match.start(), match.end())})

    eps_patterns = [
        r"(20[2-3][0-9])[E年]?[^\n。；;]{0,50}EPS[^0-9]{0,12}([0-9]{1,3}(?:\.[0-9]+)?)",
        r"EPS[^\n。；;]{0,50}(20[2-3][0-9])[E年]?[^\n。；;]{0,20}([0-9]{1,3}(?:\.[0-9]+)?)",
    ]
    for pattern in eps_patterns:
        for match in re.finditer(pattern, normalized, flags=re.IGNORECASE):
            signals["eps_forecasts"].append({"year": match.group(1), "value": _to_float(match.group(2)), "snippet": _snippet(normalized, match.start(), match.end())})

    forecast_patterns = [
        ("net_profit_forecasts", r"(20[2-3][0-9])[E年]?[^\n。；;]{0,60}(?:归母净利润|净利润)[^0-9]{0,12}([0-9]{1,6}(?:\.[0-9]+)?)\s*(?:亿|亿元|百万元)?"),
        ("revenue_forecasts", r"(20[2-3][0-9])[E年]?[^\n。；;]{0,60}(?:营收|营业收入|收入)[^0-9]{0,12}([0-9]{1,7}(?:\.[0-9]+)?)\s*(?:亿|亿元|百万元)?"),
    ]
    for key, pattern in forecast_patterns:
        for match in re.finditer(pattern, normalized, flags=re.IGNORECASE):
            signals[key].append({"year": match.group(1), "value": _to_float(match.group(2)), "snippet": _snippet(normalized, match.start(), match.end())})

    for keyword in ["一致预期", "盈利预测", "目标价", "市场规模", "竞争格局", "库存", "批价", "GMV", "门店", "IP", "盲盒"]:
        pos = normalized.find(keyword)
        if pos >= 0:
            signals["snippets"].append({"keyword": keyword, "snippet": _snippet(normalized, pos, pos + len(keyword))})
    return signals


def extract_table_forecast_signals(tables: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    signals: dict[str, list[dict[str, Any]]] = {
        "eps_forecasts": [],
        "net_profit_forecasts": [],
        "revenue_forecasts": [],
        "target_prices": [],
    }
    for table in tables:
        headers = [str(header) for header in table.get("headers") or []]
        year_by_col: dict[str, str] = {}
        for header in headers:
            match = re.search(r"(20[2-3][0-9])", header)
            if match:
                year_by_col[header] = match.group(1)
        for row in table.get("rows") or []:
            row_text = " ".join(str(value) for value in row.values())
            metric = classify_forecast_metric(row_text)
            if not metric:
                continue
            for key, value in row.items():
                number = extract_numeric_value(value)
                if number is None:
                    continue
                year = year_by_col.get(str(key)) or infer_year_from_text(str(key)) or infer_year_from_text(row_text)
                if metric == "target_price":
                    item = {
                        "value": number,
                        "snippet": row_text[:240],
                        "source": "table",
                        "table_index": table.get("table_index"),
                        "page": table.get("page"),
                    }
                    if _is_valid_forecast_observation("target_price", item):
                        signals["target_prices"].append(item)
                else:
                    item = {
                        "year": year,
                        "value": number,
                        "snippet": row_text[:240],
                        "source": "table",
                        "table_index": table.get("table_index"),
                        "page": table.get("page"),
                    }
                    if _is_valid_forecast_observation(metric, item):
                        signals[metric].append(item)
    return signals


def classify_forecast_metric(row_text: str) -> str | None:
    text = row_text.lower()
    if "eps" in text or "每股收益" in row_text or "摊薄每股收益" in row_text:
        return "eps_forecasts"
    if any(keyword in row_text for keyword in ["归母净利润", "归属母公司净利润", "净利润", "Net profit"]):
        return "net_profit_forecasts"
    if any(keyword in row_text for keyword in ["营业收入", "营收", "收入", "Revenue"]):
        return "revenue_forecasts"
    if any(keyword in row_text for keyword in ["目标价", "合理价值", "合理价格", "目标股价"]):
        return "target_price"
    return None


def extract_numeric_value(value: Any) -> float | None:
    text = clean_cell(value)
    if not text:
        return None
    match = re.search(r"-?\d+(?:,\d{3})*(?:\.\d+)?", text)
    if not match:
        return None
    return _to_float(match.group(0).replace(",", ""))


def infer_year_from_text(text: str) -> str | None:
    match = re.search(r"(20[2-3][0-9])", text)
    return match.group(1) if match else None


def _is_valid_forecast_observation(metric: str, item: dict[str, Any]) -> bool:
    value = _to_float(item.get("value"))
    snippet = str(item.get("snippet") or "")
    year = str(item.get("year") or "")
    if value is None:
        return False
    if metric == "target_price":
        return 0 < value < 100000
    if not re.fullmatch(r"20[2-3][0-9]", year):
        return False
    if metric == "eps_forecasts":
        return 0 < value < 1000
    if metric in {"revenue_forecasts", "net_profit_forecasts"}:
        if "%" in snippet and value < 100:
            return False
        return value > 100
    return True


def build_consensus_proxy(corpus: list[dict[str, Any]]) -> dict[str, Any]:
    target_prices: list[dict[str, Any]] = []
    eps: list[dict[str, Any]] = []
    net_profit: list[dict[str, Any]] = []
    revenue: list[dict[str, Any]] = []
    ratings: list[str] = []
    for doc in corpus:
        signals = doc.get("extracted_signals") or {}
        for item in signals.get("target_prices") or []:
            if _is_valid_forecast_observation("target_price", item):
                target_prices.append({**item, "source_url": doc.get("url"), "title": doc.get("title")})
        for item in signals.get("eps_forecasts") or []:
            if _is_valid_forecast_observation("eps_forecasts", item):
                eps.append({**item, "source_url": doc.get("url"), "title": doc.get("title")})
        for item in signals.get("net_profit_forecasts") or []:
            if _is_valid_forecast_observation("net_profit_forecasts", item):
                net_profit.append({**item, "source_url": doc.get("url"), "title": doc.get("title")})
        for item in signals.get("revenue_forecasts") or []:
            if _is_valid_forecast_observation("revenue_forecasts", item):
                revenue.append({**item, "source_url": doc.get("url"), "title": doc.get("title")})
        ratings.extend(signals.get("ratings") or [])

    def median_value(items: list[dict[str, Any]]) -> float | None:
        values = [_to_float(item.get("value")) for item in items]
        values = [value for value in values if value is not None]
        if not values:
            return None
        values.sort()
        mid = len(values) // 2
        if len(values) % 2:
            return values[mid]
        return round((values[mid - 1] + values[mid]) / 2, 4)

    return {
        "source": "dynamic_research_proxy",
        "method": "Extract target price, EPS, revenue and net-profit snippets from searched research reports/webpages and parsed PDF/HTML tables; use median where multiple values exist.",
        "confidence": "C" if target_prices or eps or net_profit or revenue else "D",
        "target_price_median": median_value(target_prices),
        "target_price_observations": target_prices[:20],
        "eps_forecast_observations": eps[:30],
        "net_profit_forecast_observations": net_profit[:30],
        "revenue_forecast_observations": revenue[:30],
        "ratings_observed": sorted(set(ratings)),
        "document_count": len(corpus),
        "table_count": sum(int(doc.get("table_count") or 0) for doc in corpus),
        "limitations": [
            "This is not a true Wind/Choice consensus.",
            "Regex extraction can miss table-only forecasts or misread OCR/PDF text.",
            "Table extraction depends on PDF layout quality and can misalign rows/columns.",
            "Downstream analysts should treat this as proxy evidence and infer conservatively.",
        ],
    }


def build_dynamic_evidence_items(corpus: list[dict[str, Any]]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for doc in corpus:
        signals = doc.get("extracted_signals") or {}
        snippets = signals.get("snippets") or []
        if snippets or doc.get("data_type") in {"industry", "company_specific"}:
            items.append(
                {
                    "source": "dynamic_research_document",
                    "data_type": doc.get("data_type"),
                    "title": doc.get("title"),
                    "url": doc.get("url"),
                    "document_type": doc.get("document_type"),
                    "parse_status": doc.get("parse_status"),
                    "table_count": doc.get("table_count", 0),
                    "snippets": snippets[:10],
                    "text_excerpt": doc.get("text_excerpt", "")[:1200],
                    "table_text_excerpt": doc.get("table_text_excerpt", "")[:1200],
                    "confidence": "C",
                }
            )
    return items[:30]


def _snippet(text: str, start: int, end: int, radius: int = 90) -> str:
    return text[max(0, start - radius) : min(len(text), end + radius)].strip()


def provider_status() -> dict[str, Any]:
    return {
        "search": search_key_status(),
        "futu": {
            "enabled": _futu_should_use(),
            "host": os.getenv("FUTU_OPEND_HOST", "127.0.0.1"),
            "port": int(os.getenv("FUTU_OPEND_PORT", "11111")),
            "python_package": _package_available("futu"),
            "setup_note": "安装 futu-api 并启动 Futu OpenD 后，可启用 FUTU_ENABLED=1 作为行情/K线优先源。",
        },
        "eastmoney": {"enabled": True, "requires_key": False},
        "tencent_quote": {"enabled": True, "requires_key": False},
        "akshare": {
            "enabled": _package_available("akshare"),
            "requires_key": False,
            "use": "risk-free rate and public macro/market datasets",
        },
        "tushare": {
            "enabled": bool(os.getenv("TUSHARE_TOKEN", "").strip()) and _package_available("tushare"),
            "token_present": bool(os.getenv("TUSHARE_TOKEN", "").strip()),
            "python_package": _package_available("tushare"),
            "requires_key": True,
            "use": "A-share financial statements, daily basic valuation, dividends, share float, holder count, money flow",
        },
        "document_parsing": {
            "pdf": _package_available("pypdf"),
            "pdf_tables": _package_available("pdfplumber"),
            "html": _package_available("bs4"),
            "html_tables": _package_available("pandas"),
            "csv": True,
            "excel": _package_available("pandas"),
            "json": True,
            "text": True,
            "use": "Dynamic report/PDF/HTML extraction plus local user CSV/Excel/JSON/PDF/HTML/text materials.",
        },
        "paid_or_key_sources": [
            {"name": "Tushare Pro", "env": "TUSHARE_TOKEN", "use": "A股财务、行情、宏观、资金流"},
            {"name": "Wind/Choice/iFinD", "env": "manual_or_enterprise", "use": "一致预期、行业数据、历史估值"},
            {"name": "FMP/AlphaVantage/IEX", "env": "vendor_specific", "use": "美股财务、行情和估值"},
        ],
    }


def fetch_price_history(ticker: str, *, lookback_days: int = 540) -> dict[str, Any]:
    errors: list[str] = []
    if not _is_a_share_ticker(ticker):
        try:
            return fetch_yahoo_kline(ticker, lookback_days=lookback_days)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"yahoo: {exc}")
    if _futu_should_use():
        try:
            history = fetch_futu_kline(ticker, lookback_days=lookback_days)
            history["fallback_errors"] = errors
            return history
        except Exception as exc:  # noqa: BLE001
            errors.append(f"futu: {exc}")
    try:
        history = fetch_eastmoney_kline(ticker, lookback_days=lookback_days)
        history["fallback_errors"] = errors
        return history
    except Exception as exc:  # noqa: BLE001
        errors.append(f"eastmoney_kline: {exc}")
    try:
        history = fetch_tencent_kline(ticker, lookback_days=lookback_days)
        history["fallback_errors"] = errors
        return history
    except Exception as exc:  # noqa: BLE001
        errors.append(f"tencent_kline: {exc}")
    raise RuntimeError("; ".join(errors))


def fetch_futu_quote(ticker: str) -> dict[str, Any]:
    try:
        from futu import OpenQuoteContext, RET_OK
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError("futu-api is not installed. Run: python -m pip install futu-api") from exc

    symbol = _futu_symbol(ticker)
    host = os.getenv("FUTU_OPEND_HOST", "127.0.0.1")
    port = int(os.getenv("FUTU_OPEND_PORT", "11111"))
    quote_ctx = OpenQuoteContext(host=host, port=port)
    try:
        ret, data = quote_ctx.get_market_snapshot([symbol])
        if ret != RET_OK:
            raise RuntimeError(str(data))
        if data.empty:
            raise RuntimeError(f"Futu quote returned no data for {symbol}")
        row = data.iloc[0]
        normalized = {
            "name": row.get("name") or row.get("stock_name"),
            "code": symbol,
            "last_price": _to_float(row.get("last_price")),
            "previous_close": _to_float(row.get("prev_close_price")),
            "open": _to_float(row.get("open_price")),
            "high": _to_float(row.get("high_price")),
            "low": _to_float(row.get("low_price")),
            "change": _to_float(row.get("price_spread")),
            "change_pct": _to_float(row.get("change_rate")),
            "volume": _to_float(row.get("volume")),
            "amount": _to_float(row.get("turnover")),
            "turnover_rate_pct": _to_float(row.get("turnover_rate")),
            "market_cap": _to_float(row.get("total_market_val")),
            "float_market_cap": _to_float(row.get("circular_market_val")),
            "issued_shares": _to_float(row.get("issued_shares")),
            "outstanding_shares": _to_float(row.get("outstanding_shares")),
            "eps": _to_float(row.get("earning_per_share")),
            "pe_ttm": _to_float(row.get("pe_ttm_ratio")),
            "pe_static": _to_float(row.get("pe_ratio")),
            "pb": _to_float(row.get("pb_ratio")),
            "dividend_ttm": _to_float(row.get("dividend_ttm")),
            "dividend_yield_ttm_pct": _to_float(row.get("dividend_ratio_ttm")),
            "quote_time": str(row.get("update_time") or ""),
        }
        return {
            "source": "futu_opend_snapshot",
            "retrieved_at": datetime.now().astimezone().isoformat(),
            "ticker": ticker,
            "provider_symbol": symbol,
            "raw": row.to_dict(),
            "normalized": normalized,
        }
    finally:
        quote_ctx.close()


def fetch_futu_kline(ticker: str, *, lookback_days: int = 540) -> dict[str, Any]:
    try:
        from futu import AuType, KLType, OpenQuoteContext, RET_OK
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError("futu-api 未安装。运行 pip install futu-api，并启动 Futu OpenD。") from exc

    symbol = _futu_symbol(ticker)
    end = today_iso()
    start = (date.today() - timedelta(days=lookback_days)).isoformat()
    host = os.getenv("FUTU_OPEND_HOST", "127.0.0.1")
    port = int(os.getenv("FUTU_OPEND_PORT", "11111"))
    quote_ctx = OpenQuoteContext(host=host, port=port)
    try:
        ret, data, _ = quote_ctx.request_history_kline(
            symbol,
            start=start,
            end=end,
            ktype=KLType.K_DAY,
            autype=AuType.QFQ,
        )
        if ret != RET_OK:
            raise RuntimeError(str(data))
        records = []
        for _, row in data.iterrows():
            records.append(
                {
                    "date": str(row.get("time_key", ""))[:10],
                    "open": _to_float(row.get("open")),
                    "close": _to_float(row.get("close")),
                    "high": _to_float(row.get("high")),
                    "low": _to_float(row.get("low")),
                    "volume": _to_float(row.get("volume")),
                    "amount": _to_float(row.get("turnover")),
                    "turnover_rate": _to_float(row.get("turnover_rate")),
                    "pct_change": None,
                }
            )
        return {
            "source": "futu_opend",
            "ticker": ticker,
            "provider_symbol": symbol,
            "retrieved_at": datetime.now().astimezone().isoformat(),
            "adjustment": "qfq",
            "frequency": "daily",
            "start_date": start,
            "end_date": end,
            "records": records,
            "record_count": len(records),
        }
    finally:
        quote_ctx.close()


def fetch_eastmoney_kline(ticker: str, *, lookback_days: int = 540) -> dict[str, Any]:
    secid = _eastmoney_secid(ticker)
    end = today_iso().replace("-", "")
    start = (date.today() - timedelta(days=lookback_days)).isoformat().replace("-", "")
    fields1 = "f1,f2,f3,f4,f5,f6"
    fields2 = "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61"
    url = (
        "https://push2his.eastmoney.com/api/qt/stock/kline/get"
        f"?secid={secid}&fields1={fields1}&fields2={fields2}&klt=101&fqt=1&beg={start}&end={end}"
    )
    payload = _fetch_json(url)
    data = payload.get("data") or {}
    klines = data.get("klines") or []
    records = []
    for raw in klines:
        parts = str(raw).split(",")
        if len(parts) < 11:
            continue
        records.append(
            {
                "date": parts[0],
                "open": _to_float(parts[1]),
                "close": _to_float(parts[2]),
                "high": _to_float(parts[3]),
                "low": _to_float(parts[4]),
                "volume": _to_float(parts[5]),
                "amount": _to_float(parts[6]),
                "amplitude_pct": _to_float(parts[7]),
                "pct_change": _to_float(parts[8]),
                "change": _to_float(parts[9]),
                "turnover_rate": _to_float(parts[10]),
            }
        )
    return {
        "source": "eastmoney_kline",
        "source_url": url,
        "retrieved_at": datetime.now().astimezone().isoformat(),
        "ticker": ticker,
        "name": data.get("name"),
        "adjustment": "qfq",
        "frequency": "daily",
        "start_date": (date.today() - timedelta(days=lookback_days)).isoformat(),
        "end_date": today_iso(),
        "records": records,
        "record_count": len(records),
    }


def fetch_tencent_kline(ticker: str, *, lookback_days: int = 540) -> dict[str, Any]:
    symbol = _tencent_symbol(ticker)
    end = today_iso()
    start = (date.today() - timedelta(days=lookback_days)).isoformat()
    url = f"https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param={symbol},day,{start},{end},640,qfq"
    payload = _fetch_json(url, headers={"Referer": f"https://gu.qq.com/{symbol}/gp"})
    node = (payload.get("data") or {}).get(symbol) or {}
    rows = node.get("qfqday") or node.get("day") or []
    records = []
    for row in rows:
        if len(row) < 6:
            continue
        records.append(
            {
                "date": row[0],
                "open": _to_float(row[1]),
                "close": _to_float(row[2]),
                "high": _to_float(row[3]),
                "low": _to_float(row[4]),
                "volume": _to_float(row[5]),
                "amount": _to_float(row[6]) if len(row) > 6 else None,
                "pct_change": None,
                "turnover_rate": None,
            }
        )
    return {
        "source": "tencent_fqkline",
        "source_url": url,
        "retrieved_at": datetime.now().astimezone().isoformat(),
        "ticker": ticker,
        "provider_symbol": symbol,
        "adjustment": "qfq",
        "frequency": "daily",
        "start_date": start,
        "end_date": end,
        "records": records,
        "record_count": len(records),
    }


def fetch_benchmark_data(
    *,
    ticker: str,
    company_name: str,
    data_requests: list[dict[str, Any]],
    lookback_days: int = 540,
) -> dict[str, Any]:
    benchmarks = infer_benchmark_symbols(ticker=ticker, company_name=company_name, data_requests=data_requests)
    output: dict[str, Any] = {
        "benchmark_candidates": benchmarks,
        "market_index": None,
        "broad_index": None,
        "industry_index": None,
        "fetch_errors": [],
    }
    for key in ["market_index", "broad_index", "industry_index"]:
        spec = benchmarks.get(key)
        if not spec:
            continue
        try:
            series = fetch_price_history(spec["ticker"], lookback_days=lookback_days)
            series["name"] = spec.get("name")
            series["role"] = key
            output[key] = series
        except Exception as exc:  # noqa: BLE001
            output["fetch_errors"].append({"role": key, "ticker": spec.get("ticker"), "error": str(exc)})
    return output


def fetch_risk_free_rate() -> dict[str, Any]:
    try:
        import akshare as ak
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError("akshare is not installed; cannot fetch China government bond yield.") from exc

    start = (date.today() - timedelta(days=20)).strftime("%Y%m%d")
    try:
        df = ak.bond_zh_us_rate(start_date=start)
        if not df.empty and "中国国债收益率10年" in df.columns:
            cleaned = df.dropna(subset=["中国国债收益率10年"])
            if not cleaned.empty:
                row = cleaned.iloc[-1]
                value = _to_float(row.get("中国国债收益率10年"))
                if value is not None:
                    return {
                        "source": "akshare_bond_zh_us_rate",
                        "source_name": "Eastmoney China-US government bond yield dataset via AKShare",
                        "retrieved_at": datetime.now().astimezone().isoformat(),
                        "date": str(row.get("日期"))[:10],
                        "country": "China",
                        "tenor": "10Y",
                        "value_pct": value,
                        "value_decimal": round(value / 100, 6),
                        "confidence": "B",
                    }
    except Exception:
        pass

    end = date.today().strftime("%Y%m%d")
    df = ak.bond_china_yield(start_date=start, end_date=end)
    if df.empty:
        raise RuntimeError("AKShare returned no ChinaBond yield rows.")
    treasury_rows = df[df["曲线名称"].astype(str).str.contains("国债收益率曲线", na=False)]
    if treasury_rows.empty:
        raise RuntimeError("AKShare ChinaBond yield rows did not include treasury curve.")
    row = treasury_rows.dropna(subset=["10年"]).iloc[-1]
    value = _to_float(row.get("10年"))
    if value is None:
        raise RuntimeError("China 10Y yield value is empty.")
    return {
        "source": "akshare_bond_china_yield",
        "source_name": "ChinaBond yield curve via AKShare",
        "retrieved_at": datetime.now().astimezone().isoformat(),
        "date": str(row.get("日期"))[:10],
        "country": "China",
        "tenor": "10Y",
        "value_pct": value,
        "value_decimal": round(value / 100, 6),
        "confidence": "A-",
    }


def fetch_tushare_a_share_pack(ticker: str) -> dict[str, Any] | None:
    token = os.getenv("TUSHARE_TOKEN", "").strip()
    if not token or not ticker.upper().endswith((".SH", ".SZ", ".BJ")):
        return None
    try:
        import tushare as ts
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError("tushare is not installed. Run: python -m pip install tushare") from exc

    pro = ts.pro_api(token)
    ts_code = _tushare_ts_code(ticker)
    end_date = today_iso().replace("-", "")
    start_3y = (date.today() - timedelta(days=365 * 3)).strftime("%Y%m%d")
    start_5y = (date.today() - timedelta(days=365 * 5)).strftime("%Y%m%d")

    financials: dict[str, Any] = {
        "source": "tushare_pro",
        "retrieved_at": datetime.now().astimezone().isoformat(),
        "ticker": ticker,
        "ts_code": ts_code,
        "statements": {},
    }
    errors: list[dict[str, str]] = []

    statement_calls = {
        "income": lambda: pro.income(ts_code=ts_code, start_date=start_5y, end_date=end_date),
        "balancesheet": lambda: pro.balancesheet(ts_code=ts_code, start_date=start_5y, end_date=end_date),
        "cashflow": lambda: pro.cashflow(ts_code=ts_code, start_date=start_5y, end_date=end_date),
        "fina_indicator": lambda: pro.fina_indicator(ts_code=ts_code, start_date=start_5y, end_date=end_date),
        "fina_audit": lambda: pro.fina_audit(ts_code=ts_code, start_date=start_5y, end_date=end_date),
    }
    for name, call in statement_calls.items():
        try:
            financials["statements"][name] = _tushare_table(call(), source=f"tushare_{name}")
        except Exception as exc:  # noqa: BLE001
            errors.append({"source": name, "error": str(exc)})

    output: dict[str, Any] = {
        "source": "tushare_pro",
        "retrieved_at": datetime.now().astimezone().isoformat(),
        "ticker": ticker,
        "ts_code": ts_code,
        "financial_statements": financials,
        "daily_basic": None,
        "moneyflow": None,
        "dividend": None,
        "share_float": None,
        "holder_number": None,
        "errors": errors,
    }
    optional_calls = {
        "daily_basic": lambda: pro.daily_basic(ts_code=ts_code, start_date=start_3y, end_date=end_date),
        "moneyflow": lambda: pro.moneyflow(ts_code=ts_code, start_date=start_3y, end_date=end_date),
        "dividend": lambda: pro.dividend(ts_code=ts_code),
        "share_float": lambda: pro.share_float(ts_code=ts_code),
        "holder_number": lambda: pro.stk_holdernumber(ts_code=ts_code, start_date=start_5y, end_date=end_date),
    }
    for name, call in optional_calls.items():
        try:
            output[name] = _tushare_table(call(), source=f"tushare_{name}")
        except Exception as exc:  # noqa: BLE001
            output["errors"].append({"source": name, "error": str(exc)})
    return output


def fetch_announcements(ticker: str, *, page_size: int = 30) -> list[dict[str, Any]]:
    code = _ticker_code(ticker)
    url = (
        "https://np-anotice-stock.eastmoney.com/api/security/ann"
        f"?sr=-1&page_size={page_size}&page_index=1&ann_type=A&client_source=web&stock_list={code}"
    )
    payload = _fetch_json(url, headers={"Referer": "https://data.eastmoney.com/"})
    items = (payload.get("data") or {}).get("list") or []
    results = []
    for item in items:
        art_code = item.get("art_code")
        columns = item.get("columns") or []
        results.append(
            {
                "source": "eastmoney_announcements",
                "ticker": ticker,
                "title": item.get("title_ch") or item.get("title"),
                "notice_date": item.get("notice_date"),
                "display_time": item.get("display_time"),
                "art_code": art_code,
                "columns": [col.get("column_name") for col in columns if isinstance(col, dict)],
                "source_url": f"https://data.eastmoney.com/notices/detail/{code}/{art_code}.html" if art_code else None,
                "credibility": "B",
            }
        )
    return results


def fetch_financial_key_indicators(ticker: str) -> dict[str, Any]:
    em_code = _eastmoney_f10_code(ticker)
    url = f"https://emweb.securities.eastmoney.com/PC_HSF10/NewFinanceAnalysis/ZYZBAjaxNew?type=0&code={em_code}"
    payload = _fetch_json(url, headers={"Referer": "https://emweb.securities.eastmoney.com/"})
    rows = payload.get("data") or []
    return {
        "source": "eastmoney_f10_key_indicators",
        "source_url": url,
        "retrieved_at": datetime.now().astimezone().isoformat(),
        "ticker": ticker,
        "records": rows,
        "record_count": len(rows),
        "credibility": "B",
    }


def fetch_business_analysis(ticker: str) -> dict[str, Any]:
    em_code = _eastmoney_f10_code(ticker)
    url = f"https://emweb.securities.eastmoney.com/PC_HSF10/BusinessAnalysis/PageAjax?code={em_code}"
    payload = _fetch_json(url, headers={"Referer": "https://emweb.securities.eastmoney.com/"})
    scope_items = payload.get("zyfw") or []
    segment_items = payload.get("zygcfx") or []
    return {
        "source": "eastmoney_f10_business_analysis",
        "source_url": url,
        "retrieved_at": datetime.now().astimezone().isoformat(),
        "ticker": ticker,
        "business_scope": scope_items[0].get("BUSINESS_SCOPE") if scope_items else None,
        "segments": segment_items,
        "credibility": "B",
    }


def fetch_eastmoney_quote(ticker: str) -> dict[str, Any]:
    secid = _eastmoney_secid(ticker)
    fields = ",".join(
        [
            "f43",  # 最新价
            "f44",  # 最高
            "f45",  # 最低
            "f46",  # 今开
            "f47",  # 成交量
            "f48",  # 成交额
            "f57",  # 代码
            "f58",  # 名称
            "f60",  # 昨收
            "f116",  # 总市值
            "f117",  # 流通市值
            "f162",  # 市盈率动态
            "f167",  # 市净率
            "f168",  # 换手率
            "f169",  # 涨跌额
            "f170",  # 涨跌幅
            "f173",  # 东方财富字段含义随接口变化，保留原始值但不直接作为 pe_ttm
            "f9",  # 市盈率 TTM（常用行情页口径）
            "f115",  # 市盈率静态
        ]
    )
    url = f"https://push2.eastmoney.com/api/qt/stock/get?secid={secid}&fields={fields}"
    payload = _fetch_json(url)
    data = payload.get("data")
    if not data:
        raise RuntimeError(f"Eastmoney quote returned no data for {ticker}")
    return {
        "source": "eastmoney_push2",
        "source_url": url,
        "retrieved_at": datetime.now().astimezone().isoformat(),
        "ticker": ticker,
        "raw": data,
        "normalized": {
            "name": data.get("f58"),
            "code": data.get("f57"),
            "last_price": _scale_price(data.get("f43")),
            "previous_close": _scale_price(data.get("f60")),
            "open": _scale_price(data.get("f46")),
            "high": _scale_price(data.get("f44")),
            "low": _scale_price(data.get("f45")),
            "change": _scale_price(data.get("f169")),
            "change_pct": _scale_percent(data.get("f170")),
            "turnover_rate_pct": _scale_percent(data.get("f168")),
            "volume": data.get("f47"),
            "amount": data.get("f48"),
            "market_cap": data.get("f116"),
            "float_market_cap": data.get("f117"),
            "pe_dynamic": _scale_ratio(data.get("f162")),
            "pe_ttm": _scale_ratio(data.get("f9")),
            "pe_static": _scale_ratio(data.get("f115")),
            "pb": _scale_ratio(data.get("f167")),
            "eastmoney_f173_unmapped": _scale_ratio(data.get("f173")),
        },
    }


def fetch_tencent_quote(ticker: str) -> dict[str, Any]:
    symbol = _tencent_symbol(ticker)
    url = f"https://qt.gtimg.cn/q={symbol}"
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 api_workflow/1.0",
            "Referer": "https://gu.qq.com/",
        },
    )
    context = _ssl_context()
    with urllib.request.urlopen(request, timeout=20, context=context) as response:
        text = response.read().decode("gbk", errors="replace")
    if '="' not in text:
        raise RuntimeError(f"Tencent quote returned unexpected payload for {ticker}")
    body = text.split('="', 1)[1].rsplit('"', 1)[0]
    parts = body.split("~")
    if len(parts) < 40:
        raise RuntimeError(f"Tencent quote returned too few fields for {ticker}")
    current = _to_float(parts[3])
    previous_close = _to_float(parts[4])
    change = _to_float(parts[31]) if len(parts) > 31 else None
    change_pct = _to_float(parts[32]) if len(parts) > 32 else None
    return {
        "source": "tencent_quote",
        "source_url": url,
        "retrieved_at": datetime.now().astimezone().isoformat(),
        "ticker": ticker,
        "raw": {
            "payload": text[:1000],
        },
        "normalized": {
            "name": parts[1],
            "code": parts[2],
            "last_price": current,
            "previous_close": previous_close,
            "open": _to_float(parts[5]),
            "high": _to_float(parts[33]) if len(parts) > 33 else None,
            "low": _to_float(parts[34]) if len(parts) > 34 else None,
            "change": change,
            "change_pct": change_pct,
            "volume": _to_float(parts[6]),
            "amount": _to_float(parts[37]) if len(parts) > 37 else None,
            "quote_time": parts[30] if len(parts) > 30 else None,
        },
    }


def fetch_yahoo_quote(ticker: str) -> dict[str, Any]:
    symbol = _yahoo_symbol(ticker)
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(symbol)}?range=5d&interval=1d"
    payload = _fetch_json(url, headers={"Referer": "https://finance.yahoo.com/"})
    result = ((payload.get("chart") or {}).get("result") or [None])[0]
    if not result:
        raise RuntimeError(f"Yahoo chart returned no data for {ticker}")
    meta = result.get("meta") or {}
    indicators = ((result.get("indicators") or {}).get("quote") or [{}])[0]
    timestamps = result.get("timestamp") or []
    closes = indicators.get("close") or []
    previous_close = meta.get("chartPreviousClose")
    last_price = meta.get("regularMarketPrice")
    if last_price is None:
        numeric_closes = [_to_float(value) for value in closes]
        numeric_closes = [value for value in numeric_closes if value is not None]
        last_price = numeric_closes[-1] if numeric_closes else None
    quote_time = datetime.fromtimestamp(timestamps[-1]).astimezone().isoformat() if timestamps else None
    return {
        "source": "yahoo_chart",
        "source_url": url,
        "retrieved_at": datetime.now().astimezone().isoformat(),
        "ticker": ticker,
        "raw": {"meta": meta},
        "normalized": {
            "name": meta.get("shortName") or meta.get("longName") or symbol,
            "code": symbol,
            "currency": meta.get("currency"),
            "last_price": _to_float(last_price),
            "previous_close": _to_float(previous_close),
            "change": round(_to_float(last_price) - _to_float(previous_close), 6) if _to_float(last_price) is not None and _to_float(previous_close) is not None else None,
            "change_pct": round((_to_float(last_price) / _to_float(previous_close) - 1) * 100, 6) if _to_float(last_price) is not None and _to_float(previous_close) not in {None, 0} else None,
            "quote_time": quote_time,
        },
    }


def fetch_yahoo_kline(ticker: str, *, lookback_days: int = 540) -> dict[str, Any]:
    symbol = _yahoo_symbol(ticker)
    days = max(5, int(lookback_days))
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(symbol)}?range={days}d&interval=1d&events=history"
    payload = _fetch_json(url, headers={"Referer": "https://finance.yahoo.com/"})
    result = ((payload.get("chart") or {}).get("result") or [None])[0]
    if not result:
        raise RuntimeError(f"Yahoo chart returned no kline data for {ticker}")
    timestamps = result.get("timestamp") or []
    quote = ((result.get("indicators") or {}).get("quote") or [{}])[0]
    adjclose = (((result.get("indicators") or {}).get("adjclose") or [{}])[0]).get("adjclose") or []
    records: list[dict[str, Any]] = []
    for index, timestamp in enumerate(timestamps):
        try:
            day = datetime.fromtimestamp(timestamp).date().isoformat()
        except Exception:  # noqa: BLE001
            continue
        close = _to_float((quote.get("close") or [None])[index] if index < len(quote.get("close") or []) else None)
        if close is None:
            continue
        records.append(
            {
                "date": day,
                "open": _to_float((quote.get("open") or [None])[index] if index < len(quote.get("open") or []) else None),
                "high": _to_float((quote.get("high") or [None])[index] if index < len(quote.get("high") or []) else None),
                "low": _to_float((quote.get("low") or [None])[index] if index < len(quote.get("low") or []) else None),
                "close": close,
                "volume": _to_float((quote.get("volume") or [None])[index] if index < len(quote.get("volume") or []) else None),
                "adj_close": _to_float(adjclose[index] if index < len(adjclose) else None),
            }
        )
    return {
        "source": "yahoo_chart",
        "source_url": url,
        "retrieved_at": datetime.now().astimezone().isoformat(),
        "ticker": ticker,
        "records": records,
        "record_count": len(records),
        "adjustment": "Yahoo adjusted close included when available; OHLC are exchange daily bars.",
    }


def search_web(query: str, *, max_results: int | None = None) -> list[dict[str, Any]]:
    load_dotenv_if_present()
    normalized_query = " ".join(str(query).split())
    normalized_max_results = int(max_results) if max_results is not None else int(os.getenv("WEB_SEARCH_MAX_RESULTS", "5"))
    cache_key = f"{normalized_query}||{normalized_max_results}"
    with _SEARCH_CACHE_LOCK:
        cached = _SEARCH_CACHE.get(cache_key)
    if cached is not None:
        return list(cached)
    if _usable_key("TAVILY_API_KEY"):
        results = _search_tavily(normalized_query, max_results=normalized_max_results)
    elif _usable_key("BRAVE_SEARCH_API_KEY"):
        results = _search_brave(normalized_query, max_results=normalized_max_results)
    elif _usable_key("SERPAPI_API_KEY"):
        results = _search_serpapi(normalized_query, max_results=normalized_max_results)
    else:
        results = []
    with _SEARCH_CACHE_LOCK:
        _SEARCH_CACHE[cache_key] = list(results)
    return results


def search_key_status() -> dict[str, Any]:
    load_dotenv_if_present()
    providers = {
        "tavily": os.getenv("TAVILY_API_KEY", ""),
        "brave": os.getenv("BRAVE_SEARCH_API_KEY", ""),
        "serpapi": os.getenv("SERPAPI_API_KEY", ""),
    }
    configured = {
        name: {
            "present": bool(value),
            "looks_placeholder": _looks_placeholder(value),
            "usable": bool(value) and not _looks_placeholder(value),
        }
        for name, value in providers.items()
    }
    active_provider = next((name for name, info in configured.items() if info["usable"]), None)
    return {"active_provider": active_provider, "providers": configured}


def _search_tavily(query: str, *, max_results: int | None = None) -> list[dict[str, Any]]:
    payload = {
        "api_key": os.environ["TAVILY_API_KEY"],
        "query": query,
        "search_depth": "basic",
        "max_results": int(max_results) if max_results is not None else int(os.getenv("WEB_SEARCH_MAX_RESULTS", "5")),
        "include_answer": False,
        "include_raw_content": False,
    }
    data = _post_json("https://api.tavily.com/search", payload)
    return [
        {
            "title": item.get("title"),
            "url": item.get("url"),
            "content": item.get("content"),
            "score": item.get("score"),
            "source": "tavily",
        }
        for item in data.get("results", [])
    ]


def _usable_key(env_name: str) -> bool:
    value = os.getenv(env_name, "")
    return bool(value) and not _looks_placeholder(value)


def _looks_placeholder(value: str) -> bool:
    stripped = value.strip()
    return (
        not stripped
        or stripped.startswith("请把你的")
        or stripped.lower() in {"your_key_here", "your-api-key", "xxx", "placeholder"}
    )


def _search_brave(query: str, *, max_results: int | None = None) -> list[dict[str, Any]]:
    params = urllib.parse.urlencode(
        {"q": query, "count": str(int(max_results) if max_results is not None else int(os.getenv("WEB_SEARCH_MAX_RESULTS", "5")))}
    )
    url = f"https://api.search.brave.com/res/v1/web/search?{params}"
    data = _fetch_json(url, headers={"X-Subscription-Token": os.environ["BRAVE_SEARCH_API_KEY"]})
    results = data.get("web", {}).get("results", [])
    return [
        {
            "title": item.get("title"),
            "url": item.get("url"),
            "content": item.get("description"),
            "source": "brave",
        }
        for item in results
    ]


def _search_serpapi(query: str, *, max_results: int | None = None) -> list[dict[str, Any]]:
    params = urllib.parse.urlencode(
        {
            "engine": "google",
            "q": query,
            "api_key": os.environ["SERPAPI_API_KEY"],
            "num": str(int(max_results) if max_results is not None else int(os.getenv("WEB_SEARCH_MAX_RESULTS", "5"))),
        }
    )
    data = _fetch_json(f"https://serpapi.com/search.json?{params}")
    return [
        {
            "title": item.get("title"),
            "url": item.get("link"),
            "content": item.get("snippet"),
            "source": "serpapi",
        }
        for item in data.get("organic_results", [])
    ]


def _fetch_json(url: str, headers: dict[str, str] | None = None, timeout: int = 20) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 api_workflow/1.0",
            "Accept": "application/json,text/plain,*/*",
            "Referer": "https://quote.eastmoney.com/",
            **(headers or {}),
        },
    )
    context = _ssl_context()
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=timeout, context=context) as response:
                return json.loads(response.read().decode("utf-8", errors="replace"))
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            if attempt < 2:
                time.sleep(0.8 * (attempt + 1))
    raise RuntimeError(str(last_error)) from last_error


def _post_json(url: str, payload: dict[str, Any], timeout: int = 20) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 api_workflow/1.0",
        },
        method="POST",
    )
    context = _ssl_context()
    with urllib.request.urlopen(request, timeout=timeout, context=context) as response:
        return json.loads(response.read().decode("utf-8", errors="replace"))


def _ssl_context() -> ssl.SSLContext:
    no_verify = os.getenv("DEEPSEEK_SSL_NO_VERIFY", "").strip().lower()
    if no_verify in {"1", "true", "yes"}:
        return ssl._create_unverified_context()  # noqa: SLF001
    try:
        import certifi

        return ssl.create_default_context(cafile=certifi.where())
    except Exception:  # noqa: BLE001
        return ssl.create_default_context()


def _build_search_queries(
    company_name: str,
    ticker: str,
    user_input: str,
    data_requirement_summary: dict[str, Any] | None = None,
) -> list[str]:
    base = company_name or ticker or user_input
    queries = [
        f"{base} 最新 年报 季报 公告",
        f"{base} 当前股价 市值 PE PB",
        f"{base} 风险 消费税 批价 库存",
    ]
    search_plan = (data_requirement_summary or {}).get("search_plan", {})
    if isinstance(search_plan, dict):
        extra_queries = search_plan.get("queries", [])
        if isinstance(extra_queries, list):
            queries.extend(str(query) for query in extra_queries)
    priority_needs = (data_requirement_summary or {}).get("priority_data_needs", [])
    if isinstance(priority_needs, list):
        for need in priority_needs:
            if isinstance(need, dict):
                queries.extend(str(query) for query in need.get("suggested_search_queries", []))
    deduped: list[str] = []
    seen: set[str] = set()
    for query in queries:
        cleaned = " ".join(str(query).split())
        if cleaned and cleaned not in seen:
            deduped.append(cleaned)
            seen.add(cleaned)
    max_queries = int(os.getenv("WEB_SEARCH_MAX_QUERIES", str(COLLECTION_MODE_PRESETS["standard"]["web_search_max_queries"])))
    return deduped[:max_queries]


def normalize_data_requests(
    *,
    data_requirement_summary: dict[str, Any] | None,
    analyst_data_requests: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    requests_out: list[dict[str, Any]] = []
    priority_needs = (data_requirement_summary or {}).get("priority_data_needs", [])
    if isinstance(priority_needs, list):
        for need in priority_needs:
            if not isinstance(need, dict):
                continue
            item = str(need.get("item") or "").strip()
            if item:
                requests_out.append(
                    {
                        "data_type": classify_data_need(item),
                        "item": item,
                        "priority": need.get("priority", "medium"),
                        "requested_by": need.get("requested_by", []),
                        "preferred_sources": need.get("preferred_sources", []),
                        "suggested_search_queries": need.get("suggested_search_queries", []),
                        "reason": need.get("why_it_matters"),
                    }
                )
    for analyst, payload in (analyst_data_requests or {}).items():
        if not isinstance(payload, dict):
            continue
        for need in payload.get("required_data", []) or []:
            if not isinstance(need, dict):
                continue
            item = str(need.get("item") or "").strip()
            if item:
                requests_out.append(
                    {
                        "data_type": classify_data_need(item),
                        "item": item,
                        "priority": need.get("priority", "medium"),
                        "requested_by": [analyst],
                        "preferred_sources": need.get("preferred_sources", []),
                        "suggested_search_queries": need.get("suggested_search_queries", []),
                        "reason": need.get("reason"),
                    }
                )
    deduped: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for request in requests_out:
        key = (str(request.get("data_type")), str(request.get("item")))
        if key not in seen:
            deduped.append(request)
            seen.add(key)
    return deduped


def classify_data_need(text: str) -> str:
    lower = text.lower()
    rules = [
        ("kline", ["k线", "日k", "周k", "成交量", "成交额", "复权", "price volume"]),
        ("quote", ["当前股价", "市值", "股本", "pe", "pb", "股息率", "估值倍数"]),
        ("financials", ["年报", "季报", "利润表", "资产负债表", "现金流", "财报", "eps", "roe"]),
        ("filings", ["公告", "问询函", "业绩预告", "业绩快报", "分红", "回购", "增持", "减持"]),
        ("consensus", ["一致预期", "盈利预测", "目标价", "评级", "分析师"]),
        ("macro", ["无风险利率", "国债", "beta", "erp", "利率", "汇率"]),
        ("industry", ["行业", "市场规模", "产量", "库存", "供需", "产能", "政策"]),
        ("sentiment", ["股吧", "雪球", "舆情", "社交", "热度", "kol"]),
        ("company_specific", ["价格", "订单", "用户", "会员", "门店", "渠道", "ip", "批价", "直销"]),
    ]
    for data_type, keywords in rules:
        if any(keyword.lower() in lower for keyword in keywords):
            return data_type
    return "other"


def _extract_collection_queries(data_requirement_summary: dict[str, Any] | None) -> list[str]:
    queries: list[str] = []
    search_plan = (data_requirement_summary or {}).get("search_plan", {})
    if isinstance(search_plan, dict):
        queries.extend(str(query) for query in search_plan.get("queries", []) or [])
    for need in (data_requirement_summary or {}).get("priority_data_needs", []) or []:
        if isinstance(need, dict):
            queries.extend(str(query) for query in need.get("suggested_search_queries", []) or [])
    deduped: list[str] = []
    seen: set[str] = set()
    for query in queries:
        cleaned = " ".join(query.split())
        if cleaned and cleaned not in seen:
            deduped.append(cleaned)
            seen.add(cleaned)
    return deduped[:50]


def _sentiment_queries(company_name: str, ticker: str) -> list[str]:
    base = company_name or ticker
    if not base:
        return []
    return [
        f"{base} 股吧 最新",
        f"{base} 雪球 讨论",
        f"{base} 舆情 新闻 评论",
    ]


def infer_peer_candidates(
    *,
    company_name: str,
    ticker: str,
    data_requests: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    text = " ".join([company_name, ticker] + [str(item.get("item", "")) for item in data_requests])
    if any(keyword in text for keyword in ["茅台", "白酒", "飞天", "酱香"]):
        return [
            {"company_name": "五粮液", "ticker": "000858.SZ", "reason": "高端白酒可比公司"},
            {"company_name": "泸州老窖", "ticker": "000568.SZ", "reason": "高端白酒可比公司"},
            {"company_name": "山西汾酒", "ticker": "600809.SH", "reason": "白酒龙头可比公司"},
            {"company_name": "洋河股份", "ticker": "002304.SZ", "reason": "白酒可比公司"},
        ]
    if any(keyword.lower() in text.lower() for keyword in ["泡泡玛特", "pop mart", "9992", "盲盒", "潮玩"]):
        return [
            {"company_name": "名创优品", "ticker": "9896.HK", "reason": "潮流零售和IP消费相关可比"},
            {"company_name": "Funko", "ticker": "FNKO", "reason": "IP玩具收藏品可比"},
            {"company_name": "Sanrio", "ticker": "8136.JP", "reason": "IP授权和角色消费可比"},
        ]
    return []


def required_missing_from_pack(pack: dict[str, Any]) -> list[dict[str, Any]]:
    missing: list[dict[str, Any]] = []
    if not pack.get("market_data", {}).get("daily_kline"):
        missing.append(_missing("market_data", "daily_kline", "缺少日K线，技术面和事件窗口分析应降置信度"))
    if not pack.get("financial_statements", {}).get("key_indicators"):
        missing.append(_missing("financials", "key_indicators", "缺少结构化财务指标，财务质量和估值应降置信度"))
    if not pack.get("filings_and_announcements"):
        missing.append(_missing("filings", "announcements", "缺少公告列表，催化剂和事件时间线应降置信度"))
    if not pack.get("macro_inputs", {}).get("risk_free_rate"):
        missing.append(_missing("macro", "risk_free_rate", "暂未接入无风险利率源，DCF只能使用区间假设"))
    if not pack.get("macro_inputs", {}).get("beta"):
        missing.append(_missing("macro", "beta", "暂未计算Beta，WACC应降置信度"))
    return missing


def build_evidence_ledger(pack: dict[str, Any]) -> list[dict[str, Any]]:
    ledger: list[dict[str, Any]] = []
    quote = (pack.get("market_data") or {}).get("quote")
    if quote:
        normalized = quote.get("normalized", {})
        for key in ["last_price", "market_cap", "float_market_cap", "pe_dynamic", "pe_ttm", "pb"]:
            value = normalized.get(key)
            if value is not None:
                ledger.append(
                    {
                        "evidence_id": f"quote.{key}",
                        "fact": key,
                        "value": value,
                        "source_type": "market_api",
                        "source_name": quote.get("source"),
                        "source_url": quote.get("source_url"),
                        "retrieved_at": quote.get("retrieved_at"),
                        "confidence": "B",
                    }
                )
    kline = (pack.get("market_data") or {}).get("daily_kline")
    if kline:
        ledger.append(
            {
                "evidence_id": "market.daily_kline",
                "fact": "daily kline records",
                "value": kline.get("record_count"),
                "source_type": "market_api",
                "source_name": kline.get("source"),
                "source_url": kline.get("source_url"),
                "retrieved_at": kline.get("retrieved_at"),
                "confidence": "B",
            }
        )
    benchmarks = (pack.get("market_data") or {}).get("benchmark_data") or {}
    for role in ["market_index", "broad_index", "industry_index"]:
        series = benchmarks.get(role)
        if series:
            ledger.append(
                {
                    "evidence_id": f"benchmark.{role}",
                    "fact": f"{role} daily kline records",
                    "value": series.get("record_count"),
                    "source_type": "market_api",
                    "source_name": series.get("source"),
                    "source_url": series.get("source_url"),
                    "retrieved_at": series.get("retrieved_at"),
                    "confidence": "B",
                }
            )
    beta = (pack.get("macro_inputs") or {}).get("beta")
    if beta:
        ledger.append(
            {
                "evidence_id": "macro.beta",
                "fact": "calculated beta",
                "value": beta.get("beta"),
                "source_type": "derived_market_data",
                "source_name": beta.get("source"),
                "retrieved_at": pack.get("collection_time"),
                "confidence": "B" if beta.get("observations", 0) >= 120 else "C",
            }
        )
    risk_free_rate = (pack.get("macro_inputs") or {}).get("risk_free_rate")
    if risk_free_rate:
        ledger.append(
            {
                "evidence_id": "macro.risk_free_rate",
                "fact": "China 10Y government bond yield",
                "value": risk_free_rate.get("value_pct"),
                "source_type": "macro_api",
                "source_name": risk_free_rate.get("source"),
                "retrieved_at": risk_free_rate.get("retrieved_at"),
                "confidence": risk_free_rate.get("confidence", "B"),
            }
        )
    financials = (pack.get("financial_statements") or {}).get("key_indicators")
    if financials:
        ledger.append(
            {
                "evidence_id": "financials.key_indicators",
                "fact": "key financial indicator records",
                "value": financials.get("record_count"),
                "source_type": "financial_api",
                "source_name": financials.get("source"),
                "source_url": financials.get("source_url"),
                "retrieved_at": financials.get("retrieved_at"),
                "confidence": financials.get("credibility", "B"),
            }
        )
    tushare_financials = (pack.get("financial_statements") or {}).get("tushare")
    if tushare_financials:
        for name, table in (tushare_financials.get("statements") or {}).items():
            ledger.append(
                {
                    "evidence_id": f"financials.tushare.{name}",
                    "fact": f"Tushare {name} records",
                    "value": table.get("record_count"),
                    "source_type": "financial_api",
                    "source_name": table.get("source"),
                    "retrieved_at": table.get("retrieved_at"),
                    "confidence": "B",
                }
            )
    for index, announcement in enumerate(pack.get("filings_and_announcements") or []):
        ledger.append(
            {
                "evidence_id": f"announcement.{index + 1}",
                "fact": announcement.get("title"),
                "value": announcement.get("notice_date"),
                "source_type": "announcement_index",
                "source_name": announcement.get("source"),
                "source_url": announcement.get("source_url"),
                "retrieved_at": pack.get("collection_time"),
                "confidence": announcement.get("credibility", "B"),
            }
        )
    dynamic_research = pack.get("dynamic_research") or {}
    for index, doc in enumerate(dynamic_research.get("document_corpus") or []):
        ledger.append(
            {
                "evidence_id": f"dynamic_research.document.{index + 1}",
                "fact": doc.get("title"),
                "value": doc.get("url"),
                "source_type": "dynamic_document",
                "source_name": doc.get("document_type"),
                "source_url": doc.get("url"),
                "retrieved_at": doc.get("retrieved_at"),
                "confidence": "C",
            }
        )
    consensus_proxy = dynamic_research.get("consensus_proxy")
    if consensus_proxy:
        ledger.append(
            {
                "evidence_id": "dynamic_research.consensus_proxy",
                "fact": "consensus proxy from research report/webpage extraction",
                "value": consensus_proxy.get("target_price_median"),
                "source_type": "derived_research_proxy",
                "source_name": consensus_proxy.get("source"),
                "retrieved_at": pack.get("collection_time"),
                "confidence": consensus_proxy.get("confidence", "C"),
            }
        )
    user_materials = pack.get("user_materials") or {}
    for index, file_info in enumerate(user_materials.get("files") or []):
        ledger.append(
            {
                "evidence_id": f"user_material.file.{index + 1}",
                "fact": file_info.get("name"),
                "value": file_info.get("path"),
                "source_type": "user_material",
                "source_name": file_info.get("parser"),
                "retrieved_at": file_info.get("parsed_at"),
                "confidence": "B",
            }
        )
    valuation = (pack.get("valuation_data") or {}).get("snapshot")
    if valuation:
        for key in ["pe_ttm", "pe_dynamic", "pb", "market_cap"]:
            if valuation.get(key) is not None:
                ledger.append(
                    {
                        "evidence_id": f"valuation.{key}",
                        "fact": key,
                        "value": valuation.get(key),
                        "source_type": "derived_quote_snapshot",
                        "source_name": valuation.get("source"),
                        "retrieved_at": valuation.get("retrieved_at"),
                        "confidence": "B",
                    }
                )
    return ledger


def score_research_pack(pack: dict[str, Any]) -> dict[str, Any]:
    benchmarks = (pack.get("market_data") or {}).get("benchmark_data") or {}
    checks = {
        "quote": bool((pack.get("market_data") or {}).get("quote")),
        "daily_kline": bool((pack.get("market_data") or {}).get("daily_kline")),
        "market_index_kline": bool(benchmarks.get("market_index")),
        "industry_or_broad_index_kline": bool(benchmarks.get("industry_index") or benchmarks.get("broad_index")),
        "financial_key_indicators": bool((pack.get("financial_statements") or {}).get("key_indicators")),
        "tushare_structured_financials": bool((pack.get("financial_statements") or {}).get("tushare")),
        "tushare_daily_basic": bool((pack.get("market_data") or {}).get("daily_basic")),
        "capital_actions": bool((pack.get("capital_actions") or {}).get("dividend")),
        "announcements": bool(pack.get("filings_and_announcements")),
        "business_segments": bool((pack.get("company_profile") or {}).get("business_segments")),
        "beta": bool((pack.get("macro_inputs") or {}).get("beta")),
        "risk_free_rate": bool((pack.get("macro_inputs") or {}).get("risk_free_rate")),
        "peer_quotes": bool((pack.get("market_data") or {}).get("peer_quotes")),
        "dynamic_research_documents": bool((pack.get("dynamic_research") or {}).get("document_corpus")),
        "consensus_proxy": bool((pack.get("dynamic_research") or {}).get("consensus_proxy")),
        "user_materials": bool((pack.get("user_materials") or {}).get("files")),
        "event_timeline": bool((pack.get("event_timeline") or {}).get("events")),
        "valuation_snapshot": bool((pack.get("valuation_data") or {}).get("snapshot")),
        "sentiment_samples": bool((pack.get("sentiment_data") or {}).get("samples")),
        "analyst_data_delivery": bool(pack.get("analyst_data_delivery")),
    }
    weights = {
        "quote": 2.0,
        "daily_kline": 2.0,
        "market_index_kline": 1.0,
        "industry_or_broad_index_kline": 1.0,
        "financial_key_indicators": 2.0,
        "tushare_structured_financials": 2.5,
        "tushare_daily_basic": 1.0,
        "capital_actions": 0.5,
        "announcements": 2.0,
        "business_segments": 1.0,
        "beta": 0.5,
        "risk_free_rate": 1.0,
        "peer_quotes": 1.0,
        "dynamic_research_documents": 0.5,
        "consensus_proxy": 0.5,
        "user_materials": 0.5,
        "event_timeline": 1.5,
        "valuation_snapshot": 1.5,
        "sentiment_samples": 0.5,
        "analyst_data_delivery": 0.5,
    }
    score = sum(1 for value in checks.values() if value)
    total = len(checks)
    weighted_score = sum(weight for key, weight in weights.items() if checks.get(key))
    weighted_total = sum(weights.values())
    critical_checks = {
        "core_market": checks["quote"] and checks["daily_kline"],
        "core_financials": checks["financial_key_indicators"],
        "core_filings": checks["announcements"] and checks["event_timeline"],
        "valuation_context": checks["valuation_snapshot"] and checks["risk_free_rate"],
    }
    critical_coverage = sum(1 for value in critical_checks.values() if value)
    has_full_financial_depth = checks["tushare_structured_financials"]
    has_key_financial_depth = checks["financial_key_indicators"]
    has_sentiment_depth = len(((pack.get("sentiment_data") or {}).get("samples") or [])) >= 3
    missing_data = pack.get("missing_data") or []
    missing_fields = {str(item.get("field") or "") for item in missing_data if isinstance(item, dict)}
    quality_warnings: list[str] = []
    if not has_full_financial_depth:
        quality_warnings.append("Structured financial statements are missing, which limits DCF and deep financial-quality work.")
    if has_key_financial_depth and not has_full_financial_depth:
        quality_warnings.append("Core financial indicators are available, but full statement granularity is still incomplete.")
    if not has_sentiment_depth:
        quality_warnings.append("Sentiment samples are sparse or low-depth; sentiment conclusions should be down-weighted.")
    if "quote" in missing_fields or "daily_kline" in missing_fields:
        quality_warnings.append("Primary market data has explicit collection gaps.")
    if "announcements" in missing_fields:
        quality_warnings.append("Announcement collection is incomplete or unavailable.")
    weighted_ratio = round(weighted_score / weighted_total, 4) if weighted_total else 0.0
    if critical_coverage <= 1:
        rating = "insufficient"
    elif critical_coverage == 2 or weighted_ratio < 0.45:
        rating = "low"
    elif critical_coverage == 3 or weighted_ratio < 0.72 or not has_full_financial_depth:
        rating = "medium"
    else:
        rating = "high"
    if has_full_financial_depth:
        financial_statement_completeness = "high"
        financial_modeling_readiness = "strong"
    elif has_key_financial_depth:
        financial_statement_completeness = "partial"
        financial_modeling_readiness = "moderate"
    else:
        financial_statement_completeness = "limited"
        financial_modeling_readiness = "weak"
    source_confidence = "high" if critical_coverage >= 3 else "medium" if critical_coverage == 2 else "low"
    return {
        "rating": rating,
        "score": score,
        "total": total,
        "checks": checks,
        "weighted_score": round(weighted_score, 2),
        "weighted_total": round(weighted_total, 2),
        "weighted_ratio": weighted_ratio,
        "critical_checks": critical_checks,
        "critical_coverage": critical_coverage,
        "financial_depth": "high" if has_full_financial_depth else "partial",
        "financial_source_confidence": "high" if has_key_financial_depth else "low",
        "financial_statement_completeness": financial_statement_completeness,
        "financial_modeling_readiness": financial_modeling_readiness,
        "source_confidence": source_confidence,
        "sentiment_depth": "adequate" if has_sentiment_depth else "thin",
        "quality_warnings": quality_warnings,
    }


def _missing(category: str, field: str, reason: str) -> dict[str, Any]:
    return {"category": category, "field": field, "reason": reason}


def _tushare_ts_code(ticker: str) -> str:
    normalized = ticker.upper().strip()
    if "." not in normalized and re.fullmatch(r"\d{6}", normalized):
        normalized = f"{normalized}.SH" if normalized.startswith("6") else f"{normalized}.SZ"
    return normalized


def _tushare_table(df: Any, *, source: str) -> dict[str, Any]:
    if df is None:
        records: list[dict[str, Any]] = []
        columns: list[str] = []
    else:
        columns = [str(col) for col in getattr(df, "columns", [])]
        records = json.loads(df.where(df.notna(), None).to_json(orient="records", force_ascii=False))
    return {
        "source": source,
        "retrieved_at": datetime.now().astimezone().isoformat(),
        "columns": columns,
        "records": records,
        "record_count": len(records),
    }


def infer_benchmark_symbols(
    *,
    ticker: str,
    company_name: str,
    data_requests: list[dict[str, Any]],
) -> dict[str, dict[str, str]]:
    text = " ".join([company_name, ticker] + [str(item.get("item", "")) for item in data_requests]).lower()
    normalized = ticker.upper().strip()
    if normalized.endswith((".SH", ".SZ", ".BJ")):
        result = {
            "market_index": {"name": "CSI 300", "ticker": "000300.SH"},
            "broad_index": {"name": "SSE Composite", "ticker": "000001.SH"},
        }
        if normalized.endswith("600519.SH") or any(keyword in text for keyword in ["moutai", "maotai", "baijiu", "\u8305\u53f0", "\u767d\u9152", "\u98de\u5929", "\u9171\u9999"]):
            result["industry_index"] = {"name": "CSI Liquor", "ticker": "399997.SZ"}
        return result
    if normalized.endswith(".HK") or re.fullmatch(r"\d{5}\.HK", normalized):
        return {
            "market_index": {"name": "Hang Seng Index", "ticker": "800000.HK"},
            "broad_index": {"name": "Hang Seng Composite Index", "ticker": "800100.HK"},
        }
    if normalized and not re.fullmatch(r"\d", normalized):
        return {
            "market_index": {"name": "S&P 500", "ticker": "SPY"},
            "broad_index": {"name": "NASDAQ 100", "ticker": "QQQ"},
        }
    return {}


def calculate_beta(stock_kline: dict[str, Any], benchmark_kline: dict[str, Any], *, benchmark_name: str) -> dict[str, Any]:
    stock_returns = _returns_by_date(stock_kline.get("records") or [])
    benchmark_returns = _returns_by_date(benchmark_kline.get("records") or [])
    common_dates = sorted(set(stock_returns) & set(benchmark_returns))
    pairs = [(stock_returns[day], benchmark_returns[day]) for day in common_dates]
    pairs = [(stock_return, benchmark_return) for stock_return, benchmark_return in pairs if benchmark_return is not None and stock_return is not None]
    if len(pairs) < 30:
        return {
            "source": "calculated_from_daily_kline",
            "benchmark": benchmark_name,
            "beta": None,
            "observations": len(pairs),
            "quality": "insufficient",
            "reason": "Need at least 30 overlapping daily return observations.",
        }
    stock_values = [pair[0] for pair in pairs]
    benchmark_values = [pair[1] for pair in pairs]
    stock_mean = sum(stock_values) / len(stock_values)
    benchmark_mean = sum(benchmark_values) / len(benchmark_values)
    covariance = sum((stock - stock_mean) * (benchmark - benchmark_mean) for stock, benchmark in pairs)
    variance = sum((benchmark - benchmark_mean) ** 2 for benchmark in benchmark_values)
    beta = covariance / variance if variance else None
    correlation = _correlation(stock_values, benchmark_values)
    return {
        "source": "calculated_from_daily_kline",
        "benchmark": benchmark_name,
        "beta": round(beta, 4) if beta is not None else None,
        "correlation": round(correlation, 4) if correlation is not None else None,
        "observations": len(pairs),
        "start_date": common_dates[0] if common_dates else None,
        "end_date": common_dates[-1] if common_dates else None,
        "frequency": "daily",
        "quality": "high" if len(pairs) >= 180 else "medium",
        "note": "Beta is calculated from overlapping daily close-to-close returns.",
    }


def _returns_by_date(records: list[dict[str, Any]]) -> dict[str, float]:
    ordered = sorted(
        [record for record in records if record.get("date") and _to_float(record.get("close"))],
        key=lambda item: str(item.get("date")),
    )
    output: dict[str, float] = {}
    previous_close: float | None = None
    for record in ordered:
        close = _to_float(record.get("close"))
        if close is None:
            continue
        if previous_close and previous_close != 0:
            output[str(record.get("date"))] = close / previous_close - 1
        previous_close = close
    return output


def _correlation(left: list[float], right: list[float]) -> float | None:
    if len(left) != len(right) or len(left) < 2:
        return None
    left_mean = sum(left) / len(left)
    right_mean = sum(right) / len(right)
    numerator = sum((x - left_mean) * (y - right_mean) for x, y in zip(left, right))
    left_var = sum((x - left_mean) ** 2 for x in left)
    right_var = sum((y - right_mean) ** 2 for y in right)
    denominator = (left_var * right_var) ** 0.5
    if denominator == 0:
        return None
    return numerator / denominator


def _ticker_code(ticker: str) -> str:
    normalized = ticker.upper().strip()
    if "." in normalized:
        return normalized.split(".", 1)[0]
    return normalized


def _eastmoney_f10_code(ticker: str) -> str:
    normalized = ticker.upper().strip()
    if "." not in normalized and re.fullmatch(r"\d{6}", normalized):
        normalized = f"{normalized}.SH" if normalized.startswith("6") else f"{normalized}.SZ"
    code, exchange = normalized.split(".", 1)
    prefix = {"SH": "SH", "SZ": "SZ", "BJ": "BJ"}.get(exchange, exchange)
    return f"{prefix}{code}"


def _futu_symbol(ticker: str) -> str:
    normalized = ticker.upper().strip()
    if re.fullmatch(r"\d{5}\.HK", normalized):
        code, _ = normalized.split(".", 1)
        return f"HK.{code}"
    if "." not in normalized:
        if re.fullmatch(r"\d{6}", normalized):
            return f"SH.{normalized}" if normalized.startswith("6") else f"SZ.{normalized}"
        return f"US.{normalized}"
    code, exchange = normalized.split(".", 1)
    if exchange == "SH":
        return f"SH.{code}"
    if exchange == "SZ":
        return f"SZ.{code}"
    if exchange == "HK":
        return f"HK.{code.zfill(5)}"
    return f"US.{code}"


def _env_truthy(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes", "on"}


def _package_available(name: str) -> bool:
    try:
        __import__(name)
        return True
    except Exception:  # noqa: BLE001
        return False


def _futu_should_use() -> bool:
    if _env_truthy("FUTU_DISABLED"):
        return False
    if _env_truthy("FUTU_ENABLED") or bool(os.getenv("FUTU_OPEND_HOST")):
        return True
    return False


def _is_a_share_ticker(ticker: str) -> bool:
    normalized = ticker.upper().strip()
    return bool(re.fullmatch(r"\d{6}(?:\.(?:SH|SZ|BJ))?", normalized))


def _extract_ticker(text: str) -> str | None:
    match = re.search(r"\b(\d{6}\.(?:SH|SZ|BJ)|\d{4,5}\.HK|[A-Z]{1,5}(?:\.[A-Z]{1,3})?)\b", text, flags=re.IGNORECASE)
    if match:
        value = match.group(1).upper()
        if re.fullmatch(r"\d{6}", value):
            suffix = "SH" if value.startswith("6") else "SZ"
            return f"{value}.{suffix}"
        if re.fullmatch(r"\d{4}\.HK", value):
            code, exchange = value.split(".", 1)
            return f"{code.zfill(5)}.{exchange}"
        return value
    match = re.search(r"\b(\d{6})\b", text)
    if match:
        code = match.group(1)
        suffix = "SH" if code.startswith("6") else "SZ"
        return f"{code}.{suffix}"
    return None


def _yahoo_symbol(ticker: str) -> str:
    normalized = ticker.upper().strip()
    if re.fullmatch(r"\d{4,5}\.HK", normalized):
        code, _ = normalized.split(".", 1)
        return f"{code[-4:].zfill(4)}.HK"
    if re.fullmatch(r"\d{6}\.SH", normalized):
        return normalized.replace(".SH", ".SS")
    if re.fullmatch(r"\d{6}\.SZ", normalized):
        return normalized
    return normalized


def _eastmoney_secid(ticker: str) -> str:
    normalized = ticker.upper().strip()
    if "." not in normalized and re.fullmatch(r"\d{6}", normalized):
        normalized = f"{normalized}.SH" if normalized.startswith("6") else f"{normalized}.SZ"
    code, exchange = normalized.split(".", 1)
    market_id = "1" if exchange == "SH" else "0"
    return f"{market_id}.{code}"


def _tencent_symbol(ticker: str) -> str:
    normalized = ticker.upper().strip()
    if "." not in normalized and re.fullmatch(r"\d{6}", normalized):
        normalized = f"{normalized}.SH" if normalized.startswith("6") else f"{normalized}.SZ"
    code, exchange = normalized.split(".", 1)
    prefix = "sh" if exchange == "SH" else "sz"
    return f"{prefix}{code}"


def _to_float(value: Any) -> float | None:
    try:
        if value in {None, "-", ""}:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _scale_price(value: Any) -> float | None:
    return _scale(value, 100)


def _scale_percent(value: Any) -> float | None:
    return _scale(value, 100)


def _scale_ratio(value: Any) -> float | None:
    return _scale(value, 100)


def _scale(value: Any, divisor: int) -> float | None:
    try:
        if value in {None, "-", ""}:
            return None
        return round(float(value) / divisor, 4)
    except (TypeError, ValueError):
        return None


# The project has some legacy mojibake strings in earlier helper definitions.
# Keep ASCII-safe overrides last so runtime classification does not depend on
# source-file display encoding.
def _fetch_json(url: str, headers: dict[str, str] | None = None, timeout: int = 20) -> dict[str, Any]:
    merged_headers = {
        "User-Agent": "Mozilla/5.0 api_workflow/1.0",
        "Accept": "application/json,text/plain,*/*",
        "Referer": "https://quote.eastmoney.com/",
        **(headers or {}),
    }
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            request = urllib.request.Request(url, headers=merged_headers)
            context = ssl.create_default_context()
            with urllib.request.urlopen(request, timeout=timeout, context=context) as response:
                charset = response.headers.get_content_charset() or "utf-8"
                return json.loads(response.read().decode(charset, errors="replace"))
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            if attempt < 2:
                time.sleep(0.8 * (attempt + 1))
    raise RuntimeError(str(last_error))


def provider_status() -> dict[str, Any]:
    return {
        "search": search_key_status(),
        "futu": {
            "enabled": _futu_should_use(),
            "host": os.getenv("FUTU_OPEND_HOST", "127.0.0.1"),
            "port": int(os.getenv("FUTU_OPEND_PORT", "11111")),
            "python_package": _package_available("futu"),
            "setup_note": "Install futu-api and start Futu OpenD, then set FUTU_ENABLED=1 to use it as the preferred quote/K-line source.",
        },
        "eastmoney": {"enabled": True, "requires_key": False},
        "tencent_quote": {"enabled": True, "requires_key": False},
        "akshare": {
            "enabled": _package_available("akshare"),
            "requires_key": False,
            "use": "Risk-free-rate proxies and public China macro/market datasets where available.",
        },
        "tushare": {
            "enabled": bool(os.getenv("TUSHARE_TOKEN", "").strip()) and _package_available("tushare"),
            "requires_key": True,
            "python_package": _package_available("tushare"),
            "token_configured": bool(os.getenv("TUSHARE_TOKEN", "").strip()),
            "use": "A-share structured financial statements, daily valuation basics, money flow, dividends, share float, holder count.",
        },
        "document_parsing": {
            "pdf": _package_available("pypdf"),
            "pdf_tables": _package_available("pdfplumber"),
            "html": _package_available("bs4"),
            "html_tables": _package_available("pandas"),
            "csv": True,
            "excel": _package_available("pandas"),
            "json": True,
            "text": True,
            "use": "Dynamic report/PDF/HTML extraction plus local user CSV/Excel/JSON/PDF/HTML/text materials.",
        },
        "paid_or_key_sources": [
            {"name": "Tushare Pro", "env": "TUSHARE_TOKEN", "use": "A-share financials, market data, macro data, money flow"},
            {"name": "Wind/Choice/iFinD", "env": "manual_or_enterprise", "use": "consensus estimates, industry datasets, historical valuation percentiles"},
            {"name": "FMP/AlphaVantage/IEX", "env": "vendor_specific", "use": "US/global financials, quote, estimates"},
        ],
    }


def classify_data_need(text: str) -> str:
    lower = text.lower()
    rules = [
        ("kline", ["kline", "k-line", "ohlcv", "daily bar", "\u65e5k", "\u5468k", "\u6210\u4ea4\u91cf", "\u6210\u4ea4\u989d", "\u590d\u6743", "price volume"]),
        ("quote", ["quote", "market cap", "share count", "valuation", "ev/ebitda", "\u5f53\u524d\u80a1\u4ef7", "\u80a1\u4ef7", "\u5e02\u503c", "\u80a1\u672c", "pe", "pb", "\u80a1\u606f\u7387", "\u4f30\u503c\u500d\u6570"]),
        ("financials", ["financial", "annual report", "quarterly report", "\u5e74\u62a5", "\u5b63\u62a5", "\u5229\u6da6\u8868", "\u8d44\u4ea7\u8d1f\u503a\u8868", "\u73b0\u91d1\u6d41", "\u8d22\u62a5", "eps", "roe"]),
        ("filings", ["filing", "announcement", "event", "catalyst", "\u516c\u544a", "\u4e8b\u4ef6", "\u50ac\u5316", "\u95ee\u8be2\u51fd", "\u4e1a\u7ee9\u9884\u544a", "\u4e1a\u7ee9\u5feb\u62a5", "\u5206\u7ea2", "\u56de\u8d2d", "\u589e\u6301", "\u51cf\u6301"]),
        ("consensus", ["consensus", "estimate", "target price", "\u4e00\u81f4\u9884\u671f", "\u76c8\u5229\u9884\u6d4b", "\u76ee\u6807\u4ef7", "\u8bc4\u7ea7", "\u5206\u6790\u5e08"]),
        ("macro", ["risk free", "treasury", "beta", "erp", "\u65e0\u98ce\u9669\u5229\u7387", "\u56fd\u503a", "\u5229\u7387", "\u6c47\u7387"]),
        ("industry", ["industry", "market size", "inventory", "capacity", "policy", "\u884c\u4e1a", "\u5e02\u573a\u89c4\u6a21", "\u4ea7\u91cf", "\u5e93\u5b58", "\u4f9b\u9700", "\u4ea7\u80fd", "\u653f\u7b56"]),
        ("sentiment", ["sentiment", "forum", "social", "kol", "\u80a1\u5427", "\u96ea\u7403", "\u8206\u60c5", "\u793e\u4ea4", "\u70ed\u5ea6"]),
        ("company_specific", ["sku", "gmv", "asp", "order", "member", "store", "channel", "ip", "\u4ef7\u683c", "\u8ba2\u5355", "\u7528\u6237", "\u4f1a\u5458", "\u95e8\u5e97", "\u6e20\u9053", "\u6279\u4ef7", "\u76f4\u9500", "\u76f2\u76d2", "\u6f6e\u73a9", "\u73a9\u5177"]),
    ]
    for data_type, keywords in rules:
        if any(keyword.lower() in lower for keyword in keywords):
            return data_type
    return "other"


def _sentiment_queries(company_name: str, ticker: str) -> list[str]:
    base = company_name or ticker
    if not base:
        return []
    return [
        f"{base} stock forum latest",
        f"{base} sentiment news comments",
        f"{base} \u80a1\u5427 \u96ea\u7403 \u8ba8\u8bba",
    ]


def infer_peer_candidates(
    *,
    company_name: str,
    ticker: str,
    data_requests: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    text = " ".join([company_name, ticker] + [str(item.get("item", "")) for item in data_requests]).lower()
    if ticker.upper().endswith("600519.SH") or any(keyword in text for keyword in ["moutai", "maotai", "baijiu", "\u8305\u53f0", "\u767d\u9152", "\u98de\u5929", "\u9171\u9999"]):
        return [
            {"company_name": "Wuliangye", "ticker": "000858.SZ", "reason": "High-end baijiu peer"},
            {"company_name": "Luzhou Laojiao", "ticker": "000568.SZ", "reason": "High-end baijiu peer"},
            {"company_name": "Shanxi Fenjiu", "ticker": "600809.SH", "reason": "Leading baijiu peer"},
            {"company_name": "Yanghe", "ticker": "002304.SZ", "reason": "Baijiu peer"},
        ]
    if ticker.upper().startswith("9992") or any(keyword in text for keyword in ["pop mart", "popmart", "blind box", "designer toy", "collectible toy", "\u6ce1\u6ce1\u739b\u7279", "\u76f2\u76d2", "\u6f6e\u73a9", "\u73a9\u5177"]):
        return [
            {"company_name": "Miniso", "ticker": "9896.HK", "reason": "IP retail and consumer products peer"},
            {"company_name": "Funko", "ticker": "FNKO", "reason": "Collectible toy and IP products peer"},
            {"company_name": "Sanrio", "ticker": "8136.JP", "reason": "Character IP licensing and consumer products peer"},
        ]
    return []
