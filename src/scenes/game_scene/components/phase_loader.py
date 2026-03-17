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
            print("[PhaseLoader] Sem dados da fase carregados")
            return []

        waves_data = self.current_phase_data.get("waves", {})

        print(f"\n=== PHASE LOADER DEBUG ===")
        print(f"Tipo de waves_data: {type(waves_data)}")
        print(f"Conteúdo de waves_data: {waves_data}")
        print("==========================\n")

        # CASO 1: É um dicionário com chave "waves" (formato atual do editor)
        if isinstance(waves_data, dict) and "waves" in waves_data:
            waves_list = waves_data["waves"]
            print(f"[PhaseLoader] Encontrou {len(waves_list)} waves no formato dict['waves']")
            return waves_list

        # CASO 2: É uma lista direta (formato antigo)
        if isinstance(waves_data, list):
            print(f"[PhaseLoader] Encontrou {len(waves_data)} waves no formato lista")
            return waves_data

        # CASO 3: É um dicionário sem a chave "waves" (formato muito antigo)
        if isinstance(waves_data, dict) and waves_data:
            print(f"[PhaseLoader] Convertendo dicionário para lista (1 wave)")
            return [waves_data]

        print("[PhaseLoader] Nenhuma wave encontrada")
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