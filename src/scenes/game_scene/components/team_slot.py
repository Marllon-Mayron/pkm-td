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
        'shiny': (255, 215, 0, 150),
        'xp_bar': (100, 180, 255),  # Azul para XP
        'xp_bg': (40, 45, 60),  # Fundo da barra de XP
        'level_bg': (50, 40, 70),  # Fundo do level
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
        self.xp_font = None
        self._create_fonts()

    def _create_fonts(self):
        """Cria fontes com tamanhos responsivos"""
        base_size = max(14, int(self.rect.height * 0.18))
        small_size = max(12, int(base_size * 0.8))
        self.name_font = pygame.font.Font(None, base_size)
        self.level_font = pygame.font.Font(None, base_size)
        self.hp_font = pygame.font.Font(None, small_size)
        self.xp_font = pygame.font.Font(None, max(10, int(small_size * 0.8)))

    def set_pokemon(self, pokemon):
        """Define o Pokémon do slot"""
        self.pokemon = pokemon

    def handle_event(self, event, bag_manager=None):
        """Processa eventos no slot - AGORA COM POKEBOLA"""
        if event.type == pygame.MOUSEMOTION:
            was_hovered = self.is_hovered
            self.is_hovered = self.rect.collidepoint(event.pos)

            if was_hovered != self.is_hovered:
                self.animation_offset = 8 if self.is_hovered else 0
                self.glow_alpha = 100 if self.is_hovered else 0

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.is_hovered:
                # Se tem Pokémon, pode iniciar arrasto de Pokémon
                if self.pokemon:
                    # VERIFICA SE O POKÉMON JÁ ESTÁ NO MAPA
                    if hasattr(self.pokemon, 'is_placed') and self.pokemon.is_placed:
                        print(f"[SLOT] {self.pokemon.name} já está no mapa!")
                        return {
                            'action': 'already_placed',
                            'slot_index': self.slot_index,
                            'pokemon': self.pokemon
                        }

                    # Pokémon não está no mapa - permite arrastar
                    return {
                        'action': 'start_drag',
                        'slot_index': self.slot_index,
                        'pokemon': self.pokemon
                    }

                # Slot vazio - poderia iniciar arrasto de pokebola?
                # Por enquanto, só seleciona
                return {
                    'action': 'select',
                    'slot_index': self.slot_index
                }

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:  # Clique direito
            if self.is_hovered and bag_manager and bag_manager.has_items():
                # Se tem itens e clicou direito, usa o item selecionado no Pokémon
                if self.pokemon:
                    return {
                        'action': 'use_item',
                        'slot_index': self.slot_index,
                        'pokemon': self.pokemon,
                        'item': bag_manager.get_selected_item()
                    }

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

            # Indicador de "no mapa" - agora usa a flag atualizada
            if hasattr(self.pokemon, 'is_placed') and self.pokemon.is_placed:
                self._draw_placed_indicator(screen, animated_rect)
        else:
            self._draw_empty_slot(screen, animated_rect)

    def _draw_placed_indicator(self, screen, rect):
        """Desenha indicador de que o Pokémon está no mapa"""
        # Círculo verde no canto superior esquerdo
        indicator_size = 12
        indicator_x = rect.x + 5
        indicator_y = rect.y + 5

        # Círculo com brilho
        pygame.draw.circle(screen, (0, 200, 0),
                           (indicator_x + indicator_size // 2, indicator_y + indicator_size // 2),
                           indicator_size // 2)
        pygame.draw.circle(screen, (255, 255, 255),
                           (indicator_x + indicator_size // 2, indicator_y + indicator_size // 2),
                           indicator_size // 2 - 2)

        # Ícone de check
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
            # Se estiver no mapa, borda diferente no hover
            if self.pokemon and hasattr(self.pokemon, 'is_placed') and self.pokemon.is_placed:
                border_color = (100, 255, 100)  # Verde quando no mapa
            else:
                border_color = self.COLORS['border_hover']
        else:
            base_color = self.COLORS['bg_default']
            # Borda normal ou verde se estiver no mapa
            if self.pokemon and hasattr(self.pokemon, 'is_placed') and self.pokemon.is_placed:
                border_color = (0, 200, 0)  # Verde quando no mapa
            else:
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
        """Desenha informações do Pokémon"""

        # ===== 1. TIPOS ACIMA DO SLOT =====
        self._draw_types_above(screen, rect)

        # ===== 2. LEVEL FIXO NO CANTO SUPERIOR DIREITO =====
        level_text = f"Lv.{self.pokemon.level}"
        level_surf = self.level_font.render(level_text, True, (255, 215, 100))

        # Fundo do level no canto superior direito
        level_bg_width = level_surf.get_width() + 8
        level_bg_height = level_surf.get_height() + 4
        level_bg_x = rect.x + rect.width - level_bg_width - 10  # 10px de margem direita
        level_bg_y = rect.y + 8  # 8px do topo

        pygame.draw.rect(screen, self.COLORS['level_bg'],
                         (level_bg_x, level_bg_y, level_bg_width, level_bg_height),
                         border_radius=4)
        pygame.draw.rect(screen, (100, 80, 120),
                         (level_bg_x, level_bg_y, level_bg_width, level_bg_height),
                         1, border_radius=4)

        screen.blit(level_surf, (level_bg_x + 4, level_bg_y + 2))

        # ===== 3. NOME (CENTRO SUPERIOR, DESLOCADO PARA NÃO SOBREPOR O LEVEL) =====
        name_y = rect.y + 12

        # Nome do Pokémon
        name_text = self.pokemon.name
        if self.name_font.size(name_text)[0] > rect.width * 0.5:
            name_text = self.pokemon.name[:12] + "..."

        name_surf = self.name_font.render(name_text, True, self.COLORS['text'])

        # Centraliza o nome, considerando que o level está na direita
        # Para não sobrepor, limitamos a largura máxima do nome
        max_name_width = rect.width - level_bg_width - 30  # 30px de margem
        if name_surf.get_width() > max_name_width:
            # Se o nome for muito largo, centraliza considerando o espaço disponível
            name_x = rect.x + 10  # Margem esquerda
        else:
            # Centraliza normalmente
            name_x = rect.x + (rect.width - name_surf.get_width()) // 2

        screen.blit(name_surf, (name_x, name_y))

        # ===== 4. SPRITE GRANDE NO CENTRO =====
        sprite_size = int(rect.height * 0.65)  # 65% da altura - MAIOR
        sprite = pokedex.get_sprite(self.pokemon.id, "front", self.pokemon.is_shiny)

        if sprite:
            sprite_scaled = pygame.transform.scale(sprite, (sprite_size, sprite_size))

            # Centraliza o sprite no slot
            sprite_x = rect.x + (rect.width - sprite_size) // 2
            sprite_y = rect.y + (rect.height - sprite_size) // 2 - 5  # Ajuste vertical
            screen.blit(sprite_scaled, (sprite_x, sprite_y))

            # Efeito de brilho para shiny
            if self.pokemon.is_shiny:
                self._draw_shiny_effect(screen, sprite_x, sprite_y, sprite_size)

        # ===== 5. BARRA DE HP (MAIS LARGA) =====
        hp_y = rect.y + rect.height - 45
        self._draw_hp_bar(screen, rect, hp_y)

        # ===== 6. BARRA DE XP (MAIS LARGA) =====
        xp_y = rect.y + rect.height - 22
        self._draw_xp_bar(screen, rect, xp_y)

    def _draw_types_above(self, screen, rect):
        """Desenha os tipos ACIMA do slot, centralizados"""
        if not self.pokemon.types:
            return

        # Cores dos tipos
        type_colors = {
            'normal': (168, 168, 120),
            'fire': (240, 128, 48),
            'water': (104, 144, 240),
            'electric': (248, 208, 48),
            'grass': (120, 200, 80),
            'ice': (152, 216, 216),
            'fighting': (192, 48, 40),
            'poison': (160, 64, 160),
            'ground': (224, 192, 104),
            'flying': (168, 144, 240),
            'psychic': (248, 88, 136),
            'bug': (168, 184, 32),
            'rock': (184, 160, 56),
            'ghost': (112, 88, 152),
            'dragon': (112, 56, 248),
            'dark': (112, 88, 72),
            'steel': (184, 184, 208),
            'fairy': (238, 153, 238)
        }

        # Calcula largura total dos tipos para centralizar
        total_width = 0
        type_surfs = []
        type_bg_widths = []

        for type_name in self.pokemon.types:
            color = type_colors.get(type_name.lower(), (150, 150, 150))

            type_text = type_name.capitalize()
            type_surf = self.xp_font.render(type_text, True, (255, 255, 255))

            padding = 8
            bg_width = type_surf.get_width() + padding * 2

            type_surfs.append((type_surf, color))
            type_bg_widths.append(bg_width)
            total_width += bg_width + 5  # +5 de espaçamento entre tipos

        # Remove o último espaçamento
        if len(self.pokemon.types) > 0:
            total_width -= 5

        # Posição inicial (centralizada acima do slot)
        start_x = rect.x + (rect.width - total_width) // 2
        y = rect.y - 22  # Acima do slot

        for i, (type_surf, color) in enumerate(type_surfs):
            bg_width = type_bg_widths[i]
            bg_height = type_surf.get_height() + 6

            # Desenha fundo com sombra
            shadow_rect = pygame.Rect(start_x + 2, y + 2, bg_width, bg_height)
            pygame.draw.rect(screen, (0, 0, 0, 100), shadow_rect, border_radius=8)

            # Fundo principal
            bg_rect = pygame.Rect(start_x, y, bg_width, bg_height)
            pygame.draw.rect(screen, color, bg_rect, border_radius=8)

            # Borda interna mais clara
            pygame.draw.rect(screen, (255, 255, 255, 180), bg_rect, 2, border_radius=8)

            # Desenha texto
            text_x = start_x + (bg_width - type_surf.get_width()) // 2
            text_y = y + (bg_height - type_surf.get_height()) // 2
            screen.blit(type_surf, (text_x, text_y))

            # Avança para o próximo tipo
            start_x += bg_width + 5

    def _draw_hp_bar(self, screen, rect, y):
        """Desenha barra de HP MAIS LARGA"""
        hp_percent = self.pokemon.current_hp / self.pokemon.max_hp

        # Largura da barra (ocupando quase toda a largura do slot)
        bar_width = rect.width - 20  # Margem de 10px de cada lado
        bar_x = rect.x + 10

        # Altura da barra
        bar_height = 18

        # Fundo da barra
        bg_rect = pygame.Rect(bar_x, y, bar_width, bar_height)
        pygame.draw.rect(screen, self.COLORS['hp_bg'], bg_rect, border_radius=8)

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

        current_width = max(3, int(bar_width * hp_percent))
        hp_rect = pygame.Rect(bar_x, y, current_width, bar_height)
        pygame.draw.rect(screen, hp_color, hp_rect, border_radius=8)

        # Borda da barra
        pygame.draw.rect(screen, (100, 100, 120, 150), bg_rect, 2, border_radius=8)

        # TEXTO DENTRO DA BARRA
        hp_text = f"{self.pokemon.current_hp}/{self.pokemon.max_hp}"
        text_surf = self.hp_font.render(hp_text, True, self.COLORS['hp_text'])

        # Centraliza texto na barra
        text_x = bar_x + (bar_width - text_surf.get_width()) // 2
        text_y = y + (bar_height - text_surf.get_height()) // 2

        # Fundo semi-transparente para o texto
        text_bg = pygame.Surface((text_surf.get_width() + 6, text_surf.get_height() + 4), pygame.SRCALPHA)
        text_bg.fill((0, 0, 0, 120))
        screen.blit(text_bg, (text_x - 3, text_y - 2))

        screen.blit(text_surf, (text_x, text_y))

    def _draw_xp_bar(self, screen, rect, y):
        """Desenha barra de XP MAIS LARGA"""
        # Calcula porcentagem de XP
        xp_percent = self.pokemon.xp / self.pokemon.xp_to_next if self.pokemon.xp_to_next > 0 else 0
        xp_percent = min(1.0, max(0.0, xp_percent))

        # Mesma largura da barra de HP
        bar_width = rect.width - 20
        bar_x = rect.x + 10

        # Altura da barra
        bar_height = 14

        # Fundo da barra
        bg_rect = pygame.Rect(bar_x, y, bar_width, bar_height)
        pygame.draw.rect(screen, self.COLORS['xp_bg'], bg_rect, border_radius=6)

        # Barra de XP
        xp_width = max(2, int(bar_width * xp_percent))
        if xp_width > 0:
            xp_rect = pygame.Rect(bar_x, y, xp_width, bar_height)

            # Cor gradiente para XP
            if xp_percent > 0.8:
                xp_color = (150, 230, 255)
            elif xp_percent > 0.5:
                xp_color = (100, 200, 255)
            else:
                xp_color = (70, 150, 255)

            pygame.draw.rect(screen, xp_color, xp_rect, border_radius=6)

        # Borda
        pygame.draw.rect(screen, (60, 70, 90), bg_rect, 1, border_radius=6)

        # Texto de XP
        xp_text = f"{self.pokemon.xp}/{self.pokemon.xp_to_next} XP"
        text_surf = self.xp_font.render(xp_text, True, (200, 220, 255))

        # Centraliza texto na barra
        text_x = bar_x + (bar_width - text_surf.get_width()) // 2
        text_y = y + (bar_height - text_surf.get_height()) // 2

        # Fundo semi-transparente
        text_bg = pygame.Surface((text_surf.get_width() + 4, text_surf.get_height() + 2), pygame.SRCALPHA)
        text_bg.fill((0, 0, 0, 80))
        screen.blit(text_bg, (text_x - 2, text_y - 1))

        screen.blit(text_surf, (text_x, text_y))

        # Indicador de XP cheio
        if xp_percent >= 1.0:
            star_font = pygame.font.Font(None, 16)
            star = star_font.render("★", True, (255, 215, 0))
            screen.blit(star, (bar_x + bar_width + 5, y - 2))

    def _draw_shiny_effect(self, screen, x, y, size):
        """Desenha efeito de brilho para Pokémon shiny"""
        # Estrelas brilhantes ao redor do sprite
        for i in range(6):
            angle = (self.hp_animation * 2 + i * 60) % 360
            rad = math.radians(angle)

            # Posição ao redor do sprite
            px = x + size // 2 + math.cos(rad) * (size // 2 + 10)
            py = y + size // 2 + math.sin(rad) * (size // 2 + 10)

            # Partícula brilhante
            alpha = int(150 + 105 * math.sin(self.hp_animation * 4 + i))
            particle_size = 5 + int(3 * math.sin(self.hp_animation * 3 + i))

            particle = pygame.Surface((particle_size, particle_size), pygame.SRCALPHA)
            pygame.draw.circle(particle, (255, 215, 0, alpha),
                               (particle_size // 2, particle_size // 2), particle_size // 2)
            screen.blit(particle, (px - particle_size // 2, py - particle_size // 2))

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