import sys, os, math
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from physics.base import *

ID = 16
NAME = "Superconductivity"

MU_STAR = 0.13


def run(comp: dict, **_) -> DomainResult:
    c = norm(comp)
    checks = []

    lam_vals = {s: get(s).lambda_ep for s in c if get(s).lambda_ep is not None}
    if not lam_vals:
        checks.append(INFO("λ (e-ph coupling)", None, "",
            "No electron-phonon coupling data available for this composition",
            "McMillan (1968) Phys. Rev. 167:331"))
        return DomainResult(ID, NAME, checks)

    lam = sum(c[s]*lam_vals[s] for s in lam_vals) / sum(c[s] for s in lam_vals)
    checks.append(INFO("λ (electron-phonon)", lam, "",
        f"λ̄ = {lam:.3f}  ({'strong coupling' if lam>1 else 'weak' if lam<0.3 else 'intermediate'})",
        "Allen & Dynes (1975) PRB 12:905; McMillan (1968) Phys. Rev. 167:331",
        "λ̄ = Σᵢ cᵢ·λᵢ  [tabulated values from tunnelling spectroscopy]"))

    theta_D = wmean(c, "debye_T")
    if theta_D is None:
        theta_D = 300.0
    omega_log = 0.85 * theta_D * 1.38e-23 / 1.055e-34
    omega_log_K = 0.85 * theta_D

    denom = lam - MU_STAR * (1 + 0.62 * lam)
    if denom > 0.05 and lam > MU_STAR + 0.1:
        Tc_mad = (omega_log_K / 1.2) * math.exp(-1.04 * (1 + lam) / denom)
        if lam > 1.5:
            f1 = (1 + (lam/2.46/(1+3.8*MU_STAR))**3)**(1/3)
            f2 = 1 + (lam-MU_STAR*(1+0.62*lam))/(MU_STAR*(1+0.62*lam)+lam**2)*0
            Tc_mad *= f1
        if Tc_mad > 10:
            checks.append(PASS("Tc (McMillan-Allen-Dynes)", Tc_mad, "K",
                f"Tc ≈ {Tc_mad:.1f} K — promising conventional superconductor",
                "McMillan (1968) Phys. Rev. 167:331; Allen & Dynes (1975) PRB 12:905",
                "Tc = (ω_log/1.2)·exp(−1.04(1+λ)/(λ−μ*(1+0.62λ)));  μ*=0.13"))
        elif Tc_mad > 1:
            checks.append(WARN("Tc (McMillan-Allen-Dynes)", Tc_mad, "K",
                f"Tc ≈ {Tc_mad:.1f} K — superconducting but cryogenic (< 10 K)",
                "McMillan (1968) Phys. Rev. 167:331",
                "Tc = (ω_log/1.2)·exp(−1.04(1+λ)/(λ−μ*(1+0.62λ)))"))
        else:
            checks.append(INFO("Tc (McMillan-Allen-Dynes)", Tc_mad, "K",
                f"Tc ≈ {Tc_mad:.2f} K — not a practical superconductor",
                "McMillan (1968) Phys. Rev. 167:331",
                "Tc < 1 K — no practical superconductivity"))
    else:
        checks.append(INFO("Tc (McMillan-Allen-Dynes)", 0, "K",
            f"λ = {lam:.3f} ≤ μ* = {MU_STAR} — no superconductivity expected",
            "McMillan (1968) Phys. Rev. 167:331",
            "Tc requires λ > μ* ≈ 0.13"))

    VEC_val = vec(c)
    if 4.5 <= VEC_val <= 5.5:
        checks.append(PASS("Matthias rule (VEC≈5)", VEC_val, "VEC",
            f"VEC = {VEC_val:.2f} ≈ 5 — Matthias peak (Nb, V compounds, A15 phases)",
            "Matthias et al. (1955) Phys. Rev. 97:74; Matthias (1957) Prog. Low Temp. Phys. 2:138",
            "Matthias rules: high Tc at VEC = 5 (Nb₃Sn, Nb₃Al) and VEC = 7 (Re, Os alloys)"))
    elif 6.5 <= VEC_val <= 7.5:
        checks.append(PASS("Matthias rule (VEC≈7)", VEC_val, "VEC",
            f"VEC = {VEC_val:.2f} ≈ 7 — Matthias secondary peak",
            "Matthias (1955) Phys. Rev. 97:74",
            "Matthias: VEC ≈ 5 or 7 → empirically higher Tc"))
    else:
        checks.append(INFO("Matthias rule", VEC_val, "VEC",
            f"VEC = {VEC_val:.2f} — not near Matthias peaks (VEC≈5 or ≈7)",
            "Matthias (1955) Phys. Rev. 97:74"))

    mg_at = c.get("Mg",0); b_at = c.get("B",0)
    if mg_at > 0.3 and b_at > 0.5:
        checks.append(PASS("MgB₂ candidate", b_at*100, "at% B",
            f"Mg={mg_at*100:.0f}%, B={b_at*100:.0f}% — MgB₂-type composition; Tc ≈ 39 K",
            "Nagamatsu et al. (2001) Nature 410:63",
            "MgB₂: Tc=39 K (highest Tc conventional superconductor at ambient pressure)"))

    return DomainResult(ID, NAME, checks)
