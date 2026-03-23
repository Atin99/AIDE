
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from physics.base import *

ID   = 33
NAME = "Transformation Kinetics"

VALID_PROCESSES = {"annealed", "cold_worked", "quenched", "aged", "normalised"}

PROCESS_YS_MULT = {
    "annealed":    1.0,
    "normalised":  1.1,
    "cold_worked": 1.8,
    "quenched":    1.0,
    "aged":        1.8,
}


def _ms_temperature(wt: dict) -> float | None:
    fe_wt = wt.get("Fe", 0)
    if fe_wt < 0.40:
        return None

    def wp(sym): return wt.get(sym, 0.0) * 100.0

    Ms = (539
          - 423  * wp("C")
          - 30.4 * wp("Mn")
          - 17.7 * wp("Ni")
          - 12.1 * wp("Cr")
          - 7.5  * wp("Mo"))
    return Ms


def _md30_temperature(wt: dict) -> float | None:
    fe_wt = wt.get("Fe", 0)
    cr_wt = wt.get("Cr", 0)
    if fe_wt < 0.40 or cr_wt < 0.10:
        return None

    def wp(sym): return wt.get(sym, 0.0) * 100.0

    Md30 = (413
            - 462  * (wp("C") + wp("N"))
            - 9.2  * wp("Si")
            - 8.1  * wp("Mn")
            - 13.7 * wp("Cr")
            - 9.5  * wp("Ni")
            - 18.5 * wp("Mo"))
    return Md30


def _sigma_nose_temp(wt: dict) -> float | None:
    cr_wt_pct = wt.get("Cr", 0) * 100
    if cr_wt_pct < 12:
        return None
    return 650 + 2.5 * (cr_wt_pct - 12)


