import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from physics.base import *

ID = 11
NAME = "Hydrogen Embrittlement"

HE_SUSCEPTIBILITY = {
    "V":  0.90,
    "Nb": 0.75,
    "Ta": 0.70,
    "Ti": 0.65,
    "Zr": 0.60,
    "Hf": 0.55,
    "Pd": 0.50,
    "Fe": 0.30,
    "Ni": 0.25,
    "Co": 0.20,
    "Cr": 0.15,
    "Mo": 0.10,
    "W":  0.08,
    "Cu": 0.05,
    "Al": 0.05,
    "Au": 0.02,
    "Pt": 0.02,
}
DEFAULT_HE = 0.20


def run(comp: dict, **_) -> DomainResult:
    c = norm(comp)
    checks = []

    HEI = sum(c[s] * HE_SUSCEPTIBILITY.get(s, DEFAULT_HE) for s in c)
    if HEI < 0.20:
        checks.append(PASS("HEI (H embrittlement index)", HEI, "0–1",
            f"HEI = {HEI:.3f} — low H embrittlement susceptibility",
            "Gangloff (2003) Compr. Struct. Integrity 6:31; Thompson & Bernstein (1980) ASTM STP 733",
            "HEI = Σᵢ cᵢ·HEᵢ  [V:0.9, Nb:0.75, Ti:0.65, Zr:0.6, Fe:0.3, Ni:0.25, Cu:0.05]"))
    elif HEI < 0.45:
        checks.append(WARN("HEI", HEI, "0–1",
            f"HEI = {HEI:.3f} — moderate risk; avoid H₂ atmosphere or cathodic charging environments",
            "Gangloff (2003); Somerday & Sofronis (2008) Int. Hydrogen Infrastructure",
            "HEI = Σᵢ cᵢ·HEᵢ"))
    else:
        checks.append(FAIL("HEI", HEI, "0–1",
            f"HEI = {HEI:.3f} — HIGH H embrittlement risk; incompatible with H₂ service",
            "Gangloff (2003); Oriani (1972) Ber. Bunsenges. Phys. Chem. 76:848",
            "HEI = Σᵢ cᵢ·HEᵢ"))

    VEC_val = vec(c)
    if VEC_val >= 8.0:
        mech = "FCC → HELP (hydrogen-enhanced localised plasticity) dominant"
        mech_ref = "Birnbaum & Sofronis (1994) Mater. Sci. Eng. A 176:191"
    elif VEC_val >= 6.0:
        mech = "BCC/mixed → HEDE (hydrogen-enhanced decohesion) + HAC dominant"
        mech_ref = "Troiano (1960) Trans. ASM 52:54; Oriani (1972)"
    else:
        mech = "HCP → hydride-induced embrittlement (δ-hydride) dominant in Ti/Zr"
        mech_ref = "Westlake (1969) Trans. ASM 62:1000"
    checks.append(INFO("HE mechanism", VEC_val, "VEC",
        f"VEC = {VEC_val:.2f} → {mech}",
        mech_ref,
        "VEC ≥ 8 → FCC → HELP;  VEC < 8 BCC/HCP → HEDE/hydride"))

    hydride_formers = {s: c[s] for s in c if s in {"Ti","Zr","V","Nb","Ta","Hf","Pd"}
                       and c[s] > 0.01}
    if hydride_formers:
        total_hf = sum(hydride_formers.values()) * 100
        if total_hf > 50:
            checks.append(WARN("Hydride-forming elements", total_hf, "at%",
                f"Hydride-formers (Ti/Zr/V/Nb) = {total_hf:.1f} at% — embrittling metal hydrides can form",
                "Westlake (1969) Trans. ASM 62:1000; Lufrano & Sofronis (1996) Acta Mater. 44:1767",
                "Ti, Zr, V, Nb, Hf, Pd form brittle δ-hydride phases above critical H fugacity"))
        else:
            checks.append(INFO("Hydride-forming elements", total_hf, "at%",
                f"Hydride-formers = {total_hf:.1f} at% — monitor H levels in service",
                "Westlake (1969) Trans. ASM 62:1000"))
    else:
        checks.append(PASS("Hydride-forming elements", 0, "at%",
            "No significant hydride-forming elements — no δ-hydride risk",
            "Westlake (1969) Trans. ASM 62:1000"))

    fe_at = c.get("Fe", 0); ni_at = c.get("Ni", 0); cr_at = c.get("Cr", 0)
    if fe_at > 0.4 and ni_at > 0.08 and cr_at > 0.12 and VEC_val >= 7.8:
        checks.append(PASS("Austenitic FCC stability", VEC_val, "VEC",
            "FCC austenite stable (Ni+Cr SS) → H diffusivity ≈ 10⁻¹⁴ m²/s → high HE resistance",
            "Kiuchi & McLellan (1983) Acta Metall. 31:961; Perng & Altstetter (1987) Acta Metall. 35:2547",
            "D_H(FCC) ≈ 10⁻¹⁴ m²/s vs D_H(BCC) ≈ 10⁻⁸ m²/s"))
    elif VEC_val < 6.87:
        checks.append(WARN("BCC H diffusion", VEC_val, "VEC",
            f"BCC structure (VEC={VEC_val:.2f}) → D_H ≈ 10⁻⁸ m²/s → rapid H transport → HE risk",
            "Kiuchi & McLellan (1983) Acta Metall. 31:961",
            "D_H(BCC) ≈ 10⁻⁸ m²/s — fast H transport"))
    else:
        checks.append(INFO("Crystal structure H diffusion", VEC_val, "VEC",
            f"VEC = {VEC_val:.2f} — mixed or transitional crystal structure",
            "Kiuchi & McLellan (1983) Acta Metall. 31:961"))

    return DomainResult(ID, NAME, checks)
