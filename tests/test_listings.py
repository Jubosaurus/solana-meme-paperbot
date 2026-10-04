"""listings.py: RSS lesen, Relevanz, Upbit/Binance/Coinbase/Bithumb-Ereignisse, Kursanstieg vor der Ankuendigung."""
import json
import time
from datetime import datetime, timezone

import pytest

import listings as L

JETZT = datetime(2026, 10, 4, 12, 0, tzinfo=timezone.utc).timestamp()

RSS = b"""<?xml version="1.0"?><rss version="2.0"><channel>
<item><title>Binance will list ABC (ABC) with seed tag</title><link>https://ex.test/a</link>
<pubDate>Sun, 04 Oct 2026 11:00:00 +0000</pubDate>
<description><![CDATA[<p>Binance announced it will list ABC. More text follows here.</p><p>zweiter Absatz</p>]]></description></item>
<item><title>Kein Datum</title><link>https://ex.test/b</link></item>
<item><title>Ordentlich</title><link>javascript:alert(1)</link><pubDate>Sun, 04 Oct 2026 10:00:00 +0000</pubDate></item>
</channel></rss>"""


def test_parse_rss_nur_titel_link_zeit_ein_satz():
    items = L.parse_rss(RSS, "Test")
    assert [i["titel"] for i in items] == ["Binance will list ABC (ABC) with seed tag", "Ordentlich"]
    assert items[0]["anriss"] == "Binance announced it will list ABC."
    assert items[0]["link"] == "https://ex.test/a"
    assert items[1]["link"] == ""                      # javascript: wird nie zum Link


def test_parse_rss_lehnt_entity_tricks_und_muell_ab():
    boese = b'<?xml version="1.0"?><!DOCTYPE x [<!ENTITY a "aaaa">]><rss><channel><item><title>&a;</title></item></channel></rss>'
    assert L.parse_rss(boese, "x") == []
    assert L.parse_rss(b"<rss><kaputt", "x") == []
    assert L.parse_rss(b"", "x") == []


def test_parse_atom():
    atom = (b'<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>Hallo</title>'
            b'<link href="https://ex.test/x"/><updated>2026-10-04T10:00:00Z</updated></entry></feed>')
    (i,) = L.parse_rss(atom, "A")
    assert i["link"] == "https://ex.test/x" and i["zeit"] == pytest.approx(JETZT - 7200)


def test_hole_news_ein_feed_faellt_aus_die_anderen_laufen():
    def get(url):
        if "kaputt" in url:
            raise RuntimeError("503")
        return RSS
    items, fehler = L.hole_news(get, {"gut": "https://x/gut", "schlecht": "https://x/kaputt"})
    assert len(items) == 2 and len(fehler) == 1 and fehler[0].startswith("schlecht")


@pytest.mark.parametrize("titel, marke", [
    ("Binance will list XYZ (XYZ)", "listing"),
    ("Upbit to delist ABC next week", "listing"),
    ("Protocol hacked, $20M drained", "rug"),
    ("Pump.fun launches new feature", "solana"),
    ("Bitcoin price today", None),
])
def test_bewerten_marken(titel, marke):
    i = L.bewerten({"titel": titel, "anriss": ""})
    assert (marke in i["marken"]) if marke else i["marken"] == []


def test_bewerten_position_hat_hoechste_punkte_und_kurze_ticker_nur_gross():
    a = L.bewerten({"titel": "BONK jumps after listing on Coinbase", "anriss": ""}, ["BONK"])
    assert "position" in a["marken"] and a["punkte"] >= 100
    # kurzer Ticker "cat" im Fliesstext ist kein Treffer, "CAT" schon
    assert "position" not in L.bewerten({"titel": "the cat sat", "anriss": ""}, ["cat"])["marken"]
    assert "position" in L.bewerten({"titel": "CAT surges", "anriss": ""}, ["cat"])["marken"]
    assert "position" in L.bewerten({"titel": "buy $cat now", "anriss": ""}, ["cat"])["marken"]


def test_sortiert_relevanz_vor_zeit_und_altes_fliegt_raus():
    a = L.bewerten({"titel": "Binance will list XYZ", "anriss": "", "zeit": JETZT - 3600})
    b = L.bewerten({"titel": "Irgendwas", "anriss": "", "zeit": JETZT - 60})
    alt = L.bewerten({"titel": "Binance will list OLD", "anriss": "", "zeit": JETZT - 200 * 3600})
    assert L.sortiert([b, alt, a], JETZT) == [a, b]


