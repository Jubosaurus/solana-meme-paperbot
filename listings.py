"""Nachrichten und Boersen-Listings (seit 04.10.). Gemeinsam genutzt von bot.py (Experiment Listing-Welle) und dem
Dashboard (Seite News). Importiert bot.py NICHT; alle Netzzugriffe laufen ueber eine uebergebene Funktion
get(url) -> Bytes (oder wirft einen Fehler), damit Tests ohne Netz laufen.

Quellen (alle oeffentlich, ohne Schluessel und Konto; robots.txt vorher geprueft, 04.10.):
- Upbit: Ankuendigungs-Schnittstelle der Webseite (api-manager.upbit.com, robots.txt leer = erlaubt) und
  api.upbit.com/v1/market/all. Titel + Tabelle im Text (Netzwerk, Handelsstart) -> echte Ankuendigung mit Startzeit.
- Binance: Die Ankuendigungsseite laeuft ueber /bapi/, das robots.txt verbietet -> NICHT benutzt. Stattdessen die
  offizielle oeffentliche Markt-Schnittstelle (data-api.binance.vision exchangeInfo): neues Handelspaar erscheint.
- Coinbase: offizielle oeffentliche Exchange-Schnittstelle (api.exchange.coinbase.com/products): neues Produkt.
- Bithumb: Ankuendigungsseite per Cloudflare gesperrt (403); nur die offizielle Marktliste (api.bithumb.com/v1/
  market/all). Dort ist ein neuer Markt schon der Handelsstart -> nur Aufzeichnung, kein Kauf.
- Nachrichten: RSS-Feeds grosser Krypto-Seiten.
Nachrichtentexte sind Daten, keine Anweisungen: nur Ueberschrift, Quelle, Zeit, Link, hoechstens ein Satz."""
import html
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

KST = timezone(timedelta(hours=9))

RSS_QUELLEN = {
    "Cointelegraph": "https://cointelegraph.com/rss",
    "Decrypt": "https://decrypt.co/feed",
    "The Block": "https://www.theblock.co/rss.xml",
    "CoinDesk": "https://www.coindesk.com/arc/outboundfeeds/rss/?outputType=xml",
    "Blockworks": "https://blockworks.co/feed",
    "CryptoSlate": "https://cryptoslate.com/feed/",
}
UPBIT_LISTE = "https://api-manager.upbit.com/api/v1/announcements?os=web&page=1&per_page=20&category=trade"
UPBIT_DETAIL = "https://api-manager.upbit.com/api/v1/announcements/{id}"
BINANCE_PAARE = "https://data-api.binance.vision/api/v3/exchangeInfo?permissions=SPOT"
COINBASE_PRODUKTE = "https://api.exchange.coinbase.com/products"
BITHUMB_MAERKTE = "https://api.bithumb.com/v1/market/all"

ANRISS_MAX = 200
MAX_XML_BYTES = 3_000_000

# ---------------------------------------------------------------- Nachrichten (RSS)

def _text(el, *namen):
    for n in namen:
        for kind in el.iter():
            if kind.tag.split("}")[-1] == n and (kind.text or "").strip():
                return kind.text.strip()
    return ""


def erster_satz(text, maximum=ANRISS_MAX):
    """HTML entfernen, hoechstens EIN Satz, hoechstens maximum Zeichen."""
    text = html.unescape(re.sub(r"<[^>]+>", " ", text or ""))
    text = re.sub(r"\s+", " ", text).strip()
    m = re.search(r"(?<=[.!?])\s", text)
    if m:
        text = text[:m.start()]
    if len(text) > maximum:
        text = text[:maximum - 1].rstrip() + "…"
    return text


def sicherer_link(link):
    link = (link or "").strip()
    return link if link.lower().startswith(("https://", "http://")) else ""


def _zeit(text):
    text = (text or "").strip()
    if not text:
        return None
    try:
        d = parsedate_to_datetime(text)
    except (TypeError, ValueError):
        try:
            d = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            return None
    if d.tzinfo is None:
        d = d.replace(tzinfo=timezone.utc)
    return d.timestamp()


