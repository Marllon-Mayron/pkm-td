# src/scenes/profile_scene/photo_gallery_logic.py
"""
Lógica da galeria de fotos — estado + carregamento + paginação.
Sem render de UI, sem som. A cena lê daqui.

Design Polaroid preservado (moldura creme, sombra, espaço inferior,
rotação em leque, hover lift, crop centralizado).
"""
import os
import random
import pygame
from pathlib import Path
from typing import List, Optional

from src.config.paths import SPRITES_PATH


# =====================================================================
# PHOTO ITEM
# =====================================================================
class PhotoItem:
    """
    Representa uma foto na mesa.

    NÃO guardamos x/y absolutos. Guardamos apenas OFFSETS RELATIVOS ao
    centro da célula (jitter_x, jitter_y em fração) + rotação + fator de
    tamanho. A posição final é calculada em `render_at(cell_rect)`.
    """

    def __init__(self, photo_path: Path, jitter_x: float, jitter_y: float,
                 rotation: float, size_factor: float, index: int):
        self.photo_path = photo_path
        self.jitter_x = jitter_x
        self.jitter_y = jitter_y
        self.base_rotation = rotation
        self.current_rotation = rotation
        self.size_factor = size_factor
        self.index = index

        self.hovered = False
        self.selected = False

        # Animação
        self.hover_lift = 0.0
        self.target_hover_lift = 0.0
        self.scale = 1.0
        self.target_scale = 1.0

        # Superfície original + proporção real
        self.photo_surface_original: Optional[pygame.Surface] = None
        self.original_aspect = 1.0

        # Cache da moldura Polaroid
        self._polaroid_cache: dict = {}

        # Atualizado a cada render_at
        self.screen_rect = pygame.Rect(0, 0, 0, 0)

    # ------------------------------------------------------------------
    # CARREGAMENTO
    # ------------------------------------------------------------------
    def load_photo(self) -> bool:
        if self.photo_surface_original is not None:
            return True
        try:
            self.photo_surface_original = pygame.image.load(
                str(self.photo_path)).convert_alpha()
            w, h = self.photo_surface_original.get_size()
            if h > 0:
                self.original_aspect = w / h
            return True
        except Exception as e:
            print(f"[PHOTO_ITEM] Erro ao carregar {self.photo_path}: {e}")
            self.photo_surface_original = pygame.Surface((100, 100))
            self.photo_surface_original.fill((40, 40, 50))
            self.original_aspect = 1.0
            return False

    # ------------------------------------------------------------------
    # CROP CENTRALIZADO
    # ------------------------------------------------------------------
    @staticmethod
    def _crop_to_square(surface: pygame.Surface,
                        target_size: int) -> pygame.Surface:
        w, h = surface.get_size()
        if w == 0 or h == 0:
            fb = pygame.Surface((target_size, target_size))
            fb.fill((40, 40, 50))
            return fb

        side = min(w, h)
        crop_x = (w - side) // 2
        crop_y = (h - side) // 2
        cropped = surface.subsurface(
            pygame.Rect(crop_x, crop_y, side, side)).copy()

        if side != target_size:
            cropped = pygame.transform.smoothscale(
                cropped, (target_size, target_size))
        return cropped

    # ------------------------------------------------------------------
    # MOLDURA POLAROID
    # ------------------------------------------------------------------
    def _make_polaroid(self, photo: pygame.Surface,
                       rotation_degrees: float) -> pygame.Surface:
        pad_side = max(6, int(photo.get_width() * 0.06))
        pad_top = pad_side
        pad_bottom = int(pad_side * 2.8)

        w = photo.get_width() + pad_side * 2
        h = photo.get_height() + pad_top + pad_bottom

        surf = pygame.Surface((w, h), pygame.SRCALPHA)

        # Sombra externa
        shadow_offset = 4
        pygame.draw.rect(surf, (0, 0, 0, 60),
                         (shadow_offset, shadow_offset, w - 1, h - 1),
                         border_radius=3)

        # Fundo branco creme
        pygame.draw.rect(surf, (250, 248, 240),
                         (0, 0, w, h), border_radius=3)
        pygame.draw.rect(surf, (215, 210, 200),
                         (0, 0, w, h), 1, border_radius=3)

        # Foto colada
        surf.blit(photo, (pad_side, pad_top))

        # Sombra interna
        inner_shadow = pygame.Surface(
            (photo.get_width(), 3), pygame.SRCALPHA)
        inner_shadow.fill((0, 0, 0, 40))
        surf.blit(inner_shadow, (pad_side, pad_top))

        # Rotaciona
        if abs(rotation_degrees) > 0.5:
            return pygame.transform.rotozoom(surf, rotation_degrees, 1.0)
        return surf

    def get_polaroid(self, size: int, rotation: float) -> pygame.Surface:
        cache_key = (size, round(rotation, 1))
        if cache_key in self._polaroid_cache:
            return self._polaroid_cache[cache_key]

        if self.photo_surface_original is None:
            self.load_photo()

        photo_cropped = self._crop_to_square(
            self.photo_surface_original, size)
        polaroid = self._make_polaroid(photo_cropped, rotation)

        if len(self._polaroid_cache) > 12:
            self._polaroid_cache.clear()

        self._polaroid_cache[cache_key] = polaroid
        return polaroid

    # ------------------------------------------------------------------
    # UPDATE
    # ------------------------------------------------------------------
    def update(self, dt: float):
        self.hover_lift += (self.target_hover_lift - self.hover_lift) * min(1, dt * 12)
        self.scale += (self.target_scale - self.scale) * min(1, dt * 12)
        self.current_rotation += (self.base_rotation - self.current_rotation) * min(1, dt * 8)

    def set_hover(self, hovered: bool):
        if hovered == self.hovered:
            return
        self.hovered = hovered
        self.target_hover_lift = -10.0 if hovered else 0.0
        self.target_scale = 1.06 if hovered else 1.0

    # ------------------------------------------------------------------
    # RENDER
    # ------------------------------------------------------------------
    def render_at(self, screen: pygame.Surface, cell_rect: pygame.Rect):
        """
        Renderiza a Polaroid CENTRADA em `cell_rect`, aplicando jitter,
        rotação, hover lift e seleção.
        """
        base_size = int(min(cell_rect.width, cell_rect.height) * self.size_factor)
        base_size = max(40, base_size)

        size = int(base_size * self.scale)
        rot = self.current_rotation

        polaroid = self.get_polaroid(size, rot)

        # Centro = centro do cell + jitter + hover lift
        cx = cell_rect.centerx + int(self.jitter_x * cell_rect.width)
        cy = cell_rect.centery + int(self.jitter_y * cell_rect.height)
        cy += int(self.hover_lift)

        rect = polaroid.get_rect(center=(cx, cy))
        screen.blit(polaroid, rect)

        self.screen_rect = rect

        if self.selected:
            pygame.draw.rect(screen, (255, 215, 0),
                             rect.inflate(6, 6), 3, border_radius=6)

    def contains_point(self, pos) -> bool:
        if self.screen_rect.width == 0:
            return False
        return self.screen_rect.collidepoint(pos)


