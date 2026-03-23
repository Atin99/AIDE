import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from physics.base import *

ID = 26
NAME = "Relativistic Effects"

RELATIVISTIC_EFFECTS = {
    "Au": "6s orbital contraction → yellow colour (interband transition 2.4 eV); lower reactivity vs Ag",
    "Hg": "6s² stabilisation → liquid at RT (Tm=234 K); Tl,Pb,Bi all depress Tm",
    "Pb": "6p spin-orbit: lower Tm vs expected from group trend",
    "Bi": "Relativistic band structure → semimetal, large diamagnetism, thermoelectric",
    "Pt": "5d expansion → exceptional catalytic activity; white colour (vs Au yellow)",
    "W":  "5d/6s contraction → highest Tm of all metals (3695 K)",
    "Tl": "6s lone pair → preference for +1 over +3 (vs Al/Ga/In +3)",
    "Po": "6p relativistic → metallic character despite being period-6 p element",
    "Rn": "6p SO coupling → anomalous chemistry vs Xe",
}


def run(comp: dict, **_) -> DomainResult:
    c = norm(comp)
    checks = []

    f_rel = sum(c[s] * (get(s).Z / 137.0)**2 for s in c)
    if f_rel < 0.02:
        checks.append(PASS("Relativistic correction", f_rel * 100, "%",
            f"f_rel = {f_rel*100:.3f}% — negligible relativistic effects (all Z < 70)",
            "Pyykko (1988) Chem. Rev. 88:563; Autschbach (2012) J. Chem. Educ. 89:816",
            "f_rel = Σᵢ cᵢ·(Zᵢ/137)²  [leading scalar relativistic term]"))
    elif f_rel < 0.10:
        checks.append(WARN("Relativistic correction", f_rel * 100, "%",
            f"f_rel = {f_rel*100:.2f}% — notable; standard DFT may underestimate (use PBE+SOC or ZORA)",
            "Pyykko (1988); van Lenthe et al. (1994) J. Chem. Phys. 101:9783 (ZORA)",
            "f_rel = Σᵢ cᵢ·(Zᵢ/137)²;  > 2% → relativistic DFT recommended"))
    else:
        checks.append(WARN("Relativistic correction", f_rel * 100, "%",
            f"f_rel = {f_rel*100:.1f}% — STRONG relativistic effects; "
            f"4-component or ZORA-relativistic DFT mandatory",
            "Pyykko (1988) Chem. Rev. 88:563; Autschbach (2012) J. Chem. Educ. 89:816",
            "f_rel = Σᵢ cᵢ·(Zᵢ/137)²;  > 10% → full 4-component Dirac-KS required"))

    soc_elements = [s for s in c if get(s).Z > 50 and c[s] > 0.01]
    if soc_elements:
        soc_score = sum(c[s] * (get(s).Z/137)**4 * 1e4 for s in soc_elements)
        checks.append(INFO("Spin-orbit coupling", soc_score, "rel. units",
            f"SOC significant for: {soc_elements}  (SOC ∝ Z⁴; heavy elements)",
            "Pyykko & Desclaux (1979) Acc. Chem. Res. 12:276; "
            "Autschbach (2012) J. Chem. Educ. 89:816",
            "SOC ∝ ∂V/∂r · L·S  scales as Z⁴; critical for magnetic anisotropy, NMR shifts"))

    for s in c:
        if s in RELATIVISTIC_EFFECTS and c[s] > 0.05:
            checks.append(INFO(f"Relativistic anomaly: {s}", c[s]*100, "at%",
                f"{s} ({c[s]*100:.1f}%): {RELATIVISTIC_EFFECTS[s]}",
                "Pyykko (1988) Chem. Rev. 88:563",
                "Documented relativistic effect — affects property prediction"))

    if not soc_elements and f_rel < 0.02:
        checks.append(INFO("Relativistic summary", f_rel*100, "%",
            "All elements Z ≤ 50 — standard DFT (PBE/PBEsol) fully adequate",
            "Pyykko (1988); Kresse & Furthmüller (1996) PRB 54:11169 (VASP)",
            "Z ≤ 50: scalar relativistic (PAW) sufficient"))

    return DomainResult(ID, NAME, checks)
