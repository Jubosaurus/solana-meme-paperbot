"""Komplette Schichten aller drei Bots mit kuenstlicher Uhr, Fake-WebSocket und Fake-Git.
Prueft vor allem: kein Absturz, Daten gespeichert, jeder Bot sichert nur seine eigenen Dateien."""
import csv
import json
import os
import signal
import time

import pytest
import websocket

import bot as core
import copy_bot as cb
import scout_bot as scout
from helpers import buy_tx, sell_tx, tok, addr, WALLET, MINT

PRICE_USD = 5e-5


def git_adds(git):
    return [args[1:] for args in git if args and args[0] == "add"]


# ================================================================ Copy-Bot

class FakeWS:
    """Liefert vorbereitete Nachrichten; danach Zeitueberschreitung (die Uhr laeuft 1 s weiter)."""

    def __init__(self, clock, script):
        self.clock, self.script, self.sent, self.closed = clock, list(script), [], False

    def send(self, text):
        self.sent.append(json.loads(text))

    def recv(self):
        if self.script:
            item = self.script.pop(0)
            return item() if callable(item) else item
        self.clock.sleep(1)
        raise websocket.WebSocketTimeoutException("timeout")

    def settimeout(self, t):
        pass

    def ping(self):
        pass

    def close(self):
        self.closed = True


def notification(sig, sub=101, logs=("Program log: Instruction: Buy",)):
    return json.dumps({"jsonrpc": "2.0", "method": "logsNotification", "params": {
        "subscription": sub, "result": {"value": {"signature": sig, "err": None, "logs": list(logs)}}}})


def test_copy_schicht_mit_leerer_nachricht_und_neuverbindung(clock, market, monkeypatch, sandbox):
    open(cb.WALLET_FILE, "w", encoding="utf-8").write(f"Alpha: {WALLET}\n")
    market.set(MINT, price=PRICE_USD)
    txs = {"live1": buy_tx(sig="live1", block_time=int(clock.now)),
           "live2": sell_tx(sig="live2", tokens=1_000_000, pre=1_000_000, sol=0.6, block_time=int(clock.now) + 5)}

    def rpc(method, params):
        if method == "getTransaction":
            return txs.get(params[0])
        if method == "getSignaturesForAddress":
            return []
        return None
    monkeypatch.setattr(core, "rpc", rpc)
    confirm = json.dumps({"jsonrpc": "2.0", "id": 1, "result": 101})
    sockets = [
        FakeWS(clock, [confirm, notification("live1"), "kein json", ""]),          # "" = Server hat geschlossen
        FakeWS(clock, [confirm, notification("live2", logs=("Program log: Instruction: Sell",))]),
    ]
    made = []

    def create_connection(url, timeout=None):
        ws = sockets[len(made)]
        made.append(ws)
        return ws
    monkeypatch.setattr(cb.websocket, "create_connection", create_connection)
    monkeypatch.setattr(cb, "SHIFT_SECONDS", 30)

    cb.run()

    assert len(made) == 2 and cb.STATS["reconnects"] == 1
    assert made[0].sent[0]["method"] == "logsSubscribe"
    assert cb.STATS["unlesbar"] == 1 and cb.STATS["errors"] == 0
    data = json.load(open(cb.ACCOUNTS_FILE, encoding="utf-8"))
    acct = data["wallets"]["Alpha"]
    assert acct["positionen"] == {} and len(acct["geschlossen"]) == 1
    assert acct["abgedeckt_bis"] > 0
    rows = list(csv.DictReader(open(cb.JOURNAL_FILE, encoding="utf-8")))
    assert [r["aktion"] for r in rows] == ["KAUF", "VERKAUF"]
    titles = [t for t, _ in sandbox["discord"]]
    assert any(t.endswith("Copy-Schicht beendet") and "pruefen" not in t for t in titles)
    adds = git_adds(sandbox["git"])
    assert adds and all(a == (cb.COPY_DIR,) for a in adds)              # nur copy/


# ================================================================ Hauptbot

