from __future__ import annotations

import json
from typing import Any

from .analysts import AnalystNode, load_analyst_context, load_global_context


GLOBAL_CONTEXT = load_global_context()


def _compact_for_prompt(value: Any, *, max_text_chars: int = 1200, max_items: int = 8, depth: int = 0) -> Any:
    if depth >= 5:
        if isinstance(value, dict):
            return {"_truncated": True, "keys": list(value.keys())[:max_items]}
        if isinstance(value, list):
            return {"_truncated": True, "items": len(value)}
        if isinstance(value, str):
            return value[:max_text_chars]
        return value
    if isinstance(value, dict):
        compact: dict[str, Any] = {}
        for index, (key, item) in enumerate(value.items()):
            if index >= max_items:
                compact["_truncated_keys"] = len(value) - max_items
                break
            if key in {"raw", "payload"}:
                continue
            if key in {"text_excerpt", "table_text_excerpt", "content", "search_content", "raw_text"} and isinstance(item, str):
                compact[key] = item[:max_text_chars]
            else:
                compact[key] = _compact_for_prompt(item, max_text_chars=max_text_chars, max_items=max_items, depth=depth + 1)
        return compact
    if isinstance(value, list):
        compact_list = [
            _compact_for_prompt(item, max_text_chars=max_text_chars, max_items=max_items, depth=depth + 1)
            for item in value[:max_items]
        ]
        if len(value) > max_items:
            compact_list.append({"_truncated_items": len(value) - max_items})
        return compact_list
    if isinstance(value, str):
        return value[:max_text_chars]
    return value


def compact_external_data_for_prompt(external_data: dict[str, Any] | None) -> dict[str, Any]:
    if not external_data:
        return {}
    node_summary = external_data.get("node_data_summary")
    compact = {
        "collection_time": external_data.get("collection_time"),
        "ticker": external_data.get("ticker"),
        "company_name": external_data.get("company_name"),
        "node_data_summary": node_summary,
        "queries_executed": external_data.get("queries_executed"),
        "quote_snapshot": external_data.get("quote_snapshot"),
        "errors": external_data.get("errors"),
        "notes": external_data.get("notes"),
    }
    research_pack = external_data.get("research_data_pack") or {}
    if node_summary:
        compact["research_data_pack"] = {
            "missing_data": _compact_for_prompt(research_pack.get("missing_data")),
            "fetch_errors": _compact_for_prompt(research_pack.get("fetch_errors")),
            "data_quality_score": research_pack.get("data_quality_score"),
            "provider_status": research_pack.get("provider_status"),
            "evidence_ledger": _compact_for_prompt(research_pack.get("evidence_ledger"), max_items=12),
        }
        return _compact_for_prompt(compact, max_text_chars=1000, max_items=10)
    compact["research_data_pack"] = {
        "company_profile": research_pack.get("company_profile"),
        "market_data": {
            "quote": (research_pack.get("market_data") or {}).get("quote"),
            "daily_kline": _compact_for_prompt((research_pack.get("market_data") or {}).get("daily_kline")),
            "benchmark_data": _compact_for_prompt((research_pack.get("market_data") or {}).get("benchmark_data")),
            "peer_quotes": _compact_for_prompt((research_pack.get("market_data") or {}).get("peer_quotes")),
        },
        "financial_statements": _compact_for_prompt(research_pack.get("financial_statements")),
        "filings_and_announcements": _compact_for_prompt(research_pack.get("filings_and_announcements")),
        "peer_table": _compact_for_prompt(research_pack.get("peer_table")),
        "industry_data": _compact_for_prompt(research_pack.get("industry_data")),
        "company_specific_data": _compact_for_prompt(research_pack.get("company_specific_data")),
        "user_materials": _compact_for_prompt(research_pack.get("user_materials")),
        "dynamic_research": _compact_for_prompt(research_pack.get("dynamic_research")),
        "macro_inputs": _compact_for_prompt(research_pack.get("macro_inputs")),
        "sentiment_data": _compact_for_prompt(research_pack.get("sentiment_data")),
        "event_timeline": _compact_for_prompt(research_pack.get("event_timeline")),
        "valuation_data": _compact_for_prompt(research_pack.get("valuation_data")),
        "analyst_data_delivery": _compact_for_prompt(research_pack.get("analyst_data_delivery")),
        "data_need_coverage": _compact_for_prompt(research_pack.get("data_need_coverage")),
        "missing_data": _compact_for_prompt(research_pack.get("missing_data")),
        "fetch_errors": _compact_for_prompt(research_pack.get("fetch_errors")),
        "data_quality_score": research_pack.get("data_quality_score"),
        "provider_status": research_pack.get("provider_status"),
        "evidence_ledger": _compact_for_prompt(research_pack.get("evidence_ledger")),
    }
    return _compact_for_prompt(compact, max_text_chars=1000, max_items=8)


