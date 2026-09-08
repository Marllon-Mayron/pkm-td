# src/scenes/team_select_scene/components/pokemon_grid_item.py

import pygame
from src.ui.utils.icon_loader import get_held_icon
from src.scenes.team_select_scene.utils.constants import COLORS


class PokemonGridItem:
    def __init__(self, pokemon_data, x, y, width, height):
        self.pokemon_data = pokemon_data  # dict
        self.rect = pygame.Rect(x, y, width, height)
        self.is_hovered = False
        self._portrait_cache = None
        self._is_in_team_cache = None
        self._held_icon_cache = None

    def handle_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            self.is_hovered = self.rect.collidepoint(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.is_hovered and not self.pokemon_data.get("is_in_team", False):
                return self.pokemon_data
        return None

    def _get_portrait(self, pokedex):
        """Obtém o retrato do Pokémon com cache"""
        if self._portrait_cache is None:
            pokemon_id = self.pokemon_data["id"]
            is_shiny = self.pokemon_data.get("is_shiny", False)
            portrait = pokedex.get_portrait(pokemon_id, "normal", is_shiny)

            if is_shiny and portrait:
                shiny_portrait = portrait.copy()
                overlay = pygame.Surface((40, 40), pygame.SRCALPHA)
                overlay.fill((255, 215, 0, 80))
                shiny_portrait.blit(overlay, (0, 0))
                self._portrait_cache = shiny_portrait
            else:
                self._portrait_cache = portrait
        return self._portrait_cache

    def _get_held_icon(self):
        """Retorna o ícone de item segurável em cache"""
        if self._held_icon_cache is None:
            self._held_icon_cache = get_held_icon()
        return self._held_icon_cache

    def render(self, screen, font, pokedex):
        self._draw_shadow(screen)
        self._draw_card_background(screen)
        self._draw_portrait_and_id(screen, pokedex, font)
        self._draw_info(screen, font)

        # ===== ÍCONE DE ITEM SEGURÁVEL (canto inferior direito) =====
        if self.pokemon_data.get("held_item"):
            self._draw_held_item_icon(screen)

        if self.pokemon_data.get("is_in_team", False):
            self._draw_team_overlay(screen, font)

    def _draw_held_item_icon(self, screen):
        """Desenha o ícone de item segurável no canto inferior direito"""
        icon = self._get_held_icon()
        if icon:
            # 15x15
            icon_scaled = pygame.transform.scale(icon, (15, 15))
            icon_x = self.rect.right - 20
            icon_y = self.rect.bottom - 20

            # Fundo
            bg_rect = pygame.Rect(icon_x - 2, icon_y - 2, 19, 19)
            pygame.draw.rect(screen, (0, 0, 0, 200), bg_rect, border_radius=4)
            pygame.draw.rect(screen, (255, 215, 0, 180), bg_rect, 1, border_radius=4)

            screen.blit(icon_scaled, (icon_x, icon_y))

    def _draw_card_background(self, screen):
        if self.pokemon_data.get("is_in_team", False):
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

    def _draw_shadow(self, screen):
        shadow_rect = self.rect.copy()
        shadow_rect.x += 2
        shadow_rect.y += 2
        pygame.draw.rect(screen, COLORS['GRID']['SHADOW'], shadow_rect, border_radius=6)

    def _draw_portrait_and_id(self, screen, pokedex, font):
        portrait = self._get_portrait(pokedex)
        portrait_x = self.rect.x + 5
        portrait_y = self.rect.y + (self.rect.height - 40) // 2

        # ID
        formatted_id = f"#{self.pokemon_data['id']:03d}"
        is_shiny = self.pokemon_data.get("is_shiny", False)
        id_color = COLORS['TEXT']['YELLOW'] if is_shiny else COLORS['TEXT'].get('GRAY', (128, 128, 128))
        id_font = pygame.font.Font(None, font.get_height() + 4)
        id_text = id_font.render(formatted_id, True, id_color)
        id_x = portrait_x + (40 - id_text.get_width()) // 2
        id_y = portrait_y - id_text.get_height() - 4

        id_shadow = id_font.render(formatted_id, True, (0, 0, 0))
        screen.blit(id_shadow, (id_x + 1, id_y + 1))
        screen.blit(id_text, (id_x, id_y))

        if portrait:
            screen.blit(portrait, (portrait_x, portrait_y))

    def _draw_info(self, screen, font):
        name_color = COLORS['TEXT']['YELLOW'] if self.pokemon_data.get("is_shiny", False) else COLORS['TEXT']['WHITE']
        name_x = self.rect.x + 55
        name_text = font.render(self.pokemon_data["name"], True, name_color)
        screen.blit(name_text, (name_x, self.rect.y + 10))

        lvl_text = font.render(f"Lv.{self.pokemon_data['level']}", True, COLORS['TEXT']['YELLOW'])
        screen.blit(lvl_text, (name_x, self.rect.y + 30))

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
        for i, type_name in enumerate(self.pokemon_data.get("types", [])):
            color = type_colors.get(type_name.lower(), (128, 128, 128))
            type_text = type_font.render(type_name.upper(), True, color)
            screen.blit(type_text, (name_x + (i * 45), self.rect.y + 50))

    def _draw_team_overlay(self, screen, font):
        overlay = pygame.Surface((self.rect.width, self.rect.height), pygame.SRCALPHA)
        overlay.fill((0, 50, 0, 100))
        screen.blit(overlay, self.rect)
        team_text = font.render("No time", True, COLORS['TEXT']['GREEN'])
        text_rect = team_text.get_rect(center=(self.rect.centerx, self.rect.centery + 35))
        screen.blit(team_text, text_rect)