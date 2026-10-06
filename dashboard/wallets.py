"""Wallets pruefen: die EINZIGE Stelle im Dashboard, die schreibt - und auch hier nur an das Ende von
scout/pruefen.txt. Nie loeschen oder umschreiben, nie eine andere Datei committen. copy_wallets.txt wird hier nicht
angefasst: die Aufnahme ins Copy Trading macht seit 04.10. die Automatik im Scout (auf GitHub).

Kein Streamlit-Import (Tests benutzen das Modul direkt). Keine Schluessel: git und gh benutzen die
Anmeldung des Rechners.
"""
import csv
import re
import socket
import subprocess
from datetime import datetime
from pathlib import Path

import rechnung

PRUEFLISTE = "scout/pruefen.txt"
COPY_LISTE = "copy_wallets.txt"
KANDIDATEN = "scout/kandidaten.csv"
WARTELISTE = "scout/warteliste.csv"
SCOUT_WORKFLOW = "scout_runner.yml"
MAX_ADRESSEN = 20
MAX_NAME = 30
ALPHABET = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
ADRESSE = re.compile(r"[1-9A-HJ-NP-Za-km-z]{32,44}")     # wie scout_bot.load_list
LAUFEND = {"in_progress", "queued", "waiting", "pending", "requested"}
COMMIT_TEXT = "Wallet-Pruefliste: {n} Adresse(n) per Dashboard [skip ci]"


# ================================================================ Zugriff nur vom PC selbst

def eigene_adressen():
    """IP-Adressen dieses Rechners (wer ueber die Heimnetz-Adresse des PCs im PC-Browser surft, ist auch lokal)."""
    adressen = {"127.0.0.1", "::1", "localhost"}
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None):
            adressen.add(str(info[4][0]).split("%")[0])
    except OSError:
        pass
    return adressen


def ist_lokal(ip, header=None, eigene=None):
    """True nur, wenn der Zugriff vom PC selbst kommt. Streamlit meldet bei localhost None (ip_address).
    Ein Proxy-Kopf (X-Forwarded-For o. ae.) heisst: nicht lokal. Unbekannte Adresse = nicht lokal."""
    if header and any(k.lower() in ("x-forwarded-for", "forwarded", "x-real-ip") for k in header.keys()):
        return False
    if ip is None:
        return True
    eigene = eigene_adressen() if eigene is None else eigene
    return str(ip).split("%")[0] in eigene


# ================================================================ Adressen pruefen

def ist_solana_adresse(text):
    """Base58 mit 32-44 Zeichen, die wirklich zu 32 Byte (ein Solana-Schluessel) auflosen."""
    if not re.fullmatch(r"[1-9A-HJ-NP-Za-km-z]{32,44}", text or ""):
        return False
    zahl = 0
    for zeichen in text:
        zahl = zahl * 58 + ALPHABET.index(zeichen)
    fuehrende_nullen = len(text) - len(text.lstrip("1"))
    laenge = fuehrende_nullen + (zahl.bit_length() + 7) // 8 if zahl else fuehrende_nullen
    return laenge == 32


def kurzname(adresse):
    return adresse[:4] + "…" + adresse[-4:]


def _lies(repo, name):
    try:
        return (Path(repo) / name).read_text(encoding="utf-8")
    except OSError:
        return ""


def bekannte_adressen(repo=None):
    """(Adressen aus copy_wallets.txt, auch auskommentierte; Adressen aus scout/pruefen.txt)."""
    repo = repo or rechnung.REPO
    return (set(ADRESSE.findall(_lies(repo, COPY_LISTE))), set(ADRESSE.findall(_lies(repo, PRUEFLISTE))))


def bekannte_namen(repo=None):
    """Alle Namen aus copy_wallets.txt (auch auskommentierte), scout/pruefen.txt und scout/warteliste.csv,
    kleingeschrieben. Der Copy-Bot fuehrt Konten nach Namen: ein doppelter Name wuerde zwei Wallets vermischen."""
    repo = repo or rechnung.REPO
    namen = set()
    for datei in (COPY_LISTE, PRUEFLISTE):
        for zeile in _lies(repo, datei).splitlines():
            name, trenner, rest = zeile.strip().lstrip("#").strip().partition(":")
            if trenner and ADRESSE.match(rest.strip()):
                namen.add(name.strip().lower())
    try:
        with open(Path(repo) / WARTELISTE, newline="", encoding="utf-8") as f:
            namen |= {(r.get("name") or "").strip().lower() for r in csv.DictReader(f)}
    except OSError:
        pass
    namen.discard("")
    return namen


