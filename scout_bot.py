"""Wallet-Scout: findet Kandidaten fuer das Copy Trading und erstellt eine Rangliste. Kauft und aendert nichts.

Ablauf (alle 6 Stunden):
1. Gewinner-Coins aus unseren eigenen Daten (Hauptstrategie, Experimente, Kursverlaeufe): Hoch >= 3x.
2. Kandidaten finden: fruehe Kaeufer dieser Coins (Helius, ohne die Kaeufer im ersten Block) und, falls
   verfuegbar, die Top-Trader laut Birdeye (Gratis-Tarif: CU-Zaehler, Stopp bei 28.000 CUs im Monat).
3. Stufe 1 (1 Helius-Credit je Wallet): letzte 1.000 Transaktionen mit Fehlerstatus -> Bots und stille Wallets raus.
4. Stufe 2 (rund 60 Credits je Wallet): letzte 60 erfolgreiche Transaktionen mit der Logik des Copy-Bots auswerten.
5. Rangliste in Discord und in scout/kandidaten.csv. Die Entscheidung trifft der Mensch.
"""
import argparse
import csv
import glob
import json
import os
import time
from datetime import datetime, timezone
from statistics import median

import requests

import bot as core
import copy_bot as cb

core.HELIUS_INTERVAL = 0.5          # Scout hoechstens ~2 Helius-Anfragen/s, laeuft parallel zu den anderen Bots

SCOUT_DIR = "scout"
STATE_FILE = os.path.join(SCOUT_DIR, "status.json")
CANDIDATES_FILE = os.path.join(SCOUT_DIR, "kandidaten.csv")
DISCORD_WEBHOOK_SCOUT = (os.environ.get("DISCORD_WEBHOOK_SCOUT") or os.environ.get("DISCORD_WEBHOOK_COPY") or "").strip()
BIRDEYE_API_KEY = (os.environ.get("BIRDEYE_API_KEY") or "").strip()
BIRDEYE_BASE = "https://public-api.birdeye.so"
BIRDEYE_CU = {"top_traders": 35}