def run(comp: dict, process: str = "annealed", T_K: float = 298.0, **_) -> DomainResult:
    c = norm(comp)
    checks = []
    wt = mol_to_wt(c)

    proc = (process or "annealed").lower().strip()
    if proc not in VALID_PROCESSES:
        proc = "annealed"
        checks.append(INFO("Process state", None, "",
            f"Unknown process '{process}'; defaulting to 'annealed'. "
            f"Valid: {sorted(VALID_PROCESSES)}",
            "Ashby & Jones (2012) Engineering Materials 1 4th ed."))

    fe_wt = wt.get("Fe", 0)
    ni_wt = wt.get("Ni", 0)
    ti_wt = wt.get("Ti", 0)

    mult = PROCESS_YS_MULT[proc]
    checks.append(INFO("Processing state", None, "",
        f"Process = {proc}. Yield strength multiplier: ~{mult:.1f}x annealed baseline. "
        f"(qualitative band — exact value depends on strain history and alloy)",
        "Ashby & Jones (2012) Engineering Materials 1 4th ed. Ch.8"))

    if fe_wt >= 0.40:
        Ms = _ms_temperature(wt)

        if Ms is not None:
            if proc == "quenched":
                if Ms > 25.0:
                    checks.append(WARN("Ms temperature (Andrews 1965)", Ms, "degC",
                        f"Ms = {Ms:.0f} degC > 25 — martensite WILL form on quenching. "
                        f"High hardness and reduced ductility. May need tempering.",
                        "Andrews (1965) J. Iron Steel Inst. 203:721",
                        "Ms = 539 - 423*%C - 30.4*%Mn - 17.7*%Ni - 12.1*%Cr - 7.5*%Mo"))
                elif Ms > -50.0:
                    checks.append(PASS("Ms temperature (Andrews 1965)", Ms, "degC",
                        f"Ms = {Ms:.0f} degC — martensite forms partially or not at room T. "
                        f"Austenite likely retained. Check Md30 for cold-work sensitivity.",
                        "Andrews (1965) J. Iron Steel Inst. 203:721",
                        "Ms = 539 - 423*%C - 30.4*%Mn - 17.7*%Ni - 12.1*%Cr - 7.5*%Mo"))
                else:
                    checks.append(PASS("Ms temperature (Andrews 1965)", Ms, "degC",
                        f"Ms = {Ms:.0f} degC << 25 — fully austenitic on quenching. Stable.",
                        "Andrews (1965) J. Iron Steel Inst. 203:721",
                        "Ms = 539 - 423*%C - 30.4*%Mn - 17.7*%Ni - 12.1*%Cr - 7.5*%Mo"))
            else:
                checks.append(INFO("Ms temperature (Andrews 1965)", Ms, "degC",
                    f"Ms = {Ms:.0f} degC "
                    f"({'martensitic on quench' if Ms > 25 else 'austenite stable to room T'}). "
                    f"Use --process quenched to evaluate quench response.",
                    "Andrews (1965) J. Iron Steel Inst. 203:721",
                    "Ms = 539 - 423*%C - 30.4*%Mn - 17.7*%Ni - 12.1*%Cr - 7.5*%Mo"))

        Md30 = _md30_temperature(wt)
        if Md30 is not None and proc == "cold_worked":
            T_C = T_K - 273.15
            if Md30 > T_C:
                checks.append(WARN("Md30 (Nohara 1977) — cold work martensite", Md30, "degC",
                    f"Md30 = {Md30:.0f} degC > operating T ({T_C:.0f} degC). "
                    f"30% cold strain will induce ~50% martensite (TRIP effect). "
                    f"Verify ductility for cold-forming operations.",
                    "Nohara et al. (1977) J. Iron Steel Inst. Japan 63:772",
                    "Md30 = 413 - 462*(%C+%N) - 9.2*%Si - 8.1*%Mn - 13.7*%Cr - 9.5*%Ni - 18.5*%Mo"))
            else:
                checks.append(PASS("Md30 (Nohara 1977) — austenite stable to cold work",
                    Md30, "degC",
                    f"Md30 = {Md30:.0f} degC < operating T. "
                    f"Austenite stable against cold-work-induced martensite.",
                    "Nohara et al. (1977) J. Iron Steel Inst. Japan 63:772",
                    "Md30 = 413 - 462*(%C+%N) - ..."))

        T_sig = _sigma_nose_temp(wt)
        if T_sig is not None:
            T_op_C = T_K - 273.15
            if 600 < T_op_C < 950:
                checks.append(WARN("Sigma-phase kinetics window", T_sig, "degC",
                    f"Operating T ({T_op_C:.0f} degC) is within sigma-phase formation window "
                    f"(600-950 degC). Sigma nose ~{T_sig:.0f} degC. "
                    f"Limit exposure time at this temperature.",
                    "Lippold & Kotecki (2005) Welding Metallurgy and Weldability of SS Ch.3",
                    "T_sigma_nose ~ 650 + 2.5*(Cr_wt% - 12)"))
            else:
                checks.append(PASS("Sigma-phase kinetics (T out of window)", T_sig, "degC",
                    f"Operating T ({T_op_C:.0f} degC) outside sigma-formation window (600-950 degC). "
                    f"Sigma kinetics negligible.",
                    "Lippold & Kotecki (2005) Welding Metallurgy and Weldability of SS Ch.3",
                    "T_sigma_nose ~ 650 + 2.5*(Cr_wt% - 12)"))

    elif ni_wt >= 0.40 or ti_wt >= 0.20:
        al_wt = wt.get("Al", 0)
        nb_wt = wt.get("Nb", 0)
        if proc == "aged":
            if ni_wt >= 0.40 and (al_wt + ti_wt + nb_wt) > 0.05:
                checks.append(PASS("Precipitation hardening (aged)", None, "",
                    f"Ni-base alloy with Al+Ti+Nb = {(al_wt+ti_wt+nb_wt)*100:.1f} wt%. "
                    f"gamma-prime (Ni3Al/Ni3Ti) or gamma-double-prime (Ni3Nb) "
                    f"precipitation expected. Significant strengthening.",
                    "Sims et al. (1987) Superalloys II, Wiley",
                    "gamma-prime: Ni3(Al,Ti); gamma-double-prime: Ni3Nb"))
            else:
                checks.append(INFO("Precipitation hardening", None, "",
                    f"Aged state specified but Al+Ti+Nb content low "
                    f"({(al_wt+ti_wt+nb_wt)*100:.1f} wt%). Limited precipitation expected.",
                    "Sims et al. (1987) Superalloys II, Wiley"))
        else:
            checks.append(INFO("Precipitation hardening potential", None, "",
                f"Al+Ti+Nb = {(al_wt+ti_wt+nb_wt)*100:.1f} wt%. "
                f"Use --process aged to evaluate precipitation strengthening.",
                "Sims et al. (1987) Superalloys II, Wiley"))

    else:
        checks.append(INFO("Transformation kinetics", None, "",
            "Domain 33 has limited coverage for this alloy system. "
            "Fe > 40 wt% required for Andrews Ms; Ni > 40 wt% for gamma-prime check.",
            "Andrews (1965) J. Iron Steel Inst. 203:721"))

    return DomainResult(ID, NAME, checks)
