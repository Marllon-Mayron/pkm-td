# src/config/phase_loader.py
"""
Carregador de fases - Carrega dados das fases do disco
"""
import json
import pygame
from pathlib import Path
from src.config.phase_catalog import phase_catalog
from src.config.paths import PROJECT_ROOT  # Importe o caminho absoluto
from src.editor.wave_config import WaveTemplateManager


class PhaseLoader:
    """Carrega e prepara os dados da fase para o jogo"""

    def __init__(self):
        self.base_path = Path(PROJECT_ROOT) / "src" / "data" / "phases"
        self.current_phase_data = None
        self.tile_size = 24

    def get_tile_size(self) -> int:
        """Retorna o tile_size da fase atual"""
        if self.current_phase_data:
            map_data = self.current_phase_data.get("map", {})
            return map_data.get("tile_size", 24)
        return 24

    def load_phase(self, chapter: int, phase_number: int) -> dict:
        """
        Carrega uma fase do disco
        """
        # Formata com 2 dígitos (01, 02, etc)
        filepath = self.base_path / f"chapter_{chapter:02d}" / f"phase_{phase_number:02d}.json"

        print(f"\n[PhaseLoader] Procurando fase: {filepath}")
        print(f"[PhaseLoader] Caminho absoluto: {filepath.absolute()}")
        print(f"[PhaseLoader] Arquivo existe? {filepath.exists()}")

        if not filepath.exists():
            print(f"[ERRO] Fase não encontrada: {filepath}")
            # Lista o que existe na pasta para debug
            chapter_dir = self.base_path / f"chapter_{chapter:02d}"
            if chapter_dir.exists():
                print(f"[Debug] Arquivos em {chapter_dir}:")
                for f in sorted(chapter_dir.glob("*.json")):
                    print(f"  - {f.name}")
            else:
                print(f"[Debug] Pasta do capítulo não existe: {chapter_dir}")
            return None

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)

            print(f"\n=== PHASE LOADER: Fase {chapter}-{phase_number} carregada ===")
            print(f"Arquivo: {filepath}")
            print(f"Keys no JSON: {data.keys()}")

            self.current_phase_data = data
            return data

        except Exception as e:
            print(f"Erro ao carregar fase: {e}")
            import traceback
            traceback.print_exc()
            return None

    def get_all_pokemon_ids_from_phase(self) -> list[int]:
        """
        Retorna uma lista com todos os pokemon_id únicos que podem aparecer
        em qualquer wave, template ou variant da fase atual.
        """
        ids = set()
        waves = self.get_waves_data()
        if not waves:
            return []

        for wave in waves:
            # 1. Inimigos diretos da wave
            for enemy in wave.get("enemies", []):
                pid = enemy.get("pokemon_id")
                if pid:
                    ids.add(pid)

            # 2. Template principal da wave
            template_id = wave.get("template_id")
            if template_id:
                template = WaveTemplateManager.get_template(template_id)
                if template:
                    for e in template.enemies:
                        ids.add(e.pokemon_id)

            # 3. Variants (se ativados)
            if wave.get("use_variants", False):
                for variant in wave.get("variants", []):
                    # 3a. Template do variant
                    var_template_id = variant.get("template_id")
                    if var_template_id:
                        var_template = WaveTemplateManager.get_template(var_template_id)
                        if var_template:
                            for e in var_template.enemies:
                                ids.add(e.pokemon_id)
                    # 3b. Inimigos diretos do variant
                    for enemy in variant.get("enemies", []):
                        pid = enemy.get("pokemon_id")
                        if pid:
                            ids.add(pid)

        return list(ids)

    def get_base_path(self) -> str:
        """Retorna o caminho base do projeto (onde está a pasta res)"""
        return str(PROJECT_ROOT)

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
        """Retorna dados das waves como lista (compatível com novo formato)"""
        if not self.current_phase_data:
            print("[PhaseLoader] Sem dados da fase carregados")
            return []

        waves_data = self.current_phase_data.get("waves", {})

        print(f"\n=== PHASE LOADER DEBUG ===")
        print(f"Tipo de waves_data: {type(waves_data)}")
        print("==========================\n")

        # CASO 1: É um dicionário com chave "waves" (formato atual)
        if isinstance(waves_data, dict) and "waves" in waves_data:
            waves_list = waves_data["waves"]
            print(f"[PhaseLoader] Encontrou {len(waves_list)} waves no formato dict['waves']")

            # ===== VERIFICA SE TEM TEMPLATES E VARIANTS =====
            templates = waves_data.get("templates", {})
            if templates.get("templates"):
                print(f"[PhaseLoader] Encontrou {len(templates.get('templates', []))} templates")

            # ===== VERIFICA SE TEM VARIANTS NAS WAVES =====
            for wave in waves_list:
                if wave.get("use_variants", False):
                    variants = wave.get("variants", [])
                    print(f"[PhaseLoader] Wave {wave.get('wave_index', 0)} tem {len(variants)} variants")
                if wave.get("template_id"):
                    print(f"[PhaseLoader] Wave {wave.get('wave_index', 0)} usa template {wave.get('template_id')}")

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