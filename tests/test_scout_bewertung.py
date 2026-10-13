"""Scout-Bewertung: Fenster-Bestand, Restbestaende und fehlende Transaktionen."""
import csv
import json
import os
from datetime import datetime, timezone

import pytest

import copy_bot as cb
import scout_bot as scout
from helpers import MINT, MINT2, WALLET, addr, buy_tx, sell_tx, transfer_tx


def auswerten(monkeypatch, transactions, prices=None):
    """Echte Trade-Erkennung mit kuenstlichen Transaktionen und Kursen."""
    calls = []
    monkeypatch.setattr(cb, "fetch_tx", transactions.get)

    def kurse(mints, sol_usd):
        calls.append((set(mints), sol_usd))
        return prices or {}

    monkeypatch.setattr(scout, "current_prices_sol", kurse)
    return scout.stage2(WALLET, list(transactions), 100.0), calls


def test_cr5_1_altbestand_nur_anteiliger_erloes(monkeypatch):
    """900 alte + 100 neue Token; 500 verkauft -> 50 neue, 0.5 SOL Erloes."""
    r, calls = auswerten(monkeypatch, {
        "verkauf": sell_tx(pre=1000, tokens=500, sol=5, block_time=2000),
        "kauf": buy_tx(pre=900, tokens=100, sol=1, block_time=1000),
    }, {MINT: 0.01})
    assert r["gewinn_sol"] == 0.0
    assert r["rendite_pct"] == 0.0
    assert r["coins_gehalten"] == 1
    assert calls == [({MINT}, 100.0)]


def test_cr5_1_verkauf_vor_erster_kauf_zaehlt_nicht(monkeypatch):
    r, calls = auswerten(monkeypatch, {
        "verkauf_neu": sell_tx(pre=10, tokens=10, sol=0.5, block_time=3000),
        "kauf": buy_tx(tokens=10, sol=1, block_time=2000),
        "verkauf_alt": sell_tx(pre=100, tokens=100, sol=10, block_time=1000),
    })
    assert r["gewinn_sol"] == -0.5
    assert r["rendite_pct"] == -50.0
    assert r["coins_gehalten"] == 0
    assert r["trades"] == 3 and r["verkaeufe"] == 2
    assert calls == []


def test_cr5_1_mehrere_abgaenge_und_nachkauf(monkeypatch):
    """50 neue Token verkauft, 10 ueberwiesen, 60 nachgekauft, dann alles verkauft."""
    r, calls = auswerten(monkeypatch, {
        "k1": buy_tx(pre=900, tokens=100, sol=1, block_time=1000),
        "v1": sell_tx(pre=1000, tokens=500, sol=5, block_time=2000),
        "t": transfer_tx(pre=500, tokens=100, block_time=3000),
        "k2": buy_tx(pre=400, tokens=60, sol=0.6, block_time=4000),
        "v2": sell_tx(pre=460, tokens=460, sol=4.6, block_time=5000),
    })
    assert r["gewinn_sol"] == -0.1
    assert r["coins_gehalten"] == 0
    assert r["coins_ueberwiesen"] == 1
    assert r["trades"] == 4 and r["kaeufe"] == 2 and r["verkaeufe"] == 2
    assert calls == []


def test_cr5_2_komplette_ueberweisung_verliert_einsatz(monkeypatch):
    r, calls = auswerten(monkeypatch, {
        "k": buy_tx(tokens=100, sol=1, block_time=1000),
        "t": transfer_tx(pre=100, tokens=100, block_time=2000),
    }, {MINT: 0.02})
    assert r["gewinn_sol"] == -1.0
    assert r["rendite_pct"] == -100.0
    assert r["coins_gehalten"] == 0
    assert r["coins_ueberwiesen"] == 1
    assert r["trades"] == r["kaeufe"] == 1
    assert r["verkaeufe"] == 0
    assert calls == []


def test_cr5_2_altbestand_und_mehrere_ueberweisungen_ein_coin(monkeypatch):
    r, calls = auswerten(monkeypatch, {
        "alt": transfer_tx(pre=900, tokens=100, block_time=500),
        "k": buy_tx(pre=800, tokens=100, sol=1, block_time=1000),
        "t1": transfer_tx(pre=900, tokens=450, block_time=2000),
        "t2": transfer_tx(pre=450, tokens=225, block_time=3000),
        "fremd": transfer_tx(mint=MINT2, pre=100, tokens=100, block_time=4000),
    }, {MINT: 0.02})
    assert r["gewinn_sol"] == -0.5  # 25 neue Token bleiben, Wert 0.5 SOL
    assert r["coins"] == r["coins_gehalten"] == r["coins_ueberwiesen"] == 1
    assert calls == [({MINT}, 100.0)]


def test_cr5_2_ueberweisung_aendert_keine_trade_kennzahlen(monkeypatch):
    transactions = {
        "k": buy_tx(tokens=100, sol=1, block_time=1000),
        "v": sell_tx(pre=100, tokens=1, sol=0.02, block_time=1060),
    }
    vorher, _ = auswerten(monkeypatch, transactions)
    transactions["t"] = transfer_tx(pre=99, tokens=99, botfee=10_000_000, block_time=100000)
    nachher, _ = auswerten(monkeypatch, transactions)
    for key in ("trades", "kaeufe", "verkaeufe", "trades_pro_tag",
                "mini_verkaeufe_anteil", "bot_gebuehr_anteil"):
        assert nachher[key] == vorher[key], key
    assert nachher["mini_verkaeufe_anteil"] == 1.0
    assert nachher["bot_gebuehr_anteil"] == 0.0


@pytest.mark.parametrize("verkauft, gehalten", [(90, 1), (95, 0)])
def test_cr5_3_jeder_restbestand_hat_einen_wert(monkeypatch, verkauft, gehalten):
    r, calls = auswerten(monkeypatch, {
        "k": buy_tx(tokens=100, sol=1, block_time=1000),
        "v": sell_tx(pre=100, tokens=verkauft, sol=verkauft * 0.02, block_time=2000),
    }, {MINT: 0.02})
    assert r["gewinn_sol"] == 1.0
    assert r["coins_gehalten"] == gehalten
    assert calls == [({MINT}, 100.0)]


