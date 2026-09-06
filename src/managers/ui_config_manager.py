# src/managers/ui_config_manager.py
"""
Gerenciador de configurações da UI (posição da bolsa, tamanho, etc.)
Salva em um arquivo separado dos saves de progresso.
"""

import json
import os
from src.config.paths import PROJECT_ROOT


class UIConfigManager:
    """Gerencia configurações da UI do jogador"""

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

        self.config_path = os.path.join(PROJECT_ROOT, "src/config", "ui_config.json")
        print(f"[UI_CONFIG] Caminho do arquivo: {self.config_path}")  # <-- LOG
        self.config = self._load_config()

    def _load_config(self):
        """Carrega a configuração do arquivo"""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"[UI_CONFIG] Erro ao carregar configuração: {e}")
                return self._get_default_config()
        return self._get_default_config()

    def _get_default_config(self):
        """Retorna a configuração padrão"""
        return {
            "bag": {
                "x": None,
                "y": None,
                "width": 250,
                "height": 400,
                "minimized": False,
                "category": "all"
            }
        }

    def save_config(self):
        """Salva a configuração atual"""
        try:
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[UI_CONFIG] Erro ao salvar: {e}")

    def get_bag_config(self):
        """Retorna a configuração da bolsa"""
        return self.config.get("bag", {})

    def update_bag_config(self, **kwargs):
        """Atualiza a configuração da bolsa"""
        if "bag" not in self.config:
            self.config["bag"] = {}
        self.config["bag"].update(kwargs)
        self.save_config()

    def reset_bag_config(self):
        """Reseta a configuração da bolsa para o padrão"""
        self.config["bag"] = self._get_default_config()["bag"]
        self.save_config()


# Singleton
ui_config_manager = UIConfigManager()