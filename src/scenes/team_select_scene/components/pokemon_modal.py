import pygame
import random
import math
from src.data.pokedex import Pokedex


class PokemonModal:
    def __init__(self, game, pokemon):
        self.game = game
        self.pokemon = pokemon
        self.pokedex = Pokedex()
        self.visible = True
        self.current_page = 0
        self.total_pages = 3
        self._setup_dimensions()

        self.particle_timer = 0
        self.particles = []

        self.colors = {
            'bg_primary': (20, 22, 27),
            'bg_secondary': (28, 30, 36),
            'bg_tertiary': (35, 38, 45),
            'border': (60, 65, 80),
            'border_light': (80, 85, 105),
            'text_primary': (240, 242, 245),
            'text_secondary': (160, 165, 180),
            'text_accent': (255, 215, 0),
            'text_good': (100, 200, 100),
            'hp_bar_bg': (35, 35, 45),
            'hp_green': (0, 200, 0),
            'hp_yellow': (255, 200, 0),
            'hp_red': (255, 50, 50),
            'move_bg': (30, 32, 38),
            'move_border': (50, 55, 65),
            'move_pp_text': (120, 180, 120),
            'stat_bar': (80, 140, 200),
            'type_normal': (168, 168, 120),
            'type_fire': (240, 128, 48),
            'type_water': (104, 144, 240),
            'type_electric': (248, 208, 48),
            'type_grass': (120, 200, 80),
            'type_ice': (152, 216, 216),
            'type_fighting': (192, 48, 40),
            'type_poison': (160, 64, 160),
            'type_ground': (224, 192, 104),
            'type_flying': (168, 144, 240),
            'type_psychic': (248, 88, 136),
            'type_bug': (168, 184, 32),
            'type_rock': (184, 160, 56),
            'type_ghost': (112, 88, 152),
            'type_dragon': (112, 56, 248),
            'type_dark': (112, 88, 72),
            'type_steel': (184, 184, 208),
            'type_fairy': (238, 153, 172),
            'iv_perfect': (255, 215, 0),
            'iv_great': (100, 200, 100),
            'iv_good': (100, 150, 200),
            'iv_bad': (200, 100, 100),
        }

    def _get_iv_rank(self, value):
        if value == 31:
            return "PERFEITO", self.colors['iv_perfect']
        elif value >= 28:
            return "MUITO BOM", self.colors['iv_great']
        elif value >= 24:
            return "BOM", self.colors['iv_good']
        elif value >= 18:
            return "MEDIANO", (150, 150, 180)
        elif value >= 10:
            return "RUIM", self.colors['iv_bad']
        elif value >= 1:
            return "MUITO RUIM", (180, 80, 80)
        else:
            return "HORRIVEL", (120, 40, 40)

    def _setup_dimensions(self):
        self.width = int(self.game.screen_manager.window_width * 0.8)
        self.height = int(self.game.screen_manager.window_height * 0.85)
        self.x = (self.game.screen_manager.window_width - self.width) // 2
        self.y = (self.game.screen_manager.window_height - self.height) // 2

        self.rect = pygame.Rect(self.x, self.y, self.width, self.height)
        self.close_button = pygame.Rect(self.x + self.width - 45, self.y + 15, 35, 35)

        page_button_width = 55
        page_button_height = 40
        button_y = self.y + self.height - 55

        self.prev_page_button = pygame.Rect(
            self.x + 20,
            button_y,
            page_button_width,
            page_button_height
        )
        self.next_page_button = pygame.Rect(
            self.x + self.width - 20 - page_button_width,
            button_y,
            page_button_width,
            page_button_height
        )

        button_width = 200
        button_height = 44
        self.action_button = pygame.Rect(
            self.x + (self.width - button_width) // 2,
            self.y + self.height - 60,
            button_width,
            button_height
        )

    def _create_shiny_particles(self, sprite_x, sprite_y, sprite_size):
        """Cria partículas brilhantes ao redor do sprite shiny"""
        for _ in range(4):
            angle = random.uniform(0, math.pi * 2)
            radius = random.uniform(sprite_size // 2 + 5, sprite_size // 2 + 25)
            offset_x = math.cos(angle) * radius
            offset_y = math.sin(angle) * radius

            self.particles.append({
                'x': sprite_x + sprite_size // 2 + offset_x,
                'y': sprite_y + sprite_size // 2 + offset_y,
                'vx': random.uniform(-0.2, 0.2),
                'vy': random.uniform(-0.2, 0.2),
                'life': random.uniform(0.7, 1.0),
                'size': random.randint(1, 3),
                'color': random.choice([
                    (255, 215, 0), (255, 200, 0), (255, 220, 50)
                ])
            })

    def _update_shiny_particles(self):
        """Atualiza as partículas shiny"""
        for particle in self.particles[:]:
            particle['x'] += particle['vx']
            particle['y'] += particle['vy']
            particle['life'] -= 0.01
            if particle['life'] <= 0:
                self.particles.remove(particle)

    def _draw_shiny_particles(self, screen):
        """Desenha as partículas brilhantes"""
        for particle in self.particles:
            alpha = int(particle['life'] * 200)
            color = (particle['color'][0], particle['color'][1], particle['color'][2])

            pygame.draw.circle(screen, color,
                               (int(particle['x']), int(particle['y'])),
                               particle['size'])

    def handle_event(self, event):
        if not self.visible:
            return None

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.close_button.collidepoint(event.pos):
                self.visible = False
                return "close"

            if self.prev_page_button.collidepoint(event.pos) and self.current_page > 0:
                self.current_page -= 1
                return None

            if self.next_page_button.collidepoint(event.pos) and self.current_page < self.total_pages - 1:
                self.current_page += 1
                return None

            if self.action_button.collidepoint(event.pos):
                if not self.pokemon.is_in_team and len(self.game.player.team) >= 6:
                    return None
                return "action"

            if not self.rect.collidepoint(event.pos):
                self.visible = False
                return "close"

        return None

    def _get_type_color(self, type_name):
        color_key = f"type_{type_name.lower()}"
        return self.colors.get(color_key, (128, 128, 128))

    def _draw_rounded_rect(self, screen, color, rect, radius=8, border=0, border_color=None):
        pygame.draw.rect(screen, color, rect, border_radius=radius)
        if border > 0 and border_color:
            pygame.draw.rect(screen, border_color, rect, border, border_radius=radius)

    def _draw_sparkle(self, screen, x, y, size, color):
        """Desenha uma estrela/brilho pequena"""
        points = []
        for i in range(4):
            angle = math.radians(i * 90)
            inner_x = x + math.cos(angle) * size * 0.3
            inner_y = y + math.sin(angle) * size * 0.3
            outer_x = x + math.cos(angle + math.radians(45)) * size
            outer_y = y + math.sin(angle + math.radians(45)) * size
            points.extend([(inner_x, inner_y), (outer_x, outer_y)])

        if len(points) >= 3:
            pygame.draw.polygon(screen, color, points, 1)

    def _draw_move_card(self, screen, move, x, y, width):
        card_height = 72
        move_rect = pygame.Rect(x, y, width, card_height)
        self._draw_rounded_rect(screen, self.colors['move_bg'], move_rect, radius=8)
        self._draw_rounded_rect(screen, self.colors['move_border'], move_rect, radius=8, border=1)

        name_font = pygame.font.Font(None, 15)
        stats_font = pygame.font.Font(None, 12)

        name_text = name_font.render(move.name.upper(), True, self.colors['text_accent'])
        screen.blit(name_text, (x + 12, y + 10))

        type_color = self._get_type_color(move.type)
        type_rect = pygame.Rect(x + width - 65, y + 8, 55, 22)
        pygame.draw.rect(screen, type_color, type_rect, border_radius=6)
        type_text = pygame.font.Font(None, 10).render(move.type.upper(), True, (255, 255, 255))
        screen.blit(type_text,
                    (type_rect.centerx - type_text.get_width() // 2, type_rect.centery - type_text.get_height() // 2))

        stats_y = y + 38
        power_text = stats_font.render(f"PWR: {move.power if move.power > 0 else '--'}", True,
                                       self.colors['text_secondary'])
        screen.blit(power_text, (x + 12, stats_y))

        acc_text = stats_font.render(f"ACC: {move.accuracy}", True, self.colors['text_secondary'])
        screen.blit(acc_text, (x + 85, stats_y))

        pp_text = stats_font.render(f"PP: {move.current_pp}/{move.max_pp}", True, self.colors['move_pp_text'])
        screen.blit(pp_text, (x + width - 75, stats_y))

    def render(self, screen):
        if not self.visible:
            return

        overlay = pygame.Surface((self.game.screen_manager.window_width, self.game.screen_manager.window_height))
        overlay.set_alpha(180)
        overlay.fill((0, 0, 0))
        screen.blit(overlay, (0, 0))

        self._draw_rounded_rect(screen, self.colors['bg_primary'], self.rect, radius=15)
        self._draw_rounded_rect(screen, self.colors['border'], self.rect, radius=15, border=2)

        self._draw_rounded_rect(screen, (40, 42, 48), self.close_button, radius=8)
        close_font = pygame.font.Font(None, 26)
        close_text = close_font.render("✕", True, self.colors['text_secondary'])
        close_rect = close_text.get_rect(center=self.close_button.center)
        screen.blit(close_text, close_rect)

        header_height = 160

        sprite = self.pokedex.get_sprite(self.pokemon.id, "front", self.pokemon.is_shiny)
        sprite_size = 160
        if sprite:
            sprite_big = pygame.transform.scale(sprite, (sprite_size, sprite_size))
            sprite_x = self.x + (self.width // 2) - (sprite_size // 2)
            sprite_y = self.y
            screen.blit(sprite_big, (sprite_x, sprite_y))

            if self.pokemon.is_shiny:
                self.particle_timer += 1
                if self.particle_timer > 20:
                    self.particle_timer = 0
                    self._create_shiny_particles(sprite_x, sprite_y, sprite_size)

                self._update_shiny_particles()
                self._draw_shiny_particles(screen)

                if random.randint(1, 30) == 1:
                    sparkle_x = sprite_x + random.randint(15, sprite_size - 15)
                    sparkle_y = sprite_y + random.randint(15, sprite_size - 15)
                    sparkle_size = random.randint(2, 4)
                    sparkle_color = (255, 215, 0)
                    self._draw_sparkle(screen, sparkle_x, sparkle_y, sparkle_size, sparkle_color)

        name_font = pygame.font.Font(None, 26)

        name_text = name_font.render(f"{self.pokemon.name}  Lv.{self.pokemon.level}", True, self.colors['text_accent'])
        name_x = self.x + (self.width - name_text.get_width()) // 2
        screen.blit(name_text, (name_x, sprite_y + sprite_size))

        if self.pokemon.is_shiny:
            shiny_badge = pygame.Rect(self.x + self.width - 85, self.y + 15, 70, 24)
            self._draw_rounded_rect(screen, (80, 70, 30), shiny_badge, radius=6)
            shiny_text = pygame.font.Font(None, 12).render("✨ SHINY", True, (255, 215, 0))
            screen.blit(shiny_text, (shiny_badge.centerx - shiny_text.get_width() // 2,
                                     shiny_badge.centery - shiny_text.get_height() // 2))

        separator = pygame.Rect(self.x + 20, self.y + header_height, self.width - 40, 1)
        pygame.draw.line(screen, self.colors['border'], (separator.x, separator.y),
                         (separator.x + separator.width, separator.y))

        content_rect = pygame.Rect(self.x + 20, self.y + header_height + 25, self.width - 40,
                                   self.height - header_height - 95)

        if self.current_page == 0:
            self._render_stats_page(screen, content_rect)
        elif self.current_page == 1:
            self._render_moves_page(screen, content_rect)
        elif self.current_page == 2:
            self._render_info_page(screen, content_rect)

        prev_active = self.current_page > 0
        next_active = self.current_page < self.total_pages - 1

        prev_color = (55, 60, 70) if prev_active else (35, 38, 45)
        next_color = (55, 60, 70) if next_active else (35, 38, 45)

        self._draw_rounded_rect(screen, prev_color, self.prev_page_button, radius=8)
        self._draw_rounded_rect(screen, next_color, self.next_page_button, radius=8)

        if prev_active:
            self._draw_rounded_rect(screen, (80, 85, 95), self.prev_page_button, radius=8, border=1)
        if next_active:
            self._draw_rounded_rect(screen, (80, 85, 95), self.next_page_button, radius=8, border=1)

        page_font = pygame.font.Font(None, 22)
        prev_text = page_font.render("◀", True, self.colors['text_primary'] if prev_active else (60, 65, 75))
        next_text = page_font.render("▶", True, self.colors['text_primary'] if next_active else (60, 65, 75))
        screen.blit(prev_text, (self.prev_page_button.centerx - 8, self.prev_page_button.centery - 11))
        screen.blit(next_text, (self.next_page_button.centerx - 8, self.next_page_button.centery - 11))

        if self.pokemon.is_in_team:
            button_color = (120, 60, 60)
            button_text = "✖ REMOVER DO TIME"
        else:
            if len(self.game.player.team) < 6:
                button_color = (60, 120, 60)
                button_text = "✓ ADICIONAR AO TIME"
            else:
                button_color = (55, 58, 65)
                button_text = "⚠ TIME CHEIO"

        self._draw_rounded_rect(screen, button_color, self.action_button, radius=10)
        self._draw_rounded_rect(screen, (100, 105, 115), self.action_button, radius=10, border=1)

        action_font = pygame.font.Font(None, 18)
        action_surf = action_font.render(button_text, True, (255, 255, 255))
        action_rect = action_surf.get_rect(center=self.action_button.center)
        screen.blit(action_surf, action_rect)

    def _render_stats_page(self, screen, content_rect):
        section_font = pygame.font.Font(None, 18)

        left_width = content_rect.width * 0.48
        right_width = content_rect.width * 0.48
        left_col = pygame.Rect(content_rect.x, content_rect.y, left_width, content_rect.height)
        right_col = pygame.Rect(content_rect.x + left_width + 15, content_rect.y, right_width, content_rect.height)

        stats_title = section_font.render("STATS BASE", True, self.colors['text_accent'])
        stats_title_x = left_col.x + (left_col.width - stats_title.get_width()) // 2
        screen.blit(stats_title, (stats_title_x, left_col.y))

        pygame.draw.line(screen, self.colors['border'], (left_col.x + 10, left_col.y + 22),
                         (left_col.x + left_col.width - 10, left_col.y + 22), 1)

        stats = [
            ("HP", self.pokemon.max_hp, 255),
            ("ATAQUE", self.pokemon.attack, 255),
            ("DEFESA", self.pokemon.defense, 255),
            ("SP. ATAQUE", self.pokemon.sp_attack, 255),
            ("SP. DEFESA", self.pokemon.sp_defense, 255),
            ("VELOCIDADE", self.pokemon.speed_stat, 255)
        ]

        stat_start_y = left_col.y + 40
        stat_spacing = 48

        for i, (name, value, max_val) in enumerate(stats):
            y_pos = stat_start_y + (i * stat_spacing)
            if y_pos + 45 < left_col.bottom:
                card_rect = pygame.Rect(left_col.x + 10, y_pos, left_col.width - 20, 45)
                self._draw_rounded_rect(screen, self.colors['bg_tertiary'], card_rect, radius=8)

                name_font = pygame.font.Font(None, 14)
                value_font = pygame.font.Font(None, 16)

                name_text = name_font.render(name, True, self.colors['text_secondary'])
                screen.blit(name_text, (card_rect.x + 15, card_rect.y + 15))

                value_text = value_font.render(str(value), True, self.colors['text_accent'])
                screen.blit(value_text, (card_rect.x + 100, card_rect.y + 14))

                percent = value / max_val
                bar_width = card_rect.width - 130
                bar_height = 8
                bar_x = card_rect.x + 120
                bar_y = card_rect.y + 18

                pygame.draw.rect(screen, (45, 48, 55), (bar_x, bar_y, bar_width, bar_height), border_radius=4)
                if value > 0:
                    pygame.draw.rect(screen, self.colors['stat_bar'],
                                     (bar_x, bar_y, int(bar_width * percent), bar_height), border_radius=4)

        nature_y = stat_start_y + (len(stats) * stat_spacing) + 5
        if nature_y + 40 < left_col.bottom:
            nature_card = pygame.Rect(left_col.x + 10, nature_y, left_col.width - 20, 40)
            self._draw_rounded_rect(screen, self.colors['bg_tertiary'], nature_card, radius=8)
            nature_text = pygame.font.Font(None, 13).render(f"NATUREZA: {self.pokemon.nature}", True,
                                                            self.colors['text_secondary'])
            screen.blit(nature_text, (nature_card.centerx - nature_text.get_width() // 2,
                                      nature_card.centery - nature_text.get_height() // 2))

        iv_title = section_font.render("VALORES INDIVIDUAIS", True, self.colors['text_accent'])
        iv_title_x = right_col.x + (right_col.width - iv_title.get_width()) // 2
        screen.blit(iv_title, (iv_title_x, right_col.y))

        pygame.draw.line(screen, self.colors['border'], (right_col.x + 10, right_col.y + 22),
                         (right_col.x + right_col.width - 10, right_col.y + 22), 1)

        iv_list = [
            ("HP", self.pokemon.ivs.get('hp', 0)),
            ("ATAQUE", self.pokemon.ivs.get('attack', 0)),
            ("DEFESA", self.pokemon.ivs.get('defense', 0)),
            ("SP. ATAQUE", self.pokemon.ivs.get('special_attack', 0)),
            ("SP. DEFESA", self.pokemon.ivs.get('special_defense', 0)),
            ("VELOCIDADE", self.pokemon.ivs.get('speed', 0))
        ]

        iv_start_y = right_col.y + 40
        iv_spacing = 48

        for i, (name, value) in enumerate(iv_list):
            y_pos = iv_start_y + (i * iv_spacing)
            if y_pos + 45 < right_col.bottom:
                card_rect = pygame.Rect(right_col.x + 10, y_pos, right_col.width - 20, 45)
                self._draw_rounded_rect(screen, self.colors['bg_tertiary'], card_rect, radius=8)

                name_font = pygame.font.Font(None, 14)
                value_font = pygame.font.Font(None, 16)
                rank_font = pygame.font.Font(None, 11)

                name_text = name_font.render(name, True, self.colors['text_secondary'])
                screen.blit(name_text, (card_rect.x + 15, card_rect.y + 15))

                value_text = value_font.render(str(value), True, self.colors['text_primary'])
                screen.blit(value_text, (card_rect.x + 100, card_rect.y + 14))

                percent = value / 31.0
                bar_width = card_rect.width - 180
                bar_height = 8
                bar_x = card_rect.x + 120
                bar_y = card_rect.y + 18

                if value >= 28:
                    bar_color = self.colors['iv_perfect']
                elif value >= 24:
                    bar_color = self.colors['iv_great']
                elif value >= 18:
                    bar_color = self.colors['iv_good']
                else:
                    bar_color = self.colors['iv_bad']

                pygame.draw.rect(screen, (45, 48, 55), (bar_x, bar_y, bar_width, bar_height), border_radius=4)
                if value > 0:
                    pygame.draw.rect(screen, bar_color, (bar_x, bar_y, int(bar_width * percent), bar_height),
                                     border_radius=4)

                rank_text, rank_color = self._get_iv_rank(value)
                rank_surf = rank_font.render(rank_text, True, rank_color)
                screen.blit(rank_surf, (card_rect.x + card_rect.width - rank_surf.get_width() - 12, card_rect.y + 15))

    def _render_moves_page(self, screen, content_rect):
        section_font = pygame.font.Font(None, 18)
        moves_title = section_font.render("MOVIMENTOS", True, self.colors['text_accent'])
        moves_title_x = content_rect.x + (content_rect.width - moves_title.get_width()) // 2
        screen.blit(moves_title, (moves_title_x, content_rect.y))

        pygame.draw.line(screen, self.colors['border'], (content_rect.x + 10, content_rect.y + 22),
                         (content_rect.x + content_rect.width - 10, content_rect.y + 22), 1)

        cards_per_row = 2
        card_width = (content_rect.width - 20) // cards_per_row
        card_height = 72
        start_x = content_rect.x
        start_y = content_rect.y + 45
        spacing = 12

        for i in range(4):
            row = i // cards_per_row
            col = i % cards_per_row
            card_x = start_x + (col * (card_width + spacing))
            card_y = start_y + (row * (card_height + spacing))

            if card_y + card_height < content_rect.bottom - 10:
                if i < len(self.pokemon.moves):
                    self._draw_move_card(screen, self.pokemon.moves[i], card_x, card_y, card_width)
                else:
                    empty_rect = pygame.Rect(card_x, card_y, card_width, card_height)
                    self._draw_rounded_rect(screen, (25, 27, 32), empty_rect, radius=8)
                    self._draw_rounded_rect(screen, (40, 43, 50), empty_rect, radius=8, border=1)
                    empty_font = pygame.font.Font(None, 13)
                    empty_text = empty_font.render("─ VAZIO ─", True, (60, 65, 75))
                    text_rect = empty_text.get_rect(center=empty_rect.center)
                    screen.blit(empty_text, text_rect)

    def _render_info_page(self, screen, content_rect):
        section_font = pygame.font.Font(None, 18)
        info_title = section_font.render("INFORMACOES", True, self.colors['text_accent'])
        info_title_x = content_rect.x + (content_rect.width - info_title.get_width()) // 2
        screen.blit(info_title, (info_title_x, content_rect.y))

        pygame.draw.line(screen, self.colors['border'], (content_rect.x + 10, content_rect.y + 22),
                         (content_rect.x + content_rect.width - 10, content_rect.y + 22), 1)

        card_width = (content_rect.width - 20) // 2
        left_card = pygame.Rect(content_rect.x, content_rect.y + 45, card_width, content_rect.height - 55)
        right_card = pygame.Rect(content_rect.x + card_width + 20, content_rect.y + 45, card_width,
                                 content_rect.height - 55)

        self._draw_rounded_rect(screen, self.colors['bg_secondary'], left_card, radius=10)
        self._draw_rounded_rect(screen, self.colors['border'], left_card, radius=10, border=1)
        self._draw_rounded_rect(screen, self.colors['bg_secondary'], right_card, radius=10)
        self._draw_rounded_rect(screen, self.colors['border'], right_card, radius=10, border=1)

        info_font = pygame.font.Font(None, 13)
        value_font = pygame.font.Font(None, 15)
        y_offset = left_card.y + 20
        line_spacing = 50

        left_items = [
            ("EXPERIENCIA", f"{self.pokemon.xp} / {self.pokemon.xp_to_next}"),
            ("PROXIMO NIVEL", f"{self.pokemon.xp_to_next - self.pokemon.xp} EXP"),
            ("ID POKEDEX", f"#{self.pokemon.id:04d}"),
        ]

        for label, value in left_items:
            label_text = info_font.render(label, True, self.colors['text_secondary'])
            screen.blit(label_text, (left_card.x + 20, y_offset))

            value_text = value_font.render(value, True, self.colors['text_accent'])
            screen.blit(value_text, (left_card.x + 20, y_offset + 20))
            y_offset += line_spacing

            if label == "EXPERIENCIA":
                exp_percent = self.pokemon.xp / self.pokemon.xp_to_next if self.pokemon.xp_to_next > 0 else 0
                exp_bar_width = left_card.width - 40
                exp_bar_height = 10
                exp_bar_x = left_card.x + 20
                exp_bar_y = y_offset - 15

                pygame.draw.rect(screen, (45, 48, 55), (exp_bar_x, exp_bar_y, exp_bar_width, exp_bar_height),
                                 border_radius=5)
                pygame.draw.rect(screen, (100, 180, 100),
                                 (exp_bar_x, exp_bar_y, int(exp_bar_width * exp_percent), exp_bar_height),
                                 border_radius=5)
                y_offset += 15

        right_y = right_card.y + 20

        right_items = [
            ("TIPO 1", self.pokemon.types[0] if len(self.pokemon.types) > 0 else "???"),
        ]

        if len(self.pokemon.types) > 1:
            right_items.append(("TIPO 2", self.pokemon.types[1]))

        if hasattr(self.pokemon, 'height') and self.pokemon.height:
            right_items.append(("ALTURA", f"{self.pokemon.height:.1f} m"))
        else:
            right_items.append(("ALTURA", "??? m"))

        if hasattr(self.pokemon, 'weight') and self.pokemon.weight:
            right_items.append(("PESO", f"{self.pokemon.weight:.1f} kg"))
        else:
            right_items.append(("PESO", "??? kg"))

        if hasattr(self.pokemon, 'ability') and self.pokemon.ability:
            right_items.append(("HABILIDADE", self.pokemon.ability[:18]))
        else:
            right_items.append(("HABILIDADE", "Desconhecida"))

        if self.pokemon.is_boss:
            right_items.append(("STATUS", "BOSS"))

        for label, value in right_items:
            label_text = info_font.render(label, True, self.colors['text_secondary'])
            screen.blit(label_text, (right_card.x + 20, right_y))

            if "TIPO" in label:
                type_color = self._get_type_color(value)
                type_badge = pygame.Rect(right_card.x + 100, right_y - 2, 70, 24)
                self._draw_rounded_rect(screen, type_color, type_badge, radius=6)
                type_text = pygame.font.Font(None, 11).render(value.upper(), True, (255, 255, 255))
                screen.blit(type_text, (type_badge.centerx - type_text.get_width() // 2,
                                        type_badge.centery - type_text.get_height() // 2))
            else:
                value_color = self.colors['text_good'] if "BOSS" in value else self.colors['text_primary']
                value_text = value_font.render(value, True, value_color)
                screen.blit(value_text, (right_card.x + 20, right_y + 20))
            right_y += line_spacing