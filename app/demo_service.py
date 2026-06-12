from __future__ import annotations

import json
import math
import os
import re
import threading
import urllib.request
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd


DEMO_AS_OF_DATE = date(2026, 6, 11)
ROOT_DIR = Path(__file__).resolve().parents[1]
WATCHLIST_PATH = ROOT_DIR / "outputs" / "watchlist.json"

DEMO_UNIVERSE = [
    "600519.SH", "300750.SZ", "601318.SH", "000333.SZ", "600036.SH",
    "600276.SH", "000858.SZ", "601166.SH", "600030.SH", "601888.SH",
    "600900.SH", "601398.SH", "601288.SH", "601012.SH", "600887.SH",
    "002594.SZ", "000001.SZ", "000651.SZ", "600309.SH", "601899.SH",
    "600031.SH", "002415.SZ", "300059.SZ", "002475.SZ", "600050.SH",
    "601088.SH", "601857.SH", "600104.SH", "000725.SZ", "601668.SH",
]

_TUSHARE_LOCK = threading.Lock()
_TUSHARE_CACHE: dict[str, Any] = {
    "items": [],
    "stocks": {},
    "bars": {},
    "as_of_date": None,
    "refreshed_at": None,
    "error": None,
}

DEMO_RECOMMENDATIONS: list[dict[str, Any]] = [
    {
        "signal_id": "demo-600519",
        "symbol": "600519.SH",
        "name": "贵州茅台",
        "rank": 1,
        "side": "重点关注",
        "final_score": 86.2,
        "confidence": 0.84,
        "reference_price": 1450.0,
        "change_pct": 1.25,
        "industry": "白酒",
        "summary": "质量与盈利能力突出，估值处于可跟踪区间，趋势改善。",
        "positive_reasons": ["ROE 和现金流质量较高", "20 日相对强度改善", "估值较历史高位收敛"],
        "risk_reasons": ["消费需求恢复不及预期", "批价与渠道库存变化"],
        "invalidation_conditions": ["跌破中期趋势并伴随放量", "核心盈利指标连续下修"],
        "scores": {"trend": 84, "momentum": 78, "quality": 96, "value": 72, "liquidity": 95, "risk": 28},
    },
    {
        "signal_id": "demo-300750",
        "symbol": "300750.SZ",
        "name": "宁德时代",
        "rank": 2,
        "side": "关注",
        "final_score": 82.7,
        "confidence": 0.79,
        "reference_price": 252.6,
        "change_pct": 2.10,
        "industry": "新能源",
        "summary": "成长与流动性得分领先，行业价格竞争仍需持续观察。",
        "positive_reasons": ["成长因子排名靠前", "成交活跃度充足", "中期趋势保持向上"],
        "risk_reasons": ["行业价格竞争", "海外政策不确定性"],
        "invalidation_conditions": ["成长预期显著下修", "跌破 60 日趋势"],
        "scores": {"trend": 88, "momentum": 86, "quality": 82, "value": 60, "liquidity": 98, "risk": 41},
    },
    {
        "signal_id": "demo-601318",
        "symbol": "601318.SH",
        "name": "中国平安",
        "rank": 3,
        "side": "关注",
        "final_score": 79.8,
        "confidence": 0.76,
        "reference_price": 49.8,
        "change_pct": 0.65,
        "industry": "保险",
        "summary": "估值与质量形成支撑，趋势强度中等。",
        "positive_reasons": ["估值分位较低", "盈利质量稳定", "高流动性"],
        "risk_reasons": ["权益市场波动", "长期利率变化"],
        "invalidation_conditions": ["价值与质量因子同步恶化"],
        "scores": {"trend": 68, "momentum": 66, "quality": 88, "value": 91, "liquidity": 94, "risk": 35},
    },
    {
        "signal_id": "demo-000333",
        "symbol": "000333.SZ",
        "name": "美的集团",
        "rank": 4,
        "side": "关注",
        "final_score": 78.4,
        "confidence": 0.75,
        "reference_price": 73.2,
        "change_pct": -0.30,
        "industry": "家电",
        "summary": "经营质量与估值平衡，适合跟踪中期趋势确认。",
        "positive_reasons": ["质量得分较高", "现金流稳定", "估值适中"],
        "risk_reasons": ["海外需求波动", "原材料成本变化"],
        "invalidation_conditions": ["盈利能力持续下降"],
        "scores": {"trend": 71, "momentum": 69, "quality": 91, "value": 78, "liquidity": 88, "risk": 30},
    },
    {
        "signal_id": "demo-600036",
        "symbol": "600036.SH",
        "name": "招商银行",
        "rank": 5,
        "side": "观察",
        "final_score": 76.9,
        "confidence": 0.72,
        "reference_price": 42.1,
        "change_pct": 0.42,
        "industry": "银行",
        "summary": "估值和质量较好，动量尚未形成明显优势。",
        "positive_reasons": ["低估值", "资产质量相对稳健", "流动性充足"],
        "risk_reasons": ["净息差压力", "信用成本变化"],
        "invalidation_conditions": ["资产质量指标显著走弱"],
        "scores": {"trend": 62, "momentum": 58, "quality": 87, "value": 94, "liquidity": 96, "risk": 38},
    },
]


