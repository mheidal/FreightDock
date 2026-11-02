# Stages FreightDock for a Steam Workshop upload: copies the installed .pak and .uplugin (written by the editor's
# Mod Tools > Cook & Install) into Saved/Workshop/FreightDock/content, replacing whatever was staged before.
# Usage: powershell -ExecutionPolicy Bypass -File Tools/FreightDock/stage_workshop.ps1

$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$installed = Join-Path $env:LOCALAPPDATA 'Whiskerwood\Saved\mods\FreightDock'
$content = Join-Path $repo 'Saved\Workshop\FreightDock\content'
$pak = Join-Path $installed 'FreightDock.pak'
$plugin = Join-Path $installed 'FreightDock.uplugin'

foreach ($f in $pak, $plugin) {
    if (-not (Test-Path $f)) { throw "Missing $f - run Cook & Install on Content/Mods/FreightDock first." }
}

# the game skips mods whose .uplugin doesn't name engine 5.8 or later
$info = Get-Content $plugin -Raw | ConvertFrom-Json
if (-not $info.EngineVersion -or [version]$info.EngineVersion -lt [version]'5.8') {
    throw "FreightDock.uplugin EngineVersion is '$($info.EngineVersion)'; the game needs 5.8 or later."
}

# a pak older than the newest mod asset was cooked before the last save
$newest = Get-ChildItem (Join-Path $repo 'Content\Mods\FreightDock') -Recurse -File |
    Sort-Object LastWriteTime -Descending | Select-Object -First 1
if ($newest.LastWriteTime -gt (Get-Item $pak).LastWriteTime) {
    Write-Warning "$($newest.Name) was saved after the pak was cooked - run Cook & Install again if that change should ship."
}

if (Test-Path $content) { Remove-Item $content -Recurse -Force -Confirm:$false }
New-Item -ItemType Directory -Force $content | Out-Null
Copy-Item $pak, $plugin $content

Write-Host "Staged FreightDock $($info.Version) in $content"
Get-ChildItem $content | Format-Table Name, Length, LastWriteTime -AutoSize
