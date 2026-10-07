"""Erscheinungsbild "Nexus Core" an EINER Stelle: Farben, CSS, Logo, Icons, Diagramm-Thema.

Vorgaben stehen in DESIGN.md (Farben Abschnitt 2, Schriften Abschnitt 3, Komponenten Abschnitt 4).
Bei einem Streamlit-Update nur hier nachsehen: Eigene Bausteine nutzen eigene Klassen (pb-..., nx-...); nur
wenige Regeln greifen auf Streamlit-Elemente zu (markiert mit "Streamlit-intern").
Gruen/Rot gehoeren nur Leistungswerten und sind nie allein: immer mit Pfeil und Vorzeichen.
"""
import base64
from pathlib import Path

import streamlit as st

STATIC = Path(__file__).parent / "static"

# ---------------------------------------------------------------- Farben (DESIGN.md Abschnitt 2)
CANVAS = "#080B11"
KARTE = "#0F172A"
LINIE = "#1E293B"
INDIGO = "#6366F1"
INDIGO_HELL = "#A5B4FC"
PLUS = "#10B981"          # Gewinn / ok (immer mit ▲ und +)
MINUS = "#F43F5E"         # Verlust (immer mit ▼ und −)
WARN = "#F59E0B"          # Hinweis / verzoegert
TEXT = "#E2E8F0"
TEXT_LEISE = "#94A3B8"
NEUTRAL = "#64748B"
KONTROLLE = "#64748B"     # Kontrollgruppe in Diagrammen: ruhiges Grau
# alte Namen, damit bestehende Seiten weiterlaufen
HINTERGRUND, FLAECHE, VIOLETT, BLAU = CANVAS, KARTE, INDIGO, "#38BDF8"

MONO = "'JetBrains Mono', ui-monospace, monospace"

