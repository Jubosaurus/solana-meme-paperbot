"""Workflows: nie zwei Schichten desselben Bots gleichzeitig (Pruefbericht 03.10.).
cancel-in-progress muss false bleiben: Der Kettenstart startet die naechste Schicht, waehrend die alte
noch laeuft; sie wartet dann, statt die alte abzubrechen."""
import pathlib
import re

import pytest

WF = pathlib.Path(__file__).resolve().parent.parent / ".github" / "workflows"


@pytest.mark.parametrize("datei, gruppe", [("bot_runner.yml", "solana-bot-repo"),
                                           ("copy_runner.yml", "copy-bot"),
                                           ("scout_runner.yml", "wallet-scout")])
def test_eine_schicht_gleichzeitig(datei, gruppe):
    text = (WF / datei).read_text(encoding="utf-8")
    m = re.search(r"^concurrency:\n\s+group:\s*(\S+)\n\s+cancel-in-progress:\s*(\S+)", text, re.M)
    assert m, f"{datei}: concurrency fehlt auf oberster Ebene"
    assert m.group(1) == gruppe and m.group(2) == "false"


def test_gruppen_verschieden():
    gruppen = [re.search(r"^concurrency:\n\s+group:\s*(\S+)", (WF / d).read_text(encoding="utf-8"), re.M).group(1)
               for d in ("bot_runner.yml", "copy_runner.yml", "scout_runner.yml")]
    assert len(set(gruppen)) == 3                       # Bots blockieren sich nicht gegenseitig


def test_scout_stuendlich_mit_faelligkeitspruefung():
    """04.10.: GitHub liess geplante Scout-Laeufe aus. Stuendlich anstossen, Scout laeuft einmal je 6-h-Fenster."""
    text = (WF / "scout_runner.yml").read_text(encoding="utf-8")
    assert "- cron: '29 * * * *'" in text
    assert re.search(r'event_name }}" = "schedule" \]; then\s+python scout_bot.py --wenn-faellig', text)


@pytest.mark.parametrize("datei, minute", [("bot_runner.yml", "17"), ("copy_runner.yml", "47")])
def test_sicherheitsnetz_stuendlich(datei, minute):
    """07.10.: Am 05.10. bekam ein Hauptbot-Lauf keinen Runner, die Kette riss 4 h. Stuendliches Sicherheitsnetz."""
    text = (WF / datei).read_text(encoding="utf-8")
    assert f"- cron: '{minute} * * * *'" in text
