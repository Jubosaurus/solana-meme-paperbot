"""Tag 17 auswerten: Wie liefen Coins, die als FOMO_SPRUNG knapp abgelehnt wurden?

Zweck:   Kursverlauf nach 1 h / 6 h, Nachrechnung "Hauptstrategie haette gekauft" (manage_positions,
         0,2 SOL, roh und mit 2 % Kosten, auch ohne die 3 besten), Vergleich mit echten Trades der
         Hauptstrategie und der Kontrollgruppe, Abgleich mit der Dashboard-Seite "Verpasste Chancen".
Stand:   Daten bis 07.10.2026 08:41 UTC (Zeitraum ab 02.10.2026 09:11 UTC). Ergebnis: auswertungen/2026-10-07_tag17.md.
         Das Skript liest immer den aktuellen Stand der Dateien; spaetere Laeufe geben andere Zahlen.
Aufruf:  dashboard/.venv/Scripts/python.exe auswertungen/skripte/tag17.py   (im Projekt-Hauptordner; nur lesen, kein Netzwerk,
         schreibt nur nach auswertungen/skripte/tag17_ausgabe/, nicht committen)
Vorlage: Codex (Sol), Auftragskarte 18; Claude hat Kursstatistik und echte Trades unabhaengig nachgerechnet.
"""
import sys
sys.dont_write_bytecode = True

import csv
import hashlib
import json
import math
import os
import socket
import statistics
import subprocess
from collections import Counter, defaultdict
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent / 'tag17_ausgabe'
OUT.mkdir(exist_ok=True)
START_DAY = datetime(2026, 10, 2, tzinfo=timezone.utc).timestamp()
GRUND = 'FOMO_SPRUNG'
COST = 0.02
INVESTMENT = 0.2
AUDIT = {}


def blocked(*args, **kwargs):
    raise RuntimeError('Netzwerk oder Prozessaufruf in der Auswertung gesperrt')


def audit(event, args):
    if event == 'open':
        path, mode, flags = args
        writing = (mode and any(c in mode for c in 'wax+')) or (flags and flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND))
        if writing and not isinstance(path, int) and not Path(path).resolve().is_relative_to(OUT):
            raise RuntimeError('Schreibzugriff ausserhalb der Ausgabe gesperrt')
    if event in ('socket.connect', 'socket.connect_ex', 'subprocess.Popen', 'os.system'):
        blocked()


sys.addaudithook(audit)
socket.create_connection = blocked
subprocess.Popen = blocked
os.system = blocked
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'dashboard'))
# Der Import bekommt keine Umgebungswerte und liest damit keine Zugangsdaten.
environment = os.environ
os.environ = {}
try:
    import bot as core
    import rechnung
finally:
    os.environ = environment
assert Path(core.__file__).resolve() == (ROOT / 'bot.py').resolve()
core.SESSION.request = blocked


def number(value, positive=False):
    try:
        x = float(value)
        return x if math.isfinite(x) and (not positive or x > 0) else None
    except (TypeError, ValueError):
        return None


def timestamp(value):
    try:
        if isinstance(value, (int, float)):
            return float(value) if math.isfinite(value) else None
        d = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
        return (d if d.tzinfo else d.replace(tzinfo=timezone.utc)).timestamp()
    except (ValueError, TypeError, OverflowError):
        return None


def utc(t):
    return datetime.fromtimestamp(t, timezone.utc).isoformat() if t is not None else None


def rows(path):
    info = AUDIT.setdefault(str(path.relative_to(ROOT)), {'zeilen': 0, 'kaputte_zeilen': 0})
    before = path.stat()
    digest = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            digest.update(chunk)
    info.update(sha256=digest.hexdigest(), bytes=before.st_size)
    with path.open(encoding='utf-8-sig', newline='') as f:
        reader = csv.reader(f)
        header = next(reader, [])
        info['spalten'] = header
        try:
            for values in reader:
                if not values:
                    continue
                info['zeilen'] += 1
                if len(values) != len(header):
                    info['kaputte_zeilen'] += 1
                    continue
                yield dict(zip(header, values))
        except (csv.Error, UnicodeError):
            info['datei_unvollstaendig_lesbar'] = True
    after = path.stat()
    info['waehrend_lesen_veraendert'] = (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns)


