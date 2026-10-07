"""Tabellen und kompakte Wallet-Vorschau: Daten vollstaendig, maskiert und unveraendert."""
import copy
import sys
from pathlib import Path

import pytest

pytest.importorskip("streamlit")
pd = pytest.importorskip("pandas")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "dashboard"))
import ansicht as a  # noqa: E402


def test_tabelle_alle_spalten_ohne_leerzeile_und_unveraenderte_zahlen(monkeypatch):
    html = []
    monkeypatch.setattr(a.st, "html", html.append)
    df = pd.DataFrame([
        {"Trader": "922M", "seit Start": -37.125, "wir %": -2.5, "Runde": 5,
         "Kontowert": 9.12, "Hinweise": "<script>fremd</script>"},
        {"Trader": "6ANG", "seit Start": 0.0, "wir %": None, "Runde": 1,
         "Kontowert": 10.0, "Hinweise": "ohne Ergebnis"},
    ])
    vorher = df.copy(deep=True)
    a.tabelle(df, zahlen={"Runde": (0, False, ""), "Kontowert": (2, False, " SOL")},
              pm_spalten={"seit Start": (3, " SOL"), "wir %": (1, "")}, hoehe=None,
              einzeilig={"Trader", "Hinweise"})
    pd.testing.assert_frame_equal(df, vorher)
    text = html[0]
    assert text.count("<tr>") == len(df) + 1
    assert text.count("<td ") == df.size
    for spalte in df.columns:
        assert a.e(spalte) in text
    assert a.plusminus(-37.125) in text and a.plusminus(-2.5, 1, "") in text
    assert "9,12 SOL" in text and "10,00 SOL" in text
    assert "&lt;script&gt;fremd&lt;/script&gt;" in text and "<script>fremd</script>" not in text
    assert text.index(">922M</") < text.index(">6ANG</")
    assert '<td class="text einzeilig">922M</td>' in text
    assert "max-height:none" in text and "nx-tabellenrahmen wischen" in text


def test_native_tabelle_behaelt_alle_zeilen_und_numerische_eingabe(monkeypatch):
    aufrufe, captions = [], []
    monkeypatch.setattr(a.st, "dataframe", lambda df, **kw: aufrufe.append((df, kw)))
    monkeypatch.setattr(a.st, "caption", captions.append)
    df = pd.DataFrame({"Wallet": [f"W{i}" for i in range(201)], "Rendite": [-1.2345] * 201})
    vorher = df.copy(deep=True)
    a.datentabelle(df, pm_spalten={"Rendite": (2, " SOL")})
    pd.testing.assert_frame_equal(df, vorher)
    assert len(aufrufe[0][0]) == len(df)
    assert aufrufe[0][0]["Wallet"].tolist() == df["Wallet"].tolist()
    assert set(aufrufe[0][0]["Rendite"]) == {a.plusminus(-1.2345, 2, " SOL")}
    assert "201 Zeilen – in der Tabelle scrollen" in captions[0]
    assert aufrufe[0][1]["height"] == 560
    assert aufrufe[0][1]["row_height"] == 48

@pytest.mark.parametrize("anzahl", [12, 13, 90, 200])
@pytest.mark.parametrize("hoehe", [None, 480, 560])
def test_lange_tabelle_begrenzt_auch_ohne_hoehe_und_behaelt_alle_zeilen(monkeypatch, anzahl, hoehe):
    html = []
    monkeypatch.setattr(a.st, "html", html.append)
    df = pd.DataFrame({"Wallet": [f"W{i}" for i in range(anzahl)]})
    a.tabelle(df, hoehe=hoehe)
    text = html[0]
    assert text.count("<tr>") == anzahl + 1
    assert f">W{anzahl - 1}</td>" in text
    if anzahl > 12:
        assert f"{anzahl} Zeilen – in der Tabelle scrollen" in text
        assert f"--nx-tabellenhoehe:{hoehe or 560}px" in text and "max-height:none" not in text
    else:
        assert "in der Tabelle scrollen" not in text
        assert ("max-height:none" in text) == (hoehe is None)


def test_tabellen_css_begrenzt_hoehe_auf_allen_breiten_und_fixiert_kopf():
    css = a.stil._css()
    assert "max-height: min(75vh, var(--nx-tabellenhoehe, 560px))" in css
    assert ".nx-tabelle { overflow-x: auto; overflow-y: auto;" in css
    assert ".nx-tabelle { max-height: min(75vh, 560px); }" in css
    assert ".nx-waechter-scroll { max-height: min(75vh, 560px);" in css
    assert ".nx-tabelle th { position: sticky; top: 0;" in css

