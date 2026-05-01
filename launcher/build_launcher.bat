@echo off
chcp 65001 >nul
title Gerando Launcher Profissional

echo ========================================
echo    GERANDO LAUNCHER POKEMON TD
echo ========================================
echo.

cd ..

echo [1/2] Instalando dependencias...
python -m pip install pyinstaller

echo.
echo [2/2] Gerando executavel...
python -m PyInstaller --onefile --console --name "PokemonTD_Launcher" launcher/launcher_pro.py

if errorlevel 1 (
    echo.
    echo ERRO na geracao!
    pause
    exit /b 1
)

echo.
echo ========================================
echo    SUCESSO
echo ========================================
echo.
echo Launcher criado: dist\PokemonTD_Launcher.exe
echo.
echo Funcionalidades:
echo   - Backup automatico de saves
echo   - Multi-versoes
echo   - Modo offline
echo   - Interface profissional
echo.
pause