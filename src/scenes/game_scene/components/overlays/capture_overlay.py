# src/scenes/game_scene/components/overlays/capture_overlay.py

import pygame
import math
from .base_overlay import BaseOverlay

_FONT_CACHE = {}


class CaptureOverlay(BaseOverlay):
    """Overlay exibido quando um Pokémon é capturado - COM OPÇÃO DE APELIDO"""

    # Dimensões "de design" usadas como referência para escala
    DESIGN_WIDTH = 800
    DESIGN_HEIGHT = 650

    def __init__(self, game_scene, pokemon, is_to_team=True):
        super().__init__(game_scene)
        self.pokemon = pokemon
        self.is_to_team = is_to_team
        self.animation_time = 0
        self.music_played = False

        # Estado do input de nome
        self.naming_mode = False
        self.input_text = ""
        self.input_active = False
        self.input_rect = None
        self.input_cursor_timer = 0
        self.max_name_length = 20

        # Botões
        self.button_rect = None
        self.button_hovered = False
        self.close_button_rect = None
        self.close_button_hovered = False
        self.name_button_rect = None
        self.name_button_hovered = False
        self.skip_button_rect = None
        self.skip_button_hovered = False
        self.confirm_name_rect = None
        self.confirm_name_hovered = False

        # Pausa o jogo
        self.game_scene.game_paused = True
        self.game_scene.paused = True
        if hasattr(self.game_scene, 'wave_manager'):
            self.game_scene.wave_manager.paused = True

        # Dimensões — todas recalculadas em _recalculate_dimensions
        self.scale = 1.0
        self.modal_width = 0
        self.modal_height = 0
        self.modal_padding = 0
        self.section_spacing = 0

        self.title_height = 0
        self.pokemon_section_height = 0
        self.info_section_height = 0
        self.moves_section_height = 0
        self.name_section_height = 0
        self.button_section_height = 0

        self._recalculate_dimensions()

        # Cores
        self.colors = {
            'primary': (100, 150, 255),
            'secondary': (80, 120, 200),
            'accent': (255, 215, 0),
            'success': (100, 200, 100),
            'warning': (255, 150, 100),
            'danger': (255, 100, 100),
            'bg_dark': (20, 25, 45),
            'bg_medium': (30, 35, 55),
            'bg_light': (45, 50, 75),
            'bg_card': (38, 43, 68),
            'text': (255, 255, 255),
            'text_dim': (200, 200, 220),
            'text_muted': (150, 155, 180),
            'border': (80, 100, 140),
            'input_bg': (25, 30, 50),
            'input_border': (100, 120, 160),
            'input_active': (100, 150, 255),
            'gender_male': (70, 120, 200),
            'gender_female': (230, 80, 120),
            'iv_high': (100, 220, 100),
            'iv_med': (255, 200, 100),
            'iv_low': (255, 100, 100),
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

    # ------------------------------------------------------------------ #
    # Dimensões e escala
    # ------------------------------------------------------------------ #

    def _recalculate_dimensions(self):
        """Recalcula todas as dimensões proporcionalmente ao tamanho da tela."""
        sw = self.game_scene.screen_manager.window_width
        sh = self.game_scene.screen_manager.window_height

        # Modal: ~70% da tela, respeitando limites absolutos e nunca maior que a tela
        target_w = int(sw * 0.7)
        target_h = int(sh * 0.85)
        self.modal_width = max(min(target_w, 900), min(560, sw - 30))
        self.modal_height = max(min(target_h, 750), min(520, sh - 30))
        self.modal_width = min(self.modal_width, sw - 20)
        self.modal_height = min(self.modal_height, sh - 20)

        # Fator de escala em relação ao design base (800x650)
        self.scale = min(
            self.modal_width / self.DESIGN_WIDTH,
            self.modal_height / self.DESIGN_HEIGHT,
        )
        # Evita escalas extremas que quebram o layout
        self.scale = max(0.7, min(self.scale, 1.25))

        self.modal_padding = int(22 * self.scale)
        self.section_spacing = int(7 * self.scale)

        # Alturas proporcionais à área de conteúdo disponível
        content_h = self.modal_height - 2 * self.modal_padding
        avail_h = content_h - 5 * self.section_spacing  # 6 seções = 5 gaps

        self.title_height          = int(avail_h * 0.08)
        self.pokemon_section_height = int(avail_h * 0.32)
        self.info_section_height   = int(avail_h * 0.15)
        self.moves_section_height  = int(avail_h * 0.27)
        self.name_section_height   = int(avail_h * 0.10)
        self.button_section_height = int(avail_h * 0.08)

    def _px(self, value):
        """Converte um valor de design (px @ escala 1.0) para pixels reais."""
        return int(value * self.scale)

    def _get_font(self, base_size, bold=False):
        """Fonte escalada. `base_size` é o tamanho no design 800x650."""
        actual = max(8, int(round(base_size * self.scale)))
        key = (actual, bold)
        if key not in _FONT_CACHE:
            font = pygame.font.Font(None, actual)
            if bold:
                font.set_bold(True)
            _FONT_CACHE[key] = font
        return _FONT_CACHE[key]

    @staticmethod
    def _truncate_text(font, text, max_width):
        """Trunca texto com '...' se ultrapassar max_width."""
        if font.size(text)[0] <= max_width:
            return text
        while text and font.size(text + "...")[0] > max_width:
            text = text[:-1]
        return text + "..."

    # ------------------------------------------------------------------ #
    # Eventos
    # ------------------------------------------------------------------ #

    def handle_event(self, event):
        if not self.active:
            return False

        if self.naming_mode:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    self._apply_nickname()
                    return True
                elif event.key == pygame.K_ESCAPE:
                    self._cancel_naming()
                    return True
                elif event.key == pygame.K_BACKSPACE:
                    self.input_text = self.input_text[:-1]
                else:
                    if len(self.input_text) < self.max_name_length and event.unicode.isprintable():
                        self.input_text += event.unicode
                return True

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self.confirm_name_rect and self.confirm_name_rect.collidepoint(event.pos):
                    self._apply_nickname()
                    return True
                elif self.skip_button_rect and self.skip_button_rect.collidepoint(event.pos):
                    self._cancel_naming()
                    return True
            return False

        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_ESCAPE, pygame.K_RETURN):
                self.close()
                return True

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.close_button_rect and self.close_button_rect.collidepoint(event.pos):
                self.close()
                return True
            if self.button_rect and self.button_rect.collidepoint(event.pos):
                self.close()
                return True
            if self.name_button_rect and self.name_button_rect.collidepoint(event.pos):
                self._start_naming_mode()
                return True

        elif event.type == pygame.MOUSEMOTION:
            if self.close_button_rect:
                self.close_button_hovered = self.close_button_rect.collidepoint(event.pos)
            if self.button_rect:
                self.button_hovered = self.button_rect.collidepoint(event.pos)
            if self.name_button_rect:
                self.name_button_hovered = self.name_button_rect.collidepoint(event.pos)
            if self.confirm_name_rect:
                self.confirm_name_hovered = self.confirm_name_rect.collidepoint(event.pos)
            if self.skip_button_rect:
                self.skip_button_hovered = self.skip_button_rect.collidepoint(event.pos)

        return False

    def _start_naming_mode(self):
        self.naming_mode = True
        self.input_text = self.pokemon.custom_name if self.pokemon.custom_name else ""
        self.input_active = True

    def _apply_nickname(self):
        nickname = self.input_text.strip()
        if nickname and len(nickname) <= self.max_name_length:
            self.pokemon.set_custom_name(nickname)
        elif not nickname:
            self.pokemon.set_custom_name(None)

        self.naming_mode = False
        self.input_active = False

        if hasattr(self.game_scene, 'game') and self.game_scene.game:
            self.game_scene.game.player.auto_save()

    def _cancel_naming(self):
        self.naming_mode = False
        self.input_active = False

    def update(self, dt):
        self.animation_time += dt
        self.input_cursor_timer += dt

        if not self.music_played:
            self._play_capture_sound()
            self.music_played = True

    def _play_capture_sound(self):
        try:
            from src.managers.sounds.sound_manager import sound_manager
            sound_manager.play_capture_sound()
        except Exception:
            pass

    def close(self):
        self.active = False
        self.game_scene.close_capture_overlay()

    # ------------------------------------------------------------------ #
    # Render
    # ------------------------------------------------------------------ #

    def render(self, screen):
        if not self.active:
            return

        self._recalculate_dimensions()
        viewport = self.get_viewport_rect()

        # Fundo escurecido
        overlay = pygame.Surface((viewport.width, viewport.height))
        overlay.set_alpha(200)
        overlay.fill((0, 0, 0))
        screen.blit(overlay, (viewport.x, viewport.y))

        # Modal centralizado
        modal_x = viewport.x + (viewport.width - self.modal_width) // 2
        modal_y = viewport.y + (viewport.height - self.modal_height) // 2
        modal_rect = pygame.Rect(modal_x, modal_y, self.modal_width, self.modal_height)

        # Fundo e bordas
        self._render_modal_background(screen, modal_rect)
        pygame.draw.rect(screen, self.colors['primary'], modal_rect, 3, border_radius=self._px(20))
        pygame.draw.rect(screen, self.colors['accent'], modal_rect.inflate(-6, -6), 1,
                         border_radius=self._px(18))

        self._render_close_button(screen, modal_rect)

        # Área de conteúdo
        content_rect = pygame.Rect(
            modal_rect.x + self.modal_padding,
            modal_rect.y + self.modal_padding,
            modal_rect.width - self.modal_padding * 2,
            modal_rect.height - self.modal_padding * 2,
        )

        cy = content_rect.y
        cx, cw = content_rect.x, content_rect.width

        self._render_title(screen, cx, cy, cw)
        cy += self.title_height + self.section_spacing

        self._render_pokemon_section(screen, cx, cy, cw)
        cy += self.pokemon_section_height + self.section_spacing

        self._render_info_section(screen, cx, cy, cw)
        cy += self.info_section_height + self.section_spacing

        self._render_moves_section(screen, cx, cy, cw)
        cy += self.moves_section_height + self.section_spacing

        if self.naming_mode:
            self._render_naming_section(screen, cx, cy, cw)
        else:
            self._render_name_section(screen, cx, cy, cw)
        cy += self.name_section_height + self.section_spacing

        self._render_button(screen, cx, cy, cw)

        self._render_status_message(screen, viewport)

    # --------------------- Componentes do modal ----------------------- #

    def _render_modal_background(self, screen, modal_rect):
        bg_rect = modal_rect.inflate(-2, -2)
        pygame.draw.rect(screen, self.colors['bg_dark'], bg_rect, border_radius=self._px(20))

    def _render_close_button(self, screen, modal_rect):
        size = self._px(30)
        x = modal_rect.right - size - self._px(10)
        y = modal_rect.y + self._px(10)
        self.close_button_rect = pygame.Rect(x, y, size, size)

        if self.close_button_hovered:
            bg_color = (*self.colors['danger'], 120)
            border_color = self.colors['danger']
        else:
            bg_color = (*self.colors['bg_light'], 180)
            border_color = self.colors['border']

        pygame.draw.rect(screen, bg_color, self.close_button_rect, border_radius=self._px(8))
        pygame.draw.rect(screen, border_color, self.close_button_rect, 1, border_radius=self._px(8))

        font = self._get_font(22, True)
        txt = font.render("X", True, self.colors['text_dim'])
        screen.blit(txt, (
            x + (size - txt.get_width()) // 2,
            y + (size - txt.get_height()) // 2,
        ))

    def _render_title(self, screen, x, y, width):
        font = self._get_font(30, True)
        title = font.render("CAPTURADO", True, self.colors['success'])
        screen.blit(title, (x + (width - title.get_width()) // 2, y))

        line_y = y + title.get_height() + self._px(4)
        line_w = self._px(140)
        line_x = x + (width - line_w) // 2
        pygame.draw.line(screen, self.colors['success'],
                         (line_x, line_y), (line_x + line_w, line_y), 2)

    # ---------- Seção do Pokémon (layout horizontal) ---------- #

    def _render_pokemon_section(self, screen, x, y, width):
        section_rect = pygame.Rect(x, y, width, self.pokemon_section_height)
        pygame.draw.rect(screen, (*self.colors['bg_card'], 200), section_rect,
                         border_radius=self._px(15))
        pygame.draw.rect(screen, (*self.colors['border'], 150), section_rect, 2,
                         border_radius=self._px(15))

        # Layout horizontal: sprite à esquerda, infos à direita
        sprite_area_w = int(width * 0.36)
        info_x = section_rect.x + sprite_area_w + self._px(12)
        info_w = section_rect.right - info_x - self._px(14)

        # Sprite
        sprite_center_x = section_rect.x + sprite_area_w // 2
        sprite_center_y = section_rect.centery
        sprite_size = int(min(sprite_area_w * 0.68, self.pokemon_section_height * 0.62))
        self._render_pokemon_sprite(screen, sprite_center_x, sprite_center_y, sprite_size)

        # Divisor vertical sutil
        sep_x = section_rect.x + sprite_area_w + self._px(2)
        pygame.draw.line(screen, (*self.colors['border'], 90),
                         (sep_x, section_rect.y + self._px(14)),
                         (sep_x, section_rect.bottom - self._px(14)), 1)

        # ---------- Informações ---------- #
        gap = self._px(8)

        name_font = self._get_font(26, True)
        name_surf = name_font.render(self.pokemon.name.upper(), True, self.colors['accent'])

        status_font = self._get_font(15)
        level_surf = status_font.render(f"Lv.{self.pokemon.level}", True, self.colors['text_dim'])

        id_surf = self._get_font(12).render(f"#{self.pokemon.id:04d}", True,
                                            self.colors['text_muted'])

        # Gênero
        gender_text, gender_color = "", self.colors['text_muted']
        if getattr(self.pokemon, 'gender', None) == "male":
            gender_text, gender_color = "MACHO", self.colors['gender_male']
        elif getattr(self.pokemon, 'gender', None) == "female":
            gender_text, gender_color = "FÊMEA", self.colors['gender_female']
        gender_surf = self._get_font(13, True).render(gender_text, True, gender_color) \
            if gender_text else None

        # Tipos
        type_height = self._px(26)
        type_font = self._get_font(13, True)
        type_surfs = []
        for t in (self.pokemon.types or []):
            color = self.type_colors.get(t.lower(), (150, 150, 150))
            surf = type_font.render(t.capitalize(), True, (255, 255, 255))
            type_surfs.append((surf, color))

        types_row_h = type_height if type_surfs else 0

        # Altura total para centralizar verticalmente
        total_h = name_surf.get_height() + gap + level_surf.get_height()
        if types_row_h:
            total_h += gap + types_row_h

        cursor_y = section_rect.centery - total_h // 2

        # Linha 1: nome
        screen.blit(name_surf, (info_x, cursor_y))
        cursor_y += name_surf.get_height() + gap

        # Linha 2: level | gênero | ID
        row_cy = cursor_y + level_surf.get_height() // 2
        cursor_x = info_x

        screen.blit(level_surf, (cursor_x, cursor_y))
        cursor_x += level_surf.get_width() + self._px(14)

        if gender_surf:
            gy = row_cy - gender_surf.get_height() // 2
            screen.blit(gender_surf, (cursor_x, gy))
            cursor_x += gender_surf.get_width() + self._px(14)

        iy = row_cy - id_surf.get_height() // 2
        screen.blit(id_surf, (cursor_x, iy))

        cursor_y += level_surf.get_height() + gap

        # Linha 3: tipos
        if type_surfs:
            t_spacing = self._px(6)
            tx = info_x
            for surf, color in type_surfs:
                w = surf.get_width() + self._px(20)
                rect = pygame.Rect(tx, cursor_y, w, type_height)
                pygame.draw.rect(screen, color, rect, border_radius=self._px(8))
                pygame.draw.rect(screen, (255, 255, 255, 100), rect, 1,
                                 border_radius=self._px(8))
                screen.blit(surf, (
                    tx + (w - surf.get_width()) // 2,
                    cursor_y + (type_height - surf.get_height()) // 2,
                ))
                tx += w + t_spacing

    def _render_pokemon_sprite(self, screen, center_x, center_y, target_size):
        """Sprite com animação de brilho e estrelas."""
        sprite = self.pokemon.ui_sprite
        if not sprite:
            return

        ow, oh = sprite.get_width(), sprite.get_height()
        scale = min(target_size / ow, target_size / oh)
        nw, nh = int(ow * scale), int(oh * scale)
        scaled = pygame.transform.scale(sprite, (nw, nh))
        sx = center_x - nw // 2
        sy = center_y - nh // 2

        # Glow pulsante
        glow_radius = max(nw, nh) // 2 + self._px(12)
        pulse = abs(math.sin(self.animation_time * 5)) * 4
        glow_alpha = int(70 + pulse * 4)

        for i in range(2):
            radius = glow_radius - i * 3
            alpha = glow_alpha - i * 15
            if alpha > 0:
                glow = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
                pygame.draw.circle(glow, (*self.colors['success'], alpha),
                                   (radius, radius), radius)
                screen.blit(glow, (center_x - radius, center_y - radius))

        # Fundo circular
        circle_radius = max(nw, nh) // 2 + self._px(6)
        pygame.draw.circle(screen, (*self.colors['bg_light'], 180),
                           (center_x, center_y), circle_radius)
        pygame.draw.circle(screen, (*self.colors['border'], 200),
                           (center_x, center_y), circle_radius, 2)

        screen.blit(scaled, (sx, sy))

        # Estrelas orbitando
        star_time = self.animation_time * 6
        for i in range(5):
            angle = star_time + (i * math.pi * 2 / 5)
            radius = max(nw, nh) // 2 + self._px(18)
            star_x = center_x + math.cos(angle) * radius
            star_y = center_y + math.sin(angle) * radius
            star_size = int(2 + math.sin(self.animation_time * 12 + i) * 1.5)
            pygame.draw.circle(screen, (255, 215, 0),
                               (int(star_x), int(star_y)), max(1, star_size))

    # ---------- Seção Natureza + IVs ---------- #

    def _render_info_section(self, screen, x, y, width):
        section_rect = pygame.Rect(x, y, width, self.info_section_height)
        pygame.draw.rect(screen, (*self.colors['bg_card'], 180), section_rect,
                         border_radius=self._px(12))
        pygame.draw.rect(screen, (*self.colors['border'], 150), section_rect, 1,
                         border_radius=self._px(12))

        pad = self._px(12)
        label_font = self._get_font(11, True)

        # Split: 32% natureza / 68% IVs
        nature_w = int(width * 0.32)
        iv_x = section_rect.x + nature_w + pad
        iv_area_w = section_rect.right - iv_x - pad

        # ---- Natureza ----
        label = label_font.render("NATUREZA", True, self.colors['text_muted'])
        screen.blit(label, (section_rect.x + pad, section_rect.y + self._px(8)))

        nature_name = (self.pokemon.nature.name
                       if hasattr(self.pokemon.nature, 'name')
                       else str(self.pokemon.nature))
        nature_surf = self._get_font(17, True).render(
            nature_name.capitalize(), True, self.colors['accent'])
        screen.blit(nature_surf, (section_rect.x + pad, section_rect.y + self._px(28)))

        # Divisor vertical
        sep_x = section_rect.x + nature_w + pad // 2
        pygame.draw.line(screen, (*self.colors['border'], 120),
                         (sep_x, section_rect.y + self._px(8)),
                         (sep_x, section_rect.bottom - self._px(8)), 1)

        # ---- IVs ----
        iv_label = label_font.render("IVS", True, self.colors['text_muted'])
        screen.blit(iv_label, (iv_x, section_rect.y + self._px(8)))

        if not (hasattr(self.pokemon, 'ivs') and self.pokemon.ivs):
            return

        ivs = self.pokemon.ivs
        stats = [
            ('HP',  ivs.get('hp', 0)),
            ('ATK', ivs.get('attack', 0)),
            ('DEF', ivs.get('defense', 0)),
            ('SpA', ivs.get('special_attack', 0)),
            ('SpD', ivs.get('special_defense', 0)),
            ('SPD', ivs.get('speed', 0)),
        ]

        iv_font = self._get_font(13, True)
        cols = 3
        col_w = iv_area_w // cols
        start_y = section_rect.y + self._px(28)
        row_h = self._px(22)

        for i, (name, value) in enumerate(stats):
            col = i % cols
            row = i // cols
            ix = iv_x + col * col_w
            iy = start_y + row * row_h

            if value >= 31:
                color = self.colors['iv_high']
            elif value >= 20:
                color = self.colors['iv_med']
            else:
                color = self.colors['iv_low']

            # Nome da stat
            name_surf = iv_font.render(name, True, self.colors['text_muted'])
            ny = iy + (row_h - name_surf.get_height()) // 2
            screen.blit(name_surf, (ix, ny))

            # Valor
            val_surf = iv_font.render(f"{value:02d}", True, color)
            vx = ix + self._px(32)
            screen.blit(val_surf, (vx, ny))

            # Mini barra
            bar_x = vx + val_surf.get_width() + self._px(6)
            bar_w = max(self._px(20), col_w - (bar_x - ix) - self._px(6))
            bar_h = self._px(5)
            bar_y = iy + row_h // 2 - bar_h // 2

            pygame.draw.rect(screen, (40, 45, 65), (bar_x, bar_y, bar_w, bar_h),
                             border_radius=self._px(2))
            fill_w = int(bar_w * (value / 31.0))
            if fill_w > 0:
                pygame.draw.rect(screen, color, (bar_x, bar_y, fill_w, bar_h),
                                 border_radius=self._px(2))

    # ---------- Seção de Movimentos ---------- #

    def _render_moves_section(self, screen, x, y, width):
        section_rect = pygame.Rect(x, y, width, self.moves_section_height)
        pygame.draw.rect(screen, (*self.colors['bg_card'], 180), section_rect,
                         border_radius=self._px(12))
        pygame.draw.rect(screen, (*self.colors['border'], 150), section_rect, 1,
                         border_radius=self._px(12))

        pad = self._px(10)

        # Título
        title_font = self._get_font(13, True)
        title = title_font.render("MOVIMENTOS", True, self.colors['primary'])
        screen.blit(title, (section_rect.centerx - title.get_width() // 2,
                            section_rect.y + self._px(6)))

        title_h = title.get_height() + self._px(6)

        if not self.pokemon.moves:
            no_font = self._get_font(12)
            txt = no_font.render("Nenhum ataque conhecido", True, self.colors['text_muted'])
            screen.blit(txt, (section_rect.centerx - txt.get_width() // 2,
                              section_rect.centery - txt.get_height() // 2))
            return

        # Grid 2x2 proporcional
        grid_top = section_rect.y + title_h + self._px(4)
        grid_h = section_rect.bottom - grid_top - pad
        grid_x = section_rect.x + pad
        grid_w = section_rect.width - pad * 2

        spacing = self._px(8)
        slot_w = (grid_w - spacing) // 2
        slot_h = (grid_h - spacing) // 2

        for i, move in enumerate(self.pokemon.moves[:4]):
            row = i // 2
            col = i % 2
            sx = grid_x + col * (slot_w + spacing)
            sy = grid_top + row * (slot_h + spacing)
            self._render_move_slot(screen, sx, sy, slot_w, slot_h, move)

    def _render_move_slot(self, screen, x, y, width, height, move):
        """Slot de movimento individual."""
        type_color = self.type_colors.get(move.type.lower(), (150, 150, 150))

        bg_rect = pygame.Rect(x, y, width, height)
        pygame.draw.rect(screen, type_color, bg_rect, border_radius=self._px(8))
        pygame.draw.rect(screen, (255, 255, 255, 100), bg_rect, 1,
                         border_radius=self._px(8))

        pad = self._px(6)

        # Nome (truncado por largura real)
        name_font = self._get_font(14, True)
        max_name_w = width - self._px(50)  # deixa espaço p/ badge de tipo
        move_name = self._truncate_text(name_font, move.name.upper(), max_name_w)
        name_surf = name_font.render(move_name, True, (255, 255, 255))
        screen.blit(name_surf, (x + pad, y + pad))

        # Badge de tipo (canto superior direito)
        type_font = self._get_font(9, True)
        type_txt = type_font.render(move.type.upper()[:4], True, (255, 255, 255))
        badge_w = type_txt.get_width() + self._px(6)
        badge_h = type_txt.get_height() + self._px(2)
        badge_x = x + width - badge_w - self._px(4)
        badge_y = y + self._px(3)

        badge_surf = pygame.Surface((badge_w, badge_h), pygame.SRCALPHA)
        pygame.draw.rect(badge_surf, (0, 0, 0, 140), (0, 0, badge_w, badge_h),
                         border_radius=self._px(4))
        screen.blit(badge_surf, (badge_x, badge_y))
        screen.blit(type_txt, (
            badge_x + (badge_w - type_txt.get_width()) // 2,
            badge_y + (badge_h - type_txt.get_height()) // 2,
        ))

        # PP
        pp_font = self._get_font(12, True)
        pp_text = f"PP {move.current_pp}/{move.max_pp}"
        pp_ratio = move.current_pp / move.max_pp if move.max_pp > 0 else 0
        if pp_ratio <= 0.25:
            pp_color = self.colors['danger']
        elif pp_ratio <= 0.5:
            pp_color = self.colors['warning']
        else:
            pp_color = (200, 220, 200)

        pp_surf = pp_font.render(pp_text, True, pp_color)
        screen.blit(pp_surf, (
            x + width - pp_surf.get_width() - pad,
            y + height - pp_surf.get_height() - self._px(4),
        ))

    # ---------- Seção de apelido ---------- #

    def _render_name_section(self, screen, x, y, width):
        section_rect = pygame.Rect(x, y, width, self.name_section_height)
        pygame.draw.rect(screen, (*self.colors['bg_card'], 150), section_rect,
                         border_radius=self._px(10))
        pygame.draw.rect(screen, (*self.colors['border'], 120), section_rect, 1,
                         border_radius=self._px(10))

        pad = self._px(12)

        # Pergunta
        info_font = self._get_font(12)
        info = info_font.render("Deseja dar um apelido?", True, self.colors['text_muted'])
        screen.blit(info, (section_rect.x + pad, section_rect.y + self._px(8)))

        # Botão APELIDO
        btn_w = self._px(80)
        btn_h = self._px(30)
        btn_x = section_rect.right - btn_w - pad
        btn_y = section_rect.y + (section_rect.height - btn_h) // 2
        self.name_button_rect = pygame.Rect(btn_x, btn_y, btn_w, btn_h)

        if self.name_button_hovered:
            bg, br = (60, 100, 60), (100, 180, 100)
        else:
            bg, br = (40, 70, 40), (70, 120, 70)

        pygame.draw.rect(screen, bg, self.name_button_rect, border_radius=self._px(8))
        pygame.draw.rect(screen, br, self.name_button_rect, 1, border_radius=self._px(8))

        bf = self._get_font(12, True)
        bt = bf.render("APELIDO", True, (255, 255, 255))
        screen.blit(bt, (
            self.name_button_rect.centerx - bt.get_width() // 2,
            self.name_button_rect.centery - bt.get_height() // 2,
        ))

        # Apelido atual (abaixo da pergunta)
        if self.pokemon.custom_name:
            nf = self._get_font(11)
            nt = nf.render(f"Atual: {self.pokemon.custom_name}", True, self.colors['accent'])
            screen.blit(nt, (section_rect.x + pad, section_rect.y + self._px(30)))

    def _render_naming_section(self, screen, x, y, width):
        section_rect = pygame.Rect(x, y, width, self.name_section_height)
        pygame.draw.rect(screen, (*self.colors['bg_card'], 200), section_rect,
                         border_radius=self._px(10))
        pygame.draw.rect(screen, self.colors['primary'], section_rect, 2,
                         border_radius=self._px(10))

        pad = self._px(10)
        btn_w = self._px(60)
        btn_h = self._px(28)
        btn_gap = self._px(8)

        # Input (ocupa o espaço restante à esquerda dos dois botões)
        right_block = btn_w * 2 + btn_gap + pad * 2
        input_w = max(self._px(80), width - right_block - pad)
        input_h = self._px(32)
        input_x = section_rect.x + pad
        input_y = section_rect.y + (section_rect.height - input_h) // 2
        self.input_rect = pygame.Rect(input_x, input_y, input_w, input_h)

        cursor_visible = (self.input_active and
                          int(self.input_cursor_timer * 2) % 2 == 0)
        border_color = (self.colors['input_active'] if self.input_active
                        else self.colors['input_border'])

        pygame.draw.rect(screen, self.colors['input_bg'], self.input_rect,
                         border_radius=self._px(6))
        pygame.draw.rect(screen, border_color, self.input_rect, 2,
                         border_radius=self._px(6))

        input_font = self._get_font(15)
        display = self.input_text + ("_" if cursor_visible else "")
        # Trunca visualmente se passar da largura
        while input_font.size(display)[0] > input_w - self._px(16) and display:
            display = display[1:]
        text_surf = input_font.render(display, True, self.colors['text'])
        screen.blit(text_surf, (
            input_x + self._px(8),
            input_y + (input_h - text_surf.get_height()) // 2,
        ))

        # Contador
        counter_font = self._get_font(10)
        counter = counter_font.render(
            f"{len(self.input_text)}/{self.max_name_length}", True,
            self.colors['success'] if len(self.input_text) <= self.max_name_length
            else self.colors['danger'])
        screen.blit(counter, (
            input_x + input_w - counter.get_width() - self._px(6),
            input_y + input_h - counter.get_height() - self._px(2),
        ))

        # Botão OK
        btn_y = section_rect.y + (section_rect.height - btn_h) // 2
        ok_x = section_rect.right - btn_w - pad
        self.confirm_name_rect = pygame.Rect(ok_x, btn_y, btn_w, btn_h)

        if self.confirm_name_hovered:
            ok_bg, ok_br = (60, 100, 60), (100, 180, 100)
        else:
            ok_bg, ok_br = (40, 70, 40), (70, 120, 70)

        pygame.draw.rect(screen, ok_bg, self.confirm_name_rect, border_radius=self._px(8))
        pygame.draw.rect(screen, ok_br, self.confirm_name_rect, 1, border_radius=self._px(8))

        bf = self._get_font(12, True)
        ok_txt = bf.render("OK", True, (255, 255, 255))
        screen.blit(ok_txt, (
            self.confirm_name_rect.centerx - ok_txt.get_width() // 2,
            self.confirm_name_rect.centery - ok_txt.get_height() // 2,
        ))

        # Botão PULAR
        skip_x = ok_x - btn_w - btn_gap
        self.skip_button_rect = pygame.Rect(skip_x, btn_y, btn_w, btn_h)

        if self.skip_button_hovered:
            sk_bg, sk_br = (70, 60, 60), (120, 80, 80)
        else:
            sk_bg, sk_br = (50, 40, 40), (80, 60, 60)

        pygame.draw.rect(screen, sk_bg, self.skip_button_rect, border_radius=self._px(8))
        pygame.draw.rect(screen, sk_br, self.skip_button_rect, 1, border_radius=self._px(8))

        sk_txt = bf.render("PULAR", True, (255, 200, 200))
        screen.blit(sk_txt, (
            self.skip_button_rect.centerx - sk_txt.get_width() // 2,
            self.skip_button_rect.centery - sk_txt.get_height() // 2,
        ))

    # ---------- Botão CONTINUAR ---------- #

    def _render_button(self, screen, x, y, width):
        btn_w = self._px(140)
        btn_h = self._px(38)
        btn_x = x + (width - btn_w) // 2
        btn_y = y + (self.button_section_height - btn_h) // 2

        self.button_rect = pygame.Rect(btn_x, btn_y, btn_w, btn_h)

        if self.button_hovered:
            bg, br = (70, 150, 70), (100, 200, 100)
        else:
            bg, br = (40, 100, 40), (70, 150, 70)

        pygame.draw.rect(screen, bg, self.button_rect, border_radius=self._px(12))
        pygame.draw.rect(screen, br, self.button_rect, 2, border_radius=self._px(12))

        font = self._get_font(17, True)
        txt = font.render("CONTINUAR", True, (255, 255, 255))
        screen.blit(txt, (
            self.button_rect.centerx - txt.get_width() // 2,
            self.button_rect.centery - txt.get_height() // 2,
        ))

    # ---------- Mensagem de destino ---------- #

    def _render_status_message(self, screen, viewport):
        viewport_cx = viewport.x + viewport.width // 2

        msg_w = self._px(96)
        msg_h = self._px(28)
        msg_x = viewport_cx - msg_w // 2
        msg_y = viewport.y + viewport.height - msg_h - self._px(14)

        msg_rect = pygame.Rect(msg_x, msg_y, msg_w, msg_h)
        pygame.draw.rect(screen, (*self.colors['bg_dark'], 220), msg_rect,
                         border_radius=self._px(12))
        pygame.draw.rect(screen, self.colors['border'], msg_rect, 1,
                         border_radius=self._px(12))

        font = self._get_font(13, True)
        if self.is_to_team:
            txt, color = "TIME", self.colors['success']
        else:
            txt, color = "BOX", self.colors['warning']

        surf = font.render(txt, True, color)
        screen.blit(surf, (
            msg_rect.centerx - surf.get_width() // 2,
            msg_rect.centery - surf.get_height() // 2,
        ))