@echo on
SETLOCAL

:: Check if conda is available
WHERE conda >nul 2>&1
IF %ERRORLEVEL% EQU 0 (
    :: Use conda
    call conda activate SecuritiesCorrelations
) ELSE (
    :: Use Python venv
    call .\SecuritiesCorrelations_venv\Scripts\activate
)

:: Run main_ui.py
python main_ui.py

:: Open localhost:8080 in default browser
start http://localhost:8080

ENDLOCAL
pause
