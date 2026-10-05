"""
Editor de spots para torres/pokemons.

Cada spot aceita ATÉ 4 tipos. O quadrado é desenhado com fill e borda
divididos conforme a quantidade de tipos:
    1 tipo : sólido
    2 tipos: diagonal (\\)
    3 tipos: 3 faixas verticais (| | |)
    4 tipos: 4 quadrantes (--|--)
"""
import pygame


# Cores por tipo (mesmas usadas no time para consistência)
TYPE_COLORS = {
    'normal':   (168, 168, 120), 'fire':     (240, 128, 48),
    'water':    (104, 144, 240), 'electric': (248, 208, 48),
    'grass':    (120, 200, 80),  'ice':      (152, 216, 216),
    'fighting': (192, 48, 40),   'poison':   (160, 64, 160),
    'ground':   (224, 192, 104), 'flying':   (168, 144, 240),
    'psychic':  (248, 88, 136),  'bug':      (168, 184, 32),
    'rock':     (184, 160, 56),  'ghost':    (112, 88, 152),
    'dragon':   (112, 56, 248),  'dark':     (112, 88, 72),
    'steel':    (184, 184, 208), 'fairy':    (238, 153, 238),
}

DEFAULT_SPOT_COLOR = (85, 95, 105)   # cinza neutro (sem tipos definidos)
MAX_TYPES_PER_SPOT = 4


def get_type_colors(allowed_types):
    """Retorna a lista de cores RGB dos tipos (máx 4)."""
    if not allowed_types:
        return [DEFAULT_SPOT_COLOR]
    colors = [TYPE_COLORS.get(t.lower(), DEFAULT_SPOT_COLOR)
              for t in allowed_types[:MAX_TYPES_PER_SPOT]]
    return colors or [DEFAULT_SPOT_COLOR]


