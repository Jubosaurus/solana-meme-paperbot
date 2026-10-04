"""Copy-Bot: Kauf, Verkauf, Sammeln, Runde, Schatten, Nachholen, Abgleich, Flutschutz, Bereinigung, Wallet-Pruefung."""
import csv
import json
import os
import time

import pytest

import bot as core
import copy_bot as cb
from helpers import buy_tx, sell_tx, transfer_tx, WALLET, MINT, addr

PRICE_USD = 5e-5            # = 5e-7 SOL je Token bei 100 USD/SOL, passend zu 0,5 SOL fuer 1 Mio. Token


class Chain:
    """Fake-Helius: Transaktionen, Signaturlisten und Bestaende des Traders."""

    def __init__(self):
        self.txs, self.sigs, self.balance = {}, [], None

    def add(self, sig, tx):
        self.txs[sig] = tx
        self.sigs.insert(0, {"signature": sig, "blockTime": tx["blockTime"], "err": None})   # neueste zuerst

    def rpc(self, method, params):
        if method == "getTransaction":
            return self.txs.get(params[0])
        if method == "getSignaturesForAddress":
            return list(self.sigs)
        if method == "getTokenAccountsByOwner":
            if self.balance is None:
                return None
            return {"value": [{"account": {"data": {"parsed": {"info": {"tokenAmount": {"amount": str(self.balance)}}}}}}]}
        return None


@pytest.fixture
def env(market, monkeypatch):
    market.set(MINT, price=PRICE_USD)
    chain = Chain()
    monkeypatch.setattr(core, "rpc", chain.rpc)
    data = cb.load_accounts([("Alpha", WALLET)])

    class E:
        pass
    e = E()
    e.market, e.chain, e.data, e.acct = market, chain, data, data["wallets"]["Alpha"]
    return e


def trade(tx):
    t = cb.parse_trade(tx, WALLET, 100.0)
    assert t is not None
    return t


def journal_rows():
    return list(csv.DictReader(open(cb.JOURNAL_FILE, encoding="utf-8")))


def buy(e, sig="b1", sol=0.5, tokens=1_000_000, pre=0, **kw):
    cb.copy_buy("Alpha", e.acct, trade(buy_tx(sol=sol, tokens=tokens, pre=pre, sig=sig, **kw)), sig, time.time())


def sell(e, sig, tokens, pre, sol=None, reason="VERKAUF", **kw):
    sol = tokens * 5e-7 if sol is None else sol
    tx = transfer_tx(tokens=tokens, pre=pre, sig=sig) if reason == "UEBERWEISUNG" else \
        sell_tx(sol=sol, tokens=tokens, pre=pre, sig=sig, **kw)
    t = trade(tx)
    cb.copy_sell("Alpha", e.acct, t, sig, time.time(), t["kind"])


# ================================================================ Kauf

def test_kauf_02_sol_mit_gebuehr_des_traders(env):
    buy(env, prio=95_000, jito=100_000, botfee=5_000_000)
    pos = env.acct["positionen"][MINT]
    fee = 0.000005 + 0.000095 + 0.0001                      # ohne Bot-Gebuehr
    assert env.acct["bankroll_sol"] == pytest.approx(10 - 0.2 - fee)
    assert pos["invested_sol"] == 0.2 and pos["fees_sol"] == pytest.approx(fee)
    assert pos["tokens_raw"] == pytest.approx(400_000 * 10**6, rel=1e-6)    # 0,2 SOL / 5e-7
    assert pos["trader_ausgegeben_sol"] == pytest.approx(0.5)
    row = journal_rows()[0]
    assert row["aktion"] == "KAUF" and float(row["preisabstand_pct"]) == pytest.approx(0, abs=0.01)
    assert list(row.keys()) == cb.JOURNAL_HEADER


def test_nachkauf_ist_weiterer_kauf(env):
    buy(env, "b1")
    buy(env, "b2", pre=1_000_000)
    pos = env.acct["positionen"][MINT]
    assert pos["kaeufe"] == 2 and pos["invested_sol"] == pytest.approx(0.4)


def test_kauf_unter_0_1_sol_wird_ignoriert(env):
    buy(env, sol=0.09, tokens=180_000)
    assert env.acct["positionen"] == {}
    assert journal_rows()[0]["aktion"] == "AUSGELASSEN"
    assert cb.STATS["skipped"]["trader_kauf_unter_0_1"] == 1


