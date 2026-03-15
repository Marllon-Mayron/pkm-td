# src/scenes/game_scene/components/ui/team_slot.py

import pygame
import math
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
        'hp_green': (78, 201, 96),  # Verde mais vibrante
        'hp_yellow': (255, 209, 102),  # Amarelo
        'hp_red': (255, 107, 107),  # Vermelho
        'hp_bg': (40, 45, 55),  # Fundo da barra
        'hp_text': (255, 255, 255),  # Texto branco
        'shiny': (255, 215, 0, 150)
    }

    def __init__(self, x, y, width, height, slot_index):
        self.rect = pygame.Rect(x, y, width, height)
        self.slot_index = slot_index
        self.pokemon = None
        self.is_hovered = False
        self.is_selected = False
        self.animation_offset = 0
        self.hp_animation = 0
        self.glow_alpha = 0

        # Fontes (serão recriadas no resize)
        self.name_font = None
        self.level_font = None
        self.hp_font = None
        self._create_fonts()

    def _create_fonts(self):
        """Cria fontes com tamanhos responsivos"""
        base_size = max(12, int(self.rect.height * 0.15))
        self.name_font = pygame.font.Font(None, base_size)
        self.level_font = pygame.font.Font(None, base_size)
        self.hp_font = pygame.font.Font(None, max(10, int(base_size * 0.7)))

    def set_pokemon(self, pokemon):
        """Define o Pokémon do slot"""
        self.pokemon = pokemon

    def handle_event(self, event):
        """Processa eventos no slot"""
        if event.type == pygame.MOUSEMOTION:
            was_hovered = self.is_hovered
            self.is_hovered = self.rect.collidepoint(event.pos)

            if was_hovered != self.is_hovered:
                self.animation_offset = 8 if self.is_hovered else 0
                self.glow_alpha = 100 if self.is_hovered else 0

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.is_hovered:
                # Se tem Pokémon, pode iniciar arrasto
                if self.pokemon:
                    return {
                        'action': 'start_drag',
                        'slot_index': self.slot_index,
                        'pokemon': self.pokemon
                    }
                return {
                    'action': 'select',
                    'slot_index': self.slot_index
                }

        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            # Se estava arrastando, o drag manager cuida disso
            pass

        return None

    def update(self, dt):
        """Atualiza animações"""
        # Suaviza animação de hover
        target = 8 if self.is_hovered else 0
        self.animation_offset += (target - self.animation_offset) * dt * 10

        # Suaviza glow
        target_glow = 100 if self.is_hovered else 0
        self.glow_alpha += (target_glow - self.glow_alpha) * dt * 8

        # Animação da barra de HP
        if self.pokemon:
            self.hp_animation += dt
        else:
            self.hp_animation = 0

    def start_drag(self):
        """Inicia o arrasto deste slot"""
        self.is_selected = True
        # Feedback visual de que está sendo arrastado
        self.animation_offset = 10

    def render(self, screen, pokedex):
        """Renderiza o slot com visual melhorado"""
        # Calcula posição com animação
        animated_rect = self.rect.copy()
        animated_rect.y -= int(self.animation_offset)

        # Sombra
        self._draw_shadow(screen, animated_rect)

        # Fundo do slot
        self._draw_background(screen, animated_rect)

        if self.pokemon:
            self._draw_pokemon_info(screen, animated_rect, pokedex)
        else:
            self._draw_empty_slot(screen, animated_rect)

    def _draw_shadow(self, screen, rect):
        """Desenha sombra suave"""
        shadow_rect = rect.copy()
        shadow_rect.x += 5
        shadow_rect.y += 5

        # Sombra com gradiente
        for i in range(4):
            alpha = 40 - i * 10
            if alpha > 0:
                shadow = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
                shadow.fill((0, 0, 0, alpha))
                screen.blit(shadow, (shadow_rect.x + i, shadow_rect.y + i))

    def _draw_background(self, screen, rect):
        """Desenha fundo do slot com gradiente"""
        # Define cor baseado no estado
        if self.is_selected:
            base_color = self.COLORS['bg_selected']
            border_color = self.COLORS['border_selected']
        elif self.is_hovered:
            base_color = self.COLORS['bg_hover']
            border_color = self.COLORS['border_hover']
        else:
            base_color = self.COLORS['bg_default']
            border_color = self.COLORS['border']

        # Fundo principal
        bg_surface = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)

        # Gradiente sutil
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

        # Efeito de glow no hover
        if self.glow_alpha > 0:
            glow_surface = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
            glow_color = (100, 150, 255, int(self.glow_alpha * 0.3))
            pygame.draw.rect(glow_surface, glow_color, glow_surface.get_rect(), border_radius=8)
            screen.blit(glow_surface, rect)

        # Borda
        pygame.draw.rect(screen, border_color, rect, 2, border_radius=10)

    def _draw_pokemon_info(self, screen, rect, pokedex):
        """Desenha informações do Pokémon com sprite FRONT"""
        # Sprite FRONT aumentado
        sprite = pokedex.get_sprite(self.pokemon.id, "front", self.pokemon.is_shiny)
        if sprite:
            # Sprite maior - 80% da altura do slot
            sprite_size = int(rect.height * 0.8)
            sprite_scaled = pygame.transform.scale(sprite, (sprite_size, sprite_size))

            # Posição centralizada verticalmente
            sprite_x = rect.x + 10
            sprite_y = rect.y + (rect.height - sprite_size) // 2
            screen.blit(sprite_scaled, (sprite_x, sprite_y))

            # Efeito de brilho para shiny
            if self.pokemon.is_shiny:
                self._draw_shiny_effect(screen, sprite_x, sprite_y, sprite_size)

        # Área de informações (lado direito)
        info_x = rect.x + sprite_size + 20
        info_width = rect.width - (sprite_size + 30)

        # Nome do Pokémon (canto superior esquerdo da área de info)
        name_text = self.pokemon.name
        if self.name_font.size(name_text)[0] > info_width * 0.6:
            name_text = self.pokemon.name[:12] + "..."

        name_surf = self.name_font.render(name_text, True, self.COLORS['text'])
        screen.blit(name_surf, (info_x, rect.y + 12))

        # Nível no canto superior direito
        level_text = f"Lv.{self.pokemon.level}"
        level_surf = self.level_font.render(level_text, True, (255, 215, 100))
        level_x = rect.x + rect.width - level_surf.get_width() - 12
        screen.blit(level_surf, (level_x, rect.y + 12))

        # Barra de HP mais grossa com informações dentro
        self._draw_hp_bar(screen, rect, info_x, rect.y + 40, info_width)

    def _draw_shiny_effect(self, screen, x, y, size):
        """Desenha efeito de brilho para Pokémon shiny"""
        # Estrelas brilhantes
        for i in range(5):
            angle = (self.hp_animation * 3 + i * 72) % 360
            rad = math.radians(angle)

            # Posição ao redor do sprite
            px = x + size // 2 + math.cos(rad) * (size // 2 + 5)
            py = y + size // 2 + math.sin(rad) * (size // 2 + 5)

            # Partícula brilhante
            alpha = int(150 + 105 * math.sin(self.hp_animation * 5 + i))
            particle_size = 4 + int(2 * math.sin(self.hp_animation * 3 + i))

            particle = pygame.Surface((particle_size, particle_size), pygame.SRCALPHA)
            pygame.draw.circle(particle, (255, 215, 0, alpha),
                               (particle_size // 2, particle_size // 2), particle_size // 2)
            screen.blit(particle, (px - particle_size // 2, py - particle_size // 2))

    def _draw_hp_bar(self, screen, rect, x, y, width):
        """Desenha barra de HP mais grossa com informações dentro"""
        hp_percent = self.pokemon.current_hp / self.pokemon.max_hp

        # Altura da barra (mais grossa)
        bar_height = int(rect.height * 0.18)
        bar_height = max(16, min(24, bar_height))  # Limites

        # Fundo da barra
        bg_rect = pygame.Rect(x, y, width, bar_height)
        pygame.draw.rect(screen, self.COLORS['hp_bg'], bg_rect, border_radius=6)

        # Barra de HP
        if hp_percent > 0.6:
            hp_color = self.COLORS['hp_green']
        elif hp_percent > 0.3:
            hp_color = self.COLORS['hp_yellow']
        else:
            hp_color = self.COLORS['hp_red']

        # Efeito de pulsação quando HP baixo
        if hp_percent < 0.2:
            pulse = 1.0 + 0.2 * math.sin(self.hp_animation * 10)
            hp_color = tuple(min(255, int(c * pulse)) for c in hp_color)

        current_width = max(3, int(width * hp_percent))
        hp_rect = pygame.Rect(x, y, current_width, bar_height)
        pygame.draw.rect(screen, hp_color, hp_rect, border_radius=6)

        # Borda da barra
        pygame.draw.rect(screen, (100, 100, 120, 100), bg_rect, 1, border_radius=6)

        # TEXTO DENTRO DA BARRA
        hp_text = f"{self.pokemon.current_hp}/{self.pokemon.max_hp}"

        # Calcula tamanho do texto
        text_surf = self.hp_font.render(hp_text, True, self.COLORS['hp_text'])

        # Só mostra texto se a barra for larga o suficiente
        if text_surf.get_width() < width * 0.9:
            # Posiciona texto no centro da barra
            text_x = x + (width - text_surf.get_width()) // 2
            text_y = y + (bar_height - text_surf.get_height()) // 2

            # Fundo semi-transparente para o texto (melhor legibilidade)
            text_bg = pygame.Surface((text_surf.get_width() + 4, text_surf.get_height() + 2), pygame.SRCALPHA)
            text_bg.fill((0, 0, 0, 100))
            screen.blit(text_bg, (text_x - 2, text_y - 1))

            screen.blit(text_surf, (text_x, text_y))

        # Ícone de status (se estiver em batalha)
        if hasattr(self.pokemon, 'in_battle') and self.pokemon.in_battle:
            battle_font = pygame.font.Font(None, int(bar_height * 1.5))
            battle_text = battle_font.render("⚔️", True, (255, 100, 100))
            screen.blit(battle_text, (rect.x + rect.width - 30, rect.y + 5))

    def _draw_empty_slot(self, screen, rect):
        """Desenha slot vazio com estilo"""
        center = rect.center

        # Círculo externo com animação sutil
        pulse = 1.0 + 0.1 * math.sin(self.hp_animation * 2)
        radius = int(min(rect.width, rect.height) * 0.2 * pulse)

        # Círculo
        pygame.draw.circle(screen, (60, 70, 90), center, radius, 3)

        # Símbolo de +
        plus_size = int(radius * 1.2)
        plus_font = pygame.font.Font(None, plus_size)
        plus_text = plus_font.render("+", True, (80, 90, 120))
        plus_rect = plus_text.get_rect(center=center)
        screen.blit(plus_text, plus_rect)

        # Texto "Vazio" pequeno
        empty_font = pygame.font.Font(None, max(12, int(rect.height * 0.15)))
        empty_text = empty_font.render("Vazio", True, (80, 90, 120))
        empty_rect = empty_text.get_rect(centerx=center[0], top=rect.y + rect.height - 20)
        screen.blit(empty_text, empty_rect)

    def on_resize(self, new_x, new_y):
        """Atualiza posição do slot"""
        self.rect.x = new_x
        self.rect.y = new_y
        self._create_fonts()