"""Claude-Code-Hook (PreToolUse auf Bash/PowerShell): schuetzt git commit und git push.

- git commit: abbrechen, wenn Daten-Dateien gestaged sind (Goldene Regel 2).
- git push: vorher python -m pytest -q, bei Fehler abbrechen.

Gilt nur fuer Befehle, die Claude Code ausfuehrt. Die Bots auf GitHub, die
Scout-Automatik und das Dashboard (Seite "Wallets pruefen") committen ueber
eigene Prozesse und sind davon nicht betroffen.

Exit 2 = Befehl blockieren, Grund steht auf stderr.
"""
import json
import os
import re
import subprocess
import sys

# Daten-Dateien: exakte Pfade und Ordner (Pfade relativ zum Repo, mit /)
DATEN_DATEIEN = {
    "portfolio.json", "journal.csv", "abgelehnt.csv", "knapp_abgelehnt.csv",
    "marktphase.json", "messung.csv", "dexscreener.csv",
    "scout/status.json", "scout/kandidaten.csv", "scout/tx_pruefung.csv",
}
DATEN_ORDNER = ("verlauf/", "experimente/", "copy/", "flugschreiber/")
# Ausdruecklich erlaubt, auch wenn ein Muster oben passen wuerde
AUSNAHMEN = {"copy_wallets.txt", "scout/pruefen.txt", "scout/pruefen_tx.txt",
             "scout/warteliste.csv"}

# git [optionen] commit|push  am Anfang eines Teilbefehls
GIT_RE = r"(?:^|[;&|\n(]|\bthen\b|\bdo\b)\s*git(?:\s+-[cC]\s+\S+|\s+--\S+)*\s+{}\b"


def ist_daten(pfad):
    pfad = pfad.strip().replace("\\", "/")
    if pfad in AUSNAHMEN:
        return False
    return pfad in DATEN_DATEIEN or pfad.startswith(DATEN_ORDNER)


def git(*args, cwd):
    r = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)
    return [z for z in r.stdout.splitlines() if z.strip()]


def pruefe_commit(befehl, cwd):
    dateien = git("diff", "--cached", "--name-only", cwd=cwd)
    # git commit -a / -am / --all nimmt auch geaenderte, nicht gestagte Dateien mit
    if re.search(r"\scommit\b.*\s(-[a-zA-Z]*a[a-zA-Z]*|--all)\b", befehl):
        dateien += git("diff", "--name-only", cwd=cwd)
    # "git add ... && git commit" in einem Befehl: der Hook laeuft vorher,
    # also auch die Dateien pruefen, die das git add gleich stagen wuerde
    for args in re.findall(GIT_RE.format("add") + r"([^;&|\n]*)", befehl):
        teile = args.split()
        if any(t in ("-A", "--all", ".", "-u", "--update", ":/", "*") for t in teile):
            dateien += git("diff", "--name-only", cwd=cwd)
            dateien += git("ls-files", "--others", "--exclude-standard", cwd=cwd)
        for t in teile:
            if not t.startswith("-"):
                t = t.strip("'\"").replace("\\", "/").removeprefix("./")
                dateien.append(t if "." in t.split("/")[-1] or t.endswith("/") else t + "/")
    verboten = sorted({d for d in dateien if ist_daten(d)})
    if verboten:
        print("COMMIT BLOCKIERT (Hook git_schutz): Daten-Dateien gestaged:\n  "
              + "\n  ".join(verboten)
              + "\nNur Code und Doku committen. Rausnehmen mit: git restore --staged <datei>",
              file=sys.stderr)
        sys.exit(2)


def pruefe_push(cwd):
    r = subprocess.run([sys.executable, "-m", "pytest", "-q", "-x", "-p", "no:cacheprovider"],
                       cwd=cwd, capture_output=True, text=True)
    if r.returncode != 0:
        ende = "\n".join((r.stdout + r.stderr).splitlines()[-25:])
        print("PUSH BLOCKIERT (Hook git_schutz): Tests nicht gruen.\n" + ende, file=sys.stderr)
        sys.exit(2)


def main():
    try:
        daten = json.load(sys.stdin)
    except Exception:
        return
    befehl = (daten.get("tool_input") or {}).get("command") or ""
    cwd = os.environ.get("CLAUDE_PROJECT_DIR") or daten.get("cwd") or os.getcwd()
    if re.search(GIT_RE.format("commit"), befehl):
        pruefe_commit(befehl, cwd)
    if re.search(GIT_RE.format("push"), befehl):
        pruefe_push(cwd)


if __name__ == "__main__":
    main()
