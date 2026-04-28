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
        "name": "openrouter",
        "env": "OPENROUTER_API_KEY",
        "endpoint": "https://openrouter.ai/api/v1/chat/completions",
        "model": "openai/gpt-oss-20b:free",
        "json_mode": "response_format",
        "tier": "free",
        "label": "OpenRouter Fixed Free",
    },
    {
        "name": "openrouter_router",
        "env": "OPENROUTER_API_KEY",
        "endpoint": "https://openrouter.ai/api/v1/chat/completions",
        "model": "openrouter/free",
        "json_mode": "prompt_only",
        "tier": "free",
        "label": "OpenRouter Free Router",
    },
    {
        "name": "gemini",
        "env": "GEMINI_API_KEY",
        "endpoint": "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
        "model": "gemini-2.5-flash",
        "json_mode": "prompt_only",
        "tier": "metered",
        "label": "Gemini",
    },
    {
        "name": "groq",
        "env": "GROQ_API_KEY",
        "endpoint": "https://api.groq.com/openai/v1/chat/completions",
        "model": "llama-3.1-8b-instant",
        "json_mode": "response_format",
        "tier": "metered",
        "label": "Groq",
    },
    {
        "name": "xai",
        "env": "XAI_API_KEY",
        "endpoint": "https://api.x.ai/v1/chat/completions",
        "model": "grok-3-mini",
        "json_mode": "prompt_only",
        "tier": "metered",
        "label": "xAI Grok",
    },
]
EMPTY_KEY_PREFIX = "your_"
MAX_ERROR_DETAIL_CHARS = 500
DEFAULT_HTTP_TIMEOUT_SECONDS = max(15, int(os.environ.get("AIDE_LLM_HTTP_TIMEOUT_SECONDS", "45")))
DEFAULT_BROWSER_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/123.0.0.0 Safari/537.36"
)
MODEL_ENV_BY_PROVIDER = {
    "openrouter": "AIDE_OPENROUTER_MODEL",
    "openrouter_router": "AIDE_OPENROUTER_ROUTER_MODEL",
    "gemini": "AIDE_GEMINI_MODEL",
    "groq": "AIDE_GROQ_MODEL",
    "xai": "AIDE_XAI_MODEL",
}
PROVIDER_ORDER_ENV_BY_TASK = {
    "chat": "AIDE_LLM_PROVIDER_ORDER",
    "json": "AIDE_LLM_JSON_PROVIDER_ORDER",
}
DEFAULT_PROVIDER_ORDER = {
    "chat": ["openrouter", "openrouter_router", "gemini", "groq", "xai"],
    "json": ["openrouter", "openrouter_router", "groq", "gemini", "xai"],
}


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


def _configured_model(spec: dict) -> str:
    env_name = MODEL_ENV_BY_PROVIDER.get(spec["name"])
    if env_name:
        value = os.environ.get(env_name, "").strip()
        if value:
            return value
    return spec["model"]


def _remote_llm_enabled() -> bool:
    value = os.environ.get("AIDE_ENABLE_REMOTE_LLM", "1").strip().lower()
    return value not in {"0", "false", "no", "off"}


def remote_llm_enabled() -> bool:
    """Return whether remote LLM usage is enabled by configuration."""
    return _remote_llm_enabled()


def _provider_order(task: str = "chat") -> list[str]:
    env_name = PROVIDER_ORDER_ENV_BY_TASK.get(task, "AIDE_LLM_PROVIDER_ORDER")
    configured = os.environ.get(env_name, "").strip()
    if configured:
        order = [item.strip() for item in configured.split(",") if item.strip()]
        if order:
            return order
    return list(DEFAULT_PROVIDER_ORDER.get(task, DEFAULT_PROVIDER_ORDER["chat"]))


def get_available_providers(task: str = "chat") -> list[dict]:
    """Return configured remote LLM providers in deterministic priority order."""
    if not _remote_llm_enabled():
        return []
    providers = []
    order = _provider_order(task)
    order_index = {name: idx for idx, name in enumerate(order)}
    for spec_index, spec in enumerate(PROVIDER_SPECS):
        api_key = _configured_api_key(spec["env"])
        if api_key:
            providers.append(
                {
                    **spec,
                    "api_key": api_key,
                    "model": _configured_model(spec),
                    "_priority": order_index.get(spec["name"], len(order) + spec_index),
                    "_spec_index": spec_index,
                }
            )
    providers.sort(key=lambda provider: (provider["_priority"], provider["_spec_index"]))
    for provider in providers:
        provider.pop("_priority", None)
        provider.pop("_spec_index", None)
    return providers


