
import math
from dataclasses import dataclass, field
from typing import Optional
from core.elements import get, validate_composition

R = 8.31446


def norm(comp: dict) -> dict:
    t = sum(comp.values())
    return {k: v / t for k, v in comp.items() if v > 0}


def wmean(comp: dict, attr: str, default: Optional[float] = None) -> Optional[float]:
    c = norm(comp)
    total_w = 0.0
    weighted = 0.0
    for sym, xi in c.items():
        val = getattr(get(sym), attr, None)
        if val is None:
            if default is not None:
                val = default
            else:
                continue
        weighted += xi * val
        total_w  += xi
    if total_w < 1e-12:
        return None
    return weighted / total_w


def mol_to_wt(comp: dict) -> dict:
    c = norm(comp)
    wt = {sym: c[sym] * get(sym).atomic_mass for sym in c}
    t = sum(wt.values())
    return {sym: wt[sym] / t for sym in wt}


def wt_to_mol(wt_comp: dict) -> dict:
    mol = {sym: wt_comp[sym] / get(sym).atomic_mass for sym in wt_comp}
    t = sum(mol.values())
    return {sym: mol[sym] / t for sym in mol}


METALLIC_RADIUS_PM = {
    "H":  53,  "Li":167, "Be":112, "B":  87,  "C":  77,  "N":  75,  "O":  73,
    "Na":190,  "Mg":160, "Al":143, "Si":117,  "P": 110,  "S": 104,
    "K": 243,  "Ca":197, "Sc":162, "Ti":147,  "V": 134,  "Cr":128,  "Mn":127,
    "Fe":126,  "Co":125, "Ni":124, "Cu":128,  "Zn":134,  "Ga":135,  "Ge":122,
    "As":120,  "Se":119,
    "Rb":265,  "Sr":215, "Y": 180, "Zr":160,  "Nb":146,  "Mo":139,  "Tc":136,
    "Ru":134,  "Rh":134, "Pd":137, "Ag":144,  "Cd":151,  "In":167,  "Sn":158,
    "Sb":145,  "Te":140,
    "Cs":298,  "Ba":253, "La":195, "Ce":185,  "Pr":185,  "Nd":185,  "Sm":185,
    "Gd":180,  "Tb":175, "Dy":175, "Ho":175,  "Er":175,  "Tm":175,  "Yb":175,
    "Lu":175,  "Hf":156, "Ta":146, "W": 139,  "Re":137,  "Os":135,  "Ir":136,
    "Pt":139,  "Au":144, "Hg":150, "Tl":170,  "Pb":175,  "Bi":155,
    "Th":206,  "U": 196, "Pu":187,
}


_M = {
    ("Fe","Cr"): -1.0,  ("Fe","Ni"): -2.0,  ("Fe","Co"):  1.0,
    ("Fe","Mo"): -2.0,  ("Fe","W"):  -2.0,   ("Fe","V"):  -2.0,
    ("Fe","Ti"): -6.0,  ("Fe","Al"): -9.0,   ("Fe","Si"): -7.0,
    ("Fe","Mn"):  0.0,  ("Fe","Nb"): -4.0,   ("Fe","Cu"): 13.0,
    ("Fe","Zr"): -7.0,  ("Fe","C"):  -5.0,   ("Fe","N"):  -8.0,
    ("Cr","Ni"): -7.0,  ("Cr","Co"): -4.0,   ("Cr","Mo"):  0.0,
    ("Cr","W"):  -1.0,  ("Cr","Al"): -3.0,   ("Cr","Ti"): -4.0,
    ("Cr","V"):  -2.0,  ("Cr","Nb"): -2.0,   ("Cr","Si"): -4.0,
    ("Cr","Mn"):  1.0,  ("Cr","Zr"): -4.0,   ("Cr","Cu"):  8.0,
    ("Ni","Co"):  0.0,  ("Ni","Mo"): -7.0,   ("Ni","W"):  -4.0,
    ("Ni","Al"): -16.0,   ("Ni","Ti"): -35.0,  ("Ni","V"):  -8.0,
    ("Ni","Nb"): -15.0,   ("Ni","Si"): -9.0,   ("Ni","Mn"):  4.0,
    ("Ni","Zr"): -23.0,   ("Ni","Cu"):  4.0,   ("Ni","Cr"): -7.0,
    ("Co","Mo"): -5.0,  ("Co","W"):  -3.0,   ("Co","Al"): -14.0,
    ("Co","Mn"): -5.0,
    ("Co","Ti"): -28.0,   ("Co","V"):  -7.0,   ("Co","Nb"): -13.0,
    ("Co","Si"): -8.0,  ("Co","Zr"): -21.0,   ("Co","Cu"):  6.0,
    ("Mo","W"):   0.0,  ("Mo","Al"): -4.0,   ("Mo","Ti"): -4.0,
    ("Mo","V"):  -1.0,  ("Mo","Nb"):  2.0,   ("Mo","Si"): -2.0,
    ("Mo","Zr"): -8.0,
    ("Ti","Al"): -30.0,   ("Ti","V"):  -2.0,   ("Ti","Nb"): -8.0,
    ("Ti","Si"): -28.0,   ("Ti","Zr"): -0.0,   ("Ti","Cu"): -22.0,
    ("Ti","W"):  -5.0,
    ("Al","Si"):  8.0,  ("Al","Cu"):  1.0,   ("Al","Mg"): -2.0,
    ("Al","Zn"):  6.0,  ("Al","Mn"):  0.0,   ("Al","Zr"): -44.0,
    ("Al","V"):   -9.0, ("Al","Nb"): -22.0,
    ("Zr","Nb"):  0.0,  ("Zr","Mo"): -8.0,  ("Zr","V"):  -8.0,
    ("Nb","V"):   0.0,  ("Nb","W"):   0.0,
    ("Cu","Zn"):  1.0,  ("Cu","Al"):  1.0,   ("Cu","Sn"):  2.0,
    ("Cu","Ni"):  4.0,
    ("Mg","Al"):  2.0,  ("Mg","Zn"):  4.0,   ("Mg","Ca"):  0.0,
}
MIEDEMA = {}
for (a, b), v in _M.items():
    MIEDEMA[(a, b)] = v
    MIEDEMA[(b, a)] = v


