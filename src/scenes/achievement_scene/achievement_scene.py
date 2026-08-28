# src/scenes/achievement_scene/achievement_scene.py

import pygame
from typing import List, Optional
from src.scenes.base_scene import BaseScene
from src.data.achievement_data import Achievement, AchievementRarity
from src.managers.achievement_manager import AchievementManager


class AchievementScene(BaseScene):
    """Tela de conquistas do jogador"""

    def __init__(self, game):
        super().__init__(game)
        self.player = game.player
        self.achievement_manager = self.player.achievement_manager

        # Dimensoes
        self.card_height = 90
        self.card_spacing = 10
        self.padding = 20
        self.top_margin = 140

        # Scroll
        self.scroll_offset = 0
        self.max_scroll = 0
        self.scroll_speed = 20

        # Botoes
        self.back_button_rect = None
        self.back_hovered = False

        # ===== DROPDOWN DE RARIDADE =====
        self.rarity_options = [
            {"id": None, "label": "Todas as raridades"},
            {"id": AchievementRarity.COMMON, "label": "Comum"},
            {"id": AchievementRarity.UNCOMMON, "label": "Incomum"},
            {"id": AchievementRarity.RARE, "label": "Raro"},
            {"id": AchievementRarity.EPIC, "label": "Epico"},
            {"id": AchievementRarity.LEGENDARY, "label": "Lendario"},
        ]
        self.selected_rarity_index = 0
        self.dropdown_open = False
        self.dropdown_rect = None
        self.dropdown_items_rects = []
        self.dropdown_hovered_index = -1

        # ===== FILTRO DE TEXTO =====
        self.filter_text: str = ""
        self.filter_input_rect = None
        self.filter_input_active = False
        self.filter_cursor_timer = 0

        # Conquistas filtradas
        self.achievements: List[Achievement] = []
        self._refresh_achievements()

        # ===== CORES =====
        self.colors = {
            'bg': (12, 15, 30),
            'bg_secondary': (20, 24, 45),
            'bg_card': (30, 34, 58),
            'bg_card_hover': (40, 44, 68),
            'bg_card_unlocked': (30, 50, 40),
            'text': (235, 235, 245),
            'text_dim': (180, 185, 200),
            'text_muted': (120, 125, 145),
            'border': (50, 60, 90),
            'border_accent': (80, 120, 200),
            'locked': (70, 75, 90),
            'unlocked': (100, 220, 100),
            'dropdown_bg': (25, 28, 50),
            'dropdown_hover': (40, 50, 80),
            'dropdown_border': (60, 70, 100),
            'input_bg': (22, 26, 45),
            'input_border': (50, 60, 90),
            'input_active': (80, 120, 200),
            'scroll_bg': (20, 24, 42),
            'scroll_thumb': (60, 80, 140),
            'filter_active': (50, 70, 120),  # COR ADICIONADA
            'scroll_thumb_hover': (80, 110, 180),  # COR ADICIONADA
        }

        # Cache
        self._font_cache = {}
        self._rarity_colors_cache = {}

        # Estado do scroll
        self.dragging_scroll = False
        self.scroll_drag_start_y = 0
        self.scroll_drag_offset = 0
        self._scroll_bar_rect = None
        self._scroll_bar_area = None

    def _get_font(self, size, bold=False):
        """Obtem fonte do cache"""
        key = (size, bold)
        if key not in self._font_cache:
            font = pygame.font.Font(None, size)
            if bold:
                font.set_bold(True)
            self._font_cache[key] = font
        return self._font_cache[key]

    def _get_rarity_color(self, rarity: AchievementRarity) -> tuple:
        """Retorna a cor de uma raridade"""
        if rarity == AchievementRarity.COMMON:
            return (150, 150, 150)
        elif rarity == AchievementRarity.UNCOMMON:
            return (100, 200, 100)
        elif rarity == AchievementRarity.RARE:
            return (100, 150, 255)
        elif rarity == AchievementRarity.EPIC:
            return (200, 100, 255)
        elif rarity == AchievementRarity.LEGENDARY:
            return (255, 215, 0)
        return (150, 150, 150)

    def _refresh_achievements(self):
        """Atualiza lista de conquistas com filtros aplicados"""
        all_achievements = self.achievement_manager.get_all_achievements()

        # Aplica filtro de raridade
        selected_rarity = self.rarity_options[self.selected_rarity_index]["id"]
        if selected_rarity:
            all_achievements = [a for a in all_achievements if a.rarity == selected_rarity]

        # Aplica filtro de texto
        if self.filter_text.strip():
            search_lower = self.filter_text.lower().strip()
            all_achievements = [
                a for a in all_achievements
                if search_lower in a.title.lower() or search_lower in a.description.lower()
            ]

        # Ordena: desbloqueadas primeiro, depois por raridade
        all_achievements.sort(
            key=lambda a: (
                0 if a.unlocked else 1,
                self._rarity_order(a.rarity)
            )
        )

        self.achievements = all_achievements

        # Calcula scroll maximo
        total_height = len(self.achievements) * (self.card_height + self.card_spacing)
        visible_height = self.game.screen_manager.window_height - self.top_margin - 40
        self.max_scroll = max(0, total_height - visible_height)
        self.scroll_offset = min(self.scroll_offset, self.max_scroll)

    def _rarity_order(self, rarity: AchievementRarity) -> int:
        """Retorna ordem de raridade para sorting"""
        order = {
            AchievementRarity.COMMON: 0,
            AchievementRarity.UNCOMMON: 1,
            AchievementRarity.RARE: 2,
            AchievementRarity.EPIC: 3,
            AchievementRarity.LEGENDARY: 4
        }
        return order.get(rarity, 0)

    def _get_clip_rect(self):
        """Retorna a area de clipping para a lista de conquistas"""
        start_y = self.top_margin
        return pygame.Rect(
            20, start_y,
            self.game.screen_manager.window_width - 50,
            self.game.screen_manager.window_height - start_y - 30
        )

    def handle_event(self, event):
        # ===== INPUT DE FILTRO =====
        if self.filter_input_active:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    self.filter_input_active = False
                    self._refresh_achievements()
                    return True
                elif event.key == pygame.K_ESCAPE:
                    self.filter_input_active = False
                    self.filter_text = ""
                    self._refresh_achievements()
                    return True
                elif event.key == pygame.K_BACKSPACE:
                    self.filter_text = self.filter_text[:-1]
                    self._refresh_achievements()
                else:
                    if event.unicode.isprintable():
                        self.filter_text += event.unicode
                        self._refresh_achievements()
                return True

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self.filter_input_rect and not self.filter_input_rect.collidepoint(event.pos):
                    self.filter_input_active = False
                    return True
            return False

        # ===== DROPDOWN =====
        if self.dropdown_open:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for i, item_rect in enumerate(self.dropdown_items_rects):
                    if item_rect.collidepoint(event.pos):
                        self.selected_rarity_index = i
                        self.dropdown_open = False
                        self._refresh_achievements()
                        return True

                if self.dropdown_rect and not self.dropdown_rect.collidepoint(event.pos):
                    self.dropdown_open = False
                    return True

            elif event.type == pygame.MOUSEMOTION:
                self.dropdown_hovered_index = -1
                for i, item_rect in enumerate(self.dropdown_items_rects):
                    if item_rect.collidepoint(event.pos):
                        self.dropdown_hovered_index = i
                        break

        # ===== SCROLL =====
        if event.type == pygame.MOUSEWHEEL:
            self.scroll_offset -= event.y * self.scroll_speed
            self.scroll_offset = max(0, min(self.max_scroll, self.scroll_offset))
            return True

        # ===== MOUSE =====
        elif event.type == pygame.MOUSEMOTION:
            if self.back_button_rect:
                self.back_hovered = self.back_button_rect.collidepoint(event.pos)

            if self.dragging_scroll:
                clip_rect = self._get_clip_rect()
                scroll_bar_area = pygame.Rect(
                    clip_rect.right + 5,
                    clip_rect.y,
                    12,
                    clip_rect.height
                )

                # Calcula a nova posicao baseada no mouse
                rel_y = event.pos[1] - scroll_bar_area.y
                scroll_ratio = max(0, min(1, rel_y / scroll_bar_area.height))
                self.scroll_offset = scroll_ratio * self.max_scroll
                self.scroll_offset = max(0, min(self.max_scroll, self.scroll_offset))

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            # Botao voltar
            if self.back_button_rect and self.back_button_rect.collidepoint(event.pos):
                self._go_back()
                return True

            # Abre/fecha dropdown
            if self.dropdown_rect and self.dropdown_rect.collidepoint(event.pos):
                self.dropdown_open = not self.dropdown_open
                return True

            # Input de busca
            if self.filter_input_rect and self.filter_input_rect.collidepoint(event.pos):
                self.filter_input_active = True
                return True

            # Scroll bar - CLICK NA AREA DA BARRA
            clip_rect = self._get_clip_rect()
            scroll_bar_area = pygame.Rect(
                clip_rect.right + 5,
                clip_rect.y,
                12,
                clip_rect.height
            )

            if scroll_bar_area.collidepoint(event.pos):
                self.dragging_scroll = True
                # Calcula a posicao inicial
                rel_y = event.pos[1] - scroll_bar_area.y
                scroll_ratio = max(0, min(1, rel_y / scroll_bar_area.height))
                self.scroll_offset = scroll_ratio * self.max_scroll
                self.scroll_offset = max(0, min(self.max_scroll, self.scroll_offset))
                return True

        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1 and self.dragging_scroll:
                self.dragging_scroll = False

        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                if self.dropdown_open:
                    self.dropdown_open = False
                    return True
                self._go_back()
                return True
            elif event.key == pygame.K_f:
                self.filter_input_active = True
                return True

        return False

    def _go_back(self):
        """Volta para a tela anterior"""
        from src.scenes.phase_selector.phase_select_scene import PhaseSelectScene
        self.game.phase_select_scene = PhaseSelectScene(self.game)
        self.game.current_scene = self.game.phase_select_scene

    def fixed_update(self, dt):
        self.filter_cursor_timer += dt

    def render(self, screen):
        # Fundo
        screen.fill(self.colors['bg'])

        # Titulo
        title_font = self._get_font(40, True)
        title = title_font.render("CONQUISTAS", True, self.colors['text'])
        title_x = (self.game.screen_manager.window_width - title.get_width()) // 2
        screen.blit(title, (title_x, 18))

        # Linha separadora
        line_y = 68
        pygame.draw.line(screen, self.colors['border'],
                         (50, line_y), (self.game.screen_manager.window_width - 50, line_y), 2)

        # Estatisticas
        stat_font = self._get_font(18)
        unlocked = self.achievement_manager.get_unlocked_count()
        total = self.achievement_manager.get_total_count()

        stat_text = f"{unlocked} / {total} desbloqueadas"
        stat_surf = stat_font.render(stat_text, True, self.colors['text_dim'])
        stat_x = self.game.screen_manager.window_width - stat_surf.get_width() - 30
        screen.blit(stat_surf, (stat_x, 30))

        # Botao voltar
        self._render_back_button(screen)

        # ===== FILTROS =====
        self._render_filters(screen)

        # ===== LISTA DE CONQUISTAS =====
        if self.achievements:
            self._render_achievement_list(screen)
        else:
            self._render_empty_message(screen)

    def _render_back_button(self, screen):
        """Renderiza botao voltar"""
        self.back_button_rect = pygame.Rect(20, 20, 110, 40)

        if self.back_hovered:
            bg_color = self.colors['bg_card_hover']
            border_color = self.colors['border_accent']
        else:
            bg_color = self.colors['bg_card']
            border_color = self.colors['border']

        pygame.draw.rect(screen, bg_color, self.back_button_rect, border_radius=8)
        pygame.draw.rect(screen, border_color, self.back_button_rect, 2, border_radius=8)

        back_font = self._get_font(18, True)
        back_text = back_font.render("VOLTAR", True, self.colors['text'])
        text_x = self.back_button_rect.centerx - back_text.get_width() // 2
        text_y = self.back_button_rect.centery - back_text.get_height() // 2
        screen.blit(back_text, (text_x, text_y))

    def _render_filters(self, screen):
        """Renderiza a barra de filtros"""
        y = 80
        x = 30

        # ===== DROPDOWN DE RARIDADE =====
        label_font = self._get_font(16, True)
        label = label_font.render("Raridade:", True, self.colors['text_dim'])
        screen.blit(label, (x, y + 8))
        x += label.get_width() + 10

        # Botao do dropdown
        dropdown_width = 180
        dropdown_height = 38
        self.dropdown_rect = pygame.Rect(x, y, dropdown_width, dropdown_height)

        # Sombra
        shadow_rect = self.dropdown_rect.copy()
        shadow_rect.x += 2
        shadow_rect.y += 2
        pygame.draw.rect(screen, (0, 0, 0, 60), shadow_rect, border_radius=8)

        # Fundo
        pygame.draw.rect(screen, self.colors['dropdown_bg'], self.dropdown_rect, border_radius=8)
        pygame.draw.rect(screen, self.colors['dropdown_border'], self.dropdown_rect, 2, border_radius=8)

        # Texto selecionado
        selected_label = self.rarity_options[self.selected_rarity_index]["label"]
        dropdown_font = self._get_font(16)
        text_surf = dropdown_font.render(selected_label, True, self.colors['text'])
        screen.blit(text_surf, (self.dropdown_rect.x + 12, self.dropdown_rect.centery - text_surf.get_height() // 2))

        # Seta
        arrow = "V" if not self.dropdown_open else "^"
        arrow_surf = dropdown_font.render(arrow, True, self.colors['text_muted'])
        screen.blit(arrow_surf,
                    (self.dropdown_rect.right - 25, self.dropdown_rect.centery - arrow_surf.get_height() // 2))

        # ===== DROPDOWN ABERTO =====
        if self.dropdown_open:
            self.dropdown_items_rects = []
            item_height = 34
            total_height = len(self.rarity_options) * item_height + 4

            dropdown_list_rect = pygame.Rect(
                self.dropdown_rect.x,
                self.dropdown_rect.bottom + 2,
                self.dropdown_rect.width,
                total_height
            )

            pygame.draw.rect(screen, self.colors['dropdown_bg'], dropdown_list_rect, border_radius=8)
            pygame.draw.rect(screen, self.colors['dropdown_border'], dropdown_list_rect, 2, border_radius=8)

            for i, option in enumerate(self.rarity_options):
                item_rect = pygame.Rect(
                    dropdown_list_rect.x + 4,
                    dropdown_list_rect.y + 2 + i * item_height,
                    dropdown_list_rect.width - 8,
                    item_height - 2
                )
                self.dropdown_items_rects.append(item_rect)

                if i == self.selected_rarity_index:
                    bg_color = self.colors['filter_active']
                    text_color = self.colors['text']
                elif i == self.dropdown_hovered_index:
                    bg_color = self.colors['dropdown_hover']
                    text_color = self.colors['text']
                else:
                    bg_color = self.colors['dropdown_bg']
                    text_color = self.colors['text_dim']

                pygame.draw.rect(screen, bg_color, item_rect, border_radius=6)

                item_font = self._get_font(15)
                item_text = item_font.render(option["label"], True, text_color)
                screen.blit(item_text, (item_rect.x + 12, item_rect.centery - item_text.get_height() // 2))

                if i == self.selected_rarity_index:
                    check = item_font.render("X", True, self.colors['unlocked'])
                    screen.blit(check, (item_rect.right - 25, item_rect.centery - check.get_height() // 2))

        # ===== INPUT DE BUSCA =====
        search_x = self.dropdown_rect.right + 20
        search_width = 250
        search_height = 38

        self.filter_input_rect = pygame.Rect(search_x, y, search_width, search_height)

        if self.filter_input_active:
            border_color = self.colors['input_active']
            bg_color = self.colors['bg_card_hover']
        else:
            border_color = self.colors['input_border']
            bg_color = self.colors['input_bg']

        shadow_rect = self.filter_input_rect.copy()
        shadow_rect.x += 2
        shadow_rect.y += 2
        pygame.draw.rect(screen, (0, 0, 0, 60), shadow_rect, border_radius=8)

        pygame.draw.rect(screen, bg_color, self.filter_input_rect, border_radius=8)
        pygame.draw.rect(screen, border_color, self.filter_input_rect, 2, border_radius=8)

        input_font = self._get_font(16)
        display_text = self.filter_text

        if self.filter_input_active and int(self.filter_cursor_timer * 2) % 2 == 0:
            display_text += "|"

        text_color = self.colors['text'] if display_text else self.colors['text_muted']
        text_surf = input_font.render(display_text or "Buscar conquista...", True, text_color)
        text_x = self.filter_input_rect.x + 12
        text_y = self.filter_input_rect.centery - text_surf.get_height() // 2
        screen.blit(text_surf, (text_x, text_y))

        # Linha separadora
        filter_y = y + search_height + 14
        pygame.draw.line(screen, self.colors['border'],
                         (20, filter_y), (self.game.screen_manager.window_width - 20, filter_y), 1)

    def _render_empty_message(self, screen):
        """Renderiza mensagem quando nao ha conquistas"""
        y = self.top_margin + 60

        font = self._get_font(26)
        if self.filter_text or self.selected_rarity_index > 0:
            text = font.render("Nenhuma conquista encontrada com esses filtros", True, self.colors['text_muted'])
        else:
            text = font.render("Nenhuma conquista disponivel", True, self.colors['text_muted'])

        text_x = (self.game.screen_manager.window_width - text.get_width()) // 2
        screen.blit(text, (text_x, y))

    def _render_achievement_list(self, screen):
        """Renderiza a lista de conquistas com scroll"""
        clip_rect = self._get_clip_rect()

        # Cria superficie para renderizar com scroll
        list_height = len(self.achievements) * (self.card_height + self.card_spacing)
        surface = pygame.Surface((clip_rect.width, list_height), pygame.SRCALPHA)

        y = 0
        for i, achievement in enumerate(self.achievements):
            card_rect = pygame.Rect(0, y, clip_rect.width, self.card_height)
            self._render_achievement_card(surface, card_rect, achievement)
            y += self.card_height + self.card_spacing

        # Aplica scroll
        scroll_y = int(self.scroll_offset)
        screen.blit(surface, (clip_rect.x, clip_rect.y - scroll_y),
                    area=pygame.Rect(0, scroll_y, clip_rect.width, clip_rect.height))

        # Barra de scroll
        if self.max_scroll > 0:
            self._render_scrollbar(screen, clip_rect)

    def _render_achievement_card(self, surface, rect: pygame.Rect, achievement: Achievement):
        """Renderiza um card de conquista"""
        is_unlocked = achievement.unlocked
        rarity_color = self._get_rarity_color(achievement.rarity)

        if is_unlocked:
            bg_color = self.colors['bg_card_unlocked']
            border_color = rarity_color
        else:
            bg_color = self.colors['bg_card']
            border_color = self.colors['locked']

        # Sombra
        shadow_rect = rect.copy()
        shadow_rect.x += 3
        shadow_rect.y += 3
        pygame.draw.rect(surface, (0, 0, 0, 80), shadow_rect, border_radius=10)

        # Fundo
        pygame.draw.rect(surface, bg_color, rect, border_radius=10)
        pygame.draw.rect(surface, border_color, rect, 2, border_radius=10)

        # Status
        status_font = self._get_font(14, True)
        if is_unlocked:
            status_text = "DESBLOQUEADA"
            status_color = self.colors['unlocked']
        else:
            progress = self.achievement_manager.get_progress(achievement.id)
            if progress[1] > 1:
                status_text = f"PROGRESSO: {progress[0]}/{progress[1]}"
                status_color = self.colors['text_dim']
            else:
                status_text = "BLOQUEADA"
                status_color = self.colors['locked']

        status_surf = status_font.render(status_text, True, status_color)
        status_x = rect.right - status_surf.get_width() - 15
        status_y = rect.y + 8
        surface.blit(status_surf, (status_x, status_y))

        # Raridade
        rarity_font = self._get_font(12, True)
        rarity_names = {
            AchievementRarity.COMMON: "COMUM",
            AchievementRarity.UNCOMMON: "INCOMUM",
            AchievementRarity.RARE: "RARO",
            AchievementRarity.EPIC: "EPICO",
            AchievementRarity.LEGENDARY: "LENDARIO"
        }
        rarity_text = rarity_names.get(achievement.rarity, "---")
        rarity_surf = rarity_font.render(rarity_text, True, rarity_color if is_unlocked else self.colors['locked'])
        surface.blit(rarity_surf, (rect.x + 15, rect.y + 8))

        # Titulo
        title_font = self._get_font(22, True)
        title_color = self.colors['text'] if is_unlocked else self.colors['locked']
        title_surf = title_font.render(achievement.title, True, title_color)
        surface.blit(title_surf, (rect.x + 15, rect.y + 30))

        # Descricao
        desc_font = self._get_font(16)
        desc_color = self.colors['text_dim'] if is_unlocked else self.colors['text_muted']
        desc_surf = desc_font.render(achievement.description, True, desc_color)
        surface.blit(desc_surf, (rect.x + 15, rect.y + 56))

        # Data e Fase
        if is_unlocked and achievement.unlocked_at:
            info_font = self._get_font(13)
            info_color = self.colors['text_muted']

            info_text = f"Obtido em {achievement.unlocked_at}"
            if achievement.unlocked_phase:
                info_text += f"  |  Fase {achievement.unlocked_phase}"

            info_surf = info_font.render(info_text, True, info_color)
            surface.blit(info_surf, (rect.x + 15, rect.y + 76))

        # Recompensas
        reward_font = self._get_font(14)
        rewards_text = []
        if "gold" in achievement.rewards:
            rewards_text.append(f"Ouro: {achievement.rewards['gold']}")
        if "xp" in achievement.rewards:
            rewards_text.append(f"XP: {achievement.rewards['xp']}")

        reward_str = "  |  ".join(rewards_text)
        reward_surf = reward_font.render(reward_str, True, self.colors['text_muted'])
        reward_x = rect.right - reward_surf.get_width() - 15
        reward_y = rect.y + 32
        surface.blit(reward_surf, (reward_x, reward_y))

        # Barra de progresso
        if not is_unlocked:
            progress = self.achievement_manager.get_progress(achievement.id)
            if progress[1] > 1:
                bar_x = rect.x + 15
                bar_y = rect.y + 76
                bar_width = min(200, rect.width - 30)
                bar_height = 4

                pygame.draw.rect(surface, (40, 45, 60), (bar_x, bar_y, bar_width, bar_height), border_radius=2)

                if progress[0] > 0:
                    progress_width = int((progress[0] / progress[1]) * bar_width)
                    if progress_width > 0:
                        pygame.draw.rect(surface, rarity_color, (bar_x, bar_y, progress_width, bar_height),
                                         border_radius=2)

    def _render_scrollbar(self, screen, clip_rect):
        """Renderiza barra de scroll"""
        scrollbar_width = 10
        scrollbar_x = clip_rect.right + 5

        # Fundo da barra
        scrollbar_height = clip_rect.height
        scrollbar_rect = pygame.Rect(scrollbar_x, clip_rect.y, scrollbar_width, scrollbar_height)
        self._scroll_bar_area = scrollbar_rect
        pygame.draw.rect(screen, self.colors['scroll_bg'], scrollbar_rect, border_radius=5)
        pygame.draw.rect(screen, self.colors['border'], scrollbar_rect, 1, border_radius=5)

        # Indicador
        if self.max_scroll > 0:
            visible_ratio = clip_rect.height / (self.max_scroll + clip_rect.height)
            thumb_height = max(35, int(scrollbar_height * visible_ratio))
            thumb_y = clip_rect.y + (self.scroll_offset / self.max_scroll) * (scrollbar_height - thumb_height)

            thumb_rect = pygame.Rect(scrollbar_x + 2, thumb_y, scrollbar_width - 4, thumb_height)
            self._scroll_bar_rect = thumb_rect

            if self.dragging_scroll:
                color = self.colors['scroll_thumb_hover']
            else:
                color = self.colors['scroll_thumb']

            pygame.draw.rect(screen, color, thumb_rect, border_radius=4)

            # Brilho
            glow_rect = thumb_rect.inflate(-2, -2)
            pygame.draw.rect(screen, (100, 120, 180, 30), glow_rect, border_radius=3)