@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo ========================================
echo    GERAR E DIAGNOSTICAR POKEMON TD
echo ========================================
echo.
echo Pasta atual: %CD%
echo.

:menu
echo Escolha uma opcao:
echo [1] Gerar executavel (MODO DEBUG - mostra erro)
echo [2] Executar jogo original com Python
echo [3] Testar arquivos e pastas
echo [4] Sair
echo.
set /p opcao="Digite 1, 2, 3 ou 4: "

if "%opcao%"=="1" goto gerar
if "%opcao%"=="2" goto executar_python
if "%opcao%"=="3" goto testar
if "%opcao%"=="4" exit
goto menu

:gerar
echo.
echo ========================================
echo    GERANDO EXECUTAVEL MODO DEBUG
echo ========================================
echo.

echo [1/5] Verificando arquivos...
if not exist "src\main.py" (
    echo ERRO: src\main.py nao encontrado!
    pause
    goto menu
)
if not exist "res" (
    echo AVISO: Pasta res nao encontrada!
)
echo OK!

echo [2/5] Limpando builds anteriores...
if exist build rmdir /s /q build >nul 2>&1
if exist dist rmdir /s /q dist >nul 2>&1
if exist *.spec del /q *.spec >nul 2>&1
echo OK!

echo [3/5] Gerando executavel COM CONSOLE...
echo Isso pode levar 2-3 minutos. Aguarde...

REM CORREÇÃO AQUI: Removi o --debug e usei só --console
python -m PyInstaller --onedir --console --name "PokemonTD_Debug" --add-data "res;res" --add-data "src;src" --hidden-import pygame src\main.py

if errorlevel 1 (
    echo.
    echo ERRO: PyInstaller falhou!
    echo Pressione ENTER para continuar...
    pause
    goto menu
)
echo OK!

echo [4/5] Verificando executavel gerado...
if exist "dist\PokemonTD_Debug\PokemonTD_Debug.exe" (
    echo OK! Executavel criado!

    echo [5/5] Criando arquivos auxiliares...
    REM Criar bat de execucao
    (
        echo @echo off
        echo title Pokemon TD - DEBUG
        echo echo ========================================
        echo echo    EXECUTANDO MODO DEBUG
        echo echo ========================================
        echo echo.
        echo echo Pressione CTRL+C para fechar
        echo echo.
        echo "%%~dp0PokemonTD_Debug.exe"
        echo echo.
        echo echo ========================================
        echo echo Jogo finalizado. Codigo: %%errorlevel%%
        echo echo ========================================
        echo pause
    ) > "dist\PokemonTD_Debug\Executar_Debug.bat"

    echo OK!

    echo.
    echo ========================================
    echo    SUCESSO! Executavel gerado!
    echo ========================================
    echo.
    echo Pasta: dist\PokemonTD_Debug\
    echo.
    echo Para testar, execute:
    echo   1. Abra a pasta: dist\PokemonTD_Debug\
    echo   2. Execute: Executar_Debug.bat
    echo.
    echo OU execute agora:
    echo.

    set /p testar="Deseja executar agora? (S/N): "
    if /i "!testar!"=="S" (
        echo.
        echo ========================================
        echo    EXECUTANDO JOGO
        echo ========================================
        cd dist\PokemonTD_Debug
        PokemonTD_Debug.exe
        set ERROR_LEVEL=!errorlevel!
        cd ..\..

        echo.
        echo ========================================
        echo Jogo fechou com codigo: !ERROR_LEVEL!
        echo ========================================
        echo.
        if !ERROR_LEVEL! equ 0 (
            echo Jogo executou normalmente!
        ) else (
            echo ERRO! Codigo !ERROR_LEVEL! indica problema.
            echo.
            echo Possiveis causas:
            echo - Falta de arquivos de imagem/som
            echo - Erro no codigo Python
            echo - Pygame nao inicializou corretamente
        )
        echo.
        pause
    )
) else (
    echo ERRO: Executavel nao foi gerado!
    echo Verificando pasta dist...
    if exist dist (
        echo Conteudo da pasta dist:
        dir dist /b
    ) else (
        echo Pasta dist nao criada!
    )
    pause
)
goto menu

:executar_python
echo.
echo ========================================
echo    EXECUTANDO JOGO COM PYTHON
echo ========================================
echo.
if not exist "src\main.py" (
    echo ERRO: src\main.py nao encontrado!
    pause
    goto menu
)
echo Executando...
echo.
echo ========================================
python src\main.py
echo ========================================
echo.
echo Jogo finalizado. Codigo: %errorlevel%
echo.
if %errorlevel% equ 0 (
    echo Jogo funcionou corretamente!
    echo Se o executavel nao funciona, o problema eh do PyInstaller.
) else (
    echo Jogo apresentou erro mesmo no Python!
    echo Corrija o codigo antes de gerar executavel.
)
echo.
pause
goto menu

:testar
echo.
echo ========================================
echo    TESTANDO ARQUIVOS
echo ========================================
echo.
echo [1/4] Estrutura do projeto:
echo.
echo Arquivos Python em src:
if exist src\*.py (
    dir src\*.py /b
) else (
    echo Nenhum arquivo .py encontrado em src/
)
echo.
echo [2/4] Conteudo da pasta res:
if exist res (
    echo Arquivos encontrados:
    dir res /b 2>nul
    echo.
    echo Total:
    dir res /b 2>nul | find /c /v ""
) else (
    echo PASTA res NAO ENCONTRADA!
)
echo.
echo [3/4] Verificando pygame:
python -c "import pygame; print('Pygame versao:', pygame.version.ver)" 2>nul
if errorlevel 1 (
    echo ERRO: Pygame nao instalado!
    echo Instale com: pip install pygame
) else (
    echo Pygame OK!
)
echo.
echo [4/4] Verificando PyInstaller:
python -c "import PyInstaller; print('PyInstaller versao:', PyInstaller.__version__)" 2>nul
if errorlevel 1 (
    echo PyInstaller nao encontrado!
    echo Instale com: pip install pyinstaller
) else (
    echo PyInstaller OK!
)
echo.
echo ========================================
pause
goto menu