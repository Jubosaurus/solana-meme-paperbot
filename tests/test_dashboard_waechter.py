"""Wallet-Waechter: synthetische lokale Daten, Grenzwerte und reine Vorschau."""
import csv
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

from helpers import addr as helper_addr

DASHBOARD = Path(__file__).resolve().parent.parent / "dashboard"
sys.path.insert(0, str(DASHBOARD))
import rechnung as r  # noqa: E402

JETZT = datetime(2026, 10, 7, 12, tzinfo=timezone.utc).timestamp()
TAG = 86400


def addr(name):
    # Lesbare Namen koennen Zeichen enthalten, die in Base58 ungueltig sind.
    return helper_addr(name.translate(str.maketrans({"0": "1", "O": "P", "I": "J", "l": "m"})))


def schreibe_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def schreibe_csv(path, header, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=header)
        writer.writeheader()
        writer.writerows(rows)


def konto(name, n=0, pnl=0, alter=8, pause=1, **kw):
    acct = {"adresse": addr(name), "gestartet": datetime.fromtimestamp(JETZT - alter * TAG, timezone.utc).isoformat(),
            "letzter_trade": JETZT - pause * 3600, "bankroll_sol": 10, "runde": 1, "positionen": {},
            "geschlossen": [{"pnl_sol": pnl / n, "runde": 1} for _ in range(n)]}
    acct.update(kw)
    return acct


def repository(tmp_path, wallets, saved=JETZT, flut=None, scout=(), warten=()):
    schreibe_json(tmp_path / "copy/konten.json", {"wallets": wallets, "saved_at": saved})
    schreibe_json(tmp_path / "copy/flutschutz.json", flut or {})
    (tmp_path / "copy_wallets.txt").write_text("".join(f"{n}: {addr(n)}\n" for n in wallets), encoding="utf-8")
    schreibe_csv(tmp_path / "scout/kandidaten.csv", r.SCOUT_HEADER, scout)
    schreibe_csv(tmp_path / "scout/warteliste.csv", r.WAECHTER_WARTESPALTEN, warten)
    return tmp_path


@pytest.fixture
def keine_historie(monkeypatch):
    monkeypatch.setattr(r, "_waechter_heute", lambda *args: {"anzahl": 0, "ereignisse": []})


def test_reihenfolge_bot_still_verlust_und_laengste_pause(tmp_path, keine_historie):
    wallets = {"VerlustA": konto("VerlustA", n=30, pnl=-2), "VerlustB": konto("VerlustB", n=30, pnl=-4),
               "StillA": konto("StillA", pause=72), "StillB": konto("StillB", pause=100),
               "Bot": konto("Bot", alter=0.1)}
    repo = repository(tmp_path, wallets, flut={addr("Bot"): {"zuletzt": JETZT - TAG}})
    u = r.waechter_uebersicht(repo, JETZT)
    assert u["aktiv"] == 5 and u["maximum"] == 30
    assert [z["name"] for z in u["kandidaten"]] == ["Bot", "StillB", "StillA", "VerlustB", "VerlustA"]
    assert u["naechster"]["name"] == "Bot"
    assert u["naechster"]["schonfrist"]  # Schonfrist schuetzt nur das Ergebnis.


@pytest.mark.parametrize("n,pnl,alter,erwartet,schonfrist", [
    (29, -3, 6.9, None, True), (29, -3, 7, None, False),
    (30, -1, 1, None, False), (30, -1.01, 1, "verlust", False),
    (30, 0, 8, None, False), (31, -4, 8, "verlust", False),
])
def test_verlust_und_schonfrist_grenzen(tmp_path, keine_historie, n, pnl, alter, erwartet, schonfrist):
    repo = repository(tmp_path, {"Alpha": konto("Alpha", n=n, pnl=pnl, alter=alter)})
    z = r.waechter_uebersicht(repo, JETZT)["wallets"][0]
    assert z["kandidat"] == erwartet and z["schonfrist"] == schonfrist


def _offene(wert, preis_zeit="frisch", **extra):
    """Eine offene Position (Einsatz 0.2) zum Kurs 'wert' (1 Token), Kurs jetzt gemeldet."""
    import time
    pos = {"mint": "m", "tokens_raw": 1000000, "decimals": 6, "letzter_preis_sol": wert, "invested_sol": 0.2,
           "proceeds_sol": 0.0, "fees_sol": 0.0}
    if preis_zeit == "frisch":
        pos["letzter_preis_zeit"] = time.time()
    pos.update(extra)
    return {"m": pos}


