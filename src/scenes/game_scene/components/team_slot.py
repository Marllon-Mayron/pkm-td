# src/scenes/game_scene/components/team_slot.py

import pygame
import math
from src.data.pokedex import Pokedex
from src.scenes.team_select_scene.utils.constants import COLORS


class GameTeamSlot:
    """Slot do time com visual"""

    # Cores e estilos (constantes de classe)
    COLORS = {
        'bg_default': (25, 30, 40, 200),
        'bg_hover': (35, 45, 60, 220),
        'bg_selected': (45, 60, 80, 230),
        'bg_placed': (25, 50, 70, 180),
        'bg_hover_placed': (35, 65, 90, 200),
        'border': (70, 80, 100),
        'border_hover': (100, 140, 200),
        'border_selected': (255, 215, 0),
        'border_placed': (50, 150, 255),
        'border_hover_placed': (100, 200, 255),
        'text': (255, 255, 255),
        'text_dim': (150, 150, 170),
        'hp_green': (78, 201, 96),
        'hp_yellow': (255, 209, 102),
        'hp_red': (255, 107, 107),
        'hp_bg': (40, 45, 55),
        'hp_text': (255, 255, 255),
        'shiny': (255, 215, 0, 150),
        'xp_bar': (100, 180, 255),
        'xp_bg': (40, 45, 60),
        'level_bg': (50, 40, 70),
        'map_indicator': (50, 150, 255),
    }

    # Cache de fontes por tamanho (classe)
    _font_cache = {}
    _type_font_cache = {}
    _pokedex = Pokedex()

    # Cache de sprites por slot
    _sprite_cache = {}

    # Variável de classe para o pulso global
    _global_pulse_time = 0

    def __init__(self, x, y, width, height, slot_index, game):
        self.rect = pygame.Rect(x, y, width, height)
        self.slot_index = slot_index
        self.game = game

        self.is_hovered = False
        self.is_selected = False
        self.animation_offset = 0
        self.hp_animation = 0
        self.glow_alpha = 0

        # ===== OTIMIZAÇÃO: Pré-calcular dimensões =====
        self._sprite_size = int(height * 0.65)
        self._name_y = y + 12
        self._hp_y = y + height - 45
        self._xp_y = y + height - 22

        # ===== OTIMIZAÇÃO: Cache de superfícies =====
        self._cached_bg = None
        self._cached_border_color = None
        self._last_pokemon_id = None
        self._last_is_shiny = None
        self._cached_sprite = None
        self._cached_types_surface = None
        self._last_types = None

        # Fontes (serão obtidas do cache)
        self._name_font = None
        self._level_font = None
        self._hp_font = None
        self._xp_font = None
        self._get_fonts()

    def _get_font(self, size, bold=False):
        """Obtém fonte do cache de classe"""
        key = (size, bold)
        if key not in self.__class__._font_cache:
            font = pygame.font.Font(None, size)
            if bold:
                font.set_bold(True)
            self.__class__._font_cache[key] = font
        return self.__class__._font_cache[key]

    def _get_fonts(self):
        """Inicializa fontes com tamanhos responsivos"""
        base_size = max(14, int(self.rect.height * 0.18))
        small_size = max(12, int(base_size * 0.8))
        self._name_font = self._get_font(base_size)
        self._level_font = self._get_font(base_size)
        self._hp_font = self._get_font(small_size)
        self._xp_font = self._get_font(max(10, int(small_size * 0.8)))

    @property
    def pokemon(self):
        """Retorna o Pokémon deste slot diretamente do time do jogador"""
        if self.slot_index < len(self.game.player.team):
            return self.game.player.team[self.slot_index]
        return None

    @property
    def is_placed(self):
        """Verifica se o Pokémon está no mapa"""
        pokemon = self.pokemon
        return pokemon and hasattr(pokemon, 'is_placed') and pokemon.is_placed

    def handle_event(self, event, bag_manager=None):
        """Processa eventos no slot"""
        if not hasattr(self, 'click_start_time'):
            self.click_start_time = 0
            self.click_start_pos = None
            self.is_dragging_started = False

        if event.type == pygame.MOUSEMOTION:
            was_hovered = self.is_hovered
            self.is_hovered = self.rect.collidepoint(event.pos)

            if was_hovered != self.is_hovered:
                self.animation_offset = 8 if self.is_hovered else 0
                self.glow_alpha = 100 if self.is_hovered else 0
                # Invalida cache de fundo quando hover muda
                self._cached_bg = None

            if self.click_start_time > 0 and not self.is_dragging_started:
                if self.click_start_pos:
                    distance = ((event.pos[0] - self.click_start_pos[0]) ** 2 +
                                (event.pos[1] - self.click_start_pos[1]) ** 2) ** 0.5

                    if distance >= 10:
                        pokemon = self.pokemon
                        if pokemon:
                            is_placed = hasattr(pokemon, 'is_placed') and pokemon.is_placed
                            if not is_placed:
                                self.is_dragging_started = True
                                return {
                                    'action': 'start_drag',
                                    'slot_index': self.slot_index,
                                    'pokemon': pokemon
                                }

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.is_hovered:
                pokemon = self.pokemon
                if pokemon:
                    self.click_start_time = pygame.time.get_ticks()
                    self.click_start_pos = event.pos
                    self.is_dragging_started = False
                    return None
                else:
                    return {
                        'action': 'select',
                        'slot_index': self.slot_index
                    }

        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self.click_start_time > 0 and not self.is_dragging_started:
                pokemon = self.pokemon
                if pokemon and self.is_hovered:
                    click_duration = pygame.time.get_ticks() - self.click_start_time
                    distance = 0
                    if self.click_start_pos:
                        distance = ((event.pos[0] - self.click_start_pos[0]) ** 2 +
                                    (event.pos[1] - self.click_start_pos[1]) ** 2) ** 0.5

                    if click_duration < 200 and distance < 10:
                        is_placed = hasattr(pokemon, 'is_placed') and pokemon.is_placed
                        if is_placed:
                            self.click_start_time = 0
                            self.click_start_pos = None
                            return {
                                'action': 'open_move_select',
                                'slot_index': self.slot_index,
                                'pokemon': pokemon
                            }
                        else:
                            self.click_start_time = 0
                            self.click_start_pos = None
                            return {
                                'action': 'select',
                                'slot_index': self.slot_index
                            }

            self.click_start_time = 0
            self.click_start_pos = None
            self.is_dragging_started = False

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
            if self.is_hovered and bag_manager and bag_manager.has_items():
                pokemon = self.pokemon
                if pokemon:
                    return {
                        'action': 'use_item',
                        'slot_index': self.slot_index,
                        'pokemon': pokemon,
                        'item': bag_manager.get_selected_item()
                    }

        return None

    def update(self, dt):
        """Atualiza animações"""
        target = 8 if self.is_hovered else 0
        self.animation_offset += (target - self.animation_offset) * dt * 10

        target_glow = 100 if self.is_hovered else 0
        self.glow_alpha += (target_glow - self.glow_alpha) * dt * 8

        # Atualiza o pulso global
        self.__class__._global_pulse_time += dt

        if self.pokemon:
            self.hp_animation += dt
        else:
            self.hp_animation = 0

    def start_drag(self):
        """Inicia o arrasto deste slot"""
        self.is_selected = True
        self.animation_offset = 10
        self._cached_bg = None

    def render(self, screen):
        """Renderiza o slot com visual melhorado - OTIMIZADO"""
        pokemon = self.pokemon

        animated_rect = self.rect.copy()
        animated_rect.y -= int(self.animation_offset)

        self._draw_background(screen, animated_rect, pokemon)

        if pokemon:
            self._draw_pokemon_info(screen, animated_rect, pokemon)
            if self.is_placed:
                self._draw_placed_indicator(screen, animated_rect)
        else:
            self._draw_empty_slot(screen, animated_rect)

    def _draw_background(self, screen, rect, pokemon=None):
        """Desenha fundo do slot - COM CACHE"""
        is_on_map = self.is_placed

        # Determina cores base
        if self.is_selected:
            bg_color = self.COLORS['bg_selected']
            border_color = self.COLORS['border_selected']
        elif is_on_map:
            if self.is_hovered:
                bg_color = self.COLORS['bg_hover_placed']
                border_color = self.COLORS['border_hover_placed']
            else:
                bg_color = self.COLORS['bg_placed']
                border_color = self.COLORS['border_placed']
        elif self.is_hovered:
            bg_color = self.COLORS['bg_hover']
            border_color = self.COLORS['border_hover']
        else:
            bg_color = self.COLORS['bg_default']
            border_color = self.COLORS['border']

        # Verifica se precisa recriar o cache
        cache_key = (bg_color, border_color, rect.width, rect.height)
        if self._cached_bg is None or self._cached_border_color != cache_key:
            self._cached_bg = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)

            # Gradiente simplificado (apenas algumas linhas em vez de todas)
            step = max(1, rect.height // 8)  # Só 8 linhas de gradiente
            for y in range(0, rect.height, step):
                progress = y / rect.height
                color = (
                    int(bg_color[0] * (1 - progress * 0.2)),
                    int(bg_color[1] * (1 - progress * 0.2)),
                    int(bg_color[2] * (1 - progress * 0.2)),
                    bg_color[3]
                )
                pygame.draw.rect(self._cached_bg, color, (0, y, rect.width, min(step, rect.height - y)))

            self._cached_border_color = cache_key

        screen.blit(self._cached_bg, rect)

        # Efeito de brilho para Pokémon no mapa (pulsante)
        if is_on_map:
            pulse_value = (math.sin(self.__class__._global_pulse_time * 0.5) + 1) / 2
            glow_alpha = int(30 + 20 * pulse_value)
            glow_surface = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
            glow_color = (50, 150, 255, glow_alpha)
            pygame.draw.rect(glow_surface, glow_color, glow_surface.get_rect(), border_radius=8)
            screen.blit(glow_surface, rect)

        # Efeito de hover glow
        if self.glow_alpha > 0:
            glow_surface = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
            glow_color = (100, 150, 255, int(self.glow_alpha * 0.3))
            pygame.draw.rect(glow_surface, glow_color, glow_surface.get_rect(), border_radius=8)
            screen.blit(glow_surface, rect)

        # Borda
        pygame.draw.rect(screen, border_color, rect, 2, border_radius=10)

    def _draw_pokemon_info(self, screen, rect, pokemon):
        """Desenha informações do Pokémon - OTIMIZADO"""
        # Tipos (com cache)
        self._draw_types_above(screen, rect, pokemon)

        # Nível
        level_text = f"Lv.{pokemon.level}"
        level_surf = self._level_font.render(level_text, True, (255, 215, 100))

        level_bg_width = level_surf.get_width() + 8
        level_bg_height = level_surf.get_height() + 4
        level_bg_x = rect.x + rect.width - level_bg_width - 10
        level_bg_y = rect.y + 8

        pygame.draw.rect(screen, self.COLORS['level_bg'],
                         (level_bg_x, level_bg_y, level_bg_width, level_bg_height),
                         border_radius=4)
        pygame.draw.rect(screen, (100, 80, 120),
                         (level_bg_x, level_bg_y, level_bg_width, level_bg_height),
                         1, border_radius=4)

        screen.blit(level_surf, (level_bg_x + 4, level_bg_y + 2))

        # Nome do Pokémon
        name_y = rect.y + 12

        if pokemon.custom_name:
            name_text = pokemon.custom_name
        else:
            name_text = pokemon.name

        max_name_width = rect.width - level_bg_width - 30

        name_surf = self._name_font.render(name_text, True, self.COLORS['text'])
        if name_surf.get_width() > max_name_width:
            name_x = rect.x + 10
        else:
            name_x = rect.x + (rect.width - name_surf.get_width()) // 2

        screen.blit(name_surf, (name_x, name_y))

        # Sprite (com cache)
        sprite = self._get_cached_sprite(pokemon)
        if sprite:
            sprite_x = rect.x + (rect.width - self._sprite_size) // 2
            sprite_y = rect.y + (rect.height - self._sprite_size) // 2 - 5
            screen.blit(sprite, (sprite_x, sprite_y))

            if pokemon.is_shiny:
                self._draw_shiny_effect(screen, sprite_x, sprite_y, self._sprite_size)

        # Barras
        self._draw_hp_bar(screen, rect, self._hp_y, pokemon)
        self._draw_xp_bar(screen, rect, self._xp_y, pokemon)

    def _get_cached_sprite(self, pokemon):
        """Obtém sprite do cache"""
        cache_key = (pokemon.id, pokemon.is_shiny, self._sprite_size)

        if cache_key not in self.__class__._sprite_cache:
            sprite = self.__class__._pokedex.get_sprite(pokemon.id, "front", pokemon.is_shiny)
            if sprite:
                sprite = pygame.transform.scale(sprite, (self._sprite_size, self._sprite_size))
            self.__class__._sprite_cache[cache_key] = sprite

        return self.__class__._sprite_cache[cache_key]

    def _draw_types_above(self, screen, rect, pokemon):
        """Desenha os tipos ACIMA do slot - COM CACHE"""
        if not pokemon.types:
            return

        # Verifica se o cache de tipos é válido
        current_types = tuple(pokemon.types)
        if (self._cached_types_surface is None or
                self._last_types != current_types or
                self._last_types_rect != rect):

            self._last_types = current_types
            self._last_types_rect = rect

            type_colors = {
                'normal': (168, 168, 120), 'fire': (240, 128, 48), 'water': (104, 144, 240),
                'electric': (248, 208, 48), 'grass': (120, 200, 80), 'ice': (152, 216, 216),
                'fighting': (192, 48, 40), 'poison': (160, 64, 160), 'ground': (224, 192, 104),
                'flying': (168, 144, 240), 'psychic': (248, 88, 136), 'bug': (168, 184, 32),
                'rock': (184, 160, 56), 'ghost': (112, 88, 152), 'dragon': (112, 56, 248),
                'dark': (112, 88, 72), 'steel': (184, 184, 208), 'fairy': (238, 153, 238)
            }

            # Pré-renderiza os tipos em uma superfície
            type_height = 24
            total_width = 0
            type_surfs = []
            type_bg_widths = []

            for type_name in pokemon.types:
                color = type_colors.get(type_name.lower(), (150, 150, 150))
                type_text = type_name.capitalize()
                type_surf = self._xp_font.render(type_text, True, (255, 255, 255))
                padding = 8
                bg_width = type_surf.get_width() + padding * 2
                type_surfs.append((type_surf, color))
                type_bg_widths.append(bg_width)
                total_width += bg_width + 5

            if pokemon.types:
                total_width -= 5

            start_x = rect.x + (rect.width - total_width) // 2
            y = rect.y - 22

            # Cria a superfície cacheada
            self._cached_types_surface = pygame.Surface((total_width + 10, type_height + 10), pygame.SRCALPHA)
            current_x = start_x - rect.x

            for i, (type_surf, color) in enumerate(type_surfs):
                bg_width = type_bg_widths[i]
                bg_height = type_surf.get_height() + 6

                # Desenha na superfície cacheada
                bg_rect = pygame.Rect(current_x, y - rect.y, bg_width, bg_height)
                pygame.draw.rect(self._cached_types_surface, color, bg_rect, border_radius=8)
                pygame.draw.rect(self._cached_types_surface, (255, 255, 255, 180), bg_rect, 2, border_radius=8)

                text_x = current_x + (bg_width - type_surf.get_width()) // 2
                text_y = (y - rect.y) + (bg_height - type_surf.get_height()) // 2
                self._cached_types_surface.blit(type_surf, (text_x, text_y))

                current_x += bg_width + 5

        # Renderiza a superfície cacheada
        if self._cached_types_surface:
            screen.blit(self._cached_types_surface, (rect.x, rect.y - 22))

    def _draw_hp_bar(self, screen, rect, y, pokemon):
        """Desenha barra de HP - OTIMIZADO"""
        hp_percent = pokemon.current_hp / pokemon.max_hp

        bar_width = rect.width - 20
        bar_x = rect.x + 10
        bar_height = 18

        # Fundo
        pygame.draw.rect(screen, self.COLORS['hp_bg'], (bar_x, y, bar_width, bar_height), border_radius=8)

        # Cor baseada no percentual
        if hp_percent > 0.6:
            hp_color = self.COLORS['hp_green']
        elif hp_percent > 0.3:
            hp_color = self.COLORS['hp_yellow']
        else:
            hp_color = self.COLORS['hp_red']
            if hp_percent < 0.2:
                pulse = 1.0 + 0.2 * math.sin(self.hp_animation * 10)
                hp_color = tuple(min(255, int(c * pulse)) for c in hp_color)

        current_width = max(3, int(bar_width * hp_percent))
        pygame.draw.rect(screen, hp_color, (bar_x, y, current_width, bar_height), border_radius=8)
        pygame.draw.rect(screen, (100, 100, 120, 150), (bar_x, y, bar_width, bar_height), 2, border_radius=8)

        # Texto HP
        hp_text = f"{pokemon.current_hp}/{pokemon.max_hp}"
        text_surf = self._hp_font.render(hp_text, True, self.COLORS['hp_text'])
        text_x = bar_x + (bar_width - text_surf.get_width()) // 2
        text_y = y + (bar_height - text_surf.get_height()) // 2
        screen.blit(text_surf, (text_x, text_y))

    def _draw_xp_bar(self, screen, rect, y, pokemon):
        """Desenha barra de XP - OTIMIZADO"""
        xp_percent = pokemon.xp / pokemon.xp_to_next if pokemon.xp_to_next > 0 else 0
        xp_percent = min(1.0, max(0.0, xp_percent))

        bar_width = rect.width - 20
        bar_x = rect.x + 10
        bar_height = 14

        pygame.draw.rect(screen, self.COLORS['xp_bg'], (bar_x, y, bar_width, bar_height), border_radius=6)

        if xp_percent > 0:
            xp_width = max(2, int(bar_width * xp_percent))
            if xp_percent > 0.8:
                xp_color = (150, 230, 255)
            elif xp_percent > 0.5:
                xp_color = (100, 200, 255)
            else:
                xp_color = (70, 150, 255)
            pygame.draw.rect(screen, xp_color, (bar_x, y, xp_width, bar_height), border_radius=6)

        pygame.draw.rect(screen, (60, 70, 90), (bar_x, y, bar_width, bar_height), 1, border_radius=6)

        xp_text = f"{pokemon.xp}/{pokemon.xp_to_next} XP"
        text_surf = self._xp_font.render(xp_text, True, (200, 220, 255))
        text_x = bar_x + (bar_width - text_surf.get_width()) // 2
        text_y = y + (bar_height - text_surf.get_height()) // 2
        screen.blit(text_surf, (text_x, text_y))

        if xp_percent >= 1.0:
            star_font = self._get_font(16)
            star = star_font.render("★", True, (255, 215, 0))
            screen.blit(star, (bar_x + bar_width + 5, y - 2))

    def _draw_shiny_effect(self, screen, x, y, size):
        """Desenha efeito de brilho para Pokémon shiny - OTIMIZADO"""
        # Limita o número de partículas
        for i in range(4):  # Reduzido de 6 para 4
            angle = (self.hp_animation * 2 + i * 90) % 360
            rad = math.radians(angle)
            px = x + size // 2 + math.cos(rad) * (size // 2 + 8)
            py = y + size // 2 + math.sin(rad) * (size // 2 + 8)
            alpha = int(150 + 105 * math.sin(self.hp_animation * 4 + i))
            particle_size = 4 + int(2 * math.sin(self.hp_animation * 3 + i))

            particle = pygame.Surface((particle_size, particle_size), pygame.SRCALPHA)
            pygame.draw.circle(particle, (255, 215, 0, alpha),
                               (particle_size // 2, particle_size // 2), particle_size // 2)
            screen.blit(particle, (px - particle_size // 2, py - particle_size // 2))

    def _draw_placed_indicator(self, screen, rect):
        """Desenha indicador de que o Pokémon está no mapa - OTIMIZADO"""
        indicator_size = 20
        indicator_x = rect.x + 8
        indicator_y = rect.y + 8

        pulse_value = (math.sin(self.__class__._global_pulse_time * 0.5) + 1) / 2
        pulse = 0.8 + (pulse_value * 0.4)

        # Círculo principal
        pygame.draw.circle(screen, self.COLORS['map_indicator'],
                           (indicator_x + indicator_size // 2, indicator_y + indicator_size // 2),
                           int(indicator_size // 2 * pulse))

        # Círculo interno
        inner_radius = int(indicator_size // 3 * pulse)
        pygame.draw.circle(screen, (255, 255, 255),
                           (indicator_x + indicator_size // 2, indicator_y + indicator_size // 2),
                           inner_radius)

        # Ícone simplificado (texto em vez de fonte)
        icon_font = self._get_font(int(indicator_size * 0.6))
        map_icon = icon_font.render("🌍", True, self.COLORS['map_indicator'])
        icon_rect = map_icon.get_rect(center=(indicator_x + indicator_size // 2,
                                              indicator_y + indicator_size // 2))
        screen.blit(map_icon, icon_rect)

    def _draw_empty_slot(self, screen, rect):
        """Desenha slot vazio com estilo"""
        center = rect.center
        pulse = 1.0 + 0.1 * math.sin(self.hp_animation * 2)
        radius = int(min(rect.width, rect.height) * 0.2 * pulse)

        pygame.draw.circle(screen, (60, 70, 90), center, radius, 3)

        plus_size = int(radius * 1.2)
        plus_font = self._get_font(plus_size)
        plus_text = plus_font.render("+", True, (80, 90, 120))
        plus_rect = plus_text.get_rect(center=center)
        screen.blit(plus_text, plus_rect)

        empty_font = self._get_font(max(12, int(rect.height * 0.15)))
        empty_text = empty_font.render("Vazio", True, (80, 90, 120))
        empty_rect = empty_text.get_rect(centerx=center[0], top=rect.y + rect.height - 20)
        screen.blit(empty_text, empty_rect)

    def on_resize(self, new_x, new_y):
        """Atualiza posição do slot"""
        self.rect.x = new_x
        self.rect.y = new_y
        self._sprite_size = int(self.rect.height * 0.65)
        self._name_y = self.rect.y + 12
        self._hp_y = self.rect.y + self.rect.height - 45
        self._xp_y = self.rect.y + self.rect.height - 22
        self._get_fonts()
        self._cached_bg = None
        self._cached_types_surface = None