# src/managers/reward_template_manager.py
import json
import os
from typing import List, Dict, Optional
from pathlib import Path

from src.config.paths import PROJECT_ROOT

class RewardTemplateManager:
    """Gerencia templates de recompensas (listas de itens com pesos)."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.templates: Dict[str, Dict] = {}
        self._templates_path = PROJECT_ROOT / "data" / "reward_templates.json"
        self._load_templates()

    def _load_templates(self):
        """Carrega templates do arquivo JSON."""
        if self._templates_path.exists():
            try:
                with open(self._templates_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.templates = data.get("templates", {})
            except Exception as e:
                print(f"[RewardTemplateManager] Erro ao carregar templates: {e}")
                self.templates = {}
        else:
            # Cria alguns templates padrão
            self._create_default_templates()
            self.save_templates()

    def _create_default_templates(self):
        """Cria templates padrão para exemplo."""
        self.templates = {
            "Basico": {
                "items": [
                    {"item_id": "potion", "weight": 60},
                    {"item_id": "pokeball", "weight": 40}
                ]
            },
            "Avancado": {
                "items": [
                    {"item_id": "superpotion", "weight": 40},
                    {"item_id": "greatball", "weight": 30},
                    {"item_id": "rare_candy", "weight": 10}
                ]
            },
            "Fosseis": {
                "items": [
                    {"item_id": "helix_fossil", "weight": 33},
                    {"item_id": "dome_fossil", "weight": 33},
                    {"item_id": "old_amber", "weight": 34}
                ]
            }
        }

    def save_templates(self):
        """Salva templates no arquivo JSON."""
        try:
            self._templates_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._templates_path, 'w', encoding='utf-8') as f:
                json.dump({"templates": self.templates}, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[RewardTemplateManager] Erro ao salvar templates: {e}")

    def get_template(self, name: str) -> Optional[Dict]:
        """Retorna um template pelo nome."""
        return self.templates.get(name)

    def get_all_templates(self) -> Dict[str, Dict]:
        """Retorna todos os templates."""
        return self.templates

    def add_template(self, name: str, items: List[Dict]) -> bool:
        """Adiciona ou atualiza um template."""
        if not name or not items:
            return False
        self.templates[name] = {"items": items}
        self.save_templates()
        return True

    def delete_template(self, name: str) -> bool:
        """Remove um template."""
        if name in self.templates:
            del self.templates[name]
            self.save_templates()
            return True
        return False

    def rename_template(self, old_name: str, new_name: str) -> bool:
        """Renomeia um template."""
        if old_name not in self.templates or new_name in self.templates:
            return False
        self.templates[new_name] = self.templates.pop(old_name)
        self.save_templates()
        return True

# Instância global
reward_template_manager = RewardTemplateManager()