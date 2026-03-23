import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from physics.base import *

ID = 1
NAME = "Thermodynamics"

def run(comp: dict, T_K: float = 298.0, **_) -> DomainResult:
    c = norm(comp)
    checks = []

    dH = delta_H_mix(c)
    if dH is None:
        checks.append(INFO("ΔHmix", None, "kJ/mol",
            "Insufficient Miedema parameters for this composition",
            "Boer et al. (1988) Cohesion in Metals"))
    elif -15 <= dH <= 5:
        checks.append(PASS("ΔHmix", dH, "kJ/mol",
            f"ΔHmix = {dH:.2f} kJ/mol ∈ [-15,+5] — solid-solution favoured",
            "Boer et al. (1988) Cohesion in Metals; Miedema (1980) Physica B 100:1",
            "ΔHmix = Σᵢ≠ 4cᵢcΔH_AB"))
    elif dH < -40 or dH > 20:
        checks.append(FAIL("ΔHmix", dH, "kJ/mol",
            f"ΔHmix = {dH:.2f} kJ/mol — extreme value, ordered intermetallic likely",
            "Boer et al. (1988) Cohesion in Metals",
            "ΔHmix = Σᵢ≠ 4cᵢcΔH_AB"))
    else:
        checks.append(WARN("ΔHmix", dH, "kJ/mol",
            f"ΔHmix = {dH:.2f} kJ/mol — borderline; possible secondary phases",
            "Boer et al. (1988) Cohesion in Metals",
            "ΔHmix = Σᵢ≠ 4cᵢcΔH_AB"))

    import math
    dS = delta_S_mix(c)
    n = len(c)
    dS_max = R * math.log(n) if n > 1 else 0
    if dS >= 11.0:
        checks.append(PASS("ΔSmix", dS, "J/mol·K",
            f"ΔSmix = {dS:.2f} ≥ 11 J/mol·K — high-entropy regime",
            "Yeh et al. (2004) Adv. Eng. Mater. 6:299",
            "ΔSmix = −R Σᵢ cᵢ ln cᵢ"))
    elif dS >= 6.0:
        checks.append(WARN("ΔSmix", dS, "J/mol·K",
            f"ΔSmix = {dS:.2f} — medium-entropy; entropy contribution moderate",
            "Yeh et al. (2004) Adv. Eng. Mater. 6:299",
            "ΔSmix = −R Σᵢ cᵢ ln cᵢ"))
    else:
        checks.append(INFO("ΔSmix", dS, "J/mol·K",
            f"ΔSmix = {dS:.2f} — conventional alloy (low-entropy regime)",
            "Yeh et al. (2004) Adv. Eng. Mater. 6:299",
            "ΔSmix = −R Σᵢ cᵢ ln cᵢ"))

    Om = omega_param(c)
    if Om is None:
        checks.append(INFO("Ω (Yang-Zhang)", None, "",
            "ΔHmix ≈ 0 or not calculable — Ω undefined",
            "Yang & Zhang (2012) Mater. Chem. Phys. 132:233"))
    elif Om >= 1.1:
        checks.append(PASS("Ω (Yang-Zhang)", Om, "",
            f"Ω = {Om:.2f} ≥ 1.1 — entropic stabilisation dominates; SS expected",
            "Yang & Zhang (2012) Mater. Chem. Phys. 132:233",
            "Ω = T̄ₘ · ΔSmix / |ΔHmix|"))
    else:
        checks.append(FAIL("Ω (Yang-Zhang)", Om, "",
            f"Ω = {Om:.2f} < 1.1 — intermetallic compound likely to precipitate",
            "Yang & Zhang (2012) Mater. Chem. Phys. 132:233",
            "Ω = T̄ₘ · ΔSmix / |ΔHmix|"))

    if dH is not None:
        dG = dH * 1000 - T_K * dS
        if dG < -2000:
            checks.append(PASS("ΔGmix at T", dG / 1000, "kJ/mol",
                f"ΔGmix = {dG/1000:.2f} kJ/mol < 0 — mixing thermodynamically spontaneous at {T_K:.0f} K",
                "Kubaschewski & Alcock (1979) Metallurgical Thermochemistry 5th ed.",
                "ΔGmix = ΔHmix − T·ΔSmix"))
        elif dG < 0:
            checks.append(PASS("ΔGmix at T", dG / 1000, "kJ/mol",
                f"ΔGmix = {dG/1000:.2f} kJ/mol < 0 — stable at {T_K:.0f} K",
                "Kubaschewski & Alcock (1979)",
                "ΔGmix = ΔHmix − T·ΔSmix"))
        else:
            checks.append(WARN("ΔGmix at T", dG / 1000, "kJ/mol",
                f"ΔGmix = {dG/1000:.2f} kJ/mol > 0 at {T_K:.0f} K — check higher processing T",
                "Kubaschewski & Alcock (1979)",
                "ΔGmix = ΔHmix − T·ΔSmix"))

    VEC_val = vec(c)
    sigma_formers = c.get("Cr",0) + c.get("Mo",0) + c.get("W",0) + c.get("V",0) + c.get("Si",0)
    if 6.0 <= VEC_val <= 8.0 and sigma_formers > 0.25:
        checks.append(WARN("σ-phase risk", sigma_formers * 100, "at%",
            f"VEC={VEC_val:.2f} ∈ [6,8] and σ-formers={sigma_formers*100:.1f}% > 25% — σ/Laves possible",
            "Sims et al. (1987) Superalloys II; Solomon & Devine (1982) ASM",
            "VEC ∈ [6,8] ∧ Σ(Cr,Mo,W,V,Si) > 25 at%"))
    else:
        checks.append(PASS("σ-phase risk", sigma_formers * 100, "at%",
            f"σ-formers = {sigma_formers*100:.1f}%, VEC = {VEC_val:.2f} — low σ-phase risk",
            "Sims et al. (1987) Superalloys II",
            "VEC ∈ [6,8] ∧ σ-formers > 25%"))

    return DomainResult(ID, NAME, checks)
