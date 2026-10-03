"""Gemeinsame Vorbereitung: Jeder Test laeuft in einem leeren Ordner, ohne Netzwerk, ohne Git, ohne Discord."""
import copy
import os
import signal
import sys
import time

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bot as core          # noqa: E402
import copy_bot as cb       # noqa: E402
import scout_bot as scout   # noqa: E402

_CB_STATS = copy.deepcopy(cb.STATS)
_SCOUT_STATS = copy.deepcopy(scout.STATS)
_CTX = dict(core.CTX)


class NetworkBlocked(RuntimeError):
    pass


class BlockedSession:
    """Ersetzt requests.Session: jeder Zugriff wird gemerkt und schlaegt fehl."""

    def __init__(self, calls):
        self.calls = calls
        self.headers = {}

    def get(self, url, *a, **kw):
        self.calls.append(("GET", url))
        raise NetworkBlocked(f"Netzwerk im Test: GET {url}")

    def post(self, url, *a, **kw):
        self.calls.append(("POST", url))
        raise NetworkBlocked(f"Netzwerk im Test: POST {url}")


class GitResult:
    def __init__(self, returncode=0):
        self.returncode = returncode
        self.stdout = self.stderr = ""


class Clock:
    """Kuenstliche Uhr: time.sleep laesst nur die Zeit vorruecken, ohne zu warten."""

    def __init__(self):
        self.now = time.time()

    def time(self):
        return self.now

    def sleep(self, seconds):
        self.now += max(0.0, seconds)


@pytest.fixture(autouse=True)
def sandbox(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    net = []
    monkeypatch.setattr(core, "SESSION", BlockedSession(net))
    monkeypatch.setattr(core, "jup_get", lambda path: None)
    monkeypatch.setattr(core, "rpc", lambda method, params: None)
    monkeypatch.setattr(cb, "jup", lambda path: None)

    def no_ws(*a, **kw):
        net.append(("WS", a[0] if a else ""))
        raise NetworkBlocked("WebSocket im Test")
    monkeypatch.setattr(cb.websocket, "create_connection", no_ws)
    git = []

    def fake_git(*args):
        git.append(args)
        return GitResult(1 if args and args[0] == "diff" else 0)   # diff != 0: es gibt etwas zu committen
    monkeypatch.setattr(core, "_git", fake_git)
    msgs = []
    monkeypatch.setattr(core, "discord", lambda title, text, color=0, extra=None, **kw:
                        msgs.append((core.CTX["title_prefix"] + title, text)))
    monkeypatch.setattr(time, "sleep", lambda s: None)
    monkeypatch.setattr(signal, "signal", lambda *a: None)
    # Globale Zustaende zuruecksetzen
    monkeypatch.setattr(core, "STATS", core.fresh_stats())
    monkeypatch.setattr(core, "EXP_STATS", {n: core.fresh_stats() for n in core.EXPERIMENTS})
    core.CTX.clear()
    core.CTX.update(_CTX)
    for cache in (core._tok_cache, core._bundle_cache, core._block0_cache, core._shield_cache, core._reject_seen,
                  core._symbol_leaders, core._narrative_leaders, core._social_cache, core._portfolio_alarm,
                  cb._seen, cb._done, cb._rate, cb._gap):
        cache.clear()
    monkeypatch.setattr(core, "_sol_price", [0.0])
    monkeypatch.setattr(cb, "STATS", copy.deepcopy(_CB_STATS))
    monkeypatch.setattr(scout, "STATS", copy.deepcopy(_SCOUT_STATS))
    monkeypatch.setattr(core, "HELIUS_RPC", None)
    monkeypatch.setattr(core, "SOLANA_TRACKER_API_KEY", "")
    monkeypatch.setattr(scout, "BIRDEYE_API_KEY", "")
    env = {"net": net, "git": git, "discord": msgs, "path": tmp_path}
    yield env
    core.CTX.clear()
    core.CTX.update(_CTX)
    assert not net, f"Unerwarteter Netzwerkzugriff: {net[:3]}"


@pytest.fixture
def market(monkeypatch):
    """Fake-Jupiter fuer Hauptbot und Copy-Bot."""
    from helpers import Market
    m = Market()
    monkeypatch.setattr(core, "quote", m.quote)
    monkeypatch.setattr(core, "jup_tokens", m.jup_tokens)
    monkeypatch.setattr(cb, "quote_out", m.quote)
    return m


@pytest.fixture
def clock(monkeypatch):
    c = Clock()
    monkeypatch.setattr(time, "time", c.time)
    monkeypatch.setattr(time, "sleep", c.sleep)
    return c
