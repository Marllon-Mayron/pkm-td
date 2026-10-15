# src/scenes/starter_select/starter_select_scene.py
"""
Cena de selecao de inicial — padrao Editor (JSON + Logic + Scene).
"""
import pygame

from src.ui.screen_template import StandardScreen
from src.ui.screen_loader import ScreenLoader
from src.managers.sounds.sound_manager import sound_manager, SoundEffect

from src.scenes.starter_select_scene.starter_select_logic import StarterSelectLogic


LAYOUT_PATH = "res/ui_layouts/starter_select.json"

CARD_LAYOUT = [
    (0.10,  0.27, 0.25, 0.38),
    (0.375, 0.27, 0.25, 0.38),
    (0.65,  0.27, 0.25, 0.38),
]

INMAP_LAYOUT = [
    (0.10,  0.66, 0.25, 0.18),
    (0.375, 0.66, 0.25, 0.18),
    (0.65,  0.66, 0.25, 0.18),
]


class StarterSelectScene(StandardScreen):
    title = ""
    show_back_button = False

    def __init__(self, game):
        self.logic = StarterSelectLogic(game)
        super().__init__(game)

    # =================================================================
    def build(self):
        ScreenLoader.load(self, LAYOUT_PATH)
        self._refresh_all()

    def get_actions(self):
        return {
            "gen_1":   lambda *_: self._on_gen(1),
            "gen_2":   lambda *_: self._on_gen(2),
            "gen_3":   lambda *_: self._on_gen(3),
            "go_back": self._on_back,
            "confirm": self._on_confirm,
        }

    # =================================================================
    # REFRESH
    # =================================================================
    def _refresh_all(self):
        self._refresh_gen_buttons()
        for i in range(3):
            self._refresh_card(i)
            self._clear_inmap(i)

    def _refresh_gen_buttons(self):
        for gen in (1, 2, 3):
            btn = self.get(f"btn_gen_{gen}")
            if btn is None:
                continue
            if gen == self.logic.current_generation:
                btn.fill_color   = (184, 136, 32)
                btn.border_color = (255, 210, 74)
                btn.text_color   = (255, 255, 255)
            else:
                btn.fill_color   = (42, 51, 88)
                btn.border_color = (90, 106, 154)
                btn.text_color   = (232, 232, 240)

    def _refresh_card(self, idx: int):
        # ---- Highlight do card ----
        card = self.get(f"card_{idx+1}")
        if card is not None:
            if idx == self.logic.selected_index:
                card.border_color = (255, 210, 74)
                card.border_width = 4
                card.fill_color   = (248, 232, 180)
            else:
                card.border_color = (48, 60, 96)
                card.border_width = 3
                card.fill_color   = (232, 232, 208)

        # ---- Sprite frontal ----
        sprite = self.logic.get_sprite(idx)
        img = self.get(f"card_{idx+1}_sprite")
        if img is not None:
            img.surface = self._fit_sprite(
                sprite, idx, frac_w=0.85, frac_h=0.62,
            )

        # ---- Nome ----
        starter = self.logic.get_starter(idx)
        name = starter["name"] if starter else "—"
        lbl = self.get(f"card_{idx+1}_name")
        if lbl is not None:
            lbl.text = name

        # ---- Barra(s) de tipagem (1 ou 2) ----
        bar_img = self.get(f"card_{idx+1}_type_bar")
        if bar_img is not None:
            combo = self.logic.get_type_bar_combo(idx)
            bar_img.surface = combo
            if combo is None:
                bar_img.visible = False
            else:
                bar_img.visible = True

    def _clear_inmap(self, idx: int):
        img = self.get(f"inmap_{idx+1}_sprite")
        if img is not None:
            img.surface = None
        lbl = self.get(f"inmap_{idx+1}_label")
        if lbl is not None:
            lbl.text = ""

    # =================================================================
    # ANIMACAO
    # =================================================================
    def fixed_update(self, dt):
        super().fixed_update(dt)
        self.logic.update_animations(dt)
        for i in range(3):
            self._update_inmap(i)

    def _update_inmap(self, idx: int):
        surf = self.logic.get_inmap_surface(idx)
        img = self.get(f"inmap_{idx+1}_sprite")
        if img is None:
            return

        img.surface = self._fit_sprite(
            surf, idx, frac_w=0.80, frac_h=0.72, use_inmap=True,
        )

        lbl = self.get(f"inmap_{idx+1}_label")
        if lbl is not None:
            lbl.text = self.logic.get_inmap_direction_label(idx)

    # =================================================================
    # HELPERS DE ESCALA
    # =================================================================
    def _fit_sprite(self, surf, idx: int, *, frac_w: float,
                    frac_h: float, use_inmap: bool = False):
        if surf is None:
            return None

        sm = self.screen_manager
        if sm is None:
            return surf

        layout = INMAP_LAYOUT if use_inmap else CARD_LAYOUT
        area_w = layout[idx][2] * sm.viewport_width
        area_h = layout[idx][3] * sm.viewport_height

        max_w = max(1, int(area_w * frac_w))
        max_h = max(1, int(area_h * frac_h))

        sw, sh = surf.get_width(), surf.get_height()
        if sw <= 0 or sh <= 0:
            return surf

        scale = min(max_w / sw, max_h / sh)
        new_w = max(1, int(sw * scale))
        new_h = max(1, int(sh * scale))

        try:
            return pygame.transform.scale(surf, (new_w, new_h))
        except Exception:
            return surf

    # =================================================================
    # ACOES
    # =================================================================
    def _on_gen(self, gen: int):
        if not self.logic.set_generation(gen):
            return
        self._play_sound()
        self._refresh_all()

    def _on_card(self, idx: int):
        if self.logic.select_index(idx):
            self._play_sound()
            for i in range(3):
                self._refresh_card(i)

    def _on_back(self, *_):
        self._play_sound()
        try:
            self.game.current_scene = self.game.menu_scene
        except Exception:
            pass

    def _on_confirm(self, *_):
        ok, result = self.logic.confirm()
        if ok:
            try:
                sound_manager.play_effect(SoundEffect.LEVELUP)
            except Exception:
                pass
            try:
                from src.scenes.phase_selector.phase_select_scene import PhaseSelectScene
                self.game.current_scene = PhaseSelectScene(self.game)
            except Exception as e:
                print(f"[STARTER_SELECT] Falha ao ir para PhaseSelect: {e}")
        else:
            try:
                sound_manager.play_effect(SoundEffect.ERROR)
            except Exception:
                pass
            self._set_feedback(str(result), ok=False)

    # =================================================================
    # EVENTOS
    # =================================================================
    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self._on_back()
                return True

            if event.key in (pygame.K_LEFT, pygame.K_a):
                self.logic.cycle_index(-1)
                self._play_sound()
                for i in range(3):
                    self._refresh_card(i)
                return True

            if event.key in (pygame.K_RIGHT, pygame.K_d):
                self.logic.cycle_index(+1)
                self._play_sound()
                for i in range(3):
                    self._refresh_card(i)
                return True

            if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self._on_confirm()
                return True

            if event.key in (pygame.K_1, pygame.K_KP1):
                self._on_gen(1); return True
            if event.key in (pygame.K_2, pygame.K_KP2):
                self._on_gen(2); return True
            if event.key in (pygame.K_3, pygame.K_KP3):
                self._on_gen(3); return True

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            idx = self._hit_card(event.pos)
            if idx >= 0:
                self._on_card(idx)
                return True

        super().handle_event(event)

    def _hit_card(self, pos) -> int:
        sm = self.screen_manager
        if sm is None:
            return -1
        vx, vy = sm.viewport_x, sm.viewport_y
        vw, vh = sm.viewport_width, sm.viewport_height
        for i, (cx, cy, cw, ch) in enumerate(CARD_LAYOUT):
            rx = vx + cx * vw
            ry = vy + cy * vh
            rw = cw * vw
            rh = ch * vh
            if rx <= pos[0] <= rx + rw and ry <= pos[1] <= ry + rh:
                return i
        return -1

    # =================================================================
    # HELPERS
    # =================================================================
    def _play_sound(self):
        try:
            sound_manager.play_effect(SoundEffect.CLICK, volume=0.4)
        except Exception:
            pass

    def _set_feedback(self, msg: str, ok: bool = True):
        lbl = self.get("feedback")
        if lbl is None:
            return
        lbl.text = msg
        lbl.text_color = (150, 220, 150) if ok else (240, 140, 140)

    # =================================================================
    # CICLO DE VIDA
    # =================================================================
    def on_enter(self):
        self._refresh_all()
        for i in range(3):
            self._update_inmap(i)

    def on_back(self):
        self._on_back()

    def on_resize(self):
        super().on_resize()
        self._refresh_all()