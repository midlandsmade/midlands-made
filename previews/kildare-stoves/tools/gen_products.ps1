# Reads products.json, generates one Soul Cinematic vibe image per product (by style),
# downloads to assets/products-raw, then watermarks all into assets/products.
$root = "D:\Midlands_Web\previews\kildare-stoves"
$raw  = "$root\assets\products-raw"
$out  = "$root\assets\products"
New-Item -ItemType Directory -Force $raw | Out-Null
New-Item -ItemType Directory -Force $out | Out-Null

$common = ", real interior photograph, DSLR, natural realistic lighting, warm firelight, true-to-life, high detail, sharp focus, not a render, no text, no logo"
$tpl = @{
  freestanding = "A black cast-iron freestanding wood-burning stove with a lit fire behind the glass door, on a slate hearth against a natural stone chimney breast in a cosy Irish home"
  insert       = "A glass-fronted inset wood-burning stove built into a natural stone chimney breast, lit fire behind the glass, in a cosy Irish living room"
  cassette     = "A modern wide glass-fronted inset cassette stove set flush into a stone chimney breast, wide lit fire behind the glass, in a cosy Irish living room"
  pellet       = "A modern sleek matte-black freestanding pellet stove with a glowing flame window, on a slate hearth against a stone wall in a modern Irish home"
  electric     = "A freestanding electric fireplace stove with a realistic glowing flame effect behind a glass door, matte black body with short legs, on a slate hearth against a stone wall in a cosy Irish living room"
  boiler       = "A large black cast-iron boiler stove with a lit fire behind the glass door, on a stone hearth in an Irish farmhouse living room"
  surround     = "An elegant marble fireplace surround with a lit fire in the hearth, in a tasteful Irish living room"
}

$data = Get-Content "$root\data\products.json" -Raw | ConvertFrom-Json
$n = 0; $tot = $data.products.Count
foreach ($p in $data.products) {
  $n++
  $dest = "$raw\$($p.id).png"
  if (Test-Path $dest) { Write-Output "[$n/$tot] skip $($p.id)"; continue }
  $prompt = $tpl[$p.style] + $common
  try {
    $id = (higgsfield generate create soul_cinematic --prompt $prompt --json | ConvertFrom-Json)[0]
    higgsfield generate wait $id | Out-Null
    $url = (higgsfield generate get $id --json | ConvertFrom-Json).result_url
    Invoke-WebRequest -Uri $url -OutFile $dest
    Write-Output "[$n/$tot] ok $($p.id)"
  } catch {
    Write-Output "[$n/$tot] FAIL $($p.id): $_"
  }
}
Write-Output "GEN DONE - watermarking..."
python "$root\tools\watermark.py" $raw $out
Write-Output "ALL DONE"
