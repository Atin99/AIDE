import sys, os, math
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from physics.base import *

ID = 22
NAME = "Acoustic Properties"


def run(comp: dict, **_) -> DomainResult:
    c = norm(comp)
    checks = []

    B_gpa = wmean(c, "B")
    G_gpa = wmean(c, "G")
    rho   = density_rule_of_mixtures(c)

    if not all([B_gpa, G_gpa, rho]):
        return DomainResult(ID, NAME,
            [INFO("Acoustic", None, "", "Insufficient B, G, or density data",
                  "Simmons & Wang (1971)")],
            error="Missing moduli or density")

    rho_kgm3 = rho * 1000

    C_11 = (B_gpa + 4*G_gpa/3) * 1e9
    v_L = math.sqrt(C_11 / rho_kgm3) / 1000
    checks.append(INFO("v_L (longitudinal)", v_L, "km/s",
        f"v_L = {v_L:.2f} km/s  (Fe≈5.9, Al≈6.3, Ni≈5.6, Ti≈6.1 km/s — ASM Handbook)",
        "Simmons & Wang (1971) Single-Crystal Elastic Constants; "
        "Kinsler et al. (2000) Fundamentals of Acoustics §3",
        "v_L = √((B+4G/3)/ρ)  [Navier equation — isotropic medium]"))

    v_S = math.sqrt(G_gpa * 1e9 / rho_kgm3) / 1000
    checks.append(INFO("v_S (shear)", v_S, "km/s",
        f"v_S = {v_S:.2f} km/s  (Fe≈3.2, Al≈3.1, Ni≈2.9 km/s — ASM Handbook)",
        "Simmons & Wang (1971); Auld (1973) Acoustic Fields §5",
        "v_S = √(G/ρ)"))

    Z_ac = rho_kgm3 * v_L * 1000 / 1e6
    checks.append(INFO("Acoustic impedance Z", Z_ac, "MRayl",
        f"Z = {Z_ac:.1f} MRayl  (water: 1.5, Al: 17, Fe: 46, W: 100 MRayl — Kinsler 2000)",
        "Kinsler et al. (2000) Fundamentals of Acoustics §1; Auld (1973)",
        "Z = ρ·v_L  [MRayl = 10⁶ Pa·s/m]; governs ultrasonic reflection at interfaces"))

    if 4.0 <= v_L <= 9.0:
        checks.append(PASS("UT-NDT suitability", v_L, "km/s",
            f"v_L = {v_L:.2f} km/s ∈ [4,9] — ideal for ultrasonic non-destructive testing; "
            f"recommend probe frequency ≈ {v_L*1e6/5/1e6:.1f} MHz for 5 mm grain",
            "ASNT SNT-TC-1A (2016) Ultrasonic Testing; "
            "Krautkrämer & Krautkrämer (1990) Ultrasonic Testing of Materials 4th ed.",
            "Optimal UT: v_L ∈ [4,9] km/s; f = v_L/(10·d_grain) for grain-size resolution"))
    else:
        checks.append(WARN("UT-NDT suitability", v_L, "km/s",
            f"v_L = {v_L:.2f} km/s — non-standard for UT; adjust probe frequency",
            "ASNT SNT-TC-1A (2016)",
            "UT: v_L ∈ [4,9] km/s preferred for standard probes"))

    B_gpa_v = B_gpa; G_gpa_v = G_gpa
    C11 = B_gpa_v + 4*G_gpa_v/3; C12 = B_gpa_v - 2*G_gpa_v/3
    if C11 - C12 > 0:
        A_Z = 2*G_gpa_v / (C11 - C12)
        checks.append(INFO("Zener anisotropy A_Z", A_Z, "",
            f"A_Z ≈ {A_Z:.2f}  (A=1: isotropic; Fe:2.4, Ni:2.5, Cu:3.2, W:1.0 — Simmons 1971)",
            "Zener (1948) Elasticity and Anelasticity of Metals; Simmons & Wang (1971)",
            "A_Z = 2G/(C₁₁−C₁₂)  [isotropic approx: Cᵢ from B,G]"))

    return DomainResult(ID, NAME, checks)
