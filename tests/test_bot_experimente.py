"""Experimente: Endspurt-Regeln, Kontrollgruppe, Zweite Welle, Heisse Coins, Ohne Limit, Neustart der Konten."""
import os
import time

import pytest

import bot as core
from helpers import tok, addr, price_for_vsol, MINT, MINT2

SOL = 100.0


def endspurt_view(market, mint=MINT, vsol=100, trades=2500, dev=None, **kw):
    t = market.set(mint, price=price_for_vsol(vsol, SOL), trades_24h=trades, **kw)
    if dev:
        t["dev"] = dev
    return core.token_view(t, time.time())


def load(name):
    with core.experiment(name):
        return core.load_portfolio()


# ================================================================ Endspurt

def test_curve_vsol_rechnet_preis_zurueck():
    assert core.curve_vsol(price_for_vsol(100, SOL), SOL) == pytest.approx(100)
    assert core.curve_vsol(0, SOL) is None


@pytest.mark.parametrize("vsol, ok", [(94.5, False), (95.5, True), (107.5, True), (108.5, False)])
def test_endspurt_fenster(market, vsol, ok):
    v = endspurt_view(market, vsol=vsol)
    assert (core.endspurt_candidate(v, SOL) is not None) == ok


def test_endspurt_nur_pumpfun_auf_der_kurve_und_sicher(market):
    assert core.endspurt_candidate(endspurt_view(market, launchpad="other"), SOL) is None
    assert core.endspurt_candidate(endspurt_view(market, graduated=True), SOL) is None
    assert core.endspurt_candidate(endspurt_view(market, freeze_disabled=False), SOL) is None


def test_endspurt_filter_mindestens_2000_trades(market):
    assert core.endspurt_filters_ok(endspurt_view(market, trades=2000))
    assert not core.endspurt_filters_ok(endspurt_view(market, trades=1999))


def test_endspurt_mit_und_ohne_filter(market):
    views = [endspurt_view(market, MINT, trades=2500, dev=addr("DevA")),
             endspurt_view(market, MINT2, vsol=101, trades=300, dev=addr("DevB"))]
    for name, filt in (("endspurt", True), ("endspurt_ohne_filter", False)):
        ep = load(name)
        with core.experiment(name):
            core.endspurt_picks(ep, views, SOL, time.time(), filt)
        assert set(ep["positions"]) == ({MINT} if filt else {MINT, MINT2})
        pos = ep["positions"][MINT]
        assert pos["exit_mode"] == "endspurt" and pos["entry_vsol"] == pytest.approx(100, abs=0.01)
    assert os.path.exists("experimente/endspurt/journal.csv")
    assert not os.path.exists("journal.csv")                  # Hauptstrategie unberuehrt


def test_endspurt_derselbe_dev_nur_einmal_am_tag(market):
    dev = addr("DevA")
    views = [endspurt_view(market, MINT, dev=dev), endspurt_view(market, MINT2, vsol=101, dev=dev)]
    ep = load("endspurt_ohne_filter")
    with core.experiment("endspurt_ohne_filter"):
        core.endspurt_picks(ep, views, SOL, time.time(), False)
    assert len(ep["positions"]) == 1


def test_endspurt_kein_kauf_bei_mehr_als_3_prozent_slippage(market):
    v = endspurt_view(market)
    market.buy_slippage[MINT] = 1.04
    ep = load("endspurt_ohne_filter")
    with core.experiment("endspurt_ohne_filter"):
        core.endspurt_picks(ep, [v], SOL, time.time(), False)
    assert ep["positions"] == {}


@pytest.fixture
def endspurt_pos(market):
    v = endspurt_view(market)
    ep = load("endspurt_ohne_filter")
    with core.experiment("endspurt_ohne_filter"):
        core.endspurt_picks(ep, [v], SOL, time.time(), False)
    assert MINT in ep["positions"]
    return ep


def manage(ep, market, vsol=None, now=None, graduated=False):
    if vsol is not None:
        market.price[MINT] = price_for_vsol(vsol, SOL)
    if graduated:
        market.tokens[MINT]["graduatedPool"] = "pool"
    core.STATS["loops"] += 1
    with core.experiment("endspurt_ohne_filter"):
        core.manage_positions(ep, SOL, now or time.time())
    return ep["closed"][-1]["exit_reason"] if ep["closed"] else None


def test_endspurt_raus_bei_graduation(endspurt_pos, market):
    assert manage(endspurt_pos, market, vsol=110, graduated=True).startswith("GRADUIERT")


def test_endspurt_kein_teilverkauf_bei_2x(endspurt_pos, market):
    assert manage(endspurt_pos, market, vsol=142) is None              # 2x, aber eigene Regeln
    assert endspurt_pos["positions"][MINT]["tp1_done"] is False


def test_endspurt_kurve_zurueck(endspurt_pos, market):
    assert manage(endspurt_pos, market, vsol=88.5) is None
    assert manage(endspurt_pos, market, vsol=87.5).startswith("KURVE_ZURUECK")


