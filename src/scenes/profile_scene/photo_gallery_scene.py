# src/scenes/profile_scene/photo_gallery_scene.py

"""
Galeria de Fotos do Jogador - Vibe "mesa de fotos polaroid"
- Fotos na mesa: crop centralizado em quadrado (sem distorcer)
- Preview expandido: proporção REAL da imagem (sem crop, sem esticar)
- Molduras Polaroid, rotações em leque, hover lift, animação de expansão
- Fundo consistente com a tela de perfil (azul escuro)
"""
import pygame
import os
import math
import random
from pathlib import Path

from config.paths import SPRITES_PATH
from src.scenes.base_scene import BaseScene
from src.managers.sounds.sound_manager import sound_manager, SoundEffect
from src.ui.toast_renderer import toast_info, toast_warning


# =====================================================================
# PHOTO ITEM
# =====================================================================

class PhotoItem:
    """Representa uma foto na mesa, com moldura Polaroid e rotação própria"""

    def __init__(self, photo_path: Path, x: float, y: float, rotation: float,
                 base_size: int, index: int):
        self.photo_path = photo_path
        self.x = x
        self.y = y
        self.base_rotation = rotation
        self.current_rotation = rotation
        self.base_size = base_size
        self.index = index

        # Estado
        self.hovered = False
        self.selected = False

        # Animação de hover
        self.hover_lift = 0.0
        self.target_hover_lift = 0.0
        self.scale = 1.0
        self.target_scale = 1.0

        # Superfície da foto original
        self.photo_surface_original = None

        # Proporção real (largura / altura) — usada no preview expandido
        self.original_aspect = 1.0

        # Cache da moldura Polaroid
        self._polaroid_cache = {}

        # Rect calculado a cada frame
        self.screen_rect = pygame.Rect(0, 0, 0, 0)

    # ------------------------------------------------------------------
    # CARREGAMENTO
    # ------------------------------------------------------------------
    def load_photo(self):
        """Carrega a imagem original e guarda a proporção real"""
        if self.photo_surface_original is not None:
            return True
        try:
            self.photo_surface_original = pygame.image.load(
                str(self.photo_path)
            ).convert_alpha()

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
    # CROP CENTRALIZADO (MESA)
    # ------------------------------------------------------------------
    @staticmethod
    def _crop_to_square(surface: pygame.Surface, target_size: int) -> pygame.Surface:
        """
        Corta a imagem no centro para virar um quadrado `target_size x target_size`,
        SEM distorcer — apenas recorta o excesso.
        """
        w, h = surface.get_size()
        if w == 0 or h == 0:
            fallback = pygame.Surface((target_size, target_size))
            fallback.fill((40, 40, 50))
            return fallback

        side = min(w, h)
        crop_x = (w - side) // 2
        crop_y = (h - side) // 2

        cropped = surface.subsurface(pygame.Rect(crop_x, crop_y, side, side)).copy()

        if side != target_size:
            cropped = pygame.transform.smoothscale(cropped, (target_size, target_size))

        return cropped

    # ------------------------------------------------------------------
    # MOLDURA POLAROID
    # ------------------------------------------------------------------
    def _make_polaroid(self, photo: pygame.Surface, rotation_degrees: float) -> pygame.Surface:
        """
        Cria uma superfície estilo Polaroid:
        - Moldura branca creme
        - Espaço maior embaixo
        - Sombra sutil deslocada
        """
        pad_side = max(6, int(photo.get_width() * 0.06))
        pad_top = pad_side
        pad_bottom = int(pad_side * 2.8)

        w = photo.get_width() + pad_side * 2
        h = photo.get_height() + pad_top + pad_bottom

        surf = pygame.Surface((w, h), pygame.SRCALPHA)

        # Sombra externa
        shadow_offset = 4
        pygame.draw.rect(
            surf, (0, 0, 0, 60),
            (shadow_offset, shadow_offset, w - 1, h - 1),
            border_radius=3
        )

        # Fundo branco (creme)
        pygame.draw.rect(surf, (250, 248, 240), (0, 0, w, h), border_radius=3)
        pygame.draw.rect(surf, (215, 210, 200), (0, 0, w, h), 1, border_radius=3)

        # Foto colada
        surf.blit(photo, (pad_side, pad_top))

        # Sombra interna
        inner_shadow = pygame.Surface((photo.get_width(), 3), pygame.SRCALPHA)
        inner_shadow.fill((0, 0, 0, 40))
        surf.blit(inner_shadow, (pad_side, pad_top))

        # Rotaciona
        if abs(rotation_degrees) > 0.5:
            rotated = pygame.transform.rotozoom(surf, rotation_degrees, 1.0)
            return rotated

        return surf

    def get_polaroid(self, size: int, rotation: float) -> pygame.Surface:
        """
        Retorna a moldura Polaroid em cache, já rotacionada.
        Aplica o crop centralizado (mesa) — sem distorcer.
        """
        cache_key = (size, round(rotation, 1))
        if cache_key in self._polaroid_cache:
            return self._polaroid_cache[cache_key]

        if self.photo_surface_original is None:
            self.load_photo()

        photo_cropped = self._crop_to_square(self.photo_surface_original, size)
        polaroid = self._make_polaroid(photo_cropped, rotation)

        if len(self._polaroid_cache) > 12:
            self._polaroid_cache.clear()

        self._polaroid_cache[cache_key] = polaroid
        return polaroid

    # ------------------------------------------------------------------
    # UPDATE
    # ------------------------------------------------------------------
    def update(self, dt):
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
    def render(self, screen):
        size = int(self.base_size * self.scale)
        rot = self.current_rotation

        polaroid = self.get_polaroid(size, rot)

        final_x = self.x
        final_y = self.y + self.hover_lift

        rect = polaroid.get_rect(center=(int(final_x), int(final_y)))
        screen.blit(polaroid, rect)

        self.screen_rect = rect

        if self.selected:
            pygame.draw.rect(
                screen, (255, 215, 0),
                rect.inflate(6, 6), 3, border_radius=6
            )

    def contains_point(self, pos) -> bool:
        if self.screen_rect.width == 0:
            return False
        return self.screen_rect.collidepoint(pos)


