
import math
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from physics.base import *

ID   = 30
NAME = "Structural Efficiency"

_H_CONV_W_M2K = 25.0


def _sigma_y_estimate(comp: dict) -> float | None:
    c = norm(comp)
    hv = wmean(c, "vickers")
    if hv is None or hv < 1.0:
        return None
    return hv / 3.0


def run(comp: dict, thickness_mm: float = 25.0, **_) -> DomainResult:
    c = norm(comp)
    checks = []

    rho   = density_rule_of_mixtures(c)
    E_gpa = wmean(c, "E")
    G_gpa = wmean(c, "G")
    kappa = wmean(c, "thermal_cond")
    alpha = wmean(c, "thermal_exp")
    sy    = _sigma_y_estimate(c)

    if rho is None or rho < 0.5:
        checks.append(INFO("Structural Efficiency", None, "",
            "Density data unavailable — indices cannot be computed",
            "Ashby (1989) Acta Metall. 37:1273"))
        return DomainResult(ID, NAME, checks)

    rho_gcc = rho
    E_gpa   = E_gpa   or 0.0
    G_gpa   = G_gpa   or 0.0

    if E_gpa > 0:
        spec_E = E_gpa / rho_gcc
        checks.append(INFO("Specific stiffness E/rho", spec_E, "GPa/(g/cm3)",
            f"E/rho = {spec_E:.1f} — steel ~24.6, Ti64 ~25.7, Al7075 ~25.6",
            "Ashby (2011) Materials Selection 4th ed. Appendix B"))

    if E_gpa > 0:
        M1 = math.sqrt(E_gpa) / rho_gcc
        if M1 >= 2.2:
            checks.append(PASS("M1: E^0.5/rho (stiff beam)", M1, "(GPa)^0.5/(g/cm3)",
                f"M1 = {M1:.2f} — above steel ({1.69:.2f}); good lightweight stiffness",
                "Ashby (1989) Acta Metall. 37:1273; Ashby (2011) 4th ed. Ch.5",
                "M1 = E^(1/2) / rho  [min-mass stiff beam]"))
        elif M1 >= 1.5:
            checks.append(PASS("M1: E^0.5/rho (stiff beam)", M1, "(GPa)^0.5/(g/cm3)",
                f"M1 = {M1:.2f} — comparable to structural steel ({1.69:.2f})",
                "Ashby (1989) Acta Metall. 37:1273",
                "M1 = E^(1/2) / rho"))
        else:
            checks.append(WARN("M1: E^0.5/rho (stiff beam)", M1, "(GPa)^0.5/(g/cm3)",
                f"M1 = {M1:.2f} — below steel reference ({1.69:.2f}); heavy for stiffness",
                "Ashby (1989) Acta Metall. 37:1273",
                "M1 = E^(1/2) / rho"))

    if sy is not None and sy > 1.0:
        M2 = (sy ** (2.0/3.0)) / rho_gcc
        if M2 >= 20.0:
            checks.append(PASS("M2: sy^0.67/rho (strong beam)", M2, "MPa^0.67/(g/cm3)",
                f"M2 = {M2:.1f} — excellent specific strength (Ti64~28, Al7075~26)",
                "Ashby (1989) Acta Metall. 37:1273",
                "M2 = sigma_y^(2/3) / rho  [min-mass strong beam]"))
        elif M2 >= 7.0:
            checks.append(PASS("M2: sy^0.67/rho (strong beam)", M2, "MPa^0.67/(g/cm3)",
                f"M2 = {M2:.1f} — comparable to structural steel (~7.2)",
                "Ashby (1989) Acta Metall. 37:1273",
                "M2 = sigma_y^(2/3) / rho"))
        else:
            checks.append(WARN("M2: sy^0.67/rho (strong beam)", M2, "MPa^0.67/(g/cm3)",
                f"M2 = {M2:.1f} — below structural steel reference (~7.2)",
                "Ashby (1989) Acta Metall. 37:1273",
                "M2 = sigma_y^(2/3) / rho"))

    if E_gpa > 0:
        M3 = (E_gpa ** (1.0/3.0)) / rho_gcc
        if M3 >= 0.72:
            checks.append(PASS("M3: E^0.33/rho (stiff panel)", M3, "(GPa)^0.33/(g/cm3)",
                f"M3 = {M3:.2f} — steel ref ~0.72; adequate panel stiffness efficiency",
                "Ashby (1989) Acta Metall. 37:1273",
                "M3 = E^(1/3) / rho  [min-mass stiff panel]"))
        else:
            checks.append(WARN("M3: E^0.33/rho (stiff panel)", M3, "(GPa)^0.33/(g/cm3)",
                f"M3 = {M3:.2f} — below steel ref (~0.72)",
                "Ashby (1989) Acta Metall. 37:1273",
                "M3 = E^(1/3) / rho"))

    nu_val = wmean(c, "nu") or 0.3
    if sy is not None and E_gpa > 0 and alpha is not None and alpha > 0 and kappa is not None:
        alpha_si = alpha * 1e-6
        E_si     = E_gpa * 1e9
        M5 = (kappa * sy * 1e6 * (1 - nu_val)) / (E_si * alpha_si)
        R_prime = (sy * 1e6 * (1 - nu_val)) / (E_si * alpha_si)
        if R_prime >= 100:
            checks.append(PASS("Hasselman R' (thermal shock)", R_prime, "K",
                f"R' = {R_prime:.0f} K — good thermal shock resistance (steel ~80-120 K)",
                "Hasselman (1969) J. Am. Ceram. Soc. 52:600",
                "R' = sigma_f*(1-nu) / (E*alpha)  [critical temp jump to crack]"))
        elif R_prime >= 50:
            checks.append(WARN("Hasselman R' (thermal shock)", R_prime, "K",
                f"R' = {R_prime:.0f} K — moderate; avoid rapid thermal cycling",
                "Hasselman (1969) J. Am. Ceram. Soc. 52:600",
                "R' = sigma_f*(1-nu) / (E*alpha)"))
        else:
            checks.append(WARN("Hasselman R' (thermal shock)", R_prime, "K",
                f"R' = {R_prime:.0f} K — low thermal shock resistance",
                "Hasselman (1969) J. Am. Ceram. Soc. 52:600",
                "R' = sigma_f*(1-nu) / (E*alpha)"))

    if sy is not None:
        spec_sy = sy / rho_gcc
        checks.append(INFO("Specific strength sy/rho", spec_sy, "MPa/(g/cm3)",
            f"sigma_y/rho = {spec_sy:.0f} — steel structural ~60, Ti64 ~200, Al7075 ~180",
            "Ashby (2011) Materials Selection 4th ed. Appendix B"))

    if kappa is not None:
        M_mean = wmean(c, "atomic_mass") or 55.0
        Cp_est = 3 * 8.314 / M_mean
        rho_si = rho_gcc * 1e6
        a = (kappa / (rho_si * 1e-6 * Cp_est * 1e3)) * 1e6
        a_m2s = kappa / (rho_gcc * 1e3 * Cp_est * 1e3)
        a_mm2s = a_m2s * 1e6
        checks.append(INFO("Thermal diffusivity", a_mm2s, "mm2/s",
            f"a = {a_mm2s:.2f} mm2/s (steel ~3.5, Al ~84, Ti ~2.9)",
            "Carslaw & Jaeger (1959) Conduction of Heat in Solids, Oxford",
            "a = kappa / (rho * Cp)  [Dulong-Petit Cp = 3R/M]"))

    if kappa is not None and kappa > 0:
        L_m  = (thickness_mm / 2.0) / 1000.0
        Bi   = _H_CONV_W_M2K * L_m / kappa
        if Bi < 0.1:
            checks.append(PASS("Biot number Bi (t={:.0f}mm)".format(thickness_mm),
                Bi, "",
                f"Bi = {Bi:.4f} << 0.1 — thermally thin; uniform temp in section",
                "Incropera & DeWitt (2007) Fundamentals of Heat Transfer 7th ed.",
                "Bi = h*L/kappa; L = t/2; thermally thin if Bi < 0.1"))
        elif Bi < 1.0:
            checks.append(WARN("Biot number Bi (t={:.0f}mm)".format(thickness_mm),
                Bi, "",
                f"Bi = {Bi:.3f} — moderate gradient; through-thickness thermal stress possible",
                "Incropera & DeWitt (2007)",
                "Bi = h*L/kappa; L = t/2"))
        else:
            checks.append(WARN("Biot number Bi (t={:.0f}mm)".format(thickness_mm),
                Bi, "",
                f"Bi = {Bi:.2f} > 1 — large thermal gradient; quench stress significant",
                "Incropera & DeWitt (2007)",
                "Bi = h*L/kappa"))

    return DomainResult(ID, NAME, checks)
