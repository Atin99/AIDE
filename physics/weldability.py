import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from physics.base import *

ID = 7
NAME = "Weldability"

def run(comp: dict, thickness_mm: float = 25.0, **_) -> DomainResult:
    c = norm(comp)
    checks = []
    wt = mol_to_wt(c)

    def wp(sym): return wt.get(sym, 0) * 100

    fe_wt = wp("Fe")

    c_wt = wp("C"); cr_wt = wp("Cr")

    if fe_wt >= 50 and cr_wt < 10:
        CE = (c_wt + wp("Mn")/6
              + (cr_wt + wp("Mo") + wp("V"))/5
              + (wp("Ni") + wp("Cu"))/15)
        if CE < 0.40:
            checks.append(PASS("CE_IIW", CE, "wt%",
                f"CE = {CE:.3f} < 0.40 — excellent weldability, no preheat required",
                "IIW Doc. IX-535-67 (1967); ISO 17642",
                "CE = C + Mn/6 + (Cr+Mo+V)/5 + (Ni+Cu)/15"))
        elif CE < 0.60:
            checks.append(WARN("CE_IIW", CE, "wt%",
                f"CE = {CE:.3f} — moderate; preheat 100–200 °C recommended",
                "IIW Doc. IX-535-67 (1967); ISO 17642",
                "CE = C + Mn/6 + (Cr+Mo+V)/5 + (Ni+Cu)/15"))
        else:
            checks.append(FAIL("CE_IIW", CE, "wt%",
                f"CE = {CE:.3f} > 0.60 — high HAZ cracking risk; strict preheat required",
                "IIW Doc. IX-535-67 (1967); ISO 17642",
                "CE = C + Mn/6 + (Cr+Mo+V)/5 + (Ni+Cu)/15"))
    elif fe_wt >= 30 and cr_wt >= 10:
        Cr_eq = cr_wt + wp("Mo") + 1.5*wp("Si") + 0.5*wp("Nb")
        Ni_eq = wp("Ni") + 30*c_wt + 0.5*wp("Mn")
        if Ni_eq > 12 and Cr_eq > 17:
            struct = "Austenite dominant — good weldability"
            checks.append(PASS("Schaeffler (SS weldability)", Cr_eq, "Cr_eq wt%",
                f"Cr_eq={Cr_eq:.1f}, Ni_eq={Ni_eq:.1f} → {struct}",
                "Schaeffler (1949) Met. Prog. 56:680; Lippold & Kotecki (2005)",
                "Cr_eq = Cr+Mo+1.5Si+0.5Nb;  Ni_eq = Ni+30C+0.5Mn"))
        elif Cr_eq > 25:
            checks.append(WARN("Schaeffler (SS weldability)", Cr_eq, "Cr_eq wt%",
                f"Cr_eq={Cr_eq:.1f} > 25 — ferrite + σ-phase risk in HAZ",
                "Schaeffler (1949); Lippold & Kotecki (2005)",
                "Cr_eq = Cr+Mo+1.5Si+0.5Nb"))
        else:
            checks.append(INFO("Schaeffler (SS weldability)", Cr_eq, "Cr_eq wt%",
                f"Cr_eq={Cr_eq:.1f}, Ni_eq={Ni_eq:.1f} → mixed microstructure in weld",
                "Schaeffler (1949)",
                "Cr_eq = Cr+Mo+1.5Si+0.5Nb"))
    else:
        checks.append(INFO("Weldability", fe_wt, "wt% Fe",
            f"CE_IIW/Schaeffler not applicable (Fe={fe_wt:.1f}%); consult alloy-specific data",
            "Lippold & Kotecki (2005) Welding Metallurgy and Weldability of SS"))

    reheat_risk = wp("Nb") + wp("V") + wp("Ti")
    if reheat_risk > 0.15 and fe_wt > 40:
        checks.append(WARN("Reheat cracking risk", reheat_risk, "wt%",
            f"Nb+V+Ti = {reheat_risk:.3f} wt% — precipitation embrittlement in PWHT possible",
            "Dhooge & Vinckier (1992) Weld. World 30:44",
            "Reheat cracking index: Nb+V+Ti > 0.15 wt% at risk"))
    else:
        checks.append(PASS("Reheat cracking risk", reheat_risk, "wt%",
            f"Nb+V+Ti = {reheat_risk:.3f} wt% — low reheat cracking risk",
            "Dhooge & Vinckier (1992) Weld. World 30:44"))

    if fe_wt >= 50 and cr_wt < 10:
        c_wt_local = wp("C")
        CE_local = (c_wt_local + wp("Mn")/6
                    + (wp("Cr") + wp("Mo") + wp("V"))/5
                    + (wp("Ni") + wp("Cu"))/15)
        if CE_local > 0.25:
            import math
            T_pre = 350 * math.sqrt(CE_local - 0.25) * math.sqrt(thickness_mm / 100.0)
            if T_pre < 50:
                checks.append(PASS("Preheat temp (IIW, t={:.0f}mm)".format(thickness_mm),
                    T_pre, "degC",
                    f"T_preheat = {T_pre:.0f} degC (< 50 — ambient preheat acceptable)",
                    "Seferian (1959) Metallurgie de la Soudure; IIW IX-535-67",
                    "T_pre = 350*sqrt(CE-0.25)*sqrt(t/100)"))
            elif T_pre < 150:
                checks.append(WARN("Preheat temp (IIW, t={:.0f}mm)".format(thickness_mm),
                    T_pre, "degC",
                    f"T_preheat = {T_pre:.0f} degC — preheat required before welding",
                    "Seferian (1959); IIW IX-535-67",
                    "T_pre = 350*sqrt(CE-0.25)*sqrt(t/100)"))
            else:
                checks.append(FAIL("Preheat temp (IIW, t={:.0f}mm)".format(thickness_mm),
                    T_pre, "degC",
                    f"T_preheat = {T_pre:.0f} degC > 150 — high preheat; HAZ cracking risk",
                    "Seferian (1959); IIW IX-535-67",
                    "T_pre = 350*sqrt(CE-0.25)*sqrt(t/100)"))
        else:
            checks.append(INFO("Preheat temp (IIW)", 0.0, "degC",
                f"CE = {CE_local:.3f} < 0.25 — no preheat required (t={thickness_mm:.0f}mm)",
                "IIW IX-535-67",
                "T_pre = 350*sqrt(CE-0.25)*sqrt(t/100); zero if CE <= 0.25"))

    return DomainResult(ID, NAME, checks)
