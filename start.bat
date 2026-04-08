@echo off
title ChessSuite Launcher
echo ============================================
echo  ChessSuite — Choose a tool to launch
echo ============================================
echo.
echo [1] Chess Engine      (play vs AI)   — http://localhost:5000
echo [2] Chess Analyser    (game stats)   — http://localhost:5001
echo [3] Chess Puzzles     (puzzle trainer)— http://localhost:5002
echo [4] Launch all three
echo.
set /p choice=Enter choice (1/2/3/4):

if "%choice%"=="1" goto engine
if "%choice%"=="2" goto analyser
if "%choice%"=="3" goto puzzles
if "%choice%"=="4" goto all
echo Invalid choice.
pause
goto :eof

:engine
echo.
echo Installing chess-engine dependencies...
pip install -r "%~dp0chess-engine\requirements.txt" -q
echo Starting Chess Engine at http://localhost:5000 ...
start "" cmd /k "cd /d "%~dp0chess-engine\src" && python app.py"
start "" http://localhost:5000
goto :eof

:analyser
echo.
echo Installing chess-analyser dependencies...
pip install -r "%~dp0chess-analyser\requirements.txt" -q
echo Starting Chess Analyser at http://localhost:5001 ...
echo NOTE: Run "python fetch.py lichess YOUR_USERNAME" first to load games.
start "" cmd /k "cd /d "%~dp0chess-analyser\src" && python app.py"
start "" http://localhost:5001
goto :eof

:puzzles
echo.
echo Installing chess-puzzle-generator dependencies...
pip install -r "%~dp0chess-puzzle-generator\requirements.txt" -q
echo Starting Chess Puzzle Trainer at http://localhost:5002 ...
echo NOTE: First run generates 20 starter puzzles (~30s).
start "" cmd /k "cd /d "%~dp0chess-puzzle-generator\src" && python app.py"
start "" http://localhost:5002
goto :eof

:all
echo.
echo Installing all dependencies...
pip install -r "%~dp0chess-engine\requirements.txt" -q
pip install -r "%~dp0chess-analyser\requirements.txt" -q
pip install -r "%~dp0chess-puzzle-generator\requirements.txt" -q
echo Launching all three tools...
start "" cmd /k "cd /d "%~dp0chess-engine\src" && python app.py"
start "" cmd /k "cd /d "%~dp0chess-analyser\src" && python app.py"
start "" cmd /k "cd /d "%~dp0chess-puzzle-generator\src" && python app.py"
timeout /t 2 /nobreak >nul
start "" http://localhost:5000
start "" http://localhost:5001
start "" http://localhost:5002
goto :eof
