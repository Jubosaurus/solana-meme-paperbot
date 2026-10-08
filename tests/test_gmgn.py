"""GMGN: nur Fake-Antworten, keine Zugangsdaten und keine echten Netzaufrufe."""
import csv
import time
import uuid

import pytest
import requests

import bot as core
import copy_bot as cb
import gmgn
import scout_bot as scout
from helpers import addr, buy_tx, sell_tx, MINT

SMART = "/v1/user/smartmoney"
KOL = "/v1/user/kol"
TOP = "/v1/market/token_top_traders"
HTTP_ABRUF = gmgn.abruf


class Antwort:
    def __init__(self, data=None, status=200):
        self.status_code = status
        self.data = {"code": 0, "data": []} if data is None else data

    def json(self):
        if isinstance(self.data, Exception):
            raise self.data
        return self.data


@pytest.fixture
def fake(monkeypatch):
    monkeypatch.setenv("GMGN_API_KEY", "TEST-PLATZHALTER")
    calls, replies = [], []

    def abruf(path, params, headers):
        calls.append((path, params, headers))
        reply = replies.pop(0) if replies else Antwort()
        if isinstance(reply, Exception):
            raise reply
        return reply

    monkeypatch.setattr(gmgn, "abruf", abruf)
    return calls, replies


def wallets(*addresses):
    return Antwort({"code": 0, "data": [{"wallet": w} for w in addresses]})


def test_nur_erlaubte_get_pfade_und_anmeldung(fake, monkeypatch):
    calls, _ = fake
    client = gmgn.Client()
    monkeypatch.setattr(time, "time", lambda: 1234567890.9)
    for path in (SMART, KOL, TOP):
        assert client.get(path, MINT) == []
    assert set(gmgn.PFADE) == {SMART, KOL, TOP}
    assert [c[0] for c in calls] == [SMART, KOL, TOP]
    assert len({c[1]["client_id"] for c in calls}) == 3
    for path, params, headers in calls:
        assert params["timestamp"] == 1234567890
        assert params["chain"] == "sol"
        assert str(uuid.UUID(params["client_id"])) == params["client_id"]
        assert headers == {"X-APIKEY": "TEST-PLATZHALTER", "Content-Type": "application/json"}
        assert ("address" in params) == (path == TOP)
    assert calls[-1][1]["address"] == MINT
    assert calls[-1][1]["limit"] == 20


@pytest.mark.parametrize("path", ["/v1/swap", "/v1/order", "/v1/cooking", "/v1/user/follow_wallet",
                                "/v1/user/wallet_holdings", SMART + "?x=1", "https://example.invalid"])
def test_verbotene_pfade_ohne_abruf(path, fake):
    calls, _ = fake
    with pytest.raises(ValueError, match="Pfad nicht erlaubt"):
        gmgn.Client().get(path)
    assert calls == []


def test_http_transport_nur_get_ohne_weiterleitungen(monkeypatch):
    # Der echte Transport wird hier ausschliesslich gegen einen Fake getestet.
    calls = []
    monkeypatch.setattr(requests, "get", lambda *a, **kw: calls.append((a, kw)) or Antwort())
    HTTP_ABRUF(SMART, {"chain": "sol"}, {"X-APIKEY": "TEST-PLATZHALTER"})
    assert calls == [((gmgn.HOST + SMART,), {"params": {"chain": "sol"},
                     "headers": {"X-APIKEY": "TEST-PLATZHALTER"}, "timeout": 15, "allow_redirects": False})]
    with pytest.raises(ValueError, match="Pfad nicht erlaubt"):
        HTTP_ABRUF("/v1/order", {}, {})
    assert len(calls) == 1


