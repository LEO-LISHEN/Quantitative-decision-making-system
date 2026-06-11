from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import replace
import os
import re
import json
from pathlib import Path
from typing import Any, Callable

from .analysts import ANALYSTS
from .config import CRITICAL_ANALYSTS, MODEL_PROFILES, ModelSpec
from .costs import estimate_cost_usd, summarize_costs
from .data_layer import collect_external_data, normalize_task_dates, search_key_status, today_iso
from .model_client import ChatModelClient, parse_json_object
from .prompts import (
    build_data_request_prompt,
    build_requirement_aggregation_prompt,
    build_system_prompt,
    build_task_definition_prompt,
    build_user_prompt,
)
from .relevance import is_stock_analysis_related, refusal_response


COMMON_UPSTREAM_KEYS = ["01_task_definition", "02_source_intelligence"]

NODE_UPSTREAM_KEY_MAP: dict[str, list[str]] = {
    "02_source_intelligence": ["01_task_definition", "analyst_data_requests", "02_data_requirement_summary"],
    "03_fundamental_business": COMMON_UPSTREAM_KEYS,
    "04_financial_quality": COMMON_UPSTREAM_KEYS,
    "05_dcf_intrinsic_value": COMMON_UPSTREAM_KEYS + [
        "03_fundamental_business",
        "04_financial_quality",
        "08_earnings_revision",
        "10_industry_cycle",
        "11_growth_emerging",
    ],
    "06_relative_valuation": COMMON_UPSTREAM_KEYS + [
        "03_fundamental_business",
        "04_financial_quality",
        "08_earnings_revision",
        "10_industry_cycle",
        "11_growth_emerging",
    ],
    "07_market_expectation_gap": COMMON_UPSTREAM_KEYS + [
        "03_fundamental_business",
        "04_financial_quality",
        "05_dcf_intrinsic_value",
        "06_relative_valuation",
        "08_earnings_revision",
        "10_industry_cycle",
        "11_growth_emerging",
    ],
    "08_earnings_revision": COMMON_UPSTREAM_KEYS + [
        "03_fundamental_business",
        "04_financial_quality",
        "10_industry_cycle",
        "11_growth_emerging",
    ],
    "09_catalyst_event": COMMON_UPSTREAM_KEYS + [
        "03_fundamental_business",
        "04_financial_quality",
        "07_market_expectation_gap",
        "08_earnings_revision",
        "10_industry_cycle",
        "11_growth_emerging",
    ],
    "10_industry_cycle": COMMON_UPSTREAM_KEYS,
    "11_growth_emerging": COMMON_UPSTREAM_KEYS + ["03_fundamental_business", "10_industry_cycle"],
    "12_technical_price_volume": COMMON_UPSTREAM_KEYS + [
        "07_market_expectation_gap",
        "09_catalyst_event",
    ],
    "13_sentiment_public_opinion": COMMON_UPSTREAM_KEYS + [
        "07_market_expectation_gap",
        "09_catalyst_event",
        "12_technical_price_volume",
    ],
    "14_risk_disconfirmation": [
        "01_task_definition",
        "02_source_intelligence",
        "03_fundamental_business",
        "04_financial_quality",
        "05_dcf_intrinsic_value",
        "06_relative_valuation",
        "07_market_expectation_gap",
        "08_earnings_revision",
        "09_catalyst_event",
        "10_industry_cycle",
        "11_growth_emerging",
        "12_technical_price_volume",
        "13_sentiment_public_opinion",
    ],
    "01_final_synthesis": [
        "01_task_definition",
        "02_source_intelligence",
        "03_fundamental_business",
        "04_financial_quality",
        "05_dcf_intrinsic_value",
        "06_relative_valuation",
        "07_market_expectation_gap",
        "08_earnings_revision",
        "09_catalyst_event",
        "10_industry_cycle",
        "11_growth_emerging",
        "12_technical_price_volume",
        "13_sentiment_public_opinion",
        "14_risk_disconfirmation",
    ],
}

NODE_EXTERNAL_SECTION_MAP: dict[str, list[str]] = {
    "02_source_intelligence": [
        "data_requirement_summary",
        "queries_executed",
        "quote_snapshot",
        "web_search_results",
        "errors",
        "notes",
        "research_data_pack.provider_status",
        "research_data_pack.fetch_errors",
        "research_data_pack.data_quality_score",
        "research_data_pack.missing_data",
        "research_data_pack.data_need_coverage",
        "research_data_pack.analyst_data_delivery",
        "research_data_pack.evidence_ledger",
    ],
    "03_fundamental_business": [
        "quote_snapshot",
        "research_data_pack.company_profile",
        "research_data_pack.company_specific_data",
        "research_data_pack.industry_data",
        "research_data_pack.user_materials",
        "research_data_pack.dynamic_research",
        "research_data_pack.missing_data",
    ],
    "04_financial_quality": [
        "quote_snapshot",
        "research_data_pack.financial_statements",
        "research_data_pack.filings_and_announcements",
        "research_data_pack.user_materials",
        "research_data_pack.dynamic_research",
        "research_data_pack.missing_data",
        "research_data_pack.evidence_ledger",
    ],
    "05_dcf_intrinsic_value": [
        "quote_snapshot",
        "research_data_pack.financial_statements",
        "research_data_pack.macro_inputs",
        "research_data_pack.valuation_data",
        "research_data_pack.dynamic_research",
        "research_data_pack.missing_data",
    ],
    "06_relative_valuation": [
        "quote_snapshot",
        "research_data_pack.valuation_data",
        "research_data_pack.peer_table",
        "research_data_pack.market_data.peer_quotes",
        "research_data_pack.financial_statements.consensus_proxy",
        "research_data_pack.dynamic_research",
        "research_data_pack.missing_data",
    ],
    "07_market_expectation_gap": [
        "quote_snapshot",
        "research_data_pack.financial_statements.consensus_proxy",
        "research_data_pack.dynamic_research",
        "research_data_pack.valuation_data",
        "research_data_pack.event_timeline",
        "research_data_pack.market_data.daily_kline",
        "research_data_pack.missing_data",
    ],
    "08_earnings_revision": [
        "quote_snapshot",
        "research_data_pack.financial_statements",
        "research_data_pack.dynamic_research",
        "research_data_pack.filings_and_announcements",
        "research_data_pack.event_timeline",
        "research_data_pack.missing_data",
    ],
    "09_catalyst_event": [
        "quote_snapshot",
        "research_data_pack.event_timeline",
        "research_data_pack.filings_and_announcements",
        "research_data_pack.market_data.daily_kline",
        "research_data_pack.dynamic_research",
        "research_data_pack.missing_data",
    ],
    "10_industry_cycle": [
        "quote_snapshot",
        "research_data_pack.industry_data",
        "research_data_pack.dynamic_research",
        "research_data_pack.market_data.benchmark_data",
        "research_data_pack.missing_data",
    ],
    "11_growth_emerging": [
        "quote_snapshot",
        "research_data_pack.industry_data",
        "research_data_pack.company_specific_data",
        "research_data_pack.dynamic_research",
        "research_data_pack.missing_data",
    ],
    "12_technical_price_volume": [
        "quote_snapshot",
        "research_data_pack.market_data.daily_kline",
        "research_data_pack.market_data.benchmark_data",
        "research_data_pack.market_data.peer_klines",
        "research_data_pack.event_timeline",
        "research_data_pack.missing_data",
    ],
    "13_sentiment_public_opinion": [
        "quote_snapshot",
        "research_data_pack.sentiment_data",
        "research_data_pack.event_timeline",
        "research_data_pack.market_data.daily_kline",
        "research_data_pack.dynamic_research",
        "research_data_pack.missing_data",
    ],
    "14_risk_disconfirmation": [
        "quote_snapshot",
        "queries_executed",
        "web_search_results",
        "errors",
        "research_data_pack.company_profile",
        "research_data_pack.market_data",
        "research_data_pack.financial_statements",
        "research_data_pack.filings_and_announcements",
        "research_data_pack.dynamic_research",
        "research_data_pack.event_timeline",
        "research_data_pack.valuation_data",
        "research_data_pack.sentiment_data",
        "research_data_pack.missing_data",
        "research_data_pack.evidence_ledger",
        "research_data_pack.data_quality_score",
    ],
    "01_final_synthesis": [
        "quote_snapshot",
        "queries_executed",
        "web_search_results",
        "errors",
        "notes",
        "research_data_pack.company_profile",
        "research_data_pack.market_data",
        "research_data_pack.financial_statements",
        "research_data_pack.filings_and_announcements",
        "research_data_pack.peer_table",
        "research_data_pack.industry_data",
        "research_data_pack.company_specific_data",
        "research_data_pack.user_materials",
        "research_data_pack.dynamic_research",
        "research_data_pack.macro_inputs",
        "research_data_pack.sentiment_data",
        "research_data_pack.event_timeline",
        "research_data_pack.valuation_data",
        "research_data_pack.analyst_data_delivery",
        "research_data_pack.data_need_coverage",
        "research_data_pack.missing_data",
        "research_data_pack.provider_status",
        "research_data_pack.data_quality_score",
        "research_data_pack.evidence_ledger",
    ],
}


