@echo off
echo ================================
echo   RockAI — Viewer BDD SQLite
echo ================================
call venv\Scripts\activate.bat
echo Lancement sur http://localhost:8080 ...
sqlite_web rockai.db --port 8080 --no-browser
pause
