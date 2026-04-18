import re
from core.elements import available as available_elements

ALL_SYMS = set(available_elements())

ELEMENT_NAMES = {
    "hydrogen":"H","helium":"He","lithium":"Li","beryllium":"Be","boron":"B",
    "carbon":"C","nitrogen":"N","oxygen":"O","fluorine":"F","neon":"Ne",
    "sodium":"Na","magnesium":"Mg","aluminium":"Al","aluminum":"Al","silicon":"Si",
    "phosphorus":"P","sulphur":"S","sulfur":"S","chlorine":"Cl","argon":"Ar",
    "potassium":"K","calcium":"Ca","scandium":"Sc","titanium":"Ti","vanadium":"V",
    "chromium":"Cr","manganese":"Mn","iron":"Fe","cobalt":"Co","nickel":"Ni",
    "copper":"Cu","zinc":"Zn","gallium":"Ga","germanium":"Ge","arsenic":"As",
    "zirconium":"Zr","niobium":"Nb","molybdenum":"Mo","ruthenium":"Ru",
    "rhodium":"Rh","palladium":"Pd","silver":"Ag","cadmium":"Cd","tin":"Sn",
    "antimony":"Sb","caesium":"Cs","cesium":"Cs","barium":"Ba","lanthanum":"La",
    "cerium":"Ce","neodymium":"Nd","samarium":"Sm","gadolinium":"Gd",
    "hafnium":"Hf","tantalum":"Ta","tungsten":"W","wolfram":"W","rhenium":"Re",
    "osmium":"Os","iridium":"Ir","platinum":"Pt","gold":"Au","mercury":"Hg",
    "thallium":"Tl","lead":"Pb","bismuth":"Bi","thorium":"Th","uranium":"U",
    "plutonium":"Pu","yttrium":"Y","niobium":"Nb","ruthenium":"Ru",
}


def _find_elements(text: str) -> list:
    found = []
    tl = text.lower()
    for name, sym in ELEMENT_NAMES.items():
        if re.search(r'\b' + re.escape(name) + r'\b', tl) and sym not in found:
            found.append(sym)
    for sym in sorted(ALL_SYMS, key=len, reverse=True):
        if sym not in found:
            pat = r'(?<![A-Za-z])' + re.escape(sym) + r'(?![a-z])'
            if re.search(pat, text):
                found.append(sym)
    return found


