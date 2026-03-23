import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from physics.base import *

ID = 2
NAME = "Hume-Rothery"

def run(comp: dict, **_) -> DomainResult:
    c = norm(comp)
    checks = []

    d = delta_size(c)
    if d <= 5.0:
        checks.append(PASS("Atomic size δ", d, "%",
            f"δ = {d:.2f}% ≤ 5% — good lattice compatibility",
            "Zhang et al. (2008) Adv. Eng. Mater. 10:534",
            "δ = 100√(Σᵢ cᵢ(1 − rᵢ/r̄)²)  [Slater radii]"))
    elif d <= 8.5:
        checks.append(WARN("Atomic size δ", d, "%",
            f"δ = {d:.2f}% — moderate lattice distortion; SS may form but with strain",
            "Zhang et al. (2008) Adv. Eng. Mater. 10:534",
            "δ = 100√(Σᵢ cᵢ(1 − rᵢ/r̄)²)"))
    else:
        checks.append(FAIL("Atomic size δ", d, "%",
            f"δ = {d:.2f}% > 8.5% — excessive lattice strain; solid solution unlikely",
            "Zhang et al. (2008) Adv. Eng. Mater. 10:534",
            "δ = 100√(Σᵢ cᵢ(1 − rᵢ/r̄)²)"))

    dchi = delta_chi(c)
    if dchi is None:
        checks.append(INFO("Δχ (Pauling)", None, "",
            "Missing electronegativity data for one or more elements",
            "Allen (1989) JACS 111:9003"))
    elif dchi <= 0.1:
        checks.append(PASS("Δχ (Pauling)", dchi, "",
            f"Δχ = {dchi:.3f} ≤ 0.1 — very similar electronegativity; metallic SS expected",
            "Hume-Rothery (1926) J. Inst. Met. 35:295; Allen (1989)",
            "Δχ = √(Σᵢ cᵢ(χᵢ − χ̄)²)"))
    elif dchi <= 0.4:
        checks.append(PASS("Δχ (Pauling)", dchi, "",
            f"Δχ = {dchi:.3f} — acceptable; limited ordering tendency",
            "Hume-Rothery (1926); Allen (1989)",
            "Δχ = √(Σᵢ cᵢ(χᵢ − χ̄)²)"))
    else:
        checks.append(FAIL("Δχ (Pauling)", dchi, "",
            f"Δχ = {dchi:.3f} > 0.4 — strong electronegativity difference; compound tendency",
            "Hume-Rothery (1926); Pettifor (1986) J. Phys. C 19:285",
            "Δχ = √(Σᵢ cᵢ(χᵢ − χ̄)²)"))

    VEC_val = vec(c)
    if VEC_val >= 8.0:
        pred = "FCC dominant"
        checks.append(PASS("VEC (crystal structure)", VEC_val, "",
            f"VEC = {VEC_val:.2f} ≥ 8.0 → {pred}",
            "Guo et al. (2011) Calphad 35:95; Poletti & Battezzati (2014)",
            "VEC = Σᵢ cᵢ VECᵢ;  FCC: VEC≥8;  BCC: 6≤VEC<6.87;  mixed: 6.87≤VEC<8"))
    elif VEC_val >= 6.87:
        pred = "FCC+BCC mixed"
        checks.append(PASS("VEC (crystal structure)", VEC_val, "",
            f"VEC = {VEC_val:.2f} ∈ [6.87,8) → {pred}",
            "Guo et al. (2011) Calphad 35:95",
            "VEC = Σᵢ cᵢ VECᵢ"))
    elif VEC_val >= 6.0:
        pred = "BCC dominant"
        checks.append(PASS("VEC (crystal structure)", VEC_val, "",
            f"VEC = {VEC_val:.2f} ∈ [6,6.87) → {pred}",
            "Guo et al. (2011) Calphad 35:95",
            "VEC = Σᵢ cᵢ VECᵢ"))
    else:
        pred = "HCP or complex intermetallic"
        checks.append(WARN("VEC (crystal structure)", VEC_val, "",
            f"VEC = {VEC_val:.2f} < 6 → {pred}",
            "Guo et al. (2011) Calphad 35:95",
            "VEC = Σᵢ cᵢ VECᵢ"))

    n_principal = sum(1 for xi in c.values() if xi >= 0.05)
    if n_principal >= 5:
        checks.append(PASS("Principal elements (≥5 at%)", n_principal, "",
            f"{n_principal} elements ≥ 5 at% — qualifies as HEA/MPEA (high configurational entropy)",
            "Yeh et al. (2004) Adv. Eng. Mater. 6:299; Cantor et al. (2004) Mater. Sci. Eng. A 375:213",
            "n_principal = count(cᵢ ≥ 0.05)"))
    elif n_principal >= 3:
        checks.append(INFO("Principal elements (≥5 at%)", n_principal, "",
            f"{n_principal} elements ≥ 5 at% — medium-entropy / complex alloy",
            "Yeh et al. (2004)",
            "n_principal = count(cᵢ ≥ 0.05)"))
    else:
        checks.append(INFO("Principal elements (≥5 at%)", n_principal, "",
            f"{n_principal} principal element(s) — conventional alloy",
            "Yeh et al. (2004)",
            "n_principal = count(cᵢ ≥ 0.05)"))

    return DomainResult(ID, NAME, checks)
