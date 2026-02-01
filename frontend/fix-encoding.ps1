# Restaurar caracteres UTF-8 (mojibake -> espanol correcto) en frontend/src
# Usa solo codigos Unicode para evitar problemas de codificacion del script
$src = Join-Path $PSScriptRoot "src"
$files = Get-ChildItem $src -Recurse -Include *.ts,*.tsx
$ErrorActionPreference = 'Stop'
# Mojibake: UTF-8 bytes leidos como Latin-1 -> caracteres (U+00C3 = A, U+00A9 = c, etc.)
$replacements = @(
  @{ Old = [char]0x00C3 + [char]0x00B1; New = [char]0x00F1 },   # n
  @{ Old = [char]0x00C3 + [char]0x00B3; New = [char]0x00F3 },   # o
  @{ Old = [char]0x00C3 + [char]0x00AD; New = [char]0x00ED },   # i
  @{ Old = [char]0x00C3 + [char]0x00A9; New = [char]0x00E9 },   # e
  @{ Old = [char]0x00C3 + [char]0x00A1; New = [char]0x00E1 },   # a
  @{ Old = [char]0x00C3 + [char]0x00BA; New = [char]0x00FA },   # u
  @{ Old = [char]0x00C3 + [char]0x93; New = [char]0x00D3 },     # O
  @{ Old = [char]0x00C3 + [char]0x201C; New = [char]0x00D3 },  # O (comilla tipografica)
  @{ Old = [char]0x00C3 + [char]0x89; New = [char]0x00C9 },     # E
  @{ Old = [char]0x00C3 + [char]0x81; New = [char]0x00C1 },     # A
  @{ Old = [char]0x00C3 + [char]0x8D; New = [char]0x00CD },     # I
  @{ Old = [char]0x00C3 + [char]0x9A; New = [char]0x00DA },     # U
  @{ Old = [char]0x00C3 + [char]0x91; New = [char]0x00D1 },     # N
  @{ Old = [char]0x00C3 + [char]0x00BC; New = [char]0x00FC },   # u umlaut
  @{ Old = [char]0x00C2 + [char]0x00BF; New = [char]0x00BF },   # inverted ?
  # Simbolos (mojibake de 3 bytes)
  @{ Old = [char]0x00E2 + [char]0x86 + [char]0x92; New = [char]0x2192 },
  @{ Old = [char]0x00E2 + [char]0x9C + [char]0x85; New = [char]0x2705 },
  @{ Old = [char]0x00E2 + [char]0x9D + [char]0x8C; New = [char]0x274C },
  @{ Old = [char]0x00E2 + [char]0x0084 + [char]0x00B9 + [char]0x00EF + [char]0x00B8 + [char]0x008F; New = [char]0x2139 + [char]0xFE0F },
  @{ Old = [char]0x00E2 + [char]0x0080 + [char]0x009A + [char]0x00EF + [char]0x00B8 + [char]0x008F; New = [char]0x2139 + [char]0xFE0F },
  @{ Old = [char]0x201A + [char]0xFE0F; New = [char]0x2139 + [char]0xFE0F },
  @{ Old = [char]0x00E2 + [char]0x0161 + [char]0x00EF + [char]0x00B8; New = [char]0x2139 + [char]0xFE0F },
  @{ Old = [char]0x00E2 + [char]0x0161 + [char]0x0020 + [char]0x00EF + [char]0x00B8; New = [char]0x2139 + [char]0xFE0F },
  @{ Old = [char]0x00E2 + [char]0x0161 + [char]0x0020 + [char]0x00EF + [char]0x00B8 + [char]0x008F; New = [char]0x2139 + [char]0xFE0F },
  @{ Old = [char]0x00E2 + [char]0x009C + [char]0x201C; New = [char]0x2705 },
  @{ Old = [char]0x00E2 + [char]0x009C + [char]0x0022; New = [char]0x2705 },
  @{ Old = [char]0x2705 + [char]0x0022; New = [char]0x2705 },
  # Emojis 4 bytes (F0 9F xx xx leido como Latin-1)
  @{ Old = [char]0x00F0 + [char]0x009F + [char]0x0093 + [char]0x0084; New = [char]0xD83D + [char]0xDCC4 },
  @{ Old = [char]0x00F0 + [char]0x009F + [char]0x0093 + [char]0x0085; New = [char]0xD83D + [char]0xDCC5 },
  @{ Old = [char]0x00F0 + [char]0x009F + [char]0x0093 + [char]0x008A; New = [char]0xD83D + [char]0xDCCA },
  @{ Old = [char]0x00F0 + [char]0x009F + [char]0x0093 + [char]0x008B; New = [char]0xD83D + [char]0xDCCB },
  @{ Old = [char]0x00F0 + [char]0x009F + [char]0x0092 + [char]0xB0; New = [char]0xD83D + [char]0xDCB0 },
  @{ Old = [char]0x00F0 + [char]0x009F + [char]0x0092 + [char]0xB5; New = [char]0xD83D + [char]0xDCB5 }
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
    $utf8NoBom = New-Object System.Text.UTF8Encoding $false
    [System.IO.File]::WriteAllText($f.FullName, $content, $utf8NoBom)
    Write-Host "Fixed: $($f.Name)"
  }
}
Write-Host "Done."