def test_neue_runde_auch_mit_offenen_positionen(env):
    env.acct["positionen"]["alt"] = {"mint": "alt", "runde": 1, "tokens_raw": 5, "decimals": 0,
                                     "invested_sol": 0.2, "proceeds_sol": 0}
    env.acct["bankroll_sol"] = 0.15
    buy(env)
    assert env.acct["runde"] == 2
    assert env.acct["bankroll_sol"] == pytest.approx(10 - 0.2 - 0.000005)
    assert env.acct["positionen"]["alt"]["runde"] == 1
    assert env.acct["positionen"][MINT]["runde"] == 2


def test_preisabstand_ueber_15_prozent_wird_schattenposition(env):
    env.market.price[MINT] = PRICE_USD * 1.2                 # wir kaemen 20 % teurer rein
    buy(env)
    assert env.acct["positionen"] == {}
    sh = env.acct["schatten"][MINT]
    assert sh["invested_sol"] == 0.2 and sh["preisabstand_pct"][0] == pytest.approx(20, abs=0.1)
    assert [r["aktion"] for r in journal_rows()] == ["AUSGELASSEN", "SCHATTEN_KAUF"]
    # Trader steigt aus: Schatten schliesst zum Kurs des Traders (seit 03.10. mit Journalzeile)
    sell(env, "s1", tokens=1_000_000, pre=1_000_000, sol=0.75)
    assert env.acct["schatten"] == {}
    rec = env.acct["schatten_geschlossen"][0]
    assert rec["grund"] == "TRADER_AUSSTIEG"
    assert rec["erloes_sol"] == pytest.approx(sh["tokens"] * 0.75e-6, rel=1e-6)
    assert rec["trader_pnl_pct"] == pytest.approx(50)


def test_preisabstand_15_prozent_ist_noch_erlaubt(env):
    env.market.price[MINT] = PRICE_USD * 1.149
    buy(env)
    assert MINT in env.acct["positionen"]


# ================================================================ Verkauf

def test_teilverkaeufe_werden_gesammelt(env):
    buy(env)
    start = env.acct["positionen"][MINT]["tokens_raw"]
    sell(env, "s1", tokens=100_000, pre=1_000_000)               # 10 %
    pos = env.acct["positionen"][MINT]
    assert pos["tokens_raw"] == start and pos["gemerkt"] == 1
    assert journal_rows()[-1]["aktion"] == "VERKAUF_GEMERKT"
    sell(env, "s2", tokens=135_000, pre=900_000)                 # 15 % vom Rest: zusammen 23,5 %
    assert pos["tokens_raw"] == pytest.approx(start * 0.765, rel=1e-6)
    assert pos["gemerkt"] == 0 and pos["behalten"] == 1.0
    assert "gesammelt aus 2 Verkaeufen" in journal_rows()[-1]["hinweis"]


def test_kompletter_ausstieg_schliesst_position(env):
    buy(env)
    bank = env.acct["bankroll_sol"]
    env.market.price[MINT] = PRICE_USD * 2
    sell(env, "s1", tokens=1_000_000, pre=1_000_000, sol=1.0)
    assert env.acct["positionen"] == {}
    rec = env.acct["geschlossen"][0]
    assert rec["grund"] == "VERKAUF"
    assert rec["pnl_sol"] == pytest.approx(0.4 - 0.2 - 2 * 0.000005, rel=1e-4)
    assert rec["trader_pnl_sol"] == pytest.approx(0.5)
    assert env.acct["bankroll_sol"] == pytest.approx(bank + 0.4 - 0.000005, rel=1e-6)


def test_ueberweisung_verkauft_alles_ohne_trader_vergleich(env):
    buy(env)
    sell(env, "s1", tokens=1_000_000, pre=1_000_000, reason="UEBERWEISUNG")
    rec = env.acct["geschlossen"][0]
    assert rec["grund"] == "UEBERWEISUNG" and rec["trader_pnl_sol"] is None


def test_verkauf_nie_doppelt_verarbeitet(env):
    buy(env)
    sell(env, "s1", tokens=500_000, pre=1_000_000)
    left = env.acct["positionen"][MINT]["tokens_raw"]
    sell(env, "s1", tokens=500_000, pre=1_000_000)
    assert env.acct["positionen"][MINT]["tokens_raw"] == left


