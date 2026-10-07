"""Bausteine der Darstellung (Nexus Core): Seitenkopf, Karten, Roh/Kosten-Karten, Tabellen, Leer- und Fehlerzustand,
Mini-Kurven, Ringe, Aktivitaetsprotokoll, Diagramme.

Plus/Minus immer mit Pfeil und Vorzeichen (nie Farbe allein). Alle Texte aus den Daten (Coin-Namen kommen
von der Blockchain!) werden mit html.escape eingefuegt. Farben und CSS stehen in stil.py.
"""
import base64
import html
import time

import altair as alt
import pandas as pd
import streamlit as st

import rechnung
import stil

AMPEL_KLASSE = {"besser": "gut", "schlechter": "schlecht", "gemischt": "achtung", "zu_frueh": "",
                "basis": "", "keine_daten": ""}
AMPEL_ZEICHEN = {"besser": "✓", "schlechter": "✗", "gemischt": "≈", "zu_frueh": "⌛", "basis": "–", "keine_daten": "–"}
STATUS = {"ok": ("gut", "läuft"), "achtung": ("achtung", "verzögert"), "kaputt": ("schlecht", "steht")}


def e(text):
    return html.escape(str(text), quote=True)


# ================================================================ Text-Bausteine

def plusminus(x, stellen=3, einheit=" SOL"):
    """Gewinn/Verlust als Text: Pfeil + Vorzeichen (fuer Tabellen)."""
    if x is None:
        return "–"
    t = rechnung.zahl(x, stellen, vorzeichen=True) + einheit
    return ("▲ " if t.startswith("+") else "▼ " if t.startswith("−") else "● ") + t


def pm_html(x, stellen=3, einheit=" SOL"):
    """Wie plusminus, mit Farb-Akzent."""
    t = plusminus(x, stellen, einheit)
    klasse = "pb-plus" if t.startswith("▲") else "pb-minus" if t.startswith("▼") else "pb-null"
    return f'<span class="{klasse}">{e(t)}</span>'


def txt(x, stellen=1, vorzeichen=False, einheit=""):
    """Zahl als deutscher Text fuer Tabellen; fehlender Wert = '–'."""
    return "–" if x is None else rechnung.zahl(x, stellen, vorzeichen) + einheit


def vor(ts):
    return "–" if ts is None else "vor " + rechnung.dauer_text(max(0, time.time() - ts))


def urteil_text(v):
    return f"{AMPEL_ZEICHEN[v['ampel']]} {rechnung.urteil_beide(v)}"


def urteil_roh(v):
    return rechnung.urteil_kurz(v)


def urteil_mit_kosten(v):
    """Urteil mit Kostenaufschlag; die Vergleichsbasis (Kontrollgruppe) hat keines und bleibt gleich."""
    k = v.get("kosten")
    return rechnung.urteil_kurz({**v, **k}) if k else rechnung.urteil_kurz(v)


def _urteil_zeichen(ampel):
    if ampel == "zu_frueh":
        return f'<img class="nx-urteil-symbol" src="{stil.icon_uri("zeit")}" alt="" aria-hidden="true"/>'
    return e(AMPEL_ZEICHEN[ampel])


def urteil_chip(v):
    """Urteil roh und mit Kosten untereinander (umbrechend, nie abgeschnitten)."""
    zeilen = [("roh", rechnung.urteil_kurz(v), v["ampel"])]
    k = v.get("kosten")
    if k:
        zeilen.append(("mit Kosten", rechnung.urteil_kurz({**v, **k}), k["ampel"]))
    return '<div class="nx-urteil">' + "".join(
        f'<span class="pb-chip {AMPEL_KLASSE[ampel]}">{_urteil_zeichen(ampel)} <b>{e(art)}:</b> {e(text)}</span>'
        for art, text, ampel in zeilen) + "</div>"


def chip(text, klasse=""):
    return f'<span class="pb-chip {klasse}">{e(text)}</span>'


# ================================================================ Grafik-Bausteine (SVG, ohne JavaScript)

def _als_bild(svg, klasse, alt_text=""):
    """st.html filtert eingebettetes SVG heraus; als Bild (data-URI) wird es angezeigt."""
    daten = base64.b64encode(svg.encode("utf-8")).decode("ascii")
    return f'<img class="{klasse}" src="data:image/svg+xml;base64,{daten}" alt="{e(alt_text)}"/>'