def eingabe_pruefen(text, repo=None, bekannt=None, namen=None):
    """Zerlegt die Eingabe (eine Zeile je Wallet, 'Name: Adresse' oder nur 'Adresse').
    Rueckgabe: (gueltig [(name, adresse)], abgelehnt [(zeile, grund)]). Es wird nichts geschrieben."""
    in_copy, in_liste = bekannt if bekannt is not None else bekannte_adressen(repo)
    if namen is None:
        namen = bekannte_namen(repo) if bekannt is None else set()
    namen = set(namen)
    gueltig, abgelehnt, gesehen = [], [], set()
    for roh in (text or "").splitlines():
        zeile = roh.strip()
        if not zeile or zeile.startswith("#"):
            continue
        name, trenner, rest = zeile.partition(":")
        name, adresse = (name.strip(), rest.strip()) if trenner else ("", zeile)
        name = re.sub(r"[\x00-\x1f#]", "", name).strip()
        wie_adresse = bool(ADRESSE.search(name))
        name = name[:MAX_NAME]
        anzeige = zeile if len(zeile) <= 60 else zeile[:57] + "…"
        if wie_adresse:
            abgelehnt.append((anzeige, "Der Name sieht wie eine Adresse aus. Format: „Name: Adresse“"))
        elif not ist_solana_adresse(adresse):
            abgelehnt.append((anzeige, "Keine gültige Solana-Adresse (Base58, 32–44 Zeichen, nichts davor oder dahinter)"))
        elif adresse in gesehen:
            abgelehnt.append((anzeige, "Doppelt in dieser Eingabe"))
        elif adresse in in_copy:
            abgelehnt.append((anzeige, "Steht schon in copy_wallets.txt (aktiv oder früher entfernt)"))
        elif adresse in in_liste:
            abgelehnt.append((anzeige, "Steht schon in der Prüfliste"))
        elif name and name.lower() in namen:
            abgelehnt.append((anzeige, f"Der Name „{name}“ ist schon vergeben (copy_wallets.txt, Prüfliste oder "
                                       "Warteliste). Bitte einen anderen Namen wählen, z. B. mit Adressanfang"))
        elif len(gueltig) >= MAX_ADRESSEN:
            abgelehnt.append((anzeige, f"Mehr als {MAX_ADRESSEN} Adressen auf einmal – bitte später noch einmal"))
        else:
            gesehen.add(adresse)
            if name:
                namen.add(name.lower())
            gueltig.append((name or kurzname(adresse), adresse))
    return gueltig, abgelehnt


# ================================================================ In die Pruefliste schreiben

def _git(repo, *args, timeout=90):
    res = subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, timeout=timeout)
    return res.returncode == 0, (res.stderr or res.stdout).strip()[:300]


def _anhaengen(pfad, gueltig, jetzt):
    """Haengt die Zeilen an das Ende der Datei an (Zeilenende wie in der Datei). Rueckgabe: neuer Text."""
    alt = pfad.read_bytes() if pfad.exists() else b""
    nl = b"\r\n" if b"\r\n" in alt else b"\n"
    neu = b"" if not alt or alt.endswith(b"\n") else nl
    neu += f"# {jetzt:%d.%m.%Y %H:%M} per Dashboard".encode("utf-8") + nl
    neu += b"".join(f"{n}: {a}".encode("utf-8") + nl for n, a in gueltig)
    with open(pfad, "ab") as f:
        f.write(neu)


