# src/scenes/game_scene/components/drag_drop.py

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
        self.hovered_pokemon = None
        self.place_preview_alpha = 0
        self.tile_size = 24

        self.drag_type = None  # "team" ou "placed"
        self.drag_source_spot = None

        # Preview
        self.preview_surface = None
        self.preview_size = 48
        self.preview_scale = 2.0

        # Cursor personalizado
        self.normal_cursor = pygame.SYSTEM_CURSOR_ARROW
        self.drag_cursor = pygame.SYSTEM_CURSOR_HAND

        # Cache de sprites
        self._sprite_cache = {}

    def _get_inmap_sprite_for_preview(self, pokemon):
        """Obtém o sprite InMap para preview mantendo proporção"""
        from src.data.pokedex import Pokedex
        pokedex = Pokedex()

        cache_key = f"{pokemon.id}_{pokemon.is_shiny}_inmap"
        if cache_key in self._sprite_cache:
            return self._sprite_cache[cache_key]

        inmap_frames = pokedex.get_inmap_animation(pokemon.id, pokemon.is_shiny)

        sprite = None
        if inmap_frames and "down" in inmap_frames and inmap_frames["down"]:
            sprite = inmap_frames["down"][0]

        if sprite is None:
            sprite = pokedex.get_sprite(pokemon.id, "front", pokemon.is_shiny)

        if sprite is None:
            sprite = self._create_preview_placeholder(pokemon)

        orig_width = sprite.get_width()
        orig_height = sprite.get_height()

        if orig_width > orig_height:
            target_width = self.preview_size
            target_height = int(orig_height * (self.preview_size / orig_width))
        else:
            target_height = self.preview_size
            target_width = int(orig_width * (self.preview_size / orig_height))

        scaled_sprite = pygame.transform.smoothscale(sprite, (target_width, target_height))

        final_surface = pygame.Surface((self.preview_size, self.preview_size), pygame.SRCALPHA)
        final_surface.fill((0, 0, 0, 0))

        offset_x = (self.preview_size - target_width) // 2
        offset_y = (self.preview_size - target_height) // 2
        final_surface.blit(scaled_sprite, (offset_x, offset_y))

        self._sprite_cache[cache_key] = final_surface
        return final_surface

    def _create_preview_placeholder(self, pokemon):
        """Cria um placeholder para preview quando não há sprite"""
        placeholder = pygame.Surface((self.preview_size, self.preview_size), pygame.SRCALPHA)

        colors = [
            (255, 99, 71), (135, 206, 235), (144, 238, 144),
            (255, 215, 0), (221, 160, 221), (255, 182, 193)
        ]
        color = colors[pokemon.id % len(colors)]
        pygame.draw.rect(placeholder, color, (0, 0, self.preview_size, self.preview_size), border_radius=8)
        pygame.draw.rect(placeholder, (100, 100, 100), (0, 0, self.preview_size, self.preview_size), 2, border_radius=8)

        font = pygame.font.Font(None, self.preview_size // 2)
        text = font.render(pokemon.name[0].upper(), True, (255, 255, 255))
        text_rect = text.get_rect(center=(self.preview_size // 2, self.preview_size // 2))
        placeholder.blit(text, text_rect)

        return placeholder

    def start_drag(self, slot_index, pokemon, screen_pos, world_pos):
        """Inicia o arrasto de um Pokémon do time"""
        if hasattr(pokemon, 'is_placed') and pokemon.is_placed:
            print(f"[DRAG] BLOQUEADO: {pokemon.name} já está no mapa!")
            return False

        self.is_dragging = True
        self.drag_type = "team"
        self.drag_slot_index = slot_index
        self.drag_pokemon = pokemon
        self.drag_source_spot = None
        self.drag_screen_pos = screen_pos
        self.drag_world_pos = world_pos

        self.preview_surface = self._get_inmap_sprite_for_preview(pokemon)
        self._add_glow_effect()

        pygame.mouse.set_cursor(self.drag_cursor)

        print(f"[DRAG] Arrastando {pokemon.name} do slot {slot_index}")
        return True

    def start_drag_placed(self, pokemon, spot, screen_pos, world_pos):
        """Inicia o arrasto de um Pokémon já colocado no mapa (para troca de spots)"""
        self.is_dragging = True
        self.drag_type = "placed"
        self.drag_slot_index = -1
        self.drag_pokemon = pokemon
        self.drag_source_spot = spot
        self.drag_screen_pos = screen_pos
        self.drag_world_pos = world_pos

        self.preview_surface = self._get_inmap_sprite_for_preview(pokemon)
        self._add_glow_effect()

        pygame.mouse.set_cursor(self.drag_cursor)

        print(f"[DRAG] Arrastando {pokemon.name} do spot ({spot.x // self.tile_size},{spot.y // self.tile_size})")
        return True

    def _add_glow_effect(self):
        """Adiciona efeito de brilho ao preview"""
        if not self.preview_surface:
            return

        glow_surface = pygame.Surface((self.preview_size, self.preview_size), pygame.SRCALPHA)
        center = (self.preview_size // 2, self.preview_size // 2)
        radius = self.preview_size // 2

        for i in range(3, 0, -1):
            alpha = 80 - i * 20
            color = (100, 200, 255, alpha)
            pygame.draw.circle(glow_surface, color, center, radius + i * 4, 3)

        final = self.preview_surface.copy()
        final.blit(glow_surface, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)

        if hasattr(self.drag_pokemon, 'is_shiny') and self.drag_pokemon.is_shiny:
            pygame.draw.rect(final, (255, 215, 0, 150), final.get_rect(), 3, border_radius=12)
        else:
            pygame.draw.rect(final, (255, 255, 255, 100), final.get_rect(), 3, border_radius=12)

        self.preview_surface = final

    def update_drag(self, screen_pos, world_pos, tower_spots, placed_pokemon, camera, placement_manager=None):
        """Atualiza a posição do arrasto"""
        if not self.is_dragging:
            return

        self.drag_screen_pos = screen_pos
        self.drag_world_pos = world_pos

        mouse_tile_x = world_pos[0] // self.tile_size
        mouse_tile_y = world_pos[1] // self.tile_size

        self.hovered_spot = None
        self.hovered_pokemon = None
        self.valid_target = False

        # ===== VERIFICA PRIMEIRO SE ESTÁ SOBRE UM POKÉMON COLOCADO =====
        if placement_manager and self.drag_type == "placed":
            for pokemon in placed_pokemon:
                if pokemon == self.drag_pokemon:
                    continue
                if not pokemon.is_alive() or pokemon.is_defeated:
                    continue

                pokemon_tile_x = pokemon.x // self.tile_size
                pokemon_tile_y = pokemon.y // self.tile_size

                if pokemon_tile_x == mouse_tile_x and pokemon_tile_y == mouse_tile_y:
                    self.hovered_pokemon = pokemon
                    self.valid_target = True
                    self.hovered_spot = None

                    for spot in tower_spots:
                        spot_tile_x = spot.x // self.tile_size
                        spot_tile_y = spot.y // self.tile_size
                        if spot_tile_x == pokemon_tile_x and spot_tile_y == pokemon_tile_y:
                            self.hovered_spot = spot
                            break

                    tile_center_x = (mouse_tile_x * self.tile_size) + self.tile_size // 2
                    tile_center_y = (mouse_tile_y * self.tile_size) + self.tile_size // 2
                    self.drag_world_pos = (tile_center_x, tile_center_y)

                    screen_x, screen_y = self.game.screen_manager.world_to_screen(
                        tile_center_x, tile_center_y, camera
                    )
                    self.drag_screen_pos = (screen_x, screen_y)

                    print(f"[DRAG] Sobre Pokémon {pokemon.name} - pode evoluir ou trocar")
                    break

        # ===== SE NÃO ESTÁ SOBRE POKÉMON, VERIFICA SPOTS VAZIOS =====
        if not self.valid_target:
            for spot in tower_spots:
                if spot.occupied:
                    continue

                spot_tile_x = spot.x // self.tile_size
                spot_tile_y = spot.y // self.tile_size

                if spot_tile_x == mouse_tile_x and spot_tile_y == mouse_tile_y:
                    self.hovered_spot = spot
                    self.valid_target = True

                    tile_center_x = (spot_tile_x * self.tile_size) + self.tile_size // 2
                    tile_center_y = (spot_tile_y * self.tile_size) + self.tile_size // 2
                    self.drag_world_pos = (tile_center_x, tile_center_y)

                    screen_x, screen_y = self.game.screen_manager.world_to_screen(
                        tile_center_x, tile_center_y, camera
                    )
                    self.drag_screen_pos = (screen_x, screen_y)
                    break

        self.place_preview_alpha = min(255, self.place_preview_alpha + 15)

    def _check_evolution_between_pokemon(self, pokemon_a, pokemon_b):
        """
        Verifica se dois Pokémon podem evoluir por combinação.
        Retorna os dados de evolução ou None.
        """
        # Tenta A evoluir com B
        evolution_data = pokemon_a.evolution.check_combination_evolution(pokemon_b)

        # Se não, tenta B evoluir com A
        if not evolution_data:
            evolution_data = pokemon_b.evolution.check_combination_evolution(pokemon_a)

        return evolution_data

    def stop_drag(self, tower_spots, on_place_callback=None, on_swap_callback=None, on_evolution_callback=None):
        """Finaliza o arrasto e tenta posicionar o Pokémon ou trocar com outro"""
        if not self.is_dragging:
            return None

        result = None

        # ===== PRIORIDADE 1: VERIFICA EVOLUÇÃO =====
        if self.valid_target and self.hovered_pokemon and self.drag_type == "placed":
            evolution_data = self._check_evolution_between_pokemon(self.drag_pokemon, self.hovered_pokemon)

            if evolution_data:
                print(f"[DRAG] Evolução detectada entre {self.drag_pokemon.name} e {self.hovered_pokemon.name}!")

                # CORRIGIDO: Quem evolui é o que está no SPOT (hovered_pokemon)
                # O drag_pokemon é o que está sendo arrastado (será consumido)
                result = {
                    'action': 'evolution',
                    'evolution_data': evolution_data,
                    'drag_pokemon': self.drag_pokemon,  # Será consumido/removido
                    'target_pokemon': self.hovered_pokemon,  # Este evolui
                    'drag_spot': self.drag_source_spot,
                    'target_spot': self.hovered_spot
                }

                if on_evolution_callback:
                    on_evolution_callback(result)

                self._reset_drag_state()
                return result

        # ===== PRIORIDADE 2: Troca com outro Pokémon (SÓ SE NÃO HOUVER EVOLUÇÃO) =====
        if self.valid_target and self.hovered_pokemon and self.drag_type == "placed":
            if (hasattr(self.drag_pokemon, 'is_placed') and self.drag_pokemon.is_placed and
                    hasattr(self.hovered_pokemon, 'is_placed') and self.hovered_pokemon.is_placed):

                target_spot = None
                for spot in tower_spots:
                    spot_tile_x = spot.x // self.tile_size
                    spot_tile_y = spot.y // self.tile_size
                    pokemon_tile_x = self.hovered_pokemon.x // self.tile_size
                    pokemon_tile_y = self.hovered_pokemon.y // self.tile_size

                    if spot_tile_x == pokemon_tile_x and spot_tile_y == pokemon_tile_y:
                        target_spot = spot
                        break

                if target_spot and self.drag_source_spot:
                    result = {
                        'action': 'swap',
                        'pokemon_a': self.drag_pokemon,
                        'pokemon_b': self.hovered_pokemon,
                        'spot_a': self.drag_source_spot,
                        'spot_b': target_spot
                    }

                    print(f"[DROP] Trocando {self.drag_pokemon.name} com {self.hovered_pokemon.name}")

                    if on_swap_callback:
                        on_swap_callback(result)

                    self._reset_drag_state()
                    return result

        # ===== PRIORIDADE 3: Colocar em spot vazio (time -> mapa) =====
        if self.valid_target and self.hovered_spot and self.drag_pokemon and not self.drag_pokemon.is_placed:
            if not self.hovered_spot.occupied:
                tile_center_x = (self.hovered_spot.x // self.tile_size) * self.tile_size + self.tile_size // 2
                tile_center_y = (self.hovered_spot.y // self.tile_size) * self.tile_size + self.tile_size // 2

                result = {
                    'action': 'place',
                    'pokemon': self.drag_pokemon,
                    'slot_index': self.drag_slot_index,
                    'spot': self.hovered_spot,
                    'world_pos': (tile_center_x, tile_center_y)
                }

                print(
                    f"[DROP] Colocando {self.drag_pokemon.name} no spot ({self.hovered_spot.x}, {self.hovered_spot.y})")

                if on_place_callback:
                    on_place_callback(result)

        # ===== PRIORIDADE 4: Mover Pokémon de um spot para outro spot vazio =====
        elif self.valid_target and self.hovered_spot and self.drag_type == "placed" and not self.hovered_spot.occupied:
            if hasattr(self.drag_pokemon, 'is_placed') and self.drag_pokemon.is_placed:
                result = {
                    'action': 'move',
                    'pokemon': self.drag_pokemon,
                    'from_spot': self.drag_source_spot,
                    'to_spot': self.hovered_spot,
                    'world_pos': (self.hovered_spot.x // self.tile_size * self.tile_size + self.tile_size // 2,
                                  self.hovered_spot.y // self.tile_size * self.tile_size + self.tile_size // 2)
                }

                print(f"[DROP] Movendo {self.drag_pokemon.name} para spot vazio")

                if on_place_callback:
                    on_place_callback(result)

        self._reset_drag_state()
        return result

    def _reset_drag_state(self):
        """Reseta o estado do drag"""
        self.is_dragging = False
        self.drag_pokemon = None
        self.drag_slot_index = -1
        self.drag_type = None
        self.drag_source_spot = None
        self.hovered_spot = None
        self.hovered_pokemon = None
        self.valid_target = False
        self.preview_surface = None
        self.place_preview_alpha = 0
        pygame.mouse.set_cursor(self.normal_cursor)

    def cancel_drag(self):
        """Cancela o arrasto"""
        self._reset_drag_state()

    def render(self, screen, camera):
        """Renderiza o preview durante o arrasto"""
        if not self.is_dragging or not self.preview_surface:
            return

        if self.valid_target and (self.hovered_spot or self.hovered_pokemon):
            preview_rect = self.preview_surface.get_rect()
            preview_rect.center = (int(self.drag_screen_pos[0]), int(self.drag_screen_pos[1]) - 15)
        else:
            mouse_x, mouse_y = pygame.mouse.get_pos()
            preview_rect = self.preview_surface.get_rect()
            preview_rect.center = (mouse_x, mouse_y - 20)

        preview_with_alpha = self.preview_surface.copy()
        alpha = min(200, self.place_preview_alpha)
        preview_with_alpha.set_alpha(alpha)

        screen.blit(preview_with_alpha, preview_rect)

        if self.valid_target:
            if self.hovered_pokemon:
                self._render_swap_indicator(screen, camera)
            elif self.hovered_spot:
                self._render_valid_indicator(screen, camera)

        self._render_drag_instructions(screen)

    def _render_swap_indicator(self, screen, camera):
        """Renderiza indicador de troca entre Pokémon"""
        if not self.hovered_pokemon:
            return

        tile_center_x = (self.hovered_pokemon.x // self.tile_size) * self.tile_size + self.tile_size // 2
        tile_center_y = (self.hovered_pokemon.y // self.tile_size) * self.tile_size + self.tile_size // 2

        spot_x, spot_y = self.game.screen_manager.world_to_screen(
            tile_center_x, tile_center_y, camera
        )

        pulse = 0.5 + 0.5 * math.sin(pygame.time.get_ticks() * 0.005)
        radius = 45 + int(15 * pulse)

        indicator = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
        alpha = int(150 + 105 * pulse)
        pygame.draw.circle(indicator, (255, 215, 0, alpha),
                           (radius, radius), radius, 4)
        pygame.draw.circle(indicator, (255, 215, 0, 80),
                           (radius, radius), radius - 8)

        screen.blit(indicator, (spot_x - radius, spot_y - radius))

        font = pygame.font.Font(None, 24)
        swap_text = font.render("⇄", True, (255, 215, 0))
        text_x = spot_x - swap_text.get_width() // 2
        text_y = spot_y - radius - 15
        screen.blit(swap_text, (text_x, text_y))

        font_small = pygame.font.Font(None, 20)
        text = font_small.render("TROCAR", True, (255, 215, 0))
        text_bg = pygame.Surface((text.get_width() + 10, text.get_height() + 4), pygame.SRCALPHA)
        text_bg.fill((0, 0, 0, 150))
        text_x = spot_x - text.get_width() // 2
        text_y = spot_y - radius - 35
        screen.blit(text_bg, (text_x - 5, text_y - 2))
        screen.blit(text, (text_x, text_y))

    def _render_valid_indicator(self, screen, camera):
        """Renderiza indicador de posição válida para colocar"""
        if not self.hovered_spot:
            return

        tile_center_x = (self.hovered_spot.x // self.tile_size) * self.tile_size + self.tile_size // 2
        tile_center_y = (self.hovered_spot.y // self.tile_size) * self.tile_size + self.tile_size // 2

        spot_x, spot_y = self.game.screen_manager.world_to_screen(
            tile_center_x, tile_center_y, camera
        )

        pulse = 0.5 + 0.5 * math.sin(pygame.time.get_ticks() * 0.005)
        radius = 35 + int(10 * pulse)

        indicator = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
        alpha = int(100 + 55 * pulse)
        pygame.draw.circle(indicator, (0, 255, 100, alpha),
                           (radius, radius), radius, 3)
        pygame.draw.circle(indicator, (0, 255, 100, 50),
                           (radius, radius), radius - 5)

        screen.blit(indicator, (spot_x - radius, spot_y - radius))

        if self.drag_type == "placed":
            text_str = "MOVER PARA AQUI"
        else:
            text_str = "SOLTAR PARA COLOCAR"

        font = pygame.font.Font(None, 20)
        text = font.render(text_str, True, (0, 255, 100))
        text_bg = pygame.Surface((text.get_width() + 10, text.get_height() + 4), pygame.SRCALPHA)
        text_bg.fill((0, 0, 0, 150))
        text_x = spot_x - text.get_width() // 2
        text_y = spot_y - radius - 25
        screen.blit(text_bg, (text_x - 5, text_y - 2))
        screen.blit(text, (text_x, text_y))

    def _render_drag_instructions(self, screen):
        """Renderiza instruções durante o arrasto"""
        font = pygame.font.Font(None, 18)

        if self.drag_type == "placed":
            instructions = [
                "Arraste para outro spot para mover",
                "Arraste sobre outro Pokémon para trocar/evoluir",
                "ESC para cancelar"
            ]
        else:
            instructions = [
                "Arraste até um spot para colocar",
                "ESC para cancelar"
            ]

        bg_height = len(instructions) * 22 + 10
        bg = pygame.Surface((250, bg_height), pygame.SRCALPHA)
        bg.fill((0, 0, 0, 180))

        mouse_x, mouse_y = pygame.mouse.get_pos()
        bg_x = mouse_x + 30
        bg_y = mouse_y - 30

        if bg_x + 250 > self.game.screen_manager.window_width:
            bg_x = mouse_x - 280
        if bg_y < 0:
            bg_y = mouse_y + 30

        screen.blit(bg, (bg_x, bg_y))

        y = bg_y + 5
        for text in instructions:
            if "evoluir" in text:
                color = (255, 100, 100)
            elif "trocar" in text or "mover" in text:
                color = (255, 215, 0)
            elif "spot" in text:
                color = (0, 255, 100)
            else:
                color = (200, 200, 200)
            text_surf = font.render(text, True, color)
            screen.blit(text_surf, (bg_x + 10, y))
            y += 22