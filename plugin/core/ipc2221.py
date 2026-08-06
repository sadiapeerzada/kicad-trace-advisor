"""
IPC-2221 trace width / current-carrying capacity math.

Implements the standard empirical formula used across IPC-2221 (and the
IPC-2152-style refinements most PCB tools reference) for relating trace
cross-sectional area to current-carrying capacity given an allowed
temperature rise above ambient.

    I = k * (dT ** 0.44) * (A ** 0.725)

Where:
    I  = current in amps
    dT = temperature rise in deg C above ambient
    A  = cross-sectional area of the trace in mils^2
    k  = 0.024 for internal layers, 0.048 for external layers

This module solves the formula in both directions:
    - max_current_for_width(): given a trace width, what current can it
      safely carry
    - min_width_for_current(): given a required current, what is the
      minimum safe trace width

All internal geometry is handled in mils (thousandths of an inch), which
is the convention IPC-2221 tables and most PCB tools use, then converted
to/from KiCad's internal units (nanometers) at the boundary.
"""

from dataclasses import dataclass

# Standard copper weights in oz/ft^2 -> thickness in mils
COPPER_WEIGHT_TO_THICKNESS_MILS = {
    0.5: 0.7,
    1.0: 1.4,
    2.0: 2.8,
    3.0: 4.2,
}

K_EXTERNAL_LAYER = 0.048
K_INTERNAL_LAYER = 0.024

MM_TO_MILS = 1000.0 / 25.4
NM_TO_MM = 1e-6


@dataclass
class TraceGeometry:
    width_mm: float
    length_mm: float
    copper_weight_oz: float
    is_external_layer: bool


def _thickness_mils(copper_weight_oz: float) -> float:
    """Interpolate/clamp to the nearest standard copper weight if an exact
    match isn't found, rather than failing on unusual stackups."""
    if copper_weight_oz in COPPER_WEIGHT_TO_THICKNESS_MILS:
        return COPPER_WEIGHT_TO_THICKNESS_MILS[copper_weight_oz]
    nearest = min(
        COPPER_WEIGHT_TO_THICKNESS_MILS,
        key=lambda w: abs(w - copper_weight_oz),
    )
    return COPPER_WEIGHT_TO_THICKNESS_MILS[nearest]


def max_current_for_width(
    width_mm: float,
    copper_weight_oz: float,
    is_external_layer: bool,
    temp_rise_c: float = 10.0,
) -> float:
    """Return the max current (A) this trace width can carry for the given
    allowed temperature rise."""
    width_mils = width_mm * MM_TO_MILS
    thickness_mils = _thickness_mils(copper_weight_oz)
    area_mils2 = width_mils * thickness_mils

    k = K_EXTERNAL_LAYER if is_external_layer else K_INTERNAL_LAYER
    return k * (temp_rise_c ** 0.44) * (area_mils2 ** 0.725)


def min_width_for_current(
    current_a: float,
    copper_weight_oz: float,
    is_external_layer: bool,
    temp_rise_c: float = 10.0,
) -> float:
    """Return the minimum trace width (mm) required to carry current_a
    without exceeding temp_rise_c above ambient."""
    if current_a <= 0:
        return 0.0

    k = K_EXTERNAL_LAYER if is_external_layer else K_INTERNAL_LAYER
    thickness_mils = _thickness_mils(copper_weight_oz)

    # Solve I = k * dT^0.44 * A^0.725  for A, then A = width * thickness
    area_mils2 = (current_a / (k * (temp_rise_c ** 0.44))) ** (1.0 / 0.725)
    width_mils = area_mils2 / thickness_mils
    return width_mils / MM_TO_MILS


def resistance_ohms(geom: TraceGeometry, temperature_c: float = 25.0) -> float:
    """Approximate DC resistance of a copper trace, temperature-corrected.

    Uses copper resistivity at 20C (1.68e-8 ohm*m) with the standard
    copper temperature coefficient (0.00393 /C) applied for temperature_c.
    """
    rho_20c = 1.68e-8  # ohm * meter
    alpha_cu = 0.00393  # per degree C

    rho_t = rho_20c * (1 + alpha_cu * (temperature_c - 20.0))

    thickness_mils = _thickness_mils(geom.copper_weight_oz)
    thickness_m = thickness_mils * 25.4e-6

    width_m = geom.width_mm / 1000.0
    length_m = geom.length_mm / 1000.0

    cross_section_m2 = width_m * thickness_m
    if cross_section_m2 <= 0:
        return float("inf")

    return rho_t * length_m / cross_section_m2
