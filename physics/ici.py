
import math
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from physics.base import *

ID   = 32
NAME = "India Corrosion Index"

ALPHA_H = 0.15
ALPHA_C = 0.25
ALPHA_T = 0.10
ALPHA_R = 0.08

ENVIRONMENTS = {
    "mumbai_coastal":   (82, 500,  31, 7.1,  96),
    "chennai_coastal":  (75, 400,  32, 7.3,  53),
    "kolkata_coastal":  (82, 200,  28, 7.0, 132),
    "delhi_inland":     (60,  20,  25, 7.5,  45),
    "offshore_arabian": (90, 2000, 34, 8.1,   5),
}

ICI_PASS = 40.0
ICI_WARN = 25.0


def _parse_weather(weather_str: str) -> tuple | None:
    if weather_str is None:
        return None

    key = weather_str.strip().lower()
    if key in ENVIRONMENTS:
        return ENVIRONMENTS[key]

    try:
        parts = dict(item.split(":") for item in weather_str.split(","))
        RH        = float(parts.get("RH",        75))
        Cl        = float(parts.get("Cl",        35))
        T_env     = float(parts.get("T_env",     25))
        pH        = float(parts.get("pH",         7))
        rain_days = float(parts.get("rain_days", 60))
        return (RH, Cl, T_env, pH, rain_days)
    except Exception:
        return None


def _corrosion_resistance_proxy(c: dict) -> float:
    ni = c.get("Ni", 0)
    cr = c.get("Cr", 0)
    mo = c.get("Mo", 0)
    ti = c.get("Ti", 0)

    wt = mol_to_wt(c)
    cr_wt = wt.get("Cr", 0) * 100
    mo_wt = wt.get("Mo", 0) * 100
    ni_wt = wt.get("Ni", 0) * 100
    ti_wt = wt.get("Ti", 0) * 100

    if ni > 0.40:
        return cr_wt + 3.3 * mo_wt + 0.5 * ni_wt * 0.3
    elif ti > 0.50:
        return 45.0
    elif c.get("Al", 0) > 0.50:
        return 15.0 + cr_wt
    else:
        return 20.0


def compute_ici(pren_eff: float, RH: float, Cl_mg_L: float,
                T_env_C: float, rain_days: float) -> float:
    H_factor = 1.0 + ALPHA_H * max(0, (RH - 60) / 40.0)

    Cl_safe = max(Cl_mg_L, 1.0)
    C_factor = 1.0 + ALPHA_C * math.log10(Cl_safe / 35.0)
    C_factor = max(C_factor, 0.5)

    T_factor = 1.0 + ALPHA_T * (T_env_C - 25.0) / 10.0
    T_factor = max(T_factor, 0.8)

    R_factor = 1.0 + ALPHA_R * rain_days / 100.0

    environmental_severity = H_factor * C_factor * T_factor * R_factor
    ici_score = pren_eff / environmental_severity

    return round(ici_score, 2)