@dataclass(frozen=True)
class DbSettings:
    host: str
    port: int
    database: str
    user: str
    password: str


def _db_settings() -> DbSettings:
    return DbSettings(
        host=os.getenv("POSTGRES_HOST", "127.0.0.1"),
        port=int(os.getenv("POSTGRES_PORT", "15432")),
        database=os.getenv("POSTGRES_DB", "quant"),
        user=os.getenv("POSTGRES_USER", "quant"),
        password=os.getenv("POSTGRES_PASSWORD", "quant_dev_password"),
    )


def _connect():
    try:
        import psycopg2
    except ImportError as exc:
        raise RuntimeError("psycopg2 is not installed") from exc
    cfg = _db_settings()
    return psycopg2.connect(
        host=cfg.host,
        port=cfg.port,
        dbname=cfg.database,
        user=cfg.user,
        password=cfg.password,
        connect_timeout=2,
    )


def _score(value: Any, default: float = 0.5) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return max(0.0, min(1.0, number))


def _percentile(series: pd.Series, higher_is_better: bool = True) -> pd.Series:
    numeric = pd.to_numeric(series, errors="coerce")
    ranked = numeric.rank(pct=True, ascending=higher_is_better)
    return ranked.fillna(0.5).clip(0, 1)


def get_data_source_status() -> dict[str, Any]:
    token = os.getenv("TUSHARE_TOKEN", "").strip()
    with _TUSHARE_LOCK:
        cache = dict(_TUSHARE_CACHE)
    return {
        "provider": "tushare",
        "configured": bool(token),
        "token_hint": f"***{token[-4:]}" if len(token) >= 4 else "",
        "data_mode": "tushare_direct" if cache["items"] else "demo_snapshot",
        "as_of_date": cache["as_of_date"],
        "refreshed_at": cache["refreshed_at"],
        "item_count": len(cache["items"]),
        "last_error": cache["error"],
        "universe_size": len(DEMO_UNIVERSE),
    }


def test_tushare_connection() -> dict[str, Any]:
    token = os.getenv("TUSHARE_TOKEN", "").strip()
    if not token:
        raise ValueError("尚未配置 Tushare Token")
    import tushare as ts

    pro = ts.pro_api(token)
    frame = pro.trade_cal(exchange="SSE", start_date="20260101", end_date="20260110")
    if frame is None or frame.empty:
        raise RuntimeError("Tushare 已响应，但交易日历为空")
    return {
        "success": True,
        "provider": "tushare",
        "message": "Tushare 连接成功",
        "token_hint": f"***{token[-4:]}",
    }


def _latest_open_dates(pro: Any, count: int = 35) -> list[str]:
    end = date.today()
    start = end - timedelta(days=90)
    calendar = pro.trade_cal(
        exchange="SSE",
        start_date=start.strftime("%Y%m%d"),
        end_date=end.strftime("%Y%m%d"),
        fields="cal_date,is_open",
    )
    open_dates = calendar.loc[calendar["is_open"] == 1, "cal_date"].astype(str).sort_values().tolist()
    if not open_dates:
        raise RuntimeError("没有获取到最近交易日")
    return open_dates[-count:]


def _quality_scores(pro: Any, symbols: list[str]) -> dict[str, float]:
    quality: dict[str, float] = {}
    for symbol in symbols:
        try:
            frame = pro.fina_indicator(
                ts_code=symbol,
                limit=1,
                fields="ts_code,roe,roa,grossprofit_margin,netprofit_margin,debt_to_assets",
            )
            if frame is None or frame.empty:
                continue
            row = frame.iloc[0]
            values = [
                float(row.get("roe") or 0) / 25,
                float(row.get("roa") or 0) / 12,
                float(row.get("grossprofit_margin") or 0) / 50,
                float(row.get("netprofit_margin") or 0) / 25,
                1 - float(row.get("debt_to_assets") or 50) / 100,
            ]
            quality[symbol] = max(0.0, min(1.0, sum(values) / len(values)))
        except Exception:
            continue
    return quality


