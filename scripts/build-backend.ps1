# build-backend.ps1 — PyInstaller 백엔드 빌드 + Tauri binaries/ 복사
# Usage: .\scripts\build-backend.ps1
# 사전 요구사항: backend venv 활성화 상태, PyInstaller 설치 완료

$ErrorActionPreference = "Stop"

$scriptDir  = Split-Path -Parent $MyInvocation.MyCommand.Path
$backendDir = Join-Path $scriptDir "..\backend"
$tauriDir   = Join-Path $scriptDir "..\src-tauri"

# 1. backend 디렉터리로 이동
Set-Location $backendDir
Write-Host "[1/3] backend 디렉터리: $(Get-Location)" -ForegroundColor Cyan

# 2. PyInstaller 빌드
#    실행 중인 voc-backend.exe가 있으면 build 폴더 잠금 발생 → 먼저 종료
Write-Host "[2/3] 실행 중인 voc-backend.exe 종료 시도..." -ForegroundColor Cyan
$proc = Get-Process -Name "voc-backend" -ErrorAction SilentlyContinue
if ($proc) {
    $proc | Stop-Process -Force
    Start-Sleep -Milliseconds 800
    Write-Host "      종료 완료" -ForegroundColor DarkGray
} else {
    Write-Host "      실행 중인 프로세스 없음" -ForegroundColor DarkGray
}

Write-Host "[2/3] PyInstaller 빌드 시작..." -ForegroundColor Cyan
& ".\venv\Scripts\python.exe" -m PyInstaller voc-backend.spec --clean --noconfirm

if (-not (Test-Path "dist\voc-backend.exe")) {
    Write-Error "빌드 실패: dist\voc-backend.exe 를 찾을 수 없습니다"
    exit 1
}
Write-Host "빌드 성공: dist\voc-backend.exe" -ForegroundColor Green

# 3. Tauri sidecar binaries/ 로 복사
$binariesDir = Join-Path $tauriDir "binaries"
New-Item -ItemType Directory -Force -Path $binariesDir | Out-Null

# Tauri sidecar 파일명: {name}-{target_triple}.exe
$dest = Join-Path $binariesDir "voc-backend-x86_64-pc-windows-msvc.exe"
Copy-Item "dist\voc-backend.exe" $dest -Force
Write-Host "[3/3] sidecar 복사 완료: $dest" -ForegroundColor Green
