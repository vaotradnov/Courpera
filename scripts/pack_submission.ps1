Param(
  [string]$Out = "submission.zip"
)

$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location (Join-Path $Root '..')

$include = @(
  'accounts','activity','api','assignments','config','courses','discussions','materials','messaging','static','templates','ui',
  'manage.py','mypy.ini','pytest.ini','README.md','requirements.txt','runtime.txt','SECURITY.md','Procfile','.pre-commit-config.yaml','bandit.yaml'
)
$exclude = @('.venv','htmlcov','__pycache__','.pytest_cache','.mypy_cache','.ruff_cache','media')

$tmp = Join-Path $env:TEMP ("courpera_pack_" + [guid]::NewGuid().ToString())
New-Item -Force -ItemType Directory $tmp | Out-Null

foreach ($p in $include) {
  Copy-Item -Recurse -Force $p (Join-Path $tmp $p)
}
foreach ($p in $exclude) {
  if (Test-Path $p) { Remove-Item -Recurse -Force (Join-Path $tmp $p) -ErrorAction SilentlyContinue }
}

if (Test-Path $Out) { Remove-Item $Out }
Add-Type -AssemblyName 'System.IO.Compression.FileSystem'
[System.IO.Compression.ZipFile]::CreateFromDirectory($tmp, $Out)
Remove-Item -Recurse -Force $tmp
Write-Host "Wrote $Out"
