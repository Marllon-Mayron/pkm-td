# src/scenes/phase_selector/phase_select_logic.py
"""
Lógica da Seleção de Fase — dados, filtros, progresso, estrelas.
Sem Pygame na renderização. Só orquestra dados.
"""
import pygame

from src.config.progress import progress_manager
from src.config.phase_catalog import phase_catalog
from src.config.global_settings import DEBUG_MODE
from src.config.regions import (
    RegionCatalog, DEFAULT_REGION_ID, make_phase_id, parse_phase_id,
)


class PhaseSelectLogic:
    """
    Mantém o estado da tela de seleção de fases:
      - regiões / capítulos / fases (via phase_catalog)
      - progresso + estrelas (via progress_manager)
      - seleção atual
      - cache de ícones míticos e sprites de estrela
    """

    def __init__(self, game):
        self.game = game
        self.player = getattr(game, "player", None)

        self.progress = progress_manager
        self.catalog = phase_catalog

        self._phase_name_cache: dict = {}
        self._mythical_icon_cache: dict = {}

        # Pré-carrega sprites de estrela (pixel art)
        try:
            from src.ui.utils.icon_loader import get_phase_star_surfaces
            self._star_filled, self._star_empty = get_phase_star_surfaces(28)
        except Exception as e:
            print(f"[PhaseSelectLogic] Falha ao carregar sprites de estrela: {e}")
            self._star_filled = None
            self._star_empty = None

        # ===== Estado atual =====
        self.current_region_id: int = DEFAULT_REGION_ID
        self.current_chapter_id: int = 1
        self.selected_phase_number: int | None = None

        self.available_regions: list[int] = []
        self.available_chapters: list[int] = []
        self.phases: list[dict] = []          # fases do capítulo atual

        if self.player:
            saved = getattr(self.player, "current_region", DEFAULT_REGION_ID)
            self.current_region_id = saved

        self.refresh_all()

    # =================================================================
    # DESCOBERTA DE DADOS
    # =================================================================
    def _discover_regions(self) -> list[int]:
        regions = []
        try:
            regions = self.catalog.get_all_regions()
        except (AttributeError, TypeError):
            regions = []
        if not regions:
            try:
                from src.editor.phase_exporter import phase_exporter
                regions = phase_exporter.list_regions_with_phases()
            except Exception:
                regions = []
        if not regions:
            regions = [DEFAULT_REGION_ID]
        return sorted(set(int(r) for r in regions))

    def _discover_chapters(self, region_id: int) -> list[int]:
        chapters = []
        try:
            all_phases = self.catalog.get_all_phases(region_id)
            if all_phases:
                chapters = sorted(int(c) for c in all_phases.keys())
        except (TypeError, AttributeError):
            chapters = []
        if not chapters:
            try:
                from src.editor.phase_exporter import phase_exporter
                phases = phase_exporter.list_phases(region=region_id)
                chapters = sorted({int(c) for (c, p) in phases})
            except Exception:
                chapters = []
        if not chapters:
            chapters = [1]
        return chapters

    def _get_chapter_phases(self, region_id: int, chapter_id: int) -> list[dict]:
        try:
            phases = self.catalog.get_chapter_phases(region_id, chapter_id)
            if phases and isinstance(phases[0], dict):
                return phases
        except (TypeError, AttributeError):
            pass

        try:
            phases = self.catalog.get_chapter_phases(chapter_id)
            if phases and isinstance(phases[0], dict):
                result = []
                for p in phases:
                    result.append({
                        "number":  p.get("number", 1),
                        "name":    p.get("name", f"Fase {p.get('number', 1)}"),
                        "chapter": chapter_id,
                    })
                return result
        except (TypeError, AttributeError):
            pass

        try:
            from src.editor.phase_exporter import phase_exporter
            nums = phase_exporter.list_phases(region=region_id, chapter=chapter_id)
            out = []
            for n in nums:
                out.append({
                    "number":  n,
                    "name":    self._get_phase_name_from_disk(region_id, chapter_id, n),
                    "chapter": chapter_id,
                })
            return out
        except Exception:
            return []

    def _get_phase_name_from_disk(self, region_id, chapter_id, phase_num) -> str:
        key = (region_id, chapter_id, phase_num)
        if key in self._phase_name_cache:
            return self._phase_name_cache[key]
        name = f"Fase {chapter_id}-{phase_num}"
        try:
            from src.editor.phase_exporter import phase_exporter
            data = phase_exporter.load_phase(chapter_id, phase_num, region=region_id)
            if data and data.get("name"):
                name = data["name"]
        except Exception:
            pass
        self._phase_name_cache[key] = name
        return name

    def _get_chapter_progress(self, region_id, chapter_id, phase_ids) -> dict:
        completed = 0
        for pid in phase_ids:
            try:
                if self.progress.is_phase_completed(pid):
                    completed += 1
            except Exception:
                pass
        return {"completed": completed, "total": len(phase_ids)}

    # =================================================================
    # REFRESH
    # =================================================================
    def refresh_all(self):
        try:
            self.progress.reload_progress()
        except Exception:
            pass
        try:
            self.catalog.refresh()
        except Exception:
            pass

        self.available_regions = self._discover_regions()

        if self.player:
            saved = getattr(self.player, "current_region", DEFAULT_REGION_ID)
            self.current_region_id = (
                saved if saved in self.available_regions
                else self.available_regions[0]
            )
        else:
            self.current_region_id = self.available_regions[0]

        self._refresh_chapters()

    def _refresh_chapters(self):
        self.available_chapters = self._discover_chapters(self.current_region_id)

        saved_ch = getattr(self.player, "chapter_page_num", None) if self.player else None
        if saved_ch in self.available_chapters:
            self.current_chapter_id = saved_ch
        else:
            self.current_chapter_id = (
                self.available_chapters[0] if self.available_chapters else 1
            )

        self._refresh_phases()

    def _refresh_phases(self):
        self.phases = self._get_chapter_phases(
            self.current_region_id, self.current_chapter_id
        )

        valid_nums = {p["number"] for p in self.phases}
        if self.selected_phase_number not in valid_nums:
            self.selected_phase_number = (
                self.phases[0]["number"] if self.phases else None
            )

    # =================================================================
    # Trocar região / capítulo
    # =================================================================
    def set_region(self, region_id: int):
        if region_id == self.current_region_id:
            return
        self.current_region_id = region_id
        if self.player:
            self.player.current_region = region_id
        self._refresh_chapters()

    def set_chapter(self, chapter_id: int):
        if chapter_id == self.current_chapter_id:
            return
        self.current_chapter_id = chapter_id
        if self.player:
            self.player.chapter_page_num = chapter_id
        self._refresh_phases()

    def select_phase(self, phase_number: int):
        self.selected_phase_number = phase_number

    # =================================================================
    # Labels dos TabPanels
    # =================================================================
    def region_tab_labels(self) -> list[str]:
        return [RegionCatalog.get_name(r) for r in self.available_regions]

    def current_region_label(self) -> str:
        return RegionCatalog.get_name(self.current_region_id)

    def region_id_from_label(self, label: str) -> int | None:
        for rid in self.available_regions:
            if RegionCatalog.get_name(rid) == label:
                return rid
        return None

    def chapter_tab_labels(self) -> list[str]:
        # Limpo: só "CAP 1", "CAP 2", ...
        return [f"CAP {ch}" for ch in self.available_chapters]

    def current_chapter_label(self) -> str:
        return f"CAP {self.current_chapter_id}"

    def chapter_id_from_label(self, label: str) -> int | None:
        # "CAP 3" -> 3
        try:
            return int(str(label).split()[-1])
        except (ValueError, IndexError):
            return None

    # =================================================================
    # Stats
    # =================================================================
    def total_phases(self) -> int:
        return len(self.phases)

    def total_completed(self) -> int:
        n = 0
        for p in self.phases:
            pid = make_phase_id(
                self.current_region_id, self.current_chapter_id, p["number"]
            )
            try:
                if self.progress.is_phase_completed(pid):
                    n += 1
            except Exception:
                pass
        return n

    # =================================================================
    # Estrelas
    # =================================================================
    def _get_stars(self, phase_id: str) -> int:
        """Retorna 0..3 estrelas da fase."""
        for meth in ("get_phase_stars", "get_stars", "get_stars_for"):
            fn = getattr(self.progress, meth, None)
            if callable(fn):
                try:
                    v = fn(phase_id)
                    if v is not None:
                        return max(0, min(3, int(v)))
                except Exception:
                    pass

        try:
            data = getattr(self.progress, "progress", None) or {}
            stars = data.get("stars", {}) or {}
            return max(0, min(3, int(stars.get(phase_id, 0))))
        except Exception:
            return 0

    def _build_star_triplet(self, stars: int):
        """Retorna (star_1, star_2, star_3) Surfaces — filled/empty."""
        if self._star_filled is None or self._star_empty is None:
            return None, None, None
        s1 = self._star_filled if stars >= 1 else self._star_empty
        s2 = self._star_filled if stars >= 2 else self._star_empty
        s3 = self._star_filled if stars >= 3 else self._star_empty
        return s1, s2, s3

    # =================================================================
    # CardGrid — item_dict
    # =================================================================
    def item_dict(self, index: int) -> dict:
        phase = self.phases[index]
        number = phase["number"]

        phase_id = make_phase_id(
            self.current_region_id, self.current_chapter_id, number
        )

        try:
            unlocked = self.progress.is_phase_unlocked(phase_id)
            completed = self.progress.is_phase_completed(phase_id)
        except Exception:
            unlocked = False
            completed = False

        stars = self._get_stars(phase_id)
        is_selected = (number == self.selected_phase_number)

        # -------- Paleta por estado (viva, colorida) --------
        if not unlocked:
            bg          = "#181B24"
            border      = "#2E3546"
            accent      = "#5A6278"
        elif completed:
            bg          = "#14301E"
            border      = "#42A858"
            accent      = "#6ADE88"
        elif is_selected:
            bg          = "#2A2010"
            border      = "#F8B030"
            accent      = "#FFD24A"
        else:
            bg          = "#14223C"
            border      = "#3A6AB8"
            accent      = "#5AA0F0"

        star_1, star_2, star_3 = self._build_star_triplet(stars)
        mythical_icon = self._get_mythical_icon_for_phase(phase_id)
        name = phase.get("name", f"Fase {number}")

        return {
            "index":         index,
            "phase_id":      phase_id,
            "phase_number":  f"{number:02d}",
            "display_id":    phase_id,
            "name":          name,

            "bg_color":      bg,
            "border_color":  border,
            "accent_color":  accent,

            "stars":         stars,
            "star_1":        star_1,
            "star_2":        star_2,
            "star_3":        star_3,

            "locked":        not unlocked,
            "completed":     completed,
            "is_selected":   is_selected,

            "mythical_icon": mythical_icon,
            "has_mythical":  mythical_icon is not None,
        }

    def _get_mythical_icon_for_phase(self, phase_id: str):
        """Retorna Surface com o ícone mítico (ou None)."""
        if phase_id in self._mythical_icon_cache:
            return self._mythical_icon_cache[phase_id]

        pending_id = (
            getattr(self.player, "pending_mythical_id", None)
            if self.player else None
        )
        if pending_id is None:
            self._mythical_icon_cache[phase_id] = None
            return None

        try:
            from src.data.mythical_catalog import MythicalCatalog
            entry = MythicalCatalog.get_mythical(pending_id)
            if entry is None or phase_id not in entry.phases:
                self._mythical_icon_cache[phase_id] = None
                return None

            from src.data.pokedex import Pokedex
            portrait = Pokedex().get_portrait(pending_id, "happy", False)
            if portrait is None:
                self._mythical_icon_cache[phase_id] = None
                return None

            size = 34
            portrait = pygame.transform.scale(portrait, (size, size))

            pad = 4
            box = size + pad * 2
            surf = pygame.Surface((box, box), pygame.SRCALPHA)
            surf.fill((255, 215, 0, 200))
            pygame.draw.rect(surf, (255, 215, 0), surf.get_rect(),
                             2, border_radius=6)
            surf.blit(portrait, (pad, pad))

            self._mythical_icon_cache[phase_id] = surf
            return surf
        except Exception as e:
            print(f"[PhaseSelectLogic] mythical icon erro: {e}")
            self._mythical_icon_cache[phase_id] = None
            return None

    # =================================================================
    # Detail Panel
    # =================================================================
    def get_detail_state(self) -> dict:
        phase = self.get_selected_phase()
        if phase is None:
            return {
                "valid": False,
                "name": "—",
                "number": "",
                "phase_id": "",
                "status_text": "—",
                "status_color": (80, 85, 96),
                "stars": 0,
                "star_1": None,
                "star_2": None,
                "star_3": None,
                "description": "Selecione uma fase.",
                "can_play": False,
                "unlocked": False,
                "completed": False,
                "image": None,
            }

        number = phase["number"]
        phase_id = make_phase_id(
            self.current_region_id, self.current_chapter_id, number
        )

        try:
            unlocked = self.progress.is_phase_unlocked(phase_id)
            completed = self.progress.is_phase_completed(phase_id)
        except Exception:
            unlocked = False
            completed = False

        stars = self._get_stars(phase_id)

        if not unlocked:
            status_text  = "BLOQUEADA"
            status_color = (120, 120, 130)
        elif completed:
            status_text  = "CONCLUIDA"
            status_color = (106, 222, 136)
        else:
            status_text  = "DISPONIVEL"
            status_color = (90, 160, 240)

        star_1, star_2, star_3 = self._build_star_triplet(stars)

        description = phase.get("description", "")
        if not description:
            if not unlocked:
                description = "Complete a fase anterior para desbloquear."
            elif completed:
                description = f"Voce conquistou {stars}/3 estrelas nesta fase."
            else:
                description = f"Fase {number} do capitulo {self.current_chapter_id}."

        return {
            "valid":         True,
            "name":          phase.get("name", f"Fase {number}"),
            "number":        phase_id,
            "phase_id":      phase_id,
            "status_text":   status_text,
            "status_color":  status_color,
            "stars":         stars,
            "star_1":        star_1,
            "star_2":        star_2,
            "star_3":        star_3,
            "description":   description,
            "can_play":      unlocked,
            "unlocked":      unlocked,
            "completed":     completed,
            "image":         self._get_mythical_icon_for_phase(phase_id),
        }

    def get_selected_phase(self) -> dict | None:
        if self.selected_phase_number is None:
            return None
        for p in self.phases:
            if p["number"] == self.selected_phase_number:
                return p
        return None

    # =================================================================
    # Utilidades expostas para a scene
    # =================================================================
    def is_incubator_unlocked(self) -> bool:
        try:
            return self.progress.is_phase_completed(
                make_phase_id(DEFAULT_REGION_ID, 1, 5)
            )
        except Exception:
            try:
                return self.progress.is_phase_completed("7-2")
            except Exception:
                return False

    def reset_progress(self):
        if not DEBUG_MODE:
            return
        try:
            self.progress.reset_progress()
            self.catalog.refresh()
        except Exception:
            pass
        self.refresh_all()

    def debug_unlock_next(self):
        if not DEBUG_MODE:
            return
        for p in self.phases:
            pid = make_phase_id(
                self.current_region_id, self.current_chapter_id, p["number"]
            )
            try:
                if not self.progress.is_phase_unlocked(pid):
                    self.progress.unlock_specific_phase(pid)
                    return
            except Exception:
                pass

    def debug_unlock_all(self):
        if not DEBUG_MODE:
            return
        for rid in self.available_regions:
            chapters = self._discover_chapters(rid)
            for ch in chapters:
                for p in self._get_chapter_phases(rid, ch):
                    pid = make_phase_id(rid, ch, p["number"])
                    try:
                        self.progress.unlock_specific_phase(pid)
                    except Exception:
                        pass