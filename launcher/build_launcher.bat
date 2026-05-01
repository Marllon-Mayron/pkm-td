@echo off
chcp 65001 >nul
title Gerando Launcher do Pokémon TD

echo ========================================
echo    GERANDO LAUNCHER EXECUTÁVEL
echo ========================================
echo.

REM Volta para a raiz do projeto
cd ..

REM Instala PyInstaller se não tiver
python -m pip install pyinstaller

REM Gera o launcher.exe
echo Gerando launcher.exe...
python -m PyInstaller --onefile --noconsole --name "PokemonTD_Launcher" --add-data "game_version.txt;." launcher/launcher.py

if errorlevel 1 (
    echo.
    echo ERRO: Falha ao gerar launcher!
    pause
    exit /b 1
)

echo.
echo ========================================
echo    SUCESSO!
echo ========================================
echo.
echo Launcher criado em: dist\PokemonTD_Launcher.exe
echo.
echo IMPORTANTE:
echo 1. Copie este arquivo .exe para a pasta que vai distribuir
echo 2. A primeira execução criará a pasta "PokemonTD"
echo 3. O jogo será baixado automaticamente do GitHub
echo.

pause