def test_verschachtelte_adressen_ohne_fremde_werte(fake):
    calls, replies = fake
    expected = [addr(p) for p in ("Maker", "WaA", "WaB", "WaC", "User", "Nested")]
    replies.append(Antwort({"code": 0, "data": {"items": [
        {"maker": expected[0], "gewinn": 999999, "tags": ["bot"]},
        {"wallet": expected[1], "wallet_address": expected[2]},
        {"wrapper": {"address": expected[3], "user": expected[4]}},
        {"user": {"wallet": expected[5]}, "wallet_address": expected[0]},
        {"wallet": "0" * 44, "maker": "a" * 31, "address": "a" * 45, "user": 123},
        {"token": {"address": MINT}, "profit": addr("NichtWallet")},
    ]}}))
    client = gmgn.Client()
    assert client.get(SMART) == expected
    assert client.stats["gmgn_adressen"] == 6
    assert client.stats["gmgn_fehler"] == 0
    assert len(calls) == 1


def test_toptrader_coin_ausgeschlossen_und_maximal_20(fake):
    _, replies = fake
    addresses = [addr("Trader" + a + b) for a in "ABCDE" for b in "ABCDE"]
    replies.append(wallets(MINT, *addresses))
    client = gmgn.Client()
    assert client.get(TOP, MINT) == addresses[:20]
    assert client.stats["gmgn_adressen"] == 20


@pytest.mark.parametrize("reply", [Antwort(), Antwort(status=401), requests.Timeout("nicht ausgeben"),
                                 Antwort(ValueError("kaputtes JSON"))])
def test_takt_nach_jeder_abfrage(fake, monkeypatch, reply):
    calls, replies = fake
    sleeps = []
    monkeypatch.setattr(time, "sleep", sleeps.append)
    for path, gewicht in ((SMART, 1), (KOL, 1), (TOP, 5)):
        replies.append(reply)
        gmgn.Client().get(path, MINT)
        assert sleeps[-1] == 2 * gewicht / 5
    assert sleeps == [0.4, 0.4, 2.0]
    assert len(calls) == 3


@pytest.mark.parametrize("reply", [Antwort(status=429), Antwort({"code": 429}),
                                 Antwort({"code": "RATE_LIMIT_EXCEEDED"}),
                                 Antwort({"code": 1001, "msg": "IP rate limit exceeded"}),
                                 Antwort({"code": 1002, "message": "IP is temporarily banned"})])
def test_429_sofort_sperre_ohne_wiederholung(fake, monkeypatch, reply):
    calls, replies = fake
    replies.extend([reply, wallets(addr("Trader"))])
    sleeps = []
    monkeypatch.setattr(time, "sleep", sleeps.append)
    client = gmgn.Client()
    assert list(client.kandidaten([(MINT, "COIN", 3.0)])) == []
    assert client.get(SMART) == []
    assert client.gesperrt
    assert client.stats["gmgn_429"] == 1
    assert client.stats["gmgn_abfragen"] == 1
    assert client.stats["gmgn_fehler"] == 1
    assert len(calls) == 1
    assert sleeps == [0.4]
    assert gmgn.bericht(client.stats) == "**GMGN:** nach 429 abgebrochen"


@pytest.mark.parametrize("key", [None, "", "   "])
def test_fehlender_key_kein_netz(key, monkeypatch, fake):
    calls, _ = fake
    if key is None:
        monkeypatch.delenv("GMGN_API_KEY")
    else:
        monkeypatch.setenv("GMGN_API_KEY", key)
    client = gmgn.Client()
    assert list(client.kandidaten([(MINT, "COIN", 3.0)])) == []
    assert calls == []
    assert client.stats["gmgn_abfragen"] == 0
    assert gmgn.bericht(client.stats) == "**GMGN:** kein Key"


@pytest.mark.parametrize("reply", [requests.ConnectionError("nicht ausgeben"), requests.Timeout("nicht ausgeben"),
                                 Antwort(status=401), Antwort(status=403), Antwort(status=500), Antwort(status=503),
                                 Antwort({"code": 1, "data": [{"wallet": addr("Trader")}]}),
                                 Antwort({"code": 0, "data": {"unbekannt": 123}}), Antwort(["falsche Form"]),
                                 Antwort({"code": 0, "data": {"unbekannt": []}}),
                                 Antwort({"code": 0, "data": None}), Antwort(ValueError("JSON"))])
