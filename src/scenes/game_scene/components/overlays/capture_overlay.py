# src/scenes/game_scene/components/overlays/capture_overlay.py

import pygame
import math
from .base_overlay import BaseOverlay

_FONT_CACHE = {}


class CaptureOverlay(BaseOverlay):
    """Overlay exibido quando um Pokémon é capturado - versão simplificada"""

    def __init__(self, game_scene, pokemon, is_to_team=True):
        super().__init__(game_scene)
        self.pokemon = pokemon
        self.is_to_team = is_to_team
        self.animation_time = 0
        self.music_played = False

        # Botões
        self.button_rect = None
        self.button_hovered = False
        self.close_button_rect = None
        self.close_button_hovered = False

        # Pausa o jogo
        self.game_scene.game_paused = True
        self.game_scene.paused = True
        if hasattr(self.game_scene, 'wave_manager'):
            self.game_scene.wave_manager.paused = True

        # Dimensões do modal (FIXAS)
        self.modal_width = 750
        self.modal_height = 620
        self.modal_padding = 35

        # Dimensões internas fixas
        self.section_spacing = 15
        self.title_height = 50
        self.pokemon_section_height = 190
        self.info_section_height = 100
        self.moves_section_height = 160
        self.button_section_height = 60

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

        elif event.type == pygame.MOUSEMOTION:
            if self.close_button_rect:
                self.close_button_hovered = self.close_button_rect.collidepoint(event.pos)
            if self.button_rect:
                self.button_hovered = self.button_rect.collidepoint(event.pos)

        return False

    def update(self, dt):
        """Atualiza animações"""
        self.animation_time += dt
        if not self.music_played:
            self._play_capture_sound()
            self.music_played = True

    def _play_capture_sound(self):
        try:
            from managers.sounds.sound_manager import sound_manager
            sound_manager.play_capture_sound()
        except:
            pass

    def close(self):
        self.active = False
        self.game_scene.close_capture_overlay()

    def render(self, screen):
        if not self.active:
            return

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

        # Fundo do modal
        self._render_modal_background(screen, modal_rect)

        # Borda
        pygame.draw.rect(screen, self.colors['primary'], modal_rect, 3, border_radius=20)
        pygame.draw.rect(screen, self.colors['accent'], modal_rect.inflate(-6, -6), 1, border_radius=18)

        # Botão fechar (X)
        self._render_close_button(screen, modal_rect)

        # ===== CONTEÚDO COM LIMITES =====
        content_rect = pygame.Rect(
            modal_rect.x + self.modal_padding,
            modal_rect.y + self.modal_padding,
            modal_rect.width - (self.modal_padding * 2),
            modal_rect.height - (self.modal_padding * 2)
        )

        # Calcular posições Y com espaçamento fixo
        y_positions = self._calculate_y_positions(content_rect)

        # Título
        self._render_title(screen, modal_rect, y_positions['title'])

        # Área do Pokémon
        pokemon_rect = pygame.Rect(
            content_rect.x,
            y_positions['pokemon'],
            content_rect.width,
            self.pokemon_section_height
        )
        self._render_pokemon_section(screen, pokemon_rect)

        # Área de Informações
        info_rect = pygame.Rect(
            content_rect.x,
            y_positions['info'],
            content_rect.width,
            self.info_section_height
        )
        self._render_info_section(screen, info_rect)

        # Área de Moves
        moves_rect = pygame.Rect(
            content_rect.x,
            y_positions['moves'],
            content_rect.width,
            self.moves_section_height
        )
        self._render_moves_section(screen, moves_rect)

        # Botão
        button_rect = pygame.Rect(
            content_rect.x,
            y_positions['button'],
            content_rect.width,
            self.button_section_height
        )
        self._render_button(screen, button_rect)

        # Mensagem de status (FORA do modal)
        self._render_status_message(screen, viewport)


    def _calculate_y_positions(self, content_rect):
        """Calcula as posições Y de cada seção"""
        current_y = content_rect.y

        # Título
        title_y = current_y
        current_y += self.title_height + self.section_spacing

        # Pokémon
        pokemon_y = current_y
        current_y += self.pokemon_section_height + self.section_spacing

        # Info
        info_y = current_y
        current_y += self.info_section_height + self.section_spacing

        # Moves
        moves_y = current_y
        current_y += self.moves_section_height + self.section_spacing

        # Button
        button_y = current_y

        return {
            'title': title_y,
            'pokemon': pokemon_y,
            'info': info_y,
            'moves': moves_y,
            'button': button_y
        }

    def _render_modal_background(self, screen, modal_rect):
        """Fundo do modal"""
        bg_rect = modal_rect.inflate(-2, -2)
        pygame.draw.rect(screen, self.colors['bg_dark'], bg_rect, border_radius=20)

        # Efeito de gradiente
        for i in range(6):
            alpha = 40 - i * 6
            if alpha > 0:
                inner_rect = modal_rect.inflate(-20 - i * 3, -20 - i * 3)
                pygame.draw.rect(screen, (*self.colors['bg_medium'], alpha), inner_rect, border_radius=18)

    def _render_close_button(self, screen, modal_rect):
        """Botão X"""
        size = 30
        x = modal_rect.right - size - 15
        y = modal_rect.y + 15
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
        x_text = font.render("✕", True, self.colors['text_dim'])
        text_x = x + (size - x_text.get_width()) // 2
        text_y = y + (size - x_text.get_height()) // 2
        screen.blit(x_text, (text_x, text_y))

    def _render_title(self, screen, modal_rect, y):
        """Título"""
        font = self._get_font(36, True)
        title = font.render("CAPTURADO!", True, self.colors['success'])
        title_x = modal_rect.centerx - title.get_width() // 2
        screen.blit(title, (title_x, y))

        # Linha decorativa
        line_y = y + title.get_height() + 5
        line_width = 180
        line_x = modal_rect.centerx - line_width // 2
        pygame.draw.line(screen, self.colors['success'], (line_x, line_y), (line_x + line_width, line_y), 2)

    def _render_pokemon_section(self, screen, section_rect):
        """Seção do Pokémon - com tipos fora da div e informações mais abaixo"""
        # Fundo decorado
        bg_rect = section_rect.inflate(-5, -5)
        pygame.draw.rect(screen, (*self.colors['bg_card'], 200), bg_rect, border_radius=20)
        pygame.draw.rect(screen, (*self.colors['border'], 150), bg_rect, 2, border_radius=20)

        # Centraliza o conteúdo
        center_x = section_rect.centerx

        # ===== SPRITE (mais acima) =====
        sprite_y = section_rect.y + 15
        self._render_pokemon_sprite(screen, center_x, sprite_y + 50, section_rect)

        # ===== INFORMAÇÕES MAIS ABAIXO =====
        info_y = sprite_y + 125  # Aumentado de 115 para 125 para descer mais

        # Nome e Level
        font_name = self._get_font(30, True)
        font_level = self._get_font(26)

        name_text = self.pokemon.name.upper()
        name_surf = font_name.render(name_text, True, self.colors['accent'])

        level_text = f"Lv.{self.pokemon.level}"
        level_surf = font_level.render(level_text, True, self.colors['text_dim'])

        total_width = name_surf.get_width() + 15 + level_surf.get_width()
        start_x = center_x - total_width // 2
        start_x = max(section_rect.x + 10, min(start_x, section_rect.right - total_width - 10))

        screen.blit(name_surf, (start_x, info_y))

        level_y = info_y + (name_surf.get_height() - level_surf.get_height()) // 2
        screen.blit(level_surf, (start_x + name_surf.get_width() + 15, level_y))

        # ID (mais abaixo ainda)
        font_id = self._get_font(15)
        id_text = f"#{self.pokemon.id:04d}"
        id_surf = font_id.render(id_text, True, self.colors['text_muted'])
        id_x = center_x - id_surf.get_width() // 2
        id_x = max(section_rect.x + 10, min(id_x, section_rect.right - id_surf.get_width() - 10))
        screen.blit(id_surf, (id_x, info_y + name_surf.get_height() + 8))  # Aumentado de 3 para 8

        # ===== TIPOS FORA DA DIV DO SPRITE (acima) =====
        types_y = section_rect.y - 5
        self._render_types_outside(screen, center_x, types_y, self.pokemon.types)

    def _render_pokemon_sprite(self, screen, center_x, center_y, section_rect):
        """Sprite com destaque"""
        sprite_to_use = self.pokemon.ui_sprite

        if sprite_to_use:
            target_size = 100
            orig_w, orig_h = sprite_to_use.get_width(), sprite_to_use.get_height()
            scale = min(target_size / orig_w, target_size / orig_h)
            new_w = int(orig_w * scale)
            new_h = int(orig_h * scale)

            scaled_sprite = pygame.transform.scale(sprite_to_use, (new_w, new_h))

            sprite_x = center_x - new_w // 2
            sprite_y = center_y - new_h // 2

            # Garante que não sai da section
            sprite_x = max(section_rect.x + 10, min(sprite_x, section_rect.right - new_w - 10))
            sprite_y = max(section_rect.y + 10, min(sprite_y, section_rect.bottom - new_h - 50))

            # Efeito de brilho
            glow_radius = max(new_w, new_h) // 2 + 18
            pulse = abs(math.sin(self.animation_time * 5)) * 5
            glow_alpha = int(90 + pulse * 4)

            for i in range(2):
                radius = glow_radius - i * 4
                alpha = glow_alpha - i * 15
                if alpha > 0:
                    glow_surface = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
                    pygame.draw.circle(glow_surface, (*self.colors['success'], alpha),
                                       (radius, radius), radius)
                    screen.blit(glow_surface, (center_x - radius, center_y - radius))

            # Fundo circular
            circle_radius = max(new_w, new_h) // 2 + 10
            pygame.draw.circle(screen, (*self.colors['bg_light'], 180), (center_x, center_y), circle_radius)
            pygame.draw.circle(screen, (*self.colors['border'], 200), (center_x, center_y), circle_radius, 2)

            screen.blit(scaled_sprite, (sprite_x, sprite_y))

            # Estrelas
            star_time = self.animation_time * 6
            for i in range(6):
                angle = star_time + (i * math.pi * 2 / 6)
                radius = max(new_w, new_h) // 2 + 20
                star_x = center_x + math.cos(angle) * radius
                star_y = center_y + math.sin(angle) * radius

                star_size = int(2 + math.sin(self.animation_time * 12 + i) * 1.5)
                star_color = (255, 215, 0)
                pygame.draw.circle(screen, star_color, (int(star_x), int(star_y)), star_size)

    def _render_types_outside(self, screen, center_x, y, types):
        """Renderiza os tipos FORA da div do sprite (acima)"""
        if not types:
            return

        type_font = self._get_font(14, True)
        type_spacing = 10
        type_height = 30

        # Calcula largura total
        type_surfs = []
        type_colors_list = []
        type_widths = []

        for t in types:
            type_name = t.capitalize()
            color = self.type_colors.get(t.lower(), (150, 150, 150))
            surf = type_font.render(type_name, True, (255, 255, 255))
            width = surf.get_width() + 28
            type_surfs.append(surf)
            type_colors_list.append(color)
            type_widths.append(width)

        total_width = sum(type_widths) + (len(types) - 1) * type_spacing
        start_x = center_x - total_width // 2

        current_x = start_x
        for surf, color, width in zip(type_surfs, type_colors_list, type_widths):
            bg_rect = pygame.Rect(current_x, y, width, type_height)
            pygame.draw.rect(screen, color, bg_rect, border_radius=15)
            pygame.draw.rect(screen, (255, 255, 255, 100), bg_rect, 1, border_radius=15)

            text_x = current_x + (width - surf.get_width()) // 2
            text_y = y + (type_height - surf.get_height()) // 2
            screen.blit(surf, (text_x, text_y))
            current_x += width + type_spacing

    def _render_info_section(self, screen, section_rect):
        """Seção Natureza + IVs"""
        pygame.draw.rect(screen, (*self.colors['bg_card'], 180), section_rect, border_radius=12)
        pygame.draw.rect(screen, (*self.colors['border'], 150), section_rect, 1, border_radius=12)

        # Layout 2 colunas
        col_width = section_rect.width // 2
        left_x = section_rect.x + 25
        right_x = section_rect.x + col_width + 15

        # ===== NATUREZA =====
        font_label = self._get_font(13)
        font_value = self._get_font(22, True)

        label_nature = font_label.render("NATUREZA", True, self.colors['text_muted'])
        screen.blit(label_nature, (left_x, section_rect.y + 15))

        nature_name = self.pokemon.nature if hasattr(self.pokemon.nature, 'name') else str(self.pokemon.nature)
        nature_text = nature_name.capitalize()

        if font_value.size(nature_text)[0] > col_width - 30:
            font_value = self._get_font(18, True)

        nature_surf = font_value.render(nature_text, True, self.colors['accent'])
        screen.blit(nature_surf, (left_x, section_rect.y + 42))

        # ===== IVS =====
        label_ivs = font_label.render("IVs", True, self.colors['text_muted'])
        screen.blit(label_ivs, (right_x, section_rect.y + 15))

        if hasattr(self.pokemon, 'ivs') and self.pokemon.ivs:
            ivs = self.pokemon.ivs
            font_iv = self._get_font(14)

            iv_line1 = f"HP {ivs.get('hp', 0):02d}    ATK {ivs.get('attack', 0):02d}    DEF {ivs.get('defense', 0):02d}"
            iv_surf1 = font_iv.render(iv_line1, True, self.colors['text'])
            screen.blit(iv_surf1, (right_x, section_rect.y + 42))

            iv_line2 = f"SpA {ivs.get('special_attack', 0):02d}    SpD {ivs.get('special_defense', 0):02d}    SPD {ivs.get('speed', 0):02d}"
            iv_surf2 = font_iv.render(iv_line2, True, self.colors['text'])
            screen.blit(iv_surf2, (right_x, section_rect.y + 66))

    def _render_moves_section(self, screen, section_rect):
        """Seção de Moves - com título centralizado e tipos maiores"""
        pygame.draw.rect(screen, (*self.colors['bg_card'], 180), section_rect, border_radius=12)
        pygame.draw.rect(screen, (*self.colors['border'], 150), section_rect, 1, border_radius=12)

        # Título centralizado
        font_title = self._get_font(18, True)
        title = font_title.render("MOVIMENTOS", True, self.colors['primary'])
        title_x = section_rect.centerx - title.get_width() // 2
        screen.blit(title, (title_x, section_rect.y + 12))

        # Grid 2x2
        if not self.pokemon.moves:
            font = self._get_font(14)
            no_moves = font.render("Nenhum ataque conhecido", True, self.colors['text_muted'])
            no_x = section_rect.centerx - no_moves.get_width() // 2
            no_y = section_rect.centery - no_moves.get_height() // 2
            screen.blit(no_moves, (no_x, no_y))
            return

        grid_x = section_rect.x + 18
        grid_y = section_rect.y + 48
        slot_width = (section_rect.width - 42) // 2
        slot_height = 36
        slot_spacing = 12

        for i, move in enumerate(self.pokemon.moves[:4]):
            row = i // 2
            col = i % 2
            slot_x = grid_x + col * (slot_width + slot_spacing)
            slot_y = grid_y + row * (slot_height + slot_spacing)

            # Garante que fica dentro
            if slot_x + slot_width > section_rect.right:
                slot_x = section_rect.right - slot_width - 5
            if slot_y + slot_height > section_rect.bottom - 10:
                slot_y = section_rect.bottom - slot_height - 10

            self._render_move_slot(screen, slot_x, slot_y, slot_width, slot_height, move)

    def _render_move_slot(self, screen, x, y, width, height, move):
        """Slot de move - nome em maiúsculo e tipo maior"""
        # Cor de fundo baseada no tipo do move
        type_color = self.type_colors.get(move.type.lower(), (150, 150, 150))

        # Fundo do slot (cor do tipo com opacidade)
        bg_rect = pygame.Rect(x, y, width, height)
        pygame.draw.rect(screen, type_color, bg_rect, border_radius=10)
        pygame.draw.rect(screen, (255, 255, 255, 100), bg_rect, 2, border_radius=10)

        # Nome do move (EM MAIÚSCULO e centralizado)
        font_name = self._get_font(18, True)
        move_name = move.name.upper()

        # Trunca se muito longo
        max_len = 14
        if len(move_name) > max_len:
            move_name = move_name[:max_len] + "..."

        name_surf = font_name.render(move_name, True, (255, 255, 255))
        text_x = x + (width - name_surf.get_width()) // 2
        text_y = y + (height - name_surf.get_height()) // 2
        screen.blit(name_surf, (text_x, text_y))

        # Tipo do move (maior e mais legível)
        type_font = self._get_font(13, True)  # Aumentado de 10 para 13
        type_name = move.type.upper()[:5]  # Aumentado para 5 caracteres
        type_surf = type_font.render(type_name, True, (255, 255, 255))

        # Fundo semi-transparente para o tipo
        type_bg_width = type_surf.get_width() + 8
        type_bg_height = type_surf.get_height() + 4
        type_bg_x = x + width - type_bg_width - 6
        type_bg_y = y + 4

        pygame.draw.rect(screen, (0, 0, 0, 120),
                         (type_bg_x, type_bg_y, type_bg_width, type_bg_height),
                         border_radius=6)

        type_x = type_bg_x + (type_bg_width - type_surf.get_width()) // 2
        type_y = type_bg_y + (type_bg_height - type_surf.get_height()) // 2
        screen.blit(type_surf, (type_x, type_y))

    def _render_button(self, screen, section_rect):
        """Botão CONTINUAR"""
        button_width = 240
        button_height = 50
        button_x = section_rect.centerx - button_width // 2
        button_y = section_rect.y

        self.button_rect = pygame.Rect(button_x, button_y, button_width, button_height)

        if self.button_hovered:
            button_color = (70, 150, 70)
            border_color = (100, 200, 100)
        else:
            button_color = (40, 100, 40)
            border_color = (70, 150, 70)

        pygame.draw.rect(screen, button_color, self.button_rect, border_radius=14)
        pygame.draw.rect(screen, border_color, self.button_rect, 2, border_radius=14)

        font = self._get_font(24, True)
        button_text = font.render("CONTINUAR", True, (255, 255, 255))
        text_x = self.button_rect.centerx - button_text.get_width() // 2
        text_y = self.button_rect.centery - button_text.get_height() // 2
        screen.blit(button_text, (text_x, text_y))

    def _render_status_message(self, screen, viewport):
        """Mensagem de status FORA do modal"""
        viewport_center_x = viewport.x + viewport.width // 2

        msg_width = 340
        msg_height = 52
        msg_x = viewport_center_x - msg_width // 2
        msg_y = viewport.y + viewport.height - 80

        msg_rect = pygame.Rect(msg_x, msg_y, msg_width, msg_height)

        pygame.draw.rect(screen, (*self.colors['bg_dark'], 230), msg_rect, border_radius=14)
        pygame.draw.rect(screen, self.colors['border'], msg_rect, 1, border_radius=14)

        font = self._get_font(20, True)

        if self.is_to_team:
            text = f" ADICIONADO AO TIME!"
            color = self.colors['success']
        else:
            text = f" ADICIONADO À BOX!"
            color = self.colors['warning']

        status_surf = font.render(text, True, color)
        text_x = msg_rect.centerx - status_surf.get_width() // 2
        text_y = msg_rect.centery - status_surf.get_height() // 2
        screen.blit(status_surf, (text_x, text_y))