def test_cr5_3_rest_ohne_kurs_weiter_null(monkeypatch):
    r, calls = auswerten(monkeypatch, {
        "k": buy_tx(tokens=100, sol=1, block_time=1000),
        "v": sell_tx(pre=100, tokens=95, sol=1.9, block_time=2000),
    })
    assert r["gewinn_sol"] == 0.9
    assert calls == [({MINT}, 100.0)]


def test_cr5_3_kurse_fuer_gehaltenen_coin_und_kleinen_rest_gemeinsam(monkeypatch):
    r, calls = auswerten(monkeypatch, {
        "k1": buy_tx(tokens=100, sol=1, block_time=1000),
        "v1": sell_tx(pre=100, tokens=95, sol=1.9, block_time=2000),
        "k2": buy_tx(mint=MINT2, tokens=100, sol=1, block_time=3000),
    }, {MINT: 0.02, MINT2: 0.02})
    assert r["gewinn_sol"] == 2.0
    assert r["coins_gehalten"] == 1
    assert calls == [({MINT, MINT2}, 100.0)]


def test_normalfall_gleiche_zahlen_wie_bisher(monkeypatch):
    mint_c = addr("MintC")
    r, _ = auswerten(monkeypatch, {
        "a1": buy_tx(tokens=100, sol=1, block_time=1000),
        "a2": sell_tx(pre=100, tokens=100, sol=2, block_time=2800),
        "b1": buy_tx(mint=MINT2, tokens=100, sol=1, block_time=4600),
        "b2": sell_tx(mint=MINT2, pre=100, tokens=100, sol=0.5, block_time=5800),
        "c1": buy_tx(mint=mint_c, tokens=100, sol=1, block_time=8200),
    }, {mint_c: 0.015})
    assert r == {
        "tx_abgerufen": 5, "tx_fehlend": 0,
        "trades": 5, "kaeufe": 3, "verkaeufe": 2, "trades_pro_tag": 60.0,
        "kauf_median_sol": 1.0, "anteil_kaeufe_ab_0_1": 1.0,
        "coins": 3, "coins_abgeschlossen": 2, "coins_gehalten": 1, "coins_ueberwiesen": 0,
        "trefferquote": 0.67, "gewinn_sol": 1.0, "rendite_pct": 33.3,
        "rendite_ohne_besten_pct": 0.0, "haltedauer_median_min": 25.0,
        "schnelle_verkaeufe_anteil": 0.0, "reibung_pp": 6.0,
        "mini_verkaeufe_anteil": 0.0, "bot_gebuehr_anteil": 0.0,
    }
    assert scout.score(r) == -6.0


@pytest.mark.parametrize("preis", [None, 0.05])
@pytest.mark.parametrize("abgang, gewinn, ueberwiesen", [
    (sell_tx, 1.0, 0), (transfer_tx, -1.0, 1),
])
def test_gleiche_zeit_behaelt_ausfuehrungsreihenfolge(monkeypatch, preis, abgang, gewinn, ueberwiesen):
    """Neueste Signatur zuerst: Abgang nach Kauf im selben Block."""
    k = buy_tx(tokens=100, sol=1, block_time=1000)
    v = abgang(pre=100, tokens=100, block_time=1000, **({"sol": 2} if abgang == sell_tx else {}))
    r, calls = auswerten(monkeypatch, {"v": v, "k": k}, {MINT: preis} if preis is not None else None)
    assert r["gewinn_sol"] == gewinn
    assert r["coins_gehalten"] == 0
    assert r["coins_ueberwiesen"] == ueberwiesen
    assert calls == []


@pytest.mark.parametrize("kind", ["VERKAUF", "UEBERWEISUNG"])
@pytest.mark.parametrize("pre_raw", [None, 0, 10 * 10**6])
def test_abgang_ohne_vorbestand_oder_zu_gross_begrenzt(monkeypatch, kind, pre_raw):
    k = cb.parse_trade(buy_tx(tokens=100, sol=1, block_time=1000), WALLET, 100.0)
    v = cb.parse_trade(sell_tx(pre=200, tokens=200, sol=4, block_time=2000), WALLET, 100.0)
    v["kind"] = kind
    if pre_raw is None:
        v.pop("pre_raw")
    else:
        v["pre_raw"] = pre_raw
    monkeypatch.setattr(cb, "parse_trade", lambda tx, *args: tx)
    r, calls = auswerten(monkeypatch, {"k": k, "v": v})
    assert r["gewinn_sol"] == (1.0 if kind == "VERKAUF" else -1.0)
    assert r["coins_gehalten"] == 0
    assert r["coins_ueberwiesen"] == (kind == "UEBERWEISUNG")
    assert calls == []


def test_kaputte_transaktion_stoppt_nichts(monkeypatch):
    r, _ = auswerten(monkeypatch, {
        "kaputt": {"meta": {}},
        "k": buy_tx(tokens=100, sol=1, block_time=1000),
        "v": sell_tx(pre=100, tokens=100, sol=2, block_time=2000),
    })
    assert r["gewinn_sol"] == 1.0
    assert r["trades"] == 2
    assert r["tx_abgerufen"] == 3
    assert r["tx_fehlend"] == 1
    assert scout.STATS["fehler"] == 1


@pytest.mark.parametrize("key, value", [
    ("tokens", 0), ("tokens", None), ("tokens", "kaputt"),
    ("tokens", float("inf")), ("sol", float("nan")),
    ("block_time", "kaputt"), ("mint", None),
])
def test_kaputte_trade_werte_stoppen_nichts(monkeypatch, key, value):
    k = cb.parse_trade(buy_tx(tokens=100, sol=1, block_time=1000), WALLET, 100.0)
    v = cb.parse_trade(sell_tx(pre=100, tokens=100, sol=2, block_time=2000), WALLET, 100.0)
    kaputt = dict(v, **{key: value})
    monkeypatch.setattr(cb, "parse_trade", lambda tx, *args: tx)
    r, _ = auswerten(monkeypatch, {"kaputt": kaputt, "k": k, "v": v})
    assert r["gewinn_sol"] == 1.0
    assert r["trades"] == 2
    assert r["tx_abgerufen"] == 3
    assert r["tx_fehlend"] == 1
    assert scout.STATS["fehler"] == 1


