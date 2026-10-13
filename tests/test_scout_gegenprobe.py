"""Gegenprobe: gemeinsame Rohdaten, lokale Rechnung und sichere Artefakte."""
import copy
import hashlib
import inspect
import json
import math
import re
import sys
from urllib.parse import quote
from pathlib import Path

import pytest

import bot as core
import copy_bot as cb
import scout_bot as scout
from helpers import MINT, WALLET, addr, buy_tx, sell_tx, transfer_tx
from tools import scout_gegenprobe_holen as holen
from tools import scout_gegenprobe_rechnen as rechnen

REPO = Path(__file__).resolve().parent.parent
JETZT = 1_700_000_000


@pytest.fixture(autouse=True)
def abhol_umgebung(monkeypatch):
    monkeypatch.setattr(holen, "core", core)
    monkeypatch.setattr(holen, "cb", cb)
    monkeypatch.setattr(holen, "scout", scout)
    monkeypatch.delenv("HELIUS_API_KEY", raising=False)
    monkeypatch.delenv("JUPITER_API_KEY", raising=False)


def sig(name):
    return hashlib.sha256(name.encode("utf-8")).hexdigest().replace("0", "z")


def wallet_daten(name="Altbestand", adresse=WALLET):
    trades = {}
    kurse = {}
    for i in range(3):
        mint = addr(f"Mint{i + 1}")
        kauf = buy_tx(mint=mint, pre=900, tokens=100, sol=1, block_time=JETZT - 7200 + i)
        verkauf = sell_tx(mint=mint, pre=1000, tokens=500, sol=5, block_time=JETZT - 1000 + i)
        trades[f"v{i}"] = cb.parse_trade(verkauf, WALLET, 100)
        trades[f"k{i}"] = cb.parse_trade(kauf, WALLET, 100)
        kurse[mint] = 0.01
    return {"name": name, "adresse": adresse, "signaturen": list(trades), "trades": trades,
            "juengste_block_time": JETZT - 1000, "fehler": {"anzahl": 0, "klassen": {}}}, kurse


def roh_daten(wallets, kurse=None):
    return {"wallets": wallets, "kurse_sol": kurse or {}, "sol_usd": 100.0,
            "zeitstempel": JETZT, "rpc_aufrufe": 42, "fehler": {"anzahl": 0, "klassen": {}}}


def fake_konto(adresse, pnl=2, geschlossen=5):
    return {"adresse": adresse, "geschlossen": [{"pnl_sol": pnl / geschlossen}
            for _ in range(geschlossen)], "positionen": {}}


def fake_holen(monkeypatch, tmp_path, seiten, transactions):
    liste = tmp_path / "wallets.txt"
    liste.write_text("# Kommentar\n\n" + "\n".join(f"Name{i} {w}" for i, w in enumerate(seiten))
                     + " # Kommentar am Ende\n", encoding="utf-8")
    calls = []

    def rpc(method, params):
        calls.append((method, params))
        antwort = seiten[params[0]]
        if isinstance(antwort, Exception):
            raise antwort
        return antwort

    monkeypatch.setattr(core, "rpc", rpc)
    monkeypatch.setattr(core, "sol_price", lambda: 100.0)
    monkeypatch.setattr(cb, "fetch_tx", transactions.get)
    return liste, tmp_path / "gegenprobe" / "rohdaten.json", calls


def test_holen_json_fehlt_null_transfer_fenster_und_kurse(monkeypatch, tmp_path, capsys, sandbox):
    seite = [{"signature": s, "blockTime": JETZT - i, "err": err} for i, (s, err) in enumerate(
        [(sig("fehlt"), None), (sig("transfer"), None), (sig("kein_trade"), None), (sig("kauf"), None), (sig("fehlgeschlagen"), {})])]
    seite.append({"signature": sig("zu_alt"), "blockTime": JETZT - 8 * 86400, "err": None})
    transactions = {sig("kauf"): buy_tx(block_time=JETZT - 3), sig("kein_trade"): {},
                    sig("transfer"): transfer_tx(block_time=JETZT - 1)}
    liste, ziel, calls = fake_holen(monkeypatch, tmp_path, {WALLET: seite}, transactions)
    kurse_calls = []

    def prices(mints, sol_usd):
        kurse_calls.append((set(mints), sol_usd))
        return {MINT: 0.001}

    monkeypatch.setattr(scout, "current_prices_sol", prices)
    assert holen.holen(liste, ziel, JETZT) == 0
    daten = json.loads(ziel.read_text(encoding="utf-8"))
    w = daten["wallets"][0]
    assert w["signaturen"] == [sig(s) for s in ("fehlt", "transfer", "kein_trade", "kauf")]
    assert w["trades"][sig("fehlt")] == "fehlt"
    assert w["trades"][sig("kein_trade")] is None
    assert w["trades"][sig("kauf")]["kind"] == "KAUF"
    assert w["trades"][sig("transfer")]["kind"] == "UEBERWEISUNG"
    assert w["juengste_block_time"] == JETZT
    assert daten["rpc_aufrufe"] == w["rpc_aufrufe"] == 5
    assert daten["sol_usd"] == 100 and daten["zeitstempel"] == JETZT
    assert daten["kurse_sol"] == {MINT: 0.001}
    assert daten["fehler"] == {"anzahl": 0, "klassen": {}}
    assert kurse_calls == [({MINT}, 100.0)]
    assert calls == [("getSignaturesForAddress", [WALLET, {"limit": 1000}])]
    assert capsys.readouterr().out == "Wallet 1/1: 4 Signaturen, 1 fehlen\n"
    assert not sandbox["git"] and not sandbox["discord"]
    assert not (tmp_path / "scout").exists() and not (tmp_path / "copy").exists()


