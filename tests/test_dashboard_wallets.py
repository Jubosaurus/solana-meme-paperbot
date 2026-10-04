"""Dashboard-Seite 'Wallets pruefen' (dashboard/wallets.py): Adresspruefung, Duplikate und: nur scout/pruefen.txt
wird geschrieben und committet (echtes Git mit lokalem Remote)."""
import csv
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "dashboard"))
import wallets as w  # noqa: E402

A1 = "9yYya3F5EJoLnBNKW6z4bZvyQytMXzDcpU5D6yYr4jqL"
A2 = "6ANGS6SSCxkv6hV3iymHHMESqDz7EFaecCwHA8qTswpr"
A3 = "HEBov96RdNZC7vrH9taLXwJ3b7MTHBemSee8nuvwDz3P"
A4 = "AtqZAYh4aKM3c4ay5L4ZE9WQvCi9hE3k65WbcWidr37D"
NIX = (set(), set())


def grund_von(abgelehnt, teil):
    return any(teil in g for _, g in abgelehnt)


# ---------------------------------------------------------------- Adresspruefung
def test_gueltige_adresse_mit_und_ohne_name():
    ok, nein = w.eingabe_pruefen(f"Hallo: {A1}\n{A2}\n\n# Kommentar", bekannt=NIX)
    assert ok == [("Hallo", A1), (w.kurzname(A2), A2)] and nein == []


@pytest.mark.parametrize("text", [
    "abc", "0" + A1[1:], A1[:-1] + "l", A1[:20], A1 + "xyz", "https://solscan.io/account/" + A1, A1[:31], "1" * 31,
])
def test_ungueltige_adresse_wird_abgelehnt(text):
    ok, nein = w.eingabe_pruefen(text, bekannt=NIX)
    assert ok == [] and len(nein) == 1 and grund_von(nein, "Keine gültige")


def test_base58_muss_32_byte_ergeben():
    assert not w.ist_solana_adresse("z" * 44)         # 44 Zeichen, aber mehr als 32 Byte
    assert w.ist_solana_adresse(A1) and w.ist_solana_adresse("1" * 32)


def test_name_der_wie_adresse_aussieht_wird_abgelehnt():
    ok, nein = w.eingabe_pruefen(f"{A1}: {A2}", bekannt=NIX)
    assert ok == [] and grund_von(nein, "Name")


def test_duplikate_in_eingabe_und_listen():
    ok, nein = w.eingabe_pruefen(f"{A1}\nZwei: {A1}\n{A2}\n{A3}\n{A4}", bekannt=({A2}, {A3}))
    assert [a for _, a in ok] == [A1, A4]
    assert grund_von(nein, "Doppelt") and grund_von(nein, "copy_wallets") and grund_von(nein, "Prüfliste")


def test_bekannt_liest_auch_auskommentierte_wallets(tmp_path):
    (tmp_path / "scout").mkdir()
    (tmp_path / "copy_wallets.txt").write_text(f"# alt: {A1}   <- entfernt\nName: {A2}\n", encoding="utf-8")
    (tmp_path / "scout" / "pruefen.txt").write_text(f"x: {A3}\n", encoding="utf-8")
    assert w.bekannte_adressen(tmp_path) == ({A1, A2}, {A3})


def test_hoechstens_20_pro_absenden():
    viele = []
    for i in range(30):                               # gueltige Adressen: letztes Zeichen tauschen
        a = list(A1)
        a[-1] = w.ALPHABET[i]
        viele.append("".join(a))
    viele = [a for a in viele if w.ist_solana_adresse(a)]
    assert len(viele) >= 21
    ok, nein = w.eingabe_pruefen("\n".join(viele), bekannt=NIX)
    assert len(ok) == 20 and len(nein) == len(viele) - 20 and grund_von(nein, "Mehr als 20")


# ---------------------------------------------------------------- Schreiben nur in scout/pruefen.txt
def git(cwd, *args):
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=True).stdout.strip()


@pytest.fixture
def repo(tmp_path):
    bare = tmp_path / "remote.git"
    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(bare)], check=True)
    arbeit = tmp_path / "arbeit"
    subprocess.run(["git", "clone", "-q", str(bare), str(arbeit)], check=True)
    for k, v in (("user.name", "t"), ("user.email", "t@t"), ("core.autocrlf", "false")):
        git(arbeit, "config", k, v)
    (arbeit / "scout").mkdir()
    (arbeit / "scout" / "pruefen.txt").write_bytes(b"# Liste\r\nalt: " + A3.encode() + b"\r\n")
    (arbeit / "copy_wallets.txt").write_text(f"X: {A4}\n", encoding="utf-8")
    (arbeit / "code.py").write_text("a = 1\n", encoding="utf-8")
    git(arbeit, "add", "-A")
    git(arbeit, "commit", "-q", "-m", "start")
    git(arbeit, "push", "-q", "-u", "origin", "HEAD:main")
    return arbeit


