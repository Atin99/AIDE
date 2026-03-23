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
    },
    {
        "name": "deepseek",
        "env": "DEEPSEEK_API_KEY",
        "endpoint": "https://api.deepseek.com/chat/completions",
        "model": "deepseek-chat",
    },
    {
        "name": "groq",
        "env": "GROQ_API_KEY",
        "endpoint": "https://api.groq.com/openai/v1/chat/completions",
        "model": "llama-3.3-70b-versatile",
    },
]

DEFAULT_LOCAL_MODELS = [
    "phi3:mini",
    "qwen2:1.5b",
    "qwen2.5:1.5b",
    "qwen2.5:3b",
    "llama3.2:3b",
    "mistral:7b-instruct",
]

_provider_cursor = 0
_local_cache = {
    "providers": [],
    "ts": 0.0,
    "cooldown_until": 0.0,
}


def _truthy_env(name, default=False):
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _float_env(name, default_value):
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default_value
    try:
        return float(raw)
    except Exception:
        return default_value


def _read_http_error(err):
    try:
        return err.read().decode("utf-8", errors="replace")[:500]
    except Exception:
        return str(err)


def _local_enabled():
    return _truthy_env("AIDE_USE_LOCAL_LLM", default=True)


def _local_first():
    return _truthy_env("AIDE_LOCAL_FIRST", default=True)


def _local_base_url():
    return os.environ.get("AIDE_LOCAL_LLM_URL", "http://127.0.0.1:11434").strip().rstrip("/")


def _local_model_preferences():
    forced = os.environ.get("AIDE_LOCAL_LLM_MODEL", "").strip()
    listed = os.environ.get("AIDE_LOCAL_LLM_MODELS", "").strip()

    ordered = []
    if forced:
        ordered.append(forced)

    if listed:
        for token in listed.split(","):
            model = token.strip()
            if model and model not in ordered:
                ordered.append(model)

    for model in DEFAULT_LOCAL_MODELS:
        if model not in ordered:
            ordered.append(model)
    return ordered


def _model_matches(preferred, installed):
    p = preferred.lower().strip()
    i = installed.lower().strip()
    if p == i:
        return True
    if i.startswith(p + ":"):
        return True
    if p.startswith(i + ":"):
        return True
    return False


def _pick_local_model(installed_models):
    if not installed_models:
        if _truthy_env("AIDE_LOCAL_ASSUME_MODEL", default=False):
            prefs = _local_model_preferences()
            return prefs[0] if prefs else None
        return None

    prefs = _local_model_preferences()
    for pref in prefs:
        for installed in installed_models:
            if _model_matches(pref, installed):
                return installed
    return installed_models[0]


def _fetch_local_models(base_url, timeout):
    req = urllib.request.Request(base_url + "/api/tags", method="GET")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = resp.read().decode("utf-8", errors="replace")
    payload = json.loads(body)
    models = payload.get("models", []) or []
    names = []
    for model in models:
        name = str(model.get("name", "")).strip()
        if name:
            names.append(name)
    return names


def _discover_local_providers(force_refresh=False):
    now = time.time()
    if not _local_enabled():
        _local_cache["providers"] = []
        _local_cache["ts"] = now
        return []

    if now < _local_cache["cooldown_until"]:
        return []

    ttl = _float_env("AIDE_LOCAL_DISCOVERY_TTL", 45.0)
    if (not force_refresh) and _local_cache["providers"] and (now - _local_cache["ts"]) < ttl:
        return list(_local_cache["providers"])

    base_url = _local_base_url()
    timeout = _float_env("AIDE_LOCAL_LLM_TIMEOUT", 1.3)

    providers = []
    try:
        installed = _fetch_local_models(base_url, timeout)
        chosen = _pick_local_model(installed)
        if chosen:
            providers.append({
                "name": "ollama",
                "endpoint": base_url + "/api/chat",
                "model": chosen,
                "api_key": "",
            })
        _local_cache["providers"] = providers
        _local_cache["ts"] = time.time()
        _local_cache["cooldown_until"] = 0.0
        return list(providers)
    except Exception as err:
        logger.info("[LLM] Local discovery unavailable: %s", err)
        _local_cache["providers"] = []
        _local_cache["ts"] = time.time()
        _local_cache["cooldown_until"] = time.time() + _float_env("AIDE_LOCAL_COOLDOWN", 60.0)
        return []


def _remote_providers():
    providers = []
    for spec in PROVIDER_SPECS:
        api_key = os.environ.get(spec["env"], "").strip()
        if api_key and not api_key.startswith("your_"):
            providers.append({**spec, "api_key": api_key})
    return providers


def get_available_providers(force_refresh_local=False):
    local = _discover_local_providers(force_refresh=force_refresh_local)
    remote = _remote_providers()

    if _local_first():
        return local + remote
    return remote + local


def get_provider_info():
    providers = get_available_providers()
    if not providers:
        return None, None, None
    p = providers[0]
    return p["endpoint"], p.get("api_key"), p["model"]


def is_available():
    return bool(get_available_providers())


def get_api_key():
    _, key, _ = get_provider_info()
    return key


def _ordered_providers():
    providers = get_available_providers()
    if not providers:
        return []
    start = _provider_cursor % len(providers)
    return providers[start:] + providers[:start]


def _advance_cursor(offset, provider_count):
    global _provider_cursor
    if provider_count:
        _provider_cursor = (_provider_cursor + offset) % provider_count


