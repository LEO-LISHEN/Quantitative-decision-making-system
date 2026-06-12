from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any


ROOT_DIR = Path(__file__).resolve().parents[1]
CHINA_TZ = timezone(timedelta(hours=8))
EASTERN_TZ = timezone(timedelta(hours=-4))

MARKETS: dict[str, dict[str, Any]] = {
    "a_share": {
        "label": "A股",
        "timezone": CHINA_TZ,
        "refresh_times": ["09:15", "12:45"],
        "queries": [
            "A股 重大公告 OR 业绩预告 OR 回购",
            "证监会 央行 财政部 资本市场 政策",
            "沪深 股市 产业政策 大宗商品 汇率",
        ],
    },
    "hk_share": {
        "label": "港股",
        "timezone": CHINA_TZ,
        "refresh_times": ["09:15", "12:45"],
        "queries": ["港股 重大公告 业绩", "香港 金管局 股市 政策", "恒生 科技 公司 新闻"],
    },
    "us_share": {
        "label": "美股",
        "timezone": EASTERN_TZ,
        "refresh_times": ["09:15", "12:45"],
        "queries": ["US stocks earnings guidance", "Nasdaq NYSE company material news", "Federal Reserve inflation stocks market"],
    },
}


@dataclass
class EventFocusConfig:
    api_key: str = ""
    api_base: str = "https://api.deepseek.com/chat/completions"
    model: str = "deepseek-chat"
    timeout_seconds: int = 45
    max_source_items: int = 18
    max_cards: int = 6
    cache_seconds: int = 1800


@dataclass
class MarketCache:
    payload: dict[str, Any] | None = None
    refreshed_at: float = 0
    refresh_slot: str = ""
    error: str = ""
    source_count: int = 0


@dataclass
class EventFocusService:
    config: EventFocusConfig = field(default_factory=lambda: load_config(ROOT_DIR))
    cache: dict[str, MarketCache] = field(default_factory=lambda: {market: MarketCache() for market in MARKETS})

    def get_focus(self, market: str, force: bool = False) -> dict[str, Any]:
        if market not in MARKETS:
            raise ValueError(f"Unsupported market: {market}")

        cache = self.cache[market]
        slot = current_refresh_slot(market)
        is_stale = (time.time() - cache.refreshed_at) > self.config.cache_seconds
        should_refresh = force or cache.payload is None or is_stale or cache.refresh_slot != slot
        if not should_refresh and cache.payload:
            return cache.payload

        items = fetch_market_items(market, self.config.max_source_items)
        cache.source_count = len(items)
        payload = self._analyze_market(market, items)
        cache.payload = payload
        cache.refreshed_at = time.time()
        cache.refresh_slot = slot
        cache.error = ""
        return payload

    def _analyze_market(self, market: str, items: list[dict[str, str]]) -> dict[str, Any]:
        meta = MARKETS[market]
        if not self.config.api_key:
            return fallback_payload(market, items, "DeepSeek API key is not configured.")

        messages = [
            {
                "role": "system",
                "content": (
                    "你是一个交易事件聚焦助手。你的任务不是写长报告，而是从新闻和公告候选池中筛选当前最值得关注的市场事件。"
                    "必须只输出 JSON，不要 Markdown。"
                ),
            },
            {
                "role": "user",
                "content": build_prompt(meta["label"], items, self.config.max_cards),
            },
        ]
        try:
            content = call_deepseek(self.config, messages)
            data = parse_json_object(content)
            cards = normalize_cards(data.get("cards", []), self.config.max_cards)
            if not cards:
                return fallback_payload(market, items, "DeepSeek returned no cards.")
            return {
                "market": market,
                "market_label": meta["label"],
                "status": "ready",
                "generated_at": now_iso(),
                "next_refresh_hint": next_refresh_hint(market),
                "source_count": len(items),
                "cards": cards,
                "overview": build_overview(cards),
                "summary": str(data.get("summary") or f"{meta['label']}事件聚焦已更新。"),
                "error": "",
            }
        except Exception as exc:  # noqa: BLE001
            return fallback_payload(market, items, str(exc))


def load_config(root_dir: Path) -> EventFocusConfig:
    load_env_file(root_dir / ".env")
    load_env_file(root_dir / "Event Focus" / ".env")
    load_env_file(root_dir / "Financial Analyst Skills" / ".env")
    return EventFocusConfig(
        api_key=os.getenv("DEEPSEEK_API_KEY", ""),
        api_base=os.getenv("DEEPSEEK_API_BASE", "https://api.deepseek.com/chat/completions"),
        model=os.getenv("EVENT_FOCUS_MODEL", os.getenv("DEMO_CHAT_MODEL", os.getenv("DEEPSEEK_MODEL", "deepseek-chat"))),
        timeout_seconds=int(os.getenv("EVENT_FOCUS_TIMEOUT_SECONDS", "45")),
        max_source_items=int(os.getenv("EVENT_FOCUS_MAX_SOURCE_ITEMS", "18")),
        max_cards=int(os.getenv("EVENT_FOCUS_MAX_CARDS", "6")),
        cache_seconds=int(os.getenv("EVENT_FOCUS_CACHE_SECONDS", "1800")),
    )


