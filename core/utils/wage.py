from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


@dataclass
class WageInput:
    hourly_brutto: float = 0.0
    vac_pct: float = 0.0
    holiday_pct: float = 0.0
    thirteenth_pct: float = 0.0
    expenses_per_hour: float = 0.0
    ahv_pct: float = 0.0
    nbu_pct: float = 0.0
    ktg_pct: float = 0.0
    bvg_pct: float = 0.0
    lgav_fixed_monthly: float = 0.0
    weekly_hours: float = 41.0


def _round2(x: float) -> float:
    return round(float(x or 0.0) + 1e-9, 2)


def compute_effective(w: WageInput) -> Dict[str, float]:
    """Compute effective gross and net, hourly and monthly (100% workload).
    Assumptions:
    - Effective hourly gross includes base + percentage allowances (vac, holiday, 13th).
    - Expenses are shown separately (not in gross), but added to net_effective_with_expenses.
    - Deductions AHV/NBU/KTG/BVG are applied on effective gross (hourly).
    - LGAV is a fixed monthly deduction; converted to hourly using monthly hours.
    """
    # percentages to factors
    add_pct = (w.vac_pct + w.holiday_pct + w.thirteenth_pct) / 100.0
    ded_pct = (w.ahv_pct + w.nbu_pct + w.ktg_pct + w.bvg_pct) / 100.0

    hourly_gross = w.hourly_brutto * (1.0 + add_pct)
    # monthly hours based on 52 weeks / 12 months
    monthly_hours = w.weekly_hours * (52.0 / 12.0)

    # hourly share of LGAV
    lgav_hourly = (w.lgav_fixed_monthly / monthly_hours) if monthly_hours > 0 else 0.0

    # hourly net (excl. expenses): subtract pct deductions on gross + lgav hourly
    hourly_net = hourly_gross * (1.0 - ded_pct) - lgav_hourly
    # hourly net including expenses (informative)
    hourly_net_with_expenses = hourly_net + w.expenses_per_hour

    monthly_gross = hourly_gross * monthly_hours
    monthly_net = hourly_net * monthly_hours
    monthly_net_with_expenses = (hourly_net_with_expenses) * monthly_hours

    return {
        "hourly_gross": _round2(hourly_gross),
        "hourly_net": _round2(hourly_net),
        "hourly_net_with_expenses": _round2(hourly_net_with_expenses),
        "monthly_hours": _round2(monthly_hours),
        "monthly_gross": _round2(monthly_gross),
        "monthly_net": _round2(monthly_net),
        "monthly_net_with_expenses": _round2(monthly_net_with_expenses),
        "lgav_hourly": _round2(lgav_hourly),
    }
