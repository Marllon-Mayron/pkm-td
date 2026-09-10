# src/scenes/menu_scene.py

"""
Cena do menu principal - Layout com preview de imagens
"""
import pygame
import random
import os
import json
from pathlib import Path

from config.paths import SPRITES_PATH, RES_PATH
from src.scenes.base_scene import BaseScene
from src.scenes.phase_selector.phase_select_scene import PhaseSelectScene
from src.scenes.settings_scene.settings_scene import SettingsScene
from src.managers.sounds.sound_manager import sound_manager, SoundEffect
from src.ui.toast_renderer import toast_warning


class ImageSlideshow:
    """Gerenciador de slideshow de imagens para o menu"""

    def __init__(self):
        self.images = []
        self.current_index = 0
        self.timer = 0
        self.switch_interval = 3.0  # Troca a cada 3 segundos
        self.image_surfaces = []
        self._loaded = False

    def load_images(self):
        """Carrega as imagens do diretório Res/screenshots"""
        screenshots_path = SPRITES_PATH / "screenshots"

        if not screenshots_path.exists():
            print(f"[SLIDESHOW] Diretório não encontrado: {screenshots_path}")
            return

        # Busca todas as imagens Capturar1.png a Capturar5.png
        image_files = []
        for i in range(1, 8):
            img_path = screenshots_path / f"Capturar{i}.png"
            if img_path.exists():
                image_files.append(img_path)
            else:
                # Tenta com extensão .jpg também
                img_path_jpg = screenshots_path / f"Capturar{i}.jpg"
                if img_path_jpg.exists():
                    image_files.append(img_path_jpg)

        if not image_files:
            print(f"[SLIDESHOW] Nenhuma imagem encontrada em {screenshots_path}")
            # Cria uma imagem de fallback
            self._create_fallback_images()
            return

        # Carrega as imagens
        for img_path in image_files:
            try:
                img = pygame.image.load(str(img_path))
                if img:
                    self.image_surfaces.append(img)
                    print(f"[SLIDESHOW] Carregada: {img_path.name}")
            except Exception as e:
                print(f"[SLIDESHOW] Erro ao carregar {img_path.name}: {e}")

        if not self.image_surfaces:
            self._create_fallback_images()
        else:
            self._loaded = True

    def _create_fallback_images(self):
        """Cria imagens de fallback coloridas"""
        print("[SLIDESHOW] Criando imagens de fallback")
        colors = [
            (40, 30, 80), (30, 50, 70), (50, 30, 60), (30, 60, 50), (60, 40, 30)
        ]
        for i, color in enumerate(colors):
            surf = pygame.Surface((400, 300))
            surf.fill(color)

            # Texto "Screenshot {i+1}"
            font = pygame.font.Font(None, 36)
            text = font.render(f"Preview {i + 1}", True, (200, 200, 220))
            text_rect = text.get_rect(center=(200, 150))
            surf.blit(text, text_rect)

            # Borda
            pygame.draw.rect(surf, (100, 100, 140), surf.get_rect(), 2)

            self.image_surfaces.append(surf)
        self._loaded = True

    def update(self, dt):
        """Atualiza o timer do slideshow"""
        if not self._loaded or len(self.image_surfaces) <= 1:
            return

        self.timer += dt
        if self.timer >= self.switch_interval:
            self.timer = 0
            self.current_index = (self.current_index + 1) % len(self.image_surfaces)

    def get_current_image(self):
        """Retorna a imagem atual"""
        if not self._loaded or not self.image_surfaces:
            return None
        return self.image_surfaces[self.current_index]

    def next(self):
        """Vai para a próxima imagem"""
        if not self._loaded or len(self.image_surfaces) <= 1:
            return
        self.current_index = (self.current_index + 1) % len(self.image_surfaces)
        self.timer = 0

    def prev(self):
        """Vai para a imagem anterior"""
        if not self._loaded or len(self.image_surfaces) <= 1:
            return
        self.current_index = (self.current_index - 1) % len(self.image_surfaces)
        self.timer = 0

    def get_image_count(self):
        """Retorna o número de imagens carregadas"""
        return len(self.image_surfaces)


