# Visual mock-ups (not SKN output)

Everything in this folder is a **look**, not a result. None of these files import the `skn` package.
Their numbers (ΔG, CPU, "threat" tracks, vault hashes, formation bursts) come from `random` or are
hard-coded. They were moved here on 2026-09-27 so they cannot be mistaken for the simulation.

For visuals that show what SKN actually computes:

- `python skn_orbital_tui.py` — the terminal dashboard, now driven by the real code (repository root)
- `python scripts/demo_visual.py` — the demo video in the README

| file | what it is |
|---|---|
| `skn_orbital_tui_mockup.py` | the original orbital terminal dashboard (random nodes, random "threats") |
| `skn_cinematic.py`, `skn_orbital_demo.py` | terminal animations |
| `skn_mission_control.py`, `sovereign_futuristic_demo.py`, `demo_mission_control.py` | matplotlib frame generators (they wrote `frames/`) |
| `skn_mission_control.html` | browser mock-up |