def test_trader_vergleich_nur_aufgezeichnete_coins(env):
    """Trader hielt schon 1 Mio. Token vor unserem Start; nur der aufgezeichnete Anteil zaehlt."""
    buy(env, pre=1_000_000)                                      # er kauft 1 Mio. dazu, haelt dann 2 Mio.
    sell(env, "s1", tokens=2_000_000, pre=2_000_000, sol=2.0)
    rec = env.acct["geschlossen"][0]
    assert rec["trader_erhalten_sol"] == pytest.approx(1.0)      # Haelfte des Erloeses ist aufgezeichnet


# ================================================================ Signale, Nachholen, Abgleich

def test_alter_kauf_wird_nie_nachgekauft(env):
    tx = buy_tx(sig="alt", block_time=int(time.time()) - 61)
    env.chain.add("alt", tx)
    cb.handle_signature("Alpha", env.acct, "alt", 100.0)
    assert env.acct["positionen"] == {}
    assert cb.STATS["skipped"]["kauf_zu_alt"] == 1


def test_nachholen_verkauf_mit_trader_kurs_und_verpasster_kauf(env):
    buy(env, "b1")
    old = int(time.time()) - 600
    env.chain.add("b2", buy_tx(sig="b2", pre=1_000_000, block_time=old))
    env.chain.add("s1", sell_tx(sig="s1", tokens=2_000_000, pre=2_000_000, sol=1.0, block_time=old + 60))
    n = cb.backfill("Alpha", env.acct, old - 1, 100.0)
    assert n == 2
    assert env.acct["positionen"] == {}
    rows = journal_rows()
    assert [r["aktion"] for r in rows] == ["KAUF", "VERPASST_KAUF", "VERKAUF"]
    assert "nachgeholt" in rows[-1]["hinweis"]
    assert cb.STATS["nachgeholt"] == 1 and cb.STATS["verpasst_kauf"] == 1
    assert len(cb.STATS["delays"]) == 1                                    # nur der Live-Kauf zaehlt
    # Neue Schicht (Gedaechtnis leer, Journal neu gelesen) holt dieselbe Luecke nach: nichts Neues
    cb._seen.clear()
    cb.load_accounts([("Alpha", WALLET)])
    cb.backfill("Alpha", env.acct, old - 1, 100.0)
    assert len(journal_rows()) == 3                     # vor dem 03.10.: VERPASST_KAUF wurde erneut dokumentiert


def test_abgleich_trader_haelt_nichts_mehr(env):
    buy(env)
    env.chain.balance = 0
    assert cb.reconcile(env.data, time.time(), 100.0) == 1
    rec = env.acct["geschlossen"][0]
    assert rec["grund"] == "ABGLEICH" and rec["trader_pnl_sol"] is None
    assert journal_rows()[-1]["aktion"] == "ABGLEICH"


def test_abgleich_teilweise_und_zukauf(env):
    buy(env)
    pos = env.acct["positionen"][MINT]
    start = pos["tokens_raw"]
    env.chain.balance = 500_000 * 10**6                          # Haelfte verkauft
    cb.reconcile(env.data, time.time(), 100.0)
    assert pos["tokens_raw"] == pytest.approx(start / 2, rel=1e-6)
    env.chain.balance = 900_000 * 10**6                          # zugekauft: nur merken
    cb.reconcile(env.data, time.time(), 100.0)
    assert pos["tokens_raw"] == pytest.approx(start / 2, rel=1e-6)
    assert pos["trader_bestand_raw"] == 900_000 * 10**6


def test_abgleich_unbekannter_bestand_verkauft_nichts(env):
    buy(env)
    env.chain.balance = None
    assert cb.reconcile(env.data, time.time(), 100.0) == 0
    assert MINT in env.acct["positionen"]


# ================================================================ WebSocket-Meldungen und Flutschutz

def note(sub=1, sig="x", err=None, logs=("Program log: Instruction: Buy",)):
    return {"method": "logsNotification", "params": {"subscription": sub, "result": {"value": {
        "signature": sig, "err": err, "logs": list(logs)}}}}


def test_flutschutz_bot_mit_vielen_fehlschlaegen(env):
    subs = {1: ("Alpha", WALLET)}
    for i in range(31):
        cb.process_message(note(sig=f"f{i}", err={"x": 1}), subs, env.data, 100.0)
    assert cb.STATS["muted"] == ["Alpha"] and subs == {}


