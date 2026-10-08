"""Exporta a animacao atual como MP4.

Usa imageio + imageio-ffmpeg: o binario do ffmpeg vem EMPACOTADO no
proprio pip install (`pip install imageio-ffmpeg`). Nada de ffmpeg no
PATH, nada de winget, nada externo.

Renderiza cada frame com o mesmo Animator do preview: camera, atores,
layers, mensagens, filtros — tudo identico ao que voce ve apertando P.
"""
from pathlib import Path

import pygame
import numpy as np
import imageio

from src.anim.animator import Animator
from src.anim.layer import _parse_hex_color
from src.config.paths import RES_PATH




# =====================================================================
class _ExportScreenManager:
    """Screen manager fake pro Animator achar o viewport."""
    def __init__(self, rect):
        self.viewport_x = rect.x
        self.viewport_y = rect.y
        self.viewport_width = rect.width
        self.viewport_height = rect.height
        self.render_scale = 1.0
        self.render_width = rect.width
        self.render_height = rect.height


# =====================================================================
class AnimationExporter:
    ASPECTS = {
        "youtube": (960, 540),  # 16:9 horizontal
        "hd": (1920, 1080),  # 1080p
        "tiktok": (540, 960),  # 9:16 vertical
        "square": (720, 720),  # 1:1
    }

    def __init__(self, controller):
        self.controller = controller
        self.exporting = False
        self.progress = 0.0
        self.status = ""
        self.cancel_requested = False

    # =================================================================
    @staticmethod
    def is_available() -> bool:
        """imageio e imageio-ffmpeg estao instalados?"""
        try:
            import imageio  # noqa
            import imageio_ffmpeg  # noqa
            return True
        except ImportError:
            return False

    @staticmethod
    def install_hint() -> str:
        return "Instale: pip install imageio imageio-ffmpeg numpy"

    # =================================================================
    def default_out_dir(self) -> Path:
        anim = self.controller.current_anim
        d = RES_PATH / "animations" / anim.category / "_exports"
        d.mkdir(parents=True, exist_ok=True)
        return d

    def default_name(self) -> str:
        return self.controller.current_anim.name or "animacao"

    # =================================================================
    def _make_animator(self, w, h):
        return Animator(
            definition=self.controller.current_anim,
            anchor_target=None, anchor_attacker=None,
            screen_pos=(w // 2, h // 2),
            loop_override=False,
            zoom=1.0,
        )

    def _make_surface(self, w, h):
        try:
            return pygame.Surface((w, h), depth=24).convert()
        except Exception:
            return pygame.Surface((w, h), depth=24)

    def _render_frame(self, surface, animator, frame):
        bg = self.controller.current_anim.background or {}
        t = bg.get("type", "none")

        if t == "color":
            col = _parse_hex_color(bg.get("color", "#101828"))
            surface.fill(col)
        elif t == "image":
            img = self.controller._load_bg_surface(bg.get("image", ""))
            if img is not None:
                surface.blit(
                    pygame.transform.smoothscale(img, surface.get_size()),
                    (0, 0))
            else:
                surface.fill((18, 22, 34))
        else:
            surface.fill((18, 22, 34))

        animator.current_frame = float(frame)
        sm = _ExportScreenManager(surface.get_rect())
        animator.render(surface, camera=None, screen_manager=sm)

        try:
            dim = int(bg.get("dim", 0) or 0)
        except (TypeError, ValueError):
            dim = 0
        if dim > 0:
            ov = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
            ov.fill((0, 0, 0, dim))
            surface.blit(ov, (0, 0))

    # =================================================================
    # EXPORT MP4
    # =================================================================
    def export_mp4(self, out_path=None, aspect="youtube", fps=None,
                   crf=18, preset="medium"):
        if not self.is_available():
            self.status = self.install_hint()
            return False

        size = self.ASPECTS.get(aspect, (960, 540))
        anim = self.controller.current_anim
        fps = int(fps or anim.fps or 60)
        w, h = size

        if out_path is None:
            suffix = "" if aspect == "youtube" else f"_{aspect}"
            out_path = self.default_out_dir() / f"{self.default_name()}{suffix}.mp4"
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        self.exporting = True
        self.progress = 0.0
        self.cancel_requested = False
        self.status = f"Exportando {aspect}: {out_path.name}"

        animator = self._make_animator(w, h)
        surface = self._make_surface(w, h)
        total = max(1, anim.duration_frames)

        try:
            writer = imageio.get_writer(
                str(out_path), fps=fps, codec="libx264", quality=None,
                ffmpeg_params=[
                    "-crf", str(int(crf)),
                    "-preset", str(preset),
                    "-pix_fmt", "yuv420p",
                ],
                macro_block_size=1,
            )
        except Exception as e:
            self.exporting = False
            self.status = f"Erro abrindo writer: {e}"
            return False

        ok = True
        try:
            for f in range(0, total + 1):
                if self.cancel_requested:
                    ok = False
                    break
                self._render_frame(surface, animator, f)
                arr = pygame.surfarray.array3d(surface)
                arr = np.transpose(arr, (1, 0, 2))
                writer.append_data(arr)
                self.progress = (f + 1) / (total + 1)
                self.status = f"{out_path.name}  {int(self.progress * 100)}%"
                if f % 4 == 0:
                    self._pump_events()
                    self._draw_progress_overlay()
        except Exception as e:
            ok = False
            self.status = f"Erro no frame {f}: {e}"
        finally:
            try:
                writer.close()
            except Exception:
                pass
            self.exporting = False

        if not ok:
            try:
                out_path.unlink(missing_ok=True)
            except Exception:
                pass
            if self.cancel_requested:
                self.status = "Export cancelado."
            return False

        size_mb = out_path.stat().st_size / (1024 * 1024)
        self.status = f"OK: {out_path}  ({size_mb:.1f} MB)"
        return True

    # =================================================================
    # EVENTS + OVERLAY (mesmo do anterior)
    # =================================================================
    def _pump_events(self):
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                self.cancel_requested = True
            elif ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
                self.cancel_requested = True

    def _draw_progress_overlay(self):
        screen = pygame.display.get_surface()
        if screen is None:
            return
        w, h = screen.get_size()
        ov = pygame.Surface((w, h), pygame.SRCALPHA)
        ov.fill((0, 0, 0, 200))
        screen.blit(ov, (0, 0))

        pw, ph = 560, 160
        px = (w - pw) // 2
        py = (h - ph) // 2
        panel = pygame.Rect(px, py, pw, ph)
        pygame.draw.rect(screen, (22, 26, 40), panel, border_radius=12)
        pygame.draw.rect(screen, (248, 176, 48), panel, 2, border_radius=12)

        try:
            from src.ui.theme import FontBook
            f_title = FontBook.get(18, bold=True)
            f_body = FontBook.get(13)
        except Exception:
            f_title = pygame.font.Font(None, 22)
            f_body = pygame.font.Font(None, 16)

        t = f_title.render("EXPORTANDO MP4", True, (248, 176, 48))
        screen.blit(t, (px + 24, py + 20))

        s = f_body.render(self.status, True, (220, 228, 240))
        screen.blit(s, (px + 24, py + 54))

        bar = pygame.Rect(px + 24, py + 90, pw - 48, 22)
        pygame.draw.rect(screen, (40, 48, 66), bar, border_radius=6)
        fill_w = int(bar.width * self.progress)
        if fill_w > 0:
            pygame.draw.rect(
                screen, (100, 200, 100),
                pygame.Rect(bar.x, bar.y, fill_w, bar.height),
                border_radius=6)
        pygame.draw.rect(screen, (90, 108, 150), bar, 1, border_radius=6)

        hint = f_body.render("ESC para cancelar", True, (170, 180, 200))
        screen.blit(hint, (px + 24, py + 122))

        pygame.display.flip()