# =====================================================================
# EXPANDED PHOTO
# =====================================================================

class ExpandedPhoto:
    """Foto expandida em overlay — mantém a proporção REAL da imagem"""

    STATE_OPENING = "opening"
    STATE_OPEN = "open"
    STATE_CLOSING = "closing"
    STATE_DONE = "done"

    def __init__(self, photo_item: PhotoItem, screen_rect: pygame.Rect,
                 viewport_rect: pygame.Rect):
        self.photo_item = photo_item
        self.state = self.STATE_OPENING
        self.timer = 0.0

        self.OPEN_DURATION = 0.35
        self.CLOSE_DURATION = 0.25

        self.progress = 0.0

        self.start_rect = screen_rect.copy()
        self.viewport_rect = viewport_rect

        self.target_rect = self._compute_target_rect(viewport_rect)
        self._current_rect = screen_rect.copy()

        self._render_rect = None

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

    def update(self, dt, viewport_rect=None):
        if viewport_rect is not None:
            self.viewport_rect = viewport_rect
            self.target_rect = self._compute_target_rect(viewport_rect)

        self.timer += dt

        if self.state == self.STATE_OPENING:
            self.progress = min(1.0, self.timer / self.OPEN_DURATION)
            t = 1.0 - (1.0 - self.progress) ** 3
            self._current_rect = self._lerp_rect(self.start_rect, self.target_rect, t)
            if self.progress >= 1.0:
                self.state = self.STATE_OPEN
                self.timer = 0.0
                self._current_rect = self.target_rect.copy()

        elif self.state == self.STATE_OPEN:
            self._current_rect = self.target_rect.copy()

        elif self.state == self.STATE_CLOSING:
            self.progress = min(1.0, self.timer / self.CLOSE_DURATION)
            t = self.progress ** 2
            self._current_rect = self._lerp_rect(self.target_rect, self.start_rect, t)
            if self.progress >= 1.0:
                self.state = self.STATE_DONE

    def _lerp_rect(self, a: pygame.Rect, b: pygame.Rect, t: float) -> pygame.Rect:
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
    def is_done(self):
        return self.state == self.STATE_DONE

    @property
    def is_open(self):
        return self.state == self.STATE_OPEN

    def render(self, screen):
        rect = self._current_rect

        # Fundo escurecido
        overlay = pygame.Surface(
            (screen.get_width(), screen.get_height()),
            pygame.SRCALPHA
        )
        if self.state == self.STATE_OPEN:
            alpha = 210
        elif self.state == self.STATE_OPENING:
            alpha = int(210 * self.progress)
        else:
            alpha = int(210 * (1.0 - self.progress))
        overlay.fill((0, 0, 0, alpha))
        screen.blit(overlay, (0, 0))

        # Dados da foto
        if self.photo_item.photo_surface_original is None:
            self.photo_item.load_photo()

        original = self.photo_item.photo_surface_original
        orig_w, orig_h = original.get_size()
        if orig_h == 0:
            return

        aspect = orig_w / orig_h

        # Calcula tamanho da foto a partir da largura do rect
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

        photo_scaled = pygame.transform.smoothscale(original, (photo_w, photo_h))

        # Monta a Polaroid
        polaroid = pygame.Surface((total_w, total_h), pygame.SRCALPHA)

        shadow_offset = max(4, total_w // 40)
        pygame.draw.rect(
            polaroid, (0, 0, 0, 80),
            (shadow_offset, shadow_offset, total_w - 2, total_h - 2),
            border_radius=6
        )

        pygame.draw.rect(
            polaroid, (250, 248, 240),
            (0, 0, total_w, total_h),
            border_radius=6
        )
        pygame.draw.rect(
            polaroid, (215, 210, 200),
            (0, 0, total_w, total_h),
            2, border_radius=6
        )

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
                "Clique fora ou ESC para fechar",
                True, (220, 220, 230)
            )
            hint_bg = pygame.Surface(
                (hint.get_width() + 24, hint.get_height() + 12),
                pygame.SRCALPHA
            )
            hint_bg.fill((0, 0, 0, 180))
            hint_x = self.viewport_rect.centerx - hint.get_width() // 2
            hint_y = final_y + total_h + 20
            screen.blit(hint_bg, (hint_x - 12, hint_y - 6))
            screen.blit(hint, (hint_x, hint_y))