def test_fehlende_zeit_und_optionale_werte_stoppen_nichts(monkeypatch):
    k = cb.parse_trade(buy_tx(tokens=100, sol=1, block_time=1000), WALLET, 100.0)
    v = cb.parse_trade(sell_tx(pre=100, tokens=100, sol=2, block_time=2000), WALLET, 100.0)
    k["block_time"] = None
    for key in ("block_time", "pre_raw", "other", "delta_raw"):
        v.pop(key)
    monkeypatch.setattr(cb, "parse_trade", lambda tx, *args: tx)
    r, _ = auswerten(monkeypatch, {"v": v, "k": k})
    assert r["gewinn_sol"] == 1.0
    assert r["trades_pro_tag"] is None
    assert r["mini_verkaeufe_anteil"] == 0.0


@pytest.mark.parametrize("anzahl", [None, 0, 2])
def test_discord_zeigt_ueberweisungen_nur_wenn_vorhanden(monkeypatch, anzahl):
    r, _ = auswerten(monkeypatch, {})
    if anzahl is None:
        r.pop("coins_ueberwiesen")
    else:
        r["coins_ueberwiesen"] = anzahl
    _, line = scout._rating_line("Test", WALLET, r, None)
    assert ("2 Coins ueberwiesen" in line) == (anzahl == 2)
    assert ("Coins ueberwiesen" in line) == (anzahl == 2)
    assert "coins_ueberwiesen" not in scout.CANDIDATES_HEADER
    assert "coins_ueberwiesen" not in scout.TX_RESULT_HEADER


def test_scoring_version_4():
    assert scout.SCORING_VERSION == "4"


def transaktionen_mit_luecken(fehlend, wallet=WALLET):
    """20 Signaturen, drei profitable Coins und abrufbare Transaktionen ohne Trade."""
    transactions = {}
    for i, mint in enumerate((MINT, MINT2, addr("MintC"))):
        zeit = 1000 + i * 86400
        transactions[f"k{i}"] = buy_tx(wallet=wallet, mint=mint, tokens=100, sol=1, block_time=zeit)
        transactions[f"v{i}"] = sell_tx(wallet=wallet, mint=mint, pre=100, tokens=100, sol=2, block_time=zeit + 1200)
    for i in range(14):
        transactions[f"rest{i}"] = None if i < fehlend else {}
    return transactions


@pytest.mark.parametrize("antwort, fehlend", [
    ({"meta": {}}, 14), ({"meta": {"err": "x"}}, 0), ({}, 0),
    ({"meta": {"err": None}, "transaction": {"message": {"accountKeys": []}}}, 0),
])
def test_nicht_auswertbare_transaktionen_zaehlen_als_fehlend(monkeypatch, antwort, fehlend):
    transactions = transaktionen_mit_luecken(0)
    for i in range(14):
        transactions[f"rest{i}"] = antwort
    r, _ = auswerten(monkeypatch, transactions)
    assert r["trades"] == 6
    assert r["tx_abgerufen"] == 20
    assert r["tx_fehlend"] == fehlend
    assert scout.STATS["fehler"] == fehlend
    if fehlend:
        assert scout.not_rated_reason(r).startswith("unsicher")
        assert scout.score(r) is None
    else:
        assert scout.not_rated_reason(r) is None
        assert scout.score(r) > 0


@pytest.mark.parametrize("fehlend, unsicher", [(2, False), (3, True), (20, True)])
def test_cr5_4_grenze_fehlender_transaktionen(monkeypatch, fehlend, unsicher):
    transactions = transaktionen_mit_luecken(fehlend)
    if fehlend == 20:
        transactions = dict.fromkeys(transactions)
    r, _ = auswerten(monkeypatch, transactions)
    assert r["tx_abgerufen"] == 20
    assert r["tx_fehlend"] == fehlend
    reason = scout.not_rated_reason(r)
    pts = scout.score(r)
    row = dict(r, inaktiv_h=1, ergebnis=reason or "bewertet", punkte=pts if pts is not None else "")
    if unsicher:
        assert reason == f"unsicher ({fehlend / 20:.0%} der Transaktionen nicht abrufbar)"
        assert pts is None
        assert scout.auto_reason(row) == reason
    else:
        assert reason is None
        assert pts > 0
        assert scout.auto_reason(row) is None


def test_cr5_4_unsicher_hat_vorrang_vor_kleinstkaeufen():
    r = {"tx_abgerufen": 20, "tx_fehlend": 3, "kauf_median_sol": 0.001, "coins": 1}
    assert scout.not_rated_reason(r).startswith("unsicher")


def test_cr5_4_alte_gespeicherte_bewertung_ohne_zaehler(monkeypatch):
    r, _ = auswerten(monkeypatch, transaktionen_mit_luecken(0))
    r.pop("tx_abgerufen")
    r.pop("tx_fehlend")
    assert scout.not_rated_reason(r) is None
    pts = scout.score(r)
    assert pts > 0
    assert scout.auto_reason(dict(r, inaktiv_h=1, ergebnis="bewertet", punkte=pts)) is None
    r.update(tx_abgerufen=0, tx_fehlend=3)
    assert scout.not_rated_reason(r) is None


def pruefliste_vorbereiten(monkeypatch, transactions):
    """Pruefliste im Speicher, echte Stufe 2 und keine Datei- oder Netzabfragen."""
    calls = []
    monkeypatch.setattr(scout, "load_list", lambda: [("Probe", WALLET)])
    monkeypatch.setattr(scout, "stage1", lambda *args: (calls.append(WALLET) or {"_page": [], "inaktiv_h": 1}, None))
    monkeypatch.setattr(scout, "window_sigs", lambda *args: list(transactions))
    monkeypatch.setattr(cb, "fetch_tx", transactions.get)
    monkeypatch.setattr(scout, "current_prices_sol", lambda *args: {})
    return calls


