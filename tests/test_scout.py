"""Wallet-Scout: Stufe 1, Stufe 2, Bewertung, Pruefliste, Gewinner-Coins, Birdeye-Filter."""
import csv
import json
import os
import time

import pytest

import bot as core
import copy_bot as cb
import scout_bot as scout
from helpers import buy_tx, sell_tx, tok, addr, WALLET, MINT, MINT2

NOW = time.time()


def sigs(n, per_h=10.0, failed=0.0, last_ago_h=1.0):
    """n Signaturen, neueste zuerst, gleichmaessig im Takt per_h, Anteil failed fehlgeschlagen."""
    out = []
    for i in range(n):
        out.append({"signature": f"sig{i}", "blockTime": int(NOW - last_ago_h * 3600 - i * 3600 / per_h),
                    "err": {"x": 1} if i < n * failed else None})
    return out


@pytest.fixture
def chain(monkeypatch):
    state = {"sigs": {}, "txs": {}}

    def rpc(method, params):
        if method == "getSignaturesForAddress":
            return state["sigs"].get(params[0], [])
        if method == "getTransaction":
            return state["txs"].get(params[0])
        return None
    monkeypatch.setattr(core, "rpc", rpc)
    return state


# ================================================================ Stufe 1

@pytest.mark.parametrize("kw, grund", [
    ({"n": 15}, "zu wenig Transaktionen"),
    ({"n": 200, "failed": 0.85}, "Bot (viele fehlgeschlagene Transaktionen)"),
    ({"n": 200, "failed": 0.6, "per_h": 100}, "Bot (viele fehlgeschlagene Transaktionen)"),
    ({"n": 200, "failed": 0.6, "per_h": 10}, None),                  # Mensch mit Wiederholungen (Eshi)
    ({"n": 1000, "per_h": 400}, "Bot (zu hoher Takt)"),
    ({"n": 100, "last_ago_h": 30}, "still (laenger als 24 h kein Trade)"),
])
def test_stufe1(chain, kw, grund):
    chain["sigs"][WALLET] = sigs(**kw)
    assert scout.stage1(WALLET, NOW)[1] == grund


def test_stufe1_pruefliste_erlaubt_72h_pause(chain):
    chain["sigs"][WALLET] = sigs(100, last_ago_h=48)
    assert scout.stage1(WALLET, NOW, scout.LIST_MAX_IDLE_H)[1] is None


def test_zeitfenster_7_tage(chain):
    page = sigs(30, per_h=0.1)                                       # alle 10 h eine: 300 h zurueck
    got = scout.window_sigs(WALLET, page, NOW, 150)
    assert 0 < len(got) < 30
    assert all(s["blockTime"] >= NOW - 7 * 86400 for s in page if s["signature"] in got)


# ================================================================ Stufe 2 und Bewertung

def add_trades(chain, monkeypatch, price_c_usd):
    t0 = int(NOW - 3 * 86400)
    mint_c = addr("MintC")
    plan = [
        ("a1", buy_tx(mint=MINT, sol=1.0, tokens=1_000_000, block_time=t0)),
        ("a2", sell_tx(mint=MINT, sol=2.0, tokens=1_000_000, pre=1_000_000, block_time=t0 + 30 * 60)),
        ("b1", buy_tx(mint=MINT2, sol=1.0, tokens=1_000_000, block_time=t0 + 3600)),
        ("b2", sell_tx(mint=MINT2, sol=0.5, tokens=1_000_000, pre=1_000_000, block_time=t0 + 3600 + 20 * 60)),
        ("c1", buy_tx(mint=mint_c, sol=1.0, tokens=1_000_000, block_time=t0 + 7200)),
    ]
    for sig, tx in plan:
        chain["txs"][sig] = tx
    monkeypatch.setattr(cb, "jup", lambda path: [tok(mint=mint_c, price=price_c_usd)] if mint_c in path else [])
    return [s for s, _ in plan]


