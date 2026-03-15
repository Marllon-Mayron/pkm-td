"""
Carregador de fases - Carrega dados das fases do disco
"""
import json
import pygame
from pathlib import Path
from src.config.phase_catalog import phase_catalog


class PhaseLoader:
    """Carrega e prepara os dados da fase para o jogo"""

    def __init__(self):
        self.base_path = Path("data/phases")
        self.current_phase_data = None

    def load_phase(self, chapter: int, phase_number: int) -> dict:
        """
        Carrega uma fase do disco

        Returns:
            dict com os dados da fase ou None se não encontrar
        """
        filepath = self.base_path / f"chapter_{chapter:02d}" / f"phase_{phase_number:02d}.json"

        if not filepath.exists():
            print(f"Fase não encontrada: {filepath}")
            return None

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)

            self.current_phase_data = data
            return data

        except Exception as e:
            print(f"Erro ao carregar fase: {e}")
            return None

    def get_phase_info(self) -> dict:
        """Retorna informações básicas da fase atual"""
        if not self.current_phase_data:
            return {}

        return {
            "name": self.current_phase_data.get("name", "Fase"),
            "chapter": self.current_phase_data.get("chapter", 1),
            "phase": self.current_phase_data.get("phase", 1)
        }

    def get_map_data(self) -> dict:
        """Retorna dados do mapa"""
        if not self.current_phase_data:
            return {}
        return self.current_phase_data.get("map", {})

    def get_path_data(self) -> dict:
        """Retorna dados do path"""
        if not self.current_phase_data:
            return {}
        return self.current_phase_data.get("path", {})

    def get_tower_spots_data(self) -> dict:
        """Retorna dados dos spots de torre"""
        if not self.current_phase_data:
            return {}
        return self.current_phase_data.get("tower_spots", {})

    def get_waves_data(self) -> list:
        """Retorna dados das waves como lista"""
        if not self.current_phase_data:
            return []

        waves_data = self.current_phase_data.get("waves", {})

        # Se for dicionário com chave "waves", extrai a lista
        if isinstance(waves_data, dict) and "waves" in waves_data:
            return waves_data["waves"]

        # Se já for lista, retorna direto
        if isinstance(waves_data, list):
            return waves_data

        return []

    def get_rewards_data(self) -> dict:
        """Retorna dados das recompensas"""
        if not self.current_phase_data:
            return {}
        return self.current_phase_data.get("rewards", {})

    def get_paths_data(self) -> dict:
        """Retorna dados dos paths (múltiplos)"""
        if not self.current_phase_data:
            return {"paths": []}

        # Compatibilidade com versões antigas
        if "paths" in self.current_phase_data:
            return self.current_phase_data.get("paths", {"paths": []})
        elif "path" in self.current_phase_data:
            # Converte path único para formato de múltiplos paths
            return {
                "paths": [self.current_phase_data["path"]],
                "current_path_index": 0
            }
        return {"paths": []}


# Instância global
phase_loader = PhaseLoader()