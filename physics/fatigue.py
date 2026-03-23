import sys, os, math
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from physics.base import *

ID = 9
NAME = "Fatigue & Fracture"

SFE_COEFF = {
    "Mn": -60.0,
    "Ni":  10.0,
    "Cr": -25.0,
    "N":  -150.0,
    "C":  -100.0,
    "Co": -30.0,
    "Si":  30.0,
    "Al":  20.0,
    "Cu":  10.0,
}
SFE_BASE_FCC = 78.0


def _stacking_fault_energy(comp: dict) -> float:
    c = norm(comp)
    sfe = SFE_BASE_FCC
    wt = mol_to_wt(c)
    for sym, coeff in SFE_COEFF.items():
        sfe += coeff * wt.get(sym, 0) * 100
    return max(0.0, sfe)


def run(comp: dict, **_) -> DomainResult:
    c = norm(comp)
    checks = []

    E_pa  = (wmean(c, "E") or 200.0) * 1e9
    gamma_s = 2.0
    KIC_griffith = math.sqrt(E_pa * gamma_s * 2) / 1e6
    checks.append(INFO("K_IC elastic bound (Griffith)", KIC_griffith, "MPa√m",
        f"Elastic lower bound K_IC = √(2Eγ_s) = {KIC_griffith:.1f} MPa√m. "
        f"Actual metal K_IC ≫ this due to plasticity (e.g. 316SS: ~130, Ti-64: ~55 MPa√m)",
        "Griffith (1921) Phil. Trans. Roy. Soc. A 221:163; Irwin (1957) J. Appl. Mech. 24:361; "
        "Ashby & Jones (2012) Engineering Materials, Table values",
        "K_IC(elastic) = √(2Eγ_s)  [γ_s = 2 J/m²];  metals: K_IC(actual) ≈ 20–200 MPa√m"))

    VEC_val = vec(c)
    if VEC_val >= 7.5:
        sfe = _stacking_fault_energy(c)
        if sfe < 25:
            checks.append(PASS("SFE (FCC alloy)", sfe, "mJ/m²",
                f"SFE ≈ {sfe:.0f} mJ/m² < 25 — planar slip, low crack closure, excellent fatigue crack resistance",
                "Gallagher (1976) Fatigue Crack Propagation in Metals; Laird (1967) ASTM STP 415",
                "SFE ≈ SFE_Ni + Σᵢ (dSFE/dcᵢ)·cᵢ   [Gallagher 1976; Mn, Cr, N lower SFE]"))
        elif sfe < 70:
            checks.append(PASS("SFE (FCC alloy)", sfe, "mJ/m²",
                f"SFE ≈ {sfe:.0f} mJ/m² — moderate SFE; mixed planar/wavy slip",
                "Gallagher (1976); Laird (1967) ASTM STP 415",
                "SFE ≈ SFE_Ni + Σᵢ (dSFE/dcᵢ)·cᵢ"))
        else:
            checks.append(WARN("SFE (FCC alloy)", sfe, "mJ/m²",
                f"SFE ≈ {sfe:.0f} mJ/m² > 70 — wavy slip; fatigue crack propagation faster",
                "Gallagher (1976); Laird (1967) ASTM STP 415",
                "SFE ≈ SFE_Ni + Σᵢ (dSFE/dcᵢ)·cᵢ"))
    else:
        checks.append(INFO("SFE (BCC/HCP alloy)", VEC_val, "VEC",
            f"VEC = {VEC_val:.2f} — BCC/HCP structure; screw dislocation control dominates fatigue",
            "Laird (1967) ASTM STP 415; Ritchie (1979) Met. Trans. A 10:1557",
            "SFE model valid for FCC (VEC ≥ 7.5)"))

    fe_wt = mol_to_wt(c).get("Fe", 0) * 100
    mn_wt = mol_to_wt(c).get("Mn", 0) * 100
    if fe_wt >= 40 and mn_wt >= 10 and VEC_val >= 7.5:
        sfe_check = _stacking_fault_energy(c)
        if sfe_check < 18:
            checks.append(PASS("TRIP potential", sfe_check, "mJ/m²",
                f"SFE ≈ {sfe_check:.0f} mJ/m² < 18 — TRIP (austenite→martensite) possible; very high ductility×strength",
                "Olson & Cohen (1972) Met. Trans. 3:2613; Bouaziz et al. (2011) Curr. Op. Solid State Mater.",
                "TRIP: SFE < 18 mJ/m²;  TWIP: 18 < SFE < 35 mJ/m²"))
        elif sfe_check < 35:
            checks.append(PASS("TWIP potential", sfe_check, "mJ/m²",
                f"SFE ≈ {sfe_check:.0f} mJ/m² ∈ [18,35] — TWIP (deformation twinning) expected; extreme work-hardening",
                "Olson & Cohen (1972) Met. Trans. 3:2613; Bouaziz et al. (2011)",
                "TWIP: 18 < SFE < 35 mJ/m²"))
    else:
        checks.append(INFO("TWIP/TRIP potential", 0, "mJ/m²",
            "Not an Fe-Mn austenitic composition — TWIP/TRIP not applicable",
            "Olson & Cohen (1972) Met. Trans. 3:2613"))

    HV_mpa = wmean(c, "vickers")
    if HV_mpa is not None:
        UTS_proxy = HV_mpa * 3.4 / 9.807
        sigma_e = min(0.5 * UTS_proxy, 700)
        checks.append(INFO("Endurance limit σ_e", sigma_e, "MPa",
            f"σ_e ≈ {sigma_e:.0f} MPa  (0.5 × UTS_proxy from hardness; Shigley Eq.6-8)",
            "Shigley et al. (2011) Mechanical Engineering Design 9th ed. §6-2; Tabor (1951) Hardness of Metals",
            "σ_e ≈ 0.5 × UTS  (steel);  UTS ≈ HV[MPa] × 3.4 / 9.807"))
    else:
        checks.append(INFO("Endurance limit σ_e", None, "MPa",
            "Vickers hardness unavailable for one or more elements",
            "Shigley et al. (2011)"))

    return DomainResult(ID, NAME, checks)