def compact_upstream_outputs_for_prompt(upstream_outputs: dict[str, Any]) -> dict[str, Any]:
    compact: dict[str, Any] = {}
    for key, value in upstream_outputs.items():
        if key in {"external_data"}:
            continue
        if key in {"01_task_definition", "02_data_requirement_summary", "analyst_data_requests"}:
            compact[key] = _compact_for_prompt(value, max_text_chars=700, max_items=8)
        elif isinstance(value, dict):
            compact[key] = _compact_analyst_output(value)
        else:
            compact[key] = _compact_for_prompt(value, max_text_chars=700, max_items=6)
    return compact


def _compact_analyst_output(output: dict[str, Any]) -> dict[str, Any]:
    preferred_keys = [
        "analyst",
        "company",
        "company_identification",
        "data_quality",
        "data_completeness",
        "confidence",
        "confidence_level",
        "confidence_summary",
        "high_confidence_facts",
        "medium_low_confidence_claims",
        "contradictions",
        "valuation_variables",
        "executive_conclusion",
        "overall_recommendation",
        "one_sentence_view",
        "summary",
        "key_findings",
        "core_conclusion",
        "guidance_for_master_director",
        "handoff_to_master",
        "handoff_to_downstream",
        "missing_information",
    ]
    compact: dict[str, Any] = {}
    for key in preferred_keys:
        if key in output:
            compact[key] = _compact_for_prompt(output[key], max_text_chars=700, max_items=6)
    if not compact:
        compact = _compact_for_prompt(output, max_text_chars=700, max_items=6)
    return compact


def build_system_prompt(node: AnalystNode, *, final_node: bool = False) -> str:
    role_context = load_analyst_context(node)
    final_rule = (
        "你是最终总控综合节点，可以给出最终买入、谨慎买入、持有、观望、减仓或卖出建议。"
        if final_node
        else "你是专项分析师节点，不得给出最终买入、卖出、持有、减仓等操作建议；只输出结构化分析供总控使用。"
    )
    return f"""
你正在一个多分析师股票研究 API 工作流中运行。

{final_rule}

必须遵守：
1. 严格依据本地项目文件中的角色、工作流、输入规范和输出规范。
2. 所有不确定、缺失、未经验证的信息必须显式标注。
3. 如果输入不足，仍然输出结构化 JSON，但降低置信度并列出 missing_information。
4. 只输出一个合法 JSON 对象，不要输出 Markdown，不要输出代码块。
5. JSON 的 key 和字符串分隔符必须使用 ASCII 双引号 "，不要使用中文引号或智能引号。
6. 不要输出注释、解释性前后缀、尾随逗号，确保返回内容可被标准 JSON 解析器直接解析。

# 全局协议
{GLOBAL_CONTEXT}

# 当前节点项目文件
{role_context}
""".strip()


