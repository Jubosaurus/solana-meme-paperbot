"""Gibt alle Kontowerte (roh und mit Kosten) als JSON aus; fuer den Vorher/Nachher-Vergleich bei Dashboard-Umbauten.

Aufruf: dashboard/.venv/Scripts/python.exe tools/kontowerte_pruefen.py > vorher.json   (ohne git pull dazwischen!)
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "dashboard"))
import rechnung  # noqa: E402

out = {}
for k in rechnung.alle_strategie_konten():
    out["strategie/" + k["key"]] = {"roh": round(k["kontowert"], 9), "mit_kosten": round(rechnung.kontowert_mit_kosten(k), 9)}
for k in rechnung.copy_konten()[0]:
    out["copy/" + k["name"]] = {"kontowert": round(k["kontowert"], 9), "vorsichtig": round(k["vorsichtig"], 9),
                                "ergebnis_seit_start": round(k["ergebnis_seit_start"], 9)}
print(json.dumps(out, indent=1, sort_keys=True))
