# Design Document — Trace Width & Current/Thermal Advisor

## 1. Problem

KiCad's built-in Design Rule Check validates clearances, connectivity, and
manufacturing constraints, but does not check whether a trace is wide
enough for the current it will actually carry. Undersized traces are
often only discovered after fabrication, when a board overheats or shows
excessive voltage drop under load. This plugin adds that check directly
into the KiCad 9 workflow, and goes one step further by estimating
relative thermal risk across the board, not just a binary pass/fail per
trace.

## 2. Scope (v1)

In scope:
- IPC-2221 current-carrying capacity check per net, given a user-supplied
  expected current
- Minimum safe trace width calculation (copper weight and temperature
  rise aware)
- I²R-based local power dissipation and approximate temperature rise
  estimate per segment
- A combined risk score ranking nets from most to least concerning
- Results dialog inside KiCad with click-to-highlight on the board

Out of scope for v1 (documented as future work, see §6):
- Full finite-element thermal simulation across the board
- Signal integrity / impedance / crosstalk analysis
- Automatic trace width correction (read-only advisor, does not modify
  the board)
- Via thermal contribution modeling

## 3. Architecture

```
plugin/
  __init__.py          # ActionPlugin registration, entry point (Run())
  metadata.json         # KiCad PCM plugin metadata
  core/
    board_reader.py     # pcbnew API -> internal data model (NetData, TraceGeometry)
    ipc2221.py           # Pure-Python IPC-2221 math (no pcbnew dependency)
    thermal.py           # I2R power/thermal risk estimate (no pcbnew dependency)
    analysis.py          # Combines ipc2221 + thermal into ranked NetFinding list
  ui/
    results_dialog.py    # wx.Dialog showing ranked results, board highlighting
tests/
  test_ipc2221.py         # Unit tests for the math, runnable without KiCad
  test_thermal.py
```

### Why the math is separated from the pcbnew API layer

`ipc2221.py` and `thermal.py` have zero dependency on `pcbnew` or `wx`.
They operate purely on plain dataclasses (`TraceGeometry`) and floats.
This was a deliberate design choice for two reasons:

1. **Testability.** KiCad's Python scripting environment is not trivial
   to unit test against in CI. Keeping the electrical/thermal math
   pcbnew-free means `tests/` runs in any standard Python environment
   with `pytest`, and those tests are what's actually verified in this
   submission (see `tests/` — 12 passing tests covering the IPC-2221
   formula in both directions, copper weight handling, temperature
   effects, and the thermal risk scoring).
2. **Reusability.** The same math could be reused in a CLI tool or CI
   check outside of KiCad's GUI entirely.

`board_reader.py` is the only module that touches `pcbnew` directly, and
`results_dialog.py` is the only module that touches `wx`. This keeps the
KiCad-specific surface area small and isolated.

## 4. Data flow

1. `__init__.py: Run()` is invoked by KiCad's plugin menu.
2. `BoardReader.read_nets()` walks `board.GetTracks()`, groups segments by
   net name, and reads copper weight from the board's stackup descriptor
   (falling back to 1oz if unset).
3. `BoardReader` also loads `<project>.current_map.json`, a sidecar file
   mapping net name → expected current in amps (see §5 for why this is a
   separate file rather than inferred from the schematic).
4. `BoardAnalyzer.analyze()` runs each net's segments through
   `ipc2221.max_current_for_width()` and `min_width_for_current()`, then
   `thermal.estimate_segment_thermal()`, and produces a ranked list of
   `NetFinding` objects sorted by risk score (worst first).
5. `ResultsDialog` renders the ranked list in a `wx.ListCtrl`, color-coding
   undersized nets red and elevated-risk nets amber. Clicking a row
   selects that net's tracks on the PCB canvas via `track.SetSelected()`.

## 5. Design decision: expected current input

KiCad does not store "expected current" as board or schematic metadata.
Three options were considered:

- **Infer from footprint/component power ratings** — unreliable; most
  footprints don't carry this data, and inference would be a guess
  presented as fact.
- **Add a custom schematic field per net** — more integrated, but
  requires the user to edit schematic properties per net rather than a
  single flat file, and complicates the v1 scope significantly.
- **Sidecar JSON file** (chosen) — `<project>.current_map.json` sits next
  to the `.kicad_pcb` file, is human-editable, versionable in git
  alongside the board, and keeps the plugin read-only with respect to the
  board/schematic files themselves.

Nets without an entry in the current map are still listed in the results
(marked "no spec") rather than silently dropped, so the user can see
which nets weren't evaluated and why.

## 6. Future work (post-screening-task)

- Full 2D thermal map overlay rendered directly on the PCB canvas
  (color-graded copper regions), rather than a per-net table
- Signal integrity checks: differential pair length matching, trace
  impedance estimation, crosstalk risk between adjacent parallel traces
- Via current/thermal contribution
- Reading expected current directly from a schematic net class or custom
  field, removing the need for the sidecar file
