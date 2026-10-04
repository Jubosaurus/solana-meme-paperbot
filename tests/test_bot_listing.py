"""Experiment Listing-Welle: Kauf bei Ankuendigung, Verkauf zum Handelsstart / 72 h / Notbremse, Aufzeichnung."""
import csv
import json
import time
from datetime import datetime, timezone

import pytest

import bot as core
from helpers import MINT, MINT2

SOL = 100.0
NAME = "listing_welle"


def load(name=NAME):
    with core.experiment(name):
        return core.load_portfolio()


def zeilen(pfad):
    with open(pfad, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def event(now, boerse="Upbit", symbol="POD", netz="Solana", start=None, alter=60, art="listing",
          typ="ankuendigung", eid="upbit:7"):
    return {"id": eid, "boerse": boerse, "art": art, "titel": f"{boerse} {symbol}", "zeit": now - alter,
            "quelle_typ": typ, "url": "https://ex.test/x", "coins": [{"symbol": symbol, "netzwerk": netz, "start": start}]}


@pytest.fixture
def lw(market, monkeypatch, clock):
    """Fake-Markt mit einem Solana-Token POD (Jupiter-verifiziert) und Fake-Suche; Kursverlauf liefert +12 % / +80 %."""
    t = market.set(MINT, price=0.01, symbol="POD", liquidity=500_000)
    t["isVerified"] = True
    monkeypatch.setattr(core, "jup_get", lambda path: [market.tokens[MINT]] if "query=POD" in path else [])
    monkeypatch.setattr(core.listings, "kurs_vorlauf",
                        lambda get, mint, zeit: {"anstieg_3h_pct": 12.0, "anstieg_3d_pct": 80.0})
    return market


def kaufen(ev, now):
    ep = load()
    with core.experiment(NAME):
        core.listing_ereignis(ep, ev, SOL, now)
    return ep


def test_upbit_solana_listing_wird_gekauft_und_aufgezeichnet(lw, clock):
    now = clock.time()
    start = now + 3600
    ep = kaufen(event(now, start=start), now)
    pos = ep["positions"][MINT]
    assert pos["exit_mode"] == "listing" and pos["listing_boerse"] == "Upbit" and pos["listing_start"] == start
    assert pos["invested_sol"] == core.POSITION_SOL
    assert "Listing angekuendigt" in pos["thesis"] and "+80 %" in pos["thesis"] and "+12 %" in pos["thesis"]
    (r,) = zeilen(core.LISTING_EREIGNISSE_FILE)
    assert (r["entscheidung"], r["boerse"], r["symbol"], r["mint"]) == ("gekauft", "Upbit", "POD", MINT)
    assert r["anstieg_3h_pct"] == "12.0" and r["anstieg_3d_pct"] == "80.0" and r["kurs_usd"] == "0.01"
    assert r["handelsstart_zeit"] == core._listing_iso(start)
    assert zeilen("experimente/listing_welle/journal.csv")[0]["aktion"] == "KAUF"


@pytest.mark.parametrize("kw, grund", [
    ({"alter": 601}, "zu_alt"),
    ({"netz": "Base"}, "anderes_netzwerk"),
    ({"start": "bald"}, "start_zu_nah"),
    ({"art": "delisting"}, "delisting"),
    ({"typ": "handelsstart", "boerse": "Bithumb", "netz": ""}, "nur_aufzeichnung"),
    ({"symbol": "NIX"}, "kein_solana_token"),
])
def test_kein_kauf_und_grund_in_der_csv(lw, clock, kw, grund):
    now = clock.time()
    if kw.get("start") == "bald":
        kw = {"start": now + 60}
    ep = kaufen(event(now, **kw), now)
    assert ep["positions"] == {}
    assert zeilen(core.LISTING_EREIGNISSE_FILE)[0]["entscheidung"] == grund


def test_ticker_mit_zwei_aehnlich_grossen_treffern_ist_mehrdeutig(lw, clock, monkeypatch):
    zwei = lw.set(MINT2, price=0.02, symbol="POD", liquidity=400_000)
    zwei["isVerified"] = True
    monkeypatch.setattr(core, "jup_get", lambda path: [lw.tokens[MINT], lw.tokens[MINT2]])
    now = clock.time()
    assert kaufen(event(now), now)["positions"] == {}
    assert zeilen(core.LISTING_EREIGNISSE_FILE)[0]["entscheidung"] == "mehrdeutig"


def test_zu_wenig_liquiditaet(lw, clock):
    lw.tokens[MINT]["liquidity"] = 50_000
    now = clock.time()
    kaufen(event(now), now)
    assert zeilen(core.LISTING_EREIGNISSE_FILE)[0]["entscheidung"] == "zu_wenig_liquiditaet"


def test_ohne_netzwerkangabe_nur_verifizierte_tokens(lw, clock):
    now = clock.time()
    lw.tokens[MINT]["isVerified"] = False
    assert kaufen(event(now, boerse="Binance", netz="", typ="neues_paar", eid="binance:POD"), now)["positions"] == {}
    assert zeilen(core.LISTING_EREIGNISSE_FILE)[0]["entscheidung"] == "nicht_verifiziert"


def test_derselbe_coin_nicht_zweimal(lw, clock):
    now = clock.time()
    ep = load()
    with core.experiment(NAME):
        core.listing_ereignis(ep, event(now), SOL, now)
        core.listing_ereignis(ep, event(now, eid="upbit:8"), SOL, now)
    assert len(ep["positions"]) == 1
    assert [r["entscheidung"] for r in zeilen(core.LISTING_EREIGNISSE_FILE)] == ["gekauft", "kein_platz_oder_geld"]


def test_verkauf_zum_handelsstart_und_nicht_vorher(lw, clock):
    now = clock.time()
    start = now + 1800
    ep = kaufen(event(now, start=start), now)
    exps, p = {NAME: ep}, core.load_portfolio()
    lw.price[MINT] = 0.03                                            # 3x: die Hauptregeln wuerden verkaufen, hier nicht
    core.manage_experiments(p, exps, SOL, now + 600)
    assert MINT in ep["positions"] and not ep["positions"][MINT]["tp1_done"]
    core.manage_experiments(p, exps, SOL, start + 5)
    assert ep["positions"] == {}
    assert ep["closed"][-1]["exit_reason"].startswith("HANDELSSTART")
    assert ep["closed"][-1]["listing_boerse"] == "Upbit"
    assert MINT in ep["watch"]                                       # danach 6 h weiter aufzeichnen


def test_notbremse_bei_minus_40(lw, clock):
    now = clock.time()
    ep = kaufen(event(now, start=now + 10 * 86400), now)
    lw.price[MINT] = 0.0059                                          # -41 %
    core.manage_experiments(core.load_portfolio(), {NAME: ep}, SOL, now + 60)
    assert ep["closed"][-1]["exit_reason"].startswith("NOTBREMSE")


def test_nach_72_stunden_ohne_handelsstart_raus(lw, clock):
    now = clock.time()
    ep = kaufen(event(now, start=None, boerse="Coinbase", netz="", typ="neues_paar", eid="coinbase:POD"), now)
    lw.price[MINT] = 0.011
    exps, p = {NAME: ep}, core.load_portfolio()
    opened = ep["positions"][MINT]["opened"]
    core.manage_experiments(p, exps, SOL, opened + 72 * 3600 - 60)
    assert MINT in ep["positions"]
    core.manage_experiments(p, exps, SOL, opened + 72 * 3600 + 60)
    assert ep["closed"][-1]["exit_reason"].startswith("ZEIT_STOP")


def test_binance_start_wird_nachgetragen_wenn_handelbar(lw, clock, monkeypatch):
    now = clock.time()
    ep = kaufen(event(now, boerse="Binance", netz="", typ="neues_paar", eid="binance:POD"), now)
    pos = ep["positions"][MINT]
    assert pos["listing_start"] is None
    monkeypatch.setattr(core.listings, "binance_offen", lambda get, basen: set())
    core._listing_starts_nachtragen(ep, now + 300)
    assert pos["listing_start"] is None                              # noch im Status BREAK
    monkeypatch.setattr(core.listings, "binance_offen", lambda get, basen: {"POD"})
    core._listing_starts_nachtragen(ep, now + 600)
    assert pos["listing_start"] == now + 600
    assert zeilen(core.LISTING_EREIGNISSE_FILE)[-1]["typ"] == "handelsstart"
    core.manage_experiments(core.load_portfolio(), {NAME: ep}, SOL, now + 620)
    assert ep["closed"][-1]["exit_reason"].startswith("HANDELSSTART")


# ---------------------------------------------------------------- Zeitplan, Fehler, Geruechte

def fake_netz(monkeypatch, upbit, binance=None, coinbase=None, bithumb=None, rss=b"<rss/>"):
    def get(url):
        if "upbit.com/api/v1/announcements?" in url or "api-manager.upbit.com/api/v1/announcements?" in url:
            return json.dumps({"data": {"notices": upbit}}).encode()
        if "api-manager.upbit.com" in url:
            return json.dumps({"data": {"body": "<table></table>"}}).encode()
        if "binance.vision" in url:
            if binance is None:
                raise RuntimeError("451")
            return json.dumps({"symbols": binance}).encode()
        if "coinbase.com/products" in url:
            return json.dumps(coinbase or []).encode()
        if "bithumb" in url:
            return json.dumps(bithumb or []).encode()
        return rss
    monkeypatch.setattr(core, "listing_get", get)


def test_schritt_erster_lauf_merkt_nur_und_fehler_einer_quelle_stoppt_nichts(lw, clock, monkeypatch):
    monkeypatch.setattr(core, "LISTING_UPBIT_ANKUENDIGUNG", True)
    now = clock.time()
    fake_netz(monkeypatch, [{"id": 5, "title": "x (POD) 신규 거래지원 안내", "listed_at": "2026-10-04T10:00:00+09:00"}],
              binance=None, coinbase=[{"base_currency": "OLD", "status": "online", "id": "OLD-USD"}])
    ep = load()
    with core.experiment(NAME):
        core.listing_welle_schritt(ep, SOL, now)
        q = ep["listing"]["quellen"]
        assert q["Upbit"]["ok"] == 1 and q["Binance"]["fehler"] == 1 and q["Coinbase"]["ok"] == 1
        assert "451" in q["Binance"]["letzter_fehler"]
        assert ep["listing"]["upbit"] == ["upbit:5"] and ep["positions"] == {}
        core.listing_welle_schritt(ep, SOL, now + 10)                # zu frueh: keine neue Abfrage
        assert ep["listing"]["quellen"]["Upbit"]["ok"] == 1
        core.listing_welle_schritt(ep, SOL, now + core.LISTING_POLL_SEC + 1)
        assert ep["listing"]["quellen"]["Upbit"]["ok"] == 2
    assert not __import__("os").path.exists(core.LISTING_EREIGNISSE_FILE)


def test_schritt_neue_upbit_ankuendigung_nach_dem_ersten_lauf_wird_gekauft(lw, clock, monkeypatch):
    monkeypatch.setattr(core, "LISTING_UPBIT_ANKUENDIGUNG", True)
    now = clock.time()
    jetzt_kst = datetime.fromtimestamp(now - 30, timezone.utc).astimezone(core.listings.KST).isoformat()
    ep = load()
    ep["listing"] = {"upbit": ["upbit:5"], "next_listen": now + 9999, "next_news": now + 9999}
    body = ("<table><tr><td>돌핀(POD)</td><td>KRW</td><td>Solana</td><td>x</td><td>"
            + f"{datetime.fromtimestamp(now + 7200, core.listings.KST).month}월 "
            + f"{datetime.fromtimestamp(now + 7200, core.listings.KST).day}일 "
            + f"{datetime.fromtimestamp(now + 7200, core.listings.KST).hour}시 예정</td></tr></table>")

    def get(url):
        if "announcements?" in url:
            return json.dumps({"data": {"notices": [{"id": 5, "title": "alt", "listed_at": jetzt_kst},
                                                    {"id": 6, "title": "돌핀(POD) 신규 거래지원 안내 (KRW 마켓)",
                                                     "listed_at": jetzt_kst}]}}).encode()
        return json.dumps({"data": {"body": body}}).encode()
    monkeypatch.setattr(core, "listing_get", get)
    with core.experiment(NAME):
        core.listing_welle_schritt(ep, SOL, now)
    pos = ep["positions"][MINT]
    assert pos["listing_start"] == pytest.approx(now + 7200, abs=3600) and pos["listing_id"] == "upbit:6"


def test_geruechte_werden_aufgezeichnet_ohne_zu_handeln(lw, clock):
    now = clock.time()
    ep = load()
    ep["listing"] = {"offiziell": {"FOO": now - 3600}}
    items = [{"titel": "Coinbase may list Foo (FOO) soon", "anriss": "", "link": "https://ex.test/1", "zeit": now - 600,
              "quelle": "Decrypt"},
             {"titel": "Exchange to list NEWC (NEWC)", "anriss": "", "link": "https://ex.test/2", "zeit": now - 300,
              "quelle": "Cointelegraph"},
             {"titel": "Bitcoin steigt", "anriss": "", "link": "https://ex.test/3", "zeit": now - 60, "quelle": "X"},
             {"titel": "Alte Meldung to list OLD (OLD)", "anriss": "", "link": "https://ex.test/4",
              "zeit": now - 100 * 3600, "quelle": "X"}]
    with core.experiment(NAME):
        core.listing_geruechte(ep, now, items)
        core.listing_geruechte(ep, now, items)                       # zweites Mal: keine Doppel
    rows = zeilen(core.LISTING_GERUECHTE_FILE)
    assert [(r["coin"], r["quelle"], r["offiziell_vorher"]) for r in rows] == \
        [("FOO", "Decrypt", "ja"), ("NEWC", "Cointelegraph", "nein")]
    assert ep["positions"] == {}


def test_hauptstrategie_und_andere_experimente_bleiben_unberuehrt(lw, clock):
    now = clock.time()
    kaufen(event(now), now)
    import os
    assert not os.path.exists("journal.csv") and not os.path.exists("experimente/kontrollgruppe/journal.csv")
    assert core.EXPERIMENTS[NAME] == "Listing-Welle"


def test_upbit_ankuendigung_ist_aus_und_marktliste_nur_aufzeichnung(lw, clock, monkeypatch):
    assert core.LISTING_UPBIT_ANKUENDIGUNG is False
    now = clock.time()
    stand = {"m": [{"market": "KRW-BTC"}]}

    def get(url):
        assert "announcements" not in url                       # gesperrte Schnittstelle wird nicht angefragt
        if "api.upbit.com/v1/market" in url:
            return json.dumps(stand["m"]).encode()
        return b"[]" if "bithumb" in url or "coinbase" in url else b'{"symbols": []}'
    monkeypatch.setattr(core, "listing_get", get)
    ep = load()
    with core.experiment(NAME):
        core.listing_welle_schritt(ep, SOL, now)                 # erster Lauf: nur merken
        stand["m"].append({"market": "KRW-POD", "english_name": "Dolphin"})
        core.listing_welle_schritt(ep, SOL, now + core.LISTING_LISTEN_POLL_SEC + 1)
    assert ep["positions"] == {} and ep["listing"]["quellen"]["Upbit-Markt"]["ok"] == 2
    (r,) = zeilen(core.LISTING_EREIGNISSE_FILE)
    assert (r["boerse"], r["symbol"], r["entscheidung"], r["quelle_typ"]) == ("Upbit", "POD", "nur_aufzeichnung", "handelsstart")


def test_nur_aufzeichnung_schreibt_kursanstieg_davor_ohne_zu_kaufen(lw, clock):
    now = clock.time()
    ep = kaufen(event(now, boerse="Upbit", typ="handelsstart", netz="", eid="upbit-markt:POD"), now)
    assert ep["positions"] == {}
    (r,) = zeilen(core.LISTING_EREIGNISSE_FILE)
    assert (r["entscheidung"], r["mint"], r["anstieg_3h_pct"], r["anstieg_3d_pct"]) == ("nur_aufzeichnung", MINT, "12.0", "80.0")
