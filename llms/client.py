from __future__ import annotations

import json
import logging
import os
import re
import time
import urllib.error
import urllib.request


logger = logging.getLogger("AIDE.llm")

PROVIDER_SPECS = [
    {
        "name": "gemini",
        "env": "GEMINI_API_KEY",
        "endpoint": "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
        "model": "gemini-2.5-flash",
        "json_mode": "prompt_only",
    },
    {
        "name": "groq",
        "env": "GROQ_API_KEY",
        "endpoint": "https://api.groq.com/openai/v1/chat/completions",
        "model": "llama-3.3-70b-versatile",
        "json_mode": "response_format",
    },
]
EMPTY_KEY_PREFIX = "your_"
MAX_ERROR_DETAIL_CHARS = 500

_provider_cursor = 0


class ProviderUnavailableError(RuntimeError):
    """Raised when no remote LLM credentials are configured for AIDE."""


def _read_http_error(err: urllib.error.HTTPError) -> str:
    """Extract a short human-readable error body from an HTTP error."""
    try:
        return err.read().decode("utf-8", errors="replace")[:MAX_ERROR_DETAIL_CHARS]
    except Exception:
        return str(err)


def _configured_api_key(env_name: str) -> str:
    """Return one configured API key or an empty string when unset."""
    value = os.environ.get(env_name, "").strip()
    if not value or value.startswith(EMPTY_KEY_PREFIX):
        return ""
    return value


def get_available_providers() -> list[dict]:
    """Return configured remote LLM providers in priority order."""
    providers = []
    for spec in PROVIDER_SPECS:
        api_key = _configured_api_key(spec["env"])
        if api_key:
            providers.append({**spec, "api_key": api_key})
    return providers


def get_provider_info() -> tuple[str | None, str | None, str | None]:
    """Return endpoint, API key, and default model for the first configured provider."""
    providers = get_available_providers()
    if not providers:
        return None, None, None
    provider = providers[0]
    return provider["endpoint"], provider["api_key"], provider["model"]


def is_available() -> bool:
    """Return True when Gemini or Groq credentials are configured."""
    return bool(get_available_providers())


def get_api_key() -> str | None:
    """Return the first configured API key, if any."""
    _, api_key, _ = get_provider_info()
    return api_key


def _require_provider() -> list[dict]:
    """Return providers or raise an actionable configuration error."""
    providers = get_available_providers()
    if providers:
        return providers
    raise ProviderUnavailableError(
        "No remote LLM API key configured. Set GEMINI_API_KEY or GROQ_API_KEY in .env or the environment."
    )


def _ordered_providers() -> list[dict]:
    """Rotate configured providers so fallback attempts are balanced over time."""
    providers = _require_provider()
    start = _provider_cursor % len(providers)
    return providers[start:] + providers[:start]


def _advance_cursor(offset: int, provider_count: int) -> None:
    """Advance the provider cursor after a successful request or full failure cycle."""
    global _provider_cursor
    if provider_count > 0:
        _provider_cursor = (_provider_cursor + offset) % provider_count


def _build_payload(
    provider: dict,
    messages: list[dict],
    max_tokens: int,
    temperature: float,
    force_json: bool,
) -> dict:
    """Build an OpenAI-compatible chat payload for one provider."""
    safe_temperature = float(temperature)
    if provider["name"] == "groq" and safe_temperature <= 0:
        safe_temperature = 1e-8

    payload = {
        "model": provider["model"],
        "messages": messages,
        "temperature": safe_temperature,
        "max_tokens": int(max_tokens),
    }
    if force_json and provider.get("json_mode") == "response_format":
        payload["response_format"] = {"type": "json_object"}
    return payload


def _extract_content(response_json: dict) -> str | None:
    """Extract text content from a provider response payload."""
    choices = response_json.get("choices") or []
    if choices:
        message = choices[0].get("message", {})
        content = message.get("content", "")
        if isinstance(content, list):
            parts = []
            for part in content:
                if isinstance(part, dict) and part.get("type") == "text":
                    parts.append(part.get("text", ""))
                elif isinstance(part, str):
                    parts.append(part)
            content = "".join(parts)
        if isinstance(content, str) and content.strip():
            return content.strip()

    candidates = response_json.get("candidates") or []
    if candidates:
        parts = candidates[0].get("content", {}).get("parts", [])
        text = "".join(part.get("text", "") for part in parts if isinstance(part, dict)).strip()
        if text:
            return text
    return None