def test_schreibt_und_committet_nur_pruefen_txt(repo):
    (repo / "code.py").write_text("a = 2\n", encoding="utf-8")                 # lokale Aenderung, nicht committen
    (repo / "neu.txt").write_text("x", encoding="utf-8")
    git(repo, "add", "neu.txt")                                                 # sogar vorgemerkt
    ok, meldung = w.zur_pruefung_schicken([("Eins", A1), ("Zwei", A2)], repo)
    assert ok, meldung
    assert git(repo, "show", "--name-only", "--format=", "HEAD").splitlines() == ["scout/pruefen.txt"]
    assert git(repo, "rev-parse", "HEAD") == git(repo, "rev-parse", "origin/main")          # hochgeladen
    text = (repo / "scout" / "pruefen.txt").read_bytes()
    assert text.startswith(b"# Liste\r\nalt: " + A3.encode() + b"\r\n")                     # nichts umgeschrieben
    assert f"Eins: {A1}\r\nZwei: {A2}\r\n".encode() in text                                   # Zeilenende wie in der Datei
    assert (repo / "code.py").read_text() == "a = 2\n"                                       # lokale Aenderung bleibt
    assert "neu.txt" in git(repo, "status", "--porcelain")                                   # und bleibt vorgemerkt
    assert (repo / "copy_wallets.txt").read_text() == f"X: {A4}\n"


def test_duplikat_nach_dem_pull_wird_nicht_geschrieben(repo):
    ok, meldung = w.zur_pruefung_schicken([("Alt", A3)], repo)
    assert not ok and "schon" in meldung
    assert git(repo, "rev-list", "--count", "HEAD") == "1"


def test_lokal_geaenderte_pruefliste_wird_nicht_angefasst(repo):
    (repo / "scout" / "pruefen.txt").write_bytes(b"von Hand\n")
    ok, meldung = w.zur_pruefung_schicken([("Eins", A1)], repo)
    assert not ok and "Nichts wurde gespeichert" in meldung
    assert (repo / "scout" / "pruefen.txt").read_bytes() == b"von Hand\n"


def test_fehler_beim_hochladen_nimmt_eigene_aenderung_zurueck(repo):
    git(repo, "remote", "set-url", "origin", str(repo / "gibt-es-nicht.git"))
    vorher = (repo / "scout" / "pruefen.txt").read_bytes()
    kopf = git(repo, "rev-parse", "HEAD")
    ok, meldung = w.zur_pruefung_schicken([("Eins", A1)], repo)
    assert not ok
    assert (repo / "scout" / "pruefen.txt").read_bytes() == vorher
    assert git(repo, "rev-parse", "HEAD") == kopf
    assert git(repo, "status", "--porcelain") == ""


def test_neue_bot_commits_werden_vor_dem_push_geholt(repo, tmp_path):
    zweit = tmp_path / "zweit"
    subprocess.run(["git", "clone", "-q", str(tmp_path / "remote.git"), str(zweit)], check=True)
    git(zweit, "config", "user.name", "b")
    git(zweit, "config", "user.email", "b@b")
    (zweit / "daten.csv").write_text("1\n", encoding="utf-8")
    git(zweit, "add", "-A")
    git(zweit, "commit", "-q", "-m", "COPY Update [skip ci]")
    git(zweit, "push", "-q")
    ok, meldung = w.zur_pruefung_schicken([("Eins", A1)], repo)
    assert ok, meldung
    assert (repo / "daten.csv").exists() and git(repo, "rev-parse", "HEAD") == git(repo, "rev-parse", "origin/main")


# ---------------------------------------------------------------- Scout anstossen (gh wird nachgemacht)
class Antwort:
    def __init__(self, code=0, out="", err=""):
        self.returncode, self.stdout, self.stderr = code, out, err


def gh_nachmachen(monkeypatch, status, start_code=0):
    aufrufe = []

    def fake(cmd, **kw):
        aufrufe.append(cmd)
        if cmd[:3] == ["gh", "run", "list"]:
            return Antwort(0, status)
        return Antwort(start_code)
    monkeypatch.setattr(w.subprocess, "run", fake)
    return aufrufe


def test_scout_wird_angestossen_wenn_keiner_laeuft(monkeypatch):
    aufrufe = gh_nachmachen(monkeypatch, '[{"status":"completed"},{"status":"completed"}]')
    ok, meldung = w.scout_anstossen()
    assert ok and any(a[:3] == ["gh", "workflow", "run"] for a in aufrufe)