def test_flutschutz_wird_mit_datum_gespeichert(env):
    """Seit 04.10.: Abmeldung landet in copy/flutschutz.json (Bot-Hinweis fuer die Scout-Automatik)."""
    for durchgang in (1, 2):
        cb.STATS["muted"] = []
        subs = {1: ("Alpha", WALLET)}
        for i in range(31):
            cb.process_message(note(sig=f"f{durchgang}-{i}", err={"x": 1}), subs, env.data, 100.0)
    e = json.load(open(cb.FLOOD_FILE, encoding="utf-8"))[WALLET]
    assert e["name"] == "Alpha" and e["anzahl"] == 2 and e["fehlgeschlagen_anteil"] == 1.0
    assert len(e["erstes"]) == 19 and e["zuletzt"] >= e["erstes"]


def test_flutschutz_kaputte_datei_stoppt_nichts(env):
    os.makedirs("copy", exist_ok=True)
    open(cb.FLOOD_FILE, "w").write("[kaputt")
    subs = {1: ("Alpha", WALLET)}
    for i in range(31):
        cb.process_message(note(sig=f"f{i}", err={"x": 1}), subs, env.data, 100.0)
    assert cb.STATS["muted"] == ["Alpha"]
    assert WALLET in json.load(open(cb.FLOOD_FILE, encoding="utf-8"))


def test_flutschutz_laesst_echten_vieltrader_in_ruhe(env, monkeypatch):
    """Lehre aus 922M: viele erfolgreiche Meldungen sind kein Bot."""
    monkeypatch.setattr(cb, "handle_signature", lambda *a, **kw: None)
    subs = {1: ("Alpha", WALLET)}
    for i in range(60):
        cb.process_message(note(sig=f"ok{i}", err={"x": 1} if i % 3 == 0 else None), subs, env.data, 100.0)
    assert cb.STATS["muted"] == []
    assert cb.STATS["fetched"] == 40


def test_flutschutz_ueber_300_pro_minute_immer(env, monkeypatch):
    monkeypatch.setattr(cb, "handle_signature", lambda *a, **kw: None)
    subs = {1: ("Alpha", WALLET)}
    for i in range(302):
        cb.process_message(note(sig=f"ok{i}"), subs, env.data, 100.0)
    assert cb.STATS["muted"] == ["Alpha"]
    assert env.acct["abgedeckt_bis"] > 0                          # naechste Schicht holt ab hier nach


def test_ueberweisungs_meldung_nur_mit_offener_position(env, monkeypatch):
    calls = []
    monkeypatch.setattr(cb, "handle_signature", lambda *a, **kw: calls.append(a[2]))
    subs = {1: ("Alpha", WALLET)}
    msg = note(sig="t1", logs=["Program log: Instruction: TransferChecked"])
    cb.process_message(msg, subs, env.data, 100.0)
    assert calls == []
    env.acct["positionen"][MINT] = {}
    cb.process_message(note(sig="t2", logs=["Program log: Instruction: TransferChecked"]), subs, env.data, 100.0)
    assert calls == ["t2"]


def test_fehler_bei_einem_trade_stoppt_den_bot_nicht(env, monkeypatch):
    def boom(*a, **kw):
        raise KeyError("kaputt")
    monkeypatch.setattr(cb, "handle_signature", boom)
    cb.process_message(note(sig="b"), {1: ("Alpha", WALLET)}, env.data, 100.0)
    assert cb.STATS["errors"] == 1


def test_trade_hint():
    assert cb.trade_hint({"logs": ["Program log: ray_log: abc"]}) == "handel"
    assert cb.trade_hint({"logs": ["Program log: Instruction: Sell"]}) == "handel"
    assert cb.trade_hint({"logs": ["Program log: Instruction: Transfer"]}) == "transfer"
    assert cb.trade_hint({"logs": ["Program log: Instruction: SetComputeUnitLimit"]}) is None


# ================================================================ Schichtende, Konto, Wallet-Pruefung

def test_bereinigung_nur_bei_hoechstens_1_prozent_restwert(env):
    buy(env)
    env.acct["positionen"]["tot"] = dict(env.acct["positionen"][MINT], mint="tot")
    env.market.set("tot", price=PRICE_USD * 0.005)               # -99,5 %
    env.market.decimals["tot"] = 6
    assert cb.cleanup(env.data) == 1
    assert set(env.acct["positionen"]) == {MINT}
    assert env.acct["geschlossen"][0]["grund"] == "BEREINIGT (-99 %)"


