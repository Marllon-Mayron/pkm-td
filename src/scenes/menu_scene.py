# src/scenes/menu_scene.py

"""
Cena do menu principal - Layout reformulado
"""
import pygame
import random
import os
import json

from src.scenes.base_scene import BaseScene
from src.scenes.phase_selector.phase_select_scene import PhaseSelectScene
from src.scenes.settings_scene.settings_scene import SettingsScene
from src.managers.sounds.sound_manager import sound_manager, SoundEffect


class Button:
    """Botão estilizado com responsividade e efeitos visuais"""

    def __init__(self, x, y, width, height, text, color, hover_color, callback, font=None):
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
        self.font = font
        self.is_hovered = False
        self._was_hovered = False

        # Texto pré-renderizado
        self.text_surface = None
        self.text_rect = None

        # Efeitos visuais
        self.glow_alpha = 0
        self.glow_direction = 1
        self.scale = 1.0
        self.target_scale = 1.0

    def update_absolute_position(self, viewport_width, viewport_height, viewport_x, viewport_y):
        """Atualiza posição absoluta baseada no tamanho do viewport"""
        abs_x = viewport_x + int(self.relative_x * viewport_width)
        abs_y = viewport_y + int(self.relative_y * viewport_height)
        abs_width = int(self.relative_width * viewport_width)
        abs_height = int(self.relative_height * viewport_height)

        self.rect = pygame.Rect(abs_x, abs_y, abs_width, abs_height)

        # Atualiza texto com tamanho responsivo
        font_size = max(20, int(viewport_height * 0.035))
        if self.font is None:
            self.font = pygame.font.Font(None, font_size)
        self.text_surface = self.font.render(self.text, True, (255, 255, 255))
        self.text_rect = self.text_surface.get_rect(center=self.rect.center)

    def update(self, dt):
        """Atualiza animações do botão"""
        # Animação de glow
        self.glow_alpha += self.glow_direction * 2
        if self.glow_alpha >= 150:
            self.glow_alpha = 150
            self.glow_direction = -1
        elif self.glow_alpha <= 0:
            self.glow_alpha = 0
            self.glow_direction = 1

        # Suaviza a escala
        self.scale += (self.target_scale - self.scale) * 0.1

    def handle_event(self, event):
        """Processa eventos do botão"""
        if event.type == pygame.MOUSEMOTION:
            was_hovered = self.is_hovered
            self.is_hovered = self.rect.collidepoint(event.pos)

            if self.is_hovered and not was_hovered:
                self.target_scale = 1.05
                sound_manager.play_effect(SoundEffect.CLICK)  # Volume controlado pelo SoundManager

            elif not self.is_hovered and was_hovered:
                self.target_scale = 1.0

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.is_hovered:
                sound_manager.play_effect(SoundEffect.CLICK)
                self.target_scale = 0.95
                if self.callback:
                    self.callback()

        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self.is_hovered:
                self.target_scale = 1.05

    def render(self, screen):
        """Renderiza o botão com efeitos visuais"""
        if not self.text_surface:
            return

        # Calcula o rect com escala
        scaled_rect = self.rect.copy()
        if self.scale != 1.0:
            width_offset = (self.rect.width * (self.scale - 1)) // 2
            height_offset = (self.rect.height * (self.scale - 1)) // 2
            scaled_rect = self.rect.inflate(width_offset * 2, height_offset * 2)
            scaled_rect.center = self.rect.center

        # Sombra do botão
        shadow_rect = scaled_rect.copy()
        shadow_rect.y += 4
        pygame.draw.rect(screen, (10, 10, 20, 50), shadow_rect, border_radius=10)

        # Cor do botão
        color = self.hover_color if self.is_hovered else self.color

        # Fundo com gradiente
        if self.is_hovered:
            # Efeito de glow
            glow_surface = pygame.Surface((scaled_rect.width, scaled_rect.height), pygame.SRCALPHA)
            glow_rect = glow_surface.get_rect()
            pygame.draw.rect(glow_surface, (*color[:3], self.glow_alpha), glow_rect, border_radius=10)
            screen.blit(glow_surface, scaled_rect)

            # Borda brilhante
            pygame.draw.rect(screen, (255, 215, 0), scaled_rect, 3, border_radius=10)
        else:
            pygame.draw.rect(screen, color, scaled_rect, border_radius=10)
            pygame.draw.rect(screen, (80, 70, 50), scaled_rect, 2, border_radius=10)

        # Efeito de brilho interno
        if self.is_hovered:
            inner_glow = pygame.Surface((scaled_rect.width - 10, scaled_rect.height - 10), pygame.SRCALPHA)
            pygame.draw.rect(inner_glow, (255, 255, 255, 30), inner_glow.get_rect(), border_radius=8)
            screen.blit(inner_glow, (scaled_rect.x + 5, scaled_rect.y + 5))

        # Desenha texto
        text_surface_scaled = pygame.transform.scale(
            self.text_surface,
            (int(self.text_surface.get_width() * self.scale),
             int(self.text_surface.get_height() * self.scale))
        )
        text_rect = text_surface_scaled.get_rect(center=scaled_rect.center)
        screen.blit(text_surface_scaled, text_rect)


