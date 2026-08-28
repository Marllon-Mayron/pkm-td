# src/entities/player.py
import pygame
from src.entities.base import Entity
from src.data.pokedex import Pokedex
from src.managers.bag_manager import BagManager
from src.managers.save_manager import SaveManager
from src.managers.achievement_manager import AchievementManager


class Player(Entity):
    def __init__(self, x, y):
        # Sprite placeholder
        sprite = pygame.Surface((20, 20))
        sprite.fill((255, 0, 0))

        super().__init__(x, y, 20, 20, sprite)

        self.pokedex = Pokedex()

        self.bag = BagManager(self)

        self.chapter_page_num = 1

        # Recursos
        self.money = 100
        self.score = 0

        # Time principal (máx 6)
        self.team = []

        # PC Box (armazenamento)
        self.pc_box = []

        # Lista de conquistas do jogador
        self.achievements = {
            "unlocked": [],
            "counters": {}
        }

        self.achievement_manager = AchievementManager(self)

        self._heal_count = 0
        self._capture_count = 0
        self._badge_count = 0
        self._boss_defeated_count = 0
        self._perfect_phase_count = 0

        # Slot selecionado
        self.selected_slot = 0

        # Pokedex registrada (quais já viu)
        self.seen_pokemon = set()
        self.caught_pokemon = set()

        # Mystery Gift: códigos já resgatados (completo)
        # Formato: {"CODIGO": {"pokemon_id": int, "pokemon_name": str, "date": str, "event_name": str}}
        self.redeemed_codes = {}

        # Histórico completo de gifts resgatados
        self.mystery_gift_history = []

        self.save_manager = SaveManager()



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
        # Garante que o unique_id é preservado
        if not hasattr(pokemon, 'unique_id'):
            import uuid
            pokemon.unique_id = str(uuid.uuid4())

        pokemon.is_in_team = False
        pokemon.is_placed = False
        pokemon.is_wild = False

        self.pc_box.append(pokemon)
        self.caught_pokemon.add(pokemon.id)
        print(f"[PLAYER] {pokemon.name} (ID: {pokemon.unique_id[:8]}) adicionado à PC Box. Total: {len(self.pc_box)}")

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
        """Adiciona Pokémon inicial (para testes ou seleção)"""
        from src.entities.pokemon import Pokemon

        # Verifica se o time está vazio
        if len(self.team) > 0:
            print(f"[PLAYER] Time já tem {len(self.team)} Pokémon. Limpando...")
            self.team.clear()

        starter = Pokemon(0, 0, starter_id, level=5, is_wild=False)

        # Garante que o Pokémon está configurado corretamente
        starter.is_in_team = True
        starter.is_placed = False
        starter.is_wild = False

        self.team.append(starter)
        self.caught_pokemon.add(starter_id)
        self.register_seen(starter_id)

        print(f"[PLAYER] Pokémon inicial adicionado: {starter.name} (ID: {starter_id})")
        return starter

    #SALVAMENTOS

    def save_game(self, slot=1):
        """Salva o jogo atual"""
        from src.managers.save_manager import save_manager

        # Você pode passar o estado atual do jogo
        game_state = {
            "current_chapter": getattr(self, 'current_chapter', 1),
            "current_phase": getattr(self, 'current_phase', 1)
        }

        return save_manager.save_game(self, game_state, save_name=f"Save {slot}", slot=slot)

    def load_game(self, slot=1):
        """Carrega um jogo"""
        from src.managers.save_manager import save_manager
        return save_manager.load_game(self, slot)

    # Adicione este método para salvar automaticamente em momentos chave
    def auto_save(self):
        """Salvamento automático após ações importantes"""
        self.save_game()