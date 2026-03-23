
import math, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from physics.base import wmean, norm, density_rule_of_mixtures


def stress_analysis(comp: dict, geometry: dict, loading: str = "tensile") -> dict:
    results = {}
    E = wmean(comp, "E")
    sy_hv = wmean(comp, "vickers")
    sy = sy_hv / 3.0 if sy_hv else None
    rho = density_rule_of_mixtures(comp)
    nu = wmean(comp, "nu") or 0.3

    t = geometry.get("thickness_mm", 25.0)
    D = geometry.get("diameter_mm")
    L = geometry.get("length_mm", 1000.0)
    W = geometry.get("width_mm", 100.0)
    F = geometry.get("force_kN", 10.0)
    P = geometry.get("pressure_MPa")
    shape = geometry.get("shape", "plate")

    F_N = F * 1000

    if shape == "plate" and loading == "tensile":
        A = t * W
        sigma = F_N / A
        results["stress_MPa"] = sigma
        results["formula"] = "σ = F/A"
        results["citation"] = "Timoshenko & Gere (1961) Theory of Elastic Stability"
        if sy:
            results["safety_factor"] = sy / sigma if sigma > 0 else float('inf')
        if E:
            strain = sigma / (E * 1000)
            results["strain"] = strain
            results["elongation_mm"] = strain * L

    elif shape == "plate" and loading == "bending":
        I = W * t**3 / 12
        y = t / 2
        M = F_N * L / 4
        sigma = M * y / I
        delta = F_N * L**3 / (48 * (E * 1000 if E else 200000) * I)
        results["stress_MPa"] = sigma
        results["deflection_mm"] = delta
        results["moment_of_inertia_mm4"] = I
        results["formula"] = "σ = My/I, δ = FL³/48EI"
        results["citation"] = "Timoshenko & Gere (1961)"
        if sy:
            results["safety_factor"] = sy / sigma if sigma > 0 else float('inf')

    elif shape in ("cylinder", "tube") and loading == "pressure" and P and D:
        t_wall = t
        sigma_hoop = P * D / (2 * t_wall)
        sigma_axial = P * D / (4 * t_wall)
        sigma_vm = math.sqrt(sigma_hoop**2 + sigma_axial**2 - sigma_hoop * sigma_axial)
        results["hoop_stress_MPa"] = sigma_hoop
        results["axial_stress_MPa"] = sigma_axial
        results["von_mises_MPa"] = sigma_vm
        results["formula"] = "σ_hoop = pD/2t, σ_axial = pD/4t (ASME Section VIII)"
        results["citation"] = "ASME BPVC Section VIII Div.1 (2023)"
        if sy:
            results["safety_factor"] = sy / sigma_vm if sigma_vm > 0 else float('inf')
            t_min = P * D / (2 * sy * 0.6)
            results["min_thickness_mm"] = t_min

    elif shape in ("cylinder", "tube") and loading == "tensile" and D:
        A = math.pi * D * t
        sigma = F_N / A
        results["stress_MPa"] = sigma
        results["formula"] = "σ = F/(πDt)"
        if sy:
            results["safety_factor"] = sy / sigma if sigma > 0 else float('inf')

    elif shape == "beam" and loading == "bending":
        b = W
        h = t
        I = b * h**3 / 12
        y = h / 2
        M = F_N * L / 4
        sigma = M * y / I
        delta = F_N * L**3 / (48 * (E * 1000 if E else 200000) * I)
        results["stress_MPa"] = sigma
        results["deflection_mm"] = delta
        results["formula"] = "σ = My/I (rectangular beam, center load)"
        results["citation"] = "Beer & Johnston (2020) Mechanics of Materials 8th ed."
        if sy:
            results["safety_factor"] = sy / sigma if sigma > 0 else float('inf')

    elif shape == "sphere" and loading == "pressure" and P and D:
        sigma = P * D / (4 * t)
        results["stress_MPa"] = sigma
        results["formula"] = "σ = pD/4t (thin-wall sphere)"
        if sy:
            results["safety_factor"] = sy / sigma if sigma > 0 else float('inf')

    return results


