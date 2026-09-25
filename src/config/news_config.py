# src/config/news_config.py
"""
Configuração de News e Changelogs por versão.

Cada versão do jogo pode ter:
  - Uma pasta de imagens em: res/PokemonSprites/screenshots/news/<versao>/
  - Um link de devlog (changelog completo) associado
  - Um título para cada imagem (por número no nome: news_1.png -> 1)
"""
import re


# =====================================================================
# LINKS DE DEVLOG (changelog completo) POR VERSÃO
# =====================================================================
NEWS_DEVLOGS = {
    "0.1.18": "https://bojackjeguin.itch.io/pokemon-tower-defense-by-bojackjeguin/devlog/1665606/v0118-sua-galeria",
    "0.1.17": "https://bojackjeguin.itch.io/pokemon-tower-defense-by-bojackjeguin/devlog/1661725/v0117-sorria-para-a-cmera",
    # "0.1.19": "https://...",
}


# =====================================================================
# TÍTULOS DAS IMAGENS DE NEWS
# Estrutura: versão -> { numero_da_imagem: "título" }
# O número é extraído do nome do arquivo (news_1.png -> 1, news_2.png -> 2)
# =====================================================================
NEWS_IMAGE_TITLES = {
    "0.1.21": {
        1: "Capa da versão: 0.1.21.",
        2: "Tela de seleçaõ de time para o pvp.",
        3: "Modo arena PVP",
        4: "Muitos itens seguraveis novos"
    },
    "0.1.20": {
        1: "Capa da versão: 0.1.20.",
        2: "Nova tela de hall de npcs.",
        3: "Novo npc para renomear seus pokemons",
        4: "Novo npc para reaprender moves de pokemons",
        5: "Nova forma de jogo, batalhando contra treinadores inteligentes"
    },
    "0.1.19": {
        1: "Novas fases de fim de campanha, e muitas correções pro modo mobile",
    },
    "0.1.18": {
        1: "Raids Multijogador Coopreativo disponivel!",
        2: "Adicionado nova tela de perfil do jogador.",
        3: "Adicionado nova tela de galeria!",
        4: "Painel de estatisticas.",
    },
    "0.1.17": {
        1: "Novo sistema de camera, permitindo registrar sua jornada!",
        2: "Novo painel para visualizacao dos seus pokemons",
    },

}


# =====================================================================
# HELPERS
# =====================================================================
def _version_key(v: str):
    """Chave de ordenação para versões (0.1.9 < 0.1.10 < 0.1.18)."""
    parts = []
    for p in str(v).split("."):
        try:
            parts.append(int(p))
        except ValueError:
            parts.append(0)
    return parts


def get_devlog_url(version: str):
    """Retorna a URL do devlog associado à versão, ou None."""
    if not version:
        return None
    return NEWS_DEVLOGS.get(version)


def get_all_versions():
    """Lista todas as versões conhecidas (mais recente primeiro)."""
    return sorted(NEWS_DEVLOGS.keys(), key=_version_key, reverse=True)


def get_news_title(version: str, filename: str):
    """
    Retorna o título da imagem de news da versão informada.
    O número é extraído do nome do arquivo (ex: news_3.png -> 3).
    Retorna None se não houver título mapeado.
    """
    if not version or not filename:
        return None
    titles = NEWS_IMAGE_TITLES.get(version, {})
    if not titles:
        return None
    m = re.search(r'(\d+)', filename)
    if not m:
        return None
    return titles.get(int(m.group(1)))


def natural_sort_key(path):
    """
    Chave de ordenação natural para nomes de arquivo:
    news_2.png vem ANTES de news_10.png (diferente de sort alfabético).
    """
    name = path.name if hasattr(path, "name") else str(path)
    return [int(t) if t.isdigit() else t.lower()
            for t in re.split(r'(\d+)', name)]