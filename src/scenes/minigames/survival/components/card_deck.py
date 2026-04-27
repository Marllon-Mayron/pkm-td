# src/scenes/minigames/survival/components/card_deck.py

"""
Sistema de deck estilo UNO - Suporta Pokémon e Itens
SEM ESTEIRA - Cartas fixas no leque
"""
import pygame
import random
import math
from typing import List, Dict, Any, Optional
from collections import deque
from src.data.pokedex import Pokedex
from src.data.item_bag_catalog import item_bag_catalog


class CardDeck:
    """Gerencia o deck de cartas estilo UNO (Pokémon e Itens) - SEM ESTEIRA"""

    CARD_WIDTH = 110
    CARD_HEIGHT = 150

    # Configurações do leque
    FAN_ANGLE = 35
    FAN_RADIUS = 270
    CARD_SPACING_MULTIPLIER = 1

    # Configurações do deck
    STARTING_CARDS = 3
    MAX_DECK_SIZE = 10
    DECK_GROWTH_INCREMENT = 1
    ENERGY_REWARD = 30

    # Configurações do recycle
    RECYCLE_COOLDOWN = 10.0
    RECYCLE_BUTTON_WIDTH = 80
    RECYCLE_BUTTON_HEIGHT = 40

    # Configurações de animação
    CARD_SELECT_RISE = -55

    def __init__(self, game_scene):
        self.game_scene = game_scene
        self.pokedex = Pokedex()
        self.item_catalog = item_bag_catalog

        # Pool de cartas (Pokémon e Itens)
        self.pokemon_pool: List[Dict] = []
        self.item_pool: List[Dict] = []
        self.card_pool: List[Dict] = []
        self.cards: List[Dict] = []
        self.card_cooldowns: Dict[int, float] = {}

        # Progressão do deck
        self.current_deck_size = self.STARTING_CARDS
        self.cards_used_in_current_deck = 0
        self.total_decks_completed = 0

        # Estado do recycle
        self.recycle_cooldown_remaining = 0.0
        self.recycle_hovered = False

        # Sistema de animação (apenas para subir/descer)
        self.card_x_positions: List[float] = []
        self.target_x_positions: List[float] = []
        self.card_y_positions: List[float] = []
        self.target_y_positions: List[float] = []
        self.card_rotations: List[float] = []
        self.target_rotations: List[float] = []
        self.card_selected_rise: List[float] = []
        self.target_selected_rise: List[float] = []

        # Seleção
        self.selected_index = -1
        self.hovered_index = -1

        # Cache
        self._font_cache = {}
        self._portrait_cache = {}
        self._item_sprite_cache = {}

        # Posições do leque
        self.fan_positions: List[tuple] = []

        # Cores
        self.COLORS = {
            'bg_dark': (18, 22, 35),
            'bg_light': (28, 34, 50),
            'border': (70, 90, 130),
            'border_glow': (100, 150, 220),
            'text': (240, 245, 255),
            'text_dim': (160, 170, 200),
            'cost': (255, 200, 50),
            'cooldown': (100, 150, 220),
            'energy_insufficient': (180, 60, 60),
            'level': (255, 180, 50),
            'recycle': (80, 150, 200),
            'recycle_disabled': (80, 80, 100),
            'selected_glow': (255, 215, 0),
            'item_bg': (50, 70, 100),
            'item_border': (100, 150, 200),
        }

        # Cores por tipo
        self.TYPE_COLORS = {
            "normal": (168, 168, 120), "fire": (240, 128, 48), "water": (104, 144, 240),
            "electric": (248, 208, 48), "grass": (120, 200, 80), "ice": (152, 216, 216),
            "fighting": (192, 48, 40), "poison": (160, 64, 160), "ground": (224, 192, 104),
            "flying": (168, 144, 240), "psychic": (248, 88, 136), "bug": (168, 184, 32),
            "rock": (184, 160, 56), "ghost": (112, 88, 152), "dragon": (112, 56, 248),
            "dark": (112, 88, 72), "steel": (184, 184, 208), "fairy": (238, 153, 238),
        }
        self.DEFAULT_TYPE_COLOR = (100, 100, 140)

    def set_card_pools(self, pokemon_pool: List[Dict], item_pool: List[Dict]):
        """Define os pools de Pokémon e Itens"""
        self.pokemon_pool = pokemon_pool.copy()
        self.item_pool = item_pool.copy()

        self.card_pool = []
        for p in self.pokemon_pool:
            card = {
                "type": "pokemon",
                "data": p,
                "name": self.pokedex.get_name(p["id"]),
                "cost": p["cost"],
                "level": p.get("level", 5),
                "type_name": self.pokedex.get_types(p["id"])[0] if self.pokedex.get_types(p["id"]) else "normal"
            }
            self.card_pool.append(card)

        for i in self.item_pool:
            card = {
                "type": "item",
                "data": i,
                "name": i["id"].upper(),
                "cost": i["cost"],
                "effect": i["effect"],
                "effect_value": i["effect_value"]
            }
            self.card_pool.append(card)

        random.shuffle(self.card_pool)
        self._refill_cards()

    def _refill_cards(self):
        """Preenche as cartas do deck atual - NÃO ADICIONA AUTOMATICAMENTE!"""
        self.cards = []
        self.card_cooldowns = {}
        self.card_x_positions = []
        self.target_x_positions = []
        self.card_y_positions = []
        self.target_y_positions = []
        self.card_rotations = []
        self.target_rotations = []
        self.card_selected_rise = []
        self.target_selected_rise = []

        # Pega as primeiras current_deck_size cartas do pool
        if self.card_pool:
            cards_to_take = min(self.current_deck_size, len(self.card_pool))
            for i in range(cards_to_take):
                card = self.card_pool[i].copy()
                if card["type"] == "pokemon":
                    card["data"]["portrait"] = self._get_portrait(card["data"]["id"])
                self.cards.append(card)
                self.card_cooldowns[i] = 0.0
                self.card_selected_rise.append(0.0)
                self.target_selected_rise.append(0.0)

        self._update_card_positions()

        for i in range(len(self.cards)):
            if i < len(self.target_x_positions):
                self.card_x_positions.append(self.target_x_positions[i])
                self.card_y_positions.append(self.target_y_positions[i])
                self.card_rotations.append(self.target_rotations[i])
            else:
                self.card_x_positions.append(0)
                self.card_y_positions.append(0)
                self.card_rotations.append(0)

    def _complete_deck_and_grow(self):
        """Completa o deck atual (todas cartas usadas), aumenta tamanho e dá recompensa"""
        self.total_decks_completed += 1
        self.current_deck_size = min(self.MAX_DECK_SIZE, self.current_deck_size + self.DECK_GROWTH_INCREMENT)
        self.cards_used_in_current_deck = 0

        if hasattr(self.game_scene, 'add_energy'):
            self.game_scene.add_energy(self.ENERGY_REWARD)

        if hasattr(self.game_scene, 'survival_ui'):
            self.game_scene.survival_ui.show_message(
                f"DECK EVOLUIU! +{self.ENERGY_REWARD} ENERGY",
                (100, 255, 100),
                duration=2.0
            )
            self.game_scene.survival_ui.show_message(
                f"AGORA COM {self.current_deck_size} CARTAS",
                (255, 200, 100),
                duration=2.0
            )

        self._refill_cards()

    def select_card(self, index: int):
        if self.selected_index == index:
            return

        if self.selected_index >= 0 and self.selected_index < len(self.target_selected_rise):
            self.target_selected_rise[self.selected_index] = 0.0

        self.selected_index = index

        if index >= 0 and index < len(self.target_selected_rise):
            self.target_selected_rise[index] = self.CARD_SELECT_RISE

    def clear_selection(self):
        if self.selected_index >= 0 and self.selected_index < len(self.target_selected_rise):
            self.target_selected_rise[self.selected_index] = 0.0
        self.selected_index = -1

    def remove_card(self, index: int):
        """Remove uma carta - NÃO adiciona nova automaticamente"""
        if index < 0 or index >= len(self.cards):
            return

        if self.selected_index == index:
            self.clear_selection()
        elif self.selected_index > index:
            self.selected_index -= 1

        # Remove a carta
        self.cards.pop(index)
        self.cards_used_in_current_deck += 1

        # Remove cooldown
        if index in self.card_cooldowns:
            del self.card_cooldowns[index]

        # Reindexa cooldowns
        new_cooldowns = {}
        for old_idx, time in self.card_cooldowns.items():
            if old_idx > index:
                new_cooldowns[old_idx - 1] = time
            else:
                new_cooldowns[old_idx] = time
        self.card_cooldowns = new_cooldowns

        # Remove posições
        if index < len(self.card_x_positions):
            self.card_x_positions.pop(index)
        if index < len(self.card_y_positions):
            self.card_y_positions.pop(index)
        if index < len(self.card_rotations):
            self.card_rotations.pop(index)
        if index < len(self.card_selected_rise):
            self.card_selected_rise.pop(index)
        if index < len(self.target_selected_rise):
            self.target_selected_rise.pop(index)

        # VERIFICA SE O DECK ACABOU
        if len(self.cards) == 0:
            self._complete_deck_and_grow()
            return

        # Atualiza posições sem adicionar nova carta
        self._update_card_positions()

        # Atualiza posições alvo
        for i in range(len(self.cards)):
            if i < len(self.target_x_positions):
                self.target_x_positions[i] = self.fan_positions[i][0]
                self.target_y_positions[i] = self.fan_positions[i][1]
                self.target_rotations[i] = self.fan_positions[i][2]

        # Smooth move para as posições atuais
        for i in range(len(self.cards)):
            if i < len(self.card_x_positions) and i < len(self.target_x_positions):
                self.card_x_positions[i] = self.target_x_positions[i]
                self.card_y_positions[i] = self.target_y_positions[i]
                self.card_rotations[i] = self.target_rotations[i]

    def recycle_deck(self):
        """Recicla o deck - substitui todas as cartas atuais por novas e RESETA o tamanho do deck"""
        if self.recycle_cooldown_remaining > 0:
            return False

        if not self.cards:
            return False

        # Devolve as cartas atuais para o pool
        for card in self.cards:
            clean_card = card.copy()
            if "portrait" in clean_card.get("data", {}):
                del clean_card["data"]["portrait"]
            self.card_pool.append(clean_card)

        # Embaralha o pool
        random.shuffle(self.card_pool)

        # ===== RESETA O TAMANHO DO DECK PARA O VALOR INICIAL =====
        self.current_deck_size = self.STARTING_CARDS
        self.cards_used_in_current_deck = 0
        self.total_decks_completed = 0

        # Limpa seleção
        self.clear_selection()

        # Recarrega as cartas com o tamanho resetado
        self._refill_cards()
        self.recycle_cooldown_remaining = self.RECYCLE_COOLDOWN

        if hasattr(self.game_scene, 'survival_ui'):
            self.game_scene.survival_ui.show_message(
                "DECK RECICLADO! AGORA COM 3 CARTAS",
                (100, 200, 255),
                duration=1.5
            )

        return True

    def _get_font(self, size, bold=False):
        key = (size, bold)
        if key not in self._font_cache:
            self._font_cache[key] = pygame.font.Font(None, size)
        return self._font_cache[key]

    def _get_portrait(self, pokemon_id: int) -> Optional[pygame.Surface]:
        if pokemon_id not in self._portrait_cache:
            portrait = self.pokedex.get_portrait(pokemon_id, "normal", False)
            if portrait:
                portrait = pygame.transform.scale(portrait, (58, 58))
            self._portrait_cache[pokemon_id] = portrait
        return self._portrait_cache[pokemon_id]

    def _get_item_sprite(self, item_id: str) -> Optional[pygame.Surface]:
        if item_id not in self._item_sprite_cache:
            sprite = self.item_catalog.get_sprite(item_id, scaled=True)
            if sprite:
                sprite = pygame.transform.scale(sprite, (58, 58))
            self._item_sprite_cache[item_id] = sprite
        return self._item_sprite_cache[item_id]

    def _get_type_color(self, type_name: str) -> tuple:
        return self.TYPE_COLORS.get(type_name.lower(), self.DEFAULT_TYPE_COLOR)

    def _calculate_fan_positions(self):
        """Calcula posições em leque estilo UNO - SEMPRE CENTRALIZADO"""
        viewport = self.game_scene.screen_manager
        viewport_width = viewport.viewport_width
        viewport_height = viewport.viewport_height

        if len(self.cards) <= 0:
            self.fan_positions = []
            return

        center_x = viewport_width // 2
        base_y = viewport_height - self.CARD_HEIGHT - 20

        if len(self.cards) == 1:
            self.fan_positions = [(center_x - self.CARD_WIDTH // 2, base_y, 0)]
            return

        self.fan_positions = []
        num_cards = len(self.cards)

        for i in range(num_cards):
            t = i / (num_cards - 1)
            angle_deg = -self.FAN_ANGLE / 2 + t * self.FAN_ANGLE
            angle_rad = math.radians(angle_deg)
            rotation = -angle_deg * 0.7

            angle_normalized = abs(angle_deg) / (self.FAN_ANGLE / 2)
            max_rise = self.CARD_HEIGHT * 0.10
            y_offset = -max_rise * (1 - angle_normalized)

            x_offset = math.tan(angle_rad) * self.FAN_RADIUS * self.CARD_SPACING_MULTIPLIER
            x = center_x + x_offset - self.CARD_WIDTH // 2
            y = base_y + y_offset

            self.fan_positions.append((x, y, rotation))

        # Ajusta para não ultrapassar as bordas
        if self.fan_positions:
            min_x = min(p[0] for p in self.fan_positions)
            max_x = max(p[0] + self.CARD_WIDTH for p in self.fan_positions)

            if min_x < 0:
                shift = -min_x + 10
                self.fan_positions = [(x + shift, y, r) for x, y, r in self.fan_positions]
            elif max_x > viewport_width:
                shift = viewport_width - max_x - 10
                self.fan_positions = [(x + shift, y, r) for x, y, r in self.fan_positions]

    def _update_card_positions(self):
        """Atualiza as posições alvo das cartas baseado no número atual de cartas"""
        self._calculate_fan_positions()

        self.target_x_positions = []
        self.target_y_positions = []
        self.target_rotations = []

        for i in range(len(self.cards)):
            if i < len(self.fan_positions):
                x, y, rot = self.fan_positions[i]
                self.target_x_positions.append(x)
                self.target_y_positions.append(y)
                self.target_rotations.append(rot)
            else:
                self.target_x_positions.append(0)
                self.target_y_positions.append(0)
                self.target_rotations.append(0)

    def update(self, dt: float):
        """Atualiza animações e cooldowns"""
        if self.recycle_cooldown_remaining > 0:
            self.recycle_cooldown_remaining -= dt
            if self.recycle_cooldown_remaining < 0:
                self.recycle_cooldown_remaining = 0

        # Animação de subida/descida da carta selecionada
        for i in range(len(self.cards)):
            if i < len(self.card_selected_rise) and i < len(self.target_selected_rise):
                diff = self.target_selected_rise[i] - self.card_selected_rise[i]
                if abs(diff) > 0.5:
                    self.card_selected_rise[i] += diff * min(1.0, dt * 12)
                else:
                    self.card_selected_rise[i] = self.target_selected_rise[i]

        # Update card cooldowns
        for idx in list(self.card_cooldowns.keys()):
            if self.card_cooldowns[idx] > 0:
                self.card_cooldowns[idx] -= dt
                if self.card_cooldowns[idx] < 0:
                    self.card_cooldowns[idx] = 0

    def get_card_positions(self) -> List[tuple]:
        """Retorna lista de (índice, x, y, card, rotação)"""
        positions = []

        for i, card in enumerate(self.cards):
            if i < len(self.card_x_positions):
                x = self.card_x_positions[i]
                y = self.card_y_positions[i]
                if i < len(self.card_selected_rise):
                    y += self.card_selected_rise[i]
                rot = self.card_rotations[i] if i < len(self.card_rotations) else 0
                positions.append((i, x, y, card, rot))

        return positions

    def get_card_at_pos(self, mouse_x: int, mouse_y: int) -> Optional[int]:
        positions = self.get_card_positions()

        if not positions:
            return -1

        click_order = self._get_fan_click_order(len(positions))

        for idx_in_order in click_order:
            for idx, x, y, card, rot in positions:
                if idx == idx_in_order and card is not None:
                    temp_rect = pygame.Rect(x, y, self.CARD_WIDTH, self.CARD_HEIGHT)
                    temp_rect.inflate_ip(8, 8)
                    if temp_rect.collidepoint(mouse_x, mouse_y):
                        return idx
        return -1

    def _get_fan_click_order(self, num_cards: int) -> List[int]:
        if num_cards <= 0:
            return []
        if num_cards == 1:
            return [0]

        order = []
        center = num_cards // 2
        order.append(center)

        left = center - 1
        right = center + 1

        while left >= 0 or right < num_cards:
            if left >= 0:
                order.append(left)
                left -= 1
            if right < num_cards:
                order.append(right)
                right += 1

        return order

    def get_recycle_button_rect(self) -> pygame.Rect:
        viewport = self.game_scene.screen_manager
        viewport_width = viewport.viewport_width
        viewport_height = viewport.viewport_height

        x = viewport_width - self.RECYCLE_BUTTON_WIDTH - 20
        y = viewport_height - self.CARD_HEIGHT - 25

        return pygame.Rect(x, y, self.RECYCLE_BUTTON_WIDTH, self.RECYCLE_BUTTON_HEIGHT)

    def handle_event(self, event) -> Optional[Dict]:
        if event.type == pygame.MOUSEMOTION:
            if hasattr(self.game_scene, 'screen_manager'):
                screen_mgr = self.game_scene.screen_manager
                mouse_x, mouse_y = event.pos
                rel_x = mouse_x - screen_mgr.viewport_x
                rel_y = mouse_y - screen_mgr.viewport_y

                if 0 <= rel_x <= screen_mgr.viewport_width and 0 <= rel_y <= screen_mgr.viewport_height:
                    self.hovered_index = self.get_card_at_pos(rel_x, rel_y)
                else:
                    self.hovered_index = -1

                btn_rect = self.get_recycle_button_rect()
                if btn_rect.collidepoint(rel_x, rel_y):
                    self.recycle_hovered = True
                else:
                    self.recycle_hovered = False
            return None

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if hasattr(self.game_scene, 'screen_manager'):
                screen_mgr = self.game_scene.screen_manager
                mouse_x, mouse_y = event.pos
                rel_x = mouse_x - screen_mgr.viewport_x
                rel_y = mouse_y - screen_mgr.viewport_y

                btn_rect = self.get_recycle_button_rect()
                if btn_rect.collidepoint(rel_x, rel_y):
                    if self.recycle_cooldown_remaining <= 0:
                        self.recycle_deck()
                    return None

                idx = self.get_card_at_pos(rel_x, rel_y)
                if idx >= 0 and idx < len(self.cards):
                    if self.card_cooldowns.get(idx, 0) <= 0:
                        card = self.cards[idx]
                        if self.game_scene.can_afford(card["cost"]):
                            self.select_card(idx)
                            if card["type"] == "pokemon":
                                return {
                                    "action": "card_selected",
                                    "index": idx,
                                    "card_type": "pokemon",
                                    "pokemon_data": card["data"]
                                }
                            else:
                                return {
                                    "action": "card_selected",
                                    "index": idx,
                                    "card_type": "item",
                                    "item_data": card["data"]
                                }
            return None

        return None

    def render(self, screen):
        screen_mgr = self.game_scene.screen_manager
        viewport_x = screen_mgr.viewport_x
        viewport_y = screen_mgr.viewport_y

        # Renderiza botão de recycle
        self._render_recycle_button(screen, viewport_x, viewport_y)

        positions = self.get_card_positions()

        if not positions:
            return

        selected_position = None
        normal_positions = []

        for idx, x, y, card, rot in positions:
            if idx == self.selected_index:
                selected_position = (idx, x, y, card, rot)
            else:
                normal_positions.append((idx, x, y, card, rot))

        normal_positions.sort(key=lambda p: p[0])

        for idx, x, y, card, rot in normal_positions:
            self._render_card(screen, idx, x + viewport_x, y + viewport_y, card, rot)

        if selected_position:
            idx, x, y, card, rot = selected_position
            self._render_card(screen, idx, x + viewport_x, y + viewport_y, card, rot)

    def _render_recycle_button(self, screen, viewport_x, viewport_y):
        btn_rect = self.get_recycle_button_rect()
        btn_rect.x += viewport_x
        btn_rect.y += viewport_y

        is_ready = self.recycle_cooldown_remaining <= 0

        if is_ready:
            if self.recycle_hovered:
                color = (100, 170, 220)
                border_color = (150, 200, 255)
            else:
                color = self.COLORS['recycle']
                border_color = (100, 150, 200)
        else:
            color = self.COLORS['recycle_disabled']
            border_color = (60, 60, 80)

        pygame.draw.rect(screen, color, btn_rect, border_radius=8)
        pygame.draw.rect(screen, border_color, btn_rect, 2, border_radius=8)

        font = self._get_font(12, bold=True)
        if not is_ready:
            text = f"{self.recycle_cooldown_remaining:.0f}s"
        else:
            text = "RECICLAR"

        text_surf = font.render(text, True, (255, 255, 255) if is_ready else (180, 180, 200))
        text_x = btn_rect.centerx - text_surf.get_width() // 2
        text_y = btn_rect.centery - text_surf.get_height() // 2
        screen.blit(text_surf, (text_x, text_y))

    def _render_card(self, screen, idx: int, x: int, y: int, card: Dict, rotation: float = 0):
        is_selected = (idx == self.selected_index)
        is_hovered = (idx == self.hovered_index)
        is_on_cooldown = self.card_cooldowns.get(idx, 0) > 0
        cooldown_percent = self.card_cooldowns.get(idx, 0) / 3.0 if is_on_cooldown else 0
        can_afford = self.game_scene.can_afford(card["cost"])
        energy_insufficient = not can_afford

        if card["type"] == "item":
            if energy_insufficient:
                card_color = (60, 35, 35)
            elif is_selected:
                card_color = (50, 70, 100)
            elif is_hovered:
                card_color = (45, 65, 90)
            else:
                card_color = self.COLORS['item_bg']
        else:
            if energy_insufficient:
                card_color = (60, 35, 35)
            elif is_selected:
                card_color = (40, 50, 80)
            elif is_hovered:
                card_color = (35, 42, 65)
            else:
                card_color = self.COLORS['bg_dark']

        card_surface = pygame.Surface((self.CARD_WIDTH, self.CARD_HEIGHT), pygame.SRCALPHA)

        shadow_surf = pygame.Surface((self.CARD_WIDTH, self.CARD_HEIGHT), pygame.SRCALPHA)
        shadow_surf.fill((0, 0, 0, 80))
        card_surface.blit(shadow_surf, (4, 4))

        card_rect = pygame.Rect(0, 0, self.CARD_WIDTH, self.CARD_HEIGHT)
        pygame.draw.rect(card_surface, card_color, card_rect, border_radius=10)

        if card["type"] == "item":
            border_color = self.COLORS['item_border'] if not energy_insufficient else self.COLORS['energy_insufficient']
            pygame.draw.rect(card_surface, border_color, card_rect, 3, border_radius=10)
        else:
            if not energy_insufficient:
                type_color = self._get_type_color(card["type_name"])
                pygame.draw.rect(card_surface, type_color, card_rect, 3, border_radius=10)
            else:
                pygame.draw.rect(card_surface, self.COLORS['energy_insufficient'], card_rect, 3, border_radius=10)
                energy_overlay = pygame.Surface((self.CARD_WIDTH, self.CARD_HEIGHT), pygame.SRCALPHA)
                energy_overlay.fill((180, 50, 50, 100))
                card_surface.blit(energy_overlay, (0, 0))

        if card["type"] == "pokemon":
            portrait = card["data"].get("portrait")
            if portrait:
                portrait_x = (self.CARD_WIDTH - 58) // 2
                portrait_y = 8
                card_surface.blit(portrait, (portrait_x, portrait_y))
        else:
            item_sprite = self._get_item_sprite(card["data"]["id"])
            if item_sprite:
                sprite_x = (self.CARD_WIDTH - 58) // 2
                sprite_y = 8
                card_surface.blit(item_sprite, (sprite_x, sprite_y))

        name_font = self._get_font(13, bold=True)
        name = card["name"]
        if len(name) > 10:
            name = name[:9] + "."
        name_surf = name_font.render(name, True, self.COLORS['text'])
        name_x = (self.CARD_WIDTH - name_surf.get_width()) // 2
        name_y = self.CARD_HEIGHT - 50
        card_surface.blit(name_surf, (name_x, name_y))

        type_font = self._get_font(10, bold=True)
        if card["type"] == "pokemon":
            type_name = card["type_name"].upper()
            if len(type_name) > 5:
                type_name = type_name[:4]
            type_bg_rect = pygame.Rect(5, self.CARD_HEIGHT - 24, 38, 16)
            pygame.draw.rect(card_surface, self._get_type_color(card["type_name"]), type_bg_rect, border_radius=4)
            type_surf = type_font.render(type_name, True, (255, 255, 255))
            card_surface.blit(type_surf, (7, self.CARD_HEIGHT - 23))
        else:
            effect_text = card["effect"].upper()[:4] if card["effect"] else "ITEM"
            effect_bg_rect = pygame.Rect(5, self.CARD_HEIGHT - 24, 38, 16)
            pygame.draw.rect(card_surface, (100, 150, 200), effect_bg_rect, border_radius=4)
            effect_surf = type_font.render(effect_text, True, (255, 255, 255))
            card_surface.blit(effect_surf, (7, self.CARD_HEIGHT - 23))

        if card["type"] == "pokemon":
            level_font = self._get_font(14, bold=True)
            level_text = f"Lv {card['level']}"
            level_surf = level_font.render(level_text, True, self.COLORS['level'])
            level_bg = pygame.Surface((level_surf.get_width() + 6, level_surf.get_height() + 2), pygame.SRCALPHA)
            level_bg.fill((0, 0, 0, 150))
            level_x = self.CARD_WIDTH - level_surf.get_width() - 8
            level_y = self.CARD_HEIGHT - 24
            card_surface.blit(level_bg, (level_x - 3, level_y - 1))
            card_surface.blit(level_surf, (level_x, level_y))

        cost_font = self._get_font(14, bold=True)
        cost_text = str(card['cost'])
        if energy_insufficient:
            cost_circle_color = self.COLORS['energy_insufficient']
            cost_text_color = (255, 200, 200)
        else:
            cost_circle_color = self.COLORS['cost']
            cost_text_color = (40, 30, 0)
        pygame.draw.circle(card_surface, cost_circle_color, (20, 20), 14)
        cost_surf = cost_font.render(cost_text, True, cost_text_color)
        card_surface.blit(cost_surf, (20 - cost_surf.get_width() // 2, 15))

        if is_on_cooldown:
            overlay = pygame.Surface((self.CARD_WIDTH, self.CARD_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 180))
            card_surface.blit(overlay, (0, 0))
            bar_height = 6
            bar_width = int(self.CARD_WIDTH * (1 - cooldown_percent))
            bar_rect = pygame.Rect(0, self.CARD_HEIGHT - bar_height, bar_width, bar_height)
            pygame.draw.rect(card_surface, self.COLORS['cooldown'], bar_rect)
            time_font = self._get_font(12, bold=True)
            time_text = f"{self.card_cooldowns[idx]:.0f}s"
            time_surf = time_font.render(time_text, True, self.COLORS['text'])
            time_x = (self.CARD_WIDTH - time_surf.get_width()) // 2
            time_y = (self.CARD_HEIGHT - time_surf.get_height()) // 2
            card_surface.blit(time_surf, (time_x, time_y))

        if energy_insufficient and not is_on_cooldown:
            warn_font = self._get_font(9, bold=True)
            warn_text = warn_font.render("ENERGIA", True, (255, 180, 180))
            warn_x = (self.CARD_WIDTH - warn_text.get_width()) // 2
            warn_y = self.CARD_HEIGHT - 38
            card_surface.blit(warn_text, (warn_x, warn_y))

        if is_selected:
            glow = pygame.Surface((self.CARD_WIDTH, self.CARD_HEIGHT), pygame.SRCALPHA)
            pulse = abs(math.sin(self.game_scene.survival_ui.wave_pulse)) * 0.3 + 0.4
            glow.fill((255, 215, 0, int(80 * pulse)))
            card_surface.blit(glow, (0, 0))
            pygame.draw.rect(card_surface, (255, 215, 0), card_rect, 4, border_radius=10)
        elif is_hovered and not energy_insufficient:
            glow = pygame.Surface((self.CARD_WIDTH, self.CARD_HEIGHT), pygame.SRCALPHA)
            glow.fill((100, 150, 220, 40))
            card_surface.blit(glow, (0, 0))

        final_rotation = 0 if is_selected else rotation

        if final_rotation != 0:
            rotated_surface = pygame.transform.rotate(card_surface, final_rotation)
            new_rect = rotated_surface.get_rect(center=(x + self.CARD_WIDTH // 2, y + self.CARD_HEIGHT // 2))
            screen.blit(rotated_surface, new_rect)
        else:
            screen.blit(card_surface, (x, y))