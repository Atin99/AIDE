import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from physics.base import *

ID = 23
NAME = "Shape Memory"


def run(comp: dict, **_) -> DomainResult:
    c = norm(comp)
    checks = []
    wt = mol_to_wt(c)

    ni_at = c.get("Ni",0)*100; ti_at = c.get("Ti",0)*100
    cu_at = c.get("Cu",0)*100; zn_at = c.get("Zn",0)*100
    al_at = c.get("Al",0)*100

    is_nitinol = abs(ni_at - 50) < 5 and abs(ti_at - 50) < 5
    if is_nitinol:
        ni_excess = ni_at - 50.0
        Ms_C = 100.0 - 10.0 * ni_excess
        Ms_K = Ms_C + 273.15
        checks.append(PASS("NiTi Nitinol detected", ni_at, "at% Ni",
            f"NITINOL composition (Ni={ni_at:.1f}%, Ti={ti_at:.1f}%) — "
            f"Ms ≈ {Ms_C:.0f}°C  ({Ms_K:.0f} K)",
            "Otsuka & Wayman (1998) Shape Memory Materials; "
            "Wasilewski (1971) Met. Trans. 2:2973",
            "Ms ≈ 100 − 10(Ni−50) °C  [Wasilewski 1971; for Ni ∈ [49,51]%]"))

        Af_C = Ms_C + 30
        Md_C = Ms_C + 80
        checks.append(PASS("Superelastic window", Af_C, "°C",
            f"Superelastic window ≈ {Af_C:.0f}–{Md_C:.0f}°C  "
            f"(above Af, below Md; recoverable strain ~8%)",
            "Duerig et al. (1990) Eng. Aspects of Shape Memory Alloys §1",
            "SE window: T ∈ [Af, Md];  Af ≈ Ms+30°C;  Md ≈ Ms+80°C (NiTi)"))

        checks.append(INFO("Clausius-Clapeyron dσ/dT", -6.0, "MPa/°C",
            "dσ/dT ≈ −6 MPa/°C for NiTi  (σ_cr increases with T above Ms)",
            "Otsuka & Wayman (1998); Stalmans et al. (1992) Acta Metall. 40:2921",
            "dσ/dT = −ΔH/(T₀·ε₀)  [Clausius-Clapeyron; ΔH≈−20 J/g, ε₀≈0.06 for NiTi]"))

    elif cu_at > 55 and zn_at > 15 and al_at > 3:
        checks.append(PASS("Cu-Zn-Al SMA detected", cu_at, "at% Cu",
            f"Cu={cu_at:.0f}%, Zn={zn_at:.0f}%, Al={al_at:.0f}% — "
            f"Cu-Zn-Al shape memory alloy; Ms typically −100 to +100°C",
            "Otsuka & Wayman (1998) §5; Horikawa et al. (1988) Met. Trans. A 19:915",
            "Cu-Zn-Al SMA: β₁→β₁' martensitic transformation; Tc range tunable by composition"))

    elif (c.get("Fe",0)*100 > 50 and c.get("Mn",0)*100 > 20 and c.get("Si",0)*100 > 4):
        fe_at = c.get("Fe",0)*100; mn_at = c.get("Mn",0)*100; si_at = c.get("Si",0)*100
        checks.append(WARN("Fe-Mn-Si SMA candidate", mn_at, "at% Mn",
            f"Fe={fe_at:.0f}%, Mn={mn_at:.0f}%, Si={si_at:.0f}% — "
            f"Fe-Mn-Si SMA; recoverable strain ≈ 2% (lower than NiTi)",
            "Sato et al. (1982) Trans. JIM 23:381; Otsuka (1990) Intermetallics",
            "Fe-Mn-Si: γ (FCC) → ε (HCP) martensite; less efficient than NiTi"))

    else:
        checks.append(INFO("Shape memory potential", ni_at, "at% Ni",
            f"No classical SMA composition detected  "
            f"(NiTi: Ni≈50+Ti≈50; Cu-Zn-Al; Fe-Mn-Si)",
            "Otsuka & Wayman (1998) Shape Memory Materials",
            "Known SMA systems: NiTi (Nitinol), Cu-Zn-Al, Cu-Al-Ni, Fe-Mn-Si, Ni-Mn-Ga"))

    return DomainResult(ID, NAME, checks)