def test_alle_runden_geschlossen_und_offenes_ergebnis_als_zusatz(tmp_path, keine_historie):
    # Regel seit 08.10.: offene Gewinne zaehlen mit. Realisiert -2, offen +0.5-0.2: seit Start -1.7 -> Fall.
    acct = konto("Alpha", n=30, pnl=-2, runde=3, bankroll_sol=10)
    acct["positionen"] = _offene(0.5)
    repo = repository(tmp_path, {"Alpha": acct})
    u = r.waechter_uebersicht(repo, JETZT)
    gemeinsam = r.copy_konten(repo)[0][0]
    assert u["wallets"][0]["ergebnis"] == pytest.approx(gemeinsam["pnl_geschlossen"])
    assert u["wallets"][0]["ergebnis_seit_start"] == pytest.approx(gemeinsam["ergebnis_seit_start"])
    assert gemeinsam["ergebnis_seit_start"] == pytest.approx(-2 + 0.3) and u["naechster"]["kandidat"] == "verlust"


def test_offene_gewinne_retten_eine_wallet_offene_verluste_machen_sie_zum_fall(tmp_path, keine_historie):
    gewinn = konto("Gewinn", n=30, pnl=-1.5)
    gewinn["positionen"] = _offene(1.2)                    # +1.0 offen: seit Start -0.5
    verlust = konto("Verlust", n=30, pnl=-0.6)
    verlust["positionen"] = _offene(1e-9)                   # -0.2 offen: -0.8 (noch kein Fall)
    verlust2 = konto("Verlust2", n=30, pnl=-0.9)
    verlust2["positionen"] = _offene(1e-9)                  # -0.2 offen: -1.1 (Fall, realisiert nur -0.9)
    u = r.waechter_uebersicht(repository(tmp_path, {"Gewinn": gewinn, "Verlust": verlust, "Verlust2": verlust2}), JETZT)
    assert [z["name"] for z in u["kandidaten"]] == ["Verlust2"]


def test_ohne_frischen_kurs_kein_verlust_urteil(tmp_path, keine_historie):
    wallets = {}
    for name, pos in {"Keiner": _offene(0.0, preis_zeit=None), "Null": _offene(0.0, letzter_preis_zeit=__import__("time").time()),
                      "Alt": _offene(0.5, letzter_preis_zeit=__import__("time").time() - 3 * 3600),
                      "Wartet": _offene(0.5, verkauf_offen=True)}.items():
        acct = konto(name, n=30, pnl=-1.5)
        acct["positionen"] = pos
        wallets[name] = acct
    wallets["Keiner"]["positionen"]["m"]["letzter_preis_sol"] = None
    u = r.waechter_uebersicht(repository(tmp_path, wallets), JETZT)
    assert u["kandidaten"] == []
    assert all(any("ohne frischen Kurs" in h for h in z["luecken"]) for z in u["wallets"])


def test_wert0_positionen_werden_im_waechter_gekennzeichnet(tmp_path, keine_historie):
    import time
    jetzt = time.time()
    a = konto("Alpha", n=30, pnl=-0.9)
    a["positionen"] = _offene(0.0, preis_zeit=None, letzter_preis_sol=0.0, kurs_fehlt_seit=jetzt - 25 * 3600,
                              kurs_fehlt_bis=jetzt - 60)        # seit 25 h kein Kurs: Wert 0
    b = konto("Beta", n=30, pnl=-0.9)
    b["positionen"] = _offene(0.0, preis_zeit=None, letzter_preis_sol=0.0, kurs_fehlt_seit=jetzt - 23 * 3600,
                              kurs_fehlt_bis=jetzt - 60)        # erst 23 h: kein Urteil
    u = r.waechter_uebersicht(repository(tmp_path, {"Alpha": a, "Beta": b}), JETZT)
    z = {x["name"]: x for x in u["wallets"]}
    assert z["Alpha"]["kandidat"] == "verlust"
    assert any("Wert 0" in g for g in z["Alpha"]["gruende"]) and any("nur wegen" in g for g in z["Alpha"]["gruende"])
    assert z["Beta"]["kandidat"] is None and any("ohne frischen Kurs" in h for h in z["Beta"]["luecken"])


