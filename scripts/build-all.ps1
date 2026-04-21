# build-all.ps1 — 전체 빌드: 백엔드 번들 → 프론트엔드 → Tauri 패키징
# Usage: .\scripts\build-all.ps1
# 사전 요구사항:
#   - Rust + rustup 설치 (~/.rustup/toolchains/stable-x86_64-pc-windows-msvc)
#   - Node.js + npm 설치
#   - Python venv (backend/ 에서 pip install -r requirements.txt 완료)

$ErrorActionPreference = "Stop"

# ── cargo PATH 보장 ───────────────────────────────────────────────
$cargoBin     = "$env:USERPROFILE\.cargo\bin"
$toolchainBin = (Get-ChildItem "$env:USERPROFILE\.rustup\toolchains" -Directory -ErrorAction SilentlyContinue |
                 Where-Object { $_.Name -like "stable-*-windows-msvc" } |
                 Select-Object -First 1 -ExpandProperty FullName) + "\bin"

foreach ($p in @($cargoBin, $toolchainBin)) {
    if ($p -and (Test-Path $p) -and ($env:PATH -notlike "*$p*")) {
        $env:PATH = "$p;$env:PATH"
        Write-Host "[PATH] 추가: $p" -ForegroundColor DarkGray
    }
}

$cargoExe = Get-Command cargo.exe -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source
if (-not $cargoExe) {
    # PATH에서 못 찾으면 toolchain 직접 경로 시도
    $cargoExe = $toolchainBin + "\cargo.exe"
    if (-not (Test-Path $cargoExe)) {
        Write-Error "cargo를 찾을 수 없습니다. Rust가 올바르게 설치됐는지 확인하세요."
        exit 1
    }
}
Write-Host "[INFO] cargo: $cargoExe" -ForegroundColor DarkGray
Set-Alias -Name cargo -Value $cargoExe -Scope Script

$scriptDir  = Split-Path -Parent $MyInvocation.MyCommand.Path
$rootDir    = Join-Path $scriptDir ".."
$frontendDir = Join-Path $rootDir "frontend"
$tauriDir   = Join-Path $rootDir "src-tauri"

Write-Host "=== VOC Collector v1.5 전체 빌드 ===" -ForegroundColor Yellow

# ── Phase 1: 백엔드 번들 ──────────────────────────────────────────
Write-Host "`n[1/3] 백엔드 PyInstaller 빌드" -ForegroundColor Cyan
& "$scriptDir\build-backend.ps1"

# ── npm.cmd 경로 확인 ────────────────────────────────────────────
$npmCmd = (Get-Command npm.cmd -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source)
if (-not $npmCmd) { $npmCmd = "C:\Program Files\nodejs\npm.cmd" }
if (-not (Test-Path $npmCmd)) { Write-Error "npm을 찾을 수 없습니다."; exit 1 }
Write-Host "[INFO] npm: $npmCmd" -ForegroundColor DarkGray

# ── Phase 2: 프론트엔드 빌드 ─────────────────────────────────────
Write-Host "`n[2/3] 프론트엔드 빌드" -ForegroundColor Cyan
Set-Location $frontendDir
& $npmCmd run build
if ($LASTEXITCODE -and $LASTEXITCODE -ne 0) { Write-Error "프론트엔드 빌드 실패 (exit: $LASTEXITCODE)"; exit 1 }

# ── Phase 3: Tauri 패키징 ─────────────────────────────────────────
Write-Host "`n[3/3] Tauri 패키징 (NSIS 인스톨러 생성)" -ForegroundColor Cyan
# cmd로 실행 — PATH 설정 + tauri.cmd 호출
$tauriScript = "set PATH=$toolchainBin;%PATH% && cd /d `"$tauriDir`" && `"..\frontend\node_modules\.bin\tauri.cmd`" build"
& "$env:SystemRoot\System32\cmd.exe" /c $tauriScript

$installer = Join-Path $tauriDir "target\release\bundle\nsis\VOC Collector_1.5.0_x64-setup.exe"
if (Test-Path $installer) {
    Write-Host "`n=== 빌드 완료 ===" -ForegroundColor Green
    Write-Host "인스톨러: $installer" -ForegroundColor Green
} else {
    Write-Error "인스톨러 파일을 찾을 수 없습니다: $installer"
}
