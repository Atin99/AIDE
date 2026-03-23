import sys, os, math
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from physics.base import *


class FormabilityDomain:
    ID = 36
    NAME = "Formability"
    WEIGHT = 0.9

    @staticmethod
    def run(comp, T_K=298.0, **kw):
        c = norm(comp)
        checks = []

        E = wmean(c, "E")
        hv = wmean(c, "vickers")
        if E and hv:
            sy = hv / 3.0
            n_est = 0.3 - 0.0001 * sy
            n_est = max(0.05, min(0.5, n_est))
            if n_est > 0.2:
                checks.append(PASS("Strain hardening exponent", n_est, "",
                    f"n≈{n_est:.2f} — good formability (deep drawing OK)",
                    "Hosford & Caddell (2011) Metal Forming 4th ed."))
            elif n_est > 0.1:
                checks.append(WARN("Strain hardening exponent", n_est, "",
                    f"n≈{n_est:.2f} — moderate formability",
                    "Hosford & Caddell (2011)"))
            else:
                checks.append(FAIL("Strain hardening exponent", n_est, "",
                    f"n≈{n_est:.2f} — poor formability, spring-back issues",
                    "Hosford & Caddell (2011)"))

        nu_avg = wmean(c, "nu")
        if nu_avg:
            if nu_avg > 0.33:
                checks.append(PASS("Poisson's ratio", nu_avg, "",
                    f"ν={nu_avg:.3f} — metallic, ductile",
                    "Greaves et al. (2011) Nat. Mater. 10:823"))
            elif nu_avg > 0.25:
                checks.append(WARN("Poisson's ratio", nu_avg, "",
                    f"ν={nu_avg:.3f} — semi-brittle",
                    "Greaves et al. (2011)"))
            else:
                checks.append(FAIL("Poisson's ratio", nu_avg, "",
                    f"ν={nu_avg:.3f} — brittle tendency, poor formability",
                    "Greaves et al. (2011)"))

        return DomainResult(36, "Formability", checks)


class AMDomain:
    ID = 37
    NAME = "Additive Manufacturing"
    WEIGHT = 0.8

    @staticmethod
    def run(comp, T_K=298.0, **kw):
        c = norm(comp)
        checks = []

        Tm_vals = [get(s).Tm for s in c if get(s).Tm]
        if len(Tm_vals) >= 2:
            freeze_range = max(Tm_vals) - min(Tm_vals)
            if freeze_range < 50:
                checks.append(PASS("Solidification cracking", freeze_range, "K",
                    "Narrow freeze range — low crack risk in LPBF",
                    "DebRoy et al. (2018) Prog. Mater. Sci. 92:112"))
            elif freeze_range < 150:
                checks.append(WARN("Solidification cracking", freeze_range, "K",
                    "Moderate freeze range — optimize scan strategy",
                    "DebRoy et al. (2018)"))
            else:
                checks.append(FAIL("Solidification cracking", freeze_range, "K",
                    f"Wide freeze range ({freeze_range:.0f}K) — high crack risk",
                    "DebRoy et al. (2018)"))

        k = wmean(c, "thermal_cond")
        alpha = wmean(c, "thermal_exp")
        if k and alpha:
            rs_proxy = alpha / k * 1000
            if rs_proxy < 0.5:
                checks.append(PASS("Residual stress proxy", rs_proxy, "",
                    "Low thermal gradient tendency — good for AM",
                    "Mercelis & Kruth (2006) Rapid Prototyping J. 12:254"))
            elif rs_proxy < 1.5:
                checks.append(WARN("Residual stress proxy", rs_proxy, "",
                    "Moderate — stress relief HT recommended",
                    "Mercelis & Kruth (2006)"))
            else:
                checks.append(FAIL("Residual stress proxy", rs_proxy, "",
                    "High residual stress expected — substrate preheating needed",
                    "Mercelis & Kruth (2006)"))

        rho_e = wmean(c, "resistivity")
        if rho_e:
            if rho_e > 30:
                checks.append(PASS("Laser absorptivity proxy", rho_e, "μΩ·cm",
                    "High resistivity — good laser absorption at 1064nm",
                    "Rubenchik et al. (2015) J. Mater. Process. Technol."))
            elif rho_e > 5:
                checks.append(WARN("Laser absorptivity proxy", rho_e, "μΩ·cm",
                    "Moderate absorptivity — may need higher power",
                    "Rubenchik et al. (2015)"))
            else:
                checks.append(FAIL("Laser absorptivity proxy", rho_e, "μΩ·cm",
                    "Low absorptivity (high reflectivity) — Cu/Au/Ag are difficult",
                    "Rubenchik et al. (2015)"))

        for sym in c:
            el = get(sym)
            if el.Tb and el.Tb < 1500 and c[sym] > 0.01:
                checks.append(WARN("Vaporisation risk", el.Tb, "K",
                    f"{sym} (Tb={el.Tb:.0f}K) may vaporize during LPBF",
                    "Mukherjee et al. (2016) J. Appl. Phys. 121:064904"))

        return DomainResult(37, "Additive Manufacturing", checks)