# =====================================================================
# EXPANDED PHOTO
# =====================================================================
class ExpandedPhoto:
    STATE_OPENING = "opening"
    STATE_OPEN = "open"
    STATE_CLOSING = "closing"
    STATE_DONE = "done"

    OPEN_DURATION = 0.35
    CLOSE_DURATION = 0.25

    DEFAULT_ACCENT = (255, 210, 74)

    def __init__(self, photo_item: PhotoItem, screen_rect: pygame.Rect,
                 viewport_rect: pygame.Rect):
        self.photo_item = photo_item
        self.state = self.STATE_OPENING
        self.timer = 0.0
        self.progress = 0.0

        self.start_rect = screen_rect.copy()
        self.viewport_rect = viewport_rect

        self.target_rect = self._compute_target_rect(viewport_rect)
        self._current_rect = screen_rect.copy()
        self._render_rect = None

    # ------------------------------------------------------------------
    def _compute_target_rect(self, viewport_rect: pygame.Rect) -> pygame.Rect:
        if self.photo_item.photo_surface_original is None:
            self.photo_item.load_photo()

        aspect = self.photo_item.original_aspect or 1.0

        max_photo_w = int(viewport_rect.width * 0.50)
        max_photo_h = int(viewport_rect.height * 0.55)

        photo_w = max_photo_w
        photo_h = int(photo_w / aspect)
        if photo_h > max_photo_h:
            photo_h = max_photo_h
            photo_w = int(photo_h * aspect)

        pad_side = max(8, int(photo_w * 0.06))
        pad_top = pad_side
        pad_bottom = int(pad_side * 2.8)

        total_w = photo_w + pad_side * 2
        total_h = photo_h + pad_top + pad_bottom

        rect = pygame.Rect(0, 0, total_w, total_h)
        rect.center = viewport_rect.center
        return rect

    # ------------------------------------------------------------------
    def update(self, dt: float, viewport_rect: pygame.Rect = None):
        if viewport_rect is not None:
            self.viewport_rect = viewport_rect
            self.target_rect = self._compute_target_rect(viewport_rect)

        self.timer += dt

        if self.state == self.STATE_OPENING:
            self.progress = min(1.0, self.timer / self.OPEN_DURATION)
            t = 1.0 - (1.0 - self.progress) ** 3
            self._current_rect = self._lerp_rect(
                self.start_rect, self.target_rect, t)
            if self.progress >= 1.0:
                self.state = self.STATE_OPEN
                self.timer = 0.0
                self._current_rect = self.target_rect.copy()

        elif self.state == self.STATE_OPEN:
            self._current_rect = self.target_rect.copy()

        elif self.state == self.STATE_CLOSING:
            self.progress = min(1.0, self.timer / self.CLOSE_DURATION)
            t = self.progress ** 2
            self._current_rect = self._lerp_rect(
                self.target_rect, self.start_rect, t)
            if self.progress >= 1.0:
                self.state = self.STATE_DONE

    @staticmethod
    def _lerp_rect(a: pygame.Rect, b: pygame.Rect, t: float) -> pygame.Rect:
        x = a.x + (b.x - a.x) * t
        y = a.y + (b.y - a.y) * t
        w = a.width + (b.width - a.width) * t
        h = a.height + (b.height - a.height) * t
        return pygame.Rect(int(x), int(y), int(w), int(h))

    def start_close(self):
        if self.state in (self.STATE_OPENING, self.STATE_OPEN):
            self.state = self.STATE_CLOSING
            self.timer = 0.0
            self.progress = 0.0

    @property
    def is_done(self) -> bool:
        return self.state == self.STATE_DONE

    @property
    def is_open(self) -> bool:
        return self.state == self.STATE_OPEN

    # ------------------------------------------------------------------
    def render(self, screen: pygame.Surface):
        rect = self._current_rect

        # Fundo escuro
        overlay = pygame.Surface(
            (screen.get_width(), screen.get_height()), pygame.SRCALPHA)
        if self.state == self.STATE_OPEN:
            alpha = 210
        elif self.state == self.STATE_OPENING:
            alpha = int(210 * self.progress)
        else:
            alpha = int(210 * (1.0 - self.progress))
        overlay.fill((0, 0, 0, alpha))
        screen.blit(overlay, (0, 0))

        # Foto
        if self.photo_item.photo_surface_original is None:
            self.photo_item.load_photo()

        original = self.photo_item.photo_surface_original
        orig_w, orig_h = original.get_size()
        if orig_h == 0:
            return

        aspect = orig_w / orig_h

        photo_w = int(rect.width / 1.12)
        photo_h = int(photo_w / aspect)

        pad_side = max(6, int(photo_w * 0.06))
        pad_top = pad_side
        pad_bottom = int(pad_side * 2.8)

        total_w = photo_w + pad_side * 2
        total_h = photo_h + pad_top + pad_bottom

        if total_h > rect.height:
            scale = rect.height / total_h
            photo_w = int(photo_w * scale)
            photo_h = int(photo_h * scale)
            pad_side = max(6, int(photo_w * 0.06))
            pad_top = pad_side
            pad_bottom = int(pad_side * 2.8)
            total_w = photo_w + pad_side * 2
            total_h = photo_h + pad_top + pad_bottom

        photo_scaled = pygame.transform.smoothscale(
            original, (photo_w, photo_h))

        polaroid = pygame.Surface((total_w, total_h), pygame.SRCALPHA)

        shadow_offset = max(4, total_w // 40)
        pygame.draw.rect(polaroid, (0, 0, 0, 80),
                         (shadow_offset, shadow_offset,
                          total_w - 2, total_h - 2),
                         border_radius=6)

        pygame.draw.rect(polaroid, (250, 248, 240),
                         (0, 0, total_w, total_h), border_radius=6)
        pygame.draw.rect(polaroid, (215, 210, 200),
                         (0, 0, total_w, total_h), 2, border_radius=6)

        polaroid.blit(photo_scaled, (pad_side, pad_top))

        inner_shadow = pygame.Surface((photo_w, 4), pygame.SRCALPHA)
        inner_shadow.fill((0, 0, 0, 50))
        polaroid.blit(inner_shadow, (pad_side, pad_top))

        final_x = rect.centerx - total_w // 2
        final_y = rect.centery - total_h // 2

        screen.blit(polaroid, (final_x, final_y))

        self._render_rect = pygame.Rect(final_x, final_y, total_w, total_h)

        # Hint
        if self.state == self.STATE_OPEN:
            hint_font = pygame.font.Font(None, 24)
            hint = hint_font.render(
                "Clique fora ou ESC para fechar", True, (220, 220, 230))
            hint_bg = pygame.Surface(
                (hint.get_width() + 24, hint.get_height() + 12),
                pygame.SRCALPHA)
            hint_bg.fill((0, 0, 0, 180))
            hint_x = self.viewport_rect.centerx - hint.get_width() // 2
            hint_y = final_y + total_h + 20
            screen.blit(hint_bg, (hint_x - 12, hint_y - 6))
            pygame.draw.rect(
                screen, self.DEFAULT_ACCENT,
                (hint_x - 12, hint_y - 6,
                 hint.get_width() + 24, hint.get_height() + 12),
                1, border_radius=4)
            screen.blit(hint, (hint_x, hint_y))


# =====================================================================
# LOGIC
# =====================================================================
class PhotoGalleryLogic:
    PHOTOS_PER_PAGE = 8

    def __init__(self, game):
        self.game = game

        self.photos_dir = SPRITES_PATH / "screenshots" / "player_screenshots"
        self.photos_dir.mkdir(parents=True, exist_ok=True)

        self.photo_paths: List[Path] = []
        self.photo_items: List[PhotoItem] = []

        self.current_page = 0
        self.selected_item: Optional[PhotoItem] = None
        self.expanded_photo: Optional[ExpandedPhoto] = None
        self.delete_confirmation_active = False

        self._load_photos()

    # ------------------------------------------------------------------
    # CARREGAMENTO
    # ------------------------------------------------------------------
    def _load_photos(self):
        self.photo_paths = sorted(
            self.photos_dir.glob("photo_*.png"),
            key=os.path.getmtime,
            reverse=True,
        )
        print(f"[PHOTO_GALLERY] {len(self.photo_paths)} fotos carregadas")

    def reload_photos(self):
        self._load_photos()
        self.current_page = min(self.current_page, self.total_pages - 1)
        self.rebuild_page_items()

    # ------------------------------------------------------------------
    # PAGINAÇÃO
    # ------------------------------------------------------------------
    @property
    def total_pages(self) -> int:
        if not self.photo_paths:
            return 1
        return max(1, (len(self.photo_paths) + self.PHOTOS_PER_PAGE - 1)
                   // self.PHOTOS_PER_PAGE)

    def page_paths(self) -> List[Path]:
        start = self.current_page * self.PHOTOS_PER_PAGE
        end = start + self.PHOTOS_PER_PAGE
        return self.photo_paths[start:end]

    # ------------------------------------------------------------------
    # LAYOUT
    # ------------------------------------------------------------------
    def rebuild_page_items(self, area_rect: pygame.Rect = None):
        """
        Reconstrói os PhotoItems da página atual.

        `area_rect` é ignorado (compatibilidade). A posição real é
        calculada a cada frame pelo render_callback, dentro da célula
        que o `grid` fornece.
        """
        self.photo_items = []
        page_paths = self.page_paths()
        if not page_paths:
            return

        # Seed consistente: mesma página → mesma disposição
        seed_str = f"page_{self.current_page}_" + "_".join(
            p.name for p in page_paths)
        rng = random.Random(seed_str)

        cols = 4
        center_col = (cols - 1) / 2.0

        for i, path in enumerate(page_paths):
            col = i % cols
            col_offset = (col - center_col) / max(1.0, center_col)

            # Rotação: leque + ruído
            base_rotation = col_offset * rng.uniform(5.0, 9.0)
            random_offset = rng.uniform(-6.0, 6.0)
            rotation = max(-16.0, min(16.0, base_rotation + random_offset))

            # Jitter (fração da célula)
            jitter_x = rng.uniform(-0.08, 0.08)
            jitter_y = rng.uniform(-0.10, 0.10)

            # Tamanho relativo à célula
            size_factor = rng.uniform(0.78, 0.88)

            self.photo_items.append(PhotoItem(
                photo_path=path,
                jitter_x=jitter_x,
                jitter_y=jitter_y,
                rotation=rotation,
                size_factor=size_factor,
                index=i,
            ))

    # ------------------------------------------------------------------
    # NAVEGAÇÃO
    # ------------------------------------------------------------------
    def prev_page(self) -> bool:
        if self.current_page <= 0:
            return False
        self.current_page -= 1
        self.selected_item = None
        return True

    def next_page(self) -> bool:
        if self.current_page >= self.total_pages - 1:
            return False
        self.current_page += 1
        self.selected_item = None
        return True

    # ------------------------------------------------------------------
    # SELEÇÃO / EXPANSÃO
    # ------------------------------------------------------------------
    def get_item_at(self, pos) -> Optional[PhotoItem]:
        for item in reversed(self.photo_items):
            if item.contains_point(pos):
                return item
        return None

    def update_hover(self, pos):
        item = self.get_item_at(pos)
        for it in self.photo_items:
            it.set_hover(it is item)
        return item

    def expand_item(self, item: PhotoItem, viewport_rect: pygame.Rect):
        self.selected_item = item
        item.selected = True
        self.expanded_photo = ExpandedPhoto(
            item, item.screen_rect, viewport_rect)

    def close_expanded(self):
        if self.expanded_photo and not self.expanded_photo.is_done:
            self.expanded_photo.start_close()

    def clear_selection(self):
        if self.selected_item is not None:
            self.selected_item.selected = False
            self.selected_item = None

    # ------------------------------------------------------------------
    # DELETE
    # ------------------------------------------------------------------
    def request_delete(self) -> bool:
        if self.selected_item is None:
            return False
        self.delete_confirmation_active = True
        return True

    def confirm_delete(self) -> bool:
        if self.selected_item is None:
            self.delete_confirmation_active = False
            return False

        try:
            os.remove(str(self.selected_item.photo_path))
            print(f"[PHOTO_GALLERY] Foto excluída: {self.selected_item.photo_path}")
        except Exception as e:
            print(f"[PHOTO_GALLERY] Erro ao excluir: {e}")
            self.delete_confirmation_active = False
            return False

        self.selected_item = None
        self.expanded_photo = None
        self.delete_confirmation_active = False
        self.reload_photos()
        return True

    def cancel_delete(self):
        self.delete_confirmation_active = False

    # ------------------------------------------------------------------
    # UPDATE
    # ------------------------------------------------------------------
    def update(self, dt: float, viewport_rect: pygame.Rect = None):
        for item in self.photo_items:
            item.update(dt)

        if self.expanded_photo is not None:
            if viewport_rect is not None:
                self.expanded_photo.update(dt, viewport_rect)
            else:
                self.expanded_photo.update(dt)

            if self.expanded_photo.is_done:
                if self.selected_item is not None:
                    self.selected_item.selected = False
                self.expanded_photo = None
                self.selected_item = None
                pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_ARROW)

    # ------------------------------------------------------------------
    # HELPERS
    # ------------------------------------------------------------------
    def is_expanded(self) -> bool:
        return self.expanded_photo is not None

    def has_selection(self) -> bool:
        return self.selected_item is not None