# =========================================================
# DESENHO COMPARTILHADO (usado pelo editor E pelo jogo)
# =========================================================
def draw_typed_rect(surface, x, y, w, h, colors,
                    fill_alpha=140, border_width=2, border_alpha=255):
    """
    Desenha um quadrado colorido com fill + borda divididos em 1-4 cores.
    colors: lista de RGB (1 a 4 cores).
    """
    if not colors:
        colors = [DEFAULT_SPOT_COLOR]
    colors = colors[:MAX_TYPES_PER_SPOT]
    n = len(colors)

    if w <= 0 or h <= 0:
        return

    # ---- Surface temporária (para aplicar alpha corretamente) ----
    surf = pygame.Surface((w, h), pygame.SRCALPHA)

    # =========================================================
    # FILL
    # =========================================================
    if n == 1:
        surf.fill((*colors[0], fill_alpha))

    elif n == 2:
        # Diagonal \ : top-right (c0) vs bottom-left (c1)
        pygame.draw.polygon(surf, (*colors[0], fill_alpha),
                            [(0, 0), (w, 0), (w, h)])
        pygame.draw.polygon(surf, (*colors[1], fill_alpha),
                            [(0, 0), (0, h), (w, h)])

    elif n == 3:
        # 3 faixas verticais
        step = w / 3.0
        for i, c in enumerate(colors):
            x0 = int(i * step)
            x1 = int((i + 1) * step)
            pygame.draw.rect(surf, (*c, fill_alpha), (x0, 0, x1 - x0, h))

    else:  # n == 4 — 4 quadrantes
        hw = w // 2
        hh = h // 2
        pygame.draw.rect(surf, (*colors[0], fill_alpha), (0, 0, hw, hh))
        pygame.draw.rect(surf, (*colors[1], fill_alpha), (hw, 0, w - hw, hh))
        pygame.draw.rect(surf, (*colors[2], fill_alpha), (0, hh, hw, h - hh))
        pygame.draw.rect(surf, (*colors[3], fill_alpha), (hw, hh, w - hw, h - hh))

    # =========================================================
    # BORDA
    # =========================================================
    bw = max(1, int(border_width))

    def _blend(c, alpha):
        return (*c, alpha)

    if n == 1:
        pygame.draw.rect(surf, _blend(colors[0], border_alpha),
                         (0, 0, w, h), bw)

    elif n == 2:
        # top + right = c0 | bottom + left = c1   (combina com a diagonal \)
        pygame.draw.line(surf, _blend(colors[0], border_alpha),
                         (0, 0), (w - 1, 0), bw)                 # top
        pygame.draw.line(surf, _blend(colors[0], border_alpha),
                         (w - 1, 0), (w - 1, h - 1), bw)         # right
        pygame.draw.line(surf, _blend(colors[1], border_alpha),
                         (0, h - 1), (w - 1, h - 1), bw)         # bottom
        pygame.draw.line(surf, _blend(colors[1], border_alpha),
                         (0, 0), (0, h - 1), bw)                 # left

    elif n == 3:
        # Top e bottom em 3 segmentos, laterais com as cores dos extremos
        tw = w // 3
        segs = [(0, tw), (tw, 2 * tw), (2 * tw, w - 1)]
        for i, (x0, x1) in enumerate(segs):
            c = colors[i]
            pygame.draw.line(surf, _blend(c, border_alpha), (x0, 0), (x1, 0), bw)          # top
            pygame.draw.line(surf, _blend(c, border_alpha),
                             (x0, h - 1), (x1, h - 1), bw)                                  # bottom
        # laterais
        pygame.draw.line(surf, _blend(colors[0], border_alpha),
                         (0, 0), (0, h - 1), bw)                                            # left
        pygame.draw.line(surf, _blend(colors[2], border_alpha),
                         (w - 1, 0), (w - 1, h - 1), bw)                                    # right

    else:  # n == 4 — cada lado uma cor
        pygame.draw.line(surf, _blend(colors[0], border_alpha),
                         (0, 0), (w - 1, 0), bw)                 # top
        pygame.draw.line(surf, _blend(colors[1], border_alpha),
                         (w - 1, 0), (w - 1, h - 1), bw)         # right
        pygame.draw.line(surf, _blend(colors[3], border_alpha),
                         (0, h - 1), (w - 1, h - 1), bw)         # bottom
        pygame.draw.line(surf, _blend(colors[2], border_alpha),
                         (0, 0), (0, h - 1), bw)                 # left

    surface.blit(surf, (x, y))


# =========================================================
# TOWER SPOT
# =========================================================
class TowerSpot:
    def __init__(self, x, y, size=16):
        self.x = x
        self.y = y
        self.size = size
        self.occupied = False
        self.allowed_types = []   # até 4 (case-insensitive)

    def get_rect(self):
        return pygame.Rect(self.x, self.y, self.size, self.size)

    def contains_point(self, px, py):
        return (self.x <= px <= self.x + self.size and
                self.y <= py <= self.y + self.size)

    def is_type_allowed(self, pokemon_types):
        """Vazio = qualquer tipo. Senão, precisa ter pelo menos 1 tipo em comum."""
        if not self.allowed_types:
            return True
        if not pokemon_types:
            return False
        allowed = {t.lower() for t in self.allowed_types}
        return any(str(t).lower() in allowed for t in pokemon_types)

    def __eq__(self, other):
        if isinstance(other, TowerSpot):
            return self.x == other.x and self.y == other.y and self.size == other.size
        return False


