import sys, os, math
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from physics.base import *

ID = 15
NAME = "Electronic Structure"


def run(comp: dict, T_K: float = 298.0, **_) -> DomainResult:
    c = norm(comp)
    checks = []

    d_vals = {s: get(s).d_band_centre for s in c if get(s).d_band_centre is not None}
    if len(d_vals) >= 2:
        eps_d = sum(c[s] * d_vals[s] for s in d_vals) / sum(c[s] for s in d_vals)
        checks.append(INFO("d-band centre ε_d", eps_d, "eV",
            f"ε_d = {eps_d:.2f} eV rel. to E_F  "
            f"(ε_d closer to 0 → stronger adsorbate binding; optimal HER/ORR ~ −1.8 to −2.0 eV)",
            "Hammer & Nørskov (1995) Surf. Sci. 343:211; Nørskov et al. (2004) J. Electrochem. Soc. 151:J1",
            "ε_d = Σᵢ cᵢ·ε_d,i  [Hammer & Nørskov d-band model]"))
    else:
        checks.append(INFO("d-band centre ε_d", None, "eV",
            "Insufficient d-band data for this composition",
            "Hammer & Nørskov (1995) Surf. Sci. 343:211"))

    rho_pure = wmean(c, "resistivity")
    if rho_pure is not None:
        dchi_sq = 0.0
        chi_bar = sum(c[s]*(get(s).electronegativity or 2.0) for s in c)
        for s in c:
            chi_s = get(s).electronegativity or chi_bar
            dchi_sq += c[s] * (chi_s - chi_bar)**2
        nordheim_term = 100.0 * dchi_sq * sum(c[s]*(1-c[s]) for s in c)
        rho_alloy = rho_pure + nordheim_term
        checks.append(INFO("ρ_alloy (Nordheim)", rho_alloy, "μΩ·cm",
            f"ρ ≈ {rho_alloy:.1f} μΩ·cm  (pure-metal: {rho_pure:.1f} + Nordheim scatter: {nordheim_term:.1f})",
            "Nordheim (1931) Ann. Phys. 401:607; Rossiter (1987) Electrical Resistivity of Metals",
            "ρ_alloy = Σcᵢρᵢ + C·Δχ²·Σcᵢ(1−cᵢ)  [Nordheim's rule]"))

        L0 = 2.44e-8
        rho_ohm = rho_alloy * 1e-8
        kappa_e = L0 * T_K / rho_ohm
        checks.append(INFO("κ_e (Wiedemann-Franz)", kappa_e, "W/(m·K)",
            f"κ_e = L₀T/ρ = {kappa_e:.1f} W/(m·K)  at {T_K:.0f} K",
            "Wiedemann & Franz (1853) Ann. Phys. 165:497; Sommerfeld (1927) Naturwiss. 15:825",
            "κ_e = L₀·T/ρ;  L₀ = 2.44×10⁻⁸ W·Ω/K²  (Sommerfeld value)"))
    else:
        checks.append(INFO("Resistivity / κ_e", None, "μΩ·cm",
            "Resistivity data unavailable for some elements",
            "Matula (1979) JPCRD 8:1147"))

    wf_vals = {s: get(s).work_function for s in c if get(s).work_function is not None}
    if len(wf_vals) >= 2:
        wf_mean = sum(c[s]*wf_vals[s] for s in wf_vals) / sum(c[s] for s in wf_vals)
        checks.append(INFO("Work function Φ̄", wf_mean, "eV",
            f"Φ̄ = {wf_mean:.2f} eV  (relevant for contact potential, electron emission, surface chemistry)",
            "Michaelson (1977) J. Appl. Phys. 48:4729",
            "Φ̄ = Σᵢ cᵢ·Φᵢ  [Michaelson tabulated values]"))
    else:
        checks.append(INFO("Work function Φ̄", None, "eV",
            "Insufficient work function data", "Michaelson (1977) J. Appl. Phys. 48:4729"))

    VEC_val = vec(c)
    if VEC_val > 0:
        checks.append(PASS("Metallic character", VEC_val, "VEC",
            f"VEC = {VEC_val:.2f} — metallic alloy (electrons in partially filled d/sp bands)",
            "Callister & Rethwisch (2018) Materials Science 10th ed.",
            "VEC = Σᵢ cᵢ·VECᵢ > 0 → metallic"))

    return DomainResult(ID, NAME, checks)
