"""GMGN liefert nur Wallet-Adressen; Bewertung und Speicherung bleiben beim Scout."""
import os
import re
import time
import uuid
from types import MappingProxyType

import requests

import bot as core

HOST = "https://openapi.gmgn.ai"
PFADE = MappingProxyType({
    "/v1/user/smartmoney": 1,
    "/v1/user/kol": 1,
    "/v1/market/token_top_traders": 5,
})
ADDR_RE = re.compile(r"[1-9A-HJ-NP-Za-km-z]{32,44}")
ADRESS_FELDER = {"maker", "wallet", "wallet_address", "address", "user", "owner"}
LISTEN_FELDER = {"data", "items", "list", "rows", "result", "wallets", "traders", "activities"}


def abruf(path, params, headers):
    """Einziger Netzwerkzugriff, in Tests gesperrt. Keine Weiterleitungen mit Key."""
    if path not in PFADE:
        raise ValueError("GMGN-Pfad nicht erlaubt")
    return requests.get(HOST + path, params=params, headers=headers, timeout=15, allow_redirects=False)


def adressen(data, ausschluss=""):
    """Verschachtelte Listen/Felder lesen, ohne fremde Kennzahlen zu uebernehmen."""
    out, erkannt = {}, False
    stack = [(data, isinstance(data, list))]
    while stack:
        node, adress_feld = stack.pop()
        if isinstance(node, dict):
            for name, value in reversed(list(node.items())):
                feld = name in ADRESS_FELDER
                erkannt = erkannt or feld
                # Coin-Objekte sind keine Wallets, auch wenn sie ein address-Feld haben.
                if name not in {"coin", "token", "token_info", "coin_info"}:
                    stack.append((value, feld or name in LISTEN_FELDER))
        elif isinstance(node, list):
            erkannt = erkannt or (not node and adress_feld)
            stack.extend((value, adress_feld) for value in reversed(node))
        elif adress_feld and isinstance(node, str) and ADDR_RE.fullmatch(node):
            erkannt = True
            if node != ausschluss:
                out.setdefault(node, None)
    if not erkannt:
        raise ValueError("GMGN-Antwortformat unbekannt")
    return list(out)


def _ratenlimit(data):
    code = str(data.get("code", "")).lower()
    message = str(data.get("message") or data.get("msg") or "").lower()
    return code in {"429", "-429"} or any(
        marker in (code + " " + message)
        for marker in ("rate limit", "rate_limit", "ratelimit", "too many requests", "too_many_requests",
                       "temporarily banned", "ip_banned"))


class Client:
    """Ein Client je Suchlauf: Takt, Zaehler und Sperre werden nicht gespeichert."""

    def __init__(self):
        self._key = os.environ["GMGN_API_KEY"].strip() if "GMGN_API_KEY" in os.environ else ""
        self.gesperrt = False
        self.fehler_folge = 0
        self.letzter_fehler = ""
        self.stats = {"gmgn_key": bool(self._key), "gmgn_abfragen": 0, "gmgn_adressen": 0,
                      "gmgn_neu": 0, "gmgn_429": 0, "gmgn_fehler": 0}

    def _fehler(self, grund):
        # Nur feste eigene Texte, nie Antwort, URL, Header oder Ausnahmetext.
        self.letzter_fehler = core._hide_key(grund)
        self.stats["gmgn_fehler"] += 1
        self.fehler_folge += 1
        if self.fehler_folge >= 3:
            self.gesperrt = True
        return []

    def get(self, path, address=""):
        if path not in PFADE:
            raise ValueError("GMGN-Pfad nicht erlaubt")
        if not self._key or self.gesperrt:
            return []
        params = {"chain": "sol", "timestamp": int(time.time()), "client_id": str(uuid.uuid4())}
        if path == "/v1/market/token_top_traders":
            if not isinstance(address, str) or not ADDR_RE.fullmatch(address):
                return self._fehler("GMGN-Coin-Adresse ungueltig")
            params.update(address=address, limit=20)
        self.stats["gmgn_abfragen"] += 1
        try:
            res = abruf(path, params, {"X-APIKEY": self._key, "Content-Type": "application/json"})
            if res.status_code == 429:
                self.gesperrt = True
                self.stats["gmgn_429"] += 1
                return self._fehler("GMGN-Ratenlimit")
            if res.status_code != 200:
                return self._fehler("GMGN-HTTP-Fehler")
            data = res.json()
            if not isinstance(data, dict):
                return self._fehler("GMGN-Antwortformat unbekannt")
            if _ratenlimit(data):
                self.gesperrt = True
                self.stats["gmgn_429"] += 1
                return self._fehler("GMGN-Ratenlimit")
            if str(data.get("code")) != "0":
                return self._fehler("GMGN-API-Fehler")
            out = adressen(data.get("data"), address)
            if path == "/v1/market/token_top_traders":
                out = out[:20]
            self.stats["gmgn_adressen"] += len(out)
            self.fehler_folge = 0
            return out
        except Exception:
            return self._fehler("GMGN-Abruf oder Antwort fehlgeschlagen")
        finally:
            time.sleep(2 * PFADE[path] / 5)

    def kandidaten(self, coins):
        for path, quelle in (("/v1/user/smartmoney", "GMGN-smartmoney"), ("/v1/user/kol", "GMGN-kol")):
            for wallet in self.get(path):
                yield wallet, quelle, ""
        for mint, symbol, mult in coins[:6]:
            for wallet in self.get("/v1/market/token_top_traders", mint):
                yield wallet, "GMGN-toptrader", f"{symbol} {mult:.1f}x"


def bericht(stats):
    if not stats.get("gmgn_key"):
        return "**GMGN:** kein Key"
    if stats.get("gmgn_429"):
        return "**GMGN:** nach 429 abgebrochen"
    return (f"**GMGN:** {stats.get('gmgn_abfragen', 0)} Abfragen, {stats.get('gmgn_adressen', 0)} Adressen, "
            f"{stats.get('gmgn_neu', 0)} neu, {stats.get('gmgn_429', 0)}x 429, "
            f"{stats.get('gmgn_fehler', 0)} Fehler")