# =====================================================================
# GALLERY SCENE
# =====================================================================

class PhotoGalleryScene(BaseScene):
    """Galeria de fotos com visual de mesa + Polaroid"""

    def __init__(self, game, return_scene=None):
        super().__init__(game)
        self.return_scene = return_scene or "menu"

        # Pasta
        self.photos_dir = SPRITES_PATH / "screenshots" / "player_screenshots"
        self.photos_dir.mkdir(parents=True, exist_ok=True)

        # Listas
        self.photo_paths = []
        self.photo_items = []

        # Paginação
        self.current_page = 0
        self.PHOTOS_PER_PAGE = 8

        # Expansão
        self.expanded_photo: ExpandedPhoto | None = None

        # Confirmação de exclusão
        self.delete_confirmation_active = False
        self.delete_confirmation_timer = 0
        self._confirm_yes_rect = None
        self._confirm_no_rect = None

        # Botões
        from src.scenes.profile_scene.profile_scene import ProfileButton
        BTN_VOLUME = 0.3

        self.buttons = [
            ProfileButton(
                0.05, 0.90, 0.12, 0.07, "Voltar",
                (50, 50, 70), (80, 80, 110), self.go_back,
                volume=BTN_VOLUME
            ),
            ProfileButton(
                0.25, 0.90, 0.10, 0.07, "Anterior",
                (50, 50, 70), (80, 80, 110), self.prev_page,
                volume=BTN_VOLUME
            ),
            ProfileButton(
                0.65, 0.90, 0.10, 0.07, "Próxima",
                (50, 50, 70), (80, 80, 110), self.next_page,
                volume=BTN_VOLUME
            ),
            ProfileButton(
                0.80, 0.90, 0.15, 0.07, "Excluir Foto",
                (80, 20, 20), (130, 30, 30), self.show_delete_confirmation,
                volume=BTN_VOLUME
            ),
        ]

        # Estado
        self._animation_timer = 0
        self._hovered_item: PhotoItem | None = None
        self._selected_item: PhotoItem | None = None

        self._load_photos()

    # ==================================================================
    # CARREGAMENTO
    # ==================================================================

    def _load_photos(self):
        self.photo_paths = sorted(
            self.photos_dir.glob("photo_*.png"),
            key=os.path.getmtime,
            reverse=True
        )
        self._rebuild_page_items()
        print(f"[PHOTO_GALLERY] {len(self.photo_paths)} fotos carregadas")

    def _rebuild_page_items(self):
        """Cria os PhotoItem da página atual com posições/rotações em leque"""
        self.photo_items = []

        start = self.current_page * self.PHOTOS_PER_PAGE
        end = start + self.PHOTOS_PER_PAGE
        page_paths = self.photo_paths[start:end]

        # Seed consistente (mesma página → mesma disposição)
        seed_str = f"page_{self.current_page}_" + "_".join(p.name for p in page_paths)
        rng = random.Random(seed_str)

        # Grid 4x2
        cols = 4
        rows = 2

        vx = self.screen_manager.viewport_x
        vy = self.screen_manager.viewport_y
        vw = self.screen_manager.viewport_width
        vh = self.screen_manager.viewport_height

        # Área útil
        area_x = vx + int(vw * 0.06)
        area_y = vy + int(vh * 0.16)
        area_w = int(vw * 0.88)
        area_h = int(vh * 0.68)

        cell_w = area_w / cols
        cell_h = area_h / rows

        base_size = int(min(cell_w, cell_h) * 0.85)

        for i, path in enumerate(page_paths):
            col = i % cols
            row = i // cols

            cell_cx = area_x + col * cell_w + cell_w / 2
            cell_cy = area_y + row * cell_h + cell_h / 2

            # Jitter (posição "espalhada")
            jitter_x = rng.uniform(-cell_w * 0.14, cell_w * 0.14)
            jitter_y = rng.uniform(-cell_h * 0.16, cell_h * 0.16)

            # ===== ROTAÇÃO EM LEQUE =====
            # Fotos à esquerda inclinam pra esquerda, à direita pra direita.
            center_col = (cols - 1) / 2.0
            col_offset = (col - center_col) / max(1.0, center_col)  # -1..1

            base_rotation = col_offset * rng.uniform(5.0, 9.0)
            random_offset = rng.uniform(-6.0, 6.0)
            rotation = base_rotation + random_offset

            # Clamp para nunca passar de ±16° (sem virar de cabeça pra baixo)
            rotation = max(-16.0, min(16.0, rotation))

            item = PhotoItem(
                photo_path=path,
                x=cell_cx + jitter_x,
                y=cell_cy + jitter_y,
                rotation=rotation,
                base_size=base_size,
                index=i
            )
            self.photo_items.append(item)

    # ==================================================================
    # NAVEGAÇÃO
    # ==================================================================

    @property
    def total_pages(self):
        if not self.photo_paths:
            return 1
        return max(1, (len(self.photo_paths) + self.PHOTOS_PER_PAGE - 1) // self.PHOTOS_PER_PAGE)

    def go_back(self):
        from src.scenes.profile_scene.profile_scene import ProfileScene
        self.game.current_scene = ProfileScene(self.game, return_scene=self.return_scene)

    def prev_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            self._rebuild_page_items()
            self._selected_item = None
            sound_manager.play_effect(SoundEffect.CLICK, volume=0.3)

    def next_page(self):
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            self._rebuild_page_items()
            self._selected_item = None
            sound_manager.play_effect(SoundEffect.CLICK, volume=0.3)

    # ==================================================================
    # EXPANSÃO
    # ==================================================================

    def _expand_item(self, item: PhotoItem):
        """Expande uma foto clicada"""
        self._selected_item = item
        item.selected = True

        viewport_rect = pygame.Rect(
            self.screen_manager.viewport_x,
            self.screen_manager.viewport_y,
            self.screen_manager.viewport_width,
            self.screen_manager.viewport_height
        )

        self.expanded_photo = ExpandedPhoto(item, item.screen_rect, viewport_rect)
        sound_manager.play_effect(SoundEffect.CLICK, volume=0.4)

    def _close_expanded(self):
        if self.expanded_photo and not self.expanded_photo.is_done:
            self.expanded_photo.start_close()

    # ==================================================================
    # EXCLUSÃO
    # ==================================================================

    def show_delete_confirmation(self):
        # Só permite se houver uma foto selecionada
        if self._selected_item is not None:
            self.delete_confirmation_active = True
            self.delete_confirmation_timer = 0

    def _execute_delete(self):
        if self._selected_item is None:
            self.delete_confirmation_active = False
            return

        path = self._selected_item.photo_path
        try:
            os.remove(str(path))
            print(f"[PHOTO_GALLERY] Foto excluída: {path}")
            toast_info("Foto excluída com sucesso!", duration=2.0)

            self._selected_item = None
            self.expanded_photo = None

            self._load_photos()
            self.current_page = min(self.current_page, self.total_pages - 1)
            self._rebuild_page_items()

        except Exception as e:
            print(f"[PHOTO_GALLERY] Erro ao excluir: {e}")
            toast_warning("Erro ao excluir a foto!", duration=2.0)

        self.delete_confirmation_active = False

    # ==================================================================
    # EVENTOS
    # ==================================================================

    def handle_event(self, event):
        # ===== 1. MODAL DE CONFIRMAÇÃO (prioridade máxima) =====
        if self.delete_confirmation_active:
            self._handle_delete_confirmation(event)
            return

        # ===== 2. BOTÕES (ficam na frente do preview) =====
        # Só interceptam clique se o mouse estiver em cima deles.
        # O botão "Excluir Foto" só é clicável se houver foto selecionada.
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for idx, button in enumerate(self.buttons):
                # Pula o botão "Excluir Foto" (índice 3) se não houver seleção
                if idx == 3 and self._selected_item is None:
                    continue
                if button.rect.collidepoint(event.pos):
                    button.handle_event(event)
                    return
        else:
            for idx, button in enumerate(self.buttons):
                if idx == 3 and self._selected_item is None:
                    continue
                button.handle_event(event)

        # ===== 3. PREVIEW EXPANDIDO (prioridade sobre a mesa) =====
        if self.expanded_photo is not None:
            self._handle_expanded_event(event)
            return

        # ===== 4. TECLADO DA MESA =====
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.go_back()
            elif event.key == pygame.K_LEFT:
                self.prev_page()
            elif event.key == pygame.K_RIGHT:
                self.next_page()
            elif event.key == pygame.K_DELETE and self._selected_item:
                self.show_delete_confirmation()

        # ===== 5. MOUSE NA MESA =====
        if event.type == pygame.MOUSEMOTION:
            self._update_hover(event.pos)

        if event.type == pygame.MOUSEWHEEL:
            if event.y > 0:
                self.prev_page()
            elif event.y < 0:
                self.next_page()

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self._handle_click(event.pos)

    def _handle_click(self, pos):
        # (botões já foram tratados em handle_event)
        item = self._get_item_at(pos)
        if item is not None:
            self._expand_item(item)
            return

        # Clique fora: desmarca (mas NÃO fecha preview aberto — isso é feito no _handle_expanded_event)
        if self._selected_item:
            self._selected_item.selected = False
            self._selected_item = None

    def _handle_expanded_event(self, event):
        """Eventos enquanto uma foto está expandida"""
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_SPACE):
                self._close_expanded()
            elif event.key == pygame.K_DELETE:
                # Abre o modal — ele será renderizado NA FRENTE do preview
                self.delete_confirmation_active = True
                self.delete_confirmation_timer = 0

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.expanded_photo and self.expanded_photo.is_open:
                rect = getattr(self.expanded_photo, '_render_rect', None)
                if rect is None or not rect.collidepoint(event.pos):
                    self._close_expanded()

    def _handle_delete_confirmation(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._confirm_yes_rect and self._confirm_yes_rect.collidepoint(event.pos):
                self._execute_delete()
                return
            if self._confirm_no_rect and self._confirm_no_rect.collidepoint(event.pos):
                self.delete_confirmation_active = False
                return

        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.delete_confirmation_active = False

    def _update_hover(self, pos):
        item = self._get_item_at(pos)
        if item is not self._hovered_item:
            if self._hovered_item:
                self._hovered_item.set_hover(False)
            self._hovered_item = item
            if self._hovered_item:
                self._hovered_item.set_hover(True)
                pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_HAND)
            else:
                pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_ARROW)

    def _get_item_at(self, pos):
        for item in reversed(self.photo_items):
            if item.contains_point(pos):
                return item
        return None

    # ==================================================================
    # UPDATE
    # ==================================================================

    def fixed_update(self, dt):
        self._animation_timer += dt

        for button in self.buttons:
            button.update(dt)

        for item in self.photo_items:
            item.update(dt)

        if self.expanded_photo:
            vp = pygame.Rect(
                self.screen_manager.viewport_x,
                self.screen_manager.viewport_y,
                self.screen_manager.viewport_width,
                self.screen_manager.viewport_height
            )
            self.expanded_photo.update(dt, vp)
            if self.expanded_photo.is_done:
                if self._selected_item:
                    self._selected_item.selected = False
                self.expanded_photo = None
                self._selected_item = None
                pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_ARROW)

        if self.delete_confirmation_active:
            self.delete_confirmation_timer += dt

    # ==================================================================
    # RENDER
    # ==================================================================

    def render(self, screen):
        vx = self.screen_manager.viewport_x
        vy = self.screen_manager.viewport_y
        vw = self.screen_manager.viewport_width
        vh = self.screen_manager.viewport_height

        # Fundo estilo perfil (azul escuro)
        self._render_background(screen, vx, vy, vw, vh)

        # Botões
        for button in self.buttons:
            button.update_absolute_position(vw, vh, vx, vy)

        # Cabeçalho
        self._render_header(screen, vx, vy, vw, vh)

        # Fotos
        if not self.photo_paths:
            self._render_empty_state(screen, vx, vy, vw, vh)
        else:
            sorted_items = sorted(self.photo_items, key=lambda it: it.y)
            for item in sorted_items:
                item.render(screen)

        # Paginação
        self._render_pagination(screen, vx, vy, vw, vh)

        # ===== FOTO EXPANDIDA (ANTES dos botões) =====
        if self.expanded_photo:
            self.expanded_photo.render(screen)

        # ===== BOTÕES (na frente do preview) =====
        # O botão "Excluir Foto" só aparece se houver uma foto selecionada
        for idx, button in enumerate(self.buttons):
            if idx == 3 and self._selected_item is None:
                continue  # pula o botão "Excluir Foto"
            button.render(screen)

        # ===== MODAL DE CONFIRMAÇÃO (por cima de TUDO) =====
        if self.delete_confirmation_active:
            self._render_delete_confirmation(screen, vx, vy, vw, vh)

        # Hint
        hint_font = pygame.font.Font(None, 18)
        hint = hint_font.render(
            "Clique em uma foto para expandir | DEL para excluir | ESC para voltar",
            True, (140, 150, 190)
        )
        bg = pygame.Surface((hint.get_width() + 16, hint.get_height() + 8), pygame.SRCALPHA)
        bg.fill((0, 0, 0, 120))
        screen.blit(bg, (vx + vw - hint.get_width() - 25, vy + vh - 26))
        screen.blit(hint, (vx + vw - hint.get_width() - 17, vy + vh - 22))

    # ------------------------------------------------------------------
    # FUNDO
    # ------------------------------------------------------------------
    def _render_background(self, screen, vx, vy, vw, vh):
        """
        Fundo com aparência de mesa
        """
        # ===== GRADIENTE BASE (AZUL ESCURO) =====
        for i in range(vh):
            t = i / vh
            # Topo mais claro, base mais escura — mesma "curva" do marrom, mas em azul
            r = int(22 + t * 10)
            g = int(28 + t * 14)
            b = int(48 + t * 22)
            pygame.draw.line(screen, (r, g, b), (vx, vy + i), (vx + vw, vy + i))

        # ===== FIBRAS HORIZONTAIS =====
        # Antes eram (48, 36, 28) marrom → agora azul-acinzentado sutil
        fiber_color = (35, 45, 70)
        for i in range(0, vh, 4):
            y = vy + i
            offset = int(math.sin(i * 0.05) * 2)
            pygame.draw.line(
                screen, fiber_color,
                (vx + offset, y), (vx + vw + offset, y), 1
            )

        # ===== VINHETA (CANTOS MAIS ESCUROS) =====
        vignette = pygame.Surface((vw, vh), pygame.SRCALPHA)
        for i in range(0, 60, 2):
            alpha = int((i / 60) ** 2 * 80)
            pygame.draw.rect(
                vignette, (0, 0, 0, alpha),
                (i * 2, i * 2, vw - i * 4, vh - i * 4),
                border_radius=10
            )
        screen.blit(vignette, (vx, vy))

    # ------------------------------------------------------------------
    # CABEÇALHO
    # ------------------------------------------------------------------
    def _render_header(self, screen, vx, vy, vw, vh):
        title_font = pygame.font.Font(None, int(vh * 0.05))
        title = title_font.render("GALERIA DE FOTOS", True, (255, 215, 0))
        title_shadow = title_font.render("GALERIA DE FOTOS", True, (30, 20, 10))
        tx = vx + 20
        ty = vy + 12
        screen.blit(title_shadow, (tx + 2, ty + 2))
        screen.blit(title, (tx, ty))

        count_font = pygame.font.Font(None, int(vh * 0.024))
        count = count_font.render(
            f"{len(self.photo_paths)} foto{'s' if len(self.photo_paths) != 1 else ''}",
            True, (180, 200, 240)
        )
        screen.blit(count, (vx + 22, vy + int(vh * 0.065)))

        line_y = vy + int(vh * 0.105)
        pygame.draw.line(
            screen, (80, 100, 160),
            (vx + 20, line_y), (vx + vw - 20, line_y), 2
        )

    # ------------------------------------------------------------------
    # ESTADO VAZIO
    # ------------------------------------------------------------------
    def _render_empty_state(self, screen, vx, vy, vw, vh):
        center_x = vx + vw // 2
        center_y = vy + vh // 2

        empty_font = pygame.font.Font(None, int(vh * 0.04))
        empty_text = empty_font.render("Nenhuma foto ainda...", True, (140, 160, 200))
        screen.blit(empty_text, empty_text.get_rect(center=(center_x, center_y - 20)))

        hint_font = pygame.font.Font(None, int(vh * 0.025))
        hint = hint_font.render(
            "Use a Câmera durante o jogo para tirar fotos!",
            True, (100, 120, 160)
        )
        screen.blit(hint, hint.get_rect(center=(center_x, center_y + 25)))

        # Câmera ilustrativa
        cam_w, cam_h = int(vw * 0.10), int(vh * 0.08)
        cam_x = center_x - cam_w // 2
        cam_y = center_y - int(vh * 0.20)
        pygame.draw.rect(screen, (40, 50, 80),
                         (cam_x, cam_y, cam_w, cam_h), border_radius=8)
        pygame.draw.rect(screen, (80, 100, 160),
                         (cam_x, cam_y, cam_w, cam_h), 2, border_radius=8)
        pygame.draw.circle(screen, (20, 25, 40),
                           (cam_x + cam_w // 2, cam_y + cam_h // 2),
                           int(min(cam_w, cam_h) * 0.30))
        pygame.draw.circle(screen, (100, 130, 200),
                           (cam_x + cam_w // 2, cam_y + cam_h // 2),
                           int(min(cam_w, cam_h) * 0.30), 2)
        pygame.draw.circle(screen, (200, 220, 255),
                           (cam_x + cam_w - 15, cam_y + 12), 4)

    # ------------------------------------------------------------------
    # PAGINAÇÃO
    # ------------------------------------------------------------------
    def _render_pagination(self, screen, vx, vy, vw, vh):
        if self.total_pages <= 1:
            return

        page_y = vy + int(vh * 0.855)

        page_font = pygame.font.Font(None, int(vh * 0.026))
        page_text = page_font.render(
            f"Página {self.current_page + 1} / {self.total_pages}",
            True, (200, 215, 255)
        )
        bg = pygame.Surface((page_text.get_width() + 20, page_text.get_height() + 8), pygame.SRCALPHA)
        bg.fill((0, 0, 0, 140))
        screen.blit(bg, (vx + vw // 2 - page_text.get_width() // 2 - 10, page_y - 4))
        screen.blit(page_text, page_text.get_rect(center=(vx + vw // 2, page_y)))

    # ------------------------------------------------------------------
    # CONFIRMAÇÃO DE EXCLUSÃO
    # ------------------------------------------------------------------
    def _render_delete_confirmation(self, screen, vx, vy, vw, vh):
        overlay = pygame.Surface((vw, vh), pygame.SRCALPHA)
        alpha = min(180, int(180 * (self.delete_confirmation_timer / 0.2)))
        overlay.fill((0, 0, 0, alpha))
        screen.blit(overlay, (vx, vy))

        cw = int(vw * 0.45)
        ch = int(vh * 0.30)
        cx = vx + (vw - cw) // 2
        cy = vy + (vh - ch) // 2

        container_rect = pygame.Rect(cx, cy, cw, ch)
        pygame.draw.rect(screen, (30, 20, 25), container_rect, border_radius=12)
        pygame.draw.rect(screen, (200, 60, 60), container_rect, 3, border_radius=12)

        title_font = pygame.font.Font(None, int(vh * 0.04))
        title = title_font.render("EXCLUIR FOTO", True, (255, 80, 80))
        screen.blit(title, title.get_rect(center=(cx + cw // 2, cy + 30)))

        msg_font = pygame.font.Font(None, int(vh * 0.025))
        msg1 = msg_font.render("Tem certeza que deseja excluir esta foto?", True, (200, 200, 210))
        msg2 = msg_font.render("Esta ação não pode ser desfeita!", True, (255, 150, 150))
        screen.blit(msg1, msg1.get_rect(center=(cx + cw // 2, cy + ch // 2 - 10)))
        screen.blit(msg2, msg2.get_rect(center=(cx + cw // 2, cy + ch // 2 + 20)))

        btn_w = int(cw * 0.25)
        btn_h = int(ch * 0.25)
        spacing = 20
        mouse_pos = pygame.mouse.get_pos()

        yes_rect = pygame.Rect(cx + cw // 2 - btn_w - spacing // 2,
                               cy + ch - btn_h - 15, btn_w, btn_h)
        yes_hover = yes_rect.collidepoint(mouse_pos)
        pygame.draw.rect(screen, (180, 40, 40) if yes_hover else (140, 30, 30), yes_rect, border_radius=8)
        pygame.draw.rect(screen, (255, 80, 80), yes_rect, 2, border_radius=8)

        yes_font = pygame.font.Font(None, int(vh * 0.028))
        yes_text = yes_font.render("SIM", True, (255, 255, 255))
        screen.blit(yes_text, yes_text.get_rect(center=yes_rect.center))

        no_rect = pygame.Rect(cx + cw // 2 + spacing // 2,
                              cy + ch - btn_h - 15, btn_w, btn_h)
        no_hover = no_rect.collidepoint(mouse_pos)
        pygame.draw.rect(screen, (70, 70, 80) if no_hover else (50, 50, 60), no_rect, border_radius=8)
        pygame.draw.rect(screen, (120, 120, 130), no_rect, 2, border_radius=8)

        no_text = yes_font.render("NÃO", True, (255, 255, 255))
        screen.blit(no_text, no_text.get_rect(center=no_rect.center))

        self._confirm_yes_rect = yes_rect
        self._confirm_no_rect = no_rect