def test_endspurt_zeit_stop(endspurt_pos, market):
    assert manage(endspurt_pos, market, now=time.time() + 46 * 60).startswith("ZEIT_STOP")


def test_endspurt_notbremse(endspurt_pos, market):
    # -40 % ohne 12 vSol Rueckfall geht nicht (Preis ~ vSol^2); Notbremse wird vorher geprueft
    assert manage(endspurt_pos, market, vsol=77).startswith("NOTBREMSE")


# ================================================================ Konten und Kontrollgruppe

def test_neue_runde_wenn_konto_leer():
    ep = {"bankroll_sol": 0.1, "positions": {}, "runde": 1}
    with core.experiment("kontrollgruppe"):
        core.check_reset(ep)
    assert ep["runde"] == 2 and ep["bankroll_sol"] == 10.0
    ep = {"bankroll_sol": 0.1, "positions": {"x": {}}, "runde": 1}
    core.check_reset(ep)
    assert ep["runde"] == 1


def test_kontrollgruppe_kauft_hoechstens_alle_30_minuten(market):
    now = time.time()
    views = [core.token_view(market.set(MINT), now), core.token_view(market.set(MINT2), now)]
    ep = load("kontrollgruppe")
    with core.experiment("kontrollgruppe"):
        core.control_group_pick(ep, views, SOL, now)
        core.control_group_pick(ep, views, SOL, now + 60)
    assert len(ep["positions"]) == 1
    assert ep["next_pick"] == pytest.approx(now + 30 * 60)
    with core.experiment("kontrollgruppe"):
        core.control_group_pick(ep, views, SOL, now + 31 * 60)
    assert len(ep["positions"]) == 2


def test_kontrollgruppe_nur_sicherheitspruefungen(market):
    """Holder-Wachstum ist egal, unsicherer Contract nicht."""
    assert core.control_safe(core.token_view(tok(holder_growth_1h=-50), time.time()))
    assert not core.control_safe(core.token_view(tok(mint_disabled=False), time.time()))
    assert not core.control_safe(core.token_view(tok(age_h=7), time.time()))


def test_zweite_welle_nach_notbremse(market):
    market.set(MINT, price=0.0002)
    main = {"watch": {MINT: {"symbol": "TEST", "entry_fill_usd": 0.00019, "exit_reason": "NOTBREMSE (-45%)",
                             "until": time.time() + 3600}}}
    ep = load("zweite_welle")
    with core.experiment("zweite_welle"):
        core.second_wave_entries(main, ep, SOL, time.time())
    assert MINT in ep["positions"]
    main["watch"][MINT]["entry_fill_usd"] = 0.00021                         # noch unter dem Einstieg
    ep2 = {"bankroll_sol": 10, "positions": {}, "closed": [], "cooldown": {}, "watch": {}}
    with core.experiment("zweite_welle"):
        core.second_wave_entries(main, ep2, SOL, time.time())
    assert ep2["positions"] == {}


# ================================================================ Scan: Hauptstrategie und Experimente

@pytest.fixture
def scan_env(market, monkeypatch):
    lists = {}

    def jup_get(path):
        if path.startswith("/tokens/v2/top"):
            return list(lists.values())
        if path.startswith("/ultra/v1/shield"):
            return {"warnings": {}}
        return None
    monkeypatch.setattr(core, "jup_get", jup_get)

    def add(mint, **kw):
        lists[mint] = market.set(mint, **kw)
    return add


def bundle_ok(monkeypatch, reason=None):
    monkeypatch.setattr(core, "bundle_dev_check", lambda mint: (reason, {
        "quelle": "block0", "block0_wallets": 0, "block0_supply_pct": 0.0, "block0_still_held_pct": 0.0}))


def test_scan_kauft_guten_coin_und_nicht_den_fomo_coin(scan_env, monkeypatch):
    bundle_ok(monkeypatch)
    scan_env(MINT)
    scan_env(MINT2, price_change_5m=60)
    p = core.load_portfolio()
    core.scan(p, SOL, time.time(), {})
    assert set(p["positions"]) == {MINT}
    assert p["shadow"][MINT2]["reason"] == "FOMO_SPRUNG"


def test_ohne_limit_kauft_wenn_hauptstrategie_voll_ist(scan_env, monkeypatch):
    """Mechanik (seit 04.10. beendet, siehe test_beendete_experimente_kaufen_nicht_mehr)."""
    monkeypatch.setattr(core, "EXP_BEENDET", {})
    bundle_ok(monkeypatch)
    scan_env(MINT)
    p = core.load_portfolio()
    p["positions"] = {"a": {}, "b": {}}                                   # Marktphase normal: 2 Plaetze belegt
    exps = {"ohne_limit": load("ohne_limit")}
    core.scan(p, SOL, time.time(), exps)
    assert set(exps["ohne_limit"]["positions"]) == {MINT}
    assert set(p["positions"]) == {"a", "b"}
    assert p["shadow"][MINT]["detail"] == "alle Pruefungen bestanden, Positionslimit erreicht"


