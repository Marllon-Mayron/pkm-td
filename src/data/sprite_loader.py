# src/data/sprite_loader.py - CORREÇÃO FINAL - LAYOUT HORIZONTAL CORRETO
"""
Sistema de carregamento de sprites para a nova estrutura InMap
Suporta 8 direções e animações baseadas em AnimData.xml
Os sprites são PNGs individuais como Walk-Anim.png, Idle-Anim.png

LAYOUT DO SPRITESHEET (HORIZONTAL):
- CADA LINHA = uma DIREÇÃO (8 direções)
- CADA COLUNA = um FRAME da animação para aquela direção

Exemplo para animação com 5 frames e 8 direções:
- Largura total = 5 * frame_width
- Altura total = 8 * frame_height
"""

import os
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import pygame


class SpriteLoader:
    """Carrega e gerencia sprites na nova estrutura de pastas"""

    # Direções na ordem das LINHAS do spritesheet (cada linha = uma direção)
    DIRECTIONS = [
        "down",  # linha 0
        "down-right",  # linha 1
        "right",  # linha 2
        "up-right",  # linha 3
        "up",  # linha 4
        "up-left",  # linha 5
        "left",  # linha 6
        "down-left"  # linha 7
    ]

    # Mapeamento para direções antigas (4 direções)
    LEGACY_DIRECTION_MAP = {
        "down": "down",
        "right": "right",
        "up": "up",
        "left": "left"
    }

    def __init__(self, base_path: Path):
        self.base_path = Path(base_path)
        self.cache: Dict[str, Dict] = {}  # Cache de sprites carregados

    def load_pokemon_sprites(self, pokemon_id: int, shiny: bool = False) -> Dict:
        """
        Carrega todos os sprites de um Pokémon
        Retorna dicionário com animações e direções
        """
        cache_key = f"{pokemon_id}_{shiny}"
        if cache_key in self.cache:
            return self.cache[cache_key]

        # Formata ID com 4 dígitos
        pokemon_dir_name = f"{pokemon_id:04d}"

        # Caminho base da pasta do Pokémon
        if shiny:
            # Shiny: .../InMaps/0010/0000/0001/
            pokemon_path = self.base_path / pokemon_dir_name / "0000" / "0001"
        else:
            # Normal: .../InMaps/0004/
            pokemon_path = self.base_path / pokemon_dir_name

        print(f"[SPRITE] Carregando Pokémon ID {pokemon_id} de: {pokemon_path}")

        if not pokemon_path.exists():
            print(f"[SPRITE] Pasta não encontrada: {pokemon_path}")
            return self._create_empty_animation()

        # Carrega o arquivo de dados de animação
        anim_data = self._load_anim_data(pokemon_path)
        print(f"[SPRITE] AnimData carregado: {list(anim_data.keys())}")

        # Carrega os sprites para cada animação
        animations = {}

        # Por enquanto só carregamos Idle e Walk
        for anim_name in ["Idle", "Walk"]:
            # Tenta carregar o PNG com sufixo -Anim
            png_path = pokemon_path / f"{anim_name}-Anim.png"

            if png_path.exists():
                print(f"[SPRITE] Carregando {anim_name}-Anim.png")
                anim_frames = self._load_animation_from_spritesheet(
                    png_path,
                    anim_name,
                    anim_data.get(anim_name, {})
                )
                if anim_frames:
                    animations[anim_name.lower()] = anim_frames
                    print(f"[SPRITE] ✓ {anim_name} carregado com {len(anim_frames)} direções")
                    # Mostra quantos frames por direção
                    for dir_name, frames in anim_frames.items():
                        print(f"[SPRITE]   {dir_name}: {len(frames)} frames")
            else:
                print(f"[SPRITE] {anim_name}-Anim.png não encontrado em {pokemon_path}")

        # Se não encontrou nenhuma animação, cria placeholder
        if not animations:
            print(f"[SPRITE] Nenhuma animação encontrada para {pokemon_path}")
            animations = self._create_empty_animation()

        result = {
            "animations": animations,
            "anim_data": anim_data,
            "path": pokemon_path
        }

        self.cache[cache_key] = result
        return result

    def _load_animation_from_spritesheet(self, spritesheet_path: Path, anim_name: str, anim_info: Dict) -> Dict[
        str, List[pygame.Surface]]:
        """
        Carrega animação de um spritesheet PNG

        LAYOUT HORIZONTAL:
        - CADA LINHA = uma DIREÇÃO (8 direções no total)
        - CADA COLUNA = um FRAME da animação para aquela direção

        Exemplo para animação com 5 frames:
        - Linha 0: frames da direção "down": [frame0, frame1, frame2, frame3, frame4]
        - Linha 1: frames da direção "down-right": [frame0, frame1, frame2, frame3, frame4]
        - Linha 2: frames da direção "right": [frame0, frame1, frame2, frame3, frame4]
        - etc...

        Para obter os frames de uma direção, pegamos a linha correspondente
        e percorremos todas as colunas (frames)
        """
        try:
            spritesheet = pygame.image.load(str(spritesheet_path)).convert_alpha()
            sheet_width, sheet_height = spritesheet.get_size()

            # Obtém informações do frame do AnimData
            frame_width = anim_info.get("frame_width", 32)
            frame_height = anim_info.get("frame_height", 32)
            durations = anim_info.get("durations", [])
            num_frames = len(durations)

            # Se não tem informação de duração, calcula baseado na largura
            if num_frames == 0:
                num_frames = sheet_width // frame_width
                #print(f"[SPRITE] Inferindo {num_frames} frames para {anim_name} (baseado na largura)")

            # Calcula quantas direções baseado na altura
            num_directions = sheet_height // frame_height
            #print(f"[SPRITE] Spritesheet: {sheet_width}x{sheet_height}, frame={frame_width}x{frame_height}")
            #print(f"[SPRITE] Direções (linhas): {num_directions}, Frames por direção (colunas): {num_frames}")

            frames_by_direction = {}

            # Para cada direção (linha)
            for dir_idx in range(min(num_directions, len(self.DIRECTIONS))):
                direction = self.DIRECTIONS[dir_idx]
                frames = []

                # Para cada frame da animação (coluna)
                for frame_idx in range(num_frames):
                    # Posição: x = frame * frame_width, y = direção * frame_height
                    x = frame_idx * frame_width
                    y = dir_idx * frame_height

                    # Verifica se o frame está dentro da spritesheet
                    if x + frame_width <= sheet_width and y + frame_height <= sheet_height:
                        rect = pygame.Rect(x, y, frame_width, frame_height)
                        frame_surface = spritesheet.subsurface(rect)
                        frames.append(frame_surface)

                if frames:
                    frames_by_direction[direction] = frames

            return frames_by_direction

        except Exception as e:
            print(f"[SPRITE] Erro ao carregar spritesheet {spritesheet_path}: {e}")
            return {}

    def _load_anim_data(self, pokemon_path: Path) -> Dict:
        """Carrega e parseia o AnimData.xml"""
        anim_data_path = pokemon_path / "AnimData.xml"

        if not anim_data_path.exists():
            print(f"[SPRITE] AnimData.xml não encontrado em {anim_data_path}")
            return {}

        try:
            tree = ET.parse(anim_data_path)
            root = tree.getroot()

            anims_data = {}
            anims_element = root.find("Anims")

            if anims_element is None:
                return {}

            for anim in anims_element.findall("Anim"):
                name_elem = anim.find("Name")
                if name_elem is None:
                    continue

                anim_name = name_elem.text
                anim_info = {
                    "name": anim_name,
                    "durations": []
                }

                # Pega Index se existir
                index_elem = anim.find("Index")
                if index_elem is not None and index_elem.text:
                    anim_info["index"] = int(index_elem.text)

                # Pega FrameWidth/FrameHeight
                fw = anim.find("FrameWidth")
                fh = anim.find("FrameHeight")
                if fw is not None and fw.text:
                    anim_info["frame_width"] = int(fw.text)
                if fh is not None and fh.text:
                    anim_info["frame_height"] = int(fh.text)

                # Pega durações
                durations = anim.find("Durations")
                if durations is not None:
                    for duration in durations.findall("Duration"):
                        if duration.text:
                            anim_info["durations"].append(int(duration.text))

                # Se tem CopyOf, marca para referência
                copy_of = anim.find("CopyOf")
                if copy_of is not None and copy_of.text:
                    anim_info["copy_of"] = copy_of.text

                anims_data[anim_name] = anim_info

            return anims_data

        except Exception as e:
            print(f"[SPRITE] Erro ao carregar AnimData.xml: {e}")
            return {}

    def _create_empty_animation(self) -> Dict:
        """Cria estrutura vazia de animação"""
        empty_frames = {}
        for direction in self.DIRECTIONS:
            empty_frames[direction] = []

        return {
            "idle": empty_frames,
            "walk": empty_frames
        }

    def get_sprite(self, pokemon_id: int, shiny: bool, animation: str,
                   direction: str, frame: int = 0) -> Optional[pygame.Surface]:
        """
        Obtém um sprite específico

        Args:
            pokemon_id: ID do Pokémon
            shiny: Se é shiny
            animation: "idle" ou "walk"
            direction: Direção (down, down-right, right, etc)
            frame: Índice do frame
        """
        sprites_data = self.load_pokemon_sprites(pokemon_id, shiny)
        animations = sprites_data.get("animations", {})

        anim_frames = animations.get(animation.lower(), {})
        frames = anim_frames.get(direction, [])

        if frames and 0 <= frame < len(frames):
            return frames[frame]

        return None

    def get_animation_info(self, pokemon_id: int, shiny: bool, animation: str) -> Dict:
        """Retorna informações sobre uma animação"""
        sprites_data = self.load_pokemon_sprites(pokemon_id, shiny)
        anim_data = sprites_data.get("anim_data", {})

        # Procura a animação (case insensitive)
        for name, info in anim_data.items():
            if name.lower() == animation.lower():
                return info

        return {}


