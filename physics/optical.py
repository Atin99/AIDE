import sys, os, math
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from physics.base import *

ID = 28
NAME = "Optical Properties"


def run(comp: dict, T_K: float = 298.0, **_) -> DomainResult:
    c = norm(comp)
    checks = []

    rho_res = wmean(c, "resistivity")

    rho_alloy = density_rule_of_mixtures(c)
    if rho_alloy:
        M_avg = wmean(c, "atomic_mass") or 50
        val_avg = vec(c)
        n_e = val_avg * 6.022e23 * (rho_alloy * 1e6) / M_avg
        eps0 = 8.854e-12; me = 9.109e-31; e_ch = 1.602e-19; hbar = 1.055e-34
        omega_p = math.sqrt(n_e * e_ch**2 / (eps0 * me))
        E_p = hbar * omega_p / e_ch
        checks.append(INFO("Plasma energy ħωp (Drude)", E_p, "eV",
            f"E_p = ħωp = {E_p:.1f} eV  "
            f"(Al: 15.8 eV, Cu: 10.8 eV, Ag: 3.8 eV experimental — Ashcroft & Mermin §1)",
            "Drude (1900) Ann. Phys. 1:566; Ashcroft & Mermin (1976) Solid State Physics §1",
            "ωp = √(ne²/ε₀mₑ);  Ep = ħωp  [free-electron Drude; overestimates for d-metals]"))

    if rho_res and rho_res > 0:
        rho_ohm = rho_res * 1e-8
        sigma0 = 1.0 / rho_ohm
        omega_vis = 3.0 * 1.602e-19 / 1.055e-34
        eps_real = 1 - sigma0 / (8.854e-12 * omega_vis**2 * rho_ohm) if rho_ohm else 1
        denom = sigma0
        if denom > 0:
            R_approx = max(0, min(1, 1.0 - 2.0 * math.sqrt(8.854e-12 * omega_vis / denom)))
        else:
            R_approx = 0.95
        checks.append(INFO("Reflectivity R (Drude, visible)", R_approx*100, "%",
            f"R ≈ {R_approx*100:.0f}% at 3 eV  "
            f"(Ag: 99%, Cu: 97%, Fe: 70%, Pt: 70% — Ziman 1960)",
            "Drude (1900); Ziman (1960) Electrons and Phonons §9",
            "R ≈ 1 − 2(ε₀ω/σ₀)^0.5  [Drude low-freq limit; interband ignored]"))

    if rho_res:
        mu0 = 4*math.pi*1e-7
        f_rf = 1e6
        omega_rf = 2*math.pi*f_rf
        rho_ohm2 = rho_res * 1e-8
        delta_skin = math.sqrt(2*rho_ohm2 / (omega_rf*mu0)) * 1e6
        checks.append(INFO("Skin depth δ at 1 MHz", delta_skin, "μm",
            f"δ = √(2ρ/ωμ₀) = {delta_skin:.1f} μm  "
            f"(Cu: 66 μm, Fe: 183 μm at 1 MHz — Jackson 1975)",
            "Jackson (1975) Classical Electrodynamics §5.18; Griffiths (2017) Intro. Electrodynamics",
            "δ = √(2ρ/(ωμ₀));  governs RF shielding, induction heating, eddy-current NDT"))

    if c.get("Au",0) > 0.5:
        checks.append(INFO("Optical colour", 2.4, "eV (interband)",
            "GOLD colour: relativistic 5d→6s transition at ~2.4 eV absorbs violet/blue "
            "→ reflects yellow/orange. Non-relativistic Au would be silver-coloured.",
            "Pyykko (1988) Chem. Rev. 88:563; Christensen & Seraphin (1971) PRB 4:3321",
            "Au: relativistic 5d-6s gap 2.4 eV → absorbs blue/violet → gold appearance"))
    elif c.get("Cu",0) > 0.5:
        checks.append(INFO("Optical colour", 2.1, "eV (interband)",
            "COPPER colour: 3d→4s interband transition at ~2.1 eV absorbs blue/green → reflects red-orange",
            "Ziman (1960) Electrons and Phonons §9; Ashcroft & Mermin (1976) §1",
            "Cu: 3d→4s transition ~2.1 eV → red-orange appearance"))
    else:
        checks.append(INFO("Optical colour", 0, "",
            "Silvery/grey metallic appearance (flat reflectivity in visible; no selective interband absorption)",
            "Ashcroft & Mermin (1976) Solid State Physics §1"))

    return DomainResult(ID, NAME, checks)
