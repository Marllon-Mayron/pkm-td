# src/scenes/game_scene/components/ui/drag_drop.py

import pygame
import math
from src.entities.pokemon import Pokemon


class DragDropManager:
    """Gerencia o arrastar e soltar de Pokémon do time para o mapa"""

    def __init__(self, game):
        self.game = game
        self.is_dragging = False
        self.drag_pokemon = None
        self.drag_slot_index = -1
        self.drag_world_pos = (0, 0)
        self.drag_screen_pos = (0, 0)
        self.valid_target = False
        self.hovered_spot = None
        self.place_preview_alpha = 0

        # Preview
        self.preview_surface = None
        self.preview_scale = 1.0

        # Cursor personalizado
        self.normal_cursor = pygame.SYSTEM_CURSOR_ARROW
        self.drag_cursor = pygame.SYSTEM_CURSOR_HAND

    def start_drag(self, slot_index, pokemon, screen_pos, world_pos):
        """Inicia o arrasto de um Pokémon"""
        self.is_dragging = True
        self.drag_slot_index = slot_index
        self.drag_pokemon = pokemon
        self.drag_screen_pos = screen_pos
        self.drag_world_pos = world_pos

        # Cria superfície de preview
        self._create_preview(pokemon)

        # Muda cursor
        pygame.mouse.set_cursor(self.drag_cursor)

        print(f"[DRAG] Arrastando {pokemon.name} do slot {slot_index}")

    def _create_preview(self, pokemon):
        """Cria a superfície de preview do Pokémon"""
        # Pega sprite inMap do Pokémon
        if hasattr(pokemon, 'inmap_frames') and pokemon.inmap_frames:
            frames = pokemon.inmap_frames
            if "down" in frames and frames["down"]:
                base_sprite = frames["down"][0]
            else:
                base_sprite = pokemon.sprite
        else:
            # Tenta pegar da pokedex
            from src.data.pokedex import Pokedex
            pokedex = Pokedex()
            frames = pokedex.get_inmap_animation(pokemon.id, pokemon.is_shiny)
            if frames and "down" in frames:
                base_sprite = frames["down"][0]
            else:
                base_sprite = pokemon.ui_sprite

        if base_sprite:
            # Tamanho maior para preview (2x)
            preview_size = int(base_sprite.get_width() * 2)
            self.preview_surface = pygame.transform.scale(base_sprite, (preview_size, preview_size))

            # Adiciona efeito de brilho
            self._add_glow_effect()

    def _add_glow_effect(self):
        """Adiciona efeito de brilho ao preview"""
        if not self.preview_surface:
            return

        # Cria uma cópia com efeito de brilho
        glow = pygame.Surface(self.preview_surface.get_size(), pygame.SRCALPHA)

        # Desenha círculos de brilho
        center = (glow.get_width() // 2, glow.get_height() // 2)
        radius = glow.get_width() // 2

        for i in range(3, 0, -1):
            alpha = 50 - i * 10
            color = (100, 200, 255, alpha)
            pygame.draw.circle(glow, color, center, radius + i * 5, 2)

        # Combina com o sprite original
        final = self.preview_surface.copy()
        final.blit(glow, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
        self.preview_surface = final

    def update_drag(self, screen_pos, world_pos, tower_spots, camera):
        """Atualiza a posição do arrasto"""
        if not self.is_dragging:
            return

        self.drag_screen_pos = screen_pos
        self.drag_world_pos = world_pos

        # Verifica se está sobre algum tower spot
        self.hovered_spot = None
        self.valid_target = False

        for spot in tower_spots:
            # Calcula distância do mouse ao spot (acessando como atributo, não como dicionário)
            spot_world_x = spot.x
            spot_world_y = spot.y
            distance = math.sqrt((world_pos[0] - spot_world_x) ** 2 +
                                 (world_pos[1] - spot_world_y) ** 2)

            # Raio de tolerância (tamanho do tile)
            tolerance = 32

            if distance < tolerance:
                self.hovered_spot = spot
                self.valid_target = True

                # Atualiza posição para o centro do spot
                self.drag_world_pos = (spot_world_x, spot_world_y)

                # Recalcula posição na tela
                screen_x, screen_y = self.game.screen_manager.world_to_screen(
                    spot_world_x, spot_world_y, camera
                )
                self.drag_screen_pos = (screen_x, screen_y)
                break

        # Anima o alpha do preview
        self.place_preview_alpha = min(255, self.place_preview_alpha + 15)

    def stop_drag(self, tower_spots, on_place_callback=None):
        """Finaliza o arrasto e tenta posicionar o Pokémon"""
        if not self.is_dragging:
            return None

        result = None

        # Se tem um spot hovered, coloca o Pokémon lá
        if self.valid_target and self.hovered_spot and self.drag_pokemon:
            result = {
                'pokemon': self.drag_pokemon,
                'slot_index': self.drag_slot_index,
                'spot': self.hovered_spot,
                'world_pos': self.drag_world_pos
            }

            print(f"[DROP] Colocando {self.drag_pokemon.name} no spot ({self.hovered_spot.x}, {self.hovered_spot.y})")

            if on_place_callback:
                on_place_callback(result)

        # Reseta estado
        self.is_dragging = False
        self.drag_pokemon = None
        self.drag_slot_index = -1
        self.hovered_spot = None
        self.valid_target = False
        self.preview_surface = None
        self.place_preview_alpha = 0

        # Restaura cursor
        pygame.mouse.set_cursor(self.normal_cursor)

        return result

    def cancel_drag(self):
        """Cancela o arrasto"""
        self.is_dragging = False
        self.drag_pokemon = None
        self.drag_slot_index = -1
        self.hovered_spot = None
        self.valid_target = False
        self.preview_surface = None
        self.place_preview_alpha = 0
        pygame.mouse.set_cursor(self.normal_cursor)

    def render(self, screen, camera):
        """Renderiza o preview durante o arrasto"""
        if not self.is_dragging or not self.preview_surface:
            return

        # Posição do preview (seguindo o mouse)
        mouse_x, mouse_y = pygame.mouse.get_pos()

        # Offset para centralizar no cursor
        preview_rect = self.preview_surface.get_rect()
        preview_rect.center = (mouse_x, mouse_y - 20)  # Um pouco acima do cursor

        # Aplica transparência
        preview_with_alpha = self.preview_surface.copy()
        alpha = min(200, self.place_preview_alpha)
        preview_with_alpha.set_alpha(alpha)

        screen.blit(preview_with_alpha, preview_rect)

        # Se tem um spot hovered, mostra indicador de posição válida
        if self.valid_target and self.hovered_spot:
            self._render_valid_indicator(screen, camera)

        # Instruções
        self._render_drag_instructions(screen)

    def _render_valid_indicator(self, screen, camera):
        """Renderiza indicador de posição válida"""
        if not self.hovered_spot:
            return

        # Posição do spot na tela
        spot_x, spot_y = self.game.screen_manager.world_to_screen(
            self.hovered_spot.x, self.hovered_spot.y, camera
        )

        # Círculo pulsante
        pulse = 0.5 + 0.5 * math.sin(pygame.time.get_ticks() * 0.005)
        radius = 30 + int(10 * pulse)

        # Superfície com alpha
        indicator = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)

        # Círculo externo
        alpha = int(100 + 55 * pulse)
        pygame.draw.circle(indicator, (0, 255, 100, alpha),
                           (radius, radius), radius, 3)

        # Círculo interno
        pygame.draw.circle(indicator, (0, 255, 100, 50),
                           (radius, radius), radius - 5)

        screen.blit(indicator, (spot_x - radius, spot_y - radius))

        # Texto "SOLTAR PARA COLOCAR"
        font = pygame.font.Font(None, 20)
        text = font.render("SOLTAR PARA COLOCAR", True, (0, 255, 100))
        text_bg = pygame.Surface((text.get_width() + 10, text.get_height() + 4), pygame.SRCALPHA)
        text_bg.fill((0, 0, 0, 150))

        text_x = spot_x - text.get_width() // 2
        text_y = spot_y - radius - 25

        screen.blit(text_bg, (text_x - 5, text_y - 2))
        screen.blit(text, (text_x, text_y))

    def _render_drag_instructions(self, screen):
        """Renderiza instruções durante o arrasto"""
        font = pygame.font.Font(None, 18)

        # Fundo
        instructions = [
            "Arraste até um spot para colocar",
            "ESC para cancelar"
        ]

        bg_height = len(instructions) * 22 + 10
        bg = pygame.Surface((200, bg_height), pygame.SRCALPHA)
        bg.fill((0, 0, 0, 180))

        mouse_x, mouse_y = pygame.mouse.get_pos()
        bg_x = mouse_x + 30
        bg_y = mouse_y - 30

        # Garante que fique dentro da tela
        if bg_x + 200 > self.game.screen_manager.window_width:
            bg_x = mouse_x - 230
        if bg_y < 0:
            bg_y = mouse_y + 30

        screen.blit(bg, (bg_x, bg_y))

        y = bg_y + 5
        for text in instructions:
            color = (0, 255, 100) if "spot" in text else (200, 200, 200)
            text_surf = font.render(text, True, color)
            screen.blit(text_surf, (bg_x + 10, y))
            y += 22