def refresh_tushare_recommendations() -> dict[str, Any]:
    token = os.getenv("TUSHARE_TOKEN", "").strip()
    if not token:
        raise ValueError("请先配置 Tushare Token")
    import tushare as ts

    pro = ts.pro_api(token)
    try:
        open_dates = _latest_open_dates(pro)
        daily_frames: list[pd.DataFrame] = []
        for trade_date in open_dates:
            frame = pro.daily(
                trade_date=trade_date,
                fields="ts_code,trade_date,open,high,low,close,pre_close,pct_chg,vol,amount",
            )
            if frame is not None and not frame.empty:
                daily_frames.append(frame[frame["ts_code"].isin(DEMO_UNIVERSE)])
        if not daily_frames:
            raise RuntimeError("未获取到样本股票日线，请检查 Token 权限")

        prices = pd.concat(daily_frames, ignore_index=True)
        prices["trade_date"] = prices["trade_date"].astype(str)
        prices = prices.sort_values(["ts_code", "trade_date"])
        latest_date = str(prices["trade_date"].max())
        latest = prices[prices["trade_date"] == latest_date].copy()
        try:
            basics = pro.daily_basic(
                trade_date=latest_date,
                fields="ts_code,trade_date,pe_ttm,pb,turnover_rate,total_mv",
            )
        except Exception:
            basics = None
        if basics is not None and not basics.empty:
            latest = latest.merge(basics, on=["ts_code", "trade_date"], how="left")

        try:
            stock_basic = pro.stock_basic(
                exchange="",
                list_status="L",
                fields="ts_code,name,industry,list_date",
            )
        except Exception:
            stock_basic = None
        if stock_basic is not None and not stock_basic.empty:
            latest = latest.merge(stock_basic, on="ts_code", how="left")

        grouped = prices.groupby("ts_code", sort=False)
        metrics = []
        bars: dict[str, list[dict[str, Any]]] = {}
        for symbol, group in grouped:
            group = group.sort_values("trade_date").copy()
            closes = pd.to_numeric(group["close"], errors="coerce")
            returns = closes.pct_change()
            if len(group) < 20 or closes.iloc[-1] <= 0:
                continue
            metrics.append(
                {
                    "ts_code": symbol,
                    "momentum_raw": closes.iloc[-1] / closes.iloc[-20] - 1,
                    "trend_raw": closes.iloc[-1] / closes.rolling(20).mean().iloc[-1] - 1,
                    "risk_raw": returns.tail(20).std(),
                    "liquidity_raw": pd.to_numeric(group["amount"], errors="coerce").tail(10).mean(),
                }
            )
            bars[symbol] = [
                {
                    "date": datetime.strptime(str(row.trade_date), "%Y%m%d").date().isoformat(),
                    "open": round(float(row.open), 2),
                    "high": round(float(row.high), 2),
                    "low": round(float(row.low), 2),
                    "close": round(float(row.close), 2),
                    "volume": int(float(row.vol or 0) * 100),
                }
                for row in group.itertuples()
            ]

        factors = pd.DataFrame(metrics)
        latest = latest.merge(factors, on="ts_code", how="inner")
        latest["trend_rank"] = _percentile(latest["trend_raw"])
        latest["momentum_rank"] = _percentile(latest["momentum_raw"])
        latest["liquidity_rank"] = _percentile(latest["liquidity_raw"])
        latest["low_risk_rank"] = _percentile(latest["risk_raw"], higher_is_better=False)
        pe = pd.to_numeric(latest["pe_ttm"], errors="coerce") if "pe_ttm" in latest else pd.Series(index=latest.index, dtype=float)
        pb = pd.to_numeric(latest["pb"], errors="coerce") if "pb" in latest else pd.Series(index=latest.index, dtype=float)
        latest["value_raw"] = -(pe.where(pe > 0).rank(pct=True).fillna(0.5) + pb.where(pb > 0).rank(pct=True).fillna(0.5))
        latest["value_rank"] = _percentile(latest["value_raw"])

        preliminary = (
            latest["trend_rank"] * 0.30
            + latest["momentum_rank"] * 0.25
            + latest["value_rank"] * 0.15
            + latest["liquidity_rank"] * 0.15
            + latest["low_risk_rank"] * 0.15
        )
        quality_symbols = latest.assign(preliminary=preliminary).nlargest(10, "preliminary")["ts_code"].tolist()
        quality = _quality_scores(pro, quality_symbols)
        latest["quality_rank"] = latest["ts_code"].map(quality).fillna(0.5)
        latest["final_score"] = (
            latest["trend_rank"] * 0.25
            + latest["momentum_rank"] * 0.20
            + latest["quality_rank"] * 0.20
            + latest["value_rank"] * 0.15
            + latest["liquidity_rank"] * 0.10
            + latest["low_risk_rank"] * 0.10
        ) * 100
        latest = latest.sort_values("final_score", ascending=False)

        all_items = []
        for rank, row in enumerate(latest.itertuples(), start=1):
            score = round(float(row.final_score), 1)
            quality_available = row.ts_code in quality
            all_items.append(
                {
                    "signal_id": f"tushare-{row.ts_code.replace('.', '-')}-{latest_date}",
                    "symbol": row.ts_code,
                    "name": getattr(row, "name", None) or row.ts_code,
                    "rank": rank,
                    "side": "重点关注" if rank <= 3 else "关注" if rank <= 10 else "样本观察",
                    "final_score": score,
                    "confidence": round(min(0.88, 0.55 + score / 320), 2),
                    "reference_price": round(float(row.close), 2),
                    "change_pct": round(float(row.pct_chg), 2),
                    "industry": getattr(row, "industry", None) or "未分类",
                    "summary": "Tushare 日线、估值与财务指标生成的轻量多因子推荐。",
                    "positive_reasons": [
                        "20 日趋势和动量处于样本池前列",
                        "估值与流动性满足 Demo 筛选要求",
                        "财务质量已补充" if quality_available else "财务接口不可用，质量因子采用中性分",
                    ],
                    "risk_reasons": ["仅覆盖 Demo 样本股票池", "日频数据不代表盘中实时价格"],
                    "invalidation_conditions": ["收盘价跌破 20 日均线且动量转负"],
                    "scores": {
                        "trend": round(float(row.trend_rank) * 100),
                        "momentum": round(float(row.momentum_rank) * 100),
                        "quality": round(float(row.quality_rank) * 100),
                        "value": round(float(row.value_rank) * 100),
                        "liquidity": round(float(row.liquidity_rank) * 100),
                        "risk": round((1 - float(row.low_risk_rank)) * 100),
                    },
                    "as_of_date": datetime.strptime(latest_date, "%Y%m%d").date().isoformat(),
                    "data_mode": "tushare_direct",
                }
            )
        items = all_items[:10]

        with _TUSHARE_LOCK:
            _TUSHARE_CACHE.update(
                {
                    "items": items,
                    "stocks": {item["symbol"]: item for item in all_items},
                    "bars": bars,
                    "as_of_date": items[0]["as_of_date"] if items else None,
                    "refreshed_at": datetime.now().astimezone().isoformat(timespec="seconds"),
                    "error": None,
                }
            )
        return get_data_source_status()
    except Exception as exc:
        with _TUSHARE_LOCK:
            _TUSHARE_CACHE["error"] = str(exc)
        raise


