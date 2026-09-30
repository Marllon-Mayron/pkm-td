# src/managers/progress.py

"""
Sistema de progresso do jogador — Suporta REGIÕES.

Chave de fase: "R:C:P"  (ex: "1:1:1" = Kanto, Cap 1, Fase 1)

Auto-cura:
  - Qualquer ID no formato antigo ("1-1") é convertido para "1:1:1" no load
  - A conversão é persistida de volta no save
"""
import json
import os
from typing import Dict, List, Optional

from src.config.regions import (
    DEFAULT_REGION_ID, make_phase_id, parse_phase_id, normalize_phase_id,
)


class ProgressManager:
    def __init__(self):
        from src.managers.save_manager import save_manager
        from src.config.settings import settings

        self.save_manager = save_manager
        self.settings = settings
        self.progress = self._load_from_save_manager()
        self._normalize_in_place()
        # Persiste imediatamente o formato normalizado
        self._sync_with_save_manager()

    # ==================================================================
    # CARGA / NORMALIZACAO
    # ==================================================================
    def _load_from_save_manager(self) -> Dict:
        gs = self.save_manager.save_data.get("game_state", {})

        unlocked = [str(p) for p in gs.get("unlocked_phases", [])]
        completed = [str(p) for p in gs.get("completed_phases", [])]
        stars = {str(k): v for k, v in gs.get("stars", {}).items()}

        # Fallback: garante 1:1:1 sempre
        if not unlocked:
            unlocked = [make_phase_id(DEFAULT_REGION_ID, 1, 1)]

        return {
            "unlocked_phases": unlocked,
            "completed_phases": completed,
            "current_region": int(gs.get("current_region", DEFAULT_REGION_ID)),
            "current_chapter": int(gs.get("current_chapter", 1)),
            "current_phase": int(gs.get("current_phase", 1)),
            "stars": stars,
        }

    def _normalize_in_place(self):
        """Converte tudo para o formato novo (R:C:P)."""
        before_unlocked = list(self.progress["unlocked_phases"])
        before_completed = list(self.progress["completed_phases"])

        self.progress["unlocked_phases"] = sorted({
            normalize_phase_id(p) for p in self.progress["unlocked_phases"]
        })
        self.progress["completed_phases"] = sorted({
            normalize_phase_id(p) for p in self.progress["completed_phases"]
        })

        new_stars = {}
        for pid, val in self.progress["stars"].items():
            new_stars[normalize_phase_id(pid)] = val
        self.progress["stars"] = new_stars

        # Garante 1:1:1 presente
        if "1:1:1" not in self.progress["unlocked_phases"]:
            self.progress["unlocked_phases"].append("1:1:1")
            self.progress["unlocked_phases"].sort()

        if before_unlocked != self.progress["unlocked_phases"]:
            print(f"[PROGRESS] IDs normalizados: {before_unlocked} -> {self.progress['unlocked_phases']}")

    # ==================================================================
    # SYNC COM SAVE
    # ==================================================================
    def _sync_with_save_manager(self):
        if "game_state" not in self.save_manager.save_data:
            self.save_manager.save_data["game_state"] = {}

        gs = self.save_manager.save_data["game_state"]
        gs["unlocked_phases"] = list(self.progress["unlocked_phases"])
        gs["completed_phases"] = list(self.progress["completed_phases"])
        gs["stars"] = dict(self.progress["stars"])
        gs["current_region"] = self.progress.get("current_region", DEFAULT_REGION_ID)
        gs["current_chapter"] = self.progress["current_chapter"]
        gs["current_phase"] = self.progress["current_phase"]

        self.save_manager.save_data["settings"] = {
            "sfx_volume": self.settings.sfx_volume,
            "music_volume": self.settings.music_volume,
            "music_enabled": self.settings.music_enabled,
            "sfx_enabled": self.settings.sfx_enabled,
            "ambient_volume": getattr(self.settings, 'ambient_volume', 0.5),
            "ambient_enabled": getattr(self.settings, 'ambient_enabled', True),
            "fullscreen": self.settings.fullscreen,
            "vsync": self.settings.vsync,
            "target_fps": self.settings.target_fps,
        }

        if self.save_manager.current_save_file:
            filepath = os.path.join(
                self.save_manager.save_dir,
                f"save_{self.save_manager.current_save_file}.json"
            )
            try:
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(self.save_manager.save_data, f, indent=2, ensure_ascii=False)
            except Exception as e:
                print(f"[ERRO] Falha ao sincronizar progresso: {e}")

    def _load_settings_from_save(self):
        if not self.save_manager.current_save_file:
            return False
        data = self.save_manager.save_data.get("settings", {})
        if not data:
            return False

        self.settings.sfx_volume = data.get("sfx_volume", 0.7)
        self.settings.music_volume = data.get("music_volume", 0.5)
        self.settings.music_enabled = data.get("music_enabled", True)
        self.settings.sfx_enabled = data.get("sfx_enabled", True)
        self.settings.ambient_volume = data.get("ambient_volume", 0.5)
        self.settings.ambient_enabled = data.get("ambient_enabled", True)
        self.settings.fullscreen = data.get("fullscreen", False)
        self.settings.vsync = data.get("vsync", True)
        self.settings.target_fps = data.get("target_fps", 60)

        try:
            from src.managers.sounds.sound_manager import sound_manager
            sound_manager.set_sfx_volume(
                self.settings.sfx_volume if self.settings.sfx_enabled else 0
            )
            sound_manager.set_music_volume(
                self.settings.music_volume if self.settings.music_enabled else 0
            )
        except Exception:
            pass
        return True

    # ==================================================================
    # CONSULTAS
    # ==================================================================
    def is_phase_unlocked(self, phase_id) -> bool:
        pid = normalize_phase_id(str(phase_id))
        return pid in self.progress["unlocked_phases"]

    def is_phase_completed(self, phase_id) -> bool:
        pid = normalize_phase_id(str(phase_id))
        return pid in self.progress["completed_phases"]

    def get_phase_stars(self, phase_id) -> int:
        return self.progress["stars"].get(normalize_phase_id(str(phase_id)), 0)

    def get_completed_in_region(self, region_id: int) -> List[str]:
        rid = int(region_id)
        return [pid for pid in self.progress["completed_phases"]
                if parse_phase_id(pid)[0] == rid]

    def get_chapter_progress(self, *args) -> Dict:
        """
        Aceita:
          - (chapter_id, phase_ids_list)             [legado]
          - (region_id, chapter_id, phase_ids_list)  [novo]
        """
        if len(args) == 2 and isinstance(args[1], (list, tuple, set)):
            # Assinatura legada
            phase_ids = list(args[1])
        elif len(args) == 3:
            _, _, phase_ids = args
            phase_ids = list(phase_ids or [])
        else:
            phase_ids = []

        total = len(phase_ids)
        unlocked = sum(1 for p in phase_ids if self.is_phase_unlocked(p))
        completed = sum(1 for p in phase_ids if self.is_phase_completed(p))
        return {
            "total": total,
            "unlocked": unlocked,
            "completed": completed,
            "percentage": (completed / total * 100) if total else 0,
        }

    # ==================================================================
    # MUTACOES
    # ==================================================================
    def unlock_specific_phase(self, phase_id) -> bool:
        pid = normalize_phase_id(str(phase_id))
        if pid not in self.progress["unlocked_phases"]:
            self.progress["unlocked_phases"].append(pid)
            self.progress["unlocked_phases"].sort()
            self._sync_with_save_manager()
            print(f"[PROGRESS] Desbloqueada: {pid}")
            return True
        return False

    def complete_phase(self, phase_id, stars: int = 0):
        pid = normalize_phase_id(str(phase_id))

        print(f"\n[PROGRESS] ===== Completando {pid} ({stars} estrelas) =====")

        if pid in self.progress["completed_phases"]:
            if stars > self.progress["stars"].get(pid, 0):
                self.progress["stars"][pid] = stars
                print(f"[PROGRESS] Nova pontuação em {pid}: {stars}")
        else:
            self.progress["completed_phases"].append(pid)
            self.progress["completed_phases"].sort()
            self.progress["stars"][pid] = stars
            self._unlock_next_phase(pid)

        self._sync_with_save_manager()
        print(f"[PROGRESS] Sync concluído")

    def _unlock_next_phase(self, phase_id: str) -> Optional[str]:
        """Desbloqueia a próxima fase do mesmo capítulo ou do próximo."""
        r, c, p = parse_phase_id(phase_id)
        from src.config.phase_catalog import phase_catalog

        # Tentar próxima fase no mesmo capítulo
        phases = phase_catalog.get_chapter_phases(r, c)
        if phases:
            nums = sorted(pp["number"] for pp in phases)
            if p in nums:
                idx = nums.index(p)
                if idx + 1 < len(nums):
                    nxt = make_phase_id(r, c, nums[idx + 1])
                    self.unlock_specific_phase(nxt)
                    return nxt

        # Fim do capítulo → próximo capítulo da mesma região
        all_in_region = phase_catalog.get_all_phases(r)
        if all_in_region:
            chapters = sorted(all_in_region.keys())
            if c in chapters:
                ci = chapters.index(c)
                if ci + 1 < len(chapters):
                    nxt_ch = chapters[ci + 1]
                    nxt_phases = all_in_region[nxt_ch]
                    if nxt_phases:
                        first = min(pp["number"] for pp in nxt_phases)
                        nxt = make_phase_id(r, nxt_ch, first)
                        self.unlock_specific_phase(nxt)
                        return nxt

        print("[PROGRESS] Todas as fases dessa região foram concluídas!")
        return None

    def get_next_phase(self, phase_id) -> Optional[str]:
        """Só consulta, não desbloqueia."""
        r, c, p = parse_phase_id(phase_id)
        from src.config.phase_catalog import phase_catalog

        phases = phase_catalog.get_chapter_phases(r, c)
        if phases:
            nums = sorted(pp["number"] for pp in phases)
            if p in nums and nums.index(p) + 1 < len(nums):
                return make_phase_id(r, c, nums[nums.index(p) + 1])

        all_in_region = phase_catalog.get_all_phases(r)
        if all_in_region:
            chapters = sorted(all_in_region.keys())
            if c in chapters and chapters.index(c) + 1 < len(chapters):
                nxt_ch = chapters[chapters.index(c) + 1]
                nxt_phases = all_in_region[nxt_ch]
                if nxt_phases:
                    first = min(pp["number"] for pp in nxt_phases)
                    return make_phase_id(r, nxt_ch, first)
        return None

    def unlock_next_phase(self, completed_phase_id) -> bool:
        return self._unlock_next_phase(normalize_phase_id(str(completed_phase_id))) is not None

    # ==================================================================
    # RESET / RELOAD
    # ==================================================================
    def reset_progress(self):
        self.progress = {
            "unlocked_phases": [make_phase_id(DEFAULT_REGION_ID, 1, 1)],
            "completed_phases": [],
            "current_region": DEFAULT_REGION_ID,
            "current_chapter": 1,
            "current_phase": 1,
            "stars": {},
        }
        self._sync_with_save_manager()
        print("[PROGRESS] Reset completo. Fase 1:1:1 desbloqueada.")

    def reload_progress(self):
        self.progress = self._load_from_save_manager()
        self._normalize_in_place()
        self._load_settings_from_save()
        self._sync_with_save_manager()  # persiste já normalizado
        print(f"[PROGRESS] Recarregado. Unlocked: {self.progress['unlocked_phases']}")


progress_manager = ProgressManager()