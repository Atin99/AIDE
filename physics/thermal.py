import sys, os, math
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from physics.base import *

ID = 13
NAME = "Thermal Properties"


def run(comp: dict, T_K: float = 298.0, **_) -> DomainResult:
    c = norm(comp)
    checks = []

    L0 = 2.44e-8
    rho_res = wmean(c, "resistivity")
    kappa_direct = wmean(c, "thermal_cond")

    if rho_res is not None and rho_res > 0:
        rho_ohm_m = rho_res * 1e-8
        kappa_wf = L0 * T_K / rho_ohm_m
        checks.append(INFO("κ (Wiedemann-Franz)", kappa_wf, "W/(m·K)",
            f"κ_e = L₀T/ρ = {kappa_wf:.1f} W/(m·K)  at {T_K:.0f} K  (electronic contribution)",
            "Wiedemann & Franz (1853) Ann. Phys. 165:497; Ho et al. (1972) JPCRD 1:279",
            "κ_e = L₀·T/ρ;  L₀ = 2.44×10⁻⁸ W·Ω/K²  (Sommerfeld)"))
    if kappa_direct is not None:
        checks.append(INFO("κ (measured, weighted)", kappa_direct, "W/(m·K)",
            f"κ̄ = {kappa_direct:.1f} W/(m·K)  (rule of mixtures from tabulated values)",
            "Ho et al. (1972) J. Phys. Chem. Ref. Data 1:279",
            "κ̄ = Σᵢ cᵢ·κᵢ  (Voigt; overestimates for alloys with disorder scattering)"))
    if kappa_direct is None and rho_res is None:
        checks.append(INFO("Thermal conductivity", None, "W/(m·K)",
            "Insufficient data for thermal conductivity estimation",
            "Ho et al. (1972) J. Phys. Chem. Ref. Data 1:279"))

    alpha = wmean(c, "thermal_exp")
    if alpha is not None:
        checks.append(INFO("CTE α", alpha, "μm/(m·K)",
            f"ᾱ = {alpha:.2f} μm/(m·K)  (Vegard rule of mixtures; note: non-Invar alloys 5–25 μm/m·K typical)",
            "White & Collocott (1984) JPCRD 13:1251; Vegard (1921) Z. Phys. 5:17",
            "ᾱ = Σᵢ cᵢ·αᵢ  [Fe: 11.8, Ni: 13.4, Cr: 4.9, Al: 23.1 μm/(m·K)]"))
    else:
        checks.append(INFO("CTE α", None, "μm/(m·K)",
            "Insufficient data for CTE estimation",
            "White & Collocott (1984) JPCRD 13:1251"))

    E_gpa = wmean(c, "E"); nu = wmean(c, "nu")
    kappa_use = kappa_direct or (kappa_wf if rho_res else None)
    if E_gpa and alpha and kappa_use:
        E_pa = E_gpa * 1e9
        alpha_1k = alpha * 1e-6
        sigma_f = E_pa * 0.002
        R_prime = kappa_use * sigma_f / (E_pa * alpha_1k)
        checks.append(INFO("Thermal shock R'", R_prime, "W/m",
            f"R' = κσ_f/(Eα) = {R_prime:.0f} W/m  "
            f"[Ceramics: ~1 W/m;  Metals: 10⁴–10⁷ W/m — metals far superior]",
            "Hasselman (1969) J. Am. Ceram. Soc. 52:600",
            "R' = κ·σ_f / (E·α)  [Hasselman figure-of-merit for thermal shock resistance]"))
    else:
        checks.append(INFO("Thermal shock R'", None, "W/m",
            "Insufficient data (need κ, E, α) for Hasselman R'",
            "Hasselman (1969) J. Am. Ceram. Soc. 52:600"))

    theta_D = wmean(c, "debye_T")
    if theta_D is not None:
        checks.append(INFO("Debye temperature θ_D", theta_D, "K",
            f"θ_D ≈ {theta_D:.0f} K  (rule of mixtures; affects phonon thermal conductivity and specific heat)",
            "Debye (1912) Ann. Phys. 344:789; Anderson (1963) J. Phys. Chem. Solids 24:909",
            "θ_D = Σᵢ cᵢ·θ_D,i"))

    return DomainResult(ID, NAME, checks)
