# src/scenes/profile_scene/photo_gallery_scene.py
"""
Galeria de Fotos — padrão StandardScreen.

A cena só orquestra. Toda a lógica está em photo_gallery_logic.py.
O render das Polaroids é feito por `grid.render_callback`.
"""
import pygame

from src.ui.screen_template import StandardScreen
from src.ui.screen_loader import ScreenLoader
from src.managers.sounds.sound_manager import sound_manager, SoundEffect
from src.ui.toast_renderer import toast_info, toast_warning

from .photo_gallery_logic import PhotoGalleryLogic


LAYOUT_PATH = "res/ui_layouts/photo_gallery.json"


class PhotoGalleryScene(StandardScreen):
    title = ""
    show_back_button = False

    # =================================================================
    def __init__(self, game, return_scene=None):
        self.return_scene = return_scene or "menu"
        self.logic = PhotoGalleryLogic(game)

        super().__init__(game)

    # =================================================================
    # BUILD / ENTER
    # =================================================================
    def build(self):
        ScreenLoader.load(self, LAYOUT_PATH)

        # Instala o render_callback no GRID
        grid = self.get("photos_grid")
        if grid is not None:
            grid.render_callback = self._render_photo_cell

        self.logic.rebuild_page_items()
        self._refresh()

    def enter(self):
        # Recarrega fotos ao entrar (podem ter sido tiradas no jogo)
        self.logic.reload_photos()
        self._refresh()

    def get_actions(self):
        return {
            "back":        lambda *_: self._on_back(),
            "prev_page":   lambda *_: self._on_prev(),
            "next_page":   lambda *_: self._on_next(),
            "delete":      lambda *_: self._on_delete(),
            "confirm_yes": lambda *_: self._on_confirm_yes(),
            "confirm_no":  lambda *_: self._on_confirm_no(),
        }

    # =================================================================
    # REFRESH
    # =================================================================
    def _refresh(self):
        self._feed_grid()
        self._update_header()
        self._update_buttons_visibility()
        self._update_modal_visibility()

    def _feed_grid(self):
        grid = self.get("photos_grid")
        if grid is not None:
            # O grid só precisa que `items` tenha o mesmo tamanho da
            # lista de PhotoItems. Cada item é só o índice (o callback
            # resolve o PhotoItem a partir do idx).
            grid.items = list(range(len(self.logic.photo_items)))

    def _update_header(self):
        total = len(self.logic.photo_paths)
        txt = f"{total} foto" + ("s" if total != 1 else "")
        w = self.get("lbl_count")
        if w is not None:
            w.text = txt

        w = self.get("lbl_page")
        if w is not None:
            w.text = (f"Pagina {self.logic.current_page + 1} / "
                      f"{self.logic.total_pages}")

    def _update_buttons_visibility(self):
        w = self.get("btn_delete")
        if w is not None:
            w.visible = self.logic.has_selection()

    def _update_modal_visibility(self):
        v = self.logic.delete_confirmation_active
        for wid in ("m_confirm_backdrop", "m_confirm_panel",
                    "m_confirm_title", "m_confirm_msg1", "m_confirm_msg2",
                    "m_confirm_yes", "m_confirm_no"):
            w = self.get(wid)
            if w is not None:
                w.visible = v

    # =================================================================
    # CALLBACK DE RENDER DOS CARDS
    # =================================================================
    def _render_photo_cell(self, idx, item, screen, rect):
        """
        render_callback do GRID.
        Blita a Polaroid do PhotoItem[idx] CENTRADA no cell rect atual.
        """
        if idx >= len(self.logic.photo_items):
            return True
        photo = self.logic.photo_items[idx]
        photo.render_at(screen, rect)
        return True

    # =================================================================
    # AÇÕES
    # =================================================================
    def _play_click(self, v=0.3):
        try:
            sound_manager.play_effect(SoundEffect.CLICK, volume=v)
        except Exception:
            pass

    def _on_back(self):
        self._play_click()
        from src.scenes.profile_scene.profile_scene import ProfileScene
        self.game.current_scene = ProfileScene(
            self.game, return_scene=self.return_scene)

    def _on_prev(self):
        if self.logic.prev_page():
            self._play_click(0.3)
            self.logic.rebuild_page_items()
            self._refresh()
        else:
            self._play_click(0.15)

    def _on_next(self):
        if self.logic.next_page():
            self._play_click(0.3)
            self.logic.rebuild_page_items()
            self._refresh()
        else:
            self._play_click(0.15)

    def _on_delete(self):
        if not self.logic.has_selection():
            return
        if self.logic.request_delete():
            self._play_click()
            self._update_modal_visibility()

    def _on_confirm_yes(self):
        ok = self.logic.confirm_delete()
        if ok:
            self._play_click()
            toast_info("Foto excluída com sucesso!", duration=2.0)
            self._refresh()
        else:
            toast_warning("Erro ao excluir a foto!", duration=2.0)
            self._update_modal_visibility()

    def _on_confirm_no(self):
        self.logic.cancel_delete()
        self._play_click(0.25)
        self._update_modal_visibility()

    # =================================================================
    # CLIQUE NAS FOTOS
    # =================================================================
    def _handle_photo_click(self, pos) -> bool:
        """
        Chamado no MOUSEBUTTONDOWN. Detecta clique sobre uma polaroid
        (usando screen_rect do último render) e expande.
        """
        item = self.logic.get_item_at(pos)
        if item is None:
            # Clique em área vazia: limpa seleção
            self.logic.clear_selection()
            self._update_buttons_visibility()
            return False

        viewport_rect = self._viewport_rect()
        self.logic.expand_item(item, viewport_rect)
        self._play_click(0.4)
        self._update_buttons_visibility()
        return True

    # =================================================================
    # HELPERS
    # =================================================================
    def _viewport_rect(self) -> pygame.Rect:
        return pygame.Rect(
            self.screen_manager.viewport_x,
            self.screen_manager.viewport_y,
            self.screen_manager.viewport_width,
            self.screen_manager.viewport_height,
        )

    # =================================================================
    # EVENTOS
    # =================================================================
    def handle_event(self, event):
        # ===== MODAL DE CONFIRMAÇÃO (prioridade) =====
        if self.logic.delete_confirmation_active:
            super().handle_event(event)
            return

        # ===== PREVIEW EXPANDIDO =====
        if self.logic.is_expanded():
            self._handle_expanded_event(event)
            return

        # ===== TECLADO =====
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self._on_back()
                return
            if event.key == pygame.K_LEFT:
                self._on_prev()
                return
            if event.key == pygame.K_RIGHT:
                self._on_next()
                return
            if event.key == pygame.K_DELETE and self.logic.has_selection():
                self._on_delete()
                return

        # ===== MOUSEMOTION → hover das fotos =====
        if event.type == pygame.MOUSEMOTION:
            hovered = self.logic.update_hover(event.pos)
            if hovered is not None:
                pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_HAND)
            else:
                pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_ARROW)

        # ===== MOUSEWHEEL =====
        if event.type == pygame.MOUSEWHEEL:
            if event.y > 0:
                self._on_prev()
            elif event.y < 0:
                self._on_next()
            return

        # ===== CLIQUE ESQUERDO =====
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            # Só trata clique nas fotos se NÃO for sobre um botão
            # (os botões são tratados por super().handle_event)
            if self._handle_photo_click(event.pos):
                return

        super().handle_event(event)

    def _handle_expanded_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_SPACE):
                self.logic.close_expanded()
            elif event.key == pygame.K_DELETE:
                if self.logic.request_delete():
                    self._update_modal_visibility()

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            exp = self.logic.expanded_photo
            if exp and exp.is_open:
                rect = getattr(exp, "_render_rect", None)
                if rect is None or not rect.collidepoint(event.pos):
                    self.logic.close_expanded()

    # =================================================================
    # UPDATE
    # =================================================================
    def fixed_update(self, dt):
        self.logic.update(dt, self._viewport_rect())
        self._update_buttons_visibility()
        super().fixed_update(dt)

    # =================================================================
    # RENDER
    # =================================================================
    def render(self, screen):
        # 1. Widgets (bg, painéis, botões, grid com render_callback)
        super().render(screen)

        # 2. Estado vazio
        if not self.logic.photo_paths and not self.logic.delete_confirmation_active:
            self._render_empty_state(screen)

        # 3. Preview expandido
        if (self.logic.expanded_photo is not None
                and not self.logic.delete_confirmation_active):
            self.logic.expanded_photo.render(screen)

        # 4. Hint rodapé
        if not self.logic.delete_confirmation_active:
            self._render_hint(screen)

    # -----------------------------------------------------------------
    def _render_empty_state(self, screen):
        vp = self._viewport_rect()
        center_x = vp.centerx
        center_y = vp.centery

        empty_font = pygame.font.Font(None, 34)
        text = empty_font.render(
            "Nenhuma foto ainda...", True, (200, 215, 240))
        screen.blit(text, text.get_rect(center=(center_x, center_y - 20)))

        hint_font = pygame.font.Font(None, 22)
        hint = hint_font.render(
            "Use a Camera durante o jogo para tirar fotos!",
            True, (160, 180, 220))
        screen.blit(hint, hint.get_rect(center=(center_x, center_y + 25)))

        # Câmera ilustrativa
        accent = (255, 210, 74)
        accent_soft = (255, 230, 140)

        cam_w, cam_h = int(vp.width * 0.10), int(vp.height * 0.08)
        cam_x = center_x - cam_w // 2
        cam_y = center_y - int(vp.height * 0.20)

        pygame.draw.rect(screen, (30, 38, 60),
                         (cam_x, cam_y, cam_w, cam_h), border_radius=8)
        pygame.draw.rect(screen, accent,
                         (cam_x, cam_y, cam_w, cam_h), 2, border_radius=8)
        pygame.draw.circle(screen, (20, 25, 40),
                           (cam_x + cam_w // 2, cam_y + cam_h // 2),
                           int(min(cam_w, cam_h) * 0.30))
        pygame.draw.circle(screen, accent_soft,
                           (cam_x + cam_w // 2, cam_y + cam_h // 2),
                           int(min(cam_w, cam_h) * 0.30), 2)
        pygame.draw.circle(screen, (200, 220, 255),
                           (cam_x + cam_w - 15, cam_y + 12), 4)

    def _render_hint(self, screen):
        vp = self._viewport_rect()
        hint_font = pygame.font.Font(None, 18)
        hint = hint_font.render(
            "Clique em uma foto para expandir  |  DEL para excluir  |  ESC para voltar",
            True, (140, 150, 190))
        bg = pygame.Surface(
            (hint.get_width() + 16, hint.get_height() + 8),
            pygame.SRCALPHA)
        bg.fill((0, 0, 0, 120))
        screen.blit(bg, (vp.x + vp.width - hint.get_width() - 25,
                         vp.y + vp.height - 26))
        screen.blit(hint, (vp.x + vp.width - hint.get_width() - 17,
                           vp.y + vp.height - 22))

    # =================================================================
    def on_back(self):
        self._on_back()