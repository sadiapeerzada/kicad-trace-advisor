"""
Ties together the IPC-2221 width check and the I2R thermal estimate into
a single ranked report per net, which the UI layer then displays.
"""

from dataclasses import dataclass, field

from .ipc2221 import TraceGeometry, max_current_for_width, min_width_for_current
from .thermal import estimate_segment_thermal

DEFAULT_TEMP_RISE_C = 10.0


@dataclass
class SegmentFinding:
    width_mm: float
    length_mm: float
    layer: str
    safe_current_a: float
    min_safe_width_mm: float
    power_dissipated_w: float
    estimated_dt_c: float
    risk_score: float
    undersized: bool


@dataclass
class NetFinding:
    net_name: str
    expected_current_a: float
    has_current_spec: bool
    worst_segment: SegmentFinding = None
    segment_findings: list = field(default_factory=list)
    overall_risk_score: float = 0.0


class BoardAnalyzer:
    def __init__(self, board, temp_rise_c: float = DEFAULT_TEMP_RISE_C):
        self.board = board
        self.temp_rise_c = temp_rise_c

    def analyze(self, nets: dict) -> list:
        """nets: {net_name: NetData} from BoardReader.read_nets()
        Returns a list[NetFinding] sorted worst-risk first."""
        findings = []

        for net_name, net_data in nets.items():
            has_spec = net_data.expected_current_a > 0
            net_finding = NetFinding(
                net_name=net_name,
                expected_current_a=net_data.expected_current_a,
                has_current_spec=has_spec,
            )

            if not has_spec:
                # No user-supplied current spec: still record the net so
                # it's visible in the UI, but skip risk scoring since we
                # have no basis to flag it.
                findings.append(net_finding)
                continue

            for geom in net_data.segments:
                safe_current = max_current_for_width(
                    width_mm=geom.width_mm,
                    copper_weight_oz=geom.copper_weight_oz,
                    is_external_layer=geom.is_external_layer,
                    temp_rise_c=self.temp_rise_c,
                )
                min_width = min_width_for_current(
                    current_a=net_data.expected_current_a,
                    copper_weight_oz=geom.copper_weight_oz,
                    is_external_layer=geom.is_external_layer,
                    temp_rise_c=self.temp_rise_c,
                )

                thermal = estimate_segment_thermal(
                    geom=geom,
                    current_a=net_data.expected_current_a,
                    safe_current_a=safe_current,
                )

                seg_finding = SegmentFinding(
                    width_mm=geom.width_mm,
                    length_mm=geom.length_mm,
                    layer="external" if geom.is_external_layer else "internal",
                    safe_current_a=safe_current,
                    min_safe_width_mm=min_width,
                    power_dissipated_w=thermal.power_dissipated_w,
                    estimated_dt_c=thermal.estimated_dt_c,
                    risk_score=thermal.risk_score,
                    undersized=net_data.expected_current_a > safe_current,
                )
                net_finding.segment_findings.append(seg_finding)

            if net_finding.segment_findings:
                net_finding.worst_segment = max(
                    net_finding.segment_findings, key=lambda s: s.risk_score
                )
                net_finding.overall_risk_score = net_finding.worst_segment.risk_score

            findings.append(net_finding)

        # Worst risk first; nets without a current spec sort to the bottom.
        findings.sort(key=lambda f: f.overall_risk_score, reverse=True)
        return findings
