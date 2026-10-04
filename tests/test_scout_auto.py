"""Scout seit 04.10.: Pruefliste mit Speicher (nur neue Adressen abfragen), Modus 'nur Pruefliste' und die
Automatik, die Copy-Wallets aufnimmt und ersetzt (Kriterien, Platz, Reihenfolge, Schonfrist, Tageslimit,
Warteliste, nur copy_wallets.txt wird geschrieben)."""
import csv
import json
import os
import time
from datetime import datetime, timezone

import pytest

import copy_bot as cb
import scout_bot as scout
from helpers import addr

NOW = time.time()
LETTERS = "abcdefghijkmnopqrstuvwxyz"                    # Base58 ohne 0, O, I, l


def kand(i):
    return addr("Kand" + LETTERS[i])


def git_adds(git):
    return [args[1:] for args in git if args and args[0] == "add"]


def good_row(w, punkte=20.0, quelle="frueh", **kw):
    """Bewertete Zeile, die alle Aufnahme-Kriterien erfuellt."""
    r = {"zeit": "x", "wallet": w, "quelle": quelle, "coin": "Coin 5x", "ergebnis": "bewertet", "punkte": punkte,
         "inaktiv_h": 2.0, "coins": 8, "rendite_ohne_besten_pct": punkte + 5, "trades_pro_tag": 30.0,
         "kauf_median_sol": 0.5}
    r.update(kw)
    return r


def write_wallets(n, extra=""):
    """copy_wallets.txt mit n aktiven Wallets W0..W(n-1)."""
    names = [(f"W{i}", addr("Wa" + LETTERS[i])) for i in range(n)]
    with open(cb.WALLET_FILE, "w", encoding="utf-8") as f:
        f.write("# Kopf\n" + extra + "".join(f"{n_}: {a}\n" for n_, a in names))
    return names


def write_accounts(accts):
    os.makedirs("copy", exist_ok=True)
    json.dump({"wallets": accts}, open(cb.ACCOUNTS_FILE, "w", encoding="utf-8"))


def acct(a, days=10, idle_h=1.0, closed=0, pnl_each=0.0):
    return {"adresse": a, "gestartet": datetime.fromtimestamp(NOW - days * 86400, timezone.utc).isoformat(),
            "letzter_trade": NOW - idle_h * 3600 if idle_h is not None else None,
            "geschlossen": [{"pnl_sol": pnl_each} for _ in range(closed)], "positionen": {}}


@pytest.fixture
def no_bots(monkeypatch):
    """Stufe 1 fuer aktive Wallets: kein Bot (ausser die Adresse steht in bots)."""
    bots, calls = set(), []

    def stage1(w, now, max_idle_h=None):
        calls.append(w)
        return {"_page": []}, ("Bot (zu hoher Takt)" if w in bots else None)
    monkeypatch.setattr(scout, "stage1", stage1)
    return {"bots": bots, "calls": calls}


def active_lines():
    return [l.strip() for l in open(cb.WALLET_FILE, encoding="utf-8") if l.strip() and not l.startswith("#")]


# ================================================================ Teil A: Pruefliste mit Speicher

def test_bewertete_adresse_wird_nicht_erneut_abgefragt(monkeypatch):
    os.makedirs("scout")
    a, b = addr("ListA"), addr("ListB")
    open(scout.LIST_FILE, "w", encoding="utf-8").write(f"Haru: {a}\n")
    calls = []
    monkeypatch.setattr(scout, "stage1", lambda w, now, idle=None: (calls.append(w) or {"_page": []}, "still"))
    state = scout.load_state()
    rows, lines = scout.check_list(state, NOW, 100.0)
    assert [r["wallet"] for r in rows] == [a] and calls == [a]
    assert scout.check_list(state, NOW, 100.0) == ([], [])             # nichts Neues: keine Abfrage, keine Meldung
    open(scout.LIST_FILE, "a", encoding="utf-8").write(f"Neu: {b}\n")
    rows, lines = scout.check_list(state, NOW, 100.0)
    assert calls == [a, b] and [r["wallet"] for r in rows] == [b]       # nur die neue Adresse abgefragt
    assert len(lines) == 2 and any("aus dem Speicher" in l and "Haru" in l for l in lines)
    monkeypatch.setattr(scout, "SCORING_VERSION", scout.SCORING_VERSION + "x")
    rows, _ = scout.check_list(state, NOW, 100.0)
    assert len(rows) == 2 and calls[2:] == [a, b]                       # neue Bewertung: alle erneut


