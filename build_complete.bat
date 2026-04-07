#!/bin/bash
echo "========================================"
echo "   GERANDO POKEMON TD - VERSAO FINAL"
echo "========================================"
echo ""

echo "[1/6] Verificando ambiente..."
if [ ! -f "src/main.py" ]; then
    echo "ERRO: Arquivo src/main.py nao encontrado!"
    echo "Certifique-se de estar na pasta raiz do projeto."
    read -p "Pressione ENTER para continuar..."
    exit 1
fi
echo "OK!"

echo "[2/6] Verificando PyInstaller..."
if ! command -v pyinstaller &> /dev/null; then
    echo "Instalando PyInstaller..."
    python -m pip install pyinstaller
fi
echo "OK!"

echo "[3/6] Limpando builds anteriores..."
rm -rf build dist *.spec
echo "OK!"

echo "[4/6] Gerando executavel rapido (onedir)..."
echo "Isso pode levar alguns minutos. Aguarde..."
python -m PyInstaller --onedir --windowed --name "Pokemon TD" --add-data "res;res" --add-data "src;src" --noconfirm src/main.py

if [ $? -ne 0 ]; then
    echo ""
    echo "ERRO: Falha ao gerar executavel!"
    echo "Verifique se todos os arquivos necessarios existem."
    read -p "Pressione ENTER para continuar..."
    exit 1
fi
echo "OK!"

echo "[5/6] Verificando arquivos gerados..."
if [ -f "dist/Pokemon TD/Pokemon TD.exe" ]; then
    echo "OK! Executavel criado com sucesso."
else
    echo "ERRO: Executavel nao encontrado!"
    read -p "Pressione ENTER para continuar..."
    exit 1
fi

echo "[6/6] Criando arquivo de execucao rapida..."
cat > "dist/Pokemon TD/Iniciar Jogo.bat" << EOF
@echo off
start "" "%~dp0Pokemon TD.exe"
EOF
echo "OK!"

echo ""
echo "========================================"
echo "        FINALIZADO COM SUCESSO!"
echo "========================================"
echo ""
echo "O jogo esta em: dist/Pokemon TD/"
echo ""
echo "Para executar:"
echo "   1. Abra a pasta 'dist/Pokemon TD'"
echo "   2. Execute 'Pokemon TD.exe' ou 'Iniciar Jogo.bat'"
echo ""
echo "O jogo abrira RAPIDO (2-3 segundos)!"
echo ""
echo "========================================"
read -p "Pressione ENTER para sair..."