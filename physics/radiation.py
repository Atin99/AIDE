import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from physics.base import *

ID = 6
NAME = "Radiation Physics"

def run(comp: dict, dpa_rate: float = 1e-6, T_irr_K: float = 723.0, **_) -> DomainResult:
    c = norm(comp)
    checks = []

    xs_avg = 0.0; w_total = 0.0
    for sym, xi in c.items():
        xs_i = getattr(get(sym), "neutron_xs", None)
        if xs_i is not None:
            xs_avg  += xi * xs_i
            w_total += xi
    if w_total < 0.5:
        checks.append(INFO("σ_thermal", None, "barns",
            "Neutron cross-section data not available for all elements",
            "ENDF/B-VIII.0 (Brown et al. 2018) Nucl. Data Sheets 148:1"))
    else:
        xs_avg /= w_total
        if xs_avg < 5:
            checks.append(PASS("σ_thermal (weighted)", xs_avg, "barns",
                f"σ̄ = {xs_avg:.3f} barns — low neutron absorption; good structural material",
                "ENDF/B-VIII.0 (Brown et al. 2018) Nucl. Data Sheets 148:1",
                "σ̄ = Σᵢ cᵢ σᵢ  (ENDF/B-VIII.0 thermal 0.025 eV)"))
        elif xs_avg < 20:
            checks.append(WARN("σ_thermal (weighted)", xs_avg, "barns",
                f"σ̄ = {xs_avg:.2f} barns — moderate neutron absorption",
                "ENDF/B-VIII.0 (Brown et al. 2018)",
                "σ̄ = Σᵢ cᵢ σᵢ"))
        else:
            checks.append(FAIL("σ_thermal (weighted)", xs_avg, "barns",
                f"σ̄ = {xs_avg:.1f} barns — high absorption; unsuitable for in-core structures",
                "ENDF/B-VIII.0 (Brown et al. 2018)",
                "σ̄ = Σᵢ cᵢ σᵢ"))

    radio_elems = [sym for sym, xi in c.items() if xi > 1e-4 and get(sym).radioactive]
    if not radio_elems:
        checks.append(PASS("Radioactive elements", 0, "n",
            "No radioactive elements above 0.01 at%",
            "NUBASE2020 (Kondev et al. 2021) Chin. Phys. C 45:030001"))
    else:
        checks.append(WARN("Radioactive elements", len(radio_elems), "n",
            f"Radioactive: {radio_elems} — ICRP radiation protection required",
            "NUBASE2020 (Kondev et al. 2021); ICRP-103 (2007)"))

    VEC_val = vec(c)
    swell_factor = 0.5 if VEC_val < 6.87 else 2.0
    dpa_per_year = dpa_rate * 3.15e7
    swelling_pct = swell_factor * 0.1 * dpa_per_year ** 0.5
    if swelling_pct < 1.0:
        checks.append(PASS("Void swelling estimate", swelling_pct, "%/yr",
            f"Estimated ΔV/V ≈ {swelling_pct:.2f}%/yr at {dpa_rate:.0e} dpa/s — acceptable",
            "Zinkle & Was (2013) Acta Mater. 61:735",
            "ΔV/V ≈ A·dpa^0.5  (BCC factor 0.5, FCC factor 2.0)"))
    else:
        checks.append(WARN("Void swelling estimate", swelling_pct, "%/yr",
            f"Estimated ΔV/V ≈ {swelling_pct:.2f}%/yr — significant; design around swelling",
            "Zinkle & Was (2013) Acta Mater. 61:735",
            "ΔV/V ≈ A·dpa^0.5"))

    return DomainResult(ID, NAME, checks)
