# src/scenes/npc_hall_scene/relearn_scene.py
"""
Tela de Reaprender Movimento — orquestrador (JSON + Logic + Scene).

Ao confirmar, a tela NÃO fecha: apenas mostra feedback no rodapé e
atualiza os dados. O usuário só sai clicando em CANCELAR ou ESC.
"""
import pygame

from src.ui.screen_template import StandardScreen
from src.ui.screen_loader import ScreenLoader
from src.managers.sounds.sound_manager import sound_manager, SoundEffect

from .relearn_logic import RelearnLogic


RELEARN_JSON = "res/ui_layouts/relearn.json"


class RelearnScene(StandardScreen):
    title = ""
    show_back_button = False

    # =================================================================
    def __init__(self, game, cost: int, return_scene=None):
        self.game = game
        self.player = game.player
        self.return_scene = return_scene

        self.logic = RelearnLogic(game, cost)

        super().__init__(game)

    # =================================================================
    def build(self):
        ScreenLoader.load(self, RELEARN_JSON)
        self._refresh_all()

    def enter(self):
        self._refresh_all()

    # =================================================================
    def get_actions(self):
        return {
            "poke_click":  lambda idx: self._on_poke_click(idx),
            "move_click":  lambda idx: self._on_move_click(idx),
            "slot_0":      lambda *_: self._on_slot_click(0),
            "slot_1":      lambda *_: self._on_slot_click(1),
            "slot_2":      lambda *_: self._on_slot_click(2),
            "slot_3":      lambda *_: self._on_slot_click(3),
            "confirm":     lambda *_: self._on_confirm(),
            "cancel":      lambda *_: self._on_cancel(),
        }

    # =================================================================
    # HELPERS DE UI
    # =================================================================
    def _set(self, wid, text):
        """Aplica texto num widget. Labels usam `.text`; Buttons usam `.label`."""
        w = self.get(wid)
        if w is None:
            return
        if hasattr(w, "label"):
            try:
                w.label = text
            except Exception:
                pass
        if hasattr(w, "text"):
            try:
                w.text = text
            except Exception:
                pass

    def _set_color(self, wid, *, fill=None, border=None, text=None):
        w = self.get(wid)
        if w is None:
            return
        if fill is not None and hasattr(w, "fill_color"):
            w.fill_color = fill
        if border is not None and hasattr(w, "border_color"):
            w.border_color = border
        if text is not None and hasattr(w, "text_color"):
            w.text_color = text

    def _set_surface(self, wid, surf):
        """
        Tenta aplicar um sprite a um widget. Suporta vários nomes de atributo
        comuns em widgets do projeto; se nenhum existir, retorna False.

        Quando o sprite é aplicado, também desliga o fill_color para que o
        sprite não seja desenhado por cima de uma cor sólida.
        """
        if surf is None:
            return False
        w = self.get(wid)
        if w is None:
            return False

        for attr in ("image", "surface", "sprite", "_surface", "icon"):
            if hasattr(w, attr):
                try:
                    setattr(w, attr, surf)
                    if hasattr(w, "fill_color"):
                        w.fill_color = None
                    if hasattr(w, "border_color"):
                        w.border_color = None
                    return True
                except Exception:
                    continue

        # último recurso: método set_image()
        if hasattr(w, "set_image"):
            try:
                w.set_image(surf)
                return True
            except Exception:
                return False

        return False

    def _feed(self, wid, items):
        w = self.get(wid)
        if w is not None:
            w.items = items

    def _hex_to_rgb(self, h: str):
        h = h.lstrip("#")
        return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))

    def _play(self, v=0.25):
        try:
            sound_manager.play_effect(SoundEffect.CLICK, volume=v)
        except Exception:
            pass

    # =================================================================
    # REFRESH
    # =================================================================
    def _refresh_all(self):
        self._refresh_header()
        self._refresh_pokemon_grid()
        self._refresh_moves_grid()
        self._refresh_comparison()
        self._refresh_slots()
        self._refresh_confirm_state()

    def _refresh_header(self):
        self._set("lbl_info", self.logic.header_info_text())

    def _refresh_pokemon_grid(self):
        self._feed("poke_grid", self.logic.pokemon_items())
        self._set("poke_count", str(len(self.logic.entries)))

    def _refresh_moves_grid(self):
        self._feed("moves_grid", self.logic.move_items())
        n = len(self.logic.learnable_moves)
        self._set("moves_count", f"{n} disponiveis")

    def _refresh_comparison(self):
        self._apply_comparison("left",  self.logic.comparison_data("left"))
        self._apply_comparison("right", self.logic.comparison_data("right"))

    def _apply_comparison(self, side: str, data: dict):
        p = f"cmp_{side}_"

        self._set(p + "title", data["title"])
        self._set(p + "name", data["name"])
        self._set(p + "cat_lbl", data["cat_lbl"])
        self._set(p + "stats", data["stats_str"])
        self._set(p + "desc", data["description"])

        # Type bar 3× (144×48) — Surface direto, sem reescala
        self._set_image(p + "type_bg", data.get("type_bar"))

        # Categoria continua painel de cor sólida
        self._set_color(p + "cat_bg",
                        fill=self._hex_to_rgb(data["cat_color"]))

    def _set_image(self, wid, surf):
        """Aplica uma Surface a um widget do tipo `image`."""
        w = self.get(wid)
        if w is None or surf is None:
            return
        for attr in ("surface", "image", "_surface", "sprite"):
            if hasattr(w, attr):
                try:
                    setattr(w, attr, surf)
                    return
                except Exception:
                    continue

    def _refresh_slots(self):
        slots = self.logic.slot_data()
        for i, s in enumerate(slots):
            wid = f"slot_{i}"
            self._set(wid, s["name"])  # só o nome
            self._set_icon(wid, s["icon"])  # ícone do tipo (38x38)

            selected = self.logic.slot_selected(i)
            if selected:
                self._set_color(wid,
                                fill=(55, 75, 105),
                                border=(150, 190, 255))
            else:
                self._set_color(wid,
                                fill=(26, 32, 48),
                                border=(70, 80, 106))

    def _set_icon(self, wid, surf):
        """Aplica uma Surface como ícone do botão (mesmo se vier None)."""
        w = self.get(wid)
        if w is None:
            return
        for attr in ("icon_surface", "icon", "_icon"):
            if hasattr(w, attr):
                try:
                    setattr(w, attr, surf)  # None é ok — botão desenha só texto
                    return
                except Exception:
                    continue

    def _refresh_confirm_state(self):
        ready = self.logic.confirm_ready()
        self._set("btn_confirm", self.logic.confirm_label())
        if ready:
            self._set_color("btn_confirm",
                            fill=(55, 130, 70), border=(120, 220, 140))
        else:
            self._set_color("btn_confirm",
                            fill=(55, 58, 68), border=(100, 105, 115))

    def _set_feedback(self, msg: str, ok: bool = True):
        self._set("feedback_lbl", msg)
        self._set_color("feedback_lbl",
                        text=(150, 220, 150) if ok else (240, 140, 140))

    # =================================================================
    # AÇÕES
    # =================================================================
    def _on_poke_click(self, idx):
        if self.logic.select_pokemon(idx):
            self._play(0.2)
            self._set_feedback("")
            self._refresh_pokemon_grid()
            self._refresh_moves_grid()
            self._refresh_comparison()
            self._refresh_slots()
            self._refresh_confirm_state()

    def _on_move_click(self, idx):
        if self.logic.select_move(idx):
            self._play(0.2)
            self._set_feedback("")
            self._refresh_moves_grid()
            self._refresh_comparison()
            self._refresh_confirm_state()

    def _on_slot_click(self, idx):
        if self.logic.select_slot(idx):
            self._play(0.2)
            self._set_feedback("")
            self._refresh_comparison()
            self._refresh_slots()
            self._refresh_confirm_state()

    def _on_confirm(self):
        ok, msg = self.logic.try_learn()
        if ok:
            try:
                sound_manager.play_effect(SoundEffect.LEVELUP)
            except Exception:
                pass
        else:
            self._play(0.25)

        self._set_feedback(msg, ok=ok)
        self._refresh_all()

    def _on_cancel(self):
        self._play(0.3)
        self._close_scene()

    def _close_scene(self):
        if self.return_scene is not None:
            try:
                self.game.current_scene = self.return_scene
                return
            except Exception:
                pass
        try:
            from src.scenes.menu_scene import MenuScene
            self.game.current_scene = MenuScene(self.game)
        except Exception:
            pass

    # =================================================================
    # EVENTOS
    # =================================================================
    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self._on_cancel()
            return
        super().handle_event(event)

    def fixed_update(self, dt):
        super().fixed_update(dt)

    def on_back(self):
        self._on_cancel()