CSS = """
<style>
/* ======== Grundflaeche (Streamlit-intern: stApp, stHeader, stSidebar, stMainBlockContainer) ======== */
[data-testid="stApp"] {
  background: radial-gradient(1100px 380px at 85% -6%, rgba(99, 102, 241, 0.10), transparent 70%), __CANVAS__;
}
[data-testid="stAppViewContainer"], [data-testid="stMain"] { background: transparent; }
/* Obere Leiste: deckend (nicht durchsichtig), damit beim Scrollen nichts durchscheint */
[data-testid="stHeader"] {
  background: __CANVAS__ !important; border-bottom: 1px solid __LINIE__; z-index: 999990;
  box-shadow: 0 6px 18px rgba(8, 11, 17, 0.9);
}
[data-testid="stMainBlockContainer"] { padding-top: 5rem; max-width: 1320px; }
[data-testid="stSidebar"] { background: #0B1120; border-right: 1px solid __LINIE__; }
[data-testid="stSidebarHeader"] { padding-bottom: 0.2rem; }
[data-testid="stSidebarContent"] { scrollbar-width: thin; }
h1, h2, h3 { letter-spacing: -0.01em; }
[data-testid="stCaptionContainer"], .stCaption { color: __TEXT_LEISE__; }

/* ======== Menue links: Gruppen aufklappbar, aktive Seite mit Indigo-Balken ======== */
[data-testid="stSidebar"] [data-testid="stExpander"] details {
  border: none; background: transparent; margin: 0 0 2px;
}
[data-testid="stSidebar"] [data-testid="stExpander"] summary {
  padding: 6px 8px; border-radius: 8px; color: __TEXT_LEISE__; font-size: 0.74rem; font-weight: 600;
  text-transform: uppercase; letter-spacing: 0.08em;
}
[data-testid="stSidebar"] [data-testid="stExpander"] summary:hover { color: __TEXT__; background: rgba(99, 102, 241, 0.08); }
[data-testid="stSidebar"] [data-testid="stExpander"] [data-testid="stExpanderDetails"] { padding: 0 0 4px 0; }
[data-testid="stSidebar"] [data-testid="stPageLink-NavLink"] {
  border-radius: 8px; padding: 7px 10px; border-left: 2px solid transparent; font-size: 0.92rem;
}
[data-testid="stSidebar"] [data-testid="stPageLink-NavLink"]:hover { background: rgba(99, 102, 241, 0.10); }
[data-testid="stSidebar"] [data-testid="stPageLink-NavLink"][aria-current="page"] {
  background: rgba(99, 102, 241, 0.16); border-left-color: __INDIGO__; color: #fff; font-weight: 600;
}

/* ======== Streamlit-Karten, Kennzahlen, Tabs, Meldungen (Streamlit-intern) ======== */
[data-testid="stVerticalBlockBorderWrapper"]:has(> [data-testid="stVerticalBlock"]) { border-radius: 14px; }
[data-testid="stVerticalBlockBorderWrapper"] { border-color: __LINIE__ !important; }
[data-testid="stMetric"] { background: __KARTE__; border: 1px solid __LINIE__; border-radius: 14px; padding: 12px 16px; }
[data-testid="stMetricValue"] { font-family: __MONO__; font-variant-numeric: tabular-nums; font-weight: 600; }
[data-testid="stTabs"] [role="tab"][aria-selected="true"] { color: #fff; }
[data-testid="stAlert"] { border: 1px solid __LINIE__; border-radius: 12px; }
[data-testid="stSpinner"] { color: __TEXT_LEISE__; }
[data-testid="stSpinnerIcon"] { border-top-color: __INDIGO__ !important; }
[data-testid="stExpander"] details { border-color: __LINIE__; border-radius: 12px; background: __KARTE__; }
[data-testid="stDataFrame"] { border: 1px solid __LINIE__; border-radius: 12px; }

/* ======== Eigene Bausteine ======== */
.pb-raster { display: grid; gap: 14px; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); }
.pb-raster.gross { grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); }
.pb-raster.breit { grid-template-columns: repeat(auto-fill, minmax(340px, 1fr)); }
.pb-karte {
  position: relative; border-radius: 14px; padding: 16px 18px 14px; background: __KARTE__;
  border: 1px solid __LINIE__; min-width: 0;
}
.pb-karte.leuchten { border-color: rgba(99, 102, 241, 0.55); box-shadow: 0 0 0 1px rgba(99, 102, 241, 0.18), 0 8px 28px rgba(99, 102, 241, 0.12); }
.pb-titel { min-height: 24px; display: flex; justify-content: space-between; align-items: center; gap: 8px; font-size: 0.78rem;
            color: __TEXT_LEISE__; letter-spacing: 0.02em; }
.pb-zahl { font-family: __MONO__; font-variant-numeric: tabular-nums; font-size: 1.8rem; font-weight: 700;
           letter-spacing: -0.02em; margin: 6px 0 2px; line-height: 1.15; white-space: nowrap; color: #F8FAFC; }
.pb-zahl.klein { font-size: 1.4rem; }
.pb-unter { font-size: 0.82rem; color: __TEXT_LEISE__; }
.pb-plus, .pb-minus, .pb-null { font-family: __MONO__; font-variant-numeric: tabular-nums; }
.pb-plus { color: __PLUS__; font-weight: 600; }
.pb-minus { color: __MINUS__; font-weight: 600; }
.pb-null { color: __NEUTRAL__; font-weight: 600; }
.pb-chip {
  display: inline-block; font-size: 0.72rem; padding: 2px 9px; border-radius: 999px; white-space: nowrap;
  background: rgba(99, 102, 241, 0.14); color: #C7D2FE; border: 1px solid rgba(99, 102, 241, 0.30);
}
.pb-chip.gut { background: rgba(16, 185, 129, 0.12); color: #6EE7B7; border-color: rgba(16, 185, 129, 0.32); }
.pb-chip.schlecht { background: rgba(244, 63, 94, 0.12); color: #FDA4AF; border-color: rgba(244, 63, 94, 0.34); }
.pb-chip.achtung { background: rgba(245, 158, 11, 0.12); color: #FCD34D; border-color: rgba(245, 158, 11, 0.34); }
.nx-urteil { display: flex; flex-direction: column; gap: 4px; align-items: flex-start; min-width: 0; }
.nx-urteil .pb-chip { white-space: normal; border-radius: 10px; line-height: 1.35; padding: 3px 9px; }
.pb-zeile > div { min-width: 0; }
.pb-zeile { display: flex; align-items: flex-end; justify-content: space-between; gap: 10px; }
.pb-fuss { margin-top: 8px; }
.pb-spark { display: block; width: 100%; height: 44px; }
.pb-ring { width: 62px; height: 62px; flex: 0 0 auto; }
.pb-hinweis {
  display: flex; gap: 10px; align-items: flex-start; border-radius: 10px; padding: 9px 14px; margin: 4px 0 8px;
  font-size: 0.88rem; background: rgba(245, 158, 11, 0.07); border: 1px solid rgba(245, 158, 11, 0.40);
  border-left-width: 3px; color: #FDE68A;
}
.pb-liste { display: flex; flex-direction: column; gap: 2px; }
.pb-eintrag { display: grid; grid-template-columns: 30px 1fr auto; gap: 10px; align-items: center;
              padding: 9px 6px; border-bottom: 1px solid rgba(30, 41, 59, 0.9); }
.pb-eintrag:last-child { border-bottom: none; }
.pb-symbol { width: 30px; height: 30px; border-radius: 8px; display: flex; align-items: center; justify-content: center;
             font-size: 0.8rem; font-weight: 700; background: rgba(99, 102, 241, 0.14); color: #C7D2FE; }
.pb-symbol.plus { background: rgba(16, 185, 129, 0.14); color: __PLUS__; }
.pb-symbol.minus { background: rgba(244, 63, 94, 0.14); color: __MINUS__; }
.pb-name { font-weight: 600; font-size: 0.92rem; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.pb-detail { font-size: 0.78rem; color: __TEXT_LEISE__; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.pb-wert { text-align: right; font-size: 0.9rem; white-space: nowrap; font-family: __MONO__; font-variant-numeric: tabular-nums; }
.pb-news { padding: 10px 6px; border-bottom: 1px solid rgba(30, 41, 59, 0.9); }
.pb-news:last-child { border-bottom: none; }
.pb-chips { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 5px; }
.pb-frei { white-space: normal !important; overflow: visible !important; text-overflow: clip !important; }
.pb-link { color: __TEXT__; text-decoration: underline; text-decoration-color: rgba(99, 102, 241, 0.6); }
.pb-scroll { max-height: 520px; overflow-y: auto; padding-right: 4px; }

/* ---- Seitenkopf mit Status-Pillen ---- */
.nx-kopf { margin: 0 0 14px; }
.nx-kopf h1 { font-family: 'Space Grotesk', sans-serif; font-size: 1.9rem; font-weight: 700; margin: 0 0 2px; letter-spacing: -0.02em; }
.nx-kopf p { margin: 0 0 8px; color: __TEXT_LEISE__; font-size: 0.9rem; }
.nx-pillen { display: flex; flex-wrap: wrap; gap: 8px; margin: 8px 0 4px; }
.nx-pille { display: inline-flex; align-items: center; gap: 7px; font-size: 0.76rem; padding: 3px 11px 3px 9px;
            border-radius: 999px; white-space: nowrap; background: rgba(15, 23, 42, 0.9); border: 1px solid __LINIE__;
            color: __TEXT_LEISE__; }
.nx-pille b { font-weight: 600; }
.nx-pille.gut { color: #6EE7B7; border-color: rgba(16, 185, 129, 0.35); }
.nx-pille.achtung { color: #FCD34D; border-color: rgba(245, 158, 11, 0.40); }
.nx-pille.schlecht { color: #FDA4AF; border-color: rgba(244, 63, 94, 0.40); }
.nx-punkt { width: 6px; height: 6px; border-radius: 50%; background: currentColor; flex: 0 0 auto; }
.nx-pille.gut .nx-punkt { animation: nxpuls 2.2s ease-in-out infinite; box-shadow: 0 0 6px currentColor; }
.nx-dreieck { font-size: 0.6rem; line-height: 1; }
@keyframes nxpuls { 0%, 100% { opacity: 1; transform: scale(1); } 50% { opacity: 0.35; transform: scale(0.7); } }
@media (prefers-reduced-motion: reduce) { .nx-pille.gut .nx-punkt { animation: none; } }

/* ---- roh und mit Kosten nebeneinander ---- */
.nx-duo { display: grid; grid-template-columns: 1fr 1fr; gap: 0; margin-top: 8px; }
.nx-duo > div { padding: 2px 12px 2px 0; min-width: 0; }
.nx-duo > div + div { padding: 2px 0 2px 14px; border-left: 1px solid __LINIE__; }
.nx-duo .nx-mini { font-size: 0.68rem; text-transform: uppercase; letter-spacing: 0.08em; color: __TEXT_LEISE__; }
.nx-duo .nx-mini.kosten { color: #FCD34D; }
.nx-duo .pb-zahl { font-size: 1.35rem; margin: 3px 0 1px; }

/* ---- Tabellen: Spalten passen sich dem Inhalt an, Text bricht um, erste Spalte bleibt stehen ---- */
.nx-tabelle { overflow: auto; border: 1px solid __LINIE__; border-radius: 12px; background: __KARTE__; max-height: 560px; }
.nx-tabelle table { border-collapse: separate; border-spacing: 0; width: max-content; min-width: 100%; font-size: 0.85rem; }
.nx-tabelle th { position: sticky; top: 0; z-index: 2; background: #121C33; color: __TEXT_LEISE__; text-align: left;
                 font-size: 0.68rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.06em;
                 padding: 9px 12px; border-bottom: 1px solid __LINIE__; vertical-align: bottom; }
.nx-tabelle td { padding: 8px 12px; border-bottom: 1px solid rgba(30, 41, 59, 0.8); vertical-align: top;
                 overflow-wrap: anywhere; min-width: 3.5rem; }
.nx-tabelle tr:last-child td { border-bottom: none; }
.nx-tabelle tbody tr:hover td { background: rgba(99, 102, 241, 0.06); }
.nx-tabelle th.num, .nx-tabelle td.num { text-align: right; white-space: nowrap; font-family: __MONO__;
                                         font-variant-numeric: tabular-nums; }
.nx-tabelle td:first-child, .nx-tabelle th:first-child { position: sticky; left: 0; z-index: 1; background: __KARTE__;
                                                         font-weight: 600; }
.nx-tabelle th:first-child { z-index: 3; background: #121C33; }
.nx-tabelle td.text { min-width: 9rem; max-width: 28rem; }

/* ---- Leerzustand und Fehler ---- */
.nx-leer { display: flex; flex-direction: column; align-items: center; text-align: center; gap: 6px; padding: 26px 18px;
           border: 1px dashed #2A3A58; border-radius: 14px; background: rgba(15, 23, 42, 0.6); color: __TEXT_LEISE__; }
.nx-leer img { width: 36px; height: 36px; opacity: 0.9; }
.nx-leer b { color: __TEXT__; font-size: 0.95rem; }
.nx-leer span { font-size: 0.82rem; max-width: 52ch; }
.nx-fehler { display: flex; gap: 12px; align-items: flex-start; padding: 12px 16px; border-radius: 12px; margin: 6px 0;
             background: rgba(244, 63, 94, 0.07); border: 1px solid rgba(244, 63, 94, 0.40); border-left-width: 3px; }
.nx-fehler img { width: 22px; height: 22px; flex: 0 0 auto; margin-top: 1px; }
.nx-fehler b { color: #FDA4AF; display: block; font-size: 0.92rem; }
.nx-fehler span { color: __TEXT_LEISE__; font-size: 0.82rem; }

/* ---- Fusszeile ---- */
.nx-fuss { display: flex; flex-wrap: wrap; gap: 6px 16px; align-items: center; font-size: 0.74rem; color: __NEUTRAL__;
           border-top: 1px solid __LINIE__; padding: 10px 2px 2px; margin-top: 28px; }
.nx-fuss b { color: __TEXT_LEISE__; font-weight: 600; }
.nx-fuss .nx-fuss-marke { display: inline-flex; align-items: center; gap: 6px; }
.nx-fuss img { height: 14px; width: 14px; }
.nx-fuss-leiste { margin-top: 28px; border-top: 1px solid __LINIE__; padding-top: 8px; }

/* ---- Handy ---- */
@media (max-width: 640px) {
  [data-testid="stMainBlockContainer"] { padding-top: 4.2rem; padding-left: 1rem; padding-right: 1rem; }
  .pb-zahl { font-size: 1.55rem; }
  .pb-raster, .pb-raster.gross, .pb-raster.breit { grid-template-columns: 1fr; }
  .nx-kopf h1 { font-size: 1.55rem; }
  .nx-duo .pb-zahl { font-size: 1.2rem; }
}
</style>
"""

