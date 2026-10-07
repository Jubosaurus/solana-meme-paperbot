"""Dashboard lokal fotografieren: python tools/foto.py uebersicht dashboard/.venv/fotos.

Nutzt dashboard/.venv, sperrt externe Verbindungen und verhindert git pull.
Chromium installieren mit PLAYWRIGHT_BROWSERS_PATH=dashboard/.venv/chromium.
"""

import argparse
import os
from pathlib import Path
import re
import socket
import subprocess
import sys
import time
from urllib.parse import urlsplit
from urllib.request import ProxyHandler, build_opener


REPO = Path(__file__).resolve().parent.parent
VENV = REPO / "dashboard" / ".venv"
PYTHON = VENV / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
LOKAL = {"localhost", "127.0.0.1", "::1"}


def lokal(url):
    """Nur HTTP und WebSockets auf localhost erlauben."""
    ziel = urlsplit(url)
    return ziel.scheme in {"http", "ws"} and ziel.hostname == "localhost"


def nur_lokale_verbindungen():
    """Auch RSS, DNS und direkte Socket-Verbindungen nach draussen sperren."""
    aufloesen = socket.getaddrinfo
    verbinden = socket.socket.connect
    verbinden_ex = socket.socket.connect_ex

    def pruefen(host):
        if host not in LOKAL:
            raise OSError("Fotomodus erlaubt nur localhost.")

    def getaddrinfo(host, *args, **kwargs):
        pruefen(host)
        return aufloesen(host, *args, **kwargs)

    def connect(sock, adresse):
        pruefen(adresse[0])
        return verbinden(sock, adresse)

    def connect_ex(sock, adresse):
        pruefen(adresse[0])
        return verbinden_ex(sock, adresse)

    socket.getaddrinfo = getaddrinfo
    socket.socket.connect = connect
    socket.socket.connect_ex = connect_ex


def streamlit_starten(port):
    """Fotomodus nur im Kindprozess; Projektdateien bleiben unveraendert."""
    nur_lokale_verbindungen()
    sys.path.insert(0, str(REPO / "dashboard"))
    import rechnung

    def lokaler_stand(repo=None):
        return False, "Fotomodus: lokaler Stand, kein git pull", "fotomodus"

    def keine_rss():
        return [], ["Fotomodus: RSS gesperrt"] * len(rechnung.listings.RSS_QUELLEN)

    rechnung.git_pull = lokaler_stand
    rechnung.news_holen = keine_rss

    # Git darf hier ausschliesslich lokale Historie lesen, auch auf anderen Seiten.
    def prozess_pruefen(ereignis, args):
        if ereignis == "subprocess.Popen":
            befehl = args[1]
            if (not isinstance(befehl, (list, tuple)) or len(befehl) < 2
                    or Path(befehl[0]).name.lower() not in {"git", "git.exe"}
                    or befehl[1] not in {"log", "rev-parse"}):
                raise PermissionError("Fotomodus sperrt schreibende und externe Prozesse.")

    sys.addaudithook(prozess_pruefen)
    from streamlit.web.cli import main

    sys.argv = [
        "streamlit", "run", str(REPO / "dashboard" / "app.py"),
        "--server.port", str(port), "--server.address", "localhost",
        "--server.headless", "true", "--browser.gatherUsageStats", "false",
        "--server.fileWatcherType", "none",
    ]
    main()


def warten(prozess, url, timeout=60):
    """Auf die echte Streamlit-Bereitschaft warten, ohne Proxy-Zugriffe."""
    opener = build_opener(ProxyHandler({}))
    ende = time.monotonic() + timeout
    while time.monotonic() < ende:
        if prozess.poll() is not None:
            raise RuntimeError(f"Streamlit wurde vorzeitig beendet (Exitcode {prozess.returncode}).")
        try:
            with opener.open(url + "/_stcore/health", timeout=1) as antwort:
                if antwort.status == 200 and antwort.read() == b"ok":
                    return
        except OSError:
            pass
        time.sleep(0.2)
    raise RuntimeError("Streamlit ist nach 60 Sekunden nicht erreichbar.")