def _live_recommendations(limit: int) -> list[dict[str, Any]]:
    sql = """
    WITH latest AS (
        SELECT max(trade_date) AS trade_date
        FROM research.alpha_daily_panel
    ),
    eligible AS (
        SELECT
            p.*,
            l.local_symbol,
            i.instrument_name,
            e.exchange_code,
            percent_rank() OVER (ORDER BY coalesce(p.return, -1)) AS momentum_rank,
            percent_rank() OVER (ORDER BY coalesce(p.relative_strength, 0)) AS trend_rank,
            percent_rank() OVER (ORDER BY coalesce(p.quality_score, 0)) AS quality_rank,
            percent_rank() OVER (ORDER BY coalesce(p.value_score, 0)) AS value_rank,
            percent_rank() OVER (ORDER BY coalesce(p.turnover, 0)) AS liquidity_rank,
            percent_rank() OVER (ORDER BY coalesce(p.idio_vol_60d, 1) DESC) AS low_risk_rank
        FROM research.alpha_daily_panel p
        JOIN latest d ON d.trade_date = p.trade_date
        JOIN core.instrument i ON i.asset_id = p.asset_id
        JOIN core.listing l ON l.asset_id = p.asset_id AND l.is_primary
        JOIN core.exchange e ON e.exchange_id = l.exchange_id
        WHERE p.close IS NOT NULL
          AND p.turnover IS NOT NULL
          AND coalesce(p.turnover, 0) > 0
          AND (l.listed_date IS NULL OR l.listed_date <= p.trade_date - 120)
    ),
    ranked AS (
        SELECT *,
            (
                trend_rank * 0.25 +
                momentum_rank * 0.20 +
                quality_rank * 0.20 +
                value_rank * 0.15 +
                liquidity_rank * 0.10 +
                low_risk_rank * 0.10
            ) * 100 AS final_score
        FROM eligible
    )
    SELECT *
    FROM ranked
    ORDER BY final_score DESC
    LIMIT %s
    """
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (limit,))
            columns = [item.name for item in cur.description]
            rows = [dict(zip(columns, row)) for row in cur.fetchall()]

    output: list[dict[str, Any]] = []
    for rank, row in enumerate(rows, start=1):
        exchange = str(row.get("exchange_code") or "")
        suffix = {"SSE": "SH", "SZSE": "SZ", "BSE": "BJ"}.get(exchange, exchange)
        symbol = f"{row.get('local_symbol')}.{suffix}"
        score = round(float(row.get("final_score") or 0), 1)
        output.append(
            {
                "signal_id": f"live-{row['asset_id']}-{row['trade_date']}",
                "symbol": symbol,
                "name": row.get("instrument_name") or symbol,
                "rank": rank,
                "side": "重点关注" if score >= 82 else "关注",
                "final_score": score,
                "confidence": round(min(0.9, 0.55 + score / 300), 2),
                "reference_price": float(row.get("close") or 0),
                "change_pct": round(float(row.get("return") or 0) * 100, 2),
                "industry": "待补充",
                "summary": "由趋势、动量、质量、估值、流动性和风险六个维度综合生成。",
                "positive_reasons": [
                    "趋势与相对强度排名靠前",
                    "质量和估值因子提供支持",
                    "流动性满足 Demo 股票池要求",
                ],
                "risk_reasons": ["模型仅使用日频数据", "需关注下一交易日量价确认"],
                "invalidation_conditions": ["趋势和动量得分同步跌出候选区间"],
                "scores": {
                    "trend": round(_score(row.get("trend_rank")) * 100),
                    "momentum": round(_score(row.get("momentum_rank")) * 100),
                    "quality": round(_score(row.get("quality_rank")) * 100),
                    "value": round(_score(row.get("value_rank")) * 100),
                    "liquidity": round(_score(row.get("liquidity_rank")) * 100),
                    "risk": round((1 - _score(row.get("low_risk_rank"))) * 100),
                },
                "as_of_date": str(row.get("trade_date")),
                "data_mode": "live",
            }
        )
    return output


