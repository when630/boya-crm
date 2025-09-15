@echo off
setlocal enabledelayedexpansion

REM ==========================================
REM BOYA-CRM 로컬 실행 스크립트 (Windows .bat)
REM - venv 자동 생성/의존성 설치
REM - backend / frontend 동시 실행(각각 별도 창)
REM ==========================================

REM ---- 0) 루트 기준으로 이동 (이 .bat 파일이 있는 경로)
cd /d "%~dp0"
set "ROOT=%~dp0"
set "BACKEND=%ROOT%backend"
set "FRONTEND=%ROOT%frontend"
set "VENV_DIR=%BACKEND%\.venv"
set "VENV_PY=%VENV_DIR%\Scripts\python.exe"

echo [INFO] ROOT: %ROOT%
echo [INFO] BACKEND: %BACKEND%
echo [INFO] FRONTEND: %FRONTEND%

REM ---- 1) Python 실행기 찾기 (python 또는 py -3)
set "PYTHON=python"
where %PYTHON% >nul 2>&1 || (
  set "PYTHON=py -3"
  %PYTHON% --version >nul 2>&1 || (
    echo [ERROR] Python이 설치되어 있지 않거나 PATH에 없습니다.
    echo         https://www.python.org/downloads/ 에서 설치 후 다시 시도해주세요.
    pause
    exit /b 1
  )
)

REM ---- 2) 가상환경 생성
if not exist "%VENV_DIR%" (
  echo [INFO] 백엔드 가상환경(venv) 생성 중...
  %PYTHON% -m venv "%VENV_DIR%"
  if errorlevel 1 (
    echo [ERROR] 가상환경 생성 실패
    pause
    exit /b 1
  )
)

REM ---- 3) 백엔드 의존성 설치/업데이트
echo [INFO] backend requirements 설치/업데이트...
"%VENV_PY%" -m pip install --upgrade pip
"%VENV_PY%" -m pip install -r "%BACKEND%\requirements.txt"
if errorlevel 1 (
  echo [ERROR] backend requirements 설치 실패
  pause
  exit /b 1
)

REM ---- 4) 프론트엔드 의존성 설치
where npm >nul 2>&1
if errorlevel 1 (
  echo [ERROR] npm(Node.js)가 설치되어 있지 않습니다. https://nodejs.org/ 에서 LTS 버전 설치 후 재시도해주세요.
  pause
  exit /b 1
)

if not exist "%FRONTEND%\node_modules" (
  echo [INFO] frontend 의존성 설치(npm install)...
  pushd "%FRONTEND%"
  call npm install
  if errorlevel 1 (
    echo [ERROR] npm install 실패
    popd
    pause
    exit /b 1
  )
  popd
)

REM ---- 5) 프론트 .env.local 없으면 생성 (API 기본값)
if not exist "%FRONTEND%\.env.local" (
  echo [INFO] frontend\.env.local 생성
  > "%FRONTEND%\.env.local" echo NEXT_PUBLIC_API=http://localhost:8080
)

REM ---- 6) 백엔드 실행 (새 창)
echo [INFO] 백엔드 실행 시작 (http://localhost:8080) ...
start "BOYA-CRM Backend" cmd /k ^
 "cd /d \"%BACKEND%\" && \"%VENV_PY%\" app.py"

REM ---- 7) 프론트엔드 실행 (새 창)
echo [INFO] 프론트엔드 실행 시작 (http://localhost:3000) ...
start "BOYA-CRM Frontend" cmd /k ^
 "cd /d \"%FRONTEND%\" && npm run dev"

echo(
echo ==========================================
echo BOYA-CRM 실행 완료!
echo - Backend:  http://localhost:8080/api/health
echo - Frontend: http://localhost:3000
echo ==========================================
echo (창 두 개가 뜹니다. 종료하려면 각 창을 닫으세요.)
pause