def test_heisse_coins_kauft_ohne_moeglichen_bundle_check(scan_env, monkeypatch):
    bundle_ok(monkeypatch, "BUNDLE_CHECK_NICHT_MOEGLICH")
    scan_env(MINT)
    p = core.load_portfolio()
    exps = {"heisse_coins": load("heisse_coins")}
    core.scan(p, SOL, time.time(), exps)
    assert set(exps["heisse_coins"]["positions"]) == {MINT}
    assert p["positions"] == {}


def test_kaputtes_experiment_stoppt_die_hauptstrategie_nicht(scan_env, monkeypatch):
    bundle_ok(monkeypatch)
    scan_env(MINT)
    os.makedirs("experimente/ohne_limit")
    open("experimente/ohne_limit/portfolio.json", "w").write("{kaputt")
    exps = core.load_experiments()
    assert "ohne_limit" not in exps and core.EXP_STATS["ohne_limit"]["exp_errors"] == 1
    p = core.load_portfolio()
    core.scan(p, SOL, time.time(), exps)
    assert MINT in p["positions"]


def test_unlesbares_portfolio_wird_nie_ueberschrieben(sandbox):
    open(core.PORTFOLIO_FILE, "w").write("{kaputt")
    with pytest.raises(RuntimeError):
        core.load_portfolio()
    assert open(core.PORTFOLIO_FILE).read() == "{kaputt"
    assert "unlesbar" in sandbox["discord"][0][0]


# ================================================================ Beendete Experimente und Notbremse 25 (04.10.)

def test_beendete_experimente_kaufen_nicht_mehr(scan_env, monkeypatch):
    assert set(core.EXP_BEENDET) == {"endspurt_ohne_filter", "ohne_limit"}
    bundle_ok(monkeypatch)
    scan_env(MINT)
    gerufen = []
    monkeypatch.setattr(core, "endspurt_picks", lambda ep, views, sol, now, filt: gerufen.append(filt))
    p = core.load_portfolio()
    p["positions"] = {"a": {}, "b": {}}                                   # Hauptstrategie voll
    exps = {n: load(n) for n in ("ohne_limit", "endspurt", "endspurt_ohne_filter")}
    core.scan(p, SOL, time.time(), exps)
    assert exps["ohne_limit"]["positions"] == {}
    assert gerufen == [True]                                              # nur "Endspurt viele Trades"


def test_beendetes_experiment_laesst_offene_positionen_auslaufen(endspurt_pos, market):
    ep = endspurt_pos
    ep["bankroll_sol"] = 0.05                                             # fast leer: keine neue Runde mehr
    market.price[MINT] = price_for_vsol(120, SOL)
    t = market.tokens[MINT]
    t["graduatedPool"] = "pool"
    core.manage_experiments(core.load_portfolio(), {"endspurt_ohne_filter": ep}, SOL, time.time())
    assert ep["positions"] == {} and ep["closed"][-1]["exit_reason"].startswith("GRADUIERT")
    assert ep.get("runde", 1) == 1                                        # check_reset nicht mehr aufgerufen
    assert "beendet" in " ".join(core.experiment_lines())


def test_notbremse_25_kauft_wie_hauptstrategie_und_bremst_frueher(scan_env, monkeypatch, market):
    bundle_ok(monkeypatch)
    scan_env(MINT)
    p = core.load_portfolio()
    exps = {"notbremse_25": load("notbremse_25")}
    core.scan(p, SOL, time.time(), exps)
    ep = exps["notbremse_25"]
    assert set(p["positions"]) == {MINT} and set(ep["positions"]) == {MINT}
    assert ep["positions"][MINT]["stop_pct"] == -25.0 and "stop_pct" not in p["positions"][MINT]
    assert "-25%" in ep["positions"][MINT]["exit_rule"] and "-40%" in p["positions"][MINT]["exit_rule"]
    market.price[MINT] *= 0.70                                            # -30 %
    core.manage_positions(p, SOL, time.time())
    core.manage_experiments(p, exps, SOL, time.time())
    assert MINT in p["positions"]                                         # Hauptstrategie: -40 % noch nicht erreicht
    assert ep["positions"] == {} and ep["closed"][-1]["exit_reason"].startswith("NOTBREMSE")


def test_notbremse_25_kauft_nicht_ohne_kauf_der_hauptstrategie(scan_env, monkeypatch):
    bundle_ok(monkeypatch)
    scan_env(MINT)
    p = core.load_portfolio()
    p["positions"] = {"a": {}, "b": {}}                                   # Hauptstrategie voll -> kein Kauf
    exps = {"notbremse_25": load("notbremse_25")}
    core.scan(p, SOL, time.time(), exps)
    assert exps["notbremse_25"]["positions"] == {}
