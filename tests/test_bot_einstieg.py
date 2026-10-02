"""Hauptstrategie: Token-Kennzahlen, Schnellpruefungen (inkl. Tag 17 FOMO), knapp abgelehnt, Bundle-Check."""
import csv
import time

import pytest

import bot as core
from helpers import tok, view, addr, MINT, MINT2


def test_tok_liefert_alle_felder_fuer_token_view():
    v = core.token_view(tok(), time.time())
    for key in core.ENTRY_FEATURES:
        if key == "quelle":                       # wird erst im Scan gesetzt
            continue
        assert v.get(key) is not None, key
    assert v["age_h"] == pytest.approx(1.0, abs=0.01)
    assert v["trades_24h"] == 500
    assert v["social"] is True


def test_standard_coin_besteht_schnellpruefungen():
    assert core.quick_checks(view()) is None


@pytest.mark.parametrize("kw, grund", [
    ({"age_h": None}, "KEIN_ALTER"),
    ({"age_h": 0.2}, "ZU_JUNG"),
    ({"age_h": 6.5}, "STORY_ZU_ALT"),
    ({"mcap": 3_500_000}, "SCHON_GELAUFEN"),
    ({"age_h": 3, "price_change_1h": 200}, "SCHON_GELAUFEN"),
    ({"dev_mints": 51}, "DEV_VERDAECHTIG"),
    ({"dev_balance_pct": 11}, "DEV_VERDAECHTIG"),
    ({"holder_growth_1h": 14}, "VERBREITUNG_STOCKT"),
    ({"holder_growth_5m": 0}, "VERBREITUNG_STOCKT"),
    ({"net_buyers_5m": 0}, "KEINE_ECHTEN_KAEUFER"),
    ({"organic_buyers_5m": 2}, "KEINE_ECHTEN_KAEUFER"),
    ({"organic_score": 29}, "NICHT_ORGANISCH"),
    ({"liquidity": 4_000}, "LIQUIDITAET_ZU_GERING"),
    ({"symbol": "USDC"}, "NACHAHMER_SYMBOL"),
    ({"mint_disabled": False}, "UNSICHERER_CONTRACT"),
    ({"freeze_disabled": False}, "UNSICHERER_CONTRACT"),
    ({"is_sus": True}, "UNSICHERER_CONTRACT"),
    ({"price_change_5m": 30.1}, "FOMO_SPRUNG"),
])
def test_schnellpruefung_ablehnungsgruende(kw, grund):
    assert core.quick_checks(view(**kw)) == grund


def test_chase_check_erst_ab_2_stunden():
    assert core.quick_checks(view(age_h=1.5, price_change_1h=400)) is None


def test_fomo_grenze_genau_30_prozent_ist_erlaubt():
    assert core.quick_checks(view(price_change_5m=30.0)) is None
    assert core.quick_checks(view(price_change_5m=30.01)) == "FOMO_SPRUNG"


def test_fomo_kommt_nach_den_anderen_pruefungen():
    """Ein Coin, der auch aus anderen Gruenden durchfaellt, behaelt den alten Grund (Statistik vergleichbar)."""
    assert core.quick_checks(view(price_change_5m=80, liquidity=1000)) == "LIQUIDITAET_ZU_GERING"


def test_vamp_kopie_wird_abgelehnt():
    now = time.time()
    echt = core.token_view(tok(mint=MINT2, holders=5000), now)
    core.update_symbol_leaders([echt], now)
    kopie = core.token_view(tok(mint=MINT, holders=100), now)
    assert core.quick_checks(kopie) == "VAMP_KOPIE"
    assert core.quick_checks(echt) is None


def test_fomo_wird_immer_als_knapp_abgelehnt_verfolgt():
    v = view(price_change_5m=120)
    p = {"positions": {}, "watch": {}}
    core.track_near_miss(p, v, "FOMO_SPRUNG", time.time())
    assert MINT in p["shadow"]
    assert p["shadow"][MINT]["detail"] == "+120% in 5 min (Grenze 30)"
    rows = list(csv.DictReader(open(core.NEAR_MISS_FILE, encoding="utf-8")))
    assert rows[0]["grund"] == "FOMO_SPRUNG"
    assert list(rows[0].keys()) == core.NEAR_MISS_HEADER


def test_nicht_knappe_ablehnung_wird_nicht_verfolgt():
    p = {"positions": {}, "watch": {}}
    core.track_near_miss(p, view(holder_growth_1h=2), "VERBREITUNG_STOCKT", time.time())
    assert not p.get("shadow")


