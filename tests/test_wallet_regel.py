"""Wallet-Regel Verlust (Entscheidung 08.10.): Ergebnis seit Start mit offenen Positionen, Schutzliste, kein Urteil ohne Kurs."""
import json
import os
import time

import pytest

import copy_bot as cb
import scout_bot as scout
from helpers import addr

NOW = time.time()
START = time.strftime("%Y-%m-%dT%H:%M:%S+00:00", time.gmtime(NOW - 200 * 3600))


def konto(geschlossen_pnl=-0.01, n=30, offen=None, letzter_trade=None):
    """Konto mit n geschlossenen Positionen und optional einer offenen (Einsatz 0.2, Kurs so, dass Wert = 'wert')."""
    pos = {}
    if offen is not None:
        wert, preis = offen
        pos["M1"] = {"mint": "M1", "decimals": 6, "tokens_raw": 1_000_000, "invested_sol": 0.2, "proceeds_sol": 0.0,
                     "fees_sol": 0.0, "letzter_preis_sol": preis if preis is not None else None}
        if preis is not None:
            pos["M1"]["letzter_preis_sol"] = wert          # 1 Token * Preis = Wert
            pos["M1"]["letzter_preis_zeit"] = NOW - 60     # frischer Kurs
    return {"gestartet": START, "letzter_trade": letzter_trade or NOW - 3600, "runde": 1,
            "geschlossen": [{"pnl_sol": geschlossen_pnl}] * n, "positionen": pos}


def test_ergebnis_seit_start_rechnet_offene_positionen_mit():
    a = konto(-0.01, 30, offen=(1e-9, 1e-9))                # offene Position zum Kurs 0: -0,2
    ergebnis, ohne = cb.ergebnis_seit_start(a)
    assert ergebnis == pytest.approx(-0.3 - 0.2) and ohne == 0


def test_verlust_regel_greift_nur_mit_offenen_positionen():
    a = konto(-0.02, 30, offen=(1e-9, 1e-9))                # realisiert -0,6, mit offener -0,8: noch kein Fall
    assert cb.verlust_regel(a)[0] is False
    a = konto(-0.03, 30, offen=(1e-9, 1e-9))                # realisiert -0,9, mit offener -1,1: Fall
    assert cb.verlust_regel(a)[0] is True
    a = konto(-0.04, 30)                                  # realisiert -1,2 ohne offene: Fall
    assert cb.verlust_regel(a)[0] is True


def test_verlust_regel_unter_30_positionen_kein_fall():
    assert cb.verlust_regel(konto(-0.2, 29))[0] is False


def test_kurs_null_oder_veraltet_ist_kein_kurs():
    a = konto(-0.05, 30, offen=(0.0, 0.0))                # Jupiter lieferte keinen usdPrice -> Kurs 0
    assert cb.ergebnis_seit_start(a, NOW)[1] == 1 and cb.verlust_regel(a, NOW)[0] is False
    b = konto(-0.05, 30, offen=(1e-9, 1e-9))
    b["positionen"]["M1"]["letzter_preis_zeit"] = NOW - 3 * 3600      # Abruf seit 3 h ausgefallen
    assert cb.verlust_regel(b, NOW)[0] is False
    c = konto(-0.05, 30, offen=(1e-9, 1e-9))
    del c["positionen"]["M1"]["letzter_preis_zeit"]                   # alte Position ohne Zeitstempel
    assert cb.verlust_regel(c, NOW)[0] is False
    d = konto(-0.05, 30)
    d["positionen"] = {"X": {"mint": "X"}}                            # unvollstaendig: kein Absturz
    assert cb.ergebnis_seit_start(d, NOW)[1] == 1


