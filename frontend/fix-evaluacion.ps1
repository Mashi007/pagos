$path = Join-Path $PSScriptRoot "src\components\prestamos\EvaluacionRiesgoForm.tsx"
$c = [System.IO.File]::ReadAllText($path, [System.Text.Encoding]::UTF8)
# Arrow Unicode U+2192 -> ASCII
$c = $c -replace '\u2192', '->'
# Arrow mojibake (3 chars) -> ASCII
$c = $c -replace '\u00E2\u2020\u2019', '->'
# Bullet mojibake
$c = $c -replace '\u00E2\u0080\u00A2', '-'
# Remove non-ASCII before " La edad se calcula"
$c = $c -replace '(\r?\n\s+)[^\x00-\x7F]+\s*(La edad se calcula)', '$1$2'
# Calificacion, contesto, etc.
$c = $c.Replace('CalificaciÃ³n', 'Calificacion')
$c = $c.Replace('contestÃ³', 'contesto')
$c = $c.Replace('PuntuaciÃ³n', 'Puntuacion')
$c = $c.Replace('mÃ­nimo', 'minimo')
$c = $c.Replace('dÃ©ficit', 'deficit')
$c = $c.Replace('SociodemogrÃ¡fico', 'Sociodemografico')
# Checkmark/warning emoji -> ASCII (regex: non-ASCII sequence at start of line)
$c = $c -replace '(\r?\n\s+)[^\x00-\x7F]+\s*(5%-14\.9% del ingreso)', "`$1[!] `$2"
$c = $c -replace '(\r?\n\s+)[^\x00-\x7F]+\s*(&lt;5% o deficit)', "`$1[X] `$2"
[System.IO.File]::WriteAllText($path, $c, [System.Text.UTF8Encoding]::new($false))
Write-Host "Done."
