# src/scenes/starter_select/starter_select_logic.py
"""
Logica da tela de selecao de inicial — apenas dados, sem pygame.draw.

Suporta 3 geracoes (Gen 1, 2 e 3) e dupla tipagem (ex: Bulbasaur = Grass/Poison).

Fornece a `type_bar_combo` — uma Surface pronta combinando as N barras de tipo
lado a lado, para que o JSON tenha apenas um widget `image` por card.
"""
import pygame
from typing import List, Dict, Optional

from src.data.pokedex import Pokedex
from src.ui.utils.type_bar_loader import type_bar_loader


class StarterSelectLogic:
    """Fonte de verdade da tela — orquestra dados da Pokedex + progresso."""

    # =============================================================
    # GERACOES SUPORTADAS
    # =============================================================
    GENERATIONS: Dict[int, List[dict]] = {
        1: [
            {"id": 1,   "name": "Bulbasaur"},   # Grass/Poison
            {"id": 4,   "name": "Charmander"},  # Fire
            {"id": 7,   "name": "Squirtle"},    # Water
        ],
        2: [
            {"id": 152, "name": "Chikorita"},   # Grass
            {"id": 155, "name": "Cyndaquil"},   # Fire
            {"id": 158, "name": "Totodile"},    # Water
        ],
        3: [
            {"id": 252, "name": "Treecko"},     # Grass
            {"id": 255, "name": "Torchic"},     # Fire
            {"id": 258, "name": "Mudkip"},      # Water
        ],
    }

    DIRECTIONS = [
        "down", "down-right", "right", "up-right",
        "up", "up-left", "left", "down-left",
    ]

    DIRECTION_CHANGE_INTERVAL = 1.5
    ANIMATION_SPEED           = 0.15
    INMAP_SCALE_MULTIPLIER    = 3.0

    # Tamanho de cada barra individual de tipo (escalado a partir do 48x16 original)
    TYPE_BAR_SIZE = (96, 32)
    TYPE_BAR_GAP  = 8

    # =============================================================
    # INIT
    # =============================================================
    def __init__(self, game):
        self.game = game
        self.player = getattr(game, "player", None)
        self.pokedex = Pokedex()

        self.current_generation: int = 1
        self.selected_index: int = 0

        self.anim_states = [
            {"direction_index": 0, "frame": 0, "timer": 0.0, "dir_timer": 0.0}
            for _ in range(3)
        ]

        self._frames_cache: Dict[str, list] = {}
        self._size_cache:   Dict[str, int]  = {}
        self._type_bar_cache: Dict[tuple, pygame.Surface] = {}

    # =============================================================
    # GERACOES
    # =============================================================
    def available_generations(self) -> List[int]:
        return sorted(self.GENERATIONS.keys())

    def starters(self) -> List[dict]:
        return self.GENERATIONS.get(self.current_generation, self.GENERATIONS[1])

    def set_generation(self, gen: int) -> bool:
        if gen not in self.GENERATIONS or gen == self.current_generation:
            return False
        self.current_generation = gen
        self.selected_index = 0
        self._frames_cache.clear()
        self._size_cache.clear()
        self._type_bar_cache.clear()
        self.reset_animations()
        return True

    def get_starter(self, index: int) -> Optional[dict]:
        starters = self.starters()
        if 0 <= index < len(starters):
            return starters[index]
        return None

    # =============================================================
    # SELECAO
    # =============================================================
    def select_index(self, index: int) -> bool:
        if 0 <= index < 3:
            self.selected_index = index
            self.reset_animation(index)
            return True
        return False

    def cycle_index(self, delta: int):
        self.selected_index = (self.selected_index + delta) % 3
        self.reset_animation(self.selected_index)

    # =============================================================
    # SPRITES / TIPOS
    # =============================================================
    def get_sprite(self, index: int):
        s = self.get_starter(index)
        if not s:
            return None
        try:
            return self.pokedex.get_sprite(s["id"], "front", shiny=False)
        except Exception as e:
            print(f"[STARTER_SELECT] get_sprite falhou: {e}")
            return None

    def get_types(self, index: int) -> List[str]:
        """Retorna TODOS os tipos do Pokemon (ex: ['grass', 'poison'] para Bulbasaur)."""
        s = self.get_starter(index)
        if not s:
            return []
        try:
            types = self.pokedex.get_types(s["id"]) or []
            return [str(t).lower().strip() for t in types if t]
        except Exception as e:
            print(f"[STARTER_SELECT] get_types falhou: {e}")
            return []

    def get_type_color(self, type_name: str):
        try:
            return self.pokedex.get_type_color(type_name) or (150, 150, 150)
        except Exception:
            return (150, 150, 150)

    # =============================================================
    # TYPE BAR COMBO  (1 ou 2 barras numa única Surface)
    # =============================================================
    def get_type_bar_combo(self, index: int) -> Optional[pygame.Surface]:
        """
        Monta uma Surface horizontal com 1 ou 2 barras de tipo.
        Suporta dupla tipagem (Bulbasaur -> Grass + Poison).
        Cacheada por tupla de tipos.
        """
        types = self.get_types(index)
        if not types:
            return None

        key = tuple(types[:2])
        cached = self._type_bar_cache.get(key)
        if cached is not None:
            return cached

        bars: List[pygame.Surface] = []
        for t in key:
            try:
                surf = type_bar_loader.get(t, size=self.TYPE_BAR_SIZE)
            except Exception as e:
                print(f"[STARTER_SELECT] type_bar '{t}' falhou: {e}")
                surf = None
            if surf is not None:
                bars.append(surf)

        if not bars:
            return None

        total_w = sum(b.get_width() for b in bars)
        total_w += self.TYPE_BAR_GAP * (len(bars) - 1)
        max_h = max(b.get_height() for b in bars)

        combo = pygame.Surface((total_w, max_h), pygame.SRCALPHA)
        x = 0
        for b in bars:
            y = (max_h - b.get_height()) // 2
            combo.blit(b, (x, y))
            x += b.get_width() + self.TYPE_BAR_GAP

        self._type_bar_cache[key] = combo
        return combo

    # =============================================================
    # ANIMACAO
    # =============================================================
    def reset_animation(self, idx: int):
        if 0 <= idx < len(self.anim_states):
            self.anim_states[idx] = {
                "direction_index": 0, "frame": 0, "timer": 0.0, "dir_timer": 0.0
            }

    def reset_animations(self):
        for i in range(3):
            self.reset_animation(i)

    def update_animations(self, dt: float):
        for idx, state in enumerate(self.anim_states):
            state["dir_timer"] += dt
            if state["dir_timer"] >= self.DIRECTION_CHANGE_INTERVAL:
                state["dir_timer"] = 0.0
                state["direction_index"] = (
                    state["direction_index"] + 1
                ) % len(self.DIRECTIONS)
                state["frame"] = 0
                state["timer"] = 0.0

            s = self.get_starter(idx)
            if not s:
                continue
            frames = self._get_frames(s["id"], state["direction_index"])
            if frames and len(frames) > 1:
                state["timer"] += dt
                if state["timer"] >= self.ANIMATION_SPEED:
                    state["timer"] = 0.0
                    state["frame"] = (state["frame"] + 1) % len(frames)
            else:
                state["frame"] = 0

    def get_inmap_surface(self, idx: int):
        s = self.get_starter(idx)
        if not s:
            return None
        state = self.anim_states[idx]
        frames = self._get_frames(s["id"], state["direction_index"])
        if not frames:
            return None
        frame_idx = min(state["frame"], len(frames) - 1)
        return frames[frame_idx]

    def get_inmap_direction_label(self, idx: int) -> str:
        state = self.anim_states[idx]
        s = self.get_starter(idx)
        frames = self._get_frames(s["id"], state["direction_index"]) if s else []
        d = self.DIRECTIONS[state["direction_index"]].upper()
        total = max(1, len(frames))
        cur = min(state["frame"] + 1, total)
        return f"{d}  {cur}/{total}"

    def _get_frames(self, pokemon_id: int, dir_index: int) -> list:
        direction = self.DIRECTIONS[dir_index]
        key = f"{pokemon_id}_{direction}"
        if key in self._frames_cache:
            return self._frames_cache[key]

        try:
            anim = self.pokedex.get_inmap_animation(pokemon_id, shiny=False)
        except Exception:
            anim = {}

        frames = anim.get(direction, [])
        if not frames:
            fallback = {
                "down-right": ["down", "right"],
                "up-right":   ["up", "right"],
                "up-left":    ["up", "left"],
                "down-left":  ["down", "left"],
            }
            if direction in fallback:
                for fb in fallback[direction]:
                    frames = anim.get(fb, [])
                    if frames:
                        break
        if not frames:
            for d in self.DIRECTIONS:
                frames = anim.get(d, [])
                if frames:
                    break

        self._frames_cache[key] = frames
        return frames

    def get_inmap_sprite_size(self, pokemon_id: int) -> int:
        key = f"{pokemon_id}_size"
        if key in self._size_cache:
            return self._size_cache[key]

        try:
            size = self.pokedex.get_map_sprite_size(pokemon_id, shiny=False)
            if size and size > 0:
                scaled = int(size * self.INMAP_SCALE_MULTIPLIER)
                self._size_cache[key] = scaled
                return scaled
        except Exception:
            pass

        for d in range(len(self.DIRECTIONS)):
            frames = self._get_frames(pokemon_id, d)
            if frames:
                f = frames[0]
                if f:
                    size = max(f.get_width(), f.get_height())
                    scaled = int(size * self.INMAP_SCALE_MULTIPLIER)
                    self._size_cache[key] = scaled
                    return scaled

        default = 32 * int(self.INMAP_SCALE_MULTIPLIER)
        self._size_cache[key] = default
        return default

    # =============================================================
    # CONFIRMAR
    # =============================================================
    def confirm(self, nickname: str = ""):
        s = self.get_starter(self.selected_index)
        if not s:
            return False, "Nenhum Pokemon selecionado."
        if not self.player:
            return False, "Player indisponivel."

        try:
            pokemon = self.player.add_starter(s["id"])
        except Exception as e:
            print(f"[STARTER_SELECT] add_starter falhou: {e}")
            return False, "Erro ao adicionar Pokemon."

        if not pokemon:
            return False, "Erro ao adicionar Pokemon."

        if nickname:
            try:
                pokemon.nickname = nickname
                pokemon.name = nickname
            except Exception:
                pass

        try:
            current = self.player.bag.items.get("pokeball", 0)
            self.player.bag.items["pokeball"] = current + 6
            if hasattr(self.player.bag, "_update_filtered_items"):
                self.player.bag._update_filtered_items()
        except Exception as e:
            print(f"[STARTER_SELECT] Erro itens iniciais: {e}")

        try:
            self.player.has_chosen_starter = True
        except Exception:
            pass

        try:
            from src.managers.save_manager import save_manager
            slot = save_manager.current_save_file
        except Exception:
            slot = None

        if not slot:
            return False, "Nenhum slot de save ativo."

        try:
            self.player.save_game(slot)
        except Exception as e:
            print(f"[STARTER_SELECT] Erro save: {e}")
            return False, "Erro ao salvar progresso."

        return True, pokemon