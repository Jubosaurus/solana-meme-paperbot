"""Hauptstrategie: Kauf und alle Verkaufsregeln (manage_positions)."""
import csv
import os
import time

import pytest

import bot as core
from helpers import MINT

START = 0.0001          # Kurs beim Kauf (USD)


@pytest.fixture
def pos(market):
    """Offene Position ueber open_position, Kaufkurs = Signalkurs (keine Slippage)."""
    market.set(MINT, price=START)
    p = core.load_portfolio()
    v = core.token_view(market.tokens[MINT], time.time())
    assert core.open_position(p, v, {"quelle": "block0", "block0_wallets": 0, "block0_supply_pct": 0.0,
                                     "block0_still_held_pct": 0.0}, market.sol_usd)
    return p


def step(p, market, mult, now=None, loop=None, **tokfields):
    """Ein Durchlauf von manage_positions beim Vielfachen mult des Kaufkurses."""
    market.price[MINT] = START * mult
    for k, v in tokfields.items():
        path = __import__("helpers").FIELDS[k]
        t = market.tokens[MINT]
        for part in path[:-1]:
            t = t.setdefault(part, {})
        t[path[-1]] = v
    if loop is not None:
        core.STATS["loops"] = loop
    else:
        core.STATS["loops"] += 1
    core.manage_positions(p, market.sol_usd, now or time.time())
    return p


def closed_reason(p):
    return p["closed"][-1]["exit_reason"] if p["closed"] else None


def test_kauf_bucht_einsatz_und_gebuehr(pos):
    p = pos
    position = p["positions"][MINT]
    assert p["bankroll_sol"] == pytest.approx(10 - core.POSITION_SOL - core.TX_FEE_SOL)
    assert position["entry_fill_usd"] == pytest.approx(START, rel=1e-6)
    assert position["peak_usd"] == position["entry_fill_usd"]
    rows = list(csv.DictReader(open(core.JOURNAL_FILE, encoding="utf-8")))
    assert rows[0]["aktion"] == "KAUF" and rows[0]["these"].startswith("Story verbreitet sich")


def test_hoch_startet_beim_kaufpreis_nicht_beim_signal(market):
    """Lehre aus 'cum': Kauf 62 % unter dem Signalkurs darf den Gewinnschutz nicht scharf schalten."""
    market.set(MINT, price=START)
    market.buy_slippage[MINT] = 0.38                     # wir bekommen viel mehr Token: Kaufkurs 62 % unter Signal
    p = core.load_portfolio()
    core.open_position(p, core.token_view(market.tokens[MINT], time.time()), {"quelle": "block0",
                       "block0_wallets": 0, "block0_supply_pct": 0, "block0_still_held_pct": 0}, market.sol_usd)
    position = p["positions"][MINT]
    assert position["peak_usd"] == pytest.approx(START * 0.38, rel=1e-3)
    market.buy_slippage.clear()
    step(p, market, 0.38 * 0.95)                          # leicht unter Kaufkurs: kein Gewinnschutz
    assert MINT in p["positions"]


def test_haelfte_bei_2x(pos, market):
    p = step(pos, market, 2.05)
    position = p["positions"][MINT]
    assert position["tp1_done"] is True
    assert position["tokens_left"] == pytest.approx(position["tokens_initial"] / 2)
    assert position["proceeds_sol"] == pytest.approx(0.1 * 2.05 - core.TX_FEE_SOL, rel=1e-4)


def test_trailing_30_prozent_unter_hoch_nach_teilverkauf(pos, market):
    step(pos, market, 2.01)
    step(pos, market, 4.0)
    step(pos, market, 2.85)                              # 28,75 % unter dem Hoch: bleibt
    assert MINT in pos["positions"]
    step(pos, market, 2.79)                              # 30,25 % unter dem Hoch: raus
    assert closed_reason(pos).startswith("STORY_ABGEKUEHLT (30%")


