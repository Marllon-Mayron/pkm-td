# src/scenes/menu_scene.py

"""
Cena do menu principal - Layout com preview de imagens
Agora com abas NEWS / PREVIEW + seletor de versão + título por imagem + link de changelog.
"""
import pygame
import random
import os
import json
import re
import webbrowser
from pathlib import Path

from config.paths import SPRITES_PATH, RES_PATH
from config.news_config import get_devlog_url, get_news_title, natural_sort_key
from src.scenes.base_scene import BaseScene
from src.scenes.phase_selector.phase_select_scene import PhaseSelectScene
from src.scenes.settings_scene.settings_scene import SettingsScene
from src.managers.sounds.sound_manager import sound_manager, SoundEffect
from src.ui.toast_renderer import toast_warning


# =========================================================================
# SLIDESHOW GENÉRICO (agora guarda o nome de cada imagem)
# =========================================================================
class ImageSlideshow:
    """Gerenciador de slideshow de imagens (preview ou news)."""

    def __init__(self, switch_interval: float = 3.0):
        self.images = []
        self.current_index = 0
        self.timer = 0
        self.switch_interval = switch_interval
        self.image_surfaces = []
        self.image_names = []
        self._loaded = False
        self.folder_path = None

    # ------------------------------------------------------------------
    def load_from_folder(self, folder_path):
        """Carrega TODAS as imagens de uma pasta (ordenação natural)."""
        self.image_surfaces = []
        self.image_names = []
        self.current_index = 0
        self.timer = 0
        self._loaded = False
        self.folder_path = folder_path

        if not folder_path or not folder_path.exists():
            print(f"[SLIDESHOW] Pasta não encontrada: {folder_path}")
            return False

        image_files = []
        for ext in ("*.png", "*.jpg", "*.jpeg", "*.bmp",
                    "*.PNG", "*.JPG", "*.JPEG", "*.BMP"):
            image_files.extend(folder_path.glob(ext))

        # Remove duplicatas
        seen = set()
        unique = []
        for f in image_files:
            if f not in seen:
                seen.add(f)
                unique.append(f)

        # Ordenação NATURAL: news_2 antes de news_10
        image_files = sorted(unique, key=natural_sort_key)

        if not image_files:
            print(f"[SLIDESHOW] Nenhuma imagem em {folder_path}")
            return False

        for img_path in image_files:
            try:
                img = pygame.image.load(str(img_path))
                if img:
                    self.image_surfaces.append(img)
                    self.image_names.append(img_path.name)
                    print(f"[SLIDESHOW] Carregada: {img_path.name}")
            except Exception as e:
                print(f"[SLIDESHOW] Erro ao carregar {img_path.name}: {e}")

        if self.image_surfaces:
            self._loaded = True
            return True

        return False

    def _create_fallback_images(self):
        print("[SLIDESHOW] Criando imagens de fallback")
        colors = [
            (40, 30, 80), (30, 50, 70), (50, 30, 60), (30, 60, 50), (60, 40, 30)
        ]
        self.image_surfaces = []
        self.image_names = []
        for i, color in enumerate(colors):
            surf = pygame.Surface((400, 300))
            surf.fill(color)
            font = pygame.font.Font(None, 36)
            text = font.render(f"Preview {i + 1}", True, (200, 200, 220))
            text_rect = text.get_rect(center=(200, 150))
            surf.blit(text, text_rect)
            pygame.draw.rect(surf, (100, 100, 140), surf.get_rect(), 2)
            self.image_surfaces.append(surf)
            self.image_names.append(f"fallback_{i + 1}.png")
        self._loaded = True

    # ------------------------------------------------------------------
    def update(self, dt):
        if not self._loaded or len(self.image_surfaces) <= 1:
            return
        self.timer += dt
        if self.timer >= self.switch_interval:
            self.timer = 0
            self.current_index = (self.current_index + 1) % len(self.image_surfaces)

    def get_current_image(self):
        if not self._loaded or not self.image_surfaces:
            return None
        return self.image_surfaces[self.current_index]

    def get_current_name(self):
        """Retorna o nome do arquivo da imagem atual (ou None)."""
        if not self._loaded or not self.image_names:
            return None
        if 0 <= self.current_index < len(self.image_names):
            return self.image_names[self.current_index]
        return None

    def next(self):
        if not self._loaded or len(self.image_surfaces) <= 1:
            return
        self.current_index = (self.current_index + 1) % len(self.image_surfaces)
        self.timer = 0

    def prev(self):
        if not self._loaded or len(self.image_surfaces) <= 1:
            return
        self.current_index = (self.current_index - 1) % len(self.image_surfaces)
        self.timer = 0

    def get_image_count(self):
        return len(self.image_surfaces)


