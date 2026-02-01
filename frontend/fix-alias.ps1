$srcDir = Join-Path $PSScriptRoot "src"
$files = Get-ChildItem -Path $srcDir -Recurse -Include *.ts,*.tsx -File
foreach ($f in $files) {
  $content = Get-Content $f.FullName -Raw -ErrorAction SilentlyContinue
  if ($content -notmatch '@/') { continue }
  $dir = $f.DirectoryName
  $rel = [System.IO.Path]::GetRelativePath($dir, $srcDir)
  $prefix = $rel -replace '\\', '/'
  if ($prefix -eq '.') { $prefix = './' } else { $prefix = $prefix + '/' }
  $newContent = $content -replace '@/', $prefix
  [System.IO.File]::WriteAllText($f.FullName, $newContent)
  Write-Host "Fixed: $($f.FullName.Replace($srcDir, ''))"
}
Write-Host "Done."
