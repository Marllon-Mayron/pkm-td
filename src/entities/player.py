# src/entities/player.py
import pygame
from src.entities.base import Entity
from src.entities.pokemon import Pokemon
from src.data.pokedex import Pokedex


class Player(Entity):
    def __init__(self, x, y):
        # Sprite placeholder
        sprite = pygame.Surface((20, 20))
        sprite.fill((255, 0, 0))

        super().__init__(x, y, 20, 20, sprite)

        self.pokedex = Pokedex()

        # Recursos
        self.money = 100
        self.score = 0

        # Time principal (máx 6)
        self.team = []

        # PC Box (armazenamento)
        self.pc_box = []

        # Slot selecionado
        self.selected_slot = 0

        # Pokedex registrada (quais já viu)
        self.seen_pokemon = set()
        self.caught_pokemon = set()

    def add_to_team(self, pokemon, slot=None):
        """Adiciona Pokémon ao time"""
        if len(self.team) >= 6:
            return False, "Time cheio!"

        if slot is not None and 0 <= slot < 6:
            if slot < len(self.team):
                self.team[slot] = pokemon
            else:
                self.team.append(pokemon)
        else:
            self.team.append(pokemon)

        pokemon.is_in_team = True
        return True, f"{pokemon.name} adicionado ao time"

    def remove_from_team(self, slot):
        """Remove Pokémon do time"""
        if 0 <= slot < len(self.team):
            pokemon = self.team.pop(slot)
            pokemon.is_in_team = False
            return pokemon
        return None

    def add_to_box(self, pokemon):
        """Adiciona Pokémon ao PC Box"""
        self.pc_box.append(pokemon)
        pokemon.is_in_team = False
        self.caught_pokemon.add(pokemon.id)

    def register_seen(self, pokemon_id):
        """Registra Pokémon como visto"""
        self.seen_pokemon.add(pokemon_id)

    def get_team_size(self):
        return len(self.team)

    def get_team_slot(self, index):
        if 0 <= index < len(self.team):
            return self.team[index]
        return None

    def has_team_space(self):
        return len(self.team) < 6

    def heal_team(self):
        """Cura todo o time"""
        for pokemon in self.team:
            pokemon.heal()

    def get_first_available(self):
        """Retorna primeiro Pokémon vivo do time"""
        for pokemon in self.team:
            if pokemon.is_alive():
                return pokemon
        return None

    def switch_pokemon(self, slot):
        """Troca para Pokémon em slot específico"""
        if 0 <= slot < len(self.team) and self.team[slot].is_alive():
            self.selected_slot = slot
            return self.team[slot]
        return None

    def get_team_info(self):
        """Retorna informações do time para UI"""
        info = []
        for i, pokemon in enumerate(self.team):
            status = "VIVO" if pokemon.is_alive() else "FV"
            info.append(f"{i + 1}. {pokemon.name} Lv.{pokemon.level} {status}")
        return info

    def add_starter(self, starter_id=1):
        """Adiciona Pokémon inicial (para testes)"""
        starter = Pokemon(0, 0, starter_id, level=5, is_wild=False)
        success, msg = self.add_to_team(starter, 0)
        if success:
            self.caught_pokemon.add(starter_id)
            self.register_seen(starter_id)
        return starter