"""Hauptstrategie: Kauf und alle Verkaufsregeln (manage_positions)."""
import csv
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
