# src/scenes/game_scene/components/overlays/move_select_overlay.py

import pygame
import math
from src.scenes.game_scene.components.overlays.base_overlay import BaseOverlay
from src.battle.effects.effect_factory import EffectFactory
from src.data.move_data import MoveData
from src.battle.attack_strategy import PriorityType

# Cache de fontes
_FONT_CACHE = {}


class MoveSelectOverlay(BaseOverlay):
    """Overlay para selecao de moves e prioridade de ataque de um Pokemon no mapa"""

    def __init__(self, game_scene, pokemon):
        super().__init__(game_scene)
        self.pokemon = pokemon

        # ===== LISTA DE PRIORIDADES (DEFINIR PRIMEIRO) =====
        self.priority_options = [
            PriorityType.FASTEST,
            PriorityType.SLOWEST,
            PriorityType.HOLDING_ITEM,
            PriorityType.LOWEST_HP,
            PriorityType.HIGHEST_HP,
            PriorityType.HIGHEST_LEVEL,
            PriorityType.LOWEST_LEVEL,
            PriorityType.AGGRESSIVE,
            PriorityType.NON_AGGRESSIVE,
            PriorityType.BOSS,
        ]

        # ===== Nomes em portugues =====
        self.priority_names = {
            PriorityType.FASTEST: "Mais Rapido",
            PriorityType.SLOWEST: "Mais Lento",
            PriorityType.HOLDING_ITEM: "Segurando Item",
            PriorityType.LOWEST_HP: "Menos Vida",
            PriorityType.HIGHEST_HP: "Mais Vida",
            PriorityType.HIGHEST_LEVEL: "Level Alto",
            PriorityType.LOWEST_LEVEL: "Level Baixo",
            PriorityType.AGGRESSIVE: "Agressivo",
            PriorityType.NON_AGGRESSIVE: "Nao Agressivo",
            PriorityType.BOSS: "Boss",
        }

        # ===== Descricoes das prioridades =====
        self.priority_descriptions = {
            PriorityType.FASTEST: "Ataca primeiro os inimigos mais rapidos",
            PriorityType.SLOWEST: "Ataca primeiro os inimigos mais lentos",
            PriorityType.HOLDING_ITEM: "Prioriza inimigos que estao segurando itens",
            PriorityType.LOWEST_HP: "Foca nos inimigos com menos vida",
            PriorityType.HIGHEST_HP: "Foca nos inimigos com mais vida",
            PriorityType.HIGHEST_LEVEL: "Prioriza inimigos de nivel mais alto",
            PriorityType.LOWEST_LEVEL: "Prioriza inimigos de nivel mais baixo",
            PriorityType.AGGRESSIVE: "Foca em inimigos agressivos primeiro",
            PriorityType.NON_AGGRESSIVE: "Foca em inimigos nao agressivos primeiro",
            PriorityType.BOSS: "Sempre foca no Boss primeiro",
        }

        # ===== VARIAVEIS DE SELECAO =====
        self.selected_index = pokemon.current_move_index if hasattr(pokemon, 'current_move_index') else 0
        self.selected_priority_index = self._get_priority_index()
        self.hovered_index = -1
        self.hovered_priority_index = -1
        self.animation_time = 0
        self.confirm_button_rect = None
        self.priority_panel_rect = None
        self.moves_panel_rect = None

        # Adiciona MoveData como atributo
        self.move_data = MoveData()

        # Configuracao de zoom
        self.original_camera_pos = (self.camera.x, self.camera.y)
        self.original_zoom = self.camera.zoom
        self.target_camera_pos = (pokemon.x, pokemon.y)
        self.zoom_duration = 0.3
        self.zoom_progress = 0

        # Zoom alvo
        self.target_zoom = 2.0
        self.min_zoom = 1.0
        self.max_zoom = 4.0

        # Painel lateral (direita)
        self.panel_width = 520
        self.panel_padding = 20

        # Cores do tema
        self.colors = {
            'primary': (100, 150, 255),
            'secondary': (80, 120, 200),
            'accent': (255, 215, 0),
            'bg_dark': (15, 20, 35),
            'bg_medium': (25, 30, 50),
            'bg_light': (35, 40, 65),
            'text': (255, 255, 255),
            'text_dim': (180, 180, 200),
            'border': (60, 80, 120),
            'success': (100, 200, 100),
            'warning': (255, 150, 100),
            'danger': (255, 100, 100),
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

    def _get_priority_index(self) -> int:
        """Retorna o indice da prioridade atual do Pokemon"""
        if not hasattr(self.pokemon, 'attack_priority'):
            return 0

        current_priority = self.pokemon.attack_priority.priority_type
        for i, p in enumerate(self.priority_options):
            if p == current_priority:
                return i
        return 0

    def _get_font(self, size, bold=False):
        """Obtem fonte do cache"""
        key = (size, bold)
        if key not in _FONT_CACHE:
            font = pygame.font.Font(None, size)
            if bold:
                font.set_bold(True)
            _FONT_CACHE[key] = font
        return _FONT_CACHE[key]

    def _get_move_description(self, move_name: str) -> str:
        """Obtem a descricao do movimento"""
        move_key = move_name.lower().replace(" ", "-").replace("'", "")

        effect = EffectFactory.create_effect(move_key)
        if effect and hasattr(effect, 'description') and effect.description:
            return effect.description

        config = EffectFactory.MOVE_EFFECTS.get(move_key)
        if config and config.get("description"):
            return config["description"]

        try:
            move_info = self.move_data.get_move_info(move_name)
            if move_info and move_info.get("description"):
                desc = move_info["description"]
                if desc and not desc.startswith(f"Usa {move_name}"):
                    return desc
        except Exception as e:
            print(f"[MoveSelectOverlay] Erro ao buscar descricao: {e}")

        return "Um movimento que causa dano ao oponente."

    def handle_event(self, event):
        """Processa eventos do overlay"""
        if not self.active:
            return False

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.close()
                return True
            elif event.key == pygame.K_RETURN:
                self.confirm_selection()
                return True
            elif event.key == pygame.K_UP:
                self.selected_priority_index = (self.selected_priority_index - 1) % len(self.priority_options)
                return True
            elif event.key == pygame.K_DOWN:
                self.selected_priority_index = (self.selected_priority_index + 1) % len(self.priority_options)
                return True
            elif event.key == pygame.K_RIGHT:
                if self.pokemon.moves:
                    self.selected_index = (self.selected_index + 1) % len(self.pokemon.moves)
                return True
            elif event.key == pygame.K_LEFT:
                if self.pokemon.moves:
                    self.selected_index = (self.selected_index - 1) % len(self.pokemon.moves)
                return True

        elif event.type == pygame.MOUSEMOTION:
            self._update_hover(event.pos)
            self._update_priority_hover(event.pos)

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.confirm_button_rect and self.confirm_button_rect.collidepoint(event.pos):
                self.confirm_selection()
                return True

            if self.hovered_index >= 0:
                self.selected_index = self.hovered_index
                return True

            if self.hovered_priority_index >= 0:
                self.selected_priority_index = self.hovered_priority_index
                return True

        return False

    def _update_hover(self, mouse_pos):
        """Atualiza o indice do move sob o mouse"""
        if not self.moves_panel_rect:
            self.hovered_index = -1
            return

        if not self.moves_panel_rect.collidepoint(mouse_pos):
            self.hovered_index = -1
            return

        start_y = self.moves_panel_rect.y + 115
        item_height = 105
        spacing = 8

        relative_y = mouse_pos[1] - start_y
        if relative_y >= 0:
            idx = relative_y // (item_height + spacing)
            if 0 <= idx < len(self.pokemon.moves):
                self.hovered_index = idx
                return

        self.hovered_index = -1

    def _update_priority_hover(self, mouse_pos):
        """Atualiza o hover do painel de prioridades"""
        if not self.priority_panel_rect:
            self.hovered_priority_index = -1
            return

        if not self.priority_panel_rect.collidepoint(mouse_pos):
            self.hovered_priority_index = -1
            return

        # Calcula a posicao relativa dentro do painel
        relative_x = mouse_pos[0] - self.priority_panel_rect.x
        relative_y = mouse_pos[1] - self.priority_panel_rect.y

        # Area onde os itens ficam (apos o cabecalho)
        header_height = 70  # Altura do titulo + linha
        item_height = 55

        if relative_y >= header_height:
            idx = (relative_y - header_height) // item_height
            if 0 <= idx < len(self.priority_options):
                self.hovered_priority_index = idx
                return

        self.hovered_priority_index = -1

    def _get_panel_rect(self):
        """Retorna o retangulo do painel lateral (direita)"""
        viewport = self.get_viewport_rect()
        panel_x = viewport.x + viewport.width - self.panel_width
        panel_y = viewport.y
        return pygame.Rect(panel_x, panel_y, self.panel_width, viewport.height)

    def update(self, dt):
        """Atualiza animacoes e zoom"""
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

    def close(self):
        """Fecha o overlay e restaura a camera"""
        self.active = False
        self.camera.zoom = self.original_zoom
        self.camera.x, self.camera.y = self.original_camera_pos
        self.camera._clamp_position()
        self.game_scene.close_move_select_overlay()

    def confirm_selection(self):
        """Confirma a selecao do move E da prioridade atual"""
        if self.pokemon.moves and 0 <= self.selected_index < len(self.pokemon.moves):
            self.pokemon.current_move_index = self.selected_index
            move_name = self.pokemon.moves[self.selected_index].name
            print(f"[MOVE_SELECT] {self.pokemon.name} agora usara {move_name} como ataque padrao")

        if hasattr(self.pokemon, 'attack_priority'):
            if 0 <= self.selected_priority_index < len(self.priority_options):
                selected_priority = self.priority_options[self.selected_priority_index]
                self.pokemon.attack_priority.set_priority(selected_priority)
                print(f"[PRIORITY_SELECT] {self.pokemon.name} prioridade: {selected_priority.value}")

        if hasattr(self.game_scene, 'player') and self.game_scene.player:
            self.game_scene.player.auto_save()

        self.close()

    def render(self, screen):
        """Renderiza o overlay de selecao de moves e prioridade"""
        if not self.active:
            return

        viewport = self.get_viewport_rect()

        overlay = pygame.Surface((viewport.width, viewport.height))
        overlay.set_alpha(180)
        overlay.fill((0, 0, 0))
        screen.blit(overlay, (viewport.x, viewport.y))

        self._render_priority_panel(screen, viewport)
        self._render_pokemon_area(screen, viewport)
        self._render_panel(screen, viewport)

    def _render_priority_panel(self, screen, viewport):
        """Renderiza o painel esquerdo com as prioridades de ataque"""
        panel_width = 380
        panel_rect = pygame.Rect(viewport.x + 15, viewport.y + 15, panel_width, viewport.height - 30)
        self.priority_panel_rect = panel_rect

        # Fundo do painel
        for i in range(panel_rect.height):
            progress = i / panel_rect.height
            alpha = int(200 + 55 * progress)
            color = (*self.colors['bg_dark'], alpha)
            pygame.draw.line(screen, color,
                             (panel_rect.x, panel_rect.y + i),
                             (panel_rect.x + panel_rect.width, panel_rect.y + i))

        pygame.draw.rect(screen, (*self.colors['border'], 100), panel_rect, 2, border_radius=12)

        # Titulo
        font_title = self._get_font(26, True)
        title = font_title.render("PRIORIDADE DE ATAQUE", True, self.colors['accent'])
        title_x = panel_rect.x + (panel_rect.width - title.get_width()) // 2
        screen.blit(title, (title_x, panel_rect.y + 15))

        # Linha decorativa
        line_y = panel_rect.y + 55
        pygame.draw.line(screen, self.colors['primary'],
                         (panel_rect.x + 20, line_y),
                         (panel_rect.x + panel_rect.width - 20, line_y), 2)

        # Lista de prioridades
        start_y = panel_rect.y + 70
        item_height = 55

        for i, priority in enumerate(self.priority_options):
            item_rect = pygame.Rect(panel_rect.x + 10, start_y + i * item_height,
                                    panel_rect.width - 20, item_height - 2)

            is_selected = (i == self.selected_priority_index)
            is_hovered = (i == self.hovered_priority_index)

            if is_selected:
                bg_color = (*self.colors['primary'], 80)
                border_color = self.colors['accent']
            elif is_hovered:
                bg_color = (*self.colors['secondary'], 60)
                border_color = self.colors['primary']
            else:
                bg_color = (*self.colors['bg_light'], 100)
                border_color = self.colors['border']

            pygame.draw.rect(screen, bg_color, item_rect, border_radius=8)
            pygame.draw.rect(screen, border_color, item_rect, 1, border_radius=8)

            # Nome da prioridade
            font_name = self._get_font(20, is_selected)
            name_text = self.priority_names[priority]
            name_color = self.colors['text'] if not is_selected else self.colors['accent']
            name_surf = font_name.render(name_text, True, name_color)
            screen.blit(name_surf, (item_rect.x + 12, item_rect.y + 8))

            # Descricao
            font_desc = self._get_font(14)
            desc_text = self.priority_descriptions[priority]
            if len(desc_text) > 45:
                desc_text = desc_text[:42] + "..."
            desc_surf = font_desc.render(desc_text, True, self.colors['text_dim'])
            screen.blit(desc_surf, (item_rect.x + 12, item_rect.y + 30))

            if is_selected:
                selected_rect = item_rect.inflate(-2, -2)
                pygame.draw.rect(screen, self.colors['accent'], selected_rect, 2, border_radius=7)

        # Instrucoes
        inst_y = panel_rect.bottom - 45
        font_inst = self._get_font(13)
        inst_text = font_inst.render("SETAS CIMA/BAIXO: navegar | ENTER: confirmar", True, self.colors['text_dim'])
        inst_x = panel_rect.x + (panel_rect.width - inst_text.get_width()) // 2
        screen.blit(inst_text, (inst_x, inst_y))

    def _render_pokemon_area(self, screen, viewport):
        """Renderiza a area do Pokemon com sprite proporcional"""
        screen_x, screen_y = self.screen_manager.world_to_screen(
            self.pokemon.x, self.pokemon.y, self.camera
        )

        bg_radius = 75
        bg_center = (int(screen_x), int(screen_y))

        pygame.draw.circle(screen, (*self.colors['bg_medium'], 200), bg_center, bg_radius + 8)
        pygame.draw.circle(screen, (*self.colors['bg_dark'], 180), bg_center, bg_radius + 5)

        if self.pokemon.sprite:
            target_size = 130
            original_width = self.pokemon.sprite.get_width()
            original_height = self.pokemon.sprite.get_height()

            if original_width > 0 and original_height > 0:
                scale_factor = min(target_size / original_width, target_size / original_height)
                new_width = int(original_width * scale_factor)
                new_height = int(original_height * scale_factor)

                scaled_sprite = pygame.transform.scale(self.pokemon.sprite, (new_width, new_height))
                sprite_rect = scaled_sprite.get_rect(center=(screen_x, screen_y))
                screen.blit(scaled_sprite, sprite_rect)

        font_name = self._get_font(32, True)
        name_text = f"{self.pokemon.name}"
        name_surf = font_name.render(name_text, True, self.colors['accent'])
        name_x = screen_x - name_surf.get_width() // 2
        name_y = screen_y - 110
        screen.blit(name_surf, (name_x, name_y))

        font_level = self._get_font(24, True)
        level_text = f"Lv.{self.pokemon.level}"
        level_surf = font_level.render(level_text, True, self.colors['text_dim'])
        level_x = name_x + name_surf.get_width() + 12
        level_y = name_y + (name_surf.get_height() - level_surf.get_height()) // 2
        screen.blit(level_surf, (level_x, level_y))

        self._render_hp_bar(screen, screen_x, screen_y + 80, self.pokemon)
        self._render_types(screen, screen_x, screen_y + 115, self.pokemon.types)

        if self.pokemon.moves and self.selected_index < len(self.pokemon.moves):
            selected_move = self.pokemon.moves[self.selected_index]
            font_move = self._get_font(16, True)
            move_text = f"SELECIONADO: {selected_move.name.upper()}"
            move_surf = font_move.render(move_text, True, self.colors['accent'])
            move_x = screen_x - move_surf.get_width() // 2
            move_y = screen_y + 165
            screen.blit(move_surf, (move_x, move_y))

    def _render_types(self, screen, center_x, y, types):
        """Renderiza os tipos do Pokemon"""
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
        """Renderiza o painel lateral com os moves"""
        panel_rect = self._get_panel_rect()
        self.moves_panel_rect = panel_rect

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

        self._render_panel_header(screen, panel_rect)
        self._render_moves_list(screen, panel_rect)
        self._render_confirm_button(screen, panel_rect)
        self._render_panel_instructions(screen, panel_rect)

    def _render_panel_header(self, screen, panel_rect):
        """Renderiza o cabecalho do painel"""
        font_title = self._get_font(28, True)
        font_sub = self._get_font(16)

        title = font_title.render("SELECIONAR ATAQUE", True, self.colors['accent'])
        title_x = panel_rect.x + (panel_rect.width - title.get_width()) // 2
        screen.blit(title, (title_x, panel_rect.y + 25))

        line_y = panel_rect.y + 75
        line_width = panel_rect.width - 40
        pygame.draw.line(screen, self.colors['primary'],
                         (panel_rect.x + 20, line_y),
                         (panel_rect.x + panel_rect.width - 20, line_y), 2)

        sub_text = f"Escolha o ataque de {self.pokemon.name}"
        sub_surf = font_sub.render(sub_text, True, self.colors['text_dim'])
        sub_x = panel_rect.x + (panel_rect.width - sub_surf.get_width()) // 2
        screen.blit(sub_surf, (sub_x, line_y + 12))

    def _render_moves_list(self, screen, panel_rect):
        """Renderiza a lista de moves"""
        if not self.pokemon.moves:
            font = self._get_font(20)
            no_moves = font.render("Este pokemon nao tem ataques", True, self.colors['danger'])
            no_x = panel_rect.x + (panel_rect.width - no_moves.get_width()) // 2
            no_y = panel_rect.y + 220
            screen.blit(no_moves, (no_x, no_y))
            return

        start_y = panel_rect.y + 115
        item_height = 97
        spacing = 8
        visible_count = min(len(self.pokemon.moves), 5)

        for i in range(visible_count):
            if i >= len(self.pokemon.moves):
                break

            move = self.pokemon.moves[i]
            item_y = start_y + i * (item_height + spacing)
            is_selected = (i == self.selected_index)
            is_hovered = (i == self.hovered_index)
            is_current = (i == self.pokemon.current_move_index)

            self._render_move_item(screen, panel_rect, item_y, move, is_selected, is_hovered, is_current)

    def _render_move_item(self, screen, panel_rect, y, move, is_selected, is_hovered, is_current):
        """Renderiza um item de move individual"""
        margin = 15
        item_rect = pygame.Rect(panel_rect.x + margin, y,
                                panel_rect.width - margin * 2, 97)

        if is_selected:
            bg_color = (*self.colors['primary'], 80)
            border_color = self.colors['accent']
        elif is_current:
            bg_color = (*self.colors['secondary'], 60)
            border_color = self.colors['success']
        elif is_hovered:
            bg_color = (*self.colors['secondary'], 60)
            border_color = self.colors['primary']
        else:
            bg_color = (*self.colors['bg_light'], 100)
            border_color = self.colors['border']

        pygame.draw.rect(screen, bg_color, item_rect, border_radius=12)
        pygame.draw.rect(screen, border_color, item_rect, 2, border_radius=12)

        if is_current and not is_selected:
            current_label = self._get_font(10, True).render("ATUAL", True, self.colors['success'])
            screen.blit(current_label, (item_rect.right - 55, item_rect.y + 5))

        type_name = move.type.capitalize()
        type_color = self.type_colors.get(move.type.lower(), (150, 150, 150))
        type_width = 70
        type_x = item_rect.x + 12
        type_y = item_rect.centery - 30

        type_rect = pygame.Rect(type_x, type_y, type_width, 60)
        pygame.draw.rect(screen, type_color, type_rect, border_radius=8)
        pygame.draw.rect(screen, (255, 255, 255, 100), type_rect, 2, border_radius=8)

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
            screen.blit(text2, (text2_x, type_y + 34))
        else:
            text = type_font.render(type_name, True, (255, 255, 255))
            text_x = type_x + (type_width - text.get_width()) // 2
            text_y = type_y + (60 - text.get_height()) // 2
            screen.blit(text, (text_x, text_y))

        info_x = type_x + type_width + 12

        name_font = self._get_font(20, is_selected or is_current)
        name_color = self.colors['accent'] if (is_selected or is_current) else self.colors['text']
        name_surf = name_font.render(move.name.upper(), True, name_color)
        screen.blit(name_surf, (info_x, item_rect.y + 8))

        info_font = self._get_font(14)

        category = move.category.upper() if hasattr(move, 'category') else "PHYSICAL"
        cat_color = (255, 100, 100) if category == "PHYSICAL" else (100, 100, 255)
        cat_surf = info_font.render(category, True, cat_color)
        screen.blit(cat_surf, (info_x, item_rect.y + 34))

        stats_y = item_rect.y + 54

        power_text = f"PWR: {move.power}" if move.power > 0 else "PWR: --"
        power_surf = info_font.render(power_text, True, (255, 255, 255))
        screen.blit(power_surf, (info_x, stats_y))

        pp_text = f"PP: {move.current_pp}/{move.max_pp}"
        pp_surf = info_font.render(pp_text, True, (255, 255, 255))
        screen.blit(pp_surf, (info_x + 100, stats_y))

        acc_text = f"ACC: {move.accuracy}%"
        acc_surf = info_font.render(acc_text, True, (255, 255, 255))
        screen.blit(acc_surf, (info_x + 220, stats_y))

        correct_description = self._get_move_description(move.name)

        max_desc_length = 55
        if len(correct_description) > max_desc_length:
            cut_at = correct_description[:max_desc_length].rfind(' ')
            if cut_at > 0:
                desc = correct_description[:cut_at] + "..."
            else:
                desc = correct_description[:max_desc_length] + "..."
        else:
            desc = correct_description

        desc_font = self._get_font(16)
        desc_surf = desc_font.render(desc, True, self.colors['text_dim'])
        screen.blit(desc_surf, (info_x, item_rect.y + 78))

        if is_selected:
            selected_rect = item_rect.inflate(-4, -4)
            pygame.draw.rect(screen, self.colors['accent'], selected_rect, 2, border_radius=10)

    def _render_confirm_button(self, screen, panel_rect):
        """Renderiza o botao de confirmar"""
        button_width = 200
        button_height = 50
        button_x = panel_rect.x + (panel_rect.width - button_width) // 2
        button_y = panel_rect.bottom - 120

        self.confirm_button_rect = pygame.Rect(button_x, button_y, button_width, button_height)

        mouse_pos = pygame.mouse.get_pos()
        is_hovered = self.confirm_button_rect.collidepoint(mouse_pos)

        if is_hovered:
            bg_color = self.colors['success']
            border_color = self.colors['accent']
        else:
            bg_color = self.colors['secondary']
            border_color = self.colors['primary']

        shadow_rect = self.confirm_button_rect.copy()
        shadow_rect.y += 3
        pygame.draw.rect(screen, (0, 0, 0, 100), shadow_rect, border_radius=12)

        pygame.draw.rect(screen, bg_color, self.confirm_button_rect, border_radius=12)
        pygame.draw.rect(screen, border_color, self.confirm_button_rect, 3, border_radius=12)

        font = self._get_font(24, True)
        text = font.render("CONFIRMAR", True, (255, 255, 255))
        text_x = button_x + (button_width - text.get_width()) // 2
        text_y = button_y + (button_height - text.get_height()) // 2
        screen.blit(text, (text_x, text_y))

    def _render_panel_instructions(self, screen, panel_rect):
        """Renderiza as instrucoes na parte inferior do painel"""
        inst_y = panel_rect.bottom - 55
        font = self._get_font(14)

        inst_bg = pygame.Rect(panel_rect.x + 15, inst_y - 5,
                              panel_rect.width - 30, 45)
        pygame.draw.rect(screen, (*self.colors['bg_medium'], 150), inst_bg, border_radius=8)

        instructions = [
            ("SETAS ESQ/DIR", "MOVE"),
            ("SETAS CIMA/BAIXO", "PRIORIDADE"),
            ("ENTER", "CONFIRMAR"),
            ("ESC", "FECHAR")
        ]

        total_width = 0
        for key, action in instructions:
            total_width += font.size(f"{key} {action}")[0] + 25

        start_x = panel_rect.x + (panel_rect.width - total_width) // 2
        current_x = start_x

        for key, action in instructions:
            key_surf = font.render(key, True, self.colors['accent'])
            action_surf = font.render(action, True, self.colors['text_dim'])

            screen.blit(key_surf, (current_x, inst_y))
            screen.blit(action_surf, (current_x + key_surf.get_width() + 4, inst_y))

            current_x += key_surf.get_width() + action_surf.get_width() + 25