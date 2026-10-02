# src/config/phase_loader.py
"""
Carregador de fases - Carrega dados das fases do disco.
Suporta:
  - Novo:    src/data/phases/region_RR/chapter_CC/phase_PP.json
  - Legado:  src/data/phases/chapter_CC/phase_PP.json  (assume região 1)
"""
import json
import pygame
from pathlib import Path

from src.config.phase_catalog import phase_catalog
from src.config.paths import PROJECT_ROOT
from src.config.regions import DEFAULT_REGION_ID
from src.editor.wave_config import WaveTemplateManager


class PhaseLoader:
    """Carrega e prepara os dados da fase para o jogo"""

    def __init__(self):
        self.base_path = Path(PROJECT_ROOT) / "src" / "data" / "phases"
        self.current_phase_data = None
        self.tile_size = 16

    # ==================================================================
    # RESOLUÇÃO DE PATH
    # ==================================================================
    def _resolve_phase_path(self, chapter: int, phase_number: int, region):
        """
        Retorna (Path, mode) onde mode é:
          - "new"     → arquivo no formato region_RR/chapter_CC/phase_PP.json
          - "legacy"  → arquivo no formato antigo chapter_CC/phase_PP.json
          - "missing" → nenhum existe (retorna o path novo para log)
        """
        region = int(region) if region is not None else DEFAULT_REGION_ID

        new_path = (
            self.base_path
            / f"region_{region:02d}"
            / f"chapter_{chapter:02d}"
            / f"phase_{phase_number:02d}.json"
        )
        if new_path.exists():
            return new_path, "new"

        # Fallback para o layout antigo — só faz sentido na região 1
        if region == DEFAULT_REGION_ID:
            legacy_path = (
                self.base_path
                / f"chapter_{chapter:02d}"
                / f"phase_{phase_number:02d}.json"
            )
            if legacy_path.exists():
                return legacy_path, "legacy"

        return new_path, "missing"

    # ==================================================================
    # LOAD
    # ==================================================================
    def load_phase(self, chapter: int, phase_number: int,
                   region_id: int = DEFAULT_REGION_ID) -> dict:
        """Carrega uma fase do disco."""
        region_id = int(region_id) if region_id is not None else DEFAULT_REGION_ID
        filepath, mode = self._resolve_phase_path(chapter, phase_number, region_id)

        print(f"\n[PhaseLoader] Procurando fase: {filepath}")
        print(f"[PhaseLoader] Região={region_id} Cap={chapter} Fase={phase_number} | modo={mode}")
        print(f"[PhaseLoader] Arquivo existe? {filepath.exists()}")

        if not filepath.exists():
            print(f"[ERRO] Fase não encontrada: {filepath}")

            # Debug: lista o que existe nos dois possíveis diretórios
            debug_dirs = [
                self.base_path / f"region_{region_id:02d}" / f"chapter_{chapter:02d}",
                self.base_path / f"chapter_{chapter:02d}",
            ]
            for d in debug_dirs:
                if d.exists():
                    print(f"[Debug] Arquivos em {d}:")
                    for f in sorted(d.glob("*.json")):
                        print(f"  - {f.name}")
                else:
                    print(f"[Debug] Pasta não existe: {d}")
            return None

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)

            print(f"\n=== PHASE LOADER: Fase {region_id}:{chapter}-{phase_number} carregada ===")
            print(f"Arquivo: {filepath}")
            print(f"Keys no JSON: {data.keys()}")

            # Garante região e fallbacks
            if "region" not in data:
                data["region"] = region_id
            if "chapter" not in data:
                data["chapter"] = chapter
            if "phase" not in data:
                data["phase"] = phase_number

            self.current_phase_data = data
            return data

        except Exception as e:
            print(f"Erro ao carregar fase: {e}")
            import traceback
            traceback.print_exc()
            return None

    # ==================================================================
    # MÉTODOS EXISTENTES (inalterados)
    # ==================================================================
    def get_tile_size(self) -> int:
        if self.current_phase_data:
            map_data = self.current_phase_data.get("map", {})
            return map_data.get("tile_size", 16)
        return 24

    def get_all_pokemon_ids_from_phase(self) -> list:
        ids = set()
        waves = self.get_waves_data()
        if not waves:
            return []

        for wave in waves:
            for enemy in wave.get("enemies", []):
                pid = enemy.get("pokemon_id")
                if pid:
                    ids.add(pid)

            template_id = wave.get("template_id")
            if template_id:
                template = WaveTemplateManager.get_template(template_id)
                if template:
                    for e in template.enemies:
                        ids.add(e.pokemon_id)

            if wave.get("use_variants", False):
                for variant in wave.get("variants", []):
                    var_template_id = variant.get("template_id")
                    if var_template_id:
                        var_template = WaveTemplateManager.get_template(var_template_id)
                        if var_template:
                            for e in var_template.enemies:
                                ids.add(e.pokemon_id)
                    for enemy in variant.get("enemies", []):
                        pid = enemy.get("pokemon_id")
                        if pid:
                            ids.add(pid)

        return list(ids)

    def get_base_path(self) -> str:
        return str(PROJECT_ROOT)

    def get_phase_info(self) -> dict:
        if not self.current_phase_data:
            return {}
        return {
            "name": self.current_phase_data.get("name", "Fase"),
            "chapter": self.current_phase_data.get("chapter", 1),
            "phase": self.current_phase_data.get("phase", 1),
            "region": self.current_phase_data.get("region", DEFAULT_REGION_ID),
        }

    def get_map_data(self) -> dict:
        if not self.current_phase_data:
            return {}
        return self.current_phase_data.get("map", {})

    def get_path_data(self) -> dict:
        if not self.current_phase_data:
            return {}
        return self.current_phase_data.get("path", {})

    def get_tower_spots_data(self) -> dict:
        if not self.current_phase_data:
            return {}
        return self.current_phase_data.get("tower_spots", {})

    def get_waves_data(self) -> list:
        if not self.current_phase_data:
            print("[PhaseLoader] Sem dados da fase carregados")
            return []

        waves_data = self.current_phase_data.get("waves", {})

        if isinstance(waves_data, dict) and "waves" in waves_data:
            return waves_data["waves"]

        if isinstance(waves_data, list):
            return waves_data

        if isinstance(waves_data, dict) and waves_data:
            return [waves_data]

        return []

    def get_rewards_data(self) -> dict:
        if not self.current_phase_data:
            return {}
        return self.current_phase_data.get("rewards", {})

    def get_paths_data(self) -> dict:
        if not self.current_phase_data:
            return {"paths": []}

        if "paths" in self.current_phase_data:
            return self.current_phase_data.get("paths", {"paths": []})
        elif "path" in self.current_phase_data:
            return {
                "paths": [self.current_phase_data["path"]],
                "current_path_index": 0,
            }
        return {"paths": []}

    def get_event_manager(self):
        from src.editor.event_system import EventManager
        if not self.current_phase_data:
            return EventManager()
        events_data = self.current_phase_data.get("events", {})
        event_manager = EventManager()
        event_manager.from_dict(events_data)
        return event_manager


# Instância global
phase_loader = PhaseLoader()