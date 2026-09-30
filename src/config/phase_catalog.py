# src/config/phase_catalog.py
"""
Catálogo de fases — Suporta REGIÕES.

Formato novo:   src/data/phases/region_XX/chapter_YY/phase_ZZ.json
Formato legado: src/data/phases/chapter_YY/phase_ZZ.json  (assume região 1 = Kanto)
"""
import json
from pathlib import Path
from typing import Dict, List, Optional, Union

from src.config.paths import PROJECT_ROOT
from src.config.regions import DEFAULT_REGION_ID


class PhaseCatalog:
    def __init__(self):
        self.base_path = Path(PROJECT_ROOT) / "src" / "data" / "phases"
        print(f"[PhaseCatalog] Base path: {self.base_path}")
        print(f"[PhaseCatalog] Base path existe? {self.base_path.exists()}")
        self.cache: Optional[Dict[int, Dict[int, List[Dict]]]] = None

    # ==================================================================
    # CARGA
    # ==================================================================
    def _load_single_phase(self, phase_file: Path, chapter_num: int, region_id: int) -> Optional[Dict]:
        try:
            with open(phase_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            phase_num = int(phase_file.stem.split("_")[1])
            return {
                "number": phase_num,
                "name": data.get("name", f"Fase {phase_num}"),
                "file": str(phase_file),
                "chapter": chapter_num,
                "region": region_id,
            }
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            print(f"[PhaseCatalog] Erro ao carregar {phase_file}: {e}")
            return None

    def _load_chapter(self, chapter_dir: Path, region_id: int):
        try:
            chapter_num = int(chapter_dir.name.split("_")[1])
        except (ValueError, IndexError):
            return None

        phases = []
        for phase_file in sorted(chapter_dir.glob("phase_*.json")):
            p = self._load_single_phase(phase_file, chapter_num, region_id)
            if p:
                phases.append(p)
        return (chapter_num, phases) if phases else None

    def _load_all(self) -> Dict[int, Dict[int, List[Dict]]]:
        catalog: Dict[int, Dict[int, List[Dict]]] = {}

        if not self.base_path.exists():
            print(f"[ERRO] Diretório de fases não encontrado: {self.base_path}")
            return catalog

        # ----- 1) NOVO FORMATO -----
        for region_dir in sorted(self.base_path.glob("region_*")):
            try:
                region_id = int(region_dir.name.split("_")[1])
            except (ValueError, IndexError):
                continue

            for chapter_dir in sorted(region_dir.glob("chapter_*")):
                result = self._load_chapter(chapter_dir, region_id)
                if result:
                    ch_num, phases = result
                    catalog.setdefault(region_id, {})[ch_num] = phases

        # ----- 2) LEGADO (region padrão) -----
        for chapter_dir in sorted(self.base_path.glob("chapter_*")):
            result = self._load_chapter(chapter_dir, DEFAULT_REGION_ID)
            if result:
                ch_num, phases = result
                existing = catalog.setdefault(DEFAULT_REGION_ID, {})
                # Só adiciona se não tiver vindo do formato novo
                if ch_num not in existing:
                    existing[ch_num] = phases

        return catalog

    # ==================================================================
    # API PÚBLICA
    # ==================================================================
    def get_all_phases(self, region_id: Optional[int] = None):
        """
        Sem args -> {region_id: {chapter: [phases]}}
        Com region_id -> {chapter: [phases]}
        """
        if self.cache is None:
            self.cache = self._load_all()
        if region_id is None:
            return self.cache
        return self.cache.get(int(region_id), {})

    def get_all_regions(self) -> List[int]:
        if self.cache is None:
            self.cache = self._load_all()
        return sorted(self.cache.keys())

    def get_chapter_phases(self, region_id_or_chapter, chapter: Optional[int] = None) -> List[Dict]:
        """Aceita get_chapter_phases(chapter) [legado] ou (region_id, chapter) [novo]."""
        if chapter is None:
            chapter = int(region_id_or_chapter)
            region_id = DEFAULT_REGION_ID
        else:
            region_id = int(region_id_or_chapter)
            chapter = int(chapter)
        return self.get_all_phases(region_id).get(chapter, [])

    def get_total_chapters(self, region_id: Optional[int] = None) -> int:
        if region_id is None:
            if self.cache is None:
                self.cache = self._load_all()
            return sum(len(chs) for chs in self.cache.values())
        return len(self.get_all_phases(int(region_id)))

    def get_phase_info(self, *args) -> Optional[Dict]:
        """Aceita (chapter, phase) [legado] ou (region_id, chapter, phase) [novo]."""
        if len(args) == 2:
            region_id = DEFAULT_REGION_ID
            chapter, phase = args
        elif len(args) == 3:
            region_id, chapter, phase = args
        else:
            return None

        for p in self.get_chapter_phases(int(region_id), int(chapter)):
            if p["number"] == phase:
                return p
        return None

    def get_max_phase_per_chapter(self, region_id: Optional[int] = None) -> Dict:
        if region_id is None:
            if self.cache is None:
                self.cache = self._load_all()
            return {
                (r, c): len(phases)
                for r, chs in self.cache.items()
                for c, phases in chs.items()
            }
        chapters = self.get_all_phases(int(region_id))
        return {c: len(phases) for c, phases in chapters.items()}

    def refresh(self):
        self.cache = None
        self.get_all_phases()


phase_catalog = PhaseCatalog()