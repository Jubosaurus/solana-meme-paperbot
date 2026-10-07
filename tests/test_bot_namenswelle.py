"""Namenswellen: reine Beobachtung ohne Netzwerk und ohne geaenderte Handelsregeln."""
import copy
import csv
import json
from pathlib import Path

import pytest

import bot as core
from helpers import addr, tok


@pytest.fixture(autouse=True)
def wellen_speicher(monkeypatch):
    monkeypatch.setattr(core, "_welle_index", {})
    monkeypatch.setattr(core, "_welle_preise", {})
    monkeypatch.setattr(core, "_welle_letzte_views", {})
    monkeypatch.setattr(core, "_welle_kontext", [None, None])


def kandidaten(clock, ages=(1.4, 1.2, 1.0), wort="DRAGON", holders=(100, 300, 200)):
    return [core.token_view(tok(mint=addr(f"Mint{chr(65 + i)}"), now=clock.now,
                                age_h=age, symbol=chr(65 + i), name=f"{wort} {chr(65 + i)}",
                                holders=holders[i], price=0.001), clock.now)
            for i, age in enumerate(ages)]


def erkennen(clock, views=None, p=None):
    p = core.load_portfolio() if p is None else p
    core.namenswellen_pruefen(p, kandidaten(clock) if views is None else views, clock.now)
    return p


def einzige(p):
    assert len(p["wellen"]) == 1
    return next(iter(p["wellen"].values()))


