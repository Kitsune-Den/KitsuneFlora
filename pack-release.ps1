<#
.SYNOPSIS
  Package a clean KitsuneFlora release zip from the local mod folder.

  Produces KitsuneFlora-v<version>.zip containing a single top-level
  KitsuneFlora/ folder, so it drops straight into a 7DTD Mods/ directory with
  no dev files and no double-nesting. Version is read from KitsuneFlora/ModInfo.xml
  unless -Version is passed.

  IMPORTANT: the asset bundle (Resources/Bundles/*.unity3d) is gitignored (it's a
  build artifact from the Unity project), so it is NOT in a fresh git checkout.
  This script refuses to package without it, because a zip missing the bundle is
  non-functional in-game. Build the bundle from the Unity project first.

.EXAMPLE
  .\pack-release.ps1                 # auto-detect version from ModInfo.xml
  .\pack-release.ps1 -Version 0.3.8
  .\pack-release.ps1 -Upload         # build, then attach to the matching GitHub release
#>
[CmdletBinding()]
param(
  [string]$Version,
  [switch]$Upload
)

$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
$mod  = Join-Path $root 'KitsuneFlora'

if (-not (Test-Path (Join-Path $mod 'ModInfo.xml'))) {
  throw "Mod folder not found: $mod (expected KitsuneFlora/ModInfo.xml)"
}

# Resolve version from ModInfo.xml unless provided.
if (-not $Version) {
  $mi = Get-Content (Join-Path $mod 'ModInfo.xml') -Raw
  $m = [regex]::Match($mi, '<Version\s+value="([^"]+)"')
  if (-not $m.Success) { throw "Could not read <Version> from ModInfo.xml" }
  $Version = $m.Groups[1].Value
}
Write-Host "Version: $Version"

# Guard: the asset bundle must be present (gitignored build artifact). A release
# without it is the exact bug that shipped a broken v0.3.8 source zip.
$bundles = Get-ChildItem (Join-Path $mod 'Resources\Bundles') -Filter *.unity3d -ErrorAction SilentlyContinue
if (-not $bundles) {
  throw "No .unity3d bundle in KitsuneFlora\Resources\Bundles\. Build it from the Unity project first - a zip without it will not work in-game."
}

$zip = Join-Path $root ("KitsuneFlora-v{0}.zip" -f $Version)
if (Test-Path $zip) { Remove-Item $zip -Force }

Write-Host "Packing $mod ..."
Compress-Archive -Path $mod -DestinationPath $zip -CompressionLevel Optimal

# Verify: single top-level folder 'KitsuneFlora', and the bundle made it in.
Add-Type -AssemblyName System.IO.Compression.FileSystem
$z = [System.IO.Compression.ZipFile]::OpenRead($zip)
try {
  $tops = @{}
  $hasBundle = $false
  foreach ($e in $z.Entries) {
    $top = ($e.FullName -split '[\\/]')[0]
    if ($top) { $tops[$top] = $true }
    if ($e.FullName -match '\.unity3d$') { $hasBundle = $true }
  }
  $topList = ($tops.Keys | Sort-Object) -join ', '
  if ($topList -ne 'KitsuneFlora') { throw "Unexpected top-level entries: [$topList] (expected only 'KitsuneFlora')" }
  if (-not $hasBundle)             { throw "Zip is missing the .unity3d bundle." }
  $mb = [math]::Round((Get-Item $zip).Length/1MB,1)
  Write-Host ("OK  {0}  ({1} MB, {2} entries, top-level: {3})" -f (Split-Path $zip -Leaf), $mb, $z.Entries.Count, $topList)
} finally {
  $z.Dispose()
}

if ($Upload) {
  Write-Host "Uploading to GitHub release v$Version ..."
  gh release upload "v$Version" $zip --repo Kitsune-Den/KitsuneFlora --clobber
  if ($LASTEXITCODE -eq 0) { Write-Host "Attached KitsuneFlora-v$Version.zip to release v$Version." }
  else { Write-Host "Upload failed - is release v$Version created on GitHub?" }
}
