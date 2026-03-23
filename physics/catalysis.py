import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from physics.base import *

ID = 24
NAME = "Catalysis"


def run(comp: dict, **_) -> DomainResult:
    c = norm(comp)
    checks = []

    d_vals = {s: get(s).d_band_centre for s in c if get(s).d_band_centre is not None}
    if not d_vals:
        return DomainResult(ID, NAME,
            [INFO("Catalysis", None, "eV",
                  "No d-band data available for this composition",
                  "Hammer & Nørskov (1995) Surf. Sci. 343:211")],
            error="No d-band data")

    eps_d = sum(c[s]*d_vals[s] for s in d_vals) / sum(c[s] for s in d_vals)

    her_dist = abs(eps_d - (-1.9))
    if her_dist < 0.3:
        checks.append(PASS("HER activity (d-band volcano)", eps_d, "eV",
            f"ε_d = {eps_d:.2f} eV — near HER volcano peak (ΔG_H ≈ 0; Pt: −2.3, Ni: −1.3 eV)",
            "Nørskov et al. (2004) J. Electrochem. Soc. 151:J1; "
            "Hammer & Nørskov (1995) Surf. Sci. 343:211",
            "HER volcano: ε_d ≈ −1.8 to −2.0 eV → ΔG_H ≈ 0  [Sabatier optimum]"))
    elif her_dist < 0.8:
        checks.append(WARN("HER activity (d-band volcano)", eps_d, "eV",
            f"ε_d = {eps_d:.2f} eV — moderate HER activity (off-peak)",
            "Nørskov et al. (2004) J. Electrochem. Soc. 151:J1",
            "HER: ε_d ≈ −1.8 eV optimal; farther → weaker H binding or over-binding"))
    else:
        checks.append(INFO("HER activity (d-band volcano)", eps_d, "eV",
            f"ε_d = {eps_d:.2f} eV — far from HER volcano peak; low HER activity",
            "Nørskov et al. (2004) J. Electrochem. Soc. 151:J1",
            "HER optimal ε_d ≈ −1.9 eV (Pt reference)"))

    orr_dist = abs(eps_d - (-2.1))
    if orr_dist < 0.4:
        checks.append(PASS("ORR activity (d-band volcano)", eps_d, "eV",
            f"ε_d = {eps_d:.2f} eV — near ORR volcano peak (Pt: −2.3 eV, Pd: −1.8 eV)",
            "Nørskov et al. (2004) J. Electrochem. Soc. 151:J1",
            "ORR: 4e⁻ pathway; volcano peak ε_d ≈ −2.1 eV → optimal O*/OH* binding"))
    else:
        checks.append(INFO("ORR activity (d-band volcano)", eps_d, "eV",
            f"ε_d = {eps_d:.2f} eV — not optimal for ORR",
            "Nørskov et al. (2004)"))

    if -2.5 <= eps_d <= -1.5:
        checks.append(PASS("Sabatier principle", eps_d, "eV",
            f"ε_d = {eps_d:.2f} eV ∈ [−2.5, −1.5] — intermediate adsorption energy; Sabatier optimum",
            "Sabatier (1911) Ber. Dtsch. Chem. Ges. 44:1984; "
            "Brønsted (1928) Chem. Rev. 5:231; Evans & Polanyi (1938) Trans. Faraday Soc.",
            "Sabatier: not too weak (|ε_d| too large) nor too strong (|ε_d| too small) binding"))
    elif eps_d < -2.5:
        checks.append(INFO("Sabatier principle", eps_d, "eV",
            f"ε_d = {eps_d:.2f} eV < −2.5 — weak binding; reactions not activated "
            f"(noble metals Au/Ag region)",
            "Sabatier (1911)"))
    else:
        checks.append(WARN("Sabatier principle", eps_d, "eV",
            f"ε_d = {eps_d:.2f} eV > −1.5 — strong binding; intermediates may poison surface "
            f"(Cr, V, early TM region)",
            "Sabatier (1911)"))

    pgm = {"Pt","Pd","Rh","Ru","Ir","Os"}
    pgm_frac = sum(c.get(s,0) for s in pgm)
    if pgm_frac > 0.10:
        checks.append(PASS("PGM content", pgm_frac*100, "at%",
            f"PGM content = {pgm_frac*100:.1f}% — high intrinsic catalytic activity expected",
            "Trasatti (1972) J. Electroanal. Chem. 39:163; Hammer & Nørskov (1995)",
            "PGMs: Pt,Pd,Rh,Ru,Ir,Os → near volcano peaks for multiple reactions"))
    elif pgm_frac > 0:
        checks.append(INFO("PGM content", pgm_frac*100, "at%",
            f"PGM content = {pgm_frac*100:.1f}% — minor PGM addition",
            "Hammer & Nørskov (1995)"))

    return DomainResult(ID, NAME, checks)
