import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from physics.base import *

ID = 10
NAME = "Grain Boundary"

GB_EMBRITTLERS = {
    "S":  1.00,
    "P":  0.80,
    "Sb": 0.75,
    "Sn": 0.60,
    "As": 0.55,
    "O":  0.40,
    "N":  0.10,
}

GB_STRENGTHENERS = {
    "B":  -0.80,
    "C":  -0.20,
    "Re": -0.10,
    "W":  -0.05,
    "Mo": -0.05,
}


def run(comp: dict, **_) -> DomainResult:
    c = norm(comp)
    checks = []
    wt = mol_to_wt(c)

    def wp(sym): return wt.get(sym, 0.0) * 100

    gbe = sum(GB_EMBRITTLERS.get(s, 0) * c[s] * 100 for s in c)
    gbs = sum(abs(GB_STRENGTHENERS.get(s, 0)) * c[s] * 100 for s in c)
    net_gbe = max(0.0, gbe - gbs)

    if net_gbe < 0.02:
        checks.append(PASS("GB embrittlement index", net_gbe, "at% eq.",
            f"Net GBE = {net_gbe:.4f} at% — negligible GB embrittlement risk",
            "Hondros & Seah (1977) Met. Trans. A 8:1363; Lejček (2010) Grain Boundary Segregation",
            "GBE = Σᵢ potencyᵢ·cᵢ  (S: 1.0, P: 0.8, Sb: 0.75, Sn: 0.6, As: 0.55)"))
    elif net_gbe < 0.10:
        checks.append(WARN("GB embrittlement index", net_gbe, "at% eq.",
            f"Net GBE = {net_gbe:.4f} at% — moderate; monitor S, P, Sb, Sn levels",
            "Hondros & Seah (1977); Briant & Banerji (1978) Int. Met. Rev. 4:164",
            "GBE = Σᵢ potencyᵢ·cᵢ"))
    else:
        checks.append(FAIL("GB embrittlement index", net_gbe, "at% eq.",
            f"Net GBE = {net_gbe:.4f} at% — HIGH risk of grain boundary embrittlement / temper embrittlement",
            "Hondros & Seah (1977); McMahon (2001) Eng. Fract. Mech. 68:773",
            "GBE = Σᵢ potencyᵢ·cᵢ"))

    b_at = c.get("B", 0) * 100
    if b_at >= 0.005 and b_at <= 0.05:
        checks.append(PASS("Boron GB strengthening", b_at, "at% B",
            f"B = {b_at:.4f} at% ∈ [0.005, 0.05] — optimal B for GB cohesion in Ni alloys",
            "Krueger et al. (1992) Acta Metall. 40:2471; Liu & Pope (1993) Acta Metall. 41:2371",
            "Optimal B: 0.005–0.05 at% for grain boundary strengthening"))
    elif b_at > 0.05:
        checks.append(WARN("Boron GB strengthening", b_at, "at% B",
            f"B = {b_at:.4f} at% > 0.05 — excess B may form borides (M₃B₂), reducing benefit",
            "Krueger et al. (1992) Acta Metall. 40:2471",
            "Excess B → M₃B₂ borides → embrittlement"))
    else:
        checks.append(INFO("Boron GB strengthening", b_at, "at% B",
            f"B = {b_at:.4f} at% — no intentional B addition detected",
            "Krueger et al. (1992) Acta Metall. 40:2471"))

    G_val = wmean(c, "G") or 80.0
    b_burg = 0.25e-9
    M_taylor = 3.06
    tau_crss = G_val * 1e9 * b_burg / 10
    k_y = M_taylor * tau_crss * (b_burg ** 0.5) * 1e-3 / 1e3
    k_y_mpa_um05 = k_y * (1e3 ** 0.5)
    checks.append(INFO("Hall-Petch k_y", k_y_mpa_um05, "MPa·μm^0.5",
        f"k_y ≈ {k_y_mpa_um05:.2f} MPa·μm^0.5  (σ_y = σ₀ + k_y·d^{-0.5})",
        "Hall (1951) Proc. Phys. Soc. B 64:747; Petch (1953) JISI 174:25",
        "k_y = M·τ_CRSS·b^0.5  [Taylor factor M=3.06]"))

    cu_at = c.get("Cu", 0)
    if cu_at > 0.4:
        lme_risk = (c.get("Bi", 0) * 5.0 + c.get("Pb", 0) * 3.0
                    + c.get("Sn", 0) * 1.0) * 100
        if lme_risk > 0.5:
            checks.append(WARN("LME risk (Cu-base)", lme_risk, "weighted at%",
                f"Bi+Pb+Sn in Cu-base alloy — liquid metal embrittlement possible at T > 270°C",
                "Kamdar (1983) Prog. Mater. Sci. 28:1; Gordon (1978) Met. Trans. A 9:267",
                "LME: Bi (271°C), Pb (327°C), Sn (232°C) wet Cu grain boundaries"))
        else:
            checks.append(PASS("LME risk (Cu-base)", lme_risk, "weighted at%",
                "Low Bi/Pb/Sn in Cu-base — LME risk negligible",
                "Kamdar (1983) Prog. Mater. Sci. 28:1"))
    else:
        checks.append(INFO("LME risk", c.get("Cu", 0) * 100, "at% Cu",
            "LME risk assessment applies to Cu-base alloys only",
            "Kamdar (1983) Prog. Mater. Sci. 28:1"))

    return DomainResult(ID, NAME, checks)