def test_ohne_kurs_kein_urteil():
    a = konto(-0.05, 30, offen=(0.0, None))               # offene Position noch ohne Kurs
    assert cb.ergebnis_seit_start(a)[1] == 1
    assert cb.verlust_regel(a)[0] is False
    b = konto(-0.05, 30, offen=(1e-9, 1e-9))
    b["positionen"]["M1"]["verkauf_offen"] = True         # wartet nach Jupiter-Ausfall
    assert cb.verlust_regel(b)[0] is False


def _setup(konten, namen):
    with open(cb.WALLET_FILE, "w", encoding="utf-8") as f:
        f.write("".join(f"{nm}: {addr(nm)}\n" for nm in namen))
    os.makedirs(os.path.dirname(cb.ACCOUNTS_FILE) or ".", exist_ok=True)
    with open(cb.ACCOUNTS_FILE, "w", encoding="utf-8") as f:
        json.dump({"saved_at": NOW - 60, "wallets": konten}, f)
    return [(nm, addr(nm)) for nm in namen]


def test_schutzliste_wallet_wird_nie_wegen_verlust_ersetzt(monkeypatch):
    monkeypatch.setattr(scout, "AUTO_GESCHUETZT", {"Gesch": "Test"})
    k = konto(-0.01, 30, offen=(1e-9, 1e-9))
    k["geschlossen"] = [{"pnl_sol": -0.03}] * 30          # mit offenen -1,1
    aktiv = _setup({"Gesch": dict(k), "Normal": json.loads(json.dumps(k))}, ["Gesch", "Normal"])
    accounts = scout.load_copy_accounts()
    out = scout.replaceable_wallets(aktiv, accounts, NOW, check_bots=False)
    assert [n for n, _, _ in out] == ["Normal"]
    assert "seit Start" in out[0][2]
    treffer = scout.geschuetzte_treffer(aktiv, accounts, NOW)
    assert list(treffer) == ["Gesch"] and "Verlust" in treffer["Gesch"]
    scout.STATS["geschuetzt"] = treffer
    assert "Gesch" in scout.auto_status_line() and "geschuetzt" in scout.auto_status_line()


def test_schutzliste_gilt_auch_gegen_stille_aber_nicht_gegen_bot(monkeypatch):
    monkeypatch.setattr(scout, "AUTO_GESCHUETZT", {"Gesch": "Test"})
    k = konto(0.0, 1, letzter_trade=NOW - 100 * 3600)     # 100 h still
    aktiv = _setup({"Gesch": k}, ["Gesch"])
    accounts = scout.load_copy_accounts()
    assert scout.replaceable_wallets(aktiv, accounts, NOW, check_bots=False) == []
    assert "still" in scout.geschuetzte_treffer(aktiv, accounts, NOW)["Gesch"]
    monkeypatch.setattr(scout, "load_flood_hints", lambda now: {addr("Gesch"): "heute"})
    out = scout.replaceable_wallets(aktiv, accounts, NOW, check_bots=False)
    assert [n for n, _, _ in out] == ["Gesch"] and out[0][2].startswith("Bot")


def test_ohne_kurs_wird_nicht_ersetzt(monkeypatch):
    monkeypatch.setattr(scout, "AUTO_GESCHUETZT", {})
    k = konto(-0.05, 30, offen=(0.0, None))
    aktiv = _setup({"W": k}, ["W"])
    assert scout.replaceable_wallets(aktiv, scout.load_copy_accounts(), NOW, check_bots=False) == []


def test_4dov_steht_in_der_schutzliste():
    assert "4DOV" in scout.AUTO_GESCHUETZT


def test_dashboard_und_bot_rechnen_dieselbe_zahl():
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "dashboard"))
    from dashboard import rechnung
    a = konto(-0.03, 30, offen=(1e-9, 1e-9))
    a.update({"adresse": "x", "bankroll_sol": 9.0, "schatten_geschlossen": []})
    k = rechnung.copy_konto("W", a, True, [], set())
    assert k["ergebnis_seit_start"] == pytest.approx(cb.ergebnis_seit_start(a)[0])
    assert k["ohne_kurs"] == 0
