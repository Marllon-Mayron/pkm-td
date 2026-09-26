# src/data/icon_loader.py

import pygame
from pathlib import Path
from typing import Optional, Dict, List, Tuple


class PokemonIconLoader:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.base_path = Path(__file__).parent.parent.parent / "res" / "PokemonSprites" / "IconPoke"

        self._icon_cache: Dict[int, List[pygame.Surface]] = {}
        # {(pid, size): [f0_scaled, f1_scaled]}
        self._scaled_cache: Dict[Tuple[int, int], List[pygame.Surface]] = {}
        self._fallback_frames: Optional[List[pygame.Surface]] = None
        self._fallback_scaled: Dict[int, List[pygame.Surface]] = {}

        self._frame_width = 64
        self._frame_height = 64
        self._num_frames = 2

    def _safe_convert_alpha(self, surf):
        if pygame.display.get_surface() is not None:
            try:
                return surf.convert_alpha()
            except Exception:
                pass
        return surf

    def _get_icon_path(self, pid: int) -> Path:
        return self.base_path / f"icon{pid:03d}.png"

    def _get_fallback_path(self) -> Path:
        return self.base_path / "icon000.png"

    def _slice_frames(self, sheet):
        sw, sh = sheet.get_size()
        fw = sw // self._num_frames if sw >= self._num_frames else sw
        fh = sh
        frames = []
        for i in range(self._num_frames):
            x = i * fw
            if x + fw > sw:
                break
            rect = pygame.Rect(x, 0, fw, fh)
            try:
                frames.append(sheet.subsurface(rect).copy())
            except Exception:
                s = pygame.Surface((fw, fh), pygame.SRCALPHA)
                s.blit(sheet, (0, 0), rect)
                frames.append(s)
        return frames or [sheet]

    def _load_from_disk(self, path: Path):
        if not path.exists():
            return None
        try:
            sheet = pygame.image.load(str(path))
            sheet = self._safe_convert_alpha(sheet)
            return self._slice_frames(sheet)
        except Exception as e:
            print(f"[ICON_LOADER] Erro {path}: {e}")
            return None

    def get_fallback_frames(self):
        if self._fallback_frames is None:
            frames = self._load_from_disk(self._get_fallback_path())
            if frames is None:
                s = pygame.Surface((64, 64), pygame.SRCALPHA)
                pygame.draw.rect(s, (100, 100, 120), (0, 0, 64, 64), border_radius=8)
                pygame.draw.rect(s, (200, 200, 220), (0, 0, 64, 64), 3, border_radius=8)
                frames = [s]
            self._fallback_frames = frames
        return self._fallback_frames

    def get_icon_frames(self, pid: int) -> List[pygame.Surface]:
        if pid in self._icon_cache:
            return self._icon_cache[pid]
        frames = self._load_from_disk(self._get_icon_path(pid))
        if frames is None:
            frames = self.get_fallback_frames()
        self._icon_cache[pid] = frames
        return frames

    def get_animated_icon(self, pid: int, size: int,
                          time_ms: int, frame_duration_ms: int = 400):
        """
        Retorna o frame atual já escalado. O smoothscale é feito UMA
        vez por (pid, size) e depois só alternamos entre os frames.
        """
        key = (pid, size)
        scaled = self._scaled_cache.get(key)

        if scaled is None:
            # Fallback escalado cacheado separadamente
            if pid in self._icon_cache or self._get_icon_path(pid).exists():
                frames = self.get_icon_frames(pid)
                scaled = [pygame.transform.smoothscale(f, (size, size)) for f in frames]
            else:
                # usa fallback
                if size not in self._fallback_scaled:
                    fb = self.get_fallback_frames()
                    self._fallback_scaled[size] = [
                        pygame.transform.smoothscale(f, (size, size)) for f in fb
                    ]
                scaled = self._fallback_scaled[size]
            self._scaled_cache[key] = scaled

        if len(scaled) <= 1:
            return scaled[0]
        idx = (time_ms // frame_duration_ms) % len(scaled)
        return scaled[idx]

    def get_static_icon(self, pid: int, size: int):
        key = (pid, size)
        scaled = self._scaled_cache.get(key)
        if scaled is None:
            frames = self.get_icon_frames(pid)
            scaled = [pygame.transform.smoothscale(f, (size, size)) for f in frames]
            self._scaled_cache[key] = scaled
        return scaled[0]

    def preload(self, pids):
        for pid in pids:
            self.get_icon_frames(pid)

    def clear_cache(self):
        self._icon_cache.clear()
        self._scaled_cache.clear()
        self._fallback_frames = None
        self._fallback_scaled.clear()


pokemon_icon_loader = PokemonIconLoader()