# =========================================================================
# BUTTON (inalterado)
# =========================================================================
class Button:
    """Botão estilizado com responsividade e efeitos visuais"""

    def __init__(self, x, y, width, height, text, color, hover_color, callback, font=None, volume: float = None):
        self.relative_x = x
        self.relative_y = y
        self.relative_width = width
        self.relative_height = height

        self.rect = pygame.Rect(0, 0, 0, 0)
        self.text = text
        self.color = color
        self.hover_color = hover_color
        self.callback = callback
        self.font = font
        self.is_hovered = False
        self._was_hovered = False

        self.volume = volume

        self.text_surface = None
        self.text_rect = None

        self.glow_alpha = 0
        self.glow_direction = 1
        self.scale = 1.0
        self.target_scale = 1.0

        self.icon = None
        self.icon_rect = None

        self.disabled = False
        self.disabled_tooltip = ""

    def update_absolute_position(self, viewport_width, viewport_height, viewport_x, viewport_y):
        abs_x = viewport_x + int(self.relative_x * viewport_width)
        abs_y = viewport_y + int(self.relative_y * viewport_height)
        abs_width = int(self.relative_width * viewport_width)
        abs_height = int(self.relative_height * viewport_height)

        self.rect = pygame.Rect(abs_x, abs_y, abs_width, abs_height)

        font_size = max(18, int(viewport_height * 0.032))
        if self.font is None:
            self.font = pygame.font.Font(None, font_size)
        self.text_surface = self.font.render(self.text, True, (255, 255, 255))
        self.text_rect = self.text_surface.get_rect(center=self.rect.center)

    def update(self, dt):
        self.glow_alpha += self.glow_direction * 2
        if self.glow_alpha >= 150:
            self.glow_alpha = 150
            self.glow_direction = -1
        elif self.glow_alpha <= 0:
            self.glow_alpha = 0
            self.glow_direction = 1

        self.scale += (self.target_scale - self.scale) * 0.1

    def handle_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            was_hovered = self.is_hovered
            self.is_hovered = self.rect.collidepoint(event.pos)

            if self.is_hovered and not was_hovered:
                self.target_scale = 1.05
                if not self.disabled:
                    sound_manager.play_effect(SoundEffect.CLICK, volume=self.volume)
                else:
                    sound_manager.play_effect(SoundEffect.CLICK, volume=(self.volume or 0.3) * 0.5)
            elif not self.is_hovered and was_hovered:
                self.target_scale = 1.0

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.is_hovered:
                sound_manager.play_effect(SoundEffect.CLICK, volume=self.volume)
                self.target_scale = 0.95
                if self.callback:
                    self.callback()

        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self.is_hovered:
                self.target_scale = 1.05

    def render(self, screen):
        if not self.text_surface:
            return

        scaled_rect = self.rect.copy()
        if self.scale != 1.0:
            width_offset = (self.rect.width * (self.scale - 1)) // 2
            height_offset = (self.rect.height * (self.scale - 1)) // 2
            scaled_rect = self.rect.inflate(width_offset * 2, height_offset * 2)
            scaled_rect.center = self.rect.center

        shadow_rect = scaled_rect.copy()
        shadow_rect.y += 3
        pygame.draw.rect(screen, (10, 10, 20, 50), shadow_rect, border_radius=8)

        if self.disabled:
            base_color = (45, 45, 55)
            hover_color = (60, 60, 70)
            color = hover_color if self.is_hovered else base_color

            pygame.draw.rect(screen, color, scaled_rect, border_radius=8)
            border_color = (100, 90, 90) if self.is_hovered else (70, 70, 80)
            pygame.draw.rect(screen, border_color, scaled_rect, 2, border_radius=8)

            lock_size = max(10, int(scaled_rect.height * 0.28))
            lock_x = scaled_rect.right - lock_size - 6
            lock_y = scaled_rect.y + 6
            body_rect = pygame.Rect(lock_x, lock_y + lock_size // 3,
                                    lock_size, int(lock_size * 0.7))
            pygame.draw.rect(screen, (180, 160, 90), body_rect, border_radius=2)
            arc_rect = pygame.Rect(lock_x + lock_size // 4,
                                   lock_y,
                                   lock_size // 2,
                                   lock_size // 2)
            pygame.draw.arc(screen, (180, 160, 90), arc_rect,
                            3.14, 2 * 3.14, max(2, lock_size // 8))

            text_surface_scaled = pygame.transform.scale(
                self.text_surface,
                (int(self.text_surface.get_width() * self.scale),
                 int(self.text_surface.get_height() * self.scale))
            )
            text_surface_scaled = text_surface_scaled.copy()
            dark_overlay = pygame.Surface(text_surface_scaled.get_size(), pygame.SRCALPHA)
            dark_overlay.fill((0, 0, 0, 90))
            text_surface_scaled.blit(dark_overlay, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)

            text_rect = text_surface_scaled.get_rect(center=scaled_rect.center)
            screen.blit(text_surface_scaled, text_rect)

            if self.is_hovered and self.disabled_tooltip:
                self._render_tooltip(screen, scaled_rect)
            return

        color = self.hover_color if self.is_hovered else self.color

        if self.is_hovered:
            glow_surface = pygame.Surface((scaled_rect.width, scaled_rect.height), pygame.SRCALPHA)
            glow_rect = glow_surface.get_rect()
            pygame.draw.rect(glow_surface, (*color[:3], self.glow_alpha), glow_rect, border_radius=8)
            screen.blit(glow_surface, scaled_rect)
            pygame.draw.rect(screen, (255, 215, 0), scaled_rect, 3, border_radius=8)
        else:
            pygame.draw.rect(screen, color, scaled_rect, border_radius=8)
            pygame.draw.rect(screen, (80, 70, 50), scaled_rect, 2, border_radius=8)

        if self.is_hovered:
            inner_glow = pygame.Surface((scaled_rect.width - 8, scaled_rect.height - 8), pygame.SRCALPHA)
            pygame.draw.rect(inner_glow, (255, 255, 255, 25), inner_glow.get_rect(), border_radius=6)
            screen.blit(inner_glow, (scaled_rect.x + 4, scaled_rect.y + 4))

        text_surface_scaled = pygame.transform.scale(
            self.text_surface,
            (int(self.text_surface.get_width() * self.scale),
             int(self.text_surface.get_height() * self.scale))
        )
        text_rect = text_surface_scaled.get_rect(center=scaled_rect.center)
        screen.blit(text_surface_scaled, text_rect)

    def _render_tooltip(self, screen, anchor_rect):
        font = pygame.font.Font(None, 18)
        text_surf = font.render(self.disabled_tooltip, True, (255, 230, 180))
        pad_x, pad_y = 10, 6
        tt_w = text_surf.get_width() + pad_x * 2
        tt_h = text_surf.get_height() + pad_y * 2

        tt_x = anchor_rect.centerx - tt_w // 2
        tt_y = anchor_rect.top - tt_h - 6
        show_above = tt_y >= 0
        if not show_above:
            tt_y = anchor_rect.bottom + 6

        bg = pygame.Surface((tt_w, tt_h), pygame.SRCALPHA)
        bg.fill((20, 20, 30, 230))
        screen.blit(bg, (tt_x, tt_y))
        pygame.draw.rect(screen, (200, 160, 60), (tt_x, tt_y, tt_w, tt_h), 1, border_radius=4)
        screen.blit(text_surf, (tt_x + pad_x, tt_y + pad_y))

        arrow_size = 6
        if show_above:
            pygame.draw.polygon(screen, (200, 160, 60), [
                (anchor_rect.centerx - arrow_size, tt_y + tt_h),
                (anchor_rect.centerx + arrow_size, tt_y + tt_h),
                (anchor_rect.centerx, tt_y + tt_h + arrow_size),
            ])
        else:
            pygame.draw.polygon(screen, (200, 160, 60), [
                (anchor_rect.centerx - arrow_size, tt_y),
                (anchor_rect.centerx + arrow_size, tt_y),
                (anchor_rect.centerx, tt_y - arrow_size),
            ])


# =========================================================================
# MENU SCENE
# =========================================================================
class MenuScene(BaseScene):
    """Menu principal com painel lateral NEWS / PREVIEW"""

    DEBUG_MODE = True

    def __init__(self, game):
        super().__init__(game)

        has_starter = getattr(self.game.player, 'has_chosen_starter', False)
        self.start_text = "Continuar Jogo" if has_starter else "Iniciar Jogo"

        # Estado
        self.reset_confirmation_active = False
        self.reset_confirmation_timer = 0
        self._confirm_yes_rect = None
        self._confirm_no_rect = None
        self._music_started = False
        self._animation_timer = 0

        # Slideshows
        self.preview_slideshow = ImageSlideshow(switch_interval=3.0)
        self.news_slideshow = ImageSlideshow(switch_interval=6.0)

        self.news_versions = []
        self.current_news_version_index = 0
        self.view_mode = "news"

        # Rects interativos
        self.tab_news_rect = None
        self.tab_preview_rect = None
        self.version_left_rect = None
        self.version_right_rect = None
        self.link_button_rect = None
        self._link_hover = False

        self._nav_left_rect = None
        self._nav_right_rect = None
        self._nav_hover_left = False
        self._nav_hover_right = False

        self._load_slideshows()

        self.logo_surface = None
        self.logo_rect = None
        self._logo_loaded_from_file = False
        self._create_logo()

        self.buttons = []
        self._create_buttons()

        self.particles = []
        self._create_particles()

        self._start_menu_music()

    # ======================================================================
    # CARREGAMENTO
    # ======================================================================

    def _load_slideshows(self):
        # PREVIEW
        preview_path = SPRITES_PATH / "screenshots" / "game_preview"
        ok = self.preview_slideshow.load_from_folder(preview_path)
        if not ok:
            alt = SPRITES_PATH / "screenshots"
            ok = self.preview_slideshow.load_from_folder(alt)
        if not ok:
            self.preview_slideshow._create_fallback_images()

        # NEWS (versões em subpastas)
        news_base = SPRITES_PATH / "screenshots" / "news"
        if news_base.exists() and news_base.is_dir():
            self.news_versions = sorted(
                [d.name for d in news_base.iterdir() if d.is_dir()],
                reverse=True
            )
            print(f"[MENU] Versões de news encontradas: {self.news_versions}")
        else:
            print(f"[MENU] Pasta de news não encontrada: {news_base}")

        self.current_news_version_index = 0
        self._load_current_news_version()

    def _load_current_news_version(self):
        if not self.news_versions:
            return
        version = self.news_versions[self.current_news_version_index]
        news_path = SPRITES_PATH / "screenshots" / "news" / version
        ok = self.news_slideshow.load_from_folder(news_path)
        if not ok:
            self.news_slideshow.image_surfaces = []
            self.news_slideshow.image_names = []
            self.news_slideshow._loaded = False
            self.news_slideshow.current_index = 0

    # ======================================================================
    # HELPERS DE NAVEGAÇÃO
    # ======================================================================

    def _get_active_slideshow(self):
        if self.view_mode == "preview":
            return self.preview_slideshow
        return self.news_slideshow

    def _get_current_news_version(self):
        if not self.news_versions:
            return None
        if 0 <= self.current_news_version_index < len(self.news_versions):
            return self.news_versions[self.current_news_version_index]
        return None

    def _set_view_mode(self, mode):
        if mode not in ("news", "preview"):
            return
        if self.view_mode == mode:
            return
        self.view_mode = mode
        print(f"[MENU] Aba ativa: {mode}")

    def _change_news_version(self, delta):
        if not self.news_versions:
            return
        self.current_news_version_index = (
            self.current_news_version_index + delta
        ) % len(self.news_versions)
        self._load_current_news_version()
        sound_manager.play_effect(SoundEffect.CLICK, volume=0.3)
        print(f"[MENU] Versão de news: {self._get_current_news_version()}")

    def _open_changelog(self):
        version = self._get_current_news_version()
        url = get_devlog_url(version) if version else None
        if not url:
            print(f"[MENU] Sem devlog cadastrado para v{version}")
            return
        try:
            webbrowser.open(url)
            print(f"[MENU] Abrindo changelog: {url}")
        except Exception as e:
            print(f"[MENU] Erro ao abrir URL: {e}")

    # ======================================================================
    # LOGO / BOTÕES
    # ======================================================================

    def _create_logo(self):
        logo_paths = [
            SPRITES_PATH / "UI" / "logo.png",
            RES_PATH / "PokemonSprites" / "UI" / "logo.png",
            SPRITES_PATH / "UI" / "Logo.png",
            RES_PATH / "PokemonSprites" / "UI" / "Logo.png",
            SPRITES_PATH / "screenshots" / "logo.png",
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

        print("[MENU] logo.png não encontrada - usando logo desenhada (fallback)")
        logo_width = 500
        logo_height = 150

        self.logo_surface = pygame.Surface((logo_width, logo_height), pygame.SRCALPHA)
        self._logo_loaded_from_file = False

        for i in range(logo_height):
            alpha = int(180 - (i / logo_height) * 60)
            color = (255, 215, 0, alpha)
            pygame.draw.line(self.logo_surface, color, (0, i), (logo_width, i))

        pygame.draw.rect(self.logo_surface, (200, 170, 50), (0, 0, logo_width, logo_height), 4, border_radius=20)
        pygame.draw.rect(self.logo_surface, (255, 215, 0), (4, 4, logo_width - 8, logo_height - 8), 2, border_radius=18)

        inner_rect = pygame.Rect(10, 10, logo_width - 20, logo_height - 20)
        pygame.draw.rect(self.logo_surface, (30, 20, 50, 180), inner_rect, border_radius=15)

        font_large = pygame.font.Font(None, 60)
        text_pokemon = font_large.render("POKEMON", True, (255, 255, 255))
        text_rect = text_pokemon.get_rect(center=(logo_width // 2, 55))
        self.logo_surface.blit(text_pokemon, text_rect)

        font_small = pygame.font.Font(None, 36)
        text_td = font_small.render("TOWER DEFENSE", True, (200, 200, 220))
        text_rect2 = text_td.get_rect(center=(logo_width // 2, 105))
        self.logo_surface.blit(text_td, text_rect2)

        pygame.draw.line(self.logo_surface, (255, 215, 0),
                         (logo_width // 4, 80), (logo_width * 3 // 4, 80), 2)

    def _create_buttons(self):
        left_margin = 0.05
        button_width = 0.35
        main_btn_y = 0.30
        BTN_VOLUME = 0.3

        editor_btn = Button(
            left_margin, main_btn_y + 0.28, button_width, 0.07, "Editor de Fases",
            (40, 40, 60), (80, 80, 120), self.open_editor, None,
            volume=BTN_VOLUME
        )
        if not MenuScene.DEBUG_MODE:
            editor_btn.disabled = True
            editor_btn.disabled_tooltip = "Disponível apenas em modo debug"

        self.buttons = [
            Button(left_margin, main_btn_y, button_width, 0.08, self.start_text,
                   (60, 60, 20), (120, 120, 30), self.start_game, None,
                   volume=BTN_VOLUME),
            Button(left_margin, main_btn_y + 0.10, button_width, 0.07, "Multiplayer",
                   (40, 40, 60), (80, 80, 120), self.open_multiplayer, None,
                   volume=BTN_VOLUME),
            Button(left_margin, main_btn_y + 0.19, button_width, 0.07, "Configuracoes",
                   (40, 40, 60), (80, 80, 120), self.open_settings, None,
                   volume=BTN_VOLUME),
            editor_btn,
            Button(left_margin, main_btn_y + 0.37, 0.17, 0.06, "Mystery Gift",
                   (40, 20, 40), (80, 40, 80), self.open_mystery_gift, None,
                   volume=BTN_VOLUME),
            Button(left_margin + 0.18, main_btn_y + 0.37, 0.17, 0.06, "RESETAR",
                   (60, 15, 15), (120, 25, 25), self.show_reset_confirmation, None,
                   volume=BTN_VOLUME),
            Button(left_margin, main_btn_y + 0.46, button_width, 0.07, "Sair",
                   (60, 20, 20), (120, 30, 30), self.quit_game, None,
                   volume=BTN_VOLUME),
        ]

    def _create_particles(self):
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
    # NAVEGAÇÃO DE MENUS
    # ======================================================================

    def open_multiplayer(self):
        from src.scenes.multiplayer_menu_scene.multiplayer_menu_scene import MultiplayerMenuScene
        self.game.current_scene = MultiplayerMenuScene(self.game)

    def open_settings(self):
        sound_manager.stop_music(fade_ms=300)
        self.game.current_scene = SettingsScene(self.game)

    def open_editor(self):
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
    # RESET
    # ======================================================================

    def show_reset_confirmation(self):
        if not self.reset_confirmation_active:
            self.reset_confirmation_active = True
            self.reset_confirmation_timer = 0
            sound_manager.play_effect(SoundEffect.CLICK, volume=0.3)

    def _execute_reset(self):
        print("[MENU] === INICIANDO RESET DE PROGRESSO ===")
        try:
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

            from src.managers.save_manager import save_manager
            save_manager.current_save_file = None
            save_manager.save_data = save_manager._get_default_save_data()

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
        has_starter = getattr(self.game.player, 'has_chosen_starter', False)
        self.start_text = "Continuar Jogo" if has_starter else "Iniciar Jogo"
        if self.buttons:
            self.buttons[0].text = self.start_text
            self.buttons[0].text_surface = None

    # ======================================================================
    # EVENTOS
    # ======================================================================

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_p:
                self.toggle_pause()
            elif event.key == pygame.K_RETURN:
                self.start_game()
            elif event.key == pygame.K_ESCAPE and self.reset_confirmation_active:
                self.reset_confirmation_active = False
                sound_manager.play_effect(SoundEffect.CLICK, volume=0.3)
            elif event.key == pygame.K_LEFT:
                active = self._get_active_slideshow()
                if active:
                    active.prev()
            elif event.key == pygame.K_RIGHT:
                active = self._get_active_slideshow()
                if active:
                    active.next()

        if self.reset_confirmation_active:
            self._handle_reset_confirmation_event(event)
            return

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.tab_news_rect and self.tab_news_rect.collidepoint(event.pos):
                self._set_view_mode("news")
                sound_manager.play_effect(SoundEffect.CLICK, volume=0.3)
                return
            if self.tab_preview_rect and self.tab_preview_rect.collidepoint(event.pos):
                self._set_view_mode("preview")
                sound_manager.play_effect(SoundEffect.CLICK, volume=0.3)
                return

            if self.version_left_rect and self.version_left_rect.collidepoint(event.pos):
                self._change_news_version(-1)
                return
            if self.version_right_rect and self.version_right_rect.collidepoint(event.pos):
                self._change_news_version(1)
                return

            if self.link_button_rect and self.link_button_rect.collidepoint(event.pos):
                self._open_changelog()
                sound_manager.play_effect(SoundEffect.CLICK, volume=0.3)
                return

            if self._nav_left_rect and self._nav_left_rect.collidepoint(event.pos):
                active = self._get_active_slideshow()
                if active:
                    active.prev()
                sound_manager.play_effect(SoundEffect.CLICK, volume=0.3)
                return
            if self._nav_right_rect and self._nav_right_rect.collidepoint(event.pos):
                active = self._get_active_slideshow()
                if active:
                    active.next()
                sound_manager.play_effect(SoundEffect.CLICK, volume=0.3)
                return

        for button in self.buttons:
            button.handle_event(event)

    def _handle_reset_confirmation_event(self, event):
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
        if self.paused:
            return

        self._animation_timer += dt

        for particle in self.particles:
            particle['x'] += (particle['speed'] * dt * 0.1) * (particle['angle'] == 0)
            particle['y'] += (particle['speed'] * dt * 0.05)
            particle['phase'] += dt * 0.5

            if particle['x'] > 1:
                particle['x'] = 0
            if particle['y'] > 1:
                particle['y'] = 0

        for button in self.buttons:
            button.update(dt)

        active = self._get_active_slideshow()
        if active:
            active.update(dt)

        if self.reset_confirmation_active:
            self.reset_confirmation_timer += dt

    # ======================================================================
    # RENDER
    # ======================================================================

    def render(self, screen):
        self._draw_gradient_background(screen)

        vx = self.screen_manager.viewport_x
        vy = self.screen_manager.viewport_y
        vw = self.screen_manager.viewport_width
        vh = self.screen_manager.viewport_height

        for button in self.buttons:
            button.update_absolute_position(vw, vh, vx, vy)

        for particle in self.particles:
            x = vx + int(particle['x'] * vw)
            y = vy + int(particle['y'] * vh)
            alpha = int(particle['alpha'] * (0.5 + 0.5 * (particle['phase'] % 1)))
            color = (*particle['color'], alpha)

            glow_size = particle['size'] + 4
            for i in range(glow_size, particle['size'], -2):
                alpha_glow = int(alpha * (i / glow_size))
                pygame.draw.circle(screen, (*particle['color'], alpha_glow), (x, y), i)

            pygame.draw.circle(screen, color, (x, y), particle['size'])

        button_width = int(vw * 0.35)
        left_margin = int(vw * 0.05)

        logo_width = int(vw * 0.30)
        orig_w, orig_h = self.logo_surface.get_size()
        if orig_w <= 0:
            orig_w = 1
        logo_height = int(logo_width * (orig_h / orig_w))

        logo_x = vx + left_margin + (button_width - logo_width) // 2
        logo_y = vy + int(vh * 0.05)

        try:
            logo_scaled = pygame.transform.smoothscale(self.logo_surface, (logo_width, logo_height))
        except Exception:
            logo_scaled = pygame.transform.scale(self.logo_surface, (logo_width, logo_height))

        screen.blit(logo_scaled, (logo_x, logo_y))

        self._render_preview_panel(screen, vx, vy, vw, vh)

        for button in self.buttons:
            button.render(screen)

        font_small = pygame.font.Font(None, 16)
        version_text = font_small.render(f"v{self.game.current_version} - Em desenvolvimento", True, (100, 100, 120))
        screen.blit(version_text, (vx + 15, vy + vh - 20))

        if self.reset_confirmation_active:
            self._render_reset_confirmation(screen)

        if self.paused:
            self._render_pause_overlay(screen)

    # ------------------------------------------------------------------
    # PAINEL LATERAL
    # ------------------------------------------------------------------
    def _render_preview_panel(self, screen, vx, vy, vw, vh):
        panel_x = vx + int(vw * 0.48)
        panel_y = vy + int(vh * 0.05)
        panel_width = int(vw * 0.47)
        panel_height = int(vh * 0.85)

        panel_rect = pygame.Rect(panel_x, panel_y, panel_width, panel_height)

        panel_surface = pygame.Surface((panel_width, panel_height), pygame.SRCALPHA)
        panel_surface.fill((10, 10, 30, 200))
        screen.blit(panel_surface, panel_rect)

        pygame.draw.rect(screen, (60, 50, 80), panel_rect, 2, border_radius=12)
        pygame.draw.rect(screen, (100, 80, 130), panel_rect.inflate(-4, -4), 1, border_radius=10)

        mouse_pos = pygame.mouse.get_pos()

        # ===================== TABS =====================
        pad = 10
        tab_h = max(30, int(panel_height * 0.06))
        tab_w = int(panel_width * 0.30)
        tab_gap = 10
        tabs_total = tab_w * 2 + tab_gap
        tab_x = panel_x + (panel_width - tabs_total) // 2
        tab_y = panel_y + pad

        self.tab_news_rect = pygame.Rect(tab_x, tab_y, tab_w, tab_h)
        self.tab_preview_rect = pygame.Rect(tab_x + tab_w + tab_gap, tab_y, tab_w, tab_h)

        self._render_tab(screen, self.tab_news_rect, "NEWS", self.view_mode == "news", mouse_pos)
        self._render_tab(screen, self.tab_preview_rect, "PREVIEW", self.view_mode == "preview", mouse_pos)

        content_y = tab_y + tab_h + 10

        # ===================== VERSION SELECTOR =====================
        self.version_left_rect = None
        self.version_right_rect = None

        if self.view_mode == "news" and self.news_versions:
            ver_h = max(28, int(panel_height * 0.05))
            arrow_w = max(34, ver_h)
            label_w = int(panel_width * 0.32)
            gap = 8
            ver_total = arrow_w * 2 + label_w + gap * 2
            ver_x = panel_x + (panel_width - ver_total) // 2
            ver_y = content_y

            self.version_left_rect = pygame.Rect(ver_x, ver_y, arrow_w, ver_h)
            label_rect = pygame.Rect(ver_x + arrow_w + gap, ver_y, label_w, ver_h)
            self.version_right_rect = pygame.Rect(ver_x + arrow_w + gap + label_w + gap,
                                                  ver_y, arrow_w, ver_h)

            self._render_arrow(screen, self.version_left_rect, "<", mouse_pos)
            self._render_arrow(screen, self.version_right_rect, ">", mouse_pos)

            cur_version = self._get_current_news_version() or "---"
            v_font = pygame.font.Font(None, max(18, int(ver_h * 0.6)))
            v_text = v_font.render(f"v{cur_version}", True, (255, 220, 120))
            pygame.draw.rect(screen, (20, 20, 35), label_rect, border_radius=6)
            pygame.draw.rect(screen, (90, 80, 110), label_rect, 1, border_radius=6)
            screen.blit(v_text, v_text.get_rect(center=label_rect.center))

            content_y = ver_y + ver_h + 10

        # ===================== CÁLCULO DE ESPAÇO (de baixo pra cima) =====================
        bottom_pad = 12
        bottom_y = panel_y + panel_height - bottom_pad

        # LINK (só news)
        link_h = max(34, int(panel_height * 0.065)) if self.view_mode == "news" else 0
        link_y = None
        if self.view_mode == "news":
            link_y = bottom_y - link_h
            bottom_y = link_y - 10

        # DOTS
        dots_h = 10
        dots_y = bottom_y - dots_h
        bottom_y = dots_y - 6

        # INDICADOR "3 / 8"
        ind_font = pygame.font.Font(None, max(14, int(panel_height * 0.028)))
        ind_h = ind_font.get_height()
        ind_y = bottom_y - ind_h
        bottom_y = ind_y - 6

        # NAV (< >)
        nav_h = max(30, int(panel_height * 0.06))
        nav_y = bottom_y - nav_h
        bottom_y = nav_y - 8

        # TÍTULO DA IMAGEM (só news)
        title_font = pygame.font.Font(None, max(16, int(panel_height * 0.032)))
        title_lines = []
        title_h = 0
        if self.view_mode == "news":
            version = self._get_current_news_version()
            img_name = self.news_slideshow.get_current_name()
            title_text = get_news_title(version, img_name) if img_name else None
            if title_text:
                max_title_w = panel_width - 32
                title_lines = self._wrap_text(title_text, title_font, max_title_w)
                line_h = title_font.get_height() + 2
                title_h = len(title_lines) * line_h
                bottom_y -= title_h + 8

        # ÁREA DA IMAGEM
        img_margin = 12
        img_x = panel_x + img_margin
        img_y = content_y
        img_w = panel_width - img_margin * 2
        img_h = bottom_y - img_y
        if img_h < 50:
            img_h = 50

        # ===================== IMAGEM =====================
        active = self._get_active_slideshow()
        current_img = active.get_current_image() if active else None
        self._render_slideshow_image(screen, current_img, img_x, img_y, img_w, img_h, vh)

        # ===================== TÍTULO (renderiza abaixo da imagem) =====================
        if self.view_mode == "news" and title_lines:
            line_h = title_font.get_height() + 2
            ty = bottom_y + 8 - title_h + (title_h - len(title_lines) * line_h) // 2
            for line in title_lines:
                surf = title_font.render(line, True, (230, 220, 250))
                tx = panel_x + (panel_width - surf.get_width()) // 2
                screen.blit(surf, (tx, ty))
                ty += line_h

        # ===================== NAV =====================
        nav_size = nav_h
        nav_gap = 20
        left_x = panel_x + (panel_width - nav_size * 2 - nav_gap) // 2
        self._nav_left_rect = pygame.Rect(left_x, nav_y, nav_size, nav_size)
        right_x = left_x + nav_size + nav_gap
        self._nav_right_rect = pygame.Rect(right_x, nav_y, nav_size, nav_size)

        self._nav_hover_left = self._nav_left_rect.collidepoint(mouse_pos)
        self._nav_hover_right = self._nav_right_rect.collidepoint(mouse_pos)

        for rect, hover, sym in [
            (self._nav_left_rect, self._nav_hover_left, "<"),
            (self._nav_right_rect, self._nav_hover_right, ">"),
        ]:
            color = (80, 70, 100) if hover else (50, 40, 60)
            pygame.draw.rect(screen, color, rect, border_radius=8)
            pygame.draw.rect(screen, (120, 100, 150) if hover else (70, 60, 80), rect, 1, border_radius=8)
            if hover:
                pygame.draw.rect(screen, (150, 130, 180, 30), rect.inflate(-4, -4), border_radius=6)
            f = pygame.font.Font(None, int(nav_size * 0.7))
            t = f.render(sym, True, (220, 210, 240))
            screen.blit(t, t.get_rect(center=rect.center))

        # Indicador
        count = active.get_image_count() if active else 0
        if count > 1:
            idx = active.current_index + 1
            ind_text = ind_font.render(f"{idx} / {count}", True, (180, 170, 200))
            ind_x = panel_x + (panel_width - ind_text.get_width()) // 2
            screen.blit(ind_text, (ind_x, ind_y))

            dot_size = 6
            dot_spacing = 12
            dots_width = count * dot_spacing - (dot_spacing - dot_size)
            dots_x = panel_x + (panel_width - dots_width) // 2
            cy = dots_y + dots_h // 2
            for i in range(count):
                x = dots_x + i * dot_spacing
                is_active = (i == active.current_index)
                color = (200, 180, 220) if is_active else (60, 50, 70)
                pygame.draw.circle(screen, color, (x, cy), dot_size // 2)
                if is_active:
                    pygame.draw.circle(screen, (255, 215, 0), (x, cy), dot_size // 2 + 2, 1)

        # ===================== LINK =====================
        self.link_button_rect = None
        self._link_hover = False
        if self.view_mode == "news":
            btn_h = link_h
            btn_w = int(panel_width * 0.62)
            btn_x = panel_x + (panel_width - btn_w) // 2
            btn_rect = pygame.Rect(btn_x, link_y, btn_w, btn_h)
            self.link_button_rect = btn_rect

            version = self._get_current_news_version()
            url = get_devlog_url(version) if version else None
            hover = btn_rect.collidepoint(mouse_pos)
            self._link_hover = hover

            if url:
                base = (40, 80, 130) if hover else (25, 55, 100)
                border = (120, 190, 255) if hover else (60, 130, 200)
                pygame.draw.rect(screen, base, btn_rect, border_radius=8)
                pygame.draw.rect(screen, border, btn_rect, 2, border_radius=8)
                f = pygame.font.Font(None, int(btn_h * 0.55))
                t = f.render("Ver changelog completo!", True, (220, 240, 255))
                screen.blit(t, t.get_rect(center=btn_rect.center))
            else:
                pygame.draw.rect(screen, (40, 40, 50), btn_rect, border_radius=8)
                pygame.draw.rect(screen, (70, 70, 80), btn_rect, 2, border_radius=8)
                f = pygame.font.Font(None, int(btn_h * 0.5))
                t = f.render("Sem changelog cadastrado", True, (140, 140, 150))
                screen.blit(t, t.get_rect(center=btn_rect.center))

    # ------------------------------------------------------------------
    # WRAP DE TEXTO
    # ------------------------------------------------------------------
    def _wrap_text(self, text, font, max_width):
        """Quebra texto em múltiplas linhas para caber em max_width."""
        words = str(text).split(' ')
        lines = []
        cur = ""
        for w in words:
            test = (cur + " " + w).strip()
            if font.size(test)[0] <= max_width:
                cur = test
            else:
                if cur:
                    lines.append(cur)
                # Se uma única palavra é maior que max_width, ela fica sozinha
                cur = w
        if cur:
            lines.append(cur)
        return lines

    # ------------------------------------------------------------------
    def _render_tab(self, screen, rect, label, is_active, mouse_pos):
        hover = rect.collidepoint(mouse_pos)

        if is_active:
            bg = (70, 60, 110)
            border = (200, 180, 255)
            text_color = (255, 255, 255)
        elif hover:
            bg = (50, 45, 75)
            border = (140, 120, 180)
            text_color = (230, 220, 250)
        else:
            bg = (30, 28, 45)
            border = (70, 60, 90)
            text_color = (170, 165, 190)

        pygame.draw.rect(screen, bg, rect, border_radius=8)
        pygame.draw.rect(screen, border, rect, 2, border_radius=8)

        if is_active:
            underline = pygame.Rect(rect.x + 8, rect.bottom - 4, rect.width - 16, 2)
            pygame.draw.rect(screen, (255, 215, 0), underline)

        font = pygame.font.Font(None, max(18, int(rect.height * 0.62)))
        text = font.render(label, True, text_color)
        screen.blit(text, text.get_rect(center=rect.center))

    def _render_arrow(self, screen, rect, symbol, mouse_pos):
        hover = rect.collidepoint(mouse_pos)
        color = (80, 70, 100) if hover else (40, 35, 55)
        border = (140, 120, 180) if hover else (70, 60, 80)
        pygame.draw.rect(screen, color, rect, border_radius=6)
        pygame.draw.rect(screen, border, rect, 1, border_radius=6)
        f = pygame.font.Font(None, int(rect.height * 0.75))
        t = f.render(symbol, True, (220, 210, 240))
        screen.blit(t, t.get_rect(center=rect.center))

    def _render_slideshow_image(self, screen, current_img, x, y, w, h, vh):
        if not current_img:
            self._render_placeholder(screen, x, y, w, h, vh, "Nenhuma imagem disponivel")
            return

        try:
            img_ratio = current_img.get_width() / current_img.get_height()
        except Exception:
            img_ratio = 1.0
        target_ratio = w / h if h else 1.0

        if img_ratio > target_ratio:
            display_w = w
            display_h = int(w / img_ratio)
        else:
            display_h = h
            display_w = int(h * img_ratio)

        display_x = x + (w - display_w) // 2
        display_y = y + (h - display_h) // 2

        try:
            scaled = pygame.transform.smoothscale(current_img, (display_w, display_h))
            img_rect = pygame.Rect(display_x - 2, display_y - 2, display_w + 4, display_h + 4)
            pygame.draw.rect(screen, (80, 70, 100), img_rect, border_radius=4)
            screen.blit(scaled, (display_x, display_y))
        except Exception as e:
            print(f"[MENU] Erro ao redimensionar imagem: {e}")
            self._render_placeholder(screen, x, y, w, h, vh, "Imagem indisponivel")

    def _render_placeholder(self, screen, x, y, w, h, vh, message):
        font = pygame.font.Font(None, max(16, int(vh * 0.025)))
        surf = font.render(message, True, (150, 150, 170))
        screen.blit(surf, (x + (w - surf.get_width()) // 2,
                           y + (h - surf.get_height()) // 2))

    # ------------------------------------------------------------------
    def _draw_gradient_background(self, screen):
        width = self.screen_manager.window_width
        height = self.screen_manager.window_height

        for i in range(height):
            t = i / height
            r = int(10 + t * 20)
            g = int(12 + t * 25)
            b = int(25 + t * 35)
            pygame.draw.line(screen, (r, g, b), (0, i), (width, i))

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

    # ------------------------------------------------------------------
    def _render_reset_confirmation(self, screen):
        vx = self.screen_manager.viewport_x
        vy = self.screen_manager.viewport_y
        vw = self.screen_manager.viewport_width
        vh = self.screen_manager.viewport_height

        overlay = pygame.Surface((self.screen_manager.window_width, self.screen_manager.window_height))
        alpha = min(180, int(180 * (self.reset_confirmation_timer / 0.3)))
        overlay.set_alpha(alpha)
        overlay.fill((0, 0, 0))
        screen.blit(overlay, (0, 0))

        container_width = int(vw * 0.45)
        container_height = int(vh * 0.45)
        container_x = vx + (vw - container_width) // 2
        container_y = vy + (vh - container_height) // 2

        container_rect = pygame.Rect(container_x, container_y, container_width, container_height)

        for i in range(container_height):
            t = i / container_height
            r = int(30 - t * 10)
            g = int(20 - t * 5)
            b = int(20 - t * 5)
            pygame.draw.line(screen, (r, g, b),
                             (container_x, container_y + i),
                             (container_x + container_width, container_y + i))

        pygame.draw.rect(screen, (200, 40, 40), container_rect, 3, border_radius=15)
        pygame.draw.rect(screen, (255, 60, 60), container_rect.inflate(-6, -6), 1, border_radius=12)

        title_font = pygame.font.Font(None, int(vh * 0.05))
        title_text = title_font.render("RESETAR PROGRESSO", True, (255, 80, 80))
        title_x = container_x + (container_width - title_text.get_width()) // 2
        title_y = container_y + int(container_height * 0.08)
        screen.blit(title_text, (title_x, title_y))

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

        button_width = int(vw * 0.10)
        button_height = int(vh * 0.055)
        spacing = 30
        total_width = button_width * 2 + spacing
        start_x = container_x + (container_width - total_width) // 2
        button_y = container_y + container_height - button_height - int(container_height * 0.08)

        mouse_pos = pygame.mouse.get_pos()

        yes_rect = pygame.Rect(start_x, button_y, button_width, button_height)
        yes_hover = yes_rect.collidepoint(mouse_pos)
        yes_color = (180, 40, 40) if yes_hover else (140, 30, 30)
        pygame.draw.rect(screen, yes_color, yes_rect, border_radius=10)
        pygame.draw.rect(screen, (255, 80, 80) if yes_hover else (200, 60, 60), yes_rect, 2, border_radius=10)
        if yes_hover:
            pygame.draw.rect(screen, (255, 100, 100, 30), yes_rect.inflate(-4, -4), border_radius=8)

        yes_font = pygame.font.Font(None, int(vh * 0.03))
        yes_text = yes_font.render("SIM", True, (255, 255, 255))
        screen.blit(yes_text, yes_text.get_rect(center=yes_rect.center))

        no_rect = pygame.Rect(start_x + button_width + spacing, button_y, button_width, button_height)
        no_hover = no_rect.collidepoint(mouse_pos)
        no_color = (80, 80, 80) if no_hover else (60, 60, 60)
        pygame.draw.rect(screen, no_color, no_rect, border_radius=10)
        pygame.draw.rect(screen, (120, 120, 120) if no_hover else (100, 100, 100), no_rect, 2, border_radius=10)

        no_font = pygame.font.Font(None, int(vh * 0.03))
        no_text = no_font.render("NAO", True, (255, 255, 255))
        screen.blit(no_text, no_text.get_rect(center=no_rect.center))

        self._confirm_yes_rect = yes_rect
        self._confirm_no_rect = no_rect

    # ------------------------------------------------------------------
    def _render_pause_overlay(self, screen):
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
        if not self._music_started or not pygame.mixer.music.get_busy():
            self._start_menu_music()

    def on_exit(self):
        sound_manager.stop_music(fade_ms=300)
        self._music_started = False