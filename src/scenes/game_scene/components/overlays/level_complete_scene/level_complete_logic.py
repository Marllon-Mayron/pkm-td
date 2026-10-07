# src/scenes/game_scene/components/overlays/level_complete_scene/level_complete_logic.py
"""
Lógica do overlay Fase Completa — fiel ao PhaseCompleteOverlay antigo.

Exibe:
  - Título, nome da fase
  - 3 cards: OURO / EXP / ITENS
  - Grade de itens recebidos (com quantidade)
  - Estrelas
  - Próxima fase
  - Grade de Pokémon da fase
"""
from collections import Counter

from src.config.phase_catalog import phase_catalog
from src.config.progress import progress_manager
from src.data.pokedex import Pokedex
from src.scenes.game_scene.components.phase_loader import phase_loader


class LevelCompleteLogic:
    # =================================================================
    def __init__(self, game, game_scene, stats=None):
        self.game = game
        self.game_scene = game_scene

        s = dict(stats or {})
        self.phase_info = game_scene.phase_info
        self.phase_id = game_scene.phase_id

        data = getattr(game_scene, "phase_complete_data", {}) or {}
        self.gold_total    = int(data.get("gold_total", 0))
        self.total_xp      = int(data.get("total_xp", 0))
        self.bonus_amount  = int(data.get("bonus_amount", 0))
        self.stars         = int(data.get("stars", 0))
        self.earned_items  = list(data.get("earned_items", []))

        # Agrupa itens por id
        self.item_counts = Counter(self.earned_items)

        # Nível do jogador (derivado do score/XP)
        try:
            self.player_level, self.xp_in_level, self.xp_span, _ = (
                game.player.get_level_progress()
            )
        except Exception:
            self.player_level = 1
            self.xp_in_level = 0
            self.xp_span = 100

        # --- Próxima fase ---
        self.next_phase = progress_manager.get_next_phase(self.phase_id)
        self.has_next_phase = self.next_phase is not None

        # --- Pokémon da fase ---
        try:
            ids = phase_loader.get_all_pokemon_ids_from_phase()
            self.pokemon_ids = sorted(ids)
        except Exception:
            self.pokemon_ids = []

        self.pokedex = Pokedex()

        # --- Snapshot para retry ---
        self.placement_snapshot = self._capture_placement_snapshot()

    # =================================================================
    def _capture_placement_snapshot(self):
        snapshot = []
        pm = getattr(self.game_scene, "placement_manager", None)
        if not pm:
            return snapshot
        tile_size = getattr(pm, "tile_size", 16)
        for pokemon in pm.placed_pokemon:
            if not getattr(pokemon, "is_placed", False):
                continue
            tile_x = getattr(pokemon, "placed_tile_x", None)
            tile_y = getattr(pokemon, "placed_tile_y", None)
            if tile_x is None:
                tile_x = int(pokemon.x // tile_size)
            if tile_y is None:
                tile_y = int(pokemon.y // tile_size)
            snapshot.append({
                "unique_id": getattr(pokemon, "unique_id", None),
                "pokemon_id": pokemon.id,
                "level": pokemon.level,
                "tile_x": tile_x,
                "tile_y": tile_y,
            })
        return snapshot

    # =================================================================
    # Textos
    # =================================================================
    def get_title(self):
        return "FASE COMPLETA!"

    def get_phase_name(self):
        return self.phase_info.get("name", f"Fase {self.phase_id}")

    def get_gold_text(self):
        return f"+{self.gold_total}"

    def get_bonus_text(self):
        if self.bonus_amount > 0:
            return f"(+{self.bonus_amount} bônus)"
        return ""

    def get_exp_text(self):
        return f"+{self.total_xp}"

    def get_items_count_text(self):
        return str(len(self.item_counts))

    def get_rating(self):
        """(value, max_slots) — sempre 3 slots como no overlay antigo."""
        return self.stars, 3

    def get_next_phase_text(self):
        if not self.next_phase:
            return "Última fase do capítulo!"
        try:
            chapter, phase = map(int, self.next_phase.split("-"))
            info = phase_catalog.get_phase_info(chapter, phase)
            if info:
                return f"Próxima fase: {info['name']}"
        except Exception:
            pass
        return f"Próxima fase: {self.next_phase}"

    def get_pokemon_ids(self):
        return list(self.pokemon_ids)

    def get_item_list(self):
        """Lista de (item_id, count) para renderizar a grade."""
        return list(self.item_counts.items())

    def has_items(self):
        return len(self.item_counts) > 0

    # =================================================================
    # Ações
    # =================================================================
    def retry(self):
        print(f"[LEVEL_COMPLETE] Rejogar fase {self.phase_id}")
        try:
            from src.scenes.game_scene.game_scene import GameScene
            self.game_scene.cleanup()
            new_scene = GameScene(
                self.game,
                self.game_scene.chapter_id,
                self.game_scene.phase_number,
                region_id=self.game_scene.region_id,
                keep_placement=True,
                placement_snapshot=self.placement_snapshot,
            )
            self.game.current_scene = new_scene
            return "retry"
        except Exception as e:
            print(f"[LEVEL_COMPLETE] retry falhou: {e}")
            return "menu"

    def advance(self):
        """Avança para a próxima fase/capítulo."""
        if not self.next_phase:
            return "menu"
        print(f"[LEVEL_COMPLETE] Avançando para {self.next_phase}")
        try:
            chapter, phase = map(int, self.next_phase.split("-"))
            from src.scenes.game_scene.game_scene import GameScene
            self.game_scene.cleanup()
            new_scene = GameScene(
                self.game,
                chapter,
                phase,
                region_id=self.game_scene.region_id,
            )
            self.game.current_scene = new_scene
            return "advanced"
        except Exception as e:
            print(f"[LEVEL_COMPLETE] advance falhou: {e}")
            return "menu"

    def quit_to_menu(self):
        print("[LEVEL_COMPLETE] Voltando para phase select")
        try:
            from src.scenes.phase_selector.phase_select_scene import PhaseSelectScene
            self.game_scene.cleanup()
            ps = PhaseSelectScene(self.game)
            ps._needs_refresh = True
            self.game.current_scene = ps
            return "menu"
        except Exception as e:
            print(f"[LEVEL_COMPLETE] menu falhou: {e}")
            return "menu"