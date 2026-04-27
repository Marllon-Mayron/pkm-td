# src/scenes/minigames/survival/components/card_deck.py

"""
Sistema de deck estilo esteira de supermercado
- TODAS as cartas deslizam suavemente quando uma é removida
- Layout claro com nome, nível, tipo, portrait
"""

import pygame
import random
import math
from typing import List, Dict, Any, Optional
from collections import deque
from src.data.pokedex import Pokedex


class CardDeck:
    """Gerencia o deck de cartas estilo esteira de supermercado"""

    CARD_WIDTH = 110
    CARD_HEIGHT = 130
    VISIBLE_CARDS = 5
    CARD_SPACING = 12

    # Configurações da esteira
    CARD_ENTRY_DURATION = 0.8  # Duração da entrada de nova carta
    SLIDE_DURATION = 0.25  # Duração do deslizamento

    def __init__(self, game_scene):
        self.game_scene = game_scene
        self.pokedex = Pokedex()

        # Cartas na esteira (ordem da esquerda para direita)
        self.cards: List[Dict] = []
        self.pending_cards: deque = deque()
        self.card_cooldowns: Dict[int, float] = {}

        # ===== SISTEMA DE ANIMAÇÃO =====
        # Cada carta tem sua posição X atual (para animação suave)
        self.card_x_positions: List[float] = []  # Posição atual de cada carta
        self.target_x_positions: List[float] = []  # Posição alvo de cada carta

        # Animação de deslizamento ativa
        self.is_sliding = False
        self.slide_progress = 0.0

        # Animação de entrada
        self.entering_card = None  # {"card": card, "progress": 0.0, "target_x": 0, "current_x": 0}

        # Seleção
        self.selected_index = -1
        self.hovered_index = -1

        # Cache
        self._font_cache = {}
        self._portrait_cache = {}

        # Posições fixas (calculadas uma vez e reutilizadas)
        self.fixed_positions: List[float] = []

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

    def _calculate_fixed_positions(self):
        """Calcula as posições fixas onde as cartas devem ficar (0 a 4)"""
        viewport = self.game_scene.screen_manager
        viewport_width = viewport.viewport_width

        total_width = self.VISIBLE_CARDS * (self.CARD_WIDTH + self.CARD_SPACING) - self.CARD_SPACING
        start_x = (viewport_width - total_width) // 2

        positions = []
        for i in range(self.VISIBLE_CARDS):
            x = start_x + i * (self.CARD_WIDTH + self.CARD_SPACING)
            positions.append(x)

        return positions

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
        """Preenche as 5 posições da esteira"""
        self.cards = []
        self.card_cooldowns = {}
        self.card_x_positions = []
        self.target_x_positions = []

        self.fixed_positions = self._calculate_fixed_positions()

        for i in range(self.VISIBLE_CARDS):
            if self.pending_cards:
                card = self.pending_cards.popleft()
                card["portrait"] = self._get_portrait(card["id"])
                self.cards.append(card)
                self.card_cooldowns[i] = 0.0
                self.card_x_positions.append(self.fixed_positions[i])
                self.target_x_positions.append(self.fixed_positions[i])

    def remove_card(self, index: int):
        """Remove uma carta e inicia animação de deslizamento"""
        if index < 0 or index >= len(self.cards):
            return

        removed_name = self.cards[index].get('name', 'Unknown')
        print(f"[CARD_DECK] Removendo carta {removed_name} da posição {index}")

        # Guarda as posições alvo ANTES da remoção para animação
        old_targets = self.target_x_positions.copy()

        # Remove a carta
        self.cards.pop(index)

        # Remove cooldown e reposiciona
        if index in self.card_cooldowns:
            del self.card_cooldowns[index]

        # Reorganiza cooldowns (desloca índices)
        new_cooldowns = {}
        for old_idx, time in self.card_cooldowns.items():
            if old_idx > index:
                new_cooldowns[old_idx - 1] = time
            else:
                new_cooldowns[old_idx] = time
        self.card_cooldowns = new_cooldowns

        # Calcula NOVAS posições alvo (cartas à direita vão para esquerda)
        self.fixed_positions = self._calculate_fixed_positions()
        self.target_x_positions = []
        for i in range(len(self.cards)):
            self.target_x_positions.append(self.fixed_positions[i])

        # Para cada carta restante, define sua posição atual como a posição alvo ANTIGA
        # Isso faz com que elas deslizem da posição antiga para a nova
        new_card_x_positions = []
        for i, card in enumerate(self.cards):
            # A posição antiga era a posição alvo antes da remoção
            # Se i >= index, a carta estava à direita da removida, então sua posição antiga era i+1
            old_pos_index = i if i < index else i + 1
            if old_pos_index < len(old_targets):
                new_card_x_positions.append(old_targets[old_pos_index])
            else:
                new_card_x_positions.append(self.fixed_positions[i])

        self.card_x_positions = new_card_x_positions

        # Inicia animação de deslizamento
        self.is_sliding = True
        self.slide_progress = 0.0

        # Adiciona nova carta (vai entrar pela direita depois do slide)
        self._add_new_card_from_right()

    def _add_new_card_from_right(self):
        """Prepara uma nova carta para entrar pela DIREITA"""
        if len(self.pending_cards) == 0:
            self.pending_cards = deque(self.card_pool.copy())
            random.shuffle(self.pending_cards)

        if self.pending_cards:
            card = self.pending_cards.popleft()
            card["portrait"] = self._get_portrait(card["id"])

            # A nova carta vai entrar na última posição
            final_index = len(self.cards)
            if final_index < self.VISIBLE_CARDS:
                self.fixed_positions = self._calculate_fixed_positions()
                target_x = self.fixed_positions[final_index]
                start_x = self.game_scene.screen_manager.viewport_width + 50

                self.entering_card = {
                    "card": card,
                    "progress": 0.0,
                    "current_x": start_x,
                    "start_x": start_x,
                    "target_x": target_x
                }
                print(f"[CARD_DECK] Nova carta entrando: {card['name']} -> pos {final_index}")

    def start_cooldown(self, index: int):
        """Inicia cooldown da carta"""
        if 0 <= index < len(self.cards):
            self.card_cooldowns[index] = 3.0

    def update(self, dt: float):
        """Atualiza animações"""
        # ===== ANIMAÇÃO DE DESLIZAMENTO =====
        if self.is_sliding:
            self.slide_progress += dt / self.SLIDE_DURATION

            if self.slide_progress >= 1.0:
                # Animação terminada - fixa nas posições alvo
                self.is_sliding = False
                self.card_x_positions = self.target_x_positions.copy()
            else:
                # Interpola entre posição atual e alvo
                ease = 1 - (1 - self.slide_progress) ** 3  # ease out cubic
                for i in range(len(self.cards)):
                    if i < len(self.card_x_positions) and i < len(self.target_x_positions):
                        start_x = self.card_x_positions[i]
                        end_x = self.target_x_positions[i]
                        self.card_x_positions[i] = start_x + (end_x - start_x) * ease

        # ===== ANIMAÇÃO DE ENTRADA =====
        if self.entering_card:
            self.entering_card["progress"] += dt / self.CARD_ENTRY_DURATION

            if self.entering_card["progress"] >= 1.0:
                # Insere a carta no final
                card = self.entering_card["card"]
                self.cards.append(card)
                self.card_cooldowns[len(self.cards) - 1] = 0.0

                # Atualiza posições
                self.fixed_positions = self._calculate_fixed_positions()
                self.target_x_positions = self.fixed_positions[:len(self.cards)]
                self.card_x_positions = self.target_x_positions.copy()

                self.entering_card = None
                print(f"[CARD_DECK] Carta entrou na esteira!")
            else:
                # Interpola posição da carta entrante
                ease = 1 - (1 - self.entering_card["progress"]) ** 3
                start_x = self.entering_card["start_x"]
                end_x = self.entering_card["target_x"]
                self.entering_card["current_x"] = start_x + (end_x - start_x) * ease

        # ===== ATUALIZA COOLDOWNS =====
        for idx in list(self.card_cooldowns.keys()):
            if self.card_cooldowns[idx] > 0:
                self.card_cooldowns[idx] -= dt
                if self.card_cooldowns[idx] < 0:
                    self.card_cooldowns[idx] = 0

    def get_card_positions(self) -> List[tuple]:
        """
        Retorna lista de (índice, x, y, card) para renderização
        """
        viewport = self.game_scene.screen_manager
        viewport_height = viewport.viewport_height
        base_y = viewport_height - self.CARD_HEIGHT - 30

        positions = []

        # Cartas normais
        for i, card in enumerate(self.cards):
            if i < len(self.card_x_positions):
                x = self.card_x_positions[i]
                positions.append((i, x, base_y, card))

        # Carta entrante (se existir e não estiver em posição final)
        if self.entering_card and self.entering_card["progress"] < 0.95:
            x = self.entering_card["current_x"]
            positions.append((len(self.cards), x, base_y, self.entering_card["card"]))

        return positions

    def get_card_at_pos(self, mouse_x: int, mouse_y: int) -> Optional[int]:
        """Retorna o índice da carta na posição do mouse"""
        positions = self.get_card_positions()
        for idx, x, y, card in positions:
            if card is None:
                continue
            if (x <= mouse_x <= x + self.CARD_WIDTH and
                    y <= mouse_y <= y + self.CARD_HEIGHT):
                return idx
        return -1

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
            return None

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if hasattr(self.game_scene, 'screen_manager'):
                screen_mgr = self.game_scene.screen_manager
                mouse_x, mouse_y = event.pos
                rel_x = mouse_x - screen_mgr.viewport_x
                rel_y = mouse_y - screen_mgr.viewport_y
                idx = self.get_card_at_pos(rel_x, rel_y)

                if idx >= 0 and idx < len(self.cards):
                    if self.card_cooldowns.get(idx, 0) <= 0:
                        card = self.cards[idx]
                        if self.game_scene.can_afford(card["cost"]):
                            self.selected_index = idx
                            return {
                                "action": "card_selected",
                                "index": idx,
                                "pokemon_data": card
                            }
            return None

        return None

    def clear_selection(self):
        self.selected_index = -1

    def render(self, screen):
        screen_mgr = self.game_scene.screen_manager
        viewport_x = screen_mgr.viewport_x
        viewport_y = screen_mgr.viewport_y

        # Fundo da área do deck
        deck_height = self.CARD_HEIGHT + 80
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

        for i in range(3):
            alpha = 60 - i * 15
            pygame.draw.line(screen, (80, 100, 140, alpha),
                             (deck_rect.x, deck_rect.y + i),
                             (deck_rect.x + deck_rect.width, deck_rect.y + i))

        positions = self.get_card_positions()
        for idx, x, y, card in positions:
            self._render_card(screen, idx, x + viewport_x, y + viewport_y, card)

    def _render_card(self, screen, idx: int, x: int, y: int, card: Dict):
        """Renderiza uma carta individual"""
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

        # Sombra
        shadow_surf = pygame.Surface((self.CARD_WIDTH, self.CARD_HEIGHT), pygame.SRCALPHA)
        shadow_surf.fill((0, 0, 0, 80))
        screen.blit(shadow_surf, (x + 4, y + 4))

        # Fundo
        card_rect = pygame.Rect(x, y, self.CARD_WIDTH, self.CARD_HEIGHT)
        pygame.draw.rect(screen, card_color, card_rect, border_radius=8)

        # Borda colorida pelo tipo
        if not energy_insufficient:
            type_color = self._get_type_color(card["type"])
            pygame.draw.rect(screen, type_color, card_rect, 3, border_radius=8)
        else:
            pygame.draw.rect(screen, self.COLORS['energy_insufficient'], card_rect, 3, border_radius=8)
            energy_overlay = pygame.Surface((self.CARD_WIDTH, self.CARD_HEIGHT), pygame.SRCALPHA)
            energy_overlay.fill((180, 50, 50, 100))
            screen.blit(energy_overlay, (x, y))

        # Portrait
        portrait = card.get("portrait")
        if portrait:
            portrait_x = x + (self.CARD_WIDTH - 58) // 2
            portrait_y = y + 8
            screen.blit(portrait, (portrait_x, portrait_y))

        # Nome
        name_font = self._get_font(13, bold=True)
        name = card["name"]
        if len(name) > 10:
            name = name[:9] + "."
        name_surf = name_font.render(name, True, self.COLORS['text'])
        name_x = x + (self.CARD_WIDTH - name_surf.get_width()) // 2
        name_y = y + self.CARD_HEIGHT - 48
        screen.blit(name_surf, (name_x, name_y))

        # Tipo
        type_font = self._get_font(10, bold=True)
        type_name = card["type"].upper()
        if len(type_name) > 5:
            type_name = type_name[:4]
        type_bg_rect = pygame.Rect(x + 5, y + self.CARD_HEIGHT - 22, 38, 16)
        pygame.draw.rect(screen, self._get_type_color(card["type"]), type_bg_rect, border_radius=4)
        type_surf = type_font.render(type_name, True, (255, 255, 255))
        screen.blit(type_surf, (x + 7, y + self.CARD_HEIGHT - 21))

        # Nível (destacado)
        level_font = self._get_font(14, bold=True)
        level_text = f"Lv {card['level']}"
        level_surf = level_font.render(level_text, True, self.COLORS['level'])
        level_bg = pygame.Surface((level_surf.get_width() + 6, level_surf.get_height() + 2), pygame.SRCALPHA)
        level_bg.fill((0, 0, 0, 150))
        level_x = x + self.CARD_WIDTH - level_surf.get_width() - 8
        level_y = y + self.CARD_HEIGHT - 22
        screen.blit(level_bg, (level_x - 3, level_y - 1))
        screen.blit(level_surf, (level_x, level_y))

        # Custo
        cost_font = self._get_font(14, bold=True)
        cost_text = str(card['cost'])
        if energy_insufficient:
            cost_circle_color = self.COLORS['energy_insufficient']
            cost_text_color = (255, 200, 200)
        else:
            cost_circle_color = self.COLORS['cost']
            cost_text_color = (40, 30, 0)
        pygame.draw.circle(screen, cost_circle_color, (x + 20, y + 20), 14)
        cost_surf = cost_font.render(cost_text, True, cost_text_color)
        screen.blit(cost_surf, (x + 20 - cost_surf.get_width() // 2, y + 15))

        # Cooldown
        if is_on_cooldown:
            overlay = pygame.Surface((self.CARD_WIDTH, self.CARD_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 180))
            screen.blit(overlay, (x, y))
            bar_height = 6
            bar_width = int(self.CARD_WIDTH * (1 - cooldown_percent))
            bar_rect = pygame.Rect(x, y + self.CARD_HEIGHT - bar_height, bar_width, bar_height)
            pygame.draw.rect(screen, self.COLORS['cooldown'], bar_rect)
            time_font = self._get_font(12, bold=True)
            time_text = f"{self.card_cooldowns[idx]:.0f}s"
            time_surf = time_font.render(time_text, True, self.COLORS['text'])
            time_x = x + (self.CARD_WIDTH - time_surf.get_width()) // 2
            time_y = y + (self.CARD_HEIGHT - time_surf.get_height()) // 2
            screen.blit(time_surf, (time_x, time_y))

        # Aviso energia
        if energy_insufficient and not is_on_cooldown:
            warn_font = self._get_font(9, bold=True)
            warn_text = warn_font.render("ENERGIA", True, (255, 180, 180))
            warn_x = x + (self.CARD_WIDTH - warn_text.get_width()) // 2
            warn_y = y + self.CARD_HEIGHT - 36
            screen.blit(warn_text, (warn_x, warn_y))

        # Hover glow
        if is_hovered and not is_selected and not energy_insufficient:
            glow = pygame.Surface((self.CARD_WIDTH, self.CARD_HEIGHT), pygame.SRCALPHA)
            glow.fill((100, 150, 220, 40))
            screen.blit(glow, (x, y))

        # Seleção
        if is_selected:
            pulse = abs(math.sin(self.game_scene.survival_ui.wave_pulse)) * 0.5 + 0.5
            radius = int(10 + 4 * pulse)
            pygame.draw.circle(screen, self.COLORS['border_glow'],
                               (x + self.CARD_WIDTH // 2, y + self.CARD_HEIGHT - 10), radius, 2)
            pygame.draw.circle(screen, self.COLORS['border_glow'],
                               (x + self.CARD_WIDTH // 2, y + self.CARD_HEIGHT - 10), radius // 2)