def _request_provider(
    provider: dict,
    messages: list[dict],
    max_tokens: int,
    temperature: float,
    force_json: bool,
    timeout: int,
) -> str | None:
    """Submit one chat request to one configured remote provider."""
    payload = _build_payload(provider, messages, max_tokens, temperature, force_json)
    request = urllib.request.Request(
        provider["endpoint"],
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {provider['api_key']}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        body = response.read().decode("utf-8", errors="replace")
    return _extract_content(json.loads(body))


def chat(
    messages: list[dict],
    max_tokens: int = 1000,
    temperature: float = 0.2,
    force_json: bool = False,
    retries: int = 1,
    timeout: int = 15,
) -> str | None:
    """Call Gemini first, then Groq, and return the first successful text response."""
    providers = _ordered_providers()
    last_error = ""
    rounds = max(1, int(retries))

    for attempt in range(rounds):
        ordered = _ordered_providers()
        for offset, provider in enumerate(ordered):
            try:
                content = _request_provider(
                    provider,
                    messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    force_json=force_json,
                    timeout=timeout,
                )
                if content:
                    _advance_cursor(offset + 1, len(ordered))
                    return content
                last_error = f"{provider['name']}: empty response"
            except urllib.error.HTTPError as err:
                detail = _read_http_error(err)
                last_error = f"{provider['name']} HTTP {err.code}: {detail}"
                logger.warning(last_error)
                if err.code == 429:
                    time.sleep(min(2.0 * (2 ** attempt), 20.0))
            except urllib.error.URLError as err:
                last_error = f"{provider['name']} network error: {err}"
                logger.warning(last_error)
            except Exception as err:
                last_error = f"{provider['name']}: {err}"
                logger.warning(last_error)

        if attempt < rounds - 1:
            time.sleep(min(1.5 * (2 ** attempt), 6.0))

    _advance_cursor(1, len(providers))
    if last_error:
        logger.debug("[LLM] Last remote failure: %s", last_error)
    return None


def chat_json(messages: list[dict], max_tokens: int = 1500, temperature: float = 0.2, retries: int = 3):
    """Call the remote chat gateway and parse one JSON object from the response."""
    messages = [dict(message) for message in messages]
    has_critical = any("CRITICAL" in message.get("content", "") for message in messages if message.get("role") == "system")
    if not has_critical:
        for message in messages:
            if message.get("role") == "system":
                message["content"] = (
                    message.get("content", "")
                    + "\n\nCRITICAL: You MUST respond with ONLY valid JSON. No prose, no markdown fences. Raw JSON only."
                )
                has_critical = True
                break
        if not has_critical:
            messages.insert(
                0,
                {
                    "role": "system",
                    "content": "CRITICAL: You MUST respond with ONLY valid JSON. No prose, no markdown fences. Raw JSON only.",
                },
            )

    last_raw = ""
    for attempt in range(max(1, int(retries))):
        attempt_messages = list(messages)
        if attempt > 0:
            attempt_messages.append(
                {
                    "role": "user",
                    "content": (
                        "Your previous response was not valid JSON:\n---\n"
                        + last_raw[:300]
                        + "\n---\nCorrect it. Return ONLY valid JSON."
                    ),
                }
            )

        raw = chat(
            attempt_messages,
            max_tokens=max_tokens,
            temperature=temperature,
            force_json=True,
            retries=2,
        )
        if not raw:
            continue

        last_raw = raw
        extracted = extract_json(raw)
        if extracted is not None:
            return extracted
        logger.warning("[LLM JSON] Parse failed attempt %s", attempt + 1)
    return None


def extract_json(text: str):
    """Extract JSON from raw model text, including fenced or lightly malformed output."""
    text = str(text or "").strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    repaired = _repair_json_text(text)
    if repaired and repaired != text:
        try:
            return json.loads(repaired)
        except json.JSONDecodeError:
            pass

    match = re.search(r"```(?:json)?\s*([\s\S]+?)```", text, re.IGNORECASE)
    if match:
        candidate = match.group(1).strip()
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            repaired = _repair_json_text(candidate)
            if repaired:
                try:
                    return json.loads(repaired)
                except json.JSONDecodeError:
                    pass

    for pattern in (r"(\{[\s\S]+\})", r"(\[[\s\S]+\])"):
        match = re.search(pattern, text)
        if not match:
            continue
        candidate = match.group(1)
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            repaired = _repair_json_text(candidate)
            if repaired:
                try:
                    return json.loads(repaired)
                except json.JSONDecodeError:
                    continue
    return None


def _repair_json_text(text: str) -> str | None:
    """Apply lightweight repairs to near-JSON model output."""
    candidate = str(text or "").strip()
    if not candidate:
        return None
    candidate = re.sub(r",\s*([}\]])", r"\1", candidate)
    candidate = re.sub(r"(?<!\\)'", "\"", candidate)
    candidate = re.sub(r"\bNone\b", "null", candidate)
    candidate = re.sub(r"\bTrue\b", "true", candidate)
    candidate = re.sub(r"\bFalse\b", "false", candidate)
    return candidate