def test_schutzliste_wird_im_waechter_beruecksichtigt(tmp_path, keine_historie, monkeypatch):
    import scout_bot
    monkeypatch.setattr(scout_bot, "AUTO_GESCHUETZT", {"Alpha": "Studie"})
    wallets = {"Alpha": konto("Alpha", n=30, pnl=-3), "Beta": konto("Beta", n=30, pnl=-3),
               "Gamma": konto("Gamma", pause=100)}
    wallets["Gamma"]["gestartet"] = wallets["Alpha"]["gestartet"]
    u = r.waechter_uebersicht(repository(tmp_path, wallets), JETZT)
    assert [z["name"] for z in u["kandidaten"]] == ["Gamma", "Beta"]
    alpha = next(z for z in u["wallets"] if z["name"] == "Alpha")
    assert alpha["kandidat"] is None and any("Geschützt" in g for g in alpha["gruende"])
    monkeypatch.setattr(scout_bot, "AUTO_GESCHUETZT", {"Gamma": "Studie"})      # Schutz gilt auch gegen Stille
    u = r.waechter_uebersicht(repository(tmp_path, wallets), JETZT)
    assert [z["name"] for z in u["kandidaten"]] == ["Alpha", "Beta"]


@pytest.mark.parametrize("saved,frisch", [(JETZT - 7200, True), (JETZT - 7201, False),
                                          (None, False), (JETZT + 1, False)])
def test_stille_nur_mit_frischen_konten(tmp_path, keine_historie, saved, frisch):
    repo = repository(tmp_path, {"Alpha": konto("Alpha", alter=4, pause=72)}, saved=saved)
    u = r.waechter_uebersicht(repo, JETZT)
    assert u["konten_frisch"] is frisch
    assert (u["naechster"] is not None) is frisch
    assert u["wallets"][0]["ampel"] == ("rot" if frisch else "gelb")


def test_stille_seit_start_aber_unbekannte_zeit_nie_erfinden(tmp_path, keine_historie):
    repo = repository(tmp_path, {"Alpha": konto("Alpha", alter=3, letzter_trade=0),
                                "Beta": konto("Beta", letzter_trade="kaputt", gestartet="kaputt"),
                                "Gamma": konto("Gamma", pause=71.99)})
    u = r.waechter_uebersicht(repo, JETZT)
    z = {z["name"]: z for z in u["wallets"]}
    assert z["Alpha"]["kandidat"] == "still" and z["Alpha"]["pause_h"] == 72
    assert z["Beta"]["pause_h"] is None and z["Beta"]["kandidat"] is None
    assert z["Gamma"]["kandidat"] is None


@pytest.mark.parametrize("age,erwartet", [(7 * TAG, "bot"), (7 * TAG + 1, None), (-1, None)])
def test_flutschutz_beleg_nur_sieben_tage(tmp_path, keine_historie, age, erwartet):
    repo = repository(tmp_path, {"Alpha": konto("Alpha")}, flut={addr("Alpha"): {"zuletzt": JETZT - age}})
    assert r.waechter_uebersicht(repo, JETZT)["wallets"][0]["kandidat"] == erwartet


@pytest.mark.parametrize("quote,takt,erwartet", [(0.8, 60, None), (0.801, 1, "bot"),
                                               (0.5, 100, None), (0.501, 60, None),
                                               (0.501, 61, "bot"), (0.1, 301, None)])
def test_scout_bot_schwellen_aus_gespeicherter_bewertung(tmp_path, keine_historie, quote, takt, erwartet):
    repo = repository(tmp_path, {"Alpha": konto("Alpha")}, scout=[
        {"zeit": "2026-10-07 11:00:00", "wallet": addr("Alpha"), "ergebnis": "bewertet",
         "fehlgeschlagen": quote, "tx_pro_h": takt}])
    z = r.waechter_uebersicht(repo, JETZT)["wallets"][0]
    assert z["kandidat"] == erwartet
    assert z["ampel"] == ("rot" if erwartet else "gruen")


