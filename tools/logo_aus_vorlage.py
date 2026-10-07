"""Erzeugt aus dem Original-Logo (JPG, dunkler Hintergrund) die Bilder in dashboard/static/.

Aufruf (nur wenn das Logo geaendert wird; Pillow, numpy und fonttools+brotli noetig, z. B. mit dashboard/.venv):
    python tools/logo_aus_vorlage.py [pfad/zur/vorlage.jpg]
Der einfarbige Hintergrund wird mit weichem Rand freigestellt (Alpha aus dem Abstand zur Hintergrundfarbe,
Farbe am Rand zurueckgerechnet = keine dunklen Saeume). Ergebnis: PNG mit Transparenz, kein SVG (die Verlaeufe
liessen sich als Vektor nicht treu nachbauen). Ersetzt den bisherigen Vektor-Logo-Erzeuger.
"""
import io
import json
import sys
from pathlib import Path

import numpy as np
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont
from PIL import Image, ImageDraw, ImageFont

STATIC = Path(__file__).resolve().parent.parent / "dashboard" / "static"
VORLAGE = STATIC / "neu" / "Gemini_Generated_Image_xo8v14xo8v14xo8v.jpg"
CANVAS = (8, 11, 17)
TEXT = (226, 232, 240)


def freistellen(pfad):
    rgb = np.asarray(Image.open(pfad).convert("RGB")).astype(np.float32)
    rand = np.concatenate([rgb[:300].reshape(-1, 3), rgb[-300:].reshape(-1, 3)])
    bg = np.median(rand, axis=0)
    dist = np.abs(rgb - bg).max(axis=2)
    alpha = np.clip((dist - 6.0) / 34.0, 0.0, 1.0)
    a = alpha[..., None]
    farbe = np.where(a > 0.02, (rgb - (1 - a) * bg) / np.maximum(a, 0.02), 0)
    farbe = np.clip(farbe, 0, 255)
    out = np.dstack([farbe, alpha * 255]).astype(np.uint8)
    return Image.fromarray(out, "RGBA")


def zuschneiden(img, rand=0.0):
    box = img.getchannel("A").point(lambda v: 255 if v > 8 else 0).getbbox()
    img = img.crop(box)
    if rand:
        pad = int(max(img.size) * rand)
        neu = Image.new("RGBA", (img.width + 2 * pad, img.height + 2 * pad), (0, 0, 0, 0))
        neu.paste(img, (pad, pad))
        img = neu
    return img


def quadrat(img, kante, rand=0.06):
    img = zuschneiden(img)
    innen = int(kante * (1 - 2 * rand))
    img = img.resize((innen, int(innen * img.height / img.width)) if img.width >= img.height
                     else (int(innen * img.width / img.height), innen), Image.LANCZOS)
    flaeche = Image.new("RGBA", (kante, kante), (0, 0, 0, 0))
    flaeche.paste(img, ((kante - img.width) // 2, (kante - img.height) // 2), img)
    return flaeche


def schrift(groesse):
    font = TTFont(io.BytesIO((STATIC / "fonts" / "SpaceGrotesk.woff2").read_bytes()))
    font.flavor = None
    if "fvar" in font:
        font = instantiateVariableFont(font, {"wght": 600})
    puffer = io.BytesIO()
    font.save(puffer)
    puffer.seek(0)
    return ImageFont.truetype(puffer, groesse)


def mit_schrift(zeichen, hoehe=512):
    z = quadrat(zeichen, hoehe, rand=0.0)
    f = schrift(int(hoehe * 0.34))
    text = "Nexus Core"
    breite = int(ImageDraw.Draw(Image.new("L", (1, 1))).textlength(text, font=f))
    luecke = int(hoehe * 0.10)
    bild = Image.new("RGBA", (hoehe + luecke + breite + int(hoehe * 0.04), hoehe), (0, 0, 0, 0))
    bild.paste(z, (0, 0), z)
    d = ImageDraw.Draw(bild)
    d.text((hoehe + luecke, hoehe // 2), text, font=f, fill=TEXT + (255,), anchor="lm")
    return bild


def symbol(zeichen, kante, anteil):
    """App-Symbol: Zeichen auf dunklem Grund, innerhalb der 'maskable'-Schutzzone."""
    grund = Image.new("RGBA", (kante, kante), CANVAS + (255,))
    z = quadrat(zeichen, int(kante * anteil), rand=0.0)
    grund.paste(z, ((kante - z.width) // 2, (kante - z.height) // 2), z)
    return grund


def main():
    pfad = Path(sys.argv[1]) if len(sys.argv) > 1 else VORLAGE
    z = zuschneiden(freistellen(pfad))
    quadrat(z, 1024).save(STATIC / "nexus-core-bildzeichen.png", optimize=True)
    mit_schrift(z, 512).save(STATIC / "nexus-core-logo-text.png", optimize=True)
    quadrat(z, 64, rand=0.04).save(STATIC / "favicon.png", optimize=True)
    quadrat(z, 96, rand=0.0).save(STATIC / "nexus-core-bildzeichen-klein.png", optimize=True)
    symbol(z, 192, 0.66).save(STATIC / "icon-192.png", optimize=True)
    symbol(z, 512, 0.66).save(STATIC / "icon-512.png", optimize=True)
    symbol(z, 180, 0.72).convert("RGB").save(STATIC / "apple-touch-icon.png", optimize=True)
    print("fertig")


if __name__ == "__main__":
    main()