@pytest.mark.parametrize("alter_eintrag", [False, True])
def test_cr5_4_pruefliste_hoechstens_drei_unsichere_versuche(monkeypatch, alter_eintrag):
    calls = pruefliste_vorbereiten(monkeypatch, transaktionen_mit_luecken(3))
    state = {"wallets_geprueft": {}, "liste_bewertet": {}}
    if alter_eintrag:
        state["liste_bewertet"][WALLET] = {"version": "3", "zeit": 1}
    for versuch in range(1, 4):
        rows, lines = scout.check_list(state, 200000 + versuch, 100.0)
        assert len(rows) == 1
        assert len(calls) == versuch
        assert rows[0]["ergebnis"].startswith("unsicher")
        assert rows[0]["punkte"] == ""
        assert scout.auto_reason(rows[0]).startswith("unsicher")
        assert "3 von 20 Transaktionen fehlen" in lines[0]
        memo = state["liste_bewertet"][WALLET]
        assert memo["unsicher_versuche"] == versuch
        assert (memo.get("version") == scout.SCORING_VERSION) == (versuch == 3)
        state = json.loads(json.dumps(state))         # wie nach Speichern und neuem Scout-Lauf
    assert scout.check_list(state, 200004, 100.0) == ([], [])
    assert len(calls) == 3


def test_version_3_pruefliste_wird_neu_bewertet_und_bleibt_lesbar(monkeypatch):
    zweite_wallet = addr("ListeAlt")
    transactions = transaktionen_mit_luecken(0)
    transactions.update({f"zweite_{k}": v for k, v in transaktionen_mit_luecken(0, zweite_wallet).items()})
    calls = pruefliste_vorbereiten(monkeypatch, transactions)
    alter_eintrag = {"version": "3", "zeit": 1}
    state = {"wallets_geprueft": {}, "liste_bewertet": {
        WALLET: dict(alter_eintrag), zweite_wallet: dict(alter_eintrag),
    }}
    monkeypatch.setattr(scout, "load_list", lambda: [("Probe", WALLET), ("Alt", zweite_wallet)])
    rows, lines = scout.check_list(state, 200001, 100.0)
    assert len(rows) == len(lines) == len(calls) == 2
    assert all(row["ergebnis"] == "bewertet" for row in rows)
    assert all(memo["version"] == "4" for memo in state["liste_bewertet"].values())
    assert scout.check_list(state, 200002, 100.0) == ([], [])
    assert len(calls) == 2

    # Alter Eintrag ohne optionale Felder bleibt bei einer neuen Adresse anzeigbar.
    state["liste_bewertet"].pop(zweite_wallet)
    state["liste_bewertet"][WALLET] = {"version": "4", "zeit": 1}
    rows, lines = scout.check_list(state, 200003, 100.0)
    assert [row["wallet"] for row in rows] == [zweite_wallet]
    assert any("aus dem Speicher" in line and "Probe" in line for line in lines)
    assert len(calls) == 3


@pytest.fixture
def alter_speicher(clock):
    clock.now = datetime(2026, 10, 5, 12, tzinfo=timezone.utc).timestamp()
    rows = [
        {"zeit": "2026-10-03 10:00:00", "wallet": WALLET, "ergebnis": "bewertet", "punkte": 20},
        {"zeit": "2026-10-04 10:00:00", "wallet": addr("Zweite"), "ergebnis": "bewertet", "punkte": 25},
    ]
    scout.write_csv(rows)
    scout.save_waitlist({WALLET: scout._wait_entry(rows[0], clock.now - 60)})
    return scout.load_state(), rows, clock.now


def test_versionswechsel_sperrt_alte_bewertungen_und_warteliste(alter_speicher):
    state, rows, now = alter_speicher
    assert "speicher_version" not in state
    assert scout.versionswechsel(state, now) == (2, 1)
    assert scout.stored_rows(state) == []
    assert state["speicher_geprueft"] == {r["wallet"]: r["zeit"] for r in rows}
    assert scout.load_waitlist()[WALLET]["bewertet"] == "0"
    assert state["speicher_version"] == "4"


def test_versionswechsel_zweiter_aufruf_aendert_nichts(alter_speicher, monkeypatch):
    state, _, now = alter_speicher
    scout.versionswechsel(state, now)
    vorher = json.loads(json.dumps(state))
    with open(scout.WAIT_FILE, "rb") as f:
        warteliste = f.read()
    for name in ("_latest_stored_rows", "load_waitlist", "save_waitlist"):
        monkeypatch.setattr(scout, name, lambda *a: pytest.fail("Kein erneuter Versionswechsel"))
    assert scout.versionswechsel(state, now + 1) == (0, 0)
    assert state == vorher
    with open(scout.WAIT_FILE, "rb") as f:
        assert f.read() == warteliste


def test_neue_zeile_nach_versionswechsel_bleibt_ungesehen(alter_speicher):
    state, rows, now = alter_speicher
    scout.versionswechsel(state, now)
    neue_zeile = dict(rows[0], zeit="2026-10-05 12:00:00")
    scout.write_csv([neue_zeile])
    assert scout.versionswechsel(state, now + 1) == (0, 0)
    assert [(r["wallet"], r["zeit"]) for r in scout.stored_rows(state)] == [(WALLET, neue_zeile["zeit"])]