def test_pruefliste_uebergang_vom_alten_listen_hash(monkeypatch):
    os.makedirs("scout")
    a = addr("ListA")
    open(scout.LIST_FILE, "w", encoding="utf-8").write(f"Haru: {a}\n")
    state = scout.load_state()
    state["liste_hash"] = scout._list_digest(scout.load_list())        # alter Stand: Liste schon bewertet
    state["wallets_geprueft"][a] = NOW - 3600
    monkeypatch.setattr(scout, "stage1", lambda *a_, **k: pytest.fail("darf nicht erneut abfragen"))
    assert scout.check_list(state, NOW, 100.0) == ([], [])
    assert state["liste_bewertet"][a]["version"] == scout.SCORING_VERSION


def test_fehler_bei_der_pruefung_wird_beim_naechsten_lauf_wiederholt(monkeypatch):
    os.makedirs("scout")
    a = addr("ListA")
    open(scout.LIST_FILE, "w", encoding="utf-8").write(f"{a}\n")
    calls = []

    def boom(w, now, idle=None):
        calls.append(w)
        raise RuntimeError("Helius weg")
    monkeypatch.setattr(scout, "stage1", boom)
    state = scout.load_state()
    _, lines = scout.check_list(state, NOW, 100.0)
    assert lines[0].startswith("⚠️")
    scout.check_list(state, NOW, 100.0)
    assert len(calls) == 2


def test_modus_nur_pruefliste_ohne_coinsuche_und_birdeye(monkeypatch, sandbox):
    os.makedirs("scout")
    open(scout.LIST_FILE, "w", encoding="utf-8").write(f"Haru: {addr('ListA')}\n")
    monkeypatch.setattr(scout, "stage1", lambda w, now, idle=None: ({"_page": []}, "still"))
    for f in ("winner_coins", "early_buyers", "birdeye_top_traders", "birdeye_get", "check_transactions"):
        monkeypatch.setattr(scout, f, lambda *a, _f=f, **k: pytest.fail(f"{_f} im Modus nur Pruefliste"))
    scout.run(nur_liste=True)
    assert any("Pruefliste" in t for t, _ in sandbox["discord"])
    assert not any(t == "🔭 Wallet-Scout" for t, _ in sandbox["discord"])
    rows = list(csv.DictReader(open(scout.CANDIDATES_FILE, encoding="utf-8")))
    assert len(rows) == 1 and rows[0]["quelle"] == "liste"
    assert all(a in ((scout.SCOUT_DIR,), (cb.WALLET_FILE,)) for a in git_adds(sandbox["git"]))


# ================================================================ Teil B: Kriterien

@pytest.mark.parametrize("kw,teil", [
    ({}, None),
    ({"ergebnis": "raus", "grund": "Bot (zu hoher Takt)"}, "Bot"),
    ({"inaktiv_h": 30}, "Aktivitaet"),
    ({"coins": 2}, "Coins"),
    ({"coins": 3}, None),                                              # 05.10.: 3 Coins reichen
    ({"punkte": -1}, "nach Reibung"),
    ({"rendite_ohne_besten_pct": 0}, "ohne besten"),
    ({"trades_pro_tag": 201}, "200 Trades"),
    ({"trades_pro_tag": None}, "200 Trades"),
    ({"kauf_median_sol": 0.09}, "Kauf-Median"),
])
def test_aufnahme_kriterien(kw, teil):
    why = scout.auto_reason(good_row(addr("Kand"), **kw))
    assert (why is None) if teil is None else (teil in why)