def test_holen_maximal_60_signaturen(monkeypatch, tmp_path):
    seite = [{"signature": sig(f"sig{i}"), "blockTime": JETZT - i, "err": None} for i in range(100)]
    liste, ziel, _ = fake_holen(monkeypatch, tmp_path, {WALLET: seite}, {})
    monkeypatch.setattr(scout, "current_prices_sol", lambda *a: {})
    assert holen.holen(liste, ziel, JETZT) == 0
    d = json.loads(ziel.read_text(encoding="utf-8"))
    assert d["wallets"][0]["signaturen"] == [sig(f"sig{i}") for i in range(60)]
    assert d["rpc_aufrufe"] == 61


@pytest.mark.parametrize("phase", ["rpc", "fetch", "parse"])
def test_holen_fehlertext_geheim_bleibt_unsichtbar_weiter(monkeypatch, tmp_path, capsys, phase):
    url = "https://mainnet.helius-rpc.com/?api-key=GEHEIM"
    err = RuntimeError(url)
    zweites = addr("Zweiter")
    page = [{"signature": sig("sig"), "blockTime": JETZT, "err": None}]
    liste, ziel, _ = fake_holen(monkeypatch, tmp_path,
                               {WALLET: err if phase == "rpc" else page, zweites: []}, {sig("sig"): {}})
    if phase != "rpc":
        def kaputt(*a):
            raise err
        monkeypatch.setattr(cb, "fetch_tx" if phase == "fetch" else "parse_trade", kaputt)
    monkeypatch.setattr(scout, "current_prices_sol", lambda *a: {})
    assert holen.holen(liste, ziel, JETZT) == 0
    text = ziel.read_text(encoding="utf-8")
    out = capsys.readouterr()
    for inhalt in (text, out.out, out.err):
        assert url not in inhalt and "GEHEIM" not in inhalt
    assert WALLET not in out.out and zweites not in out.out
    d = json.loads(text)
    assert len(d["wallets"]) == 2
    assert d["wallets"][0]["fehler"] == {"anzahl": 1, "klassen": {"RuntimeError": 1}}
    assert d["wallets"][1]["fehler"]["anzahl"] == 0
    assert d["fehler"]["anzahl"] == 1
    assert "Wallet 2/2: 0 Signaturen, 0 fehlen" in out.out


@pytest.mark.parametrize("inhalt", ["api-key=GEHEIM", "helius-rpc.com", "API-KEY=GEHEIM",
                                    "api%2dkey=GEHEIM", "HELIUS%2dRPC%2eCOM"])
def test_holen_gesperrter_inhalt_abbruch_ohne_datei(monkeypatch, tmp_path, capsys, inhalt):
    page = [{"signature": sig("sig"), "blockTime": JETZT, "err": None}]
    liste, ziel, _ = fake_holen(monkeypatch, tmp_path, {WALLET: page}, {sig("sig"): {}})
    monkeypatch.setattr(cb, "parse_trade", lambda *a: {"mint": inhalt})
    monkeypatch.setattr(scout, "current_prices_sol", lambda *a: {})
    assert holen.holen(liste, ziel, JETZT) == 1
    assert not ziel.exists() and not ziel.parent.exists()
    assert "GEHEIM" not in capsys.readouterr().out


@pytest.mark.parametrize("runden", [2, 5])
def test_holen_mehrfach_kodierte_helius_url_ohne_datei(monkeypatch, tmp_path, capsys, runden):
    url = "https://mainnet.helius-rpc.com/?api-key=DUMMY12345"
    inhalt = "".join(f"%{byte:02X}" for byte in url.encode("utf-8"))
    for _ in range(runden - 1):
        inhalt = quote(inhalt, safe="")
    page = [{"signature": sig("sig"), "blockTime": JETZT, "err": None}]
    liste, ziel, _ = fake_holen(monkeypatch, tmp_path, {WALLET: page}, {sig("sig"): {}})
    monkeypatch.setattr(cb, "parse_trade", lambda *a: {"mint": MINT, "unbekannt": inhalt})
    monkeypatch.setattr(scout, "current_prices_sol", lambda *a: {})
    assert holen.holen(liste, ziel, JETZT) == 1
    assert not ziel.exists() and not ziel.parent.exists()
    captured = capsys.readouterr()
    assert captured.out == "Abbruch: Rohdaten enthalten gesperrte Inhalte.\n"
    assert captured.err == ""