def test_versionswechsel_liest_alte_formate_und_markiert_juengste_zeile():
    os.makedirs(scout.SCOUT_DIR)
    header = ["zeit", "wallet", "ergebnis"]
    with open(scout.CANDIDATES_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerows([
            header,
            ["2026-10-04 10:00:00", WALLET, "bewertet"],
            ["2026-10-03 10:00:00", WALLET, "bewertet"],
            ["2026-10-02 10:00:00", addr("Alt"), "liste", "Probe", "bewertet", "", "20"]
            + [""] * (scout.OLD_ROW_LEN - 7),
            ["falsche Laenge"],
        ])
    state = {}
    assert scout.versionswechsel(state, datetime(2026, 10, 5, 12, tzinfo=timezone.utc).timestamp()) == (2, 0)
    assert state["speicher_geprueft"][WALLET] == "2026-10-04 10:00:00"
    assert scout.stored_rows(state) == []
    assert not os.path.exists(scout.WAIT_FILE)


@pytest.mark.parametrize("defekt", ["kandidaten_utf8", "warteliste", "speichern"])
def test_versionswechsel_fehler_stoppt_nichts_und_wird_wiederholt(alter_speicher, monkeypatch, defekt):
    state, _, now = alter_speicher
    datei = scout.WAIT_FILE if defekt == "warteliste" else scout.CANDIDATES_FILE
    with open(datei, "rb") as f:
        vorher = f.read()
    save = scout.save_waitlist
    if defekt == "speichern":
        def kaputt(wait):
            raise OSError("Speichern fehlgeschlagen")
        monkeypatch.setattr(scout, "save_waitlist", kaputt)
    else:
        with open(datei, "wb") as f:
            f.write(b"\xff\xfe")
    fehler = scout.STATS["fehler"]
    assert scout.versionswechsel(state, now) == (0, 0)
    assert scout.STATS["fehler"] == fehler + 1
    assert "speicher_version" not in state
    assert "speicher_geprueft" not in state
    if defekt == "speichern":
        monkeypatch.setattr(scout, "save_waitlist", save)
    else:
        with open(datei, "wb") as f:
            f.write(vorher)
    assert scout.versionswechsel(state, now + 1) == (2, 1)
    assert state["speicher_version"] == "4"


def test_versionswechsel_behaelt_csv_toleranz(alter_speicher):
    state, _, now = alter_speicher
    with open(scout.CANDIDATES_FILE, "ab") as f:
        f.write(b'"offenes Feld')
    assert scout.versionswechsel(state, now) == (2, 1)
    assert state["speicher_version"] == scout.SCORING_VERSION
    assert scout.STATS["fehler"] == 0


def test_spaeterer_versionswechsel_sperrt_auch_version_4(alter_speicher, monkeypatch):
    state, rows, now = alter_speicher
    scout.versionswechsel(state, now)
    scout.write_csv([dict(rows[0], zeit="2026-10-05 12:00:00")])
    monkeypatch.setattr(scout, "SCORING_VERSION", "5")
    assert scout.versionswechsel(state, now + 1) == (2, 1)
    assert state["speicher_version"] == "5"
    assert scout.stored_rows(state) == []


@pytest.mark.parametrize("nur_liste", [False, True])
def test_run_versionswechsel_auch_ohne_automatik(alter_speicher, monkeypatch, sandbox, nur_liste):
    _, rows, now = alter_speicher
    monkeypatch.setattr(scout, "AUTO_AUFNAHME", False)
    orig = scout.versionswechsel
    calls = []

    def wechsel(state, zeit):
        calls.append(zeit)
        return orig(state, zeit)

    def pruefliste(state, zeit, sol_usd):
        assert calls == [now]
        assert state["speicher_version"] == "4"
        assert scout.stored_rows(state) == []
        assert scout.load_waitlist()[WALLET]["bewertet"] == "0"
        return [dict(rows[0], zeit="2026-10-05 12:00:00")], []

    def suche(state, zeit, sol_usd):
        assert calls[-1] == zeit == now
        return [], [], []

    monkeypatch.setattr(scout, "versionswechsel", wechsel)
    monkeypatch.setattr(scout, "check_list", pruefliste)
    monkeypatch.setattr(scout, "search", suche)
    monkeypatch.setattr(scout, "check_transactions", lambda *a: [])
    monkeypatch.setattr(scout.core, "sol_price", lambda: 100.0)
    scout.run(nur_liste=nur_liste)
    state = scout.load_state()
    assert state["speicher_version"] == "4"
    assert [r["wallet"] for r in scout.stored_rows(state)] == [WALLET]
    meldung = "Bewertung Version 4: 2 alte Bewertungen gesperrt, 1 Warteliste neu zu pruefen"
    assert sum(meldung in text for _, text in sandbox["discord"]) == 1
    sandbox["discord"].clear()
    monkeypatch.setattr(scout, "check_list", lambda *a: ([], []))
    scout.run(nur_liste=nur_liste)
    assert calls == [now, now]
    assert all("alte Bewertungen gesperrt" not in text for _, text in sandbox["discord"])


@pytest.mark.parametrize("defekt", ["kandidaten_utf8", "speichern"])
@pytest.mark.parametrize("nur_liste", [False, True])
@pytest.mark.parametrize("voller_platz", [False, True])
def test_run_automatik_pausiert_bis_versionswechsel_erfolgreich(
        alter_speicher, monkeypatch, sandbox, defekt, nur_liste, voller_platz):
    state, _, now = alter_speicher
    state["speicher_version"] = "3"
    scout.save_state(state)
    row = {"zeit": "2026-10-05 12:00:00", "wallet": WALLET, "quelle": "liste", "coin": "Probe",
           "ergebnis": "bewertet", "punkte": 20, "inaktiv_h": 2, "coins": 8,
           "rendite_ohne_besten_pct": 25, "trades_pro_tag": 30, "kauf_median_sol": 0.5}
    assert scout.auto_reason(row) is None
    scout.save_waitlist({WALLET: scout._wait_entry(row, now - 3600)})
    still = addr("StiAAe")
    wallets_vorher = f"# Testliste\nStill: {still}\n".encode("utf-8")
    with open(cb.WALLET_FILE, "wb") as f:
        f.write(wallets_vorher)
    with open(scout.WAIT_FILE, "rb") as f:
        warteliste_vorher = f.read()
    with open(scout.CANDIDATES_FILE, "rb") as f:
        kandidaten_vorher = f.read()
    accounts = {"Still": {"adresse": still, "letzter_trade": now - 80 * 3600,
                          "geschlossen": [], "positionen": {}}}
    monkeypatch.setattr(scout, "AUTO_AUFNAHME", True)
    monkeypatch.setattr(scout, "AUTO_MAX_WALLETS", 1 if voller_platz else 30)
    monkeypatch.setattr(scout.core, "git_sync_start", lambda: None)
    monkeypatch.setattr(scout, "git_push", lambda: None)
    monkeypatch.setattr(scout.core, "sol_price", lambda: 100.0)
    monkeypatch.setattr(scout, "check_list", lambda *a: ([], []))
    monkeypatch.setattr(scout, "search", lambda *a: ([], [], []))
    monkeypatch.setattr(scout, "check_transactions", lambda *a: [])
    monkeypatch.setattr(scout, "load_copy_accounts", lambda: accounts)
    monkeypatch.setattr(scout, "copy_accounts_age_h", lambda zeit: 1 / 60)
    monkeypatch.setattr(scout, "stage1", lambda *a, **kw: ({}, None))
    neupruefungen, plaene = [], []

    def recheck(e, zeit, sol_usd):
        assert scout.load_state()["speicher_version"] == "3"  # Neuer Zustand wird erst nach der Automatik gespeichert.
        assert e["wallet"] == WALLET and float(e["bewertet"]) == 0
        assert zeit == now and sol_usd == 100.0
        neupruefungen.append(e["wallet"])
        return dict(row)

    def aufnehmen(plans, zeit, acc):
        assert neupruefungen == [WALLET]
        plaene.extend(plans)
        return scout.apply_wallet_changes(plans, "05.10.", acc)

    monkeypatch.setattr(scout, "recheck", recheck)
    monkeypatch.setattr(scout, "push_wallet_changes", aufnehmen)
    save = scout.save_waitlist
    write_csv = scout.write_csv
    if defekt == "speichern":
        def kaputt(wait):
            raise OSError("Speichern fehlgeschlagen")
        monkeypatch.setattr(scout, "save_waitlist", kaputt)
    else:
        with open(scout.CANDIDATES_FILE, "wb") as f:
            f.write(b"\xff\xfe")
        # Der separate CSV-Schreibpfad liegt ausserhalb dieser Karte; hier nur den Lesefehler pruefen.
        monkeypatch.setattr(scout, "write_csv", lambda rows: None)

    fehler = scout.STATS["fehler"]
    scout.run(nur_liste=nur_liste)
    assert scout.load_state()["speicher_version"] == "3"
    assert scout.STATS["fehler"] == fehler + 1
    assert neupruefungen == plaene == []
    with open(cb.WALLET_FILE, "rb") as f:
        assert f.read() == wallets_vorher
    with open(scout.WAIT_FILE, "rb") as f:
        assert f.read() == warteliste_vorher
    meldung = f"Automatik pausiert: Umstellung auf Bewertung Version {scout.SCORING_VERSION} noch nicht abgeschlossen"
    assert sum(meldung in text for _, text in sandbox["discord"]) == 1
    assert sandbox["git"] == []

    # Derselbe Lauf mit repariertem Speicher muss wieder aufnehmen, aber erst nach Neupruefung.
    monkeypatch.setattr(scout, "save_waitlist", save)
    monkeypatch.setattr(scout, "write_csv", write_csv)
    with open(scout.CANDIDATES_FILE, "wb") as f:
        f.write(kandidaten_vorher)
    sandbox["discord"].clear()
    scout.run(nur_liste=nur_liste)
    state = scout.load_state()
    assert state["speicher_version"] == scout.SCORING_VERSION
    assert neupruefungen == [WALLET]
    assert cb.load_wallets() == [("Probe", WALLET)]
    assert scout.load_waitlist() == {}
    assert any(p["adresse"] == WALLET for p in plaene)
    assert any((p.get("raus") or {}).get("adresse") == still for p in plaene)
    assert len(plaene) == (1 if voller_platz else 2)
    assert len(state["auto_aenderungen"]) == len(plaene)
    assert scout.STATS["fehler"] == fehler + 1
    assert all("Automatik pausiert" not in text for _, text in sandbox["discord"])
    assert sandbox["git"] == []


@pytest.mark.parametrize("version", [None, "3", "5"])
def test_auto_wallets_ohne_abgeschlossenen_versionswechsel_ruht(monkeypatch, version):
    monkeypatch.setattr(scout, "AUTO_AUFNAHME", True)
    for name in ("load_waitlist", "stored_rows", "load_copy_accounts", "replaceable_wallets", "push_wallet_changes",
                 "save_waitlist"):
        monkeypatch.setattr(scout, name, lambda *a, **kw: pytest.fail("Automatik muss vollstaendig ruhen"))
    state = {} if version is None else {"speicher_version": version}
    vorher = dict(state)
    fehler = scout.STATS["fehler"]
    rows = [{"wallet": WALLET}]
    assert scout.auto_wallets(state, 200000, 100.0, rows) == [
        f"Automatik pausiert: Umstellung auf Bewertung Version {scout.SCORING_VERSION} noch nicht abgeschlossen"]
    assert state == vorher
    assert rows == [{"wallet": WALLET}]
    assert scout.STATS["fehler"] == fehler


@pytest.mark.parametrize("alter_h, neue_punkte, recheck_limit, neupruefung, aufnahme", [
    (None, 20, 5, True, True),
    (None, -1, 5, True, False),
    (None, 20, 0, False, False),
    (None, "fehler", 5, True, False),
    (6, 20, 5, False, True),
    (6 + 1 / 3600, 20, 5, True, True),
    (1, 20, 5, False, True),
])
def test_warteliste_vor_aufnahme_neu_pruefen(
        monkeypatch, alter_h, neue_punkte, recheck_limit, neupruefung, aufnahme):
    now = 200000
    bewertet = 0 if alter_h is None else now - alter_h * 3600
    row = {"wallet": WALLET, "quelle": "liste", "coin": "Probe", "ergebnis": "bewertet",
           "punkte": 20, "inaktiv_h": 2, "coins": 8, "rendite_ohne_besten_pct": 25,
           "trades_pro_tag": 30, "kauf_median_sol": 0.5}
    assert scout.auto_reason(row) is None
    wait = {WALLET: dict(scout._wait_entry(row, now), bewertet=bewertet)}
    calls, aufgenommen, gespeichert = [], [], []
    monkeypatch.setattr(scout, "AUTO_AUFNAHME", True)
    monkeypatch.setattr(scout, "RECHECK_MAX_PRO_LAUF", recheck_limit)
    monkeypatch.setattr(scout, "load_waitlist", lambda: wait)
    monkeypatch.setattr(scout, "save_waitlist", lambda entries: gespeichert.append(dict(entries)))
    monkeypatch.setattr(scout, "stored_rows", lambda state: [])

    def recheck(e, zeit, sol_usd):
        assert aufgenommen == []                     # Erst neu pruefen, dann aufnehmen.
        assert e["wallet"] == WALLET and e["bewertet"] == bewertet
        calls.append((zeit, sol_usd))
        if neue_punkte == "fehler":
            raise OSError("Neupruefung fehlgeschlagen")
        return dict(row, punkte=neue_punkte)

    def push_wallet_changes(plans, zeit, accounts):
        assert bool(calls) == neupruefung
        aufgenommen.extend(p["adresse"] for p in plans)
        return plans

    monkeypatch.setattr(scout, "recheck", recheck)
    monkeypatch.setattr(scout, "push_wallet_changes", push_wallet_changes)
    assert not os.path.exists(cb.WALLET_FILE)         # Freier Platz im leeren Testordner.
    rows = []
    state = {"speicher_version": scout.SCORING_VERSION}
    scout.auto_wallets(state, now, 100.0, rows)
    assert calls == ([(now, 100.0)] if neupruefung else [])
    assert len(rows) == int(neupruefung and neue_punkte != "fehler")
    assert aufgenommen == ([WALLET] if aufnahme else [])
    assert len(state["auto_aenderungen"]) == int(aufnahme)
    assert len(gespeichert) == 1
    if recheck_limit == 0 or neue_punkte == "fehler":
        assert gespeichert[0][WALLET]["bewertet"] == bewertet
    else:
        assert gespeichert[0] == {}


def test_cr5_4_pruefliste_erholt_sich_beim_zweiten_versuch(monkeypatch):
    transactions = transaktionen_mit_luecken(3)
    calls = pruefliste_vorbereiten(monkeypatch, transactions)
    state = {"wallets_geprueft": {}}
    scout.check_list(state, 200001, 100.0)
    transactions.update(transaktionen_mit_luecken(2))
    rows, _ = scout.check_list(state, 200002, 100.0)
    assert rows[0]["ergebnis"] == "bewertet"
    assert state["liste_bewertet"][WALLET]["version"] == scout.SCORING_VERSION
    assert scout.check_list(state, 200003, 100.0) == ([], [])
    assert len(calls) == 2


def test_cr5_4_alter_memo_eintrag_ohne_zaehler_bleibt_bewertet(monkeypatch):
    calls = pruefliste_vorbereiten(monkeypatch, transaktionen_mit_luecken(3))
    state = {"wallets_geprueft": {}, "liste_bewertet": {WALLET: {"version": scout.SCORING_VERSION}}}
    assert scout.check_list(state, 200001, 100.0) == ([], [])
    assert calls == []


@pytest.mark.parametrize("zaehler", [None, "kaputt", float("inf"), -1])
def test_cr5_4_kaputter_versuchszaehler_stoppt_nichts(monkeypatch, zaehler):
    calls = pruefliste_vorbereiten(monkeypatch, transaktionen_mit_luecken(3))
    state = {"wallets_geprueft": {}, "liste_bewertet": {WALLET: {"unsicher_versuche": zaehler}}}
    rows, _ = scout.check_list(state, 200001, 100.0)
    assert rows[0]["ergebnis"].startswith("unsicher")
    assert state["liste_bewertet"][WALLET]["unsicher_versuche"] == 1
    assert len(calls) == 1


@pytest.mark.parametrize("fehlend", [None, 0, 2])
def test_cr5_4_discord_zeigt_fehlende_transaktionen(monkeypatch, fehlend):
    r, _ = auswerten(monkeypatch, transaktionen_mit_luecken(0))
    if fehlend is None:
        r.pop("tx_fehlend")
        r.pop("tx_abgerufen")
    else:
        r["tx_fehlend"] = fehlend
    _, line = scout._rating_line("Probe", WALLET, r, scout.score(r))
    assert ("2 von 20 Transaktionen fehlen" in line) == (fehlend == 2)
    assert ("Transaktionen fehlen" in line) == (fehlend == 2)
    for key in ("tx_abgerufen", "tx_fehlend"):
        assert key not in scout.CANDIDATES_HEADER
        assert key not in scout.TX_RESULT_HEADER


@pytest.mark.parametrize("kind", ["VERKAUF", "UEBERWEISUNG"])
@pytest.mark.parametrize("zeit", [2800, 16000])
def test_altbestand_abgang_veraendert_haltedauer_nicht(monkeypatch, kind, zeit):
    transactions = {
        "k": buy_tx(tokens=100, sol=1, block_time=10000),
        "v": sell_tx(pre=100, tokens=100, sol=2, block_time=11200),
    }
    vorher, _ = auswerten(monkeypatch, transactions)
    abgang = sell_tx if kind == "VERKAUF" else transfer_tx
    transactions["alt"] = abgang(pre=900, tokens=100, block_time=zeit)
    nachher, _ = auswerten(monkeypatch, transactions)
    assert vorher["haltedauer_median_min"] == nachher["haltedauer_median_min"] == 20.0
    assert vorher["reibung_pp"] == nachher["reibung_pp"] == scout.FRICTION_MID
    assert vorher["schnelle_verkaeufe_anteil"] == nachher["schnelle_verkaeufe_anteil"] == 0.0


def test_nachkauf_verschiebt_ersten_fenster_kauf_nicht(monkeypatch):
    r, _ = auswerten(monkeypatch, {
        "k1": buy_tx(tokens=100, sol=1, block_time=1000),
        "k2": buy_tx(pre=100, tokens=100, sol=1, block_time=1600),
        "v": sell_tx(pre=200, tokens=200, sol=4, block_time=2200),
    })
    assert r["haltedauer_median_min"] == 20.0


def test_versionswechsel_kaputte_kopfzeile_der_warteliste_wird_nicht_ueberschrieben(alter_speicher):
    state, _, now = alter_speicher
    with open(scout.WAIT_FILE, encoding="utf-8") as f:
        inhalt = f.read()
    kaputt = "xyz\n" + inhalt.split("\n", 1)[1]
    with open(scout.WAIT_FILE, "w", encoding="utf-8") as f:
        f.write(kaputt)
    assert scout.versionswechsel(state, now) == (0, 0)
    assert "speicher_version" not in state
    with open(scout.WAIT_FILE, encoding="utf-8") as f:
        assert f.read() == kaputt


def test_versionswechsel_kaputter_zustand_stoppt_nicht(alter_speicher):
    state, rows, now = alter_speicher
    state["speicher_geprueft"] = None
    assert scout.versionswechsel(state, now) == (2, 1)
    assert state["speicher_geprueft"] == {r["wallet"]: r["zeit"] for r in rows}


def test_versionswechsel_wiederholung_sperrt_keine_neuen_bewertungen(alter_speicher, monkeypatch):
    state, rows, now = alter_speicher
    save = scout.save_waitlist
    monkeypatch.setattr(scout, "save_waitlist", lambda wait: (_ for _ in ()).throw(OSError("kaputt")))
    assert scout.versionswechsel(state, now) == (0, 0)
    monkeypatch.setattr(scout, "save_waitlist", save)
    neu = {"zeit": "2026-10-05 12:00:00", "wallet": addr("Neu"), "ergebnis": "bewertet", "punkte": 30}
    scout.write_csv(rows + [neu])
    assert scout.versionswechsel(state, now + 3600) == (3, 1)
    assert neu["wallet"] not in state["speicher_geprueft"]
    assert [r["wallet"] for r in scout.stored_rows(state)] == [neu["wallet"]]
    assert "wechsel_start" not in state


def test_versionswechsel_beschaedigte_spalte_der_warteliste_wird_nicht_ueberschrieben(alter_speicher):
    state, _, now = alter_speicher
    with open(scout.WAIT_FILE, encoding="utf-8") as f:
        kaputt = f.read().replace("seit", "xyz", 1)
    with open(scout.WAIT_FILE, "w", encoding="utf-8") as f:
        f.write(kaputt)
    assert scout.versionswechsel(state, now) == (0, 0)
    assert "speicher_version" not in state


def test_pruefliste_zeitbudget_schiebt_den_rest_auf_den_naechsten_lauf(monkeypatch, clock):
    zweite_wallet = addr("ListeZwei")
    transactions = transaktionen_mit_luecken(0)
    transactions.update({f"zweite_{k}": v for k, v in transaktionen_mit_luecken(0, zweite_wallet).items()})
    calls = pruefliste_vorbereiten(monkeypatch, transactions)
    monkeypatch.setattr(scout, "load_list", lambda: [("Probe", WALLET), ("Zwei", zweite_wallet)])
    monkeypatch.setattr(scout, "LIST_ZEIT_MAX_S", 100)
    original = scout.stage1

    def stage1(*args, **kw):
        clock.now += 150                              # jede Bewertung kostet 150 s
        return original(*args, **kw)
    monkeypatch.setattr(scout, "stage1", stage1)
    state = {"wallets_geprueft": {}, "liste_bewertet": {}}
    rows, lines = scout.check_list(state, 200001, 100.0)
    assert [r["wallet"] for r in rows] == [WALLET]
    assert scout.STATS["liste_neu"] == 1 and scout.STATS["liste_offen"] == 1
    assert zweite_wallet not in state["liste_bewertet"]
    assert all(zweite_wallet not in str(z) for z in lines)
    state = json.loads(json.dumps(state))
    rows, _ = scout.check_list(state, 200002, 100.0)                 # naechster Lauf: nur noch die zweite
    assert [r["wallet"] for r in rows] == [zweite_wallet]
    assert scout.STATS["liste_offen"] == 0


def test_pruefliste_fehlerhafte_wallets_blockieren_die_hinteren_nicht(monkeypatch, clock):
    kaputt = addr("ListeKaputt")
    transactions = transaktionen_mit_luecken(0)
    calls = pruefliste_vorbereiten(monkeypatch, transactions)
    monkeypatch.setattr(scout, "load_list", lambda: [("Kaputt", kaputt), ("Probe", WALLET)])
    monkeypatch.setattr(scout, "LIST_ZEIT_MAX_S", 100)
    original = scout.stage1

    def stage1(wallet, *args, **kw):
        clock.now += 150
        if wallet == kaputt:
            raise RuntimeError("dauerhaft kaputt")
        return original(wallet, *args, **kw)
    monkeypatch.setattr(scout, "stage1", stage1)
    state = {"wallets_geprueft": {}, "liste_bewertet": {}}
    scout.check_list(state, 200001, 100.0)                          # kaputte Wallet verbraucht das Budget
    state = json.loads(json.dumps(state))
    rows, _ = scout.check_list(state, 200002, 100.0)                # jetzt kommt die hintere dran
    assert [r["wallet"] for r in rows] == [WALLET]


@pytest.mark.parametrize("kaputt", [None, [], "x", 5, {"__WALLET__": "NaN"}, {"__WALLET__": "Infinity"}])
def test_pruefliste_kaputter_versuchszustand_stoppt_nichts(monkeypatch, kaputt):
    pruefliste_vorbereiten(monkeypatch, transaktionen_mit_luecken(0))
    monkeypatch.setattr(scout, "load_list", lambda: [("Probe", WALLET)])
    if isinstance(kaputt, dict):
        kaputt = {WALLET: v for v in kaputt.values()}
    state = {"wallets_geprueft": {}, "liste_bewertet": {}, "liste_versuch": kaputt}
    rows, _ = scout.check_list(state, 200001, 100.0)
    assert [r["wallet"] for r in rows] == [WALLET]
