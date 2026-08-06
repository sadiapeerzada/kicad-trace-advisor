"""
Wraps the pcbnew API to pull out the geometry and net data the analyzer
needs, and to load user-supplied expected-current values per net.

Expected current isn't something KiCad stores natively, so we look for a
sidecar file `<project>.current_map.json` next to the .kicad_pcb, mapping
net name -> expected current in amps, e.g.:

    {
      "+5V": 2.0,
      "+12V_MOTOR": 4.5,
      "GND": 0.0
    }

Nets not present in the map are skipped from the current-capacity check
(there's no safe way to guess expected current from geometry alone), but
are still included in the thermal pass using a conservative default if
the user opts in via `--assume-default-current`.
"""

import json
import os
from dataclasses import dataclass, field

import pcbnew

from .ipc2221 import TraceGeometry


@dataclass
class NetData:
    name: str
    expected_current_a: float
    segments: list = field(default_factory=list)  # list[TraceGeometry]
    layer_names: list = field(default_factory=list)


class BoardReader:
    def __init__(self, board):
        self.board = board

    def _current_map_path(self) -> str:
        board_path = self.board.GetFileName()
        base, _ = os.path.splitext(board_path)
        return base + ".current_map.json"

    def _load_current_map(self) -> dict:
        path = self._current_map_path()
        if not os.path.exists(path):
            return {}
        try:
            with open(path, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return {}

    def read_nets(self) -> dict:
        """Return {net_name: NetData} for every net that has at least one
        copper track, with per-segment geometry attached."""
        current_map = self._load_current_map()
        nets = {}

        for track in self.board.GetTracks():
            if not isinstance(track, pcbnew.PCB_TRACK):
                continue
            # Skip vias -- handled separately if/when we model via thermal
            # contribution; v1 focuses on straight trace segments.
            if isinstance(track, pcbnew.PCB_VIA):
                continue

            net_name = track.GetNetname()
            if not net_name:
                continue

            width_mm = pcbnew.ToMM(track.GetWidth())
            length_mm = pcbnew.ToMM(track.GetLength())
            layer_id = track.GetLayer()
            is_external = layer_id in (pcbnew.F_Cu, pcbnew.B_Cu)

            copper_weight_oz = self._layer_copper_weight_oz(layer_id)

            geom = TraceGeometry(
                width_mm=width_mm,
                length_mm=length_mm,
                copper_weight_oz=copper_weight_oz,
                is_external_layer=is_external,
            )

            if net_name not in nets:
                nets[net_name] = NetData(
                    name=net_name,
                    expected_current_a=current_map.get(net_name, 0.0),
                )
            nets[net_name].segments.append(geom)

            layer_name = self.board.GetLayerName(layer_id)
            if layer_name not in nets[net_name].layer_names:
                nets[net_name].layer_names.append(layer_name)

        return nets

    def _layer_copper_weight_oz(self, layer_id) -> float:
        """Best-effort lookup of copper weight for a layer from the board
        stackup; falls back to 1oz if the stackup isn't set (common in
        quick/default boards)."""
        try:
            stackup = self.board.GetDesignSettings().GetStackupDescriptor()
            for item in stackup.GetList():
                if item.GetBrdLayerId() == layer_id and item.GetThickness() > 0:
                    thickness_mm = pcbnew.ToMM(item.GetThickness())
                    # 1oz copper ~= 0.035mm; scale linearly from that.
                    return round(thickness_mm / 0.035, 2) or 1.0
        except AttributeError:
            pass
        return 1.0

    def has_current_map(self) -> bool:
        return os.path.exists(self._current_map_path())

    def current_map_path(self) -> str:
        return self._current_map_path()
