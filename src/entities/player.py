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

        self.desfossilizadores = [] = []
        self._add_initial_desfossilizador()
        self.total_playtime = 0.0  # segundos totais de jogo
        self._playtime_accumulator = 0.0  # para acumular dt

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

    def _get_duration_for_level(self, level):
        """Retorna a duração em segundos para cada nível"""
        durations = {
            1: 3600,  # 1 hora
            2: 2700,  # 45 minutos
            3: 1200  # 20 minutos
        }
        return durations.get(level, 3600)

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

    # metodo para salvar automaticamente em momentos chave
    def auto_save(self):
        """Salvamento automático após ações importantes"""
        self.save_game()

    def _add_initial_desfossilizador(self):
        """Adiciona o desfossilizador inicial do jogador"""
        desfossilizador = {
            "id": 1,
            "level": 1,
            "status": "empty",  # "empty", "processing", "ready"
            "fossil_id": None,
            "pokemon_id": None,
            "start_time": None,
            "duration_minutes": self._get_duration_for_level(1),
            "time_elapsed": 0.0
        }
        self.desfossilizadores.append(desfossilizador)

    def add_desfossilizador(self, level=1):
        """Adiciona um novo desfossilizador vazio."""
        desfossilizador_id = len(self.desfossilizadores) + 1
        desfossilizador = {
            "id": desfossilizador_id,
            "level": level,
            "status": "empty",
            "fossil_id": None,
            "pokemon_id": None,
            "start_time": None,
            "duration_minutes": self._get_duration_for_level(level),
            "time_elapsed": 0.0
        }
        self.desfossilizadores.append(desfossilizador)

        # ===== CONQUISTA: COMPRAR DESFOSSILIZADOR =====

        self.achievement_manager.increment_counter("second_incubator_bought")
        self.achievement_manager.check_and_unlock("buy_second_incubator")

        return desfossilizador

    def start_desfossilizacao(self, desfossilizador_index, fossil_id, pokemon_id):
        """Inicia a desfossilização de um fóssil no desfossilizador."""
        desfossilizador = self.desfossilizadores[desfossilizador_index]
        if desfossilizador["status"] != "empty":
            return False
        desfossilizador["status"] = "processing"
        desfossilizador["fossil_id"] = fossil_id
        desfossilizador["pokemon_id"] = pokemon_id
        desfossilizador["start_time"] = None
        desfossilizador["time_elapsed"] = 0.0
        return True

    def update_desfossilizadores(self, dt):
        """Atualiza o progresso dos desfossilizadores."""
        for desfossilizador in self.desfossilizadores:
            if desfossilizador["status"] == "processing":
                desfossilizador["time_elapsed"] += dt
                if desfossilizador["time_elapsed"] >= desfossilizador["duration_minutes"]:
                    desfossilizador["status"] = "ready"
                    desfossilizador["start_time"] = None
                    desfossilizador["time_elapsed"] = desfossilizador["duration_minutes"]

    def collect_pokemon_from_desfossilizador(self, desfossilizador_index):
        """Coleta o Pokémon do desfossilizador pronto."""
        desfossilizador = self.desfossilizadores[desfossilizador_index]
        if desfossilizador["status"] != "ready":
            return None
        pokemon_id = desfossilizador["pokemon_id"]
        from src.entities.pokemon import Pokemon
        pokemon = Pokemon(0, 0, pokemon_id, level=5, is_wild=False)

        if len(self.team) < 6:
            self.team.append(pokemon)
            pokemon.is_in_team = True
        else:
            self.pc_box.append(pokemon)

        # ===== REGISTRA NA POKÉDEX =====
        self.caught_pokemon.add(pokemon_id)
        self.register_seen(pokemon_id)

        # ===== CONQUISTA: FÓSSIL =====
        self.achievement_manager.increment_counter("incubator_revive_count")
        self.achievement_manager.check_and_unlock("first_incubator_revive")

        desfossilizador["status"] = "empty"
        desfossilizador["fossil_id"] = None
        desfossilizador["pokemon_id"] = None
        desfossilizador["start_time"] = None
        desfossilizador["time_elapsed"] = 0.0
        return pokemon

    def upgrade_desfossilizador(self, desfossilizador_index):
        """Upgrade do desfossilizador para o próximo nível."""
        desfossilizador = self.desfossilizadores[desfossilizador_index]
        if desfossilizador["level"] >= 3:
            return False
        new_level = desfossilizador["level"] + 1
        cost = 30000 if desfossilizador["level"] == 1 else 50000
        if self.money < cost:
            return False
        self.money -= cost
        desfossilizador["level"] = new_level
        desfossilizador["duration_minutes"] = self._get_duration_for_level(new_level)

        # ===== CONQUISTA: UPGRADE DESFOSSILIZADOR =====
        self.achievement_manager.increment_counter("incubator_upgrade_count")
        self.achievement_manager.check_and_unlock("first_incubator_upgrade")
        return True