def parse_rss(daten, quelle):
    """RSS (item) oder Atom (entry) -> [{titel, link, zeit, anriss, quelle}]. Kaputtes XML -> []."""
    if isinstance(daten, str):
        daten = daten.encode("utf-8", "replace")
    if not daten or len(daten) > MAX_XML_BYTES or b"<!ENTITY" in daten.upper() or b"<!DOCTYPE" in daten.upper():
        return []                    # keine Entity-Tricks aus fremdem XML
    try:
        root = ET.fromstring(daten)
    except ET.ParseError:
        return []
    out = []
    for el in root.iter():
        if el.tag.split("}")[-1] not in ("item", "entry"):
            continue
        titel = re.sub(r"\s+", " ", html.unescape(_text(el, "title"))).strip()
        link = ""
        for k in el:
            if k.tag.split("}")[-1] == "link":
                link = k.attrib.get("href") or (k.text or "")
                if link:
                    break
        zeit = _zeit(_text(el, "pubDate", "published", "updated", "date"))
        if titel and zeit:
            out.append({"titel": titel[:300], "link": sicherer_link(link), "zeit": zeit, "quelle": quelle,
                        "anriss": erster_satz(_text(el, "description", "summary"))})
    return out


def hole_news(get, quellen=None):
    """Alle RSS-Feeds holen (Fehler einzelner Feeds werden uebersprungen). Rueckgabe (items, fehler)."""
    from concurrent.futures import ThreadPoolExecutor
    quellen = quellen or RSS_QUELLEN

    def eins(name):
        try:
            return parse_rss(get(quellen[name]), name), None
        except Exception as err:
            return [], f"{name}: {str(err)[:60]}"
    with ThreadPoolExecutor(max_workers=min(6, len(quellen) or 1)) as pool:
        ergebnisse = list(pool.map(eins, list(quellen)))
    items = [i for liste, _ in ergebnisse for i in liste]
    fehler = [f for _, f in ergebnisse if f]
    return sorted(items, key=lambda i: -i["zeit"]), fehler


# ---------------------------------------------------------------- Relevanz

RE_LISTING = re.compile(r"\b(will list|to list|listing|listings|lists|listed|delist\w*|to add|adds? support|"
                        r"launches? spot|spot trading|new trading pair)\b", re.I)
RE_GERUECHT = re.compile(r"\b(listing|will list|to list|plans? to list|set to list|lists?|listed on|"
                         r"possible listing|rumou?r\w*)\b", re.I)
RE_DELISTING = re.compile(r"\bdelist\w*", re.I)
RE_SOLANA = re.compile(r"\b(solana|sol|pump\.?fun|memecoins?|meme coins?|bonk|jupiter|raydium|phantom)\b", re.I)
RE_RUG = re.compile(r"\b(rug\w*|hack\w*|exploit\w*|scam\w*|fraud\w*|drained|stolen|phishing|"
                    r"breach\w*|honeypot)\b", re.I)
BOERSEN = ("Binance", "Coinbase", "Upbit", "Bithumb", "OKX", "Bybit", "Kraken", "Robinhood")
TICKER_STOP = {"USD", "USDT", "USDC", "BTC", "ETH", "SOL", "ETF", "SEC", "CEO", "API", "NFT", "DEX", "CEX", "AI",
               "US", "UK", "EU", "THE", "FOR", "AND", "NEW", "KRW", "FED", "IPO", "DAO", "DEFI", "ATH", "CFTC"}


def ticker_in_text(text):
    """Ticker-Kandidaten: (ABC), $abc oder 'list(s|ing) ABC'. Ohne Boersen- und Standardwoerter."""
    found = []
    for pat in (r"\(\$?([A-Z][A-Z0-9]{1,9})\)", r"\$([A-Za-z][A-Za-z0-9]{1,9})\b",
                r"\blist(?:s|ing|ed)?\s+\$?([A-Z][A-Z0-9]{2,9})\b"):
        for m in re.finditer(pat, text or ""):
            t = m.group(1).upper()
            if t not in TICKER_STOP and t.title() not in BOERSEN and t not in found:
                found.append(t)
    return found


def erwaehnt(text, symbol):
    """Kommt der Coin-Ticker im Text vor? Nur als $TICKER, (TICKER) oder GROSS geschrieben als ganzes Wort
    (sonst treffen Ticker wie HOLD oder BOT normale Woerter). Ticker unter 3 Zeichen nur mit $ oder Klammern."""
    sym = (symbol or "").strip()
    if len(sym) < 2:
        return False
    esc = re.escape(sym)
    if re.search(rf"[$(]{esc}", text, re.I):
        return True
    return len(sym) >= 3 and re.search(rf"(?<![\w$]){esc.upper()}(?!\w)", text) is not None