def sparkline(werte, breite=120, hoehe=40):
    """Mini-Kurve. Farbe nach Richtung (Ende gegen Anfang); Richtung steht zusaetzlich als Pfeil in der Karte."""
    werte = [w for w in werte if w is not None]
    if len(werte) < 2:
        return ""
    lo, hi = min(werte), max(werte)
    spanne = (hi - lo) or 1.0
    pts = [(i / (len(werte) - 1) * (breite - 4) + 2, hoehe - 4 - (w - lo) / spanne * (hoehe - 8))
           for i, w in enumerate(werte)]
    farbe = stil.PLUS if werte[-1] >= werte[0] else stil.MINUS
    linie = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    flaeche = f"2,{hoehe} " + linie + f" {breite - 2},{hoehe}"
    gid = "verlauf"
    return _als_bild(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {breite} {hoehe}" '
            f'width="{breite}" height="{hoehe}" preserveAspectRatio="none">'
            f'<defs><linearGradient id="{gid}" x1="0" y1="0" x2="0" y2="1">'
            f'<stop offset="0" stop-color="{farbe}" stop-opacity="0.35"/>'
            f'<stop offset="1" stop-color="{farbe}" stop-opacity="0"/></linearGradient></defs>'
            f'<polygon points="{flaeche}" fill="url(#{gid})"/>'
            f'<defs><filter id="glow" x="-10%" y="-30%" width="120%" height="160%"><feGaussianBlur stdDeviation="2.2"/></filter></defs>'
            f'<polyline points="{linie}" fill="none" stroke="{farbe}" stroke-width="3.5" stroke-opacity="0.55" '
            f'stroke-linejoin="round" stroke-linecap="round" filter="url(#glow)"/>'
            f'<polyline points="{linie}" fill="none" stroke="{farbe}" stroke-width="1.8" '
            f'stroke-linejoin="round" stroke-linecap="round"/>'
            f'<circle cx="{pts[-1][0]:.1f}" cy="{pts[-1][1]:.1f}" r="3" fill="{farbe}"/></svg>', "pb-spark",
                    "Mini-Kurve des Kontostands")


def ring(anteil, mitte, unten=""):
    """Ringdiagramm fuer den Fortschritt (z. B. Trades bis 200)."""
    anteil = max(0.0, min(1.0, anteil or 0.0))
    r, u = 24, 2 * 3.14159 * 24
    return _als_bild(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 62 62" width="62" height="62">'
            f'<circle cx="31" cy="31" r="{r}" fill="none" stroke="rgba(160,140,255,0.15)" stroke-width="6"/>'
            f'<circle cx="31" cy="31" r="{r}" fill="none" stroke="{stil.VIOLETT}" stroke-width="6" '
            f'stroke-linecap="round" stroke-dasharray="{anteil * u:.1f} {u:.1f}" transform="rotate(-90 31 31)"/>'
            f'<text x="31" y="{30 if unten else 35}" text-anchor="middle" font-size="12" font-weight="700" '
            f'fill="{stil.TEXT}" font-family="sans-serif">{e(mitte)}</text>'
            + (f'<text x="31" y="43" text-anchor="middle" font-size="8.5" fill="{stil.TEXT_LEISE}" '
               f'font-family="sans-serif">{e(unten)}</text>' if unten else "") + "</svg>", "pb-ring",
                    f"Fortschritt {mitte} {unten}")


# ================================================================ Karten

def karte(titel, zahl, unter="", rechts="", oben_rechts="", fuss="", leuchten=False, klein=False, zahl_einzeilig=False):
    """Karte: kleine Beschriftung, grosse Zahl, darunter Plus/Minus; rechts ein Ring, unten (fuss) eine
    Mini-Kurve oder ein Urteil ueber die ganze Breite. titel/zahl werden maskiert, der Rest ist fertiges HTML. zahl_einzeilig haelt Zahl und Einheit zusammen."""
    return (f'<div class="pb-karte{" leuchten" if leuchten else ""}">'
            f'<div class="pb-titel"><span>{e(titel)}</span>{oben_rechts}</div>'
            f'<div class="pb-zeile"><div class="pb-text"><div class="pb-zahl{" klein" if klein else ""}{" einzeilig" if zahl_einzeilig else ""}">{e(zahl)}</div>'
            f'<div class="pb-unter">{unter}</div></div>{rechts}</div>'
            + (f'<div class="pb-fuss">{fuss}</div>' if fuss else "") + "</div>")


