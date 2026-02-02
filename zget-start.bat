@echo off
setlocal

echo 🚀 Starting zget...

REM Check for uv
where uv >nul 2>nul
if %errorlevel% neq 0 (
    echo 📦 Installing uv (fast python package manager)...
    powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
    set "PATH=%USERPROFILE%\.cargo\bin;%PATH%"
)

REM Sync dependencies and run
echo ⚡️ Launching Server...
uv run zget-server --open

pause
