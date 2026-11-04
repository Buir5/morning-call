@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul 2>nul
title Morning Call - local player
cd /d "%~dp0"

set "PYEXE="
set "PYARG="

if exist "%USERPROFILE%\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe" (
  set "PYEXE=%USERPROFILE%\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe"
)

if not defined PYEXE (
  for %%P in (python.exe) do if not defined PYEXE if exist "%%~$PATH:P" set "PYEXE=%%~$PATH:P"
)

if not defined PYEXE (
  where py >nul 2>nul
  if not errorlevel 1 (
    set "PYEXE=py"
    set "PYARG=-3"
  )
)

if not defined PYEXE goto nopy

echo Starting Morning Call on http://127.0.0.1:8787/
echo Close this window to stop the server.
echo.

rem browser is opened by server.py after the port is ready

"%PYEXE%" %PYARG% server.py
set "RC=%ERRORLEVEL%"
echo.
echo Server stopped. exit code %RC%
echo Press any key to close this window.
pause >nul
goto :eof

:nopy
echo.
echo Python 3.9+ was not found on this machine.
echo Install it from https://www.python.org/downloads/ and tick "Add python.exe to PATH".
echo.
pause
goto :eof
