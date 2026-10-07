"""DexScreener-Trending-Metas gegen Namenswellen (seit 07.10., nur Beobachtung, keine Texte gespeichert).
Abruf nur in der Pause (meta_abrufen), Vergleich im Scan ohne Netzwerk (metas_pruefen)."""
import csv

import bot as core
from helpers import addr, tok
from test_bot_namenswelle import erkennen, einzige, wellen_speicher, zeilen  # noqa: F401


def metas(*namen):
    return [{"name": n, "slug": n.lower().replace(" ", "-"), "description": "Text, der nie gespeichert wird",
             "marketCap": 1, "tokenCount": 2} for n in namen]


def abrufe(monkeypatch, *antworten):
    pfade, folge = [], list(antworten)

    def dex_get(path):
        pfade.append(path)
        return folge.pop(0) if folge else None
    monkeypatch.setattr(core, "dex_get", dex_get)
    return pfade


def test_treffer_minuten_und_rang_an_der_welle(clock, monkeypatch):
    pfade = abrufe(monkeypatch, metas("AI Agents"), metas("Cats", "Dragon Season"))
    p = core.load_portfolio()
    core.meta_abrufen(clock.now)                         # erster Abruf der Schicht, noch keine Welle
    erkennen(clock, p=p)
    w = einzige(p)
    clock.sleep(300)
    core.meta_abrufen(clock.now)                         # DRAGON erscheint 5 min nach der Welle auf Rang 2
    core.metas_pruefen(p, clock.now)
    assert pfade == ["/metas/trending/v1"] * 2
    assert w["meta_treffer"] == 1 and w["meta_minuten"] == 5.0 and w["meta_rang"] == 2
    core.metas_pruefen(p, clock.now)                     # ohne neuen Abruf zaehlt nichts doppelt
    assert w["meta_abrufe"] == 1
    core.welle_aufzeichnen(w, "ende", clock.now)
    ende = [r for r in zeilen() if r["art"] == "ende"][0]
    assert (ende["meta_treffer"], ende["meta_minuten"], ende["meta_rang"]) == ("1", "5.0", "2")
    text = open(core.WELLEN_FILE, encoding="utf-8").read()
    assert "Season" not in text and "nie gespeichert" not in text      # keine Meta-Namen oder Texte


def test_seit_schichtbeginn_trending_hat_unbekannte_minuten(clock, monkeypatch):
    abrufe(monkeypatch, metas("Dragon"), metas("Dragon"))
    p = core.load_portfolio()
    core.meta_abrufen(clock.now)
    clock.sleep(60)
    erkennen(clock, p=p)
    clock.sleep(300)
    core.meta_abrufen(clock.now)
    core.metas_pruefen(p, clock.now)
    w = einzige(p)
    assert w["meta_treffer"] == 1 and w["meta_minuten"] == "" and w["meta_rang"] == 1


def test_ohne_treffer_null_ohne_abruf_leer(clock, monkeypatch):
    abrufe(monkeypatch, metas("Cats"))
    p = erkennen(clock)
    w = einzige(p)
    core.welle_aufzeichnen(w, "start", clock.now)
    assert zeilen()[0]["meta_treffer"] == ""             # noch kein Abruf waehrend der Welle
    core.meta_abrufen(clock.now)
    core.metas_pruefen(p, clock.now)
    assert not w.get("meta_treffer") and w["meta_abrufe"] == 1
    core.welle_aufzeichnen(w, "ende", clock.now)
    assert [r for r in zeilen() if r["art"] == "ende"][0]["meta_treffer"] == "0"


def test_abruf_nur_in_der_pause_hoechstens_alle_5_minuten(clock, monkeypatch):
    pfade = abrufe(monkeypatch)                          # keine Antwort
    core.sleep_with_rechecks(12)
    assert pfade == ["/metas/trending/v1"] and core.STATS["meta_fehler"] == 1
    core.sleep_with_rechecks(12)
    assert len(pfade) == 1                               # erst nach 5 min wieder
    clock.sleep(300)
    core.sleep_with_rechecks(12)
    assert len(pfade) == 2


