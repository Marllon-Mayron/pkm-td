"""
Ponto de entrada do jogo
"""
import sys
from pathlib import Path

# Adiciona o diretório raiz ao path do Python
sys.path.append(str(Path(__file__).parent.parent))

from src.core.game import Game

def main():
    """Função principal"""
    game = Game()
    game.run()

if __name__ == "__main__":
    main()