# src/battle/effects/effect_factory.py
from typing import Dict, Any, Optional
from .move_effect import MoveEffect, EffectTarget, EffectTiming


class EffectFactory:
    """Fábrica para criar efeitos de movimento a partir de configuração"""

    # Configurações pré-definidas para moves comuns
    # src/battle/effects/effect_factory.py

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
            "min_distance": 0
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
        "amnesia": {
            "effect_type": "stat_mod",
            "target": EffectTarget.SELF,
            "timing": EffectTiming.ON_HIT,
            "params": {
                "stat": "sp_defense",
                "stages": 2,
                "duration": 6.0
            },
            "description": "Aumenta sua defesa especial em dois nivel"
        },
        "withdraw": {
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
        "barrier": {
            "effect_type": "stat_mod",
            "target": EffectTarget.SELF,
            "timing": EffectTiming.ON_HIT,
            "params": {
                "stat": "defense",
                "stages": 2,
                "duration": 6.0
            },
            "description": "Aumenta sua defesa em dois nivel"
        },
        "acid-armor": {
            "effect_type": "stat_mod",
            "target": EffectTarget.SELF,
            "timing": EffectTiming.ON_HIT,
            "params": {
                "stat": "defense",
                "stages": 2,
                "duration": 6.0
            },
            "description": "Aumenta sua defesa em dois nivel"
        },
        "growth": {
            "effect_type": "stat_mod",
            "target": EffectTarget.SELF,
            "timing": EffectTiming.ON_HIT,
            "params": {
                "stats": [
                    {"stat": "attack", "stages": 1},
                    {"stat": "sp_attack", "stages": 1}
                ],
                "duration": 6.0,
                "sun_boost": True,
            },
            "description": "Aumenta o Ataque e o Ataque Especial"
        },
        "meditate": {
            "effect_type": "stat_mod",
            "target": EffectTarget.SELF,
            "timing": EffectTiming.ON_HIT,
            "params": {
                "stats": [
                    {"stat": "attack", "stages": 1},
                ],
                "duration": 6.0,
                "sun_boost": True,
            },
            "description": "Aumenta o Ataque"
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
        "sharpen": {
            "effect_type": "stat_mod",
            "target": EffectTarget.SELF,
            "timing": EffectTiming.ON_HIT,
            "params": {
                "stat": "attack",
                "stages": 1,
                "duration": 6.0
            },
            "description": "Aumenta  o Ataque"
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
            "is_area": True,
            "params": {
                "stat": "accuracy",
                "stages": -1,
                "duration": 8.0
            },
            "description": "Reduz a Precisão do oponente",
        },
        "flash": {
            "effect_type": "stat_mod",
            "target": EffectTarget.TARGET,
            "timing": EffectTiming.ON_HIT,
            "is_area": True,
            "params": {
                "stat": "accuracy",
                "stages": -1,
                "duration": 8.0
            },
            "description": "Reduz a Precisão do oponente",
        },
        "smokescreen": {
            "effect_type": "stat_mod",
            "target": EffectTarget.TARGET,
            "timing": EffectTiming.ON_HIT,
            "is_area": True,
            "params": {
                "stat": "accuracy",
                "stages": -1,
                "duration": 8.0
            },
            "description": "Reduz a Precisão do oponente",
        },
        "double-team": {
            "effect_type": "stat_mod",
            "target": EffectTarget.SELF,
            "timing": EffectTiming.ON_HIT,
            "params": {
                "stat": "evasion",
                "stages": 1,
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
                "chance": 0.30,
                "duration": None,
                "overwrite": False
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
            "is_area": True,
            "params": {
                "status": "poison",
                "duration": None,
                "overwrite": False
            },
            "description": "Envenena o oponente",
        },
        "poison-gas": {
            "effect_type": "status",
            "target": EffectTarget.TARGET,
            "timing": EffectTiming.ON_HIT,
            "is_area": True,
            "params": {
                "status": "poison",
                "duration": None,
                "overwrite": False
            },
            "description": "Envenena o oponente",
        },
        "toxic": {
            "effect_type": "status",
            "target": EffectTarget.TARGET,
            "timing": EffectTiming.ON_HIT,
            "params": {
                "status": "toxic_poison",
                "duration": None,
                "overwrite": True
            },
            "description": "Envenena gravemente o oponente"
        },
        "smog": {
            "effect_type": "status",
            "target": EffectTarget.TARGET,
            "timing": EffectTiming.ON_HIT,
            "is_area": True,
            "params": {
                "status": "poison",
                "chance": 0.40,
                "duration": None,
                "overwrite": True
            },
            "description": "Envenena o oponente"
        },
        "sludge": {
            "effect_type": "status",
            "target": EffectTarget.TARGET,
            "timing": EffectTiming.ON_HIT,
            "params": {
                "status": "poison",
                "chance": 0.30,
                "duration": None,
                "overwrite": True
            },
            "description": "Envenena o oponente"
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
        "glare": {
            "effect_type": "status",
            "target": EffectTarget.TARGET,
            "timing": EffectTiming.ON_HIT,
            "params": {
                "status": "paralysis",
                "duration": None
            },
            "description": "Paralisa o oponente"
        },
        "thunderbolt": {
            "effect_type": "status",
            "target": EffectTarget.TARGET,
            "timing": EffectTiming.ON_HIT,
            "params": {
                "status": "paralysis",
                "chance": 0.1,
                "duration": None
            },
            "description": "Paralisa o oponente"
        },
        "thunder": {
            "effect_type": "status",
            "target": EffectTarget.TARGET,
            "timing": EffectTiming.ON_HIT,
            "params": {
                "status": "paralysis",
                "chance": 0.3,
                "duration": None
            },
            "description": "Paralisa o oponente"
        },
        "stun-spore": {
            "effect_type": "status",
            "target": EffectTarget.TARGET,
            "timing": EffectTiming.ON_HIT,
            "is_area": True,
            "params": {
                "status": "paralysis",
                "duration": None
            },
            "description": "Paralisa o oponente",
        },
        "body-slam": {
            "effect_type": "status_chance",
            "target": EffectTarget.TARGET,
            "timing": EffectTiming.ON_HIT,
            "params": {
                "status": "paralysis",
                "chance": 0.3,
                "duration": None
            },
            "description": "Pode paralisar o oponente (30% de chance)",
        },
        "lick": {
            "effect_type": "status_chance",
            "target": EffectTarget.TARGET,
            "timing": EffectTiming.ON_HIT,
            "params": {
                "status": "paralysis",
                "chance": 0.3,
                "duration": None
            },
            "description": "Pode paralisar o oponente (30% de chance)",
        },
        # ===== ADORMECER (SLEEP) =====
        "sleep-powder": {
            "effect_type": "status",
            "target": EffectTarget.TARGET,
            "timing": EffectTiming.ON_HIT,
            "is_area": True,
            "params": {
                "status": "sleep",
                "duration": None,
                "overwrite": True
            },
            "description": "Coloca o oponente para dormir",
        },
        "spore": {
            "effect_type": "status",
            "target": EffectTarget.TARGET,
            "timing": EffectTiming.ON_HIT,
            "is_area": True,
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
            "is_area": True,
            "params": {
                "status": "sleep",
                "duration": None,
                "overwrite": True
            },
            "description": "Coloca o oponente para dormir"
        },
        "lovely-kiss": {
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
                "duration": None,
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
                "chance": 0.10,
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
                "chance": 0.10,
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
                "chance": 0.10,
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
                "chance": 0.10,
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
                "chance": 0.10,
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
            "is_area": True,
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
                "duration": 8,
                "tick_interval": 2.0,
                "drain_percentage": 0.125
            },
            "description": "Planta uma semente que drena HP do oponente a cada turno"
        },
        # ===== CONFUSÕES (CONFUSION) =====
        "confuse-ray": {
            "effect_type": "confusion",
            "target": EffectTarget.TARGET,
            "timing": EffectTiming.ON_HIT,
            "params": {
                "duration": None
            },
            "description": "Causa confusão no oponente",
        },
        "supersonic": {
            "effect_type": "confusion",
            "target": EffectTarget.TARGET,
            "timing": EffectTiming.ON_HIT,
            "params": {
                "duration": None
            },
            "description": "Causa confusão no oponente com ondas sônicas",
        },
        "psybeam": {
            "effect_type": "damage_with_confusion_chance",
            "target": EffectTarget.TARGET,
            "timing": EffectTiming.AFTER_DAMAGE,
            "params": {
                "chance": 0.10
            },
            "description": "Pode causar confusão (10% de chance)"
        },
        "dizzy-punch": {
            "effect_type": "damage_with_confusion_chance",
            "target": EffectTarget.TARGET,
            "timing": EffectTiming.AFTER_DAMAGE,
            "params": {
                "chance": 0.20
            },
            "description": "Pode causar confusão (20% de chance)"
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
        # ===== ATAQUES EM ÁREA =====
        "earthquake": {
            "effect_type": "",  # Pode ser qualquer tipo, o importante é is_area=True
            "target": EffectTarget.TARGET,
            "timing": EffectTiming.ON_HIT,
            "is_area": True,  # Flag de área
            "params": {
                "area": True,
                "hit_all_in_range": True,
                "use_normal_damage": True,
            },
            "description": "Causa dano a todos os inimigos próximos."
        },

        "surf": {
            "effect_type": "stat_mod",
            "target": EffectTarget.TARGET,
            "timing": EffectTiming.ON_HIT,
            "is_area": True,
            "params": {
                "area": True,
                "hit_all_in_range": True,
                "use_normal_damage": True,
            },
            "description": "Causa dano a todos os inimigos próximos."
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
        "bonemerang": {
            "effect_type": "multi_hit",
            "target": EffectTarget.TARGET,
            "timing": EffectTiming.ON_HIT,
            "params": {
                "min_hits": 2,
                "max_hits": 2
            },
            "description": "Ataque que acerta 2 vezes"
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
        "barrage": {
            "effect_type": "multi_hit",
            "target": EffectTarget.TARGET,
            "timing": EffectTiming.ON_HIT,
            "params": {
                "min_hits": 2,
                "max_hits": 5
            },
            "description": "Ataque que acerta 2-5 vezes"
        },
        "spike-cannon": {
            "effect_type": "multi_hit",
            "target": EffectTarget.TARGET,
            "timing": EffectTiming.ON_HIT,
            "params": {
                "min_hits": 2,
                "max_hits": 5
            },
            "description": "Dispara espinhos que acertam 2-5 vezes"
        },
        # ===== GOLPES DE 2 TURNOS =====
        "sky-attack": {
            "effect_type": "two_turn_attack",
            "target": EffectTarget.TARGET,
            "timing": EffectTiming.ON_HIT,
            "params": {
                "charge_turn": True,
                "high_crit": True,
                "flinch_chance": 0.30,
            },
            "charge_message": "O céu escurece... {pokemon} está brilhando intensamente!",
            "description": "1st turn: Prepare 2nd turn: Attack. High crit ratio. May cause flinching."
        },
        "skull-bash": {
            "effect_type": "two_turn_attack",
            "target": EffectTarget.TARGET,
            "timing": EffectTiming.ON_HIT,
            "params": {
                "charge_turn": True,
                "defense_boost": 1,
            },
            "charge_message": "{pokemon} baixou a cabeça e está concentrando força!",
            "description": "1st turn: Raise Defense. 2nd turn: Attack."
        },
        "solar-beam": {
            "effect_type": "two_turn_attack",
            "target": EffectTarget.TARGET,
            "timing": EffectTiming.ON_HIT,
            "params": {
                "charge_turn": True,
                "sun_skip": True,
            },
            "charge_message": "{pokemon} está absorvendo luz solar!",
            "description": "1st turn: Prepare 2nd turn: Attack. Skips charge turn in sunlight."
        },
        "razor-wind": {
            "effect_type": "two_turn_attack",
            "target": EffectTarget.TARGET,
            "timing": EffectTiming.ON_HIT,
            "params": {
                "charge_turn": True,
                "high_crit": True,
            },
            "charge_message": "Ventos fortes se formam ao redor de {pokemon}!",
            "description": "1st turn: Prepare 2nd turn: Attack. High crit ratio."
        },
        "dig": {
            "effect_type": "two_turn_attack",
            "target": EffectTarget.TARGET,
            "timing": EffectTiming.ON_HIT,
            "params": {
                "charge_turn": True,
                "high_crit": True,
            },
            "charge_message": "{pokemon} está cavando um buraco!",
            "description": "1st turn: Prepare 2nd turn: Attack. High crit ratio."
        },
        "fly": {
            "effect_type": "two_turn_attack",
            "target": EffectTarget.TARGET,
            "timing": EffectTiming.ON_HIT,
            "params": {
                "charge_turn": True,
                "high_crit": True,
            },
            "charge_message": "{pokemon} está se preparando para voar!",
            "description": "1st turn: Prepare 2nd turn: Attack. High crit ratio."
        },
        "hyper-beam": {
            "effect_type": "two_turn_attack",
            "target": EffectTarget.TARGET,
            "timing": EffectTiming.ON_HIT,
            "params": {
                "charge_turn": True,
                "high_crit": True,
            },
            "charge_message": "{pokemon} está descansando...",
            "description": "1st turn: Prepare 2nd turn: Attack. High crit ratio."
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
        "rock-slide": {
            "effect_type": "flinch",
            "target": EffectTarget.TARGET,
            "timing": EffectTiming.ON_HIT,
            "is_area": True,
            "params": {
                "chance": 0.3
            },
            "description": "Pode fazer o oponente hesitar"
        },
        "hyper-fang": {
            "effect_type": "flinch",
            "target": EffectTarget.TARGET,
            "timing": EffectTiming.ON_HIT,
            "params": {
                "chance": 0.1
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
        "waterfall": {
            "effect_type": "flinch",
            "target": EffectTarget.TARGET,
            "timing": EffectTiming.ON_HIT,
            "params": {
                "chance": 0.2
            },
            "description": "Pode fazer o oponente hesitar"
        },
        "bone-club": {
            "effect_type": "flinch",
            "target": EffectTarget.TARGET,
            "timing": EffectTiming.ON_HIT,
            "params": {
                "chance": 0.1
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
        "struggle": {
            "effect_type": "struggle",  # Tipo especial para Struggle
            "target": EffectTarget.TARGET,
            "timing": EffectTiming.ON_HIT,
            "params": {
                "recoil_percentage": 0.25,  # 25% do HP máximo de recoil
                "ignore_accuracy": True,  # Sempre acerta (accuracy null)
                "ignore_immunity": True,  # Typeless - não tem imunidade
            },
            "description": "Usado quando todos os PP acabam. Causa dano e dano de retorno."
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
            "effect_type": "high_crit",
            "target": EffectTarget.TARGET,
            "timing": EffectTiming.ON_HIT,
            "params": {
                "crit_stage": 1
            },
            "description": "Alta taxa de acerto crítico"
        },
        "crabhammer": {
            "effect_type": "high_crit",
            "target": EffectTarget.TARGET,
            "timing": EffectTiming.ON_HIT,
            "params": {
                "crit_stage": 1
            },
            "description": "Alta taxa de acerto crítico"
        },
        "razor-leaf": {
            "effect_type": "high_crit",
            "target": EffectTarget.TARGET,
            "timing": EffectTiming.ON_HIT,
            "params": {
                "crit_stage": 1
            },
            "description": "Alta taxa de acerto crítico"
        },
        "slash": {
            "effect_type": "high_crit",
            "target": EffectTarget.TARGET,
            "timing": EffectTiming.ON_HIT,
            "params": {
                "crit_stage": 1
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
            "description": "Causa dano e tem chance de 10% de reduzir a Defesa Especial do oponente"
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
            "description": "Causa dano e tem chance de 10% de reduzir a Velocidade do oponente"
        },
        "bubble": {
            "effect_type": "stat_mod",
            "target": EffectTarget.TARGET,
            "timing": EffectTiming.ON_HIT,
            "params": {
                "stat": "speed",
                "stages": -1,
                "chance": 0.1,
                "duration": 4.0
            },
            "description": "Causa dano e tem chance de 10% de reduzir a Velocidade do oponente"
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
            "description": "Causa dano e tem chance de 10% de reduzir o Ataque do oponente"
        },
        # ===== FORÇAR MOVIMENTAÇÃO =====
        "roar": {
            "effect_type": "force_switch",
            "target": EffectTarget.TARGET,
            "timing": EffectTiming.ON_HIT,
            "is_area": True,
            "params": {
                "force_wild_flee": True,
                "force_ally_return": True,
                "bypass_protect": True,
            },
            "description": "Força o oponente a fugir ou ser substituído"
        },
        "whirlwind": {
            "effect_type": "force_switch",
            "target": EffectTarget.TARGET,
            "timing": EffectTiming.ON_HIT,
            "params": {
                "force_wild_flee": True,
                "force_ally_return": True,
                "bypass_protect": False,
            },
            "description": "Força o oponente a fugir ou ser substituído"
        },
        # ===== MOVIMENTOS ESPECÍFICOS =====
        "focus-energy": {
            "effect_type": "critical_stage_mod",  # Modifica estágio de crítico
            "target": EffectTarget.SELF,
            "timing": EffectTiming.ON_HIT,
            "params": {
                "stage_increase": 2,  # Aumenta 2 estágios
                "max_stage": 4,  # Máximo +4 estágios (50% de chance)
                "stackable": False,  # Não pode acumular com outro Focus Energy
            },
            "description": "Aumenta muito a taxa de acerto crítico"
        },
        "dream-eater": {
            "effect_type": "dream_eater",  # Tipo especial para Dream Eater
            "target": EffectTarget.TARGET,
            "timing": EffectTiming.AFTER_DAMAGE,
            "params": {
                "drain_percentage": 0.5,  # Cura 50% do dano causado
                "requires_sleep": True,  # Só funciona se alvo estiver dormindo
            },
            "description": "Só funciona em Pokémon dormindo. Cura metade do dano causado"
        },
        "swift": {
            "effect_type": "never_miss",  # Tipo: nunca erra
            "target": EffectTarget.TARGET,
            "timing": EffectTiming.ON_HIT,
            "is_area": True,
            "params": {
                "never_miss": True,
            },
            "description": "Ataque que nunca erra"
        },
        "minimize": {
            "effect_type": "stat_mod_with_visual",
            "target": EffectTarget.SELF,
            "timing": EffectTiming.ON_HIT,
            "params": {
                "stats": [
                    {"stat": "evasion", "stages": 2}
                ],
                "duration": 8.0,  # 8 segundos (ajuste conforme necessidade)
                "visual_effect": "minimize",  # Efeito visual de diminuir tamanho
                "sprite_scale": 0.70,  # Metade do tamanho
            },
            "description": "Aumenta muito a Evasão e diminui o tamanho do Pokémon"
        },
        "haze": {
            "effect_type": "remove_all_stat_mods",  # Remove todos os modificadores de stat
            "target": EffectTarget.BOTH,  # Afeta todos os Pokémon em campo
            "timing": EffectTiming.ON_HIT,
            "is_area": True,
            "params": {
                "clear_all": True,  # Limpa todos os modificadores
                "affects_user": True,  # Afeta também o usuário
                "affects_target": True,  # Afeta também o alvo
            },
            "description": "Remove todos os modificadores de stat de todos os Pokémon em campo"
        },
        "rage": {
            "effect_type": "rage_mode",
            "target": EffectTarget.SELF,
            "timing": EffectTiming.ON_HIT,
            "params": {
                "stat": "attack",
                "stages_per_hit": 1,
                "max_stages": 6,
                "duration": None,  # Até o próximo ataque
            },
            "description": "A cada vez que o usuário é atingido, seu Ataque aumenta",
        },
        "teleport": {
            "effect_type": "teleport_swap",
            "target": EffectTarget.SELF,
            "timing": EffectTiming.ON_HIT,
            "params": {
                "swap_chance": 0.20,  # 20% de chance de trocar com aliado
            },
            "description": "Teleporta para um spot livre aleatório. Pode trocar de lugar com um aliado (20%)"
        },
        "tri-attack": {
            "effect_type": "random_status_chance",
            "target": EffectTarget.TARGET,
            "timing": EffectTiming.AFTER_DAMAGE,
            "params": {
                "chance": 0.20,  # 20% de chance total
                "possible_status": ["burn", "freeze", "paralysis"],
                # Pesos iguais para cada status (1/3 cada quando ativa)
                "weights": [1, 1, 1],
                "overwrite": False,
            },
            "description": "20% de chance de queimar, congelar ou paralisar o oponente"
        },
        # ===== CURA (HEAL) =====
        "recover": {
            "effect_type": "heal",
            "target": EffectTarget.SELF,
            "timing": EffectTiming.ON_HIT,
            "params": {
                "heal_percentage": 0.5,
                "heal_formula": "max_hp_percentage",
            },
            "description": "Recupera metade do HP máximo do usuário"
        },
        "soft-boiled": {
            "effect_type": "heal",
            "target": EffectTarget.SELF,
            "timing": EffectTiming.ON_HIT,
            "params": {
                "heal_percentage": 0.5,
                "heal_formula": "max_hp_percentage",
            },
            "description": "Recupera metade do HP máximo do usuário"
        },
        # ===== AUTODESTRUIÇÃO =====
        "explosion": {
            "effect_type": "self_faint",  # Tipo: usuário desmaia
            "target": EffectTarget.TARGET,
            "timing": EffectTiming.AFTER_DAMAGE,  # Após causar dano
            "is_area": True,
            "params": {
                "self_faint": True,
            },
            "description": "Causa dano massivo, mas o usuário desmaia"
        },
        "self-destruct": {
            "effect_type": "self_faint",
            "target": EffectTarget.TARGET,
            "timing": EffectTiming.AFTER_DAMAGE,
            "params": {
                "self_faint": True,
            },
            "description": "Causa muito dano, mas o usuário desmaia"
        },

        "super-fang": {
            "effect_type": "percent_damage",  # Dano baseado em porcentagem
            "target": EffectTarget.TARGET,
            "timing": EffectTiming.ON_HIT,
            "params": {
                "damage_percentage": 0.5,  # 50% do HP atual
                "damage_formula": "current_hp_percentage",  # Baseado no HP atual
                "min_damage": 1,  # Dano mínimo de 1
                "ignore_type_immunity": True,  # Normal não afeta Ghost, mas vamos ignorar
                "ignore_effectiveness": True,  # Typeless, sem resistências
            },
            "description": "Corta metade do HP restante do oponente"
        },
        "seismic-toss": {
            "effect_type": "level_damage",
            "target": EffectTarget.TARGET,
            "timing": EffectTiming.ON_HIT,
            "params": {
                "damage_formula": "level",
                "ignore_type_effectiveness": True,
            },
            "description": "Causa dano igual ao nível do usuário"
        },
        "psywave": {
            "effect_type": "variable_level_damage",
            "target": EffectTarget.TARGET,
            "timing": EffectTiming.ON_HIT,
            "params": {
                "damage_formula": "level_percentage",
                "min_percentage": 0.5,  # 50%
                "max_percentage": 1.5,  # 150%
                "increment": 0.1,  # Incrementos de 10%
                "ignore_type_immunity": False,  # Dark é imune a Psychic
                "ignore_effectiveness": True,  # Sem resistências
                "is_typeless": True,
            },
            "description": "Causa dano typeless entre 50% e 150% do nível do usuário"
        },
        "night-shade": {
            "effect_type": "level_damage",  # Mesmo tipo do Seismic Toss
            "target": EffectTarget.TARGET,
            "timing": EffectTiming.ON_HIT,
            "params": {
                "damage_formula": "level",  # level do atacante = dano
                "ignore_type_effectiveness": True,  # Ignora resistências, mas verifica imunidade
            },
            "description": "Causa dano igual ao nível do usuário"
        },
        "constrict": {
            "effect_type": "stat_mod",
            "target": EffectTarget.TARGET,
            "timing": EffectTiming.ON_HIT,  # Ou AFTER_DAMAGE, tanto faz
            "params": {
                "stat": "speed",
                "stages": -1,
                "chance": 0.10,
                "duration": 4.0
            },
            "description": "Causa dano e tem 10% de chance de reduzir a Velocidade do oponente"
        },
        "kinesis": {
            "effect_type": "stat_mod",
            "target": EffectTarget.TARGET,
            "timing": EffectTiming.AFTER_DAMAGE,
            "params": {
                "stat": "accuracy",
                "stages": -1,
                "duration": 6.0
            },
            "description": "Causa dano e reduz a precisão do oponente"
        },
        # ===== HITKILL =====
        "horn-drill": {
            "effect_type": "ohko",
            "target": EffectTarget.TARGET,
            "timing": EffectTiming.ON_HIT,
            "params": {
                "base_accuracy": 30,
                "level_difference_bonus": 1,
                "max_accuracy": 100,
            },
            "description": "Golpe que pode derrubar o oponente com um só golpe"
        },
        "fissure": {
            "effect_type": "ohko",
            "target": EffectTarget.TARGET,
            "timing": EffectTiming.ON_HIT,
            "params": {
                "base_accuracy": 30,
                "level_difference_bonus": 0,
                "max_accuracy": 100,
            },
            "description": "Golpe que pode derrubar o oponente com um só golpe"
        },
        "guillotine": {
            "effect_type": "ohko",
            "target": EffectTarget.TARGET,
            "timing": EffectTiming.ON_HIT,
            "params": {
                "base_accuracy": 30,
                "level_difference_bonus": 0,
                "max_accuracy": 100,
            },
            "description": "Golpe que pode derrubar o oponente com um só golpe"
        },

        # ===== DANOS FIXOS =====
        "sonic-boom": {
            "effect_type": "fixed_damage",
            "target": EffectTarget.TARGET,
            "timing": EffectTiming.ON_HIT,
            "params": {
                "fixed_damage": 20,
            },
            "description": "Sempre causa 20 de dano"
        },
        "dragon-rage": {
            "effect_type": "fixed_damage",
            "target": EffectTarget.TARGET,
            "timing": EffectTiming.ON_HIT,
            "params": {
                "fixed_damage": 40,
            },
            "description": "Sempre causa 40 de dano"
        },
        # ===== DANO NO ATACANTE SE ERRAR =====
        "jump-kick": {
            "effect_type": "crash_damage_on_miss",
            "target": EffectTarget.TARGET,
            "timing": EffectTiming.ON_HIT,
            "params": {
                "crash_damage_percentage": 0.5,
                "crash_damage_formula": "max_hp_percentage",
            },
            "description": "Se errar, o usuário se machuca perdendo metade do HP máximo"
        },
        "high-jump-kick": {
            "effect_type": "crash_damage_on_miss",
            "target": EffectTarget.TARGET,
            "timing": EffectTiming.ON_HIT,
            "params": {
                "crash_damage_percentage": 0.5,
                "crash_damage_formula": "max_hp_percentage",
            },
            "description": "Se errar, o usuário se machuca perdendo metade do HP máximo"
        },

        "light-screen": {
            "effect_type": "light_screen",
            "target": EffectTarget.SELF,
            "timing": EffectTiming.ON_HIT,
            "params": {
                "turns": 5,  # 5 turns
                "damage_reduction": 0.5,  # 50% reduction
                "affected_attacks": ["special"],
            },
            "description": "Erects a barrier that reduces special attack damage for 5 turns."
        },
        "reflect": {
            "effect_type": "reflect",
            "target": EffectTarget.SELF,
            "timing": EffectTiming.ON_HIT,
            "params": {
                "turns": 5,
                "damage_reduction": 0.5,
                "affected_attacks": ["physical"],
            },
            "description": "Erects a barrier that reduces physical attack damage for 5 turns."
        },

        "counter": {
            "effect_type": "counter",
            "target": EffectTarget.SELF,
            "timing": EffectTiming.ON_HIT,
            "params": {
                "multiplier": 2.0,
            },
            "description": "Returns double the physical damage received."
        },
        "bide": {
            "effect_type": "counter",
            "target": EffectTarget.SELF,
            "timing": EffectTiming.ON_HIT,
            "params": {
                "multiplier": 1.5,
            },
            "description": "Returns double the physical damage received."
        },

        "thrash": {
            "effect_type": "self_confusion_after_uses",
            "target": EffectTarget.TARGET,
            "timing": EffectTiming.AFTER_DAMAGE,
            "params": {
                "required_uses": 2,
                "reset_on_switch": True,  # Reseta se trocar de golpe
            },
            "description": "After 3 uses, user becomes confused."
        },
        "petal-dance": {
            "effect_type": "self_confusion_after_uses",
            "target": EffectTarget.TARGET,
            "timing": EffectTiming.AFTER_DAMAGE,
            "params": {
                "required_uses": 2,
                "reset_on_switch": True,
            },
            "description": "After 3 uses, user becomes confused."
        },

        "mist": {
            "effect_type": "mist",
            "target": EffectTarget.SELF,
            "timing": EffectTiming.ON_HIT,
            "is_area": True,  # Afeta todos aliados em área
            "params": {
                "clear_negative_stats": True,  # Limpa debuffs
            },
            "description": "Removes all stat reductions from allies in range."
        },
        "disable": {
            "effect_type": "disable",
            "target": EffectTarget.TARGET,
            "timing": EffectTiming.ON_HIT,
            "params": {
                "duration": 4,  # 4-7 turns, vamos usar 4 por simplicidade
                "disable_last_move": True,
            },
            "description": "Disables the target's last used move."
        },

        "pay-day": {
            "effect_type": "pay_day",
            "target": EffectTarget.TARGET,
            "timing": EffectTiming.AFTER_DAMAGE,
            "params": {
                "gold_multiplier": 2.0,  # Dobra o gold
                "xp_multiplier": 1.5,  # Aumenta XP em 50%
            },
            "description": "Doubles gold and increases XP from defeated Pokémon."
        },

        "transform": {
            "effect_type": "transform",
            "target": EffectTarget.SELF,
            "timing": EffectTiming.ON_HIT,
            "params": {
                "copy_stats": True,
                "copy_moves": True,
                "copy_sprite": True,
                "copy_types": True,
                "copy_abilities": False,
            },
            "description": "O usuário se transforma no oponente, copiando sua aparência, moves e stats."
        },
        "metronome": {
            "effect_type": "metronome",
            "target": EffectTarget.SELF,
            "timing": EffectTiming.ON_HIT,
            "params": {
                "random_move": True,
                "exclude_moves": ["metronome", "mimic", "struggle", "transform", "counter", "mirror-coat", "protect",
                                  "detect", "endure"]
            },
            "description": "Randomly uses any Pokémon move."
        },

        "mimic": {
            "effect_type": "mimic",
            "target": EffectTarget.SELF,
            "timing": EffectTiming.ON_HIT,
            "params": {
                "copy_last_move": True,
                "pp_on_copy": 5
            },
            "description": "Copies a move used by the foe."
        }
    }

    @classmethod
    def create_effect(cls, move_name: str) -> Optional[MoveEffect]:
        """Cria um efeito para um movimento"""
        # Normaliza o nome do movimento
        move_key = move_name.lower().replace(" ", "-").replace("'", "")

        config = cls.MOVE_EFFECTS.get(move_key)
        if not config:
            return None

        # Usa o método from_config
        return MoveEffect.from_config(move_name, config)