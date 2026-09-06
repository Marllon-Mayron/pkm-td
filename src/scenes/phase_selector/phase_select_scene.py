# src/scenes/phase_select_scene.py

"""
Tela de seleção de fases adaptada para usar IDs compostos (formato "capítulo-fase")
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
        self.incubator_button = None
        self.incubator_button_hovered = False

        # Cores baseadas no status
        if not unlocked:
            self.bg_color = (30, 30, 35)
            self.border_color = (50, 50, 55)
            self.text_color = (80, 80, 85)
            self.name_color = (100, 100, 105)
        elif completed:
            self.bg_color = (40, 45, 40)
            self.border_color = (70, 100, 70)
            self.text_color = (180, 220, 180)
            self.name_color = (200, 240, 200)
        else:
            self.bg_color = (45, 45, 50)
            self.border_color = (80, 100, 130)
            self.text_color = (220, 220, 240)
            self.name_color = (200, 200, 220)

    def update_position(self, x, y, width, height):
        self.rect = pygame.Rect(x, y, width, height)

    def handle_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            was_hovered = self.is_hovered
            self.is_hovered = self.rect.collidepoint(event.pos)
            # Toca som de hover quando o mouse entra no card (apenas se desbloqueado)
            if self.is_hovered and not was_hovered and self.unlocked:
                sound_manager.play_effect(SoundEffect.CLICK, volume=0.3)
            return was_hovered != self.is_hovered
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.is_hovered and self.unlocked:
                sound_manager.play_effect(SoundEffect.CLICK)
                return self.phase_number
        return None

    def render(self, screen, font_large, font_small, font_name):
        if self.is_hovered and self.unlocked:
            color = tuple(min(255, c + 20) for c in self.bg_color)
            border = tuple(min(255, c + 30) for c in self.border_color)
            name_color = tuple(min(255, c + 40) for c in self.name_color)
        else:
            color = self.bg_color
            border = self.border_color
            name_color = self.name_color

        # Sombra
        shadow_rect = self.rect.copy()
        shadow_rect.x += 4
        shadow_rect.y += 4
        pygame.draw.rect(screen, (15, 15, 15), shadow_rect, border_radius=12)

        # Card principal
        pygame.draw.rect(screen, color, self.rect, border_radius=12)
        pygame.draw.rect(screen, border, self.rect, 2, border_radius=12)

        # Numero da fase
        num_text = font_small.render(f"{self.phase_id}", True, self.text_color)
        screen.blit(num_text, (self.rect.x + 8, self.rect.y + 8))

        # Nome da fase
        self._render_wrapped_text(screen, self.phase_name, font_name, name_color,
                                  self.rect.centerx, self.rect.centery - 15)

        # Texto de status
        if not self.unlocked:
            status = font_small.render("BLOQUEADA", True, (100, 100, 100))
        elif self.completed:
            status = font_small.render("CONCLUIDA", True, (140, 200, 140))
        else:
            status = font_small.render("DISPONIVEL", True, (140, 140, 200))

        status_rect = status.get_rect(center=(self.rect.centerx, self.rect.centery + 25))
        screen.blit(status, status_rect)

        # Overlay para fases bloqueadas
        if not self.unlocked:
            overlay = pygame.Surface((self.rect.width, self.rect.height), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 180))
            screen.blit(overlay, self.rect)

    def _render_wrapped_text(self, screen, text, font, color, center_x, center_y):
        words = text.split()
        if not words:
            return

        single_line = font.render(text, True, color)
        if single_line.get_width() <= self.rect.width - 20:
            text_rect = single_line.get_rect(center=(center_x, center_y))
            screen.blit(single_line, text_rect)
            return

        if len(words) == 1:
            while font.render(words[0] + "...", True, color).get_width() > self.rect.width - 20:
                words[0] = words[0][:-1]
            truncated = font.render(words[0] + "...", True, color)
            text_rect = truncated.get_rect(center=(center_x, center_y))
            screen.blit(truncated, text_rect)
            return

        mid = len(words) // 2
        line1 = " ".join(words[:mid])
        line2 = " ".join(words[mid:])

        while line1 and font.render(line1, True, color).get_width() > self.rect.width - 20:
            line1 = line1[:-1]
        while line2 and font.render(line2, True, color).get_width() > self.rect.width - 20:
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
    def __init__(self, chapter_id, name, progress):
        self.chapter_id = chapter_id
        self.name = name
        self.progress = progress
        self.rect = pygame.Rect(0, 0, 0, 0)
        self.is_hovered = False
        self._was_hovered = False
        self.active = False

    def update_position(self, x, y, width, height):
        self.rect = pygame.Rect(x, y, width, height)

    def handle_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            was_hovered = self.is_hovered
            self.is_hovered = self.rect.collidepoint(event.pos)
            if self.is_hovered and not was_hovered:
                sound_manager.play_effect(SoundEffect.CLICK, volume=0.3)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.is_hovered:
                sound_manager.play_effect(SoundEffect.CLICK)
                return self.chapter_id
        return None

    def render(self, screen, font):
        if self.active:
            color = (70, 70, 80)
            border = (140, 140, 160)
            text_color = (255, 255, 255)
        elif self.is_hovered:
            color = (55, 55, 65)
            border = (110, 110, 130)
            text_color = (220, 220, 220)
        else:
            color = (40, 40, 45)
            border = (70, 70, 80)
            text_color = (150, 150, 150)

        pygame.draw.rect(screen, color, self.rect)
        pygame.draw.rect(screen, border, self.rect, 2)

        text = font.render(self.name, True, text_color)
        text_rect = text.get_rect(center=(self.rect.centerx, self.rect.centery - 8))
        screen.blit(text, text_rect)

        progress_text = f"{self.progress['completed']}/{self.progress['total']}"
        progress_surface = font.render(progress_text, True, text_color)
        progress_rect = progress_surface.get_rect(center=(self.rect.centerx, self.rect.centery + 10))
        screen.blit(progress_surface, progress_rect)


class PhaseSelectScene(BaseScene):
    def __init__(self, game):
        super().__init__(game)

        self.progress = progress_manager
        self.catalog = phase_catalog

        self.available_chapters = sorted(self.catalog.get_all_phases().keys())

        if hasattr(game, 'player') and game.player and game.player.chapter_page_num > 0:
            self.current_chapter_id = game.player.chapter_page_num
            if self.current_chapter_id not in self.available_chapters:
                self.current_chapter_id = self._get_first_available_chapter()
        else:
            self.current_chapter_id = self._get_first_available_chapter()

        self.chapter_tabs = []
        self.phase_cards = []
        self.back_button = None
        self.shop_button = None
        self.minigame_button = None
        self.pokedex_button = None
        self.achievement_button = None
        self.incubator_button = None

        self.scroll_y = 0
        self.scroll_target = 0
        self.max_scroll = 0
        self.dragging_scroll = False
        self.last_mouse_y = 0

        self.layout_initialized = False
        self.last_window_size = (self.screen_manager.window_width, self.screen_manager.window_height)

        self.title_font = pygame.font.Font(None, 52)
        self.tab_font = pygame.font.Font(None, 22)
        self.phase_font_large = pygame.font.Font(None, 36)
        self.phase_font_small = pygame.font.Font(None, 16)
        self.phase_font_name = pygame.font.Font(None, 18)
        self.button_font = pygame.font.Font(None, 24)

        self.hover_changed = False
        self.shop_button_hovered = False
        self._shop_was_hovered = False
        self.minigame_button_hovered = False
        self._minigame_was_hovered = False
        self.pokedex_button_hovered = False
        self._pokedex_was_hovered = False
        self.achievement_button_hovered = False
        self._achievement_was_hovered = False
        self.incubator_button_hovered = False
        self._incubator_was_hovered = False
        self.back_button_hovered = False
        self._back_was_hovered = False

        self.refresh_data()
        self.dev_mode = True

        # Controle de música
        self._music_started = False

        # INICIA A MÚSICA DA SELEÇÃO DE FASES IMEDIATAMENTE
        self._start_phase_select_music()

    def _start_phase_select_music(self):
        """Inicia a música da tela de seleção de fases"""
        if not self._music_started:
            # Tenta Come_Along primeiro (música mais animada)
            success = sound_manager.play_team_select_music(loop=True)
            if success:
                self._music_started = True
                print("[PHASE_SELECT] Música iniciada: Come_Along")
            else:
                # Tenta Title_Theme como fallback
                success = sound_manager.play_menu_music("Title_Theme", loop=True)
                if success:
                    self._music_started = True
                    print("[PHASE_SELECT] Música iniciada: Title_Theme (fallback)")

    def _get_first_available_chapter(self):
        if not self.available_chapters:
            return 1

        for chapter_id in self.available_chapters:
            phases = self.catalog.get_chapter_phases(chapter_id)
            for phase in phases:
                phase_id = f"{chapter_id}-{phase['number']}"
                if self.progress.is_phase_unlocked(phase_id):
                    return chapter_id
        return self.available_chapters[0]

    def _check_resize(self):
        current_size = (self.screen_manager.window_width, self.screen_manager.window_height)
        if current_size != self.last_window_size:
            self.last_window_size = current_size
            self.layout_initialized = False
            return True
        return False

    def _create_layout(self):
        viewport_width = self.screen_manager.viewport_width
        viewport_height = self.screen_manager.viewport_height
        viewport_x = self.screen_manager.viewport_x
        viewport_y = self.screen_manager.viewport_y

        # Botao voltar
        back_size = 45
        self.back_button = pygame.Rect(
            viewport_x + 30,
            viewport_y + 25,
            back_size,
            back_size
        )

        # Botoes inferiores (loja, minigames, pokedex e conquistas lado a lado)
        button_width = 130
        button_height = 50
        button_spacing = 10
        total_width = button_width * 5 + button_spacing * 4
        start_x = viewport_x + (viewport_width - total_width) // 2
        bottom_y = viewport_y + viewport_height - 90

        # Botão LOJA
        self.shop_button = pygame.Rect(start_x, bottom_y, button_width, button_height)

        # Botão MINIGAMES
        self.minigame_button = pygame.Rect(
            start_x + button_width + button_spacing,
            bottom_y,
            button_width,
            button_height
        )

        # Botão POKÉDEX
        self.pokedex_button = pygame.Rect(
            start_x + (button_width + button_spacing) * 2,
            bottom_y,
            button_width,
            button_height
        )

        # Botão CONQUISTAS
        self.achievement_button = pygame.Rect(
            start_x + (button_width + button_spacing) * 3,
            bottom_y,
            button_width,
            button_height
        )

        self.incubator_button = pygame.Rect(
            start_x + (button_width + button_spacing) * 4,
            bottom_y,
            button_width,
            button_height
        )

        # Abas
        if self.available_chapters:
            tab_width = 130
            tab_height = 65
            tab_spacing = 15
            tabs_total_width = len(self.available_chapters) * (tab_width + tab_spacing) - tab_spacing
            tab_start_x = viewport_x + (viewport_width - tabs_total_width) // 2
            tab_y = viewport_y + 75

            self.chapter_tabs = []
            for i, chapter_id in enumerate(self.available_chapters):
                tab_x = tab_start_x + i * (tab_width + tab_spacing)
                phases = self.catalog.get_chapter_phases(chapter_id)
                phase_ids = [f"{chapter_id}-{p['number']}" for p in phases]
                progress = self.progress.get_chapter_progress(chapter_id, phase_ids)

                tab = ChapterTab(chapter_id, f"CAPITULO {chapter_id}", progress)
                tab.update_position(tab_x, tab_y, tab_width, tab_height)
                tab.active = (chapter_id == self.current_chapter_id)
                self.chapter_tabs.append(tab)

        self._create_phase_cards()

        if hasattr(self.game, 'player') and self.game.player:
            self.game.player.chapter_page_num = self.current_chapter_id

        self.layout_initialized = True
        self.scroll_y = 0
        self.scroll_target = 0

    def _create_phase_cards(self):
        viewport_width = self.screen_manager.viewport_width
        viewport_height = self.screen_manager.viewport_height
        viewport_x = self.screen_manager.viewport_x
        viewport_y = self.screen_manager.viewport_y

        phases = self.catalog.get_chapter_phases(self.current_chapter_id)
        if not phases:
            self.phase_cards = []
            self.max_scroll = 0
            return

        card_base_width = 140
        card_margin = 20
        available_width = viewport_width - 100
        cols = max(2, min(5, available_width // (card_base_width + card_margin)))

        card_width = (available_width - (cols - 1) * card_margin) // cols
        card_width = max(100, min(160, card_width))
        card_height = int(card_width * 1.3)

        tab_y = viewport_y + 75
        grid_start_y = tab_y + 65 + 45
        grid_width = cols * card_width + (cols - 1) * card_margin
        grid_start_x = viewport_x + (viewport_width - grid_width) // 2

        rows = math.ceil(len(phases) / cols)
        grid_height = rows * (card_height + card_margin)
        visible_height = viewport_height - (grid_start_y - viewport_y) - 60
        self.max_scroll = max(0, grid_height - visible_height)

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
        """Verifica se a incubadora está desbloqueada (fase 1-5 completada)"""
        return self.progress.is_phase_completed("1-5")

    def refresh_data(self):
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
        print("Dados da PhaseSelectScene recarregados!")

    def handle_event(self, event):
        # Verifica hover para todos os botões
        if event.type == pygame.MOUSEMOTION:
            # Back button
            if self.back_button:
                was_hovered = self.back_button_hovered
                self.back_button_hovered = self.back_button.collidepoint(event.pos)
                if self.back_button_hovered and not was_hovered:
                    sound_manager.play_effect(SoundEffect.CLICK, volume=0.3)

            # Shop button
            if self.shop_button:
                was_hovered = self._shop_was_hovered
                self.shop_button_hovered = self.shop_button.collidepoint(event.pos)
                self._shop_was_hovered = self.shop_button_hovered
                if self.shop_button_hovered and not was_hovered:
                    sound_manager.play_effect(SoundEffect.CLICK, volume=0.3)

            # Minigame button
            if self.minigame_button:
                was_hovered = self._minigame_was_hovered
                self.minigame_button_hovered = self.minigame_button.collidepoint(event.pos)
                self._minigame_was_hovered = self.minigame_button_hovered
                if self.minigame_button_hovered and not was_hovered:
                    sound_manager.play_effect(SoundEffect.CLICK, volume=0.3)

            # Pokedex button
            if self.pokedex_button:
                was_hovered = self._pokedex_was_hovered
                self.pokedex_button_hovered = self.pokedex_button.collidepoint(event.pos)
                self._pokedex_was_hovered = self.pokedex_button_hovered
                if self.pokedex_button_hovered and not was_hovered:
                    sound_manager.play_effect(SoundEffect.CLICK, volume=0.3)

            # Achievement button
            if self.achievement_button:
                was_hovered = self._achievement_was_hovered
                self.achievement_button_hovered = self.achievement_button.collidepoint(event.pos)
                self._achievement_was_hovered = self.achievement_button_hovered
                if self.achievement_button_hovered and not was_hovered:
                    sound_manager.play_effect(SoundEffect.CLICK, volume=0.3)

            # Incubator button
            if self.incubator_button:
                was_hovered = self._incubator_was_hovered
                self.incubator_button_hovered = self.incubator_button.collidepoint(event.pos)
                self._incubator_was_hovered = self.incubator_button_hovered
                if self.incubator_button_hovered and not was_hovered:
                    sound_manager.play_effect(SoundEffect.CLICK, volume=0.3)

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_p:
                self.toggle_pause()
            elif event.key == pygame.K_ESCAPE:
                sound_manager.play_effect(SoundEffect.CLICK)
                # Para a música com fade ao voltar ao menu
                sound_manager.stop_music(fade_ms=300)
                self.game.current_scene = self.game.menu_scene
            elif event.key == pygame.K_LEFT:
                if self.available_chapters:
                    current_idx = self.available_chapters.index(self.current_chapter_id)
                    if current_idx > 0:
                        self.current_chapter_id = self.available_chapters[current_idx - 1]
                        if hasattr(self.game, 'player') and self.game.player:
                            self.game.player.chapter_page_num = self.current_chapter_id
                        self._create_phase_cards()
                        for tab in self.chapter_tabs:
                            tab.active = (tab.chapter_id == self.current_chapter_id)
            elif event.key == pygame.K_RIGHT:
                if self.available_chapters:
                    current_idx = self.available_chapters.index(self.current_chapter_id)
                    if current_idx < len(self.available_chapters) - 1:
                        self.current_chapter_id = self.available_chapters[current_idx + 1]
                        if hasattr(self.game, 'player') and self.game.player:
                            self.game.player.chapter_page_num = self.current_chapter_id
                        self._create_phase_cards()
                        for tab in self.chapter_tabs:
                            tab.active = (tab.chapter_id == self.current_chapter_id)
            elif event.key == pygame.K_r and pygame.key.get_mods() & pygame.KMOD_CTRL:
                self.progress.reset_progress()
                self.catalog.refresh()
                self.available_chapters = sorted(self.catalog.get_all_phases().keys())
                self.current_chapter_id = self._get_first_available_chapter()
                self.layout_initialized = False
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

        elif event.type == pygame.VIDEORESIZE:
            self.layout_initialized = False

        elif event.type == pygame.MOUSEWHEEL:
            if self.phase_cards and self.max_scroll > 0:
                self.scroll_target += event.y * -30
                self.scroll_target = max(0, min(self.max_scroll, self.scroll_target))

        elif event.type == pygame.MOUSEMOTION:
            for card in self.phase_cards:
                card.handle_event(event)
            for tab in self.chapter_tabs:
                tab.handle_event(event)

            if self.dragging_scroll:
                dy = event.pos[1] - self.last_mouse_y
                scroll_speed = self.max_scroll / self._get_scroll_bar_area()[1]
                self.scroll_target += dy * scroll_speed * 2
                self.scroll_target = max(0, min(self.max_scroll, self.scroll_target))
                self.last_mouse_y = event.pos[1]

        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                if self.back_button and self.back_button.collidepoint(event.pos):
                    sound_manager.play_effect(SoundEffect.CLICK)
                    sound_manager.stop_music(fade_ms=300)
                    self.game.current_scene = self.game.menu_scene
                    return

                if self.shop_button and self.shop_button.collidepoint(event.pos):
                    self._open_shop()
                    return

                if self.minigame_button and self.minigame_button.collidepoint(event.pos):
                    self._open_minigames()
                    return

                if self.pokedex_button and self.pokedex_button.collidepoint(event.pos):
                    self._open_pokedex()
                    return

                if self.achievement_button and self.achievement_button.collidepoint(event.pos):
                    self._open_achievements()
                    return

                if self.incubator_button and self.incubator_button.collidepoint(event.pos):
                    if self._is_incubator_unlocked():
                        self._open_incubator()
                    else:
                        print("Incubadora desbloqueada após completar a fase 1-5!")
                        sound_manager.play_effect(SoundEffect.CLICK, volume=0.5)
                    return

                for tab in self.chapter_tabs:
                    result = tab.handle_event(event)
                    if result:
                        self.current_chapter_id = result
                        if hasattr(self.game, 'player') and self.game.player:
                            self.game.player.chapter_page_num = self.current_chapter_id
                        self._create_phase_cards()
                        for t in self.chapter_tabs:
                            t.active = (t.chapter_id == self.current_chapter_id)
                        return

                if self.phase_cards and self.max_scroll > 0:
                    scroll_bar_rect = self._get_scroll_bar_rect()
                    if scroll_bar_rect and scroll_bar_rect.collidepoint(event.pos):
                        self.dragging_scroll = True
                        self.last_mouse_y = event.pos[1]
                        return

                for card in self.phase_cards:
                    result = card.handle_event(event)
                    if result:
                        sound_manager.play_effect(SoundEffect.CLICK)
                        self.start_phase(result)
                        return

            elif event.button == 3:
                self.scroll_target = 0
                self.scroll_y = 0

        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1:
                self.dragging_scroll = False

    def _open_shop(self):
        sound_manager.play_effect(SoundEffect.CLICK)
        self.game.shop_scene = ShopScene(self.game)
        self.game.shop_scene.on_close_callback = self._on_shop_closed
        self.game.current_scene = self.game.shop_scene

    def _open_minigames(self):
        """Abre a tela de minigames"""
        sound_manager.play_effect(SoundEffect.CLICK)
        from src.scenes.minigame_select_scene.minigame_select_scene import MinigameSelectScene
        self.game.current_scene = MinigameSelectScene(self.game)

    def _open_pokedex(self):
        """Abre a Pokédex"""
        sound_manager.play_effect(SoundEffect.CLICK)
        self.game.pokedex_scene = PokedexScene(self.game)
        self.game.current_scene = self.game.pokedex_scene

    def _open_achievements(self):
        """Abre a tela de conquistas"""
        sound_manager.play_effect(SoundEffect.CLICK)
        self.game.achievement_scene = AchievementScene(self.game)
        self.game.current_scene = self.game.achievement_scene

    def _open_incubator(self):
        """Abre a tela da incubadora"""
        sound_manager.play_effect(SoundEffect.CLICK)
        self.game.incubator_scene = IncubatorScene(self.game)
        self.game.current_scene = self.game.incubator_scene

    def _on_shop_closed(self):
        self.layout_initialized = False

    def _debug_unlock_next(self):
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
        all_phases = self.catalog.get_all_phases()
        for chapter_id, phases in all_phases.items():
            for phase in phases:
                phase_id = f"{chapter_id}-{phase['number']}"
                self.progress.unlock_specific_phase(phase_id)
        self._create_phase_cards()

    def fixed_update(self, dt):
        if abs(self.scroll_y - self.scroll_target) > 0.1:
            self.scroll_y += (self.scroll_target - self.scroll_y) * min(1, dt * 10)

            if self.phase_cards:
                viewport_x = self.screen_manager.viewport_x
                viewport_y = self.screen_manager.viewport_y
                viewport_width = self.screen_manager.viewport_width

                phases = self.catalog.get_chapter_phases(self.current_chapter_id)
                if phases:
                    card_base_width = 140
                    card_margin = 20
                    available_width = viewport_width - 100
                    cols = max(2, min(5, available_width // (card_base_width + card_margin)))

                    card_width = (available_width - (cols - 1) * card_margin) // cols
                    card_width = max(100, min(160, card_width))
                    card_height = int(card_width * 1.3)

                    tab_y = viewport_y + 75
                    grid_start_y = tab_y + 65 + 45
                    grid_width = cols * card_width + (cols - 1) * card_margin
                    grid_start_x = viewport_x + (viewport_width - grid_width) // 2

                    for i, card in enumerate(self.phase_cards):
                        row = i // cols
                        col = i % cols
                        card_x = grid_start_x + col * (card_width + card_margin)
                        card_y = grid_start_y + row * (card_height + card_margin) - self.scroll_y
                        card.rect.x = card_x
                        card.rect.y = card_y

    def render(self, screen):
        self._check_resize()
        self._draw_gradient_background(screen)

        if not self.layout_initialized:
            self._create_layout()

        viewport_x = self.screen_manager.viewport_x
        viewport_y = self.screen_manager.viewport_y
        viewport_width = self.screen_manager.viewport_width
        viewport_height = self.screen_manager.viewport_height

        # Titulo
        title = self.title_font.render("SELECIONAR FASE", True, (220, 220, 230))
        title_x = viewport_x + (viewport_width - title.get_width()) // 2
        screen.blit(title, (title_x, viewport_y + 25))

        # Botao voltar
        if self.back_button:
            if self.back_button_hovered:
                bg_color = (70, 70, 80)
                border_color = (160, 160, 180)
            else:
                bg_color = (50, 50, 55)
                border_color = (90, 90, 100)

            pygame.draw.rect(screen, bg_color, self.back_button, border_radius=8)
            pygame.draw.rect(screen, border_color, self.back_button, 2, border_radius=8)
            font = pygame.font.Font(None, 40)
            text = font.render("<", True, (200, 200, 210))
            text_rect = text.get_rect(center=self.back_button.center)
            screen.blit(text, text_rect)

        # Botoes inferiores
        # Botao Loja
        if self.shop_button:
            if self.shop_button_hovered:
                bg_color = (100, 80, 60)
                border_color = (255, 215, 0)
                text_color = (255, 255, 255)
            else:
                bg_color = (70, 55, 40)
                border_color = (180, 150, 100)
                text_color = (220, 220, 200)

            shadow_rect = self.shop_button.copy()
            shadow_rect.x += 4
            shadow_rect.y += 4
            pygame.draw.rect(screen, (15, 15, 15), shadow_rect, border_radius=10)
            pygame.draw.rect(screen, bg_color, self.shop_button, border_radius=10)
            pygame.draw.rect(screen, border_color, self.shop_button, 3, border_radius=10)
            shop_text = self.button_font.render("LOJA", True, text_color)
            text_rect = shop_text.get_rect(center=self.shop_button.center)
            screen.blit(shop_text, text_rect)

        # Botao Minigames
        if self.minigame_button:
            if self.minigame_button_hovered:
                bg_color = (80, 70, 100)
                border_color = (200, 180, 255)
                text_color = (255, 255, 255)
            else:
                bg_color = (55, 45, 70)
                border_color = (130, 110, 160)
                text_color = (220, 210, 240)

            shadow_rect = self.minigame_button.copy()
            shadow_rect.x += 4
            shadow_rect.y += 4
            pygame.draw.rect(screen, (15, 15, 15), shadow_rect, border_radius=10)
            pygame.draw.rect(screen, bg_color, self.minigame_button, border_radius=10)
            pygame.draw.rect(screen, border_color, self.minigame_button, 3, border_radius=10)
            minigame_text = self.button_font.render("MINIGAMES", True, text_color)
            text_rect = minigame_text.get_rect(center=self.minigame_button.center)
            screen.blit(minigame_text, text_rect)

        # Botao Pokédex
        if self.pokedex_button:
            if self.pokedex_button_hovered:
                bg_color = (80, 60, 100)
                border_color = (255, 215, 0)
                text_color = (255, 255, 255)
            else:
                bg_color = (55, 40, 70)
                border_color = (150, 110, 180)
                text_color = (220, 210, 240)

            shadow_rect = self.pokedex_button.copy()
            shadow_rect.x += 4
            shadow_rect.y += 4
            pygame.draw.rect(screen, (15, 15, 15), shadow_rect, border_radius=10)
            pygame.draw.rect(screen, bg_color, self.pokedex_button, border_radius=10)
            pygame.draw.rect(screen, border_color, self.pokedex_button, 3, border_radius=10)

            pokedex_text = self.button_font.render("POKÉDEX", True, text_color)
            text_rect = pokedex_text.get_rect(center=self.pokedex_button.center)
            screen.blit(pokedex_text, text_rect)

        # Botao Conquistas
        if self.achievement_button:
            if self.achievement_button_hovered:
                bg_color = (100, 80, 60)
                border_color = (255, 215, 0)
                text_color = (255, 255, 255)
            else:
                bg_color = (70, 55, 40)
                border_color = (180, 150, 100)
                text_color = (220, 220, 200)

            shadow_rect = self.achievement_button.copy()
            shadow_rect.x += 4
            shadow_rect.y += 4
            pygame.draw.rect(screen, (15, 15, 15), shadow_rect, border_radius=10)
            pygame.draw.rect(screen, bg_color, self.achievement_button, border_radius=10)
            pygame.draw.rect(screen, border_color, self.achievement_button, 3, border_radius=10)

            achievement_text = self.button_font.render("CONQUISTAS", True, text_color)
            text_rect = achievement_text.get_rect(center=self.achievement_button.center)
            screen.blit(achievement_text, text_rect)

        # Botao Incubadora
        if self.incubator_button:
            is_unlocked = self._is_incubator_unlocked()

            if not is_unlocked:
                bg_color = (35, 35, 40)
                border_color = (60, 60, 65)
                text_color = (80, 80, 85)
                shadow_color = (10, 10, 10)
            elif self.incubator_button_hovered:
                bg_color = (60, 100, 80)
                border_color = (100, 220, 150)
                text_color = (255, 255, 255)
                shadow_color = (15, 15, 15)
            else:
                bg_color = (40, 70, 55)
                border_color = (80, 180, 120)
                text_color = (220, 240, 230)
                shadow_color = (15, 15, 15)

            shadow_rect = self.incubator_button.copy()
            shadow_rect.x += 4
            shadow_rect.y += 4
            pygame.draw.rect(screen, shadow_color, shadow_rect, border_radius=10)
            pygame.draw.rect(screen, bg_color, self.incubator_button, border_radius=10)
            pygame.draw.rect(screen, border_color, self.incubator_button, 3, border_radius=10)

            incubator_text = self.button_font.render("INCUBADORA", True, text_color)
            text_rect = incubator_text.get_rect(center=self.incubator_button.center)
            screen.blit(incubator_text, text_rect)

            if not is_unlocked:
                req_font = pygame.font.Font(None, 16)
                req_text = req_font.render("Complete 1-5", True, (80, 80, 80))
                req_rect = req_text.get_rect(center=(self.incubator_button.centerx, self.incubator_button.bottom + 12))
                screen.blit(req_text, req_rect)

        # Abas
        for tab in self.chapter_tabs:
            tab.render(screen, self.tab_font)

        # Nome do capitulo atual e linha decorativa
        if self.chapter_tabs:
            phases = self.catalog.get_chapter_phases(self.current_chapter_id)
            if phases:
                line_y = self.chapter_tabs[0].rect.bottom + 15
                line_width = 200
                line_x = viewport_x + (viewport_width - line_width) // 2
                pygame.draw.line(screen, (70, 70, 80), (line_x, line_y), (line_x + line_width, line_y), 1)

                total_text = f"{len(phases)} fases disponiveis"
                total_surface = self.tab_font.render(total_text, True, (180, 180, 190))
                total_x = viewport_x + (viewport_width - total_surface.get_width()) // 2
                total_y = line_y + 8
                screen.blit(total_surface, (total_x, total_y))

                line_y2 = total_y + 20
                pygame.draw.line(screen, (70, 70, 80), (line_x, line_y2), (line_x + line_width, line_y2), 1)

        # Area de clipping para os cards
        clip_rect = pygame.Rect(
            viewport_x,
            viewport_y + 160,
            viewport_width,
            viewport_height - 250
        )

        old_clip = screen.get_clip()
        screen.set_clip(clip_rect)

        for card in self.phase_cards:
            if card.rect.bottom > clip_rect.top and card.rect.top < clip_rect.bottom:
                card.render(screen, self.phase_font_large, self.phase_font_small, self.phase_font_name)

        screen.set_clip(old_clip)

        # Barra de scroll
        if self.max_scroll > 0:
            self._render_scroll_bar(screen)

        # Instrucoes
        font_small = pygame.font.Font(None, 18)
        inst_text = "< >  NAVEGAR  |  CLIQUE NA FASE  |  S  LOJA  |  M  MINIGAMES  |  X  POKÉDEX  |  C  CONQUISTAS  |  I  INCUBADORA  |  ESC  VOLTAR"
        if self.dev_mode:
            inst_text += "  |  [U] proxima fase  |  [A] todas"
        inst = font_small.render(inst_text, True, (120, 120, 130))
        inst_x = viewport_x + (viewport_width - inst.get_width()) // 2
        inst_y = viewport_y + viewport_height - 20
        screen.blit(inst, (inst_x, inst_y))

        debug_text = font_small.render("CTRL+R reset", True, (70, 70, 75))
        debug_x = viewport_x + 20
        debug_y = viewport_y + viewport_height - 45
        screen.blit(debug_text, (debug_x, debug_y))

        if self.paused:
            self._render_pause_overlay(screen)

    def _get_scroll_bar_area(self):
        viewport_x = self.screen_manager.viewport_x
        viewport_y = self.screen_manager.viewport_y
        viewport_height = self.screen_manager.viewport_height

        return (
            viewport_x + self.screen_manager.viewport_width - 20,
            viewport_y + 160,
            10,
            viewport_height - 190
        )

    def _get_scroll_bar_rect(self):
        if self.max_scroll <= 0:
            return None

        x, y, width, height = self._get_scroll_bar_area()
        scroll_height = max(30, height * (height / (height + self.max_scroll)))
        scroll_pos = y + (self.scroll_y / self.max_scroll) * (height - scroll_height)

        return pygame.Rect(x, scroll_pos, width, scroll_height)

    def _render_scroll_bar(self, screen):
        if self.max_scroll <= 0:
            return

        x, y, width, height = self._get_scroll_bar_area()
        scroll_height = max(30, height * (height / (height + self.max_scroll)))
        scroll_pos = y + (self.scroll_y / self.max_scroll) * (height - scroll_height)

        pygame.draw.rect(screen, (40, 40, 45), (x, y, width, height))

        scroll_rect = pygame.Rect(x, scroll_pos, width, scroll_height)
        if self.dragging_scroll:
            color = (120, 120, 130)
        else:
            color = (90, 90, 100)

        pygame.draw.rect(screen, color, scroll_rect)
        pygame.draw.rect(screen, (140, 140, 150), scroll_rect, 1)

    def _draw_gradient_background(self, screen):
        for i in range(self.screen_manager.window_height):
            value = int(10 + (i / self.screen_manager.window_height) * 20)
            color = (value, value, value + 3)
            pygame.draw.line(screen, color, (0, i), (self.screen_manager.window_width, i))

    def _render_pause_overlay(self, screen):
        overlay = pygame.Surface((self.screen_manager.window_width, self.screen_manager.window_height))
        overlay.set_alpha(180)
        overlay.fill((10, 10, 10))
        screen.blit(overlay, (0, 0))

        font_large = pygame.font.Font(None, 74)
        pause_text = font_large.render("PAUSADO", True, (200, 200, 200))
        text_x = (self.screen_manager.window_width - pause_text.get_width()) // 2
        text_y = (self.screen_manager.window_height - pause_text.get_height()) // 2
        screen.blit(pause_text, (text_x, text_y))

    def start_phase(self, phase_number):
        sound_manager.play_effect(SoundEffect.CLICK)
        # Para a música com fade ao ir para seleção de time
        sound_manager.stop_music(fade_ms=300)

        phase_id = f"{self.current_chapter_id}-{phase_number}"
        phase_info = self.catalog.get_phase_info(self.current_chapter_id, phase_number)

        if phase_info:
            print(f"Iniciando fase: {phase_id} - {phase_info['name']}")

        from src.scenes.team_select_scene import TeamSelectScene
        self.game.team_select_scene = TeamSelectScene(self.game, self.current_chapter_id, phase_number)
        self.game.current_scene = self.game.team_select_scene

    def on_enter(self):
        """Chamado quando a cena é ativada - inicia a música se não estiver tocando"""
        if not self._music_started or not pygame.mixer.music.get_busy():
            self._start_phase_select_music()

    def on_exit(self):
        """Chamado quando a cena é desativada - para a música"""
        sound_manager.stop_music(fade_ms=300)
        self._music_started = False