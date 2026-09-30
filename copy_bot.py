"""Copy-Trading-Experiment (Paper Trading, kein echtes Geld).

Folgt den Wallets aus copy_wallets.txt per Helius-WebSocket und handelt jeden ihrer Trades nach:
- jede Wallet hat ein eigenes Konto mit 10 SOL (neue Runde, wenn leer)
- jeder Kauf des Traders = 0,2 SOL bei uns, auch Nachkaeufe
- Verkauf desselben Anteils, den der Trader verkauft; Ueberweisung der Coins = Verkauf zum aktuellen Kurs
- kein Take-Profit, kein Stop-Loss; am Schichtende werden Positionen bei -99 % oder schlechter bereinigt
- alle Pruefungen des Hauptbots laufen mit und werden gespeichert, entscheiden aber nichts

Laeuft getrennt vom Hauptbot (eigener Workflow, eigene Dateien in copy/). Nutzt dessen Funktionen fuer
Jupiter, Helius und die Pruefungen, veraendert ihn aber nicht.
"""
import argparse
import csv
import json
import os
import re
import signal
import time
from datetime import datetime, timezone

import requests
import websocket                        # Paket websocket-client

import bot as core

WALLET_FILE = "copy_wallets.txt"
COPY_DIR = "copy"
ACCOUNTS_FILE = os.path.join(COPY_DIR, "konten.json")
JOURNAL_FILE = os.path.join(COPY_DIR, "journal.csv")

START_SOL = 10.0
BUY_SOL = 0.2
FEE_SOL = core.TX_FEE_SOL
CLEANUP_MAX_VALUE_PCT = 1.0             # Schichtende: Positionen mit <= 1 % Restwert (-99 %) bereinigen
SHIFT_SECONDS = core.SHIFT_DURATION_SECONDS
PING_EVERY = 30
PUSH_EVERY = 60
MIN_SWAP_LAMPORTS = 1_000_000           # unter 0,001 SOL gilt eine Bewegung nicht als Kauf/Verkauf
BASE_FEE_LAMPORTS = 5000                # Grundgebuehr pro Signatur
JUP_INTERVAL = 1.6                      # Copy-Bot fragt Jupiter etwas langsamer ab als der Hauptbot
DISCORD_WEBHOOK_COPY = (os.environ.get("DISCORD_WEBHOOK_COPY") or "").strip()
WS_URL = f"wss://mainnet.helius-rpc.com/?api-key={core.HELIUS_API_KEY}"
USDC_MINT = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
# Quelle: Solana Cookbook "MEV protection with Jito" (verweist auf docs.jito.wtf, getTipAccounts)
JITO_TIP_ACCOUNTS = {
    "96gYZGLnJYVFmbjzopPSU6QiEV5fGqZNyN9nmNhvrZU5", "HFqU5x63VTqvQss8hp11i4wVV8bD44PvwucfZ2bU7gRe",
    "Cw8CFyM9FkoMi7K7Crf6HNQqf4uEMzpKw6QNghXLvLkY", "ADaUMid9yfUytqMBgopwjb2DTLSokTSzL1zt6iGPaS49",
    "DfXygSm4jCyNCybVYYK6DwvWqjKee8pbDmJGcLWNDXjh", "ADuUkR4vqLUMWXxW9gh6D6L8pMSawimctcNZ5pGwDcEt",
    "DttWaMuVvTiduZRnguLF7jNxTgiMBZ1hyAumKUiL2KRL", "3AVi9Tg9Uo68tJfuvoKvqKNWKkC5wPdSSdeBnizKZ6jT"}

JOURNAL_HEADER = [
    "zeit", "trader", "wallet", "aktion", "symbol", "mint", "runde",
    "trader_signatur", "trader_zeit", "verzoegerung_s",
    "trader_sol", "trader_tokens", "trader_preis_sol", "trader_anteil",
    "trader_gebuehr_basis_sol", "trader_gebuehr_prio_sol", "trader_jito_tip_sol", "trader_sonstige_sol",
    "unser_sol", "unsere_tokens", "unser_preis_sol", "unsere_gebuehr_sol", "preisabstand_pct",
    "pnl_sol", "pnl_pct", "hinweis", "pruefungen"]

STATS = {"notifications": 0, "trades": {}, "skipped": {}, "reconnects": 0, "parse_errors": 0,
         "delays": [], "git_ok": 0, "git_fail": 0, "jup_429": 0, "errors": 0, "last_error": ""}
_jup_last = [0.0]
_seen = set()


class Interrupted(Exception):
    pass


def _on_signal(signum, frame):
    raise Interrupted()


# ================================================================ Wallets und Konten