def test_scan_vergleich_ruft_nichts_ab(clock, monkeypatch):
    """Codex-Fund 07.10.: der Abruf darf Kauf und Positionspruefung nicht verzoegern."""
    pfade = abrufe(monkeypatch, metas("Dragon"))
    p = erkennen(clock)
    core.metas_pruefen(p, clock.now)
    assert pfade == [] and not einzige(p).get("meta_abrufe")


def test_unbrauchbare_antwort_ist_fehler_und_keine_beobachtung(clock, monkeypatch):
    """Codex-Fund 07.10.: kaputte Antwort darf weder als Nichttreffer noch als Schichtbeginn zaehlen."""
    abrufe(monkeypatch, [None, "x", {"name": None}, {"slug": 5}], [], metas("Dragon"))
    p = erkennen(clock)
    w = einzige(p)
    assert core.meta_abrufen(clock.now) is False and core.meta_abrufen(clock.now) is False
    core.metas_pruefen(p, clock.now)
    assert core.STATS["meta_fehler"] == 2 and not w.get("meta_abrufe")
    clock.sleep(300)
    assert core.meta_abrufen(clock.now) is True
    core.metas_pruefen(p, clock.now)
    assert w["meta_treffer"] == 1 and w["meta_minuten"] == "" and w["meta_abrufe"] == 1   # erster brauchbarer Abruf


def test_experimente_vergleichen_nicht(clock, monkeypatch):
    abrufe(monkeypatch, metas("Dragon"))
    core.meta_abrufen(clock.now)
    p = erkennen(clock)
    core.CTX["name"] = "kontrollgruppe"
    core.metas_pruefen(p, clock.now)
    assert not einzige(p).get("meta_abrufe")


def test_alte_wellen_datei_bekommt_neue_spalten_hinten(clock):
    alt = core.WELLEN_HEADER[:-3]
    with open(core.WELLEN_FILE, "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerows([alt, ["2026-10-07 10:00:00", "X_1", "start"] + [""] * (len(alt) - 3)])
    p = erkennen(clock)
    assert open(core.WELLEN_FILE, encoding="utf-8").readline().strip().split(",") == core.WELLEN_HEADER
    assert len(zeilen()) == 2 and einzige(p)


def test_dexscreener_zahlungen_nur_anzahl(market, monkeypatch, clock):
    monkeypatch.setattr(core, "dex_get", lambda path: {
        "orders": [{"type": "tokenProfile", "paymentTimestamp": (clock.now - 600) * 1000},
                   {"type": "tokenAd", "paymentTimestamp": (clock.now - 60) * 1000}], "boosts": []})
    market.set(addr("Mint1"), price=0.001)
    v = core.token_view(tok(mint=addr("Mint1"), now=clock.now), clock.now)
    core.dex_vormerken("kauf", v)
    core.run_dex()
    r = list(csv.DictReader(open(core.DEX_FILE, encoding="utf-8")))[0]
    assert r["zahlungen"] == "2" and "@" not in open(core.DEX_FILE, encoding="utf-8").read()


def test_uebernommene_welle_nach_schichtwechsel_wird_weiter_verglichen(clock, monkeypatch):
    """Codex-Fund 07.10.: der gespeicherte Stand einer Welle darf nach einem Neustart nichts blockieren."""
    abrufe(monkeypatch, metas("Cats"), metas("Dragon"), metas("Dragon"))
    p = erkennen(clock)
    w = einzige(p)
    core.meta_abrufen(clock.now)
    core.metas_pruefen(p, clock.now)
    assert w["meta_abrufe"] == 1 and w["meta_stand"] == clock.now
    monkeypatch.setattr(core, "_meta_abruf", [0.0, None, 0.0])          # neue Schicht: Speicher leer
    monkeypatch.setattr(core, "_meta_woerter", {})
    clock.sleep(600)
    core.meta_abrufen(clock.now)                                        # erster Abruf der neuen Schicht
    core.metas_pruefen(p, clock.now)
    assert w["meta_abrufe"] == 2 and w["meta_treffer"] == 1 and w["meta_minuten"] == ""
    clock.sleep(300)
    core.meta_abrufen(clock.now)
    core.metas_pruefen(p, clock.now)
    assert w["meta_abrufe"] == 3
