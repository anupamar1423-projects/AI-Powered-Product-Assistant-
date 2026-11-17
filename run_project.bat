@echo off
setlocal EnableExtensions
cd /d "%~dp0"

set "OPEN_BROWSER=1"
set "SKIP_INSTALL="

:parse_args
if "%~1"=="" goto args_done
if /I "%~1"=="--no-browser" set "OPEN_BROWSER=0"
if /I "%~1"=="--skip-install" set "SKIP_INSTALL=1"
if /I "%~1"=="--help" goto usage
if /I "%~1"=="-h" goto usage
shift
goto parse_args

:usage
echo Usage: run_project.bat [--no-browser] [--skip-install]
echo.
echo   --no-browser    Start both servers without opening browser tabs.
echo   --skip-install  Do not run pip install even if requirements changed.
echo.
echo Double-click this file, or run it from a VS Code Command Prompt.
exit /b 0

:args_done

rem ---------------------------------------------------------------- Python
set "PYTHON_CMD="
if not defined PYTHON_CMD (
    py -3.14 -c "import sys" >nul 2>&1
    if not errorlevel 1 set "PYTHON_CMD=py -3.14"
)
if not defined PYTHON_CMD (
    py -3.13 -c "import sys" >nul 2>&1
    if not errorlevel 1 set "PYTHON_CMD=py -3.13"
)
if not defined PYTHON_CMD (
    py -3.12 -c "import sys" >nul 2>&1
    if not errorlevel 1 set "PYTHON_CMD=py -3.12"
)
if not defined PYTHON_CMD (
    py -3.11 -c "import sys" >nul 2>&1
    if not errorlevel 1 set "PYTHON_CMD=py -3.11"
)
if not defined PYTHON_CMD (
    python -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>&1
    if not errorlevel 1 set "PYTHON_CMD=python"
)
if not defined PYTHON_CMD goto no_python

rem ---------------------------------------------------------- Virtualenv
if not exist ".venv\Scripts\python.exe" (
    echo [1/5] Creating the .venv virtual environment...
    %PYTHON_CMD% -m venv .venv
    if errorlevel 1 goto failed
) else (
    ".venv\Scripts\python.exe" -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>&1
    if errorlevel 1 (
        echo The existing .venv uses an unsupported Python version.
        echo Delete the .venv folder and run this file again.
        goto failed
    )
)
set "VENV_PY=%CD%\.venv\Scripts\python.exe"

rem ---------------------------------------------------------- Dependencies
set "NEED_INSTALL="
if not exist ".venv\requirements.installed" set "NEED_INSTALL=1"
if not defined NEED_INSTALL (
    fc /b requirements.txt ".venv\requirements.installed" >nul 2>&1
    if errorlevel 1 set "NEED_INSTALL=1"
)
if defined NEED_INSTALL (
    if defined SKIP_INSTALL (
        echo requirements.txt changed but --skip-install was given.
        goto failed
    )
    echo [2/5] Installing project packages. This can take a few minutes...
    "%VENV_PY%" -m pip install --upgrade pip
    if errorlevel 1 goto failed
    "%VENV_PY%" -m pip install -r requirements.txt
    if errorlevel 1 goto failed
    copy /y requirements.txt ".venv\requirements.installed" >nul
) else (
    echo [2/5] Project packages are already installed.
)
"%VENV_PY%" -c "import django, streamlit, rest_framework, ollama, huggingface_hub" >nul 2>&1
if errorlevel 1 (
    echo A required package is missing. Run: .venv\Scripts\python.exe -m pip install -r requirements.txt
    goto failed
)

rem ---------------------------------------------------------- Local config
if not exist ".env" (
    copy /y ".env.example" ".env" >nul
    echo [3/5] Created .env from .env.example.
) else (
    echo [3/5] Using the existing .env.
)
"%VENV_PY%" manage.py prepare_local_env
if errorlevel 1 goto failed

rem ---------------------------------------------------------- Database
echo [4/5] Applying migrations and loading the demo catalog...
"%VENV_PY%" manage.py migrate --noinput
if errorlevel 1 goto failed
"%VENV_PY%" manage.py seed_data
if errorlevel 1 goto failed
"%VENV_PY%" manage.py bootstrap_deploy_admin
if errorlevel 1 goto failed

rem ---------------------------------------------------------- Start servers
echo [5/5] Starting Django and Streamlit in separate windows...
start "FinVault - Django" /D "%CD%" cmd /k ""%VENV_PY%" manage.py runserver 127.0.0.1:8000"
start "FinVault - Streamlit" /D "%CD%" cmd /k ""%VENV_PY%" -m streamlit run streamlit_app\app.py --server.port 8501 --server.address 127.0.0.1 --server.headless true"

if "%OPEN_BROWSER%"=="1" (
    timeout /t 4 /nobreak >nul
    start "" "http://127.0.0.1:8000/"
    start "" "http://127.0.0.1:8501/"
)

echo.
echo Django website : http://127.0.0.1:8000/
echo Django admin   : http://127.0.0.1:8000/admin/
echo Streamlit      : http://127.0.0.1:8501/
echo The admin and Streamlit creator passwords are printed by prepare_local_env
echo and saved in the local .env file. Keep both server windows open.
exit /b 0

:no_python
echo Python 3.11 or newer was not found on PATH.
echo Install Python 3.12 from https://www.python.org/downloads/ and enable
echo "Add python.exe to PATH", or install the Python launcher and run: py --list
goto failed

:failed
echo.
echo Setup did not finish. Read the error above, fix it, and run this file again.
pause
exit /b 1
