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
                "duration": 6.0
            },
            "description": "Reduz o Ataque do oponente"
        },
        "tail-whip": {
            "effect_type": "stat_mod",
            "target": EffectTarget.TARGET,
            "timing": EffectTiming.ON_HIT,
            "params": {
                "stat": "defense",
                "stages": -1,
                "duration": 6.0
            },
            "description": "Reduz a defesa do oponente"
        },
        "leer": {
            "effect_type": "stat_mod",
            "target": EffectTarget.TARGET,
            "timing": EffectTiming.ON_HIT,
            "params": {
                "stat": "defense",
                "stages": -1,
                "duration": 6.0
            },
            "description": "Reduz a defesa do oponente"
        },

        "defense-curl": {
            "effect_type": "stat_mod",
            "target": EffectTarget.SELF,
            "timing": EffectTiming.ON_HIT,
            "params": {
                "stat": "defense",
                "stages": 1,
                "duration": 6.0
            },
            "description": "Aumenta sua defesa em 1 ponto."
        },
        "screech": {
            "effect_type": "stat_mod",
            "target": EffectTarget.TARGET,
            "timing": EffectTiming.ON_HIT,
            "params": {
                "stat": "defense",
                "stages": -2,
                "duration": 6.0
            },
            "description": "Diminui defesa do inimigo em 2 pontos."
        },
        "harden": {
            "effect_type": "stat_mod",
            "target": EffectTarget.SELF,
            "timing": EffectTiming.ON_HIT,
            "params": {
                "stat": "defense",
                "stages": 1,
                "duration": 6.0
            },
            "description": "Aumenta sua defesa em um nivel"
        },
        "growth": {
            "effect_type": "stat_mod",
            "target": EffectTarget.SELF,
            "timing": EffectTiming.ON_HIT,
            "params": {
                "stat": "sp_attack",
                "stages": 1,
                "duration": 6.0
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
                "duration": 4.0
            },
            "description": "Aumenta muito a Velocidade"
        },
        "sand-attack": {
            "effect_type": "stat_mod",
            "target": EffectTarget.TARGET,
            "timing": EffectTiming.ON_HIT,
            "params": {
                "stat": "accuracy",
                "stages": -1,
                "duration": 8.0
            },
            "description": "Reduz a Precisão do oponente",
            "attacker_animation": "shoot",
        },
        "double-team": {
            "effect_type": "stat_mod",
            "target": EffectTarget.SELF,  # Aplica no próprio usuário
            "timing": EffectTiming.ON_HIT,
            "params": {
                "stat": "evasion",
                "stages": 1,  # Aumenta evasão em 1 estágio
                "duration": 8.0
            },
            "description": "Aumenta a Evasão do usuário",
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
        "twineedle": {
            "effect_type": "status_chance",
            "target": EffectTarget.TARGET,
            "timing": EffectTiming.ON_HIT,
            "params": {
                "status": "poison",
                "chance": 0.20,
                "duration": None,
                "overwrite": False
            },
            "description": "Pode envenenar o oponente (20% de chance)"
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
        },
        "body-slam": {
            "effect_type": "status",
            "target": EffectTarget.TARGET,
            "timing": EffectTiming.ON_HIT,
            "params": {
                "status": "paralysis",
                "chance": 0.3,
                "duration": None

            },
            "description": "Paralisa o oponente",
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
        "sing": {
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
        # ===== RESIDUAIS (TURN) =====
        "leech-seed": {
            "effect_type": "residual",
            "target": EffectTarget.TARGET,
            "timing": EffectTiming.ON_HIT,
            "params": {
                "residual_type": "leech_seed",
                "duration": 8,  # 8 turnos
                "tick_interval": 2.0,
                "drain_percentage": 0.125  # 1/8 do HP máximo por tick
            },
            "description": "Planta uma semente que drena HP do oponente a cada turno"
        },
        # ===== CONFUSÕES (CONFUSION) =====
        "confuse-ray": {
            "effect_type": "confusion",
            "target": EffectTarget.TARGET,
            "timing": EffectTiming.ON_HIT,
            "params": {
                "duration": None  # Aleatório 1-4 turnos
            },
            "description": "Causa confusão no oponente",
            "attacker_animation": "shoot"
        },
        "supersonic": {
            "effect_type": "confusion",
            "target": EffectTarget.TARGET,
            "timing": EffectTiming.ON_HIT,
            "params": {
                "duration": None
            },
            "description": "Causa confusão no oponente com ondas sônicas",
            "attacker_animation": "shoot"
        },
        "psybeam": {
            "effect_type": "damage_with_confusion_chance",
            "target": EffectTarget.TARGET,
            "timing": EffectTiming.AFTER_DAMAGE,
            "params": {
                "chance": 0.10  # 10% de chance de confundir
            },
            "description": "Pode causar confusão (10% de chance)"
        },
        "confusion": {
            "effect_type": "damage_with_confusion_chance",
            "target": EffectTarget.TARGET,
            "timing": EffectTiming.AFTER_DAMAGE,
            "params": {
                "chance": 0.10
            },
            "description": "Pode causar confusão (10% de chance)"
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
        "comet-punch": {
            "effect_type": "multi_hit",
            "target": EffectTarget.TARGET,
            "timing": EffectTiming.ON_HIT,
            "params": {
                "min_hits": 2,
                "max_hits": 5
            },
            "description": "Ataque que acerta 2-5 vezes"
        },
        "fury-attack": {
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
        "pin-missile": {
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
        "stomp": {
            "effect_type": "flinch",
            "target": EffectTarget.TARGET,
            "timing": EffectTiming.ON_HIT,
            "params": {
                "chance": 0.3
            },
            "description": "Pode fazer o oponente hesitar"
        },
        "rolling-kick": {
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
        "submission": {
            "effect_type": "recoil",
            "target": EffectTarget.TARGET,
            "timing": EffectTiming.AFTER_DAMAGE,
            "params": {
                "percentage": 0.25
            },
            "description": "Causa dano de retorno"
        },

        # ===== DRENAGEM DE VIDA (DRAIN) =====
        "absorb": {
            "effect_type": "drain",
            "target": EffectTarget.TARGET,
            "timing": EffectTiming.AFTER_DAMAGE,
            "params": {
                "percentage": 0.5
            },
            "description": "Cura metade do dano causado"
        },
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
        # ===== DANOS COM EFEITOS DE STATS =====
        "karate-chop": {
            "effect_type": "high_crit",  # Novo tipo de efeito
            "target": EffectTarget.TARGET,
            "timing": EffectTiming.ON_HIT,
            "params": {
                "crit_stage": 1  # Aumenta estágio de crítico em 1
            },
            "description": "Alta taxa de acerto crítico"
        },
        "acid": {
            "effect_type": "stat_mod",
            "target": EffectTarget.TARGET,
            "timing": EffectTiming.ON_HIT,
            "params": {
                "stat": "sp_defense",
                "stages": -1,
                "chance": 0.1,
                "duration": 6.0
            },
            "description": "Causa dano e tem chance de 10% de Reduzir a defesa do oponente"
        },
        "bubble-beam": {
            "effect_type": "stat_mod",
            "target": EffectTarget.TARGET,
            "timing": EffectTiming.ON_HIT,
            "params": {
                "stat": "speed",
                "stages": -1,
                "chance": 0.1,
                "duration": 4.0
            },
            "description": "Causa dano e tem chance de 10% de Reduzir a defesa do oponente"
        },
        "aurora-beam": {
            "effect_type": "stat_mod",
            "target": EffectTarget.TARGET,
            "timing": EffectTiming.ON_HIT,
            "params": {
                "stat": "attack",
                "stages": -1,
                "chance": 0.1,
                "duration": 6.0
            },
            "description": "Causa dano e tem chance de 10% de Reduzir a defesa do oponente"
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