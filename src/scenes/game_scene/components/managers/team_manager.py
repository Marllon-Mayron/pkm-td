# src/scenes/game_scene/components/managers/team_manager.py

import pygame
from src.data.pokedex import Pokedex
from src.scenes.game_scene.components.team_slot import GameTeamSlot
from src.scenes.game_scene.components.drag_drop import DragDropManager


class GameTeamManager:
    """Gerencia a HUD do time durante o jogo"""

    def __init__(self, game):
        self.game = game
        self.pokedex = Pokedex()

        # Configurações responsivas
        self.slot_width_ratio = 0.16  # 16% da largura da tela
        self.slot_height_ratio = 0.14  # 14% da altura
        self.slot_spacing_ratio = 0.012  # 1.2% da largura
        self.bottom_margin_ratio = 0.015  # 1.5% da altura

        # Lista de slots
        self.team_slots = []
        self.selected_slot_index = -1

        # Estado
        self.visible = True
        self.expanded = False

        # Animação
        self.slide_animation = 0
        self.target_y = 0

        # Drag and Drop
        self.drag_manager = DragDropManager(game)

        # Inicializa
        self._calculate_dimensions()
        self._create_slots()
        self.update_team()

    def _calculate_dimensions(self):
        """Calcula dimensões baseado no tamanho da tela"""
        self.window_width = self.game.screen_manager.window_width
        self.window_height = self.game.screen_manager.window_height

        # Tamanhos responsivos com limites
        self.slot_width = int(self.window_width * self.slot_width_ratio)
        self.slot_width = max(140, min(220, self.slot_width))

        self.slot_height = int(self.window_height * self.slot_height_ratio)
        self.slot_height = max(90, min(140, self.slot_height))

        self.slot_spacing = int(self.window_width * self.slot_spacing_ratio)
        self.slot_spacing = max(6, min(20, self.slot_spacing))

        self.bottom_margin = int(self.window_height * self.bottom_margin_ratio)

    def _create_slots(self):
        """Cria os slots com posicionamento responsivo"""
        self.team_slots = []

        total_width = (self.slot_width * 6) + (self.slot_spacing * 5)
        start_x = (self.window_width - total_width) // 2
        start_y = self.window_height - self.slot_height - self.bottom_margin
        self.target_y = start_y

        for i in range(6):
            x = start_x + (i * (self.slot_width + self.slot_spacing))
            slot = GameTeamSlot(x, start_y, self.slot_width, self.slot_height, i)
            self.team_slots.append(slot)

    def update_team(self):
        """Atualiza os slots com o time atual do jogador"""
        team = self.game.player.team

        for i, slot in enumerate(self.team_slots):
            if i < len(team):
                slot.set_pokemon(team[i])
            else:
                slot.set_pokemon(None)

    def update(self, dt):
        """Atualiza animações e estados"""
        # Animação de slide suave
        for slot in self.team_slots:
            if abs(slot.rect.y - self.target_y) > 0.5:
                new_y = slot.rect.y + (self.target_y - slot.rect.y) * dt * 12
                slot.rect.y = new_y

        # Atualiza cada slot
        for slot in self.team_slots:
            slot.update(dt)

    def is_dragging(self):
        """Verifica se está arrastando um Pokémon"""
        return self.drag_manager.is_dragging

    def handle_event(self, event, tower_spots, camera, on_place_callback=None):
        """Processa eventos nos slots com suporte a drag and drop"""
        if not self.visible:
            return None

        # Se está arrastando, passa para o drag manager
        if self.drag_manager.is_dragging:
            if event.type == pygame.MOUSEMOTION:
                # Atualiza posição do arrasto
                world_pos = self.game.screen_manager.get_mouse_world_position(
                    event.pos, camera
                )
                if world_pos:
                    self.drag_manager.update_drag(
                        event.pos, world_pos, tower_spots, camera
                    )

            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                # Finaliza arrasto
                result = self.drag_manager.stop_drag(
                    tower_spots, on_place_callback
                )
                if result:
                    # Remove Pokémon do time após colocar
                    self.game.player.team.pop(result['slot_index'])
                    self.update_team()
                return result

            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                # Cancela arrasto
                self.drag_manager.cancel_drag()

            return None

        # Se não está arrastando, processa eventos normais
        if event.type == pygame.VIDEORESIZE:
            self._calculate_dimensions()
            self._create_slots()
            self.update_team()
            return None

        for slot in self.team_slots:
            result = slot.handle_event(event)
            if result:
                if isinstance(result, dict) and result.get('action') == 'start_drag':
                    # Inicia arrasto
                    mouse_pos = pygame.mouse.get_pos()
                    world_pos = self.game.screen_manager.get_mouse_world_position(
                        mouse_pos, camera
                    )
                    if world_pos:
                        self.drag_manager.start_drag(
                            result['slot_index'],
                            result['pokemon'],
                            mouse_pos,
                            world_pos
                        )
                        slot.start_drag()
                    return result
                else:
                    # Seleção normal
                    for s in self.team_slots:
                        s.is_selected = (s.slot_index == result)
                    self.selected_slot_index = result

                    if slot.pokemon:
                        print(f"✨ {slot.pokemon.name} selecionado! Lv.{slot.pokemon.level}")

                        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                            if hasattr(event, 'clicks') and event.clicks >= 2:
                                self.expanded = not self.expanded

                    return result
        return None

    def render(self, screen, camera, tower_spots):
        """Renderiza a HUD do time"""
        if not self.visible:
            return

        # Fundo gradiente moderno
        self._draw_modern_background(screen)

        # Linha decorativa com brilho
        if self.team_slots:
            line_y = self.team_slots[0].rect.y - 15
            self._draw_decorative_line(screen, line_y)

        # Renderiza slots
        for slot in self.team_slots:
            slot.render(screen, self.pokedex)

        # Renderiza drag and drop (se ativo)
        if self.drag_manager.is_dragging:
            self.drag_manager.render(screen, camera)

        # Modo expandido
        if self.expanded and self.selected_slot_index >= 0:
            self._render_expanded_info(screen)

        # Se está arrastando, desenha indicadores nos spots
        if self.drag_manager.is_dragging:
            self._render_spot_indicators(screen, camera, tower_spots)

    def _draw_modern_background(self, screen):
        """Desenha fundo moderno com gradiente e efeito glass"""
        if not self.team_slots:
            return

        # Área da HUD
        hud_y = self.team_slots[0].rect.y - 20
        hud_height = self.slot_height + 40

        # Gradiente vertical com efeito glass
        for i in range(hud_height):
            # Efeito glass: mais transparente em cima, mais sólido embaixo
            progress = i / hud_height
            alpha = int(80 + 100 * progress)

            color = (10, 15, 25, alpha)

            line_surface = pygame.Surface((self.window_width, 1), pygame.SRCALPHA)
            line_surface.fill(color)
            screen.blit(line_surface, (0, hud_y + i))

        # Efeito de brilho na borda superior
        glow_surface = pygame.Surface((self.window_width, 4), pygame.SRCALPHA)
        for x in range(self.window_width):
            dist_from_center = abs(x - self.window_width // 2) / (self.window_width // 2)
            alpha = int(100 * (1 - dist_from_center))
            glow_surface.set_at((x, 0), (100, 150, 255, alpha))
            glow_surface.set_at((x, 1), (80, 120, 200, alpha // 2))

        screen.blit(glow_surface, (0, hud_y - 4))

    def _draw_decorative_line(self, screen, y):
        """Desenha linha decorativa com efeito de brilho"""
        if y <= 0:
            return

        # Linha principal
        line_width = int(self.window_width * 0.85)
        line_x = (self.window_width - line_width) // 2

        # Efeito de brilho
        for i in range(4):
            alpha = 40 - i * 8
            if alpha > 0:
                line_color = (80, 120, 200, alpha)
                line_surface = pygame.Surface((line_width, 2), pygame.SRCALPHA)

                # Gradiente nas pontas
                for x in range(line_width):
                    dist_from_edge = min(x, line_width - x) / 50
                    dist_from_edge = min(1.0, dist_from_edge)
                    point_alpha = int(alpha * dist_from_edge)

                    if point_alpha > 0:
                        line_surface.set_at((x, 0), (line_color[0], line_color[1], line_color[2], point_alpha))

                screen.blit(line_surface, (line_x, y + i))

    def _render_expanded_info(self, screen):
        """Renderiza informações expandidas do Pokémon selecionado"""
        if self.selected_slot_index < 0 or self.selected_slot_index >= len(self.team_slots):
            return

        slot = self.team_slots[self.selected_slot_index]
        if not slot.pokemon:
            return

        pokemon = slot.pokemon

        # Painel responsivo
        panel_width = min(350, int(self.window_width * 0.25))
        panel_height = min(250, int(self.window_height * 0.3))
        panel_x = slot.rect.centerx - panel_width // 2
        panel_y = slot.rect.y - panel_height - 25

        # Fundo com efeito glass
        panel = pygame.Surface((panel_width, panel_height), pygame.SRCALPHA)

        # Gradiente
        for y in range(panel_height):
            progress = y / panel_height
            alpha = int(200 + 55 * (1 - progress))
            color = (20, 25, 35, alpha)
            panel.fill(color, (0, y, panel_width, 1))

        # Borda com brilho
        pygame.draw.rect(panel, (80, 120, 200, 150), panel.get_rect(), 2, border_radius=15)

        screen.blit(panel, (panel_x, panel_y))

        # Informações
        title_font = pygame.font.Font(None, int(panel_height * 0.12))
        stat_font = pygame.font.Font(None, int(panel_height * 0.09))

        y = panel_y + 20
        x = panel_x + 20

        # Título
        title = title_font.render(f"{pokemon.name} - Detalhes", True, (255, 255, 255))
        screen.blit(title, (x, y))
        y += 35

        # Stats em grid
        stats = [
            ("HP", f"{pokemon.current_hp}/{pokemon.max_hp}"),
            ("ATK", str(pokemon.attack)),
            ("DEF", str(pokemon.defense)),
            ("SPD", str(pokemon.speed))
        ]

        col_width = panel_width // 2 - 30

        for i, (stat_name, stat_value) in enumerate(stats):
            col = i % 2
            row = i // 2

            stat_x = x + (col * col_width)
            stat_y = y + (row * 30)

            # Nome do stat
            name_text = stat_font.render(stat_name, True, (150, 150, 170))
            screen.blit(name_text, (stat_x, stat_y))

            # Valor do stat
            value_text = stat_font.render(stat_value, True, (255, 255, 255))
            screen.blit(value_text, (stat_x + 50, stat_y))

    def _render_spot_indicators(self, screen, camera, tower_spots):
        """Renderiza indicadores nos spots disponíveis durante arrasto"""
        for spot in tower_spots:
            # Agora acessa como atributo, não como dicionário
            spot_x, spot_y = self.game.screen_manager.world_to_screen(
                spot.x, spot.y, camera
            )

            # Verifica se é o spot hovered
            is_hovered = (self.drag_manager.hovered_spot == spot)

            # Cor baseada no estado e ocupação
            if spot.occupied:
                # Spot ocupado - não pode colocar
                color = (150, 150, 150)
                alpha = 100
                radius = 20
            elif is_hovered:
                color = (0, 255, 100)
                alpha = 200
                radius = 25
            else:
                color = (100, 100, 150)
                alpha = 100
                radius = 20

            # Círculo do spot
            spot_surface = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
            pygame.draw.circle(spot_surface, (*color, alpha),
                               (radius, radius), radius, 2)

            # Preenchimento sutil
            pygame.draw.circle(spot_surface, (*color, alpha // 3),
                               (radius, radius), radius - 2)

            screen.blit(spot_surface, (spot_x - radius, spot_y - radius))

            # Se ocupado, desenha um "X"
            if spot.occupied:
                x_surface = pygame.Surface((20, 20), pygame.SRCALPHA)
                pygame.draw.line(x_surface, (255, 100, 100, 200), (2, 2), (18, 18), 3)
                pygame.draw.line(x_surface, (255, 100, 100, 200), (18, 2), (2, 18), 3)
                screen.blit(x_surface, (spot_x - 10, spot_y - 10))

    def toggle_visibility(self):
        """Alterna visibilidade do time"""
        self.visible = not self.visible
        print(f"👥 Time {'visível' if self.visible else 'oculto'}")

    def on_resize(self):
        """Chamado quando a janela é redimensionada"""
        self._calculate_dimensions()
        self._create_slots()
        self.update_team()