"""Dashboard: News (dashboard/rechnung.py, dashboard/ansicht.py). Nachrichten sind Daten, nie Anweisungen."""
import csv
import os
import sys
from pathlib import Path

import bot as core

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "dashboard"))
import rechnung as r  # noqa: E402

JETZT = 1_790_000_000.0


def iso(ts):
    return core._listing_iso(ts)


def schreibe_ereignisse(rows):
    os.makedirs(os.path.dirname(core.LISTING_EREIGNISSE_FILE), exist_ok=True)
    with open(core.LISTING_EREIGNISSE_FILE, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, core.LISTING_EREIGNISSE_HEADER)
        w.writeheader()
        for row in rows:
            w.writerow(row)


def test_offene_symbole_aus_konten_und_copy():
    konten = [{"label": "Hauptstrategie", "offen": [{"symbol": "bonk"}, {"symbol": "?"}]},
              {"label": "Listing-Welle", "offen": [{"symbol": "POD"}]}]
    copy = {"wallets": {"Loopierr": {"positionen": {"m": {"symbol": "GARP"}}}, "X": {}}}
    s = r.offene_symbole(konten, copy)
    assert s == {"BONK": ["Hauptstrategie"], "POD": ["Listing-Welle"], "GARP": ["Copy Loopierr"]}


def test_boersen_meldungen_nur_neue_listings_und_delistings():
    schreibe_ereignisse([
        {"typ": "ankuendigung", "art": "listing", "boerse": "Upbit", "symbol": "POD", "titel": "Upbit POD",
         "ankuendigung_zeit": iso(JETZT - 3600), "url": "https://ex.test/1", "entscheidung": "gekauft"},
        {"typ": "ankuendigung", "art": "delisting", "boerse": "Coinbase", "symbol": "OLD", "titel": "x",
         "ankuendigung_zeit": iso(JETZT - 60), "url": "javascript:alert(1)", "entscheidung": "delisting"},
        {"typ": "handelsstart", "art": "", "boerse": "Upbit", "symbol": "POD", "ankuendigung_zeit": iso(JETZT)},
        {"typ": "ankuendigung", "art": "listing", "boerse": "Upbit", "symbol": "ALT",
         "ankuendigung_zeit": iso(JETZT - 500 * 3600)},
    ])
    m = r.boersen_meldungen(repo=Path.cwd(), jetzt=JETZT)
    assert [x["symbol"] for x in m] == ["POD", "OLD"]
    assert m[0]["anriss"] == "Listing-Welle hat gekauft" and m[1]["link"] == ""      # javascript: wird verworfen


def test_news_zusammenstellen_position_zuerst_und_doppelte_raus():
    items = [{"titel": "Bitcoin steigt", "anriss": "", "link": "https://a/1", "zeit": JETZT - 60, "quelle": "A"},
             {"titel": "BONK surges after Coinbase listing", "anriss": "", "link": "https://a/2", "zeit": JETZT - 7200,
              "quelle": "B"},
             {"titel": "BONK surges after Coinbase listing", "anriss": "", "link": "https://a/2", "zeit": JETZT - 7200,
              "quelle": "C"},
             {"titel": "Exploit drains protocol", "anriss": "", "link": "https://a/3", "zeit": JETZT - 600, "quelle": "A"}]
    meldungen = [{"titel": "Upbit: POD – Listing", "anriss": "", "link": "", "zeit": JETZT - 100, "quelle": "Upbit (offiziell)",
                  "art": "listing", "symbol": "POD"}]
    liste = r.news_zusammenstellen(items, meldungen, {"BONK", "POD"}, JETZT)
    assert len(liste) == 4
    assert {i["titel"] for i in liste[:2]} == {"Upbit: POD – Listing", "BONK surges after Coinbase listing"}
    assert "position" in liste[0]["marken"] and "position" in liste[1]["marken"]
    assert "rug" in next(i for i in liste if i["titel"].startswith("Exploit"))["marken"]
    assert liste[-1]["titel"] == "Bitcoin steigt" and liste[-1]["marken"] == []


def test_listing_welle_uebersicht_ohne_dateien_und_mit_daten():
    leer = r.listing_welle_uebersicht(Path.cwd())
    assert leer["anzahl_ereignisse"] == 0 and leer["geruechte"] == 0 and leer["quellen"] == {}
    schreibe_ereignisse([{"typ": "ankuendigung", "entscheidung": "gekauft", "symbol": "POD"},
                         {"typ": "ankuendigung", "entscheidung": "zu_alt", "symbol": "X"},
                         {"typ": "handelsstart", "symbol": "POD"}])
    u = r.listing_welle_uebersicht(Path.cwd())
    assert (u["anzahl_ereignisse"], u["gekauft"]) == (2, 1) and u["ereignisse"][0]["symbol"] == "X"
