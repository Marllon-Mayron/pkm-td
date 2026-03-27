# src/scenes/game_scene/components/ui/team_slot.py

import pygame
import math
from src.data.pokedex import Pokedex
from src.scenes.team_select_scene.utils.constants import COLORS


class GameTeamSlot:
    """Slot do time com visual melhorado para o jogo"""

    # Cores e estilos
    COLORS = {
        'bg_default': (25, 30, 40, 200),
        'bg_hover': (35, 45, 60, 220),
        'bg_selected': (45, 60, 80, 230),
        'border': (70, 80, 100),
        'border_hover': (100, 140, 200),
        'border_selected': (255, 215, 0),
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
    }

    def __init__(self, x, y, width, height, slot_index, game):
        self.rect = pygame.Rect(x, y, width, height)
        self.slot_index = slot_index
        self.game = game
        self.pokedex = Pokedex()

        self.is_hovered = False
        self.is_selected = False
        self.animation_offset = 0
        self.hp_animation = 0
        self.glow_alpha = 0

        # Fontes (serão recriadas no resize)
        self.name_font = None
        self.level_font = None
        self.hp_font = None
        self.xp_font = None
        self._create_fonts()

    @property
    def pokemon(self):
        """Retorna o Pokémon deste slot diretamente do time do jogador"""
        if self.slot_index < len(self.game.player.team):
            return self.game.player.team[self.slot_index]
        return None

    def _create_fonts(self):
        """Cria fontes com tamanhos responsivos"""
        base_size = max(14, int(self.rect.height * 0.18))
        small_size = max(12, int(base_size * 0.8))
        self.name_font = pygame.font.Font(None, base_size)
        self.level_font = pygame.font.Font(None, base_size)
        self.hp_font = pygame.font.Font(None, small_size)
        self.xp_font = pygame.font.Font(None, max(10, int(small_size * 0.8)))

    def handle_event(self, event, bag_manager=None):
        """Processa eventos no slot"""
        # Variáveis para detectar clique vs arrasto
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

            # Verifica se está com o botão pressionado e já moveu o suficiente para iniciar drag
            if self.click_start_time > 0 and not self.is_dragging_started:
                if self.click_start_pos:
                    distance = ((event.pos[0] - self.click_start_pos[0]) ** 2 +
                                (event.pos[1] - self.click_start_pos[1]) ** 2) ** 0.5

                    # Se moveu mais de 10 pixels, inicia o drag
                    if distance >= 10:
                        pokemon = self.pokemon
                        if pokemon:
                            is_placed = hasattr(pokemon, 'is_placed') and pokemon.is_placed

                            # Só inicia drag se NÃO estiver no mapa
                            if not is_placed:
                                print(f"[SLOT] Arrasto detectado em {pokemon.name} - Iniciando drag")
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
                    # Registra o início do clique
                    self.click_start_time = pygame.time.get_ticks()
                    self.click_start_pos = event.pos
                    self.is_dragging_started = False
                    return None  # Aguarda para ver se é clique ou arrasto
                else:
                    # Slot vazio - apenas seleciona
                    return {
                        'action': 'select',
                        'slot_index': self.slot_index
                    }

        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            # Se não houve drag, é um clique
            if self.click_start_time > 0 and not self.is_dragging_started:
                pokemon = self.pokemon
                if pokemon and self.is_hovered:
                    # Verifica se foi um clique simples (curto e pouco movimento)
                    click_duration = pygame.time.get_ticks() - self.click_start_time
                    distance = 0
                    if self.click_start_pos:
                        distance = ((event.pos[0] - self.click_start_pos[0]) ** 2 +
                                    (event.pos[1] - self.click_start_pos[1]) ** 2) ** 0.5

                    # Se foi um clique simples (menos de 200ms e pouco movimento)
                    if click_duration < 200 and distance < 10:
                        is_placed = hasattr(pokemon, 'is_placed') and pokemon.is_placed

                        if is_placed:
                            # Pokémon no mapa - ABRE OVERLAY DE MOVES
                            print(f"[SLOT] Clique em {pokemon.name} (no mapa) - Abrindo overlay de moves")
                            self.click_start_time = 0
                            self.click_start_pos = None
                            return {
                                'action': 'open_move_select',
                                'slot_index': self.slot_index,
                                'pokemon': pokemon
                            }
                        else:
                            # Pokémon no time (não colocado) - apenas seleciona
                            print(f"[SLOT] Clique em {pokemon.name} (no time) - Selecionando")
                            self.click_start_time = 0
                            self.click_start_pos = None
                            return {
                                'action': 'select',
                                'slot_index': self.slot_index
                            }

            # Limpa os dados do clique
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

        if self.pokemon:
            self.hp_animation += dt
        else:
            self.hp_animation = 0

    def start_drag(self):
        """Inicia o arrasto deste slot"""
        self.is_selected = True
        self.animation_offset = 10

    def render(self, screen):
        """Renderiza o slot com visual melhorado"""
        pokemon = self.pokemon

        animated_rect = self.rect.copy()
        animated_rect.y -= int(self.animation_offset)

        self._draw_shadow(screen, animated_rect)
        self._draw_background(screen, animated_rect, pokemon)

        if pokemon:
            self._draw_pokemon_info(screen, animated_rect, pokemon)

            if hasattr(pokemon, 'is_placed') and pokemon.is_placed:
                self._draw_placed_indicator(screen, animated_rect)
        else:
            self._draw_empty_slot(screen, animated_rect)

    def _draw_placed_indicator(self, screen, rect):
        """Desenha indicador de que o Pokémon está no mapa"""
        indicator_size = 12
        indicator_x = rect.x + 5
        indicator_y = rect.y + 5

        pygame.draw.circle(screen, (0, 200, 0),
                           (indicator_x + indicator_size // 2, indicator_y + indicator_size // 2),
                           indicator_size // 2)
        pygame.draw.circle(screen, (255, 255, 255),
                           (indicator_x + indicator_size // 2, indicator_y + indicator_size // 2),
                           indicator_size // 2 - 2)

        font = pygame.font.Font(None, 14)
        check = font.render("✓", True, (0, 0, 0))
        check_rect = check.get_rect(center=(indicator_x + indicator_size // 2,
                                            indicator_y + indicator_size // 2))
        screen.blit(check, check_rect)

    def _draw_shadow(self, screen, rect):
        """Desenha sombra suave"""
        shadow_rect = rect.copy()
        shadow_rect.x += 5
        shadow_rect.y += 5

        for i in range(4):
            alpha = 40 - i * 10
            if alpha > 0:
                shadow = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
                shadow.fill((0, 0, 0, alpha))
                screen.blit(shadow, (shadow_rect.x + i, shadow_rect.y + i))

    def _draw_background(self, screen, rect, pokemon=None):
        """Desenha fundo do slot com gradiente"""
        if self.is_selected:
            base_color = self.COLORS['bg_selected']
            border_color = self.COLORS['border_selected']
        elif self.is_hovered:
            base_color = self.COLORS['bg_hover']
            if pokemon and hasattr(pokemon, 'is_placed') and pokemon.is_placed:
                border_color = (100, 255, 100)
            else:
                border_color = self.COLORS['border_hover']
        else:
            base_color = self.COLORS['bg_default']
            if pokemon and hasattr(pokemon, 'is_placed') and pokemon.is_placed:
                border_color = (0, 200, 0)
            else:
                border_color = self.COLORS['border']

        bg_surface = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)

        for y in range(rect.height):
            progress = y / rect.height
            color = (
                int(base_color[0] * (1 - progress * 0.2)),
                int(base_color[1] * (1 - progress * 0.2)),
                int(base_color[2] * (1 - progress * 0.2)),
                base_color[3]
            )
            bg_surface.set_at((0, y), color)
            bg_surface.set_at((rect.width - 1, y), color)

        screen.blit(bg_surface, rect)

        if self.glow_alpha > 0:
            glow_surface = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
            glow_color = (100, 150, 255, int(self.glow_alpha * 0.3))
            pygame.draw.rect(glow_surface, glow_color, glow_surface.get_rect(), border_radius=8)
            screen.blit(glow_surface, rect)

        pygame.draw.rect(screen, border_color, rect, 2, border_radius=10)

    def _draw_pokemon_info(self, screen, rect, pokemon):
        """Desenha informações do Pokémon"""
        self._draw_types_above(screen, rect, pokemon)

        level_text = f"Lv.{pokemon.level}"
        level_surf = self.level_font.render(level_text, True, (255, 215, 100))

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

        name_y = rect.y + 12
        name_text = pokemon.name
        if self.name_font.size(name_text)[0] > rect.width * 0.5:
            name_text = pokemon.name[:12] + "..."

        name_surf = self.name_font.render(name_text, True, self.COLORS['text'])

        max_name_width = rect.width - level_bg_width - 30
        if name_surf.get_width() > max_name_width:
            name_x = rect.x + 10
        else:
            name_x = rect.x + (rect.width - name_surf.get_width()) // 2

        screen.blit(name_surf, (name_x, name_y))

        sprite_size = int(rect.height * 0.65)
        sprite = self.pokedex.get_sprite(pokemon.id, "front", pokemon.is_shiny)

        if sprite:
            sprite_scaled = pygame.transform.scale(sprite, (sprite_size, sprite_size))
            sprite_x = rect.x + (rect.width - sprite_size) // 2
            sprite_y = rect.y + (rect.height - sprite_size) // 2 - 5
            screen.blit(sprite_scaled, (sprite_x, sprite_y))

            if pokemon.is_shiny:
                self._draw_shiny_effect(screen, sprite_x, sprite_y, sprite_size)

        hp_y = rect.y + rect.height - 45
        self._draw_hp_bar(screen, rect, hp_y, pokemon)

        xp_y = rect.y + rect.height - 22
        self._draw_xp_bar(screen, rect, xp_y, pokemon)

    def _draw_types_above(self, screen, rect, pokemon):
        """Desenha os tipos ACIMA do slot, centralizados"""
        if not pokemon.types:
            return

        type_colors = {
            'normal': (168, 168, 120), 'fire': (240, 128, 48), 'water': (104, 144, 240),
            'electric': (248, 208, 48), 'grass': (120, 200, 80), 'ice': (152, 216, 216),
            'fighting': (192, 48, 40), 'poison': (160, 64, 160), 'ground': (224, 192, 104),
            'flying': (168, 144, 240), 'psychic': (248, 88, 136), 'bug': (168, 184, 32),
            'rock': (184, 160, 56), 'ghost': (112, 88, 152), 'dragon': (112, 56, 248),
            'dark': (112, 88, 72), 'steel': (184, 184, 208), 'fairy': (238, 153, 238)
        }

        total_width = 0
        type_surfs = []
        type_bg_widths = []

        for type_name in pokemon.types:
            color = type_colors.get(type_name.lower(), (150, 150, 150))
            type_text = type_name.capitalize()
            type_surf = self.xp_font.render(type_text, True, (255, 255, 255))
            padding = 8
            bg_width = type_surf.get_width() + padding * 2

            type_surfs.append((type_surf, color))
            type_bg_widths.append(bg_width)
            total_width += bg_width + 5

        if len(pokemon.types) > 0:
            total_width -= 5

        start_x = rect.x + (rect.width - total_width) // 2
        y = rect.y - 22

        for i, (type_surf, color) in enumerate(type_surfs):
            bg_width = type_bg_widths[i]
            bg_height = type_surf.get_height() + 6

            shadow_rect = pygame.Rect(start_x + 2, y + 2, bg_width, bg_height)
            pygame.draw.rect(screen, (0, 0, 0, 100), shadow_rect, border_radius=8)

            bg_rect = pygame.Rect(start_x, y, bg_width, bg_height)
            pygame.draw.rect(screen, color, bg_rect, border_radius=8)
            pygame.draw.rect(screen, (255, 255, 255, 180), bg_rect, 2, border_radius=8)

            text_x = start_x + (bg_width - type_surf.get_width()) // 2
            text_y = y + (bg_height - type_surf.get_height()) // 2
            screen.blit(type_surf, (text_x, text_y))

            start_x += bg_width + 5

    def _draw_hp_bar(self, screen, rect, y, pokemon):
        """Desenha barra de HP MAIS LARGA"""
        hp_percent = pokemon.current_hp / pokemon.max_hp

        bar_width = rect.width - 20
        bar_x = rect.x + 10
        bar_height = 18

        bg_rect = pygame.Rect(bar_x, y, bar_width, bar_height)
        pygame.draw.rect(screen, self.COLORS['hp_bg'], bg_rect, border_radius=8)

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
        hp_rect = pygame.Rect(bar_x, y, current_width, bar_height)
        pygame.draw.rect(screen, hp_color, hp_rect, border_radius=8)
        pygame.draw.rect(screen, (100, 100, 120, 150), bg_rect, 2, border_radius=8)

        hp_text = f"{pokemon.current_hp}/{pokemon.max_hp}"
        text_surf = self.hp_font.render(hp_text, True, self.COLORS['hp_text'])
        text_x = bar_x + (bar_width - text_surf.get_width()) // 2
        text_y = y + (bar_height - text_surf.get_height()) // 2

        text_bg = pygame.Surface((text_surf.get_width() + 6, text_surf.get_height() + 4), pygame.SRCALPHA)
        text_bg.fill((0, 0, 0, 120))
        screen.blit(text_bg, (text_x - 3, text_y - 2))
        screen.blit(text_surf, (text_x, text_y))

    def _draw_xp_bar(self, screen, rect, y, pokemon):
        """Desenha barra de XP MAIS LARGA"""
        xp_percent = pokemon.xp / pokemon.xp_to_next if pokemon.xp_to_next > 0 else 0
        xp_percent = min(1.0, max(0.0, xp_percent))

        bar_width = rect.width - 20
        bar_x = rect.x + 10
        bar_height = 14

        bg_rect = pygame.Rect(bar_x, y, bar_width, bar_height)
        pygame.draw.rect(screen, self.COLORS['xp_bg'], bg_rect, border_radius=6)

        xp_width = max(2, int(bar_width * xp_percent))
        if xp_width > 0:
            xp_rect = pygame.Rect(bar_x, y, xp_width, bar_height)

            if xp_percent > 0.8:
                xp_color = (150, 230, 255)
            elif xp_percent > 0.5:
                xp_color = (100, 200, 255)
            else:
                xp_color = (70, 150, 255)

            pygame.draw.rect(screen, xp_color, xp_rect, border_radius=6)

        pygame.draw.rect(screen, (60, 70, 90), bg_rect, 1, border_radius=6)

        xp_text = f"{pokemon.xp}/{pokemon.xp_to_next} XP"
        text_surf = self.xp_font.render(xp_text, True, (200, 220, 255))
        text_x = bar_x + (bar_width - text_surf.get_width()) // 2
        text_y = y + (bar_height - text_surf.get_height()) // 2

        text_bg = pygame.Surface((text_surf.get_width() + 4, text_surf.get_height() + 2), pygame.SRCALPHA)
        text_bg.fill((0, 0, 0, 80))
        screen.blit(text_bg, (text_x - 2, text_y - 1))
        screen.blit(text_surf, (text_x, text_y))

        if xp_percent >= 1.0:
            star_font = pygame.font.Font(None, 16)
            star = star_font.render("★", True, (255, 215, 0))
            screen.blit(star, (bar_x + bar_width + 5, y - 2))

    def _draw_shiny_effect(self, screen, x, y, size):
        """Desenha efeito de brilho para Pokémon shiny"""
        for i in range(6):
            angle = (self.hp_animation * 2 + i * 60) % 360
            rad = math.radians(angle)
            px = x + size // 2 + math.cos(rad) * (size // 2 + 10)
            py = y + size // 2 + math.sin(rad) * (size // 2 + 10)
            alpha = int(150 + 105 * math.sin(self.hp_animation * 4 + i))
            particle_size = 5 + int(3 * math.sin(self.hp_animation * 3 + i))

            particle = pygame.Surface((particle_size, particle_size), pygame.SRCALPHA)
            pygame.draw.circle(particle, (255, 215, 0, alpha),
                               (particle_size // 2, particle_size // 2), particle_size // 2)
            screen.blit(particle, (px - particle_size // 2, py - particle_size // 2))

    def _draw_empty_slot(self, screen, rect):
        """Desenha slot vazio com estilo"""
        center = rect.center
        pulse = 1.0 + 0.1 * math.sin(self.hp_animation * 2)
        radius = int(min(rect.width, rect.height) * 0.2 * pulse)

        pygame.draw.circle(screen, (60, 70, 90), center, radius, 3)

        plus_size = int(radius * 1.2)
        plus_font = pygame.font.Font(None, plus_size)
        plus_text = plus_font.render("+", True, (80, 90, 120))
        plus_rect = plus_text.get_rect(center=center)
        screen.blit(plus_text, plus_rect)

        empty_font = pygame.font.Font(None, max(12, int(rect.height * 0.15)))
        empty_text = empty_font.render("Vazio", True, (80, 90, 120))
        empty_rect = empty_text.get_rect(centerx=center[0], top=rect.y + rect.height - 20)
        screen.blit(empty_text, empty_rect)

    def on_resize(self, new_x, new_y):
        """Atualiza posição do slot"""
        self.rect.x = new_x
        self.rect.y = new_y
        self._create_fonts()