def bewerten(item, positions_symbole=()):
    """Markierungen und Relevanz einer Nachricht. positions_symbole: Ticker der offenen Positionen aller Konten."""
    text = f"{item.get('titel', '')} {item.get('anriss', '')}"
    marken, punkte = [], 0
    gefunden = [s for s in positions_symbole if erwaehnt(text, s)]
    if gefunden:
        marken.append("position")
        punkte += 100
        item["positions_coins"] = gefunden[:4]
    if RE_LISTING.search(text) and (any(b.lower() in text.lower() for b in BOERSEN) or RE_DELISTING.search(text)
                                    or item.get("art") in ("listing", "delisting")):
        marken.append("listing")
        punkte += 70 if RE_DELISTING.search(text) else 60
    if RE_RUG.search(text):
        marken.append("rug")
        punkte += 50
    if RE_SOLANA.search(text):
        marken.append("solana")
        punkte += 30
    item["marken"], item["punkte"] = marken, punkte
    return item


def sortiert(items, jetzt, max_alter_h=96):
    """Neu genug, Relevanz (Punkte) zuerst, dann neu vor alt. Wichtige Meldungen verlieren mit dem Alter etwas."""
    ok = [i for i in items if 0 <= jetzt - i["zeit"] <= max_alter_h * 3600]
    return sorted(ok, key=lambda i: (-(i.get("punkte", 0) - min(40, (jetzt - i["zeit"]) / 3600 * 0.8)), -i["zeit"]))


def ist_geruecht(item):
    """Nachricht, die ueber ein moegliches Listing spricht (ohne zu pruefen, ob es offiziell ist)."""
    text = f"{item.get('titel', '')} {item.get('anriss', '')}"
    return bool(RE_GERUECHT.search(text)) and bool(ticker_in_text(text))


# ---------------------------------------------------------------- Boersen-Quellen

def _json(get, url):
    import json
    return json.loads(get(url))


_MONATE_RE = re.compile(r"(\d{1,2})월\s*(\d{1,2})일\s*(?:(\d{1,2})시)?\s*(?:(\d{1,2})분)?")


def upbit_start(text, bezug):
    """'10월 2일 16시 예정' (Korea-Zeit) -> Unix-Zeit. Jahr = Jahr der Ankuendigung (Jahreswechsel beachtet)."""
    m = _MONATE_RE.search(text or "")
    if not m:
        return None
    mon, tag, std, minu = int(m[1]), int(m[2]), int(m[3] or 0), int(m[4] or 0)
    ref = datetime.fromtimestamp(bezug, KST)
    try:
        d = datetime(ref.year, mon, tag, std, minu, tzinfo=KST)
    except ValueError:
        return None
    if d < ref - timedelta(days=30):
        d = d.replace(year=ref.year + 1)
    return d.timestamp()


def upbit_tabelle(body, bezug):
    """Zeilen der Tabelle im Ankuendigungstext -> [{symbol, netzwerk, start}]. Nur diese Felder bleiben erhalten."""
    out = []
    for row in re.findall(r"<tr>(.*?)</tr>", body or "", re.S):
        zellen = [html.unescape(re.sub(r"<[^>]+>", "", c)).strip() for c in re.findall(r"<td>(.*?)</td>", row, re.S)]
        if len(zellen) < 5:
            continue
        m = re.search(r"\(([A-Za-z0-9]{2,12})\)", zellen[0])
        if m:
            out.append({"symbol": m.group(1).upper(), "netzwerk": zellen[2], "start": upbit_start(zellen[4], bezug)})
    return out


