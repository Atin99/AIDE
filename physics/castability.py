import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from physics.base import *

ID   = 34
NAME = "Castability"
WEIGHT = 0.9

def run(comp: dict, T_K: float = 298.0, **kw) -> DomainResult:
    c = norm(comp)
    checks = []

    Tm_max = max((get(s).Tm or 0) for s in c)
    Tm_mean = wmean(c, "Tm")
    if Tm_mean and Tm_max:
        freeze_range = Tm_max - Tm_mean
        if freeze_range < 50:
            checks.append(PASS("Freezing range", freeze_range, "K",
                f"Narrow ({freeze_range:.0f}K) — good castability",
                "Campbell (2015) Complete Casting Handbook", "ΔT_f = T_liq - T_sol"))
        elif freeze_range < 150:
            checks.append(WARN("Freezing range", freeze_range, "K",
                f"Moderate ({freeze_range:.0f}K) — some porosity risk",
                "Campbell (2015)", "ΔT_f = T_liq - T_sol"))
        else:
            checks.append(FAIL("Freezing range", freeze_range, "K",
                f"Wide ({freeze_range:.0f}K) — high porosity and hot tear risk",
                "Campbell (2015)", "ΔT_f = T_liq - T_sol"))

    if Tm_mean:
        superheat_capacity = Tm_mean * 0.05
        thermal_cond = wmean(c, "thermal_cond")
        if thermal_cond:
            fluidity_proxy = thermal_cond * superheat_capacity / 100
            if fluidity_proxy > 5:
                checks.append(PASS("Fluidity proxy", fluidity_proxy, "",
                    f"High fluidity ({fluidity_proxy:.1f}) — mould filling OK",
                    "Flemings (1974) Solidification Processing"))
            elif fluidity_proxy > 2:
                checks.append(WARN("Fluidity proxy", fluidity_proxy, "",
                    "Moderate fluidity", "Flemings (1974)"))
            else:
                checks.append(FAIL("Fluidity proxy", fluidity_proxy, "",
                    "Low fluidity — thin sections may not fill",
                    "Flemings (1974)"))

    density = density_rule_of_mixtures(c)
    if density:
        if density > 7.0:
            shrinkage_pct = 3.0 + (density - 7.0) * 0.5
        else:
            shrinkage_pct = 2.0 + density * 0.2
        shrinkage_pct = min(shrinkage_pct, 7.0)
        if shrinkage_pct < 4.0:
            checks.append(PASS("Shrinkage estimate", shrinkage_pct, "%",
                f"{shrinkage_pct:.1f}% volumetric — typical for alloy class",
                "ASM Handbook Vol.15 (2008)"))
        else:
            checks.append(WARN("Shrinkage estimate", shrinkage_pct, "%",
                f"{shrinkage_pct:.1f}% — compensate with risering",
                "ASM Handbook Vol.15 (2008)"))

    delt = delta_size(c)
    if delt > 5:
        checks.append(FAIL("Hot tearing risk", delt, "%δ",
            f"High size mismatch ({delt:.1f}%) increases hot crack risk",
            "Eskin (2004) Physical Metallurgy of Direct Chill Casting"))
    elif delt > 3:
        checks.append(WARN("Hot tearing risk", delt, "%δ",
            "Moderate risk", "Eskin (2004)"))
    else:
        checks.append(PASS("Hot tearing risk", delt, "%δ",
            f"Low risk ({delt:.1f}%)", "Eskin (2004)"))

    return DomainResult(ID, NAME, checks)