def _build_payload(provider, messages, max_tokens, temperature, force_json):
    if provider["name"] == "ollama":
        options = {"temperature": float(temperature)}
        if max_tokens:
            options["num_predict"] = int(max_tokens)
        payload = {
            "model": provider["model"],
            "messages": messages,
            "stream": False,
            "options": options,
        }
        if force_json:
            payload["format"] = "json"
        return payload

    payload = {
        "model": provider["model"],
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if force_json and provider["name"] != "gemini":
        payload["response_format"] = {"type": "json_object"}
    return payload


def _extract_content(response_json):
    message = response_json.get("message")
    if isinstance(message, dict):
        content = message.get("content", "")
        if isinstance(content, str) and content.strip():
            return content.strip()

    response_text = response_json.get("response")
    if isinstance(response_text, str) and response_text.strip():
        return response_text.strip()

    choices = response_json.get("choices") or []
    if choices:
        msg = choices[0].get("message", {})
        content = msg.get("content", "")
        if isinstance(content, list):
            text_parts = []
            for part in content:
                if isinstance(part, dict) and part.get("type") == "text":
                    text_parts.append(part.get("text", ""))
                elif isinstance(part, str):
                    text_parts.append(part)
            content = "".join(text_parts)
        if isinstance(content, str) and content.strip():
            return content.strip()

    candidates = response_json.get("candidates") or []
    if candidates:
        parts = candidates[0].get("content", {}).get("parts", [])
        text = "".join(part.get("text", "") for part in parts if isinstance(part, dict)).strip()
        if text:
            return text

    return None


def _request_provider(provider, messages, max_tokens, temperature, force_json, timeout=30):
    payload = _build_payload(provider, messages, max_tokens, temperature, force_json)
    headers = {"Content-Type": "application/json"}
    api_key = provider.get("api_key", "")
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(provider["endpoint"], data=data, headers=headers, method="POST")
    with urllib.request.urlopen(request, timeout=timeout) as response:
        body = response.read().decode("utf-8", errors="replace")
    return _extract_content(json.loads(body))


def chat(messages, max_tokens=1000, temperature=0.2, force_json=False, retries=1, timeout=15):
    providers = _ordered_providers()
    if not providers:
        print("  [LLM] No local or API provider available. Fallback mode active.")
        return None

    rounds = max(1, retries)
    last_error = None

    for round_idx in range(rounds):
        ordered = _ordered_providers()
        for offset, provider in enumerate(ordered):
            try:
                content = _request_provider(provider, messages, max_tokens, temperature, force_json, timeout)
                if content:
                    _advance_cursor(offset + 1, len(ordered))
                    return content
            except urllib.error.HTTPError as err:
                detail = _read_http_error(err)
                last_error = f"{provider['name']} HTTP {err.code}: {detail}"
                logger.warning(last_error)

                if provider["name"] == "ollama" and ("model" in detail.lower() and "not found" in detail.lower()):
                    _discover_local_providers(force_refresh=True)

                if err.code == 429:
                    wait = min(2.0 * (2 ** round_idx), 32.0)
                    logger.warning("[LLM] 429 Rate Limit from %s - Waiting %.1fs", provider["name"], wait)
                    time.sleep(wait)
                    continue
                continue
            except urllib.error.URLError as err:
                last_error = f"{provider['name']} network: {err}"
                logger.warning(last_error)
                if provider["name"] == "ollama":
                    _local_cache["cooldown_until"] = time.time() + _float_env("AIDE_LOCAL_COOLDOWN", 60.0)
                continue
            except Exception as err:
                last_error = f"{provider['name']}: {err}"
                logger.warning(last_error)
                continue

        if round_idx < rounds - 1:
            time.sleep(min(2.0, 1.0 * (2 ** round_idx)))

    if last_error:
        logger.debug("[LLM] Last failure: %s", last_error)

    _advance_cursor(1, len(providers))
    return None


def chat_json(messages, max_tokens=1500, temperature=0.2, retries=3):
    messages = [dict(m) for m in messages]
    has_critical = any("CRITICAL" in m.get("content", "") for m in messages if m.get("role") == "system")
    if not has_critical:
        for m in messages:
            if m.get("role") == "system":
                m["content"] = m.get("content", "") + "\n\nCRITICAL: You MUST respond with ONLY valid JSON. No prose, no markdown fences. Raw JSON only."
                has_critical = True
                break
        if not has_critical:
            messages.insert(0, {
                "role": "system",
                "content": "CRITICAL: You MUST respond with ONLY valid JSON. No prose, no markdown fences. Raw JSON only.",
            })

    last_raw = ""
    for attempt in range(max(1, retries)):
        attempt_messages = list(messages)
        if attempt > 0:
            attempt_messages.append({
                "role": "user",
                "content": f"Your previous response was not valid JSON:\n---\n{last_raw[:300]}\n---\nCorrect it. Return ONLY valid JSON.",
            })

        raw = chat(attempt_messages, max_tokens=max_tokens, temperature=temperature, force_json=True, retries=2)
        if not raw:
            continue

        last_raw = raw
        extracted = extract_json(raw)
        if extracted is not None:
            return extracted

        logger.warning("[LLM JSON] Parse failed attempt %s", attempt + 1)

    return None


def extract_json(text):
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    match = re.search(r"```(?:json)?\s*([\s\S]+?)```", text, re.IGNORECASE)
    if match:
        try:
            return json.loads(match.group(1).strip())
        except json.JSONDecodeError:
            pass

    for pattern in (r"(\{[\s\S]+\})", r"(\[[\s\S]+\])"):
        m = re.search(pattern, text)
        if m:
            try:
                return json.loads(m.group(1))
            except json.JSONDecodeError:
                continue
    return None
