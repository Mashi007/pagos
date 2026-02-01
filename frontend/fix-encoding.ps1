# Restaurar caracteres UTF-8 (mojibake -> español correcto) en frontend/src
$src = Join-Path $PSScriptRoot "src"
$files = Get-ChildItem $src -Recurse -Include *.ts,*.tsx
$replacements = @(
  @{ Old = 'Ã±'; New = 'ñ' },
  @{ Old = 'Ã³'; New = 'ó' },
  @{ Old = 'Ã­'; New = 'í' },
  @{ Old = 'Ã©'; New = 'é' },
  @{ Old = 'Ã¡'; New = 'á' },
  @{ Old = 'Ãº'; New = 'ú' },
  @{ Old = 'Ã“'; New = 'Ó' },
  @{ Old = 'Ã±'; New = 'ñ' },
  @{ Old = 'â„¹ï¸'; New = 'ℹ️' },
  @{ Old = 'â†''; New = '→' },
  @{ Old = 'âœ…'; New = '✅' }
)
foreach ($f in $files) {
  $content = [System.IO.File]::ReadAllText($f.FullName, [System.Text.Encoding]::UTF8)
  $changed = $false
  foreach ($r in $replacements) {
    if ($content.Contains($r.Old)) {
      $content = $content.Replace($r.Old, $r.New)
      $changed = $true
    }
  }
  if ($changed) {
    [System.IO.File]::WriteAllText($f.FullName, $content, [System.Text.UTF8Encoding]::new($false))
    Write-Host "Fixed: $($f.Name)"
  }
}
Write-Host "Done."