@pytest.mark.parametrize("inhalt", ["https://example.test/pfad", "HtTpS://example.test/pfad",
                                    "ftp://example.test/pfad", "HtTp"])
def test_holen_url_im_feld_ohne_datei(monkeypatch, tmp_path, capsys, inhalt):
    page = [{"signature": sig("sig"), "blockTime": JETZT, "err": None}]
    liste, ziel, _ = fake_holen(monkeypatch, tmp_path, {WALLET: page}, {sig("sig"): {}})
    monkeypatch.setattr(cb, "parse_trade", lambda *a: {"mint": MINT, "unbekannt": inhalt})
    monkeypatch.setattr(scout, "current_prices_sol", lambda *a: {})
    assert holen.holen(liste, ziel, JETZT) == 1
    assert not ziel.exists() and not ziel.parent.exists()
    captured = capsys.readouterr()
    assert captured.out == "Abbruch: Rohdaten enthalten gesperrte Inhalte.\n"
    assert captured.err == ""


@pytest.mark.parametrize("schluessel", ["kaputt!", "0" * 32, "1" * 31, "1" * 91,
                                       addr("FremderMint")])
def test_holen_kurs_ungueltiger_schluessel_oder_fremder_mint_verworfen(
        monkeypatch, tmp_path, schluessel):
    page = [{"signature": sig("kauf"), "blockTime": JETZT, "err": None}]
    liste, ziel, _ = fake_holen(monkeypatch, tmp_path, {WALLET: page},
                               {sig("kauf"): buy_tx(block_time=JETZT)})
    monkeypatch.setattr(scout, "current_prices_sol", lambda *a: {MINT: 0.01, schluessel: 0.02})
    assert holen.holen(liste, ziel, JETZT) == 0
    daten = json.loads(ziel.read_text(encoding="utf-8"))
    assert daten["kurse_sol"] == {MINT: 0.01}
    assert daten["fehler"] == {"anzahl": 1, "klassen": {"ValueError": 1}}
    assert daten["wallets"][0]["fehler"]["anzahl"] == 0


@pytest.mark.parametrize("wert", [float("nan"), float("inf"), float("-inf"), None,
                                  True, "0.01", {}, []])
def test_holen_ungueltiger_kurs_verworfen(monkeypatch, tmp_path, wert):
    zweiter_mint = addr("ZweiterMint")
    page = [{"signature": sig(s), "blockTime": JETZT, "err": None}
            for s in ("kauf", "zweiter_kauf")]
    liste, ziel, _ = fake_holen(monkeypatch, tmp_path, {WALLET: page}, {
        sig("kauf"): buy_tx(block_time=JETZT),
        sig("zweiter_kauf"): buy_tx(mint=zweiter_mint, block_time=JETZT)})
    monkeypatch.setattr(scout, "current_prices_sol", lambda *a: {MINT: wert, zweiter_mint: 1})
    assert holen.holen(liste, ziel, JETZT) == 0
    daten = json.loads(ziel.read_text(encoding="utf-8"))
    assert daten["kurse_sol"] == {zweiter_mint: 1.0}
    assert type(daten["kurse_sol"][zweiter_mint]) is float
    assert daten["fehler"] == {"anzahl": 1, "klassen": {"ValueError": 1}}
    assert daten["wallets"][0]["fehler"]["anzahl"] == 0


def test_log_mit_doppelter_absicherung(monkeypatch, capsys):
    calls = []
    monkeypatch.setattr(core, "_hide_key", lambda text: calls.append(text) or text)
    holen.log('Fehler api-key=GEHEIM&weiter=1')
    assert len(calls) == 1
    assert capsys.readouterr().out == "Fehler api-key=***&weiter=1\n"


@pytest.mark.parametrize("name", ["HELIUS_API_KEY", "JUPITER_API_KEY"])
@pytest.mark.parametrize("kodiert", [False, True])
def test_holen_umgebungsschluessel_im_trade_abbruch(monkeypatch, tmp_path, capsys, name, kodiert):
    geheim = "TESTGEHEIM12345"
    monkeypatch.setenv(name, geheim)
    inhalt = "%54" + quote(geheim[1:]) if kodiert else geheim
    page = [{"signature": sig("sig"), "blockTime": JETZT, "err": None}]
    liste, ziel, _ = fake_holen(monkeypatch, tmp_path, {WALLET: page}, {sig("sig"): {}})
    monkeypatch.setattr(cb, "parse_trade", lambda *a: {"mint": MINT, "unbekannt": inhalt})
    monkeypatch.setattr(scout, "current_prices_sol", lambda *a: {})
    assert holen.holen(liste, ziel, JETZT) == 1
    assert not ziel.exists() and not ziel.parent.exists()
    captured = capsys.readouterr()
    assert geheim not in captured.out + captured.err
    assert inhalt not in captured.out + captured.err
    assert captured.out == "Abbruch: Rohdaten enthalten gesperrte Inhalte.\n"
    assert captured.err == ""