def test_warteliste_alle_spalten_grenzen_und_defekte_zahlen(tmp_path, keine_historie):
    def warten(name, age, bewertung):
        return {"seit": JETZT - age, "bewertet": JETZT - bewertung, "wallet": addr(name), "name": name,
                "quelle": "pruefliste", "punkte": "3.5", "rendite_ohne_besten_pct": "10", "coins": "3",
                "kauf_median_sol": "0.1", "trades_pro_tag": "200", "inaktiv_h": "kaputt"}
    repo = repository(tmp_path, {}, warten=[warten("Alpha", 7 * TAG, 21600),
                                          warten("Beta", 7 * TAG + 1, 21601), {"name": "ohne Adresse"}])
    u = r.waechter_uebersicht(repo, JETZT)
    a, b = u["warteliste"]
    assert set(r.WAECHTER_WARTESPALTEN) <= set(a)
    assert not a["abgelaufen"] and not a["neu_pruefen"]
    assert b["abgelaufen"] and b["neu_pruefen"]
    assert a["punkte"] == 3.5 and a["inaktiv_h"] is None
    assert any("ohne Wallet-Adresse" in h for h in u["hinweise"])


def test_defektes_konto_verdeckt_keine_andere_wallet(tmp_path, keine_historie):
    repo = repository(tmp_path, {"Alpha": konto("Alpha", n=30, pnl=-2), "Beta": konto("Beta", geschlossen=42)})
    u = r.waechter_uebersicht(repo, JETZT)
    assert u["naechster"]["name"] == "Alpha"
    assert len(u["wallets"]) == 2
    assert u["wallets"][1]["ergebnis"] is None


def test_falsche_adresse_nicht_als_aktives_konto_bewerten(tmp_path, keine_historie):
    repo = repository(tmp_path, {"Alpha": konto("Alpha", n=30, pnl=-5, adresse=addr("Beta"))})
    u = r.waechter_uebersicht(repo, JETZT)
    assert u["naechster"] is None
    assert u["wallets"][0]["ampel"] == "gelb"
    assert u["wallets"][0]["ergebnis"] is None


def test_fehlendes_positionsergebnis_und_scout_werte_bleiben_offen(tmp_path, keine_historie):
    acct = konto("Alpha", n=30, pnl=-3)
    acct["geschlossen"][0]["pnl_sol"] = None
    repo = repository(tmp_path, {"Alpha": acct}, scout=[
        {"zeit": "2026-10-07 11:00:00", "wallet": addr("Alpha"), "fehlgeschlagen": "NaN"}])
    z = r.waechter_uebersicht(repo, JETZT)["wallets"][0]
    assert z["ergebnis"] is None and z["kandidat"] is None and z["ampel"] == "gelb"
    assert "Aktuelle Scout-Prüfung fehlt" in z["luecken"]


def test_fehlende_leere_und_falsch_geformte_daten(tmp_path, keine_historie):
    u = r.waechter_uebersicht(tmp_path, JETZT)
    assert u["aktiv"] is None and not u["wallets"] and not u["warteliste"]
    for kaputt in ([], {"wallets": []}, {"wallets": {"Alpha": None}}, "kaputt"):
        schreibe_json(tmp_path / "copy/konten.json", kaputt)
        u = r.waechter_uebersicht(tmp_path, JETZT)
        assert u["naechster"] is None and u["hinweise"]
    (tmp_path / "copy/konten.json").write_text("{", encoding="utf-8")
    assert r.waechter_uebersicht(tmp_path, JETZT)["naechster"] is None


def test_vorschau_schreibt_nichts(tmp_path, keine_historie):
    repo = repository(tmp_path, {"Alpha": konto("Alpha", n=30, pnl=-3)})
    vorher = {str(p.relative_to(repo)): p.read_bytes() for p in repo.rglob("*") if p.is_file()}
    r.waechter_uebersicht(repo, JETZT)
    nachher = {str(p.relative_to(repo)): p.read_bytes() for p in repo.rglob("*") if p.is_file()}
    assert vorher == nachher