class StockAnalysisWorkflow:
    def __init__(
        self,
        *,
        profile: str = "cheap",
        collection_mode: str = "standard",
        max_workers: int = 4,
        timeout_seconds: int = 180,
        progress_callback: Callable[[str], None] | None = None,
    ) -> None:
        if profile not in MODEL_PROFILES:
            available = ", ".join(MODEL_PROFILES)
            raise ValueError(f"Unknown profile: {profile}. Available profiles: {available}")
        self.profile = profile
        self.collection_mode = collection_mode
        self.max_workers = max_workers
        self.timeout_seconds = timeout_seconds
        self.calls: list[dict] = []
        self.progress_callback = progress_callback

    def run(self, user_input: str) -> dict:
        if not is_stock_analysis_related(user_input):
            return refusal_response(user_input)

        self._progress("[0/10] workflow started")
        current_date = today_iso()
        task_brief = self._run_node(
            "01_task_definition",
            user_input=user_input,
            task_brief={
                "analysis_date": current_date,
                "information_cutoff": current_date,
                "note": "初始任务定义节点",
            },
            upstream_outputs={},
            custom_user_prompt=build_task_definition_prompt(user_input, current_date=current_date),
            max_tokens=3000,
            model_role="critical",
        )
        task_brief = normalize_task_dates(task_brief)

        self._progress("[1/12] analyst data request stage")
        data_request_nodes = [
            "03_fundamental_business",
            "04_financial_quality",
            "05_dcf_intrinsic_value",
            "06_relative_valuation",
            "07_market_expectation_gap",
            "08_earnings_revision",
            "09_catalyst_event",
            "10_industry_cycle",
            "11_growth_emerging",
            "12_technical_price_volume",
            "13_sentiment_public_opinion",
            "14_risk_disconfirmation",
        ]
        analyst_data_requests = self._run_data_request_phase(
            data_request_nodes,
            user_input=user_input,
            task_brief=task_brief,
        )

        self._progress("[2/12] 02 requirement aggregation stage")
        data_requirement_summary = self._run_node(
            "02_source_intelligence",
            user_input=user_input,
            task_brief=task_brief,
            upstream_outputs={"analyst_data_requests": analyst_data_requests},
            custom_user_prompt=build_requirement_aggregation_prompt(
                user_input=user_input,
                task_brief=task_brief,
                analyst_data_requests=analyst_data_requests,
            ),
            max_tokens=5000,
            model_role="critical",
        )

        self._progress("[3/12] external data collection stage")
        self._progress(f"  collection mode={self.collection_mode}")
        key_status = search_key_status()
        self._progress(
            "  search provider="
            + (key_status.get("active_provider") or "not_configured_or_placeholder")
        )
        external_data = collect_external_data(
            user_input,
            task_brief,
            data_requirement_summary=data_requirement_summary,
            analyst_data_requests=analyst_data_requests,
            collection_mode=self.collection_mode,
            progress_callback=self.progress_callback,
        )
        quote_status = "ok" if external_data.get("quote_snapshot") else "missing"
        search_count = sum(len(item.get("results", [])) for item in external_data.get("web_search_results", []))
        error_count = len(external_data.get("errors", []))
        self._progress(
            f"  external data collected; quote={quote_status}; "
            f"search_results={search_count}; errors={error_count}"
        )

        outputs: dict[str, Any] = {
            "01_task_definition": task_brief,
            "analyst_data_requests": analyst_data_requests,
            "02_data_requirement_summary": data_requirement_summary,
            "external_data": external_data,
        }

        self._progress("[4/12] source intelligence annotation stage")
        outputs["02_source_intelligence"] = self._run_node(
            "02_source_intelligence",
            user_input=user_input,
            task_brief=task_brief,
            upstream_outputs={
                "01_task_definition": task_brief,
                "analyst_data_requests": analyst_data_requests,
                "02_data_requirement_summary": data_requirement_summary,
                "external_data": external_data,
            },
            external_data=external_data,
            model_role="critical",
        )

        self._progress("[5/12] parallel basic quality stage: 03/04/10/11")
        group_a = self._run_parallel(
            [
                "03_fundamental_business",
                "04_financial_quality",
                "10_industry_cycle",
                "11_growth_emerging",
            ],
            user_input=user_input,
            task_brief=task_brief,
            outputs=outputs,
            external_data=external_data,
        )
        outputs.update(group_a)

        self._progress("[6/12] earnings revision stage")
        outputs["08_earnings_revision"] = self._run_node(
            "08_earnings_revision",
            user_input=user_input,
            task_brief=task_brief,
            upstream_outputs=self._select(outputs, [
                "01_task_definition",
                "02_source_intelligence",
                "03_fundamental_business",
                "04_financial_quality",
                "10_industry_cycle",
                "11_growth_emerging",
                "external_data",
            ]),
            external_data=external_data,
            model_role="critical",
        )

        self._progress("[7/12] parallel valuation stage: 05/06")
        group_b = self._run_parallel(
            ["05_dcf_intrinsic_value", "06_relative_valuation"],
            user_input=user_input,
            task_brief=task_brief,
            outputs=outputs,
            external_data=external_data,
        )
        outputs.update(group_b)

        self._progress("[8/12] parallel expectation and catalyst stage: 07/09")
        group_c = self._run_parallel(
            ["07_market_expectation_gap", "09_catalyst_event"],
            user_input=user_input,
            task_brief=task_brief,
            outputs=outputs,
            external_data=external_data,
        )
        outputs.update(group_c)

        self._progress("[9/12] parallel market confirmation stage: 12/13")
        group_d = self._run_parallel(
            ["12_technical_price_volume", "13_sentiment_public_opinion"],
            user_input=user_input,
            task_brief=task_brief,
            outputs=outputs,
            external_data=external_data,
        )
        outputs.update(group_d)

        self._progress("[10/12] risk disconfirmation stage")
        outputs["14_risk_disconfirmation"] = self._run_node(
            "14_risk_disconfirmation",
            user_input=user_input,
            task_brief=task_brief,
            upstream_outputs=outputs,
            external_data=external_data,
            model_role="critical",
        )

        self._progress("[11/12] final synthesis stage")
        final_report = self._run_node(
            "01_final_synthesis",
            user_input=user_input,
            task_brief=task_brief,
            upstream_outputs=outputs,
            external_data=external_data,
            final_node=True,
            model_role="final",
            max_tokens=9000,
        )
        final_report = self._repair_final_report_result(final_report)

        self._progress("[12/12] workflow completed")
        lean_report = self._build_lean_report(final_report, task_brief=task_brief, external_data=external_data)
        text_report = self._build_text_report(final_report, task_brief=task_brief, external_data=external_data)
        long_report = self._build_long_report(
            final_report,
            task_brief=task_brief,
            external_data=external_data,
            analyst_outputs=outputs,
        )
        return {
            "status": "completed",
            "profile": self.profile,
            "task_brief": task_brief,
            "analyst_data_requests": analyst_data_requests,
            "data_requirement_summary": data_requirement_summary,
            "external_data": external_data,
            "analyst_outputs": outputs,
            "final_report": final_report,
            "lean_report": lean_report,
            "text_report": text_report,
            "long_report": long_report,
            "cost_summary": summarize_costs(self.calls),
        }

    def _run_data_request_phase(
        self,
        node_keys: list[str],
        *,
        user_input: str,
        task_brief: Any,
    ) -> dict[str, Any]:
        results: dict[str, Any] = {}
        with ThreadPoolExecutor(max_workers=min(self.max_workers, len(node_keys))) as executor:
            futures = {
                executor.submit(
                    self._run_node,
                    node_key,
                    user_input=user_input,
                    task_brief=task_brief,
                    upstream_outputs={},
                    custom_user_prompt=build_data_request_prompt(
                        user_input=user_input,
                        node_key=node_key,
                        task_brief=task_brief,
                    ),
                    max_tokens=2200,
                    model_role="default",
                ): node_key
                for node_key in node_keys
            }
            for future in as_completed(futures):
                node_key = futures[future]
                results[node_key] = self._repair_data_request_result(node_key, future.result())
                results[node_key] = self._normalize_data_request_result(node_key, results[node_key])
                self._progress(f"  data request finished {node_key}")
        return results

    def _run_parallel(
        self,
        node_keys: list[str],
        *,
        user_input: str,
        task_brief: Any,
        outputs: dict[str, Any],
        external_data: dict[str, Any],
    ) -> dict[str, Any]:
        results: dict[str, Any] = {}
        with ThreadPoolExecutor(max_workers=min(self.max_workers, len(node_keys))) as executor:
            futures = {
                executor.submit(
                    self._run_node,
                    node_key,
                    user_input=user_input,
                    task_brief=task_brief,
                    upstream_outputs=outputs,
                    external_data=external_data,
                    model_role="critical" if node_key in CRITICAL_ANALYSTS else "default",
                ): node_key
                for node_key in node_keys
            }
            for future in as_completed(futures):
                node_key = futures[future]
                results[node_key] = future.result()
                self._progress(f"  finished {node_key}")
        return results

    def _run_node(
        self,
        node_key: str,
        *,
        user_input: str,
        task_brief: Any,
        upstream_outputs: dict[str, Any],
        external_data: dict[str, Any] | None = None,
        final_node: bool = False,
        custom_user_prompt: str | None = None,
        model_role: str = "default",
        max_tokens: int = 6000,
    ) -> Any:
        node = ANALYSTS[node_key]
        spec = self._model_spec(model_role)
        self._progress(f"  running {node_key} with {spec.provider}:{spec.model}")
        client = ChatModelClient(spec, timeout_seconds=self.timeout_seconds)
        system_prompt = build_system_prompt(node, final_node=final_node)
        routed_upstream = self._route_upstream_outputs(node_key, upstream_outputs, final_node=final_node)
        routed_external = self._route_external_data(node_key, external_data, final_node=final_node)
        user_prompt = custom_user_prompt or build_user_prompt(
            user_input=user_input,
            node_key=node_key,
            task_brief=task_brief,
            upstream_outputs=routed_upstream,
            external_data=routed_external,
            final_node=final_node,
        )
        result = client.complete_json(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_tokens=max_tokens,
        )
        self.calls.append(
            {
                "node": node_key,
                "provider": result.provider,
                "model": result.model,
                "usage": result.usage,
                "estimated_cost_usd": round(estimate_cost_usd(spec, result.usage), 6),
            }
        )
        self._progress(
            f"  completed {node_key}; tokens={result.usage.get('total_tokens', 0)}; "
            f"estimated_cost=${estimate_cost_usd(spec, result.usage):.6f}"
        )
        parsed = result.parsed_json
        if node_key == "02_source_intelligence":
            parsed = self._sanitize_source_intelligence_output(parsed)
        if final_node or node_key == "01_final_synthesis":
            parsed = self._repair_final_report_result(parsed)
        return parsed

    def _model_spec(self, role: str) -> ModelSpec:
        profile = MODEL_PROFILES[self.profile]
        spec = profile.get(role) or profile["default"]
        if spec.provider == "deepseek":
            model_env = {
                "default": "DEEPSEEK_MODEL_DEFAULT",
                "critical": "DEEPSEEK_MODEL_CRITICAL",
                "final": "DEEPSEEK_MODEL_FINAL",
            }.get(role, "DEEPSEEK_MODEL_DEFAULT")
            model = os.getenv(model_env) or os.getenv("DEEPSEEK_MODEL") or spec.model
            base_url = os.getenv("DEEPSEEK_BASE_URL") or spec.base_url
            return replace(spec, model=model, base_url=base_url)
        return spec

    @staticmethod
    def _select(outputs: dict[str, Any], keys: list[str]) -> dict[str, Any]:
        return {key: outputs[key] for key in keys if key in outputs}

    def _route_upstream_outputs(
        self,
        node_key: str,
        upstream_outputs: dict[str, Any],
        *,
        final_node: bool = False,
    ) -> dict[str, Any]:
        if not upstream_outputs:
            return {}
        keys = NODE_UPSTREAM_KEY_MAP.get(node_key)
        if final_node and not keys:
            keys = NODE_UPSTREAM_KEY_MAP.get("01_final_synthesis", [])
        if not keys:
            return self._select(upstream_outputs, COMMON_UPSTREAM_KEYS)
        return self._select(upstream_outputs, keys)

    def _route_external_data(
        self,
        node_key: str,
        external_data: dict[str, Any] | None,
        *,
        final_node: bool = False,
    ) -> dict[str, Any] | None:
        if not external_data:
            return external_data
        spec_key = "01_final_synthesis" if final_node else node_key
        sections = NODE_EXTERNAL_SECTION_MAP.get(spec_key)
        if not sections:
            return external_data
        filtered: dict[str, Any] = {
            "collection_time": external_data.get("collection_time"),
            "ticker": external_data.get("ticker"),
            "company_name": external_data.get("company_name"),
        }
        for section in sections:
            value = self._extract_path(external_data, section)
            if value is not None:
                self._assign_path(filtered, section, value)
        filtered["node_data_summary"] = self._build_node_data_summary(spec_key, external_data)
        return filtered

    def _build_node_data_summary(self, node_key: str, external_data: dict[str, Any]) -> dict[str, Any]:
        research_pack = external_data.get("research_data_pack") or {}
        market_data = research_pack.get("market_data") or {}
        financials = research_pack.get("financial_statements") or {}
        dynamic_research = research_pack.get("dynamic_research") or {}
        summary: dict[str, Any] = {
            "purpose": "Use these concise facts before declaring data missing.",
            "data_available": self._available_data_flags(external_data),
            "quote": self._quote_summary(external_data.get("quote_snapshot") or market_data.get("quote")),
            "missing_data": (research_pack.get("missing_data") or [])[:8],
            "fetch_errors": (research_pack.get("fetch_errors") or [])[:5],
        }
        if node_key in {
            "02_source_intelligence",
            "07_market_expectation_gap",
            "09_catalyst_event",
            "12_technical_price_volume",
            "13_sentiment_public_opinion",
            "14_risk_disconfirmation",
            "01_final_synthesis",
        }:
            summary["daily_kline"] = self._kline_summary(market_data.get("daily_kline"))
            summary["benchmark_data"] = self._benchmark_summary(market_data.get("benchmark_data") or {})
            summary["event_timeline"] = self._event_summary(research_pack.get("event_timeline") or {})
        if node_key in {
            "02_source_intelligence",
            "04_financial_quality",
            "05_dcf_intrinsic_value",
            "06_relative_valuation",
            "08_earnings_revision",
            "14_risk_disconfirmation",
            "01_final_synthesis",
        }:
            summary["financials"] = self._financial_summary(financials)
            summary["announcements"] = self._announcement_summary(research_pack.get("filings_and_announcements") or [])
            summary["consensus_proxy"] = self._consensus_proxy_summary(dynamic_research.get("consensus_proxy") or {})
            summary["data_quality_score"] = research_pack.get("data_quality_score") or {}
        if node_key in {
            "02_source_intelligence",
            "03_fundamental_business",
            "10_industry_cycle",
            "11_growth_emerging",
            "14_risk_disconfirmation",
            "01_final_synthesis",
        }:
            summary["company_profile"] = research_pack.get("company_profile") or {}
            summary["industry_and_company_evidence"] = self._evidence_item_summary(
                (research_pack.get("industry_data") or {}).get("items") or []
            )
        if node_key in {
            "02_source_intelligence",
            "03_fundamental_business",
            "05_dcf_intrinsic_value",
            "06_relative_valuation",
            "07_market_expectation_gap",
            "08_earnings_revision",
            "09_catalyst_event",
            "10_industry_cycle",
            "11_growth_emerging",
            "13_sentiment_public_opinion",
            "14_risk_disconfirmation",
            "01_final_synthesis",
        }:
            summary["dynamic_research"] = self._dynamic_research_summary(dynamic_research)
        if node_key in {
            "06_relative_valuation",
            "07_market_expectation_gap",
            "14_risk_disconfirmation",
            "01_final_synthesis",
        }:
            summary["valuation"] = research_pack.get("valuation_data") or {}
            summary["peers"] = {
                "peer_table": (research_pack.get("peer_table") or [])[:6],
                "peer_quotes": self._peer_quote_summary(market_data.get("peer_quotes") or []),
            }
        if node_key in {
            "02_source_intelligence",
            "13_sentiment_public_opinion",
            "14_risk_disconfirmation",
            "01_final_synthesis",
        }:
            summary["sentiment"] = self._sentiment_summary(research_pack.get("sentiment_data") or {})
        if node_key in {"02_source_intelligence", "01_final_synthesis"}:
            summary["coverage"] = {
                "data_need_coverage": (research_pack.get("data_need_coverage") or [])[:12],
                "analyst_data_delivery": research_pack.get("analyst_data_delivery") or {},
                "data_quality_score": research_pack.get("data_quality_score") or {},
            }
        if node_key == "02_source_intelligence":
            summary["evidence_classification"] = self._source_intelligence_evidence_summary(summary)
        return summary

    @staticmethod
    def _available_data_flags(external_data: dict[str, Any]) -> dict[str, Any]:
        research_pack = external_data.get("research_data_pack") or {}
        market_data = research_pack.get("market_data") or {}
        financials = research_pack.get("financial_statements") or {}
        dynamic_research = research_pack.get("dynamic_research") or {}
        sentiment = research_pack.get("sentiment_data") or {}
        event_timeline = research_pack.get("event_timeline") or {}
        return {
            "quote": bool(external_data.get("quote_snapshot") or market_data.get("quote")),
            "daily_kline_records": (market_data.get("daily_kline") or {}).get("record_count", 0),
            "benchmark_sections": [key for key in ["market_index", "broad_index", "industry_index"] if (market_data.get("benchmark_data") or {}).get(key)],
            "financial_key_indicator_records": (financials.get("key_indicators") or {}).get("record_count", 0),
            "tushare_statement_tables": list(((financials.get("tushare") or {}).get("statements") or {}).keys()),
            "announcement_count": len(research_pack.get("filings_and_announcements") or []),
            "event_count": len(event_timeline.get("events") or []),
            "sentiment_sample_count": len(sentiment.get("samples") or []),
            "dynamic_document_count": len(dynamic_research.get("document_corpus") or []),
            "consensus_proxy": bool(dynamic_research.get("consensus_proxy")),
            "user_material_files": len((research_pack.get("user_materials") or {}).get("files") or []),
        }

    @staticmethod
    def _quote_summary(quote: dict[str, Any] | None) -> dict[str, Any]:
        if not quote:
            return {"available": False}
        normalized = quote.get("normalized") or {}
        return {
            "available": True,
            "source": quote.get("source"),
            "retrieved_at": quote.get("retrieved_at"),
            "last_price": normalized.get("last_price"),
            "previous_close": normalized.get("previous_close"),
            "change_pct": normalized.get("change_pct"),
            "market_cap": normalized.get("market_cap"),
            "float_market_cap": normalized.get("float_market_cap"),
            "pe_ttm": normalized.get("pe_ttm"),
            "pe_dynamic": normalized.get("pe_dynamic"),
            "pb": normalized.get("pb"),
            "turnover_rate_pct": normalized.get("turnover_rate_pct"),
        }

    @staticmethod
    def _kline_summary(kline: dict[str, Any] | None) -> dict[str, Any]:
        if not kline:
            return {"available": False, "record_count": 0}
        records = [
            record for record in (kline.get("records") or [])
            if isinstance(record, dict) and record.get("date") and StockAnalysisWorkflow._to_float(record.get("close")) is not None
        ]
        records = sorted(records, key=lambda item: str(item.get("date")))
        if not records:
            return {"available": False, "record_count": kline.get("record_count", 0)}
        latest = records[-1]
        closes = [StockAnalysisWorkflow._to_float(record.get("close")) for record in records]
        closes = [value for value in closes if value is not None]
        volumes = [StockAnalysisWorkflow._to_float(record.get("volume")) for record in records[-20:]]
        volumes = [value for value in volumes if value is not None]
        return {
            "available": True,
            "source": kline.get("source"),
            "record_count": len(records),
            "start_date": records[0].get("date"),
            "end_date": records[-1].get("date"),
            "latest_close": latest.get("close"),
            "latest_volume": latest.get("volume"),
            "return_5d": StockAnalysisWorkflow._window_return(records, 5),
            "return_20d": StockAnalysisWorkflow._window_return(records, 20),
            "return_60d": StockAnalysisWorkflow._window_return(records, 60),
            "return_120d": StockAnalysisWorkflow._window_return(records, 120),
            "return_full_period": StockAnalysisWorkflow._window_return(records, len(records) - 1),
            "period_high": max(closes) if closes else None,
            "period_low": min(closes) if closes else None,
            "avg_volume_20d": round(sum(volumes) / len(volumes), 2) if volumes else None,
            "sample_recent_records": records[-5:],
        }

    @staticmethod
    def _window_return(records: list[dict[str, Any]], days: int) -> float | None:
        if len(records) <= days or days <= 0:
            return None
        start = StockAnalysisWorkflow._to_float(records[-days - 1].get("close"))
        end = StockAnalysisWorkflow._to_float(records[-1].get("close"))
        if start in {None, 0} or end is None:
            return None
        return round(end / start - 1, 6)

    @staticmethod
    def _benchmark_summary(benchmark_data: dict[str, Any]) -> dict[str, Any]:
        output: dict[str, Any] = {}
        for key in ["market_index", "broad_index", "industry_index"]:
            if benchmark_data.get(key):
                output[key] = StockAnalysisWorkflow._kline_summary(benchmark_data.get(key))
        if benchmark_data.get("fetch_errors"):
            output["fetch_errors"] = benchmark_data.get("fetch_errors")[:5]
        return output

    @staticmethod
    def _financial_summary(financials: dict[str, Any]) -> dict[str, Any]:
        key_indicators = financials.get("key_indicators") or {}
        records = key_indicators.get("records") or []
        tushare = financials.get("tushare") or {}
        statement_tables = (tushare.get("statements") or {})
        return {
            "coverage": StockAnalysisWorkflow._financial_coverage_summary(records, statement_tables),
            "latest_snapshot": StockAnalysisWorkflow._financial_latest_snapshot(records, statement_tables),
            "trend_summary": StockAnalysisWorkflow._financial_trend_summary(records, statement_tables),
            "comparable_trends": StockAnalysisWorkflow._financial_comparable_trends(records, statement_tables),
            "key_indicators": {
                "available": bool(records),
                "source": key_indicators.get("source"),
                "record_count": key_indicators.get("record_count", len(records)),
                "sample_records": [
                    StockAnalysisWorkflow._financial_record_summary(record)
                    for record in records[:3]
                ],
            },
            "tushare_statements": {
                "available": bool(statement_tables),
                "coverage": StockAnalysisWorkflow._tushare_statement_coverage(statement_tables),
                "tables": {
                    name: {
                        "record_count": table.get("record_count"),
                        "latest_periods": StockAnalysisWorkflow._statement_latest_periods(table),
                    }
                    for name, table in statement_tables.items()
                },
            },
            "consensus_proxy": StockAnalysisWorkflow._consensus_proxy_summary(financials.get("consensus_proxy") or {}),
            "user_tables": (financials.get("user_tables") or [])[:3],
        }

    @staticmethod
    def _financial_comparable_trends(
        key_indicator_records: list[dict[str, Any]],
        statement_tables: dict[str, Any],
    ) -> dict[str, Any]:
        latest_key_record = StockAnalysisWorkflow._latest_record_by_period(key_indicator_records)
        latest_period = StockAnalysisWorkflow._period_value(latest_key_record)
        output = {
            "latest_period": latest_period,
            "latest_report_type": StockAnalysisWorkflow._report_type_name(latest_key_record),
            "use_rule": "Prefer same-period YoY and same report-type comparisons; avoid chaining interim, annual, and quarterly periods into one trend line.",
        }
        if latest_key_record:
            output["latest_same_period_yoy"] = {
                "revenue_yoy_pct": StockAnalysisWorkflow._pick_first_value(
                    latest_key_record, ["TOTALOPERATEREVETZ", "or_yoy", "tr_yoy", "revenue_yoy_pct"]
                ),
                "parent_net_profit_yoy_pct": StockAnalysisWorkflow._pick_first_value(
                    latest_key_record, ["PARENTNETPROFITTZ", "netprofit_yoy", "parent_net_profit_yoy_pct"]
                ),
                "gross_margin_pct": StockAnalysisWorkflow._pick_first_value(
                    latest_key_record, ["XSMLL", "grossprofit_margin", "gross_margin", "gross_margin_pct"]
                ),
                "roe_weighted_pct": StockAnalysisWorkflow._pick_first_value(
                    latest_key_record, ["ROEJQ", "roe", "roe_dt", "roe_weighted_pct"]
                ),
                "operating_cashflow_to_revenue": StockAnalysisWorkflow._pick_first_value(
                    latest_key_record, ["JYXJLYYSR", "ocf_to_revenue", "operating_cashflow_to_revenue"]
                ),
                "liability_to_asset_pct": StockAnalysisWorkflow._pick_first_value(
                    latest_key_record, ["ZCFZL", "debt_to_assets", "liability_to_asset_pct"]
                ),
            }
        output["annual_view"] = StockAnalysisWorkflow._financial_period_bucket_summary(
            key_indicator_records,
            statement_tables,
            bucket="annual",
        )
        output["quarterly_view"] = StockAnalysisWorkflow._financial_period_bucket_summary(
            key_indicator_records,
            statement_tables,
            bucket="quarterly",
        )
        return output

    @staticmethod
    def _financial_coverage_summary(
        key_indicator_records: list[dict[str, Any]],
        statement_tables: dict[str, Any],
    ) -> dict[str, Any]:
        key_periods = StockAnalysisWorkflow._sorted_periods(
            StockAnalysisWorkflow._period_value(record) for record in key_indicator_records
        )
        annual_periods = [period for period in key_periods if "Q" not in period.upper()]
        quarterly_periods = [period for period in key_periods if "Q" in period.upper()]
        statement_names = list(statement_tables.keys())
        return {
            "key_indicator_period_count": len(key_periods),
            "latest_period": key_periods[0] if key_periods else None,
            "latest_annual_period": annual_periods[0] if annual_periods else None,
            "latest_quarter_period": quarterly_periods[0] if quarterly_periods else None,
            "annual_periods_sample": annual_periods[:5],
            "quarter_periods_sample": quarterly_periods[:6],
            "statement_tables_available": statement_names,
            "has_income_statement": "income" in statement_names,
            "has_balance_sheet": "balancesheet" in statement_names,
            "has_cashflow_statement": "cashflow" in statement_names,
            "has_fina_indicator": "fina_indicator" in statement_names,
            "has_audit_table": "fina_audit" in statement_names,
        }

    @staticmethod
    def _financial_latest_snapshot(
        key_indicator_records: list[dict[str, Any]],
        statement_tables: dict[str, Any],
    ) -> dict[str, Any]:
        latest_key_record = StockAnalysisWorkflow._latest_record_by_period(key_indicator_records)
        snapshot = {
            "period": StockAnalysisWorkflow._period_value(latest_key_record) if latest_key_record else None,
            "report_type": StockAnalysisWorkflow._pick_first_value(latest_key_record, ["REPORT_TYPE", "report_type"]),
            "revenue": StockAnalysisWorkflow._pick_first_value(
                latest_key_record, ["TOTALOPERATEREVE", "revenue", "total_revenue", "oper_rev"]
            ),
            "revenue_yoy_pct": StockAnalysisWorkflow._pick_first_value(
                latest_key_record, ["TOTALOPERATEREVETZ", "or_yoy", "tr_yoy", "revenue_yoy_pct"]
            ),
            "parent_net_profit": StockAnalysisWorkflow._pick_first_value(
                latest_key_record, ["PARENTNETPROFIT", "n_income_attr_p", "profit_to_gr", "parent_net_profit"]
            ),
            "parent_net_profit_yoy_pct": StockAnalysisWorkflow._pick_first_value(
                latest_key_record, ["PARENTNETPROFITTZ", "netprofit_yoy", "dt_netprofit_yoy", "parent_net_profit_yoy_pct"]
            ),
            "gross_margin_pct": StockAnalysisWorkflow._pick_first_value(
                latest_key_record, ["XSMLL", "grossprofit_margin", "gross_margin", "gross_margin_pct"]
            ),
            "net_margin_pct": StockAnalysisWorkflow._pick_first_value(
                latest_key_record, ["XSJLL", "netprofit_margin", "net_margin", "net_margin_pct"]
            ),
            "roe_weighted_pct": StockAnalysisWorkflow._pick_first_value(
                latest_key_record, ["ROEJQ", "roe", "roe_dt", "roe_weighted_pct"]
            ),
            "operating_cashflow_to_revenue": StockAnalysisWorkflow._pick_first_value(
                latest_key_record, ["JYXJLYYSR", "ocf_to_revenue", "operating_cashflow_to_revenue"]
            ),
            "liability_to_asset_pct": StockAnalysisWorkflow._pick_first_value(
                latest_key_record, ["ZCFZL", "debt_to_assets", "liability_to_asset_pct"]
            ),
            "current_ratio": StockAnalysisWorkflow._pick_first_value(latest_key_record, ["LD", "current_ratio"]),
            "quick_ratio": StockAnalysisWorkflow._pick_first_value(latest_key_record, ["SD", "quick_ratio"]),
        }
        if any(value is not None for key, value in snapshot.items() if key not in {"period", "report_type"}):
            return snapshot
        income_latest = StockAnalysisWorkflow._latest_statement_record(statement_tables.get("income"))
        cashflow_latest = StockAnalysisWorkflow._latest_statement_record(statement_tables.get("cashflow"))
        balance_latest = StockAnalysisWorkflow._latest_statement_record(statement_tables.get("balancesheet"))
        fina_indicator_latest = StockAnalysisWorkflow._latest_statement_record(statement_tables.get("fina_indicator"))
        return {
            "period": (
                StockAnalysisWorkflow._period_value(income_latest)
                or StockAnalysisWorkflow._period_value(balance_latest)
                or StockAnalysisWorkflow._period_value(cashflow_latest)
                or StockAnalysisWorkflow._period_value(fina_indicator_latest)
            ),
            "revenue": StockAnalysisWorkflow._pick_first_value(income_latest, ["total_revenue", "revenue", "oper_rev"]),
            "revenue_yoy_pct": StockAnalysisWorkflow._pick_first_value(income_latest, ["tr_yoy", "or_yoy"]),
            "parent_net_profit": StockAnalysisWorkflow._pick_first_value(
                income_latest, ["n_income_attr_p", "netprofit", "profit_to_gr"]
            ),
            "parent_net_profit_yoy_pct": StockAnalysisWorkflow._pick_first_value(income_latest, ["netprofit_yoy"]),
            "gross_margin_pct": StockAnalysisWorkflow._pick_first_value(fina_indicator_latest, ["grossprofit_margin"]),
            "net_margin_pct": StockAnalysisWorkflow._pick_first_value(fina_indicator_latest, ["netprofit_margin"]),
            "roe_weighted_pct": StockAnalysisWorkflow._pick_first_value(
                fina_indicator_latest, ["roe_dt", "roe", "q_roe"]
            ),
            "operating_cashflow": StockAnalysisWorkflow._pick_first_value(
                cashflow_latest, ["n_cashflow_act", "im_net_cashflow_oper_act"]
            ),
            "total_assets": StockAnalysisWorkflow._pick_first_value(balance_latest, ["total_assets"]),
            "total_liabilities": StockAnalysisWorkflow._pick_first_value(balance_latest, ["total_liab"]),
            "current_ratio": StockAnalysisWorkflow._pick_first_value(fina_indicator_latest, ["current_ratio"]),
            "quick_ratio": StockAnalysisWorkflow._pick_first_value(fina_indicator_latest, ["quick_ratio"]),
        }

    @staticmethod
    def _financial_trend_summary(
        key_indicator_records: list[dict[str, Any]],
        statement_tables: dict[str, Any],
    ) -> dict[str, Any]:
        revenue_series = StockAnalysisWorkflow._metric_series(
            key_indicator_records,
            ["TOTALOPERATEREVE", "revenue", "total_revenue", "oper_rev"],
        ) or StockAnalysisWorkflow._statement_metric_series(
            statement_tables.get("income"),
            ["total_revenue", "revenue", "oper_rev"],
        )
        net_profit_series = StockAnalysisWorkflow._metric_series(
            key_indicator_records,
            ["PARENTNETPROFIT", "n_income_attr_p", "profit_to_gr"],
        ) or StockAnalysisWorkflow._statement_metric_series(
            statement_tables.get("income"),
            ["n_income_attr_p", "netprofit", "profit_to_gr"],
        )
        gross_margin_series = StockAnalysisWorkflow._metric_series(
            key_indicator_records,
            ["XSMLL", "grossprofit_margin", "gross_margin"],
        ) or StockAnalysisWorkflow._statement_metric_series(
            statement_tables.get("fina_indicator"),
            ["grossprofit_margin"],
        )
        roe_series = StockAnalysisWorkflow._metric_series(
            key_indicator_records,
            ["ROEJQ", "roe", "roe_dt"],
        ) or StockAnalysisWorkflow._statement_metric_series(
            statement_tables.get("fina_indicator"),
            ["roe_dt", "roe", "q_roe"],
        )
        ocf_ratio_series = StockAnalysisWorkflow._metric_series(
            key_indicator_records,
            ["JYXJLYYSR", "ocf_to_revenue", "operating_cashflow_to_revenue"],
        )
        leverage_series = StockAnalysisWorkflow._metric_series(
            key_indicator_records,
            ["ZCFZL", "debt_to_assets", "liability_to_asset_pct"],
        ) or StockAnalysisWorkflow._statement_ratio_series(
            statement_tables.get("balancesheet"),
            numerator_keys=["total_liab"],
            denominator_keys=["total_assets"],
        )
        return {
            "revenue": StockAnalysisWorkflow._series_summary(revenue_series, value_kind="amount"),
            "net_profit": StockAnalysisWorkflow._series_summary(net_profit_series, value_kind="amount"),
            "gross_margin_pct": StockAnalysisWorkflow._series_summary(gross_margin_series, value_kind="percent"),
            "roe_weighted_pct": StockAnalysisWorkflow._series_summary(roe_series, value_kind="percent"),
            "operating_cashflow_to_revenue": StockAnalysisWorkflow._series_summary(ocf_ratio_series, value_kind="percent"),
            "liability_to_asset_pct": StockAnalysisWorkflow._series_summary(leverage_series, value_kind="percent"),
        }

    @staticmethod
    def _tushare_statement_coverage(statement_tables: dict[str, Any]) -> dict[str, Any]:
        coverage: dict[str, Any] = {}
        for name, table in statement_tables.items():
            coverage[name] = {
                "record_count": table.get("record_count", 0),
                "latest_period": (StockAnalysisWorkflow._statement_latest_periods(table) or [None])[0],
            }
        return coverage

    @staticmethod
    def _statement_latest_periods(table: dict[str, Any] | None, *, limit: int = 3) -> list[str]:
        records = (table or {}).get("records") or []
        periods = StockAnalysisWorkflow._sorted_periods(
            StockAnalysisWorkflow._period_value(record) for record in records
        )
        return periods[:limit]

    @staticmethod
    def _financial_record_summary(record: dict[str, Any]) -> dict[str, Any]:
        return {
            "period": record.get("REPORT_DATE_NAME") or record.get("REPORT_DATE"),
            "report_type": record.get("REPORT_TYPE"),
            "notice_date": record.get("NOTICE_DATE"),
            "currency": record.get("CURRENCY"),
            "revenue": record.get("TOTALOPERATEREVE"),
            "revenue_yoy_pct": record.get("TOTALOPERATEREVETZ"),
            "parent_net_profit": record.get("PARENTNETPROFIT"),
            "parent_net_profit_yoy_pct": record.get("PARENTNETPROFITTZ"),
            "deducted_net_profit": record.get("KCFJCXSYJLR"),
            "deducted_net_profit_yoy_pct": record.get("KCFJCXSYJLRTZ"),
            "eps": record.get("EPSJB"),
            "bps": record.get("BPS"),
            "gross_margin_pct": record.get("XSMLL"),
            "net_margin_pct": record.get("XSJLL"),
            "roe_weighted_pct": record.get("ROEJQ"),
            "roic_pct": record.get("ROIC"),
            "operating_cashflow_to_revenue": record.get("JYXJLYYSR"),
            "cashflow_per_share": record.get("MGJYXJJE"),
            "liability_to_asset_pct": record.get("ZCFZL"),
            "current_ratio": record.get("LD"),
            "quick_ratio": record.get("SD"),
            "fcff_forward": record.get("FCFF_FORWARD"),
        }

    @staticmethod
    def _latest_record_by_period(records: list[dict[str, Any]]) -> dict[str, Any] | None:
        valid_records = [record for record in records if isinstance(record, dict) and StockAnalysisWorkflow._period_value(record)]
        if not valid_records:
            return None
        return max(valid_records, key=lambda item: StockAnalysisWorkflow._period_sort_key(StockAnalysisWorkflow._period_value(item) or ""))

    @staticmethod
    def _report_type_name(record: dict[str, Any] | None) -> str | None:
        raw = str(StockAnalysisWorkflow._pick_first_value(record, ["REPORT_TYPE", "report_type"]) or "").strip()
        if raw:
            return raw
        period = str(StockAnalysisWorkflow._period_value(record) or "")
        upper = period.upper()
        if "Q1" in upper:
            return "quarterly"
        if "Q2" in upper or "0630" in period or "06-30" in period:
            return "interim"
        if "Q3" in upper or "0930" in period or "09-30" in period:
            return "quarterly"
        if "Q4" in upper or "1231" in period or "12-31" in period:
            return "annual"
        if "年" in period:
            return "annual"
        return None

    @staticmethod
    def _financial_period_bucket_summary(
        key_indicator_records: list[dict[str, Any]],
        statement_tables: dict[str, Any],
        *,
        bucket: str,
    ) -> dict[str, Any]:
        filtered = []
        for record in key_indicator_records:
            period = str(StockAnalysisWorkflow._period_value(record) or "")
            report_type = (StockAnalysisWorkflow._report_type_name(record) or "").lower()
            is_quarter = "q" in period.lower() or "quarter" in report_type
            is_annual = ("年" in period and "q" not in period.lower()) or "annual" in report_type
            if bucket == "annual" and is_annual:
                filtered.append(record)
            if bucket == "quarterly" and is_quarter:
                filtered.append(record)
        latest = StockAnalysisWorkflow._latest_record_by_period(filtered)
        if latest:
            return {
                "available": True,
                "latest_period": StockAnalysisWorkflow._period_value(latest),
                "revenue_yoy_pct": StockAnalysisWorkflow._pick_first_value(
                    latest, ["TOTALOPERATEREVETZ", "or_yoy", "tr_yoy", "revenue_yoy_pct"]
                ),
                "parent_net_profit_yoy_pct": StockAnalysisWorkflow._pick_first_value(
                    latest, ["PARENTNETPROFITTZ", "netprofit_yoy", "parent_net_profit_yoy_pct"]
                ),
                "gross_margin_pct": StockAnalysisWorkflow._pick_first_value(
                    latest, ["XSMLL", "grossprofit_margin", "gross_margin", "gross_margin_pct"]
                ),
                "roe_weighted_pct": StockAnalysisWorkflow._pick_first_value(
                    latest, ["ROEJQ", "roe", "roe_dt", "roe_weighted_pct"]
                ),
            }
        if bucket == "annual":
            income_latest = StockAnalysisWorkflow._latest_statement_record(statement_tables.get("income"))
            fina_latest = StockAnalysisWorkflow._latest_statement_record(statement_tables.get("fina_indicator"))
            period = StockAnalysisWorkflow._period_value(income_latest) or StockAnalysisWorkflow._period_value(fina_latest)
            if period and ("1231" in period or "12-31" in period):
                return {
                    "available": True,
                    "latest_period": period,
                    "revenue_yoy_pct": StockAnalysisWorkflow._pick_first_value(income_latest, ["tr_yoy", "or_yoy"]),
                    "parent_net_profit_yoy_pct": StockAnalysisWorkflow._pick_first_value(income_latest, ["netprofit_yoy"]),
                    "gross_margin_pct": StockAnalysisWorkflow._pick_first_value(fina_latest, ["grossprofit_margin"]),
                    "roe_weighted_pct": StockAnalysisWorkflow._pick_first_value(fina_latest, ["roe_dt", "roe", "q_roe"]),
                }
        return {"available": False}

    @staticmethod
    def _latest_statement_record(table: dict[str, Any] | None) -> dict[str, Any] | None:
        if not isinstance(table, dict):
            return None
        return StockAnalysisWorkflow._latest_record_by_period((table.get("records") or []))

    @staticmethod
    def _period_value(record: dict[str, Any] | None) -> str | None:
        if not isinstance(record, dict):
            return None
        for key in ["REPORT_DATE_NAME", "REPORT_DATE", "end_date", "ann_date", "f_ann_date"]:
            value = record.get(key)
            if value not in {None, ""}:
                return str(value)
        return None

    @staticmethod
    def _period_sort_key(period: str) -> tuple[int, int, int]:
        text = str(period or "")
        year_match = re.search(r"(20\d{2})", text)
        year = int(year_match.group(1)) if year_match else 0
        quarter_match = re.search(r"Q([1-4])", text.upper())
        if quarter_match:
            quarter = int(quarter_match.group(1))
        elif "0930" in text or "09-30" in text:
            quarter = 3
        elif "0630" in text or "06-30" in text:
            quarter = 2
        elif "0331" in text or "03-31" in text:
            quarter = 1
        elif "1231" in text or "12-31" in text:
            quarter = 4
        else:
            quarter = 0
        digits = int("".join(ch for ch in text if ch.isdigit()) or 0)
        return year, quarter, digits

    @staticmethod
    def _sorted_periods(periods: Any) -> list[str]:
        clean = sorted(
            {str(period) for period in periods if period not in {None, ""}},
            key=StockAnalysisWorkflow._period_sort_key,
            reverse=True,
        )
        return clean

    @staticmethod
    def _pick_first_value(record: dict[str, Any] | None, keys: list[str]) -> Any:
        if not isinstance(record, dict):
            return None
        for key in keys:
            if key in record and record.get(key) not in {None, ""}:
                return record.get(key)
        return None

    @staticmethod
    def _metric_series(records: list[dict[str, Any]], keys: list[str]) -> list[dict[str, Any]]:
        series: list[dict[str, Any]] = []
        for record in records:
            period = StockAnalysisWorkflow._period_value(record)
            value = StockAnalysisWorkflow._to_float(StockAnalysisWorkflow._pick_first_value(record, keys))
            if period and value is not None:
                series.append({"period": period, "value": value})
        deduped: dict[str, float] = {}
        for point in series:
            deduped[point["period"]] = point["value"]
        return [
            {"period": period, "value": deduped[period]}
            for period in StockAnalysisWorkflow._sorted_periods(deduped.keys())
        ]

    @staticmethod
    def _statement_metric_series(table: dict[str, Any] | None, keys: list[str]) -> list[dict[str, Any]]:
        if not isinstance(table, dict):
            return []
        return StockAnalysisWorkflow._metric_series((table.get("records") or []), keys)

    @staticmethod
    def _statement_ratio_series(
        table: dict[str, Any] | None,
        *,
        numerator_keys: list[str],
        denominator_keys: list[str],
    ) -> list[dict[str, Any]]:
        if not isinstance(table, dict):
            return []
        series: list[dict[str, Any]] = []
        for record in (table.get("records") or []):
            period = StockAnalysisWorkflow._period_value(record)
            numerator = StockAnalysisWorkflow._to_float(StockAnalysisWorkflow._pick_first_value(record, numerator_keys))
            denominator = StockAnalysisWorkflow._to_float(StockAnalysisWorkflow._pick_first_value(record, denominator_keys))
            if period and numerator is not None and denominator not in {None, 0}:
                series.append({"period": period, "value": round(numerator / denominator * 100, 4)})
        deduped: dict[str, float] = {}
        for point in series:
            deduped[point["period"]] = point["value"]
        return [
            {"period": period, "value": deduped[period]}
            for period in StockAnalysisWorkflow._sorted_periods(deduped.keys())
        ]

    @staticmethod
    def _series_summary(series: list[dict[str, Any]], *, value_kind: str) -> dict[str, Any]:
        if not series:
            return {"available": False}
        latest = series[0]
        earliest = series[-1]
        latest_value = StockAnalysisWorkflow._to_float(latest.get("value"))
        earliest_value = StockAnalysisWorkflow._to_float(earliest.get("value"))
        delta = None
        if latest_value is not None and earliest_value is not None:
            delta = round(latest_value - earliest_value, 4)
        if delta is None:
            trend = "unknown"
        elif delta > 0:
            trend = "up"
        elif delta < 0:
            trend = "down"
        else:
            trend = "flat"
        output = {
            "available": True,
            "latest_period": latest.get("period"),
            "latest_value": latest_value,
            "earliest_period": earliest.get("period"),
            "earliest_value": earliest_value,
            "trend": trend,
            "delta": delta,
            "observation_count": len(series),
            "recent_points": series[:4],
        }
        if value_kind == "amount" and latest_value not in {None, 0} and earliest_value not in {None, 0}:
            output["change_pct_vs_earliest"] = round(latest_value / earliest_value - 1, 6)
        return output

    @staticmethod
    def _consensus_proxy_summary(consensus: dict[str, Any]) -> dict[str, Any]:
        if not consensus:
            return {"available": False}
        return {
            "available": True,
            "source": consensus.get("source"),
            "confidence": consensus.get("confidence"),
            "target_price_median": consensus.get("target_price_median"),
            "document_count": consensus.get("document_count"),
            "table_count": consensus.get("table_count"),
            "ratings_observed": consensus.get("ratings_observed"),
            "target_price_observations": StockAnalysisWorkflow._short_observations(consensus.get("target_price_observations") or [], limit=4),
            "eps_forecast_observations": StockAnalysisWorkflow._short_observations(consensus.get("eps_forecast_observations") or [], limit=5),
            "net_profit_forecast_observations": StockAnalysisWorkflow._short_observations(consensus.get("net_profit_forecast_observations") or [], limit=5),
            "revenue_forecast_observations": StockAnalysisWorkflow._short_observations(consensus.get("revenue_forecast_observations") or [], limit=5),
            "limitations": consensus.get("limitations"),
        }

    @staticmethod
    def _short_observations(items: list[dict[str, Any]], *, limit: int) -> list[dict[str, Any]]:
        output = []
        for item in items[:limit]:
            output.append(
                {
                    "year": item.get("year"),
                    "value": item.get("value"),
                    "source": item.get("source"),
                    "title": item.get("title"),
                    "snippet": str(item.get("snippet") or "")[:180],
                }
            )
        return output

    @staticmethod
    def _announcement_summary(announcements: list[dict[str, Any]]) -> dict[str, Any]:
        return {
            "available": bool(announcements),
            "count": len(announcements),
            "latest": [
                {
                    "title": item.get("title"),
                    "notice_date": item.get("notice_date"),
                    "columns": item.get("columns"),
                    "source_url": item.get("source_url"),
                }
                for item in announcements[:8]
            ],
        }

    @staticmethod
    def _event_summary(event_timeline: dict[str, Any]) -> dict[str, Any]:
        return {
            "available": bool(event_timeline.get("events")),
            "event_count": len(event_timeline.get("events") or []),
            "latest_events": (event_timeline.get("events") or [])[:8],
            "event_windows": (event_timeline.get("event_windows") or [])[:6],
        }

    @staticmethod
    def _dynamic_research_summary(dynamic_research: dict[str, Any]) -> dict[str, Any]:
        corpus = dynamic_research.get("document_corpus") or []
        return {
            "available": bool(corpus),
            "document_count": len(corpus),
            "consensus_proxy": StockAnalysisWorkflow._consensus_proxy_summary(dynamic_research.get("consensus_proxy") or {}),
            "documents": [
                {
                    "title": doc.get("title"),
                    "url": doc.get("url"),
                    "data_type": doc.get("data_type"),
                    "document_type": doc.get("document_type"),
                    "parse_status": doc.get("parse_status"),
                    "table_count": doc.get("table_count"),
                    "extracted_signals": StockAnalysisWorkflow._signal_summary(doc.get("extracted_signals") or {}),
                    "text_excerpt": str(doc.get("text_excerpt") or doc.get("search_content") or "")[:500],
                    "table_text_excerpt": str(doc.get("table_text_excerpt") or "")[:500],
                }
                for doc in corpus[:4]
            ],
            "parse_errors": (dynamic_research.get("parse_errors") or [])[:5],
        }

    @staticmethod
    def _signal_summary(signals: dict[str, Any]) -> dict[str, Any]:
        return {
            "ratings": (signals.get("ratings") or [])[:6],
            "target_prices": StockAnalysisWorkflow._short_observations(signals.get("target_prices") or [], limit=3),
            "eps_forecasts": StockAnalysisWorkflow._short_observations(signals.get("eps_forecasts") or [], limit=3),
            "net_profit_forecasts": StockAnalysisWorkflow._short_observations(signals.get("net_profit_forecasts") or [], limit=3),
            "revenue_forecasts": StockAnalysisWorkflow._short_observations(signals.get("revenue_forecasts") or [], limit=3),
            "snippets": [
                {
                    "keyword": item.get("keyword"),
                    "snippet": str(item.get("snippet") or "")[:180],
                }
                for item in (signals.get("snippets") or [])[:4]
            ],
        }

    @staticmethod
    def _sentiment_summary(sentiment_data: dict[str, Any]) -> dict[str, Any]:
        samples = sentiment_data.get("samples") or []
        return {
            "available": bool(samples),
            "sample_count": len(samples),
            "queries": sentiment_data.get("search_queries") or [],
            "samples": [
                {
                    "source": item.get("source"),
                    "title": item.get("title") or item.get("source_name"),
                    "url": item.get("url"),
                    "content": str(item.get("content") or item.get("text_excerpt") or "")[:700],
                    "retrieved_at": item.get("retrieved_at"),
                    "confidence": item.get("confidence"),
                }
                for item in samples[:6]
            ],
        }

    @staticmethod
    def _evidence_item_summary(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        output = []
        for item in items[:6]:
            output.append(
                {
                    "source": item.get("source"),
                    "data_type": item.get("data_type"),
                    "title": item.get("title") or item.get("source_name"),
                    "url": item.get("url"),
                    "text_excerpt": str(item.get("text_excerpt") or item.get("content") or "")[:700],
                    "table_text_excerpt": str(item.get("table_text_excerpt") or "")[:700],
                    "confidence": item.get("confidence"),
                }
            )
        return output

    @staticmethod
    def _peer_quote_summary(peer_quotes: list[dict[str, Any]]) -> list[dict[str, Any]]:
        output = []
        for item in peer_quotes[:6]:
            quote = item.get("quote") or {}
            output.append(
                {
                    "ticker": item.get("ticker"),
                    "company_name": item.get("company_name"),
                    "reason": item.get("reason"),
                    "quote": StockAnalysisWorkflow._quote_summary(quote),
                }
            )
        return output

    @staticmethod
    def _source_intelligence_evidence_summary(summary: dict[str, Any]) -> dict[str, Any]:
        quote = summary.get("quote") or {}
        daily_kline = summary.get("daily_kline") or {}
        financials = summary.get("financials") or {}
        announcements = summary.get("announcements") or {}
        event_timeline = summary.get("event_timeline") or {}
        sentiment = summary.get("sentiment") or {}
        consensus = summary.get("consensus_proxy") or {}
        dynamic_research = summary.get("dynamic_research") or {}
        data_quality = ((summary.get("coverage") or {}).get("data_quality_score")) or {}
        high_confidence_facts: list[str] = []
        if quote.get("available"):
            pe_dynamic = quote.get("pe_dynamic")
            pe_text = f", 动态PE {pe_dynamic}倍" if pe_dynamic is not None else ""
            high_confidence_facts.append(
                f"最新行情可验证：股价 {quote.get('last_price')}，市值 {quote.get('market_cap')}{pe_text}。"
            )
        if daily_kline.get("available"):
            high_confidence_facts.append(
                f"日K线可验证：{daily_kline.get('record_count')} 个交易日，区间 {daily_kline.get('start_date')} 至 {daily_kline.get('end_date')}。"
            )
        key_indicators = (financials.get("key_indicators") or {})
        if key_indicators.get("available"):
            high_confidence_facts.append(
                f"财务关键指标可验证：{key_indicators.get('record_count')} 条记录，来源 {key_indicators.get('source')}。"
            )
        if announcements.get("available"):
            high_confidence_facts.append(
                f"公告与披露可验证：{announcements.get('count')} 条公告索引，最近事件已进入时间线。"
            )
        if event_timeline.get("available"):
            high_confidence_facts.append(
                f"事件时间线可验证：{event_timeline.get('event_count')} 个事件，含业绩、回购与治理公告。"
            )
        medium_confidence_facts: list[str] = []
        if dynamic_research.get("available"):
            medium_confidence_facts.append(
                f"动态研究文档共 {dynamic_research.get('document_count')} 份，可辅助行业、公司与预期差判断，但需辨别时效与口径。"
            )
        if sentiment.get("available"):
            medium_confidence_facts.append(
                f"舆情样本共 {sentiment.get('sample_count')} 条，只适合辅助观察情绪方向，不宜单独下结论。"
            )
        low_confidence_or_proxy_facts: list[str] = []
        if consensus.get("available"):
            low_confidence_or_proxy_facts.append(
                f"一致预期代理来自 {consensus.get('document_count')} 份研报/网页抽取，置信度 {consensus.get('confidence')}，不得并入高置信事实。"
            )
        for limitation in (consensus.get("limitations") or [])[:3]:
            low_confidence_or_proxy_facts.append(str(limitation))
        usage_rules = [
            "A/B级官方披露、行情和结构化财务数据可进入 high_confidence_facts。",
            "C/D级研报代理、搜索摘要、零散舆情只能进入 medium_low_confidence_claims 或 rumors。",
            "请分开表述来源可信度、数据完整度和建模适用度，避免把三者混成一个结论。",
            "若 data_quality_score.financial_modeling_readiness 不是 strong，必须明确说明财务建模精度受限。",
        ]
        if data_quality.get("quality_warnings"):
            usage_rules.extend((data_quality.get("quality_warnings") or [])[:3])
        return {
            "high_confidence_facts": high_confidence_facts,
            "medium_confidence_facts": medium_confidence_facts,
            "low_confidence_or_proxy_facts": low_confidence_or_proxy_facts,
            "usage_rules": usage_rules,
        }

    def _repair_data_request_result(self, node_key: str, result: Any) -> Any:
        if not isinstance(result, dict) or not result.get("json_parse_error"):
            return result
        raw_text = str(result.get("raw_text") or "")
        if not raw_text:
            return result
        repaired = self._repair_json_like_text(raw_text)
        parsed = parse_json_object(repaired)
        if isinstance(parsed, dict) and not parsed.get("json_parse_error"):
            parsed.setdefault("repair_note", "parsed_from_repaired_raw_text")
            parsed.setdefault("analyst", node_key)
            return parsed
        salvaged = self._salvage_data_request_output(raw_text, default_analyst=node_key)
        return salvaged or result

    def _repair_final_report_result(self, result: Any) -> Any:
        if not isinstance(result, dict) or not result.get("json_parse_error"):
            return result
        raw_text = str(result.get("raw_text") or "")
        if not raw_text:
            return result
        repaired = self._repair_json_like_text(raw_text)
        parsed = parse_json_object(repaired)
        if isinstance(parsed, dict) and not parsed.get("json_parse_error"):
            parsed.setdefault("repair_note", "parsed_from_repaired_raw_text")
            return parsed
        salvaged = self._salvage_final_report_output(raw_text)
        return salvaged or result

    @staticmethod
    def _normalize_data_request_result(node_key: str, result: Any) -> Any:
        if not isinstance(result, dict):
            return result
        normalized = dict(result)
        normalized["analyst"] = str(normalized.get("analyst") or node_key)
        required_data = normalized.get("required_data")
        clean_required: list[dict[str, Any]] = []
        if isinstance(required_data, list):
            for item in required_data[:8]:
                if not isinstance(item, dict):
                    continue
                entry = {
                    "item": str(item.get("item") or "")[:120],
                    "reason": str(item.get("reason") or "")[:180],
                    "priority": str(item.get("priority") or "medium")[:12],
                    "preferred_sources": [str(value)[:80] for value in (item.get("preferred_sources") or [])[:4]],
                    "suggested_search_queries": [str(value)[:120] for value in (item.get("suggested_search_queries") or [])[:4]],
                }
                if entry["item"]:
                    clean_required.append(entry)
        normalized["required_data"] = clean_required
        for field_name, limit, item_limit in [
            ("blocking_data", 120, 5),
            ("optional_data", 120, 5),
            ("tool_hints", 40, 6),
        ]:
            values = normalized.get(field_name)
            if isinstance(values, list):
                normalized[field_name] = [str(value)[:limit] for value in values[:item_limit] if str(value).strip()]
            else:
                normalized[field_name] = []
        return normalized

    @staticmethod
    def _repair_json_like_text(text: str) -> str:
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`")
            if cleaned.lower().startswith("json"):
                cleaned = cleaned[4:].strip()
        lines = cleaned.splitlines()
        repaired: list[str] = []
        for index, line in enumerate(lines):
            updated = line
            stripped = line.rstrip()
            if '": [' in stripped and stripped.count("[") > stripped.count("]"):
                next_nonempty = ""
                for candidate in lines[index + 1 :]:
                    candidate_stripped = candidate.strip()
                    if candidate_stripped:
                        next_nonempty = candidate_stripped
                        break
                if next_nonempty.startswith('"') or next_nonempty.startswith("}") or next_nonempty.startswith("]"):
                    updated = stripped[:-1] + "]," if stripped.endswith(",") else stripped + "]"
            repaired.append(updated)
        return "\n".join(repaired)

    @staticmethod
    def _salvage_data_request_output(raw_text: str, *, default_analyst: str) -> dict[str, Any] | None:
        analyst_match = re.search(r'"analyst"\s*:\s*"([^"]+)"', raw_text)
        analyst = analyst_match.group(1) if analyst_match else default_analyst
        required_block = StockAnalysisWorkflow._extract_json_array_block(raw_text, "required_data")
        required_items: list[dict[str, Any]] = []
        for obj_text in StockAnalysisWorkflow._extract_object_blocks(required_block):
            item = StockAnalysisWorkflow._extract_string_field(obj_text, "item")
            reason = StockAnalysisWorkflow._extract_string_field(obj_text, "reason")
            priority = StockAnalysisWorkflow._extract_string_field(obj_text, "priority")
            preferred_sources = StockAnalysisWorkflow._extract_string_array_field(
                obj_text,
                "preferred_sources",
                next_fields=["suggested_search_queries", "item", "reason", "priority"],
            )
            suggested_queries = StockAnalysisWorkflow._extract_string_array_field(
                obj_text,
                "suggested_search_queries",
                next_fields=["preferred_sources", "item", "reason", "priority"],
            )
            if item or reason or priority or preferred_sources or suggested_queries:
                required_items.append(
                    {
                        "item": item or "",
                        "reason": reason or "",
                        "priority": priority or "medium",
                        "preferred_sources": preferred_sources,
                        "suggested_search_queries": suggested_queries,
                    }
                )
        blocking_data = StockAnalysisWorkflow._extract_string_array_block(raw_text, "blocking_data")
        optional_data = StockAnalysisWorkflow._extract_string_array_block(raw_text, "optional_data")
        tool_hints = StockAnalysisWorkflow._extract_string_array_block(raw_text, "tool_hints")
        if not any([required_items, blocking_data, optional_data, tool_hints]):
            return None
        return {
            "analyst": analyst,
            "required_data": required_items,
            "blocking_data": blocking_data,
            "optional_data": optional_data,
            "tool_hints": tool_hints,
            "repair_note": "salvaged_from_raw_text_after_json_parse_error",
        }

    @staticmethod
    def _salvage_final_report_output(raw_text: str) -> dict[str, Any] | None:
        sections: dict[str, Any] = {}
        section_names = [
            "company",
            "executive_conclusion",
            "time_horizon_recommendations",
            "integrated_analysis",
            "valuation_synthesis",
            "scenario_analysis",
            "risk_and_disconfirmation",
            "tracking_plan",
            "information_quality",
            "conflicts_and_judgment",
        ]
        for field_name in section_names:
            block = StockAnalysisWorkflow._extract_json_object_block(raw_text, field_name)
            if not block:
                continue
            parsed = parse_json_object(block)
            if isinstance(parsed, dict) and not parsed.get("json_parse_error"):
                sections[field_name] = parsed
        if not sections:
            return None
        sections["repair_note"] = "salvaged_from_raw_text_after_json_parse_error"
        return sections

    @staticmethod
    def _extract_json_array_block(text: str, field_name: str) -> str:
        marker = f'"{field_name}"'
        start = text.find(marker)
        if start < 0:
            return ""
        bracket_start = text.find("[", start)
        if bracket_start < 0:
            return ""
        depth = 0
        for index in range(bracket_start, len(text)):
            char = text[index]
            if char == "[":
                depth += 1
            elif char == "]":
                depth -= 1
                if depth == 0:
                    return text[bracket_start : index + 1]
        next_field = re.search(r'\n\s*"[A-Za-z_]+\"\s*:', text[bracket_start:])
        if next_field:
            return text[bracket_start : bracket_start + next_field.start()]
        return text[bracket_start:]

    @staticmethod
    def _extract_json_object_block(text: str, field_name: str) -> str:
        marker = f'"{field_name}"'
        start = text.find(marker)
        if start < 0:
            return ""
        brace_start = text.find("{", start)
        if brace_start < 0:
            return ""
        depth = 0
        in_string = False
        escaped = False
        for index in range(brace_start, len(text)):
            char = text[index]
            if char == "\\" and not escaped:
                escaped = True
                continue
            if char == '"' and not escaped:
                in_string = not in_string
            if not in_string:
                if char == "{":
                    depth += 1
                elif char == "}":
                    depth -= 1
                    if depth == 0:
                        return text[brace_start : index + 1]
            escaped = False
        return text[brace_start:]

    @staticmethod
    def _extract_object_blocks(array_block: str) -> list[str]:
        blocks: list[str] = []
        depth = 0
        start_index: int | None = None
        for index, char in enumerate(array_block):
            if char == "{":
                if depth == 0:
                    start_index = index
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0 and start_index is not None:
                    blocks.append(array_block[start_index : index + 1])
                    start_index = None
        return blocks

    @staticmethod
    def _extract_string_field(text: str, field_name: str) -> str | None:
        match = re.search(rf'"{field_name}"\s*:\s*"([^"]*)"', text)
        return match.group(1).strip() if match else None

    @staticmethod
    def _extract_string_array_field(text: str, field_name: str, *, next_fields: list[str]) -> list[str]:
        start_match = re.search(rf'"{field_name}"\s*:\s*\[', text)
        if not start_match:
            return []
        remainder = text[start_match.end() :]
        next_pattern = "|".join(re.escape(field) for field in next_fields)
        next_match = re.search(rf'(?:\]\s*,\s*|,\s*)"(?:{next_pattern})"\s*:', remainder)
        candidate = remainder[: next_match.start()] if next_match else remainder
        return [match.strip() for match in re.findall(r'"([^"]+)"', candidate)]

    @staticmethod
    def _extract_string_array_block(text: str, field_name: str) -> list[str]:
        block = StockAnalysisWorkflow._extract_json_array_block(text, field_name)
        if not block:
            return []
        return [match.strip() for match in re.findall(r'"([^"]+)"', block)]

    @staticmethod
    def _sanitize_source_intelligence_output(result: Any) -> Any:
        if not isinstance(result, dict):
            return result
        high = [item for item in (result.get("high_confidence_facts") or []) if isinstance(item, str)]
        medium = [item for item in (result.get("medium_low_confidence_claims") or []) if isinstance(item, str)]
        downgraded: list[str] = []
        kept_high: list[str] = []
        markers = [
            "研报",
            "券商",
            "引用",
            "需核对",
            "需年报PDF核对",
            "未验证",
            "一致预期",
            "目标价中位数",
            "传闻",
            "搜索结果显示",
            "批价",
            "行业产量",
            "万千升",
        ]
        for item in high:
            if any(marker in item for marker in markers):
                downgraded.append(item)
            else:
                kept_high.append(item)
        if downgraded:
            deduped_medium = medium[:]
            for item in downgraded:
                if item not in deduped_medium:
                    deduped_medium.append(item)
            result["high_confidence_facts"] = kept_high
            result["medium_low_confidence_claims"] = deduped_medium
            summary = str(result.get("confidence_summary") or "")
            note = "部分研报转引或待核对事实已从 high_confidence_facts 下调至 medium_low_confidence_claims。"
            if note not in summary:
                result["confidence_summary"] = f"{summary} {note}".strip()
        high = [item for item in (result.get("high_confidence_facts") or []) if isinstance(item, str)]
        if len(high) > 8:
            result["high_confidence_facts"] = high[:8]
            result["supporting_high_confidence_facts"] = high[8:14]
            summary = str(result.get("confidence_summary") or "")
            note = "high_confidence_facts 已收敛为最关键的 8 条，其他高置信支持事实移至 supporting_high_confidence_facts。"
            if note not in summary:
                result["confidence_summary"] = f"{summary} {note}".strip()
        return result

    @staticmethod
    def _build_lean_report(
        final_report: dict[str, Any],
        *,
        task_brief: dict[str, Any],
        external_data: dict[str, Any],
    ) -> dict[str, Any]:
        company = final_report.get("company") or {}
        executive = final_report.get("executive_conclusion") or {}
        horizons = final_report.get("time_horizon_recommendations") or {}
        info_quality = final_report.get("information_quality") or {}
        integrated = final_report.get("integrated_analysis") or {}
        quote = ((external_data.get("research_data_pack") or {}).get("valuation_data") or {}).get("snapshot") or {}
        return {
            "company_name": company.get("company_name") or task_brief.get("company_name"),
            "ticker": company.get("ticker") or task_brief.get("ticker"),
            "analysis_date": company.get("analysis_date") or task_brief.get("analysis_date"),
            "current_price": company.get("current_price") or quote.get("last_price"),
            "overall_recommendation": executive.get("overall_recommendation"),
            "recommendation_confidence": executive.get("recommendation_confidence"),
            "one_sentence_view": executive.get("one_sentence_view"),
            "fair_value_range": executive.get("fair_value_range"),
            "short_term": (horizons.get("short_term") or {}).get("recommendation"),
            "medium_term": (horizons.get("medium_term") or {}).get("recommendation"),
            "long_term": (horizons.get("long_term") or {}).get("recommendation"),
            "key_thesis": (integrated.get("investment_thesis") or [])[:3],
            "key_risks": (info_quality.get("key_limitations") or [])[:3],
            "information_quality": info_quality.get("overall_quality"),
        }

    @staticmethod
    def _build_text_report(
        final_report: dict[str, Any],
        *,
        task_brief: dict[str, Any],
        external_data: dict[str, Any],
    ) -> str:
        company = final_report.get("company") or {}
        executive = final_report.get("executive_conclusion") or {}
        horizons = final_report.get("time_horizon_recommendations") or {}
        info_quality = final_report.get("information_quality") or {}
        integrated = final_report.get("integrated_analysis") or {}
        current_price = company.get("current_price")
        fair_value = executive.get("preferred_range") or executive.get("fair_value_range")
        fair_value_text = StockAnalysisWorkflow._format_fair_value_range(fair_value)
        upside_downside = executive.get("upside_downside") or {}
        risks = (info_quality.get("key_limitations") or [])[:3]
        theses = (integrated.get("investment_thesis") or [])[:4]
        short_term = horizons.get("short_term") or {}
        medium_term = horizons.get("medium_term") or {}
        long_term = horizons.get("long_term") or {}
        lines = [
            f"# {(company.get('company_name') or task_brief.get('company_name') or '标的')}简版分析报告",
            "",
            f"结论：{executive.get('overall_recommendation') or '待确认'}。",
            f"当前价格：{current_price if current_price is not None else '待确认'}；参考估值区间：{fair_value_text}；"
            f"结论置信度：{executive.get('recommendation_confidence') or '待确认'}。",
            "",
            str(executive.get("one_sentence_view") or "").strip(),
            "",
            "## 核心判断",
        ]
        for item in theses:
            lines.append(f"- {item}")
        if upside_downside:
            lines.extend(
                [
                    "",
                    "## 估值与回报空间",
                    f"- 基准情形上行空间：{upside_downside.get('to_base_case', '待确认')}",
                    f"- 乐观情形上行空间：{upside_downside.get('to_bull_case', '待确认')}",
                    f"- 悲观情形下行空间：{upside_downside.get('to_bear_case', '待确认')}",
                ]
            )
        lines.extend(
            [
                "",
                "## 分期限建议",
                f"- 短期：{short_term.get('recommendation', '待确认')}。{str(short_term.get('reasoning') or '')[:150]}",
                f"- 中期：{medium_term.get('recommendation', '待确认')}。{str(medium_term.get('reasoning') or '')[:150]}",
                f"- 长期：{long_term.get('recommendation', '待确认')}。{str(long_term.get('reasoning') or '')[:150]}",
                "",
                "## 主要风险",
            ]
        )
        for item in risks:
            lines.append(f"- {item}")
        lines.extend(
            [
                "",
                "## 信息质量",
                f"- 信息质量：{info_quality.get('overall_quality', '待确认')}",
                f"- 来源可信度：{info_quality.get('source_confidence', '待确认')}",
            ]
        )
        unverified = (info_quality.get("unverified_claims") or [])[:2]
        if unverified:
            lines.append("- 仍需谨慎对待的未验证信息：")
            for item in unverified:
                lines.append(f"  - {item}")
        return "\n".join(lines).strip()

    @staticmethod
    def _build_long_report(
        final_report: dict[str, Any],
        *,
        task_brief: dict[str, Any],
        external_data: dict[str, Any],
        analyst_outputs: dict[str, Any],
    ) -> str:
        return StockAnalysisWorkflow._build_long_report_v3(
            final_report,
            task_brief=task_brief,
            external_data=external_data,
            analyst_outputs=analyst_outputs,
        )

    @staticmethod
    def _build_long_report_v2(
        final_report: dict[str, Any],
        *,
        task_brief: dict[str, Any],
        external_data: dict[str, Any],
        analyst_outputs: dict[str, Any],
    ) -> str:
        company = final_report.get("company") or {}
        executive = final_report.get("executive_conclusion") or {}
        horizons = final_report.get("time_horizon_recommendations") or {}
        info_quality = final_report.get("information_quality") or {}
        integrated = final_report.get("integrated_analysis") or {}
        source_intel = analyst_outputs.get("02_source_intelligence") or {}
        financial_quality = analyst_outputs.get("04_financial_quality") or {}
        dcf = analyst_outputs.get("05_dcf_intrinsic_value") or {}
        relative = analyst_outputs.get("06_relative_valuation") or {}
        expectation_gap = analyst_outputs.get("07_market_expectation_gap") or {}
        catalyst = analyst_outputs.get("09_catalyst_event") or {}
        risk_node = analyst_outputs.get("14_risk_disconfirmation") or {}
        data_quality = ((external_data.get("research_data_pack") or {}).get("data_quality_score") or {})

        company_name = company.get("company_name") or task_brief.get("company_name") or "标的"
        ticker = company.get("ticker") or task_brief.get("ticker") or "待确认"
        analysis_date = company.get("analysis_date") or task_brief.get("analysis_date") or "待确认"
        current_price = company.get("current_price")
        fair_value_text = StockAnalysisWorkflow._format_fair_value_range(
            executive.get("fair_value_range") or executive.get("preferred_range")
        )
        lines = [
            f"# {company_name} 长版研究报告",
            "",
            f"- 证券代码：{ticker}",
            f"- 分析日期：{analysis_date}",
            f"- 当前价格：{current_price if current_price is not None else '待确认'}",
            f"- 总体结论：{executive.get('overall_recommendation', '待确认')}",
            f"- 估值区间：{fair_value_text}",
            f"- 结论置信度：{executive.get('recommendation_confidence', '待确认')}",
            f"- 信息质量：{info_quality.get('overall_quality', '待确认')}",
            "",
            "## 一、执行摘要",
        ]
        for item in (integrated.get("investment_thesis") or [])[:6]:
            lines.append(f"- {item}")
        one_sentence_view = str(executive.get("one_sentence_view") or "").strip()
        if one_sentence_view:
            lines.extend(["", one_sentence_view])

        lines.extend(
            [
                "",
                "## 二、核心投资逻辑",
                "### 1. 商业模式与护城河",
                StockAnalysisWorkflow._paragraph_or_default(integrated.get("business_quality"), "商业模式结论待补充。"),
                StockAnalysisWorkflow._evidence_note(
                    section_name="商业模式与护城河",
                    confidence="高",
                    sources=["公司公告", "基本面分析模块", "财务质量模块"],
                ),
                "",
                "### 2. 财务质量与盈利韧性",
                StockAnalysisWorkflow._paragraph_or_default(integrated.get("financial_quality"), "财务质量结论待补充。"),
                StockAnalysisWorkflow._paragraph_or_default(
                    StockAnalysisWorkflow._nested_text(financial_quality.get("earnings_quality"), "cash_conversion"),
                    "",
                ),
                StockAnalysisWorkflow._evidence_note(
                    section_name="财务质量与盈利韧性",
                    confidence="中高" if data_quality.get("financial_source_confidence") == "high" else "中",
                    sources=["东方财富F10关键指标", "财务质量模块"],
                    note=f"财务完整度={data_quality.get('financial_statement_completeness', '待确认')}；建模适用度={data_quality.get('financial_modeling_readiness', '待确认')}",
                ),
                "",
                "### 3. 估值逻辑",
                StockAnalysisWorkflow._paragraph_from_points(
                    [
                        StockAnalysisWorkflow._paragraph_or_default(integrated.get("growth_quality"), ""),
                        StockAnalysisWorkflow._paragraph_or_default((dcf.get("summary") or dcf.get("core_conclusion")), ""),
                        StockAnalysisWorkflow._paragraph_or_default((relative.get("summary") or relative.get("core_conclusion")), ""),
                    ],
                    default="估值逻辑待补充。",
                ),
                StockAnalysisWorkflow._evidence_note(
                    section_name="估值逻辑",
                    confidence="中",
                    sources=["DCF模块", "相对估值模块", "行情估值快照"],
                    note="含模型假设与代理一致预期，需结合信息质量约束使用。",
                ),
                "",
                "### 4. 预期差与修复空间",
                StockAnalysisWorkflow._paragraph_from_points(
                    [
                        StockAnalysisWorkflow._paragraph_or_default((expectation_gap.get("summary") or expectation_gap.get("core_conclusion")), ""),
                        StockAnalysisWorkflow._paragraph_or_default(integrated.get("earnings_revision"), ""),
                    ],
                    default="预期差判断待补充。",
                ),
                StockAnalysisWorkflow._evidence_note(
                    section_name="预期差与修复空间",
                    confidence="中",
                    sources=["市场预期差模块", "盈利修正模块", "动态研报代理"],
                    note="若引用一致预期与研报目标价，仅作为市场预期参考，不作为高置信估值锚点。",
                ),
                "",
                "## 三、财务与估值分析",
                "### 1. 财务分析",
            ]
        )
        historical_trends = financial_quality.get("historical_trends") or {}
        lines.extend(
            [
                f"- 收入趋势：{historical_trends.get('revenue_trend', '待确认')}",
                f"- 毛利率趋势：{historical_trends.get('gross_margin_trend', '待确认')}",
                f"- 现金流趋势：{historical_trends.get('cash_flow_trend', '待确认')}",
                f"- ROE/ROIC 趋势：{historical_trends.get('roe_roic_trend', '待确认')}",
                StockAnalysisWorkflow._evidence_note(
                    section_name="财务分析",
                    confidence="中高",
                    sources=["财务质量模块", "东方财富F10关键指标"],
                    note="趋势应优先按可比口径理解；缺完整三表与附注时，结论按保守处理。",
                ),
                "",
                "### 2. 估值分析",
                f"- 当前结论：{executive.get('overall_recommendation', '待确认')}",
                f"- 参考估值区间：{fair_value_text}",
            ]
        )
        upside = executive.get("upside_downside") or {}
        if upside:
            lines.extend(
                [
                    f"- 基准情形上行空间：{upside.get('to_base_case', '待确认')}",
                    f"- 乐观情形上行空间：{upside.get('to_bull_case', '待确认')}",
                    f"- 悲观情形下行空间：{upside.get('to_bear_case', '待确认')}",
                ]
            )
        lines.append(
            StockAnalysisWorkflow._evidence_note(
                section_name="估值分析",
                confidence="中",
                sources=["DCF模块", "相对估值模块", "历史估值与行情数据"],
                note="若引入研报代理目标价或EPS，必须视作低置信补充证据。",
            )
        )

        lines.extend(
            [
                "",
                "## 四、催化剂与时间线",
                f"- 短期：{StockAnalysisWorkflow._paragraph_or_default((horizons.get('short_term') or {}).get('reasoning'), '待确认')}",
                f"- 中期：{StockAnalysisWorkflow._paragraph_or_default((horizons.get('medium_term') or {}).get('reasoning'), '待确认')}",
                f"- 长期：{StockAnalysisWorkflow._paragraph_or_default((horizons.get('long_term') or {}).get('reasoning'), '待确认')}",
                StockAnalysisWorkflow._paragraph_or_default((catalyst.get("summary") or catalyst.get("core_conclusion")), ""),
                StockAnalysisWorkflow._evidence_note(
                    section_name="催化剂与时间线",
                    confidence="中",
                    sources=["催化剂事件模块", "公告时间线", "市场预期差模块"],
                ),
                "",
                "## 五、风险与反证",
            ]
        )
        risk_items = (risk_node.get("risk_map") or [])[:4]
        if risk_items:
            for item in risk_items:
                lines.append(
                    f"- {item.get('risk_name', '风险项')}：{item.get('valuation_impact_path', '影响路径待确认')} "
                    f"[证据等级：{item.get('evidence_grade', '待确认')}]"
                )
        else:
            for item in (info_quality.get("key_limitations") or [])[:4]:
                lines.append(f"- {item}")

        lines.extend(
            [
                "",
                "## 六、关键补充证据与分歧信息",
            ]
        )
        supplement_items = StockAnalysisWorkflow._build_supplementary_evidence_items(
            source_intel=source_intel,
            financial_quality=financial_quality,
        )
        for item in supplement_items[:8]:
            lines.append(
                f"- {item['content']} [来源：{item['source']}；置信度：{item['confidence']}；用途：{item['usage']}]"
            )

        lines.extend(
            [
                "",
                "## 七、数据缺口与后续验证重点",
            ]
        )
        for item in (info_quality.get("missing_information") or [])[:6]:
            lines.append(f"- {item}")

        lines.extend(
            [
                "",
                "## 八、最终结论",
                f"综合来看，{company_name} 当前总体建议为“{executive.get('overall_recommendation', '待确认')}”。"
                f" 短期以{(horizons.get('short_term') or {}).get('recommendation', '待确认')}为主，"
                f"中期以{(horizons.get('medium_term') or {}).get('recommendation', '待确认')}为主，"
                f"长期以{(horizons.get('long_term') or {}).get('recommendation', '待确认')}为主。",
                "",
                "## 九、证据分级附录",
                "### 高置信证据",
            ]
        )
        for item in (source_intel.get("high_confidence_facts") or [])[:8]:
            lines.append(f"- {item} [对应正文章节：核心投资逻辑 / 财务与估值分析]")
        supporting = source_intel.get("supporting_high_confidence_facts") or []
        if supporting:
            lines.extend(["", "### 高置信支持证据"])
            for item in supporting[:6]:
                lines.append(f"- {item} [对应正文章节：关键补充证据与分歧信息]")
        medium = source_intel.get("medium_low_confidence_claims") or []
        if medium:
            lines.extend(["", "### 中低置信 / 代理证据"])
            for item in medium[:10]:
                lines.append(f"- {item} [对应正文章节：关键补充证据与分歧信息]")
        rumors = source_intel.get("rumors_or_sentiment_only_items") or []
        if rumors:
            lines.extend(["", "### 传闻与情绪线索"])
            for item in rumors[:6]:
                lines.append(f"- {item} [对应正文章节：风险与反证 / 关键补充证据与分歧信息]")
        return "\n".join(lines).strip()

    @staticmethod
    def _build_long_report_v3(
        final_report: dict[str, Any],
        *,
        task_brief: dict[str, Any],
        external_data: dict[str, Any],
        analyst_outputs: dict[str, Any],
    ) -> str:
        company = final_report.get("company") or {}
        executive = final_report.get("executive_conclusion") or {}
        horizons = final_report.get("time_horizon_recommendations") or {}
        info_quality = final_report.get("information_quality") or {}
        integrated = final_report.get("integrated_analysis") or {}
        source_intel = analyst_outputs.get("02_source_intelligence") or {}
        fundamental = analyst_outputs.get("03_fundamental_business") or {}
        financial_quality = analyst_outputs.get("04_financial_quality") or {}
        dcf = analyst_outputs.get("05_dcf_intrinsic_value") or {}
        relative = analyst_outputs.get("06_relative_valuation") or {}
        expectation_gap = analyst_outputs.get("07_market_expectation_gap") or {}
        catalyst = analyst_outputs.get("09_catalyst_event") or {}
        industry = analyst_outputs.get("10_industry_cycle") or {}
        growth = analyst_outputs.get("11_growth_emerging") or {}
        technical = analyst_outputs.get("12_technical_price_volume") or {}
        sentiment = analyst_outputs.get("13_sentiment_public_opinion") or {}
        risk_node = analyst_outputs.get("14_risk_disconfirmation") or {}
        data_quality = ((external_data.get("research_data_pack") or {}).get("data_quality_score") or {})

        company_name = company.get("company_name") or task_brief.get("company_name") or "标的"
        ticker = company.get("ticker") or task_brief.get("ticker") or "待确认"
        analysis_date = company.get("analysis_date") or task_brief.get("analysis_date") or "待确认"
        current_price = company.get("current_price")
        fair_value_text = StockAnalysisWorkflow._format_fair_value_range(
            executive.get("fair_value_range") or executive.get("preferred_range")
        )

        business_model = fundamental.get("business_model_summary") or {}
        industry_comp = fundamental.get("industry_and_competition") or {}
        moat = fundamental.get("moat_assessment") or {}
        capital_allocation = fundamental.get("management_and_capital_allocation") or {}
        segment_analysis = fundamental.get("segment_analysis") or []
        historical_trends = financial_quality.get("historical_trends") or {}
        comparable_trends = (financial_quality.get("normalized_financial_view") or {}).get("comparable_trends") or []
        catalyst_items = catalyst.get("catalysts") or []
        risk_items = (risk_node.get("risk_map") or [])[:4]
        risk_summary = risk_node.get("risk_summary") or {}
        disconfirmation_matrix = risk_node.get("disconfirmation_matrix") or []
        downside_scenarios = risk_node.get("downside_scenarios") or {}
        technical_view = technical.get("technical_confirmation") or {}
        technical_trend = technical.get("trend_state") or {}
        technical_risk = technical.get("risk_signals") or {}
        sentiment_summary = (sentiment.get("handoff_to_master") or {}).get("summary") or ""
        sentiment_state = sentiment.get("sentiment_state") or {}
        narrative_map = sentiment.get("narrative_map") or {}

        lines = [
            f"# {company_name} 长版研究报告",
            "",
            f"- 证券代码：{ticker}",
            f"- 分析日期：{analysis_date}",
            f"- 当前价格：{current_price if current_price is not None else '待确认'}",
            f"- 总体结论：{executive.get('overall_recommendation', '待确认')}",
            f"- 估值区间：{fair_value_text}",
            f"- 结论置信度：{executive.get('recommendation_confidence', '待确认')}",
            f"- 信息质量：{info_quality.get('overall_quality', '待确认')}",
            "",
            "## 一、执行摘要",
        ]
        for item in (integrated.get("investment_thesis") or [])[:6]:
            lines.append(f"- {item}")
        one_sentence_view = str(executive.get("one_sentence_view") or "").strip()
        if one_sentence_view:
            lines.extend(["", one_sentence_view])

        lines.extend(
            [
                "",
                "## 二、核心投资逻辑",
                "### 1. 商业模式与护城河",
                StockAnalysisWorkflow._paragraph_or_default(integrated.get("business_quality"), "商业模式结论待补充。"),
                StockAnalysisWorkflow._paragraph_from_points(
                    [
                        business_model.get("what_it_sells"),
                        business_model.get("revenue_model"),
                        business_model.get("profit_model"),
                        business_model.get("cash_flow_characteristics"),
                    ],
                    default="",
                ),
                StockAnalysisWorkflow._paragraph_from_points(
                    [
                        industry_comp.get("industry_structure"),
                        f"主要竞争对手：{'、'.join(industry_comp.get('main_competitors') or [])}" if industry_comp.get("main_competitors") else "",
                        f"护城河来源：{'、'.join(moat.get('moat_sources') or [])}" if moat.get("moat_sources") else "",
                        capital_allocation.get("capital_allocation"),
                    ],
                    default="",
                ),
            ]
        )
        for item in segment_analysis[:2]:
            if isinstance(item, dict):
                lines.append(
                    f"- 分部观察：{item.get('segment', '核心业务')}，收入驱动为{item.get('revenue_driver', '待确认')}；"
                    f"利润驱动为{item.get('profit_driver', '待确认')}；当前判断：{item.get('growth_quality', '待确认')}。"
                )
        lines.extend(
            [
                StockAnalysisWorkflow._evidence_note(
                    section_name="商业模式与护城河",
                    confidence="高",
                    sources=["公司公告", "基本面分析模块", "财务质量模块"],
                ),
                "",
                "### 2. 财务质量与盈利韧性",
                StockAnalysisWorkflow._paragraph_or_default(integrated.get("financial_quality"), "财务质量结论待补充。"),
                StockAnalysisWorkflow._paragraph_or_default((financial_quality.get("earnings_quality") or {}).get("cash_conversion"), ""),
                StockAnalysisWorkflow._paragraph_from_points(
                    [
                        StockAnalysisWorkflow._nested_text(financial_quality.get("earnings_quality"), "margin_quality"),
                        StockAnalysisWorkflow._nested_text(financial_quality.get("balance_sheet_health"), "leverage_and_liquidity"),
                        StockAnalysisWorkflow._nested_text(financial_quality.get("balance_sheet_health"), "working_capital_signals"),
                        StockAnalysisWorkflow._nested_text(financial_quality.get("management_plan_financial_verification"), "overall_assessment"),
                    ],
                    default="",
                ),
                StockAnalysisWorkflow._evidence_note(
                    section_name="财务质量与盈利韧性",
                    confidence="中高" if data_quality.get("financial_source_confidence") == "high" else "中",
                    sources=["东方财富F10关键指标", "财务质量模块"],
                    note=f"财务完整度={data_quality.get('financial_statement_completeness', '待确认')}；建模适用度={data_quality.get('financial_modeling_readiness', '待确认')}",
                ),
                "",
                "### 3. 估值逻辑",
                StockAnalysisWorkflow._paragraph_from_points(
                    [
                        StockAnalysisWorkflow._paragraph_or_default(integrated.get("growth_quality"), ""),
                        StockAnalysisWorkflow._paragraph_or_default((growth.get("growth_narrative") or {}).get("core_judgment"), ""),
                        StockAnalysisWorkflow._paragraph_or_default((industry.get("valuation_implications") or {}).get("summary"), ""),
                        StockAnalysisWorkflow._paragraph_or_default(integrated.get("valuation_view"), ""),
                        StockAnalysisWorkflow._paragraph_or_default((dcf.get("summary") or dcf.get("core_conclusion")), ""),
                        StockAnalysisWorkflow._paragraph_or_default((relative.get("summary") or relative.get("core_conclusion")), ""),
                    ],
                    default="估值逻辑待补充。",
                ),
                StockAnalysisWorkflow._evidence_note(
                    section_name="估值逻辑",
                    confidence="中",
                    sources=["DCF模块", "相对估值模块", "行情估值快照"],
                    note="含模型假设与代理一致预期，需结合信息质量约束使用。",
                ),
                "",
                "### 4. 预期差与修复空间",
                StockAnalysisWorkflow._paragraph_from_points(
                    [
                        StockAnalysisWorkflow._paragraph_or_default((expectation_gap.get("summary") or expectation_gap.get("core_conclusion")), ""),
                        StockAnalysisWorkflow._paragraph_or_default(integrated.get("earnings_revision"), ""),
                        StockAnalysisWorkflow._paragraph_or_default(integrated.get("expectation_gap"), ""),
                    ],
                    default="预期差判断待补充。",
                ),
                StockAnalysisWorkflow._evidence_note(
                    section_name="预期差与修复空间",
                    confidence="中",
                    sources=["市场预期差模块", "盈利修正模块", "动态研报代理"],
                    note="若引用一致预期与研报目标价，仅作为市场预期参考，不作为高置信估值锚点。",
                ),
                "",
                "## 三、财务与估值分析",
                "### 1. 财务分析",
                f"- 收入趋势：{historical_trends.get('revenue_trend', '待确认')}",
                f"- 毛利率趋势：{historical_trends.get('gross_margin_trend', '待确认')}",
                f"- 现金流趋势：{historical_trends.get('cash_flow_trend', '待确认')}",
                f"- ROE/ROIC 趋势：{historical_trends.get('roe_roic_trend', '待确认')}",
            ]
        )
        for item in comparable_trends[:4]:
            lines.append(f"- 可比口径趋势：{item}")
        lines.extend(
            [
                StockAnalysisWorkflow._evidence_note(
                    section_name="财务分析",
                    confidence="中高",
                    sources=["财务质量模块", "东方财富F10关键指标"],
                    note="趋势应优先按可比口径理解；缺完整三表与附注时，结论按保守处理。",
                ),
                "",
                "### 2. 估值分析",
                f"- 当前结论：{executive.get('overall_recommendation', '待确认')}",
                f"- 参考估值区间：{fair_value_text}",
            ]
        )
        upside = executive.get("upside_downside") or {}
        if upside:
            lines.extend(
                [
                    f"- 基准情形上行空间：{upside.get('to_base_case', '待确认')}",
                    f"- 乐观情形上行空间：{upside.get('to_bull_case', '待确认')}",
                    f"- 悲观情形下行空间：{upside.get('to_bear_case', '待确认')}",
                ]
            )
        lines.append(
            StockAnalysisWorkflow._evidence_note(
                section_name="估值分析",
                confidence="中",
                sources=["DCF模块", "相对估值模块", "历史估值与行情数据"],
                note="若引入研报代理目标价或EPS，必须视作低置信补充证据。",
            )
        )

        lines.extend(
            [
                "",
                "## 四、催化剂与时间线",
                f"- 短期：{StockAnalysisWorkflow._paragraph_or_default((horizons.get('short_term') or {}).get('reasoning'), '待确认')}",
                f"- 中期：{StockAnalysisWorkflow._paragraph_or_default((horizons.get('medium_term') or {}).get('reasoning'), '待确认')}",
                f"- 长期：{StockAnalysisWorkflow._paragraph_or_default((horizons.get('long_term') or {}).get('reasoning'), '待确认')}",
                StockAnalysisWorkflow._paragraph_or_default(catalyst.get("near_term_focus"), ""),
                StockAnalysisWorkflow._paragraph_or_default(catalyst.get("valuation_realization_path"), ""),
                StockAnalysisWorkflow._paragraph_or_default((catalyst.get("summary") or catalyst.get("core_conclusion")), ""),
            ]
        )
        for item in catalyst_items[:4]:
            if isinstance(item, dict):
                event_name = item.get("event_name", "催化剂")
                event_type = item.get("event_type", "other")
                expected_timing = item.get("expected_timing") or item.get("date") or item.get("expected_date") or "待确认"
                impact_direction = item.get("impact_direction", "待确认")
                pricing_status = item.get("pricing_status", "待确认")
                description = StockAnalysisWorkflow._paragraph_from_points(
                    [
                        item.get("description"),
                        (item.get("impact_paths") or {}).get("valuation"),
                        (item.get("impact_paths") or {}).get("earnings"),
                    ],
                    default="",
                )
                lines.append(
                    f"- {event_name}（{event_type} / {expected_timing}）：{description or '需继续跟踪具体变化。'} "
                    f"[可信度：{item.get('credibility', '待确认')}；影响方向：{impact_direction}；市场定价：{pricing_status}]"
                )
        lines.extend(
            [
                StockAnalysisWorkflow._evidence_note(
                    section_name="催化剂与时间线",
                    confidence="中",
                    sources=["催化剂事件模块", "公告时间线", "市场预期差模块"],
                ),
                "",
                "## 五、风险与反证",
            ]
        )
        if risk_summary:
            lines.append(
                StockAnalysisWorkflow._paragraph_from_points(
                    [
                        f"核心多头逻辑当前状态：{risk_summary.get('core_thesis_status', '待确认')}" if risk_summary.get("core_thesis_status") else "",
                        f"最重要的风险包括：{'、'.join(risk_summary.get('most_important_risks') or [])}" if risk_summary.get("most_important_risks") else "",
                        f"市场已部分定价的风险：{'、'.join(risk_summary.get('risks_likely_priced_in') or [])}" if risk_summary.get("risks_likely_priced_in") else "",
                    ],
                    default="",
                )
            )
        if risk_items:
            for item in risk_items:
                lines.append(
                    f"- {item.get('risk_name', '风险项')}：{item.get('valuation_impact_path', '影响路径待确认')} "
                    f"[证据等级：{item.get('evidence_grade', '待确认')}]"
                )
        else:
            for item in (info_quality.get("key_limitations") or [])[:4]:
                lines.append(f"- {item}")
        for item in disconfirmation_matrix[:3]:
            if isinstance(item, dict):
                lines.append(
                    f"- 反证检查：{item.get('assumption', '核心假设')} -> {item.get('current_status', '待确认')}；"
                    f"失败触发条件：{item.get('failure_trigger', '待确认')}"
                )
        if downside_scenarios:
            bear_case = downside_scenarios.get("bear_case") or {}
            stress_case = downside_scenarios.get("stress_case") or {}
            if bear_case:
                lines.append(
                    f"- 悲观情景：{bear_case.get('description', '待确认')} [概率：{bear_case.get('probability', '待确认')}；影响程度：{bear_case.get('severity', '待确认')}]"
                )
            if stress_case:
                lines.append(
                    f"- 压力情景：{stress_case.get('description', '待确认')} [概率：{stress_case.get('probability', '待确认')}；影响程度：{stress_case.get('severity', '待确认')}]"
                )

        lines.extend(["", "## 六、关键补充证据与分歧信息"])
        supplement_items = StockAnalysisWorkflow._build_supplementary_evidence_items(
            source_intel=source_intel,
            financial_quality=financial_quality,
        )
        supplement_items.extend(StockAnalysisWorkflow._build_market_color_items(technical=technical, sentiment=sentiment))
        for item in supplement_items[:10]:
            lines.append(
                f"- {item['content']} [来源：{item['source']}；置信度：{item['confidence']}；用途：{item['usage']}]"
            )

        lines.extend(
            [
                "",
                "## 七、市场印证与情绪观察",
                StockAnalysisWorkflow._paragraph_from_points(
                    [
                        technical_view.get("reasoning"),
                        technical_view.get("timing_implication"),
                        f"主要趋势：{technical_trend.get('primary_trend', '待确认')}" if technical_trend else "",
                        f"情绪状态：{sentiment_state.get('overall_sentiment', '待确认')} / 讨论热度{sentiment_state.get('discussion_heat', '待确认')}" if sentiment_state else "",
                        sentiment_summary,
                    ],
                    default="技术面和舆情层面在本次样本下只能作为辅助印证，不宜单独决定中长期判断。",
                ),
            ]
        )
        for narrative in (narrative_map.get("main_narratives") or [])[:2]:
            if isinstance(narrative, dict):
                lines.append(
                    f"- 主要叙事：{narrative.get('narrative', '待确认')} [方向：{narrative.get('direction', '待确认')}；证据状态：{narrative.get('evidence_status', '待确认')}]"
                )
        for warning in (technical_risk.get("technical_warning_signals") or [])[:2]:
            lines.append(f"- 技术预警信号：{warning}")

        lines.extend(["", "## 八、数据缺口与后续验证重点"])
        for item in (info_quality.get("missing_information") or [])[:6]:
            lines.append(f"- {item}")

        lines.extend(
            [
                "",
                "## 九、最终结论",
                (
                    f"综合来看，{company_name} 当前总体建议为“{executive.get('overall_recommendation', '待确认')}”。"
                    f" 短期以{(horizons.get('short_term') or {}).get('recommendation', '待确认')}为主，"
                    f"中期以{(horizons.get('medium_term') or {}).get('recommendation', '待确认')}为主，"
                    f"长期以{(horizons.get('long_term') or {}).get('recommendation', '待确认')}为主。"
                ),
                "",
                "## 十、证据分级附录",
                "### 高置信证据",
            ]
        )
        for item in (source_intel.get("high_confidence_facts") or [])[:8]:
            lines.append(f"- {item} [对应正文章节：核心投资逻辑 / 财务与估值分析]")
        supporting = source_intel.get("supporting_high_confidence_facts") or []
        if supporting:
            lines.extend(["", "### 高置信支持证据"])
            for item in supporting[:6]:
                lines.append(f"- {item} [对应正文章节：关键补充证据与分歧信息]")
        medium = source_intel.get("medium_low_confidence_claims") or []
        if medium:
            lines.extend(["", "### 中低置信 / 代理证据"])
            for item in medium[:10]:
                lines.append(f"- {item} [对应正文章节：关键补充证据与分歧信息]")
        rumors = source_intel.get("rumors_or_sentiment_only_items") or []
        if rumors:
            lines.extend(["", "### 传闻与情绪线索"])
            for item in rumors[:6]:
                lines.append(f"- {item} [对应正文章节：风险与反证 / 关键补充证据与分歧信息]")
        return "\n".join(lines).strip()

    @staticmethod
    def _build_market_color_items(
        *,
        technical: dict[str, Any],
        sentiment: dict[str, Any],
    ) -> list[dict[str, str]]:
        items: list[dict[str, str]] = []
        for text in (technical.get("risk_signals") or {}).get("failure_signals", [])[:2]:
            items.append(
                {
                    "content": str(text),
                    "source": "technical_price_volume",
                    "confidence": "中",
                    "usage": "时点风险与交易层面补充",
                }
            )
        for item in (sentiment.get("rumor_and_unverified_claims") or [])[:2]:
            if not isinstance(item, dict):
                continue
            items.append(
                {
                    "content": str(item.get("claim") or ""),
                    "source": str(item.get("source") or "sentiment"),
                    "confidence": str(item.get("credibility") or "低"),
                    "usage": "市场传闻与未验证线索",
                }
            )
        return items

    @staticmethod
    def _build_supplementary_evidence_items(
        *,
        source_intel: dict[str, Any],
        financial_quality: dict[str, Any],
    ) -> list[dict[str, str]]:
        items: list[dict[str, str]] = []
        for text in (source_intel.get("medium_low_confidence_claims") or [])[:6]:
            items.append(
                {
                    "content": str(text),
                    "source": "source_intelligence / dynamic_research_proxy",
                    "confidence": "中低",
                    "usage": "补充分歧信息，不直接作为硬估值锚点",
                }
            )
        for text in (source_intel.get("rumors_or_sentiment_only_items") or [])[:3]:
            items.append(
                {
                    "content": str(text),
                    "source": "source_intelligence / sentiment",
                    "confidence": "低",
                    "usage": "情绪线索，仅作风险与市场预期补充",
                }
            )
        for question in (financial_quality.get("questions_for_downstream_analysts") or [])[:3]:
            items.append(
                {
                    "content": str(question),
                    "source": "financial_quality",
                    "confidence": "中",
                    "usage": "后续验证重点",
                }
            )
        return items

    @staticmethod
    def _paragraph_or_default(value: Any, default: str) -> str:
        text = str(value or "").strip()
        return text or default

    @staticmethod
    def _nested_text(value: Any, key: str) -> str:
        if isinstance(value, dict):
            nested = value.get(key)
            if isinstance(nested, list):
                return " ".join(str(item).strip() for item in nested if str(item or "").strip())
            return str(nested or "").strip()
        if isinstance(value, list):
            collected: list[str] = []
            for item in value:
                if isinstance(item, dict):
                    nested = item.get(key)
                    if nested:
                        if isinstance(nested, list):
                            collected.extend(str(part).strip() for part in nested if str(part or "").strip())
                        else:
                            collected.append(str(nested).strip())
                elif key == "overall_assessment" and str(item or "").strip():
                    collected.append(str(item).strip())
            return " ".join(text for text in collected if text)
        return ""

    @staticmethod
    def _paragraph_from_points(points: list[str], *, default: str) -> str:
        parts = [str(point).strip() for point in points if str(point or "").strip()]
        return " ".join(parts) if parts else default

    @staticmethod
    def _evidence_note(*, section_name: str, confidence: str, sources: list[str], note: str | None = None) -> str:
        source_text = " / ".join(source for source in sources if source)
        suffix = f"；备注：{note}" if note else ""
        return f"证据等级：{confidence}；主要来源：{source_text}{suffix}"

    @staticmethod
    def _format_fair_value_range(value: Any) -> str:
        if isinstance(value, str):
            return value
        if isinstance(value, list):
            return "-".join(str(item) for item in value)
        if isinstance(value, dict):
            preferred = value.get("preferred_range")
            if preferred:
                return StockAnalysisWorkflow._format_fair_value_range(preferred)
            parts = []
            for key in ["bear", "base", "bull"]:
                if value.get(key) is not None:
                    parts.append(f"{key}:{value.get(key)}")
            return ", ".join(parts) if parts else "待确认"
        return str(value) if value is not None else "待确认"

    @staticmethod
    def _to_float(value: Any) -> float | None:
        try:
            if value in {None, "-", ""}:
                return None
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _extract_path(data: dict[str, Any], path: str) -> Any:
        current: Any = data
        for part in path.split("."):
            if not isinstance(current, dict) or part not in current:
                return None
            current = current[part]
        return current

    @staticmethod
    def _assign_path(target: dict[str, Any], path: str, value: Any) -> None:
        parts = path.split(".")
        current = target
        for part in parts[:-1]:
            next_value = current.get(part)
            if not isinstance(next_value, dict):
                next_value = {}
                current[part] = next_value
            current = next_value
        current[parts[-1]] = value

    def _progress(self, message: str) -> None:
        if self.progress_callback:
            self.progress_callback(message)


def run_stock_analysis(
    user_input: str,
    *,
    profile: str = "cheap",
    collection_mode: str = "standard",
    max_workers: int = 4,
    timeout_seconds: int = 180,
    progress_callback: Callable[[str], None] | None = None,
) -> dict:
    workflow = StockAnalysisWorkflow(
        profile=profile,
        collection_mode=collection_mode,
        max_workers=max_workers,
        timeout_seconds=timeout_seconds,
        progress_callback=progress_callback,
    )
    return workflow.run(user_input)


def save_analysis_bundle(result: dict[str, Any], output_path: str | Path) -> dict[str, str]:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    saved = {"json": str(path)}

    text_report = str(result.get("text_report") or "").strip()
    if text_report:
        text_path = path.with_suffix(".md")
        text_path.write_text(text_report, encoding="utf-8")
        saved["text_report"] = str(text_path)

    long_report = str(result.get("long_report") or "").strip()
    if long_report:
        long_path = path.with_name(f"{path.stem}_long_report.md")
        long_path.write_text(long_report, encoding="utf-8")
        saved["long_report"] = str(long_path)

    return saved


def run_and_save_stock_analysis(
    user_input: str,
    *,
    output_path: str | Path,
    profile: str = "cheap",
    collection_mode: str = "standard",
    max_workers: int = 4,
    timeout_seconds: int = 180,
    progress_callback: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    result = run_stock_analysis(
        user_input,
        profile=profile,
        collection_mode=collection_mode,
        max_workers=max_workers,
        timeout_seconds=timeout_seconds,
        progress_callback=progress_callback,
    )
    result["saved_files"] = save_analysis_bundle(result, output_path)
    return result
