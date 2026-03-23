import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from physics.base import *

ID = 20
NAME = "Surface Energy"


def run(comp: dict, **_) -> DomainResult:
    c = norm(comp)
    checks = []

    gam_vals = {s: get(s).surface_energy for s in c if get(s).surface_energy is not None}
    if len(gam_vals) >= 2:
        gamma_mean = sum(c[s]*gam_vals[s] for s in gam_vals) / sum(c[s] for s in gam_vals)
        checks.append(INFO("Surface energy γ", gamma_mean, "J/m²",
            f"γ̄ = {gamma_mean:.2f} J/m²  (Voigt mixing; Fe:2.41, Ni:2.08, Al:1.16, Ti:2.04 J/m²)",
            "Tyson & Miller (1977) Surf. Sci. 62:267; Skapski (1956) Acta Metall. 4:576",
            "γ̄ = Σᵢ cᵢ·γᵢ  [Tyson & Miller experimental values; broken-bond model underpins]"))

        W_adh = 2 * gamma_mean
        checks.append(INFO("Work of adhesion W_adh", W_adh, "J/m²",
            f"W_adh = 2γ = {W_adh:.2f} J/m²  (self-adhesion; actual W_AB = γ_A + γ_B − γ_AB)",
            "Dupré (1869) Théorie Mécanique de la Chaleur; Johnson et al. (1971) Proc. Roy. Soc. A",
            "W_adh = 2γ for self-adhesion;  W_AB = γ_A + γ_B − γ_AB for bimaterial contact"))

        sorted_by_gam = sorted(gam_vals.items(), key=lambda x: x[1])
        seg_elem, seg_gam = sorted_by_gam[0]
        checks.append(INFO("Surface segregation", seg_gam, "J/m²",
            f"Surface-enriched element: {seg_elem} (γ={seg_gam:.2f} J/m² — lowest in alloy) "
            f"→ surface composition ≠ bulk; affects oxidation, catalysis, adhesion",
            "Gibbs (1876) Trans. Conn. Acad.; Hondros & Seah (1977) Met. Trans. A 8:1363; "
            "Wynblatt & Ku (1977) Surf. Sci. 65:511",
            "Gibbs: lower-γ component segregates to free surface → surface enrichment"))

        if gamma_mean > 1.5:
            checks.append(PASS("Wettability (metallic)", gamma_mean, "J/m²",
                f"γ = {gamma_mean:.2f} J/m² > 1.5 — high-energy metallic surface; wetted by water, adhesives",
                "Adamson & Gast (1997) Physical Chemistry of Surfaces 6th ed.",
                "γ_liquid_metal ≫ γ_liquid;  metallic surfaces are high-energy → excellent wettability"))
    else:
        checks.append(INFO("Surface energy", None, "J/m²",
            "Surface energy data unavailable for one or more elements",
            "Tyson & Miller (1977) Surf. Sci. 62:267"))

    return DomainResult(ID, NAME, checks)
