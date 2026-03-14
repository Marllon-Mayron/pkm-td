import pygame
from src.scenes.team_select_scene.utils.constants import COLORS, FONT_SIZES
from src.data.pokedex import Pokedex


class PokemonModal:
    def __init__(self, game, pokemon):
        self.game = game
        self.pokemon = pokemon
        self.pokedex = Pokedex()
        self.visible = True
        self._setup_dimensions()

    def _setup_dimensions(self):
        self.width = int(self.game.screen_manager.window_width * 0.7)
        self.height = int(self.game.screen_manager.window_height * 0.7)
        self.x = (self.game.screen_manager.window_width - self.width) // 2
        self.y = (self.game.screen_manager.window_height - self.height) // 2

        self.rect = pygame.Rect(self.x, self.y, self.width, self.height)
        self.close_button = pygame.Rect(self.x + self.width - 40, self.y + 10, 30, 30)

        button_width = 150
        button_height = 40
        self.action_button = pygame.Rect(
            self.x + (self.width - button_width) // 2,
            self.y + self.height - 70,
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
                return "action"

            if not self.rect.collidepoint(event.pos):
                self.visible = False
                return "close"

        return None

    def render(self, screen):
        if not self.visible:
            return

        self._draw_overlay(screen)
        self._draw_modal_background(screen)
        self._draw_close_button(screen)
        self._draw_pokemon_sprite(screen)
        self._draw_pokemon_info(screen)
        self._draw_types(screen)
        self._draw_stats(screen)
        self._draw_ivs(screen)
        self._draw_action_button(screen)
        self._draw_shiny_indicator(screen)

    def _draw_overlay(self, screen):
        overlay = pygame.Surface((
            self.game.screen_manager.window_width,
            self.game.screen_manager.window_height
        ))
        overlay.set_alpha(180)
        overlay.fill((0, 0, 0))
        screen.blit(overlay, (0, 0))

    def _draw_modal_background(self, screen):
        pygame.draw.rect(screen, COLORS['MODAL']['BACKGROUND'], self.rect, border_radius=15)
        pygame.draw.rect(screen, COLORS['MODAL']['BORDER'], self.rect, 3, border_radius=15)

    def _draw_close_button(self, screen):
        pygame.draw.rect(screen, COLORS['MODAL']['CLOSE_BUTTON'], self.close_button, border_radius=5)
        pygame.draw.rect(screen, COLORS['MODAL']['CLOSE_BORDER'], self.close_button, 2, border_radius=5)

        close_font = pygame.font.Font(None, 24)
        close_text = close_font.render("X", True, COLORS['TEXT']['WHITE'])
        close_rect = close_text.get_rect(center=self.close_button.center)
        screen.blit(close_text, close_rect)

    def _draw_pokemon_sprite(self, screen):
        sprite = self.pokedex.get_sprite(self.pokemon.id, "front", self.pokemon.is_shiny)
        if sprite:
            sprite_big = pygame.transform.scale(sprite, (120, 120))
            screen.blit(sprite_big, (self.x + 50, self.y + 50))

    def _draw_pokemon_info(self, screen):
        title_font = pygame.font.Font(None, FONT_SIZES['MODAL_TITLE'])

        name_text = title_font.render(
            f"{self.pokemon.name}  Lv.{self.pokemon.level}",
            True, COLORS['TEXT']['WHITE']
        )
        screen.blit(name_text, (self.x + 200, self.y + 60))

        text_font = pygame.font.Font(None, FONT_SIZES['MODAL_TEXT'])
        nature_text = text_font.render(
            f"Natureza: {self.pokemon.nature}",
            True, (200, 200, 150)
        )
        screen.blit(nature_text, (self.x + 200, self.y + 100))

    def _draw_types(self, screen):
        text_font = pygame.font.Font(None, FONT_SIZES['MODAL_TEXT'])
        type_x = self.x + 200
        type_y = self.y + 130

        for i, type_name in enumerate(self.pokemon.types):
            type_color = self.pokedex.get_type_color(type_name)
            pygame.draw.rect(screen, type_color, (type_x + (i * 80), type_y, 70, 25))
            pygame.draw.rect(screen, (200, 200, 200), (type_x + (i * 80), type_y, 70, 25), 1)

            type_text = text_font.render(type_name.upper(), True, COLORS['TEXT']['WHITE'])
            type_rect = type_text.get_rect(center=(type_x + (i * 80) + 35, type_y + 12))
            screen.blit(type_text, type_rect)

    def _draw_stats(self, screen):
        text_font = pygame.font.Font(None, FONT_SIZES['MODAL_TEXT'])
        stats_y = self.y + 180

        stats = [
            ("HP", self.pokemon.current_hp, self.pokemon.max_hp),
            ("Ataque", self.pokemon.attack, None),
            ("Defesa", self.pokemon.defense, None),
            ("Sp.Atk", self.pokemon.sp_attack, None),
            ("Sp.Def", self.pokemon.sp_defense, None),
            ("Vel.", self.pokemon.speed, None)
        ]

        for i, (stat_name, stat_value, stat_max) in enumerate(stats):
            col = i % 2
            row = i // 2
            stat_x = self.x + 50 + (col * 200)
            stat_y_pos = stats_y + (row * 40)

            stat_label = text_font.render(f"{stat_name}:", True, (180, 180, 180))
            screen.blit(stat_label, (stat_x, stat_y_pos))

            if stat_max:
                stat_value_text = text_font.render(f"{stat_value}/{stat_max}", True, COLORS['TEXT']['WHITE'])
            else:
                stat_value_text = text_font.render(str(stat_value), True, COLORS['TEXT']['WHITE'])
            screen.blit(stat_value_text, (stat_x + 80, stat_y_pos))

    def _draw_ivs(self, screen):
        text_font = pygame.font.Font(None, FONT_SIZES['MODAL_TEXT'])
        iv_y = self.y + 280

        iv_text = text_font.render("IVs:", True, (180, 180, 180))
        screen.blit(iv_text, (self.x + 50, iv_y))

        iv_values = [
            f"HP:{self.pokemon.ivs['hp']}",
            f"ATK:{self.pokemon.ivs['attack']}",
            f"DEF:{self.pokemon.ivs['defense']}",
            f"SPA:{self.pokemon.ivs['special_attack']}",
            f"SPD:{self.pokemon.ivs['special_defense']}",
            f"VEL:{self.pokemon.ivs['speed']}"
        ]

        for i, iv in enumerate(iv_values):
            col = i % 3
            row = i // 3
            iv_x = self.x + 100 + (col * 100)
            iv_y_pos = iv_y + 25 + (row * 25)

            iv_surf = text_font.render(iv, True, (200, 255, 200))
            screen.blit(iv_surf, (iv_x, iv_y_pos))

    def _draw_action_button(self, screen):
        if self.pokemon.is_in_team:
            button_color = COLORS['BUTTON']['MODAL_ACTION_REMOVE']
            button_text = "REMOVER DO TIME"
        else:
            if len(self.game.player.team) < 6:
                button_color = COLORS['BUTTON']['MODAL_ACTION_ADD']
                button_text = "ADICIONAR AO TIME"
            else:
                button_color = COLORS['BUTTON']['MODAL_ACTION_DISABLED']
                button_text = "TIME CHEIO"

        pygame.draw.rect(screen, button_color, self.action_button, border_radius=8)
        pygame.draw.rect(screen, (200, 200, 200), self.action_button, 2, border_radius=8)

        action_font = pygame.font.Font(None, 24)
        action_surf = action_font.render(button_text, True, COLORS['TEXT']['WHITE'])
        action_rect = action_surf.get_rect(center=self.action_button.center)
        screen.blit(action_surf, action_rect)

    def _draw_shiny_indicator(self, screen):
        if self.pokemon.is_shiny:
            shiny_font = pygame.font.Font(None, FONT_SIZES['MODAL_TITLE'])
            shiny_text = shiny_font.render("✨ SHINY ✨", True, COLORS['TEXT']['YELLOW'])
            shiny_rect = shiny_text.get_rect(center=(self.x + self.width - 100, self.y + 60))
            screen.blit(shiny_text, shiny_rect)