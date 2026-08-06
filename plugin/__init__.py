"""
KiCad Trace Width & Current/Thermal Advisor
---------------------------------------------
Registers the action plugin with pcbnew when KiCad loads this plugin
directory (either from the scripting plugins folder or installed via PCM).
"""

import os

import pcbnew

from .core.board_reader import BoardReader
from .core.analysis import BoardAnalyzer
from .ui.results_dialog import ResultsDialog

PLUGIN_DIR = os.path.dirname(__file__)


class TraceCurrentThermalAdvisor(pcbnew.ActionPlugin):
    """Entry point KiCad calls when the user runs the plugin from the
    Tools > External Plugins menu or the toolbar icon."""

    def defaults(self):
        self.name = "Trace Width && Current/Thermal Advisor"
        self.category = "PCB Design Verification"
        self.description = (
            "Checks trace widths against IPC-2221 current-carrying capacity "
            "and estimates I2R thermal hotspots."
        )
        self.show_toolbar_button = True
        self.icon_file_name = os.path.join(PLUGIN_DIR, "icons", "icon.png")
        self.dark_icon_file_name = os.path.join(PLUGIN_DIR, "icons", "icon_dark.png")

    def Run(self):
        board = pcbnew.GetBoard()
        if board is None:
            pcbnew.wx.MessageBox(
                "No board is currently open.", "Trace Advisor",
            )
            return

        reader = BoardReader(board)
        nets = reader.read_nets()

        analyzer = BoardAnalyzer(board)
        results = analyzer.analyze(nets)

        dialog = ResultsDialog(None, board, results)
        dialog.ShowModal()
        dialog.Destroy()


def register():
    TraceCurrentThermalAdvisor().register()


register()
