import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from physics.base import *

ID = 21
NAME = "Tribology & Wear"


def run(comp: dict, **_) -> DomainResult:
    c = norm(comp)
    checks = []
    wt = mol_to_wt(c)

    HV_mpa = wmean(c, "vickers")
    E_gpa   = wmean(c, "E")
    G_gpa   = wmean(c, "G")

    if HV_mpa and HV_mpa > 0:
        K_archard = 1.0 / (3.0 * HV_mpa)
        checks.append(INFO("Archard K_wear", K_archard, "mm³/(N·m) ×10⁻⁴",
            f"K ≈ {K_archard*1e4:.2f}×10⁻⁴ mm³/(N·m)  (H = {HV_mpa:.0f} MPa)  "
            f"[metals range 10⁻⁶–10⁻³; lower = better wear resistance]",
            "Archard (1953) J. Appl. Phys. 24:981; Rabinowicz (1995) Friction and Wear 2nd ed.",
            "Q = K·W·L/H;  K ≈ 1/(3H) for self-mated metals [Archard 1953]"))

    if HV_mpa and E_gpa and E_gpa > 0:
        HE = HV_mpa / (E_gpa * 1000)
        if HE > 0.020:
            checks.append(PASS("H/E (elastic strain limit)", HE, "",
                f"H/E = {HE:.4f} > 0.020 — good wear resistance in metals range "
                f"(hardened steels ~0.033; typical SS ~0.010)",
                "Ashby et al. (1989) Acta Metall. 37:2201; Leyland & Matthews (2000) Wear 246:1",
                "H/E for metals: 0.002–0.035;  > 0.020 = hard, good wear resistance"))
        elif HE > 0.008:
            checks.append(PASS("H/E (elastic strain limit)", HE, "",
                f"H/E = {HE:.4f} — typical structural alloy (austenitic SS ~0.010)",
                "Ashby et al. (1989) Acta Metall. 37:2201",
                "Metal range: 0.002–0.035"))
        else:
            checks.append(WARN("H/E (elastic strain limit)", HE, "",
                f"H/E = {HE:.4f} — soft alloy; higher wear rate (Pb, Al soft alloys ~0.003)",
                "Ashby et al. (1989) Acta Metall. 37:2201",
                "Metal range: 0.002–0.035; < 0.008 = soft, higher wear"))

    cr_wt = wt.get("Cr",0)*100; mo_wt = wt.get("Mo",0)*100; ni_wt = wt.get("Ni",0)*100
    galling_index = cr_wt*0.5 + mo_wt*2.0 + (HV_mpa/1000 if HV_mpa else 0.5)*10
    if galling_index > 20 or (HV_mpa and HV_mpa > 3000):
        checks.append(PASS("Galling / seizure resistance", galling_index, "index",
            f"Good galling resistance (Cr={cr_wt:.1f}%, Mo={mo_wt:.1f}%, H={HV_mpa:.0f} MPa)",
            "Budinski (1992) Galling Resistance of Engineering Alloys; ASTM G98",
            "Galling: Cr, Mo, high hardness → resist adhesive seizure"))
    elif galling_index > 8:
        checks.append(WARN("Galling / seizure resistance", galling_index, "index",
            f"Moderate galling risk (Cr={cr_wt:.1f}%, Mo={mo_wt:.1f}%)",
            "Budinski (1992); ASTM G98 Standard for Galling",
            "Lubrication recommended for high-contact applications"))
    else:
        checks.append(WARN("Galling / seizure resistance", galling_index, "index",
            f"High galling risk — low Cr/Mo, relatively soft",
            "Budinski (1992); ASTM G98",
            "Surface treatment (nitriding, coating) recommended"))

    if G_gpa and HV_mpa:
        tau_shear = G_gpa * 1e3 / 5.0
        mu_approx = tau_shear / HV_mpa
        checks.append(INFO("Friction coefficient μ (Bowden-Tabor)", mu_approx, "",
            f"μ ≈ τ/H = G/(5H) ≈ {mu_approx:.3f}  "
            f"(actual: 0.1–0.6 for metals with lubrication, 0.5–1.5 unlubricated)",
            "Bowden & Tabor (1950) Friction and Lubrication of Solids; "
            "Tabor (1951) Hardness of Metals, Oxford",
            "μ ≈ τ_c/H  [Bowden-Tabor junction growth theory];  τ_c ≈ G/5"))

    return DomainResult(ID, NAME, checks)