def load_wallets(path=WALLET_FILE):
    """Liest 'Name: Adresse' je Zeile. Ungueltige Zeilen werden gemeldet und uebersprungen."""
    wallets = []
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        name, _, addr = line.partition(":")
        name, addr = name.strip(), addr.strip()
        if not name or not re.fullmatch(r"[1-9A-HJ-NP-Za-km-z]{32,44}", addr):
            print(f"[COPY] ungueltige Zeile in {path}: {line[:60]}")
            continue
        wallets.append((name, addr))
    return wallets


def load_accounts(wallets):
    data = {"wallets": {}}
    if os.path.exists(ACCOUNTS_FILE):
        with open(ACCOUNTS_FILE, encoding="utf-8") as f:
            data = json.load(f)                  # unlesbar -> Absturz, lieber nicht still neu anfangen
    for name, addr in wallets:
        acct = data["wallets"].setdefault(name, {
            "adresse": addr, "bankroll_sol": START_SOL, "runde": 1, "positionen": {}, "geschlossen": [],
            "gestartet": datetime.now(timezone.utc).isoformat()})
        acct["adresse"] = addr                   # falls die Adresse in der Liste geaendert wurde
    return data


def save_accounts(data):
    os.makedirs(COPY_DIR, exist_ok=True)
    data["saved_at"] = time.time()
    tmp = ACCOUNTS_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=1)
    os.replace(tmp, ACCOUNTS_FILE)


