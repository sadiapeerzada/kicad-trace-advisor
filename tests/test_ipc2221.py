"""
Unit tests for plugin/core/ipc2221.py. These only exercise the pure-math
functions (no pcbnew dependency), so they run in any Python environment,
not just inside KiCad's scripting console.

Run with: python -m pytest tests/ -v
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "plugin", "core"))

import ipc2221  # noqa: E402


def test_external_layer_carries_more_current_than_internal():
    width_mm = 0.5
    ext = ipc2221.max_current_for_width(
        width_mm, copper_weight_oz=1.0, is_external_layer=True
    )
    internal = ipc2221.max_current_for_width(
        width_mm, copper_weight_oz=1.0, is_external_layer=False
    )
    assert ext > internal


def test_wider_trace_carries_more_current():
    narrow = ipc2221.max_current_for_width(0.25, 1.0, True)
    wide = ipc2221.max_current_for_width(1.0, 1.0, True)
    assert wide > narrow


def test_min_width_roundtrips_with_max_current():
    # If we compute the min width for a target current, that width should
    # (approximately) support at least that current.
    target_current = 2.0
    width = ipc2221.min_width_for_current(
        target_current, copper_weight_oz=1.0, is_external_layer=True
    )
    recovered_current = ipc2221.max_current_for_width(
        width, copper_weight_oz=1.0, is_external_layer=True
    )
    assert abs(recovered_current - target_current) < 0.05


def test_heavier_copper_needs_less_width_for_same_current():
    target_current = 3.0
    width_1oz = ipc2221.min_width_for_current(target_current, 1.0, True)
    width_2oz = ipc2221.min_width_for_current(target_current, 2.0, True)
    assert width_2oz < width_1oz


def test_higher_temp_rise_allows_narrower_trace():
    target_current = 2.0
    width_10c = ipc2221.min_width_for_current(target_current, 1.0, True, temp_rise_c=10.0)
    width_20c = ipc2221.min_width_for_current(target_current, 1.0, True, temp_rise_c=20.0)
    assert width_20c < width_10c


def test_resistance_increases_with_temperature():
    geom_low = ipc2221.TraceGeometry(
        width_mm=0.3, length_mm=50.0, copper_weight_oz=1.0, is_external_layer=True
    )
    r_25 = ipc2221.resistance_ohms(geom_low, temperature_c=25.0)
    r_85 = ipc2221.resistance_ohms(geom_low, temperature_c=85.0)
    assert r_85 > r_25


def test_zero_current_gives_zero_width():
    assert ipc2221.min_width_for_current(0.0, 1.0, True) == 0.0


def test_unusual_copper_weight_falls_back_to_nearest():
    # 1.5oz isn't a standard table entry; should not raise, should fall
    # back to the nearest defined weight rather than crashing.
    result = ipc2221.max_current_for_width(0.5, copper_weight_oz=1.5, is_external_layer=True)
    assert result > 0