def test_konto_zeile_zeigt_kontowert(env):
    buy(env)
    pos = env.acct["positionen"][MINT]
    line = cb.account_line(env.acct)
    assert "Wert jetzt ~0.20 SOL" in line                          # ohne Kurs: noch nicht zurueckgeflossener Einsatz
    pos["letzter_preis_sol"] = 1e-6                              # Kurs verdoppelt
    line = cb.account_line(env.acct)
    assert "Wert jetzt ~0.40 SOL" in line
    assert f"Kontowert ~{env.acct['bankroll_sol'] + 0.4:.2f} SOL" in line


def test_endmeldung_nach_kontowert_sortiert(env, sandbox):
    buy(env)
    env.acct["positionen"][MINT]["letzter_preis_sol"] = 1e-6       # Position 0,2 SOL -> jetzt 0,4 SOL wert
    alpha_total = env.acct["bankroll_sol"] + 0.4                   # 10,2 SOL
    data = cb.load_accounts([("Alpha", WALLET), ("Beta", addr("Beta")), ("Gamma", addr("Gamma"))])
    data["wallets"]["Alpha"] = env.acct
    data["wallets"]["Beta"].update(bankroll_sol=8.5, runde=2)      # nur frei, keine Positionen
    data["wallets"]["Gamma"]["geschlossen"] = [{"pnl_sol": 5.0}]   # realisiert spielt keine Rolle mehr
    cb.summary(data, 3600, 0, True)
    text = sandbox["discord"][-1][1]
    block = text.split("**Wallets (Kontowert")[1].split("\n**")[0]
    rows = block.strip().splitlines()[1:]
    assert [r.split(":")[0] for r in rows] == ["Alpha", "Gamma", "Beta"]
    assert f"Alpha: **~{alpha_total:.2f} SOL** (+0.20 in Runde 1) | 1 offen, 0 geschlossen" in rows[0]
    assert "Gamma: **~10.00 SOL** (+0.00 in Runde 1)" in rows[1]
    assert "Beta: **~8.50 SOL** (-1.50 in Runde 2) | 0 offen" in rows[2]


def test_wallet_pruefung(env):
    now = time.time()
    env.acct["letzter_trade"] = now - 73 * 3600
    env.acct["geschlossen"] = [{"pnl_sol": -0.03}] * 30           # -0,9 SOL: noch kein Fall zum Pruefen
    notes = cb.wallet_check(env.data, ["Alpha"], now)
    assert any("kein eigener Trade" in n for n in notes)
    assert not any("lehrreich" in n for n in notes)
    env.acct["geschlossen"] = [{"pnl_sol": -0.034}] * 30          # -1,02 SOL
    assert any("pruefen, ob noch lehrreich" in n for n in cb.wallet_check(env.data, ["Alpha"], now))


def test_wallets_datei(tmp_path):
    open("w.txt", "w", encoding="utf-8").write(
        f"# Kommentar\nAlpha: {WALLET}\n# Weg: {addr('Weg')}  (entfernt 02.10.)\nKaputt: 0OIl\n\nBeta:{addr('Beta')}\n")
    assert cb.load_wallets("w.txt") == [("Alpha", WALLET), ("Beta", addr("Beta"))]


def test_konten_alte_daten_laufen_weiter(env):
    """Alte konten.json ohne neue Felder: load_accounts ergaenzt sie."""
    old = {"wallets": {"Alpha": {"adresse": WALLET, "bankroll_sol": 7.0, "runde": 3, "positionen": {},
                                 "geschlossen": [], "gestartet": "2026-09-30T00:00:00+00:00"}}}
    cb.save_accounts(old)
    data = cb.load_accounts([("Alpha", WALLET)])
    a = data["wallets"]["Alpha"]
    assert a["bankroll_sol"] == 7.0 and a["schatten"] == {} and a["schatten_geschlossen"] == []


# ================================================================ Jupiter-Ausfall (Pruefbericht 03.10.)
# Ein Ausfall darf nie als "wertlos" gebucht werden: Position bleibt offen, Verkauf wird spaeter nachgeholt.

REAL_QUOTE_OUT = cb.quote_out
REAL_JUP = cb.jup


class FakeResponse:
    def __init__(self, status, body):
        self.status_code, self._body = status, body

    def json(self):
        if self._body is None:
            raise ValueError("kein JSON")
        return self._body