def raster(karten, gross=False, breit=False, vierer=False, experimente=False, handy_einspaltig=False):
    """Roh/Kosten-Karten in maximal zwei Spalten, einfache Kennzahlen nach Kartenanzahl."""
    karten = list(karten)
    anzahl = len(karten)
    reich = experimente or any('class="nx-duo"' in karte for karte in karten)
    spalten = min(anzahl, 2) if reich or anzahl < 3 else 4 if anzahl == 4 else 3
    ausgleich = not reich and anzahl > 4 and anzahl % 3 == 1
    handy_paar = anzahl >= 4
    st.html(f'<div class="pb-raster spalten-{spalten or 1}{" gross" if gross else ""}{" breit" if breit else ""}'
            f'{" vierer" if anzahl == 4 and not reich else ""}{" ausgleich" if ausgleich else ""}'
            f'{" handy-paar" if handy_paar else ""}{" ungerade" if anzahl % 2 else ""}'
            f'{" handy-einspaltig" if handy_einspaltig else ""}'
            f'{" nx-konten" if reich else ""}{" nx-experimente" if experimente else ""}">{"".join(karten)}</div>')


def pille(status, text):
    """Status-Pille: ok = pulsierender Punkt, verzoegert = Dreieck, steht = Kreuz. Immer auch als Wort (nie Farbe allein)."""
    klasse, wort = STATUS[status]
    zeichen = {"ok": '<i class="nx-punkt"></i>', "achtung": '<i class="nx-dreieck">▲</i>',
               "kaputt": '<i class="nx-dreieck">✗</i>'}[status]
    return f'<span class="nx-pille {klasse}">{zeichen}<b>{e(wort.capitalize())}</b> · {e(text)}</span>'


def status_leiste(eintraege):
    """eintraege: [(status, text)] -> Reihe von Status-Pillen."""
    st.html(f'<div class="nx-pillen">{"".join(pille(s, t) for s, t in eintraege)}</div>')


def bot_status_eintraege():
    """Pillen-Daten aller drei Bots (Hauptbot, Copy-Bot, Scout) wie auf der Uebersicht; bei Fehlern leer."""
    import daten
    try:
        jetzt = time.time()
        head = daten.stand()
        commits, _, _ = daten.betrieb(head)
        _, scout_lauf = daten.scout(head)
        letzte = {bot: (t[-1] if t else None) for bot, t in commits.items()}
        ergebnis = [(rechnung.bot_status(ts, jetzt), f"{bot} · {vor(ts)}") for bot, ts in letzte.items()]
        scout = "kaputt" if scout_lauf is None else "ok" if jetzt - scout_lauf <= 7 * 3600 else \
            "achtung" if jetzt - scout_lauf <= 13 * 3600 else "kaputt"
        return ergebnis + [(scout, f"Scout · {vor(scout_lauf)}")]
    except Exception:
        return []


def seitenkopf(titel, beschreibung="", status=True):
    """Einheitlicher Seitenkopf: Titel, Erklaerung, darunter die Status-Pillen der Bots."""
    st.html(f'<div class="nx-kopf"><h1>{e(titel)}</h1>' + (f'<p>{e(beschreibung)}</p>' if beschreibung else "") + "</div>")
    if status:
        eintraege = bot_status_eintraege()
        if eintraege:
            status_leiste(eintraege)


def leer(titel="Noch keine Daten", hilfe=""):
    """Leerzustand im Nexus-Stil."""
    st.html(f'<div class="nx-leer"><img src="{stil.icon_uri("leer")}" alt=""/><b>{e(titel)}</b>'
            + (f"<span>{e(hilfe)}</span>" if hilfe else "") + "</div>")


