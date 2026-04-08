@echo off
echo Starting ChessSuite...
echo.
echo   1. Chess Engine     (http://localhost:5000)
echo   2. Chess Analyser   (http://localhost:5001)
echo   3. Puzzle Generator (http://localhost:5002)
echo   4. All three
echo.
set /p choice="Enter choice (1-4): "
if "%choice%"=="1" start "Chess Engine" cmd /k "cd /d "%~dp0chess-engine" && pip install -r requirements.txt -q && python src/app.py"
if "%choice%"=="2" start "Chess Analyser" cmd /k "cd /d "%~dp0chess-analyser" && pip install -r requirements.txt -q && python src/app.py"
if "%choice%"=="3" start "Puzzle Generator" cmd /k "cd /d "%~dp0chess-puzzle-generator" && pip install -r requirements.txt -q && python src/app.py"
if "%choice%"=="4" (
  start "Chess Engine" cmd /k "cd /d "%~dp0chess-engine" && pip install -r requirements.txt -q && python src/app.py"
  start "Chess Analyser" cmd /k "cd /d "%~dp0chess-analyser" && pip install -r requirements.txt -q && python src/app.py"
  start "Puzzle Generator" cmd /k "cd /d "%~dp0chess-puzzle-generator" && pip install -r requirements.txt -q && python src/app.py"
)