def test_trailing_ab_10x_nur_25_prozent(pos, market):
    step(pos, market, 2.01)
    step(pos, market, 12.0)
    step(pos, market, 9.1)                               # 24 % unter Hoch: bleibt
    assert MINT in pos["positions"]
    step(pos, market, 8.9)                               # 25,8 % unter Hoch: raus
    assert closed_reason(pos).startswith("STORY_ABGEKUEHLT (25%")


def test_kein_trailing_vor_dem_teilverkauf(pos, market):
    step(pos, market, 1.4)
    step(pos, market, 0.9)                               # 36 % unter Hoch, aber noch kein 2x
    assert MINT in pos["positions"]


def test_gewinnschutz_ab_1_5x(pos, market):
    step(pos, market, 1.51)
    step(pos, market, 1.01)
    assert MINT in pos["positions"]
    step(pos, market, 1.0)
    assert closed_reason(pos).startswith("GEWINN_GESCHUETZT")


def test_gewinnschutz_nicht_unter_1_5x(pos, market):
    step(pos, market, 1.49)
    step(pos, market, 0.8)
    assert MINT in pos["positions"]


def test_notbremse_minus_40(pos, market):
    step(pos, market, 0.61)
    assert MINT in pos["positions"]
    step(pos, market, 0.60)
    assert closed_reason(pos) == "NOTBREMSE (-40%)"
    assert pos["closed"][-1]["pnl_sol"] < 0
    assert pos["bankroll_sol"] > 9.8 - 0.1


def test_these_gebrochen_zweimal_in_folge(pos, market):
    step(pos, market, 1.0, loop=3, holder_growth_1h=-5, net_buyers_5m=-2)
    assert MINT in pos["positions"]
    step(pos, market, 1.0, loop=4, holder_growth_1h=-5, net_buyers_5m=-2)   # keine Pruefung in diesem Takt
    assert MINT in pos["positions"]
    step(pos, market, 1.0, loop=6, holder_growth_1h=-5, net_buyers_5m=-2)
    assert closed_reason(pos).startswith("THESE_GEBROCHEN")


def test_these_erholt_sich_setzt_zaehler_zurueck(pos, market):
    step(pos, market, 1.0, loop=3, holder_growth_1h=-5, net_buyers_5m=-2)
    step(pos, market, 1.0, loop=6, holder_growth_1h=5, net_buyers_5m=-2)
    step(pos, market, 1.0, loop=9, holder_growth_1h=-5, net_buyers_5m=-2)
    assert MINT in pos["positions"]


def test_liquiditaet_abgezogen_braucht_zwei_pruefungen(pos, market):
    step(pos, market, 1.0, liquidity=30_000)              # -40 %
    assert MINT in pos["positions"]
    step(pos, market, 1.0, liquidity=30_000)
    assert closed_reason(pos) == "LIQUIDITAET_ABGEZOGEN"


def test_graduation_ist_kein_liquiditaetsabzug(pos, market):
    step(pos, market, 1.2, liquidity=20_000)
    market.tokens[MINT]["graduatedPool"] = "pool"
    step(pos, market, 1.2, liquidity=20_000)
    step(pos, market, 1.2, liquidity=20_000)
    position = pos["positions"][MINT]
    assert position["graduated_during"] is True
    assert position["entry_liquidity"] == 20_000
    assert core.STATS["graduations"] == 1


def test_hoechstdauer_24h(pos, market):
    step(pos, market, 1.1, now=time.time() + 24 * 3600 + 60)
    assert closed_reason(pos) == "MAX_HALTEDAUER"


def test_token_verschwunden_nach_30_durchlaeufen(pos, market):
    del market.tokens[MINT]
    for _ in range(29):
        step(pos, market, 1.0)
    assert MINT in pos["positions"]
    step(pos, market, 1.0)
    assert closed_reason(pos) == "TOKEN_NICHT_MEHR_HANDELBAR"


def test_nach_verkauf_wird_6h_beobachtet_und_aufgezeichnet(pos, market):
    step(pos, market, 0.5)
    assert MINT in pos["watch"]
    step(pos, market, 0.7, loop=3)
    rows = list(csv.DictReader(open(core.verlauf_file(), encoding="utf-8")))
    assert [r["phase"] for r in rows][-1] == "nach_verkauf"
    assert rows[-1]["vielfaches"] == "0.7000"


