# src/scenes/pokedex_scene/pokedex_logic.py
"""
Lógica da Pokédex — estado, filtros, animação InMap.
Sem Pygame na renderização; só orquestra dados.
"""
from pathlib import Path
from typing import List, Optional
import pygame

from src.data.pokedex import Pokedex
from src.scenes.pokedex_scene.utils.constants import (
    FILTERS, REGIONS, REGION_RANGES, TYPE_COLORS,
)


REGION_LABELS = {
    'all':   "TODAS AS REGIOES",
    'kanto': "KANTO (GEN 1)",
    'johto': "JOHTO (GEN 2)",
    'hoenn': "HOENN (GEN 3)",
}

STATUS_LABELS = {
    'all':        "Todos",
    'caught':     "Capturados",
    'seen':       "Vistos",
    'not_caught': "Nao capturados",
    'unseen':     "Nao vistos",
}

STATUS_LABEL_TO_KEY = {v: k for k, v in STATUS_LABELS.items()}
REGION_LABEL_TO_KEY = {v: k for k, v in REGION_LABELS.items()}


class PokedexLogic:
    DIRECTIONS = [
        "down", "down-right", "right", "up-right",
        "up", "up-left", "left", "down-left",
    ]

    DIRECTION_SHORT = [
        "DOWN", "D-R", "RIGHT", "U-R", "UP", "U-L", "LEFT", "D-L",
    ]

    # Fallback para diagonais quando a animação não tem a direção exata
    DIRECTION_FALLBACK = {
        "down-right": ["down", "right"],
        "up-right":   ["up", "right"],
        "up-left":    ["up", "left"],
        "down-left":  ["down", "left"],
    }

    DIRECTION_INTERVAL = 1.5
    FRAME_INTERVAL = 0.15

    def __init__(self, game):
        self.game = game
        self.player = game.player
        self.pokedex = Pokedex()

        self.region = REGIONS['ALL']
        self.filter_type = FILTERS['ALL']
        self.search_text = ""
        self.selected_id: Optional[int] = None
        self.show_inmap = False

        # animação
        self.inmap_frame = 0
        self.inmap_timer = 0.0
        self.direction_index = 0
        self.direction_timer = 0.0

        # listas e caches
        self.filtered: List[dict] = []
        self._portrait_cache: dict = {}
        self._unknown_portrait: Optional[pygame.Surface] = None
        self._front_cache: dict = {}

        self.refresh()

    # -----------------------------------------------------------------
    # Filtros / Refresh
    # -----------------------------------------------------------------
    def refresh(self):
        all_ids = sorted(self.pokedex.pokemon_data.keys())
        pdata = self.pokedex.pokemon_data

        # Região
        if self.region != 'all':
            rng = REGION_RANGES.get(self.region)
            if rng:
                lo, hi = rng
                all_ids = [pid for pid in all_ids if lo <= pid <= hi]

        result = []
        for pid in all_ids:
            is_caught = pid in self.player.caught_pokemon
            is_seen = pid in self.player.seen_pokemon

            if self.filter_type == 'caught' and not is_caught:
                continue
            if self.filter_type == 'seen' and not is_seen:
                continue
            if self.filter_type == 'not_caught' and not (is_seen and not is_caught):
                continue
            if self.filter_type == 'unseen' and (is_seen or is_caught):
                continue

            name = pdata[pid].get("name", f"Pokemon {pid}")
            if self.search_text:
                q = self.search_text.lower()
                if q not in name.lower() and q != str(pid):
                    continue

            result.append({
                "id": pid,
                "data": pdata[pid],
                "name": name,
                "is_caught": is_caught,
                "is_seen": is_seen,
            })

        self.filtered = result

        # Ajusta seleção
        ids = {r["id"] for r in self.filtered}
        if self.selected_id not in ids:
            self.selected_id = self.filtered[0]["id"] if self.filtered else None
        self._reset_animation()

    # -----------------------------------------------------------------
    # Getters de estado (labels)
    # -----------------------------------------------------------------
    def get_region_labels(self):
        return list(REGION_LABELS.values())

    def get_region_label(self):
        return REGION_LABELS[self.region]

    def get_status_labels(self):
        return list(STATUS_LABELS.values())

    def get_status_label(self):
        return STATUS_LABELS[self.filter_type]

    def set_region_label(self, label: str):
        self.region = REGION_LABEL_TO_KEY.get(label, REGIONS['ALL'])
        self.refresh()

    def set_status_label(self, label: str):
        self.filter_type = STATUS_LABEL_TO_KEY.get(label, FILTERS['ALL'])
        self.refresh()

    def set_search(self, text: str):
        self.search_text = (text or "").strip()
        self.refresh()

    def select(self, pokemon_id: int):
        if pokemon_id != self.selected_id:
            self.selected_id = pokemon_id
            self._reset_animation()

    def next_pokemon(self):
        if not self.filtered:
            return
        ids = [r["id"] for r in self.filtered]
        if self.selected_id not in ids:
            self.selected_id = ids[0]
        else:
            i = ids.index(self.selected_id)
            self.selected_id = ids[(i + 1) % len(ids)]
        self._reset_animation()

    def prev_pokemon(self):
        if not self.filtered:
            return
        ids = [r["id"] for r in self.filtered]
        if self.selected_id not in ids:
            self.selected_id = ids[0]
        else:
            i = ids.index(self.selected_id)
            self.selected_id = ids[(i - 1) % len(ids)]
        self._reset_animation()

    def toggle_view(self):
        self.show_inmap = not self.show_inmap
        self._reset_animation()

    def _reset_animation(self):
        self.inmap_frame = 0
        self.inmap_timer = 0.0
        self.direction_index = 0
        self.direction_timer = 0.0

    # -----------------------------------------------------------------
    # Estatísticas
    # -----------------------------------------------------------------
    @property
    def total_pokemon(self):
        return len(self.pokedex.pokemon_data)

    @property
    def total_seen(self):
        return len(self.player.seen_pokemon)

    @property
    def total_caught(self):
        return len(self.player.caught_pokemon)

    # -----------------------------------------------------------------
    # Cards da lista
    # -----------------------------------------------------------------
    def item_dict(self, entry: dict) -> dict:
        pid = entry["id"]
        is_caught = entry["is_caught"]
        is_seen = entry["is_seen"]
        revealed = is_caught or is_seen

        # ===== Tipos primário + secundário =====
        type_key = "undefined"
        type_key_2 = None
        if revealed:
            raw_types = entry["data"].get("types", [])
            if len(raw_types) >= 1:
                type_key = raw_types[0].lower()
            if len(raw_types) >= 2:
                type_key_2 = raw_types[1].lower()

        if is_caught:
            bg = "#1E2E1E"
            border = "#64DC64"
            name_color = "#64DC64"
            status_text = "CAPTURADO"
            status_color = "#64DC64"
            display_name = entry["name"]
        elif is_seen:
            bg = "#1E2436"
            border = "#3A4560"
            name_color = "#C0C5D0"
            status_text = "VISTO"
            status_color = "#8A8F9A"
            display_name = entry["name"]
        else:
            bg = "#15171E"
            border = "#2A2E38"
            name_color = "#505560"
            status_text = "DESCONHECIDO"
            status_color = "#505560"
            display_name = "????"

        if pid == self.selected_id:
            bg = "#2A3A5A"
            border = "#F8B030"

        return {
            "id": pid,
            "portrait": self._get_portrait(pid, revealed),
            "display_id": f"#{pid:03d}",
            "display_name": display_name,
            "status_text": status_text,
            "status_color": status_color,
            "name_color": name_color,
            "bg_color": bg,
            "border_color": border,
            "is_selected": pid == self.selected_id,
            "type_key": type_key,
            "type_key_2": type_key_2,
        }

    # -----------------------------------------------------------------
    # Sprites / portraits
    # -----------------------------------------------------------------
    def _get_unknown_portrait(self) -> pygame.Surface:
        if self._unknown_portrait is None:
            surf = pygame.Surface((60, 60), pygame.SRCALPHA)
            surf.fill((26, 30, 40))
            pygame.draw.rect(surf, (46, 54, 80), (0, 0, 60, 60), 2)
            font = pygame.font.Font(None, 30)
            txt = font.render("?", True, (80, 88, 110))
            surf.blit(txt, txt.get_rect(center=(30, 30)))
            self._unknown_portrait = surf
        return self._unknown_portrait

    def _get_portrait(self, pid: int, revealed: bool) -> pygame.Surface:
        if not revealed:
            return self._get_unknown_portrait()
        if pid in self._portrait_cache:
            return self._portrait_cache[pid]

        portrait = self.pokedex.get_portrait(pid, "normal", shiny=False)
        if portrait is None:
            portrait = self.pokedex.get_sprite(pid, "front", shiny=False)
        if portrait is not None:
            portrait = pygame.transform.scale(portrait, (60, 60))
        else:
            portrait = self._get_unknown_portrait()

        self._portrait_cache[pid] = portrait
        return portrait

    # -----------------------------------------------------------------
    # InMap — obtenção de frames com fallback para diagonais
    # -----------------------------------------------------------------
    def _get_frames_for_direction(self, anim: dict, direction: str) -> list:
        """Retorna frames para uma direção, com fallback inteligente."""
        frames = anim.get(direction, [])
        if frames:
            return frames

        # Fallback para diagonais (ex: down-right -> down ou right)
        fb = self.DIRECTION_FALLBACK.get(direction)
        if fb:
            for alt in fb:
                frames = anim.get(alt, [])
                if frames:
                    return frames

        # Último recurso: qualquer direção com frames
        for d in self.DIRECTIONS:
            frames = anim.get(d, [])
            if frames:
                return frames
        return []

    def _get_inmap_frame(self, pid: int):
        anim = self.pokedex.get_inmap_animation(pid, shiny=False)
        direction = self.DIRECTIONS[self.direction_index]
        frames = self._get_frames_for_direction(anim, direction)
        if not frames:
            return None
        return frames[self.inmap_frame % len(frames)]

    def _get_inmap_frame_count(self, pid: int) -> int:
        anim = self.pokedex.get_inmap_animation(pid, shiny=False)
        direction = self.DIRECTIONS[self.direction_index]
        return len(self._get_frames_for_direction(anim, direction))

    # -----------------------------------------------------------------
    # Propriedades de UI da animação
    # -----------------------------------------------------------------
    @property
    def direction_label(self) -> str:
        return self.DIRECTION_SHORT[self.direction_index]

    @property
    def direction_progress(self) -> float:
        if self.DIRECTION_INTERVAL <= 0:
            return 0.0
        return max(0.0, min(1.0, self.direction_timer / self.DIRECTION_INTERVAL))

    @property
    def frame_progress(self) -> float:
        if self.FRAME_INTERVAL <= 0:
            return 0.0
        return max(0.0, min(1.0, self.inmap_timer / self.FRAME_INTERVAL))

    def get_frame_label(self) -> str:
        entry = self.get_selected_entry()
        if entry is None:
            return ""
        total = self._get_inmap_frame_count(entry["id"])
        if total <= 0:
            return ""
        return f"{self.inmap_frame + 1}/{total}"

    # -----------------------------------------------------------------
    # Detail — dados do Pokémon selecionado
    # -----------------------------------------------------------------
    def get_selected_entry(self) -> Optional[dict]:
        for e in self.filtered:
            if e["id"] == self.selected_id:
                return e
        return None

    def get_detail_state(self) -> dict:
        entry = self.get_selected_entry()
        if entry is None:
            return {
                "valid": False,
                "sprite": None,
                "sprite_info": "",
                "name": "-",
                "id_str": "",
                "status_text": "",
                "status_color": (74, 128, 232),
                "types": [],
                "stats": [],
                "caught": False,
                "seen": False,
                "show_inmap": self.show_inmap,
                "counter": "0 / 0",
                "direction_label": "",
                "direction_progress": 0.0,
                "frame_progress": 0.0,
                "frame_label": "",
            }

        pid = entry["id"]
        data = entry["data"]
        is_caught = entry["is_caught"]
        is_seen = entry["is_seen"]
        revealed = is_caught or is_seen

        # nome
        display_name = data.get("name", f"Pokemon {pid}") if revealed else "????"
        name_str = f"#{pid:03d}  {display_name}"

        # status
        if is_caught:
            status_text = "CAPTURADO"
            status_color = (100, 220, 100)
        elif is_seen:
            status_text = "VISTO"
            status_color = (74, 128, 232)
        else:
            status_text = "DESCONHECIDO"
            status_color = (80, 85, 96)

        # sprite
        sprite = None
        sprite_info = ""
        if revealed:
            if self.show_inmap:
                sprite = self._get_inmap_frame(pid)
                try:
                    base = self.pokedex.get_map_sprite_size(pid, shiny=False)
                    sprite_info = f"InMap  {base}x{base}"
                except Exception:
                    sprite_info = "InMap"
            else:
                sprite = self._get_front_sprite(pid)
        else:
            sprite = self._get_unknown_portrait()

        # types
        types = []
        if revealed:
            raw_types = data.get("types", ["normal"])
            for t in raw_types[:2]:
                key = t.lower()
                color = TYPE_COLORS.get(key, (128, 128, 128))
                types.append({
                    "key": key,  # <- chave limpa p/ o loader
                    "name": t.upper(),  # legado (badge/texto)
                    "color": color,  # legado (fallback de cor)
                })

        # stats
        stats = []
        if is_caught:
            base_stats = data.get("base_stats", {}) or {}
            order = [
                ("hp", "HP"),
                ("attack", "ATK"),
                ("defense", "DEF"),
                ("special_attack", "SPA"),
                ("special_defense", "SPD"),
                ("speed", "SPE"),
            ]
            for key, label in order:
                if key in base_stats:
                    stats.append({
                        "label": label,
                        "value": base_stats[key],
                        "max": 200,
                    })

        # contador
        all_ids = [r["id"] for r in self.filtered]
        if pid in all_ids:
            counter = f"{all_ids.index(pid) + 1} / {len(all_ids)}"
        else:
            counter = f"- / {len(all_ids)}"

        return {
            "valid": True,
            "sprite": sprite,
            "sprite_info": sprite_info,
            "name": name_str,
            "id_str": f"#{pid:03d}",
            "status_text": status_text,
            "status_color": status_color,
            "types": types,
            "stats": stats,
            "caught": is_caught,
            "seen": is_seen,
            "show_inmap": self.show_inmap,
            "counter": counter,
            "data": data,
            "direction_label":    self.direction_label,
            "direction_progress": self.direction_progress,
            "frame_progress":     self.frame_progress,
            "frame_label":        self.get_frame_label() if self.show_inmap else "",
        }

    def _get_front_sprite(self, pid: int) -> Optional[pygame.Surface]:
        if pid in self._front_cache:
            return self._front_cache[pid]
        spr = self.pokedex.get_sprite(pid, "front", shiny=False)
        self._front_cache[pid] = spr
        return spr

    # -----------------------------------------------------------------
    # Animação
    # -----------------------------------------------------------------
    def update_animation(self, dt: float):
        if not self.show_inmap:
            return

        self.direction_timer += dt
        if self.direction_timer >= self.DIRECTION_INTERVAL:
            self.direction_timer = 0.0
            self.direction_index = (self.direction_index + 1) % len(self.DIRECTIONS)
            self.inmap_frame = 0
            self.inmap_timer = 0.0

        self.inmap_timer += dt
        if self.inmap_timer >= self.FRAME_INTERVAL:
            self.inmap_timer = 0.0
            self.inmap_frame += 1

    def reset_animation(self):
        self._reset_animation()