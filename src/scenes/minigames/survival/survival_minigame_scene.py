# src/scenes/minigames/survival/survival_minigame_scene.py

"""
Cena principal do minigame Survival
Estilo Plants vs Zombies / Tower Defense com cards na esteira
"""
import pygame
import math
import random
from typing import List, Optional, Dict, Any

from src.scenes.minigames.survival.components.pokemon_input_handler import PokemonInputHandler
from src.managers.notification_manager import notification_manager
from src.scenes.minigames.base_minigame_scene import BaseMinigameScene
from src.scenes.minigames.survival.components.card_deck import CardDeck
from src.scenes.minigames.survival.components.placement_manager import SurvivalPlacementManager
from src.scenes.minigames.survival.components.wave_manager import SurvivalWaveManager
from src.scenes.minigames.survival.components.ui.survival_ui import SurvivalUI
from src.battle.battle_system import BattleSystem


class SurvivalMinigameScene(BaseMinigameScene):
    """
    Minigame de sobrevivência estilo Plants vs Zombies.
    - Esteira de cards (sempre 5 cartas visíveis)
    - Cartas vêm da direita para esquerda
    - Sistema de combate idêntico ao modo campanha
    """

    # Constantes
    STARTING_LIVES = 5
    STARTING_ENERGY = 100
    ENERGY_REGEN_RATE = 1.0  # Por segundo
    MAX_ENERGY = 200

    def __init__(self, game, chapter_id: int = 1, phase_number: int = 1):
        super().__init__(game, chapter_id, phase_number, minigame_folder="survival")

        # ===== ESTADO DO MINIGAME =====
        self.lives = self.STARTING_LIVES
        self.energy = self.STARTING_ENERGY
        self.score = 0
        self.wave_number = 1
        self.game_state = "waiting"  # waiting, in_wave, game_over, completed

        # ===== CONTROLE DE CÂMERA =====
        self.dragging_camera = False
        self.last_mouse_pos = None
        # Inicializa câmera (se não existir)
        if not hasattr(self.game, 'camera') or self.game.camera is None:
            self.game.initialize_camera(self.world_width, self.world_height)

        self.camera = self.game.camera
        self.camera.set_limits(-500, self.world_width + 500, -500, self.world_height + 500)
        self.camera.x = self.world_width / 2
        self.camera.y = self.world_height /2
        # ===== ESTADO DE PAUSA =====
        self.game_paused = False  # Para overlays

        # ===== SISTEMA DE COMBATE =====
        self.battle_system = BattleSystem(self)

        # ===== COMPONENTES =====
        self.card_deck = CardDeck(self)  # Já inicializa com 5 cartas!
        self.placement_manager = SurvivalPlacementManager(self)
        self.survival_ui = SurvivalUI(self)
        self.notification_manager = notification_manager
        self.pokemon_input_handler = PokemonInputHandler(self)
        self.move_select_overlay = None
        # ===== WAVE MANAGER =====
        self._init_survival_wave_manager()

        # ===== TIMERS =====
        self.energy_regen_timer = 0.0

        # ===== ESTADO DO CARD SELECIONADO =====
        self.selected_card = None
        self.selected_card_index = -1

        # ===== POKÉMON DO JOGADOR =====
        self.player_pokemon: List[Any] = []

        # ===== FONTES =====
        self._init_fonts()

        # Inicia o jogo
        self._start_game()

    def _init_fonts(self):
        """Inicializa fontes específicas"""
        self.font_large = pygame.font.Font(None, 48)
        self.font_medium = pygame.font.Font(None, 32)
        self.font_small = pygame.font.Font(None, 24)

    def _init_survival_wave_manager(self):
        """Inicializa o wave manager customizado para survival"""
        self.wave_manager = SurvivalWaveManager(self, self.chapter_id, self.phase_number)
        self.wave_manager.set_paths(self.path_renderer.paths)
        self.wave_manager.start_waves()

    def _start_game(self):
        """Inicia o minigame"""
        print(f"[Survival] Iniciando minigame - Fase {self.chapter_id}-{self.phase_number}")

        # Reseta estado
        self.lives = self.STARTING_LIVES
        self.energy = self.STARTING_ENERGY
        self.score = 0
        self.wave_number = 1
        self.game_state = "in_wave"

        # Limpa Pokémon existentes
        self._clear_all_pokemon()

        # Reinicia o deck (já tem 5 cartas)
        self.card_deck = CardDeck(self)

        # Reinicia waves
        if hasattr(self, 'wave_manager') and self.wave_manager:
            self.wave_manager.start_waves()

    def _clear_all_pokemon(self):
        """Remove todos os Pokémon do mapa"""
        for pokemon in self.player_pokemon[:]:
            self._remove_pokemon(pokemon)
        self.player_pokemon.clear()
        self.placement_manager.clear()

    def _remove_pokemon(self, pokemon):
        """Remove um Pokémon do mapa"""
        if pokemon in self.player_pokemon:
            self.player_pokemon.remove(pokemon)

        # Libera o spot
        if hasattr(pokemon, 'placed_tile_x') and hasattr(pokemon, 'placed_tile_y'):
            for spot in self.spot_renderer.get_spots():
                spot_tile_x = spot.x // self.placement_manager.tile_size
                spot_tile_y = spot.y // self.placement_manager.tile_size
                if spot_tile_x == pokemon.placed_tile_x and spot_tile_y == pokemon.placed_tile_y:
                    spot.occupied = False
                    break

        # Remove do battle system
        if hasattr(self, 'battle_system') and self.battle_system:
            if hasattr(self.battle_system, 'effect_manager'):
                self.battle_system.effect_manager.unregister_pokemon(pokemon)

        pokemon.is_placed = False

    def try_place_pokemon(self, spot, pokemon_data: dict) -> bool:
        """
        Tenta colocar um Pokémon no spot
        """
        # Verifica se o spot está ocupado
        if spot.occupied:
            self.survival_ui.show_message("Spot ocupado!", (255, 100, 100))
            return False

        # Verifica energia
        cost = pokemon_data.get('cost', 50)
        if self.energy < cost:
            self.survival_ui.show_message(f"Energia insuficiente! ({cost} necessário)", (255, 100, 100))
            return False

        # Cria o Pokémon
        from src.entities.pokemon import Pokemon

        tile_center_x = (spot.x // self.placement_manager.tile_size) * self.placement_manager.tile_size + self.placement_manager.tile_size // 2
        tile_center_y = (spot.y // self.placement_manager.tile_size) * self.placement_manager.tile_size + self.placement_manager.tile_size // 2

        pokemon = Pokemon(
            tile_center_x, tile_center_y,
            pokemon_data['id'],
            level=pokemon_data.get('level', 5),
            is_wild=False,
            shiny=False,
            is_boss=False
        )

        # Configura o Pokémon
        pokemon.is_placed = True
        pokemon.placed_tile_x = tile_center_x // self.placement_manager.tile_size
        pokemon.placed_tile_y = tile_center_y // self.placement_manager.tile_size
        pokemon.original_spot_x = tile_center_x
        pokemon.original_spot_y = tile_center_y
        pokemon.screen_manager = self.screen_manager
        pokemon.camera = self.camera
        pokemon.game_scene = self

        # Configura battle system
        pokemon.set_battle_system(self.battle_system)

        # Adiciona ao gerenciador
        self.placement_manager.add_pokemon(pokemon, spot)
        self.player_pokemon.append(pokemon)
        spot.occupied = True

        # Consome energia
        self.energy -= cost

        # ===== REMOVE A CARTA DA ESTEIRA =====
        # Isso aciona a animação de nova carta vindo da direita
        card_index = self.selected_card_index
        if card_index >= 0:
            self.card_deck.remove_card(card_index)

        # Limpa seleção
        self.card_deck.clear_selection()
        self.selected_card = None
        self.selected_card_index = -1
        pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_ARROW)

        print(f"[Survival] {pokemon.name} colocado! Energia: {self.energy}")
        return True

    def can_afford(self, cost: int) -> bool:
        """Verifica se tem energia suficiente"""
        return self.energy >= cost

    def add_energy(self, amount: int):
        """Adiciona energia"""
        self.energy = min(self.MAX_ENERGY, self.energy + amount)

    def add_score(self, amount: int):
        """Adiciona pontos"""
        self.score += amount

    def lose_life(self, amount: int = 1):
        """Perde uma vida"""
        self.lives -= amount
        self.survival_ui.show_message(f"Perdeu uma vida! Restam: {self.lives}", (255, 100, 100))

        if self.lives <= 0:
            self.game_over()

    def game_over(self):
        """Fim de jogo"""
        self.game_state = "game_over"
        if self.wave_manager:
            self.wave_manager.paused = True
        print(f"[Survival] GAME OVER! Score final: {self.score}")

    def complete_wave(self):
        """Completa uma wave com sucesso"""
        self.wave_number += 1
        self.add_energy(50)
        self.survival_ui.show_message(f"ONDA {self.wave_number - 1} COMPLETA!", (100, 255, 100), duration=2.0)

        # Verifica se acabaram as waves
        if self.wave_manager and not self.wave_manager.has_more_waves():
            self.game_state = "completed"
            if self.wave_manager:
                self.wave_manager.paused = True
            print(f"[Survival] FASE COMPLETA! Score final: {self.score}")

    # ===== MÉTODOS DE EVENTOS =====

    def handle_event(self, event):
        """Processa eventos do minigame"""

        # ===== OVERLAY DE MOVES (se estiver ativo, processa primeiro) =====
        if self.move_select_overlay and self.move_select_overlay.active:
            self.move_select_overlay.handle_event(event)
            return

        # UI primeiro
        if self.survival_ui.handle_event(event):
            return

        # ===== INPUT HANDLER PARA CLIQUE NOS POKÉMON =====
        if self.pokemon_input_handler.handle_event(event):
            return

        # ===== MOUSE WHEEL PARA ZOOM =====
        if event.type == pygame.MOUSEWHEEL:
            if not self.paused and not self.dragging_camera:
                mouse_pos = pygame.mouse.get_pos()
                if self.screen_manager.is_mouse_in_viewport(mouse_pos):
                    world_pos = self.screen_manager.get_mouse_world_position(mouse_pos, self.camera)
                    if world_pos:
                        target_x, target_y = world_pos
                        self.camera.handle_zoom(event.y > 0)
                        new_world_pos = self.screen_manager.get_mouse_world_position(mouse_pos, self.camera)
                        if new_world_pos:
                            dx = target_x - new_world_pos[0]
                            dy = target_y - new_world_pos[1]
                            self.camera.x += dx
                            self.camera.y += dy
                            self.camera._clamp_position()
            return

        # ===== DRAG DA CÂMERA (BOTÃO DO MEIO) =====
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 2:
            mouse_pos = pygame.mouse.get_pos()
            if self.screen_manager.is_mouse_in_viewport(mouse_pos):
                self.dragging_camera = True
                self.last_mouse_pos = mouse_pos
                pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_SIZEALL)
            return

        if event.type == pygame.MOUSEBUTTONUP and event.button == 2:
            if self.dragging_camera:
                self.dragging_camera = False
                self.last_mouse_pos = None
                pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_ARROW)
            return

        if event.type == pygame.MOUSEMOTION:
            if self.dragging_camera and self.last_mouse_pos:
                dx = event.pos[0] - self.last_mouse_pos[0]
                dy = event.pos[1] - self.last_mouse_pos[1]
                self.camera.x -= dx / self.camera.zoom
                self.camera.y -= dy / self.camera.zoom
                self.camera._clamp_position()
                self.last_mouse_pos = event.pos
                return

        # ===== TECLADO =====
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_p:
                self.toggle_pause()
                return
            elif event.key == pygame.K_F1:
                self.show_debug = not self.show_debug
                return

        # Deck de cards
        card_result = self.card_deck.handle_event(event)
        if card_result:
            if card_result.get('action') == 'card_selected':
                self.selected_card = card_result
                self.selected_card_index = card_result.get('index', -1)
                pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_HAND)
            return

        # Card selecionado + clique no mapa
        if self.selected_card and event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mouse_pos = pygame.mouse.get_pos()

            if self.screen_manager.is_mouse_in_viewport(mouse_pos):
                world_pos = self.screen_manager.get_mouse_world_position(mouse_pos, self.camera)
                if world_pos:
                    spot = self.spot_renderer.get_spot_at_world_pos(world_pos[0], world_pos[1])
                    if spot:
                        success = self.try_place_pokemon(spot, self.selected_card.get('pokemon_data', {}))
                        if success:
                            pass
                    else:
                        self.card_deck.clear_selection()
                        self.selected_card = None
                        self.selected_card_index = -1
                        pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_ARROW)

        # Clique direito cancela seleção
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
            if self.selected_card:
                self.card_deck.clear_selection()
                self.selected_card = None
                self.selected_card_index = -1
                pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_ARROW)

        # ESC cancela seleção ou fecha overlay ou volta ao menu
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            if self.selected_card:
                self.card_deck.clear_selection()
                self.selected_card = None
                self.selected_card_index = -1
                pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_ARROW)
            elif self.move_select_overlay and self.move_select_overlay.active:
                self.move_select_overlay.close()
                self.move_select_overlay = None
                self.paused = False
            else:
                self.game.current_scene = self.game.menu_scene

        super().handle_event(event)

    def close_move_select_overlay(self):
        """Fecha o overlay de seleção de moves"""
        if self.move_select_overlay:
            self.move_select_overlay.active = False
            self.move_select_overlay = None

        # Despausa o jogo
        self.paused = False
        if hasattr(self, 'wave_manager') and self.wave_manager:
            self.wave_manager.paused = False

        print("[Survival] Overlay de moves fechado")

    # ===== MÉTODOS DE UPDATE =====

    def fixed_update(self, dt):
        """Atualização lógica do minigame"""

        # ===== ATUALIZA CÂMERA (movimento com mouse) =====
        if not self.paused and not self.dragging_camera:
            mouse_pos = pygame.mouse.get_pos()
            if self.screen_manager.is_mouse_in_viewport(mouse_pos):
                # Converte para posição relativa ao render
                rel_x = mouse_pos[0] - self.screen_manager.viewport_x
                rel_y = mouse_pos[1] - self.screen_manager.viewport_y
                self.camera.update(dt, (rel_x, rel_y))

        # Se está pausado por causa do overlay, atualiza o overlay
        if self.paused:
            if self.move_select_overlay and self.move_select_overlay.active:
                self.move_select_overlay.update(dt)
            return

        if self.game_state in ["game_over", "completed"]:
            return

        # Atualiza UI
        if hasattr(self, 'survival_ui'):
            self.survival_ui.update(dt)

        # Regenera energia
        self.energy_regen_timer += dt
        if self.energy_regen_timer >= 1.0:
            regen_amount = int(self.energy_regen_timer * self.ENERGY_REGEN_RATE)
            if regen_amount > 0:
                self.energy = min(self.MAX_ENERGY, self.energy + regen_amount)
                self.energy_regen_timer -= regen_amount / self.ENERGY_REGEN_RATE

        # Atualiza deck
        self.card_deck.update(dt)

        # Wave manager
        if self.wave_manager:
            enemies_at_end = self.wave_manager.update(dt)
            for enemy in enemies_at_end:
                if enemy.is_alive() and not enemy.is_defeated:
                    if not hasattr(enemy, '_escaped_counted') or not enemy._escaped_counted:
                        self.lose_life(1)
                        enemy._escaped_counted = True

        # Combate: inimigos atacam aliados
        if self.wave_manager and self.wave_manager.active_enemies:
            for enemy in self.wave_manager.active_enemies[:]:
                if not enemy.is_alive() or enemy.is_defeated:
                    continue

                target_ally = None
                min_distance = float('inf')

                for ally in self.player_pokemon:
                    if not ally.is_alive() or ally.is_defeated:
                        continue

                    dx = ally.x - enemy.x
                    dy = ally.y - enemy.y
                    distance = math.hypot(dx, dy)

                    if distance < enemy.attack_range and distance < min_distance:
                        min_distance = distance
                        target_ally = ally

                if target_ally:
                    enemy.target = target_ally
                    enemy.combat_state = "attacking"

                    if enemy.has_animation("idle") and enemy.current_animation != "idle":
                        enemy.set_animation("idle")

                    enemy.update_combat(dt, self.player_pokemon)
                else:
                    if enemy.target:
                        enemy.target = None
                    enemy.combat_state = "idle"
                    if enemy.has_animation("walk") and enemy.current_animation != "walk":
                        enemy.set_animation("walk")

                enemy.animation.update(dt)

        # Battle system
        if hasattr(self, 'battle_system'):
            self.battle_system.update(dt)

        # Effect manager
        if hasattr(self, 'battle_system') and self.battle_system:
            effect_mgr = self.battle_system.effect_manager
            if effect_mgr:
                effect_mgr.update(dt)

        # Pokémon do jogador
        for pokemon in self.player_pokemon[:]:
            if not pokemon.is_alive() or pokemon.is_defeated:
                self._remove_pokemon(pokemon)
                continue

            pokemon.update(dt)

            if self.wave_manager and self.wave_manager.active_enemies:
                pokemon.update_combat(dt, self.wave_manager.active_enemies)
            else:
                if pokemon.combat_state != "idle":
                    pokemon.combat_state = "idle"
                    if pokemon.has_animation("idle"):
                        pokemon.set_animation("idle")

            pokemon.animation.update(dt)

        # Notification manager
        if hasattr(self, 'notification_manager'):
            self.notification_manager.update(dt)

    def toggle_pause(self):
        """Alterna pausa do jogo"""
        self.paused = not self.paused
        if self.wave_manager:
            self.wave_manager.paused = self.paused
        if self.paused:
            print("[Survival] Jogo pausado")
        else:
            print("[Survival] Jogo continuando")
    # ===== MÉTODOS DE RENDER =====

    def render(self, screen):
        """Renderiza o minigame"""
        # Mapa
        self.map_renderer.render(screen, self.camera, self.screen_manager)

        # Spots
        self.spot_renderer.render(
            screen, self.camera, self.screen_manager,
            highlight_spot=self._get_hovered_spot() if self.selected_card else None
        )

        # Inimigos
        if self.wave_manager:
            for enemy in self.wave_manager.active_enemies:
                enemy.render(screen, self.camera, show_hp=True)

        # Pokémon do jogador
        for pokemon in self.player_pokemon:
            pokemon.render(screen, self.camera, show_hp=True)
            self._render_ally_name_and_level(screen, pokemon)
        # Projéteis
        if hasattr(self, 'battle_system'):
            self.battle_system.render_projectiles(screen, self.camera, self.screen_manager)

        # UI e Cards
        self.survival_ui.render(screen)
        self.card_deck.render(screen)

        # Preview do card selecionado
        if self.selected_card:
            self._render_selected_card_preview(screen)

        # Overlays
        if self.game_state == "game_over":
            self._render_game_over(screen)
        elif self.game_state == "completed":
            self._render_completed(screen)

        if self.paused:
            self._render_pause_overlay(screen)

        # Borda do viewport
        pygame.draw.rect(screen, (80, 80, 80),
                        (self.screen_manager.viewport_x, self.screen_manager.viewport_y,
                         self.screen_manager.viewport_width, self.screen_manager.viewport_height), 2)

        if self.move_select_overlay and self.move_select_overlay.active:
            self.move_select_overlay.render(screen)

    def _get_hovered_spot(self):
        """Retorna o spot sob o mouse"""
        mouse_pos = pygame.mouse.get_pos()
        if self.screen_manager.is_mouse_in_viewport(mouse_pos):
            world_pos = self.screen_manager.get_mouse_world_position(mouse_pos, self.camera)
            if world_pos:
                return self.spot_renderer.get_spot_at_world_pos(world_pos[0], world_pos[1])
        return None

    def _render_ally_name_and_level(self, screen, pokemon):
        """
        Renderiza nome, nível e barra de XP do Pokémon aliado
        (HP já é renderizado pelo próprio Pokémon)
        """
        if not pokemon or pokemon.is_defeated or not pokemon.is_alive():
            return

        # Converte posição do mundo para tela
        if hasattr(self, 'camera') and self.camera:
            screen_x, screen_y = self.screen_manager.world_to_screen(
                pokemon.x, pokemon.y, self.camera
            )
            zoom_scale = self.camera.zoom * self.screen_manager.render_scale
        else:
            screen_x, screen_y = pokemon.x, pokemon.y
            zoom_scale = 1.0

        # ===== PREPARA O SPRITE PARA PEGAR O TAMANHO =====
        sprite_to_render = None
        if hasattr(pokemon, 'sprite') and pokemon.sprite:
            if pokemon.is_boss:
                orig_width, orig_height = pokemon.sprite.get_width(), pokemon.sprite.get_height()
                new_width = int(orig_width * 2)
                new_height = int(orig_height * 2)
                sprite_to_render = pygame.transform.scale(pokemon.sprite, (new_width, new_height))
            else:
                sprite_to_render = pokemon.sprite

        if sprite_to_render:
            current_width, current_height = sprite_to_render.get_width(), sprite_to_render.get_height()
            final_width = max(1, int(current_width * zoom_scale))
            final_height = max(1, int(current_height * zoom_scale))

            if final_width != current_width or final_height != current_height:
                scaled_sprite = pygame.transform.scale(sprite_to_render, (final_width, final_height))
            else:
                scaled_sprite = sprite_to_render

            sprite_rect = scaled_sprite.get_rect()
            sprite_rect.center = (int(screen_x), int(screen_y))
        else:
            # Fallback: usa tamanho padrão
            size = int((64 if pokemon.is_boss else pokemon.map_sprite_size) * zoom_scale)
            sprite_rect = pygame.Rect(0, 0, size, size)
            sprite_rect.center = (int(screen_x), int(screen_y))

        # ===== TEXTOS (MESMO FORMATO DOS INIMIGOS) =====
        name_text = f"{pokemon.name} - "
        level_text = f"lv. {pokemon.level:02d}"

        # Cores para aliados
        text_color = (150, 200, 255)  # Azul claro
        outline_color = (0, 0, 0)

        if pokemon.is_shiny:
            level_color = (255, 215, 0)  # Dourado
        elif pokemon.level >= 30:
            level_color = (255, 100, 100)  # Vermelho claro
        else:
            level_color = (100, 255, 100)  # Verde claro

        # Tamanhos de fonte
        name_font_size = max(10, int(12 * zoom_scale))
        level_font_size = max(9, int(11 * zoom_scale))

        name_font = pygame.font.Font(None, name_font_size)
        level_font = pygame.font.Font(None, level_font_size)

        # Renderiza textos com contorno
        name_surface = name_font.render(name_text, True, text_color)
        level_surface = level_font.render(level_text, True, level_color)
        name_outline = name_font.render(name_text, True, outline_color)
        level_outline = level_font.render(level_text, True, outline_color)

        name_width = name_surface.get_width()
        level_width = level_surface.get_width()
        total_width = name_width + 2 + level_width

        # ===== POSICIONAMENTO MAIS ALTO =====
        sprite_height = sprite_rect.height
        # Aumentado de -0.65 para -0.85 para subir mais
        relative_offset = -sprite_height * 0.85

        start_x = sprite_rect.centerx - total_width // 2
        text_y = int(sprite_rect.top + relative_offset)

        name_x, name_y = start_x, text_y
        level_x = start_x + name_width + 2
        level_y = text_y + (name_font_size - level_font_size)

        # Desenha contorno
        for dx, dy in [(-1, -1), (-1, 1), (1, -1), (1, 1)]:
            screen.blit(name_outline, (name_x + dx, name_y + dy))
            screen.blit(level_outline, (level_x + dx, level_y + dy))

        # Desenha texto principal
        screen.blit(name_surface, (name_x, name_y))
        screen.blit(level_surface, (level_x, level_y))

        # ===== BARRA DE XP (ABAIXO DA BARRA DE HP ORIGINAL) =====
        self._render_ally_xp_bar(screen, sprite_rect, pokemon, zoom_scale)

    def _render_ally_xp_bar(self, screen, sprite_rect, pokemon, zoom_scale):
        """
        Renderiza a barra de XP abaixo da barra de HP original do Pokémon
        """
        # Calcula a posição da barra de HP original
        # A barra de HP original fica em: sprite_rect.top - (sprite_height * 0.35)
        # Vamos posicionar a barra de XP LOGO ABAIXO dela

        sprite_height = sprite_rect.height

        # Posição Y da barra de HP original (estimada)
        # O método _render_hp_bar do Pokémon usa: relative_offset = -sprite_height * 0.35
        hp_bar_y = sprite_rect.top + (-sprite_height * 0.35)

        # Largura da barra de HP original (padrão = 48)
        hp_bar_width = 48

        # Escala a largura com o zoom
        bar_width = int(hp_bar_width * zoom_scale)
        bar_width = max(30, min(100, bar_width))  # Limites

        # Centraliza horizontalmente no sprite
        bar_x = sprite_rect.centerx - bar_width // 2

        # Posição Y: LOGO ABAIXO da barra de HP (com 2px de espaçamento)
        xp_bar_height = max(3, int(4 * zoom_scale))  # Barra fina
        xp_bar_y = int(hp_bar_y + (6 * zoom_scale) + 2)  # Abaixo da barra de HP

        # Só renderiza se o Pokémon não estiver derrotado
        if pokemon.is_defeated or not pokemon.is_alive():
            return

        # Calcula porcentagem de XP
        xp_percent = pokemon.xp / pokemon.xp_to_next if pokemon.xp_to_next > 0 else 0

        # Fundo da barra de XP
        pygame.draw.rect(screen, (30, 30, 40), (bar_x, xp_bar_y, bar_width, xp_bar_height), border_radius=2)

        # Preenchimento da barra de XP
        if xp_percent > 0:
            xp_width = max(2, int(bar_width * xp_percent))
            xp_color = (100, 150, 255)  # Azul para XP
            pygame.draw.rect(screen, xp_color, (bar_x, xp_bar_y, xp_width, xp_bar_height), border_radius=2)

        # Borda da barra de XP
        pygame.draw.rect(screen, (100, 100, 120), (bar_x, xp_bar_y, bar_width, xp_bar_height), 1, border_radius=2)

        # Texto de XP (opcional, só se a barra for grande o suficiente)
        if bar_width > 50:
            font_xp = pygame.font.Font(None, max(7, int(8 * zoom_scale)))
            xp_text = f"{pokemon.xp}/{pokemon.xp_to_next}"
            text_surf = font_xp.render(xp_text, True, (200, 200, 220))

            # Centraliza o texto na barra
            text_x = bar_x + (bar_width - text_surf.get_width()) // 2
            text_y = xp_bar_y + (xp_bar_height - text_surf.get_height()) // 2

            # Fundo semi-transparente para o texto
            if text_x > bar_x and text_y > xp_bar_y:
                text_bg = pygame.Surface((text_surf.get_width() + 2, text_surf.get_height() + 1))
                text_bg.set_alpha(180)
                text_bg.fill((0, 0, 0))
                screen.blit(text_bg, (text_x - 1, text_y))
                screen.blit(text_surf, (text_x, text_y))

    def _render_selected_card_preview(self, screen):
        """Renderiza preview do card selecionado seguindo o mouse"""
        mouse_pos = pygame.mouse.get_pos()
        if not self.screen_manager.is_mouse_in_viewport(mouse_pos):
            return

        pokemon_data = self.selected_card.get('pokemon_data', {})
        cost = pokemon_data.get('cost', 50)
        can_afford = self.energy >= cost

        preview_size = 64
        half = preview_size // 2

        preview_bg = pygame.Surface((preview_size, preview_size), pygame.SRCALPHA)
        if can_afford:
            preview_bg.fill((100, 200, 100, 180))
        else:
            preview_bg.fill((200, 100, 100, 180))

        border_color = (0, 255, 0) if can_afford else (255, 0, 0)
        pygame.draw.rect(preview_bg, border_color, (0, 0, preview_size, preview_size), 3, border_radius=8)

        try:
            pokedex = self.game.player.pokedex if self.game.player else None
            if pokedex:
                sprite = pokedex.get_sprite(pokemon_data['id'], "front", False)
                if sprite:
                    scaled = pygame.transform.scale(sprite, (48, 48))
                    preview_bg.blit(scaled, (8, 8))
        except:
            pass

        cost_text = self.font_small.render(f"{cost}", True, (255, 255, 255))

        screen.blit(preview_bg, (mouse_pos[0] - half, mouse_pos[1] - half))

        # Círculo de energia
        pygame.draw.circle(screen, (255, 200, 50), (mouse_pos[0] + half - 15, mouse_pos[1] - half + 15), 12)
        screen.blit(cost_text, (mouse_pos[0] + half - 15 - cost_text.get_width() // 2, mouse_pos[1] - half + 11))

    def _render_game_over(self, screen):
        """Renderiza tela de game over"""
        overlay = pygame.Surface((self.screen_manager.viewport_width, self.screen_manager.viewport_height))
        overlay.set_alpha(200)
        overlay.fill((0, 0, 0))
        screen.blit(overlay, (self.screen_manager.viewport_x, self.screen_manager.viewport_y))

        title = self.font_large.render("GAME OVER", True, (255, 80, 80))
        title_x = self.screen_manager.viewport_x + (self.screen_manager.viewport_width - title.get_width()) // 2
        title_y = self.screen_manager.viewport_y + self.screen_manager.viewport_height // 2 - 60
        screen.blit(title, (title_x, title_y))

        score_text = self.font_medium.render(f"Score Final: {self.score}", True, (255, 215, 0))
        score_x = self.screen_manager.viewport_x + (self.screen_manager.viewport_width - score_text.get_width()) // 2
        score_y = title_y + 50
        screen.blit(score_text, (score_x, score_y))

        wave_text = self.font_small.render(f"Waves completadas: {self.wave_number - 1}", True, (200, 200, 200))
        wave_x = self.screen_manager.viewport_x + (self.screen_manager.viewport_width - wave_text.get_width()) // 2
        wave_y = score_y + 35
        screen.blit(wave_text, (wave_x, wave_y))

        inst_text = self.font_small.render("Pressione ESC para voltar ao menu", True, (150, 150, 150))
        inst_x = self.screen_manager.viewport_x + (self.screen_manager.viewport_width - inst_text.get_width()) // 2
        inst_y = wave_y + 50
        screen.blit(inst_text, (inst_x, inst_y))

    def _render_completed(self, screen):
        """Renderiza tela de fase completa"""
        overlay = pygame.Surface((self.screen_manager.viewport_width, self.screen_manager.viewport_height))
        overlay.set_alpha(200)
        overlay.fill((0, 0, 0))
        screen.blit(overlay, (self.screen_manager.viewport_x, self.screen_manager.viewport_y))

        title = self.font_large.render("FASE COMPLETA!", True, (100, 255, 100))
        title_x = self.screen_manager.viewport_x + (self.screen_manager.viewport_width - title.get_width()) // 2
        title_y = self.screen_manager.viewport_y + self.screen_manager.viewport_height // 2 - 60
        screen.blit(title, (title_x, title_y))

        score_text = self.font_medium.render(f"Score Final: {self.score}", True, (255, 215, 0))
        score_x = self.screen_manager.viewport_x + (self.screen_manager.viewport_width - score_text.get_width()) // 2
        score_y = title_y + 50
        screen.blit(score_text, (score_x, score_y))

        lives_text = self.font_small.render(f"Vidas restantes: {self.lives}", True, (200, 200, 200))
        lives_x = self.screen_manager.viewport_x + (self.screen_manager.viewport_width - lives_text.get_width()) // 2
        lives_y = score_y + 35
        screen.blit(lives_text, (lives_x, lives_y))

        inst_text = self.font_small.render("Pressione ESC para voltar ao menu", True, (150, 150, 150))
        inst_x = self.screen_manager.viewport_x + (self.screen_manager.viewport_width - inst_text.get_width()) // 2
        inst_y = lives_y + 50
        screen.blit(inst_text, (inst_x, inst_y))

    def _render_pause_overlay(self, screen):
        """Overlay de pausa"""
        overlay = pygame.Surface((self.screen_manager.viewport_width, self.screen_manager.viewport_height))
        overlay.set_alpha(180)
        overlay.fill((0, 0, 0))
        screen.blit(overlay, (self.screen_manager.viewport_x, self.screen_manager.viewport_y))

        pause_text = self.font_large.render("PAUSADO", True, (255, 255, 255))
        text_x = self.screen_manager.viewport_x + (self.screen_manager.viewport_width - pause_text.get_width()) // 2
        text_y = self.screen_manager.viewport_y + (self.screen_manager.viewport_height - pause_text.get_height()) // 2
        screen.blit(pause_text, (text_x, text_y))