def fotos(seite, ausgabe):
    from playwright.sync_api import sync_playwright

    # Port dynamisch waehlen, damit ein laufendes Dashboard unberuehrt bleibt.
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    url = f"http://localhost:{port}"
    env = os.environ.copy()
    env["PLAYWRIGHT_BROWSERS_PATH"] = str(VENV / "chromium")
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"
    env["STREAMLIT_SERVER_ENABLE_STATIC_SERVING"] = "false"
    prozess = subprocess.Popen(
        [str(PYTHON), str(Path(__file__).resolve()), "--streamlit", str(port)],
        cwd=REPO, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
    )
    try:
        warten(prozess, url)
        os.environ["PLAYWRIGHT_BROWSERS_PATH"] = env["PLAYWRIGHT_BROWSERS_PATH"]
        with sync_playwright() as pw:
            browser = pw.chromium.launch(args=["--disable-background-networking", "--no-proxy-server"])
            try:
                for name, breite, hoehe in (("desktop", 1280, 3200), ("handy", 390, 4200)):
                    with browser.new_context(
                        viewport={"width": breite, "height": hoehe}, device_scale_factor=1,
                        is_mobile=name == "handy", has_touch=name == "handy", service_workers="block",
                    ) as context:
                        context.route("**/*", lambda route: route.continue_()
                                      if lokal(route.request.url) else route.abort())
                        context.route_web_socket("**/*", lambda ws: ws.connect_to_server()
                                                 if lokal(ws.url) else ws.close())
                        page = context.new_page()
                        page.goto(url + ("/" if seite == "uebersicht" else "/" + seite),
                                  wait_until="domcontentloaded", timeout=60_000)
                        page.locator(".nx-fuss").wait_for(timeout=120_000)
                        if page.locator('[data-testid="stException"]').count():
                            raise RuntimeError("Die Dashboard-Seite meldet einen Fehler.")
                        if seite != "uebersicht" and urlsplit(page.url).path.rstrip("/") != "/" + seite:
                            raise RuntimeError("Der Seitenname wurde vom Dashboard nicht gefunden.")
                        page.evaluate("document.fonts.ready")
                        page.wait_for_timeout(2500)
                        if name == "handy":
                            breit = page.evaluate("document.documentElement.scrollWidth > window.innerWidth + 1")
                            print(f"{seite} handy seitliches Scrollen: {breit}")
                        page.screenshot(path=str(ausgabe / f"{seite}_{name}.png"),
                                        full_page=True, animations="disabled")
            finally:
                browser.close()
    finally:
        if prozess.poll() is None:
            prozess.terminate()
            try:
                prozess.wait(timeout=10)
            except subprocess.TimeoutExpired:
                prozess.kill()
                prozess.wait(timeout=10)


def main():
    parser = argparse.ArgumentParser(description="Lokale Dashboard-Fotos mit 1280 und 390 Pixel Breite.")
    parser.add_argument("seite", help="Seitenname in der URL, z. B. uebersicht oder copy_trading")
    parser.add_argument("ausgabe", type=Path, help="Ausgabeordner innerhalb dieses Worktrees")
    args = parser.parse_args()
    if not re.fullmatch(r"[a-zA-Z0-9_-]+", args.seite):
        parser.error("Bitte nur einen Seitennamen angeben, keine URL oder Pfade.")
    ausgabe = args.ausgabe.resolve()
    if not ausgabe.is_relative_to(REPO) or ausgabe == REPO:
        parser.error("Der Ausgabeordner muss innerhalb dieses Worktrees liegen.")
    # Screenshots duerfen nie in den geschuetzten Datenordnern landen.
    if ausgabe.relative_to(REPO).parts[0] in {"flugschreiber", "verlauf", "experimente", "copy", "scout", ".git", ".claude"}:
        parser.error("Dieser Ordner ist fuer Fotos gesperrt.")
    if any((ausgabe / f"{args.seite}_{name}.png").exists() for name in ("desktop", "handy")):
        parser.error("Vorhandene Fotos werden nicht ueberschrieben. Bitte einen anderen Ordner waehlen.")
    if not PYTHON.is_file():
        parser.error("dashboard/.venv fehlt. Bitte zuerst die Umgebung laut Auftragskarte einrichten.")
    if Path(sys.prefix).resolve() != VENV.resolve():
        env = os.environ.copy()
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        raise SystemExit(subprocess.call([str(PYTHON), str(Path(__file__).resolve()), *sys.argv[1:]], env=env))
    try:
        import streamlit  # noqa: F401
        import playwright.sync_api  # noqa: F401
        from playwright.sync_api import Error as PlaywrightError
    except ImportError as err:
        parser.exit(1, f"Fotos fehlgeschlagen: {err}\n")
    try:
        ausgabe.mkdir(parents=True, exist_ok=True)
        fotos(args.seite, ausgabe)
    except (OSError, RuntimeError, PlaywrightError) as err:
        parser.exit(1, f"Fotos fehlgeschlagen: {err}\n")
    print(f"Fotos erstellt: {ausgabe / (args.seite + '_desktop.png')} und {ausgabe / (args.seite + '_handy.png')}")


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--streamlit":
        streamlit_starten(int(sys.argv[2]))
    else:
        main()