class HeatTreatDomain:
    ID = 38
    NAME = "Heat Treatment Response"
    WEIGHT = 1.0

    @staticmethod
    def run(comp, T_K=298.0, **kw):
        c = norm(comp)
        wt = mol_to_wt(c)
        checks = []

        fe = wt.get("Fe", 0)
        if fe > 0.5:
            C = wt.get("C", 0) * 100
            Mn = wt.get("Mn", 0) * 100
            Cr = wt.get("Cr", 0) * 100
            Mo_w = wt.get("Mo", 0) * 100
            Ni_w = wt.get("Ni", 0) * 100
            DI = 0.54 * C * (1 + 0.64*Mn) * (1 + 2.16*Cr) * (1 + 3.0*Mo_w) * (1 + 0.36*Ni_w)
            if DI > 5:
                checks.append(PASS("Hardenability (DI)", DI, "inch",
                    f"DI={DI:.1f}\" — excellent through-hardening",
                    "Grossmann (1942); ASTM A255"))
            elif DI > 1.5:
                checks.append(PASS("Hardenability (DI)", DI, "inch",
                    f"DI={DI:.1f}\" — moderate hardenability",
                    "Grossmann (1942); ASTM A255"))
            else:
                checks.append(WARN("Hardenability (DI)", DI, "inch",
                    f"DI={DI:.1f}\" — shallow hardening, small sections only",
                    "Grossmann (1942); ASTM A255"))

        precip_formers = sum(c.get(s, 0) for s in ["Al", "Ti", "Nb", "V", "Cu"])
        if precip_formers > 0.03:
            checks.append(PASS("Precipitation potential", precip_formers*100, "%",
                f"{precip_formers*100:.1f}% age-hardenable elements — ageing HT viable",
                "Porter & Easterling (2009) Phase Transformations in Metals 3rd ed."))
        else:
            checks.append(INFO("Precipitation potential", precip_formers*100, "%",
                "Low precipitate former content — mainly solid solution strengthened",
                "Porter & Easterling (2009)"))

        high_Tm_frac = sum(c.get(s, 0) for s in ["W", "Mo", "Nb", "Ta", "Re", "V"]
                            if s in c)
        if high_Tm_frac > 0.05:
            checks.append(PASS("Grain growth resistance", high_Tm_frac*100, "%",
                f"{high_Tm_frac*100:.1f}% refractory elements — grain growth inhibited",
                "Humphreys & Hatherly (2012) Recrystallization 3rd ed."))
        else:
            checks.append(INFO("Grain growth resistance", high_Tm_frac*100, "%",
                "Low refractory content — normal grain growth",
                "Humphreys & Hatherly (2012)"))

        return DomainResult(38, "Heat Treatment Response", checks)


