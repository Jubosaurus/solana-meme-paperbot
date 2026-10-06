# Codex-Nachtlauf: arbeitet Auftragskarten nacheinander im Worktree ab.
# VORBEREITET, NICHT AKTIV. Ohne -Los wird nur angezeigt, was passieren wuerde.
# Codex committet und pusht nie; jede Karte startet auf sauberem origin/main,
# ihr Ergebnis wird als Patch + Protokoll gesichert, Claude spielt spaeter ein.
#
# Aufruf (Probe):  powershell -File .claude\codex-nachtlauf.ps1
# Aufruf (echt):   powershell -File .claude\codex-nachtlauf.ps1 -Los
param(
    [switch]$Los,
    [int]$MaxKarten = 5,
    [int]$MaxMinutenProKarte = 45
)
$ErrorActionPreference = "Stop"

$haupt     = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$wt        = Join-Path (Split-Path -Parent $haupt) "paperbot-codex"
$karten    = Join-Path $haupt ".claude\codex-karten"
$stempel   = (Get-Date).ToUniversalTime().ToString("yyyy-MM-dd_HHmm")
$protokoll = Join-Path $haupt ".claude\codex-protokolle\$stempel"

# Pfade, die eine Karte nie aendern darf (Patch wird dann als ABGELEHNT markiert)
$verboten = '^(portfolio\.json|journal\.csv|messung\.csv|dexscreener\.csv|abgelehnt\.csv|knapp_abgelehnt\.csv|marktphase\.json|flugschreiber/|verlauf/|experimente/|copy/|scout/|copy_wallets\.txt|\.github/|\.claude/settings|\.claude/hooks/)'
$profile   = @{ "astra" = "astra"; "sol" = "sol"; "terra" = "terra"; "luna" = "luna" }

function Schreib($text) { Write-Host $text; if ($Los) { Add-Content -Path "$protokoll\nachtlauf.log" -Value $text -Encoding utf8 } }

# --- Vorpruefungen ---
if (-not (Test-Path $karten)) { Write-Host "Keine Karten in $karten"; exit 0 }
$liste = Get-ChildItem $karten -Filter "*.md" | Sort-Object Name | Select-Object -First $MaxKarten
if ($liste.Count -eq 0) { Write-Host "Keine Karten."; exit 0 }
if (-not (Test-Path $wt)) {
    Write-Host "Worktree fehlt. Anlegen mit: git -C `"$haupt`" worktree add --detach `"$wt`" origin/main"
    exit 1
}
if ($Los) { New-Item -ItemType Directory -Force $protokoll | Out-Null }
Schreib "Nachtlauf $stempel UTC, $($liste.Count) Karte(n), Worktree $wt, Probe=$(-not $Los)"

foreach ($k in $liste) {
    $text   = Get-Content $k.FullName -Raw -Encoding utf8
    $modell = "sol"
    if ($text -match '\*\*Modell:\*\*\s*(\w+)') { $m = $Matches[1].ToLower(); if ($profile.ContainsKey($m)) { $modell = $m } }
    if ($modell -eq "astra") { Schreib "[$($k.BaseName)] Astra nachts nicht erlaubt -> uebersprungen"; continue }
    Schreib "[$($k.BaseName)] Modell $modell"
    if (-not $Los) { continue }

    # Sauberer Stand: neuester origin/main, nichts Altes im Worktree
    git -C $wt fetch --quiet origin main
    git -C $wt checkout --quiet --detach origin/main
    git -C $wt reset --quiet --hard origin/main
    git -C $wt clean -fdq
    $basis = (git -C $wt rev-parse HEAD).Trim()

    $auftrag = "Du arbeitest im Paperbot-Projekt. Halte dich an AGENTS.md. Kein git commit, kein git push. " +
               "Antworte am Ende auf Deutsch mit: geaenderte Dateien, was getan, Testergebnis, offene Punkte.`n`n" + $text
    $auftragDatei = "$protokoll\$($k.BaseName).auftrag.md"
    Set-Content -Path $auftragDatei -Value $auftrag -Encoding utf8

    $args_ = @("exec", "-p", $modell, "-C", $wt, "--sandbox", "workspace-write", "--json",
               "-o", "$protokoll\$($k.BaseName).ergebnis.md", "-")
    $p = Start-Process -FilePath "codex" -ArgumentList $args_ -NoNewWindow -PassThru `
         -RedirectStandardInput $auftragDatei `
         -RedirectStandardOutput "$protokoll\$($k.BaseName).jsonl" `
         -RedirectStandardError  "$protokoll\$($k.BaseName).stderr.txt"
    if (-not $p.WaitForExit($MaxMinutenProKarte * 60 * 1000)) {
        $p.Kill(); Schreib "[$($k.BaseName)] ZEITLIMIT nach $MaxMinutenProKarte min"
    }

    # Ergebnis sichern: alle Aenderungen (auch neue Dateien) als Patch
    git -C $wt add -A
    git -C $wt diff --cached --binary "--output=$protokoll\$($k.BaseName).patch"
    $dateien = @(git -C $wt diff --cached --name-only)
    $neueCommits = (git -C $wt rev-parse HEAD).Trim() -ne $basis
    $schlecht = $dateien | Where-Object { $_ -match $verboten }
    $urteil = "OK"
    if ($neueCommits) { $urteil = "ABGELEHNT (Codex hat committet)" }
    elseif ($schlecht) { $urteil = "ABGELEHNT (verbotene Dateien: $($schlecht -join ', '))" }
    elseif ($dateien.Count -eq 0) { $urteil = "LEER (keine Aenderung)" }
    Schreib "[$($k.BaseName)] $urteil, Dateien: $($dateien -join ', ')"

    # Kontingent aufgebraucht? Dann ganze Nacht beenden, Rest bleibt liegen
    $log = (Get-Content "$protokoll\$($k.BaseName).jsonl", "$protokoll\$($k.BaseName).stderr.txt" -Raw -ErrorAction SilentlyContinue) -join ""
    if ($log -match 'usage limit|rate limit|quota|429') {
        Schreib "[$($k.BaseName)] Kontingent erschoepft -> Nachtlauf beendet"
        break
    }
    # erledigte Karte wegsortieren
    Move-Item $k.FullName "$protokoll\$($k.Name)"
}

if ($Los) {
    git -C $wt reset --quiet --hard
    git -C $wt clean -fdq
}
Schreib "Ende $((Get-Date).ToUniversalTime().ToString('HH:mm')) UTC. Protokolle: $protokoll"