@pytest.mark.parametrize("laufend", ["in_progress", "queued"])
def test_scout_wird_nicht_angestossen_wenn_einer_laeuft(monkeypatch, laufend):
    aufrufe = gh_nachmachen(monkeypatch, f'[{{"status":"{laufend}"}},{{"status":"completed"}}]')
    ok, meldung = w.scout_anstossen()
    assert not ok and "nächsten Lauf" in meldung and not any(a[:3] == ["gh", "workflow", "run"] for a in aufrufe)


def test_scout_anstossen_ohne_gh_stuerzt_nicht_ab(monkeypatch):
    def fake(cmd, **kw):
        raise FileNotFoundError("gh")
    monkeypatch.setattr(w.subprocess, "run", fake)
    ok, meldung = w.scout_anstossen()
    assert not ok and "nächsten Scout-Lauf" in meldung


# ---------------------------------------------------------------- Liste mit Status
def test_pruefliste_status_wartet_und_geprueft(tmp_path):
    (tmp_path / "scout").mkdir()
    (tmp_path / "copy_wallets.txt").write_text(f"Aktiv: {A4}\n# Alt: {A2}   <- entfernt\n", encoding="utf-8")
    (tmp_path / "scout" / "pruefen.txt").write_text(f"# x\nEins: {A1}\n{A3}\nAlt: {A2}\nEins: {A1}\n", encoding="utf-8")
    kopf = w.rechnung.SCOUT_HEADER
    zeile = dict.fromkeys(kopf, "")
    zeile.update(zeit="2026-10-04 05:00:00", wallet=A1, quelle="liste", ergebnis="bewertet", punkte="12.5",
                 haltedauer_median_min="7.5", rendite_ohne_besten_pct="3.2", coins_abgeschlossen="9")
    abgelehnt = dict(zeile, wallet=A2, ergebnis="raus", grund="Bot", punkte="")
    with open(tmp_path / "scout" / "kandidaten.csv", "w", newline="", encoding="utf-8") as f:
        wr = csv.writer(f)
        wr.writerow(kopf)
        wr.writerow([zeile[k] for k in kopf])
        wr.writerow([abgelehnt[k] for k in kopf])
    zeilen = {z["wallet"]: z for z in w.pruefliste_status(tmp_path)}
    assert list(zeilen) == [A1, A3, A2]                                       # keine Doppelten, Reihenfolge der Datei
    assert zeilen[A1]["status"] == "geprüft" and zeilen[A1]["punkte"] == 12.5 and zeilen[A1]["name"] == "Eins"
    assert zeilen[A1]["haltedauer_min"] == 7.5 and zeilen[A1]["rendite_ohne_besten"] == 3.2
    assert zeilen[A3]["status"] == "wartet" and zeilen[A3]["punkte"] is None
    assert zeilen[A2]["ergebnis"] == "raus" and zeilen[A2]["grund"] == "Bot" and zeilen[A2]["copy"] == "früher"


# ---------------------------------------------------------------- Ausfuehrungskosten, Flugschreiber
def test_messung_detail_median_und_schlechteste_zehntel(tmp_path):
    (tmp_path / "copy").mkdir()
    with open(tmp_path / "messung.csv", "w", newline="", encoding="utf-8") as f:
        wr = csv.writer(f)
        wr.writerow(["zeit", "konto", "aktion", "symbol", "mint", "quote_sofort", "quote_spaeter", "sekunden",
                     "abweichung_pct"])
        for i in range(10):
            wr.writerow(["z", "k", "KAUF", "S", "m", 1, 1, 4.0 + i, i])         # 0..9 %, Abstand 4..13 s
    k = next(m for m in w.rechnung.messung_detail(tmp_path) if m["quelle"].startswith("Haupt") and m["aktion"] == "KAUF")
    assert k["anzahl"] == 10 and k["median"] == 4.5 and k["schlechteste_10"] == 9 and k["median_s"] == 8.5
    assert k["schlechter_5"] == 0.4 and k["max_s"] == 13.0
    assert next(m for m in w.rechnung.messung_detail(tmp_path) if m["aktion"] == "VERKAUF")["median"] is None


def test_flug_verkauf_minuten_seit_kauf(tmp_path):
    (tmp_path / "experimente" / "notbremse_25").mkdir(parents=True)
    with open(tmp_path / "experimente" / "notbremse_25" / "journal.csv", "w", newline="", encoding="utf-8") as f:
        wr = csv.writer(f)
        wr.writerow(["zeit", "aktion", "mint", "grund", "pnl_pct"])
        wr.writerow(["2026-10-04 00:00:00", "KAUF", "M", "", ""])
        wr.writerow(["2026-10-04 00:30:00", "VERKAUF", "M", "NOTBREMSE (-25%)", "-26.0"])
    v = w.rechnung.flug_verkaeufe("notbremse_25", "M", tmp_path)
    assert v == [{"minuten": 30.0, "grund": "NOTBREMSE (-25%)", "pnl_pct": -26.0}]