@pytest.mark.parametrize("gemeinsam", [False, True])
@pytest.mark.parametrize("eigener_hinweis", [False, True])
def test_wallet_scout_hinweis_einmal_und_spalte_nur_bei_eigenem_hinweis(monkeypatch, gemeinsam, eigener_hinweis):
    html = []
    monkeypatch.setattr(a.st, "html", html.append)
    monkeypatch.setattr(a.st, "caption", lambda text: None)
    wallets = [
        {"name": f"W{i}", "ampel": "gelb" if gemeinsam else "gruen", "gruende": [],
         "schonfrist": False, "luecken": [a.SCOUT_LUECKE] if gemeinsam else []}
        for i in range(24)
    ]
    if eigener_hinweis:
        wallets[3]["luecken"].append("<script>Handelspause unbekannt</script>")
    vorher = copy.deepcopy(wallets)
    a.wallet_liste(wallets)
    text = "".join(html)
    liste = html[-1]
    assert text.count(a.SCOUT_LUECKE) == int(gemeinsam)
    if gemeinsam:
        assert "bei allen angezeigten Wallets." in text
        assert text.index(a.SCOUT_LUECKE) < text.index('class="nx-waechter')
    assert a.SCOUT_LUECKE not in liste
    assert ("<span>Hinweis</span>" in liste) == eigener_hinweis
    assert ("nx-waechter-hinweis" in liste) == eigener_hinweis
    if eigener_hinweis:
        assert "&lt;script&gt;Handelspause unbekannt&lt;/script&gt;" in liste
        assert "<script>" not in liste
    assert liste.count('role="listitem"') == 24
    assert "24 Zeilen – in der Tabelle scrollen" in liste and "nx-waechter-scroll" in liste
    assert wallets == vorher


def test_wallet_scout_hinweis_nennt_nur_betroffene_wallets(monkeypatch):
    html = []
    monkeypatch.setattr(a.st, "html", html.append)
    monkeypatch.setattr(a.st, "caption", lambda text: None)
    wallets = [
        {"name": "<b>Fehlend</b>", "ampel": "gelb", "gruende": [], "schonfrist": False,
         "luecken": [a.SCOUT_LUECKE]},
        {"name": "Geprueft", "ampel": "gruen", "gruende": [], "schonfrist": False, "luecken": []},
    ]
    a.wallet_liste(wallets)
    assert "&lt;b&gt;Fehlend&lt;/b&gt;" in html[0] and "Geprueft" not in html[0]
    assert "bei allen" not in html[0] and a.SCOUT_LUECKE not in html[1]
    assert "<span>Hinweis</span>" not in html[1]


def test_wallet_liste_rot_zuerst_zaehler_und_fremdtext_maskiert(monkeypatch):


    html, captions = [], []
    monkeypatch.setattr(a.st, "html", html.append)
    monkeypatch.setattr(a.st, "caption", captions.append)
    wallets = [
        {"name": "Gelbe", "ampel": "gelb", "gruende": [], "schonfrist": True, "luecken": []},
        {"name": "Gruene", "ampel": "gruen", "gruende": [], "schonfrist": False, "luecken": []},
        {"name": "<b>Rote</b>", "ampel": "rot", "gruende": ["<script>Grund</script>"],
         "schonfrist": False, "luecken": ["Fehlende Bewertung"]},
    ]
    vorher = copy.deepcopy(wallets)
    a.wallet_liste(wallets)
    assert wallets == vorher
    assert captions == ["1 Gelb · 1 Rot · 1 Grün · Vorschau nach gespeicherten Daten; keine Änderungen."]
    text = html[0]
    assert text.index("&lt;b&gt;Rote&lt;/b&gt;") < text.index(">Gelbe</") < text.index(">Gruene</")
    assert all(wort in text for wort in ("✗ Rot", "▲ Gelb", "✓ Grün", "Schonfrist", "Keine Regel greift"))
    assert "&lt;script&gt;Grund&lt;/script&gt;" in text and "<script>Grund</script>" not in text
    assert "Fehlende Bewertung" in text and text.count('role="listitem"') == len(wallets)
    assert "Vorschau" not in text and "pb-chip" not in text


@pytest.mark.parametrize("anzahl,spalten,ausgleich", [(0, 1, False), (1, 1, False), (2, 2, False),
    (3, 3, False), (4, 4, False), (5, 3, False), (6, 3, False), (7, 3, True), (10, 3, True), (13, 3, True)])
@pytest.mark.parametrize("optionen", [{}, {"gross": True}, {"breit": True}, {"vierer": True}])
def test_raster_waehlt_spalten_fuer_tatsaechliche_kartenanzahl(monkeypatch, anzahl, spalten, ausgleich, optionen):
    html = []
    monkeypatch.setattr(a.st, "html", html.append)
    karten = [a.karte(f"Karte {i}", str(i)) for i in range(anzahl)]
    vorher = karten.copy()
    a.raster(iter(karten), **optionen)
    assert karten == vorher
    text = html[0]
    assert f"spalten-{spalten}" in text
    assert (" ausgleich" in text) == ausgleich
    assert (" handy-paar" in text) == (anzahl >= 4)
    assert (" vierer" in text) == (anzahl == 4)
    assert text.count('class="pb-karte') == anzahl
    assert all(k in text for k in karten)