def build_user_prompt(
    *,
    user_input: str,
    node_key: str,
    task_brief: Any,
    upstream_outputs: dict[str, Any],
    external_data: dict[str, Any] | None = None,
    final_node: bool = False,
) -> str:
    compact_external_data = compact_external_data_for_prompt(external_data)
    upstream_without_external = {
        key: value for key, value in upstream_outputs.items() if key != "external_data"
    }
    node_specific_instruction = ""
    if node_key == "04_financial_quality":
        node_specific_instruction = (
            " For 04_financial_quality, treat external_data.node_data_summary.financials.coverage, "
            "financials.latest_snapshot, financials.trend_summary, financials.comparable_trends, announcements, and data_quality_score "
            "as the primary structured evidence base. Distinguish between usable structured financial coverage "
            "and still-missing detailed disclosures. If structured trend points or statement coverage exist, "
            "use them in data_completeness and historical_trends instead of broadly claiming only partial data. "
            "Avoid cross-period trend statements that compare annual, interim, and quarterly periods directly."
        )
    elif final_node or node_key == "01_final_synthesis":
        node_specific_instruction = (
            " For 01_final_synthesis, focus on synthesis rather than repetition. Use upstream analyst outputs as judgments, "
            "not as passages to restate. Prioritize conflicts, decision-relevant facts, and time-horizon differentiation. "
            "Avoid repeating long background descriptions that already appear in upstream sections."
        )
    elif node_key == "02_source_intelligence":
        node_specific_instruction = (
            " For 02_source_intelligence, separate source confidence, data completeness, and modeling readiness. "
            "Keep high_confidence_facts tightly scoped to the most decision-relevant hard facts and place secondary details "
            "in medium_low_confidence_claims or supporting context."
        )
    data_usage_instruction = (
        "优先使用 external_data.node_data_summary 中的可用事实。"
        "如果 node_data_summary.data_available 显示某类数据存在，不得笼统声称该类数据缺失；"
        "只能说明数据口径、覆盖范围或可信度限制。"
        "不得把 C/D 级证据、代理一致预期、搜索摘要或零散舆情写进 high_confidence_facts。"
        "如果 node_data_summary.evidence_classification 存在，必须遵守其中的高、中、低置信度分组。"
        "若原始数据与上游分析师结论冲突，以 node_data_summary 和 evidence_ledger 为证据基准。"
    )
    if node_specific_instruction:
        data_usage_instruction = f"{data_usage_instruction}{node_specific_instruction}"
    payload = {
        "raw_user_input": user_input,
        "current_node": node_key,
        "task_brief": task_brief,
        "generation_rules": [
            "Return one valid JSON object only.",
            "Use ASCII double quotes for every JSON key and string delimiter.",
            "Do not use smart quotes such as “ ” or Chinese quotes such as 「 」.",
            "No markdown, code fences, comments, trailing commas, or explanatory text before/after JSON.",
            "Keep each field concise and schema-aligned.",
        ],
        "data_usage_instruction": data_usage_instruction,
        "external_data": compact_external_data,
        "upstream_outputs": compact_upstream_outputs_for_prompt(upstream_without_external),
        "output_requirement": (
            "请按 01_Master_Valuation_Director/output_schema.md 输出最终完整报告。"
            if final_node
            else "请按当前分析师 output_schema.md 输出 JSON，并在末尾包含 handoff_to_downstream。"
        ),
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def build_data_request_prompt(
    *,
    user_input: str,
    node_key: str,
    task_brief: Any,
) -> str:
    payload = {
        "raw_user_input": user_input,
        "current_node": node_key,
        "task_brief": task_brief,
        "task": (
            "你现在处于数据需求声明阶段，还不进行正式分析。"
            "请只声明完成你这个分析师任务所需的数据、材料、搜索关键词和优先级。"
            "不要编造数据，不要给投资结论。"
        ),
        "generation_rules": [
            "Return one valid JSON object only.",
            "No markdown, code fences, comments, or trailing commas.",
            "Keep required_data between 3 and 8 items.",
            "Keep blocking_data, optional_data, and tool_hints concise.",
            "Use short strings instead of long paragraphs.",
        ],
        "required_output_schema": {
            "analyst": node_key,
            "required_data": [
                {
                    "item": "需要的数据或材料",
                    "reason": "为什么需要",
                    "priority": "high | medium | low",
                    "preferred_sources": ["建议来源"],
                    "suggested_search_queries": ["建议搜索关键词"],
                }
            ],
            "blocking_data": ["缺失后会阻断高置信分析的数据"],
            "optional_data": ["有助于提高质量但非必需的数据"],
            "tool_hints": ["适合使用的工具，如 web_search、quote、kline、financial_report、sentiment_search"],
        },
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def build_requirement_aggregation_prompt(
    *,
    user_input: str,
    task_brief: Any,
    analyst_data_requests: dict[str, Any],
) -> str:
    payload = {
        "raw_user_input": user_input,
        "task_brief": task_brief,
        "analyst_data_requests": analyst_data_requests,
        "task": (
            "你是信息源整理与可信度分析师。现在先不要做最终证据标注，"
            "请汇总各分析师的数据需求，去重、排序，并形成联网搜索计划。"
        ),
        "required_output_schema": {
            "priority_data_needs": [
                {
                    "item": "汇总后的数据需求",
                    "priority": "high | medium | low",
                    "requested_by": ["分析师节点"],
                    "preferred_sources": ["优先来源"],
                    "suggested_search_queries": ["搜索关键词"],
                    "why_it_matters": "用途",
                }
            ],
            "blocking_needs": ["若缺失会阻断高置信分析的数据"],
            "search_plan": {
                "queries": ["最终要执行的搜索关键词"],
                "market_data_needed": ["行情/估值/财务字段"],
                "official_sources_first": ["优先官方来源"],
            },
            "notes_for_collection": ["搜索和采集注意事项"],
        },
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def build_task_definition_prompt(user_input: str, *, current_date: str) -> str:
    payload = {
        "raw_user_input": user_input,
        "run_context": {
            "current_date": current_date,
            "date_rule": "analysis_date 和 information_cutoff 必须使用 current_date，不得自行猜测或使用历史日期。",
        },
        "task": "请把用户输入标准化为本工作流可用的 task_brief。识别公司名称、股票代码、市场、交易所、分析目标、时间周期、已有材料、缺失材料、是否需要联网数据。只输出 JSON。",
        "required_keys": [
            "company_name",
            "ticker",
            "market",
            "exchange",
            "analysis_date",
            "information_cutoff",
            "user_goal",
            "user_time_horizon",
            "available_materials",
            "missing_information",
            "requires_external_data",
            "workflow_notes",
        ],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)
