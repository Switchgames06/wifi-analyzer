@echo off
:: Mount the WSL network share directory as a temporary Windows drive letter
pushd "%~dp0"

:: Execute using the Windows Python interpreter inside your Windows environment
venv_win\Scripts\python.exe main.py

:: Unmount the temporary network drive when the application closes
popd