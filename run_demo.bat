@echo off
cd /d %~dp0
echo Starting verify-agent demo server on http://127.0.0.1:8790 ...
python -m uvicorn app.main:app --host 127.0.0.1 --port 8790
pause
