# Uploads the staged FreightDock (stage_workshop.ps1) to the Steam Workshop with SteamCMD.
# Usage: powershell -ExecutionPolicy Bypass -File Tools/FreightDock/upload_workshop.ps1 -Account <steam login> -ChangeNote "<text>"
#
# The first upload creates a private item and saves its ID to workshop_id.txt beside this script; later uploads
# update that item. Visibility is only sent on the first upload and the description never is, so changes made on
# the Workshop page are kept. SteamCMD asks for the password / Steam Guard code unless the login is cached.

param(
    [Parameter(Mandatory)] [string] $Account,
    [Parameter(Mandatory)] [string] $ChangeNote,
    [string] $SteamCmd = 'C:\Program Files\steamcmd\steamcmd.exe'
)

$ErrorActionPreference = 'Stop'
$AppId = '2489330'
$Title = 'Freight Dock'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$work = Join-Path $repo 'Saved\Workshop\FreightDock'
$content = Join-Path $work 'content'
$preview = Join-Path $repo 'Assets\Thumbnail.jpg'
$vdf = Join-Path $work 'FreightDock.vdf'
$idFile = Join-Path $PSScriptRoot 'workshop_id.txt'

if (-not (Test-Path $SteamCmd)) { throw "SteamCMD not found at $SteamCmd (pass -SteamCmd)." }
if (-not (Test-Path (Join-Path $content 'FreightDock.pak'))) { throw "Nothing staged in $content - run stage_workshop.ps1 first." }
if (-not (Test-Path $preview)) { throw "Missing preview image $preview." }
if ((Get-Item $preview).Length -ge 1MB) { throw "$preview is over Steam's 1 MB preview limit." }

$id = if (Test-Path $idFile) { (Get-Content $idFile -Raw).Trim() } else { '0' }
$first = $id -eq '0'

# VDF strings: backslashes and quotes escaped
$q = { param($s) '"' + ($s -replace '\\', '\\' -replace '"', '\"') + '"' }
$lines = @(
    '"workshopitem"', '{'
    "`t`"appid`" $(& $q $AppId)"
    "`t`"publishedfileid`" $(& $q $id)"
    "`t`"contentfolder`" $(& $q $content)"
    "`t`"previewfile`" $(& $q $preview)"
    "`t`"title`" $(& $q $Title)"
    "`t`"changenote`" $(& $q $ChangeNote)"
)
if ($first) { $lines += "`t`"visibility`" `"2`"" }   # private until set public on the Workshop page
$lines += '}'
[IO.File]::WriteAllLines($vdf, $lines)

Write-Host ($(if ($first) { 'Creating a new Workshop item' } else { "Updating Workshop item $id" }))
& $SteamCmd +login $Account +workshop_build_item $vdf +quit
if ($LASTEXITCODE -ne 0) { throw "SteamCMD exited with code $LASTEXITCODE." }

# SteamCMD writes the item's ID back into the .vdf
$m = Select-String -Path $vdf -Pattern '"publishedfileid"\s+"(\d+)"'
$newId = if ($m) { $m.Matches[0].Groups[1].Value } else { '0' }
if ($newId -eq '0') { throw "No Workshop item ID in $vdf after the upload; check the SteamCMD output above." }
if ($first) {
    Set-Content -Path $idFile -Value $newId -Encoding ascii
    Write-Host "Created item $newId (saved to $idFile)."
}
Write-Host "https://steamcommunity.com/sharedfiles/filedetails/?id=$newId"
