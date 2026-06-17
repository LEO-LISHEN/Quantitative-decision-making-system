from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


ROOT_DIR = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class TechnicalAnalysisConfig:
    api_key: str = ""
    api_base: str = "https://api.openai.com/v1"
    model: str = "gpt-4.1-mini"
    timeout_seconds: int = 90
    max_output_tokens: int = 1800


@dataclass
class TechnicalAnalysisService:
    config: TechnicalAnalysisConfig = field(default_factory=lambda: load_config(ROOT_DIR))

    def is_configured(self) -> bool:
        self.config = load_config(ROOT_DIR)
        return bool(self.config.api_key)

    def analyze(
        self,
        *,
        message: str,
        image_data_url: str | None = None,
        image_data_urls: list[str] | None = None,
        history: list[dict[str, Any]] | None = None,
    ) -> dict[str, str]:
        self.config = load_config(ROOT_DIR)
        if not self.config.api_key:
            raise RuntimeError("Missing OPENAI_API_KEY in .env")

        normalized_images = validate_image_data_urls(image_data_urls or [], image_data_url)
        content: list[dict[str, Any]] = [
            {
                "type": "input_text",
                "text": build_prompt(message=message, history=history or []),
            }
        ]
        for image_url in normalized_images:
            content.append({"type": "input_image", "image_url": image_url, "detail": "high"})

        data = call_openai_responses(self.config, content)
        analysis = extract_output_text(data)
        if not analysis:
            raise RuntimeError("OpenAI returned an empty technical analysis")
        return {"status": "completed", "model": self.config.model, "analysis": analysis}


def load_config(root_dir: Path) -> TechnicalAnalysisConfig:
    load_env_file(root_dir / ".env")
    load_env_file(root_dir / "Technical Analysis" / ".env")
    return TechnicalAnalysisConfig(
        api_key=os.getenv("OPENAI_API_KEY", "").strip(),
        api_base=os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1").rstrip("/"),
        model=os.getenv("OPENAI_TECHNICAL_ANALYSIS_MODEL", "gpt-4.1-mini").strip() or "gpt-4.1-mini",
        timeout_seconds=int(os.getenv("OPENAI_TIMEOUT_SECONDS", "90")),
        max_output_tokens=int(os.getenv("OPENAI_TECHNICAL_MAX_OUTPUT_TOKENS", "1800")),
    )


def load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def validate_image_data_url(value: str | None) -> str | None:
    if not value:
        return None
    if not re.fullmatch(r"data:image/(?:png|jpeg|jpg|webp);base64,[A-Za-z0-9+/=\s]+", value):
        raise ValueError("image_data_url must be a PNG, JPEG, or WEBP base64 data URL")
    return re.sub(r"\s+", "", value)


def validate_image_data_urls(values: list[str], legacy_value: str | None = None) -> list[str]:
    raw_values = [item for item in values if item]
    if legacy_value:
        raw_values.append(legacy_value)
    if len(raw_values) > 6:
        raise ValueError("At most 6 chart screenshots can be analyzed at once")
    normalized = []
    for value in raw_values:
        image_url = validate_image_data_url(value)
        if image_url:
            normalized.append(image_url)
    return normalized


def build_prompt(*, message: str, history: list[dict[str, Any]]) -> str:
    history_lines = []
    for item in history[-10:]:
        role = str(item.get("role") or "").strip()
        speaker = "User" if role == "user" else "Assistant"
        history_lines.append(f"{speaker}: {item.get('content', '')}")
    history_text = "\n".join(history_lines) if history_lines else "No prior conversation."
    return (
        "你是一名严谨的技术面分析师。只能基于用户文字和截图里可见的信息分析，"
        "不要编造截图中看不到的价格、日期、指标数值、股票代码或市场背景。"
        "请给出概率化判断、关键支撑/压力、可见的失效条件和风险控制建议。"
        "不要承诺未来走势一定发生。\n\n"
        "输出结构：\n"
        "1. 图面观察\n"
        "2. 趋势判断\n"
        "3. 关键位\n"
        "4. 未来走势情景\n"
        "5. 交易风险提示\n\n"
        f"历史对话：\n{history_text}\n\n"
        f"用户当前问题：\n{message}"
    )


def call_openai_responses(config: TechnicalAnalysisConfig, content: list[dict[str, Any]]) -> dict[str, Any]:
    body = json.dumps(
        {
            "model": config.model,
            "input": [{"role": "user", "content": content}],
            "temperature": 0.2,
            "max_output_tokens": config.max_output_tokens,
        },
        ensure_ascii=False,
    ).encode("utf-8")
    request = urllib.request.Request(
        f"{config.api_base}/responses",
        data=body,
        headers={
            "Authorization": f"Bearer {config.api_key}",
            "Content-Type": "application/json",
            "User-Agent": "QDS-Technical-Analysis/0.1",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=config.timeout_seconds) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"OpenAI API error: {detail}") from exc
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"OpenAI request failed: {exc}") from exc


def extract_output_text(data: dict[str, Any]) -> str:
    direct = data.get("output_text")
    if direct:
        return str(direct).strip()

    parts: list[str] = []
    for output in data.get("output", []) or []:
        for content in output.get("content", []) or []:
            text = content.get("text") or content.get("output_text")
            if text:
                parts.append(str(text))
    return "\n".join(parts).strip()
