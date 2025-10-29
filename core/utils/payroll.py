from __future__ import annotations

from dataclasses import dataclass


@dataclass
class WageParams:
    hourly_brutto: float
    vac_pct: float
    holiday_pct: float
    thirteenth_pct: float
    expenses_per_hour: float
    ahv_pct: float
    nbu_pct: float
    ktg_pct: float


def _round2(x: float) -> float:
    return round(float(x or 0.0) + 1e-9, 2)


def compute_effective_hourly(params: WageParams) -> tuple[float, float]:
    """Return (effective_gross_per_hour, effective_net_per_hour).
    Assumptions (CH payroll, simplified):
      - Gross effective per hour = base + shares for vacation/holidays/13th + expenses_per_hour.
      - Social contributions (AHV+NBU+KTG) are applied to the *wage part* (base + shares), not to expenses.
      - Net per hour = (wage_part * (1 - sum_pct/100)) + expenses_per_hour.
    """
    base = float(params.hourly_brutto or 0.0)
    vac = base * (params.vac_pct or 0.0) / 100.0
    hol = base * (params.holiday_pct or 0.0) / 100.0
    th13 = base * (params.thirteenth_pct or 0.0) / 100.0
    wage_part = base + vac + hol + th13
    gross = wage_part + float(params.expenses_per_hour or 0.0)
    total_pct = (params.ahv_pct or 0.0) + (params.nbu_pct or 0.0) + (params.ktg_pct or 0.0)
    net = (wage_part * (1.0 - total_pct / 100.0)) + float(params.expenses_per_hour or 0.0)
    return _round2(gross), _round2(net)
