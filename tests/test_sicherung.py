"""Sicherungstakt (seit 08.10.): hoechstens alle 5 min, nach Handel/Journal-Zeile schon nach ca. 1 min."""
import bot as core
import copy_bot as cb
from helpers import view


def test_hauptbot_sichert_ohne_handel_erst_nach_5_minuten():
    assert not core.push_faellig(1000 + 299, 1000)
    assert core.push_faellig(1000 + 300, 1000)


def test_hauptbot_sichert_nach_journal_zeile_nach_1_minute():
    pos = {"symbol": "WIN", "mint": "m1"}
    core.journal("KAUF", pos, 0.001, 0.2)
    assert core._handel_seit_push[0]
    assert not core.push_faellig(1000 + 59, 1000)
    assert core.push_faellig(1000 + 60, 1000)


def test_hauptbot_ablehnung_loest_keine_schnelle_sicherung_aus():
    core.log_reject(view(), "ZU_JUNG")
    assert not core._handel_seit_push[0]
    assert not core.push_faellig(1000 + 120, 1000)


def test_hauptbot_git_push_meldet_erfolg(sandbox):
    open(core.PORTFOLIO_FILE, "w").write("{}")
    assert core.git_push() is True


def test_copy_sichert_ohne_journal_erst_nach_5_minuten():
    assert not cb.push_faellig(1000 + 300, 1000)
    assert cb.push_faellig(1000 + 301, 1000)


def test_copy_sichert_nach_journal_zeile_nach_1_minute():
    cb.journal({"zeit": "2026-10-08 10:00:00", "aktion": "KAUF"})
    assert cb._journal_seit_push[0]
    assert not cb.push_faellig(1000 + 60, 1000)
    assert cb.push_faellig(1000 + 61, 1000)


class _Git:
    """Fake-Git, bei dem ein Teilbefehl scheitert."""
    def __init__(self, faellt):
        self.faellt, self.aufrufe = faellt, []

    def __call__(self, *args):
        self.aufrufe.append(args)
        code = 1 if args[0] in (self.faellt, "diff") else 0
        return type("R", (), {"returncode": code, "stderr": "kaputt", "stdout": ""})()


def test_hauptbot_gescheitertes_add_oder_commit_ist_kein_erfolg(monkeypatch):
    """Codex-Fund 07.10.: Fehler bei add/commit duerfen nicht als Sicherung gelten."""
    open(core.PORTFOLIO_FILE, "w").write("{}")
    for teil in ("reset", "add", "commit", "push"):
        fake = _Git(teil)
        monkeypatch.setattr(core, "_git", fake)
        assert core.git_push() is False, teil
        if teil != "commit":
            assert not any(a[0] == "commit" for a in fake.aufrufe if teil in ("reset", "add")), teil


def test_copy_gescheitertes_add_oder_commit_ist_kein_erfolg(monkeypatch):
    import os
    os.makedirs(cb.COPY_DIR, exist_ok=True)
    for teil in ("reset", "add", "commit", "push"):
        monkeypatch.setattr(core, "_git", _Git(teil))
        assert cb.git_push() is False, teil


def test_hauptbot_ausnahme_beim_push_behaelt_handelsvormerkung(clock, market, monkeypatch, sandbox):
    """Codex-Fund 07.10.: Wirft git_push, bleibt der Handel vorgemerkt (naechster Versuch nach ca. 1 min)."""
    versuche = []

    def kaputt():
        versuche.append(core._handel_seit_push[0])
        raise OSError("git weg")
    monkeypatch.setattr(core, "git_push", kaputt)
    monkeypatch.setattr(core, "SHIFT_DURATION_SECONDS", core.LOOP_SLEEP_SECONDS * 15)
    core._handel_seit_push[0] = True
    try:
        core.run()
    except OSError:
        pass                                   # das Schichtende-Speichern ruft git_push ebenfalls auf
    assert len(versuche) >= 3                  # alle ca. 60 s erneut, nicht erst nach 5 min
    assert all(versuche)