def zeilen():
    with open(core.WELLEN_FILE, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def test_drei_coins_im_fenster_starten_welle(clock):
    p = erkennen(clock)
    w = einzige(p)
    assert w["wort"] == "DRAGON" and len(w["mints"]) == 3
    assert w["entscheidung"] == "offen"
    assert w["until"] == clock.now + 6 * 3600
    row = zeilen()[0]
    assert list(row) == core.WELLEN_HEADER
    assert row["art"] == "start" and row["anzahl_coins"] == "3"
    assert row["coins"].split() == [f"{chr(65 + i)}:{addr(f'Mint{chr(65 + i)}')[:8]}"
                                    for i in range(3)]


@pytest.mark.parametrize("ages", [(1.2, 1.0), (2.0, 1.0, 0.1), (6.01, 1.2, 1.0),
                                  (None, 1.2, 1.0)])
def test_zu_wenig_zu_weit_auseinander_oder_zu_alt(clock, ages):
    p = erkennen(clock, kandidaten(clock, ages=ages))
    assert not p["wellen"]
    assert not Path(core.WELLEN_FILE).exists()


@pytest.mark.parametrize("wort", ["INU", "COIN", "THE", "COINS", "MEMES", "BABY"])
def test_fuellwoerter_erzeugen_keine_welle(clock, wort):
    p = erkennen(clock, kandidaten(clock, wort=wort))
    assert not p["wellen"]
    assert core.NARRATIVE_STOPWORDS == {"THE", "COIN", "TOKEN", "SOL", "SOLANA", "MEME", "AND",
                                       "FOR", "OFFICIAL", "WITH", "FROM", "THIS", "THAT"}


def test_symbol_name_regex_und_eindeutige_mints(clock):
    views = kandidaten(clock)
    for v in views:
        v.update(symbol="$Dragon-X", name="dragon / THE")
    p = erkennen(clock, [views[0]] * 3)
    assert not p["wellen"]
    erkennen(clock, views, p)
    assert einzige(p)["wort"] == "DRAGON"
    assert core.welle_parts({"symbol": "$Dragon-X", "name": "THE baby"}) == {"DRAGON"}


def test_schiebefenster_findet_spaetere_gruppe(clock):
    views = kandidaten(clock)
    alter = {**views[0], "mint": addr("Alt"), "age_h": 5.0}
    w = einzige(erkennen(clock, [alter] + views))
    assert alter["mint"] not in w["mints"]


def test_groesster_nach_holdern_bei_gleichstand_aeltester(clock):
    views = kandidaten(clock, holders=(300, 300, 200))
    w = einzige(erkennen(clock, views))
    assert w["groesster"] == views[0]["mint"] and w["holders"] == 300
    assert w["ref_price"] == views[0]["price"]


def test_index_sammelt_mehrere_scans_und_bereinigt(clock):
    views = kandidaten(clock)
    p = erkennen(clock, views[:2])
    assert not p["wellen"]
    erkennen(clock, views[2:], p)
    assert einzige(p)["groesster"] == views[1]["mint"]
    clock.sleep(13 * 3600)
    core.manage_positions(p, 100, clock.now)
    erkennen(clock, [], p)
    assert not core._welle_index and not core._welle_preise and not p["wellen"]
    assert not core._welle_letzte_views


def test_cooldown_erweitert_nur_das_urspruengliche_fenster(clock):
    p = erkennen(clock)
    views = kandidaten(clock)
    extra = {**views[0], "mint": addr("Extra"), "symbol": "D", "age_h": 1.1, "holders": 9999}
    ausserhalb = {**extra, "mint": addr("Danach"), "age_h": 0.8}
    erkennen(clock, views + [extra, ausserhalb], p)
    w = einzige(p)
    assert len(w["mints"]) == 4 and extra["mint"] in w["mints"]
    assert ausserhalb["mint"] not in w["mints"]
    assert w["groesster"] == views[1]["mint"]
    assert len(zeilen()) == 1 and core.STATS["wellen"] == 1


def test_schichtwechsel_cooldown_und_kein_doppelter_start(clock, monkeypatch):
    p = erkennen(clock)
    core.save_portfolio(p)
    monkeypatch.setattr(core, "_welle_index", {})
    monkeypatch.setattr(core, "_welle_preise", {})
    p = core.load_portfolio()
    erkennen(clock, kandidaten(clock), p)
    assert len(zeilen()) == 1
    clock.sleep(6 * 3600)
    core.manage_positions(p, 100, clock.now)
    erkennen(clock, [], p)
    assert len(zeilen()) == 2
    # Gleiche Coins sind inzwischen zu alt, eine neue Gruppe darf neu starten.
    neu = kandidaten(clock)
    for i, v in enumerate(neu):
        v["mint"] = addr(f"Neu{chr(65 + i)}")
    erkennen(clock, neu, p)
    assert len(p["wellen"]) == 2 and zeilen()[-1]["art"] == "start"


def test_limit_offener_wellen(clock, monkeypatch):
    monkeypatch.setattr(core, "WELLE_MAX_OFFEN", 1)
    p = erkennen(clock, kandidaten(clock, wort="ALPHA") + kandidaten(clock, wort="ZEBRA"))
    assert einzige(p)["wort"] == "ALPHA"


def test_neue_schichtstatistik_trennt_speicher_alte_wellen_bleiben(clock, monkeypatch):
    alt = erkennen(clock)
    monkeypatch.setattr(core, "STATS", core.fresh_stats())
    neu = core.load_portfolio()
    core.manage_positions(neu, 100, clock.now)
    assert not core._welle_letzte_views
    erkennen(clock, kandidaten(clock)[:1], neu)
    assert not neu["wellen"] and einzige(alt)["wort"] == "DRAGON"


def test_letzter_reject_gilt_gekauft_bleibt(clock, market):
    p = erkennen(clock)
    v = kandidaten(clock)[1]
    core.log_reject(v, "KEIN_PLATZ")
    core.log_reject(v, "KEINE_STORY_LINKS")
    assert einzige(p)["grund"] == "KEINE_STORY_LINKS"
    market.set(v["mint"], price=v["price"])
    assert core.open_position(p, v, {}, 100)
    core.log_reject(v, "KEIN_PLATZ")
    assert einzige(p)["entscheidung"] == "gekauft" and einzige(p)["grund"] == ""


def test_experiment_kauf_und_reject_zaehlen_nicht(clock, market):
    p = erkennen(clock)
    v = kandidaten(clock)[1]
    market.set(v["mint"], price=v["price"])
    with core.experiment("kontrollgruppe"):
        ep = core.load_portfolio()
        core.log_reject(v, "KEIN_PLATZ")
        assert core.open_position(ep, v, {"quelle": "experiment"}, 100)
    assert einzige(p)["entscheidung"] == "offen"


def test_verlauf_ende_vielfache_und_altes_portfolio(clock, market, monkeypatch):
    p = core.load_portfolio()
    assert "wellen" not in p
    core.manage_positions(p, 100, clock.now)
    assert "wellen" not in p
    p = erkennen(clock, p=p)
    w = einzige(p)
    anderer = addr("Beobachter")
    market.set(anderer, price=0.001)
    p.setdefault("watch", {})[anderer] = {"symbol": "Z", "entry_fill_usd": 0.001,
                                          "opened": clock.now, "peak_usd": 0.001, "until": w["until"] - 1}
    calls = []
    monkeypatch.setattr(core, "jup_tokens", lambda mints: (calls.append(list(mints)) or market.jup_tokens(mints)))
    core.STATS["loops"] = 1
    core.manage_positions(p, 100, clock.now)
    assert not calls
    core.STATS["loops"] = core.WATCH_LOG_EVERY_LOOPS * core.NEAR_MISS_LOG_EVERY_LOOPS
    views = kandidaten(clock)
    views[1]["price"] = 0.003
    erkennen(clock, views, p)
    core.manage_positions(p, 100, clock.now)
    assert calls == [[anderer]]
    clock.sleep(5 * 3600)
    views[1].update(price=0.002, age_h=6.2)
    erkennen(clock, views, p)
    core.manage_positions(p, 100, clock.now)
    with open(core.verlauf_file(), encoding="utf-8", newline="") as f:
        paths = list(csv.DictReader(f))
    assert [r["phase"] for r in paths if r["phase"] == "welle"] == ["welle", "welle"]
    clock.sleep(3600)
    core.manage_positions(p, 100, clock.now)
    end = zeilen()[-1]
    assert end["art"] == "ende" and end["entscheidung"] == "nicht_geprueft"
    assert float(end["vielfaches"]) == 2 and float(end["hoch_vielfaches"]) == 3
    assert len(calls) == 2
    with open(core.PORTFOLIO_FILE, encoding="utf-8") as f:
        assert json.load(f)["wellen"][w["id"]]["beendet"]
    core.manage_positions(p, 100, clock.now)
    assert len(zeilen()) == 2


@pytest.mark.parametrize("art", ["start", "ende"])
def test_csv_aufzeichnung_ist_idempotent(clock, art):
    w = einzige(erkennen(clock))
    Path(core.WELLEN_FILE).unlink()
    assert core.welle_aufzeichnen(w, art, clock.now)
    assert core.welle_aufzeichnen(w, art, clock.now)
    assert [(r["welle"], r["art"]) for r in zeilen()] == [(w["id"], art)]
    andere_art = "ende" if art == "start" else "start"
    assert core.welle_aufzeichnen(w, andere_art, clock.now)
    andere = {**w, "id": w["id"] + "_neu"}
    assert core.welle_aufzeichnen(andere, art, clock.now)
    assert len(zeilen()) == 3


def test_wiederanlauf_mit_altem_portfolio_verdoppelt_start_und_ende_nicht(clock, monkeypatch):
    p = erkennen(clock)
    w = einzige(p)
    del w["start_geschrieben"]
    core.save_portfolio(p)
    clock.sleep(6 * 3600)
    assert core.wellen_beenden(p, clock.now)
    monkeypatch.setattr(core, "STATS", core.fresh_stats())
    alt = core.load_portfolio()
    assert core.wellen_beenden(alt, clock.now)
    assert einzige(alt)["start_geschrieben"] and einzige(alt)["beendet"]
    assert [r["art"] for r in zeilen()] == ["start", "ende"]


def test_leitcoin_vor_erkennung_gekauft_hat_vorrang_vor_cooldown(clock, market):
    p = core.load_portfolio()
    v = kandidaten(clock)[1]
    market.set(v["mint"], price=v["price"])
    assert core.open_position(p, v, {}, 100)
    assert v["mint"] in p["cooldown"]
    vorher = copy.deepcopy(p)
    w = einzige(erkennen(clock, p=p))
    assert (w["entscheidung"], w["grund"]) == ("gekauft", "vor_erkennung")
    assert (zeilen()[0]["entscheidung"], zeilen()[0]["grund"]) == ("gekauft", "vor_erkennung")
    core.log_reject(v, "KEIN_PLATZ")
    assert w["grund"] == "vor_erkennung"
    assert p["positions"] == vorher["positions"] and p["cooldown"] == vorher["cooldown"]
    assert p["bankroll_sol"] == vorher["bankroll_sol"]


@pytest.mark.parametrize("stunden,entscheidung,grund", [(23.99, "abgelehnt", "COOLDOWN"),
                                                       (24, "offen", ""), (25, "offen", "")])
def test_leitcoin_cooldown_gilt_nur_24_stunden(clock, stunden, entscheidung, grund):
    p = core.load_portfolio()
    p["cooldown"][kandidaten(clock)[1]["mint"]] = clock.now - stunden * 3600
    vorher = copy.deepcopy(p["cooldown"])
    w = einzige(erkennen(clock, p=p))
    assert (w["entscheidung"], w["grund"]) == (entscheidung, grund)
    assert (zeilen()[0]["entscheidung"], zeilen()[0]["grund"]) == (entscheidung, grund)
    assert p["cooldown"] == vorher and not p["positions"]


@pytest.mark.parametrize("loops", [1, core.WATCH_LOG_EVERY_LOOPS * core.NEAR_MISS_LOG_EVERY_LOOPS])
def test_nur_welle_behaelt_fruehen_ruecksprung_ohne_abruf(clock, monkeypatch, loops):
    p = erkennen(clock)
    abrufe, speichern, verlauf = [], [], []
    monkeypatch.setattr(core, "jup_tokens", lambda mints: abrufe.append(list(mints)))
    monkeypatch.setattr(core, "save_portfolio", lambda p: speichern.append(copy.deepcopy(p)))
    monkeypatch.setattr(core, "log_path", lambda *args: verlauf.append(args))
    core.STATS["loops"] = loops
    core.manage_positions(p, 100, clock.now)
    assert not abrufe and not speichern and not verlauf
    clock.sleep(6 * 3600)
    core.manage_positions(p, 100, clock.now)
    assert not abrufe and not verlauf and len(speichern) == 1
    assert einzige(speichern[0])["beendet"]


@pytest.mark.parametrize("sekunden,anzahl", [(0, 1), (600, 1), (601, 0)])
def test_verlauf_nutzt_nur_frische_scan_view(clock, monkeypatch, sekunden, anzahl):
    p = erkennen(clock)
    w = einzige(p)
    views = kandidaten(clock)
    views[1]["price"] = 0.003
    erkennen(clock, views, p)
    assert w["preis_usd"] == w["peak_usd"] == 0.003
    assert set(core._welle_letzte_views) == set(w["mints"])
    # Die gespeicherte View ist unabhaengig von spaeteren Aenderungen am Kandidaten.
    views[1]["price"] = 0.009
    clock.sleep(sekunden)
    verlauf = []
    monkeypatch.setattr(core, "log_path", lambda *args: verlauf.append(args))
    core.wellen_verlauf(p, {}, clock.now)
    assert len(verlauf) == anzahl
    if anzahl:
        assert verlauf[0][3]["price"] == 0.003
    assert w["preis_usd"] == w["peak_usd"] == 0.003


def test_scan_bereinigt_veraltete_views_und_merkte_nur_offene_wellen(clock):
    p = erkennen(clock)
    clock.sleep(601)
    erkennen(clock, [], p)
    assert not core._welle_letzte_views
    erkennen(clock, kandidaten(clock), p)
    assert core._welle_letzte_views
    einzige(p)["beendet"] = True
    erkennen(clock, kandidaten(clock), p)
    assert not core._welle_letzte_views


def test_sammelantwort_hat_vorrang_vor_scan_view(clock, monkeypatch):
    p = erkennen(clock)
    w = einzige(p)
    verlauf = []
    monkeypatch.setattr(core, "log_path", lambda *args: verlauf.append(args))
    core.wellen_verlauf(p, {w["groesster"]: tok(mint=w["groesster"], now=clock.now, price=0.004)}, clock.now)
    assert verlauf[0][3]["price"] == 0.004
    assert w["preis_usd"] == w["peak_usd"] == 0.004


@pytest.mark.parametrize("loops", [1, core.WATCH_LOG_EVERY_LOOPS, core.NEAR_MISS_LOG_EVERY_LOOPS,
                                  core.WATCH_LOG_EVERY_LOOPS * core.NEAR_MISS_LOG_EVERY_LOOPS])
def test_manage_mit_und_ohne_welle_gleiche_abrufe_und_handelsdaten(clock, market, monkeypatch, loops):
    p = erkennen(clock)
    gehalten, beobachtet, abgelehnt = [addr(name) for name in ("Position", "Watch", "Shadow")]
    for mint in (gehalten, beobachtet, abgelehnt):
        market.set(mint, price=0.001)
    v = core.token_view(market.tokens[gehalten], clock.now)
    assert core.open_position(p, v, {}, 100)
    p.setdefault("watch", {})[beobachtet] = {"symbol": "W", "entry_fill_usd": 0.001,
        "opened": clock.now, "peak_usd": 0.001, "until": clock.now + 3600}
    for mint in (gehalten, beobachtet, abgelehnt):
        p.setdefault("shadow", {})[mint] = {"symbol": "S", "ref_price": 0.001,
            "since": clock.now, "peak_usd": 0.001, "until": clock.now + 3600, "reason": "KEIN_PLATZ"}
    ohne = copy.deepcopy(p)
    del ohne["wellen"]
    abrufe = []
    monkeypatch.setattr(core, "jup_tokens", lambda mints: (abrufe.append(list(mints)) or market.jup_tokens(mints)))
    core.STATS["loops"] = loops
    market.calls.clear()
    core.manage_positions(p, 100, clock.now)
    mit_abrufe, mit_quotes = copy.deepcopy(abrufe), list(market.calls)
    abrufe.clear()
    market.calls.clear()
    core.manage_positions(ohne, 100, clock.now)
    assert abrufe == mit_abrufe and market.calls == mit_quotes
    assert einzige(p)["groesster"] not in abrufe[0]
    for feld in ("positions", "closed", "watch", "shadow", "cooldown", "bankroll_sol"):
        assert p[feld] == ohne[feld]


@pytest.mark.parametrize("store", ["shadow", "watch", "positions"])
def test_gemeinsame_mints_nur_einmal_abfragen(clock, market, monkeypatch, store):
    p = erkennen(clock)
    w = einzige(p)
    mint = w["groesster"]
    market.set(mint, price=0.0012)
    if store == "positions":
        core.open_position(p, kandidaten(clock)[1], {}, 100)
    elif store == "watch":
        p.setdefault("watch", {})[mint] = {"symbol": "B", "entry_fill_usd": 0.001,
                                          "opened": clock.now, "peak_usd": 0.001, "until": w["until"]}
    else:
        p.setdefault("shadow", {})[mint] = {"symbol": "B", "ref_price": 0.001, "since": clock.now,
                                           "peak_usd": 0.001, "until": w["until"], "reason": "KEIN_PLATZ"}
    core.STATS["loops"] = core.WATCH_LOG_EVERY_LOOPS * core.NEAR_MISS_LOG_EVERY_LOOPS
    calls = []
    monkeypatch.setattr(core, "jup_tokens", lambda mints: (calls.append(list(mints)) or market.jup_tokens(mints)))
    core.manage_positions(p, 100, clock.now)
    assert calls == [[mint]]
    assert w["preis_usd"] == 0.0012


def scan_vorbereiten(clock, market, monkeypatch):
    tokens = []
    for i, v in enumerate(kandidaten(clock)):
        tokens.append(market.set(v["mint"], age_h=v["age_h"], now=clock.now, symbol=v["symbol"],
                                name=v["name"], holders=v["holders"], price=v["price"],
                                holder_growth_1h=40 - i * 5, is_sus=i == 2))
    monkeypatch.setattr(core, "jup_category", lambda *args: tokens)
    monkeypatch.setattr(core, "safety_shield", lambda mint: None)
    monkeypatch.setattr(core, "bundle_dev_check", lambda mint: (None, {}))


def test_scan_mit_und_ohne_welle_gleiche_kaeufe_rejects_und_abrufe(clock, market, monkeypatch):
    scan_vorbereiten(clock, market, monkeypatch)
    p = core.load_portfolio()
    ohne = copy.deepcopy(p)
    core.scan(p, 100, clock.now)
    entries = copy.deepcopy(core.STATS["entries"])
    rejects = copy.deepcopy(core.STATS["rejects"])
    calls = list(market.calls)
    assert p["wellen"] and entries and rejects
    assert einzige(p)["entscheidung"] == "gekauft"
    monkeypatch.setattr(core, "STATS", core.fresh_stats())
    monkeypatch.setattr(core, "namenswellen_pruefen", lambda *args: None)
    market.calls.clear()
    core.scan(ohne, 100, clock.now)
    assert core.STATS["entries"] == entries and core.STATS["rejects"] == rejects
    assert market.calls == calls
    assert p["positions"] == ohne["positions"] and p["bankroll_sol"] == ohne["bankroll_sol"]
    assert core.STATS["helius_ok"] == core.STATS["helius_fail"] == 0


def test_fehler_in_erkennung_stoppt_scan_nicht(clock, market, monkeypatch):
    scan_vorbereiten(clock, market, monkeypatch)

    def kaputt(*args):
        raise ValueError("Testfehler")

    monkeypatch.setattr(core, "namenswellen_pruefen", kaputt)
    p = core.load_portfolio()
    core.scan(p, 100, clock.now)
    assert core.STATS["welle_fehler"] == 1
    assert core.STATS["entries"] and core.STATS["rejects"]


def test_schreibfehler_beim_ende_wird_gezaehlt_und_spaeter_wiederholt(clock, monkeypatch):
    p = erkennen(clock)
    clock.sleep(6 * 3600)
    real = core.ensure_csv_columns

    def kaputt(*args):
        raise OSError("Testfehler")

    monkeypatch.setattr(core, "ensure_csv_columns", kaputt)
    core.manage_positions(p, 100, clock.now)
    assert core.STATS["welle_fehler"] == 1 and not einzige(p).get("beendet")
    monkeypatch.setattr(core, "ensure_csv_columns", real)
    core.manage_positions(p, 100, clock.now)
    assert einzige(p)["beendet"] and len(zeilen()) == 2


def test_endmeldung_und_git_dateiliste(clock, sandbox):
    p = erkennen(clock)
    core.STATS["welle_fehler"] = 2
    core.shift_summary(p, 10.0, clock.now, "regulaer")
    assert any("Namenswellen (Beobachtung):** 1 erkannt | Fehler 2" in msg[1]
               for msg in sandbox["discord"])
    core.git_push()
    assert any(core.WELLEN_FILE in call for call in sandbox["git"])
