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
        self._avatar_cache: Dict[tuple, pygame.Surface] = {}

    # ================================================================
    # LISTAGEM
    # ================================================================
    def list_slots(self) -> List[dict]:
        """
        Retorna a lista dos 3 slots com dados prontos pra UI.

        Fonte da verdade dos dados de cada slot: o PRÓPRIO ARQUIVO do save,
        lido em `_read_slot_header()` — assim não dependemos do que o
        `save_manager.list_saves()` expõe (que historicamente omitia
        `play_time`, `team_size`, etc).
        """
        raw = save_manager.list_saves()
        out = []
        for entry in raw:
            slot_num = entry.get("slot", 1)
            is_empty = entry.get("empty", False)
            is_error = entry.get("error", False)
            is_current = (slot_num == save_manager.current_save_file)

            # Lê o cabeçalho direto do arquivo
            header = {}
            if not is_empty and not is_error:
                header = self._read_slot_header(slot_num)

            info = {
                "slot": slot_num,
                "is_empty": is_empty,
                "is_error": is_error,
                "is_current": is_current,
                "name": header.get("save_name") or entry.get("name") or f"Save {slot_num}",
                "chapter": int(header.get("chapter", entry.get("chapter", 1)) or 1),
                "phase":   int(header.get("phase", entry.get("phase", 1)) or 1),
                "pokemon_count": int(header.get("pokemon_count",
                                                entry.get("pokemon_count", 0)) or 0),
                "team_size":     int(header.get("team_size",
                                                entry.get("team_size", 0)) or 0),
                "play_time":     float(header.get("play_time",
                                                  entry.get("play_time", 0)) or 0.0),
                "last_save":     header.get("last_save") or entry.get("last_save"),
                "avatar": self._avatar_for(
                    slot_num, header.get("appearance"), is_empty, is_error),
                "ghost": is_empty or is_error,
            }
            out.append(info)
        return out

    # ================================================================
    # LEITURA LEVE DO ARQUIVO
    # ================================================================
    def _read_slot_header(self, slot_num: int) -> dict:
        """
        Abre o arquivo do save e extrai SOMENTE campos leves:
          - player.total_playtime
          - player.profile_customization.appearance
          - player.caught_pokemon (contagem)
          - player.team (contagem)
          - meta.save_name
          - meta.last_save
          - game_state.current_chapter / current_phase
        Não carrega o save inteiro. Não usa o save_manager.
        """
        filepath = os.path.join(save_manager.save_dir, f"save_{slot_num}.json")
        if not os.path.exists(filepath):
            return {}
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            print(f"[SLOT] Erro lendo header do slot {slot_num}: {e}")
            return {}

        player = data.get("player", {}) or {}
        meta   = data.get("meta", {}) or {}
        state  = data.get("game_state", {}) or {}
        pc     = player.get("profile_customization", {}) or {}
        app    = pc.get("appearance")

        # `caught_pokemon` pode ser set serializado como lista
        caught = player.get("caught_pokemon", []) or []
        try:
            pokemon_count = len(caught)
        except TypeError:
            pokemon_count = 0

        team = player.get("team", []) or []
        try:
            team_size = len(team)
        except TypeError:
            team_size = 0

        return {
            "appearance": app if isinstance(app, dict) else None,
            "play_time": float(player.get("total_playtime", 0) or 0.0),
            "save_name": meta.get("save_name"),
            "last_save": meta.get("last_save"),
            "chapter": int(state.get("current_chapter", 1) or 1),
            "phase":   int(state.get("current_phase", 1) or 1),
            "pokemon_count": pokemon_count,
            "team_size": team_size,
        }

    # ================================================================
    # AVATAR
    # ================================================================
    def _avatar_for(self, slot_num: int, appearance: Optional[dict],
                    is_empty: bool, is_error: bool) -> Optional[pygame.Surface]:
        """
        Devolve a surface do avatar para o slot.

        Cache inclui a ASSINATURA da aparência, então trocar de roupa e
        voltar pra tela de slots já pega o sprite novo automaticamente.
        """
        # Assinatura da aparência (evita cache "grudento")
        sig = None
        if appearance:
            try:
                sig = tuple(sorted((k, str(v)) for k, v in appearance.items()))
            except Exception:
                sig = None

        key = (slot_num, is_empty, is_error, sig)
        if key in self._avatar_cache:
            return self._avatar_cache[key]

        is_ghost = appearance is None
        use_appearance = appearance if appearance else DEFAULT_APPEARANCE

        surf = self._render_avatar(use_appearance, AVATAR_TARGET)

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
        """
        Mesma formatação usada no ProfileLogic.playtime_text():
            "04h 12m"
        """
        try:
            t = int(seconds or 0)
        except Exception:
            t = 0
        return f"{t // 3600:02d}h {(t % 3600) // 60:02d}m"

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