# =========================================================
# TOWER SPOT MANAGER
# =========================================================
class TowerSpotManager:
    def __init__(self):
        self.spots = []
        self.selected_spot = -1
        self.spot_size = 16
        self.snap_to_grid = True
        self.grid_size = 16

    def add_spot(self, x, y):
        if self.snap_to_grid:
            x = (x // self.grid_size) * self.grid_size
            y = (y // self.grid_size) * self.grid_size

        for spot in self.spots:
            if spot.x == x and spot.y == y:
                print(f"Spot já existe em ({x}, {y})")
                return -1

        spot = TowerSpot(x, y, self.spot_size)
        self.spots.append(spot)
        print(f"Spot adicionado em ({x}, {y})")
        return len(self.spots) - 1

    def remove_spot(self, spot_to_remove):
        if spot_to_remove in self.spots:
            self.spots.remove(spot_to_remove)
            if self.selected_spot >= len(self.spots):
                self.selected_spot = len(self.spots) - 1
            print("Spot removido")

    def remove_spot_by_index(self, index):
        if 0 <= index < len(self.spots):
            del self.spots[index]
            if self.selected_spot >= len(self.spots):
                self.selected_spot = len(self.spots) - 1

    def get_spot_at(self, x, y):
        for spot in self.spots:
            if spot.contains_point(x, y):
                return spot
        return None

    def get_spot_index_at(self, x, y):
        for i, spot in enumerate(self.spots):
            if spot.contains_point(x, y):
                return i
        return -1

    # =========================================================
    # RENDER
    # =========================================================
    def render(self, screen, camera, screen_manager):
        for i, spot in enumerate(self.spots):
            screen_x = round((spot.x - camera.x) * camera.zoom * screen_manager.render_scale +
                             (screen_manager.render_width / 2) * screen_manager.render_scale +
                             screen_manager.viewport_x)
            screen_y = round((spot.y - camera.y) * camera.zoom * screen_manager.render_scale +
                             (screen_manager.render_height / 2) * screen_manager.render_scale +
                             screen_manager.viewport_y)

            size = max(6, round(spot.size * camera.zoom * screen_manager.render_scale))

            colors = get_type_colors(spot.allowed_types)

            if i == self.selected_spot:
                fill_alpha = 220
                border_width = max(2, round(3 * screen_manager.render_scale))
                draw_typed_rect(screen, screen_x, screen_y, size, size,
                                colors, fill_alpha=fill_alpha, border_width=border_width)
                # Overlay amarelo indicando seleção
                pygame.draw.rect(screen, (255, 255, 0),
                                 (screen_x - 1, screen_y - 1, size + 2, size + 2), 2)
            elif spot.occupied:
                draw_typed_rect(screen, screen_x, screen_y, size, size,
                                colors, fill_alpha=200,
                                border_width=max(2, round(2 * screen_manager.render_scale)))
            else:
                draw_typed_rect(screen, screen_x, screen_y, size, size,
                                colors, fill_alpha=90,
                                border_width=max(1, round(2 * screen_manager.render_scale)))

    # =========================================================
    # SERIALIZAÇÃO
    # =========================================================
    def to_dict(self):
        return {
            "spot_size": self.spot_size,
            "grid_size": self.grid_size,
            "snap_to_grid": self.snap_to_grid,
            "spots": [
                {
                    "x": spot.x,
                    "y": spot.y,
                    "size": spot.size,
                    "allowed_types": list(spot.allowed_types),
                }
                for spot in self.spots
            ],
        }

    def from_dict(self, data):
        self.spot_size = data.get("spot_size", 16)
        self.grid_size = data.get("grid_size", 16)
        self.snap_to_grid = data.get("snap_to_grid", True)
        self.spots = []
        for spot_data in data.get("spots", []):
            spot = TowerSpot(spot_data["x"], spot_data["y"], spot_data["size"])
            raw = list(spot_data.get("allowed_types", []) or [])
            if len(raw) > MAX_TYPES_PER_SPOT:
                print(f"[TowerSpot] Aviso: spot em ({spot.x},{spot.y}) tinha "
                      f"{len(raw)} tipos, truncando para {MAX_TYPES_PER_SPOT}")
                raw = raw[:MAX_TYPES_PER_SPOT]
            spot.allowed_types = raw
            self.spots.append(spot)