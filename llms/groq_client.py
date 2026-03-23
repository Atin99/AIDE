
import os, json, re, time, logging, urllib.request, urllib.error
from typing import Optional

logger = logging.getLogger("AIDE.groq")

GROQ_MODEL_REASON = "llama-3.3-70b-versatile"
GROQ_MODEL_FAST   = "llama-3.3-70b-versatile"

_API_URL = "https://api.groq.com/openai/v1/chat/completions"


def get_api_key() -> str:
    return os.environ.get("GROQ_API_KEY", "").strip()


def is_available() -> bool:
    return bool(get_api_key())


def chat(messages: list[dict], model: str = None,
         max_tokens: int = 1200, temperature: float = 0.0,
         retries: int = 2, timeout: int = 30,
         force_json: bool = False) -> Optional[str]:
    api_key = get_api_key()
    if not api_key:
        logger.info("No API key set. Set GROQ_API_KEY in .env")
        print("  [GROQ] No API key set. Set GROQ_API_KEY in .env")
        return None

    model = model or GROQ_MODEL_REASON

    payload_dict = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }

    if force_json:
        payload_dict["response_format"] = {"type": "json_object"}

    payload = json.dumps(payload_dict).encode()

    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(
                _API_URL,
                data=payload,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode())

            content = (data.get("choices", [{}])[0]
                          .get("message", {})
                          .get("content", "").strip())

            if content:
                return content
            else:
                logger.warning(f"Empty response from API (attempt {attempt+1})")
                print(f"  [GROQ] Empty response from API (attempt {attempt+1})")
                return None

        except urllib.error.HTTPError as e:
            body = ""
            try:
                body = e.read().decode()[:300]
            except Exception:
                pass
            logger.error(f"HTTP {e.code} error (attempt {attempt+1}/{retries+1}): {body}")
            print(f"  [GROQ] HTTP {e.code} error (attempt {attempt+1}/{retries+1}): {body}")
            if e.code == 429:
                wait = 2.0 * (2 ** attempt)
                print(f"  [GROQ] Rate limited. Waiting {wait:.0f}s...")
                time.sleep(wait)
                continue
            elif e.code in (401, 403):
                print(f"  [GROQ] Authentication failed. Check your API key.")
                return None
            elif attempt < retries:
                time.sleep(0.5 * (2 ** attempt))
                continue
            return None

        except urllib.error.URLError as e:
            print(f"  [GROQ] Connection error (attempt {attempt+1}): {e.reason}")
            if attempt < retries:
                time.sleep(0.5 * (2 ** attempt))
                continue
            return None

        except TimeoutError:
            print(f"  [GROQ] Timeout after {timeout}s (attempt {attempt+1})")
            if attempt < retries:
                time.sleep(0.5 * (2 ** attempt))
                continue
            return None

        except json.JSONDecodeError as e:
            print(f"  [GROQ] JSON decode error: {e}")
            if attempt < retries:
                continue
            return None

        except Exception as e:
            print(f"  [GROQ] Unexpected error: {type(e).__name__}: {e}")
            return None


def chat_json(messages: list[dict], model: str = None,
              max_tokens: int = 1200, temperature: float = 0.0) -> Optional[dict]:
    raw = chat(messages, model=model, max_tokens=max_tokens,
               temperature=temperature, force_json=True)
    if not raw:
        return None

    result = extract_json(raw)
    if result is None:
        print(f"  [GROQ] Failed to parse JSON from response: {raw[:200]}")
    return result


def extract_json(text: str) -> Optional[dict]:
    if "```" in text:
        lines = text.split("\n")
        text = "\n".join(l for l in lines if not l.strip().startswith("```"))

    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    m = re.search(r'\{.*\}', text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group())
        except json.JSONDecodeError:
            pass

    return None
