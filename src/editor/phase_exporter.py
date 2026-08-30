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

        # Pasta para minigames
        self.minigames_path = Path(PROJECT_ROOT) / "src" / "data" / "minigames"
        self.minigames_path.mkdir(parents=True, exist_ok=True)

        print(f"[PhaseExporter] Base path: {self.base_path}")
        print(f"[PhaseExporter] Minigames path: {self.minigames_path}")

    def _get_phase_path(self, chapter, phase_number, localization_type="default", custom_folder=""):
        """
        Retorna o caminho para uma fase baseado na localização

        Args:
            chapter: Número do capítulo
            phase_number: Número da fase
            localization_type: "default" ou "custom"
            custom_folder: Nome da pasta custom (ex: "fishing_minigame")
        """
        if localization_type == "custom" and custom_folder:
            # Pasta customizada (minigames)
            custom_path = self.minigames_path / custom_folder
            custom_path.mkdir(parents=True, exist_ok=True)
            return custom_path / f"level_{chapter:02d}_{phase_number:02d}.json"
        else:
            # Default (capítulos normais)
            chapter_path = self.base_path / f"chapter_{chapter:02d}"
            chapter_path.mkdir(exist_ok=True)
            return chapter_path / f"phase_{phase_number:02d}.json"

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

    def export_phase(self, phase_data, chapter, phase_number, localization_type="default", custom_folder="",
                     unlock_chapter=1, unlock_phase=1):
        """
        Exporta uma fase para JSON

        Args:
            phase_data: Dados da fase
            chapter: Número do capítulo
            phase_number: Número da fase
            localization_type: "default" ou "custom"
            custom_folder: Nome da pasta custom (se localization_type for "custom")
            unlock_chapter: Capítulo necessário para desbloquear (apenas custom)
            unlock_phase: Fase necessária para desbloquear (apenas custom)
        """
        filepath = self._get_phase_path(chapter, phase_number, localization_type, custom_folder)

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
            "events": phase_data.get("events", {"triggers": []}),
            "rewards": phase_data.get("rewards", {
                "money": 100,
                "experience": 50
            }),
            "localization_type": localization_type,
            "custom_folder": custom_folder if localization_type == "custom" else "",
            "day_night_mode": phase_data.get("day_night_mode", "random"),
            "base_weather": phase_data.get("base_weather", "random"),
        }

        # Adiciona requisito de desbloqueio para minigames
        if localization_type == "custom":
            full_data["unlock_requirement"] = {
                "chapter": unlock_chapter,
                "phase": unlock_phase
            }

        # Salva arquivo
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(full_data, f, indent=4, ensure_ascii=False)

        print(
            f"\n✓ {'Minigame' if localization_type == 'custom' else 'Fase'} {chapter}-{phase_number} exportada: {filepath}")
        print(f"  Localização: {localization_type}" + (f" ({custom_folder})" if custom_folder else ""))
        if localization_type == "custom":
            print(f"  Requer desbloqueio: Capítulo {unlock_chapter}, Fase {unlock_phase}")
        print(f"  Recompensas: {full_data['rewards']['money']} gold, {full_data['rewards']['experience']} XP")
        print("=====================================\n")

        # Atualiza índice apropriado
        if localization_type == "custom":
            self._update_minigame_index(custom_folder, chapter, phase_number, unlock_chapter, unlock_phase)
        else:
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

    def _update_minigame_index(self, minigame_folder, level_chapter, level_number, unlock_chapter=1, unlock_phase=1):
        """Atualiza o índice do minigame com requisito de desbloqueio"""
        minigame_path = self.minigames_path / minigame_folder
        minigame_path.mkdir(parents=True, exist_ok=True)
        index_file = minigame_path / "index.json"

        if index_file.exists():
            with open(index_file, 'r', encoding='utf-8') as f:
                index = json.load(f)
        else:
            index = {
                "name": minigame_folder,
                "levels": []
            }

        level_info = {
            "chapter": level_chapter,
            "level": level_number,
            "unlock_requirement": {
                "chapter": unlock_chapter,
                "phase": unlock_phase
            }
        }

        # Remove se já existe e adiciona atualizado
        index["levels"] = [l for l in index["levels"] if
                           not (l["chapter"] == level_chapter and l["level"] == level_number)]
        index["levels"].append(level_info)
        index["levels"].sort(key=lambda x: (x["chapter"], x["level"]))

        with open(index_file, 'w', encoding='utf-8') as f:
            json.dump(index, f, indent=4)

    def load_phase(self, chapter, phase_number, localization_type="default", custom_folder=""):
        """
        Carrega uma fase do JSON

        Args:
            chapter: Número do capítulo
            phase_number: Número da fase
            localization_type: "default" ou "custom"
            custom_folder: Nome da pasta custom (se localization_type for "custom")
        """
        filepath = self._get_phase_path(chapter, phase_number, localization_type, custom_folder)

        if not filepath.exists():
            print(f"{'Minigame' if localization_type == 'custom' else 'Fase'} não encontrada: {filepath}")
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

            # Compatibilidade com versões antigas (rewards)
            if "rewards" not in data:
                data["rewards"] = {
                    "money": 100,
                    "experience": 50
                }

            # Compatibilidade com versões antigas (localization)
            if "localization_type" not in data:
                data["localization_type"] = "default"
                data["custom_folder"] = ""

            # Compatibilidade com versões antigas (unlock_requirement)
            if "unlock_requirement" not in data:
                data["unlock_requirement"] = {
                    "chapter": 1,
                    "phase": 1
                }

            return data
        except Exception as e:
            print(f"Erro ao carregar {filepath}: {e}")
            import traceback
            traceback.print_exc()
            return None

    def list_phases(self, chapter=None, localization_type="default", custom_folder=""):
        """Lista todas as fases disponíveis"""
        if localization_type == "custom" and custom_folder:
            # Lista minigames de uma pasta específica
            minigame_path = self.minigames_path / custom_folder
            if minigame_path.exists():
                levels = []
                # Primeiro tenta ler do index.json
                index_file = minigame_path / "index.json"
                if index_file.exists():
                    try:
                        with open(index_file, 'r', encoding='utf-8') as f:
                            index = json.load(f)
                        for level in index.get("levels", []):
                            levels.append((level["chapter"], level["level"]))
                        return sorted(levels, key=lambda x: (x[0], x[1]))
                    except:
                        pass

                # Fallback: ler direto dos arquivos
                for level_file in sorted(minigame_path.glob("level_*.json")):
                    try:
                        parts = level_file.stem.split("_")
                        if len(parts) >= 3:
                            level_chapter = int(parts[1])
                            level_number = int(parts[2])
                            levels.append((level_chapter, level_number))
                    except (ValueError, IndexError):
                        continue
                return sorted(levels, key=lambda x: (x[0], x[1]))
            return []
        elif localization_type == "default":
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

    def list_minigame_folders(self):
        """Lista todas as pastas de minigames disponíveis"""
        folders = []
        for folder in self.minigames_path.iterdir():
            if folder.is_dir():
                # Verifica se tem pelo menos um nível
                has_levels = False
                index_file = folder / "index.json"
                if index_file.exists():
                    try:
                        with open(index_file, 'r', encoding='utf-8') as f:
                            index = json.load(f)
                        if index.get("levels"):
                            has_levels = True
                    except:
                        pass

                if not has_levels:
                    # Verifica se tem arquivos level_*.json
                    if list(folder.glob("level_*.json")):
                        has_levels = True

                if has_levels:
                    folders.append(folder.name)
        return sorted(folders)

    def get_minigame_info(self, folder_name):
        """Retorna informações de um minigame específico"""
        minigame_path = self.minigames_path / folder_name
        index_file = minigame_path / "index.json"

        if index_file.exists():
            try:
                with open(index_file, 'r', encoding='utf-8') as f:
                    index = json.load(f)
                return {
                    "name": index.get("name", folder_name),
                    "levels": index.get("levels", [])
                }
            except:
                pass

        # Fallback: cria info baseada nos arquivos
        levels = []
        for level_file in sorted(minigame_path.glob("level_*.json")):
            try:
                parts = level_file.stem.split("_")
                if len(parts) >= 3:
                    levels.append({
                        "chapter": int(parts[1]),
                        "level": int(parts[2]),
                        "unlock_requirement": {"chapter": 1, "phase": 1}
                    })
            except:
                continue

        return {
            "name": folder_name,
            "levels": levels
        }

    def delete_phase(self, chapter, phase_number, localization_type="default", custom_folder=""):
        """Remove uma fase do disco"""
        filepath = self._get_phase_path(chapter, phase_number, localization_type, custom_folder)

        if filepath.exists():
            filepath.unlink()
            print(
                f"✓ {'Minigame' if localization_type == 'custom' else 'Fase'} {chapter}-{phase_number} removida: {filepath}")

            if localization_type == "default":
                self._remove_from_chapter_index(chapter, phase_number)
            else:
                self._remove_from_minigame_index(custom_folder, chapter, phase_number)
            return True
        else:
            print(f"{'Minigame' if localization_type == 'custom' else 'Fase'} não encontrada: {filepath}")
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

    def _remove_from_minigame_index(self, minigame_folder, level_chapter, level_number):
        """Remove um nível do índice do minigame"""
        minigame_path = self.minigames_path / minigame_folder
        index_file = minigame_path / "index.json"

        if index_file.exists():
            with open(index_file, 'r', encoding='utf-8') as f:
                index = json.load(f)

            level_info = {"chapter": level_chapter, "level": level_number}
            index["levels"] = [l for l in index["levels"] if
                               not (l["chapter"] == level_chapter and l["level"] == level_number)]

            if index["levels"]:
                with open(index_file, 'w', encoding='utf-8') as f:
                    json.dump(index, f, indent=4)
            else:
                index_file.unlink()
                if not any(minigame_path.iterdir()):
                    minigame_path.rmdir()

    def get_phase_path(self, chapter, phase_number, localization_type="default", custom_folder=""):
        """Retorna o caminho do arquivo da fase"""
        return self._get_phase_path(chapter, phase_number, localization_type, custom_folder)

    def phase_exists(self, chapter, phase_number, localization_type="default", custom_folder=""):
        """Verifica se uma fase existe"""
        return self.get_phase_path(chapter, phase_number, localization_type, custom_folder).exists()


# Instância global
phase_exporter = PhaseExporter()