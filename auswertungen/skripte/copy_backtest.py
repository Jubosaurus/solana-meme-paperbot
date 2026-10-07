"""ACHTUNG: Prototyp. Stand 08.10.: Regel-Nachbau (Variante A, echte Preisabstaende) trifft 4DOV fast genau
(76 Abschluesse, +1,170 gegen echt +1,177 SOL). Das Preismodell (B bis E, Preisabstand per Median/Zufall) ist
NICHT verlaesslich: B liegt 5 SOL unter A. Nur Variante A als Gegenprobe benutzen.

Copy-Backtest-Prototyp (Schritt 4 des Backtest-Plans, 07.10.2026). Nur Auswertung, kein Handel.

Spielt eine Copy-Wallet nach, als haetten wir sie kopiert (Regeln wie copy_bot.py: 0,2 SOL je Trader-Kauf
ab 0,1 SOL, Preisgrenze +-15 %, Teilverkaeufe gesammelt ab 20 %, neue Runde mit 10 SOL, Gebuehr = Netzwerk-
gebuehr des Traders) und vergleicht mit unseren echten Copy-Ergebnissen auf denselben Trades.

    python auswertungen/skripte/copy_backtest.py holen   --wallet 4DOV [--tage 30] [--max-credits 30000]
    python auswertungen/skripte/copy_backtest.py rechnen --wallet 4DOV

Rohdaten (Helius-Antworten, Trader-Trades) liegen NUR lokal ausserhalb des Repos (Standard
C:\\Users\\admin\\paperbot-daten\\copy_backtest\\<wallet>, aenderbar mit PAPERBOT_DATEN). Der Helius-Schluessel
kommt aus der Umgebung (HELIUS_API_KEY oder Windows-Benutzervariable) und wird nie ausgegeben.
Credits: 1 je getSignaturesForAddress- bzw. getTransaction-Aufruf (Helius-Doku, wie credits_used im Copy-Bot);
der Zaehler steht in zaehler.json und stoppt hart vor --max-credits.
"""
import argparse
import calendar
import csv
import gzip
import json
import os
import random
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)
import copy_bot as cb  # noqa: E402

DATEN_BASIS = Path(os.environ.get("PAPERBOT_DATEN", r"C:\Users\admin\paperbot-daten")) / "copy_backtest"
HELIUS_URL = "https://mainnet.helius-rpc.com/?api-key="
PAUSE_S = 0.25                       # hoechstens ~4 Abrufe/s (die Bots nutzen denselben Schluessel mit)
MC_LAEUFE = 200                      # Zufallslaeufe fuer die Preisstreuung


# ================================================================ Hilfen

def daten_ordner(name):
    d = DATEN_BASIS / name
    if ROOT in d.resolve().parents or d.resolve() == ROOT:
        raise SystemExit("Datenordner liegt im Repository - abgebrochen (Rohdaten nur lokal).")
    (d / "tx").mkdir(parents=True, exist_ok=True)
    return d


def wallet_adresse(name):
    konten = json.load(open(cb.ACCOUNTS_FILE, encoding="utf-8"))["wallets"]
    if name not in konten:
        raise SystemExit(f"Wallet {name} nicht in {cb.ACCOUNTS_FILE}")
    return konten[name]["adresse"], konten[name]


def helius_schluessel():
    key = (os.environ.get("HELIUS_API_KEY") or "").strip()
    if not key and os.name == "nt":
        import winreg
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as k:
                key = str(winreg.QueryValueEx(k, "HELIUS_API_KEY")[0]).strip()
        except OSError:
            key = ""
    if not key:
        raise SystemExit("Kein Helius-Schluessel gefunden (HELIUS_API_KEY). Nichts abgerufen.")
    return key


