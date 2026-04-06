@echo off
title Gerando Pokemon TD
color 0A

echo ========================================
echo    GERANDO POKEMON TD - VERSAO FINAL
echo ========================================
echo.

echo [1/6] Verificando ambiente...
if not exist "src\main.py" (
    echo ERRO: Arquivo src/main.py nao encontrado!
    echo Certifique-se de estar na pasta raiz do projeto.
    pause
    exit /b 1
)
echo OK!

echo [2/6] Verificando PyInstaller...
pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo Instalando PyInstaller...
    pip install pyinstaller
)
echo OK!

echo [3/6] Limpando builds anteriores...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist "*.spec" del /q "*.spec"
echo OK!

echo [4/6] Gerando executavel rapido (onedir)...
echo Isso pode levar alguns minutos. Aguarde...
python -m PyInstaller --onedir --windowed --name "Pokemon TD" --add-data "res;res" --add-data "src;src" --noconfirm src\main.py

if errorlevel 1 (
    echo.
    echo ERRO: Falha ao gerar executavel!
    echo Verifique se todos os arquivos necessarios existem.
    pause
    exit /b 1
)
echo OK!

echo [5/6] Verificando arquivos gerados...
if exist "dist\Pokemon TD\Pokemon TD.exe" (
    echo OK! Executavel criado com sucesso.
) else (
    echo ERRO: Executavel nao encontrado!
    pause
    exit /b 1
)

echo [6/6] Criando arquivo de execucao rapida...
(
echo @echo off
echo start "" "%%~dp0Pokemon TD.exe"
) > "dist\Pokemon TD\Iniciar Jogo.bat"
echo OK!

echo.
echo ========================================
echo        FINALIZADO COM SUCESSO!
echo ========================================
echo.
echo O jogo esta em: dist\Pokemon TD\
echo.
echo Para executar:
echo   1. Abra a pasta "dist\Pokemon TD"
echo   2. Execute "Pokemon TD.exe" ou "Iniciar Jogo.bat"
echo.
echo O jogo abrira RAPIDO (2-3 segundos)!
echo.
echo ========================================
pause