def test_tageslimit_git_tausch_einmal_stille_und_manuell_nicht(monkeypatch, tmp_path):
    ab = datetime(2026, 10, 7, tzinfo=timezone.utc).timestamp()
    log = f"""WAECHTER:{int(ab - 1)}
+# 06.10. automatisch aufgenommen: gestern
+Alt: {addr('Alt')}
WAECHTER:{int(ab)}
-Still: {addr('Still')}
+# Still: {addr('Still')} <- entfernt 07.10. automatisch: 80 h still; ersetzt durch Neu
+# 07.10. automatisch aufgenommen: geeignet
+Neu: {addr('Neu')}
WAECHTER:{int(ab + 60)}
-Pause: {addr('Pause')}
+# Pause: {addr('Pause')} <- entfernt 07.10. automatisch: 90 h still
WAECHTER:{int(ab + 120)}
+# 07.10. automatisch aufgenommen: geeignet
+Beta: {addr('Beta')}
+Manuell: {addr('Manuell')}
WAECHTER:{int(ab + 180)}
-Neu: {addr('Neu')}
+# 07.10. automatisch aufgenommen: alte Zeile umgestellt
+Neu: {addr('Neu')}
WAECHTER:{int(JETZT + 1)}
+# 07.10. automatisch aufgenommen: Zukunft
+Spaeter: {addr('Spaeter')}
"""
    calls = []
    def git(args, **kw):
        calls.append(args)
        return SimpleNamespace(returncode=0, stdout=log)
    monkeypatch.setattr(r.subprocess, "run", git)
    u = r.waechter_uebersicht(tmp_path, JETZT)
    assert u["tagesbeginn"] == ab
    assert u["heute"]["anzahl"] == 2 and u["heute"]["rest"] == 1
    assert len(u["heute"]["ereignisse"]) == 5
    assert calls[0][:2] == ["git", "log"] and "--" in calls[0]
    assert calls[0][-1] == "copy_wallets.txt"


def test_git_fehler_ist_unbekannt_statt_null(monkeypatch, tmp_path):
    monkeypatch.setattr(r.subprocess, "run", lambda *a, **kw: SimpleNamespace(returncode=128, stdout=""))
    u = r.waechter_uebersicht(tmp_path, JETZT)
    assert u["heute"]["anzahl"] is None and u["heute"]["rest"] is None


def test_seite_plakette_nur_fuer_belegte_automatische_entfernungen(tmp_path, monkeypatch):
    pytest.importorskip("streamlit")
    import threading
    import time
    from streamlit.testing.v1 import AppTest
    import ansicht
    import daten

    monkeypatch.setattr(time, "sleep", lambda s: threading.Event().wait(s))
    gruende = {
        "haru": "entfernt 07.10. automatisch: still, seit 74 h kein eigener Trade; ohne Ersatz",
        "koko": "entfernt 07.10. automatisch: still, seit 81 h kein eigener Trade; ohne Ersatz",
        "Tausch": "entfernt 07.10. automatisch: 80 h still; ersetzt durch Neu",
        "Hand": "entfernt 07.10.: still, seit 80 h kein eigener Trade; von Hand",
        "Unklar": "entfernt 07.10.: 72 h still",
        "Erwaehnung": "entfernt 07.10.: von Hand; automatisch vorgeschlagen",
    }
    ab = datetime(2026, 10, 7, tzinfo=timezone.utc).timestamp()
    log = f"WAECHTER:{int(ab)}\n" + "".join(
        f"-{name}: {addr(name)}\n+# {name}: {addr(name)} <- {grund}\n"
        for name, grund in gruende.items())
    log += f"+# 07.10. automatisch aufgenommen: geeignet\n+Neu: {addr('Neu')}\n"
    monkeypatch.setattr(r.subprocess, "run", lambda *args, **kw: SimpleNamespace(returncode=0, stdout=log))
    repo = repository(tmp_path, {})
    u = r.waechter_uebersicht(repo, JETZT)
    assert u["heute"]["anzahl"] == 1 and u["heute"]["rest"] == 2
    # Reine Entfernungen behalten das Zaehler-Feld False, auch mit sichtbarer Plakette.
    assert all(not e["automatisch"] for e in u["heute"]["ereignisse"] if e["art"] == "Entfernung")
    monkeypatch.setattr(daten, "waechter", lambda head: u)
    monkeypatch.setattr(ansicht, "bot_status_eintraege", lambda: [])
    app = AppTest.from_file(str(DASHBOARD / "app_pages/waechter.py"), default_timeout=15).run()
    assert not app.exception
    html = [e.value for e in app.get("html")]
    plakette = r'<span class="pb-chip\s*">automatisch</span>'
    for name in gruende:
        eintrag = next(h for h in html if f">{name}</" in h and "Entfernung" in h)
        assert (re.search(plakette, eintrag) is not None) == (name in {"haru", "koko", "Tausch"})
    assert not any(re.search(plakette, h) for h in html if "Aufnahme / Ersetzen" in h)
    assert u["heute"]["anzahl"] == 1 and u["heute"]["rest"] == 2