def fehler(titel, detail=""):
    """Fehlermeldung im Nexus-Stil (statt st.error): was ist passiert, was geht trotzdem."""
    st.html(f'<div class="nx-fehler" role="alert"><img src="{stil.icon_uri("fehler", stil.MINUS)}" alt=""/><div>'
            f'<b>{e(titel)}</b>' + (f"<span>{e(detail)}</span>" if detail else "") + "</div></div>")


def _zelle(wert, spalte, zahlen, pm_spalten):
    if wert is None or (isinstance(wert, float) and wert != wert):
        return "–"
    if spalte in pm_spalten and isinstance(wert, (int, float)):
        return pm_html(wert, *(pm_spalten[spalte] or ()))
    if spalte in zahlen and isinstance(wert, (int, float)):
        stellen, vorzeichen, einheit = zahlen[spalte]
        return e(txt(wert, stellen, vorzeichen, einheit))
    return e(wert)


def tabelle(df, zahlen=None, pm_spalten=None, hoehe=560, leer_text="Noch keine Daten.", einzeilig=None, layout=""):
    """Tabelle, die sich dem Inhalt anpasst: Text bricht um, Zahlen stehen rechts in Monospace, Kopfzeile und erste
    Spalte bleiben beim Scrollen stehen. Nichts wird abgeschnitten (bei schmalem Bildschirm: seitlich wischen).
    zahlen: {Spalte: (Nachkommastellen, mit_Vorzeichen, Einheit)}; pm_spalten: {Spalte: (Stellen, Einheit) oder None}
    fuer Gewinn/Verlust mit Pfeil und Farbe. Alle anderen Werte werden als Text eingefuegt (maskiert).
    Lange Tabellen bleiben auf allen Bildschirmgroessen begrenzt, auch mit hoehe=None.
    einzeilig nennt Textspalten ohne Umbruch; layout waehlt eine eigene Tabellen-Darstellung."""
    zahlen, pm_spalten = zahlen or {}, pm_spalten or {}
    einzeilig = set(einzeilig or ())
    if df is None or len(df) == 0:
        return leer(leer_text)
    numerisch = set(zahlen) | set(pm_spalten) | {
        c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])}
    breit = len(df.columns) > 5
    wisch = ('<div class="nx-wischhinweis"><span>Weitere Spalten: seitlich wischen oder scrollen</span>'
             '<b aria-hidden="true">→</b></div>') if breit else ""
    kopf = "".join(f'<th class="{"num" if c in numerisch else ""}">{e(c)}</th>' for c in df.columns)
    zeilen = []
    for _, r in df.iterrows():
        zellen = "".join(f'<td class="{"num" if c in numerisch else "text"}'
                         f'{" einzeilig" if c in einzeilig else ""}">{_zelle(r[c], c, zahlen, pm_spalten)}</td>'
                         for c in df.columns)
        zeilen.append(f"<tr>{zellen}</tr>")
    lang = len(df) > 12
    limit = min(int(hoehe or 560), 560)
    grenze = f' style="--nx-tabellenhoehe:{limit}px"' if lang or hoehe is not None else ' style="max-height:none"'
    scrollhinweis = f'<div class="nx-scrollhinweis">{len(df)} Zeilen – in der Tabelle scrollen</div>' if lang else ""
    st.html(f'{scrollhinweis}{wisch}<div class="nx-tabellenrahmen{" wischen" if breit else ""}{" " + e(layout) if layout else ""}">'
            f'<div class="nx-tabelle"{grenze}><table><thead><tr>{kopf}</tr></thead>'
            f'<tbody>{"".join(zeilen)}</tbody></table></div></div>')


SCOUT_LUECKE = "Aktuelle Scout-Prüfung fehlt"


