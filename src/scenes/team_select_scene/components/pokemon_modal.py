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
                # Verifica se pode adicionar ao time
                if not self.pokemon.is_in_team and len(self.game.player.team) >= 6:
                    return None  # Time cheio, não faz nada
                return "action"

            if not self.rect.collidepoint(event.pos):
                self.visible = False
                return "close"

        return None

    def _get_type_color(self, type_name):
        """Retorna a cor do tipo"""
        color_key = f"type_{type_name.lower()}"
        return self.colors.get(color_key, (128, 128, 128))

    def _draw_rounded_rect(self, screen, color, rect, radius=8, border=0, border_color=None):
        """Desenha um retângulo com bordas arredondadas"""
        pygame.draw.rect(screen, color, rect, border_radius=radius)
        if border > 0 and border_color:
            pygame.draw.rect(screen, border_color, rect, border, border_radius=radius)

    def _draw_hp_bar(self, screen, x, y, width=200, height=12):
        """Desenha a barra de HP"""
        hp_percent = self.pokemon.current_hp / self.pokemon.max_hp

        # Fundo
        pygame.draw.rect(screen, self.colors['hp_bar_bg'], (x, y, width, height), border_radius=6)

        # Cor da barra
        if hp_percent > 0.5:
            color = self.colors['hp_green']
        elif hp_percent > 0.25:
            color = self.colors['hp_yellow']
        else:
            color = self.colors['hp_red']

        # Barra de progresso
        bar_width = int(width * hp_percent)
        if bar_width > 0:
            pygame.draw.rect(screen, color, (x, y, bar_width, height), border_radius=6)

        # Texto do HP
        font_small = pygame.font.Font(None, 16)
        hp_text = font_small.render(f"{self.pokemon.current_hp}/{self.pokemon.max_hp}", True, self.colors['text_secondary'])
        screen.blit(hp_text, (x + width + 10, y - 2))

    def _draw_stat_bar(self, screen, stat_name, stat_value, max_value=255, x=0, y=0):
        """Desenha uma barra de stat"""
        font_small = pygame.font.Font(None, 14)

        # Nome do stat
        name_text = font_small.render(stat_name, True, self.colors['text_secondary'])
        screen.blit(name_text, (x, y))

        # Valor
        value_text = font_small.render(str(stat_value), True, self.colors['text_accent'])
        screen.blit(value_text, (x + 45, y))

        # Barra
        bar_width = 120
        bar_height = 6
        bar_x = x + 75
        bar_y = y + 2

        percent = min(1.0, stat_value / max_value)
        pygame.draw.rect(screen, (50, 50, 60), (bar_x, bar_y, bar_width, bar_height), border_radius=3)
        pygame.draw.rect(screen, (100, 150, 200), (bar_x, bar_y, int(bar_width * percent), bar_height), border_radius=3)

    def _draw_move_card(self, screen, move, index, x, y, width):
        """Desenha um card individual de move"""
        # Fundo do move
        move_rect = pygame.Rect(x, y, width, 70)
        self._draw_rounded_rect(screen, self.colors['move_bg'], move_rect, radius=6)
        self._draw_rounded_rect(screen, self.colors['move_border'], move_rect, radius=6, border=1)

        # Nome do move
        font_name = pygame.font.Font(None, 18)
        name_text = font_name.render(move.name.upper(), True, self.colors['text_accent'])
        screen.blit(name_text, (x + 10, y + 8))

        # Tipo do move
        type_color = self._get_type_color(move.type)
        type_rect = pygame.Rect(x + 10, y + 32, 55, 20)
        pygame.draw.rect(screen, type_color, type_rect, border_radius=4)
        font_small = pygame.font.Font(None, 12)
        type_text = font_small.render(move.type.upper(), True, (255, 255, 255))
        screen.blit(type_text, (type_rect.x + 3, type_rect.y + 4))

        # Categoria (físico/especial/status)
        category_colors = {
            'physical': (200, 100, 100),
            'special': (100, 100, 200),
            'status': (100, 200, 100)
        }
        cat_color = category_colors.get(move.category, (150, 150, 150))
        category_rect = pygame.Rect(x + 72, y + 32, 55, 20)
        pygame.draw.rect(screen, cat_color, category_rect, border_radius=4)
        category_text = font_small.render(move.category[:3].upper(), True, (255, 255, 255))
        screen.blit(category_text, (category_rect.x + 3, category_rect.y + 4))

        # Poder
        if move.power > 0:
            power_text = font_small.render(f"PWR: {move.power}", True, self.colors['text_secondary'])
            screen.blit(power_text, (x + 10, y + 55))

        # PP
        pp_text = font_small.render(f"PP: {move.current_pp}/{move.max_pp}", True, self.colors['move_pp_text'])
        screen.blit(pp_text, (x + width - 70, y + 55))

        # Precisão
        acc_text = font_small.render(f"ACC: {move.accuracy}", True, self.colors['text_secondary'])
        screen.blit(acc_text, (x + width - 130, y + 55))

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

        # Cabeçalho com gradiente
        header_rect = pygame.Rect(self.x, self.y, self.width, 80)
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

        # ===== LADO ESQUERDO - SPRITE E TIPOS =====
        left_x = self.x + 30
        left_y = self.y + 30

        # Sprite do Pokémon
        sprite = self.pokedex.get_sprite(self.pokemon.id, "front", self.pokemon.is_shiny)
        if sprite:
            sprite_big = pygame.transform.scale(sprite, (140, 140))
            screen.blit(sprite_big, (left_x, left_y))

        # Nome e nível
        title_font = pygame.font.Font(None, 36)
        name_text = title_font.render(f"{self.pokemon.name}", True, self.colors['text_primary'])
        screen.blit(name_text, (left_x + 160, left_y + 20))

        level_font = pygame.font.Font(None, 28)
        level_text = level_font.render(f"Lv.{self.pokemon.level}", True, self.colors['text_accent'])
        screen.blit(level_text, (left_x + 160, left_y + 55))

        # Tipos
        type_y = left_y + 95
        for i, type_name in enumerate(self.pokemon.types):
            type_color = self._get_type_color(type_name)
            type_rect = pygame.Rect(left_x + 160 + (i * 85), type_y, 75, 28)
            pygame.draw.rect(screen, type_color, type_rect, border_radius=6)
            pygame.draw.rect(screen, (200, 200, 200), type_rect, 1, border_radius=6)

            type_text = pygame.font.Font(None, 16).render(type_name.upper(), True, (255, 255, 255))
            type_rect_text = type_text.get_rect(center=type_rect.center)
            screen.blit(type_text, type_rect_text)

        # Natureza
        nature_font = pygame.font.Font(None, 20)
        nature_text = nature_font.render(f"Natureza: {self.pokemon.nature}", True, self.colors['text_secondary'])
        screen.blit(nature_text, (left_x + 160, type_y + 45))

        # HP Bar
        hp_y = left_y + 165
        hp_label = pygame.font.Font(None, 18).render("HP", True, self.colors['text_secondary'])
        screen.blit(hp_label, (left_x + 160, hp_y))
        self._draw_hp_bar(screen, left_x + 190, hp_y, width=180, height=12)

        # ===== LADO DIREITO - STATS =====
        right_x = self.x + self.width - 280
        stats_y = self.y + 30

        stats_title = pygame.font.Font(None, 24).render("STATS", True, self.colors['text_accent'])
        screen.blit(stats_title, (right_x, stats_y))

        # Barras de stats
        stats = [
            ("ATK", self.pokemon.attack),
            ("DEF", self.pokemon.defense),
            ("SPA", self.pokemon.sp_attack),
            ("SPD", self.pokemon.sp_defense),
            ("VEL", self.pokemon.speed_stat)
        ]

        stat_start_y = stats_y + 35
        for i, (name, value) in enumerate(stats):
            self._draw_stat_bar(screen, name, value, max_value=255,
                                x=right_x, y=stat_start_y + (i * 25))

        # IVs
        iv_y = stat_start_y + 140
        iv_title = pygame.font.Font(None, 20).render("IVs", True, self.colors['text_accent'])
        screen.blit(iv_title, (right_x, iv_y))

        iv_values = [
            f"HP:{self.pokemon.ivs.get('hp', 0)}",
            f"ATK:{self.pokemon.ivs.get('attack', 0)}",
            f"DEF:{self.pokemon.ivs.get('defense', 0)}",
            f"SPA:{self.pokemon.ivs.get('special_attack', 0)}",
            f"SPD:{self.pokemon.ivs.get('special_defense', 0)}",
            f"VEL:{self.pokemon.ivs.get('speed', 0)}"
        ]

        iv_font = pygame.font.Font(None, 14)
        for i, iv in enumerate(iv_values):
            col = i % 3
            row = i // 3
            iv_x = right_x + (col * 70)
            iv_y_pos = iv_y + 25 + (row * 22)

            # Cor baseada no valor
            value = int(iv.split(':')[1])
            if value >= 31:
                color = (255, 100, 100)
            elif value >= 20:
                color = (255, 200, 100)
            else:
                color = (150, 150, 150)

            iv_surf = iv_font.render(iv, True, color)
            screen.blit(iv_surf, (iv_x, iv_y_pos))

        # ===== SEÇÃO DE MOVES =====
        moves_y = left_y + 220

        # Título da seção
        moves_title = pygame.font.Font(None, 28).render("MOVES", True, self.colors['text_accent'])
        screen.blit(moves_title, (left_x, moves_y))

        # Linha separadora
        pygame.draw.line(screen, self.colors['border'],
                         (left_x, moves_y + 35),
                         (self.x + self.width - 30, moves_y + 35), 2)

        # Exibe os 4 moves
        moves_start_y = moves_y + 50
        move_card_width = (self.width - 80) // 2  # 2 colunas

        for i, move in enumerate(self.pokemon.moves[:4]):  # Mostra até 4 moves
            col = i % 2
            row = i // 2
            card_x = left_x + (col * (move_card_width + 20))
            card_y = moves_start_y + (row * 80)

            self._draw_move_card(screen, move, i, card_x, card_y, move_card_width)

        # Se tiver menos de 4 moves, mostra slots vazios
        for i in range(len(self.pokemon.moves), 4):
            col = i % 2
            row = i // 2
            card_x = left_x + (col * (move_card_width + 20))
            card_y = moves_start_y + (row * 80)

            empty_rect = pygame.Rect(card_x, card_y, move_card_width, 70)
            self._draw_rounded_rect(screen, (30, 30, 40), empty_rect, radius=6)
            self._draw_rounded_rect(screen, (60, 60, 70), empty_rect, radius=6, border=1)

            empty_font = pygame.font.Font(None, 14)
            empty_text = empty_font.render("-- Vazio --", True, (80, 80, 90))
            text_rect = empty_text.get_rect(center=empty_rect.center)
            screen.blit(empty_text, text_rect)

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
            shiny_text = pygame.font.Font(None, 24).render("✨ SHINY ✨", True, (255, 215, 0))
            shiny_rect = shiny_text.get_rect(center=(self.x + self.width - 100, self.y + 45))
            screen.blit(shiny_text, shiny_rect)

            # Brilho ao redor do sprite
            if sprite:
                glow = pygame.Surface((150, 150), pygame.SRCALPHA)
                pygame.draw.circle(glow, (255, 215, 0, 80), (75, 75), 75)
                screen.blit(glow, (left_x - 5, left_y - 5))