def load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def fetch_market_items(market: str, limit: int) -> list[dict[str, str]]:
    urls = configured_source_urls(market) or default_source_urls(market)
    items: list[dict[str, str]] = []
    seen: set[str] = set()
    for url in urls:
        for item in fetch_rss_items(url):
            key = normalize_title(item.get("title", ""))
            if not key or key in seen:
                continue
            seen.add(key)
            items.append(item)
    items.sort(key=lambda item: item.get("published_iso", ""), reverse=True)
    return items[:limit]


def configured_source_urls(market: str) -> list[str]:
    env_name = f"EVENT_FOCUS_{market.upper()}_URLS"
    raw_value = os.getenv(env_name, "")
    return [item.strip() for item in raw_value.split(",") if item.strip()]


def default_source_urls(market: str) -> list[str]:
    return [google_news_rss(query) for query in MARKETS[market]["queries"]]


def google_news_rss(query: str) -> str:
    encoded = urllib.parse.quote(query)
    return f"https://news.google.com/rss/search?q={encoded}&hl=zh-CN&gl=CN&ceid=CN:zh-Hans"


def fetch_rss_items(url: str) -> list[dict[str, str]]:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "QDS-Event-Focus/0.1",
            "Accept": "application/rss+xml, application/xml, text/xml, */*",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=12) as response:
            raw = response.read(1_500_000)
    except (urllib.error.URLError, TimeoutError):
        return []

    try:
        root = ET.fromstring(raw)
    except ET.ParseError:
        return []

    parsed: list[dict[str, str]] = []
    for node in root.findall(".//item")[:30]:
        title = text_of(node, "title")
        link = text_of(node, "link")
        published_at = text_of(node, "pubDate")
        description = strip_html(text_of(node, "description"))
        source = text_of(node, "source")
        if title:
            parsed.append(
                {
                    "title": title,
                    "link": link,
                    "published_at": published_at,
                    "published_iso": normalize_published_at(published_at),
                    "summary": description[:360],
                    "source": source or host_from_url(link),
                }
            )
    return parsed


def text_of(node: ET.Element, tag: str) -> str:
    child = node.find(tag)
    return "".join(child.itertext()).strip() if child is not None else ""


def strip_html(value: str) -> str:
    value = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def host_from_url(url: str) -> str:
    try:
        return urllib.parse.urlparse(url).netloc
    except Exception:  # noqa: BLE001
        return ""


def normalize_title(value: str) -> str:
    value = re.sub(r"\s*[-–—]\s*[^-–—]{2,30}$", "", value)
    return re.sub(r"[\W_]+", "", value).lower()


def normalize_published_at(value: str) -> str:
    if not value:
        return ""
    try:
        parsed = parsedate_to_datetime(value)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(CHINA_TZ).isoformat(timespec="minutes")
    except (TypeError, ValueError, OverflowError):
        return value


def build_prompt(market_label: str, items: list[dict[str, str]], max_cards: int) -> str:
    compact_items = [
        {
            "title": item.get("title", ""),
            "source": item.get("source", ""),
            "published_at": item.get("published_at", ""),
            "published_iso": item.get("published_iso", ""),
            "summary": item.get("summary", ""),
            "link": item.get("link", ""),
        }
        for item in items
    ]
    return (
        f"市场：{market_label}\n"
        f"请从以下候选新闻/公告中选出最多 {max_cards} 条最值得交易员关注的信息。\n"
        "优先选择影响范围广、信息新、来源明确、存在可验证后续节点的事件；合并重复事件，不得编造股票代码或事实。\n"
        "输出 JSON 格式："
        '{"summary":"一句话市场焦点","cards":[{"title":"短标题","market":"市场","priority":"高/中/低",'
        '"category":"公告/政策/业绩/资金/风险/宏观/产业","why_it_matters":"为什么重要，80字内",'
        '"impact_direction":"利多/利空/中性/分化","affected_assets":["行业、指数或股票代码"],'
        '"horizon":"盘中/1-3日/1-4周/中长期","confidence":0.0,'
        '"watch_points":["可验证观察点1","可验证观察点2"],"source":"来源",'
        '"published_at":"优先使用published_iso","url":"链接"}]}\n'
        "候选信息：\n"
        f"{json.dumps(compact_items, ensure_ascii=False)}"
    )


