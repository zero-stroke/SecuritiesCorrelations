@echo on
SETLOCAL

:: This script checks for the existence of the appropriate Python environment
:: (either a conda environment or a Python virtual environment).
:: If the environment does not exist, it will be created.
:: Then, required packages from the requirements.txt file are installed.

:: First, check if 'conda' is available in the system's PATH.
WHERE conda >nul 2>&1
IF %ERRORLEVEL% EQU 0 (
    :: If conda is available, use it to manage the Python environment.
    echo Using conda...

    :: Check if a conda environment named 'SecuritiesCorrelations' already exists.
    call conda info --envs | findstr /C:"SecuritiesCorrelations" 1>nul
    IF %ERRORLEVEL% NEQ 0 (
        :: If the environment doesn't exist, create it.
        echo Creating conda environment...
        call conda create --name SecuritiesCorrelations python=3.10.13 -y
    )

    :: Activate the conda environment and install required packages.
    echo Installing requirements...
    call conda activate SecuritiesCorrelations && pip install -r requirements.txt
) ELSE (
    :: If conda is not available, fall back to using Python's built-in 'venv' module.
    echo Using Python venv...

    :: Check if a virtual environment directory named 'SecuritiesCorrelations' already exists.
    IF NOT EXIST ".\SecuritiesCorrelations\" (
        :: If the directory doesn't exist, create the virtual environment.
        echo Creating virtual environment...
        python -m venv SecuritiesCorrelations
    )

    :: Activate the virtual environment and install required packages.
    echo Installing requirements...
    call .\SecuritiesCorrelations\Scripts\activate && pip install -r requirements.txt
)

:: End the localized environment changes and keep the command prompt open for user inspection.
ENDLOCAL
pause
