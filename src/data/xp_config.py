# src/data/xp_config.py

DIFFICULTY_PRESETS = {
    "facil": {
        "xp_multiplier": 1.0,       # fórmula real Pokémon
        "xp_curve_k": 2,             # xp_needed = level² × k
        "xp_curve_base": 0,
    },
    "medio": {
        "xp_multiplier": 0.7,
        "xp_curve_k": 5,
        "xp_curve_base": 0,
    },
    "dificil": {
        "xp_multiplier": 0.5,
        "xp_curve_k": 10,
        "xp_curve_base": 0,
    },
}

_current = "medio"

def get_config():
    return DIFFICULTY_PRESETS[_current]

def set_difficulty(name: str):
    global _current
    if name in DIFFICULTY_PRESETS:
        _current = name