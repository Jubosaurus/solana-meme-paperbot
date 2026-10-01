"""Wallet-Scout: findet Kandidaten fuer das Copy Trading und erstellt eine Rangliste. Kauft und aendert nichts.

Ablauf (alle 6 Stunden):
1. Gewinner-Coins aus unseren eigenen Daten (Hauptstrategie, Experimente, Kursverlaeufe): Hoch >= 3x.
2. Kandidaten finden: fruehe Kaeufer dieser Coins (Helius, ohne die Kaeufer im ersten Block) und, falls
   verfuegbar, die Top-Trader laut Birdeye (Gratis-Tarif: CU-Zaehler, Stopp bei 28.000 CUs im Monat).
3. Stufe 1 (1 Helius-Credit je Wallet): letzte 1.000 Transaktionen mit Fehlerstatus -> Bots und stille Wallets raus.
4. Stufe 2 (rund 60 Credits je Wallet): letzte 60 erfolgreiche Transaktionen mit der Logik des Copy-Bots auswerten.
5. Rangliste in Discord und in scout/kandidaten.csv. Die Entscheidung trifft der Mensch.
"""
import argparse
import csv
import glob
import json
import os
import time
from datetime import datetime, timezone
from statistics import median

import requests

import bot as core
import copy_bot as cb

core.HELIUS_INTERVAL = 0.5          # Scout hoechstens ~2 Helius-Anfragen/s, laeuft parallel zu den anderen Bots

SCOUT_DIR = "scout"
STATE_FILE = os.path.join(SCOUT_DIR, "status.json")
CANDIDATES_FILE = os.path.join(SCOUT_DIR, "kandidaten.csv")
DISCORD_WEBHOOK_SCOUT = (os.environ.get("DISCORD_WEBHOOK_SCOUT") or os.environ.get("DISCORD_WEBHOOK_COPY") or "").strip()
BIRDEYE_API_KEY = (os.environ.get("BIRDEYE_API_KEY") or "").strip()
BIRDEYE_BASE = "https://public-api.birdeye.so"
BIRDEYE_CU = {"top_traders": 35}
BIRDEYE_MONTH_LIMIT = 28_000        # Gratis-Tarif 30.000 CUs; Reserve fuer Probelaeufe
BIRDEYE_INTERVAL = 1.2              # Gratis-Tarif: 1 Anfrage pro Sekunde

WINNER_MIN_MULTIPLE = 3.0           # Gewinner-Coin: Hoch mindestens 3x
WINNER_LOOKBACK_H = 48
COINS_PER_RUN = 6
EARLY_TX = 80                       # so viele fruehe erfolgreiche Transaktionen je Coin auswerten
MAX_SIG_PAGES = 5                   # bis zu 5.000 Signaturen zurueck; wird der Start nicht erreicht, Coin ueberspringen
BAD_TAGS = ("bundl", "snip", "bot", "mev", "insider", "dev", "arb")   # Birdeye-Markierungen, die wir nicht kopieren
BIRDEYE_PER_COIN = 5                # hoechstens so viele Birdeye-Kandidaten je Coin
STAGE2_PER_RUN = 15
STAGE2_TX = 60
RECHECK_DAYS = 7                    # eine Wallet fruehestens nach 7 Tagen erneut pruefen

# Stufe 1: Ausschlussgruende
MAX_FAILED_SHARE = 0.5
MAX_TX_PER_HOUR = 300
MAX_IDLE_H = 24
MIN_TX = 20

_birdeye_last = [0.0]
STATS = {"coins": 0, "kandidaten": 0, "stufe1_raus": {}, "stufe2": 0, "birdeye_cu": 0, "birdeye_fehler": "", "fehler": 0}


# ================================================================ Status

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {"coins_erledigt": {}, "wallets_geprueft": {}, "birdeye": {"monat": "", "cu": 0}}


def save_state(state):
    os.makedirs(SCOUT_DIR, exist_ok=True)
    tmp = STATE_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=1)
    os.replace(tmp, STATE_FILE)


# ================================================================ 1. Gewinner-Coins aus unseren Daten