def test_log_reject_schreibt_nur_einmal_pro_stunde():
    v = view()
    core.log_reject(v, "ZU_JUNG")
    core.log_reject(v, "ZU_JUNG")
    rows = list(csv.reader(open(core.REJECT_FILE, encoding="utf-8")))
    assert len(rows) == 2                         # Kopf + 1 Zeile
    assert core.STATS["rejects"]["ZU_JUNG"] == 2


def test_ensure_csv_columns_haengt_hinten_an(tmp_path):
    path = "alt.csv"
    with open(path, "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerows([["a", "b"], ["1", "2"]])
    core.ensure_csv_columns(path, ["a", "b", "c"])
    assert list(csv.reader(open(path, encoding="utf-8"))) == [["a", "b", "c"], ["1", "2", ""]]
    # anderer Kopf (nicht nur angehaengt): nichts veraendern
    core.ensure_csv_columns(path, ["x", "b", "c", "d"])
    assert list(csv.reader(open(path, encoding="utf-8")))[0] == ["a", "b", "c"]


# ================================================================ Tag 1: Bundle-Check

def _fake_block0(monkeypatch, buyers, still_held, supply=1_000_000_000):
    """buyers: {owner: gekaufte Menge im Block 0}; still_held: {owner: heutiger Bestand}."""
    sigs = [{"signature": f"s{i}", "slot": 100, "err": None} for i in range(len(buyers))] + \
           [{"signature": "spaeter", "slot": 105, "err": None}]
    owners = list(buyers)

    def rpc(method, params):
        if method == "getSignaturesForAddress":
            return sigs
        if method == "getTokenSupply":
            return {"value": {"amount": str(supply)}}
        if method == "getTransaction":
            i = int(params[0][1:])
            o = owners[i]
            return {"meta": {"err": None, "preTokenBalances": [],
                             "postTokenBalances": [{"accountIndex": 1, "mint": MINT, "owner": o,
                                                    "uiTokenAmount": {"amount": str(buyers[o])}}]}}
        if method == "getTokenAccountsByOwner":
            o = params[0]
            return {"value": [{"account": {"data": {"parsed": {"info": {"tokenAmount": {
                "amount": str(still_held.get(o, 0))}}}}}}]}
        return None
    monkeypatch.setattr(core, "HELIUS_RPC", "https://helius.invalid")
    monkeypatch.setattr(core, "rpc", rpc)
    monkeypatch.setattr(core, "rugcheck_get", lambda mint: None)


def test_bundle_gebuendelt_wird_abgelehnt(monkeypatch):
    a, b = addr("BuyA"), addr("BuyB")
    _fake_block0(monkeypatch, {a: 100_000_000, b: 60_000_000}, {})       # 16 % im Block 0, verkauft
    reason, info = core.bundle_dev_check(MINT)
    assert reason == "GEBUENDELT"
    assert info["block0_wallets"] == 2 and info["block0_supply_pct"] == 16.0


def test_bundler_halten_noch(monkeypatch):
    a = addr("BuyA")
    _fake_block0(monkeypatch, {a: 120_000_000}, {a: 120_000_000})          # 1 Kaeufer, haelt 12 %
    assert core.bundle_dev_check(MINT)[0] == "BUNDLER_HALTEN_NOCH"


def test_sauberer_start_besteht(monkeypatch):
    a, b = addr("BuyA"), addr("BuyB")
    _fake_block0(monkeypatch, {a: 30_000_000, b: 20_000_000}, {a: 1_000_000})
    reason, info = core.bundle_dev_check(MINT)
    assert reason is None
    assert info["quelle"] == "block0" and info["gebuendelt"] is False


def test_ohne_helius_kein_kauf():
    assert core.bundle_dev_check(MINT)[0] == "BUNDLE_CHECK_NICHT_MOEGLICH"


def test_rugcheck_insider_netzwerk(monkeypatch):
    _fake_block0(monkeypatch, {addr("BuyA"): 10_000_000}, {})
    monkeypatch.setattr(core, "rugcheck_get", lambda mint: {
        "topHolders": [{"pct": 8, "insider": True}, {"pct": 5, "insider": True}], "token": {"supply": 1}})
    assert core.bundle_dev_check(MINT)[0] == "INSIDER_NETZWERK"


def test_transfergebuehr_wird_abgelehnt(monkeypatch):
    monkeypatch.setattr(core, "jup_get", lambda path: {"warnings": {MINT: [{"type": "HAS_TRANSFER_FEE"}]}})
    assert core.safety_shield(MINT) == "TRANSFERGEBUEHR"
