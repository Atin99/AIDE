import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from physics.base import *

ID = 4
NAME = "Corrosion"

def run(comp: dict, environment: str = "neutral", **_) -> DomainResult:
    c = norm(comp)
    checks = []
    wt = mol_to_wt(c)

    fe_wt  = wt.get("Fe", 0) * 100
    cr_wt  = wt.get("Cr", 0) * 100
    mo_wt  = wt.get("Mo", 0) * 100
    ni_wt  = wt.get("Ni", 0) * 100
    n_wt   = wt.get("N",  0) * 100

    if fe_wt < 30 or cr_wt < 5:
        checks.append(INFO("PREN applicability", fe_wt, "wt% Fe",
            f"PREN is defined for Fe-Cr base alloys (Fe={fe_wt:.1f}%, Cr={cr_wt:.1f}%). "
            f"Not applicable here — assess via oxide stability (Ellingham) instead.",
            "Sedriks (1996) Corrosion of Stainless Steels 2nd ed., p.70"))
    else:
        pren = PREN_wt(c)
        if pren >= 40:
            checks.append(PASS("PREN", pren, "",
                f"PREN = {pren:.1f} ≥ 40 — excellent pitting resistance (super-duplex class)",
                "Sedriks (1996); ASTM G48; Oldfield & Sutton (1978) Br. Corros. J.",
                "PREN = %Cr + 3.3·%Mo + 16·%N  (wt%)"))
        elif pren >= 25:
            checks.append(PASS("PREN", pren, "",
                f"PREN = {pren:.1f} ≥ 25 — good pitting resistance",
                "Sedriks (1996); ASTM G48",
                "PREN = %Cr + 3.3·%Mo + 16·%N"))
        elif pren >= 10:
            checks.append(WARN("PREN", pren, "",
                f"PREN = {pren:.1f} — moderate; adequate for mild environments only",
                "Sedriks (1996); ASTM G48",
                "PREN = %Cr + 3.3·%Mo + 16·%N"))
        else:
            checks.append(FAIL("PREN", pren, "",
                f"PREN = {pren:.1f} < 10 — poor pitting resistance",
                "Sedriks (1996); ASTM G48",
                "PREN = %Cr + 3.3·%Mo + 16·%N"))

    if cr_wt >= 10.5:
        checks.append(PASS("Cr₂O₃ passivation", cr_wt, "wt% Cr",
            f"Cr = {cr_wt:.1f} wt% ≥ 10.5% — continuous Cr₂O₃ passive film forms",
            "Pickering (1989) Mater. Sci. Tech. 5:213; Uhlig & Revie (2008)",
            "Threshold: 10.5 wt% Cr  (Pickering 1989)"))
    elif cr_wt >= 5:
        checks.append(WARN("Cr₂O₃ passivation", cr_wt, "wt% Cr",
            f"Cr = {cr_wt:.1f} wt% — partial passivation only; not sufficient for SS",
            "Pickering (1989)"))
    else:
        checks.append(INFO("Cr₂O₃ passivation", cr_wt, "wt% Cr",
            f"Cr = {cr_wt:.1f} wt% — no chromia passivation",
            "Pickering (1989)"))

    if fe_wt > 30 and 8 <= ni_wt <= 45:
        checks.append(WARN("SCC (Cl⁻) susceptibility", ni_wt, "wt% Ni",
            f"Ni = {ni_wt:.1f} wt% in Fe-base alloy — susceptible to chloride SCC (Copson curve)",
            "Copson (1959) Corrosion 15:194t; ISO 15156 / NACE MR0175",
            "Copson (1959): risk zone Ni ∈ [8,45] wt% in Fe-base"))
    else:
        checks.append(PASS("SCC (Cl⁻) susceptibility", ni_wt, "wt% Ni",
            f"Outside Copson SCC risk window (Ni = {ni_wt:.1f} wt%)",
            "Copson (1959) Corrosion 15:194t",
            "Copson (1959): risk Ni ∈ [8,45]%"))

    return DomainResult(ID, NAME, checks)