def upbit_ereignisse(get, gesehen):
    """Neue Upbit-Ankuendigungen (id nicht in gesehen) -> Ereignisse. gesehen wird ergaenzt.
    Beim allerersten Lauf (gesehen leer) werden alle vorhandenen nur als gesehen markiert."""
    erster_lauf = not gesehen
    liste = _json(get, UPBIT_LISTE)["data"]["notices"]
    out = []
    for n in sorted(liste, key=lambda n: n["id"]):
        eid = f"upbit:{n['id']}"
        if eid in gesehen:
            continue
        gesehen.add(eid)
        if erster_lauf:
            continue
        titel = n.get("title", "")
        zeit = datetime.fromisoformat(n["listed_at"]).timestamp()
        art = "listing" if "신규 거래지원 안내" in titel else "delisting" if "거래지원 종료" in titel else "sonst"
        if art == "listing" and re.search(r"(취소|변경)", titel):
            art = "sonst"                  # Aenderung oder Absage einer frueheren Ankuendigung
        coins = []
        if art == "listing":
            try:
                body = _json(get, UPBIT_DETAIL.format(id=n["id"]))["data"]["body"]
                coins = upbit_tabelle(body, zeit)
            except Exception:
                coins = []
            if not coins:                  # Tabelle nicht lesbar: Ticker aus dem Titel, ohne Netzwerk/Start
                coins = [{"symbol": s, "netzwerk": "", "start": None}
                         for s in re.findall(r"\(([A-Z0-9]{2,12})\)", titel) if s not in ("KRW", "BTC", "USDT")]
        elif art == "delisting":
            coins = [{"symbol": s, "netzwerk": "", "start": None} for s in re.findall(r"\(([A-Z0-9]{2,12})\)", titel)]
        out.append({"id": eid, "boerse": "Upbit", "art": art, "titel": titel[:200], "zeit": zeit,
                    "quelle_typ": "ankuendigung", "coins": coins,
                    "url": f"https://upbit.com/service_center/notice?id={n['id']}"})
    return out


def binance_ereignisse(get, bekannt):
    """Neues Basis-Asset in der Binance-Spot-Liste (nicht nur neues Paar). bekannt = Menge der Basis-Assets."""
    erster_lauf = not bekannt
    out, jetzt = [], datetime.now(timezone.utc).timestamp()
    for s in _json(get, BINANCE_PAARE).get("symbols", []):
        base = s.get("baseAsset")
        if not base or base in bekannt:
            continue
        bekannt.add(base)
        if not erster_lauf:
            out.append({"id": f"binance:{base}", "boerse": "Binance", "art": "listing",
                        "titel": f"Binance: neues Handelspaar {s.get('symbol')} (Status {s.get('status')})",
                        "zeit": jetzt, "quelle_typ": "neues_paar",
                        "coins": [{"symbol": base.upper(), "netzwerk": "", "start": jetzt if s.get("status") == "TRADING" else None}],
                        "url": f"https://www.binance.com/en/trade/{s.get('symbol')}"})
    return out


def coinbase_status(produkte):
    """{Basis-Asset: 'offen' | 'delisted' | anderer Status}. Ein Asset mit mehreren Paaren: 'offen', wenn irgendein
    Paar voll handelbar ist; 'delisted' nur, wenn alle Paare abgeschaltet sind."""
    rang = {"offen": 0, "eingeschraenkt": 1, "delisted": 2}
    out = {}
    for p in produkte:
        base = p.get("base_currency")
        if not base:
            continue
        if p.get("status") == "delisted":
            s = "delisted"
        elif p.get("status") == "online" and not (p.get("trading_disabled") or p.get("post_only") or p.get("limit_only")):
            s = "offen"
        else:
            s = "eingeschraenkt"
        if base not in out or rang[s] < rang[out[base]]:
            out[base] = s
    return out


def coinbase_ereignisse(get, bekannt):
    """bekannt: {base: status}. Neues Basis-Asset = Listing (eingeschraenkt = vor dem Start); Wechsel auf 'delisted'
    = Delisting. Erster Lauf (bekannt leer): nur merken."""
    erster_lauf = not bekannt
    out, jetzt = [], datetime.now(timezone.utc).timestamp()
    for base, status in coinbase_status(_json(get, COINBASE_PRODUKTE)).items():
        alt = bekannt.get(base)
        bekannt[base] = status
        if erster_lauf:
            continue
        if alt is None and status != "delisted":
            out.append({"id": f"coinbase:{base}", "boerse": "Coinbase", "art": "listing",
                        "titel": f"Coinbase: neues Asset {base} ({'handelbar' if status == 'offen' else 'noch eingeschraenkt'})",
                        "zeit": jetzt, "quelle_typ": "neues_paar",
                        "coins": [{"symbol": base.upper(), "netzwerk": "", "start": jetzt if status == "offen" else None}],
                        "url": f"https://www.coinbase.com/price/{base.lower()}"})
        elif alt not in (None, "delisted") and status == "delisted":
            out.append({"id": f"coinbase:{base}:delisted", "boerse": "Coinbase", "art": "delisting",
                        "titel": f"Coinbase: {base} abgeschaltet (delisted)", "zeit": jetzt,
                        "quelle_typ": "neues_paar", "coins": [{"symbol": base.upper(), "netzwerk": "", "start": None}],
                        "url": ""})
    return out


