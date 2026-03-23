import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from physics.base import *

ID   = 35
NAME = "Machinability"
WEIGHT = 0.8

MACHINABILITY_INDEX = {
    "Fe": 50, "Cr": 30, "Ni": 30, "Mo": 30, "V": 25, "W": 20,
    "Ti": 22, "Co": 25, "Al": 300, "Cu": 200, "Mg": 500, "Zn": 250,
    "Mn": 40, "Si": 35, "Nb": 20, "Ta": 15, "Zr": 25, "Sn": 200,
    "Pb": 400, "S": 450, "C": 45,
}

def run(comp: dict, T_K: float = 298.0, **kw) -> DomainResult:
    c = norm(comp)
    checks = []

    mi = sum(c.get(s, 0) * MACHINABILITY_INDEX.get(s, 40) for s in c)
    if mi > 80:
        checks.append(PASS("Machinability index", mi, "%",
            f"MI={mi:.0f}% (vs AISI 1212=100%) — good",
            "ASM Handbook Vol.16 (1989)", "MI = Σ cᵢ × MIᵢ"))
    elif mi > 40:
        checks.append(WARN("Machinability index", mi, "%",
            f"MI={mi:.0f}% — moderate, may need carbide tooling",
            "ASM Handbook Vol.16 (1989)", "MI = Σ cᵢ × MIᵢ"))
    else:
        checks.append(FAIL("Machinability index", mi, "%",
            f"MI={mi:.0f}% — difficult to machine, use CBN/diamond",
            "ASM Handbook Vol.16 (1989)", "MI = Σ cᵢ × MIᵢ"))

    hv = wmean(c, "vickers")
    if hv:
        if hv < 250:
            checks.append(PASS("Hardness for machining", hv/9.807, "HV",
                f"HV={hv/9.807:.0f} — easy cutting",
                "Machinery's Handbook 31st ed."))
        elif hv < 400:
            checks.append(WARN("Hardness for machining", hv/9.807, "HV",
                f"HV={hv/9.807:.0f} — needs hard tooling",
                "Machinery's Handbook 31st ed."))
        else:
            checks.append(FAIL("Hardness for machining", hv/9.807, "HV",
                f"HV={hv/9.807:.0f} — grinding/EDM may be needed",
                "Machinery's Handbook 31st ed."))

    k = wmean(c, "thermal_cond")
    if k:
        if k > 50:
            checks.append(PASS("Thermal conductivity", k, "W/(m·K)",
                "Good heat dissipation during cutting",
                "Trent & Wright (2000) Metal Cutting 4th ed."))
        elif k > 15:
            checks.append(INFO("Thermal conductivity", k, "W/(m·K)",
                "Moderate — built-up edge possible",
                "Trent & Wright (2000)"))
        else:
            checks.append(WARN("Thermal conductivity", k, "W/(m·K)",
                f"Low k={k:.0f} — tool overheating risk, use coolant",
                "Trent & Wright (2000)"))

    E = wmean(c, "E")
    if E and hv:
        ratio = E * 1000 / hv
        if ratio > 500:
            checks.append(WARN("Work hardening", ratio, "",
                "High E/Hv ratio — significant work hardening expected",
                "Childs et al. (2000) Metal Machining"))
        else:
            checks.append(PASS("Work hardening", ratio, "",
                "Moderate E/Hv — acceptable",
                "Childs et al. (2000)"))

    return DomainResult(ID, NAME, checks)