@pytest.mark.parametrize("inhalt", ["TESTGEHEIM12345", "%54ESTGEHEIM12345", "api%2dkey"])
def test_holen_sperre_auch_im_finalen_json(monkeypatch, tmp_path, capsys, inhalt):
    monkeypatch.setenv("HELIUS_API_KEY", "TESTGEHEIM12345")
    liste, ziel, _ = fake_holen(monkeypatch, tmp_path, {WALLET: []}, {})
    monkeypatch.setattr(scout, "current_prices_sol", lambda *a: {MINT: inhalt})
    assert holen.holen(liste, ziel, JETZT) == 1
    assert not ziel.exists() and not ziel.parent.exists()
    captured = capsys.readouterr()
    assert "TESTGEHEIM12345" not in captured.out + captured.err
    assert inhalt not in captured.out + captured.err


@pytest.mark.parametrize("ungueltig", ["ungueltig!", "0" * 64, "I" * 64, "O" * 64,
                                     "l" * 64, "1" * 31, "1" * 91, "1" * 32 + "\n"])
def test_holen_ungueltige_signatur_als_fehlt(monkeypatch, tmp_path, ungueltig):
    page = [{"signature": s, "blockTime": JETZT, "err": None}
            for s in (ungueltig, sig("kauf"))]
    liste, ziel, _ = fake_holen(monkeypatch, tmp_path, {WALLET: page}, {})
    fetch_calls = []
    monkeypatch.setattr(cb, "fetch_tx", lambda s: fetch_calls.append(s))
    monkeypatch.setattr(scout, "current_prices_sol", lambda *a: {})
    assert holen.holen(liste, ziel, JETZT) == 0
    d = json.loads(ziel.read_text(encoding="utf-8"))
    w = d["wallets"][0]
    assert w["signaturen"] == ["fehlt", sig("kauf")]
    assert w["trades"]["fehlt"] == "fehlt"
    assert ungueltig not in w["trades"]
    assert fetch_calls == [sig("kauf")]
    assert d["fehler"] == w["fehler"] == {"anzahl": 1, "klassen": {"ValueError": 1}}


def test_holen_trade_nur_bekannte_felder(monkeypatch, tmp_path):
    page = [{"signature": sig("kauf"), "blockTime": JETZT, "err": None}]
    liste, ziel, _ = fake_holen(monkeypatch, tmp_path, {WALLET: page},
                               {sig("kauf"): buy_tx(block_time=JETZT)})
    parse = cb.parse_trade
    erwartet = parse(buy_tx(block_time=JETZT), WALLET, 100)
    monkeypatch.setattr(cb, "parse_trade", lambda *a: dict(parse(*a), unbekannt="antworttext"))
    monkeypatch.setattr(scout, "current_prices_sol", lambda *a: {})
    assert holen.holen(liste, ziel, JETZT) == 0
    d = json.loads(ziel.read_text(encoding="utf-8"))
    assert d["wallets"][0]["trades"][sig("kauf")] == erwartet
    assert d["fehler"]["anzahl"] == 0


@pytest.mark.parametrize("feld,wert", [("mint", "kaputt!"), ("mint", None),
                                      ("kind", "beliebig"), ("quote_asset", "beliebig"),
                                      ("tokens", "123"), ("sol", True), ("fee_base", {}),
                                      ("block_time", [])])
def test_holen_ungueltiger_trade_fehler_und_weiter(monkeypatch, tmp_path, feld, wert):
    page = [{"signature": sig(s), "blockTime": JETZT, "err": None}
            for s in ("kaputt", "kauf")]
    tx = buy_tx(block_time=JETZT)
    liste, ziel, _ = fake_holen(monkeypatch, tmp_path, {WALLET: page},
                               {sig("kaputt"): {}, sig("kauf"): tx})
    parse = cb.parse_trade
    trade = parse(tx, WALLET, 100)
    monkeypatch.setattr(cb, "parse_trade", lambda t, *a:
                        dict(trade, **{feld: wert}) if not t else parse(t, *a))
    kurse_calls = []
    monkeypatch.setattr(scout, "current_prices_sol", lambda m, *a: kurse_calls.append(set(m)) or {})
    assert holen.holen(liste, ziel, JETZT) == 0
    d = json.loads(ziel.read_text(encoding="utf-8"))
    w = d["wallets"][0]
    assert w["trades"][sig("kaputt")] is None
    assert w["trades"][sig("kauf")] == trade
    assert kurse_calls == [{MINT}]
    assert d["fehler"] == w["fehler"] == {"anzahl": 1, "klassen": {"ValueError": 1}}