def bithumb_ereignisse(get, bekannt):
    """Neuer KRW-Markt in der Bithumb-Marktliste. Ein neuer Markt IST schon der Handelsstart -> nur Aufzeichnung."""
    erster_lauf = not bekannt
    out, jetzt = [], datetime.now(timezone.utc).timestamp()
    for m in _json(get, BITHUMB_MAERKTE):
        base = str(m.get("market", "")).split("-")[-1]
        if not base or base in bekannt:
            continue
        bekannt.add(base)
        if not erster_lauf:
            out.append({"id": f"bithumb:{base}", "boerse": "Bithumb", "art": "listing",
                        "titel": f"Bithumb: neuer Markt {m.get('market')}", "zeit": jetzt,
                        "quelle_typ": "handelsstart", "coins": [{"symbol": base.upper(), "netzwerk": "", "start": jetzt}],
                        "url": ""})
    return out


def coinbase_offen(get, basen):
    """Welche der Basis-Assets handeln auf Coinbase inzwischen voll (online, nicht limit_only/post_only)?"""
    try:
        return {b for b, st in coinbase_status(_json(get, COINBASE_PRODUKTE)).items() if b in basen and st == "offen"}
    except Exception:
        return set()


def binance_offen(get, basen):
    try:
        return {s["baseAsset"] for s in _json(get, BINANCE_PAARE).get("symbols", [])
                if s.get("baseAsset") in basen and s.get("status") == "TRADING"}
    except Exception:
        return set()


# ---------------------------------------------------------------- Kursverlauf vor der Ankuendigung

GECKO_POOLS = "https://api.geckoterminal.com/api/v2/networks/solana/tokens/{mint}/pools?page=1"
GECKO_OHLCV = "https://api.geckoterminal.com/api/v2/networks/solana/pools/{pool}/ohlcv/hour?aggregate=1&limit=100"


def kurs_vorlauf(get, mint, ereignis_zeit):
    """Kursanstieg in % in den 3 Stunden und 3 Tagen VOR dem Ereignis (GeckoTerminal, Stundenkerzen).
    Rueckgabe {'anstieg_3h_pct': x|None, 'anstieg_3d_pct': x|None}. Ohne Daten None (nie ein Fehler)."""
    leer = {"anstieg_3h_pct": None, "anstieg_3d_pct": None}
    try:
        pools = _json(get, GECKO_POOLS.format(mint=mint))["data"]
        pool = pools[0]["attributes"]["address"]
        kerzen = _json(get, GECKO_OHLCV.format(pool=pool))["data"]["attributes"]["ohlcv_list"]
    except Exception:
        return leer
    return anstiege_aus_kerzen(kerzen, ereignis_zeit) or leer


def anstiege_aus_kerzen(kerzen, t):
    """kerzen: [[unix, open, high, low, close, volume], ...] (neueste zuerst). Kurs zu t = Schluss der Kerze,
    die vor t endet; Vergleich mit dem Schlusskurs 3 h bzw. 72 h davor."""
    punkte = sorted(((float(k[0]), float(k[4])) for k in kerzen if len(k) >= 5 and float(k[4]) > 0))
    if not punkte:
        return None

    def kurs_bei(zeit):
        vor = [c for ts, c in punkte if ts <= zeit]
        return vor[-1] if vor else None
    ref = kurs_bei(t)
    res = {}
    for key, std in (("anstieg_3h_pct", 3), ("anstieg_3d_pct", 72)):
        alt = kurs_bei(t - std * 3600)
        res[key] = round((ref / alt - 1) * 100, 1) if ref and alt else None
    return res
