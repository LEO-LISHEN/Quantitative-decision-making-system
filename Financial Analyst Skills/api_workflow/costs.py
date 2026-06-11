from __future__ import annotations

from .config import ModelSpec


def estimate_cost_usd(spec: ModelSpec, usage: dict[str, int]) -> float:
    input_tokens = usage.get("prompt_tokens", 0)
    output_tokens = usage.get("completion_tokens", 0)
    return (
        input_tokens / 1_000_000 * spec.input_price_per_1m
        + output_tokens / 1_000_000 * spec.output_price_per_1m
    )


def summarize_costs(calls: list[dict]) -> dict:
    prompt_tokens = sum(call["usage"].get("prompt_tokens", 0) for call in calls)
    completion_tokens = sum(call["usage"].get("completion_tokens", 0) for call in calls)
    total_tokens = sum(call["usage"].get("total_tokens", 0) for call in calls)
    estimated_cost_usd = sum(call.get("estimated_cost_usd", 0.0) for call in calls)
    return {
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
        "estimated_cost_usd": round(estimated_cost_usd, 6),
        "calls": calls,
    }