class FractureDomain:
    ID = 39
    NAME = "Fracture Mechanics"
    WEIGHT = 1.1

    @staticmethod
    def run(comp, T_K=298.0, **kw):
        c = norm(comp)
        checks = []

        hv = wmean(c, "vickers")
        E = wmean(c, "E")

        if hv and E:
            sy = hv / 3.0
            K_IC_est = 0.1 * sy
            G_IC = K_IC_est**2 / (E * 1000)

            checks.append(INFO("K_IC estimate", K_IC_est, "MPa√m",
                f"K_IC≈{K_IC_est:.0f} MPa√m (ROUGH estimate from σ_y, NOT measured)",
                "Irwin (1957) J. Appl. Mech. 24:361",
                "K_IC ≈ 0.1 × σ_y (lower bound proxy)"))

            pugh = pugh_ratio(c)
            if pugh and pugh > 1.75:
                checks.append(PASS("Ductile fracture tendency", pugh, "B/G",
                    f"B/G={pugh:.2f} > 1.75 — ductile fracture expected",
                    "Pugh (1954) Philos. Mag. 45:823"))
            elif pugh:
                checks.append(WARN("Brittle fracture tendency", pugh, "B/G",
                    f"B/G={pugh:.2f} < 1.75 — brittle fracture risk",
                    "Pugh (1954)"))

            thickness = kw.get("thickness_mm", 25.0)
            plane_strain_t = 2.5 * (K_IC_est / sy) ** 2 * 1000
            if thickness > plane_strain_t:
                checks.append(INFO("Plane strain", plane_strain_t, "mm",
                    f"t={thickness}mm > t_ps={plane_strain_t:.1f}mm — plane strain (lower toughness)",
                    "Anderson (2005) Fracture Mechanics 3rd ed."))
            else:
                checks.append(INFO("Plane stress", plane_strain_t, "mm",
                    f"t={thickness}mm < t_ps={plane_strain_t:.1f}mm — plane stress (higher toughness)",
                    "Anderson (2005)"))

        return DomainResult(39, "Fracture Mechanics", checks)


class ImpactDomain:
    ID = 40
    NAME = "Impact Toughness"
    WEIGHT = 1.0

    @staticmethod
    def run(comp, T_K=298.0, **kw):
        c = norm(comp)
        checks = []

        vec_val = vec(c)
        bcc_frac = sum(c.get(s, 0) for s in c if get(s).crystal == "BCC")
        fcc_frac = sum(c.get(s, 0) for s in c if get(s).crystal == "FCC")

        if fcc_frac > 0.5:
            checks.append(PASS("DBTT risk (FCC)", fcc_frac, "",
                "FCC-dominant — no sharp ductile-brittle transition",
                "Hertzberg (2012) Deformation & Fracture 5th ed."))
        elif bcc_frac > 0.5:
            checks.append(WARN("DBTT risk (BCC)", bcc_frac, "",
                "BCC-dominant — ductile-brittle transition exists, low-T toughness drops",
                "Hertzberg (2012)"))

        if T_K < 200 and bcc_frac > 0.3:
            checks.append(FAIL("Low-T impact risk", T_K, "K",
                f"Service at {T_K:.0f}K with BCC alloy — DBTT concern",
                "IMO IACS UR S6 (2019)"))
        elif T_K < 200 and fcc_frac > 0.5:
            checks.append(PASS("Cryogenic impact", T_K, "K",
                f"FCC alloy at {T_K:.0f}K — retains toughness (austenitic SS, Al, Ni-base)",
                "Read & Reed (1979) Cryogenics 19:579"))

        checks.append(INFO("Impact improvement", None, "",
            "Grain refinement improves Charpy energy: fine grain → higher shelf energy",
            "Hall (1951) Proc. Phys. Soc. B 64:747"))

        return DomainResult(40, "Impact Toughness", checks)