def test_aufnahme_kriterien_auch_aus_csv_texten():
    r = {k: str(v) for k, v in good_row(addr("Kand")).items()}
    assert scout.auto_reason(r) is None


# ================================================================ Teil B: Aufnahme, Ersetzen, Warteliste

def test_aufnahme_unter_dem_limit_nur_copy_wallets_wird_geschrieben(sandbox, no_bots):
    write_wallets(20)
    write_accounts({})
    k = addr("Kand")
    state = scout.load_state()
    lines = scout.auto_wallets(state, NOW, 100.0, [good_row(k)])
    assert any(l.startswith("➕ **Kand**") for l in lines)
    text = open(cb.WALLET_FILE, encoding="utf-8").read()
    assert f"Kand: {k}\n" in text and "automatisch aufgenommen: Scout (frueh)" in text
    assert len(cb.load_wallets()) == 21                                  # Copy-Bot liest die neue Zeile
    assert git_adds(sandbox["git"]) == [(cb.WALLET_FILE,)]              # nur copy_wallets.txt
    assert any(a[0] == "push" for a in sandbox["git"])
    assert state["auto_aenderungen"][0]["adresse"] == k
    assert no_bots["calls"] == []                                        # Platz frei: keine Abfrage der aktiven


def test_bekannte_und_frueher_entfernte_wallets_werden_nicht_aufgenommen(sandbox, no_bots):
    old = addr("Abt")
    write_wallets(5, extra=f"# Abt: {old}   <- entfernt 01.10.: Bot\n")
    lines = scout.auto_wallets(scout.load_state(), NOW, 100.0, [good_row(old), good_row(addr("Wa" + LETTERS[1]))])
    assert lines == [] and len(cb.load_wallets()) == 5 and git_adds(sandbox["git"]) == []


def test_name_kollidiert_nicht_mit_altem_konto(sandbox, no_bots):
    write_wallets(3)
    k = addr("Kand")
    write_accounts({"Kand": acct(addr("Alt"))})                          # altes Konto mit diesem Namen
    scout.auto_wallets(scout.load_state(), NOW, 100.0, [good_row(k)])
    assert f"{k[:6]}: {k}" in active_lines()


def test_ersetzen_reihenfolge_bot_dann_still_dann_verlust(sandbox, no_bots):
    names = write_wallets(22)
    accts = {n: acct(a) for n, a in names}
    accts["W3"] = acct(names[3][1], closed=40, pnl_each=-0.1)          # -4 SOL
    accts["W4"] = acct(names[4][1], closed=35, pnl_each=-0.05)         # -1,75 SOL
    accts["W5"] = acct(names[5][1], idle_h=80)                          # still
    accts["W6"] = acct(names[6][1], idle_h=None, days=3.5)             # nie ein Trade, 84 h dabei -> still
    write_accounts(accts)
    no_bots["bots"].add(names[9][1])
    cands = [good_row(kand(i), punkte=50 - i) for i in range(3)]
    state = scout.load_state()
    lines = scout.auto_wallets(state, NOW, 100.0, cands)
    text = open(cb.WALLET_FILE, encoding="utf-8").read()
    raus = [e["raus"]["name"] for e in state["auto_aenderungen"]]
    assert raus == ["W9", "W6", "W5"]                                    # Bot, dann laengste Pause, dann still
    assert f"# W9: {names[9][1]}   <- entfernt" in text and "automatisch: Bot" in text
    assert len(cb.load_wallets()) == 22 and sum(l.startswith("🔁") for l in lines) == 3
    # Tageslimit erreicht: der Verlust-Kandidat bleibt, ein weiterer Kandidat wartet
    lines = scout.auto_wallets(state, NOW + 60, 100.0, [good_row(kand(9))])
    assert "W3: " + names[3][1] in active_lines() and kand(9) in open(scout.WAIT_FILE, encoding="utf-8").read()


