# src/scenes/team_select_scene/components/pokemon_grid_item.py

import pygame
from src.scenes.team_select_scene.utils.constants import COLORS


class PokemonGridItem:
    def __init__(self, pokemon, x, y, width, height):
        self.pokemon = pokemon
        self.rect = pygame.Rect(x, y, width, height)
        self.is_hovered = False
        self._portrait_cache = None  # Cache do retrato carregado

    def handle_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            self.is_hovered = self.rect.collidepoint(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.is_hovered and not self.pokemon.is_in_team:
                return self.pokemon
        return None

    def _get_portrait(self, pokedex):
        """Obtém o retrato do Pokémon com cache"""
        if self._portrait_cache is None:
            # Tenta carregar o retrato normal primeiro
            portrait = pokedex.get_portrait(self.pokemon.id, "normal", self.pokemon.is_shiny)

            # Se for shiny, adiciona efeito de brilho
            if self.pokemon.is_shiny and portrait:
                # Cria uma cópia com overlay dourado
                shiny_portrait = portrait.copy()
                overlay = pygame.Surface((40, 40), pygame.SRCALPHA)
                overlay.fill((255, 215, 0, 80))  # Amarelo dourado semi-transparente
                shiny_portrait.blit(overlay, (0, 0))
                self._portrait_cache = shiny_portrait
            else:
                self._portrait_cache = portrait

        return self._portrait_cache

    def render(self, screen, font, pokedex):
        self._draw_shadow(screen)
        self._draw_card_background(screen)
        self._draw_portrait(screen, pokedex)
        self._draw_info(screen, font)

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

    def _draw_portrait(self, screen, pokedex):
        """Desenha o retrato do Pokémon (40x40)"""
        portrait = self._get_portrait(pokedex)
        if portrait:
            # Centraliza o retrato na área esquerda do card
            portrait_x = self.rect.x + 5
            portrait_y = self.rect.y + (self.rect.height - 40) // 2
            screen.blit(portrait, (portrait_x, portrait_y))

    def _draw_info(self, screen, font):
        # Define a cor do nome baseado se é shiny ou não
        if self.pokemon.is_shiny:
            name_color = COLORS['TEXT']['YELLOW']  # Amarelo para shiny
        else:
            name_color = COLORS['TEXT']['WHITE']  # Branco para normal

        # Nome - ajustado para começar depois do retrato (40px + 10px margem)
        name_x = self.rect.x + 55
        name_text = font.render(self.pokemon.name, True, name_color)
        screen.blit(name_text, (name_x, self.rect.y + 10))

        # Nível (também pode ser amarelo para shiny? Mantive amarelo padrão)
        lvl_text = font.render(f"Lv.{self.pokemon.level}", True, COLORS['TEXT']['YELLOW'])
        screen.blit(lvl_text, (name_x, self.rect.y + 30))

        # Tipos
        type_font = pygame.font.Font(None, 11)
        type_colors = {
            "normal": (168, 168, 120),
            "fire": (240, 128, 48),
            "water": (104, 144, 240),
            "electric": (248, 208, 48),
            "grass": (120, 200, 80),
            "ice": (152, 216, 216),
            "fighting": (192, 48, 40),
            "poison": (160, 64, 160),
            "ground": (224, 192, 104),
            "flying": (168, 144, 240),
            "psychic": (248, 88, 136),
            "bug": (168, 184, 32),
            "rock": (184, 160, 56),
            "ghost": (112, 88, 152),
            "dragon": (112, 56, 248),
            "dark": (112, 88, 72),
            "steel": (184, 184, 208),
            "fairy": (238, 153, 172),
        }

        for i, type_name in enumerate(self.pokemon.types):
            color = type_colors.get(type_name.lower(), (128, 128, 128))
            type_text = type_font.render(type_name.upper(), True, color)
            screen.blit(type_text, (name_x + (i * 45), self.rect.y + 50))

    def _draw_team_overlay(self, screen, font):
        overlay = pygame.Surface((self.rect.width, self.rect.height), pygame.SRCALPHA)
        overlay.fill((0, 50, 0, 100))
        screen.blit(overlay, self.rect)

        team_text = font.render("No time", True, COLORS['TEXT']['GREEN'])
        text_rect = team_text.get_rect(center=(self.rect.centerx, self.rect.centery + 20))
        screen.blit(team_text, text_rect)