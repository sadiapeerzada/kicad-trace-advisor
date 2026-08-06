"""
Results dialog shown after the analysis runs. Lists nets ranked by risk
score, and lets the user click a row to select/highlight that net's
tracks on the board so they can jump straight to it.
"""

import wx
import pcbnew


COLUMNS = [
    ("Net", 160),
    ("Expected I (A)", 100),
    ("Safe I (A)", 100),
    ("Min Width (mm)", 110),
    ("Actual Width (mm)", 120),
    ("Est. dT (C)", 90),
    ("Risk", 70),
    ("Status", 100),
]


class ResultsDialog(wx.Dialog):
    def __init__(self, parent, board, findings):
        super().__init__(
            parent,
            title="Trace Width & Current/Thermal Advisor - Results",
            size=(920, 560),
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self.board = board
        self.findings = findings

        self._build_ui()
        self._populate()

    def _build_ui(self):
        panel = wx.Panel(self)
        vbox = wx.BoxSizer(wx.VERTICAL)

        no_spec_count = sum(1 for f in self.findings if not f.has_current_spec)
        header_text = (
            f"{len(self.findings)} nets analyzed. "
            f"{no_spec_count} skipped (no expected current supplied via "
            f"<board>.current_map.json)."
        )
        header = wx.StaticText(panel, label=header_text)
        vbox.Add(header, 0, wx.ALL, 8)

        self.list_ctrl = wx.ListCtrl(
            panel, style=wx.LC_REPORT | wx.BORDER_SUNKEN
        )
        for i, (label, width) in enumerate(COLUMNS):
            self.list_ctrl.InsertColumn(i, label, width=width)
        vbox.Add(self.list_ctrl, 1, wx.EXPAND | wx.ALL, 8)

        self.list_ctrl.Bind(wx.EVT_LIST_ITEM_SELECTED, self._on_row_selected)

        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        close_btn = wx.Button(panel, wx.ID_CLOSE, "Close")
        close_btn.Bind(wx.EVT_BUTTON, lambda evt: self.EndModal(wx.ID_CLOSE))
        btn_sizer.AddStretchSpacer()
        btn_sizer.Add(close_btn, 0, wx.ALL, 8)
        vbox.Add(btn_sizer, 0, wx.EXPAND)

        panel.SetSizer(vbox)

        outer = wx.BoxSizer(wx.VERTICAL)
        outer.Add(panel, 1, wx.EXPAND)
        self.SetSizer(outer)

    def _populate(self):
        for row, finding in enumerate(self.findings):
            self.list_ctrl.InsertItem(row, finding.net_name)

            if not finding.has_current_spec:
                self.list_ctrl.SetItem(row, 1, "-")
                self.list_ctrl.SetItem(row, 2, "-")
                self.list_ctrl.SetItem(row, 3, "-")
                self.list_ctrl.SetItem(row, 4, "-")
                self.list_ctrl.SetItem(row, 5, "-")
                self.list_ctrl.SetItem(row, 6, "-")
                self.list_ctrl.SetItem(row, 7, "no spec")
                continue

            seg = finding.worst_segment
            self.list_ctrl.SetItem(row, 1, f"{finding.expected_current_a:.2f}")
            self.list_ctrl.SetItem(row, 2, f"{seg.safe_current_a:.2f}")
            self.list_ctrl.SetItem(row, 3, f"{seg.min_safe_width_mm:.3f}")
            self.list_ctrl.SetItem(row, 4, f"{seg.width_mm:.3f}")
            self.list_ctrl.SetItem(row, 5, f"{seg.estimated_dt_c:.1f}")
            self.list_ctrl.SetItem(row, 6, f"{finding.overall_risk_score:.2f}")

            status = "UNDERSIZED" if seg.undersized else "OK"
            self.list_ctrl.SetItem(row, 7, status)

            if seg.undersized:
                self.list_ctrl.SetItemBackgroundColour(row, wx.Colour(255, 205, 205))
            elif finding.overall_risk_score > 0.3:
                self.list_ctrl.SetItemBackgroundColour(row, wx.Colour(255, 240, 200))

    def _on_row_selected(self, event):
        row = event.GetIndex()
        net_name = self.list_ctrl.GetItemText(row, 0)
        self._highlight_net(net_name)

    def _highlight_net(self, net_name: str):
        """Select every track belonging to this net so the user can see it
        highlighted on the PCB canvas immediately."""
        for track in self.board.GetTracks():
            if track.GetNetname() == net_name:
                track.SetSelected()
            else:
                track.ClearSelected()
        pcbnew.Refresh()
