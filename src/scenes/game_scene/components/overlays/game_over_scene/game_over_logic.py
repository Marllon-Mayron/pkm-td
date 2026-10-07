# src/scenes/game_scene/components/overlays/game_over_scene/game_over_logic.py
"""
Lógica do overlay Game Over — fiel ao GameOverOverlay antigo.

Estado:
  - reason:           "team_defeated" | "items_stolen"
  - items_stolen:     nº de itens roubados (se reason == items_stolen)
  - gold_lost:        valor descontado do player
  - snapshot:         placement dos pokémon no mapa (para retry)
"""


class GameOverLogic:
    # =================================================================
    def __init__(self, game, game_scene, stats=None):
        self.game = game
        self.game_scene = game_scene

        s = dict(stats or {})
        self.reason = str(s.get("reason", "items_stolen"))
        self.items_stolen = int(s.get("items_stolen", 0))

        # Penalidade de gold (10%, mín. 1) — igual ao overlay antigo
        player = game_scene.player
        current_gold = int(getattr(player, "money", 0))
        if current_gold > 0:
            self.gold_lost = max(1, int(current_gold * 0.1))
            player.money -= self.gold_lost
            print(f"[GAME_OVER] Perdeu {self.gold_lost} gold "
                  f"(10% de {current_gold})")
        else:
            self.gold_lost = 0
            print("[GAME_OVER] Sem gold para perder")

        # Snapshot para retry (igual ao overlay antigo)
        self.placement_snapshot = self._capture_placement_snapshot()

    # =================================================================
    # Snapshot
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
        print(f"[GAME_OVER] Snapshot: {len(snapshot)} pokémon(s) no mapa.")
        return snapshot

    # =================================================================
    # Textos (idênticos ao overlay antigo)
    # =================================================================
    def get_title(self):
        return "GAME OVER"

    def get_reason_text(self):
        if self.reason == "team_defeated":
            return "Seu time inteiro foi derrotado!"
        return f"{self.items_stolen} itens foram levados!"

    def get_gold_text(self):
        if self.gold_lost > 0:
            return f"Você perdeu {self.gold_lost} gold! (10%)"
        return "Você não tinha gold para perder!"

    # =================================================================
    # Ações
    # =================================================================
    def retry(self):
        print(f"[GAME_OVER] Retry — keep_placement=True")
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
            print(f"[GAME_OVER] retry falhou: {e}")
            return "menu"

    def go_team_select(self):
        print("[GAME_OVER] Voltando para seleção de time")
        try:
            from src.scenes.team_select_scene.team_select_scene import TeamSelectScene
            self.game_scene.cleanup()
            ts = TeamSelectScene(
                self.game,
                self.game_scene.phase_info.get("chapter", 1),
                self.game_scene.phase_number,
                region_id=getattr(self.game_scene, "region_id", 1),
            )
            ts._needs_refresh = True
            self.game.current_scene = ts
            return "team"
        except Exception as e:
            print(f"[GAME_OVER] team_select falhou: {e}")
            return "menu"

    def go_phase_select(self):
        print("[GAME_OVER] Voltando para seleção de fase")
        try:
            from src.config.progress import progress_manager
            from src.scenes.phase_selector.phase_select_scene import PhaseSelectScene
            self.game_scene.cleanup()
            progress_manager._load_settings_from_save()
            ps = PhaseSelectScene(self.game)
            ps._needs_refresh = True
            self.game.current_scene = ps
            return "phase_select"
        except Exception as e:
            print(f"[GAME_OVER] phase_select falhou: {e}")
            return "menu"