def parse_query(query: str) -> dict:
    q = query
    ql = query.lower()

    result = {
        "only_elements":    None,
        "must_include":     [],
        "exclude_elements": [],
        "application":      "",
        "T_op_K":           298.0,
        "min_PREN":         None,
        "min_elements":     2,
        "max_elements":     10,
        "notes":            query,
    }

    only_patterns = [
        r'only\s+(?:use\s+|contain\s+|from\s+)?([A-Za-z,\s\-and]+?)(?:\s+elements?|\s+alloy|\s+for|\s*$)',
        r'restrict(?:ed)?\s+to\s+([A-Za-z,\s\-and]+?)(?:\s+elements?|\s*$)',
        r'([A-Z][a-z]?(?:\s*[\-,]\s*[A-Z][a-z]?){1,7})\s+(?:binary|ternary|system|alloy|only)',
        r'(?:binary|ternary|quaternary|quinary)\s+([A-Za-z\-]+?)\s+(?:alloy|system)',
        r'elements?\s*[:=]\s*\[?([A-Za-z,\s\-and]+)\]?',
    ]
    for pat in only_patterns:
        m = re.search(pat, q, re.IGNORECASE)
        if m:
            elems = _find_elements(m.group(1))
            if len(elems) >= 2:
                result["only_elements"] = elems
                break

    must_patterns = [
        r'must\s+(?:contain|include|have)\s+([A-Za-z,\s\-and]+?)(?=\s+[a-z]|\s*$)',
        r'add(?:ed)?\s+([A-Za-z,\s]+?)(?=\s+to|\s+for|\s*$)',
    ]
    for pat in must_patterns:
        m = re.search(pat, ql)
        if m:
            for e in _find_elements(m.group(1).title()):
                if e not in result["must_include"]:
                    result["must_include"].append(e)

    excl_text = []
    for pat in [r'(?:no|without|avoid|exclude)\s+([A-Za-z,\s\-and]+?)(?=\s+[a-z]|\s*$)',
                r'([A-Za-z]+)\-free',
                r'not\s+(?:contain(?:ing)?)?\s+([A-Za-z,\s]+)'   ]:
        for m in re.finditer(pat, ql):
            excl_text.append(m.group(1))
    for txt in excl_text:
        for e in _find_elements(txt.title()):
            if e not in result["exclude_elements"]:
                result["exclude_elements"].append(e)

    for pat, is_celsius in [
        (r'(\d{2,4})\s*[°oO]C', True),
        (r'(\d{3,4})\s*K(?:\s+service|\s+op|\s+temp)', False),
        (r'T\s*=\s*(\d{3,4})\s*K', False),
    ]:
        m = re.search(pat, q, re.IGNORECASE)
        if m:
            val = float(m.group(1))
            result["T_op_K"] = val + 273.15 if is_celsius else val
            break

    m = re.search(r'PREN\s*[>≥>=]+\s*(\d+)', q, re.IGNORECASE)
    if m:
        result["min_PREN"] = float(m.group(1))

    for word, n in [("binary",2),("ternary",3),("quaternary",4),("quinary",5),("senary",6)]:
        if word in ql:
            result["min_elements"] = result["max_elements"] = n; break

    m_exact_count = re.search(r"\b(\d{1,2})\s*[-\s]?(?:element|component)\b", ql)
    if m_exact_count:
        try:
            exact = int(m_exact_count.group(1))
            if 2 <= exact <= 12:
                result["min_elements"] = exact
                result["max_elements"] = exact
        except Exception:
            pass

    for app, kws in [
        ("fusible_alloy",   ["fuse alloy","fuse wire","fusible","fusible wire","low melting","low-melting","solder","solder alloy","thermal fuse","fusible link","braze filler"]),
        ("electronic_alloy",["chip alloy","chip package","semiconductor","interconnect","bond wire","wire bond","solder bump","microelectronics","electronic packaging","leadframe"]),
        ("stainless",       ["stainless","316","304","duplex","marine","corrosion","bridge","pipeline","coastal"]),
        ("superalloy",      ["superalloy","turbine","jet","inconel","gas turbine","blade"]),
        ("ti_alloy",        ["titanium","ti-6","ti64","aerospace lightweight","ti alloy"]),
        ("al_alloy",        ["aluminium","aluminum","al alloy","2024","7075","6061"]),
        ("carbon_steel",    ["carbon steel","plain carbon steel","mild steel"]),
        ("nuclear",         ["nuclear","reactor","cladding","zircaloy","neutron","fission"]),
        ("hea",             ["hea","high entropy","cantor","multiprincipal","equiatomic"]),
        ("refractory",      ["refractory",">1000°","1200°c","high temperature furnace"]),
        ("biomedical",      ["biomedical","implant","surgical","bone","dental","hip","knee"]),
        ("shape_memory",    ["shape memory","sma","nitinol","superelastic"]),
        ("catalysis",       ["catalyst","catalytic","her","orr","fuel cell","electrocatal"]),
        ("hydrogen_storage",["hydrogen storage","h2 storage","hydride"]),
    ]:
        if any(kw in ql for kw in kws):
            result["application"] = app; break

    if any(kw in ql for kw in ["lead-free", "pb-free", "rohs", "cadmium-free", "cd-free"]):
        for symbol in ["Pb", "Cd", "Hg"]:
            if symbol not in result["exclude_elements"]:
                result["exclude_elements"].append(symbol)

    return result


def describe_constraints(parsed: dict) -> str:
    lines = []
    if parsed["only_elements"]:
        lines.append(f"  [LOCK] Element restriction: {parsed['only_elements']}")
    if parsed["must_include"]:
        lines.append(f"  [INCLUDE] Must include: {parsed['must_include']}")
    if parsed["exclude_elements"]:
        lines.append(f"  [EXCLUDE] Excluded: {parsed['exclude_elements']}")
    if parsed["application"]:
        lines.append(f"  [APP] Application: {parsed['application']}")
    if parsed["T_op_K"] != 298.0:
        lines.append(f"  [TEMP] T_op: {parsed['T_op_K']:.0f} K  ({parsed['T_op_K']-273:.0f} C)")
    if parsed["min_PREN"]:
        lines.append(f"  [PREN] PREN >= {parsed['min_PREN']}")
    if parsed["min_elements"] == parsed["max_elements"] and parsed["min_elements"] > 2:
        lines.append(f"  [COUNT] Exactly {parsed['min_elements']} elements")
    return "\n".join(lines) if lines else "  (general search, no specific element constraints)"
