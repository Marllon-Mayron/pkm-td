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
        """
        # Cria pasta do capítulo se não existir
        chapter_path = self.base_path / f"chapter_{chapter:02d}"
        chapter_path.mkdir(exist_ok=True)

        # Nome do arquivo
        filename = f"phase_{phase_number:02d}.json"
        filepath = chapter_path / filename

        # ANTES DE SALVAR: Verifica e ajusta caminhos dos tilesets
        map_data = phase_data["map"].copy()

        print("\n=== AJUSTANDO CAMINHOS DOS TILESETS ANTES DE SALVAR ===")

        for i, layer in enumerate(map_data["layers"]):
            if layer.get("tileset_path"):
                old_path = layer["tileset_path"]
                print(f"Layer {i} ({layer['name']})")
                print(f"  Path original: {old_path}")

                # Se for caminho absoluto, converte para relativo
                if os.path.isabs(old_path):
                    try:
                        # Pega o diretório raiz do projeto
                        project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
                        rel_path = os.path.relpath(old_path, project_root)

                        # Garante que use / e não \
                        rel_path = rel_path.replace('\\', '/')

                        # Remove qualquer referência duplicada ao nome do projeto
                        if 'pokemon-tower-defense/' in rel_path:
                            rel_path = rel_path.replace('pokemon-tower-defense/', '')

                        # Garante que comece com res/
                        if not rel_path.startswith('res/'):
                            if 'res/' in rel_path:
                                rel_path = rel_path[rel_path.index('res/'):]
                            else:
                                # Se não tem res/, coloca em res/AllTiles/
                                basename = os.path.basename(rel_path)
                                rel_path = f"res/AllTiles/{basename}"

                        layer["tileset_path"] = rel_path
                        print(f"  Convertido para: {rel_path}")

                    except Exception as e:
                        print(f"  Erro na conversão: {e}")
                        # Fallback: só o nome do arquivo
                        basename = os.path.basename(old_path)
                        layer["tileset_path"] = f"res/AllTiles/{basename}"
                        print(f"  Fallback para: {layer['tileset_path']}")
                else:
                    print(f"  Já é relativo: {old_path}")

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