# src/editor/wave_config.py

import json
import random


class WaveEnemy:
    """Representa um tipo de inimigo em uma wave"""

    def __init__(self, pokemon_id=1, percentage=100):
        self.pokemon_id = pokemon_id  # ID numérico do Pokémon
        self.percentage = percentage  # Porcentagem de aparecimento (0-100)

    def to_dict(self):
        return {
            "pokemon_id": self.pokemon_id,
            "percentage": self.percentage
        }

    def from_dict(self, data):
        self.pokemon_id = data.get("pokemon_id", 1)
        self.percentage = data.get("percentage", 100)
        return self


class Wave:
    """Representa uma wave de inimigos"""

    def __init__(self, wave_index=0):
        self.wave_index = wave_index

        # Configuração básica
        self.path_index = 0  # Qual path esta wave usa (0 = primeiro path)
        self.name = f"Wave {wave_index + 1}"
        self.enabled = True

        # Composição da wave (tipos de Pokémon)
        self.enemies = [
        ]

        # Nível dos inimigos
        self.min_level = 1
        self.max_level = 5

        # Tamanho da wave
        self.wave_size = 10  # Total de inimigos nesta wave

        # Timing de geração
        self.spawn_interval = 3.0  # Segundos entre spawns
        self.initial_delay = 2.0  # Delay antes de começar a wave

        # Pode ser usado para waves que se repetem
        self.repeat_wave = False
        self.repeat_count = 1

    def get_random_enemy(self):
        """Retorna um inimigo aleatório baseado nas porcentagens"""
        if not self.enemies:
            return None

        # Normaliza porcentagens para soma 100
        total = sum(e.percentage for e in self.enemies)
        if total <= 0:
            return random.choice(self.enemies)

        roll = random.uniform(0, total)
        cumulative = 0

        for enemy in self.enemies:
            cumulative += enemy.percentage
            if roll <= cumulative:
                return enemy

        return self.enemies[-1]

    def to_dict(self):
        return {
            "wave_index": self.wave_index,
            "path_index": self.path_index,
            "name": self.name,
            "enabled": self.enabled,
            "enemies": [e.to_dict() for e in self.enemies],
            "min_level": self.min_level,
            "max_level": self.max_level,
            "wave_size": self.wave_size,
            "spawn_interval": self.spawn_interval,
            "initial_delay": self.initial_delay,
            "repeat_wave": self.repeat_wave,
            "repeat_count": self.repeat_count
        }

    def from_dict(self, data):
        self.wave_index = data.get("wave_index", 0)
        self.path_index = data.get("path_index", 0)
        self.name = data.get("name", f"Wave {self.wave_index + 1}")
        self.enabled = data.get("enabled", True)

        self.enemies = []
        for e_data in data.get("enemies", []):
            enemy = WaveEnemy()
            enemy.from_dict(e_data)
            self.enemies.append(enemy)

        self.min_level = data.get("min_level", 1)
        self.max_level = data.get("max_level", 5)
        self.wave_size = data.get("wave_size", 10)
        self.spawn_interval = data.get("spawn_interval", 3.0)
        self.initial_delay = data.get("initial_delay", 2.0)
        self.repeat_wave = data.get("repeat_wave", False)
        self.repeat_count = data.get("repeat_count", 1)

        return self


class WaveManager:
    """Gerencia múltiplas waves"""

    def __init__(self):
        self.waves = []
        self.selected_wave = 0
        self.max_waves = 10

        # Lista de Pokémon disponíveis (mock - depois virá de um arquivo de dados)
        self.available_pokemon = [
            {"id": "pikachu", "name": "Pikachu", "sprite": None},
            {"id": "charmander", "name": "Charmander", "sprite": None},
            {"id": "squirtle", "name": "Squirtle", "sprite": None},
            {"id": "bulbasaur", "name": "Bulbasaur", "sprite": None},
            {"id": "pidgey", "name": "Pidgey", "sprite": None},
            {"id": "rattata", "name": "Rattata", "sprite": None},
            {"id": "geodude", "name": "Geodude", "sprite": None},
            {"id": "zubat", "name": "Zubat", "sprite": None},
            {"id": "machop", "name": "Machop", "sprite": None},
            {"id": "gastly", "name": "Gastly", "sprite": None},
        ]

    def add_wave(self):
        """Adiciona uma nova wave"""
        if len(self.waves) < self.max_waves:
            new_wave = Wave(len(self.waves))
            self.waves.append(new_wave)
            self.selected_wave = len(self.waves) - 1
            print(f"Wave {len(self.waves)} adicionada")
            return True
        return False

    def remove_wave(self, index):
        """Remove uma wave"""
        if 0 <= index < len(self.waves):
            del self.waves[index]
            # Reindexa as waves
            for i, wave in enumerate(self.waves):
                wave.wave_index = i
            if self.selected_wave >= len(self.waves):
                self.selected_wave = max(0, len(self.waves) - 1)
            return True
        return False

    def get_current_wave(self):
        """Retorna a wave selecionada atualmente"""
        if 0 <= self.selected_wave < len(self.waves):
            return self.waves[self.selected_wave]
        return None

    def get_waves_for_path(self, path_index):
        """Retorna todas as waves associadas a um path específico"""
        return [w for w in self.waves if w.path_index == path_index]

    def to_dict(self):
        return {
            "waves": [w.to_dict() for w in self.waves],
            "selected_wave": self.selected_wave
        }

    def from_dict(self, data):
        self.waves = []
        for w_data in data.get("waves", []):
            wave = Wave()
            wave.from_dict(w_data)
            self.waves.append(wave)
        self.selected_wave = data.get("selected_wave", 0)
        if self.selected_wave >= len(self.waves):
            self.selected_wave = max(0, len(self.waves) - 1)