def test_stufe2_rendite_mit_gehaltenem_coin_zum_kurs(chain, monkeypatch):
    s = add_trades(chain, monkeypatch, price_c_usd=1.5e-4)          # 1,5e-6 SOL je Token: 1,5 SOL Wert
    r = scout.stage2(WALLET, s, 100.0)
    assert r["coins"] == 3 and r["coins_gehalten"] == 1 and r["coins_abgeschlossen"] == 2
    assert r["gewinn_sol"] == pytest.approx(1.0)
    assert r["rendite_pct"] == pytest.approx(33.3, abs=0.1)
    assert r["rendite_ohne_besten_pct"] == pytest.approx(0.0)
    assert r["trefferquote"] == pytest.approx(0.67, abs=0.01)
    assert r["haltedauer_median_min"] == pytest.approx(25.0)
    assert r["reibung_pp"] == 6.0
    assert scout.score(r) == pytest.approx(-6.0)


def test_stufe2_gehaltener_coin_ohne_kurs_zaehlt_null(chain, monkeypatch):
    s = add_trades(chain, monkeypatch, price_c_usd=0)
    r = scout.stage2(WALLET, s, 100.0)
    assert r["gewinn_sol"] == pytest.approx(-0.5)


@pytest.mark.parametrize("s2, punkte", [
    ({"coins": 2, "rendite_ohne_besten_pct": 50, "reibung_pp": 3}, None),
    ({"coins": 5, "rendite_ohne_besten_pct": 20, "reibung_pp": 3, "anteil_kaeufe_ab_0_1": 1.0}, 17),
    ({"coins": 5, "rendite_ohne_besten_pct": 20, "reibung_pp": 10, "anteil_kaeufe_ab_0_1": 1.0,
      "mini_verkaeufe_anteil": 0.8}, 0),
    ({"coins": 5, "rendite_ohne_besten_pct": 20, "reibung_pp": 6, "anteil_kaeufe_ab_0_1": 0.2}, 4),
    ({"coins": 5, "rendite_ohne_besten_pct": None, "reibung_pp": 6}, None),
])
def test_bewertung(s2, punkte):
    assert scout.score(s2) == punkte


def test_reibung_nach_haltedauer(chain, monkeypatch):
    t0 = int(NOW - 86400)
    for i in range(3):                                              # drei schnelle Trades (2 min)
        chain["txs"][f"k{i}"] = buy_tx(mint=addr(f"Q{i}"), sol=0.5, block_time=t0 + i * 600)
        chain["txs"][f"v{i}"] = sell_tx(mint=addr(f"Q{i}"), sol=0.6, tokens=1_000_000, pre=1_000_000,
                                        block_time=t0 + i * 600 + 120)
    r = scout.stage2(WALLET, list(chain["txs"]), 100.0)
    assert r["reibung_pp"] == 10.0


# ================================================================ Pruefliste

def test_pruefliste_formate():
    os.makedirs("scout")
    a, b, c = addr("ListA"), addr("ListB"), addr("ListC")
    open(scout.LIST_FILE, "w", encoding="utf-8").write(
        f"# Kommentar\nHaru: {a}\n{b}\n['{c}', '{a}']\n")
    assert scout.load_list() == [("Haru", a), (b[:6], b), (c[:6], c)]


def test_pruefliste_nur_einmal_ausser_bei_neuer_bewertung(monkeypatch):
    os.makedirs("scout")
    open(scout.LIST_FILE, "w", encoding="utf-8").write(f"Haru: {addr('ListA')}\n")
    calls = []
    monkeypatch.setattr(scout, "stage1", lambda w, now, idle=None: (calls.append(w) or {"_page": []}, "still"))
    state = scout.load_state()
    rows, lines = scout.check_list(state, NOW, 100.0)
    assert len(rows) == 1 and rows[0]["ergebnis"] == "raus" and lines[0].startswith("❌")
    assert scout.check_list(state, NOW, 100.0) == ([], [])
    monkeypatch.setattr(scout, "SCORING_VERSION", scout.SCORING_VERSION + "x")
    assert len(scout.check_list(state, NOW, 100.0)[0]) == 1
    assert len(calls) == 2