def call_deepseek(config: EventFocusConfig, messages: list[dict[str, str]]) -> str:
    body = json.dumps(
        {
            "model": config.model,
            "messages": messages,
            "temperature": 0.2,
            "max_tokens": 2400,
            "response_format": {"type": "json_object"},
        },
        ensure_ascii=False,
    ).encode("utf-8")
    request = urllib.request.Request(
        config.api_base,
        data=body,
        headers={
            "Authorization": f"Bearer {config.api_key}",
            "Content-Type": "application/json",
            "User-Agent": "QDS-Event-Focus/0.1",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=config.timeout_seconds) as response:
        payload = json.loads(response.read().decode("utf-8"))
    return str(payload["choices"][0]["message"]["content"])


def parse_json_object(content: str) -> dict[str, Any]:
    content = content.strip()
    if content.startswith("```"):
        content = re.sub(r"^```(?:json)?", "", content).strip()
        content = re.sub(r"```$", "", content).strip()
    return json.loads(content)


def normalize_cards(cards: list[Any], max_cards: int) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for raw in cards[:max_cards]:
        if not isinstance(raw, dict):
            continue
        normalized.append(
            {
                "title": str(raw.get("title") or "未命名事件"),
                "market": str(raw.get("market") or ""),
                "priority": str(raw.get("priority") or "中"),
                "category": str(raw.get("category") or "事件"),
                "why_it_matters": str(raw.get("why_it_matters") or ""),
                "impact_direction": normalize_choice(raw.get("impact_direction"), {"利多", "利空", "中性", "分化"}, "中性"),
                "affected_assets": [str(item) for item in raw.get("affected_assets", [])[:5]],
                "horizon": normalize_choice(raw.get("horizon"), {"盘中", "1-3日", "1-4周", "中长期"}, "1-3日"),
                "confidence": normalize_confidence(raw.get("confidence")),
                "watch_points": [str(item) for item in raw.get("watch_points", [])[:3]],
                "source": str(raw.get("source") or ""),
                "published_at": str(raw.get("published_at") or ""),
                "url": str(raw.get("url") or ""),
            }
        )
    return normalized


def normalize_choice(value: Any, allowed: set[str], default: str) -> str:
    text = str(value or "").strip()
    return text if text in allowed else default


def normalize_confidence(value: Any) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0.5
    return round(max(0.0, min(1.0, number)), 2)


def build_overview(cards: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "high_priority_count": sum(card["priority"] == "高" for card in cards),
        "bullish_count": sum(card["impact_direction"] == "利多" for card in cards),
        "bearish_count": sum(card["impact_direction"] == "利空" for card in cards),
        "categories": sorted({card["category"] for card in cards}),
    }


def fallback_payload(market: str, items: list[dict[str, str]], error: str) -> dict[str, Any]:
    meta = MARKETS[market]
    cards = [
        {
            "title": item.get("title", "待筛选事件"),
            "market": meta["label"],
            "priority": "中",
            "category": "新闻",
            "why_it_matters": item.get("summary") or "DeepSeek 暂不可用，当前显示原始候选信息。",
            "impact_direction": "中性",
            "affected_assets": [],
            "horizon": "1-3日",
            "confidence": 0.35,
            "watch_points": ["等待模型完成重要性排序", "检查来源与发布时间"],
            "source": item.get("source", ""),
            "published_at": item.get("published_at", ""),
            "url": item.get("link", ""),
        }
        for item in items[:6]
    ]
    return {
        "market": market,
        "market_label": meta["label"],
        "status": "degraded",
        "generated_at": now_iso(),
        "next_refresh_hint": next_refresh_hint(market),
        "source_count": len(items),
        "cards": cards,
        "overview": build_overview(cards),
        "summary": f"{meta['label']}事件候选已更新，但模型筛选未完成。",
        "error": error,
    }


def now_iso() -> str:
    return datetime.now(CHINA_TZ).isoformat(timespec="seconds")


def current_refresh_slot(market: str) -> str:
    meta = MARKETS[market]
    local_now = datetime.now(meta["timezone"])
    current = "pre-open"
    for value in meta["refresh_times"]:
        hour, minute = [int(part) for part in value.split(":")]
        slot_time = local_now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if local_now >= slot_time:
            current = value
    return f"{local_now.date()} {current}"


def next_refresh_hint(market: str) -> str:
    meta = MARKETS[market]
    local_now = datetime.now(meta["timezone"])
    for value in meta["refresh_times"]:
        hour, minute = [int(part) for part in value.split(":")]
        slot_time = local_now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if local_now < slot_time:
            return f"{meta['label']}下一次计划刷新：{slot_time.strftime('%Y-%m-%d %H:%M')}"
    tomorrow = local_now + timedelta(days=1)
    first_hour, first_minute = [int(part) for part in meta["refresh_times"][0].split(":")]
    slot_time = tomorrow.replace(hour=first_hour, minute=first_minute, second=0, microsecond=0)
    return f"{meta['label']}下一次计划刷新：{slot_time.strftime('%Y-%m-%d %H:%M')}"