def wallet_liste(wallets):
    """Kompakte Vorschau: gemeinsame Scout-Luecke einmal, sonst Hinweise je Wallet."""
    ampel = {"rot": "✗ Rot", "gelb": "▲ Gelb", "gruen": "✓ Grün"}
    reihenfolge = {"rot": 0, "gelb": 1, "gruen": 2}
    zaehler = " · ".join(f"{sum(z['ampel'] == k for z in wallets)} {wort}" for k, wort in
                         (("gelb", "Gelb"), ("rot", "Rot"), ("gruen", "Grün")))
    st.caption(zaehler + " · Vorschau nach gespeicherten Daten; keine Änderungen.")
    ohne_scout = [z["name"] for z in wallets if SCOUT_LUECKE in z["luecken"]]
    if ohne_scout:
        umfang = "bei allen angezeigten Wallets." if len(ohne_scout) == len(wallets) else "bei: " + ", ".join(ohne_scout)
        hinweis(SCOUT_LUECKE + " – " + umfang)
    zeilen_hinweise = {
        z["name"]: (["Schonfrist"] if z["schonfrist"] and z["gruende"] else [])
                   + [h for h in z["luecken"] if h != SCOUT_LUECKE]
        for z in wallets
    }
    mit_hinweis = any(zeilen_hinweise.values())
    zeilen = []
    for z in sorted(wallets, key=lambda z: reihenfolge[z["ampel"]]):
        grund = " · ".join(z["gruende"] or (["Schonfrist"] if z["schonfrist"] else
                                            ["Datenlücke"] if z["luecken"] else ["Keine Regel greift"]))
        hinweise = zeilen_hinweise[z["name"]]
        zusatz = f'<span class="nx-waechter-hinweis">{e(" · ".join(hinweise) or "–")}</span>' if mit_hinweis else ""
        zeilen.append(f'<div class="nx-waechter-zeile" role="listitem">'
                      f'<span class="nx-waechter-name">{e(z["name"])}</span>'
                      f'<span class="nx-waechter-ampel {z["ampel"]}">{ampel[z["ampel"]]}</span>'
                      f'<span class="nx-waechter-grund">{e(grund)}</span>{zusatz}</div>')
    lang = len(wallets) > 12
    scrollhinweis = f'<div class="nx-scrollhinweis">{len(wallets)} Zeilen – in der Tabelle scrollen</div>' if lang else ""
    st.html(f'{scrollhinweis}<div class="nx-waechter{"" if mit_hinweis else " ohne-hinweise"}">'
            '<div class="nx-waechter-kopf" aria-hidden="true">'
            '<span>Wallet</span><span>Ampel</span><span>Grund</span>'
            + ('<span>Hinweis</span>' if mit_hinweis else "") + '</div>'
            f'<div class="{"nx-waechter-scroll" if lang else ""}" role="list">{"".join(zeilen)}</div></div>')


def roh_kosten_karte(titel, roh, kosten, unter_roh="", unter_kosten="", kosten_pct=None, fuss="", leuchten=False,
                     oben_rechts=""):
    """Karte mit zwei Werten nebeneinander: roh (vorher) und mit Kosten (nachher). Beide Zahlen sind fertige Texte,
    die Unterzeilen fertiges HTML (z. B. pm_html)."""
    chip_kosten = chip(f"Kosten {kosten_pct:g} %".replace(".", ","), "achtung") if kosten_pct is not None else ""
    return (f'<div class="pb-karte{" leuchten" if leuchten else ""}"><div class="pb-titel"><span>{e(titel)}</span>'
            f'{oben_rechts or chip_kosten}</div><div class="nx-duo">'
            f'<div><div class="nx-mini">roh</div><div class="pb-zahl">{e(roh)}</div><div class="pb-unter">{unter_roh}</div></div>'
            f'<div><div class="nx-mini kosten">mit Kosten</div><div class="pb-zahl">{e(kosten)}</div>'
            f'<div class="pb-unter">{unter_kosten}</div></div></div>'
            + (f'<div class="pb-fuss">{fuss}</div>' if fuss else "") + "</div>")


def konto_karte(k, fuss="", leuchten=False):
    """Konto der Hauptstrategie/eines Experiments: Kontowert roh und mit Kosten (2 %, Endspurt 4 %) nebeneinander."""
    mit = rechnung.kontowert_mit_kosten(k)
    seit = f" in Runde {k['runde']}" if (k.get("runde") or 1) > 1 else " seit Start"
    return roh_kosten_karte(k["label"], rechnung.sol_text(k["kontowert"], 2, False), rechnung.sol_text(mit, 2, False),
                            pm_html(k["ergebnis"]) + seit, pm_html(rechnung.ergebnis_mit_kosten(k)) + seit,
                            kosten_pct=k.get("kosten_pct"), fuss=fuss, leuchten=leuchten)