def test_drei_fehler_in_folge_stoppen_lauf(fake, reply):
    calls, replies = fake
    replies.extend([reply] * 3)
    client = gmgn.Client()
    for _ in range(4):
        assert client.get(SMART) == []
    assert client.gesperrt
    assert client.fehler_folge == client.stats["gmgn_fehler"] == 3
    assert client.stats["gmgn_abfragen"] == len(calls) == 3


def test_erfolg_setzt_fehlerfolge_zurueck(fake):
    calls, replies = fake
    replies.extend([Antwort(status=500), Antwort(status=500), Antwort(),
                    Antwort(status=403), wallets(addr("Trader"))])
    client = gmgn.Client()
    for _ in range(5):
        client.get(SMART)
    assert not client.gesperrt
    assert client.fehler_folge == 0
    assert client.stats["gmgn_fehler"] == 3
    assert len(calls) == 5


def test_schluessel_nie_in_fehlern_log_oder_bericht(fake, capsys, monkeypatch):
    calls, replies = fake
    filter_calls = []
    original_filter = core._hide_key
    monkeypatch.setattr(core, "_hide_key", lambda text: filter_calls.append(text) or original_filter(text))
    replies.extend([requests.Timeout("https://example.invalid X-APIKEY: TEST-PLATZHALTER"),
                    Antwort({"code": 1, "msg": "TEST-PLATZHALTER"}),
                    Antwort(status=403)])
    client = gmgn.Client()
    for _ in range(3):
        client.get(SMART)
    captured = capsys.readouterr()
    texts = captured.out + captured.err + client.letzter_fehler + gmgn.bericht(client.stats) + str(filter_calls)
    assert "TEST-PLATZHALTER" not in texts
    assert "https://" not in texts
    assert "X-APIKEY" not in texts
    assert len(filter_calls) == len(calls) == 3


def suchquellen(monkeypatch, coins=None):
    monkeypatch.setattr(scout, "winner_coins", lambda state, now: coins or [])
    monkeypatch.setattr(scout, "known_wallets", lambda: set())
    monkeypatch.setattr(scout, "early_buyers", lambda *a: [])
    monkeypatch.setattr(scout, "birdeye_top_traders", lambda *a: [])
    return scout.load_state()


