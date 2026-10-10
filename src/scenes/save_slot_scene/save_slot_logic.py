# src/scenes/save_slot_scene/save_slot_logic.py
"""Lógica da tela de seleção de save — sem render."""
import os
import json
import pygame
from datetime import datetime
from typing import Optional, Dict, List

from src.managers.save_manager import save_manager
from src.config.progress import progress_manager


# Aparência padrão (mesma que o Player cria num save novo)
DEFAULT_APPEARANCE = {
    "skin": "skin_1",
    "eyes": "eyes_1",
    "hair": None,
    "torso": None,
    "pants": None,
    "hat": None,
}

AVATAR_TARGET = 192  # tamanho do canvas do avatar em px (design 1280x720)


class SaveSlotLogic:
    def __init__(self, game):
        self.game = game
        self.player = game.player
        self._avatar_cache: Dict[int, pygame.Surface] = {}

    # ================================================================
    # LISTAGEM
    # ================================================================
    def list_slots(self) -> List[dict]:
        """Retorna a lista dos 3 slots com dados prontos pra UI."""
        raw = save_manager.list_saves()
        out = []
        for entry in raw:
            slot_num = entry.get("slot", 1)
            is_empty = entry.get("empty", False)
            is_error = entry.get("error", False)
            is_current = (slot_num == save_manager.current_save_file)

            info = {
                "slot": slot_num,
                "is_empty": is_empty,
                "is_error": is_error,
                "is_current": is_current,
                "name": entry.get("name", f"Save {slot_num}"),
                "chapter": entry.get("chapter", 1),
                "phase": entry.get("phase", 1),
                "pokemon_count": entry.get("pokemon_count", 0),
                "team_size": entry.get("team_size", 0),
                "play_time": entry.get("play_time", 0),
                "last_save": entry.get("last_save"),
                "avatar": self._build_avatar(slot_num, is_empty, is_error),
                "ghost": is_empty or is_error,
            }
            out.append(info)
        return out

    # ================================================================
    # AVATAR
    # ================================================================
    def _read_appearance(self, slot_num: int) -> Optional[dict]:
        """Lê SÓ o campo appearance do arquivo do slot (sem carregar o save)."""
        filepath = os.path.join(save_manager.save_dir, f"save_{slot_num}.json")
        if not os.path.exists(filepath):
            return None
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            app = (data.get("player", {})
                       .get("profile_customization", {})
                       .get("appearance"))
            if isinstance(app, dict):
                merged = dict(DEFAULT_APPEARANCE)
                merged.update(app)
                return merged
            return None
        except Exception as e:
            print(f"[SLOT] Erro lendo aparência do slot {slot_num}: {e}")
            return None

    def _build_avatar(self, slot_num: int, is_empty: bool, is_error: bool) -> Optional[pygame.Surface]:
        """Retorna a surface do avatar (real ou fantasma). Cacheado por slot."""
        key = (slot_num, is_empty, is_error)
        if key in self._avatar_cache:
            return self._avatar_cache[key]

        appearance = None
        if not is_empty and not is_error:
            appearance = self._read_appearance(slot_num)

        is_ghost = appearance is None
        if is_ghost:
            appearance = DEFAULT_APPEARANCE

        surf = self._render_avatar(appearance, AVATAR_TARGET)

        # Slot vazio → aplica overlay escuro (fantasma)
        if is_ghost and surf is not None:
            ghost = surf.copy()
            overlay = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 170))
            ghost.blit(overlay, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
            surf = ghost

        self._avatar_cache[key] = surf
        return surf

    @staticmethod
    def _render_avatar(appearance: dict, target: int) -> Optional[pygame.Surface]:
        """Replica exatamente o que o ProfileLogic.avatar_surface() faz."""
        try:
            from src.utils.player_sprite import render_player_sprite

            base = render_player_sprite(appearance, size=(32, 32))

            n = max(1, target // 32)
            scaled_size = 32 * n
            scaled = pygame.transform.scale(base, (scaled_size, scaled_size))

            canvas = pygame.Surface((target, target), pygame.SRCALPHA)
            ox = (target - scaled_size) // 2
            oy = (target - scaled_size) // 2
            canvas.blit(scaled, (ox, oy))
            return canvas
        except Exception as e:
            print(f"[SLOT] Erro ao renderizar avatar: {e}")
            return None

    def clear_cache(self):
        self._avatar_cache.clear()

    # ================================================================
    # FORMATAÇÃO
    # ================================================================
    @staticmethod
    def format_play_time(seconds) -> str:
        try:
            t = int(seconds or 0)
        except Exception:
            t = 0
        return f"{t // 3600}h {(t % 3600) // 60:02d}m"

    @staticmethod
    def format_last_save(iso_str) -> str:
        if not iso_str:
            return "-"
        try:
            dt = datetime.fromisoformat(iso_str)
            return dt.strftime("%d/%m/%y %H:%M")
        except Exception:
            return "?"

    def info_line_chapter(self, info: dict) -> str:
        return f"Capitulo:  {info['chapter']}-{info['phase']}"

    def info_line_pokemon(self, info: dict) -> str:
        return f"Pokemon:  {info['pokemon_count']}"

    def info_line_team(self, info: dict) -> str:
        return f"Time:  {info['team_size']}/6"

    def info_line_playtime(self, info: dict) -> str:
        return f"Tempo:  {self.format_play_time(info['play_time'])}"

    def info_line_date(self, info: dict) -> str:
        return f"Salvo em  {self.format_last_save(info['last_save'])}"

    # ================================================================
    # AÇÕES
    # ================================================================
    def load_slot(self, slot_num: int) -> bool:
        print(f"[SLOT] Carregando slot {slot_num}")
        if not self.game.load_save_slot(slot_num):
            return False
        self._enter_game()
        return True

    def new_game(self, slot_num: int):
        print(f"[SLOT] Novo jogo no slot {slot_num}")
        self.game.start_new_game_in_slot(slot_num)

        from src.scenes.starter_select_scene.starter_select_scene import StarterSelectScene
        scene = StarterSelectScene(self.game)
        self.game.starter_select_scene = scene
        self.game.current_scene = scene

    def delete_slot(self, slot_num: int) -> bool:
        print(f"[SLOT] Deletando slot {slot_num}")
        return save_manager.delete_save(slot_num)

    def _enter_game(self):
        has_starter = getattr(self.player, 'has_chosen_starter', False)
        if has_starter:
            progress_manager.reload_progress()
            from src.scenes.phase_selector.phase_select_scene import PhaseSelectScene
            self.game.current_scene = PhaseSelectScene(self.game)
        else:
            from src.scenes.starter_select_scene.starter_select_scene import StarterSelectScene
            scene = StarterSelectScene(self.game)
            self.game.starter_select_scene = scene
            self.game.current_scene = scene