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
        self.hovered_pokemon = None  # NOVO: Pokémon sob o mouse (para troca)
        self.place_preview_alpha = 0
        self.tile_size = 24  # Tamanho do tile

        # NOVO: Tipo de drag (team ou placed)
        self.drag_type = None  # "team" ou "placed"
        self.drag_source_spot = None  # Spot de origem (se for drag de Pokémon colocado)

        # Preview
        self.preview_surface = None
        self.preview_scale = 1.0

        # Cursor personalizado
        self.normal_cursor = pygame.SYSTEM_CURSOR_ARROW
        self.drag_cursor = pygame.SYSTEM_CURSOR_HAND

    def start_drag(self, slot_index, pokemon, screen_pos, world_pos):
        """Inicia o arrasto de um Pokémon do time - com validação"""
        # VALIDAÇÃO DUPLA: Verifica se já está no mapa
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

        # Cria superfície de preview
        self._create_preview(pokemon)

        # Muda cursor
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

        # Cria superfície de preview
        self._create_preview(pokemon)

        # Muda cursor
        pygame.mouse.set_cursor(self.drag_cursor)

        print(f"[DRAG] Arrastando {pokemon.name} do spot {spot.x // self.tile_size},{spot.y // self.tile_size}")
        return True

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

    def update_drag(self, screen_pos, world_pos, tower_spots, placed_pokemon, camera, placement_manager=None):
        """Atualiza a posição do arrasto"""
        if not self.is_dragging:
            return

        self.drag_screen_pos = screen_pos
        self.drag_world_pos = world_pos

        # Converte posição do mouse para tile
        mouse_tile_x = world_pos[0] // self.tile_size
        mouse_tile_y = world_pos[1] // self.tile_size

        # Reseta hover
        self.hovered_spot = None
        self.hovered_pokemon = None
        self.valid_target = False

        # ===== VERIFICA PRIMEIRO SE ESTÁ SOBRE UM POKÉMON COLOCADO =====
        if placement_manager and self.drag_type == "placed":
            # Só permite troca se está arrastando um Pokémon já colocado
            for pokemon in placed_pokemon:
                if pokemon == self.drag_pokemon:
                    continue  # Ignora o próprio Pokémon

                # Calcula tile do Pokémon
                pokemon_tile_x = pokemon.x // self.tile_size
                pokemon_tile_y = pokemon.y // self.tile_size

                if pokemon_tile_x == mouse_tile_x and pokemon_tile_y == mouse_tile_y:
                    # Encontrou um Pokémon para trocar
                    self.hovered_pokemon = pokemon
                    self.valid_target = True
                    self.hovered_spot = None

                    # Encontra o spot desse Pokémon
                    for spot in tower_spots:
                        spot_tile_x = spot.x // self.tile_size
                        spot_tile_y = spot.y // self.tile_size
                        if spot_tile_x == pokemon_tile_x and spot_tile_y == pokemon_tile_y:
                            self.hovered_spot = spot
                            break

                    # Atualiza posição do preview para o centro do tile
                    tile_center_x = (mouse_tile_x * self.tile_size) + self.tile_size // 2
                    tile_center_y = (mouse_tile_y * self.tile_size) + self.tile_size // 2
                    self.drag_world_pos = (tile_center_x, tile_center_y)

                    screen_x, screen_y = self.game.screen_manager.world_to_screen(
                        tile_center_x, tile_center_y, camera
                    )
                    self.drag_screen_pos = (screen_x, screen_y)

                    print(f"[DRAG] Sobre Pokémon {pokemon.name} - pode trocar")
                    break

        # ===== SE NÃO ESTÁ SOBRE POKÉMON, VERIFICA SPOTS VAZIOS =====
        if not self.valid_target:
            for spot in tower_spots:
                # Pula spots ocupados (não pode colocar em spot ocupado)
                if spot.occupied:
                    continue

                # Converte spot para coordenadas de tile
                spot_tile_x = spot.x // self.tile_size
                spot_tile_y = spot.y // self.tile_size

                # Verifica se é o mesmo tile
                if spot_tile_x == mouse_tile_x and spot_tile_y == mouse_tile_y:
                    self.hovered_spot = spot
                    self.valid_target = True

                    # Posição do centro do tile em coordenadas do mundo
                    tile_center_x = (spot_tile_x * self.tile_size) + self.tile_size // 2
                    tile_center_y = (spot_tile_y * self.tile_size) + self.tile_size // 2

                    # Atualiza posição para o centro do tile
                    self.drag_world_pos = (tile_center_x, tile_center_y)

                    # Recalcula posição na tela
                    screen_x, screen_y = self.game.screen_manager.world_to_screen(
                        tile_center_x, tile_center_y, camera
                    )
                    self.drag_screen_pos = (screen_x, screen_y)
                    break

        # Anima o alpha do preview
        self.place_preview_alpha = min(255, self.place_preview_alpha + 15)

    def stop_drag(self, tower_spots, on_place_callback=None, on_swap_callback=None):
        """Finaliza o arrasto e tenta posicionar o Pokémon ou trocar com outro"""
        if not self.is_dragging:
            return None

        result = None

        # ===== CASO 1: Troca com outro Pokémon =====
        if self.valid_target and self.hovered_pokemon and self.drag_type == "placed":
            # Verifica se os dois Pokémon estão colocados
            if (hasattr(self.drag_pokemon, 'is_placed') and self.drag_pokemon.is_placed and
                    hasattr(self.hovered_pokemon, 'is_placed') and self.hovered_pokemon.is_placed):

                # Encontra o spot do Pokémon alvo
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

        # ===== CASO 2: Colocar em spot vazio (time -> mapa) =====
        elif self.valid_target and self.hovered_spot and self.drag_pokemon and not self.drag_pokemon.is_placed:
            # Verifica se o spot não está ocupado
            if not self.hovered_spot.occupied:
                # Calcula posição central do tile para o Pokémon
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

        # ===== CASO 3: Mover Pokémon de um spot para outro spot vazio =====
        elif self.valid_target and self.hovered_spot and self.drag_type == "placed" and not self.hovered_spot.occupied:
            # Verifica se o Pokémon está colocado e o spot alvo está vazio
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
                    # Reutiliza o callback de place para mover
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

        # Se tem um spot hovered, desenha o preview no centro do tile
        if self.valid_target and self.hovered_spot:
            # Usa a posição calculada do centro do tile
            preview_rect = self.preview_surface.get_rect()
            preview_rect.center = (int(self.drag_screen_pos[0]), int(self.drag_screen_pos[1]) - 20)
        else:
            # Segue o mouse
            mouse_x, mouse_y = pygame.mouse.get_pos()
            preview_rect = self.preview_surface.get_rect()
            preview_rect.center = (mouse_x, mouse_y - 20)

        # Aplica transparência
        preview_with_alpha = self.preview_surface.copy()
        alpha = min(200, self.place_preview_alpha)
        preview_with_alpha.set_alpha(alpha)

        screen.blit(preview_with_alpha, preview_rect)

        # Se tem um spot hovered ou Pokémon hovered, mostra indicador
        if self.valid_target:
            if self.hovered_pokemon:
                self._render_swap_indicator(screen, camera)
            elif self.hovered_spot:
                self._render_valid_indicator(screen, camera)

        # Instruções
        self._render_drag_instructions(screen)

    def _render_swap_indicator(self, screen, camera):
        """Renderiza indicador de troca entre Pokémon"""
        if not self.hovered_pokemon:
            return

        # Calcula centro do tile do Pokémon alvo
        tile_center_x = (self.hovered_pokemon.x // self.tile_size) * self.tile_size + self.tile_size // 2
        tile_center_y = (self.hovered_pokemon.y // self.tile_size) * self.tile_size + self.tile_size // 2

        # Posição do centro do tile na tela
        spot_x, spot_y = self.game.screen_manager.world_to_screen(
            tile_center_x, tile_center_y, camera
        )

        # Círculo pulsante com cor diferente (amarelo para troca)
        pulse = 0.5 + 0.5 * math.sin(pygame.time.get_ticks() * 0.005)
        radius = 40 + int(15 * pulse)

        # Superfície com alpha
        indicator = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)

        # Círculo externo (amarelo para troca)
        alpha = int(150 + 105 * pulse)
        pygame.draw.circle(indicator, (255, 215, 0, alpha),
                           (radius, radius), radius, 4)

        # Círculo interno
        pygame.draw.circle(indicator, (255, 215, 0, 80),
                           (radius, radius), radius - 8)

        screen.blit(indicator, (spot_x - radius, spot_y - radius))

        # Ícone de troca
        font = pygame.font.Font(None, 24)
        swap_text = font.render("⇄", True, (255, 215, 0))
        text_x = spot_x - swap_text.get_width() // 2
        text_y = spot_y - radius - 15
        screen.blit(swap_text, (text_x, text_y))

        # Texto "TROCAR"
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

        # Calcula centro do tile
        tile_center_x = (self.hovered_spot.x // self.tile_size) * self.tile_size + self.tile_size // 2
        tile_center_y = (self.hovered_spot.y // self.tile_size) * self.tile_size + self.tile_size // 2

        # Posição do centro do tile na tela
        spot_x, spot_y = self.game.screen_manager.world_to_screen(
            tile_center_x, tile_center_y, camera
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

        # Texto
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

        # Fundo
        if self.drag_type == "placed":
            instructions = [
                "Arraste para outro spot para mover",
                "Arraste sobre outro Pokémon para trocar",
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

        # Garante que fique dentro da tela
        if bg_x + 250 > self.game.screen_manager.window_width:
            bg_x = mouse_x - 280
        if bg_y < 0:
            bg_y = mouse_y + 30

        screen.blit(bg, (bg_x, bg_y))

        y = bg_y + 5
        for text in instructions:
            if "trocar" in text or "mover" in text:
                color = (255, 215, 0)
            elif "spot" in text:
                color = (0, 255, 100)
            else:
                color = (200, 200, 200)
            text_surf = font.render(text, True, color)
            screen.blit(text_surf, (bg_x + 10, y))
            y += 22