def load_json(path):
    data = path.read_bytes()
    AUDIT[str(path.relative_to(ROOT))] = {'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)}
    return json.loads(data)


def stats(trades, cost=False):
    vals = [t['pnl_sol'] - (t['invested_sol'] * COST if cost else 0) for t in trades]
    n = len(vals)
    return {'n': n, 'summe_sol': math.fsum(vals), 'durchschnitt_sol': statistics.mean(vals) if n else None,
            'median_sol': statistics.median(vals) if n else None, 'gewinner': sum(v > 0 for v in vals),
            'gewinner_pct': 100 * sum(v > 0 for v in vals) / n if n else None}


def summaries(trades):
    ordered = sorted(trades, key=lambda t: (-t['pnl_sol'], t['mint'], str(t.get('opened', ''))))
    return {'roh': stats(trades), 'kosten_2pct': stats(trades, True),
            'ohne_beste_3': {'roh': stats(ordered[3:]), 'kosten_2pct': stats(ordered[3:], True)},
            'entfernte_beste_3': [{'mint': t['mint'], 'symbol': t['symbol'], 'pnl_sol': t['pnl_sol']} for t in ordered[:3]]}


def horizons(cases, paths):
    result = {}
    for h in (1, 6):
        vals = []
        for mint, case in cases.items():
            target = case['zeit'] + h * 3600
            points = paths.get(mint, [])
            point = min(points, key=lambda r: (abs(r['zeit'] - target), r['zeit'])) if points else None
            measurement = {'ziel': utc(target), 'messbar': False}
            if point and abs(point['zeit'] - target) <= 300 and point['zeit'] > case['zeit'] and case['preis_usd'] is not None and point['preis_usd'] is not None:
                multiple = point['preis_usd'] / case['preis_usd']
                if math.isfinite(multiple):
                    vals.append(multiple)
                    measurement.update(messbar=True, zeit=utc(point['zeit']), preis_usd=point['preis_usd'],
                                       abstand_s=point['zeit'] - target, vielfaches=multiple, rendite_pct=(multiple-1)*100)
            case.setdefault('horizonte', {})[str(h)] = measurement
        n = len(vals)
        result[str(h)] = {'coins': len(cases), 'n': n, 'nicht_messbar': len(cases) - n,
                          'median_vielfaches': statistics.median(vals) if n else None,
                          'median_pct': (statistics.median(vals)-1)*100 if n else None,
                          'im_plus': sum(v > 1 for v in vals), 'im_plus_pct': 100*sum(v > 1 for v in vals)/n if n else None,
                          'mindestens_2x': sum(v >= 2 for v in vals), 'mindestens_2x_pct': 100*sum(v >= 2 for v in vals)/n if n else None}
    return result


def setup_simulation():
    for name in ('journal', 'log_path', 'save_portfolio', 'discord', 'flug_aufzeichnen', 'schedule_recheck'):
        setattr(core, name, lambda *a, **kw: None)
    core.portfolio_embed = lambda *a, **kw: None
    core.TX_FEE_SOL = 0.0
    core.CTX['watch'] = False


def simulate(mint, case, points):
    usable, invalid = [], 0
    for r in points:
        if r['zeit'] <= case['zeit']:
            continue
        if r['preis_usd'] is None or any(r.get(k) is None for k in ('liquiditaet', 'holder_1h_pct', 'netto_kaeufer_5m')):
            invalid += 1
        else:
            usable.append(r)
    base = case['preis_usd']
    record = {'mint': mint, 'symbol': case['symbol'], 'opened': utc(case['zeit']), 'invested_sol': INVESTMENT,
              'zeilen': len(usable), 'ungueltige_zeilen': invalid, 'zu_wenige_zeilen': len(usable) < 2}
    if not usable or base is None or case['liquiditaet'] is None:
        return dict(record, messbar=False, grund='NICHT_SIMULIERBAR', offen=None, pnl_sol=None)
    price = {'x': 1.0}
    core.quote = lambda i, o, raw: int(raw / 1e6 * price['x'] * 1e9)
    core.STATS = core.fresh_stats()
    pos = {'mint': mint, 'symbol': case['symbol'], 'opened': case['zeit'], 'invested_sol': INVESTMENT,
           'fees_sol': 0.0, 'entry_signal_usd': 1.0, 'entry_fill_usd': 1.0, 'entry_slippage_pct': 0.0,
           'roundtrip_cost_pct': None, 'tokens_initial': INVESTMENT, 'tokens_left': INVESTMENT,
           'decimals': 6, 'proceeds_sol': 0.0, 'peak_usd': 1.0, 'tp1_done': False, 'thesis_breaks': 0,
           'missing_loops': 0, 'liq_low_checks': 0, 'graduated': False, 'entry_liquidity': case['liquiditaet'],
           'entry_view': {}, 'bundle': {}, 'phase': 'normal', 'thesis': '', 'exit_rule': ''}
    p = {'bankroll_sol': 10.0, 'closed': [], 'cooldown': {}, 'watch': {}, 'positions': {mint: pos}}
    previous = case['zeit']
    gaps = []
    all_gaps = [b-a for a,b in zip([case['zeit']]+[r['zeit'] for r in usable], [r['zeit'] for r in usable]) if b-a > 900]
    sales = []
    core.journal = lambda kind, pos, px, sol, reason, *a, **kw: sales.append({'art': kind, 'grund': reason, 'kurs': px, 'sol': sol}) if kind in ('TEILVERKAUF', 'VERKAUF') else None
    for n, r in enumerate(usable, 1):
        if r['zeit'] - previous > 900:
            gaps.append(r['zeit'] - previous)
        previous = r['zeit']
        core.STATS['loops'] = n
        price['x'] = r['preis_usd'] / base
        tok = {'id': mint, 'symbol': case['symbol'], 'usdPrice': price['x'], 'liquidity': r['liquiditaet'],
               'stats1h': {'holderChange': r['holder_1h_pct']}, 'stats5m': {'numNetBuyers': int(r['netto_kaeufer_5m'])}}
        core.jup_tokens = lambda mints, tok=tok: {mint: tok}
        core.manage_positions(p, 1.0, r['zeit'])
        if not p['positions']:
            break
    is_open = bool(p['positions'])
    pnl = pos['proceeds_sol'] + pos['tokens_left'] * price['x'] - INVESTMENT if is_open else p['closed'][0]['pnl_sol']
    record.update(messbar=True, offen=is_open, pnl_sol=pnl, pnl_kosten_sol=pnl-INVESTMENT*COST,
                  grund='OFFEN' if is_open else p['closed'][0]['exit_reason'].split(' (')[0],
                  verkaufsgrund_voll=None if is_open else p['closed'][0]['exit_reason'], ende=utc(previous),
                  zeilen_bis_ende=n, letzte_kursrelation=price['x'], teilverkauf=pos['tp1_done'],
                  lueckenhaft=bool(all_gaps), luecken_bis_ende=bool(gaps), luecken_s=gaps, gesamter_verlauf_luecken_s=all_gaps,
                  zu_kurz=is_open or len(usable)<2, verkaeufe=sales)
    return record


def real_group(data, begin, end):
    selected, unknown, boundary, outside = [], 0, [], 0
    for trade in data.get('closed', []):
        close = timestamp(trade.get('closed_at'))
        hold = number(trade.get('hold_h'))
        opened = timestamp(trade.get('opened'))
        estimated = opened is None
        if estimated and close is not None and hold is not None:
            opened = close - hold * 3600
        pnl, invested = number(trade.get('pnl_sol')), number(trade.get('invested_sol'), True)
        if opened is None or close is None or pnl is None or invested is None:
            unknown += 1
            continue
        if estimated and (abs(opened-begin) <= 18 or abs(opened-end) <= 18):
            boundary.append(trade.get('symbol'))
        if not begin <= opened <= end or close > end:
            outside += 1
            continue
        selected.append({'mint': trade['mint'], 'symbol': trade.get('symbol', '?'), 'pnl_sol': pnl,
                         'invested_sol': invested, 'opened': utc(opened), 'closed_at': utc(close), 'kaufzeit_geschaetzt': estimated})
    opened_positions = []
    for mint, pos in data.get('positions', {}).items():
        opened = timestamp(pos.get('opened'))
        opened_positions.append({'mint': mint, 'symbol': pos.get('symbol', '?'), 'opened': utc(opened),
                                 'im_zeitraum': opened is not None and begin <= opened <= end,
                                 'invested_sol': pos.get('invested_sol')})
    return {'statistik': summaries(selected), 'trades': selected, 'offene_positionen': opened_positions,
            'offen_n': len(opened_positions), 'offen_im_zeitraum_n': sum(p['im_zeitraum'] for p in opened_positions),
            'nicht_zuordenbar_n': unknown, 'ausserhalb_zeitraum_n': outside,
            'kaufzeit_aus_gerundeter_haltedauer_n': sum(t['kaufzeit_geschaetzt'] for t in selected),
            'unsichere_grenzfaelle': boundary, 'saved_at': data.get('saved_at')}


def dashboard_check(cases, task_horizons):
    original = rechnung._rueckblick_csv
    # Die zweite Quelle ist fuer diesen Vergleich irrelevant und nicht freigegeben.
    def approved_csv(path, *a, **kw):
        if path.name == 'abgelehnt.csv' or path.parent.name == 'abgelehnt':
            return iter(())
        return original(path, *a, **kw)
    rechnung._rueckblick_csv = approved_csv
    try:
        result = rechnung.abgelehnt_rueckblick(repo=ROOT, grund=GRUND, stunden=(1, 6))
    finally:
        rechnung._rueckblick_csv = original
    source = result['quellen']['knapp_abgelehnt']
    group = next((g for g in source['gruende'] if g['grund'] == GRUND), {'coins': 0, 'horizonte': {}})
    comparisons = []
    for h, task in task_horizons.items():
        page = group['horizonte'][int(h)]
        pairs = [('coins',len(cases),group['coins']), ('n',task['n'],page['n']),
                 ('nicht_messbar',task['nicht_messbar'],page['fehlend']), ('median_pct',task['median_pct'],page['median_pct']),
                 ('im_plus',task['im_plus'],page['hoeher']), ('im_plus_pct',task['im_plus_pct'],page['hoeher_pct'])]
        for key, ours, theirs in pairs:
            equal = ours == theirs or (isinstance(ours,(float,int)) and isinstance(theirs,(float,int)) and math.isclose(ours,theirs,abs_tol=1e-9))
            comparisons.append({'stunden': int(h), 'kennzahl': key, 'auftrag': ours, 'dashboard': theirs,
                                'gleich': equal, 'n':task['n'] if key not in ('coins','nicht_messbar') else len(cases)})
    return {'knapp_abgelehnt': source, 'hinweise': result['hinweise'], 'vergleich': comparisons,
            'fehlende_kennzahl_auf_seite': 'Anteil mindestens 2x',
            'code_ursachen': ['Kein Datumsfilter in abgelehnt_rueckblick; die Auftragskarte beginnt am 02.10.',
                             'Erste Ablehnung je Quelle/Mint/Grund, passende Phase und +/-300 s wie im Auftrag.',
                             'Die oberste Coin-Karte zaehlt alle Gruende; die FOMO-Gruppe ist darunter separat.',
                             'Derzeit stammen alle FOMO-Erstablehnungen aus dem Auftragszeitraum.'],
            'zweite_quelle': 'abgelehnt.csv nicht gelesen; nur ihr unabhaengiger Zweig leer gelassen'}


def fmt(value, digits=4):
    return 'nicht messbar' if value is None else f'{value:.{digits}f}'.replace('.', ',')


def make_report(result):
    meta = result['metadaten']
    lines = ['# Tag 17: FOMO-Sprung', '', f"Zeitraum: {meta['beginn_utc']} bis {meta['ende_utc']} (UTC).",
             f"Erste Ablehnung je Mint: **{meta['coins_n']} Coins (n={meta['coins_n']})**. Keine Zwischenkurse geschätzt.", '',
             '## Kurs nach der Ablehnung', '', '| Zeitpunkt | Messbar | Median | Im Plus | Mindestens 2x | Nicht messbar |',
             '|---|---|---|---|---|---|']
    for h,s in result['aufgabe_1'].items():
        n=s['n']; total=s['coins']
        lines.append(f"| {h} h | {n}/{total} Coins | {fmt(s['median_vielfaches'])}x / {fmt(s['median_pct'],1)} % (n={n}) | {s['im_plus']}/{n}: {fmt(s['im_plus_pct'],1)} % | {s['mindestens_2x']}/{n}: {fmt(s['mindestens_2x_pct'],1)} % | {s['nicht_messbar']}/{total} |")
    lines += ['', 'Anteile beziehen sich auf messbare Coins. Nächster Messpunkt höchstens ±5 Minuten; bei gleichem Abstand der frühere. Fehlende Kurse können das Bild verzerren.', '',
              '## Kauf mit der Hauptstrategie nachgerechnet', '', 'Einsatz je Coin: 0,2 SOL (je n=1 Trade). Kaufkurs = erste Ablehnung. Jede spätere gültige Zeile wird durch den Bot im Hauptordner geführt, ohne Gebühren. Kosten: zusätzlich 2 % des Einsatzes = 0,004 SOL je Trade (je n=1).', '']
    sim=result['aufgabe_2']
    lines.append(f"Simulation: n={sim['messbar_n']} von {meta['coins_n']}; geschlossen n={sim['geschlossen_n']}, offen zum letzten Kurs n={sim['offen_n']}, nicht simulierbar n={sim['nicht_simulierbar_n']}.")
    lines.append(f"Zu kurz: {sim['zu_kurz_n']}/{meta['coins_n']} Verläufe (davon weniger als zwei gültige Zeilen: {sim['zu_wenige_zeilen_n']}/{meta['coins_n']}). Lücken über 15 Minuten: {sim['lueckenhaft_n']}/{meta['coins_n']}; davon vor Ausstieg/Ende: {sim['luecken_bis_ende_n']}/{meta['coins_n']}.")
    missing=[t['symbol'] for t in sim['trades'] if not t['messbar']]
    lines.append(f"Ohne eine einzige spätere Kurszeile: {', '.join(missing)} (n={len(missing)}). Ihr Ergebnis bleibt unbekannt und geht nicht als null ein.")
    def table(label, data, median=True):
        lines.extend(['',label,'', '| Auswahl | n | Summe SOL | Ø SOL | Median SOL | Gewinner |', '|---|---:|---:|---:|---:|---|'])
        for name, obj in [('Alle roh',data['roh']),('Alle mit Kosten',data['kosten_2pct']),('Ohne beste 3 roh',data['ohne_beste_3']['roh']),('Ohne beste 3 mit Kosten',data['ohne_beste_3']['kosten_2pct'])]:
            n=obj['n']
            lines.append(f"| {name} | {n} | {fmt(obj['summe_sol'])} | {fmt(obj['durchschnitt_sol'])} | {fmt(obj['median_sol'])} | {obj['gewinner']}/{n}: {fmt(obj['gewinner_pct'],1)} % |")
        lines.append('Alle Zahlen einer Zeile beziehen sich auf das dort genannte n. Gewinner: Ergebnis > 0. Die drei besten werden nach rohem SOL-Ergebnis entfernt.')
    table('Alle simulierbaren Verläufe, einschließlich letzter Bewertung offener Positionen:',sim['alle'])
    table('Ohne zu kurze, lückenhafte und wegen ungültiger Zeilen unvollständige Fälle:',sim['ohne_unsichere'])
    lines.append('Hier werden auch Verläufe ausgeschlossen, deren Lücke erst nach dem simulierten Verkauf liegt. Die mildere Auswahl, die nur Lücken vor dem Verkauf ausschließt, steht zusätzlich im JSON.')
    lines += ['', '| Verkaufsgrund / Ende | Anzahl |', '|---|---:|']
    for reason,n in sim['gruende'].items():
        lines.append(f"| {reason} | {n} (Grundgesamtheit n={sim['messbar_n']}) |")
    lines += ['', f"Teilverkauf bei 2x: {sim['teilverkauf_n']}/{sim['messbar_n']} Trades. Endgültige Verkaufsgründe stehen oben; offene Bewertungen sind kein Verkauf.", '',
              '## Echte Trades im selben Zeitraum', '', 'Nur geschlossene Trades mit Kauf im oben genannten Zeitraum. Das gespeicherte SOL-Ergebnis enthält die Bot-Gebühren; davon werden für die Kostenspalte weitere 2 % des tatsächlichen Einsatzes abgezogen. Offene Positionen sind getrennt und zählen nicht in diesen Tabellen.']
    for key,label in [('hauptstrategie','Hauptstrategie'),('kontrollgruppe','Kontrollgruppe')]:
        group=result['aufgabe_3'][key]
        table(label,group['statistik'])
        lines.append(f"Offen: n={group['offen_n']}, davon Kauf im Zeitraum n={group['offen_im_zeitraum_n']}. Kaufzeit aus Verkaufszeit minus gerundeter Haltedauer: n={group['kaufzeit_aus_gerundeter_haltedauer_n']}; Grenzfälle am Zeitraumrand n={len(group['unsichere_grenzfaelle'])}. Nicht zuordenbar n={group['nicht_zuordenbar_n']}.")
        lines.append(f"Portfolio-Stand: {utc(timestamp(group['saved_at']))} UTC.")
    lines += ['', 'Zur Formulierung „Käufe ab 02.10.“: Die Tabellen beginnen am ersten FOMO-Fall um 09:11:25 UTC. Zusätzlich ab 00:00 UTC am 02.10.:', '',
              '| Gruppe | n | Summe roh SOL | Mit Kosten SOL |', '|---|---:|---:|---:|']
    for key,label in [('hauptstrategie','Hauptstrategie'),('kontrollgruppe','Kontrollgruppe')]:
        s=result['aufgabe_3_ab_02_10_0000'][key]['statistik']
        lines.append(f"| {label} | {s['roh']['n']} | {fmt(s['roh']['summe_sol'])} | {fmt(s['kosten_2pct']['summe_sol'])} |")
    lines.append('Alle Zahlen je Zeile beziehen sich auf das genannte n; vollständige Zusatzwerte stehen im JSON.')
    lines += ['', '## Abgleich mit „Verpasste Chancen“', '', '| Zeit | Kennzahl | Auftrag | Dashboard | Gleich? | n |', '|---|---|---:|---:|---|---:|']
    for row in result['aufgabe_4']['vergleich']:
        digits=1 if row['kennzahl'].endswith('pct') else 0
        lines.append(f"| {row['stunden']} h | {row['kennzahl']} | {fmt(row['auftrag'],digits)} | {fmt(row['dashboard'],digits)} | {'ja' if row['gleich'] else 'nein'} | {row['n']} |")
    lines += ['', 'Der Anteil mindestens 2x fehlt auf der Seite. Die Rechnung hat keinen Datumsfilter; derzeit liegen aber alle FOMO-Erstablehnungen im Auftragszeitraum. Die oberste Coin-Karte der Seite zählt alle Gründe. Für diesen Vergleich zählt die darunterliegende FOMO-Gruppe. Phase, erste Ablehnung und Zeitfenster stimmen überein. Seite und Rechnung wurden nicht geändert.', '',
              '## Grenzen und Gegenprüfung', '', 'Die geschätzten Kaufzeiten echter geschlossener Trades sind wegen auf zwei Dezimalen gerundeter Haltedauer bis etwa ±18 Sekunden ungenau. Kein Kauf am Zeitraumrand liegt in diesem Unsicherheitsfenster, sofern die Grenzfallzahl oben null ist.', '',
              'Lücken zählen auch zwischen Ablehnung und erstem Messpunkt. Bei der Simulation wird die Liquidität der Ablehnung als Einstiegsbasis genutzt. Kursverhältnisse kommen aus USD-Kurs / erstem Ablehnungskurs; gespeicherte Vielfache können sich bei wiederholter Ablehnung auf einen anderen Start beziehen. Laufzähler und Thesenprüfung folgen der Regressionsvorlage: eine Kurszeile = ein Bot-Durchlauf. Das bildet die grobe Aufzeichnung ab, nicht alle etwa 12 Sekunden eines echten Bots. Graduation und sonstige nicht aufgezeichnete Merkmale werden wie in der Vorlage nicht ergänzt.', '',
              'Offene Fälle werden nur mit dem letzten beobachteten Kurs bewertet. Auch ausgeschlossene Fälle stehen einzeln im JSON. Kaputte CSV-Zeilen werden gezählt und übersprungen; widersprüchliche Kurse zur selben Zeit bleiben unmessbar. Keine Interpolation, keine Netzabfragen, keine Aussage zu einer Strategieänderung.', '',
              f"CSV-Zeilen: n={meta['csv_zeilen_n']}; kaputte Zeilen: n={meta['kaputte_csv_zeilen_n']}. Nicht zuordenbare FOMO-Ablehnungen: n={meta['unzuordenbare_fomo_n']}. Widersprüchliche Verlaufspunkte: n={meta['kurskonflikte_n']}.", '',
              'Unabhängige Gegenprüfung: Ein separater Datenprüfer bestätigt die Kursstatistik und die echten Trade-Ergebnisse. Zusätzlich liest das Skript drei Coins mit einem zweiten CSV-Leseweg und rechnet mit Dezimalzahlen direkt Folgekurs / Ablehnungskurs:', '',
              '| Coin (je n=1) | Nach 1 h | Nach 6 h |', '|---|---:|---:|']
    for symbol in dict.fromkeys(c['symbol'] for c in result['gegenpruefung']['pruefungen']):
        checks={c['stunden']:c['vielfaches'] for c in result['gegenpruefung']['pruefungen'] if c['symbol']==symbol}
        lines.append(f"| {symbol} | {fmt(checks.get(1),6)}x | {fmt(checks.get(6),6)}x |")
    lines += ['', 'Jeder Quotient betrifft einen Coin (n=1). Kurse, Zeitpunkte, volle Mint-Adressen und Prüfergebnisse stehen im JSON.', '']
    return '\n'.join(lines)


def main():
    cases, unassigned, rejection_count, pre_start = {}, 0, 0, 0
    for row in rows(ROOT/'knapp_abgelehnt.csv'):
        if row.get('grund','').strip() != GRUND:
            continue
        rejection_count += 1
        t=timestamp(row.get('zeit')); mint=row.get('mint','').strip()
        if t is None or not mint:
            unassigned+=1; continue
        if t < START_DAY:
            pre_start+=1; continue
        case={'mint':mint,'symbol':row.get('symbol','?'),'zeit':t,'preis_usd':number(row.get('preis_usd'),True),
              'liquiditaet':number(row.get('liquidity')), 'startkonflikt':False}
        old=cases.get(mint)
        if old is None or t < old['zeit']:
            cases[mint]=case
        elif t == old['zeit'] and old['preis_usd'] != case['preis_usd']:
            old.update(preis_usd=None,startkonflikt=True)
    if not cases:
        raise RuntimeError('Keine zeitlich zuordenbaren FOMO-Erstablehnungen ab 02.10.')
    begin=min(c['zeit'] for c in cases.values())
    paths=defaultdict(list); max_path_time=begin; invalid_time=0
    for path in sorted((ROOT/'verlauf').glob('*.csv')):
        if path.stem < '2026-10-02':
            continue
        for row in rows(path):
            if row.get('phase') != 'abgelehnt_'+GRUND or row.get('mint') not in cases:
                continue
            t=timestamp(row.get('zeit'))
            if t is None:
                invalid_time+=1; continue
            if t < cases[row['mint']]['zeit']:
                continue
            max_path_time=max(max_path_time,t)
            paths[row['mint']].append({'zeit':t,'preis_usd':number(row.get('preis_usd'),True),
                                      **{k:number(row.get(k)) for k in ('liquiditaet','holder_1h_pct','netto_kaeufer_5m')}})
    price_conflicts=duplicate=feature_conflicts=0
    for mint,points in paths.items():
        grouped=defaultdict(list)
        for p in points: grouped[p['zeit']].append(p)
        unique=[]
        for t,group in sorted(grouped.items()):
            p=dict(group[0]); duplicate+=len(group)-1
            for key in ('preis_usd','liquiditaet','holder_1h_pct','netto_kaeufer_5m'):
                if len({r[key] for r in group}) > 1:
                    p[key]=None
                    if key=='preis_usd': price_conflicts+=1
                    else: feature_conflicts+=1
            unique.append(p)
        paths[mint]=unique
    main_port=load_json(ROOT/'portfolio.json')
    control_port=load_json(ROOT/'experimente/kontrollgruppe/portfolio.json')
    saved_times=[timestamp(p.get('saved_at')) for p in (main_port,control_port)]
    end=max([max_path_time]+[c['zeit'] for c in cases.values()]+[t for t in saved_times if t is not None])
    task1=horizons(cases,paths)
    setup_simulation()
    simulations=[simulate(mint,case,paths.get(mint,[])) for mint,case in sorted(cases.items())]
    usable=[r for r in simulations if r['messbar']]
    clean=[r for r in usable if not r['zu_kurz'] and not r['lueckenhaft'] and not r['ungueltige_zeilen']]
    clean_exit=[r for r in usable if not r['zu_kurz'] and not r['luecken_bis_ende'] and not r['ungueltige_zeilen']]
    task2={'alle':summaries(usable),'ohne_unsichere':summaries(clean),
           'ohne_unsichere_nur_luecken_bis_ende':summaries(clean_exit),'messbar_n':len(usable),
           'geschlossen_n':sum(not r['offen'] for r in usable),'offen_n':sum(r['offen'] for r in usable),
           'nicht_simulierbar_n':len(simulations)-len(usable),'zu_kurz_n':sum(r.get('zu_kurz',True) for r in simulations),
           'zu_wenige_zeilen_n':sum(r['zu_wenige_zeilen'] for r in simulations),
           'lueckenhaft_n':sum(r['lueckenhaft'] for r in usable),
           'luecken_bis_ende_n':sum(r['luecken_bis_ende'] for r in usable),
           'gesamter_verlauf_lueckenhaft_n':sum(bool(r['gesamter_verlauf_luecken_s']) for r in usable),
           'teilverkauf_n':sum(r['teilverkauf'] for r in usable), 'gruende':dict(Counter(r['grund'] for r in usable)),
           'trades':simulations}
    # Ein zweiter Leseweg benutzt DictReader und eine direkte Suche je Stichprobe.
    checks=[]
    sample_mints=['21fX473LMyHnCYb4kvAUG4z4bGYpqTbp9vyakDPgs9Hm', '26Y3RwnUPghZ7hyRVktaTY6NjxgGSruRVPSZtgRbpump', '29aF6EWpTTMs5H1AVz84b6GKXC6oR39nLYvvPW72pump']
    if not all(m in cases for m in sample_mints):
        sample_mints=list(sorted(cases, key=lambda m:cases[m]['zeit']))[:3]
    independent_starts={}
    with (ROOT/'knapp_abgelehnt.csv').open(encoding='utf-8-sig',newline='') as f:
        for row in csv.DictReader(f):
            mint=row.get('mint'); t=timestamp(row.get('zeit'))
            if None not in row and mint in sample_mints and row.get('grund')==GRUND and t is not None and t>=START_DAY:
                if mint not in independent_starts or t<independent_starts[mint][0]:
                    independent_starts[mint]=(t,row['preis_usd'])
    for mint in sample_mints:
        start_t,start_price=independent_starts[mint]
        observed=[]
        for path in sorted((ROOT/'verlauf').glob('2026-10-*.csv')):
            with path.open(encoding='utf-8-sig',newline='') as f:
                for row in csv.DictReader(f):
                    if None not in row and row.get('mint')==mint and row.get('phase')=='abgelehnt_'+GRUND:
                        t=timestamp(row.get('zeit'))
                        if t is not None and t>=start_t: observed.append((t,number(row.get('preis_usd'),True),row.get('preis_usd')))
        for h in (1,6):
            target=start_t+h*3600
            p=min(observed,key=lambda p:(abs(p[0]-target),p[0])) if observed else None
            ratio=float(Decimal(p[2])/Decimal(start_price)) if p and abs(p[0]-target)<=300 and p[1] is not None and number(start_price,True) else None
            expected=cases[mint]['horizonte'][str(h)].get('vielfaches')
            equal=ratio==expected or ratio is not None and expected is not None and math.isclose(ratio,expected,abs_tol=1e-12)
            assert equal, 'Unabhaengige Kurs-Gegenprobe fehlgeschlagen'
            checks.append({'mint':mint,'symbol':cases[mint]['symbol'],'n':1,'stunden':h,'kaufkurs':float(start_price),'kaufzeit':utc(start_t),
                           'folgekurs':p[1] if p and ratio is not None else None,'zeit':utc(p[0]) if p and ratio is not None else None,
                           'vielfaches':ratio,'gleich':equal})
    result={'metadaten':{'beginn_utc':utc(begin),'ende_utc':utc(end),'erzeugt_utc':datetime.now(timezone.utc).isoformat(),
                        'coins_n':len(cases),'fomo_ablehnungen_n':rejection_count,'unzuordenbare_fomo_n':unassigned,
                        'fomo_vor_02_10_n':pre_start,'kaputte_csv_zeilen_n':sum(i.get('kaputte_zeilen',0) for i in AUDIT.values()),
                        'csv_zeilen_n':sum(i.get('zeilen',0) for i in AUDIT.values()),'kurskonflikte_n':price_conflicts,
                        'merkmalskonflikte_n':feature_conflicts,'doppelte_verlaufspunkte_n':duplicate,
                        'verlauf_ungueltige_zeit_n':invalid_time,'kosten_pct':2,'simulation_einsatz_sol':INVESTMENT,
                        'bot_import':str(Path(core.__file__).resolve()),'rechnung_import':str(Path(rechnung.__file__).resolve())},
            'aufgabe_1':task1,'aufgabe_2':task2,
            'aufgabe_3':{'hauptstrategie':real_group(main_port,begin,end),'kontrollgruppe':real_group(control_port,begin,end)},
            'aufgabe_3_ab_02_10_0000':{'hauptstrategie':real_group(main_port,START_DAY,end),'kontrollgruppe':real_group(control_port,START_DAY,end)},
            'aufgabe_4':dashboard_check(cases,task1),'faelle':list(cases.values()),
            'gegenpruefung':{'methode':'Separater DictReader-Leseweg fuer Ablehnungen und Verlaeufe, drei Coins, Decimal-Division USD-Folgekurs / Ablehnungskurs',
                            'stichprobe_coins_n':3,'horizont_pruefungen_n':len(checks),'pruefungen':checks}, 'quellen':AUDIT}
    result['unsicherheiten']=['Kaufzeiten echter geschlossener Trades aus closed_at minus gerundetem hold_h, bis etwa +/-18 s.',
                              'Offene Simulationen sind letzte Kursbewertungen, keine realisierten Ergebnisse.',
                              'Grobe Aufzeichnung: Laufzaehler wie Regressionsvorlage; nicht jeder reale Bot-Durchlauf bekannt.',
                              'Einstiegsliquiditaet aus Ablehnung, USD-Kurse relativ zum ersten Ablehnungskurs, keine Interpolation.',
                              'Graduation und nicht gespeicherte Merkmale wie in simulate nicht rekonstruierbar.',
                              'Portfolio-Datenstand pro Gruppe getrennt gespeichert; Zeitraumende ist das Maximum der zugelassenen Datenstaende.',
                              'Nicht messbare Faelle koennen die messbare Teilmenge verzerren.']
    (OUT/'tag17.json').write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    (OUT/'tag17_entwurf.md').write_text(make_report(result),encoding='utf-8')
    print(json.dumps({'zeitraum':result['metadaten'],'kurs':task1,'simulation':task2['alle'],
                      'simulation_sauber':task2['ohne_unsichere'],'qualitaet':{k:v for k,v in task2.items() if k.endswith('_n')},
                      'echte_trades':{k:v['statistik'] for k,v in result['aufgabe_3'].items()},
                      'dashboard_gleich':all(c['gleich'] for c in result['aufgabe_4']['vergleich'])},ensure_ascii=False,indent=2))


if __name__ == '__main__':
    main()
