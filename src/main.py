"""
Ponto de entrada do jogo
"""
import sys
from pathlib import Path

# Adiciona o diretório raiz ao path do Python
sys.path.append(str(Path(__file__).parent.parent))


# Importa as constantes (não causa circular import)
from src.config.paths import PROJECT_ROOT

from src.core.game import Game

def main():
    """Função principal"""
    print("aaaaaaaaa"+str(Path(__file__).parent.parent))
    game = Game()
    game.run()

if __name__ == "__main__":
    main()