class GalvanicDomain:
    ID = 41
    NAME = "Galvanic Compatibility"
    WEIGHT = 0.9

    GALVANIC_POTENTIAL = {
        "Mg": -1600, "Zn": -1030, "Al": -760, "Cr": -500, "Fe": -440,
        "Ni": -250, "Sn": -140, "Pb": -130, "Cu": -200, "Ti": -50,
        "Ag": 50, "Pt": 150, "Au": 250, "Co": -280, "Mo": -200,
        "W": -200, "Nb": -300, "V": -350, "Zr": -900, "Mn": -600,
        "Ta": -300,
    }

    @staticmethod
    def run(comp, T_K=298.0, **kw):
        c = norm(comp)
        checks = []

        potentials = {s: GalvanicDomain.GALVANIC_POTENTIAL.get(s) for s in c}
        known = {s: p for s, p in potentials.items() if p is not None}
        if known:
            E_alloy = sum(c[s] * p for s, p in known.items()) / sum(c[s] for s in known)
            checks.append(INFO("Galvanic potential", E_alloy, "mV vs SCE",
                f"E_alloy ≈ {E_alloy:.0f} mV vs SCE (seawater galvanic series)",
                "Revie & Uhlig (2008) Corrosion and Corrosion Control 4th ed."))

            common_metals = {"Carbon steel": -440, "316L SS": -50, "Copper": -200,
                              "Aluminium": -760, "Titanium": -50}
            for name, E_partner in common_metals.items():
                dE = abs(E_alloy - E_partner)
                if dE < 50:
                    checks.append(PASS(f"vs {name}", dE, "mV",
                        f"ΔE={dE:.0f}mV — compatible", "MIL-STD-889D"))
                elif dE < 250:
                    checks.append(WARN(f"vs {name}", dE, "mV",
                        f"ΔE={dE:.0f}mV — monitor, insulate if wet",
                        "MIL-STD-889D"))
                else:
                    checks.append(FAIL(f"vs {name}", dE, "mV",
                        f"ΔE={dE:.0f}mV — severe galvanic corrosion risk",
                        "MIL-STD-889D; ASTM G82"))

        return DomainResult(41, "Galvanic Compatibility", checks)


class SolidificationDomain:
    ID = 42
    NAME = "Solidification"
    WEIGHT = 0.9

    @staticmethod
    def run(comp, T_K=298.0, **kw):
        c = norm(comp)
        checks = []

        Tm_bar = wmean(c, "Tm")
        if Tm_bar:
            checks.append(INFO("Liquidus estimate", Tm_bar, "K",
                f"T_liq ≈ {Tm_bar:.0f}K ({Tm_bar-273:.0f}°C) — rule-of-mixtures",
                "Vegard (1921) Z. Phys. 5:17"))

        Tm_vals = [get(s).Tm for s in c if get(s).Tm and c[s] > 0.01]
        if len(Tm_vals) >= 2:
            delta_T = max(Tm_vals) - min(Tm_vals)
            if delta_T < 50:
                checks.append(PASS("Microsegregation", delta_T, "K",
                    f"Narrow freeze range ({delta_T:.0f}K) — low segregation",
                    "Kurz & Fisher (1998) Fundamentals of Solidification 4th ed."))
            elif delta_T < 200:
                checks.append(WARN("Microsegregation", delta_T, "K",
                    f"Moderate freeze range ({delta_T:.0f}K) — dendritic segregation expected",
                    "Kurz & Fisher (1998)"))
            else:
                checks.append(FAIL("Microsegregation", delta_T, "K",
                    f"Wide freeze range ({delta_T:.0f}K) — severe segregation, homogenise",
                    "Kurz & Fisher (1998)"))

        k = wmean(c, "thermal_cond")
        if k:
            if k > 30:
                checks.append(PASS("Constitutional supercooling", k, "W/(m·K)",
                    "High thermal conductivity — planar/cellular preferred",
                    "Tiller et al. (1953) Acta Met. 1:428"))
            else:
                checks.append(WARN("Constitutional supercooling", k, "W/(m·K)",
                    "Low thermal conductivity — dendritic growth likely",
                    "Tiller et al. (1953)"))

        return DomainResult(42, "Solidification", checks)


def run_formability(comp, **kw):       return FormabilityDomain.run(comp, **kw)
def run_am(comp, **kw):                return AMDomain.run(comp, **kw)
def run_heat_treat(comp, **kw):        return HeatTreatDomain.run(comp, **kw)
def run_fracture(comp, **kw):          return FractureDomain.run(comp, **kw)
def run_impact(comp, **kw):            return ImpactDomain.run(comp, **kw)
def run_galvanic(comp, **kw):          return GalvanicDomain.run(comp, **kw)
def run_solidification(comp, **kw):    return SolidificationDomain.run(comp, **kw)
