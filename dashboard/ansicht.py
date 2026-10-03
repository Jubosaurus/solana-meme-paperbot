"""Darstellung: Ampel, Plus/Minus ohne Farbe lesbar, ruhige Diagramme (dataviz-Palette)."""
import time

import altair as alt
import pandas as pd
import streamlit as st

import rechnung

PLUS, MINUS, NEUTRAL = "#2a78d6", "#e34948", "#8a8984"       # Blau = Plus, Rot = Minus (immer mit Vorzeichen)
GRID, ACHSE = "#ecebe7", "#52514e"

AMPEL = {   # Status nie nur ueber Farbe: Symbol + Wort
    "besser": (":material/check_circle:", "besser", "green", "✓ besser"),
    "schlechter": (":material/cancel:", "schlechter", "red", "✗ schlechter"),
    "gemischt": (":material/error:", "hält nicht", "orange", "≈ hält nicht"),
    "zu_frueh": (":material/hourglass_top:", "zu früh", "gray", "… zu früh"),
    "basis": (":material/flag:", "Vergleichsbasis", "gray", "– Vergleichsbasis"),
    "keine_daten": (":material/remove:", "keine Daten", "gray", "– keine Daten"),
}
STATUS = {
    "ok": (":material/check_circle:", "läuft", "green"),
    "achtung": (":material/schedule:", "verzögert", "orange"),
    "kaputt": (":material/error:", "steht", "red"),
}


def ampel_text(v):
    text = AMPEL[v["ampel"]][3]
    if v["ampel"] == "zu_frueh":
        text += f", Tendenz {v['tendenz']}"
    return text


def ampel_badge(v):
    icon, label, farbe, _ = AMPEL[v["ampel"]]
    if v["ampel"] == "zu_frueh":
        label += f" · Tendenz {v['tendenz']}"
    st.badge(label, icon=icon, color=farbe)


def status_badge(status, text=""):
    icon, label, farbe = STATUS[status]
    st.badge(f"{label} {text}".strip(), icon=icon, color=farbe)


def plusminus(x, stellen=3, einheit=" SOL"):
    """Gewinn/Verlust ohne Farbe lesbar: Pfeil + Vorzeichen."""
    if x is None:
        return "–"
    t = rechnung.zahl(x, stellen, vorzeichen=True) + einheit
    if t.startswith("+"):
        return "▲ " + t
    if t.startswith("−"):
        return "▼ " + t
    return "● " + t


def txt(x, stellen=1, vorzeichen=False, einheit=""):
    """Zahl als deutscher Text fuer Tabellen; fehlender Wert = '–' statt 'None'."""
    return "–" if x is None else rechnung.zahl(x, stellen, vorzeichen) + einheit


def vor(ts):
    """'vor 3 min' fuer Unix-Zeit."""
    if ts is None:
        return "–"
    return "vor " + rechnung.dauer_text(max(0, time.time() - ts))


def sol_metric(label, wert, ergebnis=None, hilfe=None, delta_text=None):
    """Grosse Kennzahl: Wert in SOL, darunter Plus/Minus als Pfeil + Vorzeichen (ruhig grau, nicht bunt)."""
    # Streamlit erkennt "runter" nur am normalen Bindestrich, nicht am typografischen Minus
    delta = (delta_text or rechnung.sol_text(ergebnis, 3)).replace("−", "-") if ergebnis is not None else None
    st.metric(label, rechnung.sol_text(wert, 2, vorzeichen=False), delta=delta,
              delta_color="off" if ergebnis is None or abs(ergebnis) < 0.0005 else "normal",
              help=hilfe, border=True)


def _basis(chart):
    return chart.configure_axis(gridColor=GRID, domainColor=GRID, tickColor=GRID, labelColor=ACHSE,
                                titleColor=ACHSE, labelFontSize=12, titleFontWeight="normal") \
        .configure_view(strokeWidth=0)