def get_recommendations(limit: int = 10) -> dict[str, Any]:
    mode = os.getenv("DATA_SOURCE_MODE", "tushare_direct").strip().lower()
    with _TUSHARE_LOCK:
        cached_stocks = list(_TUSHARE_CACHE["stocks"].values())
        cached = [dict(item) for item in cached_stocks[:limit]]
    recommendations = cached
    if recommendations:
        as_of_date = recommendations[0]["as_of_date"]
        data_mode = "tushare_direct"
    elif mode == "postgres":
        try:
            recommendations = _live_recommendations(limit)
        except Exception:
            recommendations = []
    if recommendations:
        as_of_date = recommendations[0]["as_of_date"]
        data_mode = recommendations[0].get("data_mode", "live")
    else:
        recommendations = [dict(item) for item in DEMO_RECOMMENDATIONS[:limit]]
        as_of_date = DEMO_AS_OF_DATE.isoformat()
        data_mode = "demo_snapshot"
        for item in recommendations:
            item["as_of_date"] = as_of_date
            item["data_mode"] = data_mode
    return {
        "as_of_date": as_of_date,
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "strategy_version": "a_share_demo_v1",
        "data_mode": data_mode,
        "items": recommendations,
    }


def get_recommendation(signal_id: str) -> dict[str, Any] | None:
    payload = get_recommendations(30)
    return next((item for item in payload["items"] if item["signal_id"] == signal_id), None)


