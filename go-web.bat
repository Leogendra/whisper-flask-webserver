@echo off
call venv\Scripts\activate

start http://localhost:5000

@REM The -u option forces the stdout and stderr streams to be unbuffered.
python -u app.py


pause