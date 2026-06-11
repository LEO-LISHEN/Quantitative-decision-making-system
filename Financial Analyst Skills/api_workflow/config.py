from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_SPECS_ROOT = PROJECT_ROOT / "workflow_specs"
ANALYST_SPECS_ROOT = WORKFLOW_SPECS_ROOT / "analysts"
GLOBAL_SPECS_ROOT = WORKFLOW_SPECS_ROOT / "global"


@dataclass(frozen=True)
class ModelSpec:
    provider: str
    model: str
    base_url: str
    api_key_env: str
    input_price_per_1m: float
    output_price_per_1m: float


MODEL_PROFILES: dict[str, dict[str, ModelSpec]] = {
    "cheap": {
        "default": ModelSpec(
            provider="deepseek",
            model="deepseek-v4-flash",
            base_url="https://api.deepseek.com/chat/completions",
            api_key_env="DEEPSEEK_API_KEY",
            input_price_per_1m=0.14,
            output_price_per_1m=0.28,
        ),
        "critical": ModelSpec(
            provider="deepseek",
            model="deepseek-v4-flash",
            base_url="https://api.deepseek.com/chat/completions",
            api_key_env="DEEPSEEK_API_KEY",
            input_price_per_1m=0.14,
            output_price_per_1m=0.28,
        ),
        "final": ModelSpec(
            provider="deepseek",
            model="deepseek-v4-flash",
            base_url="https://api.deepseek.com/chat/completions",
            api_key_env="DEEPSEEK_API_KEY",
            input_price_per_1m=0.14,
            output_price_per_1m=0.28,
        ),
    },
    "balanced": {
        "default": ModelSpec(
            provider="deepseek",
            model="deepseek-v4-flash",
            base_url="https://api.deepseek.com/chat/completions",
            api_key_env="DEEPSEEK_API_KEY",
            input_price_per_1m=0.14,
            output_price_per_1m=0.28,
        ),
        "critical": ModelSpec(
            provider="deepseek",
            model="deepseek-v4-pro",
            base_url="https://api.deepseek.com/chat/completions",
            api_key_env="DEEPSEEK_API_KEY",
            input_price_per_1m=0.435,
            output_price_per_1m=0.87,
        ),
        "final": ModelSpec(
            provider="deepseek",
            model="deepseek-v4-pro",
            base_url="https://api.deepseek.com/chat/completions",
            api_key_env="DEEPSEEK_API_KEY",
            input_price_per_1m=0.435,
            output_price_per_1m=0.87,
        ),
    },
}


ANALYST_DIRS = {
    "01_task_definition": "workflow_specs/analysts/01_Master_Valuation_Director",
    "01_final_synthesis": "workflow_specs/analysts/01_Master_Valuation_Director",
    "02_source_intelligence": "workflow_specs/analysts/02_Source_Intelligence_Analyst",
    "03_fundamental_business": "workflow_specs/analysts/03_Fundamental_Business_Analyst",
    "04_financial_quality": "workflow_specs/analysts/04_Financial_Statements_Quality_Analyst",
    "05_dcf_intrinsic_value": "workflow_specs/analysts/05_DCF_Intrinsic_Value_Analyst",
    "06_relative_valuation": "workflow_specs/analysts/06_Relative_Valuation_Comps_Analyst",
    "07_market_expectation_gap": "workflow_specs/analysts/07_Market_Expectation_Gap_Analyst",
    "08_earnings_revision": "workflow_specs/analysts/08_Earnings_Forecast_Revision_Analyst",
    "09_catalyst_event": "workflow_specs/analysts/09_Catalyst_Event_Analyst",
    "10_industry_cycle": "workflow_specs/analysts/10_Industry_Cycle_Analyst",
    "11_growth_emerging": "workflow_specs/analysts/11_Growth_Emerging_Industries_Analyst",
    "12_technical_price_volume": "workflow_specs/analysts/12_Technical_Price_Volume_Analyst",
    "13_sentiment_public_opinion": "workflow_specs/analysts/13_Sentiment_Public_Opinion_Analyst",
    "14_risk_disconfirmation": "workflow_specs/analysts/14_Risk_Disconfirmation_Short_Analyst",
}


CRITICAL_ANALYSTS = {
    "02_source_intelligence",
    "04_financial_quality",
    "05_dcf_intrinsic_value",
    "07_market_expectation_gap",
    "08_earnings_revision",
    "14_risk_disconfirmation",
}
