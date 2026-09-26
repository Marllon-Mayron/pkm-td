# src/scenes/team_select_scene/components/team_slot.py

import pygame
import math
import random
from src.ui.utils.icon_loader import get_held_icon
from src.ui.utils.font_cache import get_font
from src.data.icon_loader import pokemon_icon_loader
from src.scenes.team_select_scene.utils.constants import COLORS


TYPE_COLORS = {
    "normal": (168, 168, 120), "fire": (240, 128, 48),
    "water": (104, 144, 240), "electric": (248, 208, 48),
    "grass": (120, 200, 80), "ice": (152, 216, 216),
    "fighting": (192, 48, 40), "poison": (160, 64, 160),
    "ground": (224, 192, 104), "flying": (168, 144, 240),
    "psychic": (248, 88, 136), "bug": (168, 184, 32),
    "rock": (184, 160, 56), "ghost": (112, 88, 152),
    "dragon": (112, 56, 248), "dark": (112, 88, 72),
    "steel": (184, 184, 208), "fairy": (238, 153, 172),
}


class _Sparkles:
    """Partículas de shiny com cache de superfície."""
    _sprite_cache = {}   # {(size, color): Surface}

    def __init__(self, seed=0):
        self.particles = []
        self._rng = random.Random(seed)
        self._timer = 0
        self._interval = 8
        self._rect = None

    @classmethod
    def _get_sprite(cls, size, color):
        key = (size, color)
        s = cls._sprite_cache.get(key)
        if s is None:
            d = size * 2
            s = pygame.Surface((d, d), pygame.SRCALPHA)
            cx = cy = d // 2
            pygame.draw.line(s, color, (cx - size, cy), (cx + size, cy), 1)
            pygame.draw.line(s, color, (cx, cy - size), (cx, cy + size), 1)
            pygame.draw.circle(s, color, (cx, cy), max(1, size // 2))
            cls._sprite_cache[key] = s
        return s

    def update_and_draw(self, screen, rect):
        self._rect = rect
        self._timer += 1
        if self._timer >= self._interval:
            self._timer = 0
            self._spawn()

        alive = []
        for p in self.particles:
            p['life'] -= p['decay']
            if p['life'] <= 0:
                continue
            p['x'] += p['vx']
            p['y'] += p['vy']
            p['vy'] += 0.02
            if p['y'] > rect.bottom + 4:
                p['y'] = rect.top - 4
            if p['x'] < rect.left - 4:
                p['x'] = rect.right + 4
            if p['x'] > rect.right + 4:
                p['x'] = rect.left - 4

            alpha = int(200 * p['life'])
            spr = self._get_sprite(p['size'], p['color'])
            spr.set_alpha(alpha)
            screen.blit(spr, (p['x'] - p['size'], p['y'] - p['size']))
            alive.append(p)
        self.particles = alive

    def _spawn(self):
        if not self._rect:
            return
        r = self._rect
        side = self._rng.randint(0, 3)
        if side == 0:
            x = self._rng.uniform(r.left, r.right); y = r.top
        elif side == 1:
            x = r.right; y = self._rng.uniform(r.top, r.bottom)
        elif side == 2:
            x = self._rng.uniform(r.left, r.right); y = r.bottom
        else:
            x = r.left; y = self._rng.uniform(r.top, r.bottom)

        self.particles.append({
            'x': x, 'y': y,
            'vx': self._rng.uniform(-0.3, 0.3),
            'vy': self._rng.uniform(-0.4, -0.1),
            'size': self._rng.choice([2, 2, 3]),
            'life': 1.0,
            'decay': self._rng.uniform(0.015, 0.03),
            'color': self._rng.choice([
                (255, 235, 140), (255, 215, 0), (255, 245, 200),
            ]),
        })


class TeamSlot:
    def __init__(self, x, y, width, height, slot_index):
        self.rect = pygame.Rect(x, y, width, height)
        self.slot_index = slot_index
        self.pokemon = None
        self.is_hovered = False
        self.is_selected = False
        self.is_drag_hover = False
        self._held_icon_cache = None
        self._sparkles = _Sparkles(seed=slot_index * 7919)

    def set_pokemon(self, pokemon):
        self.pokemon = pokemon

    def _get_held_icon(self):
        if self._held_icon_cache is None:
            self._held_icon_cache = get_held_icon()
        return self._held_icon_cache

    def handle_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            self.is_hovered = self.rect.collidepoint(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.is_hovered:
                return self.slot_index
        return None

    def render(self, screen, font, pokedex):
        self._draw_shadow(screen)
        self._draw_background(screen)
        self._draw_number(screen)

        if self.pokemon:
            self._draw_content(screen)
            if getattr(self.pokemon, "is_shiny", False):
                self._sparkles.update_and_draw(screen, self.rect)
        else:
            self._draw_empty(screen)

    def _draw_shadow(self, screen):
        r = self.rect.copy(); r.x += 3; r.y += 3
        pygame.draw.rect(screen, COLORS['SLOT']['SHADOW'], r, border_radius=8)

    def _draw_background(self, screen):
        is_shiny = self.pokemon and getattr(self.pokemon, "is_shiny", False)

        if self.is_drag_hover:
            color, border = (60, 100, 160), (150, 200, 255)
        elif is_shiny:
            t = pygame.time.get_ticks() / 1000.0
            pulse = (math.sin(t * 2.2) + 1) * 0.5
            shift = int(25 * pulse)
            color = (60 + shift, 48 + shift, 18 + shift // 2)
            border = (255, 215, 0)
        elif self.is_selected:
            color = COLORS['SLOT']['SELECTED']
            border = COLORS['SLOT']['BORDER_SELECTED']
        elif self.is_hovered:
            color = COLORS['SLOT']['HOVER']
            border = COLORS['SLOT']['BORDER_HOVER']
        else:
            color = COLORS['SLOT']['DEFAULT']
            border = COLORS['SLOT']['BORDER']

        pygame.draw.rect(screen, color, self.rect, border_radius=8)
        if is_shiny:
            pygame.draw.rect(screen, border, self.rect, 3, border_radius=8)
            pygame.draw.rect(screen, (180, 140, 40),
                             self.rect.inflate(-6, -6), 1, border_radius=6)
        else:
            pygame.draw.rect(screen, border, self.rect, 2, border_radius=8)

    def _draw_number(self, screen):
        is_shiny = self.pokemon and getattr(self.pokemon, "is_shiny", False)
        color = (255, 230, 140) if is_shiny else COLORS['TEXT']['DARK_GRAY']
        t = get_font(16).render(f"#{self.slot_index + 1}", True, color)
        screen.blit(t, (self.rect.x + 6, self.rect.y + 5))

    def _draw_content(self, screen):
        is_shiny = getattr(self.pokemon, "is_shiny", False)

        # TIPAGEM À DIREITA
        types = getattr(self.pokemon, "types", []) or []
        top_h = self._draw_types_right(screen, types) if types else 6

        # ÍCONE
        footer_h = 34
        top = self.rect.y + top_h
        bottom = self.rect.bottom - footer_h
        avail_h = bottom - top
        avail_w = self.rect.width - 12
        icon_size = max(40, min(int(avail_h * 0.68), avail_w, 110))

        try:
            icon = pokemon_icon_loader.get_animated_icon(
                self.pokemon.id, icon_size,
                pygame.time.get_ticks(), 400,
            )
        except Exception:
            icon = None

        if icon:
            screen.blit(icon, (
                self.rect.centerx - icon_size // 2,
                top + (avail_h - icon_size) // 2,
            ))

        # NOME + LEVEL (fonte maior)
        name_font = get_font(20)
        lvl_font = get_font(18)

        name_color = (255, 235, 150) if is_shiny else COLORS['TEXT']['WHITE']
        name_text = self.pokemon.name
        lvl_text = f" Lv.{self.pokemon.level}"

        name_s = name_font.render(name_text, True, name_color)
        lvl_s = lvl_font.render(lvl_text, True, COLORS['TEXT']['YELLOW'])

        total_w = name_s.get_width() + lvl_s.get_width()
        max_w = self.rect.width - 10
        if total_w > max_w:
            while name_s.get_width() + lvl_s.get_width() > max_w and len(name_text) > 3:
                name_text = name_text[:-1]
                name_s = name_font.render(name_text + ".", True, name_color)

        total_w = name_s.get_width() + lvl_s.get_width()
        x = self.rect.centerx - total_w // 2
        y = self.rect.bottom - footer_h + 6

        if is_shiny:
            sh_n = name_font.render(name_text, True, (0, 0, 0))
            sh_l = lvl_font.render(lvl_text, True, (0, 0, 0))
            screen.blit(sh_n, (x + 1, y + 1))
            screen.blit(sh_l, (x + name_s.get_width() + 1, y + 2))

        screen.blit(name_s, (x, y))
        screen.blit(lvl_s, (x + name_s.get_width(), y + 2))

        # ÍCONE DE ITEM (canto inferior direito)
        if self.pokemon.held_item:
            self._draw_item_icon(screen)

    def _draw_types_right(self, screen, types):
        """Badges alinhados à DIREITA."""
        bw, bh, gap = 42, 14, 3
        total_w = len(types) * bw + (len(types) - 1) * gap
        x = self.rect.right - 6 - total_w
        y = self.rect.y + 5
        f = get_font(11)

        for t in types:
            c = TYPE_COLORS.get(t.lower(), (128, 128, 128))
            b = pygame.Rect(x, y, bw, bh)
            pygame.draw.rect(screen, c, b, border_radius=3)
            pygame.draw.rect(screen, (0, 0, 0), b, 1, border_radius=3)
            s = f.render(t.upper(), True, (255, 255, 255))
            screen.blit(s, s.get_rect(center=b.center))
            x += bw + gap
        return bh + 8

    def _draw_item_icon(self, screen):
        icon = self._get_held_icon()
        if icon:
            s = pygame.transform.scale(icon, (16, 16))
            x = self.rect.right - 22
            y = self.rect.bottom - 22
            bg = pygame.Rect(x - 2, y - 2, 20, 20)
            pygame.draw.rect(screen, (0, 0, 0), bg, border_radius=4)
            pygame.draw.rect(screen, (255, 215, 0), bg, 1, border_radius=4)
            screen.blit(s, (x, y))

    def _draw_empty(self, screen):
        f = get_font(50)
        t = f.render("+", True, COLORS['SLOT']['EMPTY_PLUS'])
        screen.blit(t, t.get_rect(center=self.rect.center))