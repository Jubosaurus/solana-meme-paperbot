"""Erscheinungsbild an EINER Stelle: Farben, eigenes CSS und Diagramm-Thema.

Bei einem Streamlit-Update nur hier nachsehen. Eigene Bausteine (Karten, Ringe, Protokoll) nutzen eigene
Klassen (pb-...); nur wenige Regeln greifen auf Streamlit-Elemente zu (markiert mit "Streamlit-intern").
Dunkles Design mit sanftem Violett/Blau-Verlauf. Gruen/Rot nur als Akzent und nie allein: immer mit
Pfeil und Vorzeichen.
"""
import streamlit as st

# ---------------------------------------------------------------- Farben
HINTERGRUND = "#0c0a1d"
FLAECHE = "#16132e"
TEXT = "#ecebf7"
TEXT_LEISE = "#a3a0c2"
LINIE = "#2c2852"
VIOLETT = "#8b7cf6"
BLAU = "#4f8df5"
PLUS = "#34c77b"          # Akzent fuer Gewinn (immer mit ▲ und +)
MINUS = "#ff6b7a"         # Akzent fuer Verlust (immer mit ▼ und −)
NEUTRAL = "#8e8bab"
KONTROLLE = "#8e8bab"     # Kontrollgruppe in Diagrammen: ruhiges Grau

