from __future__ import annotations

import json
import os
import re
import ssl
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .config import ModelSpec


_UNICODE_QUOTE_TRANSLATION = str.maketrans(
    {
        "\u201c": '"',
        "\u201d": '"',
        "\u201e": '"',
        "\u201f": '"',
        "\u2033": '"',
        "\u300c": '"',
        "\u300d": '"',
        "\u300e": '"',
        "\u300f": '"',
        "\uff02": '"',
        "\u2018": "'",
        "\u2019": "'",
        "\u201a": "'",
        "\u201b": "'",
        "\u2032": "'",
        "\uff07": "'",
    }
)


@dataclass
class ModelResult:
    content: str
    parsed_json: Any
    usage: dict[str, int]
    model: str
    provider: str


def parse_json_object(text: str) -> Any:
    cleaned = _strip_code_fences(text.strip())
    candidates = [cleaned]
    outer = _extract_outer_json(cleaned)
    if outer and outer != cleaned:
        candidates.append(outer)
    repaired_candidates: list[str] = []
    for candidate in candidates:
        repaired = _repair_json_like_text(candidate)
        if repaired and repaired not in candidates and repaired not in repaired_candidates:
            repaired_candidates.append(repaired)
        repaired_outer = _extract_outer_json(repaired)
        if repaired_outer and repaired_outer not in candidates and repaired_outer not in repaired_candidates:
            repaired_candidates.append(repaired_outer)
    for candidate in candidates + repaired_candidates:
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            continue
    return {"raw_text": text, "json_parse_error": True}


def _strip_code_fences(text: str) -> str:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:].strip()
    return cleaned.strip()


def _extract_outer_json(text: str) -> str:
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        return text[start : end + 1]
    return text


def _repair_json_like_text(text: str) -> str:
    repaired = text.translate(_UNICODE_QUOTE_TRANSLATION)
    repaired = repaired.replace("\r\n", "\n").replace("\r", "\n")
    repaired = re.sub(r",\s*([}\]])", r"\1", repaired)
    repaired = _close_unterminated_string_lines(repaired)
    return repaired.strip()


def _close_unterminated_string_lines(text: str) -> str:
    lines = text.splitlines()
    if not lines:
        return text
    repaired_lines: list[str] = []
    for index, line in enumerate(lines):
        next_line = lines[index + 1] if index + 1 < len(lines) else ""
        if _line_needs_closing_quote(line, next_line):
            repaired_lines.append(f'{line}"')
        else:
            repaired_lines.append(line)
    return "\n".join(repaired_lines)


def _line_needs_closing_quote(line: str, next_line: str) -> bool:
    stripped = line.rstrip()
    if not stripped or stripped.endswith('"'):
        return False
    if '"' not in stripped:
        return False
    if stripped.lstrip().startswith("//"):
        return False
    quote_count = _count_unescaped_quotes(stripped)
    if quote_count % 2 == 0:
        return False
    next_stripped = next_line.lstrip()
    return bool(next_stripped.startswith(("]", "}", ",")))


def _count_unescaped_quotes(text: str) -> int:
    count = 0
    escaped = False
    for char in text:
        if char == "\\" and not escaped:
            escaped = True
            continue
        if char == '"' and not escaped:
            count += 1
        escaped = False
    return count


class ChatModelClient:
    def __init__(self, spec: ModelSpec, timeout_seconds: int = 180) -> None:
        self.spec = spec
        self.timeout_seconds = timeout_seconds

    @staticmethod
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

    def complete_json(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2,
        max_tokens: int = 6000,
        retries: int = 4,
    ) -> ModelResult:
        content, usage = self._complete(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            retries=retries,
            force_json=True,
        )
        return ModelResult(
            content=content,
            parsed_json=parse_json_object(content),
            usage=usage,
            model=self.spec.model,
            provider=self.spec.provider,
        )

    def _complete(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        temperature: float,
        max_tokens: int,
        retries: int,
        force_json: bool,
    ) -> tuple[str, dict[str, int]]:
        last_error: Exception | None = None
        for attempt in range(retries + 1):
            try:
                return self._post_chat_completion(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    force_json=force_json,
                )
            except urllib.error.HTTPError as exc:
                body = exc.read().decode("utf-8", errors="replace")
                last_error = RuntimeError(f"HTTP {exc.code}: {body}")
                if force_json and exc.code in {400, 422}:
                    try:
                        return self._post_chat_completion(
                            system_prompt=system_prompt,
                            user_prompt=user_prompt,
                            temperature=temperature,
                            max_tokens=max_tokens,
                            force_json=False,
                        )
                    except urllib.error.HTTPError as fallback_exc:
                        fallback_body = fallback_exc.read().decode("utf-8", errors="replace")
                        last_error = RuntimeError(
                            f"HTTP {fallback_exc.code} after json fallback: {fallback_body}"
                        )
            except Exception as exc:  # noqa: BLE001
                last_error = exc
            if attempt < retries:
                time.sleep(1.5 * (attempt + 1))
        raise RuntimeError(f"Model call failed after retries: {last_error}") from last_error

    def _post_chat_completion(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        temperature: float,
        max_tokens: int,
        force_json: bool,
    ) -> tuple[str, dict[str, int]]:
        api_key = os.getenv(self.spec.api_key_env)
        if not api_key:
            self.load_dotenv_if_present()
            api_key = os.getenv(self.spec.api_key_env)
        if api_key and api_key.startswith("请把你的"):
            raise RuntimeError(f"Please set a real API key in .env for {self.spec.api_key_env}")
        if not api_key:
            raise RuntimeError(f"Missing API key env var: {self.spec.api_key_env}")

        payload: dict[str, Any] = {
            "model": self.spec.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if force_json:
            payload["response_format"] = {"type": "json_object"}

        request = urllib.request.Request(
            self.spec.base_url,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "Connection": "close",
                "User-Agent": "QDS-Financial-Analyst-Workflow/0.1",
            },
            method="POST",
        )
        context = self._ssl_context()
        with urllib.request.urlopen(request, timeout=self.timeout_seconds, context=context) as response:
            raw = response.read().decode("utf-8")
        data = json.loads(raw)
        message = data["choices"][0]["message"]["content"]
        usage_raw = data.get("usage", {})
        usage = {
            "prompt_tokens": int(usage_raw.get("prompt_tokens", 0) or 0),
            "completion_tokens": int(usage_raw.get("completion_tokens", 0) or 0),
            "total_tokens": int(usage_raw.get("total_tokens", 0) or 0),
        }
        return message, usage

    def _ssl_context(self) -> ssl.SSLContext:
        no_verify = os.getenv("DEEPSEEK_SSL_NO_VERIFY", "").strip().lower()
        if no_verify in {"1", "true", "yes"}:
            return ssl._create_unverified_context()  # noqa: SLF001

        try:
            import certifi

            return ssl.create_default_context(cafile=certifi.where())
        except Exception:  # noqa: BLE001
            return ssl.create_default_context()
