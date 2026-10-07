"""Sicherheit (07.10.): Schluessel und Webhook-Adressen nie im Log/Discord, Begruendung bleibt eine Kommentarzeile."""
import importlib.util
import io
import os

import bot as core
import copy_bot as cb
import scout_bot as scout
from helpers import addr



def echtes_bot_modul():
    """bot.py noch einmal laden: die Testumgebung ersetzt core.discord durch einen Rekorder."""
    spec = importlib.util.spec_from_file_location("bot_echt", os.path.join(os.path.dirname(__file__), "..", "bot.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


HOOK = "https://discord.com/api/webhooks/123456789012345678/AbCdEfGhIjKlMnOpQrStUvWxYz0123456789"


def test_hide_key_webhook_auch_abgeschnitten():
    err = f"HTTPSConnectionPool(host='discord.com', port=443): Max retries exceeded with url: {HOOK[19:]}"
    for text in (err, err[:110], "x /api/webhooks/1234/ab", "/api/webhooks/"):
        out = core._hide_key(text)
        assert "AbCd" not in out and "12345678" not in out and "/api/webhooks/1234/ab" not in out
    assert "/api/webhooks/***" in core._hide_key(err)


def test_hide_key_api_key_und_umgebungswerte(monkeypatch):
    monkeypatch.setenv("JUPITER_API_KEY", "jup-geheim-12345")
    monkeypatch.setenv("DISCORD_WEBHOOK_COPY", HOOK)
    out = core._hide_key(f"wss://mainnet.helius-rpc.com/?api-key=abc123def&x=1 jup-geheim-12345 {HOOK}")
    assert "abc123def" not in out and "jup-geheim" not in out and "AbCdEf" not in out
    assert "&x=1" in out                          # Rest der Adresse bleibt lesbar


def test_hide_key_normaler_text_bleibt():
    assert core._hide_key("Kauf: PEPE +12 %") == "Kauf: PEPE +12 %"


def test_log_filter_stdout(monkeypatch):
    ziel = io.StringIO()
    monkeypatch.setattr("sys.stdout", ziel)
    monkeypatch.setattr("sys.stderr", io.StringIO())
    core.log_schutz_an()
    core.log_schutz_an()                           # zweimal: nicht doppelt verpacken
    print(f"[DISCORD] Fehler {HOOK}")
    assert "AbCdEf" not in ziel.getvalue() and "/api/webhooks/***" in ziel.getvalue()


def test_discord_fehler_ohne_webhook_im_log(monkeypatch, capsys):
    echt = echtes_bot_modul()
    monkeypatch.setattr(echt, "DISCORD_WEBHOOK_URL", HOOK)
    echt.CTX["webhook"] = None

    def post(url, **kw):
        raise echt.requests.ConnectionError(f"Max retries exceeded with url: {HOOK[19:]}")
    monkeypatch.setattr(echt.SESSION, "post", post)
    monkeypatch.setattr(echt.time, "sleep", lambda s: None)
    echt.log_schutz_an()
    echt.discord("t", "x")
    out = capsys.readouterr().out
    assert "AbCdEf" not in out and "nicht zugestellt" in out


def test_discord_text_wird_gefiltert(monkeypatch):
    gesendet = []
    echt = echtes_bot_modul()
    monkeypatch.setattr(echt, "DISCORD_WEBHOOK_URL", HOOK)
    echt.CTX["webhook"] = None

    class R:
        status_code = 204
    monkeypatch.setattr(echt.SESSION, "post", lambda url, json=None, **kw: gesendet.append(json) or R())
    echt.discord("Titel api-key=geheim99", f"Fehler bei {HOOK}")
    emb = gesendet[0]["embeds"][0]
    assert "geheim99" not in emb["title"] and "AbCdEf" not in emb["description"]


def test_begruendung_ohne_zeilenumbruch_keine_neue_aktive_zeile(tmp_path):
    kopf = addr("Alt")
    with open(cb.WALLET_FILE, "w", encoding="utf-8") as f:
        f.write(f"# Kopf\nAlt: {kopf}\n")
    boese = addr("Boese")
    plan = {"name": "Kand", "adresse": addr("Kand"),
            "grund": f"ok\nEvil: {boese}\r\nEvil2: {boese} Evil3: {boese}\x85Evil4: {boese}"}
    done = scout.apply_wallet_changes([plan], "07.10.", set())
    assert len(done) == 1
    aktiv = [l.strip() for l in open(cb.WALLET_FILE, encoding="utf-8").read().splitlines()
             if l.strip() and not l.strip().startswith("#")]
    assert aktiv == [f"Alt: {kopf}", f"{done[0]['name']}: {addr('Kand')}"]


def test_ungueltige_adresse_wird_nicht_geschrieben():
    with open(cb.WALLET_FILE, "w", encoding="utf-8") as f:
        f.write("# Kopf\n")
    plan = {"name": "Kand", "adresse": addr("Kand") + "\nEvil: " + addr("Boese"), "grund": "g"}
    assert scout.apply_wallet_changes([plan], "07.10.", set()) == []
    assert "Evil" not in open(cb.WALLET_FILE, encoding="utf-8").read()


def test_one_line():
    assert scout.one_line("a\nb\r\nc d") == "a b c d"


def test_log_filter_faellt_nie_aus(monkeypatch):
    ziel = io.StringIO()
    strom = core._SaubererStrom(ziel)
    monkeypatch.setattr(core, "_hide_key", lambda t: 1 / 0)
    assert strom.write("geheim\n") == 7                 # kein Fehler, nichts Ungefiltertes im Log
    assert ziel.getvalue() == "***\n"


def test_hide_key_version_pfad_und_nachbartext():
    out = core._hide_key("url /api/v10/webhooks/123/AbCdEf_-x?wait=1 und api-key=abc,HTTP=500")
    assert "AbCdEf" not in out and "123/" not in out
    assert "HTTP=500" in out and "wait=1" in out


def test_log_filter_writelines(monkeypatch):
    ziel = io.StringIO()
    strom = core._SaubererStrom(ziel)
    strom.writelines([f"a {HOOK}", "b"])
    assert "AbCdEf" not in ziel.getvalue()


def test_extra_embeds_werden_gefiltert(monkeypatch):
    gesendet = []
    echt = echtes_bot_modul()
    monkeypatch.setattr(echt, "DISCORD_WEBHOOK_URL", HOOK)
    echt.CTX["webhook"] = None

    class R:
        status_code = 204
    monkeypatch.setattr(echt.SESSION, "post", lambda url, json=None, **kw: gesendet.append(json) or R())
    echt.discord("t", "x", extra_embeds=[{"title": "e", "fields": [{"name": "n", "value": f"v {HOOK}"}]}])
    assert "AbCdEf" not in str(gesendet[0])