def run(comp: dict, weather: str = None, T_K: float = 298.0, **_) -> DomainResult:
    c = norm(comp)
    checks = []

    if not weather:
        checks.append(INFO("India Corrosion Index (inactive)", None, "",
            "Provide --weather to activate. Example: --weather mumbai_coastal  "
            "or  --weather 'RH:82,Cl:500,T_env:31,rain_days:96'",
            "Novel index — see physics/ici.py for formula and citations"))
        return DomainResult(ID, NAME, checks)

    env = _parse_weather(weather)
    if env is None:
        checks.append(INFO("India Corrosion Index (parse error)", None, "",
            f"Could not parse --weather '{weather}'. "
            f"Valid presets: {list(ENVIRONMENTS.keys())}",
            "Novel index — see physics/ici.py"))
        return DomainResult(ID, NAME, checks)

    RH, Cl_mg_L, T_env_C, pH, rain_days = env
    env_label = weather if weather in ENVIRONMENTS else f"RH={RH}%, Cl={Cl_mg_L}mg/L"

    wt = mol_to_wt(c)
    fe_wt  = wt.get("Fe", 0) * 100
    cr_wt  = wt.get("Cr", 0) * 100
    mo_wt  = wt.get("Mo", 0) * 100
    n_wt   = wt.get("N",  0) * 100

    if fe_wt > 30 and cr_wt > 5:
        pren_eff = cr_wt + 3.3 * mo_wt + 16 * n_wt
        pren_label = f"PREN={pren_eff:.1f}"
    else:
        pren_eff = _corrosion_resistance_proxy(c)
        pren_label = f"corrosion proxy={pren_eff:.1f}"

    ici = compute_ici(pren_eff, RH, Cl_mg_L, T_env_C, rain_days)

    H_factor  = 1.0 + ALPHA_H * max(0, (RH - 60) / 40.0)
    Cl_safe   = max(Cl_mg_L, 1.0)
    C_factor  = max(1.0 + ALPHA_C * math.log10(Cl_safe / 35.0), 0.5)
    T_factor  = max(1.0 + ALPHA_T * (T_env_C - 25.0) / 10.0, 0.8)
    R_factor  = 1.0 + ALPHA_R * rain_days / 100.0
    sev       = round(H_factor * C_factor * T_factor * R_factor, 3)

    detail = (f"env={env_label}, RH={RH}%, Cl={Cl_mg_L}mg/L, "
              f"T={T_env_C}°C, rain={rain_days}d/yr, "
              f"severity={sev:.2f}x, {pren_label}")

    citation = ("Proposed index. Factors from: ISO 9223:2012; "
                "Knotkova et al. (1995) NACE/95 P552; "
                "Roberge (2008) Corrosion Eng. Ch.5; "
                "Revie & Uhlig (2008) 4th ed.; "
                "Natesan & Venkatachari (2006) Curr. Sci. 90:1060")
    formula  = ("ICI = PREN_eff / (H_f * C_f * T_f * R_f)  "
                "H_f=1+0.15*(RH-60)/40, C_f=1+0.25*log10(Cl/35), "
                "T_f=1+0.10*(T-25)/10, R_f=1+0.08*rain_days/100")

    if ici >= ICI_PASS:
        checks.append(PASS("ICI (India Corrosion Index)", ici, "",
            f"ICI={ici:.1f} >= 40 — suitable for Indian coastal/tropical exposure. {detail}",
            citation, formula))
    elif ici >= ICI_WARN:
        checks.append(WARN("ICI (India Corrosion Index)", ici, "",
            f"ICI={ici:.1f} — marginal for Indian coastal use. "
            f"Protective coating or cathodic protection recommended. {detail}",
            citation, formula))
    else:
        checks.append(FAIL("ICI (India Corrosion Index)", ici, "",
            f"ICI={ici:.1f} < 25 — unsuitable for unprotected Indian coastal exposure. {detail}",
            citation, formula))

    if pH < 6.5:
        checks.append(WARN("Acidic environment (pH)", pH, "",
            f"pH={pH:.1f} < 6.5 — passive film on Cr may dissolve; "
            f"increases pitting risk substantially.",
            "Revie & Uhlig (2008) Corrosion and Corrosion Control 4th ed.",
            "Cr2O3 passive film stable pH 4-13; below 4 active dissolution"))
    elif pH > 9.0:
        checks.append(INFO("Alkaline environment (pH)", pH, "",
            f"pH={pH:.1f} > 9.0 — alkaline condition; generally favours passivity "
            f"but may cause stress corrosion cracking in specific alloys.",
            "Revie & Uhlig (2008) 4th ed."))
    else:
        checks.append(PASS("pH in passive range", pH, "",
            f"pH={pH:.1f} — within passive film stability range (6.5-9.0).",
            "Revie & Uhlig (2008) 4th ed."))

    return DomainResult(ID, NAME, checks)
