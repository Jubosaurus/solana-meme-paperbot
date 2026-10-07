"""Einmaliges Hilfsskript: erzeugt das Nexus-Core-Logo (SVG), Symbole (PNG) und das Web-App-Manifest in static/.

Aufruf (nur wenn das Logo geaendert wird; braucht zusaetzlich fonttools, brotli und Pillow):
    python tools/nexus_logo_bauen.py
Die Wortmarke wird aus der Schrift Space Grotesk (SIL OFL) in Pfade umgewandelt, damit sie ohne Schrift-Laden
als Bild funktioniert. Farben stehen in DESIGN.md (Abschnitt 2).
"""
import json
from pathlib import Path

from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont
from PIL import Image, ImageDraw

HIER = Path(__file__).resolve().parent.parent / "dashboard"
STATIC = HIER / "static"
INDIGO, INDIGO_HELL, TEXT = "#6366F1", "#A5B4FC", "#E2E8F0"
CANVAS, KARTE, LINIE = "#080B11", "#0F172A", "#1E293B"

# Knoten (Viewbox 48x48): vier aussen, einer in der Mitte, Linien laufen zusammen (= "Nexus")
AUSSEN = [(12, 14), (12, 34), (36, 14), (36, 34)]
MITTE = (24, 24)


def marke_svg_innen(mit_rahmen=True):
    teile = []
    if mit_rahmen:
        teile.append(f'<rect x="1.5" y="1.5" width="45" height="45" rx="12" fill="{KARTE}" stroke="{LINIE}" stroke-width="1.5"/>')
    for x, y in AUSSEN:
        teile.append(f'<line x1="{x}" y1="{y}" x2="{MITTE[0]}" y2="{MITTE[1]}" stroke="{INDIGO}" stroke-opacity="0.6" '
                     f'stroke-width="2" stroke-linecap="round"/>')
    teile.append(f'<circle cx="{MITTE[0]}" cy="{MITTE[1]}" r="9.5" fill="none" stroke="{INDIGO}" stroke-opacity="0.35" stroke-width="1.5"/>')
    for x, y in AUSSEN:
        teile.append(f'<circle cx="{x}" cy="{y}" r="2.6" fill="{INDIGO_HELL}"/>')
    teile.append(f'<circle cx="{MITTE[0]}" cy="{MITTE[1]}" r="5.5" fill="{INDIGO}"/>')
    teile.append(f'<circle cx="{MITTE[0]}" cy="{MITTE[1]}" r="2" fill="#EEF2FF"/>')
    return "".join(teile)


def wortmarke():
    """Pfade fuer 'NEXUS' und 'CORE' (Space Grotesk 700), Rueckgabe: (pfad_nexus, pfad_core, breite, hoehe)."""
    f = instantiateVariableFont(TTFont(STATIC / "fonts" / "SpaceGrotesk.woff2"), {"wght": 700})
    gs, cmap = f.getGlyphSet(), f.getBestCmap()
    x, track, teile = 0, 70, {"NEXUS": [], "CORE": []}
    for wort in ("NEXUS", "CORE"):
        for ch in wort:
            g = cmap[ord(ch)]
            pen = SVGPathPen(gs)
            gs[g].draw(TransformPen(pen, (1, 0, 0, 1, x, 0)))
            teile[wort].append(pen.getCommands())
            x += gs[g].width + track
        x += 260  # Wortzwischenraum
    return " ".join(teile["NEXUS"]), " ".join(teile["CORE"]), x - 260 - track


def logo_svg():
    nexus, core, breite = wortmarke()
    s = 14 / 700  # Grosshoehe 14 px
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {48 + 12 + breite * s + 2:.1f} 48" height="48" '
            f'role="img" aria-label="Nexus Core">{marke_svg_innen()}'
            f'<g transform="translate(60 31) scale({s:.5f} -{s:.5f})">'
            f'<path d="{nexus}" fill="{TEXT}"/><path d="{core}" fill="{INDIGO_HELL}"/></g></svg>')


def png(groesse, dateiname, rahmen=False):
    """Symbol als PNG (4-fach gezeichnet und verkleinert = glatte Kanten). Vollflaechiger Canvas-Hintergrund."""
    k = 4
    g = groesse * k
    bild = Image.new("RGB", (g, g), CANVAS)
    d = ImageDraw.Draw(bild)
    skala = g * (0.80 if not rahmen else 0.72) / 48
    ox = oy = (g - 48 * skala) / 2

    def p(x, y):
        return ox + x * skala, oy + y * skala

    d.rounded_rectangle([*p(1.5, 1.5), *p(46.5, 46.5)], radius=12 * skala, fill=KARTE, outline=LINIE, width=int(1.5 * skala))
    for x, y in AUSSEN:
        d.line([p(x, y), p(*MITTE)], fill=(60, 63, 150), width=int(2 * skala))
    cx, cy = p(*MITTE)
    d.ellipse([cx - 9.5 * skala, cy - 9.5 * skala, cx + 9.5 * skala, cy + 9.5 * skala], outline=(46, 48, 120), width=max(1, int(1.5 * skala)))
    for x, y in AUSSEN:
        px, py = p(x, y)
        r = 2.6 * skala
        d.ellipse([px - r, py - r, px + r, py + r], fill=INDIGO_HELL)
    d.ellipse([cx - 5.5 * skala, cy - 5.5 * skala, cx + 5.5 * skala, cy + 5.5 * skala], fill=INDIGO)
    d.ellipse([cx - 2 * skala, cy - 2 * skala, cx + 2 * skala, cy + 2 * skala], fill="#EEF2FF")
    bild.resize((groesse, groesse), Image.LANCZOS).save(STATIC / dateiname)


def main():
    (STATIC / "nexus-core-logo.svg").write_text(logo_svg(), encoding="utf-8")
    (STATIC / "nexus-core-marke.svg").write_text(
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48" width="48" height="48" role="img" '
        f'aria-label="Nexus Core">{marke_svg_innen()}</svg>', encoding="utf-8")
    png(192, "icon-192.png")
    png(512, "icon-512.png")
    png(64, "favicon.png")
    (STATIC / "manifest.webmanifest").write_text(json.dumps({
        "name": "Nexus Core", "short_name": "Nexus Core", "start_url": "/", "display": "standalone",
        "background_color": CANVAS, "theme_color": CANVAS,
        "icons": [{"src": "icon-192.png", "sizes": "192x192", "type": "image/png"},
                  {"src": "icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any maskable"}]},
        indent=2, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
