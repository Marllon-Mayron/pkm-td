import pygame
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
            # Botão fechar
            if self.close_button.collidepoint(event.pos):
                self.visible = False
                return "close"

            # Botão de ação
            if self.action_button.collidepoint(event.pos):
                return "action"

            # Clique fora do modal fecha
            if not self.rect.collidepoint(event.pos):
                self.visible = False
                return "close"

        return None

    def render(self, screen):
        if not self.visible:
            return

        # Overlay escuro atrás
        overlay = pygame.Surface((
            self.game.screen_manager.window_width,
            self.game.screen_manager.window_height
        ))
        overlay.set_alpha(180)
        overlay.fill((0, 0, 0))
        screen.blit(overlay, (0, 0))

        # Fundo do modal
        pygame.draw.rect(screen, (30, 30, 40), self.rect, border_radius=15)
        pygame.draw.rect(screen, (100, 100, 150), self.rect, 3, border_radius=15)

        # Botão fechar
        pygame.draw.rect(screen, (60, 60, 70), self.close_button, border_radius=5)
        pygame.draw.rect(screen, (150, 150, 150), self.close_button, 2, border_radius=5)
        close_font = pygame.font.Font(None, 24)
        close_text = close_font.render("X", True, (255, 255, 255))
        close_rect = close_text.get_rect(center=self.close_button.center)
        screen.blit(close_text, close_rect)

        # Sprite do Pokémon
        sprite = self.pokedex.get_sprite(self.pokemon.id, "front", self.pokemon.is_shiny)
        if sprite:
            sprite_big = pygame.transform.scale(sprite, (120, 120))
            screen.blit(sprite_big, (self.x + 50, self.y + 50))

        # Informações básicas
        title_font = pygame.font.Font(None, 32)
        text_font = pygame.font.Font(None, 24)
        small_font = pygame.font.Font(None, 20)

        # Nome e nível
        name_text = title_font.render(f"{self.pokemon.name}  Lv.{self.pokemon.level}",
                                      True, (255, 255, 255))
        screen.blit(name_text, (self.x + 200, self.y + 60))

        # Natureza
        nature_text = text_font.render(f"Natureza: {self.pokemon.nature}",
                                       True, (200, 200, 150))
        screen.blit(nature_text, (self.x + 200, self.y + 100))

        # Tipos
        type_x = self.x + 200
        type_y = self.y + 130
        for i, type_name in enumerate(self.pokemon.types):
            type_color = self.pokedex.get_type_color(type_name)
            pygame.draw.rect(screen, type_color, (type_x + (i * 80), type_y, 70, 25))
            pygame.draw.rect(screen, (200, 200, 200), (type_x + (i * 80), type_y, 70, 25), 1)

            type_text = small_font.render(type_name.upper(), True, (255, 255, 255))
            type_rect = type_text.get_rect(center=(type_x + (i * 80) + 35, type_y + 12))
            screen.blit(type_text, type_rect)

        # Stats
        stats_y = self.y + 180
        stats = [
            ("HP", f"{self.pokemon.current_hp}/{self.pokemon.max_hp}"),
            ("Ataque", str(self.pokemon.attack)),
            ("Defesa", str(self.pokemon.defense)),
            ("Sp.Atk", str(self.pokemon.sp_attack)),
            ("Sp.Def", str(self.pokemon.sp_defense)),
            ("Vel.", str(self.pokemon.speed))
        ]

        for i, (stat_name, stat_value) in enumerate(stats):
            col = i % 2
            row = i // 2

            stat_x = self.x + 50 + (col * 200)
            stat_y_pos = stats_y + (row * 35)

            stat_label = small_font.render(f"{stat_name}:", True, (180, 180, 180))
            screen.blit(stat_label, (stat_x, stat_y_pos))

            stat_value_text = small_font.render(stat_value, True, (255, 255, 255))
            screen.blit(stat_value_text, (stat_x + 80, stat_y_pos))

        # IVs
        iv_y = stats_y + 120
        iv_text = small_font.render("IVs:", True, (180, 180, 180))
        screen.blit(iv_text, (self.x + 50, iv_y))

        iv_values = [
            f"HP:{self.pokemon.ivs.get('hp', 0)}",
            f"ATK:{self.pokemon.ivs.get('attack', 0)}",
            f"DEF:{self.pokemon.ivs.get('defense', 0)}",
            f"SPA:{self.pokemon.ivs.get('special_attack', 0)}",
            f"SPD:{self.pokemon.ivs.get('special_defense', 0)}",
            f"VEL:{self.pokemon.ivs.get('speed', 0)}"
        ]

        for i, iv in enumerate(iv_values):
            col = i % 3
            row = i // 3
            iv_x = self.x + 100 + (col * 100)
            iv_y_pos = iv_y + 25 + (row * 25)

            iv_surf = small_font.render(iv, True, (200, 255, 200))
            screen.blit(iv_surf, (iv_x, iv_y_pos))

        # Botão de ação
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

        pygame.draw.rect(screen, button_color, self.action_button, border_radius=8)
        pygame.draw.rect(screen, (200, 200, 200), self.action_button, 2, border_radius=8)

        action_font = pygame.font.Font(None, 24)
        action_surf = action_font.render(button_text, True, (255, 255, 255))
        action_rect = action_surf.get_rect(center=self.action_button.center)
        screen.blit(action_surf, action_rect)

        # Shiny indicator
        if self.pokemon.is_shiny:
            shiny_text = title_font.render("✨ SHINY ✨", True, (255, 255, 100))
            shiny_rect = shiny_text.get_rect(center=(self.x + self.width - 100, self.y + 60))
            screen.blit(shiny_text, shiny_rect)