def balken(df, wert, name, titel_x, stellen=3, referenz=None, referenz_text=""):
    """Waagerechte Balken, Plus blau / Minus rot, Beschriftung mit Vorzeichen am Balkenende."""
    df = df.copy()
    df["richtung"] = df[wert].apply(lambda v: "Plus" if v >= 0 else "Minus")
    df["beschriftung"] = df[wert].apply(lambda v: rechnung.zahl(v, stellen, vorzeichen=True))
    df["ausrichtung"] = df[wert].apply(lambda v: "left" if v >= 0 else "right")
    hoehe = max(140, 30 * len(df) + 40)
    reihenfolge = list(df.sort_values(wert, ascending=False)[name])   # feste Reihenfolge fuer alle Ebenen
    y = alt.Y(f"{name}:N", sort=reihenfolge, title=None,
              axis=alt.Axis(labelLimit=180, ticks=False, domain=False))
    farbe = alt.Color("richtung:N", scale=alt.Scale(domain=["Plus", "Minus"], range=[PLUS, MINUS]),
                      legend=None)
    tooltip = [alt.Tooltip(f"{name}:N", title="Konto"), alt.Tooltip("beschriftung:N", title=titel_x)]
    basis = alt.Chart(df).encode(y=y)
    bars = basis.mark_bar(size=14, cornerRadiusEnd=4).encode(
        x=alt.X(f"{wert}:Q", title=titel_x, axis=alt.Axis(grid=True, tickCount=5)), color=farbe, tooltip=tooltip)
    plus = basis.transform_filter(alt.datum[wert] >= 0).mark_text(align="left", dx=4, fontSize=12,
                                                                 color=ACHSE).encode(
        x=f"{wert}:Q", text="beschriftung:N")
    # Minus-Werte rechts neben der Nulllinie beschriften, damit sie nicht mit den Namen links kollidieren
    minus = basis.transform_filter(alt.datum[wert] < 0).transform_calculate(null="0").mark_text(
        align="left", dx=4, fontSize=12, color=ACHSE).encode(x="null:Q", text="beschriftung:N")
    null = alt.Chart(pd.DataFrame({"x": [0]})).mark_rule(color=ACHSE, strokeWidth=1).encode(x="x:Q")
    lagen = [bars, plus, minus, null]
    if referenz is not None:
        ref = pd.DataFrame({"x": [referenz], "t": [referenz_text]})
        lagen.append(alt.Chart(ref).mark_rule(color=NEUTRAL, strokeWidth=2, strokeDash=[]).encode(
            x="x:Q", tooltip=alt.Tooltip("t:N", title="Linie")))
    return _basis(alt.layer(*lagen).properties(height=hoehe))


def kontoverlauf(df_eigen, name, df_kontrolle=None):
    """Kontostand ueber die Zeit (Stufen), Kontrollgruppe grau zum Vergleich, Linie bei 10 SOL."""
    teile = [df_eigen.assign(konto=name)]
    if df_kontrolle is not None and len(df_kontrolle):
        teile.append(df_kontrolle.assign(konto="Kontrollgruppe"))
    df = pd.concat(teile)
    df["zeit_text"] = df["zeit"].apply(lambda t: rechnung.zeit_text(t))
    df["stand_text"] = df["kontostand"].apply(lambda v: rechnung.sol_text(v, 3, vorzeichen=False))
    namen = [name] + (["Kontrollgruppe"] if len(teile) > 1 else [])
    farbe = alt.Color("konto:N", scale=alt.Scale(domain=namen, range=[PLUS, NEUTRAL][:len(namen)]),
                      legend=alt.Legend(title=None, orient="top", direction="horizontal") if len(namen) > 1
                      else None)
    linie = alt.Chart(df).mark_line(interpolate="step-after", strokeWidth=2).encode(
        x=alt.X("zeit:T", title=None, axis=alt.Axis(format="%d.%m. %H:%M", labelAngle=0, tickCount=6, grid=False)),
        y=alt.Y("kontostand:Q", title="Kontostand (SOL)", scale=alt.Scale(zero=False)),
        color=farbe,
        tooltip=[alt.Tooltip("konto:N", title="Konto"), alt.Tooltip("zeit_text:N", title="Zeit"),
                 alt.Tooltip("stand_text:N", title="Kontostand")])
    punkte = alt.Chart(df).mark_point(size=60, opacity=0).encode(x="zeit:T", y="kontostand:Q", tooltip=[
        alt.Tooltip("konto:N", title="Konto"), alt.Tooltip("zeit_text:N", title="Zeit"),
        alt.Tooltip("stand_text:N", title="Kontostand")])
    start = alt.Chart(pd.DataFrame({"y": [rechnung.START_SOL]})).mark_rule(color=ACHSE, strokeWidth=1).encode(y="y:Q")
    return _basis(alt.layer(start, linie, punkte).properties(height=300))