class Helius:
    def __init__(self, key, zaehler_pfad, max_credits):
        import requests
        self.session, self.url = requests.Session(), HELIUS_URL + key
        self.pfad, self.max = zaehler_pfad, max_credits
        self.z = json.load(open(zaehler_pfad)) if zaehler_pfad.exists() else {"credits": 0, "aufrufe": {}, "fehler": 0}
        self.letzter = 0.0

    def frei(self):
        return self.max - self.z["credits"]

    def rpc(self, method, params):
        if self.z["credits"] + 1 > self.max:
            raise RuntimeError("Credit-Grenze erreicht")
        for versuch in range(4):
            warte = PAUSE_S - (time.time() - self.letzter)
            if warte > 0:
                time.sleep(warte)
            self.letzter = time.time()
            self.z["credits"] += 1                       # auch fehlgeschlagene Aufrufe zaehlen (vorsichtig)
            self.z["aufrufe"][method] = self.z["aufrufe"].get(method, 0) + 1
            try:
                res = self.session.post(self.url, json={"jsonrpc": "2.0", "id": 1, "method": method,
                                                        "params": params}, timeout=30)
            except Exception as err:                      # Schluessel steckt in der URL: Text nie ausgeben
                self.z["fehler"] += 1
                print(f"[HELIUS] {method}: Verbindungsfehler ({type(err).__name__})")
                time.sleep(2 * (versuch + 1))
                continue
            if res.status_code == 429:
                time.sleep(2 * (versuch + 1))
                continue
            if res.status_code != 200:
                self.z["fehler"] += 1
                print(f"[HELIUS] {method}: HTTP {res.status_code}")
                return None
            try:
                return res.json().get("result")
            except ValueError:
                self.z["fehler"] += 1
                return None
        return None

    def speichern(self):
        json.dump(self.z, open(self.pfad, "w"), indent=1)


# ================================================================ Holen (braucht Helius)

def holen(name, tage, max_credits):
    d = daten_ordner(name)
    adresse, _ = wallet_adresse(name)
    h = Helius(helius_schluessel(), d / "zaehler.json", max_credits)
    sig_pfad = d / "signaturen.jsonl"
    sigs = [json.loads(z) for z in open(sig_pfad, encoding="utf-8")] if sig_pfad.exists() else []
    grenze = time.time() - tage * 86400
    print(f"[HOLEN] {name}: bisher {len(sigs)} Signaturen, {h.z['credits']} Credits verbraucht, Grenze {max_credits}")
    try:
        if not sigs or min(s.get("blockTime") or 0 for s in sigs) > grenze:
            before = sigs[-1]["signature"] if sigs else None
            while True:
                opt = {"limit": 1000}
                if before:
                    opt["before"] = before
                seite = h.rpc("getSignaturesForAddress", [adresse, opt]) or []
                if not seite:
                    break
                sigs += [{"signature": s["signature"], "slot": s.get("slot"), "blockTime": s.get("blockTime"),
                          "fehlgeschlagen": s.get("err") is not None} for s in seite]
                before = seite[-1]["signature"]
                if (seite[-1].get("blockTime") or 0) < grenze or len(seite) < 1000:
                    break
            with open(sig_pfad, "w", encoding="utf-8") as f:
                for s in sigs:
                    f.write(json.dumps(s) + "\n")
        offen = [s for s in sigs if not s["fehlgeschlagen"] and (s.get("blockTime") or 0) >= grenze
                 and not (d / "tx" / f"{s['signature']}.json.gz").exists()]
        print(f"[HOLEN] {len(sigs)} Signaturen, {len(offen)} Transaktionen noch zu laden "
              f"(frei: {h.frei()} Credits)")
        for i, s in enumerate(offen, 1):
            tx = h.rpc("getTransaction", [s["signature"], {"encoding": "jsonParsed", "commitment": "confirmed",
                                                          "maxSupportedTransactionVersion": 1}])
            if tx:
                with gzip.open(d / "tx" / f"{s['signature']}.json.gz", "wt", encoding="utf-8") as f:
                    json.dump(tx, f)
            if i % 200 == 0:
                h.speichern()
                print(f"[HOLEN] {i}/{len(offen)} geladen, {h.z['credits']} Credits")
    except RuntimeError as err:
        print(f"[HOLEN] gestoppt: {err}")
    finally:
        h.speichern()
    print(f"[HOLEN] fertig: {h.z['credits']} Credits verbraucht ({h.z['aufrufe']}), Fehler {h.z['fehler']}")


# ================================================================ Unsere echten Daten