# ================================================================ Kandidaten finden

def test_gewinner_coins_aus_eigenen_daten():
    json.dump({"closed": [
        {"mint": MINT, "symbol": "WIN", "peak_multiple": 4.0, "closed_at": "2999-01-01T00:00:00+00:00"},
        {"mint": MINT2, "symbol": "LOSE", "peak_multiple": 1.5, "closed_at": "2999-01-01T00:00:00+00:00"},
        {"mint": addr("Alt"), "symbol": "ALT", "peak_multiple": 9, "closed_at": "2000-01-01T00:00:00+00:00"}]},
        open("portfolio.json", "w"))
    os.makedirs("copy/verlauf")
    day = time.strftime("%Y-%m-%d", time.gmtime(NOW))
    with open(f"copy/verlauf/{day}.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["zeit", "mint", "symbol", "vielfaches"])
        w.writerow(["x", addr("Copy"), "CPY", "5.5"])
    state = {"coins_erledigt": {}}
    coins = scout.winner_coins(state, NOW)
    assert [c[1] for c in coins] == ["CPY", "WIN"]
    state["coins_erledigt"][addr("Copy")] = NOW
    assert [c[1] for c in scout.winner_coins(state, NOW)] == ["WIN"]


def test_birdeye_filter(monkeypatch):
    items = [{"owner": addr("Good"), "tags": [], "totalPnl": 50},
             {"owner": addr("Sniper"), "tags": ["sniper"], "totalPnl": 500},
             {"owner": addr("Bundle"), "tags": ["Bundler"], "totalPnl": 500},
             {"owner": addr("Loser"), "tags": [], "realizedPnl": 100, "unrealizedPnl": -200},
             {"owner": addr("Held"), "tags": [], "realizedPnl": -10, "unrealizedPnl": 100}]
    monkeypatch.setattr(scout, "birdeye_get", lambda *a: {"data": {"items": items}})
    assert scout.birdeye_top_traders(MINT, {}) == [addr("Good"), addr("Held")]


def test_birdeye_stoppt_an_der_monatsgrenze(monkeypatch):
    monkeypatch.setattr(scout, "BIRDEYE_API_KEY", "test")
    state = {"birdeye": {"monat": time.strftime("%Y-%m", time.gmtime()), "cu": 27_990}}
    assert scout.birdeye_get("/x", state, 35) is None                # kein Netzwerkzugriff
    assert "Monatsgrenze" in scout.STATS["birdeye_fehler"]


def test_bekannte_wallets_inkl_auskommentierter():
    open(cb.WALLET_FILE, "w", encoding="utf-8").write(
        f"Alpha: {WALLET}\n# Weg: {addr('Weg')} (entfernt 02.10., Bot)\n")
    assert {WALLET, addr("Weg")} <= scout.known_wallets()


def test_fruehe_kaeufer_ohne_ersten_block(chain):
    first, early = addr("Bundler"), addr("Frueh")
    chain["sigs"][MINT] = [{"signature": "e1", "slot": 12, "err": None},
                           {"signature": "b0", "slot": 10, "err": None}]          # neueste zuerst
    chain["txs"]["b0"] = buy_tx(wallet=first, sol=1.0)
    chain["txs"]["e1"] = buy_tx(wallet=early, sol=0.5)
    assert scout.early_buyers(MINT, 100.0) == [early]


def test_fruehe_kaeufer_nur_wenn_start_erreichbar(chain):
    chain["sigs"][MINT] = [{"signature": f"s{i}", "slot": 99, "err": None} for i in range(1000)]
    assert scout.early_buyers(MINT, 100.0) == []
    assert scout.STATS["coins_zu_aktiv"] == 1
