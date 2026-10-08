# src/scenes/achievement_scene/achievement_logic.py
"""
Lógica da tela de conquistas — estado + ações + cache de card art.
Não desenha nada. A cena lê daqui.
"""
import pygame
from typing import Dict, List, Optional

from src.data.achievement_data import Achievement, AchievementRarity
from src.config.regions import (
    RegionCatalog, DEFAULT_REGION_ID, parse_phase_id,
)
from src.config.paths import RES_PATH


class AchievementLogic:
    # ===== Caminho dos cards =====
    CARD_DIR       = RES_PATH / "PokemonSprites" / "UI" / "achievementCard"
    CARD_PREFIX    = "achievement_card_"
    CARD_TEMPLATE  = "achievement_card_background_template"

    # ===== Tabelas fixas =====
    RARITY_ORDER = {
        AchievementRarity.COMMON:    0,
        AchievementRarity.UNCOMMON:  1,
        AchievementRarity.RARE:      2,
        AchievementRarity.EPIC:      3,
        AchievementRarity.LEGENDARY: 4,
    }
    RARITY_NAMES = {
        AchievementRarity.COMMON:    "COMUM",
        AchievementRarity.UNCOMMON:  "INCOMUM",
        AchievementRarity.RARE:      "RARO",
        AchievementRarity.EPIC:      "EPICO",
        AchievementRarity.LEGENDARY: "LENDARIO",
    }
    RARITY_COLORS = {
        AchievementRarity.COMMON:    (150, 150, 150),
        AchievementRarity.UNCOMMON:  (100, 200, 100),
        AchievementRarity.RARE:      (100, 150, 255),
        AchievementRarity.EPIC:      (200, 100, 255),
        AchievementRarity.LEGENDARY: (255, 215, 0),
    }

    # =================================================================
    def __init__(self, game):
        self.game = game
        self.player = game.player
        self.manager = self.player.achievement_manager

        # Filtros
        self.rarity_index = 0
        self.region_index = 0
        self.search_text = ""

        # Seleção
        self.selected: Optional[Achievement] = None

        # Cache
        self._card_cache: Dict[str, Optional[pygame.Surface]] = {}

        # Opções
        self.rarity_options = [
            {"id": None,                        "label": "Todas"},
            {"id": AchievementRarity.COMMON,    "label": "Comum"},
            {"id": AchievementRarity.UNCOMMON,  "label": "Incomum"},
            {"id": AchievementRarity.RARE,      "label": "Raro"},
            {"id": AchievementRarity.EPIC,      "label": "Epico"},
            {"id": AchievementRarity.LEGENDARY, "label": "Lendario"},
        ]
        self.region_options: List[dict] = []
        self._build_region_options()

        self.filtered: List[Achievement] = []
        self.refresh()

    # -----------------------------------------------------------------
    # Regiões
    # -----------------------------------------------------------------
    def _build_region_options(self):
        self.region_options = [{"id": None, "label": "Todas"}]
        used = set()

        raw = getattr(self.player, "achievements", {}).get("unlocked", []) or []
        for entry in raw:
            s = str(entry)
            parts = s.split(":")
            if len(parts) == 2:
                try:
                    used.add(int(parts[0]))
                except (TypeError, ValueError):
                    pass

        try:
            used.add(self.manager.get_current_region())
        except Exception:
            pass

        if not used:
            used.add(DEFAULT_REGION_ID)

        for rid in sorted(used):
            self.region_options.append({
                "id": rid,
                "label": RegionCatalog.get_name(rid),
            })

        if self.region_index >= len(self.region_options):
            self.region_index = 0

    def get_rarity_labels(self):
        return [o["label"] for o in self.rarity_options]

    def get_region_labels(self):
        return [o["label"] for o in self.region_options]

    # -----------------------------------------------------------------
    # Filtros
    # -----------------------------------------------------------------
    def refresh(self):
        rarity_filter = self.rarity_options[self.rarity_index]["id"]
        region_filter = self.region_options[self.region_index]["id"]

        if region_filter is None:
            regions = [o["id"] for o in self.region_options
                       if o["id"] is not None]
            if not regions:
                regions = [self.manager.get_current_region()]
        else:
            regions = [region_filter]

        all_achs: List[Achievement] = []
        for rid in regions:
            all_achs.extend(self.manager.get_all_achievements(region_id=rid))

        if rarity_filter is not None:
            all_achs = [a for a in all_achs if a.rarity == rarity_filter]

        if self.search_text.strip():
            q = self.search_text.strip().lower()
            all_achs = [
                a for a in all_achs
                if q in a.title.lower() or q in a.description.lower()
            ]

        # Deduplica
        seen = set()
        unique: List[Achievement] = []
        for a in all_achs:
            key = (getattr(a, "region_id", 1), a.id)
            if key in seen:
                continue
            seen.add(key)
            unique.append(a)

        unique.sort(key=lambda a: (
            0 if a.unlocked else 1,
            self.RARITY_ORDER.get(a.rarity, 0),
        ))
        self.filtered = unique

        # Limpa seleção se ela saiu da lista
        if self.selected is not None:
            for a in unique:
                if (a.id == self.selected.id and
                    getattr(a, "region_id", 1) ==
                    getattr(self.selected, "region_id", 1)):
                    self.selected = a
                    return
            self.selected = None

    def set_rarity_index(self, idx: int):
        self.rarity_index = int(idx)
        self.refresh()

    def set_region_index(self, idx: int):
        self.region_index = int(idx)
        self.refresh()

    def set_search(self, text: str):
        self.search_text = text or ""
        self.refresh()

    def select(self, achievement: Optional[Achievement]):
        self.selected = achievement

    # -----------------------------------------------------------------
    # Card image
    # -----------------------------------------------------------------
    def get_card_surface(self, ach: Achievement) -> Optional[pygame.Surface]:
        """Retorna Surface do card específico; cai no template se não existir."""
        if ach is None:
            return None
        aid = ach.id
        if aid in self._card_cache:
            return self._card_cache[aid]

        surf: Optional[pygame.Surface] = None

        # 1) Específico: achievement_card_{id}.png
        specific = self.CARD_DIR / f"{self.CARD_PREFIX}{aid}.png"
        if specific.exists():
            try:
                surf = pygame.image.load(str(specific)).convert_alpha()
            except Exception as e:
                print(f"[Achievement] falha '{specific}': {e}")

        # 2) Fallback: template
        if surf is None:
            fallback = self.CARD_DIR / f"{self.CARD_TEMPLATE}.png"
            if fallback.exists():
                try:
                    surf = pygame.image.load(str(fallback)).convert_alpha()
                except Exception as e:
                    print(f"[Achievement] fallback falhou: {e}")

        self._card_cache[aid] = surf
        return surf

    # -----------------------------------------------------------------
    # Helpers
    # -----------------------------------------------------------------
    def format_phase(self, phase_id) -> str:
        if not phase_id:
            return ""
        s = str(phase_id).strip()
        if s.lower() in ("none", ""):
            return ""
        try:
            r, c, p = parse_phase_id(s)
            return f"{RegionCatalog.get_name(r)} - Cap {c} Fase {p}"
        except Exception:
            return s

    def get_reward_list(self, ach: Achievement) -> list:
        """Lista de (kind, value) para render do grid."""
        out = []
        if ach is None:
            return out
        r = ach.rewards or {}
        if "gold" in r:
            out.append(("gold", r["gold"]))
        if "xp" in r:
            out.append(("xp", r["xp"]))
        if "items" in r:
            for iid, qty in r["items"].items():
                out.append(("item", (iid, qty)))
        if "pokemon" in r:
            out.append(("pokemon", r["pokemon"]))
        return out

    def build_meta_text(self, ach: Achievement) -> str:
        if ach is None:
            return ""
        if ach.unlocked and ach.unlocked_at:
            phase = self.format_phase(ach.unlocked_phase)
            if phase:
                return f"Obtida em {ach.unlocked_at}\n{phase}"
            return f"Obtida em {ach.unlocked_at}"
        return ""