class MenuScene(BaseScene):
    """Cena do menu principal com layout reformulado"""

    def __init__(self, game):
        super().__init__(game)

        # ===== DADOS DO JOGADOR =====
        has_starter = getattr(self.game.player, 'has_chosen_starter', False)
        self.start_text = "Continuar Jogo" if has_starter else "Iniciar Jogo"

        # ===== ESTADO =====
        self.reset_confirmation_active = False
        self.reset_confirmation_timer = 0
        self._confirm_yes_rect = None
        self._confirm_no_rect = None
        self._music_started = False
        self._animation_timer = 0

        # ===== LOGO =====
        self.logo_surface = None
        self.logo_rect = None
        self._create_logo()

        # ===== BOTÕES =====
        self.buttons = []
        self._create_buttons()

        # ===== PARTÍCULAS =====
        self.particles = []
        self._create_particles()

        # ===== INICIA MÚSICA =====
        self._start_menu_music()

    # ======================================================================
    # INICIALIZAÇÃO
    # ======================================================================

    def _create_logo(self):
        """Cria um logo mais elaborado"""
        # Tamanho base
        logo_width = 500
        logo_height = 150

        self.logo_surface = pygame.Surface((logo_width, logo_height), pygame.SRCALPHA)

        # Fundo do logo com gradiente
        for i in range(logo_height):
            alpha = int(180 - (i / logo_height) * 60)
            color = (255, 215, 0, alpha)
            pygame.draw.line(self.logo_surface, color, (0, i), (logo_width, i))

        # Borda dourada
        pygame.draw.rect(self.logo_surface, (200, 170, 50), (0, 0, logo_width, logo_height), 4, border_radius=20)
        pygame.draw.rect(self.logo_surface, (255, 215, 0), (4, 4, logo_width - 8, logo_height - 8), 2, border_radius=18)

        # Fundo interno com transparência
        inner_rect = pygame.Rect(10, 10, logo_width - 20, logo_height - 20)
        pygame.draw.rect(self.logo_surface, (30, 20, 50, 180), inner_rect, border_radius=15)

        # Título "POKEMON"
        font_large = pygame.font.Font(None, 60)
        text_pokemon = font_large.render("POKÉMON", True, (255, 255, 255))
        text_rect = text_pokemon.get_rect(center=(logo_width // 2, 55))
        self.logo_surface.blit(text_pokemon, text_rect)

        # Subtítulo "TOWER DEFENSE"
        font_small = pygame.font.Font(None, 36)
        text_td = font_small.render("TOWER DEFENSE", True, (200, 200, 220))
        text_rect2 = text_td.get_rect(center=(logo_width // 2, 105))
        self.logo_surface.blit(text_td, text_rect2)

        # Linha decorativa
        pygame.draw.line(self.logo_surface, (255, 215, 0),
                         (logo_width // 4, 80), (logo_width * 3 // 4, 80), 2)

    def _create_buttons(self):
        """Cria os botões com layout melhorado"""
        self.buttons = [
            # ===== BOTÃO PRINCIPAL (DESTAQUE) =====
            Button(0.25, 0.42, 0.50, 0.08, self.start_text,
                   (60, 60, 20), (120, 120, 30), self.start_game, None),

            # ===== BOTÕES SECUNDÁRIOS =====
            Button(0.25, 0.52, 0.50, 0.07, "Multiplayer",
                   (40, 40, 60), (80, 80, 120), self.open_multiplayer, None),

            Button(0.25, 0.61, 0.50, 0.07, "Configurações",
                   (40, 40, 60), (80, 80, 120), self.open_settings, None),

            Button(0.25, 0.70, 0.50, 0.07, "Editor de Fases",
                   (40, 40, 60), (80, 80, 120), self.open_editor, None),

            Button(0.25, 0.79, 0.50, 0.07, "Sair",
                   (60, 20, 20), (120, 30, 30), self.quit_game, None),
        ]

        # ===== BOTÕES DOS CANTOS (menores) =====
        # Mystery Gift (canto inferior esquerdo)
        mg_button = Button(0.02, 0.88, 0.15, 0.05, "Mystery Gift",
                           (40, 20, 40), (80, 40, 80), self.open_mystery_gift, None)
        self.buttons.append(mg_button)

        # Reset (canto inferior direito)
        reset_button = Button(0.83, 0.88, 0.15, 0.05, "RESETAR",
                              (60, 15, 15), (120, 25, 25), self.show_reset_confirmation, None)
        self.buttons.append(reset_button)

    def _create_particles(self):
        """Cria partículas decorativas mais bonitas"""
        for _ in range(30):
            self.particles.append({
                'x': random.uniform(0, 1),
                'y': random.uniform(0, 1),
                'speed': random.uniform(0.3, 0.8),
                'angle': random.uniform(0, 2 * 3.14159),
                'color': (
                    random.randint(180, 255),
                    random.randint(180, 255),
                    random.randint(100, 200)
                ),
                'size': random.randint(2, 5),
                'alpha': random.randint(50, 150),
                'phase': random.uniform(0, 6.28)
            })

    def _start_menu_music(self):
        """Inicia a música do menu"""
        if not self._music_started:
            success = sound_manager.play_menu_music("Title_Theme", loop=True)
            if success:
                self._music_started = True
                print("[MENU] Música do menu iniciada: Title_Theme")
            else:
                success = sound_manager.play_menu_music("Come_Along", loop=True)
                if success:
                    self._music_started = True
                    print("[MENU] Música do menu iniciada: Come_Along (fallback)")

    # ======================================================================
    # MÉTODOS DE NAVEGAÇÃO
    # ======================================================================

    def open_multiplayer(self):
        from src.scenes.multiplayer_menu_scene.multiplayer_menu_scene import MultiplayerMenuScene
        self.game.current_scene = MultiplayerMenuScene(self.game)

    def open_settings(self):
        sound_manager.stop_music(fade_ms=300)
        self.game.current_scene = SettingsScene(self.game)

    def open_editor(self):
        from src.scenes.editor.editor_scene import EditorScene
        self.game.current_scene = EditorScene(self.game)

    def open_mystery_gift(self):
        from src.scenes.mystery_gift_scene.mystery_gift_scene import MysteryGiftScene
        self.game.current_scene = MysteryGiftScene(self.game)

    def quit_game(self):
        sound_manager.stop_music(fade_ms=300)
        self.game.running = False

    def start_game(self):
        """Inicia o jogo - verifica se já escolheu o inicial"""
        sound_manager.stop_music(fade_ms=300)

        has_chosen_starter = getattr(self.game.player, 'has_chosen_starter', False)

        if has_chosen_starter:
            from src.config.progress import progress_manager
            progress_manager._load_settings_from_save()
            self.game.current_scene = PhaseSelectScene(self.game)
        else:
            from src.scenes.starter_select_scene.starter_select_scene import StarterSelectScene
            self.game.starter_select_scene = StarterSelectScene(self.game)
            self.game.current_scene = self.game.starter_select_scene

    # ======================================================================
    # CONFIRMAÇÃO DE RESET
    # ======================================================================

    def show_reset_confirmation(self):
        if not self.reset_confirmation_active:
            self.reset_confirmation_active = True
            self.reset_confirmation_timer = 0
            sound_manager.play_effect(SoundEffect.CLICK)

    def _execute_reset(self):
        """Executa o reset do progresso"""
        print("[MENU] === INICIANDO RESET DE PROGRESSO ===")

        try:
            # Reseta jogador
            self.game.player.team.clear()
            self.game.player.pc_box.clear()
            self.game.player.money = 100
            self.game.player.score = 0
            self.game.player.seen_pokemon.clear()
            self.game.player.caught_pokemon.clear()
            self.game.player.achievements = {"unlocked": [], "counters": {}, "unlocked_data": {}}
            self.game.player.desfossilizadores.clear()
            if hasattr(self.game.player, '_add_initial_desfossilizador'):
                self.game.player._add_initial_desfossilizador()
            self.game.player.has_chosen_starter = False
            self.game.player.total_playtime = 0.0
            self.game.player.redeemed_codes = {}
            self.game.player.mystery_gift_history = []
            self.game.player.x = 100
            self.game.player.y = 100
            self.game.player.bag.items = {}
            if hasattr(self.game.player.bag, '_update_filtered_items'):
                self.game.player.bag._update_filtered_items()

            # Deleta saves
            saves_dir = "saves"
            if os.path.exists(saves_dir):
                for i in range(1, 4):
                    save_file = os.path.join(saves_dir, f"save_{i}.json")
                    if os.path.exists(save_file):
                        try:
                            os.remove(save_file)
                            print(f"[MENU] Save {i} deletado")
                        except Exception as e:
                            print(f"[MENU] Erro ao deletar save {i}: {e}")

            # Reseta SaveManager
            from src.managers.save_manager import save_manager
            save_manager.current_save_file = None
            save_manager.save_data = save_manager._get_default_save_data()

            # Cria novo save
            from src.config.progress import progress_manager
            game_state = {
                "current_chapter": 1,
                "current_phase": 1,
                "unlocked_chapters": [1],
                "unlocked_phases": ["1-1"],
                "completed_phases": [],
                "stars": {}
            }

            success = save_manager.save_game(self.game.player, game_state, save_name="Save 1", slot=1)
            if success:
                progress_manager._load_settings_from_save()

            self.reset_confirmation_active = False
            self._refresh_buttons()
            sound_manager.play_effect(SoundEffect.CLICK)
            print("[MENU] === RESET DE PROGRESSO CONCLUÍDO ===")

        except Exception as e:
            print(f"[MENU] ERRO durante o reset: {e}")
            import traceback
            traceback.print_exc()
            self.reset_confirmation_active = False

    def _refresh_buttons(self):
        """Atualiza o texto do botão Iniciar/Continuar"""
        has_starter = getattr(self.game.player, 'has_chosen_starter', False)
        self.start_text = "Continuar Jogo" if has_starter else "Iniciar Jogo"
        if self.buttons:
            self.buttons[0].text = self.start_text
            self.buttons[0].text_surface = None

    # ======================================================================
    # EVENTOS
    # ======================================================================

    def handle_event(self, event):
        """Processa eventos"""
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_p:
                self.toggle_pause()
            elif event.key == pygame.K_RETURN:
                self.start_game()
            elif event.key == pygame.K_ESCAPE and self.reset_confirmation_active:
                self.reset_confirmation_active = False
                sound_manager.play_effect(SoundEffect.CLICK)

        if self.reset_confirmation_active:
            self._handle_reset_confirmation_event(event)
            return

        for button in self.buttons:
            button.handle_event(event)

    def _handle_reset_confirmation_event(self, event):
        """Processa eventos da confirmação de reset"""
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mouse_pos = event.pos
            if self._confirm_yes_rect and self._confirm_yes_rect.collidepoint(mouse_pos):
                sound_manager.play_effect(SoundEffect.CLICK)
                self._execute_reset()
                return
            if self._confirm_no_rect and self._confirm_no_rect.collidepoint(mouse_pos):
                sound_manager.play_effect(SoundEffect.CLICK)
                self.reset_confirmation_active = False
                return

        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.reset_confirmation_active = False
            sound_manager.play_effect(SoundEffect.CLICK)

    # ======================================================================
    # UPDATE
    # ======================================================================

    def fixed_update(self, dt):
        """Update para animações"""
        if self.paused:
            return

        self._animation_timer += dt

        # Atualiza partículas
        for particle in self.particles:
            particle['x'] += (particle['speed'] * dt * 0.1) * (particle['angle'] == 0)
            particle['y'] += (particle['speed'] * dt * 0.05)
            particle['phase'] += dt * 0.5

            if particle['x'] > 1:
                particle['x'] = 0
            if particle['y'] > 1:
                particle['y'] = 0

        # Atualiza botões
        for button in self.buttons:
            button.update(dt)

        # Atualiza timer da confirmação
        if self.reset_confirmation_active:
            self.reset_confirmation_timer += dt

    # ======================================================================
    # RENDERIZAÇÃO
    # ======================================================================

    def render(self, screen):
        """Renderiza o menu"""
        self._draw_gradient_background(screen)

        vx = self.screen_manager.viewport_x
        vy = self.screen_manager.viewport_y
        vw = self.screen_manager.viewport_width
        vh = self.screen_manager.viewport_height

        # ===== ATUALIZA POSIÇÕES DOS BOTÕES =====
        for button in self.buttons:
            button.update_absolute_position(vw, vh, vx, vy)

        # ===== PARTÍCULAS =====
        for particle in self.particles:
            x = vx + int(particle['x'] * vw)
            y = vy + int(particle['y'] * vh)
            alpha = int(particle['alpha'] * (0.5 + 0.5 * (particle['phase'] % 1)))
            color = (*particle['color'], alpha)

            # Brilho das partículas
            glow_size = particle['size'] + 4
            for i in range(glow_size, particle['size'], -2):
                alpha_glow = int(alpha * (i / glow_size))
                pygame.draw.circle(screen, (*particle['color'], alpha_glow), (x, y), i)

            pygame.draw.circle(screen, color, (x, y), particle['size'])

        # ===== LOGO =====
        logo_width = int(vw * 0.35)
        logo_height = int(logo_width * (150 / 500))  # Mantém proporção
        logo_scaled = pygame.transform.scale(self.logo_surface, (logo_width, logo_height))

        logo_x = vx + (vw - logo_width) // 2
        logo_y = vy + int(vh * 0.08)

        # Sombra do logo
        shadow_surface = pygame.Surface((logo_width + 10, logo_height + 10), pygame.SRCALPHA)
        shadow_surface.fill((0, 0, 0, 30))
        screen.blit(shadow_surface, (logo_x - 5, logo_y + 5))

        screen.blit(logo_scaled, (logo_x, logo_y))

        # ===== BOTÕES =====
        for button in self.buttons:
            button.render(screen)

        # ===== VERSÃO =====
        font_small = pygame.font.Font(None, 16)
        version_text = font_small.render(f"v{self.game.current_version} - Em desenvolvimento", True, (100, 100, 120))
        version_x = vx + 15
        version_y = vy + vh - 20
        screen.blit(version_text, (version_x, version_y))

        # ===== CONFIRMAÇÃO DE RESET =====
        if self.reset_confirmation_active:
            self._render_reset_confirmation(screen)

        if self.paused:
            self._render_pause_overlay(screen)

    def _draw_gradient_background(self, screen):
        """Desenha fundo com gradiente e estrelas"""
        width = self.screen_manager.window_width
        height = self.screen_manager.window_height

        # Gradiente principal
        for i in range(height):
            t = i / height
            r = int(10 + t * 20)
            g = int(12 + t * 25)
            b = int(25 + t * 35)
            pygame.draw.line(screen, (r, g, b), (0, i), (width, i))

        # Estrelas (piscando)
        star_positions = [
            (0.05, 0.05), (0.15, 0.12), (0.25, 0.08), (0.35, 0.15),
            (0.45, 0.03), (0.55, 0.18), (0.65, 0.06), (0.75, 0.14),
            (0.85, 0.09), (0.95, 0.13), (0.08, 0.25), (0.18, 0.30),
            (0.88, 0.22), (0.92, 0.35), (0.02, 0.40), (0.98, 0.45),
        ]

        vx = self.screen_manager.viewport_x
        vy = self.screen_manager.viewport_y
        vw = self.screen_manager.viewport_width
        vh = self.screen_manager.viewport_height

        for i, (rx, ry) in enumerate(star_positions):
            x = vx + int(rx * vw)
            y = vy + int(ry * vh)
            alpha = int(80 + 80 * (0.5 + 0.5 * (self._animation_timer * 0.5 + i * 1.2) % 1))
            size = 1 + int(((i * 7) % 3))

            color = (200 + int(55 * (self._animation_timer * 0.3 + i) % 1),
                     200 + int(55 * (self._animation_timer * 0.4 + i + 1) % 1),
                     255)

            pygame.draw.circle(screen, color, (x, y), size)

    def _render_reset_confirmation(self, screen):
        """Renderiza o diálogo de confirmação de reset"""
        vx = self.screen_manager.viewport_x
        vy = self.screen_manager.viewport_y
        vw = self.screen_manager.viewport_width
        vh = self.screen_manager.viewport_height

        # Overlay escuro com animação
        overlay = pygame.Surface((self.screen_manager.window_width, self.screen_manager.window_height))
        alpha = min(180, int(180 * (self.reset_confirmation_timer / 0.3)))
        overlay.set_alpha(alpha)
        overlay.fill((0, 0, 0))
        screen.blit(overlay, (0, 0))

        # Container
        container_width = int(vw * 0.45)
        container_height = int(vh * 0.45)
        container_x = vx + (vw - container_width) // 2
        container_y = vy + (vh - container_height) // 2

        container_rect = pygame.Rect(container_x, container_y, container_width, container_height)

        # Fundo com gradiente
        for i in range(container_height):
            t = i / container_height
            r = int(30 - t * 10)
            g = int(20 - t * 5)
            b = int(20 - t * 5)
            pygame.draw.line(screen, (r, g, b),
                             (container_x, container_y + i),
                             (container_x + container_width, container_y + i))

        # Bordas
        pygame.draw.rect(screen, (200, 40, 40), container_rect, 3, border_radius=15)
        pygame.draw.rect(screen, (255, 60, 60), container_rect.inflate(-6, -6), 1, border_radius=12)

        # Título
        title_font = pygame.font.Font(None, int(vh * 0.05))
        title_text = title_font.render("⚠ RESETAR PROGRESSO", True, (255, 80, 80))
        title_x = container_x + (container_width - title_text.get_width()) // 2
        title_y = container_y + int(container_height * 0.08)
        screen.blit(title_text, (title_x, title_y))

        # Mensagem
        warn_font = pygame.font.Font(None, int(vh * 0.025))
        lines = [
            "Você está prestes a APAGAR TODO o seu progresso!",
            "",
            "Isso irá:",
            "• Deletar todos os seus Pokémon",
            "• Resetar seu dinheiro e itens",
            "• Apagar todas as conquistas",
            "• Deletar todos os saves",
            "",
            "Esta ação é IRREVERSÍVEL!",
        ]

        line_y = title_y + title_text.get_height() + int(container_height * 0.03)
        line_spacing = int(vh * 0.028)

        for line in lines:
            if line:
                if "IRREVERSÍVEL" in line:
                    color = (255, 80, 80)
                    font = pygame.font.Font(None, int(vh * 0.028))
                elif "APAGAR TODO" in line:
                    color = (255, 200, 100)
                    font = warn_font
                elif line.startswith("•"):
                    color = (200, 200, 200)
                    font = warn_font
                else:
                    color = (180, 180, 200)
                    font = warn_font

                text_surface = font.render(line, True, color)
                text_x = container_x + int(container_width * 0.08)
                screen.blit(text_surface, (text_x, line_y))
            line_y += line_spacing

        # Botões
        button_width = int(vw * 0.10)
        button_height = int(vh * 0.055)
        spacing = 30
        total_width = button_width * 2 + spacing
        start_x = container_x + (container_width - total_width) // 2
        button_y = container_y + container_height - button_height - int(container_height * 0.08)

        mouse_pos = pygame.mouse.get_pos()

        # Botão SIM
        yes_rect = pygame.Rect(start_x, button_y, button_width, button_height)
        yes_hover = yes_rect.collidepoint(mouse_pos)
        yes_color = (180, 40, 40) if yes_hover else (140, 30, 30)
        pygame.draw.rect(screen, yes_color, yes_rect, border_radius=10)
        pygame.draw.rect(screen, (255, 80, 80) if yes_hover else (200, 60, 60), yes_rect, 2, border_radius=10)
        if yes_hover:
            pygame.draw.rect(screen, (255, 100, 100, 30), yes_rect.inflate(-4, -4), border_radius=8)

        yes_font = pygame.font.Font(None, int(vh * 0.03))
        yes_text = yes_font.render("SIM", True, (255, 255, 255))
        yes_text_rect = yes_text.get_rect(center=yes_rect.center)
        screen.blit(yes_text, yes_text_rect)

        # Botão NÃO
        no_rect = pygame.Rect(start_x + button_width + spacing, button_y, button_width, button_height)
        no_hover = no_rect.collidepoint(mouse_pos)
        no_color = (80, 80, 80) if no_hover else (60, 60, 60)
        pygame.draw.rect(screen, no_color, no_rect, border_radius=10)
        pygame.draw.rect(screen, (120, 120, 120) if no_hover else (100, 100, 100), no_rect, 2, border_radius=10)

        no_font = pygame.font.Font(None, int(vh * 0.03))
        no_text = no_font.render("NÃO", True, (255, 255, 255))
        no_text_rect = no_text.get_rect(center=no_rect.center)
        screen.blit(no_text, no_text_rect)

        self._confirm_yes_rect = yes_rect
        self._confirm_no_rect = no_rect

    def _render_pause_overlay(self, screen):
        """Overlay de pausa"""
        overlay = pygame.Surface((self.screen_manager.window_width, self.screen_manager.window_height))
        overlay.set_alpha(128)
        overlay.fill((0, 0, 0))
        screen.blit(overlay, (0, 0))

        font_large = pygame.font.Font(None, 74)
        pause_text = font_large.render("⏸ PAUSADO", True, (255, 255, 255))
        text_rect = pause_text.get_rect(center=(
            self.screen_manager.window_width // 2,
            self.screen_manager.window_height // 2
        ))
        screen.blit(pause_text, text_rect)

    # ======================================================================
    # CICLO DE VIDA
    # ======================================================================

    def on_enter(self):
        """Chamado quando a cena é ativada"""
        if not self._music_started or not pygame.mixer.music.get_busy():
            self._start_menu_music()

    def on_exit(self):
        """Chamado quando a cena é desativada"""
        sound_manager.stop_music(fade_ms=300)
        self._music_started = False