def ausreisser_text(name, wert, anteil, gesamt, bereich):
    """Hinweis, wenn ein einzelnes Konto oder ein Trader mehr als die Haelfte des Gesamtergebnisses ausmacht."""
    teil = "mehr als das gesamte Ergebnis" if anteil > 1 else f"{anteil:.0%} des Gesamtergebnisses"
    return (f"Ausreißer {bereich}: {name} allein {rechnung.sol_text(wert, 2)} – das ist {teil} "
            f"({rechnung.sol_text(gesamt, 2)}). Ein Einzelner bestimmt das Bild.")


def hinweis(text):
    st.html(f'<div class="pb-hinweis"><span>▲</span><span>{e(text)}</span></div>')


def protokoll(eintraege, scroll=True, kompakt=False):
    """Aktivitaetsprotokoll. eintraege: dicts mit name, detail, wert (Zahl, SOL), optional rechts_unten."""
    zeilen = []
    for x in eintraege:
        w = x.get("wert")
        klasse = "plus" if w is not None and w > 0.0005 else "minus" if w is not None and w < -0.0005 else ""
        zeichen = "▲" if klasse == "plus" else "▼" if klasse == "minus" else "•"
        zeilen.append(f'<div class="pb-eintrag"><div class="pb-symbol {klasse}">{zeichen}</div>'
                      f'<div style="min-width:0"><div class="pb-name">{e(x["name"])}</div>'
                      f'<div class="pb-detail">{e(x.get("detail", ""))}</div></div>'
                      f'<div class="pb-wert">{pm_html(w) if w is not None else ""}'
                      f'<div class="pb-detail">{e(x.get("rechts_unten", ""))}</div></div></div>')
    inhalt = f'<div class="pb-liste{" nx-kurzprotokoll" if kompakt else ""}">{"".join(zeilen)}</div>'
    st.html(f'<div class="pb-karte">' + (f'<div class="pb-scroll">{inhalt}</div>' if scroll else inhalt) + "</div>")


def ereignisse(zeilen):
    """Liste 'Was ist neu'. zeilen: (Titel, Text) - beides MUSS schon mit e() maskiert sein (Text darf HTML enthalten)."""
    teile = "".join(f'<div class="pb-eintrag"><div class="pb-symbol">•</div><div style="min-width:0">'
                    f'<div class="pb-name">{titel}</div><div class="pb-detail" style="white-space:normal">{text}</div>'
                    f'</div><div></div></div>' for titel, text in zeilen)
    st.html(f'<div class="pb-karte"><div class="pb-scroll"><div class="pb-liste">{teile}</div></div></div>')


NEWS_MARKEN = {"position": ("Meine Coins", "achtung"), "listing": ("Listing", ""), "rug": ("Rug / Hack", "schlecht"),
               "solana": ("Solana", "gut")}


def news_liste(items, scroll=True):
    """Nachrichten: Markierungen, Ueberschrift (Link), hoechstens ein Satz, Quelle und Alter. Fremder Text wird
    maskiert; Links nur http(s) (sicherer_link in listings.py)."""
    zeilen = []
    for i in items:
        chips = "".join(chip(*NEWS_MARKEN[m]) for m in i.get("marken", []) if m in NEWS_MARKEN)
        titel = e(i["titel"])
        if i.get("link"):
            titel = f'<a class="pb-link" href="{e(i["link"])}" target="_blank" rel="noopener noreferrer">{titel}</a>'
        coins = f" · deine Coins: {e(', '.join(i['positions_coins']))}" if i.get("positions_coins") else ""
        anriss = f'<div class="pb-detail pb-frei">{e(i["anriss"])}</div>' if i.get("anriss") else ""
        zeilen.append('<div class="pb-news">' + (f'<div class="pb-chips">{chips}</div>' if chips else "") +
                      f'<div class="pb-name pb-frei">{titel}</div>{anriss}'
                      f'<div class="pb-detail">{e(i["quelle"])} · {e(vor(i["zeit"]))}{coins}</div></div>')
    inhalt = f'<div class="pb-liste">{"".join(zeilen)}</div>'
    st.html('<div class="pb-karte">' + (f'<div class="pb-scroll">{inhalt}</div>' if scroll else inhalt) + "</div>")