@pytest.mark.parametrize("status, body, expected", [
    (200, {"outAmount": "12345"}, 12345),
    (400, {"error": "not tradable", "errorCode": "TOKEN_NOT_TRADABLE"}, 0),
    (400, {"error": "no route", "errorCode": "COULD_NOT_FIND_ANY_ROUTE"}, 0),
    (500, None, None),
    (400, {"error": "Bad request"}, None),
    (429, None, None),
])
def test_quote_unterscheidet_keine_route_und_ausfall(monkeypatch, status, body, expected):
    class Session:
        def get(self, *a, **kw):
            return FakeResponse(status, body)
    monkeypatch.setattr(core, "SESSION", Session())
    monkeypatch.setattr(cb, "jup", REAL_JUP)
    assert REAL_QUOTE_OUT(MINT, core.WSOL_MINT, 1000) == expected


def test_quote_ohne_antwort_ist_ausfall(monkeypatch):
    monkeypatch.setattr(cb, "jup", lambda path: None)
    assert REAL_QUOTE_OUT(MINT, core.WSOL_MINT, 1000) is None
    assert cb.STATS["quote_ausfall"] == 1


def test_kauf_bei_ausfall_ausgelassen(env):
    env.market.ausfall.add(MINT)
    bank = env.acct["bankroll_sol"]
    buy(env)
    assert env.acct["positionen"] == {} and env.acct["bankroll_sol"] == bank


def test_verkauf_bei_ausfall_vorgemerkt_und_beim_abgleich_nachgeholt(env):
    buy(env)
    pos = env.acct["positionen"][MINT]
    tokens, bank = pos["tokens_raw"], env.acct["bankroll_sol"]
    env.market.ausfall.add(MINT)
    sell(env, "s1", tokens=1_000_000, pre=1_000_000, sol=0.5)
    assert env.acct["positionen"][MINT] is pos                     # nicht mit Wert 0 geschlossen
    assert pos["tokens_raw"] == tokens and env.acct["bankroll_sol"] == bank
    assert pos["verkauf_offen"] is True and cb.STATS["verkauf_verschoben"] == 1
    row = journal_rows()[-1]
    assert row["aktion"] == "VERKAUF_GEMERKT" and "Ausfall" in row["hinweis"]
    sell(env, "s1", tokens=1_000_000, pre=1_000_000, sol=0.5)      # gleiche Signatur: nicht doppelt
    assert cb.STATS["verkauf_verschoben"] == 1

    env.chain.balance = 0
    cb.reconcile(env.data, time.time(), 100.0)                     # Jupiter noch weg: bleibt offen
    assert MINT in env.acct["positionen"]

    env.market.ausfall.clear()
    cb.reconcile(env.data, time.time(), 100.0)
    assert env.acct["positionen"] == {}
    rec = env.acct["geschlossen"][0]
    assert rec["grund"] == "VERKAUF" and rec["proceeds_sol"] == pytest.approx(0.2, rel=1e-4)   # 0,2 SOL zum unveraenderten Kurs
    assert rec["trader_pnl_sol"] == pytest.approx(0.0, abs=1e-9)   # Trader-Vergleich bleibt erhalten
    assert "nach Jupiter-Ausfall nachgeholt" in journal_rows()[-1]["hinweis"]


def test_vorgemerkter_teilverkauf_beim_naechsten_signal(env):
    buy(env)
    pos = env.acct["positionen"][MINT]
    start = pos["tokens_raw"]
    env.market.ausfall.add(MINT)
    sell(env, "s1", tokens=300_000, pre=1_000_000)                 # 30 %: wuerde verkauft, Jupiter weg
    assert pos["tokens_raw"] == start and pos["verkauf_offen"]
    env.market.ausfall.clear()
    sell(env, "s2", tokens=70_000, pre=700_000)                    # weitere 10 % des Rests
    assert pos["tokens_raw"] == pytest.approx(start * 0.7 * 0.9, rel=1e-6)
    assert "verkauf_offen" not in pos


def test_abgleich_bei_ausfall_verkauft_nichts(env):
    buy(env)
    env.chain.balance = 0
    env.market.ausfall.add(MINT)
    assert cb.reconcile(env.data, time.time(), 100.0) == 0
    assert MINT in env.acct["positionen"] and env.acct["positionen"][MINT]["tokens_raw"] > 0


