param(
    [string]$PythonExe = (Join-Path $PSScriptRoot '..\.venv\Scripts\python.exe'),
    [string]$IsccPath = (Join-Path $PSScriptRoot '..\tools\InnoSetup7\ISCC.exe'),
    [switch]$InstallBuildDependencies,
    [switch]$SkipTests
)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$buildArgs = @((Join-Path $PSScriptRoot 'build_release.py'), '--iscc', $IsccPath)
if ($InstallBuildDependencies) { $buildArgs += '--install-build-dependencies' }
if ($SkipTests) { $buildArgs += '--skip-tests' }
& $PythonExe @buildArgs
if ($LASTEXITCODE -ne 0) { throw "RetroMind build failed with exit code $LASTEXITCODE" }
