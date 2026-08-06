# KiCad Trace Width & Current/Thermal Advisor

A KiCad 9 action plugin that checks PCB trace widths against **IPC-2221**
current-carrying capacity and estimates **I²R-based thermal risk** across
the board — surfacing undersized/hot traces that KiCad's built-in DRC
doesn't catch, ranked by severity.

Built for the FOSSEE eSim Semester Long Internship (Autumn 2026), Task 6.

## Why

KiCad's DRC checks clearances and connectivity, not whether a trace can
actually carry the current running through it. This plugin closes that
gap without leaving the KiCad workflow.

See [`docs/DESIGN.md`](docs/DESIGN.md) for the full architecture and
design rationale.

## Install

1. Locate your KiCad 9 scripting plugins directory:
   - Linux: `~/.local/share/kicad/9.0/scripting/plugins/`
   - macOS: `~/Documents/KiCad/9.0/scripting/plugins/`
   - Windows: `%APPDATA%\kicad\9.0\scripting\plugins\`
2. Copy (or symlink) the `plugin/` folder from this repo into that
   directory, e.g.:
   ```bash
   cp -r plugin ~/.local/share/kicad/9.0/scripting/plugins/trace-advisor
   ```
3. Open KiCad's PCB Editor and go to **Tools → External Plugins → Refresh
   Plugins** (or restart KiCad).
4. The plugin appears as a toolbar icon and under **Tools → External
   Plugins → Trace Width & Current/Thermal Advisor**.

## Run

1. Open a `.kicad_pcb` file with routed copper.
2. (Optional but recommended) create `<yourboard>.current_map.json` next
   to your `.kicad_pcb`, mapping net names to expected current in amps:
   ```json
   {
     "+5V": 2.0,
     "+12V_MOTOR": 4.5
   }
   ```
   Nets not listed here still show up in results (marked "no spec") but
   aren't risk-scored, since there's no basis to evaluate them.
3. Run the plugin from the toolbar or **Tools → External Plugins**.
4. A results dialog opens, ranked worst-risk-first. Click any row to
   highlight that net's tracks on the PCB canvas.

## Test

The IPC-2221 and thermal math (`plugin/core/ipc2221.py`,
`plugin/core/thermal.py`) has zero dependency on `pcbnew` or `wx`, so it
can be tested in any standard Python environment — you do not need KiCad
installed to run these:

```bash
pip install pytest
python -m pytest tests/ -v
```

12 tests currently pass, covering:
- IPC-2221 formula correctness in both directions (width→current,
  current→width)
- Copper weight and temperature-rise sensitivity
- Resistance temperature-coefficient behavior
- Thermal risk scoring monotonicity (more overcurrent / more heat →
  higher risk score)

`board_reader.py`, `analysis.py`, and `results_dialog.py` depend on
`pcbnew`/`wx` and are exercised by running the plugin inside KiCad 9
directly (see Run, above).

## Project structure

```
plugin/
  __init__.py            # ActionPlugin registration
  metadata.json           # KiCad PCM metadata
  core/
    ipc2221.py             # IPC-2221 math (pure Python, tested)
    thermal.py              # I2R thermal risk model (pure Python, tested)
    board_reader.py          # pcbnew API -> internal data model
    analysis.py               # Combines the two into ranked results
  ui/
    results_dialog.py          # wx results table + board highlighting
tests/
  test_ipc2221.py
  test_thermal.py
docs/
  DESIGN.md               # Full architecture + design rationale
```

## License

MIT