def test_search_gmgn_durch_eigene_stufen_und_csv(fake, monkeypatch):
    calls, replies = fake
    now = time.time()
    early, bird, smart, kol, top, known, recent = [addr(p) for p in
                                               ("Early", "Bird", "Smart", "Ko", "Top", "Known", "Recent")]
    state = suchquellen(monkeypatch, [(MINT, "COIN", 3.0)])
    state["wallets_geprueft"][recent] = now - 10
    monkeypatch.setattr(scout, "known_wallets", lambda: {known})
    monkeypatch.setattr(scout, "early_buyers", lambda *a: [early])
    monkeypatch.setattr(scout, "birdeye_top_traders", lambda *a: [early, bird])
    replies.extend([wallets(early, bird, smart, known, recent), wallets(smart, kol), wallets(MINT, top)])
    signatures, transactions = {}, {}
    for wallet in (early, bird, smart, kol, top):
        signatures[wallet] = []
        for i in range(30):
            sig = f"{wallet}:{i}"
            signatures[wallet].append({"signature": sig, "blockTime": int(now - 3600 - i * 600), "err": None})
            if i < 6:
                mint = addr("Mint" + "ABC"[i // 2])
                transactions[sig] = (sell_tx(wallet=wallet, mint=mint, sol=0.8,
                                             block_time=int(now - 3600 - i * 600))
                                     if i % 2 == 0 else buy_tx(wallet=wallet, mint=mint, sol=0.5,
                                                             block_time=int(now - 3600 - i * 600)))
    stage1_calls, stage2_calls, window_calls = [], [], []
    original_stage1, original_stage2, original_window = scout.stage1, scout.stage2, scout.window_sigs
    monkeypatch.setattr(core, "rpc", lambda method, params: signatures.get(params[0], []))
    monkeypatch.setattr(cb, "fetch_tx", lambda sig: transactions.get(sig))

    def stage1(wallet, at):
        stage1_calls.append(wallet)
        return original_stage1(wallet, at)

    def stage2(wallet, sigs, sol_usd):
        stage2_calls.append(wallet)
        return original_stage2(wallet, sigs, sol_usd)

    def window(wallet, page, at, limit):
        window_calls.append((wallet, limit))
        return original_window(wallet, page, at, limit)

    monkeypatch.setattr(scout, "stage1", stage1)
    monkeypatch.setattr(scout, "stage2", stage2)
    monkeypatch.setattr(scout, "window_sigs", window)
    _, rows, ranked = scout.search(state, now, 100.0)
    assert stage1_calls == [early, bird, smart, kol, top]
    assert set(stage2_calls) == set(stage1_calls)
    assert all(limit == scout.STAGE2_TX for _, limit in window_calls)
    assert len(ranked) == 5
    by_wallet = {r["wallet"]: r for r in rows}
    assert by_wallet[early]["quelle"] == "frueh"
    assert by_wallet[bird]["quelle"] == "birdeye"
    assert [(by_wallet[w]["quelle"], by_wallet[w]["coin"]) for w in (smart, kol, top)] == [
        ("GMGN-smartmoney", ""), ("GMGN-kol", ""), ("GMGN-toptrader", "COIN 3.0x")]
    expected = original_stage2(smart, [s["signature"] for s in signatures[smart]], 100.0)
    assert by_wallet[smart]["punkte"] == scout.score(expected)
    assert scout.STATS["gmgn_neu"] == 3
    assert scout.STATS["gmgn_abfragen"] == len(calls) == 3
    scout.write_csv(rows)
    with open(scout.CANDIDATES_FILE, encoding="utf-8") as fh:
        saved = list(csv.DictReader(fh))
    assert {r["wallet"] for r in saved} == set(stage1_calls)
    assert not any("gmgn" in field.lower() for field in saved[0])


def test_search_40_kandidaten_6_coins_und_stufe2_limit(fake, monkeypatch):
    calls, replies = fake
    coins = [(addr("Mint" + ch), ch, 3.0) for ch in "ABCDEFG"]
    state = suchquellen(monkeypatch, coins)
    addresses = [addr("Trader" + a + b) for a in "ABCDEFG" for b in "ABCDEFG"]
    replies.extend([wallets(*addresses[:25]), wallets(*addresses[20:]), *[Antwort()] * 6])
    stage1_calls, stage2_calls = [], []

    def stage1(wallet, now):
        stage1_calls.append(wallet)
        return {"tx_pro_h": 10, "_page": []}, None

    monkeypatch.setattr(scout, "stage1", stage1)
    monkeypatch.setattr(scout, "stage2", lambda wallet, *a: stage2_calls.append(wallet) or {})
    scout.search(state, time.time(), 100.0)
    assert stage1_calls == addresses[:40]
    assert len(stage2_calls) == scout.STAGE2_PER_RUN
    assert [c[0] for c in calls] == [SMART, KOL] + [TOP] * 6
    assert [c[1]["address"] for c in calls[2:]] == [c[0] for c in coins[:6]]
    assert scout.STATS["gmgn_neu"] == 40
    assert scout.STATS["gmgn_adressen"] == 54


def test_search_geprueft_wallets_verbrauchen_kein_kontingent(fake, monkeypatch):
    calls, replies = fake
    state = suchquellen(monkeypatch)
    alt = [addr("Alt" + str(i)) for i in range(40)]
    neu = [addr("Neu1"), addr("Neu2")]
    now = time.time()
    state["wallets_geprueft"].update({w: now for w in alt})
    replies.extend([wallets(*alt), wallets(*neu)])
    geprueft = []
    monkeypatch.setattr(scout, "stage1", lambda w, n: geprueft.append(w) or ({}, "zu wenig Transaktionen"))
    scout.search(state, now, 100.0)
    assert geprueft == neu
    assert scout.STATS["gmgn_neu"] == 2


def test_search_ohne_coins_liefert_smartmoney_und_kol(fake, monkeypatch):
    calls, replies = fake
    state = suchquellen(monkeypatch)
    replies.extend([wallets(addr("Smart")), wallets(addr("Ko"))])
    monkeypatch.setattr(scout, "stage1", lambda *a: ({}, "zu wenig Transaktionen"))
    _, rows, _ = scout.search(state, time.time(), 100.0)
    assert [c[0] for c in calls] == [SMART, KOL]
    assert [r["quelle"] for r in rows] == ["GMGN-smartmoney", "GMGN-kol"]


def lauf_vorbereiten(monkeypatch):
    monkeypatch.setattr(core, "git_sync_start", lambda: None)
    monkeypatch.setattr(scout, "git_push", lambda: None)
    monkeypatch.setattr(scout, "check_list", lambda *a: ([], []))
    monkeypatch.setattr(scout, "check_transactions", lambda *a: [])
    monkeypatch.setattr(scout, "auto_wallets", lambda *a: [])


@pytest.mark.parametrize("modus", ["probe", "pruefliste"])
@pytest.mark.parametrize("key", [True, False])
def test_probe_und_pruefliste_ohne_gmgn_abfragen(fake, monkeypatch, modus, key, capsys):
    calls, _ = fake
    if not key:
        monkeypatch.delenv("GMGN_API_KEY")
    suchquellen(monkeypatch)
    lauf_vorbereiten(monkeypatch)
    if modus == "probe":
        scout.probe()
        assert "GMGN-Key: " + ("gesetzt" if key else "FEHLT") in capsys.readouterr().out
    else:
        scout.run(nur_liste=True)
    assert calls == []


@pytest.mark.parametrize("fall", ["normal", "kein_key", "429", "drei_fehler"])
def test_discord_zeile_im_scout_lauf(fake, monkeypatch, sandbox, fall):
    calls, replies = fake
    suchquellen(monkeypatch, [(MINT, "COIN", 3.0)])
    lauf_vorbereiten(monkeypatch)
    monkeypatch.setattr(scout, "stage1", lambda *a: ({}, "zu wenig Transaktionen"))
    if fall == "kein_key":
        monkeypatch.delenv("GMGN_API_KEY")
        expected = "**GMGN:** kein Key"
    elif fall == "429":
        replies.append(Antwort(status=429))
        expected = "**GMGN:** nach 429 abgebrochen"
    elif fall == "drei_fehler":
        replies.extend([Antwort(status=503)] * 3)
        expected = "**GMGN:** 3 Abfragen, 0 Adressen, 0 neu, 0x 429, 3 Fehler"
    else:
        replies.extend([wallets(addr("Smart")), wallets(addr("Ko")), wallets(addr("Top"))])
        expected = "**GMGN:** 3 Abfragen, 3 Adressen, 3 neu, 0x 429, 0 Fehler"
    scout.run()
    messages = [msg for title, msg in sandbox["discord"] if title == "🔭 Wallet-Scout"]
    assert len(messages) == 1
    assert expected in messages[0].splitlines()
    assert "TEST-PLATZHALTER" not in messages[0]
    assert len(calls) == (0 if fall == "kein_key" else 1 if fall == "429" else 3)