def test_bereinigung_bei_ausfall_laesst_position_offen(env):
    buy(env)
    env.market.ausfall.add(MINT)                                   # Kurssuche (cb.jup) liefert im Test nichts
    assert cb.cleanup(env.data) == 0
    assert MINT in env.acct["positionen"] and env.acct["geschlossen"] == []


def test_bereinigung_ohne_route_schliesst_weiter(env):
    buy(env)
    env.market.price[MINT] = 0                                     # Fake: Quote 0 = Jupiter sagt "keine Route"
    assert cb.cleanup(env.data) == 1
    assert env.acct["geschlossen"][0]["grund"] == "BEREINIGT (-99 %)"


def test_endmeldung_zeigt_wartende_verkaeufe(env, sandbox):
    buy(env)
    env.market.ausfall.add(MINT)
    sell(env, "s1", tokens=1_000_000, pre=1_000_000, sol=0.5)
    cb.summary(env.data, 3600, 0, True)
    text = sandbox["discord"][-1][1]
    assert "1 Position(en) warten noch auf den Verkauf" in text


# ================================================================ Nachholen ueber Schichtgrenzen (Pruefbericht 03.10.)
# 16 Verkaeufe wurden doppelt ausgefuehrt und 220 Kaeufe faelschlich als VERPASST_KAUF dokumentiert: Der Abgleich
# einer neuen Schicht holte bis zur Eroeffnung der Position nach, gemerkt waren nur 60 Signaturen je Position.

def neue_schicht(env):
    """Schichtwechsel: Konten speichern, Gedaechtnis leeren, Konten und Journal neu laden."""
    cb.save_accounts(env.data)
    cb._seen.clear()
    cb._done.clear()
    env.data = cb.load_accounts([("Alpha", WALLET)])
    env.acct = env.data["wallets"]["Alpha"]


def test_neue_schicht_verkauf_nicht_doppelt_trotz_60er_grenze(env):
    now = int(time.time())
    env.chain.add("b1", buy_tx(sig="b1", block_time=now))
    env.chain.add("s1", sell_tx(sig="s1", tokens=300_000, pre=1_000_000, block_time=now + 1))
    cb.handle_signature("Alpha", env.acct, "b1", 100.0)
    cb.handle_signature("Alpha", env.acct, "s1", 100.0)
    tokens = env.acct["positionen"][MINT]["tokens_raw"]
    rows = len(journal_rows())
    neue_schicht(env)
    env.acct["positionen"][MINT]["sigs"] = []           # wie bei 922M: alte Signaturen aus der 60er-Liste gefallen
    cb.backfill("Alpha", env.acct, now - 60, 100.0)
    pos = env.acct["positionen"][MINT]
    assert pos["tokens_raw"] == tokens and pos["kaeufe"] == 1 and pos["verkaeufe"] == 1
    assert len(journal_rows()) == rows                  # weder VERKAUF noch VERPASST_KAUF erneut
    assert cb.STATS["skipped"]["schon_verarbeitet"] == 2


def test_neue_schicht_holt_wirklich_verpasste_verkaeufe_weiter_nach(env):
    now = int(time.time())
    env.chain.add("b1", buy_tx(sig="b1", block_time=now))
    cb.handle_signature("Alpha", env.acct, "b1", 100.0)
    neue_schicht(env)
    env.chain.add("s1", sell_tx(sig="s1", tokens=1_000_000, pre=1_000_000, block_time=now + 1))
    cb.backfill("Alpha", env.acct, now - 60, 100.0)
    assert env.acct["positionen"] == {} and journal_rows()[-1]["aktion"] == "VERKAUF"


def test_schattenverkauf_mit_journalzeile_und_nicht_doppelt(env):
    env.market.price[MINT] = PRICE_USD * 1.2
    buy(env)
    sell(env, "s1", tokens=300_000, pre=1_000_000, sol=0.2)
    rows = journal_rows()
    assert rows[-1]["aktion"] == "SCHATTEN_VERKAUF" and rows[-1]["trader_signatur"] == "s1"
    behalten = env.acct["schatten"][MINT]["behalten"]
    neue_schicht(env)
    env.acct["schatten"][MINT]["sigs"] = []
    env.chain.add("s1", sell_tx(sig="s1", tokens=300_000, pre=1_000_000, sol=0.2))
    cb.handle_signature("Alpha", env.acct, "s1", 100.0)
    assert env.acct["schatten"][MINT]["behalten"] == behalten and len(journal_rows()) == len(rows)