def zur_pruefung_schicken(gueltig, repo=None, jetzt=None):
    """Haengt gueltige (name, adresse) an scout/pruefen.txt an, pull --rebase, committet NUR diese Datei, push.
    Bei jedem Fehler wird die eigene Aenderung wieder zurueckgenommen. Rueckgabe: (ok, Meldung)."""
    repo = Path(repo or rechnung.REPO)
    jetzt = jetzt or datetime.now(rechnung.BERLIN)
    if not gueltig:
        return False, "Nichts zu speichern."
    datei = repo / PRUEFLISTE
    try:
        ok, msg = _git(repo, "status", "--porcelain", "--", PRUEFLISTE)
        if not ok:
            return False, f"Git antwortet nicht: {msg}"
        if msg:
            return False, "scout/pruefen.txt ist auf diesem Rechner schon geändert und noch nicht hochgeladen. " \
                          "Nichts wurde gespeichert."
        ok, offen = _git(repo, "rev-list", "--count", "@{u}..HEAD")
        if not ok or offen.strip() != "0":
            return False, "Auf diesem Rechner gibt es noch nicht hochgeladene Commits. Damit sie nicht "                           "mitgeschickt werden, wurde nichts gespeichert."
        ok, msg = _git(repo, "pull", "--rebase", "--autostash", "-q", timeout=120)
        if not ok:
            _git(repo, "rebase", "--abort")
            return False, f"Neueste Daten konnten nicht geholt werden. Nichts wurde gespeichert. ({msg})"
        # nach dem Pull noch einmal gegen den frischen Stand pruefen (jemand war evtl. schneller)
        gueltig, _ = eingabe_pruefen("\n".join(f"{n}: {a}" for n, a in gueltig), repo)
        if not gueltig:
            return False, "Alle Adressen stehen inzwischen schon in einer der Listen. Nichts wurde gespeichert."
        _anhaengen(datei, gueltig, jetzt)
        text = COMMIT_TEXT.format(n=len(gueltig))
        ok, msg = _git(repo, "commit", "-q", "-m", text, "--", PRUEFLISTE)
        if not ok:
            _verwerfen(repo, eigener_commit=False)
            return False, f"Speichern (commit) fehlgeschlagen. Nichts wurde geändert. ({msg})"
        for _ in range(3):                    # die Bots pushen jede Minute: bei Ablehnung neu aufsetzen
            ok, msg = _git(repo, "push", "-q", timeout=120)
            if ok:
                return True, f"{len(gueltig)} Adresse(n) gespeichert und hochgeladen."
            ok2, _ = _git(repo, "pull", "--rebase", "--autostash", "-q", timeout=120)
            if not ok2:
                _git(repo, "rebase", "--abort")
                break
        _verwerfen(repo, eigener_commit=True)
        return False, f"Hochladen fehlgeschlagen, deine Eingabe wurde nicht gespeichert. Bitte später noch " \
                      f"einmal versuchen. ({msg})"
    except (OSError, subprocess.SubprocessError) as err:
        _verwerfen(repo, eigener_commit=_eigener_commit_da(repo))
        return False, f"Fehler: {str(err)[:200]}. Die eigene Änderung wurde zurückgenommen."


def _eigener_commit_da(repo):
    """True, wenn der oberste Commit unserer ist und noch nicht hochgeladen wurde."""
    try:
        ok, msg = _git(repo, "log", "-1", "--format=%s")
        ok2, offen = _git(repo, "rev-list", "--count", "@{u}..HEAD")
    except (OSError, subprocess.SubprocessError):
        return False
    return ok and ok2 and msg.startswith("Wallet-Pruefliste:") and offen.strip() not in ("", "0")


def _verwerfen(repo, eigener_commit):
    """Nimmt nur die eigene Aenderung an scout/pruefen.txt zurueck (nie andere Dateien)."""
    try:
        if eigener_commit:
            _git(repo, "reset", "-q", "--soft", "HEAD~1")
        _git(repo, "reset", "-q", "--", PRUEFLISTE)
        _git(repo, "checkout", "-q", "--", PRUEFLISTE)
    except (OSError, subprocess.SubprocessError):
        pass