_TOKEN = {"__CANVAS__": CANVAS, "__KARTE__": KARTE, "__LINIE__": LINIE, "__INDIGO__": INDIGO, "__PLUS__": PLUS,
          "__MINUS__": MINUS, "__TEXT__": TEXT, "__TEXT_LEISE__": TEXT_LEISE, "__NEUTRAL__": NEUTRAL, "__MONO__": MONO}


def _css():
    text = CSS
    for k, v in _TOKEN.items():
        text = text.replace(k, v)
    return text


# ---------------------------------------------------------------- Icons (kleine SVG-Bilder, als Data-URI)
_ICONS = {
    "leer": '<rect x="3" y="5" width="18" height="14" rx="3" fill="none" stroke="{c}" stroke-width="1.6"/>'
            '<path d="M3 13h5l1.5 2.5h5L16 13h5" fill="none" stroke="{c}" stroke-width="1.6" stroke-linejoin="round"/>',
    "fehler": '<path d="M12 3.5 22 20H2L12 3.5Z" fill="none" stroke="{c}" stroke-width="1.7" stroke-linejoin="round"/>'
              '<path d="M12 10v5M12 17.6v.1" stroke="{c}" stroke-width="1.8" stroke-linecap="round"/>',
    "info": '<circle cx="12" cy="12" r="9" fill="none" stroke="{c}" stroke-width="1.6"/>'
            '<path d="M12 11v5M12 7.6v.1" stroke="{c}" stroke-width="1.8" stroke-linecap="round"/>',
}


