# src/scenes/phase_select_scene.py

"""
Tela de selecao de fases - Layout reformulado com estilo consistente
"""
import pygame
import math
from src.scenes.base_scene import BaseScene
from src.config.progress import progress_manager
from src.config.phase_catalog import phase_catalog
from src.scenes.incubator_scene.incubator_scene import IncubatorScene
from src.scenes.shop_scene.shop_scene import ShopScene
from src.scenes.pokedex_scene import PokedexScene
from src.scenes.achievement_scene.achievement_scene import AchievementScene
from src.managers.sounds.sound_manager import sound_manager, SoundEffect


class PhaseCard:
    """Card de fase estilizado com animacoes"""

    def __init__(self, phase_data, unlocked=False, completed=False):
        self.phase_data = phase_data
        self.phase_number = phase_data["number"]
        self.phase_name = phase_data["name"]
        self.chapter_id = phase_data["chapter"]
        self.phase_id = f"{self.chapter_id}-{self.phase_number}"
        self.unlocked = unlocked
        self.completed = completed

        self.rect = pygame.Rect(0, 0, 0, 0)
        self.is_hovered = False
        self._was_hovered = False

        # Animacoes
        self.scale = 1.0
        self.target_scale = 1.0
        self.glow_alpha = 0
        self.glow_direction = 1

        # Cores baseadas no status
        self._update_colors()

    def _update_colors(self):
        """Atualiza cores baseado no status"""
        if not self.unlocked:
            self.bg_color = (30, 30, 35)
            self.border_color = (50, 50, 55)
            self.text_color = (80, 80, 85)
            self.name_color = (100, 100, 105)
            self.status_color = (80, 80, 85)
            self.status_text = "BLOQUEADA"
        elif self.completed:
            self.bg_color = (35, 50, 35)
            self.border_color = (70, 120, 70)
            self.text_color = (180, 220, 180)
            self.name_color = (200, 240, 200)
            self.status_color = (140, 200, 140)
            self.status_text = "CONCLUIDA"
        else:
            self.bg_color = (40, 45, 55)
            self.border_color = (80, 100, 140)
            self.text_color = (220, 220, 240)
            self.name_color = (200, 200, 220)
            self.status_color = (140, 140, 200)
            self.status_text = "DISPONIVEL"

    def update(self, dt):
        """Atualiza animacoes"""
        self.scale += (self.target_scale - self.scale) * 0.1

        # Glow animation
        if self.is_hovered and self.unlocked:
            self.glow_alpha += self.glow_direction * 3
            if self.glow_alpha >= 120:
                self.glow_alpha = 120
                self.glow_direction = -1
            elif self.glow_alpha <= 0:
                self.glow_alpha = 0
                self.glow_direction = 1
        else:
            self.glow_alpha = max(0, self.glow_alpha - 5)

    def update_position(self, x, y, width, height):
        self.rect = pygame.Rect(x, y, width, height)

    def handle_event(self, event):
        """Processa eventos do card"""
        if event.type == pygame.MOUSEMOTION:
            was_hovered = self.is_hovered
            self.is_hovered = self.rect.collidepoint(event.pos)

            if self.is_hovered and not was_hovered and self.unlocked:
                self.target_scale = 1.05
                sound_manager.play_effect(SoundEffect.CLICK)
            elif not self.is_hovered and was_hovered:
                self.target_scale = 1.0

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.is_hovered and self.unlocked:
                sound_manager.play_effect(SoundEffect.CLICK)
                self.target_scale = 0.95
                return self.phase_number

        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self.is_hovered:
                self.target_scale = 1.05

        return None

    def render(self, screen, font_large, font_small, font_name):
        """Renderiza o card com efeitos visuais"""
        # Calcula rect com escala
        scaled_rect = self.rect.copy()
        if self.scale != 1.0:
            width_offset = (self.rect.width * (self.scale - 1)) // 2
            height_offset = (self.rect.height * (self.scale - 1)) // 2
            scaled_rect = self.rect.inflate(width_offset * 2, height_offset * 2)
            scaled_rect.center = self.rect.center

        # Sombra
        shadow_rect = scaled_rect.copy()
        shadow_rect.x += 4
        shadow_rect.y += 4
        pygame.draw.rect(screen, (10, 10, 15), shadow_rect, border_radius=12)

        # Cores com hover
        if self.is_hovered and self.unlocked:
            color = tuple(min(255, c + 20) for c in self.bg_color)
            border = tuple(min(255, c + 30) for c in self.border_color)
            name_color = tuple(min(255, c + 40) for c in self.name_color)
        else:
            color = self.bg_color
            border = self.border_color
            name_color = self.name_color

        # Fundo do card
        pygame.draw.rect(screen, color, scaled_rect, border_radius=12)
        pygame.draw.rect(screen, border, scaled_rect, 2, border_radius=12)

        # Efeito de glow
        if self.is_hovered and self.unlocked and self.glow_alpha > 0:
            glow_surface = pygame.Surface((scaled_rect.width, scaled_rect.height), pygame.SRCALPHA)
            pygame.draw.rect(glow_surface, (*border[:3], self.glow_alpha), glow_surface.get_rect(), border_radius=12)
            screen.blit(glow_surface, scaled_rect)

        # Numero da fase
        num_text = font_small.render(f"{self.phase_id}", True, self.text_color)
        screen.blit(num_text, (scaled_rect.x + 10, scaled_rect.y + 10))

        # Nome da fase (centralizado)
        self._render_wrapped_text(screen, self.phase_name, font_name, name_color,
                                  scaled_rect.centerx, scaled_rect.centery - 12)

        # Status
        status = font_small.render(self.status_text, True, self.status_color)
        status_rect = status.get_rect(center=(scaled_rect.centerx, scaled_rect.centery + 28))
        screen.blit(status, status_rect)

        # Overlay para fases bloqueadas
        if not self.unlocked:
            overlay = pygame.Surface((scaled_rect.width, scaled_rect.height), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 160))
            screen.blit(overlay, scaled_rect)

    def _render_wrapped_text(self, screen, text, font, color, center_x, center_y):
        """Renderiza texto com quebra de linha automatica"""
        words = text.split()
        if not words:
            return

        single_line = font.render(text, True, color)
        if single_line.get_width() <= self.rect.width - 30:
            text_rect = single_line.get_rect(center=(center_x, center_y))
            screen.blit(single_line, text_rect)
            return

        if len(words) == 1:
            while font.render(words[0] + "...", True, color).get_width() > self.rect.width - 30:
                words[0] = words[0][:-1]
            truncated = font.render(words[0] + "...", True, color)
            text_rect = truncated.get_rect(center=(center_x, center_y))
            screen.blit(truncated, text_rect)
            return

        mid = len(words) // 2
        line1 = " ".join(words[:mid])
        line2 = " ".join(words[mid:])

        while line1 and font.render(line1, True, color).get_width() > self.rect.width - 30:
            line1 = line1[:-1]
        while line2 and font.render(line2, True, color).get_width() > self.rect.width - 30:
            line2 = line2[:-1]

        if line1:
            surf1 = font.render(line1, True, color)
            rect1 = surf1.get_rect(center=(center_x, center_y - 10))
            screen.blit(surf1, rect1)

        if line2:
            surf2 = font.render(line2, True, color)
            rect2 = surf2.get_rect(center=(center_x, center_y + 10))
            screen.blit(surf2, rect2)


