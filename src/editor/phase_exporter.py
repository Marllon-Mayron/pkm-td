# src/editor/phase_exporter.py

"""
Exportador de fases para JSON — Suporta Regiões.
Estrutura nova:
  src/data/phases/region_XX/chapter_YY/phase_ZZ.json
  src/data/minigames/<folder>/level_RR_CC_PP.json
"""
import json
import os
from pathlib import Path
from src.config.paths import PROJECT_ROOT, RES_PATH
from src.config.regions import DEFAULT_REGION_ID


class PhaseExporter:
    def __init__(self):
        self.base_path = Path(PROJECT_ROOT) / "src" / "data" / "phases"
        self.base_path.mkdir(parents=True, exist_ok=True)

        self.minigames_path = Path(PROJECT_ROOT) / "src" / "data" / "minigames"
        self.minigames_path.mkdir(parents=True, exist_ok=True)

        print(f"[PhaseExporter] Base path: {self.base_path}")
        print(f"[PhaseExporter] Minigames path: {self.minigames_path}")

    # ==================================================================
    # PATHS
    # ==================================================================
    def _get_phase_path(self, chapter, phase_number,
                        localization_type="default", custom_folder="",
                        region=DEFAULT_REGION_ID):
        """Retorna o Path do arquivo da fase (novo padrão com região)."""
        region = int(region) if region is not None else DEFAULT_REGION_ID

        if localization_type == "custom" and custom_folder:
            custom_path = self.minigames_path / custom_folder
            custom_path.mkdir(parents=True, exist_ok=True)
            return custom_path / f"level_{region:02d}_{chapter:02d}_{phase_number:02d}.json"
        else:
            region_path = self.base_path / f"region_{region:02d}"
            chapter_path = region_path / f"chapter_{chapter:02d}"
            chapter_path.mkdir(parents=True, exist_ok=True)
            return chapter_path / f"phase_{phase_number:02d}.json"

    # ==================================================================
    # TILESET RELATIVE PATH (inalterado)
    # ==================================================================
    def _make_relative_path(self, absolute_path):
        try:
            abs_path = os.path.normpath(absolute_path)
            if "res" in abs_path:
                res_index = abs_path.find("res")
                if res_index != -1:
                    relative = abs_path[res_index:].replace('\\', '/')
                    return relative
            rel_path = os.path.relpath(abs_path, PROJECT_ROOT)
            rel_path = rel_path.replace('\\', '/')
            if not rel_path.startswith('res/'):
                if 'res/' in rel_path:
                    rel_path = rel_path[rel_path.index('res/'):]
                else:
                    basename = os.path.basename(rel_path)
                    rel_path = f"res/AllTiles/{basename}"
            return rel_path
        except Exception as e:
            print(f"  Erro ao converter caminho: {e}")
            return os.path.basename(absolute_path)

    # ==================================================================
    # EXPORT
    # ==================================================================
    def export_phase(self, phase_data, chapter, phase_number,
                     localization_type="default", custom_folder="",
                     unlock_chapter=1, unlock_phase=1,
                     region=DEFAULT_REGION_ID,
                     unlock_region=DEFAULT_REGION_ID):
        region = int(region) if region is not None else DEFAULT_REGION_ID
        filepath = self._get_phase_path(
            chapter, phase_number, localization_type, custom_folder, region
        )

        map_data = phase_data["map"].copy()

        print("\n=== AJUSTANDO CAMINHOS DOS TILESETS ANTES DE SALVAR ===")
        for i, layer in enumerate(map_data["layers"]):
            tileset_paths = []
            if layer.get("tileset_paths"):
                tileset_paths = layer["tileset_paths"]
            elif layer.get("tileset_path"):
                tileset_paths = [layer["tileset_path"]]
            if not tileset_paths and hasattr(layer, 'tileset_paths') and layer.tileset_paths:
                tileset_paths = layer.tileset_paths

            if tileset_paths:
                converted_paths = []
                for old_path in tileset_paths:
                    if old_path:
                        rel_path = self._make_relative_path(old_path)
                        converted_paths.append(rel_path)
                layer["tileset_paths"] = converted_paths
                if "tileset_path" in layer:
                    del layer["tileset_path"]

        full_data = {
            "region": region,
            "chapter": chapter,
            "phase": phase_number,
            "name": phase_data.get("name", f"Fase {phase_number}"),
            "map": map_data,
            "paths": phase_data["paths"],
            "waves": phase_data.get("waves", {"waves": []}),
            "tower_spots": phase_data["tower_spots"],
            "target_items": phase_data.get("target_items", {"items": []}),
            "events": phase_data.get("events", {"triggers": []}),
            "rewards": phase_data.get("rewards", {"money": 100, "experience": 50}),
            "localization_type": localization_type,
            "custom_folder": custom_folder if localization_type == "custom" else "",
            "day_night_mode": phase_data.get("day_night_mode", "random"),
            "base_weather": phase_data.get("base_weather", "random"),
        }

        if localization_type == "custom":
            full_data["unlock_requirement"] = {
                "region": int(unlock_region) if unlock_region is not None else DEFAULT_REGION_ID,
                "chapter": unlock_chapter,
                "phase": unlock_phase,
            }

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(full_data, f, indent=4, ensure_ascii=False)

        print(f"\n✓ {'Minigame' if localization_type == 'custom' else 'Fase'} "
              f"{region}:{chapter}-{phase_number} exportada: {filepath}")

        if localization_type == "custom":
            self._update_minigame_index(
                custom_folder, chapter, phase_number,
                unlock_chapter, unlock_phase, region, unlock_region
            )
        else:
            self._update_chapter_index(region, chapter, phase_number)

        return filepath

    # ==================================================================
    # ÍNDICES
    # ==================================================================
    def _update_chapter_index(self, region, chapter, new_phase):
        region_path = self.base_path / f"region_{region:02d}"
        chapter_path = region_path / f"chapter_{chapter:02d}"
        chapter_path.mkdir(parents=True, exist_ok=True)
        index_file = chapter_path / "index.json"

        if index_file.exists():
            with open(index_file, 'r', encoding='utf-8') as f:
                index = json.load(f)
        else:
            index = {"region": region, "chapter": chapter, "phases": []}

        index["region"] = region
        index["chapter"] = chapter

        if new_phase not in index["phases"]:
            index["phases"].append(new_phase)
            index["phases"].sort()
            with open(index_file, 'w', encoding='utf-8') as f:
                json.dump(index, f, indent=4)

    def _update_minigame_index(self, minigame_folder, level_chapter, level_number,
                               unlock_chapter=1, unlock_phase=1,
                               region=DEFAULT_REGION_ID, unlock_region=DEFAULT_REGION_ID):
        minigame_path = self.minigames_path / minigame_folder
        minigame_path.mkdir(parents=True, exist_ok=True)
        index_file = minigame_path / "index.json"

        if index_file.exists():
            with open(index_file, 'r', encoding='utf-8') as f:
                index = json.load(f)
        else:
            index = {"name": minigame_folder, "levels": []}

        level_info = {
            "region": int(region) if region is not None else DEFAULT_REGION_ID,
            "chapter": level_chapter,
            "level": level_number,
            "unlock_requirement": {
                "region": int(unlock_region) if unlock_region is not None else DEFAULT_REGION_ID,
                "chapter": unlock_chapter,
                "phase": unlock_phase,
            },
        }

        index["levels"] = [
            l for l in index["levels"]
            if not (l.get("chapter") == level_chapter and l.get("level") == level_number
                    and l.get("region", DEFAULT_REGION_ID) == level_info["region"])
        ]
        index["levels"].append(level_info)
        index["levels"].sort(key=lambda x: (x.get("region", 1), x["chapter"], x["level"]))

        with open(index_file, 'w', encoding='utf-8') as f:
            json.dump(index, f, indent=4)

    # ==================================================================
    # LOAD
    # ==================================================================
    def load_phase(self, chapter, phase_number,
                   localization_type="default", custom_folder="",
                   region=DEFAULT_REGION_ID):
        filepath = self._get_phase_path(
            chapter, phase_number, localization_type, custom_folder, region
        )

        if not filepath.exists():
            # Tenta fallback: se estamos em modo default e o path novo não existe,
            # tenta o path antigo (retrocompatibilidade para saves/mapas legados)
            if localization_type == "default":
                legacy = self.base_path / f"chapter_{chapter:02d}" / f"phase_{phase_number:02d}.json"
                if legacy.exists():
                    filepath = legacy
                else:
                    print(f"Fase não encontrada: {filepath}")
                    return None
            else:
                print(f"Minigame não encontrado: {filepath}")
                return None

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Retrocompatibilidade
            if "path" in data and "paths" not in data:
                data["paths"] = {"paths": [data["path"]], "current_path_index": 0}
            if "rewards" not in data:
                data["rewards"] = {"money": 100, "experience": 50}
            if "localization_type" not in data:
                data["localization_type"] = "default"
                data["custom_folder"] = ""
            if "unlock_requirement" not in data:
                data["unlock_requirement"] = {"region": DEFAULT_REGION_ID, "chapter": 1, "phase": 1}
            if "region" not in data:
                data["region"] = DEFAULT_REGION_ID

            return data
        except Exception as e:
            print(f"Erro ao carregar {filepath}: {e}")
            import traceback
            traceback.print_exc()
            return None

    # ==================================================================
    # LIST
    # ==================================================================
    def list_phases(self, chapter=None, localization_type="default",
                    custom_folder="", region=None):
        """
        Lista fases.
          - Se region=None -> retorna TODAS as regiões como (region, chapter, phase)
          - Se region=X e chapter=None -> (chapter, phase) daquela região
          - Se region=X e chapter=Y -> [phase, ...]
        """
        if localization_type == "custom" and custom_folder:
            minigame_path = self.minigames_path / custom_folder
            if minigame_path.exists():
                levels = []
                index_file = minigame_path / "index.json"
                if index_file.exists():
                    try:
                        with open(index_file, 'r', encoding='utf-8') as f:
                            index = json.load(f)
                        for level in index.get("levels", []):
                            r = level.get("region", DEFAULT_REGION_ID)
                            if region is not None and r != region:
                                continue
                            levels.append((r, level["chapter"], level["level"]))
                        return sorted(levels, key=lambda x: (x[0], x[1], x[2]))
                    except Exception:
                        pass

                for level_file in sorted(minigame_path.glob("level_*.json")):
                    try:
                        parts = level_file.stem.split("_")
                        # level_RR_CC_PP (5 partes) OU level_CC_PP (3 partes, legado)
                        if len(parts) >= 5:
                            r = int(parts[1]); c = int(parts[2]); p = int(parts[3])
                        elif len(parts) >= 3:
                            r = DEFAULT_REGION_ID; c = int(parts[1]); p = int(parts[2])
                        else:
                            continue
                        if region is not None and r != region:
                            continue
                        levels.append((r, c, p))
                    except (ValueError, IndexError):
                        continue
                return sorted(levels, key=lambda x: (x[0], x[1], x[2]))

        elif localization_type == "default":
            # Varre todas as regiões + retrocompat com layout antigo
            results = []
            region_dirs = sorted(self.base_path.glob("region_*"))
            for region_dir in region_dirs:
                try:
                    r = int(region_dir.name.split("_")[1])
                except (ValueError, IndexError):
                    continue
                if region is not None and r != region:
                    continue
                for chapter_dir in sorted(region_dir.glob("chapter_*")):
                    try:
                        c = int(chapter_dir.name.split("_")[1])
                    except (ValueError, IndexError):
                        continue
                    if chapter is not None and c != chapter:
                        continue
                    for phase_file in sorted(chapter_dir.glob("phase_*.json")):
                        try:
                            p = int(phase_file.stem.split("_")[1])
                            results.append((r, c, p))
                        except (ValueError, IndexError):
                            continue

            # Layout antigo (sem region_) — considera como região 1
            for chapter_dir in sorted(self.base_path.glob("chapter_*")):
                try:
                    c = int(chapter_dir.name.split("_")[1])
                except (ValueError, IndexError):
                    continue
                if chapter is not None and c != chapter:
                    continue
                r = DEFAULT_REGION_ID
                if region is not None and r != region:
                    continue
                for phase_file in sorted(chapter_dir.glob("phase_*.json")):
                    try:
                        p = int(phase_file.stem.split("_")[1])
                        results.append((r, c, p))
                    except (ValueError, IndexError):
                        continue

            results = sorted(set(results), key=lambda x: (x[0], x[1], x[2]))

            if region is not None and chapter is not None:
                return [p for (r, c, p) in results if r == region and c == chapter]
            if region is not None:
                return [(c, p) for (r, c, p) in results if r == region]
            return results

        return []

    def list_regions_with_phases(self):
        """Retorna lista ordenada de region_ids que possuem fases."""
        all_phases = self.list_phases(localization_type="default")
        return sorted({r for (r, c, p) in all_phases})

    def list_chapters_in_region(self, region):
        """Retorna lista de chapters com fases na região."""
        all_phases = self.list_phases(localization_type="default", region=region)
        return sorted({c for (c, p) in all_phases})

    def list_minigame_folders(self):
        folders = []
        for folder in self.minigames_path.iterdir():
            if folder.is_dir():
                has_levels = False
                index_file = folder / "index.json"
                if index_file.exists():
                    try:
                        with open(index_file, 'r', encoding='utf-8') as f:
                            index = json.load(f)
                        if index.get("levels"):
                            has_levels = True
                    except Exception:
                        pass
                if not has_levels:
                    if list(folder.glob("level_*.json")):
                        has_levels = True
                if has_levels:
                    folders.append(folder.name)
        return sorted(folders)

    def get_minigame_info(self, folder_name):
        minigame_path = self.minigames_path / folder_name
        index_file = minigame_path / "index.json"
        if index_file.exists():
            try:
                with open(index_file, 'r', encoding='utf-8') as f:
                    index = json.load(f)
                return {"name": index.get("name", folder_name),
                        "levels": index.get("levels", [])}
            except Exception:
                pass
        return {"name": folder_name, "levels": []}

    # ==================================================================
    # DELETE / UTIL
    # ==================================================================
    def delete_phase(self, chapter, phase_number,
                     localization_type="default", custom_folder="",
                     region=DEFAULT_REGION_ID):
        filepath = self._get_phase_path(
            chapter, phase_number, localization_type, custom_folder, region
        )
        if filepath.exists():
            filepath.unlink()
            if localization_type == "default":
                self._remove_from_chapter_index(region, chapter, phase_number)
            else:
                self._remove_from_minigame_index(custom_folder, chapter, phase_number, region)
            return True
        return False

    def _remove_from_chapter_index(self, region, chapter, phase_number):
        chapter_path = self.base_path / f"region_{region:02d}" / f"chapter_{chapter:02d}"
        index_file = chapter_path / "index.json"
        if index_file.exists():
            with open(index_file, 'r', encoding='utf-8') as f:
                index = json.load(f)
            if phase_number in index.get("phases", []):
                index["phases"].remove(phase_number)
                with open(index_file, 'w', encoding='utf-8') as f:
                    json.dump(index, f, indent=4)
                if not index["phases"]:
                    index_file.unlink()

    def _remove_from_minigame_index(self, minigame_folder, level_chapter,
                                    level_number, region=DEFAULT_REGION_ID):
        minigame_path = self.minigames_path / minigame_folder
        index_file = minigame_path / "index.json"
        if index_file.exists():
            with open(index_file, 'r', encoding='utf-8') as f:
                index = json.load(f)
            index["levels"] = [
                l for l in index["levels"]
                if not (l.get("chapter") == level_chapter
                        and l.get("level") == level_number
                        and l.get("region", DEFAULT_REGION_ID) == region)
            ]
            if index["levels"]:
                with open(index_file, 'w', encoding='utf-8') as f:
                    json.dump(index, f, indent=4)
            else:
                index_file.unlink()

    def get_phase_path(self, chapter, phase_number, localization_type="default",
                       custom_folder="", region=DEFAULT_REGION_ID):
        return self._get_phase_path(chapter, phase_number, localization_type,
                                     custom_folder, region)

    def phase_exists(self, chapter, phase_number, localization_type="default",
                     custom_folder="", region=DEFAULT_REGION_ID):
        return self.get_phase_path(chapter, phase_number, localization_type,
                                    custom_folder, region).exists()


phase_exporter = PhaseExporter()