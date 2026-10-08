"""Bundle-Check: echter Grund eines Ausfalls und fehlende Transaktionen werden nur aufgezeichnet (08.10.),
am Kauf-/Ablehnungsverhalten aendert sich nichts."""
import bot as core

MINT = "MintGrund1111111111111111111111111111111111"


def _sig(i, slot=100):
    return {"signature": f"s{i}", "slot": slot, "err": None}


def test_rpc_fehler_wird_als_grund_gemerkt(monkeypatch):
    monkeypatch.setattr(core, "HELIUS_RPC", "https://helius.invalid")
    monkeypatch.setattr(core, "rpc", lambda method, params: None)
    assert core.block0_analysis(MINT) is None
    assert core._block0_diag[MINT]["grund"] == "rpc_fehler"
    reason, info = core.bundle_dev_check(MINT)
    assert reason == "BUNDLE_CHECK_NICHT_MOEGLICH" and info == {}


def test_zu_viele_transaktionen_wird_als_grund_gemerkt(monkeypatch):
    monkeypatch.setattr(core, "HELIUS_RPC", "https://helius.invalid")
    monkeypatch.setattr(core, "rpc", lambda method, params: [_sig(i) for i in range(1000)])
    reason, info = core.bundle_dev_check(MINT)
    assert reason == "BUNDLE_CHECK_NICHT_MOEGLICH" and info == {}
    assert core._block0_diag[MINT]["grund"] == "zu_viele_transaktionen"


def test_keine_signaturen(monkeypatch):
    monkeypatch.setattr(core, "HELIUS_RPC", "https://helius.invalid")
    monkeypatch.setattr(core, "rpc", lambda method, params: [])
    assert core.block0_analysis(MINT) is None
    assert core._block0_diag[MINT]["grund"] == "keine_signaturen"


def test_ohne_helius_grund(monkeypatch):
    monkeypatch.setattr(core, "HELIUS_RPC", None)
    reason, _ = core.bundle_dev_check(MINT)
    assert reason == "BUNDLE_CHECK_NICHT_MOEGLICH"
    assert core._block0_diag[MINT]["grund"] == "kein_helius"


def test_fehlende_transaktionen_und_halter_werden_gezaehlt(monkeypatch):
    monkeypatch.setattr(core, "HELIUS_RPC", "https://helius.invalid")
    post = {"mint": MINT, "owner": "w1", "accountIndex": 1, "uiTokenAmount": {"amount": "100"}}

    def rpc(method, params):
        if method == "getSignaturesForAddress":
            return [_sig(1), _sig(2), _sig(3)]
        if method == "getTokenSupply":
            return {"value": {"amount": "1000"}}
        if method == "getTransaction":
            if params[0] == "s1":
                return {"meta": {"err": None, "preTokenBalances": [], "postTokenBalances": [post]}}
            return None                       # s2, s3 nicht abrufbar
        return None                           # Halter-Abfrage faellt aus

    monkeypatch.setattr(core, "rpc", rpc)
    res = core.block0_analysis(MINT)
    assert res["block0_wallets"] == 1
    assert res["block0_tx_fehlend"] == 2 and res["block0_halter_fehlend"] == 1
    assert core.bundle_diag_felder(MINT, "GEBUENDELT", res) == ["", "tx 2, halter 1"]


def test_diag_felder_ohne_besonderheit():
    assert core.bundle_diag_felder(MINT, "FOMO_SPRUNG", {}) == ["", ""]
    core._block0_diag[MINT] = {"grund": "rpc_fehler"}
    assert core.bundle_diag_felder(MINT, "BUNDLE_CHECK_NICHT_MOEGLICH", {}) == ["rpc_fehler", ""]
