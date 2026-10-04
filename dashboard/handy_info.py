"""Hilfe fuer start_handy.bat: zeigt die Heimnetz-Adresse des PCs und erzeugt einen QR-Code (handy_qr.png).
Nur Anzeige, schreibt nichts ausser der Bilddatei handy_qr.png (nicht im Repository)."""
import os
import socket
import subprocess
import sys

PORT = 8501
BILD = os.path.join(os.path.dirname(os.path.abspath(__file__)), "handy_qr.png")


def heimnetz_ip():
    """IP des PCs im Heimnetz. Der UDP-Trick schickt nichts, er fragt nur, welche Netzkarte genutzt wuerde."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("192.0.2.1", 9))
        return s.getsockname()[0]
    except OSError:
        return None
    finally:
        s.close()


def netz_art():
    """'Private', 'Public' oder None (Windows-Einstufung des aktuellen Netzwerks)."""
    try:
        res = subprocess.run(["powershell", "-NoProfile", "-Command",
                              "(Get-NetConnectionProfile | Select-Object -First 1).NetworkCategory"],
                             capture_output=True, text=True, timeout=15)
        return res.stdout.strip() or None
    except (OSError, subprocess.SubprocessError):
        return None


def main():
    ip = heimnetz_ip()
    if not ip:
        print("Keine Netzwerkverbindung gefunden. Ist der PC mit dem WLAN/Heimnetz verbunden?")
        return 1
    url = f"http://{ip}:{PORT}"
    print(f"\n  Adresse im Heimnetz: {url}\n")
    art = netz_art()
    if art == "Public":
        print("  ACHTUNG: Windows stuft dieses Netzwerk als OEFFENTLICH ein. Dann blockiert die Firewall den Zugriff.")
        print("  Loesung: Windows-Einstellungen > Netzwerk > WLAN/Ethernet > Eigenschaften > 'Privat'.\n")
    try:
        import segno
        segno.make(url, error="m").save(BILD, scale=10, border=2)
        print("  QR-Code gespeichert, er oeffnet sich gleich. Mit der Handy-Kamera scannen.")
        os.startfile(BILD)
    except Exception as err:  # QR ist nur Komfort, die Adresse steht oben
        print(f"  QR-Code nicht moeglich ({err}). Tippe die Adresse oben im Handy-Browser ein.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