def test_hauptbot_schicht(clock, market, monkeypatch, sandbox):
    market.set(MINT)
    listed = {MINT: market.tokens[MINT]}

    def jup_get(path):
        if path.startswith("/tokens/v2/top"):
            return list(listed.values())
        if path.startswith("/ultra/v1/shield"):
            return {"warnings": {}}
        return None
    monkeypatch.setattr(core, "jup_get", jup_get)
    monkeypatch.setattr(core, "bundle_dev_check", lambda mint: (None, {
        "quelle": "block0", "block0_wallets": 0, "block0_supply_pct": 0.0, "block0_still_held_pct": 0.0}))
    monkeypatch.setattr(core, "SHIFT_DURATION_SECONDS", core.LOOP_SLEEP_SECONDS * 6)

    core.run()

    assert core.STATS["loops"] == 6 and core.STATS["loop_errors"] == 0
    p = json.load(open(core.PORTFOLIO_FILE, encoding="utf-8"))
    assert MINT in p["positions"]
    assert [r["aktion"] for r in csv.DictReader(open(core.JOURNAL_FILE, encoding="utf-8"))] == ["KAUF"]
    assert os.path.exists("experimente/kontrollgruppe/portfolio.json")
    titles = [t for t, _ in sandbox["discord"]]
    assert "🔴 Schicht beendet" in titles
    own = {core.PORTFOLIO_FILE, core.JOURNAL_FILE, core.REJECT_FILE, core.PHASE_FILE, core.VERLAUF_DIR,
           core.NEAR_MISS_FILE, "verlauf.csv", core.EXP_DIR, core.MESSUNG_FILE, core.DEX_FILE}
    adds = git_adds(sandbox["git"])
    assert len(adds) >= 2                                               # Zwischensicherung und Schichtende
    assert all(set(a) <= own for a in adds)
    assert core.PORTFOLIO_FILE in adds[-1]


def test_hauptbot_schicht_ueberlebt_fehler_im_loop(clock, market, monkeypatch, sandbox):
    def kaputt(*a, **kw):
        raise ValueError("API-Antwort kaputt")
    monkeypatch.setattr(core, "update_phase", kaputt)
    monkeypatch.setattr(core, "SHIFT_DURATION_SECONDS", core.LOOP_SLEEP_SECONDS * 3)
    core.run()
    assert core.STATS["loops"] == 3 and core.STATS["loop_errors"] == 1
    assert "⚠️ Schicht beendet (pruefen)" in [t for t, _ in sandbox["discord"]]


# ================================================================ Scout

def test_scout_lauf(monkeypatch, sandbox):
    now = time.time()
    json.dump({"closed": [{"mint": MINT, "symbol": "WIN", "peak_multiple": 5.0,
                           "closed_at": "2999-01-01T00:00:00+00:00"}]}, open("portfolio.json", "w"))
    cand = addr("Kand")
    monkeypatch.setattr(scout, "early_buyers", lambda mint, sol_usd: [cand])
    sigs = [{"signature": f"s{i}", "blockTime": int(now - 3600 - i * 600), "err": None} for i in range(40)]
    txs = {}
    for i in range(3):
        m = addr(f"Coin{i}")
        txs[f"s{2 * i + 1}"] = buy_tx(wallet=cand, mint=m, sol=0.5, block_time=int(now - 86400 + i * 3600))
        txs[f"s{2 * i}"] = sell_tx(wallet=cand, mint=m, sol=0.8, tokens=1_000_000, pre=1_000_000,
                                  block_time=int(now - 86400 + i * 3600 + 7200))

    def rpc(method, params):
        if method == "getSignaturesForAddress":
            return sigs if params[0] == cand else []
        if method == "getTransaction":
            return txs.get(params[0])
        return None
    monkeypatch.setattr(core, "rpc", rpc)

    scout.run()

    rows = list(csv.DictReader(open(scout.CANDIDATES_FILE, encoding="utf-8")))
    assert len(rows) == 1 and rows[0]["wallet"] == cand and rows[0]["ergebnis"] == "bewertet"
    assert float(rows[0]["punkte"]) == pytest.approx(60 - 3)           # +60 % je Coin, lange Haltedauer
    state = json.load(open(scout.STATE_FILE, encoding="utf-8"))
    assert MINT in state["coins_erledigt"] and cand in state["wallets_geprueft"]
    assert any("Wallet-Scout" in t for t, _ in sandbox["discord"])
    adds = git_adds(sandbox["git"])
    assert adds and all(a == (scout.SCOUT_DIR,) for a in adds)          # nur scout/


# ================================================================ Copy-Bot: Abbruch (Fehler C, Pruefbericht 03.10.)
# Am 02.10. wurde eine Schicht von Hand abgebrochen: Das Signal wurde von "except Exception" verschluckt, am Ende
# nicht gespeichert, die Zrool-Position ging verloren und eine 922M-Position wurde doppelt geschlossen.