def icon_uri(name, farbe=INDIGO_HELL):
    svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">' + _ICONS[name].format(c=farbe) + "</svg>")
    return "data:image/svg+xml;base64," + base64.b64encode(svg.encode()).decode("ascii")


def marke_uri():
    """Logo-Marke als Data-URI (fuer die Fusszeile)."""
    try:
        return "data:image/svg+xml;base64," + base64.b64encode((STATIC / "nexus-core-marke.svg").read_bytes()).decode("ascii")
    except OSError:
        return ""


def seite_einrichten():
    """Muss der ERSTE Streamlit-Aufruf sein: Titel, Favicon, Layout."""
    favicon = STATIC / "favicon.png"
    st.set_page_config(page_title="Nexus Core", page_icon=str(favicon) if favicon.exists() else None,
                       layout="wide", initial_sidebar_state="auto")


def logo_einbinden():
    """Logo in der oberen Leiste (ausgeklappt: Marke + Wortmarke, eingeklappt: nur die Marke)."""
    voll, marke = STATIC / "nexus-core-logo.svg", STATIC / "nexus-core-marke.svg"
    if voll.exists() and marke.exists():
        st.logo(str(voll), icon_image=str(marke), size="large")


def anwenden():
    """Eigenes CSS einmal je Seitenaufruf einbinden."""
    st.html(_css())


# ---------------------------------------------------------------- Diagramm-Thema (Altair/Vega-Lite)
def diagramm(chart):
    """Einheitliches Diagramm-Aussehen (dunkel, ruhig, haarfeine Achsen, Zahlen in Monospace)."""
    return (chart.configure(background="transparent", font="Inter, sans-serif")
            .configure_view(strokeWidth=0)
            .configure_axis(gridColor=LINIE, domainColor=LINIE, tickColor=LINIE, labelColor=TEXT_LEISE,
                            titleColor=TEXT_LEISE, labelFontSize=12, titleFontWeight="normal",
                            labelFont="JetBrains Mono, monospace")
            .configure_legend(labelColor=TEXT, titleColor=TEXT_LEISE, labelFontSize=12))


def zeigen(chart, alt_text):
    """Diagramm mit unserem Thema statt dem Streamlit-Thema anzeigen."""
    st.altair_chart(diagramm(chart), theme=None, alt=alt_text)
