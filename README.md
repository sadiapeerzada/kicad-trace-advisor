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

## Verified working (KiCad 10, macOS)

This plugin was originally targeted at KiCad 9's `pcbnew` API, but has been
installed and manually tested end-to-end against a live **KiCad 10.0**
install on macOS, using a real `.kicad_pcb` project:

1. Plugin loads via **Tools → External Plugins** with no import errors
2. Reading an empty board correctly reports 0 nets analyzed
3. A 0.2mm test trace assigned to net `TEST_NET`, with a
   `current_map.json` specifying 2.0 A expected current, was correctly
   flagged **UNDERSIZED** — plugin computed a safe current of 0.75 A for
   that width, a minimum safe width of 0.769 mm, an estimated temperature
   rise of 26.5°C, and a risk score of 1.65
4. Clicking the flagged row in the results dialog correctly selected the
   underlying trace segments on the PCB canvas (confirmed via KiCad's own
   Properties panel showing "9 objects selected", net = TEST_NET)

Screenshots of this test run:
- [`docs/screenshots/ss_1.png`](docs/screenshots/ss_1.png) — results table showing the flagged UNDERSIZED net
- [`docs/screenshots/ss_2.png`](docs/screenshots/ss_2.png) — click-to-highlight selecting the trace on the board

The pure-math layer (`ipc2221.py`, `thermal.py`) is additionally covered
by the 12 automated unit tests described above.

## Project structure
plugin/
init.py # ActionPlugin registration
metadata.json # KiCad PCM metadata
core/
ipc2221.py # IPC-2221 math (pure Python, tested)
thermal.py # I2R thermal risk model (pure Python, tested)
board_reader.py # pcbnew API -> internal data model
analysis.py # Combines the two into ranked results
ui/
results_dialog.py # wx results table + board highlighting
tests/
test_ipc2221.py
test_thermal.py
docs/
DESIGN.md # Full architecture + design rationale
screenshots/ # Verified test run evidence (KiCad 10, macOS)


## License

MIT
