# src/ui/pokemon_modal.py

import pygame
import random
import math
from src.data.pokedex import Pokedex
from src.battle.effects.effect_factory import EffectFactory
from src.data.move_data import MoveData


class PokemonModal:
    def __init__(self, game, pokemon):
        self.game = game
        self.pokemon = pokemon
        self.pokedex = Pokedex()
        self.move_data = MoveData()
        self.visible = True
        self.current_page = 0
        self.total_pages = 3
        self.confirmation_active = False
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
            'iv_great': (80, 200, 80),
            'iv_good': (80, 150, 220),
            'iv_median': (100, 130, 200),
            'iv_bad': (220, 100, 80),
            'iv_very_bad': (180, 60, 60),
            'iv_horrible': (160, 80, 200)
        }

    def _get_iv_rank(self, value):
        if value == 31:
            return "PERFEITO", self.colors['iv_perfect']
        elif value >= 27:
            return "MUITO BOM", self.colors['iv_great']
        elif value >= 22:
            return "BOM", self.colors['iv_good']
        elif value >= 16:
            return "MEDIANO", self.colors['iv_median']
        elif value >= 9:
            return "RUIM", self.colors['iv_bad']
        elif value >= 1:
            return "MUITO RUIM", self.colors['iv_very_bad']
        else:
            return "HORRIVEL", self.colors['iv_horrible']

    def _setup_dimensions(self):
        self.width = int(self.game.screen_manager.window_width * 0.85)
        self.height = int(self.game.screen_manager.window_height * 0.9)
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

        button_width = 165
        button_height = 44
        button_spacing = 15

        total_buttons_width = (button_width * 2) + button_spacing
        start_x = self.x + (self.width - total_buttons_width) // 2

        self.action_button = pygame.Rect(
            start_x,
            self.y + self.height - 60,
            button_width,
            button_height
        )

        self.release_button = pygame.Rect(
            start_x + button_width + button_spacing,
            self.y + self.height - 60,
            button_width,
            button_height
        )

        confirm_width = 110
        confirm_height = 40
        confirm_spacing = 20
        confirm_y = self.y + self.height - 130

        confirm_start_x = self.x + (self.width - (confirm_width * 2 + confirm_spacing)) // 2

        self.confirm_yes_button = pygame.Rect(
            confirm_start_x,
            confirm_y,
            confirm_width,
            confirm_height
        )

        self.confirm_no_button = pygame.Rect(
            confirm_start_x + confirm_width + confirm_spacing,
            confirm_y,
            confirm_width,
            confirm_height
        )

    def _create_shiny_particles(self, sprite_x, sprite_y, sprite_size):
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
        for particle in self.particles[:]:
            particle['x'] += particle['vx']
            particle['y'] += particle['vy']
            particle['life'] -= 0.01
            if particle['life'] <= 0:
                self.particles.remove(particle)

    def _draw_shiny_particles(self, screen):
        for particle in self.particles:
            color = (particle['color'][0], particle['color'][1], particle['color'][2])
            pygame.draw.circle(screen, color,
                               (int(particle['x']), int(particle['y'])),
                               particle['size'])

    def _get_move_description(self, move_name: str) -> str:
        """Obtém a descrição do movimento (prioridade: EffectFactory -> MoveData)"""
        move_key = move_name.lower().replace(" ", "-").replace("'", "")

        # Tenta EffectFactory
        effect = EffectFactory.create_effect(move_key)
        if effect and hasattr(effect, 'description') and effect.description:
            desc = effect.description
            # Limita tamanho para caber no card
            if len(desc) > 85:
                desc = desc[:82] + "..."
            return desc

        # Tenta configuração direta
        config = EffectFactory.MOVE_EFFECTS.get(move_key)
        if config and config.get("description"):
            desc = config["description"]
            if len(desc) > 85:
                desc = desc[:82] + "..."
            return desc

        # Tenta MoveData
        move_info = self.move_data.get_move_info(move_name)
        if move_info and move_info.get("description"):
            desc = move_info["description"]
            if desc and not desc.startswith(f"Usa {move_name}"):
                if len(desc) > 85:
                    desc = desc[:82] + "..."
                return desc

        return "Um movimento que causa dano ao oponente."

    def handle_event(self, event):
        if not self.visible:
            return None

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.close_button.collidepoint(event.pos):
                self.visible = False
                self.confirmation_active = False
                return "close"

            if self.prev_page_button.collidepoint(event.pos) and self.current_page > 0:
                self.current_page -= 1
                self.confirmation_active = False
                return None

            if self.next_page_button.collidepoint(event.pos) and self.current_page < self.total_pages - 1:
                self.current_page += 1
                self.confirmation_active = False
                return None

            if self.confirmation_active:
                if self.confirm_yes_button.collidepoint(event.pos):
                    self.confirmation_active = False
                    return "release_confirm"
                elif self.confirm_no_button.collidepoint(event.pos):
                    self.confirmation_active = False
                    return None
                return None

            if self.action_button.collidepoint(event.pos):
                if not self.pokemon.is_in_team and len(self.game.player.team) >= 6:
                    return None
                return "action"

            if self.release_button.collidepoint(event.pos):
                self.confirmation_active = True
                return None

            if not self.rect.collidepoint(event.pos):
                self.visible = False
                self.confirmation_active = False
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
        """Renderiza um card de movimento - PP e Categoria alinhados à direita"""
        card_height = 135
        move_rect = pygame.Rect(x, y, width, card_height)

        # Fundo do card
        self._draw_rounded_rect(screen, self.colors['move_bg'], move_rect, radius=10)
        self._draw_rounded_rect(screen, self.colors['move_border'], move_rect, radius=10, border=2)

        # Nome do movimento (esquerda)
        name_font = pygame.font.Font(None, 20)
        name_text = name_font.render(move.name.upper(), True, self.colors['text_accent'])
        screen.blit(name_text, (x + 12, y + 10))

        # Badge do tipo (direita)
        type_color = self._get_type_color(move.type)
        type_rect = pygame.Rect(x + width - 75, y + 8, 65, 26)
        pygame.draw.rect(screen, type_color, type_rect, border_radius=8)
        type_font = pygame.font.Font(None, 14)
        type_text = type_font.render(move.type.upper(), True, (255, 255, 255))
        screen.blit(type_text, (type_rect.centerx - type_text.get_width() // 2,
                                type_rect.centery - type_text.get_height() // 2))

        # Stats do movimento
        stats_font = pygame.font.Font(None, 14)
        stats_y = y + 44

        # Poder (esquerda)
        power_text = stats_font.render(f"Poder: {move.power if move.power > 0 else '--'}", True,
                                       self.colors['text_primary'])
        screen.blit(power_text, (x + 12, stats_y))

        # Acerto (esquerda)
        acc_text = stats_font.render(f"Acerto: {move.accuracy}%", True, self.colors['text_primary'])
        screen.blit(acc_text, (x + 12, stats_y + 20))

        # PP (direita - alinhado com o tipo)
        pp_text = stats_font.render(f"PP: {move.current_pp}/{move.max_pp}", True,
                                    self.colors['move_pp_text'])
        pp_width = pp_text.get_width()
        screen.blit(pp_text, (x + width - pp_width - 12, stats_y))

        # Categoria (direita - abaixo do PP)
        if move.power > 0:
            category = "FÍSICO" if move.category == "physical" else "ESPECIAL"
            cat_color = (255, 180, 100) if move.category == "physical" else (100, 180, 255)
        else:
            category = "STATUS"
            cat_color = (180, 180, 180)

        cat_text = stats_font.render(category, True, cat_color)
        cat_width = cat_text.get_width()
        screen.blit(cat_text, (x + width - cat_width - 12, stats_y + 20))

        # Linha separadora
        separator_y = y + 88
        pygame.draw.line(screen, self.colors['border'],
                         (x + 10, separator_y), (x + width - 10, separator_y), 1)

        # Descrição do movimento
        desc = self._get_move_description(move.name)
        desc_font = pygame.font.Font(None, 18)

        # Quebra a descrição em até 2 linhas
        words = desc.split()
        lines = []
        current_line = []
        current_width = 0
        max_width = width - 24

        for word in words:
            test_line = current_line + [word]
            test_text = " ".join(test_line)
            test_width = desc_font.size(test_text)[0]

            if test_width <= max_width:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(" ".join(current_line))
                current_line = [word]

        if current_line:
            lines.append(" ".join(current_line))

        # Mostra até 2 linhas de descrição
        desc_y = separator_y + 8
        for idx, line in enumerate(lines[:2]):
            line_surface = desc_font.render(line, True, self.colors['text_secondary'])
            screen.blit(line_surface, (x + 12, desc_y + (idx * 16)))

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
        close_text = close_font.render("x", True, self.colors['text_secondary'])
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
        prev_text = page_font.render("<", True, self.colors['text_primary'] if prev_active else (60, 65, 75))
        next_text = page_font.render(">", True, self.colors['text_primary'] if next_active else (60, 65, 75))
        screen.blit(prev_text, (self.prev_page_button.centerx - 8, self.prev_page_button.centery - 11))
        screen.blit(next_text, (self.next_page_button.centerx - 8, self.next_page_button.centery - 11))

        if self.confirmation_active:
            confirm_overlay = pygame.Surface((self.width, self.height))
            confirm_overlay.set_alpha(200)
            confirm_overlay.fill((0, 0, 0))
            screen.blit(confirm_overlay, (self.x, self.y))

            confirm_box = pygame.Rect(
                self.x + self.width // 4,
                self.y + self.height // 3,
                self.width // 2,
                110
            )
            self._draw_rounded_rect(screen, self.colors['bg_secondary'], confirm_box, radius=12)
            self._draw_rounded_rect(screen, self.colors['border'], confirm_box, radius=12, border=2)

            confirm_font = pygame.font.Font(None, 20)
            confirm_text = confirm_font.render("Tem certeza que deseja LIBERTAR este Pokémon?", True, (255, 200, 200))
            confirm_rect = confirm_text.get_rect(center=(confirm_box.centerx, confirm_box.y + 30))
            screen.blit(confirm_text, confirm_rect)

            warning_font = pygame.font.Font(None, 14)
            warning_text = warning_font.render("Esta ação é IRREVERSÍVEL!", True, (255, 100, 100))
            warning_rect = warning_text.get_rect(center=(confirm_box.centerx, confirm_box.y + 55))
            screen.blit(warning_text, warning_rect)

            pokemon_font = pygame.font.Font(None, 18)
            pokemon_text = pokemon_font.render(f"{self.pokemon.name} Lv.{self.pokemon.level}", True,
                                               self.colors['text_accent'])
            pokemon_rect = pokemon_text.get_rect(center=(confirm_box.centerx, confirm_box.y + 78))
            screen.blit(pokemon_text, pokemon_rect)

            self._draw_rounded_rect(screen, (180, 60, 60), self.confirm_yes_button, radius=8)
            self._draw_rounded_rect(screen, (220, 80, 80), self.confirm_yes_button, radius=8, border=1)
            sim_font = pygame.font.Font(None, 18)
            sim_text = sim_font.render("SIM, LIBERTAR", True, (255, 255, 255))
            sim_rect = sim_text.get_rect(center=self.confirm_yes_button.center)
            screen.blit(sim_text, sim_rect)

            self._draw_rounded_rect(screen, (60, 60, 80), self.confirm_no_button, radius=8)
            self._draw_rounded_rect(screen, (80, 80, 100), self.confirm_no_button, radius=8, border=1)
            nao_font = pygame.font.Font(None, 18)
            nao_text = nao_font.render("NÃO, CANCELAR", True, (255, 255, 255))
            nao_rect = nao_text.get_rect(center=self.confirm_no_button.center)
            screen.blit(nao_text, nao_rect)
            return

        if self.pokemon.is_in_team:
            button_color = (120, 60, 60)
            button_text = "REMOVER DO TIME"
        else:
            if len(self.game.player.team) < 6:
                button_color = (60, 120, 60)
                button_text = "ADICIONAR AO TIME"
            else:
                button_color = (55, 58, 65)
                button_text = "TIME CHEIO"

        self._draw_rounded_rect(screen, button_color, self.action_button, radius=10)
        self._draw_rounded_rect(screen, (100, 105, 115), self.action_button, radius=10, border=1)

        action_font = pygame.font.Font(None, 15)
        action_surf = action_font.render(button_text, True, (255, 255, 255))
        action_rect = action_surf.get_rect(center=self.action_button.center)
        screen.blit(action_surf, action_rect)

        release_color = (150, 40, 40) if self.pokemon.is_in_team else (180, 50, 50)
        self._draw_rounded_rect(screen, release_color, self.release_button, radius=10)
        self._draw_rounded_rect(screen, (200, 70, 70), self.release_button, radius=10, border=1)

        release_font = pygame.font.Font(None, 15)
        release_surf = release_font.render("LIBERTAR", True, (255, 255, 255))
        release_rect = release_surf.get_rect(center=self.release_button.center)
        screen.blit(release_surf, release_rect)

    def _calculate_actual_ev_bonus(self, stat: str) -> int:
        ev_value = self.pokemon.evs.get(stat, 0)
        ev_bonus_raw = ev_value // 8

        if ev_bonus_raw == 0:
            return 0

        base = self.pokemon.base_stats[stat]
        iv = self.pokemon.ivs.get(stat, 0)
        level = self.pokemon.level

        if stat == 'hp':
            stat_with_evs = ((2 * base + iv + ev_bonus_raw) * level) // 100 + level + 10
            stat_without_evs = ((2 * base + iv) * level) // 100 + level + 10
        else:
            stat_with_evs = ((2 * base + iv + ev_bonus_raw) * level) // 100 + 5
            stat_without_evs = ((2 * base + iv) * level) // 100 + 5

        return stat_with_evs - stat_without_evs

    def _render_stats_page(self, screen, content_rect):
        section_font = pygame.font.Font(None, 18)

        left_width = content_rect.width * 0.48
        right_width = content_rect.width * 0.48
        left_col = pygame.Rect(content_rect.x, content_rect.y, left_width, content_rect.height)
        right_col = pygame.Rect(content_rect.x + left_width + 15, content_rect.y, right_width, content_rect.height)

        stats_title = section_font.render("STATS ATUAIS", True, self.colors['text_accent'])
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

        stat_start_y = left_col.y + 20
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
            nature_text = pygame.font.Font(None, 16).render(f"NATUREZA: {self.pokemon.nature}", True,
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

        iv_start_y = right_col.y + 20
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

                if value == 31:
                    bar_color = self.colors['iv_perfect']
                elif value >= 27:
                    bar_color = self.colors['iv_great']
                elif value >= 22:
                    bar_color = self.colors['iv_good']
                elif value >= 16:
                    bar_color = self.colors['iv_median']
                elif value >= 9:
                    bar_color = self.colors['iv_bad']
                elif value >= 1:
                    bar_color = self.colors['iv_very_bad']
                else:
                    bar_color = self.colors['iv_horrible']

                pygame.draw.rect(screen, (45, 48, 55), (bar_x, bar_y, bar_width, bar_height), border_radius=4)
                if value > 0:
                    pygame.draw.rect(screen, bar_color, (bar_x, bar_y, int(bar_width * percent), bar_height),
                                     border_radius=4)

                rank_text, rank_color = self._get_iv_rank(value)
                rank_surf = rank_font.render(rank_text, True, rank_color)
                screen.blit(rank_surf, (card_rect.x + card_rect.width - rank_surf.get_width() - 12, card_rect.y + 18))

        ev_section_y = iv_start_y + 5 + (len(iv_list) * iv_spacing)

        if ev_section_y < right_col.bottom:
            ev_title = section_font.render("ESFORCO (EVs)", True, self.colors['text_accent'])
            ev_title_x = right_col.x + (right_col.width - ev_title.get_width()) // 2
            screen.blit(ev_title, (ev_title_x, ev_section_y))

            pygame.draw.line(screen, self.colors['border'], (right_col.x + 10, ev_section_y + 22),
                             (right_col.x + right_col.width - 10, ev_section_y + 22), 1)

            ev_font = pygame.font.Font(None, 13)
            value_font = pygame.font.Font(None, 15)
            bonus_font = pygame.font.Font(None, 12)

            ev_stats = [
                ("HP", self.pokemon.evs.get('hp', 0), 'hp'),
                ("ATAQUE", self.pokemon.evs.get('attack', 0), 'attack'),
                ("DEFESA", self.pokemon.evs.get('defense', 0), 'defense'),
                ("SP. ATAQUE", self.pokemon.evs.get('special_attack', 0), 'special_attack'),
                ("SP. DEFESA", self.pokemon.evs.get('special_defense', 0), 'special_defense'),
                ("VELOCIDADE", self.pokemon.evs.get('speed', 0), 'speed')
            ]

            row_height = 35
            cols = 2
            card_width = (right_col.width - 30) // cols

            for idx, (name, ev_value, stat_key) in enumerate(ev_stats):
                row = idx // cols
                col = idx % cols

                card_x = right_col.x + 10 + (col * (card_width + 10))
                card_y = ev_section_y + 20 + (row * row_height)

                if card_y + row_height < right_col.bottom:
                    card_rect = pygame.Rect(card_x, card_y, card_width, row_height - 5)

                    if ev_value > 0:
                        self._draw_rounded_rect(screen, self.colors['bg_tertiary'], card_rect, radius=6)
                    else:
                        self._draw_rounded_rect(screen, (25, 27, 32), card_rect, radius=6)

                    name_text = ev_font.render(name, True, self.colors['text_secondary'])
                    screen.blit(name_text, (card_rect.x + 12, card_rect.y + 10))

                    if ev_value > 0:
                        if ev_value >= 252:
                            ev_color = self.colors['iv_perfect']
                        elif ev_value >= 200:
                            ev_color = self.colors['iv_great']
                        elif ev_value >= 126:
                            ev_color = self.colors['iv_good']
                        elif ev_value >= 64:
                            ev_color = self.colors['iv_median']
                        else:
                            ev_color = self.colors['text_primary']
                    else:
                        ev_color = (60, 65, 75)

                    value_text = value_font.render(str(ev_value), True, ev_color)
                    screen.blit(value_text, (card_rect.centerx - 20, card_rect.y + 9))

                    actual_bonus = self._calculate_actual_ev_bonus(stat_key)

                    if actual_bonus > 0:
                        bonus_text = f"(+{actual_bonus})"
                        bonus_color = self.colors['text_good']
                    else:
                        bonus_text = "(+0)"
                        bonus_color = (60, 65, 75)

                    bonus_surf = bonus_font.render(bonus_text, True, bonus_color)
                    screen.blit(bonus_surf, (card_rect.x + card_width - bonus_surf.get_width() - 12, card_rect.y + 10))

            total_evs = self.pokemon.stats.get_ev_total()
            max_evs = self.pokemon.stats.MAX_TOTAL_EVS
            ev_percent = total_evs / max_evs if max_evs > 0 else 0

            total_font = pygame.font.Font(None, 12)

            if ev_percent >= 0.9:
                total_color = self.colors['iv_perfect']
            elif ev_percent >= 0.5:
                total_color = self.colors['iv_great']
            else:
                total_color = self.colors['text_accent']

            total_text = total_font.render(f"TOTAL: {total_evs}/{max_evs} EVs ({ev_percent * 100:.1f}%)",
                                           True, total_color)

            total_y = ev_section_y + 20 + (3 * row_height) + 5
            if total_y + 0 < right_col.bottom:
                screen.blit(total_text, (right_col.centerx - total_text.get_width() // 2, total_y))

                bar_width = right_col.width - 40
                bar_height = 10
                bar_x = right_col.x + 20
                bar_y = total_y + 15

                pygame.draw.rect(screen, (45, 48, 55), (bar_x, bar_y, bar_width, bar_height), border_radius=5)
                if total_evs > 0:
                    pygame.draw.rect(screen, (100, 180, 200),
                                     (bar_x, bar_y, int(bar_width * ev_percent), bar_height), border_radius=5)

    def _render_moves_page(self, screen, content_rect):
        """Renderiza página de moves - Layout 2x2 como nos jogos originais"""
        section_font = pygame.font.Font(None, 24)
        moves_title = section_font.render("MOVIMENTOS", True, self.colors['text_accent'])
        moves_title_x = content_rect.x + (content_rect.width - moves_title.get_width()) // 2
        screen.blit(moves_title, (moves_title_x, content_rect.y))

        pygame.draw.line(screen, self.colors['border'], (content_rect.x + 10, content_rect.y + 32),
                         (content_rect.x + content_rect.width - 10, content_rect.y + 32), 2)

        # Layout 2 colunas
        cards_per_row = 2
        card_width = (content_rect.width - 30) // cards_per_row
        card_height = 135
        start_x = content_rect.x
        start_y = content_rect.y + 50
        spacing = 15

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
                    self._draw_rounded_rect(screen, (25, 27, 32), empty_rect, radius=10)
                    self._draw_rounded_rect(screen, (40, 43, 50), empty_rect, radius=10, border=2)
                    empty_font = pygame.font.Font(None, 14)
                    empty_text = empty_font.render("─ VAZIO ─", True, (80, 85, 95))
                    text_rect = empty_text.get_rect(center=empty_rect.center)
                    screen.blit(empty_text, text_rect)

    def _render_info_page(self, screen, content_rect):
        """Renderiza página de informações - ORGANIZADA com Felicidade e Nome Personalizado"""

        # ===== FONTES AUMENTADAS =====
        title_font = pygame.font.Font(None, 28)  # Aumentado de 22 para 28
        section_title_font = pygame.font.Font(None, 20)  # Aumentado de 16 para 20
        label_font = pygame.font.Font(None, 16)  # Aumentado de 13 para 16
        value_font = pygame.font.Font(None, 18)  # Aumentado de 15 para 18
        type_font = pygame.font.Font(None, 13)  # Aumentado de 11 para 13

        # Título da página
        info_title = title_font.render("INFORMAÇÕES DETALHADAS", True, self.colors['text_accent'])
        info_title_x = content_rect.x + (content_rect.width - info_title.get_width()) // 2
        screen.blit(info_title, (info_title_x, content_rect.y))

        pygame.draw.line(screen, self.colors['border'],
                         (content_rect.x + 10, content_rect.y + 34),
                         (content_rect.x + content_rect.width - 10, content_rect.y + 34), 2)

        # Layout em 2 colunas
        card_width = (content_rect.width - 25) // 2
        card_height = content_rect.height - 55

        left_card = pygame.Rect(content_rect.x, content_rect.y + 50, card_width, card_height)
        right_card = pygame.Rect(content_rect.x + card_width + 15, content_rect.y + 50, card_width, card_height)

        # Fundo dos cards
        self._draw_rounded_rect(screen, self.colors['bg_secondary'], left_card, radius=12)
        self._draw_rounded_rect(screen, self.colors['border'], left_card, radius=12, border=1)
        self._draw_rounded_rect(screen, self.colors['bg_secondary'], right_card, radius=12)
        self._draw_rounded_rect(screen, self.colors['border'], right_card, radius=12, border=1)

        # ===== COLUNA ESQUERDA: Identificação =====
        left_title = section_title_font.render("IDENTIFICAÇÃO", True, self.colors['text_accent'])
        screen.blit(left_title, (left_card.x + (left_card.width - left_title.get_width()) // 2, left_card.y + 12))

        pygame.draw.line(screen, self.colors['border'],
                         (left_card.x + 15, left_card.y + 38),
                         (left_card.x + left_card.width - 15, left_card.y + 38), 1)

        y_offset = left_card.y + 60
        line_spacing = 55

        # ===== ESPÉCIE (nome verdadeiro do Pokémon) =====
        label_text = label_font.render("ESPÉCIE", True, self.colors['text_secondary'])
        screen.blit(label_text, (left_card.x + 20, y_offset))

        # Exibe o nome da espécie (nome real do Pokémon)
        species_name = self.pokemon.name
        species_text = value_font.render(species_name, True, self.colors['text_primary'])
        screen.blit(species_text, (left_card.x + 20, y_offset + 24))
        y_offset += line_spacing

        # ===== APELIDO (nome personalizado pelo jogador) =====
        label_text = label_font.render("APELIDO", True, self.colors['text_secondary'])
        screen.blit(label_text, (left_card.x + 20, y_offset))

        if self.pokemon.custom_name:
            nickname = self.pokemon.custom_name.strip()
            nickname_text = value_font.render(f"{nickname}", True, self.colors['text_accent'])
        else:
            nickname_text = value_font.render("sem apelido", True, self.colors['text_secondary'])

        screen.blit(nickname_text, (left_card.x + 20, y_offset + 24))
        y_offset += line_spacing

        # ===== ID POKÉDEX =====
        label_text = label_font.render("ID POKÉDEX", True, self.colors['text_secondary'])
        screen.blit(label_text, (left_card.x + 20, y_offset))

        value_text = value_font.render(f"#{self.pokemon.id:04d}", True, self.colors['text_accent'])
        screen.blit(value_text, (left_card.x + 20, y_offset + 24))
        y_offset += line_spacing

        # ===== LOCALIZAÇÃO =====
        if hasattr(self.game.player, 'pc_box'):
            label_text = label_font.render("LOCALIZAÇÃO", True, self.colors['text_secondary'])
            screen.blit(label_text, (left_card.x + 20, y_offset))

            if self.pokemon.is_in_team:
                position = self.game.player.team.index(self.pokemon) + 1
                location_text = f"No time (posição {position})"
                location_color = self.colors['text_good']
            else:
                location_text = "Na box do PC"
                location_color = self.colors['text_secondary']

            value_text = value_font.render(location_text, True, location_color)
            screen.blit(value_text, (left_card.x + 20, y_offset + 24))
            y_offset += line_spacing

        # ===== EXPERIÊNCIA =====
        label_text = label_font.render("EXPERIÊNCIA", True, self.colors['text_secondary'])
        screen.blit(label_text, (left_card.x + 20, y_offset))

        exp_text = f"{self.pokemon.xp} / {self.pokemon.xp_to_next}"
        value_text = value_font.render(exp_text, True, self.colors['text_primary'])
        screen.blit(value_text, (left_card.x + 20, y_offset + 24))

        # Barra de XP (SOMENTE A BARRA, SEM TEXTO DENTRO)
        exp_percent = self.pokemon.xp / self.pokemon.xp_to_next if self.pokemon.xp_to_next > 0 else 0
        bar_width = left_card.width - 40
        bar_height = 12
        bar_x = left_card.x + 20
        bar_y = y_offset + 44

        pygame.draw.rect(screen, (45, 48, 55), (bar_x, bar_y, bar_width, bar_height), border_radius=6)
        if exp_percent > 0:
            pygame.draw.rect(screen, (100, 180, 100),
                             (bar_x, bar_y, int(bar_width * exp_percent), bar_height), border_radius=6)
        y_offset += line_spacing

        # ===== PRÓXIMO NÍVEL =====
        label_text = label_font.render("PRÓXIMO NÍVEL", True, self.colors['text_secondary'])
        screen.blit(label_text, (left_card.x + 20, y_offset + 10))

        exp_needed = self.pokemon.xp_to_next - self.pokemon.xp
        value_text = value_font.render(f"{exp_needed} EXP restantes", True, self.colors['text_good'])
        screen.blit(value_text, (left_card.x + 20, y_offset + 34))

        # ===== COLUNA DIREITA: Características =====
        right_title = section_title_font.render("CARACTERÍSTICAS", True, self.colors['text_accent'])
        screen.blit(right_title, (right_card.x + (right_card.width - right_title.get_width()) // 2, right_card.y + 12))

        pygame.draw.line(screen, self.colors['border'],
                         (right_card.x + 15, right_card.y + 38),
                         (right_card.x + right_card.width - 15, right_card.y + 38), 1)

        right_y = right_card.y + 60
        right_line_spacing = 55

        # ===== TIPOS =====
        label_text = label_font.render("TIPO(S)", True, self.colors['text_secondary'])
        screen.blit(label_text, (right_card.x + 20, right_y))

        # Renderiza badges de tipo
        type_badge_x = right_card.x + 120
        for i, type_name in enumerate(self.pokemon.types):
            type_color = self._get_type_color(type_name)
            type_badge = pygame.Rect(type_badge_x + (i * 80), right_y - 2, 72, 28)
            self._draw_rounded_rect(screen, type_color, type_badge, radius=8)
            type_text = type_font.render(type_name.upper(), True, (255, 255, 255))
            screen.blit(type_text, (type_badge.centerx - type_text.get_width() // 2,
                                    type_badge.centery - type_text.get_height() // 2))
        right_y += right_line_spacing

        # ===== NATUREZA =====
        label_text = label_font.render("NATUREZA", True, self.colors['text_secondary'])
        screen.blit(label_text, (right_card.x + 20, right_y))
        value_text = value_font.render(self.pokemon.nature, True, self.colors['text_primary'])
        screen.blit(value_text, (right_card.x + 20, right_y + 24))
        right_y += right_line_spacing

        # ===== SEXO =====
        label_text = label_font.render("SEXO", True, self.colors['text_secondary'])
        screen.blit(label_text, (right_card.x + 20, right_y))

        if hasattr(self.pokemon, 'gender'):
            if self.pokemon.gender == "male":
                gender_value = "MACHO"
                gender_color = (70, 120, 200)
            elif self.pokemon.gender == "female":
                gender_value = "FÊMEA"
                gender_color = (230, 80, 120)
            else:
                gender_value = "SEM GÊNERO"
                gender_color = self.colors['text_secondary']
        else:
            gender_value = "??? GÊNERO"
            gender_color = self.colors['text_secondary']

        value_text = value_font.render(gender_value, True, gender_color)
        screen.blit(value_text, (right_card.x + 20, right_y + 24))
        right_y += right_line_spacing

        # ===== ALTURA =====
        label_text = label_font.render("ALTURA", True, self.colors['text_secondary'])
        screen.blit(label_text, (right_card.x + 20, right_y))

        if hasattr(self.pokemon, 'height_m') and self.pokemon.height_m:
            height_value = f"{self.pokemon.height_m:.2f} m"
            # Mostra categoria de tamanho
            if self.pokemon.height_m < 0.5:
                height_category = "Muito pequeno"
            elif self.pokemon.height_m < 1.0:
                height_category = "Pequeno"
            elif self.pokemon.height_m < 1.5:
                height_category = "Médio"
            elif self.pokemon.height_m < 2.5:
                height_category = "Grande"
            else:
                height_category = "Muito grande"
        else:
            height_value = "??? m"
            height_category = "Desconhecido"

        value_text = value_font.render(height_value, True, self.colors['text_primary'])
        screen.blit(value_text, (right_card.x + 20, right_y + 24))
        category_text = label_font.render(f"({height_category})", True, self.colors['text_secondary'])
        screen.blit(category_text, (right_card.x + 80, right_y + 26))
        right_y += right_line_spacing

        # ===== PESO =====
        label_text = label_font.render("PESO", True, self.colors['text_secondary'])
        screen.blit(label_text, (right_card.x + 20, right_y))

        if hasattr(self.pokemon, 'weight_kg') and self.pokemon.weight_kg:
            weight_value = f"{self.pokemon.weight_kg:.1f} kg"
            if self.pokemon.weight_kg < 10:
                weight_category = "Leve"
            elif self.pokemon.weight_kg < 50:
                weight_category = "Médio"
            elif self.pokemon.weight_kg < 200:
                weight_category = "Pesado"
            else:
                weight_category = "Muito pesado"
        else:
            weight_value = "??? kg"
            weight_category = "Desconhecido"

        value_text = value_font.render(weight_value, True, self.colors['text_primary'])
        screen.blit(value_text, (right_card.x + 20, right_y + 24))
        category_text = label_font.render(f"({weight_category})", True, self.colors['text_secondary'])
        screen.blit(category_text, (right_card.x + 80, right_y + 26))
        right_y += right_line_spacing

        # ===== FELICIDADE =====
        label_text = label_font.render("FELICIDADE", True, self.colors['text_secondary'])
        screen.blit(label_text, (right_card.x + 20, right_y))

        happiness = self.pokemon.get_happiness()
        happiness_text = f"{happiness} / 100"

        # Determina a cor baseada na felicidade
        if happiness >= 80:
            happiness_color = (255, 215, 0)  # Dourado
        elif happiness >= 60:
            happiness_color = (100, 220, 100)  # Verde
        elif happiness >= 40:
            happiness_color = (255, 220, 100)  # Amarelo
        elif happiness >= 20:
            happiness_color = (255, 150, 100)  # Laranja
        else:
            happiness_color = (255, 100, 100)  # Vermelho

        # Mostra o valor numérico
        value_text = value_font.render(happiness_text, True, happiness_color)
        screen.blit(value_text, (right_card.x + 20 + 110, right_y + 2))

        # Barra de felicidade
        bar_width = right_card.width - 40
        bar_height = 12
        bar_x = right_card.x + 20
        bar_y = right_y + 32

        # Fundo da barra
        pygame.draw.rect(screen, (45, 48, 55), (bar_x, bar_y, bar_width, bar_height), border_radius=6)

        # Calcula largura da barra de felicidade
        happiness_width = int(bar_width * (happiness / 100))

        # Gradiente da barra (vermelho -> amarelo -> verde)
        if happiness_width > 0:
            if happiness <= 50:
                r = 255
                g = int(255 * (happiness / 50))
                b = 0
            else:
                r = int(255 * (1 - ((happiness - 50) / 50)))
                g = 255
                b = 0

            bar_color = (r, g, b)
            pygame.draw.rect(screen, bar_color, (bar_x, bar_y, happiness_width, bar_height), border_radius=6)

        # Borda da barra
        pygame.draw.rect(screen, self.colors['border_light'], (bar_x, bar_y, bar_width, bar_height), 2, border_radius=6)

        # Nível de felicidade em texto (SEM EMOJIS)
        if happiness >= 80:
            level_text = "Muito feliz!"
        elif happiness >= 60:
            level_text = "Feliz"
        elif happiness >= 40:
            level_text = "Normal"
        elif happiness >= 20:
            level_text = "Triste"
        else:
            level_text = "Muito triste!"

        level_surf = label_font.render(level_text, True, happiness_color)
        screen.blit(level_surf, (bar_x + bar_width - level_surf.get_width(), bar_y - 22))

        # ===== EFEITO BOSS (se for boss) =====
        if self.pokemon.is_boss:
            badge_y = right_card.y + right_card.height - 50
            boss_badge = pygame.Rect(right_card.x + 20, badge_y, right_card.width - 40, 40)
            self._draw_rounded_rect(screen, (180, 60, 60), boss_badge, radius=10)
            boss_text = pygame.font.Font(None, 16).render("⚡ POKÉMON CHEFE ⚡", True, (255, 255, 255))
            screen.blit(boss_text, (boss_badge.centerx - boss_text.get_width() // 2,
                                    boss_badge.centery - boss_text.get_height() // 2))