def echte_daten(adresse):
    zeilen = [r for r in csv.DictReader(open(cb.JOURNAL_FILE, encoding="utf-8")) if r["wallet"] == adresse]
    je_sig = {}
    for r in zeilen:
        if r.get("trader_signatur"):
            je_sig.setdefault(r["trader_signatur"], []).append(r)
    return zeilen, je_sig


def utc_ts(text):
    """Journal-Zeit (UTC-Text) -> Unix-Zeit. Nicht mktime verwenden: das rechnet im Sommer 1 h falsch."""
    return calendar.timegm(time.strptime(text, "%Y-%m-%d %H:%M:%S"))


def zahl(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def abstaende():
    """Echte Preisabstaende aller Wallets: Kauf (inkl. geblockter Schattenkaeufe) und Verkauf, in %."""
    kauf, verkauf = [], []
    for r in csv.DictReader(open(cb.JOURNAL_FILE, encoding="utf-8")):
        g = zahl(r.get("preisabstand_pct"))
        if g is None:
            continue
        if r["aktion"] in ("KAUF", "SCHATTEN_KAUF"):
            kauf.append(g)
        elif r["aktion"] == "VERKAUF" and abs(g) <= 100:      # >100 % = Trader-Preis (fast) null: Ausreisser bis 5 Mio. %
            verkauf.append(g)
    return kauf, verkauf


# ================================================================ Trader-Trades aus den lokalen Rohdaten

def sol_usd_schaetzen(name, adresse):
    """Der Trader handelt gegen USDC. Umrechnung wie im Live-Bot, aber hier aus den eigenen Live-Zeilen
    (USDC-Betrag der Transaktion / trader_sol) geeicht; Median ueber bis zu 200 Kaeufe."""
    d = daten_ordner(name)
    zeilen, _ = echte_daten(adresse)
    ratios = []
    for r in zeilen:
        if r["aktion"] != "KAUF" or not r.get("trader_signatur") or not zahl(r.get("trader_sol")):
            continue
        p = d / "tx" / f"{r['trader_signatur']}.json.gz"
        if not p.exists():
            continue
        with gzip.open(p, "rt", encoding="utf-8") as f:
            meta = json.load(f).get("meta") or {}
        usdc = 0
        for e, vz in ((meta.get("postTokenBalances"), 1), (meta.get("preTokenBalances"), -1)):
            for b in e or []:
                if b.get("owner") == adresse and b.get("mint") == cb.USDC_MINT:
                    usdc += vz * int((b.get("uiTokenAmount") or {}).get("amount") or 0)
        if usdc:
            ratios.append(abs(usdc) / 1e6 / float(r["trader_sol"]))
        if len(ratios) >= 200:
            break
    return statistics.median(ratios) if ratios else None


def trader_trades(name, adresse):
    d = daten_ordner(name)
    sol_usd = sol_usd_schaetzen(name, adresse)
    print(f"[RECHNEN] SOL/USD fuer USDC-Handel (aus Live-Zeilen geeicht): {sol_usd}")
    trades = []
    for p in sorted((d / "tx").glob("*.json.gz")):
        with gzip.open(p, "rt", encoding="utf-8") as f:
            tx = json.load(f)
        t = cb.parse_trade(tx, adresse, sol_usd)
        if t:
            t["sig"] = p.name[:-len(".json.gz")]
            t["slot"] = tx.get("slot") or 0
            trades.append(t)
    trades.sort(key=lambda t: (t["slot"], t.get("block_time") or 0, t["sig"]))
    return trades


# ================================================================ Nachbau der Copy-Regeln

class Konto:
    def __init__(self):
        self.bank, self.runde = cb.START_SOL, 1
        self.pos, self.zu, self.n = {}, [], {"kauf": 0, "geblockt": 0, "unter_0_1": 0, "verkauf": 0,
                                             "gemerkt": 0, "ohne_position": 0, "runden": 1}

    def kauf(self, t, gap_pct):
        if t["sol"] < cb.MIN_TRADER_BUY_SOL:
            self.n["unter_0_1"] += 1
            return
        fee = cb.trade_fee(t)
        if self.bank < cb.BUY_SOL + fee:
            self.runde += 1
            self.n["runden"] += 1
            self.bank = cb.START_SOL
        if gap_pct is None or abs(gap_pct) > cb.MAX_PRICE_GAP_PCT:
            self.n["geblockt"] += 1
            return
        tokens = cb.BUY_SOL / (t["price_sol"] * (1 + gap_pct / 100))
        p = self.pos.setdefault(t["mint"], {"mint": t["mint"], "tokens": 0.0, "invest": 0.0, "gebuehr": 0.0,
                                            "erloes": 0.0, "behalten": 1.0, "runde": self.runde, "kaeufe": 0})
        p["tokens"] += tokens
        p["invest"] += cb.BUY_SOL
        p["gebuehr"] += fee
        p["kaeufe"] += 1
        self.bank -= cb.BUY_SOL + fee
        self.n["kauf"] += 1

    def verkauf(self, t, gap_pct, ueberweisung=False):
        p = self.pos.get(t["mint"])
        if not p:
            self.n["ohne_position"] += 1
            return
        anteil = 1.0 if ueberweisung else (min(1.0, abs(t["delta_raw"]) / t["pre_raw"]) if t["pre_raw"] > 0 else 1.0)
        p["behalten"] *= (1 - anteil)
        weg = 1 - p["behalten"]
        komplett = ueberweisung or anteil >= 0.999 or p["behalten"] < 0.001
        if not komplett and weg < cb.SELL_BATCH_MIN:
            self.n["gemerkt"] += 1
            return
        menge = p["tokens"] if komplett else p["tokens"] * weg
        preis = 0.0 if ueberweisung or not t.get("price_sol") else t["price_sol"] * (1 + (gap_pct or 0) / 100)
        erloes = menge * preis
        fee = cb.trade_fee(t)
        p["tokens"] -= menge
        p["erloes"] += erloes
        p["gebuehr"] += fee
        p["behalten"] = 1.0
        self.bank += erloes - fee
        self.n["verkauf"] += 1
        if komplett or p["tokens"] <= 1e-12:
            p["pnl"] = p["erloes"] - p["invest"] - p["gebuehr"]
            self.zu.append(p)
            del self.pos[t["mint"]]

    def bereinigen(self, t):
        """Schichtende-Bereinigung (Restwert <= 1 %): Restposition wird zum Jupiter-Restwert t["sol"] verkauft."""
        p = self.pos.get(t["mint"])
        if not p:
            return
        fee = cb.DEFAULT_FEE_SOL if t["sol"] > 0 else 0.0
        p["erloes"] += t["sol"]
        p["gebuehr"] += fee
        self.bank += t["sol"] - fee
        p["pnl"] = p["erloes"] - p["invest"] - p["gebuehr"]
        p["grund"] = "BEREINIGT"
        self.zu.append(p)
        del self.pos[t["mint"]]
        self.n["bereinigt"] = self.n.get("bereinigt", 0) + 1

    def ergebnis(self):
        zu = sum(p["pnl"] for p in self.zu)
        return {"geschlossen": len(self.zu), "pnl_geschlossen": round(zu, 4), "offen": len(self.pos),
                "offen_einsatz": round(sum(p["invest"] for p in self.pos.values()), 4), **self.n}


def simulieren(trades, gap_kauf, gap_verkauf):
    k = Konto()
    for t in trades:
        if t["kind"] == "KAUF":
            k.kauf(t, gap_kauf(t))
        elif t["kind"] == "VERKAUF":
            k.verkauf(t, gap_verkauf(t))
        elif t["kind"] == "UEBERWEISUNG":
            k.verkauf(t, None, ueberweisung=True)
        elif t["kind"] == "BEREINIGT":
            k.bereinigen(t)
    return k


# ================================================================ Rechnen (offline)

GESEHEN = {"KAUF", "SCHATTEN_KAUF", "AUSGELASSEN", "VERKAUF", "VERKAUF_GEMERKT", "SCHATTEN_VERKAUF",
           "UEBERWEISUNG", "BEREINIGT"}


def rechnen(name):
    adresse, konto = wallet_adresse(name)
    zeilen, je_sig = echte_daten(adresse)
    trades = trader_trades(name, adresse)
    if not trades:
        raise SystemExit("Keine lokalen Trader-Trades. Zuerst 'holen'.")
    # Helius-Daten enden beim Abruf: alles Spaetere (Journal, echte Abschluesse) bleibt aussen vor
    daten_ende = max(s.get("blockTime") or 0 for s in (json.loads(z) for z in
                     open(daten_ordner(name) / "signaturen.jsonl", encoding="utf-8")))
    zeilen = [r for r in zeilen if utc_ts(r["zeit"]) <= daten_ende]
    je_sig = {}
    for r in zeilen:
        if r.get("trader_signatur"):
            je_sig.setdefault(r["trader_signatur"], []).append(r)
    kauf_abst, verk_abst = abstaende()
    med_k, med_v = statistics.median(kauf_abst), statistics.median(verk_abst)
    start = min(r["zeit"] for r in zeilen)
    start_ts = utc_ts(start)
    ende = max(r["zeit"] for r in zeilen)
    ende_ts = utc_ts(ende)
    im_fenster = [t for t in trades if start_ts - 120 <= (t.get("block_time") or 0) <= ende_ts]   # Trader-Trade liegt vor unserer Journalzeile
    vorher = [t for t in trades if (t.get("block_time") or 0) < start_ts - 120]

    def echte_luecke(t):
        rows = je_sig.get(t["sig"], [])
        for r in rows:
            g = zahl(r.get("preisabstand_pct"))
            if r["aktion"] in ("KAUF", "SCHATTEN_KAUF", "VERKAUF") and g is not None:
                return g
        return None

    def gesehen(t):
        return any(r["aktion"] in GESEHEN for r in je_sig.get(t["sig"], []))

    def nur_live_kaeufe(t):
        """Live nicht gekaufte Trader-Kaeufe (keine Quote, verpasst, kein Geld) auch im Nachbau auslassen."""
        aktionen = {r["aktion"] for r in je_sig.get(t["sig"], [])}
        return t["kind"] != "KAUF" or bool(aktionen & {"KAUF", "SCHATTEN_KAUF"}) or t["sol"] < cb.MIN_TRADER_BUY_SOL

    bereinigt = [{"kind": "BEREINIGT", "mint": r["mint"], "sol": zahl(r["unser_sol"]) or 0.0,
                  "block_time": utc_ts(r["zeit"]), "sig": ""} for r in zeilen if r["aktion"] == "BEREINIGT"]

    def mit_bereinigung(liste):
        return sorted(liste + bereinigt, key=lambda t: t.get("block_time") or 0)

    varianten = {}
    # A: nur die Trades, die unser Bot live gesehen hat, mit echten Preisabstaenden -> prueft den Regel-Nachbau
    a = mit_bereinigung([t for t in im_fenster if gesehen(t) and nur_live_kaeufe(t)])
    varianten["A_live_trades_echte_preise"] = simulieren(
        a, lambda t: echte_luecke(t) if echte_luecke(t) is not None else med_k,
        lambda t: echte_luecke(t) if echte_luecke(t) is not None else med_v).ergebnis()
    # B: dieselben Trades, aber Preis aus dem Modell (Median) -> prueft das Preismodell
    varianten["B_live_trades_median"] = simulieren(a, lambda t: med_k, lambda t: med_v).ergebnis()
    # C: alle Trader-Trades im Fenster laut Helius, Median -> zeigt, was Luecken/Ausfaelle live kosteten
    varianten["C_alle_trades_median"] = simulieren(im_fenster, lambda t: med_k, lambda t: med_v).ergebnis()
    # D: wie C, Preis exakt wie der Trader (obere Schranke)
    varianten["D_alle_trades_traderpreis"] = simulieren(im_fenster, lambda t: 0.0, lambda t: 0.0).ergebnis()
    # E: ganzer geladener Zeitraum (bis 30 Tage), Zufall aus den echten Abstaenden
    rng = random.Random(7)
    mc = []
    for _ in range(MC_LAEUFE):
        mc.append(simulieren(trades, lambda t: rng.choice(kauf_abst), lambda t: rng.choice(verk_abst)).ergebnis())
    pnl_mc = sorted(m["pnl_geschlossen"] for m in mc)
    varianten["E_30_tage_median"] = simulieren(trades, lambda t: med_k, lambda t: med_v).ergebnis()
    varianten["E_30_tage_zufall"] = {"laeufe": MC_LAEUFE, "pnl_p10": pnl_mc[len(pnl_mc) // 10],
                                     "pnl_median": pnl_mc[len(pnl_mc) // 2], "pnl_p90": pnl_mc[len(pnl_mc) * 9 // 10]}

    def _iso_ts(text):
        from datetime import datetime
        return datetime.fromisoformat(text).timestamp()
    echt_zu = [g for g in konto["geschlossen"] if _iso_ts(g["geschlossen"]) <= daten_ende
               and g["opened"] >= start_ts - 3600]
    echt = {"geschlossen": len(echt_zu), "pnl_geschlossen": round(sum(g["pnl_sol"] for g in echt_zu), 4),
            "offen": len(konto["positionen"]), "bankroll": round(konto["bankroll_sol"], 4), "runde": konto["runde"],
            "kauf": sum(r["aktion"] == "KAUF" for r in zeilen), "verkauf": sum(r["aktion"] == "VERKAUF" for r in zeilen),
            "geblockt": sum(r["aktion"] == "SCHATTEN_KAUF" for r in zeilen),
            "verpasst": sum(r["aktion"] == "VERPASST_KAUF" for r in zeilen),
            "ausgelassen": sum(r["aktion"] == "AUSGELASSEN" for r in zeilen)}

    # Je Coin: echter Gewinn gegen Nachbau A (Ursachen der Abweichung)
    sim_a = simulieren(a, lambda t: echte_luecke(t) if echte_luecke(t) is not None else med_k,
                       lambda t: echte_luecke(t) if echte_luecke(t) is not None else med_v)
    je_coin_echt, je_coin_sim = {}, {}
    for g in echt_zu:
        je_coin_echt[g["mint"]] = je_coin_echt.get(g["mint"], 0) + g["pnl_sol"]
    for p in sim_a.zu:
        je_coin_sim[p["mint"]] = je_coin_sim.get(p["mint"], 0) + p["pnl"]
    diffs = sorted(((m, je_coin_echt.get(m), je_coin_sim.get(m)) for m in set(je_coin_echt) | set(je_coin_sim)),
                   key=lambda x: -abs((x[1] or 0) - (x[2] or 0)))

    helius_seen = {t["sig"] for t in im_fenster}
    live_sigs = {s for s, rows in je_sig.items() if any(r["aktion"] in GESEHEN | {"VERPASST_KAUF"} for r in rows)}
    ergebnis = {
        "wallet": name, "fenster_start_utc": start, "fenster_ende_utc": ende, "trades_geladen": len(trades), "trades_im_fenster": len(im_fenster),
        "trades_vor_fenster": len(vorher),
        "trades_im_fenster_nach_art": {k: sum(t["kind"] == k for t in im_fenster) for k in ("KAUF", "VERKAUF", "UEBERWEISUNG")},
        "live_gesehen_und_bei_helius": len(helius_seen & live_sigs), "live_gesehen_nicht_bei_helius": len(live_sigs - helius_seen),
        "bei_helius_nicht_live": len(helius_seen - live_sigs),
        "median_abstand_kauf_pct": round(med_k, 2), "median_abstand_verkauf_pct": round(med_v, 2),
        "n_abstaende": [len(kauf_abst), len(verk_abst)],
        "echt": echt, "varianten": varianten,
        "groesste_abweichungen_je_coin": [{"mint": m[:8], "echt": None if e is None else round(e, 4),
                                           "nachbau_A": None if s is None else round(s, 4)} for m, e, s in diffs[:12]],
    }
    d = daten_ordner(name)
    json.dump(ergebnis, open(d / "ergebnis.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print(json.dumps(ergebnis, indent=1, ensure_ascii=False))
    z = d / "zaehler.json"
    if z.exists():
        print("[CREDITS]", json.load(open(z)))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("modus", choices=["holen", "rechnen"])
    ap.add_argument("--wallet", default="4DOV")
    ap.add_argument("--tage", type=int, default=30)
    ap.add_argument("--max-credits", type=int, default=30000)
    a = ap.parse_args()
    holen(a.wallet, a.tage, a.max_credits) if a.modus == "holen" else rechnen(a.wallet)
