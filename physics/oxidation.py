import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from physics.base import *

ID = 5
NAME = "Oxidation"

PBR = {
    "Al": 1.28, "Cr": 2.07, "Fe": 1.77, "Ni": 1.65, "Co": 1.99,
    "Cu": 1.68, "Ti": 1.73, "Zr": 1.56, "Si": 2.27, "Mo": 3.40,
    "W":  3.40, "Ta": 2.47, "Nb": 2.68, "V":  3.25, "Mn": 1.79,
    "Mg": 0.81, "Ca": 0.64, "Hf": 1.62,
}

def run(comp: dict, T_K: float = 1073.0, **_) -> DomainResult:
    c = norm(comp)
    checks = []
    wt = mol_to_wt(c)

    pbr_val = sum(c[s] * PBR.get(s, 2.0) for s in c)
    if 1.0 <= pbr_val <= 2.5:
        checks.append(PASS("PBR (Pilling-Bedworth)", pbr_val, "",
            f"PBR = {pbr_val:.2f} ∈ [1.0, 2.5] — protective adherent oxide scale",
            "Pilling & Bedworth (1923) J. Inst. Met. 29:529; Birks et al. (2006)",
            "PBR = V_oxide / V_metal  (1.0–2.5 protective)"))
    elif pbr_val < 1.0:
        checks.append(FAIL("PBR", pbr_val, "",
            f"PBR = {pbr_val:.2f} < 1.0 — porous non-protective oxide (e.g. Mg)",
            "Pilling & Bedworth (1923)",
            "PBR < 1 → oxide volume less than metal → porous film"))
    else:
        checks.append(WARN("PBR", pbr_val, "",
            f"PBR = {pbr_val:.2f} > 2.5 — spalling risk (high compressive stress in oxide)",
            "Pilling & Bedworth (1923); Birks et al. (2006)",
            "PBR > 2.5 → excessive compressive stress → spalling"))

    al_wt = wt.get("Al", 0) * 100
    cr_wt = wt.get("Cr", 0) * 100
    si_wt = wt.get("Si", 0) * 100
    ti_wt = wt.get("Ti", 0) * 100
    if al_wt >= 4.0:
        checks.append(PASS("Selective oxidation", al_wt, "wt% Al",
            f"Al = {al_wt:.1f} wt% — Al₂O₃ will form selectively (most stable common oxide at T > 800 K)",
            "Ellingham (1944) J. Soc. Chem. Ind. 63:125; Richardson & Jeffes (1948) JISI 160:261",
            "Ellingham diagram: Al₂O₃ most stable at T > 800 K among common metals"))
    elif cr_wt >= 12.0:
        checks.append(PASS("Selective oxidation", cr_wt, "wt% Cr",
            f"Cr = {cr_wt:.1f} wt% — Cr₂O₃ protective scale (ΔG°₁₀₀₀K ≈ −450 kJ/mol O₂)",
            "Ellingham (1944); Richardson & Jeffes (1948) JISI",
            "ΔGf(Cr₂O₃) = −1128 kJ/mol at 298 K; selective above 12 wt% Cr"))
    elif si_wt >= 4.0:
        checks.append(WARN("Selective oxidation", si_wt, "wt% Si",
            f"Si = {si_wt:.1f} wt% — SiO₂ may form (PBR=2.27, risk of spalling)",
            "Ellingham (1944)",
            "PBR(SiO₂) = 2.27 → borderline protective"))
    else:
        checks.append(FAIL("Selective oxidation", cr_wt, "wt% Cr",
            "No strong selective oxide former (Al<4%, Cr<12%, Si<4%) — non-protective FeO/NiO expected",
            "Ellingham (1944); Sedriks (1996)",
            "Minimum Cr: 12 wt% for Cr₂O₃;  Al: 4 wt% for Al₂O₃"))

    Tm_mean = wmean(c, "Tm")
    if Tm_mean is not None:
        T_hom = T_K / Tm_mean
        if T_hom < 0.8:
            checks.append(PASS("T_op homologous", T_hom, "T/Tₘ",
                f"T/Tₘ = {T_hom:.3f} < 0.8 — no melting risk",
                "Frost & Ashby (1982) Deformation Mechanism Maps",
                "T_hom = T_op / T̄ₘ"))
        elif T_hom < 1.0:
            checks.append(WARN("T_op homologous", T_hom, "T/Tₘ",
                f"T/Tₘ = {T_hom:.3f} — approaching melting; rapid diffusion and oxidation",
                "Frost & Ashby (1982)",
                "T_hom = T_op / T̄ₘ"))
        else:
            checks.append(FAIL("T_op homologous", T_hom, "T/Tₘ",
                f"T_op > T̄ₘ — alloy would be molten at operating temperature",
                "Frost & Ashby (1982)",
                "T_hom = T_op / T̄ₘ"))

    return DomainResult(ID, NAME, checks)
