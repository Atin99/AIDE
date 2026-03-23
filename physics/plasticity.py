import sys, os, math
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from physics.base import *

ID = 18
NAME = "Plasticity"


def run(comp: dict, **_) -> DomainResult:
    c = norm(comp)
    checks = []
    VEC_val = vec(c)

    if VEC_val >= 8.0:
        n_slip = 12; struct = "FCC {111}<110>"
    elif VEC_val >= 6.0:
        n_slip = 48; struct = "BCC {110,112,123}<111>"
    else:
        n_slip = 3;  struct = "HCP {0001}<11̄20> basal only"

    if n_slip >= 5:
        checks.append(PASS("Von Mises criterion (≥5 indep. systems)", n_slip, "systems",
            f"{n_slip} slip systems ({struct}) — satisfies Von Mises ≥5 for polycrystal ductility",
            "Von Mises (1928) Z. Angew. Math. Mech. 8:161; Taylor (1938) J. Inst. Met. 62:307",
            "Von Mises: ≥5 independent slip systems required for polycrystalline ductility"))
    else:
        checks.append(WARN("Von Mises criterion", n_slip, "systems",
            f"Only {n_slip} basal slip systems (HCP) — limited ductility without secondary slip activation",
            "Von Mises (1928); Kocks & Westlake (1967) Trans. Met. Soc. AIME 239:1107",
            "HCP: only 3 basal systems → limited ductility; prismatic/pyramidal needed"))

    G_val = wmean(c, "G") or 80.0
    nu_val = wmean(c, "nu") or 0.30
    b_burg = 2.5e-10
    w_pn   = b_burg
    sigma_PN = (2*G_val*1e9/(1-nu_val)) * math.exp(-2*math.pi*w_pn/b_burg) / 1e6
    checks.append(INFO("Peierls-Nabarro stress", sigma_PN, "MPa",
        f"σ_PN = 2G/(1−ν)·exp(−2πw/b) = {sigma_PN:.0f} MPa  "
        f"(FCC: very low; BCC: higher due to narrow cores → DBTT)",
        "Peierls (1940) Proc. Phys. Soc. 52:34; Nabarro (1947) Proc. Phys. Soc. 59:256",
        "σ_PN = 2G/(1−ν)·exp(−2πw/b);  w ≈ b for metals;  BCC screw cores narrow → higher σ_PN"))

    d_val = delta_size(c) / 100.0
    c_minor = [xi for xi in c.values() if xi < 0.5]
    if c_minor:
        c_eff = sum(c_minor) / len(c_minor)
        delta_sigma_ss = G_val * 1e3 * c_eff**0.5 * d_val
        checks.append(INFO("Solid solution Δσ_ss (Fleischer)", delta_sigma_ss, "MPa",
            f"Δσ_ss ≈ G·c_eff^0.5·δ/100 = {delta_sigma_ss:.0f} MPa  (contribution from SS hardening)",
            "Fleischer (1963) Acta Metall. 11:203; Labusch (1970) Phys. Stat. Sol. 41:659",
            "Δσ_ss ≈ G·c^0.5·ε_s  [Fleischer model; ε_s ≈ δ for size mismatch]"))

    wt = mol_to_wt(c)
    fe_wt = wt.get("Fe",0)*100; mn_wt = wt.get("Mn",0)*100
    if fe_wt >= 40 and mn_wt >= 10 and VEC_val >= 7.5:
        SFE_BASE = 78.0
        SFE_COEFF = {"Mn":-60,"Ni":10,"Cr":-25,"N":-150,"C":-100,"Co":-30,"Si":30,"Al":20}
        sfe = max(0, SFE_BASE + sum(SFE_COEFF.get(s,0)*wt.get(s,0)*100 for s in SFE_COEFF))
        if sfe < 18:
            checks.append(PASS("TRIP potential", sfe, "mJ/m²",
                f"SFE ≈ {sfe:.0f} mJ/m² < 18 → martensitic transformation under stress → extreme ductility×strength",
                "Olson & Cohen (1972) Met. Trans. 3:2613; Bouaziz et al. (2011) Curr. Op. Solid State",
                "TRIP: SFE < 18 mJ/m² (γ → ε → α' martensite); TWIP: 18–35 mJ/m² (twinning)"))
        elif sfe < 35:
            checks.append(PASS("TWIP potential", sfe, "mJ/m²",
                f"SFE ≈ {sfe:.0f} mJ/m² ∈ [18,35] → deformation twinning → very high work-hardening rate",
                "Olson & Cohen (1972) Met. Trans. 3:2613",
                "TWIP: 18 < SFE < 35 mJ/m² → twinning-induced plasticity"))
        else:
            checks.append(INFO("TWIP/TRIP", sfe, "mJ/m²",
                f"SFE ≈ {sfe:.0f} mJ/m² > 35 — slip-dominated deformation",
                "Olson & Cohen (1972)"))
    else:
        checks.append(INFO("TWIP/TRIP", 0, "",
            "TWIP/TRIP applies to Fe-Mn austenitic steels (Fe≥40%, Mn≥10%, FCC)",
            "Olson & Cohen (1972) Met. Trans. 3:2613"))

    Tm_val = wmean(c, "Tm") or 1500
    checks.append(INFO("Superplasticity window", Tm_val*0.5, "K",
        f"Superplastic regime: T > {Tm_val*0.5:.0f} K ({Tm_val*0.5-273:.0f}°C) with grain size < 10 μm",
        "Langdon (1982) Met. Sci. 16:175; Edington et al. (1976) Prog. Mater. Sci. 21:61",
        "Superplasticity: T > 0.5Tₘ, d < 10 μm, έ = 10⁻³–10⁻⁴ s⁻¹"))

    return DomainResult(ID, NAME, checks)
