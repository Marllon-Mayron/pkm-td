# src/scenes/menu_scene.py

"""
Cena do menu principal
"""
import pygame
import random

from src.scenes.base_scene import BaseScene
from src.scenes.phase_selector.phase_select_scene import PhaseSelectScene
from src.scenes.settings_scene.settings_scene import SettingsScene


class Button:
    def __init__(self, x, y, width, height, text, color, hover_color, callback, font):
        # Coordenadas relativas (0-1) para responsividade
        self.relative_x = x
        self.relative_y = y
        self.relative_width = width
        self.relative_height = height

        # Valores absolutos calculados
        self.rect = pygame.Rect(0, 0, 0, 0)
        self.text = text
        self.color = color
        self.hover_color = hover_color
        self.callback = callback
        self.is_hovered = False
        self.font = font

        # Texto pré-renderizado
        self.text_surface = None
        self.text_rect = None

    def update_absolute_position(self, viewport_width, viewport_height, viewport_x, viewport_y):
        """Atualiza posição absoluta baseada no tamanho do viewport"""
        # Calcula posição absoluta dentro do viewport
        abs_x = viewport_x + int(self.relative_x * viewport_width)
        abs_y = viewport_y + int(self.relative_y * viewport_height)
        abs_width = int(self.relative_width * viewport_width)
        abs_height = int(self.relative_height * viewport_height)

        self.rect = pygame.Rect(abs_x, abs_y, abs_width, abs_height)

        # Atualiza texto
        font_size = max(24, int(viewport_height * 0.05))
        self.font = pygame.font.Font(None, font_size)
        self.text_surface = self.font.render(self.text, True, (255, 255, 255))
        self.text_rect = self.text_surface.get_rect(center=self.rect.center)

    def handle_event(self, event):
        """Processa eventos sem precisar de viewport_offset"""
        if event.type == pygame.MOUSEMOTION:
            self.is_hovered = self.rect.collidepoint(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.is_hovered:
                self.callback()

    def render(self, screen):
        """Renderiza botão"""
        if not self.text_surface:
            return

        # Desenha botão
        color = self.hover_color if self.is_hovered else self.color
        pygame.draw.rect(screen, color, self.rect)
        pygame.draw.rect(screen, (255, 255, 255), self.rect, 3)

        # Desenha texto
        screen.blit(self.text_surface, self.text_rect)


class MenuScene(BaseScene):
    def __init__(self, game):
        super().__init__(game)

        # Logo
        self.logo = None
        self.create_logo()

        # Botões - "Iniciar Jogo" agora verifica save
        self.buttons = [
            Button(0.3, 0.5, 0.4, 0.08, "Iniciar Jogo",
                  (100, 100, 0), (150, 150, 0), self.start_game, None),
            Button(0.3, 0.6, 0.4, 0.08, "Configurações",
                  (100, 100, 0), (150, 150, 0), self.open_settings, None),
            Button(0.3, 0.4, 0.4, 0.08, "Editor de Fases",
                   (100, 100, 0), (150, 150, 0), self.open_editor, None),
            Button(0.015, 0.86, 0.15, 0.06, "Mystery Gift",
                   (100, 50, 100), (150, 80, 150), self.open_mystery_gift, None),
            Button(0.3, 0.7, 0.4, 0.08, "Sair",
                  (100, 0, 0), (150, 0, 0), self.quit_game, None)

        ]

        # Partículas
        self.particles = []
        self.create_particles()

    def create_logo(self):
        """Cria um logo simples"""
        self.logo = pygame.Surface((400, 100), pygame.SRCALPHA)
        pygame.draw.rect(self.logo, (255, 215, 0), (0, 0, 400, 100), border_radius=20)
        pygame.draw.rect(self.logo, (200, 0, 0), (10, 10, 380, 80), border_radius=15)

        font = pygame.font.Font(None, 48)
        text = font.render("POKEMON", True, (255, 255, 255))
        text_rect = text.get_rect(center=(200, 35))
        self.logo.blit(text, text_rect)

        text2 = font.render("TOWER DEFENSE", True, (255, 255, 255))
        text_rect2 = text2.get_rect(center=(200, 70))
        self.logo.blit(text2, text_rect2)

    def create_particles(self):
        """Cria partículas decorativas"""
        for _ in range(20):
            self.particles.append({
                'x': pygame.math.Vector2(
                    random.uniform(0, self.screen_manager.render_width),
                    random.uniform(0, self.screen_manager.render_height)
                ),
                'vel': pygame.math.Vector2(
                    random.uniform(-20, 20),
                    random.uniform(-20, 20)
                ),
                'color': (random.randint(100, 255),
                         random.randint(100, 255),
                         random.randint(100, 255)),
                'size': random.randint(2, 5)
            })

    def handle_event(self, event):
        """Processa eventos"""
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_p:
                self.toggle_pause()
            elif event.key == pygame.K_RETURN:
                self.start_game()

        for button in self.buttons:
            button.handle_event(event)

    def fixed_update(self, dt):
        """Update para animações"""
        if self.paused:
            return

        for particle in self.particles:
            particle['x'] += particle['vel'] * dt
            if particle['x'].x < 0 or particle['x'].x > self.screen_manager.render_width:
                particle['vel'].x *= -1
            if particle['x'].y < 0 or particle['x'].y > self.screen_manager.render_height:
                particle['vel'].y *= -1

    def render(self, screen):
        """Renderiza o menu"""
        self._draw_gradient_background(screen)

        # Atualiza posições dos botões
        for button in self.buttons:
            button.update_absolute_position(
                self.screen_manager.viewport_width,
                self.screen_manager.viewport_height,
                self.screen_manager.viewport_x,
                self.screen_manager.viewport_y
            )

        # Desenha partículas
        for particle in self.particles:
            screen_x = self.screen_manager.viewport_x + int(particle['x'].x)
            screen_y = self.screen_manager.viewport_y + int(particle['x'].y)
            pygame.draw.circle(screen, particle['color'], (screen_x, screen_y), particle['size'])

        # Desenha logo
        logo_width = int(self.screen_manager.viewport_width * 0.4)
        logo_height = int(self.screen_manager.viewport_height * 0.15)
        logo_scaled = pygame.transform.scale(self.logo, (logo_width, logo_height))
        logo_x = self.screen_manager.viewport_x + (self.screen_manager.viewport_width - logo_width) // 2
        logo_y = self.screen_manager.viewport_y + int(self.screen_manager.viewport_height * 0.2)
        screen.blit(logo_scaled, (logo_x, logo_y))

        # Desenha botões
        for button in self.buttons:
            button.render(screen)

        # Versão
        font_small = pygame.font.Font(None, 20)
        version_text = font_small.render("v"+self.game.current_version+" - Em desenvolvimento", True, (150, 150, 150))
        version_x = self.screen_manager.viewport_x + 10
        version_y = self.screen_manager.viewport_y + self.screen_manager.viewport_height - 25
        screen.blit(version_text, (version_x, version_y))

        if self.paused:
            self._render_pause_overlay(screen)

    def _draw_gradient_background(self, screen):
        """Desenha fundo com gradiente"""
        for i in range(self.screen_manager.window_height):
            color_value = int(20 + (i / self.screen_manager.window_height) * 30)
            color = (color_value, color_value, color_value + 20)
            pygame.draw.line(screen, color, (0, i), (self.screen_manager.window_width, i))

    def _render_pause_overlay(self, screen):
        """Overlay de pausa"""
        overlay = pygame.Surface((self.screen_manager.window_width,
                                 self.screen_manager.window_height))
        overlay.set_alpha(128)
        overlay.fill((0, 0, 0))
        screen.blit(overlay, (0, 0))

        font_large = pygame.font.Font(None, 74)
        pause_text = font_large.render("PAUSADO", True, (255, 255, 255))
        text_x = (self.screen_manager.window_width - pause_text.get_width()) // 2
        text_y = (self.screen_manager.window_height - pause_text.get_height()) // 2
        screen.blit(pause_text, (text_x, text_y))

    def start_game(self):
        """Inicia o jogo - verifica se tem save ou precisa escolher inicial"""

        # Verifica se existe um save
        save_loaded = self.game.player.load_game(1)

        if not save_loaded:
            # Sem save: mostra tela de seleção de inicial
            from src.scenes.starter_select_scene.starter_select_scene import StarterSelectScene

            self.game.starter_select_scene = StarterSelectScene(self.game)
            self.game.current_scene = self.game.starter_select_scene
        else:
            # Com save: vai direto para seleção de fases
            print("[MENU] Save encontrado - indo para seleção de fases")
            print(f"  - Time: {len(self.game.player.team)} Pokémon")
            print(f"  - Último capítulo acessado: {self.game.player.chapter_page_num}")

            # Carrega as configurações do save
            from src.config.progress import progress_manager
            progress_manager._load_settings_from_save()

            # A PhaseSelectScene agora vai ler o chapter_page_num automaticamente
            self.game.current_scene = PhaseSelectScene(self.game)

    def open_settings(self):
        """Abre configurações"""
        print("Abrindo configurações...")
        self.game.current_scene = SettingsScene(self.game)

    def open_editor(self):
        """Abre o editor de fases"""
        print("Abrindo editor de fases...")
        from src.scenes.editor.editor_scene import EditorScene
        self.game.current_scene = EditorScene(self.game)

    def open_mystery_gift(self):
        """Abre a tela de Mystery Gift"""
        print("[MENU] Abrindo Mystery Gift...")
        from src.scenes.mystery_gift_scene.mystery_gift_scene import MysteryGiftScene
        self.game.current_scene = MysteryGiftScene(self.game)

    def quit_game(self):
        """Sai do jogo"""
        print("Saindo do jogo...")
        self.game.running = False