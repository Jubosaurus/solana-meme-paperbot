"""Bausteine fuer die Tests: Jupiter-Token, Transaktionen im Format jsonParsed, Fake-Markt."""
import math
import time
from datetime import datetime, timezone

import bot as core


def addr(prefix):
    """Gueltige Solana-Adresse (Base58, 44 Zeichen) mit lesbarem Anfang."""
    return (prefix + "1" * 44)[:44]


WALLET = addr("Trader")
MINT = addr("Mint")
MINT2 = addr("MintB")
POOL = addr("Poo")
JITO = sorted(__import__("copy_bot").JITO_TIP_ACCOUNTS)[0]
BOTFEE = addr("BotFee")
TMP_WSOL = addr("TmpWso")
USDC = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"


# ================================================================ Jupiter-Token

# token_view-Name -> Pfad im Jupiter-Token
FIELDS = {
    "symbol": ("symbol",), "name": ("name",), "decimals": ("decimals",), "price": ("usdPrice",),
    "mcap": ("mcap",), "liquidity": ("liquidity",), "holders": ("holderCount",),
    "holder_growth_1h": ("stats1h", "holderChange"), "holder_growth_5m": ("stats5m", "holderChange"),
    "net_buyers_5m": ("stats5m", "numNetBuyers"), "organic_buyers_5m": ("stats5m", "numOrganicBuyers"),
    "organic_score": ("organicScore",), "price_change_1h": ("stats1h", "priceChange"),
    "price_change_5m": ("stats5m", "priceChange"), "buys_5m": ("stats5m", "numBuys"),
    "sells_5m": ("stats5m", "numSells"), "traders_5m": ("stats5m", "numTraders"),
    "buy_vol_5m": ("stats5m", "buyVolume"), "sell_vol_5m": ("stats5m", "sellVolume"),
    "buy_vol_1h": ("stats1h", "buyVolume"), "sell_vol_1h": ("stats1h", "sellVolume"),
    "organic_buy_vol_1h": ("stats1h", "buyOrganicVolume"), "traders_1h": ("stats1h", "numTraders"),
    "buy_organic_vol_5m": ("stats5m", "buyOrganicVolume"), "organic_label": ("organicScoreLabel",),
    "mint_disabled": ("audit", "mintAuthorityDisabled"), "freeze_disabled": ("audit", "freezeAuthorityDisabled"),
    "is_sus": ("audit", "isSus"), "dev_mints": ("audit", "devMints"),
    "dev_balance_pct": ("audit", "devBalancePercentage"), "top_holders_pct": ("audit", "topHoldersPercentage"),
    "dev": ("dev",), "launchpad": ("launchpad",), "twitter": ("twitter",),
}