def get_stock_snapshot(symbol: str) -> dict[str, Any] | None:
    normalized = symbol.upper()
    with _TUSHARE_LOCK:
        cached = _TUSHARE_CACHE["stocks"].get(normalized)
    if cached:
        item = dict(cached)
    else:
        item = next((dict(row) for row in DEMO_RECOMMENDATIONS if row["symbol"] == normalized), None)
    if not item:
        return None
    bars = get_stock_bars(normalized, 35)["bars"]
    closes = [float(row["close"]) for row in bars if row.get("close") is not None]
    tracking = {
        "period_return_pct": None,
        "ma20": None,
        "price_vs_ma20_pct": None,
        "period_high": None,
        "period_low": None,
        "tracking_status": "数据不足",
    }
    if len(closes) >= 20:
        latest = closes[-1]
        ma20 = sum(closes[-20:]) / 20
        period_return = (latest / closes[0] - 1) * 100 if closes[0] else 0
        deviation = (latest / ma20 - 1) * 100 if ma20 else 0
        tracking = {
            "period_return_pct": round(period_return, 2),
            "ma20": round(ma20, 2),
            "price_vs_ma20_pct": round(deviation, 2),
            "period_high": round(max(closes), 2),
            "period_low": round(min(closes), 2),
            "tracking_status": "趋势偏强" if deviation > 2 else "趋势偏弱" if deviation < -2 else "震荡观察",
        }
    item["tracking"] = tracking
    item["in_watchlist"] = normalized in _WATCHLIST
    return item


def search_stocks(query: str, limit: int = 12) -> list[dict[str, Any]]:
    keyword = query.strip().upper()
    if not keyword:
        return []
    with _TUSHARE_LOCK:
        universe = list(_TUSHARE_CACHE["stocks"].values())
    if not universe:
        universe = DEMO_RECOMMENDATIONS
    matches = [
        item
        for item in universe
        if keyword in item["symbol"].upper() or keyword in str(item.get("name") or "").upper()
    ]
    return [
        {
            "symbol": item["symbol"],
            "name": item.get("name") or item["symbol"],
            "industry": item.get("industry") or "未分类",
            "rank": item.get("rank"),
            "final_score": item.get("final_score"),
            "reference_price": item.get("reference_price"),
            "change_pct": item.get("change_pct"),
            "in_watchlist": item["symbol"] in _WATCHLIST,
        }
        for item in matches[:limit]
    ]


def get_dashboard() -> dict[str, Any]:
    recommendations = get_recommendations(10)
    return {
        "market": {
            "label": "A 股",
            "status": "收盘后数据",
            "breadth": "结构性机会",
            "risk_level": "中等",
        },
        "recommendations": recommendations,
        "latest_reports": get_reports(),
        "watchlist_count": len(_WATCHLIST),
    }


def get_stock_bars(symbol: str, days: int = 90) -> dict[str, Any]:
    with _TUSHARE_LOCK:
        cached_bars = list(_TUSHARE_CACHE["bars"].get(symbol, []))
    if cached_bars:
        return {"symbol": symbol, "data_mode": "tushare_direct", "bars": cached_bars[-days:]}
    base = next(
        (item["reference_price"] for item in DEMO_RECOMMENDATIONS if item["symbol"] == symbol),
        100.0,
    )
    start = DEMO_AS_OF_DATE - timedelta(days=days * 2)
    value = float(base) * 0.88
    bars = []
    cursor = start
    index = 0
    while len(bars) < days:
        if cursor.weekday() < 5:
            drift = math.sin(index / 7) * 0.008 + 0.0012
            open_price = value * (1 + math.sin(index) * 0.003)
            close = max(1.0, open_price * (1 + drift))
            bars.append(
                {
                    "date": cursor.isoformat(),
                    "open": round(open_price, 2),
                    "high": round(max(open_price, close) * 1.008, 2),
                    "low": round(min(open_price, close) * 0.992, 2),
                    "close": round(close, 2),
                    "volume": int(1_000_000 * (1.0 + abs(math.sin(index / 5)))),
                }
            )
            value = close
            index += 1
        cursor += timedelta(days=1)
    return {"symbol": symbol, "data_mode": "demo_snapshot", "bars": bars}


def _load_watchlist() -> set[str]:
    try:
        payload = json.loads(WATCHLIST_PATH.read_text(encoding="utf-8"))
        return {str(symbol).upper() for symbol in payload if str(symbol).strip()}
    except (FileNotFoundError, json.JSONDecodeError, TypeError):
        return {"600519.SH", "300750.SZ"}


def _save_watchlist() -> None:
    WATCHLIST_PATH.parent.mkdir(parents=True, exist_ok=True)
    temp_path = WATCHLIST_PATH.with_suffix(".tmp")
    temp_path.write_text(json.dumps(sorted(_WATCHLIST), ensure_ascii=False, indent=2), encoding="utf-8")
    temp_path.replace(WATCHLIST_PATH)


_WATCHLIST: set[str] = _load_watchlist()