def test_geruecht_und_ticker():
    i = {"titel": "Coinbase may list Foo (FOO) soon", "anriss": ""}
    assert L.ist_geruecht(i) and L.ticker_in_text(i["titel"]) == ["FOO"]
    assert not L.ist_geruecht({"titel": "Bitcoin steigt", "anriss": ""})
    assert L.ticker_in_text("Binance lists $wif and (USDT)") == ["WIF"]


# ---------------------------------------------------------------- Upbit

UPBIT_BODY = """<table><tbody><tr><td>돌핀(POD)</td><td>KRW, BTC</td><td>Solana</td><td>2시간 이내</td><td>10월 4일 16시 30분 예정</td></tr>
<tr><td>베타(BETA)</td><td>KRW</td><td>Base</td><td>x</td><td>10월 4일 16시 예정</td></tr></tbody></table>"""


def upbit_get(notices, bodies=None):
    def get(url):
        if "announcements?" in url:
            return json.dumps({"data": {"notices": notices}}).encode()
        nid = int(url.rsplit("/", 1)[1])
        return json.dumps({"data": {"body": (bodies or {}).get(nid, UPBIT_BODY)}}).encode()
    return get


def notice(i, titel, zeit="2026-10-04T20:55:00+09:00"):
    return {"id": i, "title": titel, "listed_at": zeit}


def test_upbit_erster_lauf_merkt_nur():
    gesehen = set()
    assert L.upbit_ereignisse(upbit_get([notice(1, "돌핀(POD) 신규 거래지원 안내 (KRW 마켓)")]), gesehen) == []
    assert gesehen == {"upbit:1"}


def test_upbit_neues_listing_mit_netzwerk_und_startzeit():
    gesehen = {"upbit:1"}
    evs = L.upbit_ereignisse(upbit_get([notice(1, "alt"), notice(2, "돌핀(POD), 베타(BETA) 신규 거래지원 안내 (KRW 마켓)")]), gesehen)
    (ev,) = evs
    assert ev["art"] == "listing" and ev["boerse"] == "Upbit" and ev["quelle_typ"] == "ankuendigung"
    pod, beta = ev["coins"]
    assert (pod["symbol"], pod["netzwerk"]) == ("POD", "Solana") and beta["netzwerk"] == "Base"
    # 16:30 Koreazeit = 07:30 UTC
    assert pod["start"] == datetime(2026, 10, 4, 7, 30, tzinfo=timezone.utc).timestamp()
    assert ev["zeit"] == datetime(2026, 10, 4, 11, 55, tzinfo=timezone.utc).timestamp()
    assert gesehen == {"upbit:1", "upbit:2"}


def test_upbit_delisting_aenderung_und_sonstiges():
    gesehen = {"upbit:0"}
    liste = [notice(1, "아이콘(ICX) 거래지원 종료 안내 (10/19 15:00)"),
             notice(2, "렌조(REZ) 신규 거래지원 안내 (USDT 마켓) (거래지원 개시 시점 추가 변경 안내)"),
             notice(3, "블라스트(BLAST) 거래 유의 종목 지정 안내")]
    evs = {e["id"]: e for e in L.upbit_ereignisse(upbit_get(liste), gesehen)}
    assert evs["upbit:1"]["art"] == "delisting" and evs["upbit:1"]["coins"][0]["symbol"] == "ICX"
    assert evs["upbit:2"]["art"] == "sonst" and evs["upbit:3"]["art"] == "sonst"


def test_upbit_start_jahreswechsel():
    bezug = datetime(2026, 12, 31, 10, tzinfo=timezone.utc).timestamp()
    assert L.upbit_start("1월 2일 16시 예정", bezug) == datetime(2027, 1, 2, 7, tzinfo=timezone.utc).timestamp()
    assert L.upbit_start("kein datum", bezug) is None


def test_upbit_detail_faellt_aus_ticker_aus_dem_titel():
    def get(url):
        if "announcements?" in url:
            return json.dumps({"data": {"notices": [notice(5, "돌핀(POD) 신규 거래지원 안내 (KRW, BTC 마켓)")]}}).encode()
        raise RuntimeError("500")
    (ev,) = L.upbit_ereignisse(get, {"upbit:1"})
    assert [c["symbol"] for c in ev["coins"]] == ["POD"] and ev["coins"][0]["netzwerk"] == ""


# ---------------------------------------------------------------- Binance, Coinbase, Bithumb

