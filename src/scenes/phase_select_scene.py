"""
Tela de seleção de fases
"""
import pygame
import math
from src.scenes.base_scene import BaseScene
from src.scenes.game_scene import GameScene
from src.config.progress import progress_manager

class PhaseCard:
    def __init__(self, phase_number, chapter_id, unlocked=False, completed=False):
        self.phase_number = phase_number
        self.chapter_id = chapter_id
        self.unlocked = unlocked
        self.completed = completed
        self.rect = pygame.Rect(0, 0, 0, 0)
        self.is_hovered = False

        # Cores monocromáticas
        if not unlocked:
            # Bloqueada - cinza escuro
            self.bg_color = (30, 30, 35)
            self.border_color = (50, 50, 55)
            self.text_color = (80, 80, 85)
        elif completed:
            # Completada - cinza claro com detalhe verde sutil
            self.bg_color = (40, 45, 40)
            self.border_color = (70, 100, 70)
            self.text_color = (180, 220, 180)
        else:
            # Disponível - cinza médio com detalhe azul sutil
            self.bg_color = (45, 45, 50)
            self.border_color = (80, 100, 130)
            self.text_color = (220, 220, 240)

    def update_position(self, x, y, width, height):
        self.rect = pygame.Rect(x, y, width, height)

    def handle_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            self.is_hovered = self.rect.collidepoint(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.is_hovered and self.unlocked:
                return self.phase_number
        return None

    def render(self, screen, font_large, font_small):
        # Efeito hover (só para fases disponíveis)
        if self.is_hovered and self.unlocked:
            color = tuple(min(255, c + 20) for c in self.bg_color)
            border = tuple(min(255, c + 30) for c in self.border_color)
        else:
            color = self.bg_color
            border = self.border_color

        # Sombra suave
        shadow_rect = self.rect.copy()
        shadow_rect.x += 4
        shadow_rect.y += 4
        pygame.draw.rect(screen, (15, 15, 15), shadow_rect, border_radius=12)

        # Card principal
        pygame.draw.rect(screen, color, self.rect, border_radius=12)
        pygame.draw.rect(screen, border, self.rect, 2, border_radius=12)

        # Número da fase (grande)
        text = font_large.render(str(self.phase_number), True, self.text_color)
        text_rect = text.get_rect(center=(self.rect.centerx, self.rect.centery - 12))
        screen.blit(text, text_rect)

        # Texto de status
        if not self.unlocked:
            status = font_small.render("BLOQUEADA", True, (100, 100, 100))
        elif self.completed:
            status = font_small.render("CONCLUÍDA", True, (140, 200, 140))
        else:
            status = font_small.render("DISPONÍVEL", True, (140, 140, 200))

        status_rect = status.get_rect(center=(self.rect.centerx, self.rect.centery + 18))
        screen.blit(status, status_rect)

        # Overlay para fases bloqueadas
        if not self.unlocked:
            overlay = pygame.Surface((self.rect.width, self.rect.height), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 180))
            screen.blit(overlay, self.rect)

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
        # Cores monocromáticas para abas
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

        # Referência ao progress manager
        self.progress = progress_manager

        # Configurações de grid por capítulo
        self.grid_config = {
            1: {"cols": 4, "rows": 2},   # 8 fases
            2: {"cols": 5, "rows": 1},   # 5 fases
            3: {"cols": 5, "rows": 2},   # 10 fases
            4: {"cols": 3, "rows": 2},   # 6 fases
            5: {"cols": 4, "rows": 3},   # 12 fases
        }

        # Dados das fases
        self.chapters = self._create_chapters()

        # Estado atual
        self.current_chapter_id = self._get_first_available_chapter()

        # Botões
        self.chapter_tabs = []
        self.phase_cards = []
        self.back_button = None

        # Flag para controlar se já criou os cards
        self.layout_initialized = False

        # Fontes
        self.title_font = pygame.font.Font(None, 52)
        self.tab_font = pygame.font.Font(None, 22)
        self.phase_font_large = pygame.font.Font(None, 36)
        self.phase_font_small = pygame.font.Font(None, 16)

        # Último tamanho da tela para detectar redimensionamento
        self.last_window_size = (self.screen_manager.window_width, self.screen_manager.window_height)

    def _create_chapters(self):
        """Cria os capítulos com suas fases"""
        return {
            1: {"id": 1, "name": "CAPÍTULO I", "full_name": "Início da Jornada", "phases": list(range(1, 9))},
            2: {"id": 2, "name": "CAPÍTULO II", "full_name": "Floresta Sombria", "phases": list(range(9, 14))},
            3: {"id": 3, "name": "CAPÍTULO III", "full_name": "Montanhas Gélidas", "phases": list(range(14, 24))},
            4: {"id": 4, "name": "CAPÍTULO IV", "full_name": "Caverna Misteriosa", "phases": list(range(24, 30))},
            5: {"id": 5, "name": "CAPÍTULO V", "full_name": "Torre do Dragão", "phases": list(range(30, 42))},
        }

    def _get_first_available_chapter(self):
        """Retorna o primeiro capítulo com fases desbloqueadas"""
        for chapter_id, chapter in self.chapters.items():
            for phase in chapter["phases"]:
                if self.progress.is_phase_unlocked(phase):
                    return chapter_id
        return 1

    def _check_resize(self):
        """Verifica se a tela foi redimensionada e recria layout se necessário"""
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

        # Área das abas
        tab_width = 130
        tab_height = 65
        tab_spacing = 15
        tabs_total_width = len(self.chapters) * (tab_width + tab_spacing) - tab_spacing
        tab_start_x = viewport_x + (viewport_width - tabs_total_width) // 2
        tab_y = viewport_y + 75

        self.chapter_tabs = []
        for i, (chapter_id, chapter) in enumerate(self.chapters.items()):
            tab_x = tab_start_x + i * (tab_width + tab_spacing)
            progress = self.progress.get_chapter_progress(chapter_id, chapter["phases"])

            tab = ChapterTab(chapter_id, chapter["name"], progress)
            tab.update_position(tab_x, tab_y, tab_width, tab_height)
            tab.active = (chapter_id == self.current_chapter_id)
            self.chapter_tabs.append(tab)

        # Cria cards das fases
        self._create_phase_cards()

        self.layout_initialized = True

    def _create_phase_cards(self):
        """Cria os cards das fases para o capítulo atual"""
        viewport_width = self.screen_manager.viewport_width
        viewport_height = self.screen_manager.viewport_height
        viewport_x = self.screen_manager.viewport_x
        viewport_y = self.screen_manager.viewport_y

        # Configuração do grid
        grid_config = self.grid_config.get(self.current_chapter_id, {"cols": 4, "rows": 2})
        cols = grid_config["cols"]

        # Tamanho dos cards - responsivo
        card_margin = 25
        available_width = viewport_width - 120

        # Calcula tamanho ideal dos cards baseado no espaço disponível
        card_width = (available_width - (cols - 1) * card_margin) // cols
        # Limita tamanho mínimo e máximo
        card_width = max(80, min(120, card_width))
        card_height = int(card_width * 1.2)

        # Posição inicial do grid
        tab_y = viewport_y + 75
        grid_start_y = tab_y + 65 + 45
        grid_width = cols * card_width + (cols - 1) * card_margin
        grid_start_x = viewport_x + (viewport_width - grid_width) // 2

        # Cria cards
        self.phase_cards = []
        chapter_phases = self.chapters[self.current_chapter_id]["phases"]

        for i, phase_num in enumerate(chapter_phases):
            row = i // cols
            col = i % cols

            card_x = grid_start_x + col * (card_width + card_margin)
            card_y = grid_start_y + row * (card_height + card_margin)

            unlocked = self.progress.is_phase_unlocked(phase_num)
            completed = self.progress.is_phase_completed(phase_num)

            card = PhaseCard(phase_num, self.current_chapter_id, unlocked, completed)
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
                chapters = list(self.chapters.keys())
                current_idx = chapters.index(self.current_chapter_id)
                if current_idx > 0:
                    self.current_chapter_id = chapters[current_idx - 1]
                    self._create_phase_cards()
                    for tab in self.chapter_tabs:
                        tab.active = (tab.chapter_id == self.current_chapter_id)
            elif event.key == pygame.K_RIGHT:
                chapters = list(self.chapters.keys())
                current_idx = chapters.index(self.current_chapter_id)
                if current_idx < len(chapters) - 1:
                    self.current_chapter_id = chapters[current_idx + 1]
                    self._create_phase_cards()
                    for tab in self.chapter_tabs:
                        tab.active = (tab.chapter_id == self.current_chapter_id)
            elif event.key == pygame.K_r and pygame.key.get_mods() & pygame.KMOD_CTRL:
                self.progress.reset_progress()
                self.current_chapter_id = self._get_first_available_chapter()
                self._create_phase_cards()
                for tab in self.chapter_tabs:
                    tab.active = (tab.chapter_id == self.current_chapter_id)

        elif event.type == pygame.VIDEORESIZE:
            # Quando a tela é redimensionada, marcamos para recriar o layout
            self.layout_initialized = False

        elif event.type == pygame.MOUSEMOTION:
            for card in self.phase_cards:
                card.handle_event(event)
            for tab in self.chapter_tabs:
                tab.handle_event(event)

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
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

            # Cards de fase
            for card in self.phase_cards:
                result = card.handle_event(event)
                if result:
                    self.start_phase(result)
                    return

    def fixed_update(self, dt):
        """Update fixo para lógica"""
        pass

    def render(self, screen):
        """Renderiza a tela de seleção"""
        # Verifica se a tela foi redimensionada
        self._check_resize()

        # Fundo gradiente
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

        # Nome do capítulo atual
        if self.chapter_tabs:
            chapter = self.chapters[self.current_chapter_id]

            # Linhas decorativas
            line_y = self.chapter_tabs[0].rect.bottom + 15
            line_width = 200
            line_x = self.screen_manager.viewport_x + (self.screen_manager.viewport_width - line_width) // 2
            pygame.draw.line(screen, (70, 70, 80), (line_x, line_y), (line_x + line_width, line_y), 1)

            chapter_surface = self.tab_font.render(chapter['full_name'], True, (180, 180, 190))
            chapter_x = self.screen_manager.viewport_x + (self.screen_manager.viewport_width - chapter_surface.get_width()) // 2
            chapter_y = line_y + 8
            screen.blit(chapter_surface, (chapter_x, chapter_y))

            line_y2 = chapter_y + 20
            pygame.draw.line(screen, (70, 70, 80), (line_x, line_y2), (line_x + line_width, line_y2), 1)

        # Grid de fases
        for card in self.phase_cards:
            card.render(screen, self.phase_font_large, self.phase_font_small)

        # Instruções
        font_small = pygame.font.Font(None, 18)
        inst_text = "< >  NAVEGAR  |  CLIQUE NA FASE  |  ESC  VOLTAR"
        inst = font_small.render(inst_text, True, (120, 120, 130))
        inst_x = self.screen_manager.viewport_x + (self.screen_manager.viewport_width - inst.get_width()) // 2
        inst_y = self.screen_manager.viewport_y + self.screen_manager.viewport_height - 25
        screen.blit(inst, (inst_x, inst_y))

        # Debug (opcional)
        debug_text = font_small.render("CTRL+R reset", True, (70, 70, 75))
        debug_x = self.screen_manager.viewport_x + 20
        debug_y = self.screen_manager.viewport_y + self.screen_manager.viewport_height - 25
        screen.blit(debug_text, (debug_x, debug_y))

        # Overlay de pausa
        if self.paused:
            self._render_pause_overlay(screen)

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
        self.game.current_scene = GameScene(self.game, phase_number)