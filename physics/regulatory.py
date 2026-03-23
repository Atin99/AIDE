import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from physics.base import *

ID = 14
NAME = "Regulatory & Safety"

ROHS_RESTRICTED = {"Pb", "Hg", "Cd"}

REACH_SVHC_METALS = {"Pb", "As", "Cd", "Hg", "Cr", "Ni", "Co", "Tl", "Be"}

IARC_GROUP1  = {"As", "Cd", "Cr", "Ni", "Be", "Hg"}
IARC_GROUP2A = {"Co", "Pb", "Se"}


def run(comp: dict, **_) -> DomainResult:
    c = norm(comp)
    checks = []
    wt = mol_to_wt(c)

    def wp(sym): return wt.get(sym, 0.0) * 100

    rohs_threshold = {"Cd": 0.01}
    rohs_violations = []
    for sym in ROHS_RESTRICTED:
        thresh = rohs_threshold.get(sym, 0.1)
        if wp(sym) > thresh:
            rohs_violations.append(f"{sym}={wp(sym):.3f}%>{thresh}%")

    if not rohs_violations:
        checks.append(PASS("RoHS 2011/65/EU", 0, "violations",
            "No restricted substances above RoHS thresholds",
            "EU RoHS Directive 2011/65/EU (as amended by 2015/863/EU); Annex II",
            "Thresholds: Pb,Hg,Cr⁶⁺,PBB,PBDE < 0.1 wt%;  Cd < 0.01 wt%"))
    else:
        checks.append(FAIL("RoHS 2011/65/EU", len(rohs_violations), "violations",
            f"RoHS violations: {'; '.join(rohs_violations)}",
            "EU RoHS Directive 2011/65/EU Annex II",
            "Thresholds: Pb,Hg < 0.1 wt%;  Cd < 0.01 wt%"))

    group1_present  = [s for s in IARC_GROUP1  if wp(s) > 0.1]
    group2a_present = [s for s in IARC_GROUP2A if wp(s) > 0.1]

    if not group1_present and not group2a_present:
        checks.append(PASS("IARC carcinogen", 0, "group-1/2A elements > 0.1%",
            "No IARC Group 1 or 2A carcinogens above 0.1 wt%",
            "IARC Monographs Vol. 100C (2012); Vol. 123 (2023)"))
    elif group1_present:
        checks.append(WARN("IARC carcinogen (Group 1)", len(group1_present), "elements",
            f"IARC Group 1 (definitely carcinogenic): {group1_present} — occupational exposure limits apply",
            "IARC Monographs Vol. 100C (2012); EU REACH Reg. 1907/2006 Art. 59",
            "IARC Group 1: As, Cd, Cr(VI) compounds, Ni compounds, Be — in compound form"))
    if group2a_present:
        checks.append(WARN("IARC carcinogen (Group 2A)", len(group2a_present), "elements",
            f"IARC Group 2A (probably carcinogenic): {group2a_present}",
            "IARC Monographs; EU REACH SVHC Candidate List (2024)"))

    svhc_present = [(s, wp(s)) for s in REACH_SVHC_METALS if wp(s) > 0.1 and s in c]
    if not svhc_present:
        checks.append(PASS("REACH SVHC", 0, "SVHC elements > 0.1%",
            "No SVHC metals above 0.1 wt% article threshold",
            "EU REACH Reg. 1907/2006 Art. 57,59; ECHA Candidate List (June 2024)"))
    else:
        svhc_str = "; ".join(f"{s}:{w:.2f}%" for s, w in svhc_present)
        checks.append(WARN("REACH SVHC", len(svhc_present), "SVHC elements",
            f"SVHC above 0.1% threshold: {svhc_str} — REACH Art. 33 disclosure obligations",
            "EU REACH Reg. 1907/2006 Art. 57,59; ECHA SVHC Candidate List",
            "SVHC threshold: 0.1 wt% in article (REACH Art. 7(2))"))

    radio = [s for s in c if get(s).radioactive and c[s] > 1e-4]
    if not radio:
        checks.append(PASS("Radioactive elements", 0, "elements",
            "No radioactive elements above 0.01 at% — no ICRP controls required",
            "ICRP Publication 103 (2007); NUBASE2020 (Kondev et al. 2021)"))
    else:
        checks.append(WARN("Radioactive elements", len(radio), "elements",
            f"Radioactive: {radio} — ICRP radiation protection measures required",
            "ICRP Publication 103 (2007); NUBASE2020 (Kondev et al. 2021) Chin. Phys. C 45:030001"))

    fe_wt = wp("Fe"); cr_wt = wp("Cr"); ni_wt = wp("Ni"); mo_wt = wp("Mo")
    if fe_wt >= 50 and cr_wt >= 10.5:
        if ni_wt >= 8 and cr_wt >= 18:
            bis = "BIS IS:6911 Type 304-equivalent or higher"
        elif ni_wt >= 8 and cr_wt >= 16 and mo_wt >= 2:
            bis = "BIS IS:6911 Type 316-equivalent"
        elif ni_wt < 1 and cr_wt >= 10.5:
            bis = "BIS IS:6911 ferritic grade"
        else:
            bis = "BIS IS:6911 stainless steel (verify exact grade)"
        checks.append(INFO("BIS IS:6911 classification", cr_wt, "wt% Cr",
            f"{bis}  (Cr={cr_wt:.1f}%, Ni={ni_wt:.1f}%, Mo={mo_wt:.1f}%)",
            "Bureau of Indian Standards IS:6911:2017 Specification for Stainless Steel Sheet and Strip"))
    else:
        checks.append(INFO("BIS classification", fe_wt, "wt% Fe",
            f"Not an SS composition (Fe={fe_wt:.1f}%, Cr={cr_wt:.1f}%) — check applicable BIS standard",
            "Bureau of Indian Standards — consult IS:1570 (alloy steels) or IS:733 (Al alloys)"))

    return DomainResult(ID, NAME, checks)
