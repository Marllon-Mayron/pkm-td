"""Carrega/salva animações em res/animations/."""
import json
from pathlib import Path

from src.config.paths import RES_PATH
from src.anim.animation import AnimDefinition
from src.anim.animation_registry import animation_registry


ANIM_ROOT = RES_PATH / "animations"


# =====================================================================
def list_categories() -> list:
    return ["items", "effects", "moves", "weather", "ui", "cutscene"]


def list_animations(category: str) -> list:
    d = ANIM_ROOT / category
    if not d.exists():
        return []
    return sorted(p.stem for p in d.glob("*.json"))


def list_all_animations() -> list:
    out = []
    for cat in list_categories():
        for name in list_animations(cat):
            out.append((cat, name))
    return out


def list_shared_sprites() -> list:
    out = []
    for folder in ("_shared", "_assets"):
        d = ANIM_ROOT / folder
        if not d.exists():
            continue
        for ext in ("*.png", "*.jpg", "*.bmp"):
            for p in d.glob(ext):
                out.append(f"{folder}/{p.name}")
    return sorted(out)


def list_backgrounds() -> list:
    """Imagens candidatas a background (de res/animations/_backgrounds/)."""
    out = []
    d = ANIM_ROOT / "_backgrounds"
    if not d.exists():
        d.mkdir(parents=True, exist_ok=True)
        return []
    for ext in ("*.png", "*.jpg", "*.jpeg", "*.bmp"):
        for p in d.glob(ext):
            out.append(f"_backgrounds/{p.name}")
    return sorted(out)


# =====================================================================
def load_animation(category: str, name: str) -> AnimDefinition:
    return AnimDefinition.from_json(ANIM_ROOT / category / f"{name}.json")


def save_animation(defn: AnimDefinition):
    path = ANIM_ROOT / defn.category / f"{defn.name}.json"
    defn.save(path)
    animation_registry.reload()


# =====================================================================
def list_pokemon() -> list:
    try:
        from src.data.pokedex import Pokedex
        pokedex = Pokedex()
        out = []
        for pid in sorted(pokedex.pokemon_data.keys()):
            out.append({"id": pid, "name": pokedex.get_name(pid)})
        return out
    except Exception as e:
        print(f"[SCENE_LOADER] erro list_pokemon: {e}")
        return []


def list_pokemon_animations(pid: int, shiny: bool = False) -> list:
    try:
        from src.data.pokedex import Pokedex
        pokedex = Pokedex()
        info = pokedex.get_pokemon_animations_info(pid, shiny)
        anims = info.get("available_animations", []) or []
        return sorted(set(str(a) for a in anims))
    except Exception as e:
        print(f"[SCENE_LOADER] erro list_pokemon_animations: {e}")
        return []


def list_pokemon_directions(pid: int, anim: str, shiny: bool = False) -> list:
    try:
        from src.data.pokedex import Pokedex
        pokedex = Pokedex()
        dirs = pokedex.get_animation_directions(pid, anim, shiny)
        return [d for d in dirs if not str(d).startswith("_")]
    except Exception as e:
        print(f"[SCENE_LOADER] erro list_pokemon_directions: {e}")
        return []


def get_pokemon_frames(pid: int, anim: str, direction: str,
                       shiny: bool = False) -> list:
    try:
        from src.data.pokedex import Pokedex
        pokedex = Pokedex()
        return pokedex.get_animation_frames(pid, anim, direction, shiny) or []
    except Exception as e:
        print(f"[SCENE_LOADER] erro get_pokemon_frames: {e}")
        return []


def get_pokemon_durations(pid: int, anim: str, shiny: bool = False) -> list:
    try:
        from src.data.pokedex import Pokedex
        pokedex = Pokedex()
        return pokedex.get_animation_durations(pid, anim, shiny) or []
    except Exception as e:
        return []


def get_pokemon_portrait(pid: int, size=(40, 40), shiny: bool = False):
    try:
        import pygame
        from src.data.pokedex import Pokedex
        pokedex = Pokedex()
        portrait = pokedex.get_portrait(pid, "normal", shiny)
        if portrait is None:
            portrait = pokedex.get_sprite(pid, "front", shiny)
        if portrait is None:
            return None
        if portrait.get_size() != size:
            portrait = pygame.transform.smoothscale(portrait, size)
        return portrait
    except Exception as e:
        return None


# =====================================================================
def list_items() -> list:
    try:
        from src.data.item_bag_catalog import item_bag_catalog
        out = []
        for item_id, data in item_bag_catalog.items.items():
            out.append({
                "id": item_id,
                "name": data.get("name", item_id),
                "category": data.get("category", "items"),
            })
        out.sort(key=lambda x: (x["category"], x["name"].lower()))
        return out
    except Exception as e:
        return []


def get_item_sprite(item_id: str, scaled=True):
    try:
        from src.data.item_bag_catalog import item_bag_catalog
        return item_bag_catalog.get_sprite(item_id, scaled=scaled)
    except Exception:
        return None


# =====================================================================
def make_item_uri(item_id: str) -> str:
    return f"item://{item_id}"


def make_pokemon_uri(pid: int, anim: str, direction: str,
                     frame_idx: int, shiny: bool = False) -> str:
    s = "true" if shiny else "false"
    return f"pokemon://{pid}/{anim}/{direction}/{frame_idx}/{s}"


# =====================================================================
def list_triggers() -> list:
    triggers = set()
    try:
        from src.data.item_bag_catalog import item_bag_catalog
        for item_id in item_bag_catalog.items.keys():
            triggers.add(f"item.{item_id}.use_on_ally")
            triggers.add(f"item.{item_id}.use_on_enemy")
            triggers.add(f"item.{item_id}.use_on_self")
    except Exception:
        pass
    for t in ("poison", "toxic_poison", "burn", "paralysis",
              "sleep", "freeze", "confusion"):
        triggers.add(f"effect.{t}.apply")
        triggers.add(f"effect.{t}.tick")
        triggers.add(f"effect.{t}.remove")
    for w in ("rain", "sunny", "sandstorm", "hail"):
        triggers.add(f"weather.{w}.enter")
        triggers.add(f"weather.{w}.leave")
    for p in ("shiny.enter", "evolve.start", "evolve.end", "level_up",
              "faint", "capture.start", "capture.success"):
        triggers.add(f"pokemon.{p}")
    for u in ("button.hover", "button.click", "notification.enter",
              "notification.leave", "menu.open", "menu.close"):
        triggers.add(f"ui.{u}")
    return sorted(triggers)


def load_bindings() -> dict:
    path = ANIM_ROOT / "bindings.json"
    if not path.exists():
        return {"schema_version": 1, "bindings": {}}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        return {"schema_version": 1, "bindings": {}}


def save_bindings(data: dict):
    path = ANIM_ROOT / "bindings.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"[SCENE_LOADER] bindings salvos: {path}")