class ChapterTab:
    """Aba de capitulo estilizada"""

    def __init__(self, chapter_id, name, progress):
        self.chapter_id = chapter_id
        self.name = name
        self.progress = progress
        self.rect = pygame.Rect(0, 0, 0, 0)
        self.is_hovered = False
        self.active = False

        # Animacoes
        self.scale = 1.0
        self.target_scale = 1.0

    def update(self, dt):
        self.scale += (self.target_scale - self.scale) * 0.1

    def update_position(self, x, y, width, height):
        self.rect = pygame.Rect(x, y, width, height)

    def handle_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            was_hovered = self.is_hovered
            self.is_hovered = self.rect.collidepoint(event.pos)
            if self.is_hovered and not was_hovered:
                self.target_scale = 1.05
                sound_manager.play_effect(SoundEffect.CLICK)
            elif not self.is_hovered and was_hovered:
                self.target_scale = 1.0

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.is_hovered:
                sound_manager.play_effect(SoundEffect.CLICK)
                self.target_scale = 0.95
                return self.chapter_id

        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self.is_hovered:
                self.target_scale = 1.05

        return None

    def render(self, screen, font):
        """Renderiza a aba com estilo consistente"""
        # Rect com escala
        scaled_rect = self.rect.copy()
        if self.scale != 1.0:
            width_offset = (self.rect.width * (self.scale - 1)) // 2
            height_offset = (self.rect.height * (self.scale - 1)) // 2
            scaled_rect = self.rect.inflate(width_offset * 2, height_offset * 2)
            scaled_rect.center = self.rect.center

        # Cores baseado no estado
        if self.active:
            color = (55, 55, 70)
            border = (140, 140, 170)
            text_color = (255, 255, 255)
        elif self.is_hovered:
            color = (50, 50, 60)
            border = (110, 110, 140)
            text_color = (230, 230, 240)
        else:
            color = (35, 35, 42)
            border = (60, 60, 75)
            text_color = (160, 160, 180)

        # Sombra
        shadow_rect = scaled_rect.copy()
        shadow_rect.y += 3
        pygame.draw.rect(screen, (10, 10, 15), shadow_rect, border_radius=8)

        # Fundo
        pygame.draw.rect(screen, color, scaled_rect, border_radius=8)
        pygame.draw.rect(screen, border, scaled_rect, 2, border_radius=8)

        # Nome do capitulo
        text = font.render(self.name, True, text_color)
        text_rect = text.get_rect(center=(scaled_rect.centerx, scaled_rect.centery - 8))
        screen.blit(text, text_rect)

        # Progresso
        progress_text = f"{self.progress['completed']}/{self.progress['total']}"
        progress_surface = font.render(progress_text, True, text_color)
        progress_rect = progress_surface.get_rect(center=(scaled_rect.centerx, scaled_rect.centery + 14))
        screen.blit(progress_surface, progress_rect)

        # Barra de progresso (apenas se ativo)
        if self.active and self.progress['total'] > 0:
            bar_width = scaled_rect.width - 20
            bar_height = 3
            bar_x = scaled_rect.x + 10
            bar_y = scaled_rect.bottom - 8

            # Fundo da barra
            pygame.draw.rect(screen, (30, 30, 40), (bar_x, bar_y, bar_width, bar_height), border_radius=2)

            # Progresso
            progress_ratio = self.progress['completed'] / self.progress['total']
            if progress_ratio > 0:
                fill_width = int(bar_width * progress_ratio)
                color_progress = (100, 180, 100) if progress_ratio >= 1 else (80, 120, 200)
                pygame.draw.rect(screen, color_progress, (bar_x, bar_y, fill_width, bar_height), border_radius=2)


