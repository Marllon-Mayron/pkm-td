# src/scenes/game_scene/components/overlays/capture_overlay.py

import pygame
import math
from .base_overlay import BaseOverlay

_FONT_CACHE = {}


class CaptureOverlay(BaseOverlay):
    """Overlay exibido quando um Pokémon é capturado - COM OPÇÃO DE APELIDO"""

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

        # Dimensões base
        self.modal_width = 0
        self.modal_height = 0
        self.modal_padding = 25

        # Alturas das seções (otimizadas)
        self.title_height = 55
        self.pokemon_section_height = 210
        self.info_section_height = 95  # Reduzido (Natureza + IVs compactos)
        self.moves_section_height = 140
        self.name_section_height = 55
        self.button_section_height = 65
        self.section_spacing = 8

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

    def _recalculate_dimensions(self):
        """Recalcula dimensões baseado no tamanho da tela atual"""
        screen_width = self.game_scene.screen_manager.window_width
        screen_height = self.game_scene.screen_manager.window_height

        self.modal_width = min(int(screen_width * 0.7), 800)
        self.modal_height = min(int(screen_height * 0.82), 650)
        self.modal_width = max(self.modal_width, 650)
        self.modal_height = max(self.modal_height, 580)
        self.modal_padding = max(20, int(self.modal_width * 0.04))

    def _get_font(self, size, bold=False):
        """Obtém fonte do cache"""
        key = (size, bold)
        if key not in _FONT_CACHE:
            font = pygame.font.Font(None, size)
            if bold:
                font.set_bold(True)
            _FONT_CACHE[key] = font
        return _FONT_CACHE[key]

    def handle_event(self, event):
        """Processa eventos"""
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
            if event.key == pygame.K_ESCAPE or event.key == pygame.K_RETURN:
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
        except:
            pass

    def close(self):
        self.active = False
        self.game_scene.close_capture_overlay()

    def render(self, screen):
        if not self.active:
            return

        self._recalculate_dimensions()

        viewport = self.get_viewport_rect()

        # Fundo escuro
        overlay = pygame.Surface((viewport.width, viewport.height))
        overlay.set_alpha(200)
        overlay.fill((0, 0, 0))
        screen.blit(overlay, (viewport.x, viewport.y))

        # Centraliza o modal
        modal_x = viewport.x + (viewport.width - self.modal_width) // 2
        modal_y = viewport.y + (viewport.height - self.modal_height) // 2
        modal_rect = pygame.Rect(modal_x, modal_y, self.modal_width, self.modal_height)

        # Fundo e borda
        self._render_modal_background(screen, modal_rect)
        pygame.draw.rect(screen, self.colors['primary'], modal_rect, 3, border_radius=20)
        pygame.draw.rect(screen, self.colors['accent'], modal_rect.inflate(-6, -6), 1, border_radius=18)

        # Botão fechar
        self._render_close_button(screen, modal_rect)

        # Área de conteúdo
        content_rect = pygame.Rect(
            modal_rect.x + self.modal_padding,
            modal_rect.y + self.modal_padding,
            modal_rect.width - (self.modal_padding * 2),
            modal_rect.height - (self.modal_padding * 2)
        )

        # Calcula posições Y sequenciais
        current_y = content_rect.y

        # Título
        self._render_title(screen, content_rect.x, current_y, content_rect.width)
        current_y += self.title_height + self.section_spacing

        # Pokémon
        self._render_pokemon_section(screen, content_rect.x, current_y, content_rect.width)
        current_y += self.pokemon_section_height + self.section_spacing

        # Informações (Natureza + IVs compactos)
        self._render_info_section(screen, content_rect.x, current_y, content_rect.width)
        current_y += self.info_section_height + self.section_spacing

        # Moves
        self._render_moves_section(screen, content_rect.x, current_y, content_rect.width)
        current_y += self.moves_section_height + self.section_spacing

        # Apelido
        if self.naming_mode:
            self._render_naming_section(screen, content_rect.x, current_y, content_rect.width)
        else:
            self._render_name_section(screen, content_rect.x, current_y, content_rect.width)
        current_y += self.name_section_height + self.section_spacing

        # Botão
        self._render_button(screen, content_rect.x, current_y, content_rect.width)

        # Mensagem de destino
        self._render_status_message(screen, viewport)

    def _render_modal_background(self, screen, modal_rect):
        """Fundo do modal"""
        bg_rect = modal_rect.inflate(-2, -2)
        pygame.draw.rect(screen, self.colors['bg_dark'], bg_rect, border_radius=20)

    def _render_close_button(self, screen, modal_rect):
        """Botão X"""
        size = 30
        x = modal_rect.right - size - 10
        y = modal_rect.y + 10
        self.close_button_rect = pygame.Rect(x, y, size, size)

        if self.close_button_hovered:
            bg_color = (*self.colors['danger'], 120)
            border_color = self.colors['danger']
        else:
            bg_color = (*self.colors['bg_light'], 180)
            border_color = self.colors['border']

        pygame.draw.rect(screen, bg_color, self.close_button_rect, border_radius=8)
        pygame.draw.rect(screen, border_color, self.close_button_rect, 1, border_radius=8)

        font = self._get_font(22, True)
        x_text = font.render("X", True, self.colors['text_dim'])
        text_x = x + (size - x_text.get_width()) // 2
        text_y = y + (size - x_text.get_height()) // 2
        screen.blit(x_text, (text_x, text_y))

    def _render_title(self, screen, x, y, width):
        """Título"""
        font = self._get_font(30, True)
        title = font.render("CAPTURADO", True, self.colors['success'])
        title_x = x + (width - title.get_width()) // 2
        screen.blit(title, (title_x, y))

        line_y = y + title.get_height() + 4
        line_width = 140
        line_x = x + (width - line_width) // 2
        pygame.draw.line(screen, self.colors['success'], (line_x, line_y), (line_x + line_width, line_y), 2)

    def _render_pokemon_section(self, screen, x, y, width):
        """Seção do Pokémon"""
        section_rect = pygame.Rect(x, y, width, self.pokemon_section_height)

        pygame.draw.rect(screen, (*self.colors['bg_card'], 200), section_rect, border_radius=15)
        pygame.draw.rect(screen, (*self.colors['border'], 150), section_rect, 2, border_radius=15)

        center_x = section_rect.centerx

        # Sprite
        sprite_size = 90
        self._render_pokemon_sprite(screen, center_x, section_rect.y + 50, sprite_size, section_rect)

        # Informações abaixo do sprite
        info_y = section_rect.y + 105

        # Espécie e Level e Gênero
        species_font = self._get_font(22, True)
        level_font = self._get_font(18)

        species_text = self.pokemon.name.upper()
        species_surf = species_font.render(species_text, True, self.colors['accent'])

        level_text = f"Lv.{self.pokemon.level}"
        level_surf = level_font.render(level_text, True, self.colors['text_dim'])

        # Gênero como texto
        if hasattr(self.pokemon, 'gender'):
            if self.pokemon.gender == "male":
                gender_text = "MACHO"
                gender_color = self.colors['gender_male']
            elif self.pokemon.gender == "female":
                gender_text = "FÊMEA"
                gender_color = self.colors['gender_female']
            else:
                gender_text = ""
                gender_color = self.colors['text_muted']
        else:
            gender_text = ""
            gender_color = self.colors['text_muted']

        total_width = species_surf.get_width() + 10 + level_surf.get_width()

        if gender_text:
            gender_font = self._get_font(14, True)
            gender_surf = gender_font.render(gender_text, True, gender_color)
            total_width += 12 + gender_surf.get_width()

        start_x = center_x - total_width // 2

        screen.blit(species_surf, (start_x, info_y))
        level_y = info_y + (species_surf.get_height() - level_surf.get_height()) // 2
        screen.blit(level_surf, (start_x + species_surf.get_width() + 10, level_y))

        if gender_text:
            gender_y = info_y + (species_surf.get_height() - gender_surf.get_height()) // 2
            screen.blit(gender_surf, (start_x + species_surf.get_width() + 10 + level_surf.get_width() + 12, gender_y))

        # ID
        id_font = self._get_font(11)
        id_text = f"#{self.pokemon.id:04d}"
        id_surf = id_font.render(id_text, True, self.colors['text_muted'])
        id_x = center_x - id_surf.get_width() // 2
        screen.blit(id_surf, (id_x, info_y + species_surf.get_height() + 4))

        # Tipos (acima do sprite)
        types_y = section_rect.y - 6
        self._render_types(screen, center_x, types_y, self.pokemon.types)

    def _render_pokemon_sprite(self, screen, center_x, center_y, target_size, section_rect):
        """Sprite com animação"""
        sprite_to_use = self.pokemon.ui_sprite

        if sprite_to_use:
            orig_w, orig_h = sprite_to_use.get_width(), sprite_to_use.get_height()
            scale = min(target_size / orig_w, target_size / orig_h)
            new_w = int(orig_w * scale)
            new_h = int(orig_h * scale)

            scaled_sprite = pygame.transform.scale(sprite_to_use, (new_w, new_h))

            sprite_x = center_x - new_w // 2
            sprite_y = center_y - new_h // 2

            # Efeito de brilho
            glow_radius = max(new_w, new_h) // 2 + 12
            pulse = abs(math.sin(self.animation_time * 5)) * 4
            glow_alpha = int(70 + pulse * 4)

            for i in range(2):
                radius = glow_radius - i * 3
                alpha = glow_alpha - i * 15
                if alpha > 0:
                    glow_surface = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
                    pygame.draw.circle(glow_surface, (*self.colors['success'], alpha),
                                       (radius, radius), radius)
                    screen.blit(glow_surface, (center_x - radius, center_y - radius))

            # Fundo circular
            circle_radius = max(new_w, new_h) // 2 + 6
            pygame.draw.circle(screen, (*self.colors['bg_light'], 180), (center_x, center_y), circle_radius)
            pygame.draw.circle(screen, (*self.colors['border'], 200), (center_x, center_y), circle_radius, 2)

            screen.blit(scaled_sprite, (sprite_x, sprite_y))

            # Estrelas
            star_time = self.animation_time * 6
            for i in range(5):
                angle = star_time + (i * math.pi * 2 / 5)
                radius = max(new_w, new_h) // 2 + 18
                star_x = center_x + math.cos(angle) * radius
                star_y = center_y + math.sin(angle) * radius
                star_size = int(2 + math.sin(self.animation_time * 12 + i) * 1.5)
                pygame.draw.circle(screen, (255, 215, 0), (int(star_x), int(star_y)), star_size)

    def _render_types(self, screen, center_x, y, types):
        """Renderiza os tipos"""
        if not types:
            return

        type_font = self._get_font(11, True)
        type_spacing = 6
        type_height = 24

        type_surfs = []
        type_colors_list = []
        type_widths = []

        for t in types:
            type_name = t.capitalize()
            color = self.type_colors.get(t.lower(), (150, 150, 150))
            surf = type_font.render(type_name, True, (255, 255, 255))
            width = surf.get_width() + 18
            type_surfs.append(surf)
            type_colors_list.append(color)
            type_widths.append(width)

        total_width = sum(type_widths) + (len(types) - 1) * type_spacing
        start_x = center_x - total_width // 2

        current_x = start_x
        for surf, color, width in zip(type_surfs, type_colors_list, type_widths):
            bg_rect = pygame.Rect(current_x, y, width, type_height)
            pygame.draw.rect(screen, color, bg_rect, border_radius=8)
            pygame.draw.rect(screen, (255, 255, 255, 100), bg_rect, 1, border_radius=8)

            text_x = current_x + (width - surf.get_width()) // 2
            text_y = y + (type_height - surf.get_height()) // 2
            screen.blit(surf, (text_x, text_y))
            current_x += width + type_spacing

    def _render_info_section(self, screen, x, y, width):
        """Seção Natureza + IVs (compacta)"""
        section_rect = pygame.Rect(x, y, width, self.info_section_height)

        pygame.draw.rect(screen, (*self.colors['bg_card'], 180), section_rect, border_radius=12)
        pygame.draw.rect(screen, (*self.colors['border'], 150), section_rect, 1, border_radius=12)

        # ===== NATUREZA (linha única) =====
        nature_label = self._get_font(11).render("NATUREZA", True, self.colors['text_muted'])
        screen.blit(nature_label, (section_rect.x + 12, section_rect.y + 8))

        nature_name = self.pokemon.nature if hasattr(self.pokemon.nature, 'name') else str(self.pokemon.nature)
        nature_surf = self._get_font(16, True).render(nature_name.capitalize(), True, self.colors['accent'])
        screen.blit(nature_surf, (section_rect.x + 12, section_rect.y + 28))

        # ===== IVS (compactos em linha) =====
        iv_label = self._get_font(11).render("IVS", True, self.colors['text_muted'])
        screen.blit(iv_label, (section_rect.x + section_rect.width // 2 + 10, section_rect.y + 8))

        if hasattr(self.pokemon, 'ivs') and self.pokemon.ivs:
            ivs = self.pokemon.ivs
            iv_font = self._get_font(13, True)

            # Lista de stats
            iv_stats = [
                ('HP', ivs.get('hp', 0)),
                ('ATK', ivs.get('attack', 0)),
                ('DEF', ivs.get('defense', 0)),
                ('SpA', ivs.get('special_attack', 0)),
                ('SpD', ivs.get('special_defense', 0)),
                ('SPD', ivs.get('speed', 0))
            ]

            start_x = section_rect.x + section_rect.width // 2 + 10
            current_x = start_x
            current_y = section_rect.y + 28

            for i, (name, value) in enumerate(iv_stats):
                # Cor baseada no valor
                if value >= 31:
                    color = self.colors['iv_high']
                elif value >= 20:
                    color = self.colors['iv_med']
                else:
                    color = self.colors['iv_low']

                iv_text = f"{name}:{value:02d}"
                iv_surf = iv_font.render(iv_text, True, color)

                # Posiciona em 2 linhas (3 colunas cada)
                if i < 3:
                    screen.blit(iv_surf, (current_x, current_y))
                    current_x += 65
                else:
                    if i == 3:
                        current_x = start_x
                        current_y += 22
                    screen.blit(iv_surf, (current_x, current_y))
                    current_x += 65

    def _render_moves_section(self, screen, x, y, width):
        """Seção de Moves"""
        section_rect = pygame.Rect(x, y, width, self.moves_section_height)

        pygame.draw.rect(screen, (*self.colors['bg_card'], 180), section_rect, border_radius=12)
        pygame.draw.rect(screen, (*self.colors['border'], 150), section_rect, 1, border_radius=12)

        # Título
        title_font = self._get_font(13, True)
        title = title_font.render("MOVIMENTOS", True, self.colors['primary'])
        title_x = section_rect.centerx - title.get_width() // 2
        screen.blit(title, (title_x, section_rect.y + 6))

        if not self.pokemon.moves:
            no_font = self._get_font(12)
            no_moves = no_font.render("Nenhum ataque conhecido", True, self.colors['text_muted'])
            no_x = section_rect.centerx - no_moves.get_width() // 2
            no_y = section_rect.centery - no_moves.get_height() // 2
            screen.blit(no_moves, (no_x, no_y))
            return

        # Grid 2x2
        grid_x = section_rect.x + 10
        grid_y = section_rect.y + 28
        slot_width = (section_rect.width - 25) // 2
        slot_height = 48
        slot_spacing = 8

        for i, move in enumerate(self.pokemon.moves[:4]):
            row = i // 2
            col = i % 2
            slot_x = grid_x + col * (slot_width + slot_spacing)
            slot_y = grid_y + row * (slot_height + slot_spacing)

            if slot_y + slot_height < section_rect.bottom - 4:
                self._render_move_slot(screen, slot_x, slot_y, slot_width, slot_height, move)

    def _render_move_slot(self, screen, x, y, width, height, move):
        """Slot de movimento - com PP em fonte maior"""
        type_color = self.type_colors.get(move.type.lower(), (150, 150, 150))

        bg_rect = pygame.Rect(x, y, width, height)
        pygame.draw.rect(screen, type_color, bg_rect, border_radius=8)
        pygame.draw.rect(screen, (255, 255, 255, 100), bg_rect, 1, border_radius=8)

        # Nome do move
        name_font = self._get_font(14, True)
        move_name = move.name.upper()
        max_len = 11 if width < 200 else 14
        if len(move_name) > max_len:
            move_name = move_name[:max_len] + "..."

        name_surf = name_font.render(move_name, True, (255, 255, 255))
        text_x = x + (width - name_surf.get_width()) // 2
        text_y = y + 6
        screen.blit(name_surf, (text_x, text_y))

        # Tipo (canto superior direito)
        type_font = self._get_font(9, True)
        type_name = move.type.upper()[:4]
        type_surf = type_font.render(type_name, True, (255, 255, 255))

        type_bg_w = type_surf.get_width() + 5
        type_bg_h = type_surf.get_height() + 2
        type_bg_x = x + width - type_bg_w - 4
        type_bg_y = y + 3

        pygame.draw.rect(screen, (0, 0, 0, 140), (type_bg_x, type_bg_y, type_bg_w, type_bg_h), border_radius=4)
        type_x = type_bg_x + (type_bg_w - type_surf.get_width()) // 2
        type_y = type_bg_y + (type_bg_h - type_surf.get_height()) // 2
        screen.blit(type_surf, (type_x, type_y))

        # PP (fonte maior e mais destacada)
        pp_font = self._get_font(12, True)  # Aumentado de 10 para 12 e bold
        pp_text = f"PP {move.current_pp}/{move.max_pp}"

        # Cor do PP (amarelo se estiver baixo)
        pp_ratio = move.current_pp / move.max_pp if move.max_pp > 0 else 0
        if pp_ratio <= 0.25:
            pp_color = self.colors['danger']
        elif pp_ratio <= 0.5:
            pp_color = self.colors['warning']
        else:
            pp_color = (200, 220, 200)

        pp_surf = pp_font.render(pp_text, True, pp_color)
        pp_x = x + width - pp_surf.get_width() - 5
        pp_y = y + height - pp_surf.get_height() - 4
        screen.blit(pp_surf, (pp_x, pp_y))

    def _render_name_section(self, screen, x, y, width):
        """Seção para definir apelido"""
        section_rect = pygame.Rect(x, y, width, self.name_section_height)

        pygame.draw.rect(screen, (*self.colors['bg_card'], 150), section_rect, border_radius=10)
        pygame.draw.rect(screen, (*self.colors['border'], 120), section_rect, 1, border_radius=10)

        info_font = self._get_font(12)
        info_text = info_font.render("Deseja dar um apelido?", True, self.colors['text_muted'])
        screen.blit(info_text, (section_rect.x + 12, section_rect.y + 10))

        # Botão
        button_width = 75
        button_height = 30
        button_x = section_rect.right - button_width - 12
        button_y = section_rect.y + (section_rect.height - button_height) // 2
        self.name_button_rect = pygame.Rect(button_x, button_y, button_width, button_height)

        if self.name_button_hovered:
            button_color = (60, 100, 60)
            border_color = (100, 180, 100)
        else:
            button_color = (40, 70, 40)
            border_color = (70, 120, 70)

        pygame.draw.rect(screen, button_color, self.name_button_rect, border_radius=8)
        pygame.draw.rect(screen, border_color, self.name_button_rect, 1, border_radius=8)

        button_font = self._get_font(12, True)
        button_text = button_font.render("APELIDO", True, (255, 255, 255))
        text_x = self.name_button_rect.centerx - button_text.get_width() // 2
        text_y = self.name_button_rect.centery - button_text.get_height() // 2
        screen.blit(button_text, (text_x, text_y))

        # Apelido atual
        if self.pokemon.custom_name:
            nick_font = self._get_font(11)
            nick_text = nick_font.render(f"Atual: {self.pokemon.custom_name}", True, self.colors['accent'])
            screen.blit(nick_text, (section_rect.x + 12, section_rect.y + 32))

    def _render_naming_section(self, screen, x, y, width):
        """Seção de input para o apelido"""
        section_rect = pygame.Rect(x, y, width, self.name_section_height)

        pygame.draw.rect(screen, (*self.colors['bg_card'], 200), section_rect, border_radius=10)
        pygame.draw.rect(screen, self.colors['primary'], section_rect, 2, border_radius=10)

        # Input
        input_width = width - 170
        input_height = 32
        input_x = section_rect.x + 10
        input_y = section_rect.y + (section_rect.height - input_height) // 2
        self.input_rect = pygame.Rect(input_x, input_y, input_width, input_height)

        if self.input_active:
            border_color = self.colors['input_active']
            cursor_visible = int(self.input_cursor_timer * 2) % 2 == 0
        else:
            border_color = self.colors['input_border']
            cursor_visible = False

        pygame.draw.rect(screen, self.colors['input_bg'], self.input_rect, border_radius=6)
        pygame.draw.rect(screen, border_color, self.input_rect, 2, border_radius=6)

        # Texto
        input_font = self._get_font(15)
        display_text = self.input_text
        if self.input_active and cursor_visible:
            display_text += "_"

        text_surf = input_font.render(display_text, True, self.colors['text'])
        text_x = input_x + 8
        text_y = input_y + (input_height - text_surf.get_height()) // 2
        screen.blit(text_surf, (text_x, text_y))

        # Contador
        counter_font = self._get_font(10)
        counter_text = f"{len(self.input_text)}/{self.max_name_length}"
        counter_color = self.colors['success'] if len(self.input_text) <= self.max_name_length else self.colors[
            'danger']
        counter_surf = counter_font.render(counter_text, True, counter_color)
        screen.blit(counter_surf, (input_x + input_width - counter_surf.get_width() - 8, input_y + input_height - 14))

        # Botões
        btn_width = 60
        btn_height = 28
        btn_y = section_rect.y + (section_rect.height - btn_height) // 2

        # Confirmar
        confirm_x = section_rect.right - btn_width - 10
        self.confirm_name_rect = pygame.Rect(confirm_x, btn_y, btn_width, btn_height)

        if self.confirm_name_hovered:
            confirm_color = (60, 100, 60)
            confirm_border = (100, 180, 100)
        else:
            confirm_color = (40, 70, 40)
            confirm_border = (70, 120, 70)

        pygame.draw.rect(screen, confirm_color, self.confirm_name_rect, border_radius=8)
        pygame.draw.rect(screen, confirm_border, self.confirm_name_rect, 1, border_radius=8)

        confirm_font = self._get_font(12, True)
        confirm_text = confirm_font.render("OK", True, (255, 255, 255))
        text_x = self.confirm_name_rect.centerx - confirm_text.get_width() // 2
        text_y = self.confirm_name_rect.centery - confirm_text.get_height() // 2
        screen.blit(confirm_text, (text_x, text_y))

        # Pular
        skip_x = confirm_x - btn_width - 8
        self.skip_button_rect = pygame.Rect(skip_x, btn_y, btn_width, btn_height)

        if self.skip_button_hovered:
            skip_color = (70, 60, 60)
            skip_border = (120, 80, 80)
        else:
            skip_color = (50, 40, 40)
            skip_border = (80, 60, 60)

        pygame.draw.rect(screen, skip_color, self.skip_button_rect, border_radius=8)
        pygame.draw.rect(screen, skip_border, self.skip_button_rect, 1, border_radius=8)

        skip_font = self._get_font(12, True)
        skip_text = skip_font.render("PULAR", True, (255, 200, 200))
        text_x = self.skip_button_rect.centerx - skip_text.get_width() // 2
        text_y = self.skip_button_rect.centery - skip_text.get_height() // 2
        screen.blit(skip_text, (text_x, text_y))

    def _render_button(self, screen, x, y, width):
        """Botão CONTINUAR"""
        button_width = 130
        button_height = 38
        button_x = x + (width - button_width) // 2
        button_y = y + (self.button_section_height - button_height) // 2

        self.button_rect = pygame.Rect(button_x, button_y, button_width, button_height)

        if self.button_hovered:
            button_color = (70, 150, 70)
            border_color = (100, 200, 100)
        else:
            button_color = (40, 100, 40)
            border_color = (70, 150, 70)

        pygame.draw.rect(screen, button_color, self.button_rect, border_radius=12)
        pygame.draw.rect(screen, border_color, self.button_rect, 2, border_radius=12)

        font = self._get_font(17, True)
        button_text = font.render("CONTINUAR", True, (255, 255, 255))
        text_x = self.button_rect.centerx - button_text.get_width() // 2
        text_y = self.button_rect.centery - button_text.get_height() // 2
        screen.blit(button_text, (text_x, text_y))

    def _render_status_message(self, screen, viewport):
        """Mensagem de destino"""
        viewport_center_x = viewport.x + viewport.width // 2

        msg_width = 90
        msg_height = 28
        msg_x = viewport_center_x - msg_width // 2
        msg_y = viewport.y + viewport.height - 45

        msg_rect = pygame.Rect(msg_x, msg_y, msg_width, msg_height)

        pygame.draw.rect(screen, (*self.colors['bg_dark'], 220), msg_rect, border_radius=12)
        pygame.draw.rect(screen, self.colors['border'], msg_rect, 1, border_radius=12)

        font = self._get_font(13, True)

        if self.is_to_team:
            text = "TIME"
            color = self.colors['success']
        else:
            text = "BOX"
            color = self.colors['warning']

        status_surf = font.render(text, True, color)
        text_x = msg_rect.centerx - status_surf.get_width() // 2
        text_y = msg_rect.centery - status_surf.get_height() // 2
        screen.blit(status_surf, (text_x, text_y))