def test_journal_hat_ergebnis_mit_pnl(pos, market):
    step(pos, market, 0.5)
    rows = list(csv.DictReader(open(core.JOURNAL_FILE, encoding="utf-8")))
    assert [r["aktion"] for r in rows] == ["KAUF", "VERKAUF", "ERGEBNIS"]
    assert float(rows[-1]["pnl_sol"]) < 0


# Pruefbericht 03.10.: ein Jupiter-Ausfall darf nie als "Coin nicht mehr handelbar" gelten
REAL_JUP_TOKENS = core.jup_tokens


def test_jupiter_ausfall_schliesst_keine_position(pos, market, monkeypatch):
    monkeypatch.setattr(core, "jup_tokens", REAL_JUP_TOKENS)
    monkeypatch.setattr(core, "jup_get", lambda path: None)          # Jupiter antwortet gar nicht
    for _ in range(40):
        core.STATS["loops"] += 1
        core.manage_positions(pos, market.sol_usd, time.time())
    assert MINT in pos["positions"] and not pos["closed"]
    assert pos["positions"][MINT]["missing_loops"] == 0


def test_echte_antwort_ohne_coin_schliesst_weiter_nach_30(pos, market, monkeypatch):
    monkeypatch.setattr(core, "jup_tokens", REAL_JUP_TOKENS)
    monkeypatch.setattr(core, "jup_get", lambda path: [])            # Jupiter antwortet, Coin fehlt
    for _ in range(29):
        core.STATS["loops"] += 1
        core.manage_positions(pos, market.sol_usd, time.time())
    assert MINT in pos["positions"]
    core.STATS["loops"] += 1
    core.manage_positions(pos, market.sol_usd, time.time())
    assert closed_reason(pos) == "TOKEN_NICHT_MEHR_HANDELBAR"


def test_ausfall_zaehlt_verschwunden_nicht_weiter(pos, market, monkeypatch):
    """29 echte Antworten ohne Coin, dann Ausfall: Zaehler bleibt stehen, Position bleibt offen."""
    monkeypatch.setattr(core, "jup_tokens", REAL_JUP_TOKENS)
    monkeypatch.setattr(core, "jup_get", lambda path: [])
    for _ in range(29):
        core.manage_positions(pos, market.sol_usd, time.time())
    monkeypatch.setattr(core, "jup_get", lambda path: None)
    for _ in range(10):
        core.manage_positions(pos, market.sol_usd, time.time())
    assert MINT in pos["positions"] and pos["positions"][MINT]["missing_loops"] == 29


# ================================================================ Messung (03.10., nur Aufzeichnung)

def journal_rows_main():
    return list(csv.DictReader(open(core.JOURNAL_FILE, encoding="utf-8")))


def messung_rows_main():
    return list(csv.DictReader(open(core.MESSUNG_FILE, encoding="utf-8")))


def test_messung_quote_2s_in_der_pause_nicht_beim_handel(market, monkeypatch, clock):
    market.set(MINT, price=START)
    p = core.load_portfolio()
    v = core.token_view(market.tokens[MINT], time.time())
    t0 = clock.now
    assert core.open_position(p, v, {"quelle": "block0", "block0_wallets": 0, "block0_supply_pct": 0.0,
                                     "block0_still_held_pct": 0.0}, market.sol_usd)
    assert clock.now == t0                                       # der Kauf wartet nicht auf die Messung
    assert len(core._rechecks) == 1 and not os.path.exists(core.MESSUNG_FILE)
    market.price[MINT] = START * 1.25                            # Kurs steigt in den 2 s: 20 % weniger Token
    core.sleep_with_rechecks(12)
    assert clock.now == pytest.approx(t0 + 12)                   # Pause wird nicht laenger
    row = messung_rows_main()[0]
    assert row["konto"] == "hauptstrategie" and row["aktion"] == "KAUF" and row["abweichung_pct"] == "+20.00"
    assert float(row["sekunden"]) == pytest.approx(2.0)

    pos = p["positions"][MINT]
    t1 = clock.now
    core.close_position(p, pos, START * 1.25, "TEST", market.sol_usd)
    assert clock.now == t1                                       # Verkauf (z. B. Notbremse) wartet nicht
    assert p["closed"][0]["proceeds_sol"] == pytest.approx(0.25 - core.TX_FEE_SOL, rel=1e-4)
    market.price[MINT] = START                                   # 20 % billiger: 20 % weniger SOL
    core.sleep_with_rechecks(12)
    row = messung_rows_main()[-1]
    assert row["aktion"] == "VERKAUF" and row["abweichung_pct"] == "+20.00"
    assert len(core.STATS["quote_2s"]) == 2


