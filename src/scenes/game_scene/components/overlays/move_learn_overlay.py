# src/scenes/game_scene/components/overlays/move_learn_overlay.py

import pygame
from src.scenes.game_scene.components.overlays.base_overlay import BaseOverlay

_FONT_CACHE = {}


class MoveLearnOverlay(BaseOverlay):
    """Overlay para quando um Pokémon aprende um novo move e precisa escolher qual substituir"""

    def __init__(self, game_scene, pokemon, new_move_name):
        super().__init__(game_scene)
        self.pokemon = pokemon
        self.new_move_name = new_move_name
        self.new_move = None
        self.selected_index = -1  # -1 = não substituir, 0-3 = substituir move específico
        self.hovered_index = -1
        self.animation_time = 0

        # Busca informações do novo move
        self._load_new_move_info()

        # Configuração de zoom
        self.original_camera_pos = (self.camera.x, self.camera.y)
        self.original_zoom = self.camera.zoom
        self.target_camera_pos = (pokemon.x, pokemon.y)
        self.zoom_duration = 0.3
        self.zoom_progress = 0
        self.target_zoom = 2.2

        # Painel lateral (direita)
        self.panel_width = 520
        self.panel_padding = 20

        # Cores do tema
        self.colors = {
            'primary': (100, 150, 255),
            'secondary': (80, 120, 200),
            'accent': (255, 215, 0),
            'success': (100, 200, 100),
            'warning': (255, 150, 100),
            'danger': (255, 100, 100),
            'bg_dark': (15, 20, 35),
            'bg_medium': (25, 30, 50),
            'bg_light': (35, 40, 65),
            'text': (255, 255, 255),
            'text_dim': (180, 180, 200),
            'border': (60, 80, 120),
        }

        # Cores dos tipos
        self.type_colors = {
            'normal': (168, 168, 120), 'fire': (240, 128, 48), 'water': (104, 144, 240),
            'electric': (248, 208, 48), 'grass': (120, 200, 80), 'ice': (152, 216, 216),
            'fighting': (192, 48, 40), 'poison': (160, 64, 160), 'ground': (224, 192, 104),
            'flying': (168, 144, 240), 'psychic': (248, 88, 136), 'bug': (168, 184, 32),
            'rock': (184, 160, 56), 'ghost': (112, 88, 152), 'dragon': (112, 56, 248),
            'dark': (112, 88, 72), 'steel': (184, 184, 208), 'fairy': (238, 153, 238)
        }

    def _load_new_move_info(self):
        """Carrega informações do novo move"""
        from src.data.move_data import MoveData
        move_data = MoveData()
        move_info = move_data.get_move_info(self.new_move_name)
        if move_info:
            from src.entities.move import Move
            self.new_move = Move(self.new_move_name, move_info)

    def _get_font(self, size, bold=False):
        """Obtém fonte do cache"""
        key = (size, bold)
        if key not in _FONT_CACHE:
            font = pygame.font.Font(None, size)
            if bold:
                font.set_bold(True)
            _FONT_CACHE[key] = font
        return _FONT_CACHE[key]

    def handle_event(self, event):
        """Processa eventos do overlay"""
        if not self.active:
            return False

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                # Não aprende o novo move
                self.close(cancel=True)
                return True
            elif event.key == pygame.K_RETURN:
                self.confirm_selection()
                return True
            elif event.key == pygame.K_UP:
                if self.selected_index == -1:
                    self.selected_index = 0
                else:
                    self.selected_index = (self.selected_index - 1) % 4
                return True
            elif event.key == pygame.K_DOWN:
                if self.selected_index == -1:
                    self.selected_index = 0
                else:
                    self.selected_index = (self.selected_index + 1) % 4
                return True
            elif event.key == pygame.K_LEFT:
                if self.selected_index >= 0:
                    # Move para o slot da esquerda
                    if self.selected_index % 2 == 1:
                        self.selected_index -= 1
                return True
            elif event.key == pygame.K_RIGHT:
                if self.selected_index >= 0:
                    # Move para o slot da direita
                    if self.selected_index % 2 == 0 and self.selected_index + 1 < 4:
                        self.selected_index += 1
                return True

        elif event.type == pygame.MOUSEMOTION:
            self._update_hover(event.pos)

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.hovered_index >= 0:
                self.selected_index = self.hovered_index
                return True
            elif self._is_in_new_move_area(event.pos):
                self.selected_index = -1  # Não aprender
                return True

        return False

    def _update_hover(self, mouse_pos):
        """Atualiza o índice do move sob o mouse"""
        # Verifica hover nos moves existentes
        panel_rect = self._get_panel_rect()
        if not panel_rect.collidepoint(mouse_pos):
            self.hovered_index = -1
            return

        # Grid 2x2 para os moves existentes
        grid_x = panel_rect.x + 50
        grid_y = panel_rect.y + 200
        slot_width = (panel_rect.width - 100) // 2
        slot_height = 100

        for i in range(4):
            row = i // 2
            col = i % 2
            slot_x = grid_x + col * slot_width
            slot_y = grid_y + row * slot_height

            rect = pygame.Rect(slot_x, slot_y, slot_width - 10, slot_height - 10)
            if rect.collidepoint(mouse_pos):
                self.hovered_index = i
                return

        # Verifica hover na área "Não aprender"
        cancel_rect = self._get_cancel_rect(panel_rect)
        if cancel_rect.collidepoint(mouse_pos):
            self.hovered_index = -1
            return

        self.hovered_index = -1

    def _is_in_new_move_area(self, mouse_pos):
        """Verifica se o mouse está na área do novo move"""
        panel_rect = self._get_panel_rect()
        cancel_rect = self._get_cancel_rect(panel_rect)
        return cancel_rect.collidepoint(mouse_pos)

    def _get_cancel_rect(self, panel_rect):
        """Retorna o retângulo da opção de cancelar (não aprender)"""
        return pygame.Rect(
            panel_rect.x + 50,
            panel_rect.y + 420,
            panel_rect.width - 100,
            60
        )

    def _get_panel_rect(self):
        """Retorna o retângulo do painel lateral (direita)"""
        viewport = self.get_viewport_rect()
        panel_x = viewport.x + viewport.width - self.panel_width
        panel_y = viewport.y
        return pygame.Rect(panel_x, panel_y, self.panel_width, viewport.height)

    def update(self, dt):
        """Atualiza animações e zoom"""
        self.animation_time += dt

        if self.zoom_progress < 1.0:
            self.zoom_progress += dt / self.zoom_duration
            if self.zoom_progress > 1.0:
                self.zoom_progress = 1.0

            t = 1 - (1 - self.zoom_progress) ** 3

            current_zoom = self.original_zoom + (self.target_zoom - self.original_zoom) * t
            self.camera.zoom = current_zoom

            target_x = self.target_camera_pos[0]
            target_y = self.target_camera_pos[1]

            self.camera.x = self.original_camera_pos[0] + (target_x - self.original_camera_pos[0]) * t
            self.camera.y = self.original_camera_pos[1] + (target_y - self.original_camera_pos[1]) * t
            self.camera._clamp_position()

    def close(self, cancel=False):
        """Fecha o overlay e restaura a câmera"""
        self.active = False
        self.camera.zoom = self.original_zoom
        self.camera.x, self.camera.y = self.original_camera_pos
        self.camera._clamp_position()
        self.game_scene.close_move_learn_overlay(cancel)

    def confirm_selection(self):
        """Confirma a seleção e aprende o move"""
        if self.selected_index >= 0:
            # Substitui o move selecionado
            self.pokemon.replace_move(self.selected_index, self.new_move_name)
        else:
            # Não aprende o novo move
            print(f"[MOVES] {self.pokemon.name} decidiu não aprender {self.new_move_name}")

        self.close(cancel=(self.selected_index == -1))

    def render(self, screen):
        """Renderiza o overlay de aprendizado"""
        if not self.active:
            return

        viewport = self.get_viewport_rect()

        # Fundo escuro semi-transparente
        overlay = pygame.Surface((viewport.width, viewport.height))
        overlay.set_alpha(180)
        overlay.fill((0, 0, 0))
        screen.blit(overlay, (viewport.x, viewport.y))

        # Área do Pokémon (metade esquerda)
        self._render_pokemon_area(screen, viewport)

        # Painel lateral (direita)
        self._render_panel(screen, viewport)

    def _render_pokemon_area(self, screen, viewport):
        """Renderiza a área do Pokémon"""
        screen_x, screen_y = self.screen_manager.world_to_screen(
            self.pokemon.x, self.pokemon.y, self.camera
        )

        # Círculo de fundo
        bg_radius = 75
        bg_center = (int(screen_x), int(screen_y))

        pygame.draw.circle(screen, (*self.colors['bg_medium'], 200), bg_center, bg_radius + 8)
        pygame.draw.circle(screen, (*self.colors['bg_dark'], 180), bg_center, bg_radius + 5)

        # Renderiza o Pokémon
        if self.pokemon.sprite:
            sprite_size = 130
            scaled_sprite = pygame.transform.scale(self.pokemon.sprite, (sprite_size, sprite_size))
            sprite_rect = scaled_sprite.get_rect(center=(screen_x, screen_y))
            screen.blit(scaled_sprite, sprite_rect)

        # Nome e nível
        font_name = self._get_font(32, True)
        name_text = f"{self.pokemon.name}"
        name_surf = font_name.render(name_text, True, self.colors['accent'])
        name_x = screen_x - name_surf.get_width() // 2
        name_y = screen_y - 100
        screen.blit(name_surf, (name_x, name_y))

        font_level = self._get_font(20)
        level_text = f"Nível {self.pokemon.level}"
        level_surf = font_level.render(level_text, True, self.colors['text_dim'])
        level_x = screen_x - level_surf.get_width() // 2
        level_y = screen_y - 70
        screen.blit(level_surf, (level_x, level_y))

        # Tipos
        self._render_types(screen, screen_x, screen_y - 50, self.pokemon.types)

        # Barra de HP
        self._render_hp_bar(screen, screen_x, screen_y + 80, self.pokemon)

    def _render_types(self, screen, center_x, y, types):
        """Renderiza os tipos do Pokémon"""
        if not types:
            return

        type_font = self._get_font(16, True)
        type_spacing = 10
        total_width = 0
        type_surfs = []

        for t in types:
            type_name = t.capitalize()
            color = self.type_colors.get(t.lower(), (150, 150, 150))
            surf = type_font.render(type_name, True, (255, 255, 255))
            width = surf.get_width() + 30
            type_surfs.append((surf, color, width))
            total_width += width + type_spacing

        if total_width > 0:
            total_width -= type_spacing
            start_x = center_x - total_width // 2
            current_x = start_x

            for surf, color, width in type_surfs:
                bg_rect = pygame.Rect(current_x, y, width, 32)
                pygame.draw.rect(screen, color, bg_rect, border_radius=16)
                pygame.draw.rect(screen, (255, 255, 255, 100), bg_rect, 1, border_radius=16)

                text_x = current_x + (width - surf.get_width()) // 2
                text_y = y + (32 - surf.get_height()) // 2
                screen.blit(surf, (text_x, text_y))
                current_x += width + type_spacing

    def _render_hp_bar(self, screen, center_x, y, pokemon):
        """Renderiza a barra de HP"""
        hp_percent = pokemon.current_hp / pokemon.max_hp
        bar_width = 200
        bar_height = 14
        bar_x = center_x - bar_width // 2

        pygame.draw.rect(screen, (40, 45, 60), (bar_x, y, bar_width, bar_height), border_radius=7)

        if hp_percent > 0.6:
            color = self.colors['success']
        elif hp_percent > 0.3:
            color = self.colors['warning']
        else:
            color = self.colors['danger']

        hp_width = max(4, int(bar_width * hp_percent))
        pygame.draw.rect(screen, color, (bar_x, y, hp_width, bar_height), border_radius=7)

        font = self._get_font(14)
        hp_text = f"{pokemon.current_hp}/{pokemon.max_hp}"
        text_surf = font.render(hp_text, True, (255, 255, 255))
        text_x = center_x - text_surf.get_width() // 2
        text_y = y - 20
        screen.blit(text_surf, (text_x, text_y))

    def _render_panel(self, screen, viewport):
        """Renderiza o painel lateral com as opções"""
        panel_rect = self._get_panel_rect()

        # Fundo do painel
        for i in range(panel_rect.height):
            progress = i / panel_rect.height
            alpha = int(200 + 55 * progress)
            color = (*self.colors['bg_dark'], alpha)
            pygame.draw.line(screen, color,
                             (panel_rect.x, panel_rect.y + i),
                             (panel_rect.x + panel_rect.width, panel_rect.y + i))

        pygame.draw.line(screen, (*self.colors['primary'], 150),
                         (panel_rect.x, panel_rect.y),
                         (panel_rect.x, panel_rect.y + panel_rect.height), 3)
        pygame.draw.rect(screen, (*self.colors['border'], 100), panel_rect, 2, border_radius=12)

        # Título
        font_title = self._get_font(28, True)
        title = font_title.render("NOVO ATAQUE!", True, self.colors['accent'])
        title_x = panel_rect.x + (panel_rect.width - title.get_width()) // 2
        screen.blit(title, (title_x, panel_rect.y + 25))

        # Linha decorativa
        line_y = panel_rect.y + 75
        pygame.draw.line(screen, self.colors['primary'],
                         (panel_rect.x + 20, line_y),
                         (panel_rect.x + panel_rect.width - 20, line_y), 2)

        # Novo move
        self._render_new_move(screen, panel_rect)

        # Subtitle
        font_sub = self._get_font(16)
        sub_text = f"Escolha qual ataque {self.pokemon.name} deve esquecer:"
        sub_surf = font_sub.render(sub_text, True, self.colors['text_dim'])
        sub_x = panel_rect.x + (panel_rect.width - sub_surf.get_width()) // 2
        screen.blit(sub_surf, (sub_x, line_y + 12))

        # Grid de moves existentes
        self._render_moves_grid(screen, panel_rect)

        # Opção de não aprender
        self._render_cancel_option(screen, panel_rect)

        # Instruções
        self._render_instructions(screen, panel_rect)

    def _render_new_move(self, screen, panel_rect):
        """Renderiza o novo move que está sendo aprendido"""
        if not self.new_move:
            return

        # Área do novo move
        new_move_y = panel_rect.y + 110
        new_move_rect = pygame.Rect(panel_rect.x + 50, new_move_y,
                                    panel_rect.width - 100, 70)

        # Fundo com destaque
        pygame.draw.rect(screen, (*self.colors['success'], 80), new_move_rect, border_radius=12)
        pygame.draw.rect(screen, self.colors['success'], new_move_rect, 2, border_radius=12)

        # Tipo do move
        type_name = self.new_move.type.capitalize()
        type_color = self.type_colors.get(self.new_move.type.lower(), (150, 150, 150))
        type_width = 70
        type_x = new_move_rect.x + 10
        type_y = new_move_rect.centery - 28

        type_rect = pygame.Rect(type_x, type_y, type_width, 56)
        pygame.draw.rect(screen, type_color, type_rect, border_radius=8)

        type_font = self._get_font(13, True)
        if len(type_name) > 8:
            mid = len(type_name) // 2
            line1 = type_name[:mid]
            line2 = type_name[mid:]
            text1 = type_font.render(line1, True, (255, 255, 255))
            text2 = type_font.render(line2, True, (255, 255, 255))
            text1_x = type_x + (type_width - text1.get_width()) // 2
            text2_x = type_x + (type_width - text2.get_width()) // 2
            screen.blit(text1, (text1_x, type_y + 12))
            screen.blit(text2, (text2_x, type_y + 32))
        else:
            text = type_font.render(type_name, True, (255, 255, 255))
            text_x = type_x + (type_width - text.get_width()) // 2
            text_y = type_y + (56 - text.get_height()) // 2
            screen.blit(text, (text_x, text_y))

        # Informações do novo move
        info_x = type_x + type_width + 12

        name_font = self._get_font(22, True)
        name_surf = name_font.render(f"{self.new_move.name.upper()}", True, self.colors['accent'])
        screen.blit(name_surf, (info_x, new_move_rect.y + 8))

        info_font = self._get_font(14)
        category = self.new_move.category.upper()
        cat_color = (255, 100, 100) if category == "PHYSICAL" else (100, 100, 255)
        cat_surf = info_font.render(category, True, cat_color)
        screen.blit(cat_surf, (info_x, new_move_rect.y + 34))

        power_text = f"PWR: {self.new_move.power}" if self.new_move.power > 0 else "PWR: --"
        power_surf = info_font.render(power_text, True, (255, 255, 255))
        screen.blit(power_surf, (info_x, new_move_rect.y + 54))

        # Ícone de "NOVO!"
        new_tag = self._get_font(12, True).render("NOVO!", True, self.colors['success'])
        screen.blit(new_tag, (new_move_rect.right - 55, new_move_rect.y + 5))

    def _render_moves_grid(self, screen, panel_rect):
        """Renderiza os moves existentes em grid 2x2"""
        if not self.pokemon.moves:
            return

        grid_x = panel_rect.x + 50
        grid_y = panel_rect.y + 200
        slot_width = (panel_rect.width - 100) // 2
        slot_height = 100

        for i in range(min(4, len(self.pokemon.moves))):
            move = self.pokemon.moves[i]
            row = i // 2
            col = i % 2
            slot_x = grid_x + col * slot_width
            slot_y = grid_y + row * slot_height

            is_selected = (i == self.selected_index)
            is_hovered = (i == self.hovered_index)

            self._render_move_slot(screen, slot_x, slot_y, slot_width - 10, slot_height - 10,
                                   move, is_selected, is_hovered)

    def _render_move_slot(self, screen, x, y, width, height, move, is_selected, is_hovered):
        """Renderiza um slot de move individual"""
        # Fundo
        if is_selected:
            bg_color = (*self.colors['primary'], 80)
            border_color = self.colors['accent']
        elif is_hovered:
            bg_color = (*self.colors['secondary'], 60)
            border_color = self.colors['primary']
        else:
            bg_color = (*self.colors['bg_light'], 100)
            border_color = self.colors['border']

        rect = pygame.Rect(x, y, width, height)
        pygame.draw.rect(screen, bg_color, rect, border_radius=12)
        pygame.draw.rect(screen, border_color, rect, 2, border_radius=12)

        # Tipo do move (pequeno)
        type_name = move.type.capitalize()
        type_color = self.type_colors.get(move.type.lower(), (150, 150, 150))
        type_width = 55
        type_x = rect.x + 8
        type_y = rect.centery - 20

        type_rect = pygame.Rect(type_x, type_y, type_width, 40)
        pygame.draw.rect(screen, type_color, type_rect, border_radius=6)

        type_font = self._get_font(10, True)
        text = type_font.render(type_name[:6], True, (255, 255, 255))
        text_x = type_x + (type_width - text.get_width()) // 2
        text_y = type_y + (40 - text.get_height()) // 2
        screen.blit(text, (text_x, text_y))

        # Nome do move
        info_x = type_x + type_width + 6
        name_font = self._get_font(14, is_selected)
        name_color = self.colors['accent'] if is_selected else self.colors['text']
        name_surf = name_font.render(move.name.upper(), True, name_color)
        screen.blit(name_surf, (info_x, rect.y + 8))

        # Info resumida
        info_font = self._get_font(11)
        pp_text = f"PP: {move.current_pp}/{move.max_pp}"
        pp_surf = info_font.render(pp_text, True, self.colors['text_dim'])
        screen.blit(pp_surf, (info_x, rect.y + 32))

        power_text = f"PWR: {move.power}" if move.power > 0 else "PWR: --"
        power_surf = info_font.render(power_text, True, self.colors['text_dim'])
        screen.blit(power_surf, (info_x, rect.y + 48))

    def _render_cancel_option(self, screen, panel_rect):
        """Renderiza a opção de não aprender o novo move"""
        cancel_rect = self._get_cancel_rect(panel_rect)
        is_selected = (self.selected_index == -1)

        # Fundo
        if is_selected:
            bg_color = (*self.colors['danger'], 80)
            border_color = self.colors['danger']
        else:
            bg_color = (*self.colors['bg_medium'], 100)
            border_color = self.colors['border']

        pygame.draw.rect(screen, bg_color, cancel_rect, border_radius=12)
        pygame.draw.rect(screen, border_color, cancel_rect, 2, border_radius=12)

        # Texto
        font = self._get_font(18, is_selected)
        text = font.render("✗ NÃO APRENDER ESTE ATAQUE", True, self.colors['danger'] if is_selected else self.colors['text_dim'])
        text_x = cancel_rect.centerx - text.get_width() // 2
        text_y = cancel_rect.centery - text.get_height() // 2
        screen.blit(text, (text_x, text_y))

    def _render_instructions(self, screen, panel_rect):
        """Renderiza as instruções na parte inferior"""
        inst_y = panel_rect.bottom - 50
        font = self._get_font(12)

        inst_bg = pygame.Rect(panel_rect.x + 15, inst_y - 5,
                              panel_rect.width - 30, 40)
        pygame.draw.rect(screen, (*self.colors['bg_medium'], 150), inst_bg, border_radius=8)

        instructions = [
            ("SETAS/WASD", "NAVEGAR"),
            ("ENTER", "CONFIRMAR"),
            ("ESC", "NÃO APRENDER")
        ]

        total_width = 0
        for key, action in instructions:
            total_width += font.size(f"{key} {action}")[0] + 25

        start_x = panel_rect.x + (panel_rect.width - total_width) // 2

        for key, action in instructions:
            key_surf = font.render(key, True, self.colors['accent'])
            action_surf = font.render(action, True, self.colors['text_dim'])

            screen.blit(key_surf, (start_x, inst_y))
            screen.blit(action_surf, (start_x + key_surf.get_width() + 5, inst_y))

            start_x += key_surf.get_width() + action_surf.get_width() + 25