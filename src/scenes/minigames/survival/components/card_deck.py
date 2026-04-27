# src/scenes/minigames/survival/components/card_deck.py

"""
Sistema de deck estilo UNO
- Cartas em leque com rotação correta (pontas para fora)
- Texto acompanha rotação da carta
- Carta selecionada sobe bem mais alto e fica reta
- Botão de recycle com cooldown de 15 segundos
"""

import pygame
import random
import math
from typing import List, Dict, Any, Optional
from collections import deque
from src.data.pokedex import Pokedex


class CardDeck:
    """Gerencia o deck de cartas estilo UNO"""

    CARD_WIDTH = 110
    CARD_HEIGHT = 150

    # Configurações do leque (fan)
    FAN_ANGLE = 35  # Ângulo total do leque em graus
    FAN_RADIUS = 270  # Raio do círculo imaginário
    CARD_SPACING_MULTIPLIER = 1 # Aumenta o espaçamento entre cartas

    # Configurações do deck progressivo
    STARTING_CARDS = 3
    DECK_GROWTH_INCREMENT = 1
    ENERGY_REWARD = 30

    # Configurações do recycle
    RECYCLE_COOLDOWN = 15.0
    RECYCLE_BUTTON_WIDTH = 80
    RECYCLE_BUTTON_HEIGHT = 40

    # Configurações da esteira
    CARD_ENTRY_DURATION = 0.5
    SLIDE_DURATION = 0.2
    CARD_SELECT_RISE = -55  # Quanto a carta selecionada sobe (bem mais alto)

    def __init__(self, game_scene):
        self.game_scene = game_scene
        self.pokedex = Pokedex()

        # Cartas na esteira
        self.cards: List[Dict] = []
        self.pending_cards: deque = deque()
        self.card_cooldowns: Dict[int, float] = {}

        # Progressão do deck
        self.current_deck_size = self.STARTING_CARDS
        self.cards_used_in_current_deck = 0
        self.total_decks_completed = 0

        # Estado do recycle
        self.recycle_cooldown_remaining = 0.0
        self.recycle_hovered = False

        # ===== SISTEMA DE ANIMAÇÃO =====
        self.card_x_positions: List[float] = []
        self.target_x_positions: List[float] = []
        self.card_y_positions: List[float] = []
        self.target_y_positions: List[float] = []
        self.card_rotations: List[float] = []
        self.target_rotations: List[float] = []
        self.card_selected_rise: List[float] = []
        self.target_selected_rise: List[float] = []

        self.is_sliding = False
        self.slide_progress = 0.0
        self.entering_card = None

        # Seleção
        self.selected_index = -1
        self.hovered_index = -1

        # Cache
        self._font_cache = {}
        self._portrait_cache = {}

        # Posições do leque
        self.fan_positions: List[tuple] = []  # (x, y, angle)

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

        self._init_card_pool()

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

    def _get_type_color(self, type_name: str) -> tuple:
        return self.TYPE_COLORS.get(type_name.lower(), self.DEFAULT_TYPE_COLOR)

    def _calculate_fan_positions(self):
        """
        Calcula posições em leque estilo UNO.
        Pontas inclinadas para FORA (carta esquerda gira anti-horário, direita gira horário)
        Arco suave: centro sobe levemente (efeito "colina" em vez de "vale")
        """
        viewport = self.game_scene.screen_manager
        viewport_width = viewport.viewport_width
        viewport_height = viewport.viewport_height

        if self.current_deck_size <= 0:
            return

        # Ponto central do leque (base das cartas)
        center_x = viewport_width // 2
        base_y = viewport_height - self.CARD_HEIGHT - 20

        if self.current_deck_size == 1:
            self.fan_positions = [(center_x - self.CARD_WIDTH // 2, base_y, 0)]
            return

        self.fan_positions = []

        # Calcula posições (da esquerda para a direita)
        for i in range(self.current_deck_size):
            # Progressão linear do ângulo: da esquerda (negativo) para direita (positivo)
            t = i / (self.current_deck_size - 1)  # 0 = esquerda, 1 = direita
            # Ângulo: negativo na esquerda, positivo na direita
            angle_deg = -self.FAN_ANGLE / 2 + t * self.FAN_ANGLE
            angle_rad = math.radians(angle_deg)

            # Rotação: pontas viradas para FORA
            # Esquerda: rotação positiva (anti-horário = ponta para cima-esquerda)
            # Direita: rotação negativa (horário = ponta para cima-direita)
            # Centro: rotação zero
            rotation = -angle_deg * 0.7

            # ===== ARCO SUAVE: centro sobe, pontas descem =====
            # Usa função cosseno para criar arco suave: centro = máximo, pontas = mínimo
            # angle_deg vai de -15 a +15 (assumindo FAN_ANGLE=30)
            # cos(0°) = 1 (centro), cos(15°) ≈ 0.96 (pontas)
            # Quanto maior o ângulo, menor o y_offset
            angle_normalized = abs(angle_deg) / (self.FAN_ANGLE / 2)  # 0 no centro, 1 nas pontas
            # Centro sobe 10% da altura da carta (15px), pontas ficam na base
            max_rise = self.CARD_HEIGHT * 0.10  # 10% da altura da carta = ~15px
            y_offset = -max_rise * (1 - angle_normalized)  # Negativo = sobe, centro = -15, pontas = 0

            # Posição X: afastamento do centro conforme ângulo
            x_offset = math.tan(angle_rad) * self.FAN_RADIUS * self.CARD_SPACING_MULTIPLIER

            x = center_x + x_offset - self.CARD_WIDTH // 2
            y = base_y + y_offset  # Centro sobe, pontas na base

            self.fan_positions.append((x, y, rotation))

        # Ajusta para não ultrapassar as bordas
        min_x = min(p[0] for p in self.fan_positions)
        max_x = max(p[0] + self.CARD_WIDTH for p in self.fan_positions)

        if min_x < 0:
            shift = -min_x + 10
            self.fan_positions = [(x + shift, y, r) for x, y, r in self.fan_positions]
        elif max_x > viewport_width:
            shift = viewport_width - max_x - 10
            self.fan_positions = [(x + shift, y, r) for x, y, r in self.fan_positions]

    def _update_card_positions(self):
        """Atualiza as posições alvo das cartas baseado no tamanho atual do deck"""
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

    def _init_card_pool(self):
        """Inicializa o pool de cartas"""
        self.card_pool = [
            {"id": 1, "name": "Bulbasaur", "cost": 50, "level": 5, "type": "grass"},
            {"id": 4, "name": "Charmander", "cost": 50, "level": 5, "type": "fire"},
            {"id": 7, "name": "Squirtle", "cost": 50, "level": 5, "type": "water"},
            {"id": 25, "name": "Pikachu", "cost": 60, "level": 5, "type": "electric"},
            {"id": 16, "name": "Pidgey", "cost": 40, "level": 5, "type": "normal"},
            {"id": 19, "name": "Rattata", "cost": 30, "level": 5, "type": "normal"},
            {"id": 21, "name": "Spearow", "cost": 40, "level": 5, "type": "normal"},
            {"id": 29, "name": "Nidoran F", "cost": 45, "level": 5, "type": "poison"},
            {"id": 32, "name": "Nidoran M", "cost": 45, "level": 5, "type": "poison"},
            {"id": 41, "name": "Zubat", "cost": 35, "level": 5, "type": "poison"},
            {"id": 43, "name": "Oddish", "cost": 45, "level": 5, "type": "grass"},
            {"id": 46, "name": "Paras", "cost": 45, "level": 5, "type": "bug"},
            {"id": 48, "name": "Venonat", "cost": 45, "level": 5, "type": "bug"},
            {"id": 50, "name": "Diglett", "cost": 40, "level": 5, "type": "ground"},
            {"id": 52, "name": "Meowth", "cost": 40, "level": 5, "type": "normal"},
            {"id": 54, "name": "Psyduck", "cost": 50, "level": 5, "type": "water"},
            {"id": 56, "name": "Mankey", "cost": 45, "level": 5, "type": "fighting"},
            {"id": 58, "name": "Growlithe", "cost": 55, "level": 5, "type": "fire"},
            {"id": 60, "name": "Poliwag", "cost": 45, "level": 5, "type": "water"},
            {"id": 63, "name": "Abra", "cost": 60, "level": 5, "type": "psychic"},
            {"id": 66, "name": "Machop", "cost": 50, "level": 5, "type": "fighting"},
            {"id": 69, "name": "Bellsprout", "cost": 45, "level": 5, "type": "grass"},
            {"id": 72, "name": "Tentacool", "cost": 45, "level": 5, "type": "water"},
            {"id": 74, "name": "Geodude", "cost": 45, "level": 5, "type": "rock"},
        ]

        random.shuffle(self.card_pool)
        self.pending_cards = deque(self.card_pool.copy())
        self._refill_cards()

    def _refill_cards(self):
        """Preenche as cartas do deck atual"""
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

        cards_to_add = min(self.current_deck_size, len(self.pending_cards))
        if cards_to_add < self.current_deck_size:
            self.pending_cards = deque(self.card_pool.copy())
            random.shuffle(self.pending_cards)
            cards_to_add = min(self.current_deck_size, len(self.pending_cards))

        for i in range(cards_to_add):
            if self.pending_cards:
                card = self.pending_cards.popleft()
                card["portrait"] = self._get_portrait(card["id"])
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
        """Completa o deck atual, aumenta o tamanho e dá recompensa"""
        self.total_decks_completed += 1
        self.current_deck_size += self.DECK_GROWTH_INCREMENT
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
        """Seleciona uma carta - ela sobe bem alto e fica reta"""
        if self.selected_index == index:
            return

        # Anima a carta anterior descendo
        if self.selected_index >= 0 and self.selected_index < len(self.target_selected_rise):
            self.target_selected_rise[self.selected_index] = 0.0

        self.selected_index = index

        # Carta selecionada sobe bem alto e fica reta
        if index >= 0 and index < len(self.target_selected_rise):
            self.target_selected_rise[index] = self.CARD_SELECT_RISE

    def clear_selection(self):
        """Limpa a seleção atual"""
        if self.selected_index >= 0 and self.selected_index < len(self.target_selected_rise):
            self.target_selected_rise[self.selected_index] = 0.0
        self.selected_index = -1

    def remove_card(self, index: int):
        """Remove uma carta e inicia animação"""
        if index < 0 or index >= len(self.cards):
            return

        # Limpa seleção se a carta removida era a selecionada
        if self.selected_index == index:
            self.clear_selection()
        elif self.selected_index > index:
            self.selected_index -= 1

        # Guarda posições antigas
        old_targets_x = self.target_x_positions.copy()
        old_targets_y = self.target_y_positions.copy()
        old_targets_rot = self.target_rotations.copy()
        old_targets_rise = self.target_selected_rise.copy()

        # Remove a carta
        self.cards.pop(index)
        self.cards_used_in_current_deck += 1

        if index in self.card_cooldowns:
            del self.card_cooldowns[index]

        new_cooldowns = {}
        for old_idx, time in self.card_cooldowns.items():
            if old_idx > index:
                new_cooldowns[old_idx - 1] = time
            else:
                new_cooldowns[old_idx] = time
        self.card_cooldowns = new_cooldowns

        # Verifica se o deck acabou
        if len(self.cards) == 0:
            self._complete_deck_and_grow()
            return

        # Atualiza posições alvo
        self._update_card_positions()

        # Recalcula posições atuais
        new_card_x = []
        new_card_y = []
        new_card_rot = []
        new_card_rise = []

        for i in range(len(self.cards)):
            old_idx = i if i < index else i + 1
            if old_idx < len(old_targets_x):
                new_card_x.append(old_targets_x[old_idx])
                new_card_y.append(old_targets_y[old_idx])
                new_card_rot.append(old_targets_rot[old_idx])
                new_card_rise.append(old_targets_rise[old_idx] if old_idx < len(old_targets_rise) else 0)
            else:
                new_card_x.append(self.target_x_positions[i] if i < len(self.target_x_positions) else 0)
                new_card_y.append(self.target_y_positions[i] if i < len(self.target_y_positions) else 0)
                new_card_rot.append(self.target_rotations[i] if i < len(self.target_rotations) else 0)
                new_card_rise.append(0)

        self.card_x_positions = new_card_x
        self.card_y_positions = new_card_y
        self.card_rotations = new_card_rot
        self.card_selected_rise = new_card_rise
        self.target_selected_rise = [0] * len(self.cards)

        # Inicia animação
        self.is_sliding = True
        self.slide_progress = 0.0
        self._add_new_card_from_right()

    def _add_new_card_from_right(self):
        """Prepara uma nova carta para entrar pela DIREITA"""
        if len(self.pending_cards) == 0:
            self.pending_cards = deque(self.card_pool.copy())
            random.shuffle(self.pending_cards)

        if self.pending_cards and len(self.cards) < self.current_deck_size:
            card = self.pending_cards.popleft()
            card["portrait"] = self._get_portrait(card["id"])

            final_index = len(self.cards)
            if final_index < self.current_deck_size:
                self._update_card_positions()

                if final_index < len(self.target_x_positions):
                    target_x = self.target_x_positions[final_index]
                    target_y = self.target_y_positions[final_index]
                    target_rot = self.target_rotations[final_index]
                else:
                    target_x = 0
                    target_y = 0
                    target_rot = 0

                start_x = self.game_scene.screen_manager.viewport_width + 50

                self.entering_card = {
                    "card": card,
                    "progress": 0.0,
                    "current_x": start_x,
                    "start_x": start_x,
                    "target_x": target_x,
                    "target_y": target_y,
                    "target_rot": target_rot,
                    "current_y": 0,
                    "current_rot": 0
                }

    def recycle_deck(self):
        """Recicla o deck - substitui todas as cartas atuais por novas"""
        if self.recycle_cooldown_remaining > 0:
            return False

        if not self.cards:
            return False

        for card in self.cards:
            clean_card = {k: v for k, v in card.items() if k != 'portrait'}
            self.pending_cards.append(clean_card)

        temp_list = list(self.pending_cards)
        random.shuffle(temp_list)
        self.pending_cards = deque(temp_list)

        self.clear_selection()
        self._refill_cards()
        self.recycle_cooldown_remaining = self.RECYCLE_COOLDOWN

        if hasattr(self.game_scene, 'survival_ui'):
            self.game_scene.survival_ui.show_message(
                "DECK RECICLADO!",
                (100, 200, 255),
                duration=1.5
            )

        return True

    def update(self, dt: float):
        """Atualiza animações e cooldowns"""
        # Update recycle cooldown
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

        # Animação de deslizamento
        if self.is_sliding:
            self.slide_progress += dt / self.SLIDE_DURATION

            if self.slide_progress >= 1.0:
                self.is_sliding = False
                self.card_x_positions = self.target_x_positions.copy()
                self.card_y_positions = self.target_y_positions.copy()
                self.card_rotations = self.target_rotations.copy()
            else:
                ease = 1 - (1 - self.slide_progress) ** 3
                for i in range(len(self.cards)):
                    if i < len(self.card_x_positions) and i < len(self.target_x_positions):
                        self.card_x_positions[i] = self.card_x_positions[i] + (
                                    self.target_x_positions[i] - self.card_x_positions[i]) * ease
                    if i < len(self.card_y_positions) and i < len(self.target_y_positions):
                        self.card_y_positions[i] = self.card_y_positions[i] + (
                                    self.target_y_positions[i] - self.card_y_positions[i]) * ease
                    if i < len(self.card_rotations) and i < len(self.target_rotations):
                        self.card_rotations[i] = self.card_rotations[i] + (
                                    self.target_rotations[i] - self.card_rotations[i]) * ease

        # Animação de entrada
        if self.entering_card:
            self.entering_card["progress"] += dt / self.CARD_ENTRY_DURATION

            if self.entering_card["progress"] >= 1.0:
                card = self.entering_card["card"]
                self.cards.append(card)
                self.card_cooldowns[len(self.cards) - 1] = 0.0
                self.card_selected_rise.append(0.0)
                self.target_selected_rise.append(0.0)

                self._update_card_positions()
                self.target_x_positions = [self.target_x_positions[i] if i < len(self.target_x_positions) else 0 for i
                                           in range(len(self.cards))]
                self.target_y_positions = [self.target_y_positions[i] if i < len(self.target_y_positions) else 0 for i
                                           in range(len(self.cards))]
                self.target_rotations = [self.target_rotations[i] if i < len(self.target_rotations) else 0 for i in
                                         range(len(self.cards))]
                self.card_x_positions = self.target_x_positions.copy()
                self.card_y_positions = self.target_y_positions.copy()
                self.card_rotations = self.target_rotations.copy()

                self.entering_card = None
            else:
                ease = 1 - (1 - self.entering_card["progress"]) ** 3
                start_x = self.entering_card["start_x"]
                end_x = self.entering_card["target_x"]
                self.entering_card["current_x"] = start_x + (end_x - start_x) * ease
                self.entering_card["current_y"] = self.entering_card["target_y"] * ease
                self.entering_card["current_rot"] = self.entering_card["target_rot"] * ease

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

        # Carta entrante
        if self.entering_card and self.entering_card["progress"] < 0.95:
            x = self.entering_card["current_x"]
            y = self.entering_card["current_y"]
            rot = self.entering_card["current_rot"]
            positions.append((len(self.cards), x, y, self.entering_card["card"], rot))

        return positions

    def get_card_at_pos(self, mouse_x: int, mouse_y: int) -> Optional[int]:
        """
        Retorna o índice da carta na posição do mouse.
        Prioridade: centro primeiro (está na frente), depois as laterais.
        """
        positions = self.get_card_positions()

        if not positions:
            return -1

        # Ordem de clique: do centro para as pontas (inverso da renderização)
        click_order = self._get_fan_click_order(len(positions))

        # Verifica na ordem de prioridade (centro primeiro)
        for idx_in_order in click_order:
            for idx, x, y, card, rot in positions:
                if idx == idx_in_order and card is not None:
                    temp_rect = pygame.Rect(x, y, self.CARD_WIDTH, self.CARD_HEIGHT)
                    temp_rect.inflate_ip(8, 8)
                    if temp_rect.collidepoint(mouse_x, mouse_y):
                        return idx
        return -1

    def _get_fan_click_order(self, num_cards: int) -> List[int]:
        """
        Retorna a ordem de clique para um leque de cartas.
        Prioridade: centro primeiro (está na frente), depois alterna para as pontas.
        Exemplo com 5 cartas: [2, 1, 3, 0, 4]
        Exemplo com 4 cartas: [1, 2, 0, 3]
        Exemplo com 3 cartas: [1, 0, 2]
        """
        if num_cards <= 0:
            return []
        if num_cards == 1:
            return [0]

        order = []
        center = num_cards // 2
        order.append(center)

        left = center - 1
        right = center + 1

        # Alterna para esquerda e direita
        while left >= 0 or right < num_cards:
            if left >= 0:
                order.append(left)
                left -= 1
            if right < num_cards:
                order.append(right)
                right += 1

        return order

    def get_recycle_button_rect(self) -> pygame.Rect:
        """Retorna o retângulo do botão de recycle"""
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

                # Recycle button
                btn_rect = self.get_recycle_button_rect()
                if btn_rect.collidepoint(rel_x, rel_y):
                    if self.recycle_cooldown_remaining <= 0:
                        self.recycle_deck()
                    return None

                # Card click
                idx = self.get_card_at_pos(rel_x, rel_y)
                if idx >= 0 and idx < len(self.cards):
                    if self.card_cooldowns.get(idx, 0) <= 0:
                        card = self.cards[idx]
                        if self.game_scene.can_afford(card["cost"]):
                            self.select_card(idx)
                            return {
                                "action": "card_selected",
                                "index": idx,
                                "pokemon_data": card
                            }
            return None

        return None

    def render(self, screen):
        screen_mgr = self.game_scene.screen_manager
        viewport_x = screen_mgr.viewport_x
        viewport_y = screen_mgr.viewport_y

        # Fundo da área do deck
        deck_height = self.CARD_HEIGHT + 90
        deck_rect = pygame.Rect(
            viewport_x,
            viewport_y + screen_mgr.viewport_height - deck_height,
            screen_mgr.viewport_width,
            deck_height
        )

        for i in range(deck_height):
            alpha = 80 + int(80 * (1 - i / deck_height))
            color = (15, 20, 35, min(180, alpha))
            pygame.draw.line(screen, color[:3],
                             (deck_rect.x, deck_rect.y + i),
                             (deck_rect.x + deck_rect.width, deck_rect.y + i))

        # Renderiza botão de recycle
        self._render_recycle_button(screen, viewport_x, viewport_y)

        # ===== ORDEM DE RENDERIZAÇÃO CORRETA =====
        # 1. Cartas do leque (da esquerda para direita - esquerda atrás, direita na frente)
        # 2. Carta selecionada por ÚLTIMO (acima de todas)

        positions = self.get_card_positions()

        if not positions:
            return

        # Separa a carta selecionada das demais
        selected_position = None
        normal_positions = []

        for idx, x, y, card, rot in positions:
            if idx == self.selected_index:
                selected_position = (idx, x, y, card, rot)
            else:
                normal_positions.append((idx, x, y, card, rot))

        # Ordem de renderização: da esquerda para a direita (índice crescente)
        # Carta com índice menor fica ATRÁS, índice maior fica na FRENTE
        normal_positions.sort(key=lambda p: p[0])  # Ordena por índice crescente

        # Renderiza todas as cartas normais
        for idx, x, y, card, rot in normal_positions:
            self._render_card(screen, idx, x + viewport_x, y + viewport_y, card, rot)

        # Renderiza a carta selecionada por ÚLTIMO (acima de todas)
        if selected_position:
            idx, x, y, card, rot = selected_position
            self._render_card(screen, idx, x + viewport_x, y + viewport_y, card, rot)

    def _get_fan_render_order(self, num_cards: int) -> List[int]:
        """
        Retorna a ordem de renderização para um leque de cartas.
        ESTILO BARALHO REAL: da esquerda para a direita (esquerda por baixo, direita por cima)
        Exemplo com 5 cartas: [0, 1, 2, 3, 4] (4 é a última, fica por cima)
        Exemplo com 4 cartas: [0, 1, 2, 3]
        """
        if num_cards <= 0:
            return []

        # Simples: da esquerda para a direita (índice 0 primeiro = atrás, último = na frente)
        return list(range(num_cards))

    def _render_recycle_button(self, screen, viewport_x, viewport_y):
        """Renderiza o botão de recycle simplificado"""
        btn_rect = self.get_recycle_button_rect()
        btn_rect.x += viewport_x
        btn_rect.y += viewport_y

        is_ready = self.recycle_cooldown_remaining <= 0

        # Cores
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

        # Fundo
        pygame.draw.rect(screen, color, btn_rect, border_radius=8)
        pygame.draw.rect(screen, border_color, btn_rect, 2, border_radius=8)

        # Texto
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
        """Renderiza uma carta individual com rotação estilo UNO"""
        is_selected = (idx == self.selected_index)
        is_hovered = (idx == self.hovered_index)
        is_on_cooldown = self.card_cooldowns.get(idx, 0) > 0
        cooldown_percent = self.card_cooldowns.get(idx, 0) / 3.0 if is_on_cooldown else 0
        can_afford = self.game_scene.can_afford(card["cost"])
        energy_insufficient = not can_afford

        # Cor base
        if energy_insufficient:
            card_color = (60, 35, 35)
        elif is_selected:
            card_color = (40, 50, 80)
        elif is_hovered:
            card_color = (35, 42, 65)
        else:
            card_color = self.COLORS['bg_dark']

        # Cria superfície
        card_surface = pygame.Surface((self.CARD_WIDTH, self.CARD_HEIGHT), pygame.SRCALPHA)

        # Sombra
        shadow_surf = pygame.Surface((self.CARD_WIDTH, self.CARD_HEIGHT), pygame.SRCALPHA)
        shadow_surf.fill((0, 0, 0, 80))
        card_surface.blit(shadow_surf, (4, 4))

        # Fundo
        card_rect = pygame.Rect(0, 0, self.CARD_WIDTH, self.CARD_HEIGHT)
        pygame.draw.rect(card_surface, card_color, card_rect, border_radius=10)

        # Borda
        if not energy_insufficient:
            type_color = self._get_type_color(card["type"])
            pygame.draw.rect(card_surface, type_color, card_rect, 3, border_radius=10)
        else:
            pygame.draw.rect(card_surface, self.COLORS['energy_insufficient'], card_rect, 3, border_radius=10)
            energy_overlay = pygame.Surface((self.CARD_WIDTH, self.CARD_HEIGHT), pygame.SRCALPHA)
            energy_overlay.fill((180, 50, 50, 100))
            card_surface.blit(energy_overlay, (0, 0))

        # Portrait
        portrait = card.get("portrait")
        if portrait:
            portrait_x = (self.CARD_WIDTH - 58) // 2
            portrait_y = 8
            card_surface.blit(portrait, (portrait_x, portrait_y))

        # Nome
        name_font = self._get_font(13, bold=True)
        name = card["name"]
        if len(name) > 10:
            name = name[:9] + "."
        name_surf = name_font.render(name, True, self.COLORS['text'])
        name_x = (self.CARD_WIDTH - name_surf.get_width()) // 2
        name_y = self.CARD_HEIGHT - 50
        card_surface.blit(name_surf, (name_x, name_y))

        # Tipo
        type_font = self._get_font(10, bold=True)
        type_name = card["type"].upper()
        if len(type_name) > 5:
            type_name = type_name[:4]
        type_bg_rect = pygame.Rect(5, self.CARD_HEIGHT - 24, 38, 16)
        pygame.draw.rect(card_surface, self._get_type_color(card["type"]), type_bg_rect, border_radius=4)
        type_surf = type_font.render(type_name, True, (255, 255, 255))
        card_surface.blit(type_surf, (7, self.CARD_HEIGHT - 23))

        # Nível
        level_font = self._get_font(14, bold=True)
        level_text = f"Lv {card['level']}"
        level_surf = level_font.render(level_text, True, self.COLORS['level'])
        level_bg = pygame.Surface((level_surf.get_width() + 6, level_surf.get_height() + 2), pygame.SRCALPHA)
        level_bg.fill((0, 0, 0, 150))
        level_x = self.CARD_WIDTH - level_surf.get_width() - 8
        level_y = self.CARD_HEIGHT - 24
        card_surface.blit(level_bg, (level_x - 3, level_y - 1))
        card_surface.blit(level_surf, (level_x, level_y))

        # Custo
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

        # Cooldown
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

        # Aviso energia
        if energy_insufficient and not is_on_cooldown:
            warn_font = self._get_font(9, bold=True)
            warn_text = warn_font.render("ENERGIA", True, (255, 180, 180))
            warn_x = (self.CARD_WIDTH - warn_text.get_width()) // 2
            warn_y = self.CARD_HEIGHT - 38
            card_surface.blit(warn_text, (warn_x, warn_y))

        # Efeitos visuais
        if is_selected:
            # Glow dourado
            glow = pygame.Surface((self.CARD_WIDTH, self.CARD_HEIGHT), pygame.SRCALPHA)
            pulse = abs(math.sin(self.game_scene.survival_ui.wave_pulse)) * 0.3 + 0.4
            glow.fill((255, 215, 0, int(80 * pulse)))
            card_surface.blit(glow, (0, 0))
            # Borda dourada grossa
            pygame.draw.rect(card_surface, (255, 215, 0), card_rect, 4, border_radius=10)
        elif is_hovered and not energy_insufficient:
            glow = pygame.Surface((self.CARD_WIDTH, self.CARD_HEIGHT), pygame.SRCALPHA)
            glow.fill((100, 150, 220, 40))
            card_surface.blit(glow, (0, 0))

        # Aplica rotação (carta selecionada fica reta)
        final_rotation = 0 if is_selected else rotation

        if final_rotation != 0:
            rotated_surface = pygame.transform.rotate(card_surface, final_rotation)
            new_rect = rotated_surface.get_rect(center=(x + self.CARD_WIDTH // 2, y + self.CARD_HEIGHT // 2))
            screen.blit(rotated_surface, new_rect)
        else:
            screen.blit(card_surface, (x, y))