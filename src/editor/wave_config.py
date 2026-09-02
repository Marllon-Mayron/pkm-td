# src/editor/wave_config.py

import json
import random
from typing import List, Dict, Optional, Any


class WaveEnemy:
    """Representa um tipo de inimigo em uma wave com porcentagem decimal"""

    def __init__(self, pokemon_id=1, percentage=100.0):
        self.pokemon_id = pokemon_id
        self.percentage = percentage  # Agora aceita float (ex: 0.2)

    def to_dict(self):
        return {
            "pokemon_id": self.pokemon_id,
            "percentage": self.percentage
        }

    def from_dict(self, data):
        self.pokemon_id = data.get("pokemon_id", 1)
        self.percentage = float(data.get("percentage", 100.0))
        return self


class WaveTemplate:
    """
    Template de composição de Pokémon reutilizável entre waves.
    Pode ser usado em diferentes paths e waves.
    """

    def __init__(self, template_id: str = None, name: str = "Template"):
        self.template_id = template_id or f"template_{random.randint(1000, 9999)}"
        self.name = name
        self.enemies: List[WaveEnemy] = []
        self.min_level = 1
        self.max_level = 5

    def to_dict(self):
        return {
            "template_id": self.template_id,
            "name": self.name,
            "enemies": [e.to_dict() for e in self.enemies],
            "min_level": self.min_level,
            "max_level": self.max_level
        }

    def from_dict(self, data):
        self.template_id = data.get("template_id", f"template_{random.randint(1000, 9999)}")
        self.name = data.get("name", "Template")
        self.min_level = data.get("min_level", 1)
        self.max_level = data.get("max_level", 5)

        self.enemies = []
        for e_data in data.get("enemies", []):
            enemy = WaveEnemy()
            enemy.from_dict(e_data)
            self.enemies.append(enemy)

        return self


class WaveVariant:
    """
    Variação de uma wave baseada em condições (dia, noite, etc).
    """

    def __init__(self, condition: str = "any", enemies: List[WaveEnemy] = None):
        self.condition = condition  # "any", "day", "night", "dusk", "dawn", "cave", "deep"
        self.enemies = enemies or []
        self.min_level = 1
        self.max_level = 5
        self.template_id = None  # NOVO: pode usar um template

    def to_dict(self):
        return {
            "condition": self.condition,
            "enemies": [e.to_dict() for e in self.enemies],
            "min_level": self.min_level,
            "max_level": self.max_level,
            "template_id": self.template_id  # NOVO
        }

    def from_dict(self, data):
        self.condition = data.get("condition", "any")
        self.min_level = data.get("min_level", 1)
        self.max_level = data.get("max_level", 5)
        self.template_id = data.get("template_id")  # NOVO

        self.enemies = []
        for e_data in data.get("enemies", []):
            enemy = WaveEnemy()
            enemy.from_dict(e_data)
            self.enemies.append(enemy)

        return self


