"""requirements.txt: feste Versionen, damit ein neues Paket-Release nicht beim
naechsten Schichtstart alle Bots bricht (Pruefbericht 03.10.)."""
import pathlib
import re

REQ = pathlib.Path(__file__).resolve().parent.parent / "requirements.txt"


def test_alle_pakete_mit_fester_version():
    zeilen = [z.strip() for z in REQ.read_text(encoding="utf-8").splitlines()
              if z.strip() and not z.strip().startswith("#")]
    assert zeilen, "requirements.txt ist leer"
    for z in zeilen:
        assert re.fullmatch(r"[A-Za-z0-9_.\-]+==[0-9][0-9A-Za-z.\-]*", z), f"keine feste Version: {z}"


def test_benoetigte_pakete_vorhanden():
    namen = {z.split("==")[0].lower() for z in REQ.read_text(encoding="utf-8").splitlines() if "==" in z}
    assert {"requests", "websocket-client"} <= namen
