"""Bausteine der Darstellung: Karten, Mini-Kurven, Ringe, Aktivitaetsprotokoll, Diagramme.

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
AMPEL_ZEICHEN = {"besser": "✓", "schlechter": "✗", "gemischt": "≈", "zu_frueh": "…", "basis": "–", "keine_daten": "–"}
STATUS = {"ok": ("gut", "✓", "läuft"), "achtung": ("achtung", "!", "verzögert"), "kaputt": ("schlecht", "✗", "steht")}


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
    return f"{AMPEL_ZEICHEN[v['ampel']]} {rechnung.urteil_kurz(v)}"


def urteil_chip(v):
    return f'<span class="pb-chip {AMPEL_KLASSE[v["ampel"]]}">{e(urteil_text(v))}</span>'


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
            f'<polyline points="{linie}" fill="none" stroke="{farbe}" stroke-width="2" '
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

def karte(titel, zahl, unter="", rechts="", oben_rechts="", fuss="", leuchten=False, klein=False):
    """Karte: kleine Beschriftung, grosse Zahl, darunter Plus/Minus; rechts ein Ring, unten (fuss) eine
    Mini-Kurve oder ein Urteil ueber die ganze Breite. titel/zahl werden maskiert, der Rest ist fertiges HTML."""
    return (f'<div class="pb-karte{" leuchten" if leuchten else ""}">'
            f'<div class="pb-titel"><span>{e(titel)}</span>{oben_rechts}</div>'
            f'<div class="pb-zeile"><div class="pb-text"><div class="pb-zahl{" klein" if klein else ""}">{e(zahl)}</div>'
            f'<div class="pb-unter">{unter}</div></div>{rechts}</div>'
            + (f'<div class="pb-fuss">{fuss}</div>' if fuss else "") + "</div>")


def raster(karten, gross=False):
    st.html(f'<div class="pb-raster{" gross" if gross else ""}">{"".join(karten)}</div>')


def status_leiste(eintraege):
    """eintraege: [(status, text)] -> Reihe von Status-Chips mit Zeichen + Wort."""
    teile = []
    for status, text in eintraege:
        klasse, zeichen, wort = STATUS[status]
        teile.append(chip(f"{zeichen} {wort} · {text}", klasse))
    st.html(f'<div class="pb-status">{"".join(teile)}</div>')


def ausreisser_text(name, wert, anteil, gesamt, bereich):
    """Hinweis, wenn ein einzelnes Konto oder ein Trader mehr als die Haelfte des Gesamtergebnisses ausmacht."""
    teil = "mehr als das gesamte Ergebnis" if anteil > 1 else f"{anteil:.0%} des Gesamtergebnisses"
    return (f"Ausreißer {bereich}: {name} allein {rechnung.sol_text(wert, 2)} – das ist {teil} "
            f"({rechnung.sol_text(gesamt, 2)}). Ein Einzelner bestimmt das Bild.")


def hinweis(text):
    st.html(f'<div class="pb-hinweis">⚠ {e(text)}</div>')


def protokoll(eintraege, scroll=True):
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
    inhalt = f'<div class="pb-liste">{"".join(zeilen)}</div>'
    st.html(f'<div class="pb-karte">' + (f'<div class="pb-scroll">{inhalt}</div>' if scroll else inhalt) + "</div>")


def ereignisse(zeilen):
    """Liste 'Was ist neu'. zeilen: (Titel, Text) - beides MUSS schon mit e() maskiert sein (Text darf HTML enthalten)."""
    teile = "".join(f'<div class="pb-eintrag"><div class="pb-symbol">•</div><div style="min-width:0">'
                    f'<div class="pb-name">{titel}</div><div class="pb-detail" style="white-space:normal">{text}</div>'
                    f'</div><div></div></div>' for titel, text in zeilen)
    st.html(f'<div class="pb-karte"><div class="pb-scroll"><div class="pb-liste">{teile}</div></div></div>')


# ================================================================ Diagramme

def balken(df, wert, name, titel_x, stellen=3, referenz=None, referenz_text=""):
    """Waagerechte Balken, Plus gruen / Minus rot, Beschriftung mit Vorzeichen; Minus-Werte rechts der Null."""
    df = df.copy()
    df["richtung"] = df[wert].apply(lambda v: "Plus" if v >= 0 else "Minus")
    df["beschriftung"] = df[wert].apply(lambda v: rechnung.zahl(v, stellen, vorzeichen=True))
    reihenfolge = list(df.sort_values(wert, ascending=False)[name])
    y = alt.Y(f"{name}:N", sort=reihenfolge, title=None, axis=alt.Axis(labelLimit=180, ticks=False, domain=False))
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
