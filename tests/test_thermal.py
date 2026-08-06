import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "plugin", "core"))

import ipc2221  # noqa: E402
import thermal  # noqa: E402


def _geom(width_mm=0.3, length_mm=40.0):
    return ipc2221.TraceGeometry(
        width_mm=width_mm,
        length_mm=length_mm,
        copper_weight_oz=1.0,
        is_external_layer=True,
    )


def test_risk_score_zero_when_current_well_within_safe_limit():
    geom = _geom()
    safe_current = ipc2221.max_current_for_width(geom.width_mm, 1.0, True)
    result = thermal.estimate_segment_thermal(
        geom, current_a=safe_current * 0.2, safe_current_a=safe_current
    )
    assert result.risk_score < 0.1


def test_risk_score_rises_when_current_exceeds_safe_limit():
    geom = _geom()
    safe_current = ipc2221.max_current_for_width(geom.width_mm, 1.0, True)
    over_result = thermal.estimate_segment_thermal(
        geom, current_a=safe_current * 1.5, safe_current_a=safe_current
    )
    under_result = thermal.estimate_segment_thermal(
        geom, current_a=safe_current * 0.5, safe_current_a=safe_current
    )
    assert over_result.risk_score > under_result.risk_score


def test_power_dissipated_scales_with_current_squared():
    geom = _geom()
    safe_current = ipc2221.max_current_for_width(geom.width_mm, 1.0, True)
    low = thermal.estimate_segment_thermal(geom, 1.0, safe_current)
    high = thermal.estimate_segment_thermal(geom, 2.0, safe_current)
    # power ~ I^2, so doubling current should ~quadruple dissipated power
    ratio = high.power_dissipated_w / low.power_dissipated_w
    assert 3.5 < ratio < 4.5


def test_longer_trace_dissipates_more_power_same_current():
    short_geom = _geom(length_mm=20.0)
    long_geom = _geom(length_mm=80.0)
    safe_current = ipc2221.max_current_for_width(short_geom.width_mm, 1.0, True)

    short_result = thermal.estimate_segment_thermal(short_geom, 1.5, safe_current)
    long_result = thermal.estimate_segment_thermal(long_geom, 1.5, safe_current)

    assert long_result.power_dissipated_w > short_result.power_dissipated_w