def test_holen_keyboardinterrupt_nur_klasse(monkeypatch, tmp_path, capsys):
    page = [{"signature": sig("kauf"), "blockTime": JETZT, "err": None}]
    liste, ziel, _ = fake_holen(monkeypatch, tmp_path, {WALLET: page}, {})

    def kaputt(*args):
        print("TESTGEHEIM12345", file=sys.stderr)
        raise KeyboardInterrupt("TESTGEHEIM12345")

    monkeypatch.setattr(cb, "fetch_tx", kaputt)
    original = holen.holen
    monkeypatch.setattr(holen, "holen", lambda: original(liste, ziel, JETZT))
    assert holen.main() == 1
    assert not ziel.exists() and not ziel.parent.exists()
    captured = capsys.readouterr()
    assert captured.out == "Abbruch: KeyboardInterrupt\n" and captured.err == ""


@pytest.mark.parametrize("modul", ["bot", "copy_bot", "scout_bot"])
def test_holen_importfehler_nur_klasse(monkeypatch, capsys, modul):
    import builtins
    import logging
    import warnings
    original = builtins.__import__
    monkeypatch.setattr(holen, "core", None)

    def kaputt(name, *args, **kwargs):
        if name == modul:
            print("TESTGEHEIM12345")
            logging.critical("TESTGEHEIM12345")
            warnings.warn("TESTGEHEIM12345")
            raise ImportError("TESTGEHEIM12345")
        return original(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", kaputt)
    assert holen.main() == 1
    captured = capsys.readouterr()
    assert captured.out == "Abbruch: ImportError\n" and captured.err == ""


def test_holen_excepthook_nur_klasse(capsys):
    holen._excepthook(ValueError, ValueError("TESTGEHEIM12345"), None)
    captured = capsys.readouterr()
    assert captured.out == "" and captured.err == "ValueError\n"


def test_holen_main_abbruch_keine_fehlermeldung_mit_url(monkeypatch, capsys):
    def kaputt():
        raise ValueError("https://mainnet.helius-rpc.com/?api-key=GEHEIM")
    monkeypatch.setattr(holen, "holen", kaputt)
    assert holen.main() == 1
    assert capsys.readouterr().out == "Abbruch: ValueError\n"


@pytest.mark.parametrize("phase", ["sol", "kurse"])
def test_holen_globaler_abruf_fehler_ohne_artefakt_und_antworttext(
        monkeypatch, tmp_path, capsys, phase):
    liste, ziel, _ = fake_holen(monkeypatch, tmp_path, {WALLET: []}, {})

    def kaputt(*args):
        text = "https://mainnet.helius-rpc.com/?api-key=GEHEIM"
        print(text)
        raise RuntimeError(text)

    monkeypatch.setattr(scout, "current_prices_sol", lambda *a: {})
    if phase == "sol":
        monkeypatch.setattr(core, "sol_price", kaputt)
    else:
        monkeypatch.setattr(scout, "current_prices_sol", kaputt)
    original = holen.holen
    monkeypatch.setattr(holen, "holen", lambda: original(liste, ziel, JETZT))
    assert holen.main() == 1
    assert not ziel.exists()
    captured = capsys.readouterr()
    assert captured.out.endswith("Abbruch: RuntimeError\n")
    assert captured.err == ""
    assert "GEHEIM" not in captured.out and WALLET not in captured.out
    assert "helius-rpc.com" not in captured.out


def test_stage2_alt_wortgleich_mit_historischer_quelle():
    # SHA256 der Funktion aus 8d72e20073:scout_bot.py, nur Name in stage2_alt geaendert.
    # Zeilenenden vereinheitlicht; kein Git-Aufruf und kein historischer Modulimport im Test.
    quelle = inspect.getsource(rechnen.stage2_alt).rstrip("\n")
    assert hashlib.sha256(quelle.encode("utf-8")).hexdigest() == (
        "796ae7dce8c37455a790dc6c3c1889911f9f5229936e94cf6600322a57f7bab4")


def test_holen_hilfsfunktionen_duerfen_keine_antworttexte_loggen(monkeypatch, tmp_path, capsys):
    page = [{"signature": sig("sig"), "blockTime": JETZT, "err": None}]
    liste, ziel, _ = fake_holen(monkeypatch, tmp_path, {WALLET: page}, {sig("sig"): {}})

    def noisy(result):
        def call(*args):
            print(f"https://mainnet.helius-rpc.com/?api-key=GEHEIM {WALLET}")
            return result
        return call

    monkeypatch.setattr(core, "sol_price", noisy(100))
    monkeypatch.setattr(core, "rpc", noisy(page))
    monkeypatch.setattr(cb, "fetch_tx", noisy({}))
    monkeypatch.setattr(cb, "parse_trade", noisy(None))
    monkeypatch.setattr(scout, "current_prices_sol", noisy({}))
    assert holen.holen(liste, ziel, JETZT) == 0
    captured = capsys.readouterr()
    assert captured.out == "Wallet 1/1: 1 Signaturen, 0 fehlen\n" and captured.err == ""
    assert "GEHEIM" not in ziel.read_text(encoding="utf-8")


def test_rechnen_altbestand_alt_groesser_neu_bericht_copy(monkeypatch, tmp_path, sandbox):
    wallet, kurse = wallet_daten()
    monkeypatch.setattr(scout, "load_copy_accounts", lambda: {"AndererName": fake_konto(WALLET)})
    quelle = tmp_path / "rohdaten.json"
    quelle.write_text(json.dumps(roh_daten([wallet], kurse)), encoding="utf-8")
    ziel = tmp_path / "bericht.md"
    originale = cb.fetch_tx, cb.parse_trade, scout.current_prices_sol, core.rpc
    rows = rechnen.rechnen(quelle, ziel)
    r = rows[0]
    assert r["alt"]["punkte"] > r["neu"]["punkte"]
    assert r["alt"]["gewinn_sol"] == 12 and r["neu"]["gewinn_sol"] == 0
    assert r["alt"]["coins_gehalten"] == 0 and r["neu"]["coins_gehalten"] == 3
    assert r["alt"]["aufnahme_grund"] is None and r["neu"]["aufnahme_grund"] is not None
    assert r["copy"] == {"ergebnis": 2, "geschlossen": 5, "ohne_kurs": 0}
    assert not r["fehler"]
    assert originale == (cb.fetch_tx, cb.parse_trade, scout.current_prices_sol, core.rpc)
    text = ziel.read_text(encoding="utf-8")
    assert "| Altbestand | 397,0 | -3,0 |" in text
    assert "Alt aufgenommen, neu abgelehnt: 1." in text
    assert "Copy-Summe dieser Wallets: 2,000 SOL" in text
    assert "Helius-Aufrufe laut Rohdaten (grob): 42." in text
    assert "| Mindestens 5 geschlossene Positionen | – | 1 | – | 1 |" in text
    assert not sandbox["git"] and not sandbox["discord"] and not sandbox["net"]


def test_rechnen_transfer_fehlend_und_null_gleich_fuer_beide(monkeypatch):
    w, kurse = wallet_daten()
    for i, mint in enumerate(kurse):
        w["trades"][f"t{i}"] = dict(w["trades"][f"v{i}"], kind="UEBERWEISUNG", sol=0,
                                    tokens=500, pre_raw=500 * 10**6, block_time=JETZT - 100)
    # 6 Trades + 3 Transfers + 2 fehlende + 1 Nicht-Handel: neu unsicher.
    w["trades"].update(fehlt1="fehlt", fehlt2="fehlt", kein_trade=None)
    w["signaturen"] = list(w["trades"])
    monkeypatch.setattr(scout, "load_copy_accounts", lambda: {})
    daten = roh_daten([w], kurse)
    vorher = copy.deepcopy(daten)
    r = rechnen.auswerten(daten)[0]
    assert r["alt"]["punkte"] == 397
    assert r["neu"]["punkte"] is None
    assert r["neu"]["tx_fehlend"] == 2 and r["neu"]["tx_abgerufen"] == 12
    assert r["neu"]["coins_ueberwiesen"] == 3
    assert r["neu"]["coins_gehalten"] == 0
    assert r["neu"]["aufnahme_grund"].startswith("unsicher")
    assert r["copy"] is None
    assert daten == vorher


def test_rechnen_inaktivitaet_verwendet_rohdaten_zeit(monkeypatch):
    w, kurse = wallet_daten()
    w["juengste_block_time"] = JETZT - 25 * 3600
    monkeypatch.setattr(scout, "load_copy_accounts", lambda: {})
    r = rechnen.auswerten(roh_daten([w], kurse))[0]
    assert r["alt"]["punkte"] == 397
    assert r["alt"]["aufnahme_grund"] == "letzte Aktivitaet nicht unter 24 h"


@pytest.mark.parametrize("defekt", [None, {}, {"name": "Kaputt", "adresse": "kaputt"},
                                   {"name": "Kaputt", "adresse": "kaputt", "fehler": {"anzahl": 1}}])
def test_kaputte_wallet_stoppt_nichts(monkeypatch, tmp_path, defekt):
    w, kurse = wallet_daten()
    monkeypatch.setattr(scout, "load_copy_accounts", lambda: {})
    quelle, ziel = tmp_path / "roh.json", tmp_path / "bericht.md"
    quelle.write_text(json.dumps(roh_daten([defekt, w], kurse)), encoding="utf-8")
    rows = rechnen.rechnen(quelle, ziel)
    assert len(rows) == 2 and rows[0]["fehler"]
    assert rows[1]["alt"]["punkte"] == 397
    assert "Fehler" in ziel.read_text(encoding="utf-8")


def test_ersatzfunktionen_auch_nach_fehler_zurueck(monkeypatch):
    w, kurse = wallet_daten()
    w["trades"]["k0"]["sol"] = "kaputt"
    original = cb.fetch_tx, cb.parse_trade, scout.current_prices_sol
    monkeypatch.setattr(scout, "load_copy_accounts", lambda: {})
    rows = rechnen.auswerten(roh_daten([w], kurse))
    assert rows[0]["fehler"]
    assert original == (cb.fetch_tx, cb.parse_trade, scout.current_prices_sol)


def test_netz_beim_rechnen_gesperrt(monkeypatch):
    w, kurse = wallet_daten()
    monkeypatch.setattr(scout, "load_copy_accounts", lambda: {})
    def stage(*a):
        core.rpc("getTransaction", [])
    monkeypatch.setattr(scout, "stage2", stage)
    r = rechnen.auswerten(roh_daten([w], kurse))[0]
    assert r["neu"] is None and ("neu", "RuntimeError") in r["fehler"]
    assert r["alt"]["punkte"] == 397


@pytest.mark.parametrize("x,y,erwartet", [([1, 2, 3], [2, 4, 6], 1),
                                          ([1, 2, 3], [6, 4, 2], -1),
                                          ([1, 1, 2], [1, 2, 3], math.sqrt(3) / 2),
                                          ([1, 1, 2, 2], [4, 4, 8, 8], 1)])
def test_spearman_bekannte_werte(x, y, erwartet):
    assert rechnen.spearman(x, y) == pytest.approx(erwartet)
    assert rechnen.spearman(y, x) == pytest.approx(erwartet)


def test_spearman_undefiniert_und_mittelrang():
    assert rechnen.mittelraenge([30, 10, 10, 20]) == [4, 1.5, 1.5, 3]
    assert rechnen.spearman([], []) is None
    assert rechnen.spearman([1], [2]) is None
    assert rechnen.spearman([1, 1], [1, 2]) is None
    with pytest.raises(ValueError):
        rechnen.spearman([1], [1, 2])


def test_korrelation_getrennte_stichproben_und_bericht_sortierung(monkeypatch):
    wallets, kurse, accounts = [], {}, {}
    for i in range(3):
        adresse = addr(f"Trader{i + 1}")
        w, prices = wallet_daten(f"Name{i}", adresse)
        for t in w["trades"].values():
            if t["kind"] == "VERKAUF":
                t["sol"] = 5 + i
        wallets.append(w)
        kurse.update(prices)
        accounts[f"Konto{i}"] = fake_konto(adresse, pnl=i + 1, geschlossen=5 if i else 4)
    # Fehlender Kurs wird gezeigt; Konto bleibt wie gefordert in der Korrelation.
    accounts["Konto1"]["positionen"] = {"offen": {"invested_sol": 1, "proceeds_sol": 0,
                                                    "tokens_raw": 10, "decimals": 0}}
    monkeypatch.setattr(scout, "load_copy_accounts", lambda: accounts)
    daten = roh_daten(wallets, kurse)
    rows = rechnen.auswerten(daten)
    assert rows[1]["copy"]["ohne_kurs"] == 1
    for art in ("alt", "neu"):
        rho5, n5 = rechnen.korrelation(rows, art, 5)
        rho0, n0 = rechnen.korrelation(rows, art, 0)
        assert rho5 == pytest.approx(1) and n5 == 2
        assert rho0 == pytest.approx(1) and n0 == 3
    text = rechnen.bericht(daten, rows)
    assert text.index("| Name2 |") < text.index("| Name1 |") < text.index("| Name0 |")
    assert "| Mindestens 5 geschlossene Positionen | 1,0000 | 2 | 1,0000 | 2 |" in text
    assert "| Alle mit Copy-Konto | 1,0000 | 3 | 1,0000 | 3 |" in text


def test_rechnen_cli_schreibt_bericht(monkeypatch, tmp_path):
    w, kurse = wallet_daten()
    monkeypatch.setattr(scout, "load_copy_accounts", lambda: {})
    quelle, ziel = tmp_path / "roh.json", tmp_path / "bericht.md"
    quelle.write_text(json.dumps(roh_daten([w], kurse)), encoding="utf-8")
    assert rechnen.main([str(quelle), str(ziel)]) == 0
    assert ziel.exists()
    assert rechnen.main([str(tmp_path / "fehlt.json"), str(ziel)]) == 1


def test_copy_ladefunktion_mit_fake_datei_und_kaputtem_konto(monkeypatch, tmp_path):
    w, kurse = wallet_daten()
    zweites, _ = wallet_daten("Zweite", addr("Zweiter"))
    quelle = tmp_path / "fake_konten.json"
    quelle.write_text(json.dumps({"wallets": {
        "AlterName": {"adresse": WALLET, "geschlossen": [None], "positionen": {}},
        "NeuerName": fake_konto(zweites["adresse"], pnl=-2)}}), encoding="utf-8")
    monkeypatch.setattr(cb, "ACCOUNTS_FILE", str(quelle))
    rows = rechnen.auswerten(roh_daten([w, zweites], kurse))
    assert rows[0]["copy"] is None and ("Copy", "AttributeError") in rows[0]["fehler"]
    assert rows[0]["alt"]["punkte"] == 397
    assert rows[1]["copy"] == {"ergebnis": -2, "ohne_kurs": 0, "geschlossen": 5}
    assert rows[1]["alt"]["punkte"] == 397


def test_holen_rechnen_durchgehend_mit_derselben_datei(monkeypatch, tmp_path):
    transactions = {
        sig("kauf"): buy_tx(pre=900, tokens=100, sol=1, block_time=JETZT - 7200),
        sig("verkauf"): sell_tx(pre=1000, tokens=500, sol=5, block_time=JETZT - 1000),
    }
    page = [{"signature": sig(s), "blockTime": JETZT - i, "err": None}
            for i, s in enumerate(("fehlt", "verkauf", "kauf"))]
    liste, ziel, _ = fake_holen(monkeypatch, tmp_path, {WALLET: page}, transactions)
    monkeypatch.setattr(scout, "current_prices_sol", lambda *a: {MINT: 0.01})
    monkeypatch.setattr(scout, "load_copy_accounts", lambda: {})
    assert holen.holen(liste, ziel, JETZT) == 0
    rows = rechnen.rechnen(ziel, tmp_path / "bericht.md")
    assert rows[0]["alt"]["gewinn_sol"] == 4
    assert rows[0]["neu"]["gewinn_sol"] == 0
    assert rows[0]["neu"]["tx_fehlend"] == 1 and rows[0]["neu"]["tx_abgerufen"] == 3


def test_workflow_nur_manuell_lesend_kurze_aufbewahrung_zwei_secrets():
    text = (REPO / ".github/workflows/scout_gegenprobe.yml").read_text(encoding="utf-8")
    bloecke = dict(re.findall(r"^(\w+):([^\n]*(?:\n[ \t]+[^\n]*|\n)*)", text, re.M))
    assert set(bloecke) == {"name", "on", "permissions", "concurrency", "jobs"}
    assert bloecke["on"].strip() == "workflow_dispatch:"
    assert bloecke["permissions"].strip() == "contents: read"
    assert "group: wallet-scout" in bloecke["concurrency"]
    assert "cancel-in-progress: false" in bloecke["concurrency"]
    assert "timeout-minutes: 30" in text
    assert "retention-days: 1\n" in text and "if-no-files-found: error" in text
    assert "name: scout-gegenprobe" in text and "path: gegenprobe/rohdaten.json" in text
    assert "actions/upload-artifact@cf430e030ddbb5b0abf93d22962f4752f3646cd9" in text
    runner = (REPO / ".github/workflows/scout_runner.yml").read_text(encoding="utf-8")
    for action in ("checkout", "setup-python"):
        pinned = re.search(rf"actions/{action}@[a-f0-9]{{40}}", runner).group()
        assert pinned in text
    assert "pip install -r requirements.txt" in text
    assert "python tools/scout_gegenprobe_holen.py" in text
    secrets = re.findall(r"secrets\.([A-Z_]+)", text)
    assert sorted(secrets) == ["HELIUS_API_KEY", "JUPITER_API_KEY"]
    env = re.search(r"        env:\n(.*?)        run:", text, re.S).group(1)
    assert re.findall(r"^          (\w+):", env, re.M) == ["HELIUS_API_KEY", "JUPITER_API_KEY"]
    assert not re.search(r"\bgit\s|contents: write|schedule:|push:", text)


def test_wallet_liste_genau_29_und_vier_adressen_aus_copy_liste():
    wallets = holen.load_wallets(REPO / "tools/scout_gegenprobe_wallets.txt")
    assert len(wallets) == 29 and len({a for _, a in wallets}) == 29
    assert {n: a for n, a in wallets[-4:]} == {
        "Dior": "87rRdssFiTJKY4MGARa4G5vQ31hmR7MxSmhzeaJ5AAxJ",
        "C7bF": "C7bFqgUrJ1EE4fNAmuSeqvU6VnaCEYnPg2agAWUVV2fF",
        "6ANG": "6ANGS6SSCxkv6hV3iymHHMESqDz7EFaecCwHA8qTswpr",
        "4DOV": "4DovZLQMSrHhptkcteC7x5UCGRSEmLqfAQKtjBUEJxC1"}
