# src/entities/target_item.py

import pygame
import os
import random
import math
from src.entities.base import Entity
from src.data.item_catalog import item_catalog

class TargetItem(Entity):
    """Item que precisa ser protegido durante a wave"""

    def __init__(self, x, y, item_id, offset_range=15):
        super().__init__(x, y, 16, 16, None)  # Hitbox continua 16x16

        self.item_id = item_id

        # Carrega informações do catálogo
        item_info = item_catalog.get_item(item_id)
        self.item_name = item_info["name"]
        self.sprite_path = item_info["sprite"]

        self.is_protected = True
        self.carried_by = None
        self.is_stolen = False
        self.capture_progress = 0
        self.capture_rate = 10

        # Variação visual (não afeta hitbox)
        self.visual_offset_x = random.uniform(-offset_range, offset_range)
        self.visual_offset_y = random.uniform(-offset_range, offset_range)
        self.rotation = random.uniform(-30, 30)

        # Posição base (posição original no mapa)
        self.base_x = x
        self.base_y = y

        # Posição atual (pode mudar quando dropado)
        self.current_x = x
        self.current_y = y

        # Flag para indicar se o item foi dropado
        self.was_carried = False

        # Carrega sprite
        self.sprite = None
        self.original_sprite_size = 32
        self.load_sprite()

        # Referência ao screen_manager
        self.screen_manager = None

    def load_sprite(self):
        """Carrega o sprite do item"""
        if self.sprite_path and os.path.exists(self.sprite_path):
            try:
                self.sprite = pygame.image.load(self.sprite_path).convert_alpha()
            except Exception as e:
                print(f"✗ Erro ao carregar sprite do item {self.sprite_path}: {e}")
                self.sprite = None

    def get_capture_position(self) -> tuple:
        """
        Retorna a posição atual do item para detecção de captura.
        Se está sendo carregado, retorna a posição do Pokémon que carrega.
        Se não, retorna a posição atual onde está no chão.
        """
        if self.carried_by:
            return (self.carried_by.x, self.carried_by.y)
        else:
            return (self.current_x, self.current_y)

    def update(self, dt):
        """Atualiza lógica do item"""
        if self.carried_by:
            # Item sendo carregado - segue o Pokémon
            self.current_x = self.carried_by.x
            self.current_y = self.carried_by.y
            self.x = self.current_x
            self.y = self.current_y
            self.rect.center = (int(self.x), int(self.y))
        else:
            # Quando não está sendo carregado, usa a posição atual
            self.x = self.current_x
            self.y = self.current_y
            self.rect.center = (int(self.x), int(self.y))

    def start_capture(self, pokemon):
        """Inicia o processo de captura por um Pokémon"""
        if not self.carried_by and self.is_protected:
            self.carried_by = pokemon
            pokemon.is_carrying = self
            print(f"{pokemon.name} começou a carregar {self.item_name}")

    def reset_capture(self):
        """Reseta o processo de captura quando o Pokémon é morto/capturado (item volta ao chão)"""
        if self.carried_by:
            print(f"[ITEM] Resetando captura de {self.item_name} - {self.carried_by.name} foi derrotado/capturado")

            # ===== CORREÇÃO: Salva a posição atual onde o Pokémon morreu =====
            drop_x = self.carried_by.x
            drop_y = self.carried_by.y

            # Limpa a referência no Pokémon
            if hasattr(self.carried_by, 'is_carrying'):
                self.carried_by.is_carrying = None

            # Reseta o estado do item
            self.carried_by = None
            self.capture_progress = 0
            self.is_protected = True
            self.is_stolen = False
            self.was_carried = True

            # ===== CRUCIAL: Atualiza a posição atual para onde o Pokémon morreu =====
            self.current_x = drop_x
            self.current_y = drop_y
            self.x = drop_x
            self.y = drop_y
            self.rect.center = (int(drop_x), int(drop_y))

            print(f"[ITEM] {self.item_name} dropado em ({drop_x:.1f}, {drop_y:.1f})")

    def update_capture(self, dt):
        """Atualiza o progresso de captura"""
        if self.carried_by:
            self.capture_progress += self.capture_rate * dt
            if self.capture_progress >= 100:
                self.complete_capture()

    def get_capture_position(self) -> tuple:
        """
        Retorna a posição atual do item para detecção de captura.
        Se está sendo carregado, retorna a posição do Pokémon que carrega.
        Se não, retorna a posição atual onde está no chão.
        """
        if self.carried_by:
            return (self.carried_by.x, self.carried_by.y)
        else:
            return (self.current_x, self.current_y)

    def complete_capture(self):
        """Completa a captura do item"""
        if self.carried_by:
            self.is_protected = False
            self.is_stolen = True
            self.carried_by.is_carrying = None
            self.carried_by = None