def buckling_analysis(comp: dict, geometry: dict) -> dict:
    E = wmean(comp, "E")
    if not E:
        return {"error": "Young's modulus not available"}

    L = geometry.get("length_mm", 1000.0)
    shape = geometry.get("shape", "beam")
    W = geometry.get("width_mm", 50.0)
    t = geometry.get("thickness_mm", 10.0)
    D = geometry.get("diameter_mm")

    if shape in ("cylinder", "tube") and D:
        I = math.pi * D**3 * t / 8
    else:
        I = W * t**3 / 12

    E_MPa = E * 1000
    P_cr = math.pi**2 * E_MPa * I / L**2
    sigma_cr = P_cr / (W * t if shape not in ("cylinder", "tube") else math.pi * D * t) if t > 0 else 0

    return {
        "critical_load_N": P_cr,
        "critical_load_kN": P_cr / 1000,
        "critical_stress_MPa": sigma_cr,
        "formula": "P_cr = π²EI/L² (Euler buckling)",
        "citation": "Euler (1757); Timoshenko & Gere (1961)",
    }


def thermal_stress_analysis(comp: dict, delta_T: float, geometry: dict = None) -> dict:
    E = wmean(comp, "E")
    alpha = wmean(comp, "thermal_exp")
    nu = wmean(comp, "nu") or 0.3

    if not E or not alpha:
        return {"error": "E or CTE data not available"}

    alpha_K = alpha * 1e-6
    sigma = E * 1000 * alpha_K * abs(delta_T) / (1 - nu)

    sy_hv = wmean(comp, "vickers")
    sy = sy_hv / 3.0 if sy_hv else None

    result = {
        "thermal_stress_MPa": sigma,
        "delta_T_K": delta_T,
        "CTE_per_K": alpha_K,
        "formula": "σ_th = EαΔT/(1−ν)",
        "citation": "Boley & Weiner (1960) Theory of Thermal Stresses",
    }
    if sy:
        result["safety_factor"] = sy / sigma if sigma > 0 else float('inf')
        result["will_yield"] = sigma > sy
    return result


def heat_transfer_analysis(comp: dict, geometry: dict, T_hot: float, T_cold: float,
                            h_conv: float = 25.0) -> dict:
    k = wmean(comp, "thermal_cond")
    if not k:
        return {"error": "Thermal conductivity not available"}

    t = geometry.get("thickness_mm", 25.0) / 1000
    W = geometry.get("width_mm", 100.0) / 1000
    L_m = geometry.get("length_mm", 1000.0) / 1000
    A = W * L_m if geometry.get("shape", "plate") == "plate" else math.pi * geometry.get("diameter_mm", 100.0) / 1000 * L_m

    dT = abs(T_hot - T_cold)
    q_cond = k * A * dT / t
    q_conv = h_conv * A * dT
    Bi = h_conv * t / k

    return {
        "heat_flux_conduction_W": q_cond,
        "heat_flux_convection_W": q_conv,
        "biot_number": Bi,
        "lumped_valid": Bi < 0.1,
        "formula": "q = kAΔT/L (Fourier); Bi = hL/k",
        "citation": "Incropera & DeWitt (2006) Fundamentals of Heat and Mass Transfer 6th ed.",
    }


