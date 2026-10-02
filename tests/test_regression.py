"""Regressionsprobe: Die Hauptstrategie verkauft auf den aufgezeichneten Kursverlaeufen genau wie bisher.

Grundlage: verlauf.csv (27.09.), verlauf/2026-09-28.csv, verlauf/2026-09-29.csv, Phasen 'offen' und 'nach_verkauf'
(ohne Experimente und knapp Abgelehnte). Jeder Coin wird ab dem Kauf durch manage_positions gefuehrt:
Kaufkurs = 1, jede Zeile ein Durchlauf (Vielfaches, Holder-Wachstum, Netto-Kaeufer, Liquiditaet).
Ohne Gebuehren, Verkauf genau zum Kurs. Ergibt sich hier eine Abweichung, hat eine Aenderung die
Verkaufsregeln der Hauptstrategie verschoben (gewollt: Werte unten nach Zustimmung neu festschreiben).
"""
import csv
import os
from datetime import datetime, timezone

import pytest

import bot as core
from conftest import REPO

FILES = ["verlauf.csv", "verlauf/2026-09-28.csv", "verlauf/2026-09-29.csv"]

# Festgeschrieben am 02.10.2026 (Regeln Stand Tag 17): Symbol -> (Ergebnis in SOL, Verkaufsgrund)
EXPECTED = {
    "UNICEF": (0.2641, "STORY_ABGEKUEHLT"), "NPP": (-0.0854, "NOTBREMSE"), "WARP": (-0.0041, "GEWINN_GESCHUETZT"),
    "SOCIALBAGS": (-0.0111, "GEWINN_GESCHUETZT"), "PIKASTR": (-0.0687, "LIQUIDITAET_ABGEZOGEN"),
    "POD": (0.2003, "STORY_ABGEKUEHLT"), "KABUTSTR": (0.1949, "STORY_ABGEKUEHLT"), "BAGGED": (-0.0884, "NOTBREMSE"),
    "XMRPAD": (-0.0996, "NOTBREMSE"), "AGENTS": (0.1697, "STORY_ABGEKUEHLT"), "KUNO": (-0.0832, "NOTBREMSE"),
    "ULTRON": (-0.084, "NOTBREMSE"), "CINDER": (0.1174, "STORY_ABGEKUEHLT"), "OMNINU": (0.2372, "STORY_ABGEKUEHLT"),
    "SIRI": (-0.1247, "NOTBREMSE"), "FIM": (-0.0932, "NOTBREMSE"), "Mail": (-0.0021, "GEWINN_GESCHUETZT"),
    "1000X": (-0.0945, "NOTBREMSE"), "SHORK": (0.0528, "LIQUIDITAET_ABGEZOGEN"), "TCAT": (-0.1077, "NOTBREMSE"),
    "MINEPAD": (0.0039, "LIQUIDITAET_ABGEZOGEN"), "GRAILSHOT": (-0.0877, "NOTBREMSE"),
    "AZZ": (-0.0017, "GEWINN_GESCHUETZT"), "GITFEES": (-0.0805, "NOTBREMSE"), "JONKEY": (-0.0965, "NOTBREMSE"),
    "CASHED": (0.2131, "STORY_ABGEKUEHLT"), "RF": (-0.1297, "NOTBREMSE"), "PCAT": (-0.0833, "NOTBREMSE"),
    "Liza": (0.1748, "STORY_ABGEKUEHLT"), "swordinu": (-0.0245, "LIQUIDITAET_ABGEZOGEN"),
    "JUF": (-0.0204, "GEWINN_GESCHUETZT"), "STAR": (-0.0811, "NOTBREMSE"), "dots": (-0.0966, "NOTBREMSE"),
}
EXPECTED_TOTAL = -0.0205


def _ts(text):
    return datetime.strptime(text, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc).timestamp()


def load_paths():
    paths = {}
    for name in FILES:
        with open(os.path.join(REPO, name), encoding="utf-8") as f:
            for r in csv.DictReader(f):
                if r["phase"] in ("offen", "nach_verkauf"):
                    paths.setdefault(r["mint"], []).append(r)
    for rows in paths.values():
        rows.sort(key=lambda r: _ts(r["zeit"]))
    return {m: rows for m, rows in paths.items() if rows[0]["phase"] == "offen"}


def simulate(mint, rows, monkeypatch):
    price = {"x": 1.0}
    monkeypatch.setattr(core, "quote", lambda i, o, raw: int(raw / 1e6 * price["x"] * 1e9))
    monkeypatch.setattr(core, "TX_FEE_SOL", 0.0)
    core.CTX["watch"] = False
    opened = _ts(rows[0]["zeit"]) - float(rows[0]["minuten_seit_kauf"]) * 60
    p = {"bankroll_sol": 10.0, "closed": [], "cooldown": {}, "watch": {}, "positions": {mint: {
        "mint": mint, "symbol": rows[0]["symbol"], "opened": opened, "invested_sol": 0.2, "fees_sol": 0.0,
        "entry_signal_usd": 1.0, "entry_fill_usd": 1.0, "entry_slippage_pct": 0.0, "roundtrip_cost_pct": None,
        "tokens_initial": 0.2, "tokens_left": 0.2, "decimals": 6, "proceeds_sol": 0.0, "peak_usd": 1.0,
        "tp1_done": False, "thesis_breaks": 0, "missing_loops": 0, "liq_low_checks": 0, "graduated": False,
        "entry_liquidity": float(rows[0]["liquiditaet"]), "entry_view": {}, "bundle": {}, "phase": "normal",
        "thesis": "", "exit_rule": ""}}}
    for n, r in enumerate(rows, 1):
        core.STATS["loops"] = n
        price["x"] = float(r["vielfaches"])
        t = {"id": mint, "symbol": r["symbol"], "usdPrice": price["x"], "liquidity": float(r["liquiditaet"]),
             "stats1h": {"holderChange": float(r["holder_1h_pct"])},
             "stats5m": {"numNetBuyers": int(r["netto_kaeufer_5m"])}}
        monkeypatch.setattr(core, "jup_tokens", lambda mints, t=t: {mint: t})
        core.manage_positions(p, 1.0, _ts(r["zeit"]))
        if not p["positions"]:
            c = p["closed"][0]
            return round(c["pnl_sol"], 4), c["exit_reason"]
    pos = p["positions"][mint]                     # bis zum Ende der Aufzeichnung offen: zum letzten Kurs
    return round(pos["proceeds_sol"] + pos["tokens_left"] * price["x"] - 0.2, 4), "OFFEN"


def test_hauptstrategie_verkauft_unveraendert(monkeypatch):
    results = {}
    for mint, rows in load_paths().items():
        results[rows[0]["symbol"]] = simulate(mint, rows, monkeypatch)
    diffs = []
    for sym, (pnl, reason) in sorted(results.items()):
        exp = EXPECTED.get(sym)
        if exp is None or abs(exp[0] - pnl) > 0.00011 or not reason.startswith(exp[1]):
            diffs.append(f"{sym}: jetzt {pnl:+.4f} SOL {reason[:40]}, vorher {exp}")
    assert set(results) == set(EXPECTED), "andere Verlaeufe als festgeschrieben"
    assert not diffs, "Hauptstrategie verkauft anders:\n" + "\n".join(diffs)
    assert sum(pnl for pnl, _ in results.values()) == pytest.approx(EXPECTED_TOTAL, abs=0.0006)