def tok(mint=MINT, age_h=1.0, now=None, graduated=False, trades_24h=500, **kw):
    """Jupiter-Token (tokens/v2) mit allen Feldern, die token_view liest.
    Standard: ein Coin, der alle Schnellpruefungen besteht."""
    now = time.time() if now is None else now
    t = {
        "id": mint, "symbol": "TEST", "name": "Test Coin", "decimals": 6, "usdPrice": 0.0001,
        "mcap": 500_000, "fdv": 500_000, "liquidity": 50_000, "holderCount": 800,
        "organicScore": 60, "organicScoreLabel": "medium", "twitter": "https://x.com/test",
        "dev": addr("Dev"), "launchpad": "pump.fun",
        "firstPool": {"id": POOL, "createdAt": datetime.fromtimestamp(now - age_h * 3600, timezone.utc)
                      .strftime("%Y-%m-%dT%H:%M:%SZ")} if age_h is not None else {},
        "audit": {"mintAuthorityDisabled": True, "freezeAuthorityDisabled": True, "isSus": False,
                  "devMints": 2, "devBalancePercentage": 1.0, "topHoldersPercentage": 20.0},
        "stats5m": {"priceChange": 5.0, "holderChange": 2.0, "numNetBuyers": 6, "numOrganicBuyers": 5,
                    "numBuys": 40, "numSells": 20, "numTraders": 30, "buyVolume": 5000, "sellVolume": 3000,
                    "buyOrganicVolume": 2000},
        "stats1h": {"priceChange": 40.0, "holderChange": 25.0, "buyVolume": 40_000, "sellVolume": 30_000,
                    "buyOrganicVolume": 15_000, "numTraders": 300},
        "stats24h": {"numBuys": trades_24h // 2, "numSells": trades_24h - trades_24h // 2},
    }
    if graduated:
        t["graduatedPool"] = addr("GradPool")
    for key, value in kw.items():
        path = FIELDS[key]
        target = t
        for p in path[:-1]:
            target = target.setdefault(p, {})
        target[path[-1]] = value
    return t


def view(**kw):
    t = tok(**kw)
    return core.token_view(t, time.time())


# ================================================================ Endspurt

def price_for_vsol(vsol, sol_usd):
    """USD-Preis, bei dem curve_vsol genau vsol ergibt."""
    return vsol ** 2 / core.PUMP_K * sol_usd


# ================================================================ Transaktionen (jsonParsed)

def _bal(idx, mint, owner, amount, decimals=6):
    return {"accountIndex": idx, "mint": mint, "owner": owner,
            "uiTokenAmount": {"amount": str(int(amount)), "decimals": decimals}}


def _transfer(src, dst, lamports):
    return {"program": "system", "programId": "11111111111111111111111111111111",
            "parsed": {"type": "transfer", "info": {"source": src, "destination": dst, "lamports": lamports}}}


def swap_tx(wallet=WALLET, mint=MINT, pre=0, post=0, sol=0.0, fee=5000, prio=0, jito=0, botfee=0,
            decimals=6, block_time=None, signer=True, err=None, sig="sig1", wsol_temp=0,
            usdc_pre=None, usdc_post=None, wsol_pre=None, wsol_post=None):
    """Transaktion wie von Helius getTransaction (encoding jsonParsed).
    sol > 0: die Wallet gibt so viele SOL fuer den Tausch aus (Kauf); sol < 0: sie erhaelt SOL (Verkauf).
    pre/post: Token-Bestand der Wallet in kleinsten Einheiten (None = kein Token-Konto).
    fee/prio: Grund- und Prioritaetsgebuehr in Lamports; jito/botfee: Ueberweisungen in Lamports.
    wsol_temp: temporaeres WSOL-Konto, das mit so vielen Lamports befuellt und wieder geschlossen wird."""
    keys = [wallet, addr("WalTok"), POOL, JITO, BOTFEE, TMP_WSOL, addr("WalUsd"), addr("WalWso")]
    if not signer:
        keys = [addr("Other")] + keys
    w = keys.index(wallet)
    total_fee = fee + prio
    pre_sol = 50_000_000_000
    post_sol = pre_sol - int(round(sol * 1e9)) - (total_fee if w == 0 else 0) - jito - botfee
    pre_bal = [0] * len(keys)
    post_bal = [0] * len(keys)
    pre_bal[w], post_bal[w] = pre_sol, post_sol
    if wsol_pre is not None:                   # dauerhaftes WSOL-Konto: SOL-Teil des Tauschs laeuft darueber
        post_bal[w] += int(round(sol * 1e9))
    pre_tb, post_tb = [], []
    tok_idx = keys.index(addr("WalTok"))
    if pre is not None:
        pre_tb.append(_bal(tok_idx, mint, wallet, pre, decimals))
    if post is not None:
        post_tb.append(_bal(tok_idx, mint, wallet, post, decimals))
    # Gegenseite: der Pool (fremder Besitzer, darf nicht mitzaehlen)
    pool_idx = keys.index(POOL)
    pre_tb.append(_bal(pool_idx, mint, addr("PoolOwner"), 10**15, decimals))
    post_tb.append(_bal(pool_idx, mint, addr("PoolOwner"), 10**15 - ((post or 0) - (pre or 0)), decimals))
    if usdc_pre is not None or usdc_post is not None:
        u = keys.index(addr("WalUsd"))
        if usdc_pre is not None:
            pre_tb.append(_bal(u, USDC, wallet, usdc_pre, 6))
        if usdc_post is not None:
            post_tb.append(_bal(u, USDC, wallet, usdc_post, 6))
    if wsol_pre is not None:
        x = keys.index(addr("WalWso"))
        pre_tb.append(_bal(x, core.WSOL_MINT, wallet, wsol_pre, 9))
        post_tb.append(_bal(x, core.WSOL_MINT, wallet, wsol_post, 9))
    ins = []
    if wsol_temp:
        ins.append({"program": "system", "parsed": {"type": "createAccountWithSeed", "info": {
            "source": wallet, "newAccount": TMP_WSOL, "lamports": 2039280}}})
        ins.append(_transfer(wallet, TMP_WSOL, wsol_temp))
        ins.append({"program": "spl-token", "parsed": {"type": "syncNative", "info": {"account": TMP_WSOL}}})
    ins.append({"programId": "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P", "accounts": [], "data": "x"})
    if jito:
        ins.append(_transfer(wallet, JITO, jito))
    if botfee:
        ins.append(_transfer(wallet, BOTFEE, botfee))
    if wsol_temp:
        ins.append({"program": "spl-token", "parsed": {"type": "closeAccount", "info": {
            "account": TMP_WSOL, "destination": wallet, "owner": wallet}}})
    inner = [{"index": len(ins) - 1, "instructions": [_transfer(wallet, POOL, 1234)]}]   # innerer Transfer: Tausch
    return {
        "slot": 1, "blockTime": int(time.time()) if block_time is None else block_time,
        "meta": {"err": err, "fee": total_fee, "preBalances": pre_bal, "postBalances": post_bal,
                 "preTokenBalances": pre_tb, "postTokenBalances": post_tb, "innerInstructions": inner,
                 "logMessages": []},
        "transaction": {"signatures": [sig],
                        "message": {"accountKeys": [{"pubkey": k, "signer": i == 0, "writable": True,
                                                     "source": "transaction"} for i, k in enumerate(keys)],
                                    "instructions": ins}},
    }


def buy_tx(sol=0.5, tokens=1_000_000, pre=0, **kw):
    """Kauf: sol SOL fuer tokens ganze Token (6 Nachkommastellen); pre = Bestand vorher in ganzen Token."""
    return swap_tx(pre=pre * 10**6 if pre else None, post=(pre + tokens) * 10**6, sol=sol, **kw)


def sell_tx(sol=0.5, tokens=500_000, pre=1_000_000, **kw):
    """Verkauf: tokens ganze Token fuer sol SOL."""
    post = pre - tokens
    return swap_tx(pre=pre * 10**6, post=post * 10**6 if post > 0 else None, sol=-sol, **kw)


def transfer_tx(tokens=1_000_000, pre=1_000_000, **kw):
    """Token-Ueberweisung an eine andere Wallet: kein SOL-Tausch."""
    post = pre - tokens
    return swap_tx(pre=pre * 10**6, post=post * 10**6 if post > 0 else None, sol=0, **kw)


# ================================================================ Fake-Markt

class Market:
    """Ersetzt Jupiter: Kurse je Mint in USD, Quotes passend zum Kurs (ohne Slippage, ausser eingestellt)."""

    def __init__(self, sol_usd=100.0):
        self.sol_usd = sol_usd
        self.price = {}           # mint -> USD
        self.tokens = {}          # mint -> Jupiter-Token (tok())
        self.decimals = {}
        self.buy_slippage = {}    # mint -> Faktor (> 1 = weniger Token beim Kauf)
        self.ausfall = set()      # Mints, fuer die Jupiter nicht antwortet (Quote = None)
        self.calls = []

    def set(self, mint, price=None, **kw):
        t = tok(mint=mint, **kw)
        if price is not None:
            t["usdPrice"] = price
        self.tokens[mint] = t
        self.price[mint] = t["usdPrice"]
        self.decimals[mint] = t["decimals"]
        return t

    def quote(self, input_mint, output_mint, raw):
        self.calls.append(("quote", input_mint, output_mint, raw))
        if input_mint in self.ausfall or output_mint in self.ausfall:
            return None
        if input_mint == core.WSOL_MINT:
            m = output_mint
            p = self.price.get(m, 0)
            if p <= 0:
                return 0
            tokens = raw / 1e9 * self.sol_usd / p / self.buy_slippage.get(m, 1.0)
            return int(tokens * 10 ** self.decimals.get(m, 6))
        m = input_mint
        p = self.price.get(m, 0)
        return int(raw / 10 ** self.decimals.get(m, 6) * p / self.sol_usd * 1e9) if p > 0 else 0

    def jup_tokens(self, mints):
        out = {}
        for m in mints:
            t = self.tokens.get(m)
            if t is not None:
                t = dict(t)
                t["usdPrice"] = self.price[m]
                out[m] = t
        return out

    def search(self, mints):
        return list(self.jup_tokens(mints).values())


def vsol_price(vsol, sol_usd=100.0):
    return price_for_vsol(vsol, sol_usd)


def approx(a, b, tol=1e-6):
    return math.isclose(a, b, rel_tol=tol, abs_tol=tol)
