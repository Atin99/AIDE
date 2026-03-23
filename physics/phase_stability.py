import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from physics.base import *

ID = 17
NAME = "Phase Stability"

SIGMA_FORMERS = {"Cr","Mo","W","Re","V","Si","Mn"}
TCP_ELEMENTS  = {"Mo","W","Re","Cr","V","Nb"}
L12_FORMERS   = {"Al","Ti","Ta","Nb"}
B2_FORMERS    = {"Al"}


def run(comp: dict, **_) -> DomainResult:
    c = norm(comp)
    checks = []
    VEC_val = vec(c)
    dH = delta_H_mix(c)
    d = delta_size(c)

    if VEC_val >= 8.0:
        xtal = "FCC solid solution"
    elif VEC_val >= 6.87:
        xtal = "FCC+BCC dual-phase"
    elif VEC_val >= 6.0:
        xtal = "BCC solid solution"
    else:
        xtal = "HCP or complex (low VEC)"
    checks.append(INFO("Crystal structure (VEC)", VEC_val, "VEC",
        f"VEC = {VEC_val:.2f} → {xtal}",
        "Guo et al. (2011) Calphad 35:95; Poletti & Battezzati (2014) Acta Mater. 75:297",
        "FCC: VEC≥8.0;  BCC: 6≤VEC<6.87;  FCC+BCC: 6.87≤VEC<8.0"))

    sigma_frac = sum(c.get(s,0) for s in SIGMA_FORMERS)
    if 6.0 <= VEC_val <= 8.0 and sigma_frac > 0.25:
        checks.append(FAIL("σ/Laves phase risk", sigma_frac*100, "at%",
            f"VEC={VEC_val:.2f} ∈ [6,8] AND σ-formers={sigma_frac*100:.1f}% > 25% → σ or Laves embrittlement",
            "Sims et al. (1987) Superalloys II, Wiley; Solomon & Devine (1982) ASM Symp.",
            "σ-phase: VEC ∈ [6,8] ∧ Σ(Cr,Mo,W,Re,V,Si,Mn) > 25 at%"))
    else:
        checks.append(PASS("σ/Laves phase risk", sigma_frac*100, "at%",
            f"σ-formers = {sigma_frac*100:.1f}%, VEC = {VEC_val:.2f} — low TCP/σ risk",
            "Sims et al. (1987) Superalloys II",
            "σ-phase: VEC ∈ [6,8] ∧ σ-formers > 25%"))

    ti_at = c.get("Ti",0); zr_at = c.get("Zr",0)
    beta_stab = c.get("V",0)+c.get("Mo",0)+c.get("Nb",0)+c.get("Cr",0)
    if (ti_at+zr_at) > 0.5 and 0.05 < beta_stab < 0.30:
        checks.append(WARN("ω-phase (Ti/Zr BCC)", beta_stab*100, "at% β-stab.",
            f"Ti/Zr={( ti_at+zr_at)*100:.0f}%, β-stabilisers={beta_stab*100:.1f}% → ω-phase precipitate on aging",
            "Williams (1971) Met. Trans. 2:3285; de Fontaine (1988) Met. Trans. A 19:169",
            "ω in BCC Ti/Zr: β-stab. (V,Mo,Nb,Cr) ∈ [5,30]% triggers ω on slow cool/aging"))
    else:
        checks.append(PASS("ω-phase (Ti/Zr BCC)", beta_stab*100, "at% β-stab.",
            f"No ω-phase risk (Ti+Zr={( ti_at+zr_at)*100:.0f}%, β-stab={beta_stab*100:.1f}%)",
            "Williams (1971) Met. Trans. 2:3285"))

    ni_at = c.get("Ni",0)
    l12_at = sum(c.get(s,0) for s in L12_FORMERS)
    if ni_at > 0.40 and l12_at > 0.04:
        checks.append(PASS("L12 γ' precipitation", l12_at*100, "at% (Al+Ti+Ta+Nb)",
            f"Ni={ni_at*100:.0f}%, L12-formers={l12_at*100:.1f}% → Ni₃(Al,Ti) γ' expected; precipitation hardening",
            "Sims et al. (1987) Superalloys II; Pollock & Tin (2006) J. Propul. Power 22:361",
            "γ': Ni₃(Al,Ti,Nb,Ta) — ordered L12 in Ni-base alloys; requires Al+Ti+Nb+Ta > 4 at%"))
    else:
        checks.append(INFO("L12 γ' precipitation", l12_at*100, "at%",
            f"L12 formers = {l12_at*100:.1f}% (Ni={ni_at*100:.0f}%) — no strong L12 γ' expected",
            "Sims et al. (1987) Superalloys II"))

    al_at = c.get("Al",0)
    b2_base = c.get("Fe",0)+c.get("Ni",0)+c.get("Co",0)
    if al_at > 0.15 and b2_base > 0.35:
        checks.append(WARN("B2 ordering (XAl)", al_at*100, "at% Al",
            f"Al={al_at*100:.0f}%, (Fe+Ni+Co)={b2_base*100:.0f}% → B2 ordered phase (FeAl, NiAl) risk; may embrittle",
            "Miracle (1993) Acta Metall. 41:649; Liu et al. (1990) Intermetallics",
            "B2: Al > 15 at% + Fe/Ni/Co base → ordered bcc-derivative; brittle at RT"))
    else:
        checks.append(PASS("B2 ordering (XAl)", al_at*100, "at% Al",
            f"Al = {al_at*100:.1f}% — below B2 ordering threshold",
            "Miracle (1993) Acta Metall. 41:649"))

    if dH is not None and dH > 5:
        checks.append(FAIL("Spinodal decomposition", dH, "kJ/mol",
            f"ΔHmix = {dH:.2f} > 5 kJ/mol — d²G/dc² < 0 possible; spinodal decomposition risk",
            "Cahn & Hilliard (1958) J. Chem. Phys. 28:258",
            "Spinodal: d²G/dc² < 0 when ΔHmix > 0 (immiscibility)"))
    elif dH is not None and dH > 0:
        checks.append(WARN("Spinodal decomposition", dH, "kJ/mol",
            f"ΔHmix = {dH:.2f} > 0 — possible miscibility gap at low T",
            "Cahn & Hilliard (1958) J. Chem. Phys. 28:258",
            "Spinodal instability when ΔHmix > 0"))
    else:
        checks.append(PASS("Spinodal decomposition", dH if dH else 0, "kJ/mol",
            f"ΔHmix {'= '+str(round(dH,2)) if dH else 'unavailable'} — no spinodal risk",
            "Cahn & Hilliard (1958) J. Chem. Phys. 28:258",
            "Spinodal: d²G/dc² < 0 ↔ ΔHmix > 0"))

    return DomainResult(ID, NAME, checks)
