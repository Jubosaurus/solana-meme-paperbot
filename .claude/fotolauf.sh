#!/bin/bash
# Aufruf: .claude/fotolauf.sh <ausgabeordner> [seiten...]
cd /c/Users/admin/solana-meme-paperbot
aus="$1"; shift
seiten="${@:-uebersicht strategie copy_trading scout flugschreiber lernen news wallets_pruefen betrieb rennbahn waechter verpasste_chancen tageszeit wissen}"
for s in $seiten; do echo "== $s"; dashboard/.venv/Scripts/python.exe tools/foto.py $s "$aus" 2>&1 | tail -3; done
echo ALLE_FERTIG
