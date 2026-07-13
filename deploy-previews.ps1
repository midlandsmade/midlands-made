# Midlands Made — redeploy all previews to https://midlands-previews.netlify.app
# Usage:  $env:NETLIFY_AUTH_TOKEN="nfp_..."; powershell -File D:\Midlands_Web\deploy-previews.ps1
# Token is NEVER stored on disk — it's read from the environment each run.
# Rebuilds a clean staging copy (drops _helper files + screenshots), then deploys.

$ErrorActionPreference = "Stop"
if (-not $env:NETLIFY_AUTH_TOKEN) { Write-Error "Set NETLIFY_AUTH_TOKEN first (Netlify user settings > Applications > personal access token)"; exit 1 }

$SITE = "858fd271-00fc-42ea-bdc1-b264746bba2b"   # midlands-previews.netlify.app
$SRC  = "D:\Midlands_Web\previews"
$STAGE = Join-Path $env:TEMP ("mm_pv_" + (Get-Random))
New-Item -ItemType Directory -Path $STAGE -Force | Out-Null

# copy every preview file except helper/_ files (screenshots are named _preview*.png)
Get-ChildItem $SRC -Recurse -File |
  Where-Object { $_.Name -notlike "_*" } |
  ForEach-Object {
    $rel  = $_.FullName.Substring($SRC.Length).TrimStart('\')
    $dest = Join-Path $STAGE $rel
    New-Item -ItemType Directory -Path (Split-Path $dest) -Force | Out-Null
    Copy-Item $_.FullName $dest -Force
  }

Write-Output "Deploying $((Get-ChildItem $STAGE -Recurse -File).Count) files to midlands-previews.netlify.app ..."
netlify deploy --prod --no-build --dir="$STAGE" --site=$SITE
Remove-Item $STAGE -Recurse -Force
Write-Output "Done -> https://midlands-previews.netlify.app"
