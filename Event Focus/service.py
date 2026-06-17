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
        "queries": ["A股 公告 财经", "沪深 股市 重要公告", "中国 资本市场 政策 财经"],
    },
    "hk_share": {
        "label": "港股",
        "timezone": CHINA_TZ,
        "refresh_times": ["09:15", "12:45"],
        "queries": ["港股 公告 财经", "香港 股市 公司公告", "恒生 科技 股市 新闻"],
    },
    "us_share": {
        "label": "美股",
        "timezone": EASTERN_TZ,
        "refresh_times": ["09:15", "12:45"],
        "queries": ["US stocks earnings market news", "Nasdaq NYSE company news", "Federal Reserve stocks market"],
    },
}

CATEGORY_ORDER = [
    "政策监管",
    "宏观流动性",
    "产业趋势",
    "公司公告",
    "业绩预期",
    "资金流向",
    "市场情绪",
    "估值重定价",
    "供需变化",
    "地缘与外部冲击",
    "交易结构",
    "风险暴露",
    "其他事件",
]


@dataclass
class EventFocusConfig:
    api_key: str = ""
    api_base: str = "https://api.deepseek.com/chat/completions"
    model: str = "deepseek-v4-flash"
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
            groups = group_cards(cards)
            return {
                "market": market,
                "market_label": meta["label"],
                "status": "ready",
                "generated_at": now_iso(),
                "next_refresh_hint": next_refresh_hint(market),
                "source_count": len(items),
                "cards": cards,
                "groups": groups,
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
        model=os.getenv("EVENT_FOCUS_MODEL", os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash")),
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
            key = item.get("link") or item.get("title") or ""
            if not key or key in seen:
                continue
            seen.add(key)
            items.append(item)
            if len(items) >= limit:
                return items
    return items


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


def build_prompt(market_label: str, items: list[dict[str, str]], max_cards: int) -> str:
    compact_items = [
        {
            "title": item.get("title", ""),
            "source": item.get("source", ""),
            "published_at": item.get("published_at", ""),
            "summary": item.get("summary", ""),
            "link": item.get("link", ""),
        }
        for item in items
    ]
    return (
        f"市场：{market_label}\n"
        f"请从以下候选新闻/公告中选出最多 {max_cards} 条最值得交易员关注的信息。\n"
        "输出 JSON 格式："
        '{"summary":"一句话市场焦点","cards":[{"title":"短标题","market":"市场","priority":"高/中/低",'
        '"category":"政策监管/宏观流动性/产业趋势/公司公告/业绩预期/资金流向/市场情绪/估值重定价/供需变化/地缘与外部冲击/交易结构/风险暴露/其他事件",'
        '"impact_path":"盈利/估值/流动性/风险偏好/供需/监管/交易结构/其他","time_horizon":"短期/中期/长期",'
        '"affected_assets":["行业/指数/个股"],"market_impact":"利多/利空/分化/待确认","why_it_matters":"为什么重要，80字内",'
        '"watch_points":["观察点1","观察点2"],"source":"来源","published_at":"时间","url":"链接"}]}\n'
        "要求：尽量覆盖不同类别，不要把所有信息都塞进同一类别；同一类别可返回多条卡片。\n"
        "候选信息：\n"
        f"{json.dumps(compact_items, ensure_ascii=False)}"
    )


def call_deepseek(config: EventFocusConfig, messages: list[dict[str, str]]) -> str:
    body = json.dumps(
        {
            "model": config.model,
            "messages": messages,
            "temperature": 0.2,
            "thinking": {"type": "disabled"},
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
                "category": normalize_category(str(raw.get("category") or "其他事件")),
                "impact_path": str(raw.get("impact_path") or "其他"),
                "time_horizon": str(raw.get("time_horizon") or "短期"),
                "affected_assets": [str(item) for item in raw.get("affected_assets", [])[:4]],
                "market_impact": str(raw.get("market_impact") or "待确认"),
                "why_it_matters": str(raw.get("why_it_matters") or ""),
                "watch_points": [str(item) for item in raw.get("watch_points", [])[:3]],
                "source": str(raw.get("source") or ""),
                "published_at": str(raw.get("published_at") or ""),
                "url": str(raw.get("url") or ""),
            }
        )
    return normalized


def fallback_payload(market: str, items: list[dict[str, str]], error: str) -> dict[str, Any]:
    meta = MARKETS[market]
    cards = [
        {
            "title": item.get("title", "待筛选事件"),
            "market": meta["label"],
            "priority": "中",
            "category": "其他事件",
            "impact_path": "其他",
            "time_horizon": "短期",
            "affected_assets": [meta["label"]],
            "market_impact": "待确认",
            "why_it_matters": item.get("summary") or "DeepSeek 暂不可用，当前显示原始候选信息。",
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
        "groups": group_cards(cards),
        "summary": f"{meta['label']}事件候选已更新，但模型筛选未完成。",
        "error": error,
    }


def normalize_category(value: str) -> str:
    value = value.strip()
    aliases = {
        "公告": "公司公告",
        "政策": "政策监管",
        "宏观": "宏观流动性",
        "业绩": "业绩预期",
        "资金": "资金流向",
        "风险": "风险暴露",
        "产业": "产业趋势",
        "情绪": "市场情绪",
    }
    normalized = aliases.get(value, value)
    return normalized if normalized in CATEGORY_ORDER else "其他事件"


def group_cards(cards: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for card in cards:
        grouped.setdefault(card["category"], []).append(card)

    groups: list[dict[str, Any]] = []
    for category in CATEGORY_ORDER:
        if category not in grouped:
            continue
        groups.append(
            {
                "category": category,
                "count": len(grouped[category]),
                "cards": grouped[category],
            }
        )
    return groups


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
