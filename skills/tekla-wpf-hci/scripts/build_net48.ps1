param(
    [string]$SolutionOrProject = "",
    [string]$Configuration = "Debug",
    [string]$Platform = "",
    [switch]$Restore
)

$ErrorActionPreference = "Stop"

$vswhere = "${env:ProgramFiles(x86)}\Microsoft Visual Studio\Installer\vswhere.exe"
if (-not (Test-Path -LiteralPath $vswhere)) {
    Write-Error "vswhere.exe not found. Install Visual Studio or MSBuild Build Tools for .NET Framework 4.8."
    exit 1
}

$msbuild = & $vswhere -latest -products * -requires Microsoft.Component.MSBuild -find "MSBuild\**\Bin\MSBuild.exe" | Select-Object -First 1
if (-not $msbuild -or -not (Test-Path -LiteralPath $msbuild)) {
    Write-Error "MSBuild.exe not found via vswhere."
    exit 1
}

if ([string]::IsNullOrWhiteSpace($SolutionOrProject)) {
    $target = Get-ChildItem -File | Where-Object { $_.Extension -eq ".slnx" } | Select-Object -First 1
    if (-not $target) {
        $target = Get-ChildItem -File | Where-Object { $_.Extension -eq ".sln" } | Select-Object -First 1
    }
    if (-not $target) {
        $target = Get-ChildItem -File | Where-Object { $_.Extension -eq ".csproj" } | Select-Object -First 1
    }
    if (-not $target) {
        Write-Error "No .slnx, .sln, or .csproj found in current working directory: $(Get-Location)"
        exit 1
    }
    $SolutionOrProject = $target.FullName
}

$msbuildArgs = @(
    $SolutionOrProject,
    "/m",
    "/nologo",
    "/v:minimal",
    "/t:Build",
    "/p:Configuration=$Configuration"
)

if (-not [string]::IsNullOrWhiteSpace($Platform)) {
    $msbuildArgs += "/p:Platform=$Platform"
}

if ($Restore) {
    $msbuildArgs += "/restore"
}

$platLabel = if ([string]::IsNullOrWhiteSpace($Platform)) { "SolutionDefault" } else { $Platform }
Write-Host "Building $SolutionOrProject [$Configuration|$platLabel] via $msbuild"
& $msbuild @msbuildArgs
exit $LASTEXITCODE