class Button:
    """Botão estilizado com responsividade e efeitos visuais"""

    def __init__(self, x, y, width, height, text, color, hover_color, callback, font=None, volume: float = None):
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

        # ===== VOLUME DO SOM DO BOTÃO =====
        # Se None, usa o volume global. Se for um valor, usa esse volume diretamente
        self.volume = volume

        # Texto pré-renderizado
        self.text_surface = None
        self.text_rect = None

        # Efeitos visuais
        self.glow_alpha = 0
        self.glow_direction = 1
        self.scale = 1.0
        self.target_scale = 1.0

        # Ícone (opcional)
        self.icon = None
        self.icon_rect = None

        # ===== ESTADO DE BLOQUEIO (ex: botão editor quando DEBUG_MODE=False) =====
        self.disabled = False
        self.disabled_tooltip = ""

    def update_absolute_position(self, viewport_width, viewport_height, viewport_x, viewport_y):
        """Atualiza posição absoluta baseada no tamanho do viewport"""
        abs_x = viewport_x + int(self.relative_x * viewport_width)
        abs_y = viewport_y + int(self.relative_y * viewport_height)
        abs_width = int(self.relative_width * viewport_width)
        abs_height = int(self.relative_height * viewport_height)

        self.rect = pygame.Rect(abs_x, abs_y, abs_width, abs_height)

        # Atualiza texto com tamanho responsivo
        font_size = max(18, int(viewport_height * 0.032))
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
                if not self.disabled:
                    sound_manager.play_effect(SoundEffect.CLICK, volume=self.volume)
                else:
                    # Som mais baixo/erro para botão bloqueado
                    sound_manager.play_effect(SoundEffect.CLICK, volume=(self.volume or 0.3) * 0.5)

            elif not self.is_hovered and was_hovered:
                self.target_scale = 1.0

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.is_hovered:
                sound_manager.play_effect(SoundEffect.CLICK, volume=self.volume)
                self.target_scale = 0.95
                # Se está bloqueado, ainda chama callback (o callback decide o que fazer)
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
        shadow_rect.y += 3
        pygame.draw.rect(screen, (10, 10, 20, 50), shadow_rect, border_radius=8)

        # ===== APARÊNCIA QUANDO BLOQUEADO =====
        if self.disabled:
            # Botão acinzentado (aspecto "desabilitado")
            base_color = (45, 45, 55)
            hover_color = (60, 60, 70)
            color = hover_color if self.is_hovered else base_color

            pygame.draw.rect(screen, color, scaled_rect, border_radius=8)
            border_color = (100, 90, 90) if self.is_hovered else (70, 70, 80)
            pygame.draw.rect(screen, border_color, scaled_rect, 2, border_radius=8)

            # Cadeado pequeno no canto superior direito
            lock_size = max(10, int(scaled_rect.height * 0.28))
            lock_x = scaled_rect.right - lock_size - 6
            lock_y = scaled_rect.y + 6
            # Corpo do cadeado
            body_rect = pygame.Rect(lock_x, lock_y + lock_size // 3,
                                    lock_size, int(lock_size * 0.7))
            pygame.draw.rect(screen, (180, 160, 90), body_rect, border_radius=2)
            # Arco do cadeado
            arc_rect = pygame.Rect(lock_x + lock_size // 4,
                                   lock_y,
                                   lock_size // 2,
                                   lock_size // 2)
            pygame.draw.arc(screen, (180, 160, 90), arc_rect,
                            3.14, 2 * 3.14, max(2, lock_size // 8))

            # Texto com cor mais apagada
            text_surface_scaled = pygame.transform.scale(
                self.text_surface,
                (int(self.text_surface.get_width() * self.scale),
                 int(self.text_surface.get_height() * self.scale))
            )
            # Aplica uma camada escura ao texto pra parecer "apagado"
            text_surface_scaled = text_surface_scaled.copy()
            dark_overlay = pygame.Surface(text_surface_scaled.get_size(), pygame.SRCALPHA)
            dark_overlay.fill((0, 0, 0, 90))
            text_surface_scaled.blit(dark_overlay, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)

            text_rect = text_surface_scaled.get_rect(center=scaled_rect.center)
            screen.blit(text_surface_scaled, text_rect)

            # Tooltip quando hover
            if self.is_hovered and self.disabled_tooltip:
                self._render_tooltip(screen, scaled_rect)
            return

        # ===== APARÊNCIA NORMAL =====
        # Cor do botão
        color = self.hover_color if self.is_hovered else self.color

        # Fundo com gradiente
        if self.is_hovered:
            # Efeito de glow
            glow_surface = pygame.Surface((scaled_rect.width, scaled_rect.height), pygame.SRCALPHA)
            glow_rect = glow_surface.get_rect()
            pygame.draw.rect(glow_surface, (*color[:3], self.glow_alpha), glow_rect, border_radius=8)
            screen.blit(glow_surface, scaled_rect)

            # Borda brilhante
            pygame.draw.rect(screen, (255, 215, 0), scaled_rect, 3, border_radius=8)
        else:
            pygame.draw.rect(screen, color, scaled_rect, border_radius=8)
            pygame.draw.rect(screen, (80, 70, 50), scaled_rect, 2, border_radius=8)

        # Efeito de brilho interno
        if self.is_hovered:
            inner_glow = pygame.Surface((scaled_rect.width - 8, scaled_rect.height - 8), pygame.SRCALPHA)
            pygame.draw.rect(inner_glow, (255, 255, 255, 25), inner_glow.get_rect(), border_radius=6)
            screen.blit(inner_glow, (scaled_rect.x + 4, scaled_rect.y + 4))

        # Desenha texto
        text_surface_scaled = pygame.transform.scale(
            self.text_surface,
            (int(self.text_surface.get_width() * self.scale),
             int(self.text_surface.get_height() * self.scale))
        )
        text_rect = text_surface_scaled.get_rect(center=scaled_rect.center)
        screen.blit(text_surface_scaled, text_rect)

    def _render_tooltip(self, screen, anchor_rect):
        """Renderiza um pequeno tooltip abaixo do botão."""
        font = pygame.font.Font(None, 18)
        text_surf = font.render(self.disabled_tooltip, True, (255, 230, 180))
        pad_x, pad_y = 10, 6
        tt_w = text_surf.get_width() + pad_x * 2
        tt_h = text_surf.get_height() + pad_y * 2

        tt_x = anchor_rect.centerx - tt_w // 2
        tt_y = anchor_rect.bottom + 6

        # Fundo
        bg = pygame.Surface((tt_w, tt_h), pygame.SRCALPHA)
        bg.fill((20, 20, 30, 230))
        screen.blit(bg, (tt_x, tt_y))
        pygame.draw.rect(screen, (200, 160, 60), (tt_x, tt_y, tt_w, tt_h), 1, border_radius=4)
        screen.blit(text_surf, (tt_x + pad_x, tt_y + pad_y))


class MenuScene(BaseScene):
    """Cena do menu principal com layout reformulado - botões à esquerda e preview à direita"""

    # =====================================================================
    # MODO DEBUG — mude para True para liberar ferramentas internas
    # (Editor de Fases). Em builds públicas, mantenha False.
    # =====================================================================
    DEBUG_MODE = False

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

        # ===== SLIDESHOW =====
        self.slideshow = ImageSlideshow()
        self.slideshow.load_images()

        # ===== LOGO =====
        self.logo_surface = None
        self.logo_rect = None
        self._logo_loaded_from_file = False
        self._create_logo()

        # ===== BOTÕES =====
        self.buttons = []
        self._create_buttons()

        # ===== PARTÍCULAS =====
        self.particles = []
        self._create_particles()

        # ===== INICIA MÚSICA =====
        self._start_menu_music()

        # ===== NAVEGAÇÃO DO SLIDESHOW =====
        self._nav_left_rect = None
        self._nav_right_rect = None
        self._nav_hover_left = False
        self._nav_hover_right = False

    # ======================================================================
    # INICIALIZAÇÃO
    # ======================================================================

    def _create_logo(self):
        """Cria o logo - carrega logo.png do diretório UI ou usa fallback desenhado"""
        # ===== TENTA CARREGAR logo.png DO DIRETÓRIO UI =====
        logo_paths = [
            SPRITES_PATH / "UI" / "logo.png",
            RES_PATH / "PokemonSprites" / "UI" / "logo.png",
            SPRITES_PATH / "UI" / "Logo.png",
            RES_PATH / "PokemonSprites" / "UI" / "Logo.png",
            SPRITES_PATH / "screenshots" / "logo.png",  # fallback extra
        ]

        for logo_path in logo_paths:
            if logo_path.exists():
                try:
                    loaded_logo = pygame.image.load(str(logo_path)).convert_alpha()
                    if loaded_logo and loaded_logo.get_width() > 0:
                        self.logo_surface = loaded_logo
                        self._logo_loaded_from_file = True
                        print(f"[MENU] Logo carregada: {logo_path}")
                        return
                except Exception as e:
                    print(f"[MENU] Erro ao carregar logo {logo_path}: {e}")

        # ===== FALLBACK: LOGO DESENHADA PROGRAMATICAMENTE =====
        print("[MENU] logo.png não encontrada - usando logo desenhada (fallback)")
        logo_width = 500
        logo_height = 150

        self.logo_surface = pygame.Surface((logo_width, logo_height), pygame.SRCALPHA)
        self._logo_loaded_from_file = False

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
        text_pokemon = font_large.render("POKEMON", True, (255, 255, 255))
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
        """Cria os botões com layout melhorado - posicionados à esquerda"""
        # Ajuste para ocupar a metade esquerda da tela
        left_margin = 0.05
        button_width = 0.35

        # Botão principal (mais espaçado)
        main_btn_y = 0.30

        # ===== VOLUME DOS BOTÕES (30% do volume global) =====
        BTN_VOLUME = 0.3

        # ===== BOTÃO EDITOR DE FASES (bloqueado se DEBUG_MODE=False) =====
        editor_btn = Button(
            left_margin, main_btn_y + 0.28, button_width, 0.07, "Editor de Fases",
            (40, 40, 60), (80, 80, 120), self.open_editor, None,
            volume=BTN_VOLUME
        )
        if not MenuScene.DEBUG_MODE:
            editor_btn.disabled = True
            editor_btn.disabled_tooltip = "Disponível apenas em modo debug"

        self.buttons = [
            # ===== BOTÃO PRINCIPAL (DESTAQUE) =====
            Button(left_margin, main_btn_y, button_width, 0.08, self.start_text,
                   (60, 60, 20), (120, 120, 30), self.start_game, None,
                   volume=BTN_VOLUME),

            # ===== BOTÕES SECUNDÁRIOS =====
            Button(left_margin, main_btn_y + 0.10, button_width, 0.07, "Multiplayer",
                   (40, 40, 60), (80, 80, 120), self.open_multiplayer, None,
                   volume=BTN_VOLUME),

            Button(left_margin, main_btn_y + 0.19, button_width, 0.07, "Configuracoes",
                   (40, 40, 60), (80, 80, 120), self.open_settings, None,
                   volume=BTN_VOLUME),

            # Editor (potencialmente bloqueado)
            editor_btn,

            # ===== BOTÕES DE AÇÕES RÁPIDAS (lado a lado abaixo do Editor) =====
            Button(left_margin, main_btn_y + 0.37, 0.17, 0.06, "Mystery Gift",
                   (40, 20, 40), (80, 40, 80), self.open_mystery_gift, None,
                   volume=BTN_VOLUME),

            Button(left_margin + 0.18, main_btn_y + 0.37, 0.17, 0.06, "RESETAR",
                   (60, 15, 15), (120, 25, 25), self.show_reset_confirmation, None,
                   volume=BTN_VOLUME),

            # ===== BOTÃO SAIR (mais abaixo) =====
            Button(left_margin, main_btn_y + 0.46, button_width, 0.07, "Sair",
                   (60, 20, 20), (120, 30, 30), self.quit_game, None,
                   volume=BTN_VOLUME),
        ]

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
        """Abre o editor de fases — bloqueado quando DEBUG_MODE=False."""
        if not MenuScene.DEBUG_MODE:
            toast_warning(
                "Editor de Fases indisponível (modo debug desativado).",
                duration=3.5,
            )
            print("[MENU] Editor bloqueado: DEBUG_MODE=False")
            return

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
            sound_manager.play_effect(SoundEffect.CLICK, volume=0.3)

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
            sound_manager.play_effect(SoundEffect.CLICK, volume=0.3)
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
                sound_manager.play_effect(SoundEffect.CLICK, volume=0.3)
            elif event.key == pygame.K_LEFT:
                self.slideshow.prev()
            elif event.key == pygame.K_RIGHT:
                self.slideshow.next()

        if self.reset_confirmation_active:
            self._handle_reset_confirmation_event(event)
            return

        # Eventos para os botões de navegação do slideshow
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._nav_left_rect and self._nav_left_rect.collidepoint(event.pos):
                self.slideshow.prev()
                sound_manager.play_effect(SoundEffect.CLICK, volume=0.3)
                return
            if self._nav_right_rect and self._nav_right_rect.collidepoint(event.pos):
                self.slideshow.next()
                sound_manager.play_effect(SoundEffect.CLICK, volume=0.3)
                return

        # Eventos dos botões
        for button in self.buttons:
            button.handle_event(event)

    def _handle_reset_confirmation_event(self, event):
        """Processa eventos da confirmação de reset"""
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mouse_pos = event.pos
            if self._confirm_yes_rect and self._confirm_yes_rect.collidepoint(mouse_pos):
                sound_manager.play_effect(SoundEffect.CLICK, volume=0.3)
                self._execute_reset()
                return
            if self._confirm_no_rect and self._confirm_no_rect.collidepoint(mouse_pos):
                sound_manager.play_effect(SoundEffect.CLICK, volume=0.3)
                self.reset_confirmation_active = False
                return

        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.reset_confirmation_active = False
            sound_manager.play_effect(SoundEffect.CLICK, volume=0.3)

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

        # Atualiza slideshow
        self.slideshow.update(dt)

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

        # ===== LOGO (centralizada com os botões) =====
        button_width = int(vw * 0.35)
        left_margin = int(vw * 0.05)

        # Calcula o tamanho da logo MANTENDO A PROPORÇÃO da imagem original
        logo_width = int(vw * 0.30)
        orig_w, orig_h = self.logo_surface.get_size()
        if orig_w <= 0:
            orig_w = 1
        logo_height = int(logo_width * (orig_h / orig_w))

        # Centraliza a logo na mesma área dos botões
        logo_x = vx + left_margin + (button_width - logo_width) // 2
        logo_y = vy + int(vh * 0.05)

        try:
            logo_scaled = pygame.transform.smoothscale(self.logo_surface, (logo_width, logo_height))
        except Exception:
            logo_scaled = pygame.transform.scale(self.logo_surface, (logo_width, logo_height))

        screen.blit(logo_scaled, (logo_x, logo_y))

        # ===== PAINEL DE PREVIEW (lado direito, paralelo à logo) =====
        self._render_preview_panel(screen, vx, vy, vw, vh)

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

    def _render_preview_panel(self, screen, vx, vy, vw, vh):
        """Renderiza o painel de preview com slideshow"""
        # Define a área do preview (lado direito, paralelo à logo)
        panel_x = vx + int(vw * 0.48)
        panel_y = vy + int(vh * 0.05)  # Mesmo y da logo
        panel_width = int(vw * 0.47)
        panel_height = int(vh * 0.85)  # Um pouco mais alto para compensar

        # Borda e fundo do painel
        panel_rect = pygame.Rect(panel_x, panel_y, panel_width, panel_height)

        # Fundo escuro com transparência
        panel_surface = pygame.Surface((panel_width, panel_height), pygame.SRCALPHA)
        panel_surface.fill((10, 10, 30, 200))
        screen.blit(panel_surface, panel_rect)

        # Borda
        pygame.draw.rect(screen, (60, 50, 80), panel_rect, 2, border_radius=12)
        pygame.draw.rect(screen, (100, 80, 130), panel_rect.inflate(-4, -4), 1, border_radius=10)

        # Área interna da imagem (com margem)
        margin = 15
        img_x = panel_x + margin
        img_y = panel_y + margin + 30  # Espaço para o título
        img_width = panel_width - margin * 2
        img_height = panel_height - margin * 2 - 60  # Espaço para título e indicadores

        # Título do painel
        title_font = pygame.font.Font(None, int(vh * 0.028))
        title_text = title_font.render("PREVIEW DO JOGO", True, (220, 210, 240))
        title_x = panel_x + (panel_width - title_text.get_width()) // 2
        title_y = panel_y + 15
        screen.blit(title_text, (title_x, title_y))

        # Obtém a imagem atual
        current_img = self.slideshow.get_current_image()

        if current_img:
            # Calcula o tamanho mantendo a proporção
            img_ratio = current_img.get_width() / current_img.get_height()
            target_ratio = img_width / img_height

            if img_ratio > target_ratio:
                # Imagem mais larga que o container
                display_width = img_width
                display_height = int(img_width / img_ratio)
            else:
                # Imagem mais alta que o container
                display_height = img_height
                display_width = int(img_height * img_ratio)

            # Centraliza a imagem
            display_x = img_x + (img_width - display_width) // 2
            display_y = img_y + (img_height - display_height) // 2

            # Redimensiona a imagem
            try:
                scaled_img = pygame.transform.smoothscale(current_img, (display_width, display_height))

                # Adiciona uma borda sutil ao redor da imagem
                img_rect = pygame.Rect(display_x - 2, display_y - 2, display_width + 4, display_height + 4)
                pygame.draw.rect(screen, (80, 70, 100), img_rect, border_radius=4)

                screen.blit(scaled_img, (display_x, display_y))
            except Exception as e:
                print(f"[MENU] Erro ao redimensionar imagem: {e}")
                # Fallback: texto
                fallback_font = pygame.font.Font(None, int(vh * 0.025))
                fallback_text = fallback_font.render("Imagem indisponivel", True, (150, 150, 170))
                text_x = img_x + (img_width - fallback_text.get_width()) // 2
                text_y = img_y + (img_height - fallback_text.get_height()) // 2
                screen.blit(fallback_text, (text_x, text_y))
        else:
            # Sem imagem
            fallback_font = pygame.font.Font(None, int(vh * 0.025))
            fallback_text = fallback_font.render("Nenhuma imagem disponivel", True, (150, 150, 170))
            text_x = img_x + (img_width - fallback_text.get_width()) // 2
            text_y = img_y + (img_height - fallback_text.get_height()) // 2
            screen.blit(fallback_text, (text_x, text_y))

        # ===== BOTÕES DE NAVEGAÇÃO =====
        nav_size = int(vh * 0.04)
        nav_y = panel_y + panel_height - nav_size - 10
        nav_spacing = 20

        # Botão esquerdo
        left_x = panel_x + (panel_width - nav_size * 2 - nav_spacing) // 2
        self._nav_left_rect = pygame.Rect(left_x, nav_y, nav_size, nav_size)

        # Botão direito
        right_x = left_x + nav_size + nav_spacing
        self._nav_right_rect = pygame.Rect(right_x, nav_y, nav_size, nav_size)

        mouse_pos = pygame.mouse.get_pos()

        # Verifica hover
        self._nav_hover_left = self._nav_left_rect.collidepoint(mouse_pos) if self._nav_left_rect else False
        self._nav_hover_right = self._nav_right_rect.collidepoint(mouse_pos) if self._nav_right_rect else False

        # Desenha botões de navegação
        for rect, hover, symbol in [
            (self._nav_left_rect, self._nav_hover_left, "<"),
            (self._nav_right_rect, self._nav_hover_right, ">")
        ]:
            if rect:
                # Fundo do botão
                color = (80, 70, 100) if hover else (50, 40, 60)
                pygame.draw.rect(screen, color, rect, border_radius=8)
                pygame.draw.rect(screen, (120, 100, 150) if hover else (70, 60, 80), rect, 1, border_radius=8)

                if hover:
                    pygame.draw.rect(screen, (150, 130, 180, 30), rect.inflate(-4, -4), border_radius=6)

                # Símbolo
                nav_font = pygame.font.Font(None, int(nav_size * 0.7))
                nav_text = nav_font.render(symbol, True, (220, 210, 240))
                text_rect = nav_text.get_rect(center=rect.center)
                screen.blit(nav_text, text_rect)

        # ===== INDICADOR DE PÁGINA =====
        count = self.slideshow.get_image_count()
        if count > 1:
            indicator_font = pygame.font.Font(None, int(vh * 0.018))
            indicator_text = indicator_font.render(
                f"{self.slideshow.current_index + 1} / {count}",
                True, (180, 170, 200)
            )
            indicator_x = panel_x + (panel_width - indicator_text.get_width()) // 2
            indicator_y = nav_y + nav_size + 15
            screen.blit(indicator_text, (indicator_x, indicator_y))

            # Bolinhas indicadoras
            dot_size = 6
            dot_spacing = 12
            dots_width = count * dot_spacing - (dot_spacing - dot_size)
            dots_x = panel_x + (panel_width - dots_width) // 2
            dots_y = indicator_y + indicator_text.get_height() + 10

            for i in range(count):
                x = dots_x + i * dot_spacing
                is_active = (i == self.slideshow.current_index)
                color = (200, 180, 220) if is_active else (60, 50, 70)
                pygame.draw.circle(screen, color, (x, dots_y), dot_size // 2)
                if is_active:
                    pygame.draw.circle(screen, (255, 215, 0, 100), (x, dots_y), dot_size // 2 + 2, 1)

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
        title_text = title_font.render("RESETAR PROGRESSO", True, (255, 80, 80))
        title_x = container_x + (container_width - title_text.get_width()) // 2
        title_y = container_y + int(container_height * 0.08)
        screen.blit(title_text, (title_x, title_y))

        # Mensagem
        warn_font = pygame.font.Font(None, int(vh * 0.025))
        lines = [
            "Voce esta prestes a APAGAR TODO o seu progresso!",
            "",
            "Isso ira:",
            "* Deletar todos os seus Pokemon",
            "* Resetar seu dinheiro e itens",
            "* Apagar todas as conquistas",
            "* Deletar todos os saves",
            "",
            "Esta acao e IRREVERSIVEL!",
        ]

        line_y = title_y + title_text.get_height() + int(container_height * 0.03)
        line_spacing = int(vh * 0.028)

        for line in lines:
            if line:
                if "IRREVERSIVEL" in line:
                    color = (255, 80, 80)
                    font = pygame.font.Font(None, int(vh * 0.028))
                elif "APAGAR TODO" in line:
                    color = (255, 200, 100)
                    font = warn_font
                elif line.startswith("*"):
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
        no_text = no_font.render("NAO", True, (255, 255, 255))
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
        pause_text = font_large.render("PAUSADO", True, (255, 255, 255))
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