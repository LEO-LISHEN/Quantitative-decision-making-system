from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class KellyInput:
    available_cash: float
    win_probability: float
    current_price: float
    take_profit_price: float
    stop_loss_price: float
    kelly_multiplier: float = 0.5


@dataclass(frozen=True)
class KellyResult:
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

    def to_dict(self) -> dict[str, float | str | bool | list[str]]:
        return asdict(self)


def calculate_position(payload: KellyInput) -> KellyResult:
    available_cash = _positive(payload.available_cash, "available_cash")
    current_price = _positive(payload.current_price, "current_price")
    take_profit_price = _positive(payload.take_profit_price, "take_profit_price")
    stop_loss_price = _positive(payload.stop_loss_price, "stop_loss_price")
    win_probability = _normalize_probability(payload.win_probability)
    kelly_multiplier = _bounded(payload.kelly_multiplier, 0, 1, "kelly_multiplier")

    direction = _infer_direction(current_price, take_profit_price, stop_loss_price)
    if direction == "long":
        reward_per_unit = take_profit_price - current_price
        risk_per_unit = current_price - stop_loss_price
    else:
        reward_per_unit = current_price - take_profit_price
        risk_per_unit = stop_loss_price - current_price

    reward_risk_ratio = reward_per_unit / risk_per_unit
    loss_probability = 1 - win_probability
    full_kelly_fraction = win_probability - (loss_probability / reward_risk_ratio)
    edge = (win_probability * reward_per_unit) - (loss_probability * risk_per_unit)

    if full_kelly_fraction <= 0:
        applied_kelly_fraction = 0.0
        risk_capital = 0.0
        raw_position_amount = 0.0
        recommended_position_amount = 0.0
        capped_by_cash = False
        verdict = "不建议下注"
        notes = ["该交易在当前主观胜率和盈亏比下没有正凯利优势。"]
    else:
        applied_kelly_fraction = full_kelly_fraction * kelly_multiplier
        risk_capital = available_cash * applied_kelly_fraction
        stop_loss_pct = risk_per_unit / current_price
        raw_position_amount = risk_capital / stop_loss_pct
        recommended_position_amount = min(raw_position_amount, available_cash)
        capped_by_cash = raw_position_amount > available_cash
        verdict = "可考虑参与" if applied_kelly_fraction < 0.2 else "高波动仓位"
        notes = []
        if capped_by_cash:
            notes.append("原始凯利反推投入金额超过可用资金，结果已按可用资金封顶。")
        if applied_kelly_fraction > 0.25:
            notes.append("凯利比例较高，建议降低主观胜率或使用更低凯利折扣复核。")
        if kelly_multiplier < 1:
            notes.append(f"已使用 {kelly_multiplier:.0%} 凯利折扣，以降低单笔交易波动。")

    units = recommended_position_amount / current_price if current_price else 0.0
    max_loss_amount = units * risk_per_unit
    expected_profit_amount = units * edge
    stop_loss_pct = risk_per_unit / current_price
    take_profit_pct = reward_per_unit / current_price
    account_exposure_pct = recommended_position_amount / available_cash

    return KellyResult(
        direction=direction,
        win_probability=win_probability,
        loss_probability=loss_probability,
        reward_per_unit=round(reward_per_unit, 6),
        risk_per_unit=round(risk_per_unit, 6),
        reward_risk_ratio=round(reward_risk_ratio, 6),
        full_kelly_fraction=round(max(full_kelly_fraction, 0.0), 6),
        applied_kelly_fraction=round(applied_kelly_fraction, 6),
        risk_capital=round(risk_capital, 2),
        raw_position_amount=round(raw_position_amount, 2),
        recommended_position_amount=round(recommended_position_amount, 2),
        capped_by_cash=capped_by_cash,
        units=round(units, 4),
        max_loss_amount=round(max_loss_amount, 2),
        expected_profit_amount=round(expected_profit_amount, 2),
        stop_loss_pct=round(stop_loss_pct, 6),
        take_profit_pct=round(take_profit_pct, 6),
        account_exposure_pct=round(account_exposure_pct, 6),
        edge=round(edge, 6),
        verdict=verdict,
        notes=notes,
    )


def _positive(value: float, field_name: str) -> float:
    value = float(value)
    if value <= 0:
        raise ValueError(f"{field_name} must be greater than 0")
    return value


def _bounded(value: float, minimum: float, maximum: float, field_name: str) -> float:
    value = float(value)
    if not minimum <= value <= maximum:
        raise ValueError(f"{field_name} must be between {minimum} and {maximum}")
    return value


def _normalize_probability(value: float) -> float:
    value = float(value)
    if value > 1:
        value = value / 100
    if not 0 < value < 1:
        raise ValueError("win_probability must be between 0 and 1, or between 0 and 100")
    return value


def _infer_direction(current_price: float, take_profit_price: float, stop_loss_price: float) -> str:
    if take_profit_price > current_price > stop_loss_price:
        return "long"
    if take_profit_price < current_price < stop_loss_price:
        return "short"
    raise ValueError(
        "Invalid price structure. For long trades use take_profit > current > stop_loss; "
        "for short trades use take_profit < current < stop_loss."
    )