def delta_size(comp: dict) -> float:
    c = norm(comp)
    radii = {sym: METALLIC_RADIUS_PM.get(sym, 150.0) for sym in c}
    r_bar = sum(c[sym] * radii[sym] for sym in c)
    if r_bar < 1e-9:
        return 0.0
    return 100.0 * math.sqrt(sum(c[sym] * (1 - radii[sym] / r_bar) ** 2 for sym in c))


def vec(comp: dict) -> float:
    c = norm(comp)
    return sum(c[sym] * get(sym).valence_e for sym in c)


def delta_chi(comp: dict) -> float:
    c = norm(comp)
    vals = {sym: get(sym).electronegativity for sym in c}
    missing = [sym for sym in c if vals[sym] is None]
    if missing:
        return None
    chi_bar = sum(c[sym] * vals[sym] for sym in c)
    return math.sqrt(sum(c[sym] * (vals[sym] - chi_bar) ** 2 for sym in c))


def delta_H_mix(comp: dict) -> Optional[float]:
    c = norm(comp)
    elems = list(c.keys())
    dH = 0.0
    n_pairs = 0
    for i in range(len(elems)):
        for j in range(i + 1, len(elems)):
            a, b = elems[i], elems[j]
            H_ij = MIEDEMA.get((a, b))
            if H_ij is None:
                continue
            dH += 4.0 * c[a] * c[b] * H_ij
            n_pairs += 1
    return dH if n_pairs > 0 else None


def delta_S_mix(comp: dict) -> float:
    c = norm(comp)
    s = 0.0
    for xi in c.values():
        if xi > 1e-12:
            s -= xi * math.log(xi)
    return R * s


def omega_param(comp: dict) -> Optional[float]:
    dH = delta_H_mix(comp)
    if dH is None or abs(dH) < 0.01:
        return None
    Tm_bar = wmean(comp, "Tm")
    if Tm_bar is None:
        return None
    dS = delta_S_mix(comp)
    return Tm_bar * dS / (abs(dH) * 1000.0)


def PREN_wt(comp_mol: dict) -> float:
    wt = mol_to_wt(comp_mol)
    cr = wt.get("Cr", 0) * 100
    mo = wt.get("Mo", 0) * 100
    n  = wt.get("N",  0) * 100
    return cr + 3.3 * mo + 16.0 * n


def pugh_ratio(comp: dict) -> Optional[float]:
    B = wmean(comp, "B")
    G = wmean(comp, "G")
    if B is None or G is None or G < 1e-9:
        return None
    return B / G


def cauchy_pressure(comp: dict) -> Optional[float]:
    B = wmean(comp, "B")
    G = wmean(comp, "G")
    if B is None or G is None:
        return None
    return B - (5.0 / 3.0) * G


def density_rule_of_mixtures(comp: dict) -> Optional[float]:
    wt = mol_to_wt(comp)
    inv_rho = 0.0
    total_w = 0.0
    for sym, wi in wt.items():
        rho_i = get(sym).density
        if rho_i is None or rho_i < 1.0:
            continue
        inv_rho += wi / rho_i
        total_w  += wi
    if total_w < 1e-12 or inv_rho < 1e-12:
        return None
    inv_rho_normalised = inv_rho / total_w
    return 1.0 / inv_rho_normalised


@dataclass
class Check:
    name:      str
    status:    str
    value:     Optional[float]
    unit:      str
    message:   str
    citation:  str
    formula:   str = ""

    @property
    def score(self) -> float:
        return {"PASS": 1.0, "WARN": 0.6, "FAIL": 0.0, "INFO": 1.0}.get(self.status, 0.5)


def PASS(name, value, unit, msg, citation, formula="") -> Check:
    return Check(name, "PASS", value, unit, msg, citation, formula)

def WARN(name, value, unit, msg, citation, formula="") -> Check:
    return Check(name, "WARN", value, unit, msg, citation, formula)

def FAIL(name, value, unit, msg, citation, formula="") -> Check:
    return Check(name, "FAIL", value, unit, msg, citation, formula)

def INFO(name, value, unit, msg, citation, formula="") -> Check:
    return Check(name, "INFO", value, unit, msg, citation, formula)


@dataclass
class DomainResult:
    domain_id:   int
    domain_name: str
    checks:      list = field(default_factory=list)
    error:       Optional[str] = None

    def score(self) -> float:
        if not self.checks:
            return 50.0
        s = sum(c.score for c in self.checks)
        return 100.0 * s / len(self.checks)

    @property
    def n_pass(self): return sum(1 for c in self.checks if c.status == "PASS")
    @property
    def n_warn(self): return sum(1 for c in self.checks if c.status == "WARN")
    @property
    def n_fail(self): return sum(1 for c in self.checks if c.status == "FAIL")

    def one_line(self) -> str:
        if self.error:
            return f"[{self.domain_id:2d}] {self.domain_name:<32} ERROR: {self.error}"
        return (f"[{self.domain_id:2d}] {self.domain_name:<32} "
                f"{self.score():5.1f}/100  "
                f"P:{self.n_pass} W:{self.n_warn} F:{self.n_fail}")