class PhaseSelectScene(BaseScene):
    """Tela de selecao de fases reformulada"""

    def __init__(self, game):
        super().__init__(game)

        self.progress = progress_manager
        self.catalog = phase_catalog

        self.available_chapters = sorted(self.catalog.get_all_phases().keys())

        # Capitulo atual
        if hasattr(game, 'player') and game.player and game.player.chapter_page_num > 0:
            self.current_chapter_id = game.player.chapter_page_num
            if self.current_chapter_id not in self.available_chapters:
                self.current_chapter_id = self._get_first_available_chapter()
        else:
            self.current_chapter_id = self._get_first_available_chapter()

        # Elementos da UI
        self.chapter_tabs = []
        self.phase_cards = []

        # Botoes
        self.back_button_rect = None
        self.shop_button_rect = None
        self.minigame_button_rect = None
        self.pokedex_button_rect = None
        self.achievement_button_rect = None
        self.incubator_button_rect = None

        # Hover states
        self.back_button_hovered = False
        self.shop_button_hovered = False
        self.minigame_button_hovered = False
        self.pokedex_button_hovered = False
        self.achievement_button_hovered = False
        self.incubator_button_hovered = False

        # Scroll
        self.scroll_y = 0
        self.scroll_target = 0
        self.max_scroll = 0
        self.dragging_scroll = False
        self.last_mouse_y = 0

        # Estado
        self.layout_initialized = False
        self.last_window_size = (self.screen_manager.window_width, self.screen_manager.window_height)
        self.dev_mode = True
        self._animation_timer = 0
        self._music_started = False

        # Fontes
        self.title_font = pygame.font.Font(None, 52)
        self.tab_font = pygame.font.Font(None, 20)
        self.phase_font_large = pygame.font.Font(None, 34)
        self.phase_font_small = pygame.font.Font(None, 15)
        self.phase_font_name = pygame.font.Font(None, 17)
        self.button_font = pygame.font.Font(None, 22)

        # Inicializa dados
        self.refresh_data()
        self._start_phase_select_music()

    # ======================================================================
    # METODOS DE INICIALIZACAO
    # ======================================================================

    def _start_phase_select_music(self):
        """Inicia a musica da tela de selecao de fases"""
        if not self._music_started:
            success = sound_manager.play_team_select_music(loop=True)
            if success:
                self._music_started = True
                print("[PHASE_SELECT] Musica iniciada: Come_Along")
            else:
                success = sound_manager.play_menu_music("Title_Theme", loop=True)
                if success:
                    self._music_started = True
                    print("[PHASE_SELECT] Musica iniciada: Title_Theme (fallback)")

    def _get_first_available_chapter(self):
        """Obtem o primeiro capitulo disponivel"""
        if not self.available_chapters:
            return 1

        for chapter_id in self.available_chapters:
            phases = self.catalog.get_chapter_phases(chapter_id)
            for phase in phases:
                phase_id = f"{chapter_id}-{phase['number']}"
                if self.progress.is_phase_unlocked(phase_id):
                    return chapter_id
        return self.available_chapters[0]

    def refresh_data(self):
        """Recarrega os dados"""
        self.progress.reload_progress()
        self.catalog.refresh()
        self.available_chapters = sorted(self.catalog.get_all_phases().keys())

        if hasattr(self.game, 'player') and self.game.player:
            saved_chapter = self.game.player.chapter_page_num
            if saved_chapter > 0 and saved_chapter in self.available_chapters:
                self.current_chapter_id = saved_chapter
            else:
                self.current_chapter_id = self._get_first_available_chapter()
        else:
            self.current_chapter_id = self._get_first_available_chapter()

        self.layout_initialized = False

    def _check_resize(self):
        """Verifica se a janela foi redimensionada"""
        current_size = (self.screen_manager.window_width, self.screen_manager.window_height)
        if current_size != self.last_window_size:
            self.last_window_size = current_size
            self.layout_initialized = False
            return True
        return False

    # ======================================================================
    # LAYOUT
    # ======================================================================

    def _create_layout(self):
        """Cria o layout completo"""
        vx = self.screen_manager.viewport_x
        vy = self.screen_manager.viewport_y
        vw = self.screen_manager.viewport_width
        vh = self.screen_manager.viewport_height

        # ===== BOTAO VOLTAR =====
        back_size = int(min(vw * 0.045, vh * 0.065, 40))
        self.back_button_rect = pygame.Rect(vx + 20, vy + 20, back_size, back_size)

        # ===== BOTOES INFERIORES =====
        button_width = int(vw * 0.10)
        button_height = int(vh * 0.055)
        button_spacing = int(vw * 0.012)

        # 5 botoes: Loja, Minigames, Pokedex, Conquistas, Incubadora
        total_width = button_width * 5 + button_spacing * 4
        start_x = vx + (vw - total_width) // 2
        bottom_y = vy + vh - button_height - int(vh * 0.06)

        self.shop_button_rect = pygame.Rect(start_x, bottom_y, button_width, button_height)
        self.minigame_button_rect = pygame.Rect(start_x + button_width + button_spacing, bottom_y, button_width,
                                                button_height)
        self.pokedex_button_rect = pygame.Rect(start_x + (button_width + button_spacing) * 2, bottom_y, button_width,
                                               button_height)
        self.achievement_button_rect = pygame.Rect(start_x + (button_width + button_spacing) * 3, bottom_y,
                                                   button_width, button_height)
        self.incubator_button_rect = pygame.Rect(start_x + (button_width + button_spacing) * 4, bottom_y, button_width,
                                                 button_height)

        # ===== ABAS =====
        if self.available_chapters:
            tab_width = int(vw * 0.10)
            tab_height = int(vh * 0.075)
            tab_spacing = int(vw * 0.012)
            tabs_total_width = len(self.available_chapters) * (tab_width + tab_spacing) - tab_spacing
            tab_start_x = vx + (vw - tabs_total_width) // 2
            tab_y = vy + int(vh * 0.10)

            self.chapter_tabs = []
            for i, chapter_id in enumerate(self.available_chapters):
                tab_x = tab_start_x + i * (tab_width + tab_spacing)
                phases = self.catalog.get_chapter_phases(chapter_id)
                phase_ids = [f"{chapter_id}-{p['number']}" for p in phases]
                progress = self.progress.get_chapter_progress(chapter_id, phase_ids)

                tab = ChapterTab(chapter_id, f"CAP {chapter_id}", progress)
                tab.update_position(tab_x, tab_y, tab_width, tab_height)
                tab.active = (chapter_id == self.current_chapter_id)
                self.chapter_tabs.append(tab)

        # ===== CARDS =====
        self._create_phase_cards()

        # Salva o capitulo atual
        if hasattr(self.game, 'player') and self.game.player:
            self.game.player.chapter_page_num = self.current_chapter_id

        self.layout_initialized = True
        self.scroll_y = 0
        self.scroll_target = 0

    def _create_phase_cards(self):
        """Cria os cards de fase"""
        vx = self.screen_manager.viewport_x
        vy = self.screen_manager.viewport_y
        vw = self.screen_manager.viewport_width
        vh = self.screen_manager.viewport_height

        phases = self.catalog.get_chapter_phases(self.current_chapter_id)
        if not phases:
            self.phase_cards = []
            self.max_scroll = 0
            return

        # Calcula grid
        card_base_width = int(vw * 0.10)
        card_margin = int(vw * 0.015)
        available_width = vw - int(vw * 0.08)
        cols = max(2, min(5, available_width // (card_base_width + card_margin)))

        card_width = (available_width - (cols - 1) * card_margin) // cols
        card_width = max(int(vw * 0.07), min(int(vw * 0.12), card_width))
        card_height = int(card_width * 1.25)

        # Posicao do grid
        tab_height = int(vh * 0.075) if self.chapter_tabs else 0
        grid_start_y = vy + int(vh * 0.20) + tab_height
        grid_width = cols * card_width + (cols - 1) * card_margin
        grid_start_x = vx + (vw - grid_width) // 2

        rows = math.ceil(len(phases) / cols)
        grid_height = rows * (card_height + card_margin)
        visible_height = vh - (grid_start_y - vy) - int(vh * 0.15)
        self.max_scroll = max(0, grid_height - visible_height)

        # Cria cards
        self.phase_cards = []
        for i, phase_data in enumerate(phases):
            row = i // cols
            col = i % cols

            card_x = grid_start_x + col * (card_width + card_margin)
            card_y = grid_start_y + row * (card_height + card_margin) - self.scroll_y

            phase_id = f"{self.current_chapter_id}-{phase_data['number']}"
            unlocked = self.progress.is_phase_unlocked(phase_id)
            completed = self.progress.is_phase_completed(phase_id)

            card = PhaseCard(phase_data, unlocked, completed)
            card.update_position(card_x, card_y, card_width, card_height)
            self.phase_cards.append(card)

    def _is_incubator_unlocked(self) -> bool:
        """Verifica se a incubadora esta desbloqueada (fase 1-5 completada)"""
        return self.progress.is_phase_completed("1-5")

    # ======================================================================
    # EVENTOS
    # ======================================================================

    def handle_event(self, event):
        """Processa eventos"""
        # Hover para todos os botoes
        if event.type == pygame.MOUSEMOTION:
            self._update_hover_states(event.pos)

        # Teclas
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_p:
                self.toggle_pause()
            elif event.key == pygame.K_ESCAPE:
                sound_manager.play_effect(SoundEffect.CLICK)
                sound_manager.stop_music(fade_ms=300)
                self.game.current_scene = self.game.menu_scene
            elif event.key == pygame.K_LEFT:
                self._previous_chapter()
            elif event.key == pygame.K_RIGHT:
                self._next_chapter()
            elif event.key == pygame.K_r and pygame.key.get_mods() & pygame.KMOD_CTRL:
                self._reset_progress()
            elif event.key == pygame.K_u and self.dev_mode:
                self._debug_unlock_next()
            elif event.key == pygame.K_a and self.dev_mode:
                self._debug_unlock_all()
            elif event.key == pygame.K_s:
                self._open_shop()
            elif event.key == pygame.K_m:
                self._open_minigames()
            elif event.key == pygame.K_x:
                self._open_pokedex()
            elif event.key == pygame.K_c:
                self._open_achievements()
            elif event.key == pygame.K_i:
                self._open_incubator()

        # Redimensionamento
        elif event.type == pygame.VIDEORESIZE:
            self.layout_initialized = False

        # Scroll
        elif event.type == pygame.MOUSEWHEEL:
            if self.phase_cards and self.max_scroll > 0:
                self.scroll_target += event.y * -30
                self.scroll_target = max(0, min(self.max_scroll, self.scroll_target))

        # Cliques
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self._handle_click(event.pos)

        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.dragging_scroll = False

        # Hover dos cards e abas
        if event.type == pygame.MOUSEMOTION:
            for card in self.phase_cards:
                card.handle_event(event)
            for tab in self.chapter_tabs:
                tab.handle_event(event)

            if self.dragging_scroll:
                dy = event.pos[1] - self.last_mouse_y
                scroll_speed = self.max_scroll / (self.screen_manager.viewport_height - 200)
                self.scroll_target += dy * scroll_speed * 1.5
                self.scroll_target = max(0, min(self.max_scroll, self.scroll_target))
                self.last_mouse_y = event.pos[1]

    def _update_hover_states(self, pos):
        """Atualiza estados de hover dos botoes"""
        self.back_button_hovered = self.back_button_rect.collidepoint(pos) if self.back_button_rect else False
        self.shop_button_hovered = self.shop_button_rect.collidepoint(pos) if self.shop_button_rect else False
        self.minigame_button_hovered = self.minigame_button_rect.collidepoint(
            pos) if self.minigame_button_rect else False
        self.pokedex_button_hovered = self.pokedex_button_rect.collidepoint(pos) if self.pokedex_button_rect else False
        self.achievement_button_hovered = self.achievement_button_rect.collidepoint(
            pos) if self.achievement_button_rect else False
        self.incubator_button_hovered = self.incubator_button_rect.collidepoint(
            pos) if self.incubator_button_rect else False

    def _handle_click(self, pos):
        """Processa cliques"""
        # Back button
        if self.back_button_rect and self.back_button_rect.collidepoint(pos):
            sound_manager.play_effect(SoundEffect.CLICK)
            sound_manager.stop_music(fade_ms=300)
            self.game.current_scene = self.game.menu_scene
            return

        # Botoes inferiores
        if self.shop_button_rect and self.shop_button_rect.collidepoint(pos):
            self._open_shop()
            return

        if self.minigame_button_rect and self.minigame_button_rect.collidepoint(pos):
            self._open_minigames()
            return

        if self.pokedex_button_rect and self.pokedex_button_rect.collidepoint(pos):
            self._open_pokedex()
            return

        if self.achievement_button_rect and self.achievement_button_rect.collidepoint(pos):
            self._open_achievements()
            return

        if self.incubator_button_rect and self.incubator_button_rect.collidepoint(pos):
            if self._is_incubator_unlocked():
                self._open_incubator()
            else:
                sound_manager.play_effect(SoundEffect.CLICK)
                print("Incubadora desbloqueada apos completar a fase 1-5!")
            return

        # Abas
        for tab in self.chapter_tabs:
            result = tab.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=pos))
            if result:
                self.current_chapter_id = result
                if hasattr(self.game, 'player') and self.game.player:
                    self.game.player.chapter_page_num = self.current_chapter_id
                self._create_phase_cards()
                for t in self.chapter_tabs:
                    t.active = (t.chapter_id == self.current_chapter_id)
                return

        # Scroll bar
        if self.phase_cards and self.max_scroll > 0:
            scroll_bar_rect = self._get_scroll_bar_rect()
            if scroll_bar_rect and scroll_bar_rect.collidepoint(pos):
                self.dragging_scroll = True
                self.last_mouse_y = pos[1]
                return

        # Cards
        for card in self.phase_cards:
            result = card.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=pos))
            if result:
                self.start_phase(result)
                return

    # ======================================================================
    # NAVEGACAO
    # ======================================================================

    def _previous_chapter(self):
        """Vai para o capitulo anterior"""
        if self.available_chapters:
            current_idx = self.available_chapters.index(self.current_chapter_id)
            if current_idx > 0:
                self.current_chapter_id = self.available_chapters[current_idx - 1]
                if hasattr(self.game, 'player') and self.game.player:
                    self.game.player.chapter_page_num = self.current_chapter_id
                self._create_phase_cards()
                for tab in self.chapter_tabs:
                    tab.active = (tab.chapter_id == self.current_chapter_id)

    def _next_chapter(self):
        """Vai para o proximo capitulo"""
        if self.available_chapters:
            current_idx = self.available_chapters.index(self.current_chapter_id)
            if current_idx < len(self.available_chapters) - 1:
                self.current_chapter_id = self.available_chapters[current_idx + 1]
                if hasattr(self.game, 'player') and self.game.player:
                    self.game.player.chapter_page_num = self.current_chapter_id
                self._create_phase_cards()
                for tab in self.chapter_tabs:
                    tab.active = (tab.chapter_id == self.current_chapter_id)

    def _reset_progress(self):
        """Reseta o progresso (CTRL+R)"""
        self.progress.reset_progress()
        self.catalog.refresh()
        self.available_chapters = sorted(self.catalog.get_all_phases().keys())
        self.current_chapter_id = self._get_first_available_chapter()
        self.layout_initialized = False

    # ======================================================================
    # ABERTURA DE TELAS
    # ======================================================================

    def _open_shop(self):
        sound_manager.play_effect(SoundEffect.CLICK)
        self.game.shop_scene = ShopScene(self.game)
        self.game.shop_scene.on_close_callback = self._on_shop_closed
        self.game.current_scene = self.game.shop_scene

    def _open_minigames(self):
        sound_manager.play_effect(SoundEffect.CLICK)
        from src.scenes.minigame_select_scene.minigame_select_scene import MinigameSelectScene
        self.game.current_scene = MinigameSelectScene(self.game)

    def _open_pokedex(self):
        sound_manager.play_effect(SoundEffect.CLICK)
        self.game.pokedex_scene = PokedexScene(self.game)
        self.game.current_scene = self.game.pokedex_scene

    def _open_achievements(self):
        sound_manager.play_effect(SoundEffect.CLICK)
        self.game.achievement_scene = AchievementScene(self.game)
        self.game.current_scene = self.game.achievement_scene

    def _open_incubator(self):
        sound_manager.play_effect(SoundEffect.CLICK)
        self.game.incubator_scene = IncubatorScene(self.game)
        self.game.current_scene = self.game.incubator_scene

    def _on_shop_closed(self):
        self.layout_initialized = False

    def start_phase(self, phase_number):
        """Inicia uma fase"""
        sound_manager.play_effect(SoundEffect.CLICK)
        sound_manager.stop_music(fade_ms=300)

        phase_id = f"{self.current_chapter_id}-{phase_number}"
        phase_info = self.catalog.get_phase_info(self.current_chapter_id, phase_number)

        if phase_info:
            print(f"Iniciando fase: {phase_id} - {phase_info['name']}")

        from src.scenes.team_select_scene import TeamSelectScene
        self.game.team_select_scene = TeamSelectScene(self.game, self.current_chapter_id, phase_number)
        self.game.current_scene = self.game.team_select_scene

    # ======================================================================
    # DEBUG
    # ======================================================================

    def _debug_unlock_next(self):
        """Desbloqueia a proxima fase (modo debug)"""
        if self.phase_cards:
            for card in self.phase_cards:
                if not card.unlocked:
                    self.progress.unlock_specific_phase(card.phase_id)
                    self._create_phase_cards()
                    break
            else:
                next_chapter = self.current_chapter_id + 1
                if next_chapter in self.available_chapters:
                    phases = self.catalog.get_chapter_phases(next_chapter)
                    if phases:
                        first_phase = phases[0]
                        phase_id = f"{next_chapter}-{first_phase['number']}"
                        self.progress.unlock_specific_phase(phase_id)
                        self._create_phase_cards()

    def _debug_unlock_all(self):
        """Desbloqueia todas as fases (modo debug)"""
        all_phases = self.catalog.get_all_phases()
        for chapter_id, phases in all_phases.items():
            for phase in phases:
                phase_id = f"{chapter_id}-{phase['number']}"
                self.progress.unlock_specific_phase(phase_id)
        self._create_phase_cards()

    # ======================================================================
    # UPDATE
    # ======================================================================

    def fixed_update(self, dt):
        """Atualiza animacoes"""
        if self.paused:
            return

        self._animation_timer += dt

        # Suaviza o scroll
        if abs(self.scroll_y - self.scroll_target) > 0.1:
            self.scroll_y += (self.scroll_target - self.scroll_y) * min(1, dt * 10)

            # Atualiza posicao dos cards
            if self.phase_cards:
                self._update_cards_position()

        # Atualiza animacoes dos cards
        for card in self.phase_cards:
            card.update(dt)

        # Atualiza animacoes das abas
        for tab in self.chapter_tabs:
            tab.update(dt)

    def _update_cards_position(self):
        """Atualiza a posicao dos cards baseado no scroll"""
        vx = self.screen_manager.viewport_x
        vy = self.screen_manager.viewport_y
        vw = self.screen_manager.viewport_width
        vh = self.screen_manager.viewport_height

        phases = self.catalog.get_chapter_phases(self.current_chapter_id)
        if not phases or not self.phase_cards:
            return

        card_base_width = int(vw * 0.10)
        card_margin = int(vw * 0.015)
        available_width = vw - int(vw * 0.08)
        cols = max(2, min(5, available_width // (card_base_width + card_margin)))

        card_width = (available_width - (cols - 1) * card_margin) // cols
        card_width = max(int(vw * 0.07), min(int(vw * 0.12), card_width))
        card_height = int(card_width * 1.25)

        tab_height = int(vh * 0.075) if self.chapter_tabs else 0
        grid_start_y = vy + int(vh * 0.20) + tab_height
        grid_width = cols * card_width + (cols - 1) * card_margin
        grid_start_x = vx + (vw - grid_width) // 2

        for i, card in enumerate(self.phase_cards):
            row = i // cols
            col = i % cols
            card_x = grid_start_x + col * (card_width + card_margin)
            card_y = grid_start_y + row * (card_height + card_margin) - self.scroll_y
            card.rect.x = card_x
            card.rect.y = card_y

    # ======================================================================
    # RENDERIZACAO
    # ======================================================================

    def render(self, screen):
        """Renderiza a cena"""
        self._check_resize()
        self._draw_gradient_background(screen)

        if not self.layout_initialized:
            self._create_layout()

        vx = self.screen_manager.viewport_x
        vy = self.screen_manager.viewport_y
        vw = self.screen_manager.viewport_width
        vh = self.screen_manager.viewport_height

        # ===== TITULO =====
        title = self.title_font.render("SELECIONAR FASE", True, (255, 255, 255))
        title_shadow = self.title_font.render("SELECIONAR FASE", True, (30, 30, 45))
        title_x = vx + (vw - title.get_width()) // 2
        title_y = vy + 15
        screen.blit(title_shadow, (title_x + 2, title_y + 2))
        screen.blit(title, (title_x, title_y))

        # Linha decorativa
        bar_width = int(vw * 0.15)
        bar_x = vx + (vw - bar_width) // 2
        bar_y = title_y + title.get_height() + 6
        pygame.draw.rect(screen, (100, 85, 55), (bar_x, bar_y, bar_width, 3), border_radius=2)

        # ===== BOTAO VOLTAR =====
        self._render_button(screen, self.back_button_rect, "<", self.back_button_hovered)

        # ===== BOTOES INFERIORES =====
        self._render_bottom_button(screen, self.shop_button_rect, "LOJA", self.shop_button_hovered)
        self._render_bottom_button(screen, self.minigame_button_rect, "MINIGAMES", self.minigame_button_hovered)
        self._render_bottom_button(screen, self.pokedex_button_rect, "POKEDEX", self.pokedex_button_hovered)
        self._render_bottom_button(screen, self.achievement_button_rect, "CONQUISTAS", self.achievement_button_hovered)
        self._render_bottom_button(screen, self.incubator_button_rect, "INCUBADORA", self.incubator_button_hovered,
                                   not self._is_incubator_unlocked())

        # ===== ABAS =====
        for tab in self.chapter_tabs:
            tab.render(screen, self.tab_font)

        # ===== LINHA SEPARADORA =====
        if self.chapter_tabs:
            line_y = self.chapter_tabs[0].rect.bottom + 12
            line_width = int(vw * 0.3)
            line_x = vx + (vw - line_width) // 2
            pygame.draw.line(screen, (70, 70, 80), (line_x, line_y), (line_x + line_width, line_y), 1)

            # Total de fases
            phases = self.catalog.get_chapter_phases(self.current_chapter_id)
            if phases:
                total_text = f"{len(phases)} fases disponiveis"
                total_surface = self.tab_font.render(total_text, True, (180, 180, 190))
                total_x = vx + (vw - total_surface.get_width()) // 2
                total_y = line_y + 8
                screen.blit(total_surface, (total_x, total_y))

                line_y2 = total_y + 20
                pygame.draw.line(screen, (70, 70, 80), (line_x, line_y2), (line_x + line_width, line_y2), 1)

        # ===== CARDS (com clipping) =====
        clip_rect = pygame.Rect(
            vx,
            vy + int(vh * 0.20),
            vw,
            vh - int(vh * 0.20) - int(vh * 0.12)
        )

        old_clip = screen.get_clip()
        screen.set_clip(clip_rect)

        for card in self.phase_cards:
            if card.rect.bottom > clip_rect.top and card.rect.top < clip_rect.bottom:
                card.render(screen, self.phase_font_large, self.phase_font_small, self.phase_font_name)

        screen.set_clip(old_clip)

        # ===== BARRA DE SCROLL =====
        if self.max_scroll > 0:
            self._render_scroll_bar(screen)

        # ===== INSTRUCOES =====
        font_small = pygame.font.Font(None, 16)
        inst_text = "SETAS NAVEGAR | CLIQUE NA FASE | ESC VOLTAR"
        if self.dev_mode:
            inst_text += " | [U] proxima | [A] todas"
        inst = font_small.render(inst_text, True, (100, 100, 120))
        inst_x = vx + (vw - inst.get_width()) // 2
        inst_y = vy + vh - 18
        screen.blit(inst, (inst_x, inst_y))

        # Debug info
        debug_text = font_small.render("CTRL+R resetar progresso", True, (60, 60, 70))
        debug_x = vx + 15
        debug_y = vy + vh - 40
        screen.blit(debug_text, (debug_x, debug_y))

        # ===== PAUSA =====
        if self.paused:
            self._render_pause_overlay(screen)

    def _render_button(self, screen, rect, text, hovered):
        """Renderiza um botao estilizado"""
        if not rect:
            return

        # Sombra
        shadow_rect = rect.copy()
        shadow_rect.y += 3
        pygame.draw.rect(screen, (10, 10, 15), shadow_rect, border_radius=8)

        # Fundo
        if hovered:
            bg_color = (70, 70, 80)
            border_color = (160, 160, 180)
            text_color = (255, 255, 255)
        else:
            bg_color = (45, 45, 55)
            border_color = (90, 90, 105)
            text_color = (200, 200, 210)

        pygame.draw.rect(screen, bg_color, rect, border_radius=8)
        pygame.draw.rect(screen, border_color, rect, 2, border_radius=8)

        # Texto
        font = pygame.font.Font(None, int(rect.height * 0.6))
        text_surface = font.render(text, True, text_color)
        text_rect = text_surface.get_rect(center=rect.center)
        screen.blit(text_surface, text_rect)

    def _render_bottom_button(self, screen, rect, text, hovered, locked=False):
        """Renderiza um botao inferior estilizado"""
        if not rect:
            return

        # Sombra
        shadow_rect = rect.copy()
        shadow_rect.y += 3
        pygame.draw.rect(screen, (10, 10, 15), shadow_rect, border_radius=8)

        if locked:
            bg_color = (35, 35, 40)
            border_color = (60, 60, 65)
            text_color = (80, 80, 85)
        elif hovered:
            bg_color = (70, 70, 85)
            border_color = (160, 160, 190)
            text_color = (255, 255, 255)
        else:
            bg_color = (50, 50, 60)
            border_color = (100, 100, 120)
            text_color = (220, 220, 230)

        pygame.draw.rect(screen, bg_color, rect, border_radius=8)
        pygame.draw.rect(screen, border_color, rect, 2, border_radius=8)

        # Texto
        font = pygame.font.Font(None, int(rect.height * 0.4))
        text_surface = font.render(text, True, text_color)
        text_rect = text_surface.get_rect(center=rect.center)
        screen.blit(text_surface, text_rect)

        # Label de bloqueio
        if locked:
            lock_font = pygame.font.Font(None, int(rect.height * 0.3))
            lock_text = lock_font.render("Complete 1-5", True, (70, 70, 75))
            lock_rect = lock_text.get_rect(center=(rect.centerx, rect.bottom + 14))
            screen.blit(lock_text, lock_rect)

    def _render_scroll_bar(self, screen):
        """Renderiza a barra de scroll"""
        if self.max_scroll <= 0:
            return

        x, y, width, height = self._get_scroll_bar_area()
        scroll_height = max(30, height * (height / (height + self.max_scroll)))
        scroll_pos = y + (self.scroll_y / self.max_scroll) * (height - scroll_height)

        # Fundo
        pygame.draw.rect(screen, (30, 30, 38), (x, y, width, height), border_radius=4)

        # Scroll
        scroll_rect = pygame.Rect(x, scroll_pos, width, scroll_height)
        color = (120, 120, 140) if self.dragging_scroll else (80, 80, 95)
        pygame.draw.rect(screen, color, scroll_rect, border_radius=4)
        pygame.draw.rect(screen, (150, 150, 170), scroll_rect, 1, border_radius=4)

    def _get_scroll_bar_area(self):
        """Retorna a area da barra de scroll"""
        vx = self.screen_manager.viewport_x
        vy = self.screen_manager.viewport_y
        vw = self.screen_manager.viewport_width
        vh = self.screen_manager.viewport_height

        return (
            vx + vw - 14,
            vy + int(vh * 0.20),
            8,
            vh - int(vh * 0.20) - int(vh * 0.15)
        )

    def _get_scroll_bar_rect(self):
        """Retorna o rect da barra de scroll"""
        if self.max_scroll <= 0:
            return None

        x, y, width, height = self._get_scroll_bar_area()
        scroll_height = max(30, height * (height / (height + self.max_scroll)))
        scroll_pos = y + (self.scroll_y / self.max_scroll) * (height - scroll_height)

        return pygame.Rect(x, scroll_pos, width, scroll_height)

    def _draw_gradient_background(self, screen):
        """Desenha o fundo com gradiente e estrelas"""
        width = self.screen_manager.window_width
        height = self.screen_manager.window_height

        # Gradiente
        for i in range(height):
            t = i / height
            r = int(10 + t * 20)
            g = int(12 + t * 25)
            b = int(25 + t * 35)
            pygame.draw.line(screen, (r, g, b), (0, i), (width, i))

        # Estrelas
        star_positions = [
            (0.03, 0.03), (0.08, 0.08), (0.15, 0.05), (0.22, 0.10), (0.30, 0.04),
            (0.38, 0.12), (0.45, 0.06), (0.52, 0.09), (0.60, 0.04), (0.68, 0.11),
            (0.75, 0.05), (0.82, 0.08), (0.90, 0.07), (0.95, 0.10), (0.05, 0.15),
            (0.12, 0.18), (0.88, 0.17), (0.93, 0.22), (0.02, 0.25), (0.98, 0.28),
        ]

        vx = self.screen_manager.viewport_x
        vy = self.screen_manager.viewport_y
        vw = self.screen_manager.viewport_width
        vh = self.screen_manager.viewport_height

        for i, (rx, ry) in enumerate(star_positions):
            x = vx + int(rx * vw)
            y = vy + int(ry * vh)
            alpha = int(60 + 80 * (0.5 + 0.5 * (self._animation_timer * 0.5 + i * 1.3) % 1))
            size = 1 + int(((i * 5) % 2))

            color = (200 + int(55 * (self._animation_timer * 0.3 + i) % 1),
                     200 + int(55 * (self._animation_timer * 0.4 + i + 1) % 1),
                     255)

            pygame.draw.circle(screen, color, (x, y), size)

    def _render_pause_overlay(self, screen):
        """Overlay de pausa"""
        overlay = pygame.Surface((self.screen_manager.window_width, self.screen_manager.window_height))
        overlay.set_alpha(180)
        overlay.fill((10, 10, 10))
        screen.blit(overlay, (0, 0))

        font_large = pygame.font.Font(None, 74)
        pause_text = font_large.render("PAUSADO", True, (200, 200, 200))
        text_rect = pause_text.get_rect(center=(
            self.screen_manager.window_width // 2,
            self.screen_manager.window_height // 2
        ))
        screen.blit(pause_text, text_rect)

    # ======================================================================
    # CICLO DE VIDA
    # ======================================================================

    def on_enter(self):
        """Chamado quando a cena e ativada"""
        if not self._music_started or not pygame.mixer.music.get_busy():
            self._start_phase_select_music()

    def on_exit(self):
        """Chamado quando a cena e desativada"""
        sound_manager.stop_music(fade_ms=300)
        self._music_started = False