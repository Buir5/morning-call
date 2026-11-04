@echo off
chcp 65001 >nul
title MORNING CALL
cd /d "%~dp0"
set "PY=C:\Users\Administrator\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe"
echo 正在启动 MORNING CALL ...
start "" http://127.0.0.1:8787/
"%PY%" server.py
echo.
echo 服务已停止，按任意键关闭。
pause >nul