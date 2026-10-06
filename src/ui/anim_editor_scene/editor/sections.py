"""Constantes e opções de campo do editor."""

ANCHORS = ["target", "attacker", "projectile", "world", "screen", "mouse"]
SPACES = ["world", "screen"]
CATEGORIES = ["items", "effects", "moves", "weather", "ui", "cutscene"]
BLENDS = ["normal", "add", "mult", "screen"]
PIVOTS = ["center", "top_left", "top_center", "top_right",
          "bottom_left", "bottom_center", "bottom_right"]
SOURCES = ["sfx", "move", "ambient"]
LAYER_TYPES = ["sprite", "emitter", "filter"]
AGENT_MODES = ["mock", "pokemon", "item", "sprite"]
BG_TYPES = ["none", "color", "image"]
BG_MODES = ["stretch", "contain", "cover", "tile"]

EASINGS = [
    "linear", "ease_in", "ease_out", "ease_in_out",
    "ease_out_back", "bounce", "smoothstep",
]