def datentabelle(df, zahlen=None, pm_spalten=None, hilfen=None, alt_text="Datentabelle", leer_text="Noch keine Daten.",
                hoehe=560, einzeilig=None, hauptspalten=None, detail_gruppen=None, layout=""):
    """Bis 200 Zeilen Nexus-Tabelle, darueber native Tabelle mit breiten Textspalten.

    Eingaben bleiben numerisch; nur die Anzeige von Leistungswerten bekommt Pfeil und Vorzeichen.
    Spalten-Erklaerungen bleiben auch bei der HTML-Tabelle ueber einen aufklappbaren Hinweis erreichbar.
    hauptspalten und detail_gruppen ordnen dieselben Daten in schmale Haupt- und Detailtabellen.
    """
    zahlen, pm_spalten, hilfen = zahlen or {}, pm_spalten or {}, hilfen or {}
    gesamt = df
    if hauptspalten and df is not None and len(df):
        df = df[hauptspalten]
    if df is None or len(df) <= 200:
        tabelle(df, zahlen=zahlen, pm_spalten=pm_spalten, leer_text=leer_text, hoehe=hoehe, einzeilig=einzeilig, layout=layout)
    else:
        anzeige = df.copy()
        config = {}
        for spalte in df.columns:
            hilfe = hilfen.get(spalte)
            if spalte in pm_spalten:
                anzeige[spalte] = df[spalte].map(
                    lambda x: "–" if pd.isna(x) else plusminus(x, *(pm_spalten[spalte] or ())))
                config[spalte] = st.column_config.TextColumn(width="medium", help=hilfe)
            elif spalte in zahlen:
                stellen, vorzeichen, einheit = zahlen[spalte]
                fmt = f"%{'+' if vorzeichen else ''}.{stellen}f{einheit.replace('%', '%%')}"
                config[spalte] = st.column_config.NumberColumn(width="medium", format=fmt, help=hilfe)
            elif pd.api.types.is_numeric_dtype(df[spalte]):
                config[spalte] = st.column_config.NumberColumn(width="medium", help=hilfe)
            else:
                config[spalte] = st.column_config.TextColumn(width="large", help=hilfe)
        st.dataframe(anzeige, hide_index=True, column_config=config, row_height=48, alt=alt_text, width="stretch",
                     height=min(int(hoehe or 560), 560))
        st.caption(f"{len(df)} Zeilen – in der Tabelle scrollen · weitere Spalten durch seitliches Wischen erreichbar.")
    if hilfen and df is not None and len(df):
        with st.expander("Spalten erklärt", icon=":material/info:"):
            tabelle(pd.DataFrame([{"Spalte": s, "Erklärung": h} for s, h in hilfen.items()]))
    if detail_gruppen and gesamt is not None and len(gesamt):
        with st.expander("Weitere Kennzahlen und Hinweise", icon=":material/table_rows:"):
            for titel, spalten in detail_gruppen.items():
                st.caption(titel)
                datentabelle(gesamt[spalten], zahlen=zahlen, pm_spalten=pm_spalten,
                             alt_text=f"{alt_text}: {titel}", hoehe=hoehe, einzeilig=einzeilig)


# ================================================================ Diagramme

