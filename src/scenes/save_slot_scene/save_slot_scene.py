# src/scenes/save_slot_scene/save_slot_scene.py
"""Tela de seleção de save — orquestrador JSON ↔ lógica."""
import pygame

from src.ui.screen_template import StandardScreen
from src.ui.screen_loader import ScreenLoader
from src.managers.sounds.sound_manager import sound_manager, SoundEffect

from .save_slot_logic import SaveSlotLogic


MAIN_JSON = "res/ui_layouts/save_slot.json"


class SaveSlotScene(StandardScreen):
    title = ""
    show_back_button = False

    def __init__(self, game):
        self.player = game.player
        self.logic = SaveSlotLogic(game)

        # Modal de confirmação
        self._pending = None   # (slot_num, action, title, msg)

        super().__init__(game)

    # =================================================================
    def build(self):
        ScreenLoader.load(self, MAIN_JSON)
        self._refresh_slots()

    def enter(self):
        self.logic.clear_cache()
        self._refresh_slots()
        if not pygame.mixer.music.get_busy():
            try:
                self.game.menu_scene.on_enter()
            except Exception:
                pass

    def get_actions(self):
        return {
            "back":           self._on_back,
            "slot1_primary":  lambda *_: self._slot_primary(1),
            "slot1_delete":   lambda *_: self._slot_delete(1),
            "slot2_primary":  lambda *_: self._slot_primary(2),
            "slot2_delete":   lambda *_: self._slot_delete(2),
            "slot3_primary":  lambda *_: self._slot_primary(3),
            "slot3_delete":   lambda *_: self._slot_delete(3),
            "modal_yes":      lambda *_: self._modal_confirm(),
            "modal_no":       lambda *_: self._modal_cancel(),
        }

    # =================================================================
    # ATUALIZAÇÃO DOS SLOTS
    # =================================================================
    def _refresh_slots(self):
        slots = self.logic.list_slots()
        for i, info in enumerate(slots):
            self._apply_slot(i + 1, info)

    def _apply_slot(self, slot_num: int, info: dict):
        prefix = f"slot_{slot_num}_"

        # Nome do save
        self._set(f"{prefix}name", info["name"])

        # Infos
        self._set(f"{prefix}info_ch", self.logic.info_line_chapter(info))
        self._set(f"{prefix}info_pk", self.logic.info_line_pokemon(info))
        self._set(f"{prefix}info_tm", self.logic.info_line_team(info))
        self._set(f"{prefix}info_ti", self.logic.info_line_playtime(info))
        self._set(f"{prefix}info_dt", self.logic.info_line_date(info))

        # Avatar
        self._set_surface(f"{prefix}avatar", info.get("avatar"))

        # Badge "ATUAL"
        badge = self.get(f"{prefix}badge")
        if badge is not None:
            badge.visible = bool(info["is_current"])

        # Borda do painel: dourada se for o atual
        panel = self.get(f"{prefix}panel")
        if panel is not None:
            if info["is_current"]:
                panel.border_color = (255, 210, 74)
                panel.border_width = 3
            else:
                panel.border_color = (58, 72, 112)
                panel.border_width = 2

        # Botão primário — ATRIBUTOS DIRETOS (não .props!)
        btn_primary = self.get(f"{prefix}btn_primary")
        if btn_primary is not None:
            if info["is_empty"]:
                btn_primary.label = "NOVO JOGO"
                btn_primary.fill_color = (42, 110, 62)
                btn_primary.border_color = (90, 216, 112)
                btn_primary.text_color = (216, 240, 224)
            elif info["is_error"]:
                btn_primary.label = "DELETAR"
                btn_primary.fill_color = (138, 42, 42)
                btn_primary.border_color = (200, 85, 85)
                btn_primary.text_color = (240, 216, 216)
            else:
                btn_primary.label = "CARREGAR"
                btn_primary.fill_color = (42, 110, 62)
                btn_primary.border_color = (90, 216, 112)
                btn_primary.text_color = (216, 240, 224)

            btn_primary.visible = True

            # Invalida cache de gradiente (senão a cor não muda)
            if hasattr(btn_primary, "_invalidate_cache"):
                btn_primary._invalidate_cache()

        # Botão de deletar (só aparece em slots preenchidos)
        btn_delete = self.get(f"{prefix}btn_delete")
        if btn_delete is not None:
            btn_delete.visible = bool(not info["is_empty"] and not info["is_error"])

    def _set(self, wid: str, text: str):
        w = self.get(wid)
        if w is not None and hasattr(w, "text"):
            w.text = text

    def _set_surface(self, wid: str, surf):
        w = self.get(wid)
        if w is not None and hasattr(w, "surface"):
            w.surface = surf

    def _play_click(self, v=0.3):
        try:
            sound_manager.play_effect(SoundEffect.CLICK, volume=v)
        except Exception:
            pass

    # =================================================================
    # AÇÕES DOS SLOTS
    # =================================================================
    def _slot_primary(self, slot_num: int):
        self._play_click()
        slots = self.logic.list_slots()
        if slot_num - 1 >= len(slots):
            return
        info = slots[slot_num - 1]

        if info["is_empty"]:
            # Novo jogo → confirmação
            self._open_modal(
                slot_num, "new",
                "Iniciar novo jogo?",
                f"Um novo save sera criado no Slot {slot_num}."
            )
        elif info["is_error"]:
            # Corrompido → confirmação de delete
            self._open_modal(
                slot_num, "delete",
                f"Deletar Slot {slot_num}?",
                "Este arquivo esta corrompido. Esta acao nao pode ser desfeita."
            )
        else:
            # Carregar
            sound_manager.stop_music(fade_ms=300)
            ok = self.logic.load_slot(slot_num)
            if not ok:
                try:
                    from src.ui.toast_renderer import toast_warning
                    toast_warning(f"Erro ao carregar o Slot {slot_num}", duration=3.0)
                except Exception:
                    pass

    def _slot_delete(self, slot_num: int):
        self._play_click()
        self._open_modal(
            slot_num, "delete",
            f"Deletar Slot {slot_num}?",
            "Esta acao nao pode ser desfeita."
        )

    # =================================================================
    # MODAL
    # =================================================================
    def _open_modal(self, slot_num: int, action: str, title: str, msg: str):
        self._pending = (slot_num, action, title, msg)
        self._set("modal_title", title)
        self._set("modal_msg", msg)
        self._show_modal(True)

    def _close_modal(self):
        self._pending = None
        self._show_modal(False)

    def _show_modal(self, visible: bool):
        for wid in ("modal_backdrop", "modal_panel", "modal_title",
                    "modal_msg", "modal_yes", "modal_no"):
            w = self.get(wid)
            if w is not None:
                w.visible = visible

    def _modal_confirm(self):
        self._play_click()
        if self._pending is None:
            self._close_modal()
            return
        slot_num, action, _, _ = self._pending
        self._close_modal()

        if action == "delete":
            self.logic.delete_slot(slot_num)
            self.logic.clear_cache()
            self._refresh_slots()
        elif action == "new":
            sound_manager.stop_music(fade_ms=300)
            self.logic.new_game(slot_num)

    def _modal_cancel(self):
        self._play_click()
        self._close_modal()

    # =================================================================
    # NAVEGAÇÃO
    # =================================================================
    def _on_back(self, *_):
        self._play_click()
        self.game.current_scene = self.game.menu_scene

    # =================================================================
    # EVENTOS
    # =================================================================
    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            if self._pending is not None:
                self._close_modal()
            else:
                self._on_back()
            return
        super().handle_event(event)

    # =================================================================
    def on_back(self):
        self._on_back()