def test_verlust_reihenfolge_und_schonfrist(sandbox, no_bots):
    names = write_wallets(22)
    accts = {n: acct(a) for n, a in names}
    accts["W3"] = acct(names[3][1], closed=40, pnl_each=-0.05)         # -2 SOL
    accts["W4"] = acct(names[4][1], closed=40, pnl_each=-0.1)          # -4 SOL: zuerst
    accts["W7"] = acct(names[7][1], days=2, closed=29, pnl_each=-0.3)  # Schonfrist: 2 Tage, 29 Positionen
    accts["W8"] = acct(names[8][1], closed=40, pnl_each=-0.02)         # -0,8 SOL: unter 1 SOL, bleibt
    write_accounts(accts)
    state = scout.load_state()
    scout.auto_wallets(state, NOW, 100.0, [good_row(kand(i), punkte=50 - i) for i in range(3)])
    assert [e["raus"]["name"] for e in state["auto_aenderungen"]] == ["W4", "W3"]
    assert all(f"W{i}: " in t for i in (7, 8) for t in ["\n".join(active_lines())])
    assert kand(2) in open(scout.WAIT_FILE, encoding="utf-8").read()   # kein dritter ersetzbarer Platz


def test_schonfrist_gilt_nicht_fuer_bot_und_stille(sandbox, no_bots):
    names = write_wallets(22)
    accts = {n: acct(a) for n, a in names}
    accts["W1"] = acct(names[1][1], days=3.5, idle_h=None)              # neu, nie getradet, 84 h dabei
    write_accounts(accts)
    no_bots["bots"].add(names[2][1])                                     # neu dabei, aber Bot
    accts["W2"] = acct(names[2][1], days=1)
    write_accounts(accts)
    state = scout.load_state()
    scout.auto_wallets(state, NOW, 100.0, [good_row(kand(i), punkte=50 - i) for i in range(2)])
    assert [e["raus"]["name"] for e in state["auto_aenderungen"]] == ["W2", "W1"]


def test_tageslimit_drei_aenderungen(sandbox, no_bots):
    write_wallets(10)
    state = scout.load_state()
    cands = [good_row(kand(i), punkte=50 - i) for i in range(5)]
    scout.auto_wallets(state, NOW, 100.0, cands)
    assert len(cb.load_wallets()) == 13
    wait = list(csv.DictReader(open(scout.WAIT_FILE, encoding="utf-8")))
    assert sorted(r["wallet"] for r in wait) == sorted(kand(i) for i in (3, 4))
    scout.auto_wallets(state, NOW + 3600, 100.0, [])                    # gleicher Tag: nichts mehr
    assert len(cb.load_wallets()) == 13


def test_warteliste_und_spaetere_neupruefung(sandbox, monkeypatch, no_bots):
    names = write_wallets(22)
    write_accounts({n: acct(a) for n, a in names})                     # niemand ersetzbar
    k = addr("Kand")
    state = scout.load_state()
    lines = scout.auto_wallets(state, NOW, 100.0, [good_row(k, quelle="liste", coin="Haru")])
    assert lines == [] and len(cb.load_wallets()) == 22 and git_adds(sandbox["git"]) == []
    wait = list(csv.DictReader(open(scout.WAIT_FILE, encoding="utf-8")))
    assert [(r["wallet"], r["name"]) for r in wait] == [(k, "Haru")]
    # Einen Tag spaeter ist W0 still -> Platz. Bewertung ist alt -> vorher frisch pruefen
    accts = {n: acct(a) for n, a in names}
    accts["W0"] = acct(names[0][1], idle_h=100)
    write_accounts(accts)
    rechecked = []

    def recheck(e, now, sol_usd):
        rechecked.append(e["wallet"])
        return good_row(e["wallet"], quelle="warteliste", coin=e["name"])
    monkeypatch.setattr(scout, "recheck", recheck)
    rows = []
    lines = scout.auto_wallets(state, NOW + 86400, 100.0, rows)
    assert rechecked == [k] and len(rows) == 1                           # Neupruefung landet in kandidaten.csv
    assert f"Haru: {k}" in active_lines() and any("ersetzt **W0**" in l for l in lines)
    assert list(csv.DictReader(open(scout.WAIT_FILE, encoding="utf-8"))) == []


