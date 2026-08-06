"""
I2R-based thermal risk estimation for individual copper segments.

This is deliberately a *local* per-segment heating estimate (power
dissipated per unit trace, P = I^2 * R) rather than a full finite-element
thermal solve across the board, which is out of scope for a v1 plugin.
It is combined with the IPC-2221 width check in analysis.py to produce a
ranked risk score, since a trace can pass the width check by a small
margin while still dissipating meaningfully more power than its
neighbours because of current draw.
"""

from dataclasses import dataclass

try:
    from .ipc2221 import TraceGeometry, resistance_ohms
except ImportError:
    # Allows this module to be imported standalone (e.g. by tests running
    # outside the KiCad plugin package context).
    from ipc2221 import TraceGeometry, resistance_ohms


@dataclass
class ThermalResult:
    power_dissipated_w: float
    estimated_dt_c: float
    risk_score: float  # 0.0 (safe) - 1.0+ (severe)


# Rough thermal resistance per unit trace area, used only to translate
# dissipated power into an approximate local temperature rise for ranking
# purposes. This is a simplification (assumes still air, 1oz-equivalent
# board environment) -- documented clearly as an estimate, not a
# substitute for real thermal simulation.
THERMAL_RESISTANCE_C_PER_W_PER_MM2 = 550.0


def estimate_segment_thermal(
    geom: TraceGeometry,
    current_a: float,
    safe_current_a: float,
) -> ThermalResult:
    r_ohms = resistance_ohms(geom)
    power_w = (current_a ** 2) * r_ohms

    area_mm2 = geom.width_mm * geom.length_mm
    area_mm2 = max(area_mm2, 1e-6)

    estimated_dt = (power_w * THERMAL_RESISTANCE_C_PER_W_PER_MM2) / area_mm2

    # Risk score blends how far over the IPC-2221 safe current this net is
    # with the estimated local temperature rise, so a trace that's only
    # slightly underwidth but carries a lot of current still surfaces near
    # the top of the ranked list.
    current_ratio = current_a / safe_current_a if safe_current_a > 0 else float("inf")
    dt_ratio = estimated_dt / 10.0  # normalized against a 10C rise baseline

    risk_score = max(current_ratio - 1.0, 0.0) * 0.6 + max(dt_ratio - 1.0, 0.0) * 0.4

    return ThermalResult(
        power_dissipated_w=power_w,
        estimated_dt_c=estimated_dt,
        risk_score=risk_score,
    )
