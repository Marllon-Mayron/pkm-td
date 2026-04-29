# src/scenes/minigames/base_minigame_scene.py (CORRIGIDO)

"""
Classe base para todos os minigames
"""
import pygame
import json
import os
from typing import List, Optional, Any

from src.scenes.base_scene import BaseScene
from src.battle.battle_system import BattleSystem
from src.scenes.game_scene.components.renderer.map_renderer import MapRenderer
from src.scenes.game_scene.components.renderer.path_renderer import PathRenderer
from src.scenes.game_scene.components.renderer.pokemon_spot_renderer import PokemonSpotRenderer
from src.config.paths import PROJECT_ROOT


class BaseMinigameScene(BaseScene):
    """Classe base para minigames"""

    def __init__(self, game, chapter_id: int = 1, phase_number: int = 1, minigame_folder: str = ""):
        super().__init__(game)

        self.chapter_id = chapter_id
        self.phase_number = phase_number
        self.minigame_folder = minigame_folder

        # ===== COMPONENTES DO MAPA =====
        self.map_renderer = MapRenderer()
        self.path_renderer = PathRenderer()
        self.spot_renderer = PokemonSpotRenderer()

        # ===== SISTEMA DE COMBATE =====
        self.battle_system = BattleSystem(self)

        # ===== WAVE MANAGER =====
        self.wave_manager = None

        # ===== POKÉMON DO JOGADOR =====
        self.player_pokemon: List[Any] = []

        # ===== ESTADO DO JOGO =====
        self.game_state = "waiting"
        self.paused = False

        # ===== CÂMERA =====
        self.world_width = 2000
        self.world_height = 2000
        self.game.initialize_camera(self.world_width, self.world_height)
        self.camera = self.game.camera
        self.camera.set_limits(-500, self.world_width + 500, -500, self.world_height + 500)
        self.camera.x = self.world_width / 2
        self.camera.y = self.world_height / 2

        # ===== UI =====
        self.font_title = pygame.font.Font(None, 48)
        self.font_medium = pygame.font.Font(None, 32)
        self.font_small = pygame.font.Font(None, 24)

        # Carrega dados da fase
        self._load_phase_data()

    def _load_phase_data(self):
        """Carrega os dados da fase do minigame"""
        # Caminho para o minigame
        minigame_path = os.path.join(PROJECT_ROOT, "src", "data", "minigames", self.minigame_folder)
        level_file = os.path.join(minigame_path, f"level_{self.chapter_id:02d}_{self.phase_number:02d}.json")

        print(f"[BaseMinigame] Carregando fase: {level_file}")

        if not os.path.exists(level_file):
            print(f"[BaseMinigame] ERRO: Arquivo não encontrado: {level_file}")
            return

        try:
            with open(level_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            print(f"[BaseMinigame] Fase carregada: {data.get('name', 'Sem nome')}")

            # Carrega o mapa
            map_data = data.get("map", {})
            if map_data:
                self.map_renderer.load_from_data(map_data, PROJECT_ROOT)

            # Carrega os paths
            paths_data = data.get("paths", {"paths": []})
            self.path_renderer.load_from_data(paths_data)

            # Carrega os spots
            spots_data = data.get("tower_spots", {"spots": []})
            self.spot_renderer.load_from_data(spots_data)

            # Atualiza dimensões do mundo
            map_width, map_height = self.map_renderer.get_dimensions()
            if map_width > 0 and map_height > 0:
                self.world_width = map_width
                self.world_height = map_height
                self.camera.set_limits(-500, self.world_width + 500, -500, self.world_height + 500)
                self.camera.x = self.world_width / 2
                self.camera.y = self.world_height / 2

            print(f"[BaseMinigame] Mapa: {self.world_width}x{self.world_height}")
            print(f"[BaseMinigame] Paths: {len(self.path_renderer.paths)}")
            print(f"[BaseMinigame] Spots: {len(self.spot_renderer.get_spots())}")

        except Exception as e:
            print(f"[BaseMinigame] Erro ao carregar fase: {e}")
            import traceback
            traceback.print_exc()

    def start_waves(self):
        """Inicia as waves - deve ser sobrescrito pela subclasse"""
        pass

    def add_player_pokemon(self, pokemon):
        """Adiciona um Pokémon do jogador"""
        self.player_pokemon.append(pokemon)

    def remove_player_pokemon(self, pokemon):
        """Remove um Pokémon do jogador"""
        if pokemon in self.player_pokemon:
            self.player_pokemon.remove(pokemon)

    def toggle_pause(self):
        """Alterna pausa do jogo"""
        self.paused = not self.paused

    def handle_event(self, event):
        """Processa eventos base"""
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.game.current_scene = self.game.menu_scene
                return
            elif event.key == pygame.K_p:
                self.toggle_pause()

    def fixed_update(self, dt):
        """Update base"""
        if self.paused:
            return

        # Atualiza battle system
        if hasattr(self, 'battle_system'):
            self.battle_system.update(dt)

        # Atualiza Pokémon do jogador
        for pokemon in self.player_pokemon[:]:
            if not pokemon.is_alive() or pokemon.is_defeated:
                self.remove_player_pokemon(pokemon)
                continue

            pokemon.update(dt)
            if self.wave_manager:
                pokemon.update_combat(dt, self.wave_manager.active_enemies)

    def on_resize(self):
        pass

    def render(self, screen):
        """Renderiza base"""
        # Renderiza mapa
        self.map_renderer.render(screen, self.camera, self.screen_manager)

        # Renderiza spots
        self.spot_renderer.render(screen, self.camera, self.screen_manager)

        # Renderiza inimigos
        if self.wave_manager:
            for enemy in self.wave_manager.active_enemies:
                enemy.render(screen, self.camera, show_hp=True)

        # Renderiza Pokémon do jogador
        for pokemon in self.player_pokemon:
            pokemon.render(screen, self.camera, show_hp=True)

        # Renderiza projéteis
        if hasattr(self, 'battle_system'):
            self.battle_system.render_projectiles(screen, self.camera, self.screen_manager)

        # Borda do viewport
        pygame.draw.rect(screen, (80, 80, 80),
                         (self.screen_manager.viewport_x, self.screen_manager.viewport_y,
                          self.screen_manager.viewport_width, self.screen_manager.viewport_height), 2)

        # UI básica
        self._render_base_ui(screen)

        # Pausa
        if self.paused:
            self._render_pause_overlay(screen)

    def _render_base_ui(self, screen):
        """Renderiza UI base"""
        viewport_x = self.screen_manager.viewport_x
        viewport_y = self.screen_manager.viewport_y

        inst_text = self.font_small.render("P - Pausa | ESC - Sair", True, (150, 150, 150))
        screen.blit(inst_text, (viewport_x + 15, viewport_y + 15))

    def _render_pause_overlay(self, screen):
        """Overlay de pausa"""
        overlay = pygame.Surface((self.screen_manager.viewport_width, self.screen_manager.viewport_height))
        overlay.set_alpha(180)
        overlay.fill((0, 0, 0))
        screen.blit(overlay, (self.screen_manager.viewport_x, self.screen_manager.viewport_y))

        pause_text = self.font_title.render("PAUSADO", True, (255, 255, 255))
        text_x = self.screen_manager.viewport_x + (self.screen_manager.viewport_width - pause_text.get_width()) // 2
        text_y = self.screen_manager.viewport_y + (self.screen_manager.viewport_height - pause_text.get_height()) // 2
        screen.blit(pause_text, (text_x, text_y))