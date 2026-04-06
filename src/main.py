"""
Ponto de entrada do jogo
"""
import sys
from pathlib import Path

# Adiciona o diretório raiz ao path do Python
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config.paths import PROJECT_ROOT
from src.core.game import Game

def main():
    """Função principal"""
    print(f"[MAIN] Diretório raiz: {PROJECT_ROOT}")
    print(f"[MAIN] Diretório src: {Path(__file__).parent}")

    game = Game()
    game.run()

if __name__ == "__main__":
    main()