def get_provider_info(task: str = "chat") -> tuple[str | None, str | None, str | None]:
    """Return endpoint, API key, and default model for the first configured provider."""
    providers = get_available_providers(task=task)
    if not providers:
        return None, None, None
    provider = providers[0]
    return provider["endpoint"], provider["api_key"], provider["model"]


def is_available(task: str = "chat") -> bool:
    """Return True when any configured remote LLM provider is available."""
    return bool(get_available_providers(task=task))


def get_api_key(task: str = "chat") -> str | None:
    """Return the first configured API key, if any."""
    _, api_key, _ = get_provider_info(task=task)
    return api_key


def _require_provider(task: str = "chat") -> list[dict]:
    """Return providers or raise an actionable configuration error."""
    providers = get_available_providers(task=task)
    if providers:
        return providers
    raise ProviderUnavailableError(
        "No remote LLM API key configured. Set OPENROUTER_API_KEY, GEMINI_API_KEY, GROQ_API_KEY, or XAI_API_KEY in .env or the environment."
    )


def _ordered_providers(task: str = "chat") -> list[dict]:
    """Return configured providers in stable fallback order."""
    return _require_provider(task=task)


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
    if force_json and provider["name"].startswith("openrouter"):
        payload["plugins"] = [{"id": "response-healing"}]
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


def _request_headers(provider: dict) -> dict[str, str]:
    headers = {
        "Authorization": f"Bearer {provider['api_key']}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    if provider["name"].startswith("openrouter"):
        title = os.environ.get("AIDE_OPENROUTER_TITLE", "AIDE v5").strip()
        referer = os.environ.get("AIDE_OPENROUTER_REFERER", "http://localhost:9000/app/").strip()
        if title:
            headers["X-OpenRouter-Title"] = title
        if referer:
            headers["HTTP-Referer"] = referer
    if provider["name"] == "groq":
        headers.update(
            {
                "User-Agent": DEFAULT_BROWSER_USER_AGENT,
                "Accept-Language": "en-US,en;q=0.9",
                "Cache-Control": "no-cache",
                "Pragma": "no-cache",
            }
        )
    return headers


def _is_retriable_http(provider: dict, status_code: int, detail: str) -> bool:
    if provider["name"] == "gemini":
        return status_code in {408, 429, 500, 502, 503, 504}
    if provider["name"] == "groq":
        if status_code == 403 and "1010" in (detail or ""):
            return False
        return status_code in {408, 429, 500, 502, 503, 504}
    if provider["name"] == "xai":
        return status_code in {408, 429, 500, 502, 503, 504}
    return status_code in {408, 429, 500, 502, 503, 504}


def _retry_delay_seconds(err: urllib.error.HTTPError, attempt: int, detail: str = "") -> float:
    retry_after = ""
    try:
        retry_after = (err.headers.get("Retry-After") or "").strip()
    except Exception:
        retry_after = ""
    if retry_after.isdigit():
        return min(float(retry_after), 60.0)
    match = re.search(r"retry in ([0-9.]+)s", detail or "", re.IGNORECASE)
    if match:
        try:
            return min(float(match.group(1)), 60.0)
        except ValueError:
            pass
    return min(5.0 * (2 ** attempt), 40.0)


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
        headers=_request_headers(provider),
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
    timeout: int = DEFAULT_HTTP_TIMEOUT_SECONDS,
    task: str = "chat",
) -> str | None:
    """Call remote providers in stable fallback order and return the first successful text response."""
    providers = _ordered_providers(task=task)
    last_error = ""
    rounds = max(1, int(retries))

    for attempt in range(rounds):
        ordered = _ordered_providers(task=task)
        for provider in ordered:
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
                    return content
                last_error = f"{provider['name']}: empty response"
            except urllib.error.HTTPError as err:
                detail = _read_http_error(err)
                last_error = f"{provider['name']} HTTP {err.code}: {detail}"
                logger.warning(last_error)
                if _is_retriable_http(provider, err.code, detail):
                    delay = _retry_delay_seconds(err, attempt, detail)
                    logger.warning("[LLM] Retrying %s after %.1fs", provider["name"], delay)
                    time.sleep(delay)
            except urllib.error.URLError as err:
                last_error = f"{provider['name']} network error: {err}"
                logger.warning(last_error)
            except Exception as err:
                last_error = f"{provider['name']}: {err}"
                logger.warning(last_error)

        if attempt < rounds - 1:
            time.sleep(min(1.5 * (2 ** attempt), 6.0))

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
            timeout=DEFAULT_HTTP_TIMEOUT_SECONDS,
            task="json",
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
