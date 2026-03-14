import pygame
from src.scenes.team_select_scene.utils.constants import COLORS


class PokemonGridItem:
    def __init__(self, pokemon, x, y, width, height):
        self.pokemon = pokemon
        self.rect = pygame.Rect(x, y, width, height)
        self.is_hovered = False

    def handle_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            self.is_hovered = self.rect.collidepoint(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.is_hovered and not self.pokemon.is_in_team:
                return self.pokemon
        return None

    def render(self, screen, font, pokedex):
        self._draw_shadow(screen)
        self._draw_card_background(screen)
        self._draw_sprite(screen, pokedex)
        self._draw_info(screen, font)
        self._draw_shiny_indicator(screen)

        if self.pokemon.is_in_team:
            self._draw_team_overlay(screen, font)

    def _draw_shadow(self, screen):
        shadow_rect = self.rect.copy()
        shadow_rect.x += 2
        shadow_rect.y += 2
        pygame.draw.rect(screen, COLORS['GRID']['SHADOW'], shadow_rect, border_radius=6)

    def _draw_card_background(self, screen):
        if self.pokemon.is_in_team:
            color = COLORS['GRID']['IN_TEAM']
            border_color = COLORS['GRID']['BORDER_IN_TEAM']
        elif self.is_hovered:
            color = COLORS['GRID']['HOVER']
            border_color = COLORS['GRID']['BORDER_HOVER']
        else:
            color = COLORS['GRID']['DEFAULT']
            border_color = COLORS['GRID']['BORDER']

        pygame.draw.rect(screen, color, self.rect, border_radius=6)
        pygame.draw.rect(screen, border_color, self.rect, 1, border_radius=6)

    def _draw_sprite(self, screen, pokedex):
        sprite = pokedex.get_sprite(self.pokemon.id, "inmap", self.pokemon.is_shiny)
        if sprite:
            sprite_scaled = pygame.transform.scale(sprite, (48, 48))
            screen.blit(sprite_scaled, (self.rect.x + 5, self.rect.y + 5))

    def _draw_info(self, screen, font):
        # Nome
        name_text = font.render(self.pokemon.name, True, COLORS['TEXT']['WHITE'])
        screen.blit(name_text, (self.rect.x + 60, self.rect.y + 10))

        # Nível
        lvl_text = font.render(f"Lv.{self.pokemon.level}", True, COLORS['TEXT']['YELLOW'])
        screen.blit(lvl_text, (self.rect.x + 60, self.rect.y + 30))

    def _draw_shiny_indicator(self, screen):
        if self.pokemon.is_shiny:
            star_font = pygame.font.Font(None, 20)
            star = star_font.render("⭐", True, COLORS['TEXT']['YELLOW'])
            screen.blit(star, (self.rect.right - 25, self.rect.y + 5))

    def _draw_team_overlay(self, screen, font):
        overlay = pygame.Surface((self.rect.width, self.rect.height), pygame.SRCALPHA)
        overlay.fill((0, 50, 0, 100))
        screen.blit(overlay, self.rect)

        team_text = font.render("No time", True, COLORS['TEXT']['GREEN'])
        text_rect = team_text.get_rect(center=(self.rect.centerx, self.rect.centery + 20))
        screen.blit(team_text, text_rect)