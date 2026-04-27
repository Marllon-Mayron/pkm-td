# src/scenes/minigames/survival/components/card_slot.py
"""
Slot individual de card na esteira - Estilo Plants vs Zombies
"""
import pygame
import math
from typing import Optional, Dict, Any
from src.data.pokedex import Pokedex


class CardSlot:
    """Slot individual de card na esteira"""

    # Cores por tipo
    TYPE_COLORS = {
        "grass": (80, 160, 80),
        "fire": (220, 100, 60),
        "water": (60, 120, 200),
        "electric": (240, 210, 60),
        "normal": (160, 140, 110),
        "fighting": (180, 100, 80),
        "flying": (130, 160, 190),
        "poison": (140, 80, 160),
        "ground": (170, 130, 70),
        "rock": (150, 130, 80),
        "bug": (140, 160, 70),
        "ghost": (100, 80, 140),
        "steel": (120, 140, 160),
        "psychic": (220, 100, 140),
        "ice": (100, 180, 200),
        "dragon": (140, 100, 180),
        "dark": (100, 80, 100),
        "fairy": (220, 140, 180),
        "default": (70, 80, 110)
    }

    def __init__(self, index: int, x: int, y: int, width: int, height: int):
        self.index = index
        self.rect = pygame.Rect(x, y, width, height)
        self.pokemon_id: Optional[int] = None
        self.pokemon_data: Optional[Dict] = None
        self.cost: int = 0
        self.cooldown: float = 0.0
        self.cooldown_max: float = 0.0
        self.is_selected: bool = False
        self.is_available: bool = True
        self.pokemon_type: str = "default"

        # Cache de sprite
        self._sprite = None
        self._sprite_scaled = None
        self._last_sprite_size = (0, 0)

        # Animação de glow
        self.glow_animation = 0.0
        self.glow_direction = 1

    def set_pokemon(self, pokemon_id: int, pokemon_data: Dict, cost: int, cooldown: float = 1.0):
        """Define o Pokémon deste card"""
        self.pokemon_id = pokemon_id
        self.pokemon_data = pokemon_data
        self.cost = cost
        self.cooldown_max = cooldown
        self.cooldown = 0.0
        self._sprite = None
        self._sprite_scaled = None

        # Detecta tipo
        types = pokemon_data.get('types', [])
        if types:
            self.pokemon_type = types[0].lower()

    def update(self, dt: float):
        """Atualiza cooldown e animações"""
        if self.cooldown > 0:
            self.cooldown -= dt
            if self.cooldown < 0:
                self.coordown = 0

        # Anima glow quando selecionado
        if self.is_selected:
            self.glow_animation += dt * 5
            if self.glow_animation > math.pi * 2:
                self.glow_animation -= math.pi * 2

    def is_ready(self) -> bool:
        """Verifica se o card está pronto para uso"""
        return self.cooldown <= 0 and self.is_available

    def start_cooldown(self):
        """Inicia o cooldown após usar o card"""
        self.cooldown = self.cooldown_max

    def get_sprite(self, pokedex: Pokedex, slot_width: int, slot_height: int):
        """Obtém o sprite do Pokémon para o card"""
        if not self.pokemon_id:
            return None

        current_size = (slot_width, slot_height)
        if self._sprite_scaled is None or self._last_sprite_size != current_size:
            self._sprite = pokedex.get_sprite(self.pokemon_id, "front", False)
            if self._sprite:
                sprite_w, sprite_h = self._sprite.get_size()
                max_size = min(slot_width - 12, slot_height - 30)
                scale = min(max_size / sprite_w, max_size / sprite_h)
                new_w = max(16, int(sprite_w * scale))
                new_h = max(16, int(sprite_h * scale))
                self._sprite_scaled = pygame.transform.scale(self._sprite, (new_w, new_h))
                self._last_sprite_size = current_size

        return self._sprite_scaled

    def get_type_color(self) -> tuple:
        """Retorna a cor baseada no tipo do Pokémon"""
        return self.TYPE_COLORS.get(self.pokemon_type, self.TYPE_COLORS["default"])

    def render(self, screen, pokedex: Pokedex, can_afford: bool, is_selected: bool = False):
        """Renderiza o card com visual melhorado"""
        self.is_selected = is_selected
        type_color = self.get_type_color()

        # Cor base dependendo do estado
        if is_selected:
            base_color = type_color
            glow_intensity = (math.sin(self.glow_animation) + 1) / 2
        elif not self.is_ready():
            base_color = (60, 55, 75)
        elif not can_afford:
            base_color = (100, 55, 55)
        else:
            base_color = type_color

        # Sombra do card
        shadow_rect = self.rect.copy()
        shadow_rect.x += 3
        shadow_rect.y += 3
        pygame.draw.rect(screen, (0, 0, 0, 80), shadow_rect, border_radius=10)

        # Fundo do card
        card_bg = pygame.Surface((self.rect.width, self.rect.height), pygame.SRCALPHA)
        pygame.draw.rect(card_bg, (*base_color, 220), card_bg.get_rect(), border_radius=10)

        # Gradiente no fundo
        for i in range(8):
            y = i * 4
            alpha = 40 - i * 5
            pygame.draw.rect(card_bg, (255, 255, 255, alpha), (2, y, self.rect.width - 4, 4), border_radius=2)

        screen.blit(card_bg, self.rect)

        # Borda
        border_color = (255, 215, 0) if is_selected else (120, 120, 150)
        border_width = 3 if is_selected else 2
        pygame.draw.rect(screen, border_color, self.rect, border_width, border_radius=10)

        # Efeito de glow quando selecionado
        if is_selected:
            glow = pygame.Surface((self.rect.width + 8, self.rect.height + 8), pygame.SRCALPHA)
            glow_intensity = int(80 * (math.sin(self.glow_animation) * 0.5 + 0.5))
            pygame.draw.rect(glow, (*type_color, glow_intensity),
                             glow.get_rect(), 3, border_radius=12)
            screen.blit(glow, (self.rect.x - 4, self.rect.y - 4))

        # Sprite do Pokémon
        sprite = self.get_sprite(pokedex, self.rect.width, self.rect.height)
        if sprite:
            sprite_x = self.rect.centerx - sprite.get_width() // 2
            sprite_y = self.rect.y + 12
            screen.blit(sprite, (sprite_x, sprite_y))

        # Nome do Pokémon
        name_font = pygame.font.Font(None, 11)
        if self.pokemon_data:
            name = self.pokemon_data.get('name', '???')
            if len(name) > 10:
                name = name[:8] + "."
            name_text = name_font.render(name, True, (255, 255, 200))
            screen.blit(name_text, (self.rect.x + 6, self.rect.y + 5))

        # Ícone do tipo
        type_font = pygame.font.Font(None, 10)
        type_icon = self.pokemon_type[:3].upper()
        type_text = type_font.render(type_icon, True, (200, 200, 200))
        screen.blit(type_text, (self.rect.right - type_text.get_width() - 6, self.rect.y + 5))

        # Custo (energia) com ícone
        font = pygame.font.Font(None, 16)
        cost_color = (255, 215, 0) if can_afford else (200, 80, 80)
        cost_text = font.render(f"⚡{self.cost}", True, cost_color)

        # Fundo do custo
        cost_bg = pygame.Surface((cost_text.get_width() + 6, 20), pygame.SRCALPHA)
        cost_bg.fill((0, 0, 0, 150))
        pygame.draw.rect(cost_bg, (60, 60, 80), cost_bg.get_rect(), 1, border_radius=4)
        screen.blit(cost_bg, (self.rect.x + 4, self.rect.bottom - 22))
        screen.blit(cost_text, (self.rect.x + 7, self.rect.bottom - 20))

        # Cooldown overlay
        if not self.is_ready() and self.cooldown_max > 0:
            cooldown_percent = self.cooldown / self.cooldown_max
            overlay_height = int(self.rect.height * cooldown_percent)
            if overlay_height > 0:
                overlay = pygame.Surface((self.rect.width, overlay_height), pygame.SRCALPHA)
                overlay.fill((0, 0, 0, 200))
                screen.blit(overlay, (self.rect.x, self.rect.y + self.rect.height - overlay_height))

                # Texto do tempo restante
                if self.cooldown > 0:
                    cd_font = pygame.font.Font(None, 14)
                    cd_text = cd_font.render(f"{self.cooldown:.1f}", True, (255, 255, 255))
                    cd_bg = pygame.Surface((cd_text.get_width() + 4, cd_text.get_height() + 4), pygame.SRCALPHA)
                    cd_bg.fill((0, 0, 0, 200))
                    cd_x = self.rect.centerx - cd_text.get_width() // 2
                    cd_y = self.rect.centery - cd_text.get_height() // 2
                    screen.blit(cd_bg, (cd_x - 2, cd_y - 2))
                    screen.blit(cd_text, (cd_x, cd_y))

    def get_tooltip_text(self) -> str:
        """Retorna o texto do tooltip para este card"""
        if not self.pokemon_data:
            return ""

        name = self.pokemon_data.get('name', '???')
        types = '/'.join(self.pokemon_data.get('types', ['unknown']))

        base_stats = self.pokemon_data.get('base_stats', {})
        hp = base_stats.get('hp', '?')
        attack = base_stats.get('attack', '?')

        return f"{name}\nTipo: {types}\nCusto: {self.cost}⚡\nHP:{hp} ATK:{attack}"

    def is_hovered(self, mouse_pos: tuple) -> bool:
        """Verifica se o mouse está sobre o card"""
        return self.rect.collidepoint(mouse_pos)