def test_binance_nur_neue_basis_assets():
    def get(url):
        return json.dumps({"symbols": [{"symbol": "ABCUSDT", "baseAsset": "ABC", "status": "BREAK"},
                                       {"symbol": "ABCBTC", "baseAsset": "ABC", "status": "BREAK"},
                                       {"symbol": "OLDUSDT", "baseAsset": "OLD", "status": "TRADING"}]}).encode()
    bekannt = {"OLD"}
    evs = L.binance_ereignisse(get, bekannt)
    assert [e["coins"][0]["symbol"] for e in evs] == ["ABC"] and evs[0]["coins"][0]["start"] is None
    assert bekannt == {"OLD", "ABC"}
    assert L.binance_ereignisse(get, bekannt) == []              # zweiter Lauf: nichts Neues
    assert L.binance_ereignisse(get, set()) == []                # erster Lauf: nur merken


def produkt(base, status="online", **kw):
    return {"id": f"{base}-USD", "base_currency": base, "status": status, "trading_disabled": False,
            "post_only": False, "limit_only": False, **kw}


def test_coinbase_listing_vorab_start_und_delisting():
    stand = {"produkte": [produkt("OLD"), produkt("GONE")]}
    get = lambda url: json.dumps(stand["produkte"]).encode()
    bekannt = {}
    assert L.coinbase_ereignisse(get, bekannt) == [] and bekannt == {"OLD": "offen", "GONE": "offen"}
    stand["produkte"] = [produkt("OLD"), produkt("GONE", "delisted"), produkt("NEU", limit_only=True)]
    evs = {e["id"]: e for e in L.coinbase_ereignisse(get, bekannt)}
    assert set(evs) == {"coinbase:NEU", "coinbase:GONE:delisted"}
    assert evs["coinbase:NEU"]["coins"][0]["start"] is None          # noch eingeschraenkt: Start offen
    assert evs["coinbase:GONE:delisted"]["art"] == "delisting"
    stand["produkte"] = [produkt("OLD"), produkt("GONE", "delisted"), produkt("NEU")]
    assert L.coinbase_ereignisse(get, bekannt) == []                 # NEU jetzt offen: kein neues Listing
    assert L.coinbase_offen(get, {"NEU", "OLD", "X"}) == {"NEU", "OLD"}


def test_coinbase_mehrere_paare_ein_paar_weg_ist_kein_delisting():
    stand = {"p": [produkt("AAA"), {**produkt("AAA"), "id": "AAA-EUR"}]}
    get = lambda url: json.dumps(stand["p"]).encode()
    bekannt = {}
    L.coinbase_ereignisse(get, bekannt)
    stand["p"] = [produkt("AAA"), {**produkt("AAA", "delisted"), "id": "AAA-EUR"}]
    assert L.coinbase_ereignisse(get, bekannt) == []


def test_bithumb_neuer_markt_ist_nur_aufzeichnung():
    get = lambda url: json.dumps([{"market": "KRW-BTC"}, {"market": "KRW-NEU"}, {"market": "BTC-NEU"}]).encode()
    (ev,) = L.bithumb_ereignisse(get, {"BTC"})
    assert ev["quelle_typ"] == "handelsstart" and ev["coins"][0]["symbol"] == "NEU"


# ---------------------------------------------------------------- Kursverlauf

def test_anstiege_aus_kerzen():
    t = 1_000_000 * 3600.0
    kerzen = [[t - h * 3600, 0, 0, 0, 100 - h * 0.5, 0] for h in range(0, 80)]   # neueste zuerst, Kurs steigt
    r = L.anstiege_aus_kerzen(kerzen, t)
    assert r["anstieg_3h_pct"] == pytest.approx((100 / 98.5 - 1) * 100, abs=0.1)
    assert r["anstieg_3d_pct"] == pytest.approx((100 / 64 - 1) * 100, abs=0.1)
    assert L.anstiege_aus_kerzen([], t) is None
    assert L.anstiege_aus_kerzen([[t + 5, 0, 0, 0, 1, 0]], t)["anstieg_3h_pct"] is None   # keine Daten vor t


def test_kurs_vorlauf_ohne_daten_ist_kein_fehler():
    def get(url):
        raise RuntimeError("429")
    assert L.kurs_vorlauf(get, "Mint", JETZT) == {"anstieg_3h_pct": None, "anstieg_3d_pct": None}


def test_upbit_marktliste_neues_asset_nur_handelsstart():
    get = lambda url: json.dumps([{"market": "KRW-BTC"}, {"market": "BTC-BTC"}, {"market": "KRW-NEU", "english_name": "Neu"}]).encode()
    (ev,) = L.upbit_markt_ereignisse(get, {"BTC"})
    assert ev["id"] == "upbit-markt:NEU" and ev["quelle_typ"] == "handelsstart"
    assert L.upbit_markt_ereignisse(get, set()) == []