def winner_coins(state, now):
    """Coins mit Hoch >= 3x aus Portfolios, Experimenten und Kursverlaeufen der letzten 48 Stunden."""
    best = {}
    since = datetime.fromtimestamp(now - WINNER_LOOKBACK_H * 3600, timezone.utc).isoformat()
    for f in ["portfolio.json"] + glob.glob("experimente/*/portfolio.json"):
        try:
            p = json.load(open(f, encoding="utf-8"))
        except (OSError, ValueError):
            continue
        for c in p.get("closed", []):
            if c.get("closed_at", "") >= since and c.get("peak_multiple", 0) >= WINNER_MIN_MULTIPLE:
                best[c["mint"]] = max(best.get(c["mint"], (0, ""))[0], c["peak_multiple"]), c["symbol"]
    days = {datetime.fromtimestamp(now - h * 3600, timezone.utc).strftime("%Y-%m-%d") for h in (0, 24, 48)}
    for f in [p for d in days for p in (f"verlauf/{d}.csv", f"copy/verlauf/{d}.csv")]:
        if not os.path.exists(f):
            continue
        with open(f, encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                try:
                    m = float(row.get("vielfaches") or 0)
                except ValueError:
                    continue
                if m >= WINNER_MIN_MULTIPLE and row.get("mint"):
                    if m > best.get(row["mint"], (0, ""))[0]:
                        best[row["mint"]] = (m, row.get("symbol", "?"))
    done = state["coins_erledigt"]
    fresh = [(m, s, mint) for mint, (m, s) in best.items() if mint not in done]
    return [(mint, s, m) for m, s, mint in sorted(fresh, reverse=True)[:COINS_PER_RUN]]


# ================================================================ 2. Kandidaten finden

def early_buyers(mint, sol_usd):
    """Fruehe Kaeufer eines Coins: aelteste erfolgreiche Transaktionen, ohne den ersten Block (Bundler)."""
    sigs, before, reached_start = [], None, False
    for _ in range(MAX_SIG_PAGES):
        opts = {"limit": 1000}
        if before:
            opts["before"] = before
        page = core.rpc("getSignaturesForAddress", [mint, opts]) or []
        sigs.extend(page)
        if len(page) < 1000:
            reached_start = True
            break
        before = page[-1].get("signature")
    if not reached_start:
        STATS["coins_zu_aktiv"] = STATS.get("coins_zu_aktiv", 0) + 1
        return []                                   # Start nicht erreicht: das waeren keine fruehen Kaeufer
    ok = [s for s in reversed(sigs) if s.get("err") is None and s.get("signature")]
    if not ok:
        return []
    first_slot = ok[0].get("slot")
    buyers = []
    for s in ok[:EARLY_TX]:
        if s.get("slot") == first_slot:
            continue                                # erster Block: Dev und Bundler
        tx = cb.fetch_tx(s["signature"])
        keys = ((tx or {}).get("transaction") or {}).get("message", {}).get("accountKeys") or []
        if not keys:
            continue
        signer = keys[0].get("pubkey") if isinstance(keys[0], dict) else keys[0]
        t = cb.parse_trade(tx, signer, sol_usd)
        if t and t["kind"] == "KAUF" and t["mint"] == mint:
            buyers.append(signer)
    return list(dict.fromkeys(buyers))


def birdeye_get(path, state, cost):
    if not BIRDEYE_API_KEY:
        return None
    month = datetime.now(timezone.utc).strftime("%Y-%m")
    usage = state["birdeye"]
    if usage.get("monat") != month:
        usage.update(monat=month, cu=0)
    if usage["cu"] + cost > BIRDEYE_MONTH_LIMIT:
        STATS["birdeye_fehler"] = f"Monatsgrenze erreicht ({usage['cu']} CUs)"
        return None
    core._throttle(_birdeye_last, BIRDEYE_INTERVAL)
    try:
        res = core.SESSION.get(f"{BIRDEYE_BASE}{path}", headers={"X-API-KEY": BIRDEYE_API_KEY, "x-chain": "solana",
                                                                 "accept": "application/json"}, timeout=15)
    except requests.RequestException as err:
        STATS["birdeye_fehler"] = str(err)[:80]
        return None
    usage["cu"] += cost
    STATS["birdeye_cu"] += cost
    if res.status_code != 200:
        STATS["birdeye_fehler"] = f"HTTP {res.status_code}: {res.text[:80]}"
        return None
    try:
        return res.json()
    except ValueError:
        return None


def birdeye_top_traders(mint, state):
    data = birdeye_get(f"/defi/v2/tokens/top_traders?address={mint}&time_frame=24h&sort_type=desc"
                       f"&sort_by=volume&offset=0&limit=10", state, BIRDEYE_CU["top_traders"])
    items = ((data or {}).get("data") or {}).get("items") or []
    out = []
    for it in items:
        addr = it.get("owner") or it.get("address") or it.get("wallet")
        tags = " ".join(str(t).lower() for t in (it.get("tags") or []))
        if not addr or any(b in tags for b in BAD_TAGS):
            STATS["birdeye_markiert"] = STATS.get("birdeye_markiert", 0) + (1 if addr else 0)
            continue
        if core.as_float(it.get("realizedPnl")) <= 0:
            continue                                # nur Trader, die auf diesem Coin Gewinn realisiert haben
        out.append(addr)
    return out[:BIRDEYE_PER_COIN]


# ================================================================ 3./4. Wallets pruefen

def stage1(wallet, now):
    """Billige Vorpruefung: Fehleranteil, Takt, letzte Aktivitaet. Gibt (Kennzahlen, Grund zum Ausschluss)."""
    sigs = core.rpc("getSignaturesForAddress", [wallet, {"limit": 1000}]) or []
    if len(sigs) < MIN_TX:
        return {"tx": len(sigs)}, "zu wenig Transaktionen"
    times = [s["blockTime"] for s in sigs if s.get("blockTime")]
    failed = sum(1 for s in sigs if s.get("err") is not None) / len(sigs)
    span_h = max((max(times) - min(times)) / 3600, 1 / 60) if times else 0
    per_h = len(sigs) / span_h if span_h else 0
    idle_h = (now - max(times)) / 3600 if times else 999
    m = {"tx": len(sigs), "fehlgeschlagen": round(failed, 3), "tx_pro_h": round(per_h, 1), "inaktiv_h": round(idle_h, 1),
         "sigs": [s["signature"] for s in sigs if s.get("err") is None][:STAGE2_TX]}
    if failed > MAX_FAILED_SHARE:
        return m, "Bot (viele fehlgeschlagene Transaktionen)"
    if per_h > MAX_TX_PER_HOUR:
        return m, "Bot (zu hoher Takt)"
    if idle_h > MAX_IDLE_H:
        return m, "still (laenger als 24 h kein Trade)"
    return m, None


def stage2(wallet, sigs, sol_usd):
    """Gruendliche Auswertung der letzten erfolgreichen Transaktionen mit der Logik des Copy-Bots."""
    trades = []
    for sig in sigs:
        t = cb.parse_trade(cb.fetch_tx(sig), wallet, sol_usd)
        if t and t["kind"] in ("KAUF", "VERKAUF"):
            trades.append(t)
    buys = [t for t in trades if t["kind"] == "KAUF"]
    sells = [t for t in trades if t["kind"] == "VERKAUF"]
    per = {}
    for t in sorted(trades, key=lambda t: t["block_time"] or 0):
        p = per.setdefault(t["mint"], {"aus": 0.0, "ein": 0.0, "gekauft": 0.0, "verkauft": 0.0,
                                       "t0": t["block_time"] or 0, "t1": t["block_time"] or 0})
        p["aus" if t["kind"] == "KAUF" else "ein"] += t["sol"]
        p["gekauft" if t["kind"] == "KAUF" else "verkauft"] += t["tokens"]
        p["t0"] = min(p["t0"], t["block_time"] or p["t0"])
        p["t1"] = max(p["t1"], t["block_time"] or p["t1"])
    # abgeschlossen: im Zeitraum gekauft und mindestens 90 % davon wieder verkauft (sonst noch offen)
    closed = [p for p in per.values() if p["aus"] > 0 and p["gekauft"] > 0 and p["verkauft"] >= 0.9 * p["gekauft"]]
    pnl = sorted((p["ein"] - p["aus"] for p in closed), reverse=True)
    drop = 3 if len(pnl) >= 12 else 1 if len(pnl) >= 4 else 0   # Gluckstreffer abziehen, aber nicht alles
    micro = [t for t in sells if t["pre_raw"] and abs(t["delta_raw"]) / t["pre_raw"] < 0.05]
    times = [t["block_time"] for t in trades if t["block_time"]]
    span_d = max((max(times) - min(times)) / 86400, 1 / 24) if len(times) > 1 else None
    return {
        "trades": len(trades), "kaeufe": len(buys), "verkaeufe": len(sells),
        "trades_pro_tag": round(len(trades) / span_d, 1) if span_d else None,
        "kauf_median_sol": round(median(t["sol"] for t in buys), 3) if buys else None,
        "anteil_kaeufe_ab_0_1": round(sum(t["sol"] >= 0.1 for t in buys) / len(buys), 2) if buys else None,
        "coins_abgeschlossen": len(closed),
        "trefferquote": round(sum(x > 0 for x in pnl) / len(pnl), 2) if pnl else None,
        "gewinn_sol": round(sum(pnl), 3) if pnl else None,
        "gewinn_ohne_beste_sol": round(sum(pnl[drop:]), 3) if pnl else None, "beste_abgezogen": drop,
        "haltedauer_median_min": round(median((p["t1"] - p["t0"]) / 60 for p in closed), 1) if closed else None,
        "mini_verkaeufe_anteil": round(len(micro) / len(sells), 2) if sells else None,
        "bot_gebuehr_anteil": round(sum(t["other"] > 0.003 * t["sol"] for t in trades) / len(trades), 2) if trades else None,
    }


def score(s2):
    """Rangfolge: Gewinn ohne die besten Coins (3 ab 12 Coins, sonst 1), dazu Trefferquote.
    Abzuege fuer ueberwiegend Mini-Verkaeufe und ueberwiegend Kaeufe unter 0,1 SOL (fuer uns schwer kopierbar)."""
    if not s2 or not s2.get("coins_abgeschlossen"):
        return -999
    base = s2.get("gewinn_ohne_beste_sol") or 0
    base += (s2.get("trefferquote") or 0) * 0.5
    if (s2.get("mini_verkaeufe_anteil") or 0) > 0.5:
        base -= 1
    if (s2.get("anteil_kaeufe_ab_0_1") or 0) < 0.5:
        base -= 1
    return round(base, 3)


# ================================================================ Ausgabe

def write_csv(rows):
    os.makedirs(SCOUT_DIR, exist_ok=True)
    header = ["zeit", "wallet", "quelle", "coin", "ergebnis", "grund", "punkte", "tx", "fehlgeschlagen", "tx_pro_h",
              "inaktiv_h", "trades", "kaeufe", "verkaeufe", "trades_pro_tag", "kauf_median_sol", "anteil_kaeufe_ab_0_1",
              "coins_abgeschlossen", "trefferquote", "gewinn_sol", "gewinn_ohne_beste_sol", "beste_abgezogen", "haltedauer_median_min",
              "mini_verkaeufe_anteil", "bot_gebuehr_anteil"]
    new = not os.path.exists(CANDIDATES_FILE)
    with open(CANDIDATES_FILE, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new:
            w.writerow(header)
        for r in rows:
            w.writerow([r.get(k, "") for k in header])


def notify(title, lines):
    saved = dict(core.CTX)
    core.CTX.update(webhook=DISCORD_WEBHOOK_SCOUT or None, title_prefix="")
    try:
        core.discord(title, "\n".join(l for l in lines if l), 0x0EA5E9)
    finally:
        core.CTX.clear()
        core.CTX.update(saved)


def git_push():
    g = core._git
    g("config", "user.name", "github-actions[bot]")
    g("config", "user.email", "github-actions[bot]@users.noreply.github.com")
    for _ in range(3):
        if g("fetch", "-q", "origin", "main").returncode != 0:
            continue
        g("reset", "-q", "origin/main")
        g("add", SCOUT_DIR)
        if g("diff", "--cached", "--quiet").returncode == 0:
            return
        g("commit", "-q", "-m", "SCOUT Update [skip ci]")
        if g("push", "-q", "origin", "HEAD:main").returncode == 0:
            return


# ================================================================ Lauf

def known_wallets():
    known = set()
    if os.path.exists(cb.WALLET_FILE):
        for line in open(cb.WALLET_FILE, encoding="utf-8"):
            part = line.lstrip("# ").split(":", 1)
            if len(part) == 2:
                known.add(part[1].split()[0].strip() if part[1].split() else "")
    return known


def run():
    now = time.time()
    core.git_sync_start()
    state = load_state()
    sol_usd = core.sol_price()
    coins = winner_coins(state, now)
    STATS["coins"] = len(coins)
    known = known_wallets()
    recent = {w for w, ts in state["wallets_geprueft"].items() if now - ts < RECHECK_DAYS * 86400}
    found = {}                                       # Wallet -> (Quelle, Coin)
    for mint, symbol, mult in coins:
        try:
            for w in early_buyers(mint, sol_usd):
                found.setdefault(w, ("frueh", f"{symbol} {mult:.1f}x"))
            for w in birdeye_top_traders(mint, state):
                found.setdefault(w, ("birdeye", f"{symbol} {mult:.1f}x"))
        except Exception as err:
            STATS["fehler"] += 1
            print(f"[SCOUT] {symbol}: {str(err)[:120]}")
        state["coins_erledigt"][mint] = now
    cands = [w for w in found if w not in known and w not in recent]
    STATS["kandidaten"] = len(cands)
    rows, stage2_list = [], []
    for w in cands:
        try:
            m, reason = stage1(w, now)
        except Exception as err:
            STATS["fehler"] += 1
            print(f"[SCOUT] Stufe 1 {w[:8]}: {str(err)[:100]}")
            continue
        state["wallets_geprueft"][w] = now
        row = {"zeit": cb.now_str(), "wallet": w, "quelle": found[w][0], "coin": found[w][1],
               **{k: v for k, v in m.items() if k != "sigs"}}
        if reason:
            STATS["stufe1_raus"][reason.split(" (")[0]] = STATS["stufe1_raus"].get(reason.split(" (")[0], 0) + 1
            rows.append(dict(row, ergebnis="raus", grund=reason))
        else:
            stage2_list.append((m["tx_pro_h"], w, row, m["sigs"]))
    ranked = []
    for _, w, row, sigs in sorted(stage2_list)[:STAGE2_PER_RUN]:  # ruhigere Wallets zuerst (eher menschlich)
        try:
            s2 = stage2(w, sigs, sol_usd)
        except Exception as err:
            STATS["fehler"] += 1
            print(f"[SCOUT] Stufe 2 {w[:8]}: {str(err)[:100]}")
            continue
        STATS["stufe2"] += 1
        pts = score(s2)
        r = dict(row, **s2, ergebnis="bewertet", punkte=pts)
        rows.append(r)
        ranked.append(r)
    ranked.sort(key=lambda r: -r["punkte"])
    write_csv(rows)
    save_state(state)
    lines = [f"**Gewinner-Coins:** {', '.join(f'{s} {m:.1f}x' for _, s, m in coins) or 'keine neuen'}",
             f"**Kandidaten:** {STATS['kandidaten']} neu | **Stufe 1 aussortiert:** {STATS['stufe1_raus'] or 0} | "
             f"**Stufe 2 bewertet:** {STATS['stufe2']}"
             + (f" | Birdeye-Markierte (Bundler, Sniper, Bots) ausgelassen: {STATS['birdeye_markiert']}"
                if STATS.get("birdeye_markiert") else "")
             + (f" | Coins zu aktiv fuer fruehe Kaeufer: {STATS['coins_zu_aktiv']}" if STATS.get("coins_zu_aktiv") else "")]
    top = [r for r in ranked if r["punkte"] > 0][:8]
    if top:
        lines.append("**Rangliste** (Gewinn ohne beste Coins | Treffer | Kauf-Median | Trades/Tag | Haltedauer):")
        for i, r in enumerate(top, 1):
            lines.append(f"{i}. `{r['wallet']}` ({r['quelle']}, {r['coin']})\n"
                         f"   {r['gewinn_ohne_beste_sol']:+} SOL (ohne {r['beste_abgezogen']} beste) | "
                         f"{(r['trefferquote'] or 0):.0%} | {r['kauf_median_sol']} SOL | {r['trades_pro_tag']} | "
                         f"{r['haltedauer_median_min']} min | Punkte {r['punkte']}")
        lines.append("Eintragen in copy_wallets.txt als `Name: Adresse`.")
    else:
        lines.append("Keine Wallet mit positivem Ergebnis in diesem Lauf.")
    lines.append(f"**Birdeye:** {STATS['birdeye_cu']} CUs in diesem Lauf, {state['birdeye']['cu']} im Monat"
                 + (f" | {STATS['birdeye_fehler']}" if STATS["birdeye_fehler"] else "") if BIRDEYE_API_KEY
                 else "**Birdeye:** kein Key, nur Helius")
    if STATS["fehler"]:
        lines.append(f"**Fehler:** {STATS['fehler']}")
    notify("🔭 Wallet-Scout", lines)
    git_push()


def probe():
    print("[SCOUT PROBE] Birdeye-Key:", "gesetzt" if BIRDEYE_API_KEY else "FEHLT")
    print("[SCOUT PROBE] Discord-Kanal:", "Scout" if os.environ.get("DISCORD_WEBHOOK_SCOUT") else
          ("Copy (kein eigener Scout-Kanal)" if DISCORD_WEBHOOK_SCOUT else "FEHLT"))
    state = load_state()
    sol_usd = core.sol_price()
    coins = winner_coins(state, time.time())
    print(f"[SCOUT PROBE] Gewinner-Coins (noch nicht untersucht): {[(s, round(m, 1)) for _, s, m in coins]}")
    if not coins:
        return
    mint, symbol, _ = coins[0]
    buyers = early_buyers(mint, sol_usd)
    print(f"[SCOUT PROBE] Fruehe Kaeufer von {symbol}: {len(buyers)}, z. B. {buyers[:3]}")
    if BIRDEYE_API_KEY:
        data = birdeye_get(f"/defi/v2/tokens/top_traders?address={mint}&time_frame=24h&sort_type=desc"
                           f"&sort_by=volume&offset=0&limit=10", state, BIRDEYE_CU["top_traders"])
        items = ((data or {}).get("data") or {}).get("items") or []
        print(f"[SCOUT PROBE] Birdeye Top-Trader: {len(items)} | Fehler: {STATS['birdeye_fehler'] or 'keiner'}")
        if items:
            tags = sorted({str(t) for it in items for t in (it.get("tags") or [])})
            print(f"        Markierungen in der Liste: {tags or 'keine'}")
            for it in items[:10]:
                print(f"        {it.get('owner', '?')[:8]} Tags {it.get('tags')} | Trades {it.get('trade')} | "
                      f"realisiert {core.as_float(it.get('realizedPnl')):,.0f} $")
            sb_items = [it.get("owner") for it in items]
            kept = [w for w in sb_items if w and not any(b in " ".join(str(t).lower() for t in
                    (next(i for i in items if i.get("owner") == w).get("tags") or [])) for b in BAD_TAGS)
                    and core.as_float(next(i for i in items if i.get("owner") == w).get("realizedPnl")) > 0]
            print(f"        Nach Filter (keine Markierung, Gewinn > 0): {len(kept)} von {len(items)}")
            if kept:
                pnl = birdeye_get(f"/wallet/v2/pnl/summary?wallet={kept[0]}", state, 30)
                print(f"[SCOUT PROBE] Birdeye PnL-Zusammenfassung (30 CUs): "
                      f"{'verfuegbar: ' + json.dumps(pnl)[:250] if pnl else 'nicht verfuegbar: ' + STATS['birdeye_fehler']}")
    if buyers:
        m, reason = stage1(buyers[0], time.time())
        print(f"[SCOUT PROBE] Stufe 1 fuer {buyers[0][:8]}: { {k: v for k, v in m.items() if k != 'sigs'} } -> {reason or 'weiter'}")
        if not reason:
            print(f"[SCOUT PROBE] Stufe 2: {stage2(buyers[0], m['sigs'][:20], sol_usd)}")
    save_state(state)                                # nur der CU-Zaehler
    print("[SCOUT PROBE] fertig. Diese Ausgabe bitte an Claude schicken.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--probe", action="store_true")
    probe() if ap.parse_args().probe else run()