class Wave:
    """Representa uma wave de inimigos com suporte a templates e variantes"""

    def __init__(self, wave_index=0):
        self.wave_index = wave_index

        # Configuração básica
        self.path_index = 0
        self.name = f"Wave {wave_index + 1}"
        self.enabled = True

        # ===== NOVO: Templates =====
        self.template_id = None  # Se definido, usa os inimigos do template

        # ===== NOVO: Variantes por período =====
        self.variants: List[WaveVariant] = []
        self.use_variants = False  # Se True, usa variants em vez de enemies direto

        # ===== LEGADO: enemies direto (mantido para compatibilidade) =====
        self.enemies: List[WaveEnemy] = []

        # Nível dos inimigos
        self.min_level = 1
        self.max_level = 5

        # Tamanho da wave
        self.wave_size = 10

        # Timing
        self.spawn_interval = 3.0
        self.initial_delay = 2.0

        # Repetição
        self.repeat_wave = False
        self.repeat_count = 1

    def get_enemies_for_condition(self, condition: str = "any") -> List[WaveEnemy]:
        """
        Retorna a lista de inimigos para uma condição específica.
        Se usar templates, retorna do template.
        Se usar variants, retorna a variant da condição.
        Senão, retorna enemies direto.
        """
        # ===== PRIORIDADE 1: Template =====
        if self.template_id:
            template = WaveTemplateManager.get_template(self.template_id)
            if template:
                return template.enemies

        # ===== PRIORIDADE 2: Variants =====
        if self.use_variants and self.variants:
            # Tenta encontrar variant para a condição
            for variant in self.variants:
                if variant.condition == condition:
                    return variant.enemies
            # Se não encontrar, tenta "any"
            for variant in self.variants:
                if variant.condition == "any":
                    return variant.enemies
            # Fallback: primeira variant
            if self.variants:
                return self.variants[0].enemies

        # ===== PRIORIDADE 3: enemies direto (legado) =====
        return self.enemies

    def get_level_range_for_condition(self, condition: str = "any") -> tuple:
        """Retorna (min_level, max_level) para a condição"""
        # Template
        if self.template_id:
            template = WaveTemplateManager.get_template(self.template_id)
            if template:
                return (template.min_level, template.max_level)

        # Variants
        if self.use_variants and self.variants:
            for variant in self.variants:
                if variant.condition == condition:
                    return (variant.min_level, variant.max_level)
            for variant in self.variants:
                if variant.condition == "any":
                    return (variant.min_level, variant.max_level)
            if self.variants:
                return (self.variants[0].min_level, self.variants[0].max_level)

        # Legado
        return (self.min_level, self.max_level)

    def get_random_enemy(self, condition: str = "any") -> Optional[WaveEnemy]:
        """Retorna um inimigo aleatório baseado nas porcentagens para a condição"""
        enemies = self.get_enemies_for_condition(condition)

        if not enemies:
            return None

        total = sum(e.percentage for e in enemies)
        if total <= 0:
            return random.choice(enemies)

        roll = random.uniform(0, total)
        cumulative = 0.0

        for enemy in enemies:
            cumulative += enemy.percentage
            if roll <= cumulative:
                return enemy

        return enemies[-1]

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
            "repeat_count": self.repeat_count,
            # ===== NOVOS CAMPOS =====
            "template_id": self.template_id,
            "use_variants": self.use_variants,
            "variants": [v.to_dict() for v in self.variants]
        }

    def from_dict(self, data):
        self.wave_index = data.get("wave_index", 0)
        self.path_index = data.get("path_index", 0)  # JÁ ESTÁ CORRETO
        self.name = data.get("name", f"Wave {self.wave_index + 1}")
        self.enabled = data.get("enabled", True)

        # ===== CARREGA ENEMIES (LEGADO) =====
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

        # ===== NOVOS CAMPOS (COM FALLBACK PARA COMPATIBILIDADE) =====
        self.template_id = data.get("template_id")
        self.use_variants = data.get("use_variants", False)

        self.variants = []
        for v_data in data.get("variants", []):
            variant = WaveVariant()
            variant.from_dict(v_data)
            self.variants.append(variant)

        return self


class WaveTemplateManager:
    """Gerencia templates de Pokémon reutilizáveis"""

    _templates: Dict[str, WaveTemplate] = {}

    @classmethod
    def add_template(cls, template: WaveTemplate):
        cls._templates[template.template_id] = template

    @classmethod
    def get_template(cls, template_id: str) -> Optional[WaveTemplate]:
        return cls._templates.get(template_id)

    @classmethod
    def get_all_templates(cls) -> List[WaveTemplate]:
        return list(cls._templates.values())

    @classmethod
    def remove_template(cls, template_id: str):
        if template_id in cls._templates:
            del cls._templates[template_id]

    @classmethod
    def clear(cls):
        cls._templates.clear()

    @classmethod
    def to_dict(cls):
        return {
            "templates": [t.to_dict() for t in cls._templates.values()]
        }

    @classmethod
    def from_dict(cls, data):
        cls._templates.clear()
        for t_data in data.get("templates", []):
            template = WaveTemplate()
            template.from_dict(t_data)
            cls._templates[template.template_id] = template


class WaveManager:
    """Gerencia múltiplas waves com suporte a templates e variants"""

    def __init__(self):
        self.waves: List[Wave] = []
        self.selected_wave = 0
        self.max_waves = 10

        # Templates
        self.template_manager = WaveTemplateManager()

    def add_wave(self):
        if len(self.waves) < self.max_waves:
            new_wave = Wave(len(self.waves))
            self.waves.append(new_wave)
            self.selected_wave = len(self.waves) - 1
            return True
        return False

    def remove_wave(self, index):
        if 0 <= index < len(self.waves):
            del self.waves[index]
            for i, wave in enumerate(self.waves):
                wave.wave_index = i
            if self.selected_wave >= len(self.waves):
                self.selected_wave = max(0, len(self.waves) - 1)
            return True
        return False

    def get_current_wave(self):
        if 0 <= self.selected_wave < len(self.waves):
            return self.waves[self.selected_wave]
        return None

    def get_waves_for_path(self, path_index):
        return [w for w in self.waves if w.path_index == path_index]

    def to_dict(self):
        return {
            "waves": [w.to_dict() for w in self.waves],
            "selected_wave": self.selected_wave,
            "templates": self.template_manager.to_dict()
        }

    def from_dict(self, data):
        # Carrega templates primeiro
        template_data = data.get("templates", {})
        self.template_manager.from_dict(template_data)

        # Carrega waves
        self.waves = []
        for w_data in data.get("waves", []):
            wave = Wave()
            wave.from_dict(w_data)
            self.waves.append(wave)

        self.selected_wave = data.get("selected_wave", 0)
        if self.selected_wave >= len(self.waves):
            self.selected_wave = max(0, len(self.waves) - 1)