def get_watchlist() -> list[dict[str, Any]]:
    items = []
    for symbol in sorted(_WATCHLIST):
        snapshot = get_stock_snapshot(symbol)
        if snapshot:
            items.append(snapshot)
        else:
            items.append(
                {
                    "symbol": symbol,
                    "name": symbol,
                    "reference_price": None,
                    "change_pct": None,
                    "rank": None,
                    "final_score": None,
                    "tracking": {"tracking_status": "等待数据"},
                    "in_watchlist": True,
                }
            )
    return items


def add_watchlist(symbol: str) -> list[dict[str, Any]]:
    normalized = symbol.upper()
    if not get_stock_snapshot(normalized):
        raise ValueError("当前样本池中未找到该股票，请输入完整代码，例如 600519.SH")
    _WATCHLIST.add(normalized)
    _save_watchlist()
    return get_watchlist()


def remove_watchlist(symbol: str) -> list[dict[str, Any]]:
    _WATCHLIST.discard(symbol.upper())
    _save_watchlist()
    return get_watchlist()


def get_reports() -> list[dict[str, Any]]:
    return [
        {
            "report_id": "demo-pre-market",
            "report_type": "pre_market",
            "title": "A 股盘前关注摘要",
            "summary": "关注高质量龙头、盈利修复和相对强势方向，避免追逐缺少成交确认的短期异动。",
            "as_of_time": f"{DEMO_AS_OF_DATE.isoformat()}T08:30:00+08:00",
            "data_mode": "demo_snapshot",
        },
        {
            "report_id": "demo-post-market",
            "report_type": "post_market",
            "title": "A 股盘后复盘",
            "summary": "推荐池整体表现平稳，新能源和高质量消费方向相对活跃，次日重点观察量价延续。",
            "as_of_time": f"{DEMO_AS_OF_DATE.isoformat()}T16:30:00+08:00",
            "data_mode": "demo_snapshot",
        },
    ]


