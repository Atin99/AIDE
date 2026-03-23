import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from physics.base import *

ID = 27
NAME = "Nuclear Fuel Compatibility"

U_EUTECTIC_K = {
    "Fe": 998,   "Ni": 900,  "Cr": 1523, "Co": 1100,
    "Al": 930,   "Si": 940,  "Mn": 983,  "Mo": 2173,
    "Zr": 1680,  "Nb": 1800,
}

FCCI_RATE = {
    "Fe": 0.30, "Ni": 0.70, "Cr": 0.40, "Co": 0.50,
    "Mo": 0.10, "Zr": 0.05, "V":  0.20, "Ti": 0.15,
    "Si": 0.20, "Mn": 0.25,
}


def run(comp: dict, T_K: float = 1073.0, **_) -> DomainResult:
    c = norm(comp)
    checks = []

    u_pu = c.get("U",0) + c.get("Pu",0)

    if u_pu < 0.01:
        checks.append(INFO("Nuclear fuel context", u_pu*100, "at% U+Pu",
            "U/Pu content < 1% — this is a cladding/structural material, not fuel. "
            "Evaluating as structural material for nuclear service.",
            "Was (2007) Fundamentals of Radiation Materials Science"))
        zr_at = c.get("Zr",0)
        if zr_at > 0.8:
            checks.append(PASS("Zr-base cladding suitability", zr_at*100, "at% Zr",
                f"Zr = {zr_at*100:.1f}% — Zircaloy-type; low σ_thermal = {get('Zr').neutron_xs} barns; "
                f"excellent corrosion in water at 300–400°C",
                "IAEA-TECDOC-1654 (2011); Lemaignan & Motta (1994) Mater. Sci. Tech. 10B:1",
                "Zr cladding: σ_n = 0.185 barns; corrosion resistant; zirconia ZrO₂ protective"))
        return DomainResult(ID, NAME, checks)

    non_fuel_elems = {s: c[s] for s in c if s not in {"U","Pu","Am","Np"}}
    fcci = sum(non_fuel_elems.get(s,0) * FCCI_RATE.get(s, 0.25)
               for s in non_fuel_elems)
    if fcci < 0.10:
        checks.append(PASS("FCCI index", fcci, "0–1",
            f"FCCI = {fcci:.3f} — low fuel-cladding chemical interaction",
            "Hofman et al. (1996) J. Nucl. Mater. 233:868",
            "FCCI: interdiffusion + eutectic formation between fuel and cladding"))
    elif fcci < 0.30:
        checks.append(WARN("FCCI index", fcci, "0–1",
            f"FCCI = {fcci:.3f} — moderate interaction; barrier layer may be needed",
            "Hofman et al. (1996); Was (2007) §14",
            "FCCI index = Σᵢ cᵢ·rate_FCCI,i"))
    else:
        checks.append(FAIL("FCCI index", fcci, "0–1",
            f"FCCI = {fcci:.3f} — HIGH interaction; cladding failure risk",
            "Hofman et al. (1996) J. Nucl. Mater. 233:868; IAEA-TECDOC-1654",
            "FCCI index = Σᵢ cᵢ·rate_FCCI,i"))

    min_eutectic = min((U_EUTECTIC_K.get(s, 2500) for s in non_fuel_elems),
                       default=2500)
    if min_eutectic > T_K + 400:
        checks.append(PASS("U-X eutectic T", min_eutectic, "K",
            f"Lowest U eutectic T = {min_eutectic} K — well above T_op={T_K:.0f} K",
            "Crawford et al. (2007) J. Nucl. Mater. 371:202",
            "U-Fe eutectic: 998 K; U-Ni: 900 K; U-Zr: 1680 K [Crawford 2007]"))
    elif min_eutectic > T_K:
        checks.append(WARN("U-X eutectic T", min_eutectic, "K",
            f"U eutectic T = {min_eutectic} K — only {min_eutectic-T_K:.0f} K above T_op",
            "Crawford et al. (2007) J. Nucl. Mater. 371:202",
            "Temperature margin < 400 K is concerning for transients"))
    else:
        checks.append(FAIL("U-X eutectic T", min_eutectic, "K",
            f"U eutectic T = {min_eutectic} K < T_op = {T_K:.0f} K — LIQUID FUEL CONTACT possible",
            "Crawford et al. (2007) J. Nucl. Mater. 371:202",
            "Eutectic T below operating T → catastrophic cladding failure"))

    return DomainResult(ID, NAME, checks)
