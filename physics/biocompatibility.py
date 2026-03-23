import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from physics.base import *

ID = 25
NAME = "Biocompatibility"

CYTOTOX = {
    "Ti": 0.00, "Zr": 0.00, "Ta": 0.00, "Nb": 0.05,
    "Al": 0.10, "V":  0.40,
    "Fe": 0.05, "Cr": 0.30,
    "Ni": 0.60,
    "Co": 0.50,
    "Mo": 0.05, "W":  0.05,
    "Cu": 0.20, "Mn": 0.15,
    "Be": 1.00, "As": 1.00, "Cd": 1.00, "Hg": 1.00, "Pb": 0.90,
}
OSSEO = {"Ti":1.0,"Zr":0.85,"Ta":0.80,"Nb":0.75,"Al":0.40,"Co":0.30,"Cr":0.25,"Ni":0.10}


def run(comp: dict, **_) -> DomainResult:
    c = norm(comp)
    checks = []

    cyto = sum(c[s] * CYTOTOX.get(s, 0.15) for s in c)
    if cyto < 0.10:
        checks.append(PASS("Cytotoxicity index (ISO 10993-5)", cyto, "0–1",
            f"CytoIdx = {cyto:.3f} < 0.10 — biocompatible; low ion release toxicity",
            "ISO 10993-5:2009 Biological evaluation; Geetha et al. (2009) Prog. Mater. Sci. 54:397",
            "CytoIdx = Σᵢ cᵢ·cytoᵢ  [Ti:0, Ni:0.6, V:0.4, Be:1.0]"))
    elif cyto < 0.25:
        checks.append(WARN("Cytotoxicity index (ISO 10993-5)", cyto, "0–1",
            f"CytoIdx = {cyto:.3f} — caution; in-vitro testing required per ISO 10993-5",
            "ISO 10993-5:2009; Rack & Qazi (2006) Mater. Sci. Eng. C 26:1269",
            "CytoIdx = Σᵢ cᵢ·cytoᵢ"))
    else:
        checks.append(FAIL("Cytotoxicity index (ISO 10993-5)", cyto, "0–1",
            f"CytoIdx = {cyto:.3f} — HIGH toxicity risk; NOT suitable for implant without coating",
            "ISO 10993-5:2009; ASTM F2129",
            "CytoIdx = Σᵢ cᵢ·cytoᵢ; Ni, Co, Cr, V major concerns"))

    osseo = sum(c[s] * OSSEO.get(s, 0.20) for s in c)
    if osseo > 0.50:
        checks.append(PASS("Osseointegration", osseo, "0–1",
            f"Osseo = {osseo:.2f} — excellent bone-implant bonding expected (Ti-rich alloy)",
            "Rack & Qazi (2006) Mater. Sci. Eng. C 26:1269; Niinomi (2008) J. Mech. Behav. Biomed. 1:30",
            "Osseo = Σᵢ cᵢ·osseoᵢ  [Ti:1.0, Zr:0.85, Ta:0.80, Nb:0.75]"))
    elif osseo > 0.25:
        checks.append(WARN("Osseointegration", osseo, "0–1",
            f"Osseo = {osseo:.2f} — moderate bone bonding; surface treatment may improve",
            "Rack & Qazi (2006); Niinomi (2008)",
            "Osseo = Σᵢ cᵢ·osseoᵢ"))
    else:
        checks.append(FAIL("Osseointegration", osseo, "0–1",
            f"Osseo = {osseo:.2f} — poor bone bonding; not suitable for load-bearing implant",
            "Rack & Qazi (2006) Mater. Sci. Eng. C 26:1269",
            "Osseo = Σᵢ cᵢ·osseoᵢ"))

    ferro_frac = c.get("Fe",0) + c.get("Co",0) + c.get("Ni",0)
    if ferro_frac < 0.05:
        checks.append(PASS("MRI compatibility (ASTM F2213)", ferro_frac*100, "at% ferro",
            f"Ferromagnetic elements = {ferro_frac*100:.1f}% — MRI safe (non-magnetic)",
            "ASTM F2213-17 MRI compatibility; ASTM F2503-20 labelling",
            "ASTM F2213: Fe+Co+Ni < 5% → MRI conditional/safe"))
    elif ferro_frac < 0.15:
        checks.append(WARN("MRI compatibility (ASTM F2213)", ferro_frac*100, "at%",
            f"Ferromagnetic = {ferro_frac*100:.1f}% — MRI artifact possible; full testing required",
            "ASTM F2213-17; ASTM F2503-20",
            "ASTM F2213: measure force, torque, heating in MRI scanner"))
    else:
        checks.append(FAIL("MRI compatibility (ASTM F2213)", ferro_frac*100, "at%",
            f"Ferromagnetic = {ferro_frac*100:.1f}% — MRI incompatible",
            "ASTM F2213-17; ASTM F2503-20",
            "Fe+Co+Ni > 15% → strong force in MRI bore → dangerous"))

    ti_at = c.get("Ti",0)*100; al_at = c.get("Al",0)*100; v_at = c.get("V",0)*100
    if abs(ti_at-90)<3 and abs(al_at-6)<1.5 and abs(v_at-4)<1.5:
        checks.append(PASS("Ti-6Al-4V ELI (ASTM F136)", ti_at, "at% Ti",
            f"Ti-{al_at:.0f}Al-{v_at:.0f}V — ASTM F136 Ti-6Al-4V ELI specification; "
            f"gold-standard orthopaedic/dental implant",
            "ASTM F136-13 Ti-6Al-4V ELI; Rack & Qazi (2006)",
            "Ti-6Al-4V ELI: O<0.13%, Fe<0.25%, C<0.08%, N<0.05%  [ASTM F136]"))
    elif c.get("Ti",0) > 0.7:
        checks.append(INFO("Ti-based implant alloy", ti_at, "at% Ti",
            f"Ti-rich alloy ({ti_at:.0f}%) — potential implant material; verify cyto and osseo",
            "ASTM F136, F1295, F2066 (various Ti implant grades)"))

    return DomainResult(ID, NAME, checks)
