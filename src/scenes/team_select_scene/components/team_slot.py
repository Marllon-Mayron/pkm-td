# src/scenes/team_select_scene/components/team_slot.py

import pygame
from src.scenes.team_select_scene.utils.constants import COLORS


class TeamSlot:
    def __init__(self, x, y, width, height, slot_index):
        self.rect = pygame.Rect(x, y, width, height)
        self.slot_index = slot_index
        self.pokemon = None
        self.is_hovered = False
        self.is_selected = False
        self._portrait_cache = None

    def set_pokemon(self, pokemon):
        self.pokemon = pokemon
        self._portrait_cache = None  # Limpa cache quando o Pokémon muda

    def _get_portrait(self, pokedex):
        """Obtém o retrato do Pokémon com cache"""
        if not self.pokemon:
            return None

        if self._portrait_cache is None:
            portrait = pokedex.get_portrait(self.pokemon.id, "normal", self.pokemon.is_shiny)

            # Se for shiny, adiciona efeito de brilho
            if self.pokemon.is_shiny and portrait:
                shiny_portrait = portrait.copy()
                overlay = pygame.Surface((40, 40), pygame.SRCALPHA)
                overlay.fill((255, 215, 0, 80))
                shiny_portrait.blit(overlay, (0, 0))
                self._portrait_cache = shiny_portrait
            else:
                self._portrait_cache = portrait

        return self._portrait_cache

    def handle_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            self.is_hovered = self.rect.collidepoint(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.is_hovered:
                return self.slot_index
        return None

    def render(self, screen, font, pokedex):
        self._draw_shadow(screen)
        self._draw_slot_background(screen)
        self._draw_slot_number(screen)

        if self.pokemon:
            self._draw_pokemon_info(screen, font, pokedex)
        else:
            self._draw_empty_slot(screen)

    def _draw_shadow(self, screen):
        shadow_rect = self.rect.copy()
        shadow_rect.x += 3
        shadow_rect.y += 3
        pygame.draw.rect(screen, COLORS['SLOT']['SHADOW'], shadow_rect, border_radius=8)

    def _draw_slot_background(self, screen):
        if self.is_selected:
            color = COLORS['SLOT']['SELECTED']
            border_color = COLORS['SLOT']['BORDER_SELECTED']
        elif self.is_hovered:
            color = COLORS['SLOT']['HOVER']
            border_color = COLORS['SLOT']['BORDER_HOVER']
        else:
            color = COLORS['SLOT']['DEFAULT']
            border_color = COLORS['SLOT']['BORDER']

        pygame.draw.rect(screen, color, self.rect, border_radius=8)
        pygame.draw.rect(screen, border_color, self.rect, 2, border_radius=8)

    def _draw_slot_number(self, screen):
        font = pygame.font.Font(None, 18)
        num_text = font.render(f"#{self.slot_index + 1}", True, COLORS['TEXT']['DARK_GRAY'])
        screen.blit(num_text, (self.rect.x + 5, self.rect.y + 5))

    def _draw_pokemon_info(self, screen, font, pokedex):
        # Retrato (40x40)
        portrait = self._get_portrait(pokedex)
        if portrait:
            portrait_x = self.rect.x + 8
            portrait_y = self.rect.y + (self.rect.height - 40) // 2
            screen.blit(portrait, (portrait_x, portrait_y))

        # Nome - ajustado para começar depois do retrato
        name_x = self.rect.x + 58
        name_text = self.pokemon.name[:8] + ("." if len(self.pokemon.name) > 8 else "")
        name_surf = font.render(name_text, True, COLORS['TEXT']['WHITE'])
        screen.blit(name_surf, (name_x, self.rect.y + 15))

        # Nível
        lvl_text = font.render(f"Lv.{self.pokemon.level}", True, COLORS['TEXT']['YELLOW'])
        screen.blit(lvl_text, (name_x, self.rect.y + 35))

        # HP Bar (mais compacta)
        self._draw_hp_bar(screen)

        # Shiny effect
        if self.pokemon.is_shiny:
            pygame.draw.rect(screen, COLORS['TEXT']['YELLOW'], self.rect, 3, border_radius=8)

    def _draw_hp_bar(self, screen):
        hp_percent = self.pokemon.current_hp / self.pokemon.max_hp
        bar_width = 50
        bar_height = 4
        bar_x = self.rect.x + 58
        bar_y = self.rect.y + 55

        # Fundo
        pygame.draw.rect(screen, (40, 40, 40), (bar_x, bar_y, bar_width, bar_height))

        # Barra colorida
        if hp_percent > 0.5:
            hp_color = COLORS['TEXT']['HP_GREEN']
        elif hp_percent > 0.25:
            hp_color = COLORS['TEXT']['HP_YELLOW']
        else:
            hp_color = COLORS['TEXT']['HP_RED']

        pygame.draw.rect(screen, hp_color,
                         (bar_x, bar_y, int(bar_width * hp_percent), bar_height))

    def _draw_empty_slot(self, screen):
        empty_font = pygame.font.Font(None, 40)
        empty_text = empty_font.render("+", True, COLORS['SLOT']['EMPTY_PLUS'])
        empty_rect = empty_text.get_rect(center=(self.rect.centerx, self.rect.centery))
        screen.blit(empty_text, empty_rect)