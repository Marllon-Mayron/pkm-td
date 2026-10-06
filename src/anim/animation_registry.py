"""Registro de animações — carrega de res/animations/."""
import json
from pathlib import Path
from typing import Optional

from src.config.paths import RES_PATH
from src.anim.animation import AnimDefinition


class AnimationRegistry:
    def __init__(self, root: Optional[Path] = None):
        self.root = Path(root) if root else (RES_PATH / "animations")
        self._cache: dict = {}
        self._bindings: dict = {}
        self.loaded = False

    # =================================================================
    def reload(self):
        self._cache.clear()
        self._bindings.clear()

        self._ensure_structure()

        self._load_bindings()

        for cat_dir in sorted(self.root.iterdir()):
            if not cat_dir.is_dir() or cat_dir.name.startswith("_"):
                continue
            for json_file in sorted(cat_dir.glob("*.json")):
                try:
                    defn = AnimDefinition.from_json(json_file)
                    key = f"{cat_dir.name}/{json_file.stem}"
                    self._cache[key] = defn
                    if defn.default_binding:
                        trig = defn.default_binding.get("trigger")
                        if trig and trig not in self._bindings:
                            self._bindings[trig] = {"animation": key}
                except Exception as e:
                    print(f"[ANIM_REG] erro {json_file}: {e}")

        self.loaded = True
        print(f"[ANIM_REG] {len(self._cache)} animações | {len(self._bindings)} bindings")

    def _ensure_structure(self):
        self.root.mkdir(parents=True, exist_ok=True)
        for cat in ("items", "effects", "moves", "weather", "ui",
                    "_assets", "_shared"):
            (self.root / cat).mkdir(exist_ok=True)

    def _load_bindings(self):
        bfile = self.root / "bindings.json"
        if not bfile.exists():
            return
        try:
            with open(bfile, "r", encoding="utf-8") as f:
                data = json.load(f)
            self._bindings = dict(data.get("bindings", {}))
        except Exception as e:
            print(f"[ANIM_REG] erro bindings.json: {e}")

    # =================================================================
    def get(self, key: str) -> Optional[AnimDefinition]:
        return self._cache.get(key)

    def all_keys(self) -> list:
        return sorted(self._cache.keys())

    def list_by_category(self, category: str) -> list:
        prefix = f"{category}/"
        return sorted(k for k in self._cache if k.startswith(prefix))

    def resolve_trigger(self, trigger: str) -> Optional[AnimDefinition]:
        entry = self._bindings.get(trigger)
        if not entry:
            return None
        key = entry.get("animation")
        return self._cache.get(key) if key else None

    def all_bindings(self) -> dict:
        return dict(self._bindings)

    def set_binding(self, trigger: str, key: str):
        self._bindings[trigger] = {"animation": key}

    def remove_binding(self, trigger: str):
        self._bindings.pop(trigger, None)

    def save_bindings(self):
        bfile = self.root / "bindings.json"
        try:
            bfile.parent.mkdir(parents=True, exist_ok=True)
            with open(bfile, "w", encoding="utf-8") as f:
                json.dump({"schema_version": 1, "bindings": self._bindings},
                          f, indent=2, ensure_ascii=False)
            print(f"[ANIM_REG] bindings salvos: {bfile}")
        except Exception as e:
            print(f"[ANIM_REG] erro salvando bindings: {e}")


animation_registry = AnimationRegistry()