def send_wecom_test(symbol: str) -> dict[str, Any]:
    webhook = os.getenv("WECOM_WEBHOOK_URL", "").strip()
    title = f"Demo 提醒：{symbol}"
    content = f"{symbol} 触发模拟关键位置提醒。该消息用于 AI 量化投资助手 Demo，不构成投资建议。"
    if not webhook:
        return {"status": "simulated", "title": title, "content": content}
    body = json.dumps(
        {"msgtype": "markdown", "markdown": {"content": f"**{title}**\n\n{content}"}},
        ensure_ascii=False,
    ).encode("utf-8")
    request = urllib.request.Request(webhook, data=body, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            provider_response = json.loads(response.read().decode("utf-8"))
        return {"status": "sent", "title": title, "content": content, "provider_response": provider_response}
    except Exception as exc:  # noqa: BLE001
        return {"status": "failed", "title": title, "content": content, "error": str(exc)}


KNOWLEDGE_BASE = [
    {
        "title": "多因子推荐方法",
        "keywords": ["推荐", "选股", "因子", "评分", "为什么"],
        "content": "Demo 使用趋势、动量、质量、估值、流动性和风险六个维度综合排序，不使用未来收益标签。",
    },
    {
        "title": "风险与失效条件",
        "keywords": ["风险", "止损", "失效", "回撤"],
        "content": "推荐不是买入指令。应同时观察风险原因和失效条件，并结合仓位、流动性与个人风险承受能力。",
    },
    {
        "title": "数据口径",
        "keywords": ["数据", "日期", "tushare", "实时", "延迟"],
        "content": "推荐按最近可用交易日日频数据生成。页面会明确显示 live 或 demo_snapshot，避免把快照误认为实时行情。",
    },
]


def _find_stock_context(message: str, symbol: str | None) -> dict[str, Any] | None:
    match = re.search(r"\b(\d{6}\.(?:SH|SZ|BJ))\b", message.upper())
    normalized = match.group(1) if match else (symbol or "").upper()
    candidates = get_recommendations(30)["items"]
    with _TUSHARE_LOCK:
        cached_stocks = list(_TUSHARE_CACHE["stocks"].values())
    candidates = cached_stocks or candidates
    return next(
        (
            item
            for item in candidates
            if item["symbol"] == normalized or item["name"] in message
        ),
        None,
    )


def _technical_context(stock: dict[str, Any] | None) -> dict[str, Any] | None:
    if not stock:
        return None
    bars_payload = get_stock_bars(stock["symbol"], days=35)
    bars = bars_payload.get("bars") or []
    closes = [float(item["close"]) for item in bars if item.get("close") is not None]
    technical: dict[str, Any] = {
        "symbol": stock["symbol"],
        "as_of_date": stock.get("as_of_date"),
        "data_mode": stock.get("data_mode"),
        "reference_price": stock.get("reference_price"),
        "daily_change_pct": stock.get("change_pct"),
        "factor_scores": stock.get("scores") or {},
    }
    if len(closes) >= 20:
        latest = closes[-1]
        ma20 = sum(closes[-20:]) / 20
        technical.update(
            {
                "bar_count": len(closes),
                "ma20": round(ma20, 2),
                "price_vs_ma20_pct": round((latest / ma20 - 1) * 100, 2) if ma20 else None,
                "period_return_pct": round((latest / closes[0] - 1) * 100, 2) if closes[0] else None,
                "period_high": round(max(closes), 2),
                "period_low": round(min(closes), 2),
            }
        )
    return technical


def _knowledge_context(message: str) -> list[dict[str, str]]:
    matched = [
        item
        for item in KNOWLEDGE_BASE
        if any(keyword.lower() in message.lower() for keyword in item["keywords"])
    ]
    return matched[:2] or KNOWLEDGE_BASE[:1]


def _fallback_chat(
    message: str,
    stock: dict[str, Any] | None,
    knowledge: list[dict[str, str]],
    technical: dict[str, Any] | None,
) -> str:
    if stock:
        reasons = "；".join(stock["positive_reasons"][:3])
        risks = "；".join(stock["risk_reasons"][:2])
        invalidations = "；".join(stock["invalidation_conditions"][:2])
        trend = ""
        if technical and technical.get("ma20") is not None:
            trend = (
                f" 最近 {technical['bar_count']} 个交易日收益约 {technical['period_return_pct']}%，"
                f"最新价相对 20 日均线 {technical['price_vs_ma20_pct']}%。"
            )
        return (
            f"{stock['name']}（{stock['symbol']}）当前综合得分 {stock['final_score']}，"
            f"推荐级别为“{stock['side']}”。主要依据：{reasons}。"
            f"需要重点关注：{risks}。判断失效条件：{invalidations}。{trend}"
            f" 数据日期为 {stock['as_of_date']}，模式为 {stock['data_mode']}。"
            "以上为研究辅助结论，不构成投资建议。"
        )
    return (
        f"{knowledge[0]['content']} "
        "你可以继续询问某只推荐股票，例如“贵州茅台为什么被推荐”或“600519.SH 有哪些风险”。"
    )


def answer_demo_chat(message: str, symbol: str | None = None) -> dict[str, Any]:
    stock = _find_stock_context(message, symbol)
    technical = _technical_context(stock)
    knowledge = _knowledge_context(message)
    citations = [{"title": item["title"], "source": "内置 Demo 知识库"} for item in knowledge]
    if stock:
        citations.insert(
            0,
            {
                "title": f"{stock['name']}行情与因子",
                "source": f"Tushare / {stock['as_of_date']} / {stock['data_mode']}",
            },
        )

    api_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
    if not api_key:
        return {
            "answer": _fallback_chat(message, stock, knowledge, technical),
            "mode": "rules",
            "symbol": stock["symbol"] if stock else None,
            "citations": citations,
        }

    context = {
        "stock": stock,
        "technical": technical,
        "knowledge": knowledge,
        "rules": [
            "只根据给定上下文回答",
            "明确数据日期和数据模式",
            "不承诺收益，不给出确定性买卖指令",
            "使用简洁中文",
        ],
    }
    body = json.dumps(
        {
            "model": os.getenv("DEMO_CHAT_MODEL", os.getenv("DEEPSEEK_MODEL", "deepseek-chat")),
            "messages": [
                {
                    "role": "system",
                    "content": "你是 AI 量化投资助手 Demo。回答必须可解释、克制，并提示不构成投资建议。",
                },
                {"role": "user", "content": f"上下文：{json.dumps(context, ensure_ascii=False)}\n问题：{message}"},
            ],
            "temperature": 0.2,
        },
        ensure_ascii=False,
    ).encode("utf-8")
    request = urllib.request.Request(
        os.getenv("DEEPSEEK_API_BASE", "https://api.deepseek.com/chat/completions"),
        data=body,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))
        answer = payload["choices"][0]["message"]["content"].strip()
        return {
            "answer": answer,
            "mode": "deepseek",
            "symbol": stock["symbol"] if stock else None,
            "citations": citations,
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "answer": _fallback_chat(message, stock, knowledge, technical),
            "mode": "rules_fallback",
            "symbol": stock["symbol"] if stock else None,
            "citations": citations,
            "warning": str(exc),
        }