def balken(df, wert, name, titel_x, stellen=3, referenz=None, referenz_text=""):
    """Waagerechte Balken, Plus gruen / Minus rot, Beschriftung mit Vorzeichen; Minus-Werte rechts der Null."""
    df = df.copy()
    df["richtung"] = df[wert].apply(lambda v: "Plus" if v >= 0 else "Minus")
    df["beschriftung"] = df[wert].apply(lambda v: rechnung.zahl(v, stellen, vorzeichen=True))
    reihenfolge = list(df.sort_values(wert, ascending=False)[name])
    y = alt.Y(f"{name}:N", sort=reihenfolge, title=None, axis=alt.Axis(labelLimit=170, labelFontSize=11, labelFont="Inter, sans-serif", ticks=False, domain=False))
    farbe = alt.Color("richtung:N", scale=alt.Scale(domain=["Plus", "Minus"], range=[stil.PLUS, stil.MINUS]),
                      legend=None)
    basis = alt.Chart(df).encode(y=y)
    bars = basis.mark_bar(size=12, cornerRadiusEnd=4, opacity=0.85).encode(
        x=alt.X(f"{wert}:Q", title=titel_x, axis=alt.Axis(grid=True, tickCount=5)), color=farbe,
        tooltip=[alt.Tooltip(f"{name}:N", title="Name"), alt.Tooltip("beschriftung:N", title=titel_x)])
    plus = basis.transform_filter(alt.datum[wert] >= 0).mark_text(
        align="left", dx=4, fontSize=12, color=stil.TEXT).encode(x=f"{wert}:Q", text="beschriftung:N")
    minus = basis.transform_filter(alt.datum[wert] < 0).transform_calculate(null="0").mark_text(
        align="left", dx=4, fontSize=12, color=stil.TEXT).encode(x="null:Q", text="beschriftung:N")
    null = alt.Chart(pd.DataFrame({"x": [0]})).mark_rule(color=stil.TEXT_LEISE, strokeWidth=1).encode(x="x:Q")
    lagen = [bars, plus, minus, null]
    if referenz is not None:
        lagen.append(alt.Chart(pd.DataFrame({"x": [referenz], "t": [referenz_text]})).mark_rule(
            color=stil.KONTROLLE, strokeWidth=2).encode(x="x:Q", tooltip=alt.Tooltip("t:N", title="Linie")))
    return alt.layer(*lagen).properties(height=max(140, 28 * len(df) + 40))


def _verlauf_df(df, name):
    df = df.assign(konto=name)
    df["zeit_text"] = df["zeit"].apply(rechnung.zeit_text)
    df["stand_text"] = df["kontostand"].apply(lambda v: rechnung.sol_text(v, 3, vorzeichen=False))
    return df


def kontoverlauf(df_eigen, name, df_kontrolle=None, hoehe=340):
    """Grosser Kontoverlauf: Flaeche mit Farbverlauf, Kontrollgruppe grau, gestrichelte Linie bei 10 SOL."""
    df = _verlauf_df(df_eigen, name)
    tip = [alt.Tooltip("konto:N", title="Konto"), alt.Tooltip("zeit_text:N", title="Zeit"),
           alt.Tooltip("stand_text:N", title="Kontostand")]
    werte = list(df["kontostand"]) + [rechnung.START_SOL]
    if df_kontrolle is not None and len(df_kontrolle):
        werte += list(df_kontrolle["kontostand"])
    unten, oben = min(werte), max(werte)
    rand = (oben - unten) * 0.08 or 0.5
    skala = alt.Scale(domain=[unten - rand, oben + rand])
    x = alt.X("zeit:T", title=None, axis=alt.Axis(format="%d.%m. %H:%M", labelAngle=0, tickCount=6, grid=False))
    y = alt.Y("kontostand:Q", title="Kontostand (SOL)", scale=skala)
    farbverlauf = alt.Gradient(gradient="linear", x1=1, x2=1, y1=1, y2=0, stops=[
        alt.GradientStop(color="rgba(139,124,246,0.0)", offset=0),
        alt.GradientStop(color="rgba(139,124,246,0.45)", offset=1)])
    flaeche = alt.Chart(df).mark_area(interpolate="step-after", color=farbverlauf,
                                      line={"color": stil.VIOLETT, "strokeWidth": 2.2}).encode(
        x=x, y=y, y2=alt.datum(unten - rand), tooltip=tip)
    start = alt.Chart(pd.DataFrame({"y": [rechnung.START_SOL]})).mark_rule(
        color=stil.TEXT_LEISE, strokeWidth=1, strokeDash=[4, 4]).encode(y=alt.Y("y:Q", scale=skala))
    lagen = [flaeche, start]
    if df_kontrolle is not None and len(df_kontrolle):
        k = _verlauf_df(df_kontrolle, "Kontrollgruppe")
        lagen.append(alt.Chart(k).mark_line(interpolate="step-after", strokeWidth=1.6, color=stil.KONTROLLE)
                     .encode(x=x, y=y, tooltip=tip))
    return alt.layer(*lagen).properties(height=hoehe)
