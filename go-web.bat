@echo off
call venv\Scripts\activate

@REM The -u option forces the stdout and stderr streams to be unbuffered.
python -u app.py

start http://localhost:5000

pause