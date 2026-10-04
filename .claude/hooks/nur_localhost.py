"""Claude-Code-Hook (PreToolUse auf Playwright-Navigation): nur http://localhost erlaubt.

Zweite Sicherung neben --allowed-origins des Playwright-MCP-Servers.
Exit 2 = blockieren.
"""
import json
import re
import sys

ERLAUBT = re.compile(r"^http://(localhost|127\.0\.0\.1)(:\d+)?(/|$)", re.I)


def main():
    try:
        daten = json.load(sys.stdin)
    except Exception:
        return
    url = (daten.get("tool_input") or {}).get("url")
    if url is None:
        return
    if not ERLAUBT.match(str(url).strip()):
        print(f"BLOCKIERT (Hook nur_localhost): Playwright darf nur http://localhost oeffnen, nicht {url}",
              file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
