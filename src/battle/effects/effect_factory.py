# src/battle/effects/effect_factory.py
from typing import Dict, Any, Optional
from .move_effect import MoveEffect, EffectTarget, EffectTiming


class EffectFactory:
    """Fábrica para criar efeitos de movimento a partir de configuração"""

    # Configurações pré-definidas para moves comuns
    MOVE_EFFECTS = {
        # Status moves - Stat Modifiers (4 segundos de duração)
        "string-shot": {
            "effect_type": "stat_mod",
            "target": EffectTarget.TARGET,
            "timing": EffectTiming.ON_HIT,
            "params": {
                "stat": "speed",
                "stages": -1,
                "duration": 4.0
            },
            "description": "Reduz a Velocidade do oponente",
            "attacker_animation": "shoot",  # Animação do atacante
            "min_distance": 0  # Distância mínima para usar animação
        },
        "growl": {
            "effect_type": "stat_mod",
            "target": EffectTarget.TARGET,
            "timing": EffectTiming.ON_HIT,
            "params": {
                "stat": "attack",
                "stages": -1,
                "duration": 4.0
            },
            "description": "Reduz o Ataque do oponente"
        },
        "growth": {
            "effect_type": "stat_mod",
            "target": EffectTarget.SELF,
            "timing": EffectTiming.ON_HIT,
            "params": {
                "stat": "sp_attack",
                "stages": 1,
                "duration": 4.0
            },
            "description": "Aumenta o Ataque Especial"
        },
        "swords-dance": {
            "effect_type": "stat_mod",
            "target": EffectTarget.SELF,
            "timing": EffectTiming.ON_HIT,
            "params": {
                "stat": "attack",
                "stages": 2,
                "duration": 6.0
            },
            "description": "Aumenta muito o Ataque"
        },
        "agility": {
            "effect_type": "stat_mod",
            "target": EffectTarget.SELF,
            "timing": EffectTiming.ON_HIT,
            "params": {
                "stat": "speed",
                "stages": 2,
                "duration": 3.0
            },
            "description": "Aumenta muito a Velocidade"
        },
        # ===== VENENO (POISON) =====
        "poison-sting": {
            "effect_type": "status_chance",
            "target": EffectTarget.TARGET,
            "timing": EffectTiming.ON_HIT,
            "params": {
                "status": "poison",
                "chance": 0.30,  # 30% de chance de envenenar
                "duration": None,  # Veneno é permanente até cura
                "overwrite": False  # Não sobrescreve outros status
            },
            "description": "Pode envenenar o oponente (30% de chance)"
        },
        "poison-powder": {
            "effect_type": "status",
            "target": EffectTarget.TARGET,
            "timing": EffectTiming.ON_HIT,
            "params": {
                "status": "poison",
                "duration": None,  # Veneno permanente
                "overwrite": False
            },
            "description": "Envenena o oponente",
            "attacker_animation": "rotate",
            "min_distance": 0
        },
        "toxic": {
            "effect_type": "status",
            "target": EffectTarget.TARGET,
            "timing": EffectTiming.ON_HIT,
            "params": {
                "status": "toxic_poison",  # Veneno tóxico (dano aumenta)
                "duration": None,
                "overwrite": True
            },
            "description": "Envenena gravemente o oponente"
        },
        # ===== PARALIZIA (PARALYZED) =====
        "thunder-wave": {
            "effect_type": "status",
            "target": EffectTarget.TARGET,
            "timing": EffectTiming.ON_HIT,
            "params": {
                "status": "paralysis",
                "duration": None
            },
            "description": "Paralisa o oponente"
        },
        "stun-spore": {
            "effect_type": "status",
            "target": EffectTarget.TARGET,
            "timing": EffectTiming.ON_HIT,
            "params": {
                "status": "paralysis",
                "duration": None
            },
            "description": "Paralisa o oponente",
            "attacker_animation": "rotate",
            "min_distance": 0
        },
        # ===== ADORMECER (SLEEP) =====
        "sleep-powder": {
            "effect_type": "status",
            "target": EffectTarget.TARGET,
            "timing": EffectTiming.ON_HIT,
            "params": {
                "status": "sleep",
                "duration": None,
                "overwrite": True
            },
            "description": "Coloca o oponente para dormir",
            "attacker_animation": "rotate",
            "min_distance": 0
        },
        "hypnosis": {
            "effect_type": "status",
            "target": EffectTarget.TARGET,
            "timing": EffectTiming.ON_HIT,
            "params": {
                "status": "sleep",
                "duration": None,
                "overwrite": True
            },
            "description": "Coloca o oponente para dormir"
        },
        # ===== QUEIMADURA (BURN) =====
        "will-o-wisp": {
            "effect_type": "status",
            "target": EffectTarget.TARGET,
            "timing": EffectTiming.ON_HIT,
            "params": {
                "status": "burn",
                "duration": None,  # Queimadura é permanente
                "overwrite": False
            },
            "description": "Queima o oponente"
        },
        "ember": {
            "effect_type": "status_chance",
            "target": EffectTarget.TARGET,
            "timing": EffectTiming.ON_HIT,
            "params": {
                "status": "burn",
                "chance": 0.10,
                "duration": None,
                "overwrite": False
            },
            "description": "Pode queimar o oponente (10% de chance)"
        },
        "flamethrower": {
            "effect_type": "status_chance",
            "target": EffectTarget.TARGET,
            "timing": EffectTiming.ON_HIT,
            "params": {
                "status": "burn",
                "chance": 0.10,  # 10% de chance
                "duration": None,
                "overwrite": False
            },
            "description": "Pode queimar o oponente (10% de chance)"
        },
        "fire-blast": {
            "effect_type": "status_chance",
            "target": EffectTarget.TARGET,
            "timing": EffectTiming.ON_HIT,
            "params": {
                "status": "burn",
                "chance": 0.10,  # 10% de chance
                "duration": None,
                "overwrite": False
            },
            "description": "Pode queimar o oponente (10% de chance)"
        },
        "fire-punch": {
            "effect_type": "status_chance",
            "target": EffectTarget.TARGET,
            "timing": EffectTiming.ON_HIT,
            "params": {
                "status": "burn",
                "chance": 0.10,  # 10% de chance
                "duration": None,
                "overwrite": False
            },
            "description": "Pode queimar o oponente (10% de chance)"
        },
        # ===== CONGELAMENTO (FREEZE) =====
        "ice-beam": {
            "effect_type": "status_chance",
            "target": EffectTarget.TARGET,
            "timing": EffectTiming.ON_HIT,
            "params": {
                "status": "freeze",
                "chance": 0.10,  # 10% de chance de congelar
                "duration": None,
                "overwrite": False
            },
            "description": "Pode congelar o oponente (10% de chance)"
        },
        "blizzard": {
            "effect_type": "status_chance",
            "target": EffectTarget.TARGET,
            "timing": EffectTiming.ON_HIT,
            "params": {
                "status": "freeze",
                "chance": 0.90,
                "duration": None,
                "overwrite": False
            },
            "description": "Pode congelar o oponente (10% de chance)"
        },
        "ice-punch": {
            "effect_type": "status_chance",
            "target": EffectTarget.TARGET,
            "timing": EffectTiming.ON_HIT,
            "params": {
                "status": "freeze",
                "chance": 0.10,
                "duration": None,
                "overwrite": False
            },
            "description": "Pode congelar o oponente (10% de chance)"
        },
        "powder-snow": {
            "effect_type": "status_chance",
            "target": EffectTarget.TARGET,
            "timing": EffectTiming.ON_HIT,
            "params": {
                "status": "freeze",
                "chance": 0.10,
                "duration": None,
                "overwrite": False
            },
            "description": "Pode congelar o oponente (10% de chance)"
        },
        # Multi-hit moves
        "double-slap": {
            "effect_type": "multi_hit",
            "target": EffectTarget.TARGET,
            "timing": EffectTiming.ON_HIT,
            "params": {
                "min_hits": 2,
                "max_hits": 5
            },
            "description": "Ataque que acerta 2-5 vezes"
        },
        "fury-swipes": {
            "effect_type": "multi_hit",
            "target": EffectTarget.TARGET,
            "timing": EffectTiming.ON_HIT,
            "params": {
                "min_hits": 2,
                "max_hits": 5
            },
            "description": "Ataque que acerta 2-5 vezes"
        },
        # Flinch moves
        "bite": {
            "effect_type": "flinch",
            "target": EffectTarget.TARGET,
            "timing": EffectTiming.ON_HIT,
            "params": {
                "chance": 0.3
            },
            "description": "Pode fazer o oponente hesitar"
        },
        "headbutt": {
            "effect_type": "flinch",
            "target": EffectTarget.TARGET,
            "timing": EffectTiming.ON_HIT,
            "params": {
                "chance": 0.3
            },
            "description": "Pode fazer o oponente hesitar"
        },
        # Recoil moves
        "take-down": {
            "effect_type": "recoil",
            "target": EffectTarget.TARGET,
            "timing": EffectTiming.AFTER_DAMAGE,
            "params": {
                "percentage": 0.25
            },
            "description": "Causa dano de retorno"
        },
        "double-edge": {
            "effect_type": "recoil",
            "target": EffectTarget.TARGET,
            "timing": EffectTiming.AFTER_DAMAGE,
            "params": {
                "percentage": 0.33
            },
            "description": "Causa dano de retorno"
        },
        # Drain moves
        "mega-drain": {
            "effect_type": "drain",
            "target": EffectTarget.TARGET,
            "timing": EffectTiming.AFTER_DAMAGE,
            "params": {
                "percentage": 0.5
            },
            "description": "Cura metade do dano causado"
        },
        "giga-drain": {
            "effect_type": "drain",
            "target": EffectTarget.TARGET,
            "timing": EffectTiming.AFTER_DAMAGE,
            "params": {
                "percentage": 0.5
            },
            "description": "Cura metade do dano causado"
        },
        "leech-life": {
            "effect_type": "drain",
            "target": EffectTarget.TARGET,
            "timing": EffectTiming.AFTER_DAMAGE,
            "params": {
                "percentage": 0.5
            },
            "description": "Cura metade do dano causado"
        },

    }

    @classmethod
    def create_effect(cls, move_name: str) -> Optional[MoveEffect]:
        """Cria um efeito para um movimento"""
        # Normaliza o nome do movimento
        move_key = move_name.lower().replace(" ", "-").replace("'", "")

        config = cls.MOVE_EFFECTS.get(move_key)
        if not config:
            return None

        # Usa o novo método from_config
        return MoveEffect.from_config(move_name, config)