def fatigue_life_estimate(comp: dict, sigma_max: float, sigma_min: float = 0,
                           R: float = -1) -> dict:
    sy_hv = wmean(comp, "vickers")
    UTS_est = sy_hv / 2.5 if sy_hv else None

    if not UTS_est:
        return {"error": "Hardness data not available for fatigue estimate"}

    sigma_a = (sigma_max - sigma_min) / 2
    sigma_m = (sigma_max + sigma_min) / 2

    sigma_f_prime = 1.5 * UTS_est
    b = -0.085

    if UTS_est > 0:
        sigma_a_corrected = sigma_a / (1 - sigma_m / UTS_est) if sigma_m < UTS_est else sigma_a
    else:
        sigma_a_corrected = sigma_a

    if sigma_a_corrected <= 0:
        return {"N_f_cycles": float('inf'), "note": "No alternating stress"}

    try:
        N_f = 0.5 * (sigma_a_corrected / sigma_f_prime) ** (1 / b)
    except (ValueError, ZeroDivisionError):
        N_f = float('inf')

    Se = 0.5 * UTS_est if UTS_est < 1400 else 700

    return {
        "stress_amplitude_MPa": sigma_a,
        "mean_stress_MPa": sigma_m,
        "corrected_amplitude_MPa": sigma_a_corrected,
        "fatigue_life_cycles": N_f,
        "endurance_limit_MPa": Se,
        "infinite_life": sigma_a_corrected < Se,
        "formula": "Basquin: σ_a = σ'_f(2N_f)^b; Goodman mean stress correction",
        "citation": "Dowling (2013) Mechanical Behavior of Materials 4th ed.",
    }


def critical_crack_size(comp: dict, sigma_applied: float) -> dict:
    E = wmean(comp, "E")
    sy_hv = wmean(comp, "vickers")
    sy = sy_hv / 3.0 if sy_hv else None

    if not E or not sy:
        return {"error": "E or yield data not available"}

    K_IC_est = 0.1 * sy
    Y = 1.12

    if sigma_applied <= 0:
        return {"error": "Applied stress must be positive"}

    a_c = (K_IC_est / (Y * sigma_applied)) ** 2 / math.pi * 1000

    return {
        "critical_crack_mm": a_c,
        "K_IC_estimated_MPa_sqrt_m": K_IC_est,
        "geometry_factor_Y": Y,
        "note": "K_IC is a ROUGH estimate from hardness. Real K_IC must be measured experimentally.",
        "formula": "a_c = (K_IC / Yσ)² / π (Irwin 1957)",
        "citation": "Irwin (1957) J. Appl. Mech. 24:361; Anderson (2005) Fracture Mechanics 3rd ed.",
    }


def natural_frequency(comp: dict, geometry: dict, boundary: str = "simply_supported") -> dict:
    E = wmean(comp, "E")
    rho = density_rule_of_mixtures(comp)
    if not E or not rho:
        return {"error": "E or density not available"}

    L = geometry.get("length_mm", 1000.0) / 1000
    W = (geometry.get("width_mm", 50.0)) / 1000
    t = geometry.get("thickness_mm", 10.0) / 1000

    I = W * t**3 / 12
    A = W * t
    E_Pa = E * 1e9
    rho_kgm3 = rho * 1000

    lam = {"simply_supported": math.pi, "cantilever": 1.8751,
           "fixed_fixed": 4.7300, "free_free": 4.7300}
    lam_val = lam.get(boundary, math.pi)

    f_n = lam_val**2 / (2 * math.pi) * math.sqrt(E_Pa * I / (rho_kgm3 * A * L**4))

    return {
        "natural_frequency_Hz": f_n,
        "boundary": boundary,
        "formula": "f_n = (λ²/2π)√(EI/ρAL⁴)",
        "citation": "Rao (2017) Mechanical Vibrations 6th ed.",
    }


def full_engineering_analysis(comp: dict, geometry: dict, loading: str = "tensile",
                                T_op_K: float = 298.0, T_ambient_K: float = 298.0) -> dict:
    results = {"composition": comp, "geometry": geometry, "loading": loading}

    results["stress"] = stress_analysis(comp, geometry, loading)
    results["buckling"] = buckling_analysis(comp, geometry)

    if T_op_K != T_ambient_K:
        results["thermal_stress"] = thermal_stress_analysis(comp, T_op_K - T_ambient_K, geometry)
        results["heat_transfer"] = heat_transfer_analysis(comp, geometry, T_op_K, T_ambient_K)

    if loading in ("cyclic", "fatigue"):
        sigma = results["stress"].get("stress_MPa", 100)
        results["fatigue"] = fatigue_life_estimate(comp, sigma, sigma * 0.1)

    results["vibration"] = natural_frequency(comp, geometry)

    return results
