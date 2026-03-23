
import os, json, re, hashlib, sqlite3, time, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
CACHE_DB = os.path.join(CACHE_DIR, "web_cache.db")


def _init_cache():
    os.makedirs(CACHE_DIR, exist_ok=True)
    conn = sqlite3.connect(CACHE_DB)
    conn.execute("""CREATE TABLE IF NOT EXISTS cache (
        key TEXT PRIMARY KEY,
        url TEXT,
        content TEXT,
        summary TEXT,
        timestamp REAL
    )""")
    conn.commit()
    return conn


def _cache_get(key: str) -> dict | None:
    try:
        conn = _init_cache()
        row = conn.execute("SELECT url, content, summary, timestamp FROM cache WHERE key=?",
                            (key,)).fetchone()
        conn.close()
        if row:
            return {"url": row[0], "content": row[1], "summary": row[2], "timestamp": row[3]}
    except Exception:
        pass
    return None


def _cache_set(key: str, url: str, content: str, summary: str = ""):
    try:
        conn = _init_cache()
        conn.execute("INSERT OR REPLACE INTO cache (key, url, content, summary, timestamp) VALUES (?,?,?,?,?)",
                      (key, url, content, summary, time.time()))
        conn.commit()
        conn.close()
    except Exception:
        pass


def fetch_url(url: str, timeout: int = 10) -> str | None:
    import urllib.request, urllib.error
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "AIDE-v2.0-Materials-Research-Bot/1.0"
        })
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="ignore")
    except Exception:
        return None


def search_wikipedia(query: str) -> dict | None:
    cache_key = f"wiki_{hashlib.md5(query.encode()).hexdigest()}"
    cached = _cache_get(cache_key)
    if cached:
        return cached

    import urllib.parse
    search_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(query)}"
    html = fetch_url(search_url)
    if html:
        try:
            data = json.loads(html)
            content = data.get("extract", "")
            if content:
                result = {
                    "url": data.get("content_urls", {}).get("desktop", {}).get("page", ""),
                    "content": content,
                    "summary": content[:500],
                }
                _cache_set(cache_key, result["url"], content, result["summary"])
                return result
        except json.JSONDecodeError:
            pass
    return None


def search_materials_project(formula: str, api_key: str = None) -> dict | None:
    api_key = api_key or os.environ.get("MP_API_KEY", "")
    if not api_key:
        return None

    cache_key = f"mp_{hashlib.md5(formula.encode()).hexdigest()}"
    cached = _cache_get(cache_key)
    if cached:
        return cached

    try:
        from mp_api.client import MPRester
        with MPRester(api_key) as mpr:
            docs = mpr.summary.search(formula=formula, fields=[
                "material_id", "formula_pretty", "formation_energy_per_atom",
                "energy_above_hull", "band_gap", "density",
                "bulk_modulus", "shear_modulus"
            ])
            if docs:
                doc = docs[0]
                content = json.dumps({
                    "material_id": str(doc.material_id),
                    "formula": doc.formula_pretty,
                    "formation_energy_eV": doc.formation_energy_per_atom,
                    "e_above_hull_eV": doc.energy_above_hull,
                    "band_gap_eV": doc.band_gap,
                    "density_gcc": doc.density,
                    "bulk_modulus_GPa": getattr(doc, 'bulk_modulus', None),
                    "shear_modulus_GPa": getattr(doc, 'shear_modulus', None),
                }, default=str)
                result = {"url": f"https://next-gen.materialsproject.org/materials/{doc.material_id}",
                          "content": content, "summary": f"MP: {doc.formula_pretty}"}
                _cache_set(cache_key, result["url"], content, result["summary"])
                return result
    except Exception:
        pass
    return None


def scrape_alloy_info(alloy_name: str) -> dict:
    results = {"alloy": alloy_name, "sources": []}

    wiki = search_wikipedia(alloy_name)
    if wiki:
        results["sources"].append({"source": "Wikipedia", **wiki})

    if not wiki:
        wiki2 = search_wikipedia(f"{alloy_name} (alloy)")
        if wiki2:
            results["sources"].append({"source": "Wikipedia", **wiki2})

    for src in results.get("sources", []):
        comp = _extract_composition_from_text(src.get("content", ""))
        if comp:
            results["composition_extracted"] = comp
            break

    return results


def _extract_composition_from_text(text: str) -> dict | None:
    comp = {}

    for m in re.finditer(r'(\d+\.?\d*)\s*%\s*([A-Z][a-z]?)', text):
        frac = float(m.group(1)) / 100
        sym = m.group(2)
        if 0 < frac <= 1:
            comp[sym] = frac

    for m in re.finditer(r'([A-Z][a-z]?)\s+(\d+\.?\d*)\s*%', text):
        sym = m.group(1)
        frac = float(m.group(2)) / 100
        if 0 < frac <= 1:
            comp[sym] = frac

    if comp and 0.5 < sum(comp.values()) < 1.5:
        total = sum(comp.values())
        return {k: v/total for k, v in comp.items()}
    return None


def summarize_with_llm(text: str, query: str) -> str:
    api_key = os.environ.get("GROQ_API_KEY", "").strip()
    if not api_key or not text:
        return text[:500] if text else ""

    import urllib.request
    payload = json.dumps({
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {"role": "system", "content": "You are a metallurgy expert. Summarize the given text focusing on: composition, mechanical properties, applications, and any relevant engineering data. Be concise (max 200 words)."},
            {"role": "user", "content": f"Query: {query}\n\nText to summarize:\n{text[:3000]}"}
        ],
        "max_tokens": 300,
        "temperature": 0.1,
    }).encode()

    try:
        req = urllib.request.Request(
            "https://api.groq.com/openai/v1/chat/completions",
            data=payload,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
        return data.get("choices", [{}])[0].get("message", {}).get("content", text[:500])
    except Exception:
        return text[:500]


def web_lookup(query: str) -> dict:
    results = {"query": query, "found": False, "sources": []}

    alloy_info = scrape_alloy_info(query)
    if alloy_info.get("sources"):
        results["sources"].extend(alloy_info["sources"])
        results["found"] = True
        if alloy_info.get("composition_extracted"):
            results["composition"] = alloy_info["composition_extracted"]

    if not results["found"]:
        wiki = search_wikipedia(query)
        if wiki:
            results["sources"].append({"source": "Wikipedia", **wiki})
            results["found"] = True

    if results["found"]:
        all_content = " ".join(s.get("content", "") for s in results["sources"])
        results["summary"] = summarize_with_llm(all_content, query)

    return results
