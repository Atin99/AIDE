import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from physics.base import *

ID = 3
NAME = "Mechanical"

def run(comp: dict, **_) -> DomainResult:
    c = norm(comp)
    checks = []

    bg = pugh_ratio(c)
    if bg is None:
        checks.append(INFO("Pugh B/G", None, "",
            "Insufficient modulus data",
            "Pugh (1954) Philos. Mag. 45:823"))
    elif bg >= 1.75:
        checks.append(PASS("Pugh B/G", bg, "",
            f"B/G = {bg:.2f} ≥ 1.75 — ductile regime",
            "Pugh (1954) Philos. Mag. 45:823; Niu et al. (2012)",
            "B/G: ductile ≥ 1.75, brittle < 1.75"))
    else:
        checks.append(WARN("Pugh B/G", bg, "",
            f"B/G = {bg:.2f} < 1.75 — brittle tendency",
            "Pugh (1954) Philos. Mag. 45:823",
            "B/G: ductile ≥ 1.75, brittle < 1.75"))

    nu = wmean(c, "nu")
    if nu is not None:
        if nu >= 0.26:
            checks.append(PASS("Poisson ratio ν", nu, "",
                f"ν = {nu:.3f} ≥ 0.26 — ductile (metallic bonding)",
                "Greaves et al. (2011) Nature Mater. 10:823",
                "ν ≥ 0.26 metallic; ν < 0.26 brittle tendency"))
        else:
            checks.append(WARN("Poisson ratio ν", nu, "",
                f"ν = {nu:.3f} < 0.26 — brittle tendency",
                "Greaves et al. (2011) Nature Mater. 10:823",
                "ν ≥ 0.26 metallic"))
    else:
        checks.append(INFO("Poisson ratio ν", None, "", "Insufficient data",
            "Greaves et al. (2011)"))

    cp = cauchy_pressure(c)
    if cp is not None:
        if cp > 0:
            checks.append(PASS("Cauchy pressure C₁₂−C₄₄", cp, "GPa",
                f"C₁₂−C₄₄ ≈ {cp:.1f} GPa > 0 — metallic bonding character",
                "Pettifor (1992) Mater. Sci. Tech. 8:345",
                "C₁₂−C₄₄ ≈ B − 8G/3  (isotropic approx.)"))
        else:
            checks.append(WARN("Cauchy pressure C₁₂−C₄₄", cp, "GPa",
                f"C₁₂−C₄₄ ≈ {cp:.1f} GPa < 0 — covalent/ionic bonding character",
                "Pettifor (1992) Mater. Sci. Tech. 8:345",
                "C₁₂−C₄₄ ≈ B − 8G/3"))
    else:
        checks.append(INFO("Cauchy pressure", None, "GPa",
            "Insufficient B or G data", "Pettifor (1992)"))

    E = wmean(c, "E")
    if E is not None:
        checks.append(INFO("Young's modulus E", E, "GPa",
            f"E = {E:.0f} GPa (rule of mixtures)",
            "Voigt (1889) Ann. Phys. 38:573; Reuss (1929) ZAMM",
            "Ē = Σᵢ cᵢ Eᵢ  (Voigt upper bound)"))

    return DomainResult(ID, NAME, checks)
