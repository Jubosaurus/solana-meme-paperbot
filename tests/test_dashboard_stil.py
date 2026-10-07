"""Logo-Verweise, vorhandene Static-Dateien und PNG-Einbindung pruefen."""
import ast
import base64
import json
import os
import re
import struct
import sys
import tomllib
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
DASHBOARD = REPO / "dashboard"
STATIC = DASHBOARD / "static"
sys.path.insert(0, str(DASHBOARD))


def test_keine_veralteten_logo_verweise_und_static_dateien_vorhanden():
    # Namen zusammensetzen, damit die Pruefung selbst keinen alten Verweis enthaelt.
    alt = ("nexus-core-" + "logo.svg", "nexus-core-" + "marke.svg", "nexus_" + "logo_bauen.py")
    # Daten, lokale Umgebungen und private Konfigurationen werden nicht gelesen.
    auslassen = {".git", ".venv", ".claude", ".codex", ".aws", ".github", "__pycache__",
                 ".pytest_cache", "node_modules", "copy", "scout", "experimente", "verlauf", "flugschreiber"}
    for ordner, unterordner, dateien in os.walk(REPO):
        unterordner[:] = [n for n in unterordner if n not in auslassen]
        for name in dateien:
            pfad = Path(ordner) / name
            if pfad.suffix not in {".py", ".md", ".html", ".css", ".toml", ".webmanifest", ".svg"}:
                continue
            text = pfad.read_text(encoding="utf-8")
            assert not any(n in text for n in alt), str(pfad.relative_to(REPO))
    assert not (STATIC / alt[0]).exists() and not (STATIC / alt[1]).exists()
    assert not (REPO / "tools" / alt[2]).exists()

    quelle = (DASHBOARD / "stil.py").read_text(encoding="utf-8")
    referenzen = {k.right.value for k in ast.walk(ast.parse(quelle))
                  if isinstance(k, ast.BinOp) and isinstance(k.op, ast.Div)
                  and isinstance(k.left, ast.Name) and k.left.id == "STATIC"
                  and isinstance(k.right, ast.Constant) and isinstance(k.right.value, str)}
    assert {"nexus-core-logo-text.png", "nexus-core-bildzeichen.png", "favicon.png"} <= referenzen
    manifest = json.loads((STATIC / "manifest.webmanifest").read_text(encoding="utf-8"))
    assert manifest["background_color"] == manifest["theme_color"] == "#080B11"
    assert {i["src"] for i in manifest["icons"]} == {"icon-192.png", "icon-512.png"}
    for icon in manifest["icons"]:
        referenzen.add(icon["src"])
        with (STATIC / icon["src"]).open("rb") as f:
            kopf = f.read(24)
        assert kopf[:8] == b"\x89PNG\r\n\x1a\n"
        breite, hoehe = struct.unpack(">II", kopf[16:24])
        assert icon["sizes"] == f"{breite}x{hoehe}"
        assert icon["type"] == "image/png"
    # Auch die dokumentierten Logo-/App-Bilder und konfigurierten Schriften pruefen.
    referenzen.update(re.findall(r"`([^`/]+\.png)`", (DASHBOARD / "DESIGN.md").read_text(encoding="utf-8")))
    config = tomllib.loads((DASHBOARD / ".streamlit/config.toml").read_text(encoding="utf-8"))
    referenzen.update(font["url"].removeprefix("app/static/") for font in config["theme"]["fontFaces"])
    for name in referenzen:
        assert (STATIC / name).is_file(), name


def test_logo_favicon_und_fussmarke_verwenden_png(monkeypatch):
    pytest.importorskip("streamlit")
    import stil

    logos, config = [], []
    monkeypatch.setattr(stil.st, "logo", lambda *args, **kw: logos.append((args, kw)))
    monkeypatch.setattr(stil.st, "set_page_config", lambda **kw: config.append(kw))
    stil.logo_einbinden()
    stil.seite_einrichten()
    assert logos == [((str(STATIC / "nexus-core-logo-text.png"),),
                      {"icon_image": str(STATIC / "nexus-core-bildzeichen.png"), "size": "large"})]
    assert config[0]["page_icon"] == str(STATIC / "favicon.png")
    typ, inhalt = stil.marke_uri().split(",", 1)
    assert typ == "data:image/png;base64"
    assert base64.b64decode(inhalt) == (STATIC / "nexus-core-bildzeichen-klein.png").read_bytes()
