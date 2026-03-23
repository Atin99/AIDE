import sys, os, math
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from physics.base import *

ID = 29
NAME = "Hydrogen Storage"

HYDRIDE_CAPACITY_WT = {
    "Mg": 7.60,  "Li": 12.7, "Na": 4.2, "Ca": 4.8,
    "Ti": 4.0,   "Zr": 2.2,  "V":  2.1, "Nb": 1.9,
    "La": 1.37,  "Ce": 1.4,  "Ni": 1.6, "Fe": 1.9,
    "Pd": 0.56,  "Mn": 1.8,  "Cu": 0.0,
}


def run(comp: dict, **_) -> DomainResult:
    c = norm(comp)
    checks = []

    H_cap_wt = sum(c[s] * HYDRIDE_CAPACITY_WT.get(s, 0.5)
                   for s in c if s in HYDRIDE_CAPACITY_WT)
    total_known = sum(c[s] for s in c if s in HYDRIDE_CAPACITY_WT)
    H_cap_eff = H_cap_wt / total_known if total_known > 0.5 else H_cap_wt

    if H_cap_eff >= 5.5:
        checks.append(PASS("Gravimetric H capacity", H_cap_eff, "wt% H",
            f"H capacity ≈ {H_cap_eff:.2f} wt% — meets or exceeds DOE 2025 target (5.5 wt%)",
            "Schlapbach & Züttel (2001) Nature 414:353; "
            "DOE Hydrogen Storage Technical Targets (2023)",
            "H_cap = Σcᵢ·(cap_i); DOE target: 5.5 wt% system capacity"))
    elif H_cap_eff >= 2.0:
        checks.append(WARN("Gravimetric H capacity", H_cap_eff, "wt% H",
            f"H capacity ≈ {H_cap_eff:.2f} wt% — below DOE target; suitable for stationary storage",
            "Schlapbach & Züttel (2001) Nature 414:353",
            "H_cap = Σcᵢ·cap_i;  DOE target 5.5 wt% (vehicle), 2 wt% (stationary)"))
    else:
        checks.append(INFO("Gravimetric H capacity", H_cap_eff, "wt% H",
            f"H capacity ≈ {H_cap_eff:.2f} wt% — low; not a hydrogen storage alloy",
            "Schlapbach & Züttel (2001) Nature 414:353",
            "H_cap < 2 wt% — not suitable for hydrogen storage applications"))

    la_ce = c.get("La",0) + c.get("Ce",0) + c.get("Pr",0) + c.get("Nd",0)
    ni_at = c.get("Ni",0)
    if la_ce > 0.12 and ni_at > 0.50:
        ratio_AB5 = ni_at / la_ce if la_ce > 0 else 0
        if 4.5 < ratio_AB5 < 5.5:
            checks.append(PASS("AB₅ Laves (LaNi₅-type)", la_ce*100, "at% La/Ce",
                f"La/Ce = {la_ce*100:.1f}%, Ni = {ni_at*100:.1f}% → LaNi₅-type AB₅ Laves; "
                f"capacity ≈ 1.4 wt% H; P_eq ≈ 2 bar at 25°C",
                "van Mal et al. (1974) J. Less-Common Met. 35:65; "
                "Sandrock (1999) J. Alloys Compd. 293:877",
                "AB₅: A=La,Ce,Mm (Misch metal), B=Ni,Co,Mn,Al; Ni/A ≈ 5"))

    ti_zr = c.get("Ti",0) + c.get("Zr",0)
    b_elements = c.get("Mn",0) + c.get("V",0) + c.get("Cr",0) + c.get("Fe",0) + c.get("Ni",0)
    if ti_zr > 0.20 and b_elements > 0.50:
        ratio_AB2 = b_elements / ti_zr if ti_zr > 0 else 0
        if 1.5 < ratio_AB2 < 2.5:
            checks.append(PASS("AB₂ Laves (TiMn₂-type)", ti_zr*100, "at% Ti+Zr",
                f"Ti+Zr = {ti_zr*100:.1f}%, B-elements = {b_elements*100:.1f}% → "
                f"TiMn₂/ZrMn₂ AB₂ Laves; capacity ≈ 1.8–2.0 wt% H",
                "Reilly & Wiswall (1974) Inorg. Chem. 13:218; "
                "Sandrock (1999) J. Alloys Compd. 293:877",
                "AB₂: A=Ti,Zr; B=Mn,V,Cr,Fe,Ni; B/A ≈ 2"))

    mg_at = c.get("Mg",0)
    if mg_at > 0.5:
        T_des = 573.0
        checks.append(INFO("MgH₂ formation", mg_at*100, "at% Mg",
            f"Mg = {mg_at*100:.0f}% → MgH₂ possible; max capacity {mg_at*7.6:.1f} wt% "
            f"but T_desorb ≈ 300°C (kinetics slow without catalyst)",
            "Schlapbach & Züttel (2001) Nature 414:353; "
            "Bogdanović & Sandrock (2002) MRS Bull. 27:712",
            "MgH₂: ΔH_d = 75 kJ/mol H₂;  T_eq(1 bar) ≈ 300°C → high T required"))

    return DomainResult(ID, NAME, checks)
