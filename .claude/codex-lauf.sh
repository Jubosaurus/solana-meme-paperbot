#!/bin/bash
# Aufruf: .claude/codex-lauf.sh <kartendatei> [ausgabe]
# WICHTIG: "< /dev/null" noetig, sonst wartet codex exec auf Eingabe ("Reading additional input from stdin...") und haengt.
karte="$1"; aus="${2:-/tmp/codex-out.txt}"
cd /c/Users/admin/solana-meme-paperbot
codex exec -p sol -C ../paperbot-codex -s workspace-write -o "$aus" "Lies und erledige die Auftragskarte unten. Regeln aus AGENTS.md gelten.

$(cat "$karte")" < /dev/null