def copy_shift_setup(clock, market, monkeypatch, script):
    open(cb.WALLET_FILE, "w", encoding="utf-8").write(f"Alpha: {WALLET}\n")
    market.set(MINT, price=PRICE_USD)
    txs = {"live1": buy_tx(sig="live1", block_time=int(clock.now)),
           "live2": sell_tx(sig="live2", tokens=1_000_000, pre=1_000_000, sol=0.6, block_time=int(clock.now) + 5)}

    def rpc(method, params):
        if method == "getTransaction":
            return txs.get(params[0])
        if method == "getSignaturesForAddress":
            return []
        return None
    monkeypatch.setattr(core, "rpc", rpc)
    confirm = json.dumps({"jsonrpc": "2.0", "id": 1, "result": 101})
    ws = FakeWS(clock, [confirm] + script)
    monkeypatch.setattr(cb.websocket, "create_connection", lambda url, timeout=None: ws)
    monkeypatch.setattr(cb, "SHIFT_SECONDS", 30)
    return ws


def sigterm():
    cb._on_signal(signal.SIGTERM, None)


def saved_account():
    return json.load(open(cb.ACCOUNTS_FILE, encoding="utf-8"))["wallets"]["Alpha"]


def test_abbruch_wird_nicht_verschluckt_und_gespeichert(clock, market, monkeypatch, sandbox):
    assert not issubclass(cb.Interrupted, Exception)
    ws = copy_shift_setup(clock, market, monkeypatch, [
        notification("live1"), sigterm, notification("live2", logs=("Program log: Instruction: Sell",))])
    cb.run()                                                     # endet ohne Ausnahme (Sicherung + Kettenstart)
    assert ws.script == [notification("live2", logs=("Program log: Instruction: Sell",))]   # sofort aufgehoert
    acct = saved_account()
    assert MINT in acct["positionen"] and acct["abgedeckt_bis"] > 0       # Kauf gespeichert
    rows = list(csv.DictReader(open(cb.JOURNAL_FILE, encoding="utf-8")))
    assert [r["aktion"] for r in rows] == ["KAUF"]
    assert cb.STATS["errors"] == 0
    titles = [t for t, _ in sandbox["discord"]]
    assert any("Copy-Schicht beendet" in t for t in titles)


def test_abbruch_mitten_im_kauf_bucht_ihn_vollstaendig(clock, market, monkeypatch, sandbox):
    copy_shift_setup(clock, market, monkeypatch, [notification("live1"), notification("live2")])

    def quote_with_signal(*a):
        sigterm()                                                # Signal kommt waehrend der Jupiter-Abfrage
        return market.quote(*a)
    monkeypatch.setattr(cb, "quote_out", quote_with_signal)
    cb.run()
    acct = saved_account()
    pos = acct["positionen"][MINT]
    assert pos["kaeufe"] == 1 and acct["bankroll_sol"] < 10       # Kauf ganz gebucht ...
    rows = list(csv.DictReader(open(cb.JOURNAL_FILE, encoding="utf-8")))
    assert [r["aktion"] for r in rows] == ["KAUF"]               # ... und Journal passt zum Konto
    assert pos["tokens_raw"] > 0
    assert "uebersprungen (Abbruch)" in rows[0]["pruefungen"]    # lange Pruefungen nicht mehr abgewartet


def test_zweites_signal_stoert_das_speichern_nicht(clock, market, monkeypatch, sandbox):
    copy_shift_setup(clock, market, monkeypatch, [notification("live1"), sigterm])
    original = cb.save_accounts
    calls = []

    def save_with_signal(data):
        calls.append(1)
        if len(calls) == 2:                                      # erster Aufruf: Start, zweiter: Ende
            cb._on_signal(signal.SIGINT, None)                   # GitHub schickt noch ein Signal
        original(data)
    monkeypatch.setattr(cb, "save_accounts", save_with_signal)
    cb.run()
    assert len(calls) == 2 and MINT in saved_account()["positionen"]


def test_fehler_in_bereinigung_und_endmeldung_verhindern_speichern_nicht(clock, market, monkeypatch, sandbox):
    copy_shift_setup(clock, market, monkeypatch, [notification("live1")])

    def boom(*a, **kw):
        raise RuntimeError("kaputt")
    monkeypatch.setattr(cb, "cleanup", boom)
    monkeypatch.setattr(cb, "summary", boom)
    cb.run()                                                     # kein Absturz: Kettenstart bleibt erhalten
    assert MINT in saved_account()["positionen"]
    assert "Bereinigung" in cb.STATS["last_error"]


def test_signal_ausserhalb_einer_buchung_bricht_sofort_ab():
    with pytest.raises(cb.Interrupted):
        sigterm()
    cb._stopping[0] = False
    with pytest.raises(cb.Interrupted):
        with cb.booking():
            sigterm()                                            # wird aufgeschoben ...
            assert cb._stop[0] == "SIGTERM"                      # ... bis die Buchung fertig ist
    assert cb._critical[0] == 0 and cb._stop[0] is None
