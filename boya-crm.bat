@echo off
setlocal enabledelayedexpansion

REM ==========================================
REM BOYA-CRM 로컬 실행 스크립트 (Windows .bat)
REM - venv 자동 생성/활성화
REM - backend 요구사항 설치
REM - frontend 의존성 설치
REM - backend / frontend 동시에 실행
REM ==========================================

REM ---- 0) 루트 기준으로 이동 (이 .bat 파일이 있는 경로)
cd /d "%~dp0"

REM ---- 1) Python 실행기 찾기 (python 또는 py -3)
set PYTHON=python
%PYTHON% --version >NUL 2>&1
if errorlevel 1 (
  set PYTHON=py -3
  %PYTHON% --version >NUL 2>&1
  if errorlevel 1 (
    echo [ERROR] Python이 설치되어 있지 않거나 PATH에 없습니다.
    echo        https://www.python.org/downloads/ 에서 설치 후 다시 시도해주세요.
    pause
    exit /b 1
  )
)

REM ---- 2) 가상환경 생성/활성화
if not exist backend\.venv (
  echo [INFO] backend\.venv 가상환경 생성 중...
  %PYTHON% -m venv backend\.venv
  if errorlevel 1 (
    echo [ERROR] 가상환경 생성 실패
    pause
    exit /b 1
  )
)

call backend\.venv\Scripts\activate

REM ---- 3) 백엔드 의존성 설치
echo [INFO] backend requirements 설치/업데이트...
pip install --upgrade pip >NUL
pip install -r backend\requirements.txt
if errorlevel 1 (
  echo [ERROR] requirements 설치 실패
  pause
  exit /b 1
)

REM ---- 4) 프론트엔드 의존성 설치
if not exist frontend\node_modules (
  echo [INFO] frontend 의존성 설치(npm install)...
  pushd frontend
  call npm install
  if errorlevel 1 (
    echo [ERROR] npm install 실패
    popd
    pause
    exit /b 1
  )
  popd
)

REM ---- 5) 프론트에 API 주소 노출 (NEXT_PUBLIC_API)
REM .env.local 파일이 없으면 기본값으로 생성
if not exist frontend\.env.local (
  echo [INFO] frontend\.env.local 생성
  > frontend\.env.local echo NEXT_PUBLIC_API=http://localhost:8080
)

REM ---- 6) 백엔드 실행
echo [INFO] 백엔드 실행 시작 (http://localhost:8080) ...
start "BOYA-CRM Backend" cmd /k "cd /d %cd% & call backend\.venv\Scripts\activate && python backend\app.py"

REM ---- 7) 프론트엔드 실행
echo [INFO] 프론트엔드 실행 시작 (http://localhost:3000) ...
start "BOYA-CRM Frontend" cmd /k "cd /d %cd%\frontend && npm run dev"

echo.
echo ==========================================
echo BOYA-CRM 실행 완료!
echo - Backend: http://localhost:8080/api/health
echo - Frontend: http://localhost:3000
echo ==========================================
echo (창 두 개가 뜹니다. 종료하려면 각 창을 닫으세요.)
pause