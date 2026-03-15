# src/editor/phase_exporter.py

"""
Exportador de fases para JSON
"""
import json
import os
from pathlib import Path


class PhaseExporter:
    def __init__(self):
        self.base_path = Path("data/phases")
        self.base_path.mkdir(parents=True, exist_ok=True)

    def export_phase(self, phase_data, chapter, phase_number):
        """
        Exporta uma fase para JSON

        phase_data: {
            "name": str,
            "map": layer_manager dict,
            "paths": path_manager dict,
            "waves": wave_manager dict,
            "tower_spots": tower_spot_manager dict,
            "rewards": dict
        }
        """
        # Cria pasta do capítulo se não existir
        chapter_path = self.base_path / f"chapter_{chapter:02d}"
        chapter_path.mkdir(exist_ok=True)

        # Nome do arquivo
        filename = f"phase_{phase_number:02d}.json"
        filepath = chapter_path / filename

        # Prepara dados completos
        full_data = {
            "chapter": chapter,
            "phase": phase_number,
            "name": phase_data.get("name", f"Fase {phase_number}"),
            "map": phase_data["map"],
            "paths": phase_data["paths"],
            "waves": phase_data.get("waves", {"waves": []}),
            "tower_spots": phase_data["tower_spots"],
            "rewards": phase_data.get("rewards", {
                "money": 100,
                "experience": 50
            })
        }

        # Salva arquivo
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(full_data, f, indent=4, ensure_ascii=False)

        print(f"Fase {chapter}-{phase_number} exportada: {filepath}")

        # Atualiza índice do capítulo
        self._update_chapter_index(chapter, phase_number)

        return filepath

    def _update_chapter_index(self, chapter, new_phase):
        """Atualiza o arquivo de índice do capítulo"""
        chapter_path = self.base_path / f"chapter_{chapter:02d}"
        index_file = chapter_path / "index.json"

        # Carrega índice existente ou cria novo
        if index_file.exists():
            with open(index_file, 'r') as f:
                index = json.load(f)
        else:
            index = {
                "chapter": chapter,
                "phases": []
            }

        # Adiciona nova fase se não existir
        if new_phase not in index["phases"]:
            index["phases"].append(new_phase)
            index["phases"].sort()

            with open(index_file, 'w') as f:
                json.dump(index, f, indent=4)

    def load_phase(self, chapter, phase_number):
        """Carrega uma fase do JSON"""
        filepath = self.base_path / f"chapter_{chapter:02d}" / f"phase_{phase_number:02d}.json"

        if not filepath.exists():
            print(f"Fase não encontrada: {filepath}")
            return None

        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Compatibilidade com versões antigas
        if "path" in data and "paths" not in data:
            # Converte path único para lista de paths
            data["paths"] = {
                "paths": [data["path"]],
                "current_path_index": 0
            }

        return data

    def list_phases(self, chapter=None):
        """Lista todas as fases disponíveis"""
        if chapter:
            chapter_path = self.base_path / f"chapter_{chapter:02d}"
            if chapter_path.exists():
                return [f.stem for f in chapter_path.glob("phase_*.json")]
        else:
            phases = []
            for chapter_dir in sorted(self.base_path.glob("chapter_*")):
                chapter_num = int(chapter_dir.name.split("_")[1])
                for phase_file in sorted(chapter_dir.glob("phase_*.json")):
                    phase_num = int(phase_file.stem.split("_")[1])
                    phases.append((chapter_num, phase_num))
            return phases
        return []