def journal(row):
    os.makedirs(COPY_DIR, exist_ok=True)
    new = not os.path.exists(JOURNAL_FILE)
    with open(JOURNAL_FILE, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new:
            w.writerow(JOURNAL_HEADER)
        w.writerow([row.get(k, "") for k in JOURNAL_HEADER])


def count(kind, key):
    STATS[kind][key] = STATS[kind].get(key, 0) + 1


# ================================================================ Jupiter (eigener Takt, Wiederholung bei 429)

def jup(path):
    headers = {"x-api-key": core.JUPITER_API_KEY} if core.JUPITER_API_KEY else {}
    for attempt in range(3):
        core._throttle(_jup_last, JUP_INTERVAL)
        try:
            res = core.SESSION.get(f"{core.JUP_BASE}{path}", headers=headers, timeout=12)
        except requests.RequestException as err:
            print(f"[COPY JUPITER] {path.split('?')[0]} -> {str(err)[:100]}")
            return None
        if res.status_code == 429:
            STATS["jup_429"] += 1
            time.sleep(2 * (attempt + 1))
            continue
        if res.status_code != 200:
            return None
        try:
            return res.json()
        except ValueError:
            return None
    return None


def quote_out(input_mint, output_mint, raw_amount):
    data = jup(f"/swap/v1/quote?inputMint={input_mint}&outputMint={output_mint}"
               f"&amount={int(raw_amount)}&slippageBps=500")
    try:
        return int((data or {}).get("outAmount") or 0)
    except (TypeError, ValueError):
        return 0


# ================================================================ Transaktion des Traders auswerten

def _instructions(tx):
    msg, meta = tx["transaction"]["message"], tx.get("meta") or {}
    for ins in msg.get("instructions") or []:
        yield ins, True
    for group in meta.get("innerInstructions") or []:
        for ins in group.get("instructions") or []:
            yield ins, False


def parse_trade(tx, wallet, sol_usd=None):
    """Erkennt Kauf, Verkauf oder Ueberweisung eines Tokens durch die Wallet.
    Gibt None zurueck, wenn es keine eigene Handelsaktion der Wallet ist."""
    if not tx or (tx.get("meta") or {}).get("err") is not None:
        return None
    meta, msg = tx["meta"], tx["transaction"]["message"]
    raw_keys = msg.get("accountKeys") or []
    keys = [k.get("pubkey") if isinstance(k, dict) else k for k in raw_keys]
    if wallet not in keys:
        return None
    i = keys.index(wallet)
    signer = bool(raw_keys[i].get("signer")) if isinstance(raw_keys[i], dict) else i == 0
    if not signer:
        return None                              # fremde Transaktion, die die Wallet nur erwaehnt
    fee = int(meta.get("fee") or 0) if i == 0 else 0
    n_sig = max(1, len(tx["transaction"].get("signatures") or []))
    fee_base = min(fee, BASE_FEE_LAMPORTS * n_sig)

    dec, owned, pre, post = {}, set(), {}, {}
    for entries, store in ((meta.get("preTokenBalances"), pre), (meta.get("postTokenBalances"), post)):
        for e in entries or []:
            if e.get("owner") != wallet:
                continue
            ui = e.get("uiTokenAmount") or {}
            store[e["mint"]] = store.get(e["mint"], 0) + int(ui.get("amount") or 0)
            dec[e["mint"]] = int(ui.get("decimals") or 0)
            if isinstance(e.get("accountIndex"), int) and e["accountIndex"] < len(keys):
                owned.add(keys[e["accountIndex"]])
    deltas = {m: post.get(m, 0) - pre.get(m, 0) for m in set(pre) | set(post)}
    wsol = deltas.pop(core.WSOL_MINT, 0)
    usdc = deltas.pop(USDC_MINT, 0)
    deltas = {m: d for m, d in deltas.items() if d != 0}
    if not deltas:
        return None
    mint = max(deltas, key=lambda m: abs(deltas[m]))
    d = deltas[mint]

    # Token-Konten, die in dieser Transaktion angelegt, befuellt oder geschlossen werden (z. B. temporaeres
    # WSOL-Konto). Eine Ueberweisung dorthin ist Teil des Tauschs, keine Gebuehr.
    token_accounts = set()
    for ins, _outer in _instructions(tx):
        parsed = ins.get("parsed") if isinstance(ins.get("parsed"), dict) else None
        if not parsed:
            continue
        info = parsed.get("info") or {}
        if ins.get("program") in ("spl-token", "spl-associated-token-account"):
            for k in ("account", "newAccount"):
                if isinstance(info.get(k), str):
                    token_accounts.add(info[k])
        elif ins.get("program") == "system" and str(parsed.get("type", "")).startswith("createAccount"):
            if info.get("source") == wallet and isinstance(info.get("newAccount"), str):
                token_accounts.add(info["newAccount"])

    jito = other = 0
    for ins, outer in _instructions(tx):
        parsed = ins.get("parsed") if isinstance(ins.get("parsed"), dict) else None
        if ins.get("program") != "system" or not parsed or parsed.get("type") != "transfer":
            continue
        info = parsed.get("info") or {}
        if info.get("source") != wallet:
            continue
        dest, lam = info.get("destination"), int(info.get("lamports") or 0)
        if dest in JITO_TIP_ACCOUNTS:
            jito += lam
        elif outer and dest != wallet and dest not in owned and dest not in token_accounts:
            other += lam                         # z. B. Gebuehr des Trading-Bots oder anderer Tip-Dienst

    sol_change = meta["postBalances"][i] - meta["preBalances"][i] + wsol
    swap = -(sol_change + fee + jito + other)    # > 0: SOL ausgegeben, < 0: SOL erhalten
    quote_asset = "SOL"
    if abs(swap) < MIN_SWAP_LAMPORTS and usdc and sol_usd:
        swap = int(-usdc / 1e6 / sol_usd * 1e9)  # Handel gegen USDC in SOL umgerechnet
        quote_asset = "USDC"
    if d > 0 and swap >= MIN_SWAP_LAMPORTS:
        kind = "KAUF"
    elif d < 0 and swap <= -MIN_SWAP_LAMPORTS:
        kind = "VERKAUF"
    elif d < 0:
        kind = "UEBERWEISUNG"
    else:
        return None                              # Token erhalten ohne zu zahlen (Airdrop, Uebertrag)
    tokens = abs(d) / 10 ** dec.get(mint, 0)
    return {"kind": kind, "mint": mint, "decimals": dec.get(mint, 0), "delta_raw": d,
            "pre_raw": pre.get(mint, 0), "tokens": tokens, "sol": abs(swap) / 1e9,
            "price_sol": (abs(swap) / 1e9 / tokens) if tokens and kind != "UEBERWEISUNG" else None,
            "fee_base": fee_base / 1e9, "fee_prio": (fee - fee_base) / 1e9, "jito": jito / 1e9,
            "other": other / 1e9, "block_time": tx.get("blockTime"), "quote_asset": quote_asset}


def fetch_tx(sig):
    """Die Transaktion ist bei 'confirmed' manchmal noch nicht abrufbar, deshalb bis zu 4 Versuche."""
    for attempt in range(4):
        tx = core.rpc("getTransaction", [sig, {"encoding": "jsonParsed", "commitment": "confirmed",
                                               "maxSupportedTransactionVersion": 0}])
        if tx:
            return tx
        time.sleep(0.6 * (attempt + 1))
    return None


# ================================================================ Pruefungen (nur zur Information)

def run_checks(mint, now):
    """Laeuft die Pruefungen des Hauptbots, ohne etwas zu entscheiden."""
    out = {}
    try:
        data = jup(f"/tokens/v2/search?query={mint}")
        tok = next((t for t in data or [] if t.get("id") == mint), None)
        if not tok:
            return {"fehler": "Token bei Jupiter nicht gefunden"}, None
        v = core.token_view(tok, now)
        out["schnellpruefung"] = core.quick_checks(v) or "bestanden"
        out["social"] = bool(core.has_social(v))
        out["sicherheit"] = core.safety_shield(mint) or "bestanden"
        reason, bundle = core.bundle_dev_check(mint)
        out["bundle_dev"] = reason or "bestanden"
        out["block0"] = {k: bundle.get(k) for k in ("block0_wallets", "block0_supply_pct",
                                                     "block0_still_held_pct") if k in (bundle or {})}
        out["merkmale"] = {k: v.get(k) for k in core.ENTRY_FEATURES}
        return out, v
    except Exception as err:                     # Pruefungen duerfen den Copy-Trade nie verhindern
        return {"fehler": str(err)[:120]}, None


# ================================================================ Nachhandeln

def trader_fields(t, sig):
    return {"trader_signatur": sig, "trader_zeit": datetime.fromtimestamp(t["block_time"], timezone.utc)
            .strftime("%Y-%m-%d %H:%M:%S") if t.get("block_time") else "",
            "trader_sol": f"{t['sol']:.6f}", "trader_tokens": f"{t['tokens']:.6f}",
            "trader_preis_sol": f"{t['price_sol']:.12g}" if t.get("price_sol") else "",
            "trader_gebuehr_basis_sol": f"{t['fee_base']:.6f}", "trader_gebuehr_prio_sol": f"{t['fee_prio']:.6f}",
            "trader_jito_tip_sol": f"{t['jito']:.6f}", "trader_sonstige_sol": f"{t['other']:.6f}"}


def notify(title, lines, color):
    saved = dict(core.CTX)
    core.CTX.update(webhook=DISCORD_WEBHOOK_COPY or None, title_prefix="[Copy] " if not DISCORD_WEBHOOK_COPY else "")
    try:
        core.discord(title, "\n".join(line for line in lines if line), color)
    finally:
        core.CTX.clear()
        core.CTX.update(saved)


def account_line(acct):
    invested = sum(p["invested_sol"] for p in acct["positionen"].values())
    return (f"**Konto:** frei {acct['bankroll_sol']:.3f} SOL | {len(acct['positionen'])} offen "
            f"(Einsatz {invested:.2f} SOL) | Runde {acct['runde']}")


def copy_buy(name, acct, t, sig, now):
    if acct["bankroll_sol"] < BUY_SOL + FEE_SOL:
        if not acct["positionen"]:
            acct["runde"] += 1
            acct["bankroll_sol"] = START_SOL
            notify(f"♻️ {name}: Konto aufgebraucht - Neustart", [f"Runde {acct['runde']} beginnt mit 10 SOL."], 0x8B5CF6)
        else:
            count("skipped", "kein_geld")
            journal({"zeit": now_str(), "trader": name, "wallet": acct["adresse"], "aktion": "AUSGELASSEN",
                     "mint": t["mint"], "runde": acct["runde"], "hinweis": "kein Geld frei", **trader_fields(t, sig)})
            return
    raw = quote_out(core.WSOL_MINT, t["mint"], int(BUY_SOL * 1e9))
    our_time = time.time()
    if raw <= 0:
        count("skipped", "keine_quote")
        journal({"zeit": now_str(), "trader": name, "wallet": acct["adresse"], "aktion": "AUSGELASSEN",
                 "mint": t["mint"], "runde": acct["runde"], "hinweis": "keine Jupiter-Quote", **trader_fields(t, sig)})
        return
    tokens = raw / 10 ** t["decimals"]
    our_price = BUY_SOL / tokens
    delay = our_time - t["block_time"] if t.get("block_time") else None
    if delay is not None:
        STATS["delays"].append(delay)
    pos = acct["positionen"].setdefault(t["mint"], {
        "mint": t["mint"], "symbol": t["mint"][:6], "decimals": t["decimals"], "tokens_raw": 0,
        "invested_sol": 0.0, "fees_sol": 0.0, "proceeds_sol": 0.0, "opened": our_time, "kaeufe": 0,
        "verkaeufe": 0, "trader_ausgegeben_sol": 0.0, "trader_erhalten_sol": 0.0, "runde": acct["runde"]})
    pos["tokens_raw"] += raw
    pos["invested_sol"] += BUY_SOL
    pos["fees_sol"] += FEE_SOL
    pos["kaeufe"] += 1
    pos["trader_ausgegeben_sol"] += t["sol"]
    acct["bankroll_sol"] -= BUY_SOL + FEE_SOL
    count("trades", "KAUF")
    checks, v = run_checks(t["mint"], now)
    if v:
        pos["symbol"] = v["symbol"]
    gap = (our_price / t["price_sol"] - 1) * 100 if t.get("price_sol") else None
    journal({"zeit": now_str(), "trader": name, "wallet": acct["adresse"], "aktion": "KAUF", "symbol": pos["symbol"],
             "mint": t["mint"], "runde": acct["runde"], "verzoegerung_s": f"{delay:.1f}" if delay is not None else "",
             "unser_sol": f"{BUY_SOL:.4f}", "unsere_tokens": f"{tokens:.6f}", "unser_preis_sol": f"{our_price:.12g}",
             "unsere_gebuehr_sol": f"{FEE_SOL:.4f}", "preisabstand_pct": f"{gap:+.2f}" if gap is not None else "",
             "trader_anteil": "", "hinweis": f"Kauf Nr. {pos['kaeufe']}" + (" (USDC)" if t["quote_asset"] == "USDC" else ""),
             "pruefungen": json.dumps(checks, ensure_ascii=False), **trader_fields(t, sig)})
    verdict = "alle Pruefungen bestanden" if all(
        checks.get(k) == "bestanden" for k in ("schnellpruefung", "sicherheit", "bundle_dev")) else \
        f"Pruefungen: {checks.get('schnellpruefung', '?')}, {checks.get('bundle_dev', '?')}"
    notify(f"🎯 {name}: Kauf {pos['symbol']}" + (f" (Nachkauf {pos['kaeufe']})" if pos["kaeufe"] > 1 else ""), [
        f"**Trader:** {t['sol']:.3f} SOL zu {t['price_sol']:.3g} SOL/Token | Prio {t['fee_prio']:.5f}, "
        f"Jito {t['jito']:.5f}, sonstige {t['other']:.5f} SOL",
        f"**Wir:** {BUY_SOL} SOL zu {our_price:.3g} SOL/Token, {delay:.1f} s spaeter" if delay is not None else
        f"**Wir:** {BUY_SOL} SOL zu {our_price:.3g} SOL/Token",
        f"**Preisabstand:** {gap:+.1f}%" if gap is not None else "", f"**{verdict}** (nur Beobachtung)",
        account_line(acct), f"https://jup.ag/tokens/{t['mint']}"], 0x3B82F6)


def close_if_empty(name, acct, pos, reason, now):
    if pos["tokens_raw"] > 0:
        return
    pnl = pos["proceeds_sol"] - pos["invested_sol"] - pos["fees_sol"]
    trader_pnl = pos["trader_erhalten_sol"] - pos["trader_ausgegeben_sol"]
    rec = dict(pos, pnl_sol=round(pnl, 6), pnl_pct=round(pnl / pos["invested_sol"] * 100, 2),
               grund=reason, geschlossen=datetime.now(timezone.utc).isoformat(),
               haltedauer_h=round((now - pos["opened"]) / 3600, 2),
               trader_pnl_sol=round(trader_pnl, 6),
               trader_pnl_pct=round(trader_pnl / pos["trader_ausgegeben_sol"] * 100, 2)
               if pos["trader_ausgegeben_sol"] else None)
    acct["geschlossen"].append(rec)
    del acct["positionen"][pos["mint"]]
    return rec


def copy_sell(name, acct, t, sig, now, reason="VERKAUF"):
    pos = acct["positionen"].get(t["mint"])
    if not pos:
        count("skipped", "verkauf_ohne_position")
        return
    fraction = 1.0 if reason == "UEBERWEISUNG" else min(1.0, abs(t["delta_raw"]) / t["pre_raw"]) \
        if t["pre_raw"] > 0 else 1.0
    sell_raw = pos["tokens_raw"] if fraction >= 0.999 else int(pos["tokens_raw"] * fraction)
    out = quote_out(t["mint"], core.WSOL_MINT, sell_raw) if sell_raw > 0 else 0
    our_time = time.time()
    proceeds = out / 1e9
    delay = our_time - t["block_time"] if t.get("block_time") else None
    if delay is not None:
        STATS["delays"].append(delay)
    pos["tokens_raw"] -= sell_raw
    pos["proceeds_sol"] += proceeds
    pos["fees_sol"] += FEE_SOL
    pos["verkaeufe"] += 1
    if reason != "UEBERWEISUNG":
        pos["trader_erhalten_sol"] += t["sol"]
    acct["bankroll_sol"] += proceeds - FEE_SOL
    count("trades", reason)
    tokens = sell_raw / 10 ** pos["decimals"]
    our_price = proceeds / tokens if tokens else None
    gap = (our_price / t["price_sol"] - 1) * 100 if our_price and t.get("price_sol") else None
    rec = close_if_empty(name, acct, pos, reason, now)
    journal({"zeit": now_str(), "trader": name, "wallet": acct["adresse"], "aktion": reason, "symbol": pos["symbol"],
             "mint": t["mint"], "runde": pos["runde"], "verzoegerung_s": f"{delay:.1f}" if delay is not None else "",
             "trader_anteil": f"{fraction:.4f}", "unser_sol": f"{proceeds:.6f}", "unsere_tokens": f"{tokens:.6f}",
             "unser_preis_sol": f"{our_price:.12g}" if our_price else "", "unsere_gebuehr_sol": f"{FEE_SOL:.4f}",
             "preisabstand_pct": f"{gap:+.2f}" if gap is not None else "",
             "pnl_sol": f"{rec['pnl_sol']:+.6f}" if rec else "", "pnl_pct": f"{rec['pnl_pct']:+.2f}" if rec else "",
             "hinweis": "Position geschlossen" if rec else f"Teilverkauf {fraction:.0%}"
                        + ("; keine Quote, Wert 0" if sell_raw > 0 and out <= 0 else ""),
             **trader_fields(t, sig)})
    lines = [f"**Trader verkauft:** {fraction:.0%} seines Bestands" + (f" zu {t['price_sol']:.3g} SOL/Token"
             if t.get("price_sol") else " (Ueberweisung, kein Verkauf)"),
             f"**Wir:** {proceeds:.4f} SOL" + (f" zu {our_price:.3g} SOL/Token" if our_price else "")
             + (f", {delay:.1f} s spaeter" if delay is not None else "")]
    if rec:
        lines.append(f"**Ergebnis:** {rec['pnl_sol']:+.4f} SOL ({rec['pnl_pct']:+.1f}%) | Trader auf diesen Coin: "
                     + (f"{rec['trader_pnl_sol']:+.3f} SOL ({rec['trader_pnl_pct']:+.0f}%)" if rec["trader_pnl_pct"]
                        is not None else "?"))
    lines.append(account_line(acct))
    good = rec is None or rec["pnl_sol"] > 0
    notify(f"{'🟢' if good else '🔴'} {name}: {'Verkauf' if reason == 'VERKAUF' else 'Ueberweisung'} "
           f"{pos['symbol']}" + ("" if rec else f" ({fraction:.0%})"), lines, 0x10B981 if good else 0xEF4444)


def handle_signature(name, acct, sig, sol_usd):
    key = (name, sig)
    if key in _seen:
        return
    _seen.add(key)
    tx = fetch_tx(sig)
    if tx is None:
        count("skipped", "transaktion_nicht_abrufbar")
        return
    try:
        t = parse_trade(tx, acct["adresse"], sol_usd)
    except Exception as err:
        STATS["parse_errors"] += 1
        print(f"[COPY] Auswertung {sig[:12]} fehlgeschlagen: {str(err)[:120]}")
        return
    if not t:
        return
    now = time.time()
    if t["kind"] == "KAUF":
        copy_buy(name, acct, t, sig, now)
    else:
        copy_sell(name, acct, t, sig, now, t["kind"])


# ================================================================ Bereinigung am Schichtende

def cleanup(data):
    """Positionen mit hoechstens 1 % Restwert verkaufen (so viel, wie Jupiter noch bietet)."""
    closed = 0
    open_mints = {m for a in data["wallets"].values() for m in a["positionen"]}
    prices = {}
    for chunk in [list(open_mints)[i:i + 100] for i in range(0, len(open_mints), 100)]:
        for tok in jup(f"/tokens/v2/search?query={','.join(chunk)}") or []:
            prices[tok.get("id")] = core.as_float(tok.get("usdPrice"))
    sol_usd = core.sol_price() or 0
    now = time.time()
    for name, acct in data["wallets"].items():
        for mint, pos in list(acct["positionen"].items()):
            est = pos["tokens_raw"] / 10 ** pos["decimals"] * prices.get(mint, 0) / sol_usd if sol_usd else 0
            if est > pos["invested_sol"] * 0.1:              # grob vorsortieren, genau prueft die Quote
                continue
            out = quote_out(mint, core.WSOL_MINT, pos["tokens_raw"]) / 1e9
            if out > pos["invested_sol"] * CLEANUP_MAX_VALUE_PCT / 100:
                continue
            pos["proceeds_sol"] += out
            pos["fees_sol"] += FEE_SOL if out > 0 else 0
            acct["bankroll_sol"] += out - (FEE_SOL if out > 0 else 0)
            pos["tokens_raw"] = 0
            rec = close_if_empty(name, acct, pos, "BEREINIGT (-99 %)", now)
            journal({"zeit": now_str(), "trader": name, "wallet": acct["adresse"], "aktion": "BEREINIGT",
                     "symbol": pos["symbol"], "mint": mint, "runde": pos["runde"], "unser_sol": f"{out:.6f}",
                     "pnl_sol": f"{rec['pnl_sol']:+.6f}", "pnl_pct": f"{rec['pnl_pct']:+.2f}",
                     "hinweis": "Schichtende: Restwert hoechstens 1 %"})
            closed += 1
    return closed


# ================================================================ Git (nur die eigenen Dateien)

def git_push():
    if not os.path.exists(COPY_DIR):
        return
    g = core._git
    g("config", "user.name", "github-actions[bot]")
    g("config", "user.email", "github-actions[bot]@users.noreply.github.com")
    for _ in range(3):
        if g("fetch", "-q", "origin", "main").returncode != 0:
            continue
        g("reset", "-q", "origin/main")          # Index = neuester Stand, eigene Dateien bleiben
        g("add", COPY_DIR)
        if g("diff", "--cached", "--quiet").returncode == 0:
            return
        g("commit", "-q", "-m", "COPY Update [skip ci]")
        if g("push", "-q", "origin", "HEAD:main").returncode == 0:
            STATS["git_ok"] += 1
            return
    STATS["git_fail"] += 1


# ================================================================ WebSocket

def connect(wallets):
    ws = websocket.create_connection(WS_URL, timeout=20)
    for idx, (name, addr) in enumerate(wallets, 1):
        ws.send(json.dumps({"jsonrpc": "2.0", "id": idx, "method": "logsSubscribe",
                            "params": [{"mentions": [addr]}, {"commitment": "confirmed"}]}))
    subs, early, pending, deadline = {}, [], set(range(1, len(wallets) + 1)), time.time() + 20
    while pending and time.time() < deadline:
        msg = json.loads(ws.recv())
        if msg.get("id") in pending:
            pending.discard(msg["id"])
            if "result" in msg:
                subs[msg["result"]] = wallets[msg["id"] - 1]
            else:
                print(f"[COPY] Anmeldung fuer {wallets[msg['id'] - 1][0]} abgelehnt: {str(msg.get('error'))[:120]}")
        elif msg.get("method") == "logsNotification":
            early.append(msg)
    ws.settimeout(1.0)
    return ws, subs, early


def notification_sig(msg):
    value = ((msg.get("params") or {}).get("result") or {}).get("value") or {}
    if value.get("err") is not None:
        return None
    return value.get("signature")


def run(probe=False):
    wallets = load_wallets()
    if probe:
        return run_probe(wallets)
    signal.signal(signal.SIGTERM, _on_signal)
    signal.signal(signal.SIGINT, _on_signal)
    core.git_sync_start()
    data = load_accounts(wallets)
    save_accounts(data)
    started, sol_usd = time.time(), core.sol_price()
    notify("🟢 Copy-Schicht gestartet", [f"{len(wallets)} Wallets, je eigenes Konto mit {START_SOL:.0f} SOL."], 0x10B981)
    ws, subs, last_ping, last_push, last_sol, normal_end = None, {}, time.time(), time.time(), time.time(), False
    try:
        while time.time() - started < SHIFT_SECONDS:
            if ws is None:
                try:
                    ws, subs, early = connect(wallets)
                    print(f"[COPY] verbunden, {len(subs)} von {len(wallets)} Wallets angemeldet")
                    for msg in early:
                        process_message(msg, subs, data, sol_usd)
                except Exception as err:
                    STATS["reconnects"] += 1
                    print(f"[COPY] Verbindung fehlgeschlagen: {str(err)[:120]}")
                    ws = None
                    time.sleep(min(30, 3 * STATS["reconnects"]))
                    continue
            try:
                msg = json.loads(ws.recv())
                process_message(msg, subs, data, sol_usd)
            except websocket.WebSocketTimeoutException:
                pass
            except (websocket.WebSocketConnectionClosedException, ConnectionError, OSError) as err:
                STATS["reconnects"] += 1
                print(f"[COPY] Verbindung verloren: {str(err)[:100]}")
                ws = None
                continue
            now = time.time()
            if now - last_ping > PING_EVERY and ws is not None:
                try:
                    ws.ping()
                except Exception:
                    ws = None
                last_ping = now
            if now - last_sol > 300:
                sol_usd, last_sol = core.sol_price() or sol_usd, now
            if now - last_push > PUSH_EVERY:
                save_accounts(data)
                git_push()
                last_push = now
        normal_end = True
    except Interrupted:
        print("[COPY] Abbruch-Signal erhalten")
    finally:
        cleaned = cleanup(data) if normal_end else 0
        save_accounts(data)
        git_push()
        try:
            if ws is not None:
                ws.close()
        except Exception:
            pass
        summary(data, time.time() - started, cleaned, normal_end)


def process_message(msg, subs, data, sol_usd):
    if msg.get("method") != "logsNotification":
        return
    STATS["notifications"] += 1
    sub = (msg.get("params") or {}).get("subscription")
    sig = notification_sig(msg)
    if sub not in subs or not sig:
        return
    name, _ = subs[sub]
    try:
        handle_signature(name, data["wallets"][name], sig, sol_usd)
    except Exception as err:                     # ein fehlerhafter Trade darf den Bot nicht stoppen
        STATS["errors"] += 1
        STATS["last_error"] = str(err)[:200]
        print(f"[COPY] Fehler bei {name} {sig[:12]}: {str(err)[:150]}")


def summary(data, dur, cleaned, normal_end):
    lines = [f"**Dauer:** {dur / 3600:.2f} h | **Meldungen:** {STATS['notifications']} | "
             f"**Trades:** {STATS['trades'] or 0}"]
    if STATS["skipped"]:
        lines.append(f"**Ausgelassen:** {STATS['skipped']}")
    if STATS["delays"]:
        d = sorted(STATS["delays"])
        lines.append(f"**Verzoegerung nach dem Trader:** Median {d[len(d) // 2]:.1f} s, "
                     f"90 % unter {d[int(len(d) * 0.9)]:.1f} s")
    lines.append(f"**Bereinigt (-99 %):** {cleaned}")
    rows = []
    for name, a in data["wallets"].items():
        value = a["bankroll_sol"] + sum(p["invested_sol"] for p in a["positionen"].values())
        realized = sum(c["pnl_sol"] for c in a["geschlossen"])
        rows.append((realized, f"{name}: frei {a['bankroll_sol']:.2f} SOL, {len(a['positionen'])} offen, "
                               f"{len(a['geschlossen'])} geschlossen, realisiert {realized:+.3f} SOL, Runde {a['runde']}"))
    lines.append("**Wallets (realisiert):**\n" + "\n".join(r for _, r in sorted(rows, reverse=True)))
    lines.append(f"**Verbindungsabbrueche:** {STATS['reconnects']} | **Auswertungsfehler:** "
                 f"{STATS['parse_errors'] + STATS['errors']} | **Jupiter-Bremse (429):** {STATS['jup_429']} | "
                 f"**GitHub-Sicherung:** {STATS['git_ok']} ok / {STATS['git_fail']} Fehler")
    ok = normal_end and not STATS["errors"] and not STATS["git_fail"]
    notify("🔴 Copy-Schicht beendet" if ok else "⚠️ Copy-Schicht beendet (pruefen)", lines, 0x64748B)


def now_str():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


# ================================================================ Probelauf

def run_probe(wallets):
    print(f"[COPY PROBE] {len(wallets)} Wallets aus {WALLET_FILE} gelesen")
    print(f"[COPY PROBE] Discord-Kanal Copy: {'gesetzt' if DISCORD_WEBHOOK_COPY else 'FEHLT (Meldungen gingen in den Hauptkanal)'}")
    sol_usd = core.sol_price()
    print(f"[COPY PROBE] SOL-Kurs: {sol_usd}")
    kinds = {}
    for name, addr in wallets:
        sigs = core.rpc("getSignaturesForAddress", [addr, {"limit": 6}]) or []
        parsed = []
        for s in sigs:
            if s.get("err") is not None:
                continue
            t = parse_trade(fetch_tx(s["signature"]), addr, sol_usd)
            if t:
                kinds[t["kind"]] = kinds.get(t["kind"], 0) + 1
                parsed.append(f"{t['kind']} {t['mint'][:6]} {t['sol']:.3f} SOL"
                              + (f" @ {t['price_sol']:.3g}" if t.get("price_sol") else "")
                              + f" (Prio {t['fee_prio']:.5f}, Jito {t['jito']:.5f}, sonst. {t['other']:.5f})")
        last = datetime.fromtimestamp(sigs[0]["blockTime"], timezone.utc).strftime("%d.%m. %H:%M") \
            if sigs and sigs[0].get("blockTime") else "?"
        print(f"  {name:<10} letzte Aktivitaet {last} UTC | erkannt: {parsed[:3] or 'keine Trades in den letzten 6 Tx'}")
    print(f"[COPY PROBE] Erkannte Trades gesamt: {kinds}")
    try:
        ws, subs, early = connect(wallets)
        print(f"[COPY PROBE] WebSocket verbunden, {len(subs)} von {len(wallets)} Wallets angemeldet")
        got, t_end = len(early), time.time() + 90
        while time.time() < t_end:
            try:
                msg = json.loads(ws.recv())
            except websocket.WebSocketTimeoutException:
                continue
            if msg.get("method") == "logsNotification":
                got += 1
                sub = msg["params"]["subscription"]
                sig = notification_sig(msg)
                if sub in subs and sig and got <= 5:
                    name, addr = subs[sub]
                    t = parse_trade(fetch_tx(sig), addr, sol_usd)
                    print(f"  live: {name} -> {t['kind'] + ' ' + t['mint'][:6] if t else 'keine Handelsaktion'}"
                          + (f", Block vor {time.time() - t['block_time']:.1f} s" if t and t.get('block_time') else ""))
        ws.close()
        print(f"[COPY PROBE] Live-Meldungen in 90 s: {got}")
    except Exception as err:
        print(f"[COPY PROBE] WebSocket FEHLER: {str(err)[:200]}")
    raw = quote_out(core.WSOL_MINT, USDC_MINT, int(0.01 * 1e9))
    print(f"[COPY PROBE] Jupiter-Quote 0,01 SOL -> USDC: {raw / 1e6 if raw else 'FEHLER'}")
    print("[COPY PROBE] fertig. Diese Ausgabe bitte an Claude schicken.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--probe", action="store_true")
    run(probe=ap.parse_args().probe)
