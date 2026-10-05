# src/ui/sound_helper.py
"""
Helper para tocar sons de UI por nome.

Regras:
  - Se o nome bater com um membro de SoundEffect (ex: "CLICK", "SHINY"),
    toca via sound_manager.play_effect.
  - Senão, procura no dicionário de sons carregados (play_sound).
  - "NONE" / "" / None não toca nada.
"""
from src.managers.sounds.sound_manager import sound_manager, SoundEffect


_ENUM_LOOKUP = {e.name: e for e in SoundEffect}


def play_ui_sound(name, volume=None):
    if not name:
        return False
    key = str(name).strip()
    if not key or key.upper() in ("NONE", "(NENHUM)", "(NONE)", "-"):
        return False
    upper = key.upper()
    if upper in _ENUM_LOOKUP:
        return sound_manager.play_effect(_ENUM_LOOKUP[upper], volume=volume)
    return sound_manager.play_sound(key, volume=volume)


def available_sound_names():
    """Lista de nomes para o editor (enum + custom carregados)."""
    names = ["(nenhum)"] + [e.name for e in SoundEffect]
    try:
        for k in sorted(sound_manager._sounds.keys()):
            names.append(k)
    except Exception:
        pass
    # Únicos preservando ordem
    seen, out = set(), []
    for n in names:
        if n not in seen:
            seen.add(n)
            out.append(n)
    return out