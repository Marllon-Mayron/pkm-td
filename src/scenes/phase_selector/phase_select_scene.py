# src/scenes/phase_select_scene.py

"""
Tela de seleção de fases - Versão dinâmica com scroll
"""
import pygame
import math
from src.scenes.base_scene import BaseScene
from src.config.progress import progress_manager
from src.config.phase_catalog import phase_catalog
from src.scenes.game_scene.game_scene import GameScene
from src.scenes.team_select_scene import TeamSelectScene


class PhaseCard:
    def __init__(self, phase_data, unlocked=False, completed=False):
        self.phase_data = phase_data
        self.phase_number = phase_data["number"]
        self.phase_name = phase_data["name"]
        self.chapter_id = phase_data["chapter"]
        self.unlocked = unlocked
        self.completed = completed
        self.rect = pygame.Rect(0, 0, 0, 0)
        self.is_hovered = False

        # Cores baseadas no status (mantendo o estilo monocromático)
        if not unlocked:
            # Bloqueada - cinza escuro
            self.bg_color = (30, 30, 35)
            self.border_color = (50, 50, 55)
            self.text_color = (80, 80, 85)
            self.name_color = (100, 100, 105)
        elif completed:
            # Completada - cinza claro com detalhe verde sutil
            self.bg_color = (40, 45, 40)
            self.border_color = (70, 100, 70)
            self.text_color = (180, 220, 180)
            self.name_color = (200, 240, 200)
        else:
            # Disponível - cinza médio com detalhe azul sutil
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
            return was_hovered != self.is_hovered  # Retorna se houve mudança
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.is_hovered and self.unlocked:
                return self.phase_number
        return None

    def render(self, screen, font_large, font_small, font_name):
        # Efeito hover (só para fases disponíveis)
        if self.is_hovered and self.unlocked:
            color = tuple(min(255, c + 20) for c in self.bg_color)
            border = tuple(min(255, c + 30) for c in self.border_color)
            name_color = tuple(min(255, c + 40) for c in self.name_color)
        else:
            color = self.bg_color
            border = self.border_color
            name_color = self.name_color

        # Sombra suave
        shadow_rect = self.rect.copy()
        shadow_rect.x += 4
        shadow_rect.y += 4
        pygame.draw.rect(screen, (15, 15, 15), shadow_rect, border_radius=12)

        # Card principal
        pygame.draw.rect(screen, color, self.rect, border_radius=12)
        pygame.draw.rect(screen, border, self.rect, 2, border_radius=12)

        # Número da fase (pequeno no canto)
        num_text = font_small.render(f"#{self.phase_number}", True, self.text_color)
        screen.blit(num_text, (self.rect.x + 8, self.rect.y + 8))

        # Nome da fase (centralizado, com quebra de linha se necessário)
        self._render_wrapped_text(screen, self.phase_name, font_name, name_color,
                                 self.rect.centerx, self.rect.centery - 15)

        # Texto de status
        if not self.unlocked:
            status = font_small.render("BLOQUEADA", True, (100, 100, 100))
        elif self.completed:
            status = font_small.render("CONCLUÍDA", True, (140, 200, 140))
        else:
            status = font_small.render("DISPONÍVEL", True, (140, 140, 200))

        status_rect = status.get_rect(center=(self.rect.centerx, self.rect.centery + 25))
        screen.blit(status, status_rect)

        # Overlay para fases bloqueadas
        if not self.unlocked:
            overlay = pygame.Surface((self.rect.width, self.rect.height), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 180))
            screen.blit(overlay, self.rect)

    def _render_wrapped_text(self, screen, text, font, color, center_x, center_y):
        """Renderiza texto com quebra de linha se necessário"""
        words = text.split()
        if not words:
            return

        # Se o texto couber em uma linha
        single_line = font.render(text, True, color)
        if single_line.get_width() <= self.rect.width - 20:
            text_rect = single_line.get_rect(center=(center_x, center_y))
            screen.blit(single_line, text_rect)
            return

        # Tenta dividir em duas linhas
        if len(words) == 1:
            # Palavra única muito longa - trunca
            while font.render(words[0] + "...", True, color).get_width() > self.rect.width - 20:
                words[0] = words[0][:-1]
            truncated = font.render(words[0] + "...", True, color)
            text_rect = truncated.get_rect(center=(center_x, center_y))
            screen.blit(truncated, text_rect)
            return

        # Divide em duas linhas
        mid = len(words) // 2
        line1 = " ".join(words[:mid])
        line2 = " ".join(words[mid:])

        # Verifica se as linhas cabem
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
        self.active = False

    def update_position(self, x, y, width, height):
        self.rect = pygame.Rect(x, y, width, height)

    def handle_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            self.is_hovered = self.rect.collidepoint(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.is_hovered:
                return self.chapter_id
        return None

    def render(self, screen, font):
        # Cores para abas
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

        # Desenha aba
        pygame.draw.rect(screen, color, self.rect)
        pygame.draw.rect(screen, border, self.rect, 2)

        # Nome do capítulo
        text = font.render(self.name, True, text_color)
        text_rect = text.get_rect(center=(self.rect.centerx, self.rect.centery - 8))
        screen.blit(text, text_rect)

        # Progresso
        progress_text = f"{self.progress['completed']}/{self.progress['total']}"
        progress_surface = font.render(progress_text, True, text_color)
        progress_rect = progress_surface.get_rect(center=(self.rect.centerx, self.rect.centery + 10))
        screen.blit(progress_surface, progress_rect)


class PhaseSelectScene(BaseScene):
    def __init__(self, game):
        super().__init__(game)

        # Referências
        self.progress = progress_manager
        self.catalog = phase_catalog

        # Estado atual
        self.available_chapters = sorted(self.catalog.get_all_phases().keys())
        self.current_chapter_id = self._get_first_available_chapter()

        # Elementos UI
        self.chapter_tabs = []
        self.phase_cards = []
        self.back_button = None

        # Scroll
        self.scroll_y = 0
        self.scroll_target = 0
        self.max_scroll = 0
        self.scroll_speed = 500
        self.dragging_scroll = False
        self.last_mouse_y = 0

        # Layout
        self.layout_initialized = False
        self.last_window_size = (self.screen_manager.window_width, self.screen_manager.window_height)

        # Fontes
        self.title_font = pygame.font.Font(None, 52)
        self.tab_font = pygame.font.Font(None, 22)
        self.phase_font_large = pygame.font.Font(None, 36)
        self.phase_font_small = pygame.font.Font(None, 16)
        self.phase_font_name = pygame.font.Font(None, 18)

        # Animação
        self.hover_changed = False

    def _get_first_available_chapter(self):
        """Retorna o primeiro capítulo com fases desbloqueadas"""
        if not self.available_chapters:
            return 1

        for chapter_id in self.available_chapters:
            phases = self.catalog.get_chapter_phases(chapter_id)
            for phase in phases:
                if self.progress.is_phase_unlocked(phase["number"]):
                    return chapter_id
        return self.available_chapters[0]

    def _check_resize(self):
        """Verifica se a tela foi redimensionada"""
        current_size = (self.screen_manager.window_width, self.screen_manager.window_height)
        if current_size != self.last_window_size:
            self.last_window_size = current_size
            self.layout_initialized = False
            return True
        return False

    def _create_layout(self):
        """Cria o layout dos elementos"""
        viewport_width = self.screen_manager.viewport_width
        viewport_height = self.screen_manager.viewport_height
        viewport_x = self.screen_manager.viewport_x
        viewport_y = self.screen_manager.viewport_y

        # Botão voltar
        back_size = 45
        self.back_button = pygame.Rect(
            viewport_x + 30,
            viewport_y + 25,
            back_size,
            back_size
        )

        # Área das abas - só mostra capítulos que existem
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
                progress = self.progress.get_chapter_progress(
                    chapter_id,
                    [p["number"] for p in phases]
                )

                tab = ChapterTab(chapter_id, f"CAPÍTULO {chapter_id}", progress)
                tab.update_position(tab_x, tab_y, tab_width, tab_height)
                tab.active = (chapter_id == self.current_chapter_id)
                self.chapter_tabs.append(tab)

        # Cria cards das fases
        self._create_phase_cards()

        self.layout_initialized = True
        self.scroll_y = 0
        self.scroll_target = 0

    def _create_phase_cards(self):
        """Cria os cards das fases para o capítulo atual"""
        viewport_width = self.screen_manager.viewport_width
        viewport_height = self.screen_manager.viewport_height
        viewport_x = self.screen_manager.viewport_x
        viewport_y = self.screen_manager.viewport_y

        # Pega as fases do capítulo atual
        phases = self.catalog.get_chapter_phases(self.current_chapter_id)
        if not phases:
            self.phase_cards = []
            self.max_scroll = 0
            return

        # Define número de colunas baseado no espaço disponível
        card_base_width = 140
        card_margin = 20

        # Calcula quantas colunas cabem
        available_width = viewport_width - 100
        cols = max(2, min(5, available_width // (card_base_width + card_margin)))

        # Ajusta tamanho dos cards
        card_width = (available_width - (cols - 1) * card_margin) // cols
        card_width = max(100, min(160, card_width))
        card_height = int(card_width * 1.3)

        # Posição inicial do grid
        tab_y = viewport_y + 75
        grid_start_y = tab_y + 65 + 45
        grid_width = cols * card_width + (cols - 1) * card_margin
        grid_start_x = viewport_x + (viewport_width - grid_width) // 2

        # Calcula número de linhas
        rows = math.ceil(len(phases) / cols)
        grid_height = rows * (card_height + card_margin)

        # Área visível do grid
        visible_height = viewport_height - (grid_start_y - viewport_y) - 60
        self.max_scroll = max(0, grid_height - visible_height)

        # Cria cards
        self.phase_cards = []
        for i, phase_data in enumerate(phases):
            row = i // cols
            col = i % cols

            card_x = grid_start_x + col * (card_width + card_margin)
            card_y = grid_start_y + row * (card_height + card_margin) - self.scroll_y

            unlocked = self.progress.is_phase_unlocked(phase_data["number"])
            completed = self.progress.is_phase_completed(phase_data["number"])

            card = PhaseCard(phase_data, unlocked, completed)
            card.update_position(card_x, card_y, card_width, card_height)
            self.phase_cards.append(card)

    def handle_event(self, event):
        """Processa eventos"""
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_p:
                self.toggle_pause()
            elif event.key == pygame.K_ESCAPE:
                self.game.current_scene = self.game.menu_scene
            elif event.key == pygame.K_LEFT:
                if self.available_chapters:
                    current_idx = self.available_chapters.index(self.current_chapter_id)
                    if current_idx > 0:
                        self.current_chapter_id = self.available_chapters[current_idx - 1]
                        self._create_phase_cards()
                        for tab in self.chapter_tabs:
                            tab.active = (tab.chapter_id == self.current_chapter_id)
            elif event.key == pygame.K_RIGHT:
                if self.available_chapters:
                    current_idx = self.available_chapters.index(self.current_chapter_id)
                    if current_idx < len(self.available_chapters) - 1:
                        self.current_chapter_id = self.available_chapters[current_idx + 1]
                        self._create_phase_cards()
                        for tab in self.chapter_tabs:
                            tab.active = (tab.chapter_id == self.current_chapter_id)
            elif event.key == pygame.K_r and pygame.key.get_mods() & pygame.KMOD_CTRL:
                self.progress.reset_progress()
                self.catalog.refresh()  # Recarrega catálogo
                self.available_chapters = sorted(self.catalog.get_all_phases().keys())
                self.current_chapter_id = self._get_first_available_chapter()
                self.layout_initialized = False

        elif event.type == pygame.VIDEORESIZE:
            self.layout_initialized = False

        elif event.type == pygame.MOUSEWHEEL:
            if self.phase_cards and self.max_scroll > 0:
                self.scroll_target += event.y * -30  # Invertido para scroll natural
                self.scroll_target = max(0, min(self.max_scroll, self.scroll_target))

        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:  # Left click
                # Botão voltar
                if self.back_button and self.back_button.collidepoint(event.pos):
                    self.game.current_scene = self.game.menu_scene
                    return

                # Abas de capítulo
                for tab in self.chapter_tabs:
                    result = tab.handle_event(event)
                    if result:
                        self.current_chapter_id = result
                        self._create_phase_cards()
                        for t in self.chapter_tabs:
                            t.active = (t.chapter_id == self.current_chapter_id)
                        return

                # Scroll dragging
                if self.phase_cards and self.max_scroll > 0:
                    scroll_bar_rect = self._get_scroll_bar_rect()
                    if scroll_bar_rect and scroll_bar_rect.collidepoint(event.pos):
                        self.dragging_scroll = True
                        self.last_mouse_y = event.pos[1]
                        return

                # Cards de fase
                for card in self.phase_cards:
                    result = card.handle_event(event)
                    if result:
                        self.start_phase(result)
                        return

            elif event.button == 3:  # Right click - reset scroll (opcional)
                self.scroll_target = 0
                self.scroll_y = 0

        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1:
                self.dragging_scroll = False

        elif event.type == pygame.MOUSEMOTION:
            # Atualiza hover dos cards
            hover_changed = False
            for card in self.phase_cards:
                result = card.handle_event(event)
                if result:
                    hover_changed = True

            for tab in self.chapter_tabs:
                tab.handle_event(event)

            # Scroll dragging
            if self.dragging_scroll:
                dy = event.pos[1] - self.last_mouse_y
                scroll_speed = self.max_scroll / self._get_scroll_bar_area()[1]
                self.scroll_target += dy * scroll_speed * 2
                self.scroll_target = max(0, min(self.max_scroll, self.scroll_target))
                self.last_mouse_y = event.pos[1]

    def fixed_update(self, dt):
        """Update com suavização do scroll"""
        # Suaviza o scroll
        if abs(self.scroll_y - self.scroll_target) > 0.1:
            self.scroll_y += (self.scroll_target - self.scroll_y) * min(1, dt * 10)

            # Atualiza posição dos cards
            if self.phase_cards:
                viewport_x = self.screen_manager.viewport_x
                viewport_y = self.screen_manager.viewport_y
                viewport_width = self.screen_manager.viewport_width

                # Recalcula grid (simplificado - só atualiza Y)
                phases = self.catalog.get_chapter_phases(self.current_chapter_id)
                if phases:
                    # Determina número de colunas (mesmo cálculo do _create_phase_cards)
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
        """Renderiza a tela de seleção"""
        # Verifica resize
        self._check_resize()

        # Fundo
        self._draw_gradient_background(screen)

        # Cria layout se necessário
        if not self.layout_initialized:
            self._create_layout()

        # Título
        title = self.title_font.render("SELECIONAR FASE", True, (220, 220, 230))
        title_x = self.screen_manager.viewport_x + (self.screen_manager.viewport_width - title.get_width()) // 2
        screen.blit(title, (title_x, self.screen_manager.viewport_y + 25))

        # Botão voltar
        if self.back_button:
            pygame.draw.rect(screen, (50, 50, 55), self.back_button, border_radius=8)
            pygame.draw.rect(screen, (90, 90, 100), self.back_button, 2, border_radius=8)
            font = pygame.font.Font(None, 40)
            text = font.render("<", True, (200, 200, 210))
            text_rect = text.get_rect(center=self.back_button.center)
            screen.blit(text, text_rect)

        # Abas
        for tab in self.chapter_tabs:
            tab.render(screen, self.tab_font)

        # Nome do capítulo atual e linha decorativa
        if self.chapter_tabs:
            phases = self.catalog.get_chapter_phases(self.current_chapter_id)
            if phases:
                # Linhas decorativas
                line_y = self.chapter_tabs[0].rect.bottom + 15
                line_width = 200
                line_x = self.screen_manager.viewport_x + (self.screen_manager.viewport_width - line_width) // 2
                pygame.draw.line(screen, (70, 70, 80), (line_x, line_y), (line_x + line_width, line_y), 1)

                # Total de fases
                total_text = f"{len(phases)} fases disponíveis"
                total_surface = self.tab_font.render(total_text, True, (180, 180, 190))
                total_x = self.screen_manager.viewport_x + (self.screen_manager.viewport_width - total_surface.get_width()) // 2
                total_y = line_y + 8
                screen.blit(total_surface, (total_x, total_y))

                line_y2 = total_y + 20
                pygame.draw.line(screen, (70, 70, 80), (line_x, line_y2), (line_x + line_width, line_y2), 1)

        # Área de clipping para os cards (para scroll funcionar)
        viewport_x = self.screen_manager.viewport_x
        viewport_y = self.screen_manager.viewport_y
        viewport_width = self.screen_manager.viewport_width
        viewport_height = self.screen_manager.viewport_height

        # Define área de clipping
        clip_rect = pygame.Rect(
            viewport_x,
            viewport_y + 160,  # Começa depois das abas
            viewport_width,
            viewport_height - 190  # Altura disponível
        )

        old_clip = screen.get_clip()
        screen.set_clip(clip_rect)

        # Grid de fases
        for card in self.phase_cards:
            # Só renderiza se estiver dentro da área de clipping
            if card.rect.bottom > clip_rect.top and card.rect.top < clip_rect.bottom:
                card.render(screen, self.phase_font_large, self.phase_font_small, self.phase_font_name)

        # Restaura clipping
        screen.set_clip(old_clip)

        # Barra de scroll (se necessário)
        if self.max_scroll > 0:
            self._render_scroll_bar(screen)

        # Instruções
        font_small = pygame.font.Font(None, 18)
        inst_text = "< >  NAVEGAR  |  CLIQUE NA FASE  |  ESC  VOLTAR"
        inst = font_small.render(inst_text, True, (120, 120, 130))
        inst_x = self.screen_manager.viewport_x + (self.screen_manager.viewport_width - inst.get_width()) // 2
        inst_y = self.screen_manager.viewport_y + self.screen_manager.viewport_height - 25
        screen.blit(inst, (inst_x, inst_y))

        # Debug
        debug_text = font_small.render("CTRL+R reset", True, (70, 70, 75))
        debug_x = self.screen_manager.viewport_x + 20
        debug_y = self.screen_manager.viewport_y + self.screen_manager.viewport_height - 25
        screen.blit(debug_text, (debug_x, debug_y))

        # Overlay de pausa
        if self.paused:
            self._render_pause_overlay(screen)

    def _get_scroll_bar_area(self):
        """Retorna a área onde a barra de scroll pode ser desenhada"""
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
        """Retorna o retângulo da barra de scroll para detecção de clique"""
        if self.max_scroll <= 0:
            return None

        x, y, width, height = self._get_scroll_bar_area()
        scroll_height = max(30, height * (height / (height + self.max_scroll)))
        scroll_pos = y + (self.scroll_y / self.max_scroll) * (height - scroll_height)

        return pygame.Rect(x, scroll_pos, width, scroll_height)

    def _render_scroll_bar(self, screen):
        """Renderiza a barra de scroll"""
        if self.max_scroll <= 0:
            return

        x, y, width, height = self._get_scroll_bar_area()
        scroll_height = max(30, height * (height / (height + self.max_scroll)))
        scroll_pos = y + (self.scroll_y / self.max_scroll) * (height - scroll_height)

        # Fundo da barra
        pygame.draw.rect(screen, (40, 40, 45), (x, y, width, height))

        # Barra de scroll
        scroll_rect = pygame.Rect(x, scroll_pos, width, scroll_height)
        if self.dragging_scroll:
            color = (120, 120, 130)
        else:
            color = (90, 90, 100)

        pygame.draw.rect(screen, color, scroll_rect)
        pygame.draw.rect(screen, (140, 140, 150), scroll_rect, 1)

    def _draw_gradient_background(self, screen):
        """Desenha fundo com gradiente"""
        for i in range(self.screen_manager.window_height):
            value = int(10 + (i / self.screen_manager.window_height) * 20)
            color = (value, value, value + 3)
            pygame.draw.line(screen, color, (0, i), (self.screen_manager.window_width, i))

    def _render_pause_overlay(self, screen):
        """Overlay de pausa"""
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
        """Inicia a fase selecionada"""
        # Pega informações da fase
        phase_info = self.catalog.get_phase_info(self.current_chapter_id, phase_number)
        if phase_info:
            print(f"Iniciando fase: {phase_info['name']}")

        # Vai para a tela de seleção de time
        # Importa aqui para evitar import circular
        from src.scenes.team_select_scene import TeamSelectScene

        # Cria a cena se não existir ou recria
        self.game.team_select_scene = TeamSelectScene(self.game)
        self.game.current_scene = self.game.team_select_scene