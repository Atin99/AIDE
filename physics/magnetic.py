import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from physics.base import *

ID = 12
NAME = "Magnetism"


def run(comp: dict, **_) -> DomainResult:
    c = norm(comp)
    checks = []

    mu_bar = sum(c[s] * (get(s).mag_moment or 0.0) for s in c)
    checks.append(INFO("Saturation μ̄", mu_bar, "μ_B/atom",
        f"μ̄ = {mu_bar:.3f} μ_B/atom  (linear mixing; does not account for exchange coupling)",
        "Bethe (1933) Z. Phys. 71:205; Weiss (1907) J. Phys. Théor. Appl.",
        "μ̄ = Σᵢ cᵢ·μᵢ  (Bohr magneton; Fe: 2.22, Co: 1.72, Ni: 0.60, Cr: -0.5 antiferro)"))

    Tc_est = sum(c[s] * (get(s).curie_T or 0.0) for s in c)
    if Tc_est > 0:
        checks.append(INFO("Tc estimate", Tc_est, "K",
            f"Tc ≈ {Tc_est:.0f} K  ({Tc_est - 273:.0f} °C)  [linear mixing — significant error expected for alloys]",
            "Weiss (1907); Johnston et al. (2011) Prog. Solid State Chem. 39:201",
            "Tc = Σᵢ cᵢ·Tc,i  (linear; actual Tc requires ab-initio or measured data)"))

    ferro_frac = (c.get("Fe", 0) + c.get("Co", 0) + c.get("Ni", 0) +
                  c.get("Gd", 0) * 2)
    if ferro_frac > 0.30:
        checks.append(WARN("Ferromagnetism (Stoner)", ferro_frac * 100, "at%",
            f"Ferro-formers (Fe+Co+Ni+Gd) = {ferro_frac*100:.1f} at% — alloy likely ferromagnetic",
            "Stoner (1938) Proc. Roy. Soc. A 165:372; Jiles (1991) Introduction to Magnetism",
            "Stoner criterion: I·N(E_F) > 1 → ferromagnetic; proxy: c(Fe+Co+Ni+Gd) > 30%"))
    elif ferro_frac > 0.05:
        checks.append(INFO("Ferromagnetism (Stoner)", ferro_frac * 100, "at%",
            f"Ferro-formers = {ferro_frac*100:.1f} at% — weak ferromagnetism or paramagnetism expected",
            "Stoner (1938); Jiles (1991)"))
    else:
        checks.append(PASS("Ferromagnetism (Stoner)", ferro_frac * 100, "at%",
            f"Ferro-formers = {ferro_frac*100:.1f} at% — non-ferromagnetic (paramagnetic or diamagnetic)",
            "Stoner (1938) Proc. Roy. Soc. A 165:372",
            "Stoner criterion proxy: c(Fe+Co+Ni+Gd) < 5%"))

    fe_at = c.get("Fe", 0) * 100; ni_at = c.get("Ni", 0) * 100
    if 60 <= fe_at <= 75 and 25 <= ni_at <= 40:
        checks.append(PASS("Invar effect", ni_at, "at% Ni",
            f"Fe-{ni_at:.0f}at%Ni — Invar composition; CTE ≈ 1–2 μm/(m·K) near RT",
            "Guillaume (1897) C. R. Acad. Sci. Paris 125:235; Wassermann (1990) J. Magn. Magn. Mater. 84:115",
            "Invar: Fe₆₅Ni₃₅ → ΔV/ΔT near-zero due to magnetovolume effect"))
    else:
        checks.append(INFO("Invar effect", ni_at, "at% Ni",
            f"Not an Invar composition (Fe={fe_at:.0f}%, Ni={ni_at:.0f}%); Invar requires Fe 65–75% + Ni 25–35%",
            "Guillaume (1897); Wassermann (1990)"))

    return DomainResult(ID, NAME, checks)
