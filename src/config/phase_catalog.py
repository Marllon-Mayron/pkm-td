# src/config/phase_catalog.py
"""
Catálogo de fases - Lista todas as fases disponíveis no jogo
"""
import json
from pathlib import Path
from typing import List, Dict, Optional
from src.config.paths import PROJECT_ROOT  # Importe o caminho absoluto


class PhaseCatalog:
    """Gerencia o catálogo de todas as fases disponíveis no jogo"""

    def __init__(self):
        # Use o PROJECT_ROOT para construir o caminho absoluto
        self.base_path = Path(PROJECT_ROOT) / "src" / "data" / "phases"
        print(f"[PhaseCatalog] Base path: {self.base_path}")
        print(f"[PhaseCatalog] Base path existe? {self.base_path.exists()}")
        self.cache = None

    def get_all_phases(self) -> Dict[int, List[Dict]]:
        """
        Retorna todas as fases organizadas por capítulo

        Returns:
            {
                1: [{"number": 1, "name": "Nome", "file": "path"}, ...],
                2: [...],
                ...
            }
        """
        if self.cache is not None:
            return self.cache

        catalog = {}

        # Verifica se o diretório base existe
        if not self.base_path.exists():
            print(f"[ERRO] Diretório de fases não encontrado: {self.base_path}")
            print(f"[ERRO] PROJECT_ROOT: {PROJECT_ROOT}")
            return catalog

        # Procura por pastas de capítulo
        for chapter_dir in sorted(self.base_path.glob("chapter_*")):
            try:
                chapter_num = int(chapter_dir.name.split("_")[1])
                phases = []
                # Lista todos os arquivos JSON de fase
                for phase_file in sorted(chapter_dir.glob("phase_*.json")):
                    try:
                        # Carrega o arquivo para pegar o nome
                        with open(phase_file, 'r', encoding='utf-8') as f:
                            data = json.load(f)

                        phase_num = int(phase_file.stem.split("_")[1])
                        phases.append({
                            "number": phase_num,
                            "name": data.get("name", f"Fase {phase_num}"),
                            "file": str(phase_file),
                            "chapter": chapter_num
                        })
                    except (json.JSONDecodeError, ValueError, KeyError) as e:
                        print(f"Erro ao carregar fase {phase_file}: {e}")
                        continue
                if phases:
                    catalog[chapter_num] = phases
            except (ValueError, IndexError) as e:
                print(f"Pasta ignorada: {chapter_dir} - {e}")
                continue

        self.cache = catalog
        return catalog

    def get_chapter_phases(self, chapter: int) -> List[Dict]:
        """Retorna as fases de um capítulo específico"""
        catalog = self.get_all_phases()
        return catalog.get(chapter, [])

    def get_total_chapters(self) -> int:
        """Retorna o número total de capítulos"""
        return len(self.get_all_phases())

    def get_phase_info(self, chapter: int, phase: int) -> Optional[Dict]:
        """Retorna informações de uma fase específica"""
        phases = self.get_chapter_phases(chapter)
        for p in phases:
            if p["number"] == phase:
                return p
        return None

    def get_max_phase_per_chapter(self) -> Dict[int, int]:
        """Retorna o número máximo de fase por capítulo"""
        catalog = self.get_all_phases()
        return {chapter: len(phases) for chapter, phases in catalog.items()}

    def refresh(self):
        """Força o recarregamento do catálogo"""
        self.cache = None
        self.get_all_phases()


# Instância global
phase_catalog = PhaseCatalog()