CSS = f"""
<style>
/* ---- Hintergrund mit sanftem Verlauf (Streamlit-intern: stApp, stHeader, stSidebar) ---- */
[data-testid="stApp"] {{
  background:
    radial-gradient(900px 520px at 80% 4%, rgba(124, 92, 255, 0.30), transparent 65%),
    radial-gradient(800px 520px at 8% 40%, rgba(79, 141, 245, 0.18), transparent 65%),
    radial-gradient(900px 600px at 55% 100%, rgba(170, 90, 220, 0.16), transparent 65%),
    {HINTERGRUND};
  background-attachment: fixed;
}}
[data-testid="stAppViewContainer"], [data-testid="stMain"], [data-testid="stHeader"] {{ background: transparent; }}
[data-testid="stSidebar"] {{ background: rgba(14, 12, 34, 0.85); }}

/* ---- Streamlit-Karten (Rahmen-Container, Kennzahlen) leicht abrunden und leuchten lassen (Streamlit-intern) ---- */
[data-testid="stVerticalBlockBorderWrapper"], [data-testid="stMetric"] {{
  border-radius: 18px !important;
  box-shadow: 0 0 0 1px rgba(160, 140, 255, 0.10), 0 8px 30px rgba(80, 60, 200, 0.10);
  background: linear-gradient(160deg, rgba(255,255,255,0.045), rgba(255,255,255,0.015));
}}
[data-testid="stMetricValue"] {{ font-weight: 600; letter-spacing: -0.01em; }}

/* ---- Eigene Bausteine ---- */
.pb-raster {{ display: grid; gap: 14px; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); }}
.pb-raster.gross {{ grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); }}
.pb-karte {{
  position: relative; border-radius: 18px; padding: 16px 18px 14px;
  background: linear-gradient(160deg, rgba(255,255,255,0.06), rgba(255,255,255,0.015));
  border: 1px solid rgba(160, 140, 255, 0.16);
  box-shadow: 0 8px 30px rgba(70, 50, 190, 0.14), inset 0 1px 0 rgba(255,255,255,0.05);
  color: {TEXT}; overflow: hidden;
}}
.pb-karte.leuchten {{ box-shadow: 0 0 28px rgba(124, 92, 255, 0.28), inset 0 1px 0 rgba(255,255,255,0.06); }}
.pb-titel {{ font-size: 0.82rem; color: {TEXT_LEISE}; display: flex; justify-content: space-between;
             align-items: flex-start; gap: 8px; }}
.pb-titel .pb-chip {{ flex: 0 0 auto; }}
.pb-text {{ min-width: 0; }}
.pb-fuss {{ margin-top: 10px; }}
.pb-fuss .pb-chip + .pb-spark {{ margin-top: 10px; }}
.pb-zahl {{ font-size: 1.9rem; font-weight: 650; letter-spacing: -0.02em; margin: 4px 0 2px; line-height: 1.15;
            white-space: nowrap; }}
.pb-zahl.klein {{ font-size: 1.45rem; }}
.pb-unter {{ font-size: 0.85rem; color: {TEXT_LEISE}; }}
.pb-plus {{ color: {PLUS}; font-weight: 600; }}
.pb-minus {{ color: {MINUS}; font-weight: 600; }}
.pb-null {{ color: {NEUTRAL}; font-weight: 600; }}
.pb-chip {{
  display: inline-block; font-size: 0.74rem; padding: 2px 9px; border-radius: 999px; white-space: nowrap;
  background: rgba(139, 124, 246, 0.16); color: #d6d0ff; border: 1px solid rgba(139, 124, 246, 0.25);
}}
.pb-chip.gut {{ background: rgba(52, 199, 123, 0.12); color: #9ff0c4; border-color: rgba(52, 199, 123, 0.3); }}
.pb-chip.schlecht {{ background: rgba(255, 107, 122, 0.12); color: #ffc2c8; border-color: rgba(255, 107, 122, 0.3); }}
.pb-chip.achtung {{ background: rgba(250, 178, 25, 0.12); color: #ffe0a0; border-color: rgba(250, 178, 25, 0.3); }}
.pb-zeile {{ display: flex; align-items: flex-end; justify-content: space-between; gap: 10px; }}
.pb-spark {{ display: block; width: 100%; height: 44px; }}
.pb-ring {{ width: 62px; height: 62px; flex: 0 0 auto; }}
.pb-status {{ display: flex; flex-wrap: wrap; gap: 8px; margin: 2px 0 6px; }}
.pb-hinweis {{
  border-radius: 14px; padding: 10px 14px; margin: 4px 0 8px; font-size: 0.9rem;
  background: rgba(250, 178, 25, 0.10); border: 1px solid rgba(250, 178, 25, 0.35); color: #ffe7b0;
}}
.pb-liste {{ display: flex; flex-direction: column; gap: 2px; }}
.pb-eintrag {{
  display: grid; grid-template-columns: 30px 1fr auto; gap: 10px; align-items: center;
  padding: 9px 6px; border-bottom: 1px solid rgba(160, 140, 255, 0.08);
}}
.pb-eintrag:last-child {{ border-bottom: none; }}
.pb-symbol {{
  width: 30px; height: 30px; border-radius: 10px; display: flex; align-items: center; justify-content: center;
  font-size: 0.85rem; font-weight: 700; background: rgba(139, 124, 246, 0.14);
}}
.pb-symbol.plus {{ background: rgba(52, 199, 123, 0.14); color: {PLUS}; }}
.pb-symbol.minus {{ background: rgba(255, 107, 122, 0.14); color: {MINUS}; }}
.pb-name {{ font-weight: 600; font-size: 0.92rem; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
.pb-detail {{ font-size: 0.78rem; color: {TEXT_LEISE}; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
.pb-wert {{ text-align: right; font-size: 0.92rem; white-space: nowrap; }}
.pb-scroll {{ max-height: 520px; overflow-y: auto; padding-right: 4px; }}
@media (max-width: 640px) {{
  .pb-zahl {{ font-size: 1.6rem; }}
  .pb-raster, .pb-raster.gross {{ grid-template-columns: 1fr; }}
}}
</style>
"""


def anwenden():
    """Eigenes CSS einmal je Seitenaufruf einbinden."""
    st.html(CSS)


# ---------------------------------------------------------------- Diagramm-Thema (Altair/Vega-Lite)
def diagramm(chart):
    """Einheitliches Diagramm-Aussehen (dunkel, ruhig, haarfeine Achsen)."""
    return chart.configure(background="transparent", font="sans-serif")         .configure_view(strokeWidth=0)         .configure_axis(gridColor="#25213f", domainColor=LINIE, tickColor=LINIE, labelColor=TEXT_LEISE,
                        titleColor=TEXT_LEISE, labelFontSize=12, titleFontWeight="normal")         .configure_legend(labelColor=TEXT, titleColor=TEXT_LEISE, labelFontSize=12)


def zeigen(chart, alt_text):
    """Diagramm mit unserem Thema statt dem Streamlit-Thema anzeigen."""
    st.altair_chart(diagramm(chart), theme=None, alt=alt_text)