def test_kaputte_trader_zeit_im_journal_verhindert_start_nicht(env):
    buy(env)
    cb.journal({"zeit": "x", "trader": "Alpha", "aktion": "KAUF", "trader_zeit": "kaputt", "trader_signatur": "z"})
    data = cb.load_accounts([("Alpha", WALLET)])
    assert "Alpha" in data["wallets"] and ("Alpha", "z") in cb._done


# ================================================================ Messung Quote 2 s spaeter (03.10., nur Aufzeichnung)

def messung_rows():
    return list(csv.DictReader(open(cb.MESSUNG_FILE, encoding="utf-8")))


def test_messung_nach_kauf_ohne_warten(env, monkeypatch):
    monkeypatch.setattr(cb, "_jup_last", [0.0])
    buy(env, sig="b1")
    assert len(cb._rechecks) == 1
    now = time.time()
    cb.run_rechecks(now)                                          # noch nicht faellig
    assert len(cb._rechecks) == 1
    env.market.price[MINT] = PRICE_USD * 1.25                     # Kurs steigt: 2 s spaeter 20 % weniger Token
    cb.run_rechecks(now + 2.5)
    row = messung_rows()[0]
    assert row["aktion"] == "KAUF" and row["trader_signatur"] == "b1" and row["abweichung_pct"] == "+20.00"
    assert row["mint"] == MINT and cb.STATS["messung"] == [pytest.approx(20.0)]


def test_messung_nach_verkauf(env, monkeypatch):
    monkeypatch.setattr(cb, "_jup_last", [0.0])
    buy(env)
    cb._rechecks.clear()
    sell(env, "s1", tokens=1_000_000, pre=1_000_000)
    env.market.price[MINT] = PRICE_USD * 0.9
    cb.run_rechecks(time.time() + 2.5)
    row = messung_rows()[0]
    assert row["aktion"] == "VERKAUF" and row["abweichung_pct"] == "+10.00" and row["mint"] == MINT


def test_messung_wartet_auf_freien_jupiter_takt_und_verwirft_zu_spaete(env, monkeypatch):
    buy(env)
    now = time.time() + 2.5
    monkeypatch.setattr(cb, "_jup_last", [now])                   # Jupiter gerade erst abgefragt
    cb.run_rechecks(now)
    assert len(cb._rechecks) == 1 and not os.path.exists(cb.MESSUNG_FILE)
    cb.run_rechecks(now + 20)                                     # viel zu spaet: keine 2-s-Messung mehr
    assert len(cb._rechecks) == 0 and cb.STATS["messung_verworfen"] == 1


def test_messung_bei_ausfall_verworfen(env, monkeypatch):
    monkeypatch.setattr(cb, "_jup_last", [0.0])
    buy(env)
    env.market.ausfall.add(MINT)
    cb.run_rechecks(time.time() + 2.5)
    assert cb.STATS["messung_verworfen"] == 1 and not os.path.exists(cb.MESSUNG_FILE)


def test_copy_verlauf_mit_flugschreiber_spalten_hinten(env, monkeypatch):
    buy(env)
    monkeypatch.setattr(cb, "jup", lambda path: env.market.search([MINT]) if path.startswith("/tokens/v2/search") else None)
    alt = ["zeit", "trader", "art", "symbol", "mint", "minuten_seit_kauf", "preis_sol", "vielfaches", "wert_sol",
           "liquiditaet"]
    os.makedirs(cb.COPY_VERLAUF_DIR, exist_ok=True)
    from datetime import datetime, timezone
    pfad = os.path.join(cb.COPY_VERLAUF_DIR, datetime.now(timezone.utc).strftime("%Y-%m-%d") + ".csv")
    with open(pfad, "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerows([alt, ["x", "Alpha", "offen", "A", "m", "1", "1", "1", "1", "1"]])
    cb.log_paths(env.data, 100.0, time.time())
    rows = list(csv.reader(open(pfad, encoding="utf-8")))
    assert rows[0] == cb.COPY_VERLAUF_HEADER and rows[0][:10] == alt
    assert len(rows[1]) == len(cb.COPY_VERLAUF_HEADER) and rows[1][10:] == [""] * 5      # alte Zeile: leer ergaenzt
    neu = dict(zip(rows[0], rows[-1]))
    assert neu["mint"] == MINT and neu["holder"] != "" and neu["top10_pct"] != ""
