# Legacy generators (kept, not part of the package)

| file | what it did | why it is here |
|---|---|---|
| `build_skn.py` | wrote the v1.7.0 `skn/` sources from embedded strings | its copies are older than `skn/`; it refuses to overwrite without `--force` |
| `write_readme.py` | replaced README.md with base64 text from stdin | it overwrites the README wholesale; edit the README directly instead |
| `generate_assets.py` | drew `assets/rendezvous_3d.png`, `assets/performance_dashboard.png` and the architecture figure from hard-coded values | those figures are illustrations, not results (see the README's Illustrations section) |

Moved here on 2026-09-27 so the repository root holds only what runs.
