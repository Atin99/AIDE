
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from physics.base import *

ID   = 31
NAME = "CALPHAD Stability"

_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         "data")

_FREE_TDBS = [
    ({"Al","Cu","Fe","Mg","Mn","Si","Zn"},
     "COST507.tdb",
     "COST 507 Al-alloy database (Ansara 1998, public domain)"),
    ({"Al","Cu","Fe","Mg","Mn","Si"},
     "COST507.tdb",
     "COST 507 Al-alloy database (subset)"),
    ({"Fe","Cr","C"},
     "FeCrC.tdb",
     "Fe-Cr-C ternary (SGTE/Andersson, public domain)"),
    ({"Fe","Cr"},
     "FeCrC.tdb",
     "Fe-Cr binary (SGTE/Andersson, public domain)"),
]


def _find_tdb(elements: set) -> tuple | None:
    for tdb_elements, fname, desc in _FREE_TDBS:
        if elements.issubset(tdb_elements):
            tdb_path = os.path.join(_DATA_DIR, fname)
            if os.path.exists(tdb_path):
                return tdb_path, desc
    return None


def _pycalphad_available() -> bool:
    try:
        import pycalphad  # noqa: F401
        return True
    except ImportError:
        return False


def run(comp: dict, T_K: float = 298.0, **_) -> DomainResult:
    c = norm(comp)
    checks = []
    elements = set(c.keys())

    if not _pycalphad_available():
        checks.append(INFO("CALPHAD (pycalphad not installed)", None, "",
            "Install with: pip install pycalphad   "
            "CALPHAD check skipped; empirical Miedema/Omega used in Domain 1.",
            "Otis & Liu (2017) J. Open Res. Software 5:1"))
        return DomainResult(ID, NAME, checks)

    tdb_result = _find_tdb(elements)
    if tdb_result is None:
        covered = [str(s) for s, _, _ in _FREE_TDBS]
        checks.append(INFO("CALPHAD (no free TDB for system)", None, "",
            f"No free TDB covers elements: {sorted(elements)}. "
            f"Free databases cover: Al-Cu-Fe-Mg-Mn-Si-Zn and Fe-Cr-C. "
            f"Domain 17 (Phase Stability) provides empirical screening.",
            "Ansara et al. (1998) COST 507 Vol.2; Dinsdale (1991) CALPHAD 15:317"))
        return DomainResult(ID, NAME, checks)

    tdb_path, tdb_desc = tdb_result

    try:
        from pycalphad import Database, equilibrium
        from pycalphad import variables as v
        import numpy as np

        db = Database(tdb_path)

        el_list = sorted(elements)
        dep_el = el_list[-1]
        conds = {v.T: T_K, v.P: 101325}
        for sym in el_list[:-1]:
            conds[v.X(sym)] = c[sym]

        available_phases = list(db.phases.keys())
        target_phases = ["LIQUID", "FCC_A1", "BCC_A2", "SIGMA", "HCP_A3",
                         "LAVES_C14", "MU_PHASE"]
        phases_to_calc = [p for p in target_phases if p in available_phases]
        if not phases_to_calc:
            phases_to_calc = available_phases[:6]

        result = equilibrium(db, el_list, phases_to_calc, conds,
                             output="GM")

        phase_fracs = {}
        for phase in phases_to_calc:
            try:
                nf = float(result.NP.sel(Phase=phase).values.flat[0])
                if not np.isnan(nf) and nf > 0.01:
                    phase_fracs[phase] = round(nf, 4)
            except Exception:
                pass

        phase_str = "  ".join(f"{p}:{v:.0%}" for p, v in
                               sorted(phase_fracs.items(), key=lambda x: -x[1]))
        checks.append(INFO("Equilibrium phases", None, "",
            f"At {T_K:.0f} K: {phase_str or 'single phase'}  |  TDB: {tdb_desc}",
            "Otis & Liu (2017) J. Open Res. Software 5:1",
            "Gibbs energy minimisation via pycalphad"))

        liq_frac = phase_fracs.get("LIQUID", 0.0)
        if liq_frac > 0.05:
            checks.append(FAIL("Liquid fraction", liq_frac * 100, "%",
                f"Liquid = {liq_frac:.0%} at {T_K:.0f} K — partial melting at operating T",
                "Otis & Liu (2017); pycalphad equilibrium calculation",
                "G_liquid < G_solid at T_K -> partial melt"))
        elif liq_frac > 0.001:
            checks.append(WARN("Liquid fraction", liq_frac * 100, "%",
                f"Trace liquid ({liq_frac:.2%}) at {T_K:.0f} K — near solidus",
                "Otis & Liu (2017)"))
        else:
            checks.append(PASS("No liquid at operating T", liq_frac * 100, "%",
                f"Fully solid at {T_K:.0f} K — no solidification concern",
                "Otis & Liu (2017)"))

        sigma_frac = phase_fracs.get("SIGMA", 0.0)
        if sigma_frac > 0.05:
            checks.append(FAIL("Sigma-phase (CALPHAD)", sigma_frac * 100, "%",
                f"CALPHAD predicts {sigma_frac:.0%} sigma at {T_K:.0f} K — "
                f"embrittlement risk confirmed by thermodynamics",
                "Otis & Liu (2017); pycalphad",
                "G_sigma < G_FCC at T_K -> sigma stable"))
        elif sigma_frac > 0.01:
            checks.append(WARN("Sigma-phase (CALPHAD)", sigma_frac * 100, "%",
                f"Trace sigma ({sigma_frac:.2%}) at {T_K:.0f} K — monitor",
                "Otis & Liu (2017)"))
        else:
            checks.append(PASS("No sigma-phase (CALPHAD)", sigma_frac * 100, "%",
                f"CALPHAD: sigma not stable at {T_K:.0f} K",
                "Otis & Liu (2017)"))

    except Exception as e:
        checks.append(INFO("CALPHAD calculation error", None, "",
            f"pycalphad raised: {str(e)[:120]}. "
            f"Domain 17 empirical screening still applies.",
            "Otis & Liu (2017) J. Open Res. Software 5:1"))

    return DomainResult(ID, NAME, checks)