def test_warteliste_neupruefung_faellt_durch(sandbox, monkeypatch, no_bots):
    write_wallets(10)
    k = addr("Kand")
    os.makedirs("scout", exist_ok=True)
    with open(scout.WAIT_FILE, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(scout.WAIT_HEADER)
        w.writerow([NOW - 86400, NOW - 86400, k, "Kand", "frueh", 20, 25, 8, 0.5, 30, 2])
    monkeypatch.setattr(scout, "recheck", lambda e, now, s: good_row(k, inaktiv_h=40))
    lines = scout.auto_wallets(scout.load_state(), NOW, 100.0, [])
    assert any("gestrichen" in l and "Aktivitaet" in l for l in lines)
    assert len(cb.load_wallets()) == 10 and list(csv.DictReader(open(scout.WAIT_FILE, encoding="utf-8"))) == []


def test_frische_ablehnung_streicht_von_der_warteliste(sandbox, no_bots):
    names = write_wallets(22)
    write_accounts({n: acct(a) for n, a in names})
    k = addr("Kand")
    state = scout.load_state()
    scout.auto_wallets(state, NOW, 100.0, [good_row(k)])
    assert k in open(scout.WAIT_FILE, encoding="utf-8").read()
    scout.auto_wallets(state, NOW + 3600, 100.0, [good_row(k, punkte=-5)])
    assert k not in open(scout.WAIT_FILE, encoding="utf-8").read()


def test_schalter_aus_aendert_nichts(sandbox, monkeypatch, no_bots):
    monkeypatch.setattr(scout, "AUTO_AUFNAHME", False)
    write_wallets(5)
    assert scout.auto_wallets(scout.load_state(), NOW, 100.0, [good_row(addr("Kand"))]) == []
    assert len(cb.load_wallets()) == 5 and not os.path.exists(scout.WAIT_FILE) and sandbox["git"] == []
    assert "aus" in scout.auto_status_line()


def test_push_fehlgeschlagen_kandidat_bleibt_wartend(sandbox, monkeypatch, no_bots):
    write_wallets(5)
    remote = open(cb.WALLET_FILE, encoding="utf-8").read()
    orig = scout.core._git

    def git(*args):                                  # wie echtes Git: checkout holt den Stand von origin/main
        res = orig(*args)
        if args[0] == "checkout":
            open(cb.WALLET_FILE, "w", encoding="utf-8").write(remote)
        if args[0] == "push":
            res.returncode = 1
        return res
    monkeypatch.setattr(scout.core, "_git", git)
    k = addr("Kand")
    state = scout.load_state()
    lines = scout.auto_wallets(state, NOW, 100.0, [good_row(k)])
    assert any("nicht gespeichert" in l for l in lines)
    assert state["auto_aenderungen"] == [] and k in open(scout.WAIT_FILE, encoding="utf-8").read()
    assert open(cb.WALLET_FILE, encoding="utf-8").read() == remote          # nichts halb Gespeichertes
    assert sum(a[0] == "push" for a in sandbox["git"]) == 3


def test_zu_ersetzende_wallet_inzwischen_von_hand_entfernt(sandbox):
    names = write_wallets(22)
    plan = {"name": "Kand", "adresse": addr("Kand"), "grund": "g",
            "raus": {"name": "W0", "adresse": names[0][1], "grund": "still"}}
    with open(cb.WALLET_FILE, encoding="utf-8") as f:
        text = f.read().replace(f"W0: {names[0][1]}", f"# W0: {names[0][1]}   <- entfernt von Hand")
    open(cb.WALLET_FILE, "w", encoding="utf-8").write(text)
    assert scout.apply_wallet_changes([plan], "04.10.", set()) == []    # nichts doppelt, Limit bleibt
    assert addr("Kand") not in open(cb.WALLET_FILE, encoding="utf-8").read()


def test_scout_lauf_mit_automatik(monkeypatch, sandbox, no_bots):
    """Komplette Schicht: Kandidat aus der Suche wird aufgenommen, git committet getrennt copy_wallets.txt und scout/."""
    write_wallets(5)
    k = addr("Kand")
    monkeypatch.setattr(scout, "search", lambda state, now, sol: ([], [good_row(k)], []))
    scout.run()
    assert f"Kand: {k}" in active_lines()
    assert git_adds(sandbox["git"]) == [(cb.WALLET_FILE,), (scout.SCOUT_DIR,)]
    titles = [t for t, _ in sandbox["discord"]]
    assert "🔁 Wallet-Scout: Copy-Wallets automatisch geaendert" in titles
    assert any("Automatik:** an | heute 1 von 3" in text for t, text in sandbox["discord"] if t == "🔭 Wallet-Scout")


def test_zu_wenig_transaktionen_wird_nicht_gemerkt(monkeypatch):
    """Leere Helius-Antwort sieht aus wie 'zu wenig Transaktionen' - nicht dauerhaft speichern."""
    os.makedirs("scout")
    open(scout.LIST_FILE, "w", encoding="utf-8").write(f"{addr('ListA')}\n")
    calls = []
    monkeypatch.setattr(scout, "stage1", lambda w, now, idle=None: (calls.append(w) or {"_page": []},
                                                                    "zu wenig Transaktionen"))
    state = scout.load_state()
    scout.check_list(state, NOW, 100.0)
    scout.check_list(state, NOW, 100.0)
    assert len(calls) == 2


# ================================================================ Lockerung 05.10.

def test_stille_wallets_ohne_ersatz_entfernt_hoechstens_drei(sandbox, no_bots):
    names = write_wallets(22)
    accts = {n: acct(a) for n, a in names}
    for i, h in ((2, 80), (3, 100), (4, 75), (5, 90)):
        accts[f"W{i}"] = acct(names[i][1], idle_h=h)
    accts["W6"] = acct(names[6][1], idle_h=71)                          # knapp unter 72 h: bleibt
    write_accounts(accts)
    state = scout.load_state()
    lines = scout.auto_wallets(state, NOW, 100.0, [])
    assert [e["raus"]["name"] for e in state["auto_aenderungen"]] == ["W3", "W5", "W2"]   # laengste Pause zuerst
    text = open(cb.WALLET_FILE, encoding="utf-8").read()
    assert f"# W3: {names[3][1]}   <- entfernt" in text and "ohne Ersatz" in text
    assert len(cb.load_wallets()) == 19 and "W4: " + names[4][1] in active_lines()
    assert sum(l.startswith("➖") and "ohne Ersatz" in l for l in lines) == 3
    assert no_bots["calls"] == [] and git_adds(sandbox["git"]) == [(cb.WALLET_FILE,)]   # keine Helius-Abfrage


def test_kandidat_ersetzt_stille_wallet_statt_zwei_aenderungen(sandbox, no_bots):
    names = write_wallets(22)
    accts = {n: acct(a) for n, a in names}
    accts["W2"] = acct(names[2][1], idle_h=80)
    accts["W3"] = acct(names[3][1], idle_h=90)
    write_accounts(accts)
    state = scout.load_state()
    scout.auto_wallets(state, NOW, 100.0, [good_row(kand(0))])
    log = state["auto_aenderungen"]
    assert [(e["adresse"], e["raus"]["name"]) for e in log] == [(kand(0), "W3"), (None, "W2")]
    assert len(cb.load_wallets()) == 21


def write_candidates(rows):
    header = ["zeit", "wallet", "quelle", "coin", "ergebnis", "grund", "punkte", "tx", "fehlgeschlagen", "tx_pro_h",
              "inaktiv_h", "trades", "kaeufe", "verkaeufe", "trades_pro_tag", "kauf_median_sol"]
    full = header + ["coins", "rendite_ohne_besten_pct"]
    os.makedirs("scout", exist_ok=True)
    with open(scout.CANDIDATES_FILE, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(full)
        for r in rows:
            keys = full if r.get("coins") is not None else header           # alte Zeilen: weniger Spalten
            w.writerow([r.get(k, "") for k in keys])


def test_gespeicherte_bewertungen_ohne_neue_abfrage(sandbox, monkeypatch, no_bots):
    write_wallets(10)
    old = "2026-10-03 22:00:00"
    write_candidates([
        good_row(kand(0), quelle="liste", coin="Haru", zeit=old),          # passt -> Warteliste/Aufnahme
        good_row(kand(1), zeit=old, coins=None),                           # alte Zeile ohne Coins -> nein
        good_row(kand(2), zeit=old, punkte=-3),                            # nicht im Plus -> nein
        good_row(kand(3), zeit="2026-10-01 10:00:00", punkte=-3),          # aeltere Zeile derselben Wallet ...
        good_row(kand(3), zeit=old),                                       # ... die neueste zaehlt: passt
    ])
    rechecked = []

    def recheck(e, now, sol_usd):
        rechecked.append(e["wallet"])
        return good_row(e["wallet"], quelle="warteliste", coin=e["name"])
    monkeypatch.setattr(scout, "recheck", recheck)
    state = scout.load_state()
    scout.auto_wallets(state, NOW, 100.0, [])
    assert sorted(rechecked) == sorted([kand(0), kand(3)])               # alt: vor Aufnahme frisch geprueft
    assert f"Haru: {kand(0)}" in active_lines() and len(cb.load_wallets()) == 12
    assert no_bots["calls"] == []
    rechecked.clear()
    scout.auto_wallets(state, NOW + 60, 100.0, [])                      # gleiche Zeilen: nicht noch einmal
    assert rechecked == []


def test_gespeicherte_bewertung_wartet_ohne_platz(sandbox, no_bots, monkeypatch):
    names = write_wallets(22)
    write_accounts({n: acct(a) for n, a in names})
    write_candidates([good_row(kand(0), zeit="2026-10-03 22:00:00")])
    monkeypatch.setattr(scout, "recheck", lambda *a: pytest.fail("ohne Platz keine Neupruefung"))
    scout.auto_wallets(scout.load_state(), NOW, 100.0, [])
    assert kand(0) in open(scout.WAIT_FILE, encoding="utf-8").read() and git_adds(sandbox["git"]) == []


def test_gespeicherte_zeilen_nach_laenge_wie_im_dashboard(sandbox, no_bots):
    """Echte Datei: alte Kopfzeile (25 Spalten), neuere Zeilen im Aufbau von CANDIDATES_HEADER (32 Spalten)."""
    os.makedirs("scout", exist_ok=True)
    old_header = [f"alt{i}" for i in range(25)]
    new = good_row(kand(0), zeit="2026-10-04 05:00:00")
    with open(scout.CANDIDATES_FILE, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(old_header)
        w.writerow([new.get(k, "") for k in scout.CANDIDATES_HEADER])
        w.writerow(["x"] * 27)                                           # Zwischenformat: uebersprungen
    rows = scout.stored_rows({})
    assert len(rows) == 1 and rows[0]["wallet"] == kand(0) and scout.auto_reason(rows[0]) is None


def test_kaputte_kandidaten_datei_und_fehlende_konten_stoppen_nichts(sandbox, no_bots):
    write_wallets(22)                                                    # kein copy/konten.json
    os.makedirs("scout", exist_ok=True)
    open(scout.CANDIDATES_FILE, "wb").write(b"zeit,wallet\n\xff\xfe kaputt\x00\n")
    state = scout.load_state()
    assert scout.auto_wallets(state, NOW, 100.0, []) == []
    assert len(cb.load_wallets()) == 22 and scout.STATS["fehler"] == 1


def test_hoechstens_fuenf_neupruefungen_je_lauf(sandbox, monkeypatch, no_bots):
    write_wallets(10)
    write_candidates([good_row(kand(i), zeit="2026-10-03 22:00:00") for i in range(8)])
    calls = []
    monkeypatch.setattr(scout, "recheck", lambda e, now, s: calls.append(e) or good_row(e["wallet"], punkte=-1))
    state = scout.load_state()
    scout.auto_wallets(state, NOW, 100.0, [])
    assert len(calls) == 5 and len(cb.load_wallets()) == 10            # alle durchgefallen, Rest wartet
    assert len(list(csv.DictReader(open(scout.WAIT_FILE, encoding="utf-8")))) == 3


# ================================================================ Flutschutz-Hinweis und Zeitplan (04.10.)

def write_flood(entries):
    os.makedirs("copy", exist_ok=True)
    json.dump(entries, open(cb.FLOOD_FILE, "w", encoding="utf-8"))


def flood_entry(name, hours_ago):
    t = datetime.fromtimestamp(NOW - hours_ago * 3600, timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    return {"name": name, "erstes": t, "zuletzt": t, "anzahl": 1, "pro_min": 40, "fehlgeschlagen_anteil": 0.9}


def test_flutschutz_im_copy_bot_zaehlt_als_bot(sandbox, no_bots):
    names = write_wallets(22)
    write_accounts({n: acct(a) for n, a in names})
    write_flood({names[7][1]: flood_entry("W7", 20), names[8][1]: flood_entry("W8", 8 * 24 + 1)})  # W8 zu alt
    state = scout.load_state()
    scout.auto_wallets(state, NOW, 100.0, [good_row(kand(0))])
    e = state["auto_aenderungen"][0]
    assert e["raus"]["name"] == "W7" and "Flutschutz" in e["raus"]["grund"]
    assert names[7][1] not in no_bots["calls"]                         # Hinweis ohne Helius-Abfrage
    assert "W8: " + names[8][1] in active_lines()


def test_flutschutz_kaputte_datei_wird_ignoriert(sandbox, no_bots):
    os.makedirs("copy", exist_ok=True)
    open(cb.FLOOD_FILE, "w").write("{kaputt")
    assert scout.load_flood_hints(NOW) == {}
    write_flood({"x": {"zuletzt": "kein Datum"}, "y": "falsch"})
    assert scout.load_flood_hints(NOW) == {}


def test_zeitplan_nur_einmal_je_sechs_stunden_fenster():
    h = 3600
    tag = 1_790_000_000 // 86400 * 86400                               # 00:00 UTC eines Tages
    assert scout.run_due({}, tag + 12.5 * h)
    assert scout.run_due({"letzter_lauf": "kaputt"}, tag + 12.5 * h)
    assert not scout.run_due({"letzter_lauf": tag + 12.5 * h}, tag + 17.9 * h)
    assert scout.run_due({"letzter_lauf": tag + 11.9 * h}, tag + 12.5 * h)      # neues Fenster ab 12:00
    assert scout.run_due({"letzter_lauf": tag + 6.5 * h}, tag + 13.5 * h)       # 12:29 ausgefallen -> 13:29


def test_wenn_faellig_ueberspringt_und_kompletter_lauf_merkt_sich_die_zeit(monkeypatch, sandbox, no_bots):
    write_wallets(5)
    runs = []
    monkeypatch.setattr(scout, "search", lambda state, now, sol: (runs.append(now), ([], [], []))[1])
    scout.main(["--wenn-faellig"])
    assert len(runs) == 1 and scout.load_state()["letzter_lauf"] == runs[0]
    scout.main(["--wenn-faellig"])                                     # gleiches Fenster: nichts tun
    assert len(runs) == 1
    scout.main([])                                                     # von Hand: laeuft immer
    assert len(runs) == 2


def test_nur_pruefliste_zaehlt_nicht_als_kompletter_lauf(monkeypatch, sandbox, no_bots):
    write_wallets(5)
    scout.main(["--nur-pruefliste"])
    assert "letzter_lauf" not in scout.load_state()