def test_cache_vermeidet_neues_lesen(monkeypatch):
    pytest.importorskip("streamlit")
    import daten
    calls = []
    monkeypatch.setattr(r, "waechter_uebersicht", lambda: calls.append(1) or {"wallets": []})
    daten.waechter.clear()
    assert daten.waechter("waechter-test") == {"wallets": []}
    daten.waechter("waechter-test")
    assert calls == [1]
    daten.waechter.clear()


def test_kompakte_liste_und_wallet_details_wechsel(tmp_path, monkeypatch, keine_historie):
    pytest.importorskip("streamlit")
    import threading
    import time
    from streamlit.testing.v1 import AppTest
    import ansicht
    import daten
    monkeypatch.setattr(time, "sleep", lambda s: threading.Event().wait(s))
    repo = repository(tmp_path, {"Jung": konto("Jung", alter=1),
                                "Verlust": konto("Verlust", n=30, pnl=-2)})
    u = r.waechter_uebersicht(repo, JETZT)
    monkeypatch.setattr(daten, "waechter", lambda head: u)
    monkeypatch.setattr(ansicht, "bot_status_eintraege", lambda: [])
    app = AppTest.from_file(str(DASHBOARD / "app_pages/waechter.py"), default_timeout=15).run()
    assert not app.exception
    liste = next(e.value for e in app.get("html") if "nx-waechter-zeile" in e.value)
    assert liste.index(">Verlust</") < liste.index(">Jung</")
    assert "pb-chip" not in liste
    assert "Aktuelle Scout-Prüfung fehlt" not in liste and "<span>Hinweis</span>" not in liste
    html = "".join(e.value for e in app.get("html"))
    assert html.count("Aktuelle Scout-Prüfung fehlt") == 1
    assert any("1 Gelb · 1 Rot · 0 Grün" in e.value for e in app.caption)
    assert len([e for e in app.expander if e.label == "Wallet-Details"]) == 1
    assert app.selectbox[0].value == "Verlust"
    details = next(e.value for e in app.get("html") if ">Adresse</" in e.value)
    assert addr("Verlust") in details and addr("Jung") not in details
    app.selectbox[0].select("Jung").run()
    assert not app.exception
    details = next(e.value for e in app.get("html") if ">Adresse</" in e.value)
    assert addr("Jung") in details and addr("Verlust") not in details


def test_seite_vorschau_details_leer_und_ladefehler(tmp_path, monkeypatch, keine_historie):
    pytest.importorskip("streamlit")
    import threading
    import time
    from streamlit.testing.v1 import AppTest
    import ansicht
    import daten
    monkeypatch.setattr(time, "sleep", lambda s: threading.Event().wait(s))
    repo = repository(tmp_path, {"Alpha": konto("Alpha", n=30, pnl=-2)}, warten=[
        {"wallet": addr("Beta"), "name": "<b>Beta</b>", "quelle": "<script>fremd</script>"}])
    u = r.waechter_uebersicht(repo, JETZT)
    monkeypatch.setattr(daten, "waechter", lambda head: u)
    monkeypatch.setattr(ansicht, "bot_status_eintraege", lambda: [])
    app = AppTest.from_file(str(DASHBOARD / "app_pages/waechter.py"), default_timeout=15).run()
    assert not app.exception and not app.button
    html = "\n".join(e.value for e in app.get("html"))
    assert "nur Vorschau" in html and "Größter Verlust" in html
    assert "&lt;script&gt;fremd&lt;/script&gt;" in html and "<script>fremd</script>" not in html
    assert any("UTC" in e.value and "dt. Zeit" in e.value for e in app.caption)
    u["heute"]["rest"] = 0
    app.run()
    assert "Tageslimit ist erreicht" in "\n".join(e.value for e in app.get("html"))
    u["wallets"], u["warteliste"], u["naechster"] = [], [], None
    app.run()
    assert not app.exception
    assert "Keine aktiven Wallets" in "\n".join(e.value for e in app.get("html"))
    def fehler(head):
        raise ValueError("unlesbar")
    monkeypatch.setattr(daten, "waechter", fehler)
    app.run()
    assert not app.exception
    assert "konnte nicht geladen" in "\n".join(e.value for e in app.get("html"))
