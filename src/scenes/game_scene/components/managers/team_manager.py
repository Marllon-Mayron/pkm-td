# src/scenes/game_scene/components/managers/team_manager.py

import pygame
from src.scenes.game_scene.components.team_slot import GameTeamSlot
from src.scenes.game_scene.components.drag_drop import DragDropManager


class GameTeamManager:
    """Gerencia a HUD do time durante o jogo - Otimizada para Performance"""

    def __init__(self, game, game_scene=None):
        self.game = game
        self.game_scene = game_scene

        # Configurações responsivas
        self.slot_width_ratio = 0.16
        self.slot_height_ratio = 0.14
        self.slot_spacing_ratio = 0.012
        self.bottom_margin_ratio = 0.015

        # Lista de slots
        self.team_slots = []
        self.selected_slot_index = -1

        # Estado
        self.visible = True
        self.expanded = False

        # Animação
        self.target_y = 0

        # Drag and Drop
        self.drag_manager = DragDropManager(game)

        # ===== OTIMIZAÇÃO: Cache de Superfícies =====
        self._bg_surface = None
        self._glow_surface = None
        self._deco_line_surface = None
        self._last_window_width = 0
        self._last_window_height = 0
        self._needs_cache_rebuild = True

        # ===== OTIMIZAÇÃO: Cache de Fontes =====
        self._title_font = None
        self._stat_font = None

        # Inicializa
        self._calculate_dimensions()
        self._create_slots()

    def _get_title_font(self):
        """Obtém fonte do título com lazy loading"""
        if self._title_font is None:
            self._title_font = pygame.font.Font(None, 28)
        return self._title_font

    def _get_stat_font(self):
        """Obtém fonte de stats com lazy loading"""
        if self._stat_font is None:
            self._stat_font = pygame.font.Font(None, 22)
        return self._stat_font

    def set_game_scene(self, game_scene):
        self.game_scene = game_scene

    def _calculate_dimensions(self):
        """Calcula dimensões e marca para rebuild do cache"""
        self.window_width = self.game.screen_manager.window_width
        self.window_height = self.game.screen_manager.window_height

        self.slot_width = max(140, min(220, int(self.window_width * self.slot_width_ratio)))
        self.slot_height = max(90, min(140, int(self.window_height * self.slot_height_ratio)))
        self.slot_spacing = max(6, min(20, int(self.window_width * self.slot_spacing_ratio)))
        self.bottom_margin = int(self.window_height * self.bottom_margin_ratio)

        # Marca para rebuild do cache
        self._needs_cache_rebuild = True

    def _rebuild_cache(self):
        """Reconstrói os caches visuais (só quando necessário)"""
        if not self._needs_cache_rebuild:
            return

        hud_height = self.slot_height + 40

        # 1. Cache do Fundo Gradiente (SIMPLIFICADO - menos linhas)
        self._bg_surface = pygame.Surface((self.window_width, hud_height), pygame.SRCALPHA)
        step = max(1, hud_height // 20)  # Reduzido de 1px para 20px chunks
        for i in range(0, hud_height, step):
            progress = i / hud_height
            alpha = int(80 + 100 * progress)
            color = (10, 15, 25, alpha)
            pygame.draw.rect(self._bg_surface, color, (0, i, self.window_width, min(step, hud_height - i)))

        # 2. Cache do Glow Superior (SIMPLIFICADO)
        self._glow_surface = pygame.Surface((self.window_width, 2), pygame.SRCALPHA)
        # Só desenha alguns pontos em vez de todos os pixels
        for x in range(0, self.window_width, max(1, self.window_width // 50)):
            dist_from_center = abs(x - self.window_width // 2) / (self.window_width // 2)
            alpha = int(100 * (1 - dist_from_center))
            if alpha > 0:
                self._glow_surface.set_at((x, 0), (100, 150, 255, alpha))
                self._glow_surface.set_at((x, 1), (80, 120, 200, alpha // 2))

        # 3. Cache da Linha Decorativa
        line_width = int(self.window_width * 0.85)
        self._deco_line_surface = pygame.Surface((line_width, 4), pygame.SRCALPHA)
        for i in range(4):
            alpha = 40 - i * 8
            if alpha > 0:
                pygame.draw.line(self._deco_line_surface, (80, 120, 200, alpha), (0, i), (line_width, i))

        self._needs_cache_rebuild = False

    def _create_slots(self):
        """Cria os slots (sem cache aqui, pois é chamado raramente)"""
        self.team_slots = []
        total_width = (self.slot_width * 6) + (self.slot_spacing * 5)
        start_x = (self.window_width - total_width) // 2
        start_y = self.window_height - self.slot_height - self.bottom_margin
        self.target_y = start_y

        for i in range(6):
            x = start_x + (i * (self.slot_width + self.slot_spacing))
            slot = GameTeamSlot(x, start_y, self.slot_width, self.slot_height, i, self.game)
            self.team_slots.append(slot)

    def update(self, dt):
        """Atualiza slots - OTIMIZADO: só recalcula cache se necessário"""
        # Verifica se dimensões mudaram
        if (self.game.screen_manager.window_width != self._last_window_width or
                self.game.screen_manager.window_height != self._last_window_height):
            self._last_window_width = self.game.screen_manager.window_width
            self._last_window_height = self.game.screen_manager.window_height
            self._calculate_dimensions()
            self._create_slots()

        # Atualiza posições dos slots
        for slot in self.team_slots:
            if abs(slot.rect.y - self.target_y) > 0.5:
                slot.rect.y += (self.target_y - slot.rect.y) * dt * 12
            slot.update(dt)

        # Reconstroi cache se necessário
        if self._needs_cache_rebuild:
            self._rebuild_cache()

    def is_dragging(self):
        return self.drag_manager.is_dragging

    def handle_event(self, event, tower_spots, camera, on_place_callback=None, on_swap_callback=None):
        if not self.visible:
            return None

        if self.drag_manager.is_dragging:
            if event.type == pygame.MOUSEMOTION:
                world_pos = self.game.screen_manager.get_mouse_world_position(event.pos, camera)
                if world_pos:
                    game_scene = self.game.current_scene
                    placement_manager = getattr(game_scene, 'placement_manager', None)
                    self.drag_manager.update_drag(
                        event.pos, world_pos, tower_spots,
                        placement_manager.placed_pokemon if placement_manager else [],
                        camera, placement_manager
                    )

            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                return self.drag_manager.stop_drag(tower_spots, on_place_callback, on_swap_callback)

            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self.drag_manager.cancel_drag()
            return None

        if event.type == pygame.VIDEORESIZE:
            self._calculate_dimensions()
            self._create_slots()
            return None

        for slot in self.team_slots:
            result = slot.handle_event(event, self.game.player.bag)
            if result and isinstance(result, dict):
                if result.get('action') == 'start_drag':
                    mouse_pos = pygame.mouse.get_pos()
                    world_pos = self.game.screen_manager.get_mouse_world_position(mouse_pos, camera)
                    if world_pos:
                        self.drag_manager.start_drag(result['slot_index'], result['pokemon'], mouse_pos, world_pos)
                        slot.start_drag()
                    return result
                elif result.get('action') == 'open_move_select':
                    if result.get('pokemon') and self.game_scene:
                        self.game_scene.open_move_select_overlay(result['pokemon'])
                    return result
            elif result is not None:
                for s in self.team_slots:
                    s.is_selected = (s.slot_index == result)
                self.selected_slot_index = result
                return result
        return None

    def render(self, screen, camera, tower_spots):
        """Renderiza o time manager - OTIMIZADO com cache"""
        if not self.visible or not self.team_slots:
            return

        # Garante que o cache está construído
        if self._needs_cache_rebuild:
            self._rebuild_cache()

        # Render fundo via Cache
        hud_y = self.team_slots[0].rect.y - 20

        if self._bg_surface:
            screen.blit(self._bg_surface, (0, hud_y))
        if self._glow_surface:
            screen.blit(self._glow_surface, (0, hud_y - 2))

        # Linha decorativa via Cache
        if self._deco_line_surface:
            line_x = (self.window_width - self._deco_line_surface.get_width()) // 2
            screen.blit(self._deco_line_surface, (line_x, hud_y + 5))

        # Renderiza slots
        for slot in self.team_slots:
            slot.render(screen)

        # Drag manager (só renderiza se estiver arrastando)
        if self.drag_manager.is_dragging:
            self.drag_manager.render(screen, camera)

        # Expanded info (só se necessário)
        if self.expanded and self.selected_slot_index >= 0:
            self._render_expanded_info(screen)

    def _render_expanded_info(self, screen):
        """Renderiza informações expandidas - OTIMIZADO"""
        if self.selected_slot_index < 0 or self.selected_slot_index >= len(self.team_slots):
            return

        slot = self.team_slots[self.selected_slot_index]
        pokemon = slot.pokemon
        if not pokemon:
            return

        panel_width, panel_height = 300, 200
        panel_x = slot.rect.centerx - panel_width // 2
        panel_y = slot.rect.y - panel_height - 25

        # Usa cores sólidas em vez de alpha blending quando possível
        pygame.draw.rect(screen, (20, 25, 35), (panel_x, panel_y, panel_width, panel_height), border_radius=15)
        pygame.draw.rect(screen, (80, 120, 200), (panel_x, panel_y, panel_width, panel_height), 2, border_radius=15)

        title_font = self._get_title_font()
        stat_font = self._get_stat_font()

        title = title_font.render(f"{pokemon.name}", True, (255, 255, 255))
        screen.blit(title, (panel_x + 20, panel_y + 20))

        stats = [
            ("HP", f"{pokemon.current_hp}/{pokemon.max_hp}"),
            ("ATK", pokemon.attack),
            ("DEF", pokemon.defense),
            ("SPD", pokemon.speed_stat)
        ]

        for i, (name, val) in enumerate(stats):
            txt = stat_font.render(f"{name}: {val}", True, (200, 200, 220))
            screen.blit(txt, (panel_x + 20 + (i // 2 * 130), panel_y + 60 + (i % 2 * 30)))

    def toggle_visibility(self):
        self.visible = not self.visible

    def on_resize(self):
        self._calculate_dimensions()
        self._create_slots()
        self._needs_cache_rebuild = True