class PokemonSpriteManager:
    """
    Gerencia os sprites dos Pokémon no mapa
    """

    def __init__(self):
        base_path = Path(__file__).parent.parent.parent / "res" / "PokemonSprites" / "InMaps"
        self.loader = SpriteLoader(base_path)
        self._animation_cache = {}  # Cache de animações carregadas

    def get_inmap_animation(self, pokemon_id: int, shiny: bool = False) -> Dict:
        """
        Retorna animações no formato compatível com o sistema antigo (4 direções)
        para facilitar a migração

        Formato de retorno:
        {
            "down": [frame0, frame1, ...],
            "left": [frame0, frame1, ...],
            "right": [frame0, frame1, ...],
            "up": [frame0, frame1, ...],
            "_raw": {  # Dados brutos com 8 direções
                "animations": {...},
                "anim_data": {...}
            }
        }
        """
        cache_key = f"{pokemon_id}_{shiny}"
        if cache_key in self._animation_cache:
            return self._animation_cache[cache_key]

        sprites_data = self.loader.load_pokemon_sprites(pokemon_id, shiny)

        # Vamos criar um dicionário com 4 direções para compatibilidade
        result = {
            "down": [],
            "left": [],
            "right": [],
            "up": [],
            "_raw": sprites_data
        }

        # Obtém frames de Walk (usado para movimento)
        walk_frames = sprites_data.get("animations", {}).get("walk", {})

        # Mapeia direções de 8 para 4 - usa apenas as direções principais
        direction_mapping = {
            "down": ["down"],
            "left": ["left"],
            "right": ["right"],
            "up": ["up"]
        }

        # Para cada direção antiga, pega os frames da direção principal
        for legacy_dir, source_dirs in direction_mapping.items():
            frames = []
            for src_dir in source_dirs:
                src_frames = walk_frames.get(src_dir, [])
                frames.extend(src_frames)
            result[legacy_dir] = frames

        # Se não tem Walk, tenta Idle
        if not any(result.values()):
            idle_frames = sprites_data.get("animations", {}).get("idle", {})
            for legacy_dir, source_dirs in direction_mapping.items():
                frames = []
                for src_dir in source_dirs:
                    src_frames = idle_frames.get(src_dir, [])
                    frames.extend(src_frames)
                result[legacy_dir] = frames

        self._animation_cache[cache_key] = result
        return result

    def get_sprite_size(self, pokemon_id: int, shiny: bool = False) -> int:
        """Retorna o tamanho do sprite no mapa"""
        # Tenta obter tamanho do AnimData.xml
        sprites_data = self.loader.load_pokemon_sprites(pokemon_id, shiny)
        anim_data = sprites_data.get("anim_data", {})

        for anim_name, anim_info in anim_data.items():
            if "frame_width" in anim_info:
                return anim_info["frame_width"]

        return 32  # Tamanho padrão

    def clear_cache(self):
        """Limpa o cache de animações"""
        self._animation_cache.clear()
        self.loader.cache.clear()