def scout_anstossen(repo=None):
    """Startet einen Scout-Lauf im Modus "pruefliste" (nur die Pruefliste, ohne Coin-Suche und Birdeye) per gh,
    aber nur wenn gerade keiner laeuft. Rueckgabe: (gestartet, Meldung)."""
    repo = repo or rechnung.REPO
    spaeter = "Die Adressen werden beim nächsten Scout-Lauf geprüft (alle 6 Stunden)."
    try:
        res = subprocess.run(["gh", "run", "list", "--workflow", SCOUT_WORKFLOW, "--limit", "10", "--json", "status"],
                             cwd=repo, capture_output=True, text=True, timeout=60)
        if res.returncode != 0:
            return False, f"Scout-Lauf konnte nicht gestartet werden (gh: {res.stderr.strip()[:100]}). " + spaeter
        status = re.findall(r'"status"\s*:\s*"([a-z_]+)"', res.stdout)
        if any(s in LAUFEND for s in status):
            return False, "Ein Scout-Lauf läuft gerade. Die neuen Adressen werden beim nächsten Lauf geprüft."
        res = subprocess.run(["gh", "workflow", "run", SCOUT_WORKFLOW, "-f", "modus=pruefliste"], cwd=repo,
                             capture_output=True, text=True, timeout=60)
        if res.returncode != 0:
            return False, f"Scout-Lauf konnte nicht gestartet werden (gh: {res.stderr.strip()[:100]}). " + spaeter
        return True, "Scout-Lauf gestartet. Das Ergebnis steht in 5–15 Minuten unten in der Liste."
    except (OSError, subprocess.SubprocessError):
        return False, "Scout-Lauf konnte nicht gestartet werden (gh nicht erreichbar). " + spaeter


# ================================================================ Liste mit Ergebnissen

def _scout_zeilen(repo):
    """Zeilen aus scout/kandidaten.csv als dict. Die Datei hat Zeilen mit altem (25 Spalten) und neuem Aufbau
    (32 Spalten); jede Zeile wird nach ihrer Laenge zugeordnet, andere werden ignoriert."""
    try:
        with open(Path(repo) / KANDIDATEN, newline="", encoding="utf-8") as f:
            rows = list(csv.reader(f))
    except OSError:
        return []
    if not rows:
        return []
    kopf = rows[0]
    out = []
    for r in rows[1:]:
        if len(r) in (len(rechnung.SCOUT_HEADER), len(rechnung.SCOUT_HEADER) - 1):
            out.append(dict(zip(rechnung.SCOUT_HEADER, r)))
        elif len(r) == len(kopf):
            out.append(dict(zip(kopf, r)))
    return out


def pruefliste_status(repo=None):
    """Alle Adressen aus scout/pruefen.txt mit Status und Scout-Ergebnis (neueste Bewertung aus der Liste)."""
    repo = repo or rechnung.REPO
    neueste = {}
    for d in _scout_zeilen(repo):
        if d.get("quelle") == "liste" and d.get("wallet") and d.get("zeit", "") >= neueste.get(d["wallet"], {}).get("zeit", ""):
            neueste[d["wallet"]] = d
    aktiv = {a for _, a in rechnung.aktive_wallets(repo)}
    in_copy_je = set(ADRESSE.findall(_lies(repo, COPY_LISTE)))
    wartend = set(ADRESSE.findall(_lies(repo, WARTELISTE)))
    zeilen, gesehen = [], set()
    for roh in _lies(repo, PRUEFLISTE).splitlines():
        zeile = roh.strip()
        if not zeile or zeile.startswith("#"):
            continue
        for adresse in ADRESSE.findall(zeile):
            if adresse in gesehen:
                continue
            gesehen.add(adresse)
            kopf = zeile.split(":", 1)[0].strip() if ":" in zeile and adresse not in zeile.split(":", 1)[0] else ""
            d = neueste.get(adresse)
            zeilen.append({
                "name": kopf or kurzname(adresse), "wallet": adresse,
                "status": "geprüft" if d else "wartet",
                "copy": "aktiv" if adresse in aktiv else "früher" if adresse in in_copy_je
                        else "Warteliste" if adresse in wartend else "",
                "zeit": d["zeit"] if d else None,
                "ergebnis": d["ergebnis"] if d else None,
                "grund": (d.get("grund") or "") if d else "",
                "punkte": rechnung.as_float(d.get("punkte"), None) if d else None,
                "haltedauer_min": rechnung.as_float(d.get("haltedauer_median_min"), None) if d else None,
                "schnell_anteil": rechnung.as_float(d.get("schnelle_verkaeufe_anteil"), None) if d else None,
                "rendite_ohne_besten": rechnung.as_float(d.get("rendite_ohne_besten_pct") or
                                                         d.get("rendite_ohne_beste_pct"), None) if d else None,
                "coins": rechnung.as_float(d.get("coins_abgeschlossen"), None) if d else None,
            })
    return zeilen
