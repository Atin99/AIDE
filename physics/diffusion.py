import sys, os, math
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from physics.base import *

ID = 19
NAME = "Diffusion"


def run(comp: dict, T_K: float = 1273.0, **_) -> DomainResult:
    c = norm(comp)
    checks = []

    Tm = wmean(c, "Tm")
    if Tm is None:
        return DomainResult(ID, NAME,
            [INFO("Diffusion", None, "", "Tm data unavailable", "Sherby & Burke (1968)")],
            error="No Tm")

    Qsd = 17.0 * R * Tm / 1000
    checks.append(INFO("Qsd (Sherby-Burke)", Qsd, "kJ/mol",
        f"Qsd ≈ 17R·T̄ₘ = {Qsd:.0f} kJ/mol  "
        f"(benchmarks: Fe 239 kJ/mol, Ni 270 kJ/mol, Al 142 kJ/mol — NIST SRD 34)",
        "Sherby & Burke (1968) Prog. Mater. Sci. 13:325",
        "Qsd ≈ 17·R·Tₘ  [Sherby-Burke empirical rule]"))

    D0 = 5e-5
    D_T = D0 * math.exp(-Qsd * 1000 / (R * T_K))
    checks.append(INFO("D_self at T", D_T, "m²/s",
        f"D_self ≈ {D_T:.2e} m²/s  at {T_K:.0f} K  "
        f"(Fe at 1000°C ≈ 5×10⁻¹⁵ m²/s measured — Gale & Totemeier 2004)",
        "Crank (1975) Mathematics of Diffusion 2nd ed.; Gale & Totemeier (2004) Smithells 8th ed.",
        "D = D₀·exp(−Qsd/RT);  D₀ ≈ 5×10⁻⁵ m²/s [metals]"))

    T_hom = T_K / Tm
    checks.append(INFO("Homologous T/Tₘ", T_hom, "",
        f"T/Tₘ = {T_hom:.3f}  at {T_K:.0f} K  "
        f"(grain boundary diffusion dominates < 0.5Tₘ; bulk diffusion > 0.5Tₘ)",
        "Frost & Ashby (1982) Deformation Mechanism Maps; Gale & Totemeier (2004)",
        "T_hom = T/Tₘ;  < 0.3: negligible; 0.3–0.5: power-law creep; > 0.5: diffusion creep"))

    T_hom_ann = 0.70 * Tm
    checks.append(INFO("T_homogenise (70%Tₘ)", T_hom_ann, "K",
        f"Homogenisation anneal at {T_hom_ann:.0f} K ({T_hom_ann-273:.0f}°C) for D significant",
        "Crank (1975) Mathematics of Diffusion; Flemings (1974) Solidification Processing",
        "T_hom ≈ 0.70·Tₘ for D ≫ 1; time ≈ L²/D where L = segregation length scale"))

    d_val = delta_size(c) / 100.0
    if d_val > 0.05 and len(c) >= 2:
        checks.append(WARN("Kirkendall effect", d_val * 100, "%",
            f"δ = {d_val*100:.1f}% — significant size mismatch → unequal diffusivities → "
            f"Kirkendall voids possible during interdiffusion",
            "Kirkendall & Smigelskas (1947) Trans. AIME 171:130; Tu & Gösele (2005) Appl. Phys. Lett.",
            "Kirkendall: |D_A − D_B|/D_avg large → net vacancy flux → void nucleation"))
    else:
        checks.append(PASS("Kirkendall effect", d_val * 100, "%",
            f"δ = {d_val*100:.1f}% — similar atomic sizes → low Kirkendall void risk",
            "Kirkendall & Smigelskas (1947) Trans. AIME 171:130",
            "Kirkendall voids: δ > 5% + strongly asymmetric interdiffusion → risk"))

    return DomainResult(ID, NAME, checks)
