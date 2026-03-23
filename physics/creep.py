import sys, os, math
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from physics.base import *

ID = 8
NAME = "Creep"

def run(comp: dict, T_K: float = 873.0, **_) -> DomainResult:
    c = norm(comp)
    checks = []

    Tm = wmean(c, "Tm")
    if Tm is None:
        return DomainResult(ID, NAME,
            [INFO("Creep", None, "", "Melting point data unavailable", "Frost & Ashby (1982)")],
            error="No Tm data")

    T_hom = T_K / Tm

    if T_hom < 0.3:
        checks.append(PASS("Homologous T/Tₘ", T_hom, "T/Tₘ",
            f"T/Tₘ = {T_hom:.3f} < 0.3 — diffusion creep negligible",
            "Frost & Ashby (1982) Deformation Mechanism Maps, Pergamon",
            "T_hom = T_op / T̄ₘ  (weighted mean melting point)"))
    elif T_hom < 0.5:
        checks.append(PASS("Homologous T/Tₘ", T_hom, "T/Tₘ",
            f"T/Tₘ = {T_hom:.3f} — power-law creep regime, design with creep data",
            "Frost & Ashby (1982)",
            "T_hom = T_op / T̄ₘ"))
    elif T_hom < 0.7:
        checks.append(WARN("Homologous T/Tₘ", T_hom, "T/Tₘ",
            f"T/Tₘ = {T_hom:.3f} — high creep rate expected; grain boundary sliding active",
            "Frost & Ashby (1982)",
            "T_hom = T_op / T̄ₘ"))
    else:
        checks.append(FAIL("Homologous T/Tₘ", T_hom, "T/Tₘ",
            f"T/Tₘ = {T_hom:.3f} > 0.7 — near-melting; unacceptable creep rate",
            "Frost & Ashby (1982)",
            "T_hom = T_op / T̄ₘ"))

    C_lm = 20.0
    t_hr = 1000.0
    LMP = T_K * (C_lm + math.log10(t_hr)) * 1e-3
    checks.append(INFO("Larson-Miller P (1000 h)", LMP, "kK",
        f"LMP = T × (C + log₁₀t) = {LMP:.2f} kK  (C=20, t=1000h)",
        "Larson & Miller (1952) Trans. ASME 74:765",
        "LMP = T[K] × (20 + log₁₀ t[h]) × 10⁻³"))

    Qsd = 17.0 * R * Tm / 1000
    checks.append(INFO("Self-diffusion Qsd", Qsd, "kJ/mol",
        f"Qsd ≈ 17R·Tₘ = {Qsd:.0f} kJ/mol",
        "Sherby & Burke (1968) Prog. Mater. Sci. 13:325",
        "Qsd ≈ 17RT̄ₘ  (Sherby-Burke rule)"))

    wt = mol_to_wt(c)
    ni_wt = wt.get("Ni", 0) * 100
    al_wt = wt.get("Al", 0) * 100
    ti_wt = wt.get("Ti", 0) * 100
    if ni_wt >= 40 and (al_wt + ti_wt) >= 3:
        checks.append(PASS("γ'-forming potential", al_wt + ti_wt, "wt% Al+Ti",
            f"Ni = {ni_wt:.0f} wt%, Al+Ti = {al_wt+ti_wt:.1f} wt% — Ni₃(Al,Ti) γ' precipitation strengthening expected",
            "Sims et al. (1987) Superalloys II, Wiley",
            "γ': Ni₃(Al,Ti), requires Ni≥40% and Al+Ti≥3 wt%"))
    else:
        checks.append(INFO("γ'-forming potential", al_wt + ti_wt, "wt% Al+Ti",
            f"No γ'-precipitation expected (Ni={ni_wt:.0f}%, Al+Ti={al_wt+ti_wt:.1f}%)",
            "Sims et al. (1987) Superalloys II"))

    return DomainResult(ID, NAME, checks)