def test_kompaktes_protokoll_behaelt_namen_details_und_werte(monkeypatch):
    html = []
    monkeypatch.setattr(a.st, "html", html.append)
    eintraege = [{"name": "<b>Langes Experiment</b>", "detail": "Strategie", "wert": -1.234,
                  "rechts_unten": "seit Start"}]
    vorher = copy.deepcopy(eintraege)
    a.protokoll(eintraege, scroll=False)
    a.protokoll(eintraege, scroll=False, kompakt=True)
    assert html[1].replace(" nx-kurzprotokoll", "") == html[0]
    assert "&lt;b&gt;Langes Experiment&lt;/b&gt;" in html[1]
    assert a.pm_html(-1.234) in html[1]
    assert "Strategie" in html[1] and "seit Start" in html[1]
    assert eintraege == vorher


@pytest.mark.parametrize("ampel", list(a.AMPEL_ZEICHEN))
def test_urteilschips_behalten_wortlaut_und_zeigen_uhr_statt_auslassung(ampel):
    v = {"ampel": ampel, "tendenz": "besser", "im_plus": True,
         "kosten": {"ampel": "zu_frueh", "tendenz": "schlechter", "im_plus": False}}
    vorher = copy.deepcopy(v)
    text = a.urteil_chip(v)
    assert text.count('class="pb-chip') == 2
    assert '<b>roh:</b>' in text and '<b>mit Kosten:</b>' in text
    assert a.e(a.rechnung.urteil_kurz(v)) in text
    assert a.e(a.rechnung.urteil_kurz({**v, **v["kosten"]})) in text
    assert "…" not in text
    assert text.count('class="nx-urteil-symbol"') == (2 if ampel == "zu_frueh" else 1)
    assert 'alt="" aria-hidden="true"' in text
    assert v == vorher


def test_tabellen_css_verhindert_umbruch_mitten_im_wort_und_haelt_spalten_lesbar():
    import re
    css = a.stil._css()
    regeln = re.findall(r"([^{}]+)\{([^{}]*)\}", css)
    zellregeln = [regel for selektor, regel in regeln
                 if re.search(r"\.nx-tabelle\s+(?:th|td)\b", selektor)]
    assert zellregeln
    for regel in zellregeln:
        assert not re.search(r"overflow-wrap\s*:\s*anywhere|word-break\s*:\s*(?:break-all|break-word)", regel)
    gemeinsam = next(regel for selektor, regel in regeln if selektor.strip() == ".nx-tabelle th, .nx-tabelle td")
    for eigenschaft in ("overflow-wrap: normal", "word-break: normal", "hyphens: none"):
        assert eigenschaft in gemeinsam
    table = next(regel for selektor, regel in regeln if selektor.strip() == ".nx-tabelle table")
    assert "min-width: min-content" in table
    text = next(regel for selektor, regel in regeln if selektor.strip() == ".nx-tabelle td.text")
    assert "min-width: 10ch" in text
    zahl = next(regel for selektor, regel in regeln if selektor.strip() == ".nx-tabelle td.num")
    assert "white-space: nowrap" in zahl


def test_numerische_spalten_auch_ohne_formatvorgabe_einzeilig(monkeypatch):
    html = []
    monkeypatch.setattr(a.st, "html", html.append)
    df = pd.DataFrame({"Konto": ["Endspurt viele Trades"], "Messungen": [123], "Median": [1.25]})
    vorher = df.copy(deep=True)
    a.tabelle(df)
    assert '<td class="text">Endspurt viele Trades</td>' in html[0]
    assert '<td class="num">123</td>' in html[0]
    assert '<td class="num">1.25</td>' in html[0]
    pd.testing.assert_frame_equal(df, vorher)


@pytest.mark.parametrize("anzahl", [1, 2, 3, 4, 7, 10, 13])
@pytest.mark.parametrize("experimente", [False, True])
def test_reiche_karten_maximal_zwei_spalten_ohne_schmalen_rest(monkeypatch, anzahl, experimente):
    html = []
    monkeypatch.setattr(a.st, "html", html.append)
    karten = [a.roh_kosten_karte(f"Konto {i}", "10,00 SOL", "9,99 SOL") for i in range(anzahl)]
    a.raster(karten, experimente=experimente)
    text = html[0]
    assert f"spalten-{min(anzahl, 2)}" in text and "nx-konten" in text
    assert " vierer" not in text and " ausgleich" not in text
    assert (" ungerade" in text) == bool(anzahl % 2)
    assert text.count('class="nx-duo"') == anzahl
    assert all(karte in text for karte in karten)
    css = a.stil._css()
    assert ".pb-raster.nx-konten.ungerade > .pb-karte:last-child { grid-column: 1 / -1; }" in css
    assert ".pb-raster.nx-konten, .pb-raster.handy-einspaltig { grid-template-columns: 1fr; }" in css


def test_gemischtes_raster_mit_konto_karte_bleibt_zweispaltig(monkeypatch):
    html = []
    monkeypatch.setattr(a.st, "html", html.append)
    karten = [a.roh_kosten_karte("Konto", "10 SOL", "9 SOL")] + [a.karte(str(i), "10") for i in range(3)]
    a.raster(karten)
    assert "spalten-2" in html[0] and "nx-konten" in html[0]
    assert "spalten-4" not in html[0] and " vierer" not in html[0]
