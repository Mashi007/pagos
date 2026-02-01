$src = Join-Path $PSScriptRoot "src"
$folders = @(
  @{ Path = "pages"; Prefix = "../" },
  @{ Path = "hooks"; Prefix = "../" },
  @{ Path = "data"; Prefix = "../" },
  @{ Path = "utils"; Prefix = "../" }
)
foreach ($f in $folders) {
  $dir = Join-Path $src $f.Path
  if (-not (Test-Path $dir)) { continue }
  Get-ChildItem $dir -Recurse -Include *.ts,*.tsx | ForEach-Object {
    $c = [System.IO.File]::ReadAllText($_.FullName)
    $c = $c -replace "from '/", "from '$($f.Prefix)"
    $c = $c -replace 'from "/', 'from "' + $f.Prefix
    $c = $c -replace "import('/", "import('$($f.Prefix)"
    $c = $c -replace 'import("/', 'import("' + $f.Prefix
    [System.IO.File]::WriteAllText($_.FullName, $c)
  }
}
$comp = Join-Path $src "components"
$modals = Join-Path $comp "dashboard\modals"
# Primero components (excepto modals) con ../../
Get-ChildItem $comp -Recurse -Include *.ts,*.tsx | Where-Object { $_.FullName -notlike "*\modals\*" } | ForEach-Object {
  $c = [System.IO.File]::ReadAllText($_.FullName)
  if ($c -match "from '/" -or $c -match 'from "/' -or $c -match "import('/" -or $c -match 'import("/') {
    $c = $c -replace "from '/", "from '../../"
    $c = $c -replace 'from "/', 'from "../../'
    $c = $c -replace "import('/", "import('../../"
    $c = $c -replace 'import("/', 'import("../../'
    [System.IO.File]::WriteAllText($_.FullName, $c)
  }
}
# Luego modals con ../../../
if (Test-Path $modals) {
  Get-ChildItem $modals -Include *.ts,*.tsx | ForEach-Object {
    $c = [System.IO.File]::ReadAllText($_.FullName)
    $c = $c -replace "from '../../", "from '../../../"
    $c = $c -replace 'from "../../', 'from "../../../'
    $c = $c -replace "import('../../", "import('../../../"
    $c = $c -replace 'import("../../', 'import("../../../'
    [System.IO.File]::WriteAllText($_.FullName, $c)
  }
}
Write-Host "Done."