def test_messung_im_experiment_mit_kontoname(market, clock):
    market.set(MINT, price=START)
    with core.experiment("kontrollgruppe"):
        p = core.load_portfolio()
        core.open_position(p, core.token_view(market.tokens[MINT], time.time()),
                           {"quelle": "experiment", "text": "Test"}, market.sol_usd)
    core.sleep_with_rechecks(12)
    assert messung_rows_main()[0]["konto"] == "kontrollgruppe"


def test_messung_zu_spaet_oder_ohne_quote_verworfen(pos, market, monkeypatch, clock):
    core._rechecks[0] = (clock.now - 20,) + core._rechecks[0][1:]   # Kauf-Messung laengst ueberfaellig
    core.sleep_with_rechecks(12)
    assert core.STATS["messung_verworfen"] == 1 and not os.path.exists(core.MESSUNG_FILE)
    core.schedule_recheck("VERKAUF", "X", MINT, core.WSOL_MINT, 100, 50, clock.now)
    monkeypatch.setattr(core, "quote", lambda *a: 0)
    core.sleep_with_rechecks(12)
    assert core.STATS["messung_verworfen"] == 2 and not os.path.exists(core.MESSUNG_FILE)


def test_notloesung_wird_gezaehlt_und_vermerkt(pos, market, monkeypatch):
    monkeypatch.setattr(core, "quote", lambda *a: 0)                       # keine Quote beim Verkauf
    core.close_position(pos, pos["positions"][MINT], START, "TEST", market.sol_usd)
    row = [r for r in journal_rows_main() if r["aktion"] == "VERKAUF"][0]
    assert row["notloesung"] == "1"
    assert core.STATS["notloesung"] == 1


