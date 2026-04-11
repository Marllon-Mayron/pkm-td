# src/entities/pokemon/rendering.py
import pygame


class PokemonRendering:
    """Gerencia renderização do Pokémon"""

    def __init__(self, pokemon):
        self.pokemon = pokemon

    def get_font(self, size):
        """Obtém fonte do cache"""
        from src.entities.pokemon.pokemon import _FONT_CACHE

        if size not in _FONT_CACHE:
            try:
                _FONT_CACHE[size] = pygame.font.Font(None, size)
            except:
                _FONT_CACHE[size] = pygame.font.SysFont('Arial', size)
        return _FONT_CACHE[size]

    def prepare_sprite(self, zoom_scale):
        if not self.pokemon.sprite:
            return None

        # ===== APLICA ESCALA DO MINIMIZE =====
        base_scale = 1.0
        if hasattr(self.pokemon, '_current_sprite_scale') and self.pokemon._current_sprite_scale != 1.0:
            base_scale = self.pokemon._current_sprite_scale

        if self.pokemon.is_boss:
            orig_width, orig_height = self.pokemon.sprite.get_width(), self.pokemon.sprite.get_height()
            new_width = int(orig_width * 2 * base_scale)
            new_height = int(orig_height * 2 * base_scale)
            return pygame.transform.scale(self.pokemon.sprite, (new_width, new_height))

        if base_scale != 1.0:
            orig_width, orig_height = self.pokemon.sprite.get_width(), self.pokemon.sprite.get_height()
            new_width = max(1, int(orig_width * base_scale))
            new_height = max(1, int(orig_height * base_scale))
            return pygame.transform.scale(self.pokemon.sprite, (new_width, new_height))

        return self.pokemon.sprite

    def render_sprite(self, screen, sprite, screen_x, screen_y, zoom_scale):
        """Renderiza o sprite com posicionamento correto pelo centro"""
        current_width, current_height = sprite.get_width(), sprite.get_height()
        final_width = max(1, int(current_width * zoom_scale))
        final_height = max(1, int(current_height * zoom_scale))

        if final_width != current_width or final_height != current_height:
            scaled_sprite = pygame.transform.scale(sprite, (final_width, final_height))
        else:
            scaled_sprite = sprite

        sprite_rect = scaled_sprite.get_rect()
        sprite_rect.center = (int(screen_x), int(screen_y))

        screen.blit(scaled_sprite, sprite_rect)
        return sprite_rect

    def render_hp_bar(self, screen, sprite_rect, zoom_scale):
        """Renderiza barra de HP"""
        hp_percent = self.pokemon.current_hp / self.pokemon.max_hp

        bar_width = int(self.pokemon.hp_bar_width * zoom_scale)
        bar_height = max(2, int(self.pokemon.hp_bar_height * zoom_scale))
        bar_x = sprite_rect.centerx - bar_width // 2
        bar_y = sprite_rect.top - bar_height - 5

        pygame.draw.rect(screen, (60, 60, 60), (bar_x, bar_y, bar_width, bar_height))

        if self.pokemon.is_boss:
            color = (0, 0, 255)
        else:
            if not self.pokemon.is_shiny:
                if hp_percent > 0.5:
                    color = (0, 200, 0)
                elif hp_percent > 0.25:
                    color = (255, 255, 0)
                else:
                    color = (255, 0, 0)
            else:
                color = (255, 0, 0)

        progress_width = int(bar_width * hp_percent)
        if progress_width > 0:
            pygame.draw.rect(screen, color, (bar_x, bar_y, progress_width, bar_height))

        pygame.draw.rect(screen, (100, 100, 100), (bar_x, bar_y, bar_width, bar_height), 1)

    def render_wild_text(self, screen, sprite_rect, zoom_scale):
        """Renderiza nome e nível do Pokémon selvagem"""
        name_font_size = max(8, int(10 * zoom_scale))
        level_font_size = max(7, int(9 * zoom_scale))

        name_font = self.get_font(name_font_size)
        level_font = self.get_font(level_font_size)

        name_text = f"{self.pokemon.name} - "
        level_text = f"lv. {self.pokemon.level:02d}"

        text_color = (255, 255, 255)
        outline_color = (0, 0, 0)

        if self.pokemon.is_shiny:
            level_color = (255, 215, 0)
        elif self.pokemon.is_boss:
            level_color = (255, 100, 100)
            text_color = (255, 100, 100)
        else:
            level_color = (255, 255, 255)

        name_surface = name_font.render(name_text, True, text_color)
        level_surface = level_font.render(level_text, True, level_color)
        name_outline = name_font.render(name_text, True, outline_color)
        level_outline = level_font.render(level_text, True, outline_color)

        name_width = name_surface.get_width()
        level_width = level_surface.get_width()
        total_width = name_width + 2 + level_width
        start_x = sprite_rect.centerx - total_width // 2

        text_y = sprite_rect.top - self.pokemon.hp_bar_height - 10 - name_font_size

        name_x, name_y = start_x, text_y
        level_x = start_x + name_width + 2
        level_y = text_y + (name_font_size - level_font_size)

        for dx, dy in [(-1, -1), (-1, 1), (1, -1), (1, 1)]:
            screen.blit(name_outline, (name_x + dx, name_y + dy))
            screen.blit(level_outline, (level_x + dx, level_y + dy))

        screen.blit(name_surface, (name_x, name_y))
        screen.blit(level_surface, (level_x, level_y))

    def render_miss_text(self, screen, sprite_rect, zoom_scale):
        """Renderiza o texto MISS acima do Pokémon"""
        if self.pokemon.miss_timer <= 0:
            return

        font_size = max(10, int(16 * zoom_scale))
        font = self.get_font(font_size)

        text = "MISS!"
        text_surface = font.render(text, True, (255, 100, 100))
        text_outline = font.render(text, True, (100, 0, 0))

        text_width = text_surface.get_width()
        text_x = sprite_rect.centerx - text_width // 2
        text_y = sprite_rect.top - self.pokemon.hp_bar_height - 25

        for dx, dy in [(-1, -1), (-1, 1), (1, -1), (1, 1)]:
            screen.blit(text_outline, (text_x + dx, text_y + dy))
        screen.blit(text_surface, (text_x, text_y))

    def render_placeholder(self, screen, screen_x, screen_y, zoom_scale):
        """Renderiza placeholder para quando sprite não existe"""
        size = int((64 if self.pokemon.is_boss else self.pokemon.map_sprite_size) * zoom_scale)

        rect = pygame.Rect(0, 0, size, size)
        rect.center = (int(screen_x), int(screen_y))

        pygame.draw.rect(screen, (255, 0, 255), rect)
        pygame.draw.rect(screen, (255, 255, 255), rect, 2)
        return rect