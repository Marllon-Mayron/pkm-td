# src/editor/phase_exporter.py

"""
Exportador de fases para JSON
"""
import json
import os
from pathlib import Path
from src.config.paths import PROJECT_ROOT, RES_PATH


class PhaseExporter:
    def __init__(self):
        # Use o PROJECT_ROOT para construir o caminho absoluto
        self.base_path = Path(PROJECT_ROOT) / "src" / "data" / "phases"
        self.base_path.mkdir(parents=True, exist_ok=True)
        print(f"[PhaseExporter] Base path: {self.base_path}")

    def _make_relative_path(self, absolute_path):
        """
        Converte um caminho absoluto para relativo à pasta res/
        Ex: C:/.../pkm-td/res/AllTiles/xxx.png -> res/AllTiles/xxx.png
        """
        try:
            # Normaliza o caminho
            abs_path = os.path.normpath(absolute_path)

            # Se o caminho já contém "res/", extrai a partir de "res"
            if "res" in abs_path:
                # Procura pela pasta "res" no caminho
                res_index = abs_path.find("res")
                if res_index != -1:
                    relative = abs_path[res_index:].replace('\\', '/')
                    print(f"  Convertendo: {abs_path} -> {relative}")
                    return relative

            # Tenta calcular caminho relativo ao PROJECT_ROOT
            rel_path = os.path.relpath(abs_path, PROJECT_ROOT)
            rel_path = rel_path.replace('\\', '/')

            # Se não começar com res/, tenta extrair apenas o nome do arquivo
            if not rel_path.startswith('res/'):
                # Procura se tem res/ no caminho
                if 'res/' in rel_path:
                    rel_path = rel_path[rel_path.index('res/'):]
                else:
                    # Fallback: só o nome do arquivo na pasta AllTiles
                    basename = os.path.basename(rel_path)
                    rel_path = f"res/AllTiles/{basename}"

            print(f"  Convertendo: {abs_path} -> {rel_path}")
            return rel_path

        except Exception as e:
            print(f"  Erro ao converter caminho: {e}")
            return os.path.basename(absolute_path)

    def export_phase(self, phase_data, chapter, phase_number):
        """
        Exporta uma fase para JSON
        """
        # Cria pasta do capítulo se não existir
        chapter_path = self.base_path / f"chapter_{chapter:02d}"
        chapter_path.mkdir(exist_ok=True)

        # Nome do arquivo
        filename = f"phase_{phase_number:02d}.json"
        filepath = chapter_path / filename

        # Processa os tilesets
        map_data = phase_data["map"].copy()

        print("\n=== AJUSTANDO CAMINHOS DOS TILESETS ANTES DE SALVAR ===")

        for i, layer in enumerate(map_data["layers"]):
            # Pega os caminhos dos tilesets
            tileset_paths = []

            # Verifica diferentes formas de armazenar os caminhos
            if layer.get("tileset_paths"):
                tileset_paths = layer["tileset_paths"]
            elif layer.get("tileset_path"):
                tileset_paths = [layer["tileset_path"]]

            # Também verifica se o layer tem atributo tileset_paths (quando vem do editor)
            if not tileset_paths and hasattr(layer, 'tileset_paths') and layer.tileset_paths:
                tileset_paths = layer.tileset_paths

            if tileset_paths:
                converted_paths = []
                for old_path in tileset_paths:
                    if old_path:
                        # Converte para caminho relativo
                        rel_path = self._make_relative_path(old_path)
                        converted_paths.append(rel_path)
                        print(f"Layer {i} ({layer['name']}): {os.path.basename(old_path)} -> {rel_path}")

                layer["tileset_paths"] = converted_paths
                # Remove o antigo tileset_path para evitar duplicação
                if "tileset_path" in layer:
                    del layer["tileset_path"]
            else:
                print(f"Layer {i} ({layer['name']}): sem tilesets")

        # Prepara dados completos
        full_data = {
            "chapter": chapter,
            "phase": phase_number,
            "name": phase_data.get("name", f"Fase {phase_number}"),
            "map": map_data,
            "paths": phase_data["paths"],
            "waves": phase_data.get("waves", {"waves": []}),
            "tower_spots": phase_data["tower_spots"],
            "target_items": phase_data.get("target_items", {"items": []}),
            "rewards": phase_data.get("rewards", {
                "money": 100,
                "experience": 50
            })
        }

        # Salva arquivo
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(full_data, f, indent=4, ensure_ascii=False)

        print(f"\n✓ Fase {chapter}-{phase_number} exportada: {filepath}")
        print("=====================================\n")

        # Atualiza índice do capítulo
        self._update_chapter_index(chapter, phase_number)

        return filepath

    def _update_chapter_index(self, chapter, new_phase):
        """Atualiza o arquivo de índice do capítulo"""
        chapter_path = self.base_path / f"chapter_{chapter:02d}"
        index_file = chapter_path / "index.json"

        if index_file.exists():
            with open(index_file, 'r', encoding='utf-8') as f:
                index = json.load(f)
        else:
            index = {
                "chapter": chapter,
                "phases": []
            }

        if new_phase not in index["phases"]:
            index["phases"].append(new_phase)
            index["phases"].sort()

            with open(index_file, 'w', encoding='utf-8') as f:
                json.dump(index, f, indent=4)

    def load_phase(self, chapter, phase_number):
        """Carrega uma fase do JSON"""
        filepath = self.base_path / f"chapter_{chapter:02d}" / f"phase_{phase_number:02d}.json"

        if not filepath.exists():
            print(f"Fase não encontrada: {filepath}")
            return None

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Compatibilidade com versões antigas
            if "path" in data and "paths" not in data:
                data["paths"] = {
                    "paths": [data["path"]],
                    "current_path_index": 0
                }

            return data
        except Exception as e:
            print(f"Erro ao carregar fase {filepath}: {e}")
            return None

    def list_phases(self, chapter=None):
        """Lista todas as fases disponíveis"""
        if chapter:
            chapter_path = self.base_path / f"chapter_{chapter:02d}"
            if chapter_path.exists():
                phases = []
                for phase_file in sorted(chapter_path.glob("phase_*.json")):
                    phase_num = int(phase_file.stem.split("_")[1])
                    phases.append(phase_num)
                return phases
        else:
            phases = []
            for chapter_dir in sorted(self.base_path.glob("chapter_*")):
                try:
                    chapter_num = int(chapter_dir.name.split("_")[1])
                    for phase_file in sorted(chapter_dir.glob("phase_*.json")):
                        phase_num = int(phase_file.stem.split("_")[1])
                        phases.append((chapter_num, phase_num))
                except (ValueError, IndexError):
                    continue
            return phases

    def delete_phase(self, chapter, phase_number):
        """Remove uma fase do disco"""
        filepath = self.base_path / f"chapter_{chapter:02d}" / f"phase_{phase_number:02d}.json"

        if filepath.exists():
            filepath.unlink()
            print(f"✓ Fase {chapter}-{phase_number} removida: {filepath}")

            self._remove_from_chapter_index(chapter, phase_number)
            return True
        else:
            print(f"Fase não encontrada: {filepath}")
            return False

    def _remove_from_chapter_index(self, chapter, phase_number):
        """Remove uma fase do arquivo de índice do capítulo"""
        chapter_path = self.base_path / f"chapter_{chapter:02d}"
        index_file = chapter_path / "index.json"

        if index_file.exists():
            with open(index_file, 'r', encoding='utf-8') as f:
                index = json.load(f)

            if phase_number in index["phases"]:
                index["phases"].remove(phase_number)

                with open(index_file, 'w', encoding='utf-8') as f:
                    json.dump(index, f, indent=4)

                if not index["phases"]:
                    index_file.unlink()
                    if not any(chapter_path.iterdir()):
                        chapter_path.rmdir()

    def get_phase_path(self, chapter, phase_number):
        """Retorna o caminho do arquivo da fase"""
        return self.base_path / f"chapter_{chapter:02d}" / f"phase_{phase_number:02d}.json"

    def phase_exists(self, chapter, phase_number):
        """Verifica se uma fase existe"""
        return self.get_phase_path(chapter, phase_number).exists()


# Instância global
phase_exporter = PhaseExporter()