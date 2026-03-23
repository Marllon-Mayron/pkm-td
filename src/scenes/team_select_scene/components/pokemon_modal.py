import pygame
from src.data.pokedex import Pokedex


class PokemonModal:
    def __init__(self, game, pokemon):
        self.game = game
        self.pokemon = pokemon
        self.pokedex = Pokedex()
        self.visible = True
        self._setup_dimensions()

        # Cores do tema
        self.colors = {
            'bg_primary': (25, 25, 35),
            'bg_secondary': (35, 35, 45),
            'border': (100, 100, 150),
            'border_light': (150, 150, 200),
            'text_primary': (255, 255, 255),
            'text_secondary': (200, 200, 200),
            'text_accent': (255, 215, 0),
            'hp_bar_bg': (40, 40, 50),
            'hp_green': (0, 200, 0),
            'hp_yellow': (255, 200, 0),
            'hp_red': (255, 50, 50),
            'stat_bg': (45, 45, 55),
            'move_bg': (40, 40, 50),
            'move_border': (80, 80, 100),
            'move_pp_bg': (30, 30, 40),
            'move_pp_text': (150, 200, 150),
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
        }

    def _setup_dimensions(self):
        self.width = int(self.game.screen_manager.window_width * 0.85)
        self.height = int(self.game.screen_manager.window_height * 0.85)
        self.x = (self.game.screen_manager.window_width - self.width) // 2
        self.y = (self.game.screen_manager.window_height - self.height) // 2

        self.rect = pygame.Rect(self.x, self.y, self.width, self.height)
        self.close_button = pygame.Rect(self.x + self.width - 45, self.y + 15, 35, 35)

        button_width = 180
        button_height = 45
        self.action_button = pygame.Rect(
            self.x + (self.width - button_width) // 2,
            self.y + self.height - 60,
            button_width,
            button_height
        )

    def handle_event(self, event):
        if not self.visible:
            return None

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.close_button.collidepoint(event.pos):
                self.visible = False
                return "close"

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

    def _draw_hp_bar(self, screen, x, y, width=200, height=12):
        hp_percent = self.pokemon.current_hp / self.pokemon.max_hp

        pygame.draw.rect(screen, self.colors['hp_bar_bg'], (x, y, width, height), border_radius=6)

        if hp_percent > 0.5:
            color = self.colors['hp_green']
        elif hp_percent > 0.25:
            color = self.colors['hp_yellow']
        else:
            color = self.colors['hp_red']

        bar_width = int(width * hp_percent)
        if bar_width > 0:
            pygame.draw.rect(screen, color, (x, y, bar_width, height), border_radius=6)

        font_small = pygame.font.Font(None, 16)
        hp_text = font_small.render(f"{self.pokemon.current_hp}/{self.pokemon.max_hp}", True,
                                    self.colors['text_secondary'])
        screen.blit(hp_text, (x + width + 10, y - 2))

    def _draw_stat_bar(self, screen, stat_name, stat_value, max_value=255, x=0, y=0, width=120):
        font_small = pygame.font.Font(None, 14)

        name_text = font_small.render(stat_name, True, self.colors['text_secondary'])
        screen.blit(name_text, (x, y))

        value_text = font_small.render(str(stat_value), True, self.colors['text_accent'])
        screen.blit(value_text, (x + 45, y))

        bar_width = width - 70
        bar_height = 6
        bar_x = x + 70
        bar_y = y + 2

        percent = min(1.0, stat_value / max_value)
        pygame.draw.rect(screen, (50, 50, 60), (bar_x, bar_y, bar_width, bar_height), border_radius=3)
        pygame.draw.rect(screen, (100, 150, 200), (bar_x, bar_y, int(bar_width * percent), bar_height),
                         border_radius=3)

    def _draw_move_card(self, screen, move, index, x, y, width):
        card_height = 65
        move_rect = pygame.Rect(x, y, width, card_height)
        self._draw_rounded_rect(screen, self.colors['move_bg'], move_rect, radius=6)
        self._draw_rounded_rect(screen, self.colors['move_border'], move_rect, radius=6, border=1)

        font_name = pygame.font.Font(None, 16)
        font_stats = pygame.font.Font(None, 14)

        name_text = font_name.render(move.name.upper(), True, self.colors['text_accent'])
        screen.blit(name_text, (x + 8, y + 8))

        type_color = self._get_type_color(move.type)
        type_rect = pygame.Rect(x + width - 60, y + 8, 52, 20)
        pygame.draw.rect(screen, type_color, type_rect, border_radius=5)
        font_type = pygame.font.Font(None, 11)
        type_text = font_type.render(move.type.upper(), True, (255, 255, 255))
        screen.blit(type_text, (type_rect.centerx - type_text.get_width() // 2,
                                type_rect.centery - type_text.get_height() // 2))

        stats_y = y + 38

        if move.power > 0:
            power_text = font_stats.render(f"PWR {move.power}", True, self.colors['text_secondary'])
        else:
            power_text = font_stats.render(f"PWR --", True, self.colors['text_secondary'])
        screen.blit(power_text, (x + 8, stats_y))

        acc_text = font_stats.render(f"ACC {move.accuracy}", True, self.colors['text_secondary'])
        acc_x = x + (width // 2) - (acc_text.get_width() // 2)
        screen.blit(acc_text, (acc_x, stats_y))

        pp_text = font_stats.render(f"PP {move.current_pp}/{move.max_pp}", True, self.colors['move_pp_text'])
        pp_x = x + width - pp_text.get_width() - 8
        screen.blit(pp_text, (pp_x, stats_y))

    def render(self, screen):
        if not self.visible:
            return

        # Overlay escuro
        overlay = pygame.Surface((
            self.game.screen_manager.window_width,
            self.game.screen_manager.window_height
        ))
        overlay.set_alpha(200)
        overlay.fill((0, 0, 0))
        screen.blit(overlay, (0, 0))

        # Fundo principal do modal
        self._draw_rounded_rect(screen, self.colors['bg_primary'], self.rect, radius=15)
        self._draw_rounded_rect(screen, self.colors['border'], self.rect, radius=15, border=2)

        # Cabeçalho
        for i in range(80):
            alpha = 40 - int(i * 0.5)
            color = (45, 45, 55, max(0, min(255, alpha)))
            pygame.draw.line(screen, color[:3], (self.x, self.y + i), (self.x + self.width, self.y + i))

        # Botão fechar
        self._draw_rounded_rect(screen, (60, 60, 70), self.close_button, radius=8)
        close_font = pygame.font.Font(None, 28)
        close_text = close_font.render("✕", True, (255, 255, 255))
        close_rect = close_text.get_rect(center=self.close_button.center)
        screen.blit(close_text, close_rect)

        # ===== LAYOUT RESPONSIVO =====
        # Área útil do modal (excluindo header e footer)
        header_height = 80
        footer_height = 80
        usable_height = self.height - header_height - footer_height
        usable_y = self.y + header_height

        # Margens
        margin = 20
        inner_width = self.width - (margin * 2)
        inner_x = self.x + margin

        # Layout: 2 colunas, 2 linhas
        col_width = (inner_width - margin) // 2
        row_height = (usable_height - margin) // 2

        # Definindo as 4 células
        cells = {
            'sprite': pygame.Rect(inner_x, usable_y, col_width, row_height),
            'stats': pygame.Rect(inner_x + col_width + margin, usable_y, col_width, row_height),
            'moves': pygame.Rect(inner_x, usable_y + row_height + margin, col_width, row_height),
            'info': pygame.Rect(inner_x + col_width + margin, usable_y + row_height + margin, col_width, row_height)
        }

        # ===== CÉLULA 1: SPRITE E INFO BÁSICA =====
        cell = cells['sprite']

        # Sprite
        sprite = self.pokedex.get_sprite(self.pokemon.id, "front", self.pokemon.is_shiny)
        sprite_size = min(cell.width - 40, cell.height - 100)
        if sprite:
            sprite_big = pygame.transform.scale(sprite, (sprite_size, sprite_size))
            sprite_x = cell.x + (cell.width - sprite_size) // 2
            sprite_y = cell.y + 10
            screen.blit(sprite_big, (sprite_x, sprite_y))

            if self.pokemon.is_shiny:
                glow = pygame.Surface((sprite_size + 20, sprite_size + 20), pygame.SRCALPHA)
                pygame.draw.circle(glow, (255, 215, 0, 80), (sprite_size // 2 + 10, sprite_size // 2 + 10),
                                   sprite_size // 2 + 10)
                screen.blit(glow, (sprite_x - 10, sprite_y - 10))

        # Nome e nível
        title_font = pygame.font.Font(None, 24)
        level_font = pygame.font.Font(None, 20)

        name_text = title_font.render(f"{self.pokemon.name}", True, self.colors['text_primary'])
        level_text = level_font.render(f"Lv.{self.pokemon.level}", True, self.colors['text_accent'])

        name_y = cell.y + sprite_size + 20 if sprite else cell.y + 60
        name_x = cell.x + (cell.width - (name_text.get_width() + level_text.get_width() + 10)) // 2

        screen.blit(name_text, (name_x, name_y))
        screen.blit(level_text, (name_x + name_text.get_width() + 10,
                                 name_y + (name_text.get_height() - level_text.get_height()) // 2))

        # Tipos
        type_y = name_y + 35
        type_spacing = 80
        total_types_width = len(self.pokemon.types) * type_spacing
        type_start_x = cell.x + (cell.width - total_types_width) // 2

        for i, type_name in enumerate(self.pokemon.types):
            type_color = self._get_type_color(type_name)
            type_rect = pygame.Rect(type_start_x + (i * type_spacing), type_y, 70, 26)
            pygame.draw.rect(screen, type_color, type_rect, border_radius=6)
            pygame.draw.rect(screen, (200, 200, 200), type_rect, 1, border_radius=6)

            type_text = pygame.font.Font(None, 12).render(type_name.upper(), True, (255, 255, 255))
            type_rect_text = type_text.get_rect(center=type_rect.center)
            screen.blit(type_text, type_rect_text)

        # Natureza
        nature_font = pygame.font.Font(None, 14)
        nature_text = nature_font.render(f"Natureza: {self.pokemon.nature}", True, self.colors['text_secondary'])
        nature_x = cell.x + (cell.width - nature_text.get_width()) // 2
        if type_y + 40 + nature_text.get_height() < cell.bottom - 5:
            screen.blit(nature_text, (nature_x, type_y + 35))

        # ===== CÉLULA 2: STATS =====
        cell = cells['stats']

        stats_title = pygame.font.Font(None, 22).render("STATS", True, self.colors['text_accent'])
        stats_title_x = cell.x + (cell.width - stats_title.get_width()) // 2
        screen.blit(stats_title, (stats_title_x, cell.y + 8))

        stats = [
            ("ATK", self.pokemon.attack),
            ("DEF", self.pokemon.defense),
            ("SPA", self.pokemon.sp_attack),
            ("SPD", self.pokemon.sp_defense),
            ("VEL", self.pokemon.speed_stat)
        ]

        stat_start_y = cell.y + 45
        stat_spacing = 28
        stat_bar_width = cell.width - 30

        for i, (name, value) in enumerate(stats):
            y_pos = stat_start_y + (i * stat_spacing)
            if y_pos + 20 < cell.bottom:
                self._draw_stat_bar(screen, name, value, max_value=255,
                                    x=cell.x + 10, y=y_pos, width=stat_bar_width)

        # ===== HP BAR (DESTAQUE) =====
        hp_y = stat_start_y + (len(stats) * stat_spacing) + 8

        # Fundo para destacar a área de HP
        hp_bg_rect = pygame.Rect(cell.x + 5, hp_y - 5, cell.width - 10, 40)
        pygame.draw.rect(screen, (35, 35, 45), hp_bg_rect, border_radius=8)

        # Label HP
        hp_label_font = pygame.font.Font(None, 18)
        hp_label = hp_label_font.render("HP", True, self.colors['text_accent'])
        screen.blit(hp_label, (cell.x + 15, hp_y))

        # Valor HP
        hp_value_font = pygame.font.Font(None, 16)
        hp_text = hp_value_font.render(f"{self.pokemon.current_hp}/{self.pokemon.max_hp}",
                                       True, self.colors['text_primary'])
        screen.blit(hp_text, (cell.x + 55, hp_y))

        # Barra de HP
        hp_bar_width = cell.width - 100
        hp_bar_height = 12
        hp_bar_x = cell.x + 55
        hp_bar_y = hp_y + 20

        hp_percent = self.pokemon.current_hp / self.pokemon.max_hp

        # Fundo da barra
        pygame.draw.rect(screen, self.colors['hp_bar_bg'],
                         (hp_bar_x, hp_bar_y, hp_bar_width, hp_bar_height), border_radius=6)

        # Cor da barra baseada no percentual
        if hp_percent > 0.5:
            hp_color = self.colors['hp_green']
        elif hp_percent > 0.25:
            hp_color = self.colors['hp_yellow']
        else:
            hp_color = self.colors['hp_red']

        # Barra de progresso
        bar_width = int(hp_bar_width * hp_percent)
        if bar_width > 0:
            pygame.draw.rect(screen, hp_color,
                             (hp_bar_x, hp_bar_y, bar_width, hp_bar_height), border_radius=6)

        # ===== IVs =====
        iv_y = hp_y + 45
        if iv_y + 80 < cell.bottom:
            iv_title = pygame.font.Font(None, 16).render("IVs", True, self.colors['text_accent'])
            iv_title_x = cell.x + (cell.width - iv_title.get_width()) // 2
            screen.blit(iv_title, (iv_title_x, iv_y))

            iv_values = [
                f"HP:{self.pokemon.ivs.get('hp', 0)}",
                f"ATK:{self.pokemon.ivs.get('attack', 0)}",
                f"DEF:{self.pokemon.ivs.get('defense', 0)}",
                f"SPA:{self.pokemon.ivs.get('special_attack', 0)}",
                f"SPD:{self.pokemon.ivs.get('special_defense', 0)}",
                f"VEL:{self.pokemon.ivs.get('speed', 0)}"
            ]

            iv_font = pygame.font.Font(None, 12)
            iv_start_y = iv_y + 25
            col_width_iv = (cell.width - 20) // 3

            for i, iv in enumerate(iv_values):
                col = i % 3
                row = i // 3
                iv_x = cell.x + 10 + (col * col_width_iv)
                iv_y_pos = iv_start_y + (row * 20)

                if iv_y_pos + 15 < cell.bottom:
                    value = int(iv.split(':')[1])
                    if value >= 31:
                        color = (255, 100, 100)
                    elif value >= 20:
                        color = (255, 200, 100)
                    else:
                        color = (150, 150, 150)

                    iv_surf = iv_font.render(iv, True, color)
                    screen.blit(iv_surf, (iv_x, iv_y_pos))

        # ===== CÉLULA 3: MOVES (GRID 2x2) =====
        cell = cells['moves']

        moves_title = pygame.font.Font(None, 22).render("MOVES", True, self.colors['text_accent'])
        moves_title_x = cell.x + (cell.width - moves_title.get_width()) // 2
        screen.blit(moves_title, (moves_title_x, cell.y + 8))

        # Grid de moves 2x2
        move_card_width = (cell.width - 25) // 2
        move_card_height = 65
        move_spacing = 10
        moves_start_y = cell.y + 45

        for i in range(4):
            if i < len(self.pokemon.moves):
                move = self.pokemon.moves[i]
                col = i % 2
                row = i // 2

                card_x = cell.x + 5 + (col * (move_card_width + move_spacing))
                card_y = moves_start_y + (row * (move_card_height + move_spacing))

                if card_y + move_card_height < cell.bottom - 5:
                    self._draw_move_card(screen, move, i, card_x, card_y, move_card_width)
            else:
                col = i % 2
                row = i // 2

                card_x = cell.x + 5 + (col * (move_card_width + move_spacing))
                card_y = moves_start_y + (row * (move_card_height + move_spacing))

                if card_y + move_card_height < cell.bottom - 5:
                    empty_rect = pygame.Rect(card_x, card_y, move_card_width, move_card_height)
                    self._draw_rounded_rect(screen, (30, 30, 40), empty_rect, radius=6)
                    self._draw_rounded_rect(screen, (60, 60, 70), empty_rect, radius=6, border=1)

                    empty_font = pygame.font.Font(None, 12)
                    empty_text = empty_font.render("-- Vazio --", True, (80, 80, 90))
                    text_rect = empty_text.get_rect(center=empty_rect.center)
                    screen.blit(empty_text, text_rect)

        # ===== CÉLULA 4: INFORMAÇÕES =====
        cell = cells['info']

        info_title = pygame.font.Font(None, 22).render("INFORMAÇÕES", True, self.colors['text_accent'])
        info_title_x = cell.x + (cell.width - info_title.get_width()) // 2
        screen.blit(info_title, (info_title_x, cell.y + 8))

        info_font = pygame.font.Font(None, 14)
        y_offset = 45
        line_spacing = 25

        # Experiência
        exp_text = info_font.render(f"Experiência: {self.pokemon.xp}", True, self.colors['text_secondary'])
        exp_x = cell.x + (cell.width - exp_text.get_width()) // 2
        if y_offset < cell.height - 10:
            screen.blit(exp_text, (exp_x, cell.y + y_offset))
        y_offset += line_spacing

        # Próximo nível
        exp_needed_text = info_font.render(f"Próximo nível: {self.pokemon.xp_to_next} EXP", True,
                                           self.colors['text_secondary'])
        exp_needed_x = cell.x + (cell.width - exp_needed_text.get_width()) // 2
        if y_offset < cell.height - 10:
            screen.blit(exp_needed_text, (exp_needed_x, cell.y + y_offset))
        y_offset += line_spacing

        # Barra de experiência
        exp_bar_width = cell.width - 40
        exp_bar_height = 10
        exp_bar_x = cell.x + 20
        exp_bar_y = cell.y + y_offset

        if exp_bar_y + exp_bar_height < cell.bottom - 10:
            exp_percent = self.pokemon.xp / self.pokemon.xp_to_next if self.pokemon.xp_to_next > 0 else 0
            pygame.draw.rect(screen, (50, 50, 60), (exp_bar_x, exp_bar_y, exp_bar_width, exp_bar_height),
                             border_radius=5)
            pygame.draw.rect(screen, (100, 150, 200),
                             (exp_bar_x, exp_bar_y, int(exp_bar_width * exp_percent), exp_bar_height), border_radius=5)
            y_offset += line_spacing

        # ID
        id_text = info_font.render(f"ID: #{self.pokemon.id:04d}", True, self.colors['text_secondary'])
        id_x = cell.x + (cell.width - id_text.get_width()) // 2
        if y_offset < cell.height - 10:
            screen.blit(id_text, (id_x, cell.y + y_offset))
        y_offset += line_spacing

        # Status Boss
        if self.pokemon.is_boss:
            boss_text = info_font.render("⭐ BOSS ⭐", True, (255, 100, 100))
            boss_x = cell.x + (cell.width - boss_text.get_width()) // 2
            if y_offset < cell.height - 10:
                screen.blit(boss_text, (boss_x, cell.y + y_offset))

        # ===== BOTÃO DE AÇÃO =====
        if self.pokemon.is_in_team:
            button_color = (150, 80, 80)
            button_text = "REMOVER DO TIME"
        else:
            if len(self.game.player.team) < 6:
                button_color = (80, 150, 80)
                button_text = "ADICIONAR AO TIME"
            else:
                button_color = (80, 80, 80)
                button_text = "TIME CHEIO"

        self._draw_rounded_rect(screen, button_color, self.action_button, radius=10)

        action_font = pygame.font.Font(None, 24)
        action_surf = action_font.render(button_text, True, (255, 255, 255))
        action_rect = action_surf.get_rect(center=self.action_button.center)
        screen.blit(action_surf, action_rect)

        # ===== INDICADOR SHINY =====
        if self.pokemon.is_shiny:
            shiny_text = pygame.font.Font(None, 18).render("✨ SHINY ✨", True, (255, 215, 0))
            shiny_rect = shiny_text.get_rect(center=(self.x + self.width - 70, self.y + 45))
            screen.blit(shiny_text, shiny_rect)