def test_alte_journale_bekommen_neue_spalten_hinten(market):
    old = ["zeit", "aktion", "symbol", "mint", "preis_usd", "sol", "these", "verkaufsbedingung", "grund",
           "pnl_sol", "pnl_pct"]
    with open(core.JOURNAL_FILE, "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerows([old, ["2026-10-01 00:00:00", "KAUF", "X", "m", "1", "0.2", "", "", "", "", ""]])
    core.ensure_csv_columns(core.JOURNAL_FILE, core.JOURNAL_HEADER)
    rows = list(csv.reader(open(core.JOURNAL_FILE, encoding="utf-8")))
    assert rows[0] == core.JOURNAL_HEADER and rows[0][:11] == old and len(rows[1]) == len(core.JOURNAL_HEADER)


# ================================================================ DexScreener-Beobachtung (04.10., nur Aufzeichnung)

def dex_rows():
    return list(csv.DictReader(open(core.DEX_FILE, encoding="utf-8")))


def test_dexscreener_beim_kauf_in_der_pause(market, monkeypatch, clock):
    antworten = []

    def dex_get(path):
        antworten.append(path)
        return {"orders": [{"type": "tokenProfile", "status": "approved",
                            "paymentTimestamp": (clock.now - 600) * 1000},
                           {"type": "tokenAd", "status": "approved", "paymentTimestamp": (clock.now - 60) * 1000}],
                "boosts": [{"amount": 10, "paymentTimestamp": (clock.now - 120) * 1000}]}
    monkeypatch.setattr(core, "dex_get", dex_get)
    market.set(MINT, price=START)
    p = core.load_portfolio()
    v = core.token_view(market.tokens[MINT], time.time())
    t0 = clock.now
    core.open_position(p, v, {"quelle": "block0", "block0_wallets": 0, "block0_supply_pct": 0.0,
                              "block0_still_held_pct": 0.0}, market.sol_usd)
    assert clock.now == t0 and antworten == []                 # Kauf wartet nicht auf DexScreener
    core.sleep_with_rechecks(12)
    assert antworten == [f"/orders/v1/solana/{MINT}"]
    r = dex_rows()[0]
    assert r["art"] == "kauf" and r["konto"] == "hauptstrategie" and r["profil"] == "1" and r["werbung"] == "1"
    assert r["boosts"] == "1" and r["erste_zahlung_min_vor_ereignis"] == "10.0"
    assert r["letzte_zahlung_min_vor_ereignis"] == "1.0"
    assert clock.now == pytest.approx(t0 + 12)                 # Pause wird nicht laenger


def test_dexscreener_ohne_antwort_und_nur_einmal_je_coin(market, monkeypatch, clock):
    market.set(MINT, price=START)
    v = core.token_view(market.tokens[MINT], time.time())
    core.dex_vormerken("knapp_abgelehnt", v, "FOMO_SPRUNG")
    core.dex_vormerken("knapp_abgelehnt", v, "FOMO_SPRUNG")    # derselbe Coin: nur einmal in 6 h
    assert len(core._dex_queue) == 1
    core.sleep_with_rechecks(12)                               # dex_get liefert im Test None
    r = dex_rows()[0]
    assert r["fehler"] == "keine Antwort" and r["grund"] == "FOMO_SPRUNG" and core.STATS["dex_fehler"] == 1


# ================================================================ Flugschreiber (04.10., nur Aufzeichnung)

def flug_rows():
    import glob
    return [r for f in sorted(glob.glob(os.path.join(core.FLUG_DIR, "*.csv")))
            for r in csv.DictReader(open(f, encoding="utf-8"))]


def test_flugschreiber_jede_minute_mit_bundler_bestand(market, monkeypatch, clock):
    market.set(MINT, price=START)
    core._block0_cache[MINT] = {"supply": 1e9, "bought": {"w1": 2e8, "w2": 1e8, "w3": 5e7}}
    abfragen = []

    def rpc(method, params):
        abfragen.append(params[0])
        menge = {"w1": 2e8, "w2": 0, "w3": 5e7}[params[0]]          # w2 ist ausgestiegen
        return {"value": [{"account": {"data": {"parsed": {"info": {"tokenAmount": {"amount": str(int(menge))}}}}}}]}
    monkeypatch.setattr(core, "rpc", rpc)
    p = core.load_portfolio()
    core.open_position(p, core.token_view(market.tokens[MINT], time.time()),
                       {"quelle": "block0", "block0_wallets": 3, "block0_supply_pct": 35.0,
                        "block0_still_held_pct": 35.0}, market.sol_usd)
    pos = p["positions"][MINT]
    assert set(pos["block0_flug"]["bought"]) == {"w1", "w2", "w3"}
    for _ in range(3):                                         # 3 Durchlaeufe in derselben Minute: 1 Zeile
        core.manage_positions(p, market.sol_usd, time.time())
        clock.sleep(12)
    rows = flug_rows()
    assert len(rows) == 1
    r = rows[0]
    assert r["konto"] == "hauptstrategie" and r["block0_gehalten_pct"] == "25.0" and r["block0_ausgestiegen"] == "1"
    assert r["holder"] and r["liquiditaet"] and r["top10_pct"] != ""
    clock.sleep(60)
    core.manage_positions(p, market.sol_usd, time.time())      # naechste Minute: neue Zeile, Bundler aus dem Speicher
    assert len(flug_rows()) == 2 and len(abfragen) == 3        # Helius erst wieder nach 10 min
    clock.sleep(600)
    core.manage_positions(p, market.sol_usd, time.time())
    assert len(abfragen) == 6


def test_flugschreiber_ohne_bundler_daten_und_ohne_helius(pos, market, clock):
    core.manage_positions(pos, market.sol_usd, time.time())
    r = flug_rows()[0]
    assert r["block0_gehalten_pct"] == "" and r["mint"] == MINT
