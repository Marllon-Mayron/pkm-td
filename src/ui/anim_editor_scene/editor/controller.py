"""AnimEditorController — editor de animacoes e cutscenes.

Atalhos:
  Space       play/pause
  Setas       step frame (Shift = 10)
  Home/End    primeiro/ultimo frame
  Ctrl+S      salvar
  Ctrl+N      novo
  Ctrl+Z      desfazer
  Ctrl+Y      refazer (ou Ctrl+Shift+Z)
  Ctrl+L      log
  G           grid
  O           onion skin
  K           auto-key
  P           preview em tela cheia
  F           fit zoom
  +/-         zoom
  Delete      remove keyframe selecionado
  Middle drag pan no canvas
  Ctrl+scroll zoom no canvas
  Esc         sair
"""
import pygame

from src.scenes.base_scene import BaseScene
from src.ui.theme import Palette, FontBook
from src.anim.animation import AnimDefinition
from src.anim.actor import ActorDef, ActorKeyframe, ActorRuntime
from src.anim.layer import (
    Keyframe, LayerDef, SpriteLayerDef, EmitterLayerDef, FilterLayerDef,
    _parse_hex_color, _to_hex_color,
)
from src.anim.camera import CameraDef, CameraKeyframe, CameraRuntime
from src.anim.animator import Animator

from src.ui.anim_editor_scene.editor.timeline import TimelineWidget
from src.ui.anim_editor_scene.editor.scrollbar import ScrollBar
from src.ui.anim_editor_scene.editor.pokemon_picker import PokemonPicker
from src.ui.anim_editor_scene.editor.open_picker import OpenPicker
from src.ui.anim_editor_scene.editor import sections as S
from src.ui.anim_editor_scene.editor import scene_loader as SL
from src.ui.anim_editor_scene.editor.logger import EditorLogger
from src.ui.anim_editor_scene.editor.render_mixin import AnimEditorRenderMixin


# =====================================================================
class InlineField:
    def __init__(self, key, kind="text"):
        self.key = key
        self.kind = kind
        self.focused = False
        self.buffer = ""
        self.rect = pygame.Rect(0, 0, 0, 0)

    def begin(self, value):
        self.focused = True
        self.buffer = "" if value is None else str(value)

    def cancel(self):
        self.focused = False
        self.buffer = ""

    def handle_key(self, event) -> str:
        if event.key in (pygame.K_RETURN, pygame.K_TAB):
            return "commit"
        if event.key == pygame.K_ESCAPE:
            return "cancel"
        if event.key == pygame.K_BACKSPACE:
            self.buffer = self.buffer[:-1]
            return "edit"
        if event.unicode and event.unicode.isprintable():
            self.buffer += event.unicode
            return "edit"
        return "edit"


# =====================================================================
class AnimEditorController(AnimEditorRenderMixin, BaseScene):
    TOP_H = 78
    STATUS_H = 28
    LEFT_W = 300
    RIGHT_W = 380
    TIMELINE_H = 220

    FONT_SM = 12
    FONT_BASE = 13
    FONT_VALUE = 14
    FONT_HEADER = 15
    FONT_TITLE = 19

    ROW_H = 28
    ROW_GAP = 4

    UNDO_LIMIT = 60

    _FIELD_LABELS = {
        "name": "Nome", "category": "Categoria", "fps": "FPS",
        "duration_frames": "Duracao", "loop": "Loop",
        "loop_count": "Loop count", "anchor": "Ancora", "space": "Space",
        "binding_trigger": "Trigger",
        "bg_type": "BG tipo", "bg_color": "BG cor",
        "bg_image": "BG imagem", "bg_mode": "BG modo", "bg_dim": "BG dim",
        "source": "Fonte", "start_frame": "Frame ini", "volume": "Volume",
        "id": "ID", "type": "Tipo", "z": "Z", "blend": "Blend",
        "pivot": "Pivot", "offset_x": "Offset X", "offset_y": "Offset Y",
        "vis_start": "Vis ini", "vis_end": "Vis fim",
        "image_path": "Imagem", "easing": "Easing",
        "anchor_actor": "Segue ator",
        "aim_at": "Mirar em",
        "camera_enabled": "Camera ON", "camera_x": "Camera X",
        "camera_y": "Camera Y", "camera_zoom": "Camera Zoom",
        "camera_easing": "Camera Easing", "camera_follow": "Camera Follow",
        "frame_width": "Frame W", "frame_height": "Frame H",
        "frame_index": "Frame idx",
        "f": "Frame", "x": "X", "y": "Y",
        "rot": "Rotacao", "scale": "Escala",
        "alpha": "Alpha", "tint": "Tint",
        "spawn_rate": "Taxa/s", "max_particles": "Max part",
        "gravity": "Gravidade",
        "area_x": "Area X", "area_y": "Area Y",
        "area_w": "Area W", "area_h": "Area H",
        "vel_x_min": "Vel X min", "vel_x_max": "Vel X max",
        "vel_y_min": "Vel Y min", "vel_y_max": "Vel Y max",
        "life_min": "Vida min", "life_max": "Vida max",
        "scale_min": "Esc min", "scale_max": "Esc max",
        "alpha_min": "Alpha min", "alpha_max": "Alpha max",
        "rot_min": "Rot min", "rot_max": "Rot max",
        "fade_out": "Fade out", "tints": "Tints",
        "actor_id": "ID do ator", "source_type": "Fonte",
        "pokemon_id": "Pokemon ID", "shiny": "Shiny",
        "default_anim": "Anim padrao", "default_dir": "Dir padrao",
        "item_id": "Item ID", "sprite_path": "Sprite path",
        "mock_label": "Mock label", "mock_color": "Mock cor",
        "display_scale": "Escala base",
        "flip_x": "Flip X",
        "kf_x": "X", "kf_y": "Y",
        "kf_rot": "Rot", "kf_scale": "Escala",
        "kf_alpha": "Alpha",
        "kf_anim": "Anim", "kf_dir": "Dir",
        "size_px": "Tamanho (px)",
    }

    # =================================================================
    def __init__(self, game):
        super().__init__(game)

        self.logger = EditorLogger()

        # retangulos
        self.top_rect = None
        self.left_rect = None
        self.canvas_rect = None
        self.right_rect = None
        self.timeline_rect = None
        self.status_rect = None
        self._last_size = (0, 0)

        # hit-regions
        self._top_btns = {}
        self._left_clip_rect = pygame.Rect(0, 0, 0, 0)
        self._left_row_rects = []
        self._left_toggle_rects = []     # [(kind, obj_id, "lock"|"hide", rect)]
        self._left_add_rects = []
        self._right_clip_rect = pygame.Rect(0, 0, 0, 0)
        self._right_field_rects = []
        self._right_action_rects = []
        self.right_content_height = 0

        # scrollbars
        self.left_scrollbar = ScrollBar(width=8, wheel_step=3)
        self.right_scrollbar = ScrollBar(width=8, wheel_step=3)
        self.left_scroll = 0
        self.right_scroll = 0

        # animacao atual
        self.current_anim = self._make_default_anim()
        self.current_path = None
        self.dirty = False

        # selecao
        self.selection = None

        # reproducao
        self.current_frame = 0.0
        self.is_playing = False
        self.dragging_playhead = False
        self._drag_kf = None

        # canvas
        self.show_grid = True
        self.canvas_zoom = 1.0
        self.canvas_cam_x = 0.0
        self.canvas_cam_y = 0.0
        self._canvas_panning = False
        self._pan_start = (0, 0)

        # auto-key / onion
        self.auto_key = True
        self.show_onion = True
        self.onion_offsets = (-15, -30)

        # drag de ator
        self._drag_actor = None

        # preview animator (cache)
        self._preview_animator = None
        self._preview_animator_key = None
        self._preview_revision = 0

        # preview fullscreen
        self.preview_mode = False
        self.preview_playing = True
        self.preview_hud_hidden = False

        # ==== estado do editor: travar / esconder ====
        # Sets de (kind, obj_id): kind = "actor" | "layer"
        self._locked: set = set()
        self._hidden: set = set()

        # ==== undo / redo ====
        self._undo_stack: list = []
        self._redo_stack: list = []
        self._undo_in_progress = False

        # pickers
        self.pokemon_picker = PokemonPicker()
        self.open_picker = OpenPicker()

        # timeline
        self.timeline = TimelineWidget()

        # fields
        self.fields = {}
        self._rebuild_fields()

        # assets
        self.asset_list = []
        self.item_list = []
        self.pokemon_list = []
        self._reload_assets(initial=True)

        self.status_text = "Editor pronto. Ctrl+Z/Y desfaz/refaz. L/H trava/esconde."
        self._layout()
        self.logger.info("Editor iniciado.")

    # =================================================================
    def _make_default_anim(self) -> AnimDefinition:
        anim = AnimDefinition(name="nova_cutscene", category="cutscene")
        anim.duration_frames = 180
        anim.fps = 60
        anim.anchor = "screen"
        anim.space = "screen"
        anim.actors = []
        anim.layers = []
        anim.background = None
        return anim

    # =================================================================
    # HELPERS DE SELECAO
    # =================================================================
    def selected_actor(self):
        if self.selection and self.selection[0] == "actor":
            idx = self.selection[1]
            if 0 <= idx < len(self.current_anim.actors):
                return self.current_anim.actors[idx]
        return None

    def selected_layer(self):
        if self.selection and self.selection[0] == "layer":
            idx = self.selection[1]
            if 0 <= idx < len(self.current_anim.layers):
                return self.current_anim.layers[idx]
        return None

    # =================================================================
    # UNDO / REDO
    # =================================================================
    def _push_undo(self):
        """Grava snapshot do estado atual na pilha de undo.

        Deve ser chamado ANTES de qualquer mutacao que valha a pena
        desfazer. Snapshot = copia completa via AnimDefinition.to_dict().
        """
        if self._undo_in_progress:
            return
        try:
            snap = self.current_anim.to_dict()
        except Exception:
            return
        # Evita duplicar o topo
        if self._undo_stack and self._undo_stack[-1] == snap:
            return
        self._undo_stack.append(snap)
        if len(self._undo_stack) > self.UNDO_LIMIT:
            self._undo_stack.pop(0)
        self._redo_stack.clear()

    def _undo(self):
        if not self._undo_stack:
            self.status_text = "Nada para desfazer."
            return
        self._undo_in_progress = True
        try:
            current = self.current_anim.to_dict()
            self._redo_stack.append(current)
            snap = self._undo_stack.pop()
            self._restore_from_snapshot(snap)
            self.status_text = "Desfeito."
        finally:
            self._undo_in_progress = False

    def _redo(self):
        if not self._redo_stack:
            self.status_text = "Nada para refazer."
            return
        self._undo_in_progress = True
        try:
            current = self.current_anim.to_dict()
            self._undo_stack.append(current)
            snap = self._redo_stack.pop()
            self._restore_from_snapshot(snap)
            self.status_text = "Refeito."
        finally:
            self._undo_in_progress = False

    def _restore_from_snapshot(self, snap: dict):
        """Recria o current_anim a partir de um snapshot."""
        self.current_anim = AnimDefinition.from_dict(snap)

        # corrige selecao se saiu de range
        if self.selection:
            kind, idx = self.selection
            if kind == "actor" and idx >= len(self.current_anim.actors):
                self.selection = None
            elif kind == "layer" and idx >= len(self.current_anim.layers):
                self.selection = None

        # limpa drags
        self._drag_actor = None
        self._drag_kf = None

        # reseta o preview animator pra nao herdar cache de atores antigos
        if self._preview_animator is not None:
            self._preview_animator.stop()
        self._preview_animator = None
        self._preview_animator_key = None
        self._preview_revision += 1

        self._rebuild_fields()
        self._layout_right_panel()
        self._layout_left_list()
        self.timeline._recalc_tracks()
        self.mark_dirty()

    # =================================================================
    # TRAVAR / ESCONDER
    # =================================================================
    def _actor_key(self, actor_def):
        return ("actor", getattr(actor_def, "id", ""))

    def _layer_key(self, layer_def):
        return ("layer", getattr(layer_def, "id", ""))

    def is_locked(self, kind, obj_id):
        return (kind, obj_id) in self._locked

    def is_hidden(self, kind, obj_id):
        return (kind, obj_id) in self._hidden

    def toggle_lock(self, kind, obj_id):
        k = (kind, obj_id)
        if k in self._locked:
            self._locked.discard(k)
            self.status_text = f"{kind} '{obj_id}' destravado."
        else:
            self._locked.add(k)
            self.status_text = f"{kind} '{obj_id}' travado."
        self._rebuild_fields()
        self._layout_right_panel()

    def toggle_hide(self, kind, obj_id):
        k = (kind, obj_id)
        if k in self._hidden:
            self._hidden.discard(k)
            self.status_text = f"{kind} '{obj_id}' visivel."
        else:
            self._hidden.add(k)
            self.status_text = f"{kind} '{obj_id}' escondido."
        self._rebuild_fields()
        self._layout_right_panel()

    def _hidden_actor_ids(self) -> set:
        """Set de ids de atores escondidos (pro Animator filtrar)."""
        return {oid for (kind, oid) in self._hidden if kind == "actor"}

    def _is_hidden_layer(self, layer_id):
        return ("layer", layer_id) in self._hidden

    # =================================================================
    # LAYOUT
    # =================================================================
    def _layout(self):
        sm = self.screen_manager
        vx, vy = sm.viewport_x, sm.viewport_y
        vw, vh = sm.viewport_width, sm.viewport_height

        self.top_rect = pygame.Rect(vx, vy, vw, self.TOP_H)
        body_y = vy + self.TOP_H
        body_h = vh - self.TOP_H - self.TIMELINE_H - self.STATUS_H

        self.left_rect = pygame.Rect(vx, body_y, self.LEFT_W, body_h)
        self.right_rect = pygame.Rect(vx + vw - self.RIGHT_W, body_y,
                                      self.RIGHT_W, body_h)
        canvas_w = vw - self.LEFT_W - self.RIGHT_W
        self.canvas_rect = pygame.Rect(vx + self.LEFT_W, body_y,
                                       canvas_w, body_h)

        self.timeline_rect = pygame.Rect(
            vx, vy + vh - self.STATUS_H - self.TIMELINE_H,
            vw, self.TIMELINE_H)
        self.status_rect = pygame.Rect(vx, vy + vh - self.STATUS_H,
                                       vw, self.STATUS_H)

        self._layout_top_buttons()
        self._layout_left_list()
        self._layout_right_panel()
        self.timeline.layout(self.timeline_rect, self)

    def _layout_top_buttons(self):
        if not self.top_rect:
            return
        self._top_btns = {}
        r = self.top_rect

        y1 = r.y + 8
        h1 = 26
        x = r.x + 200

        row1 = (
            ("novo",       "Novo",           60),
            ("salvar",     "Salvar",         70),
            ("abrir",      "Abrir",          60),
            ("sep1",       "",               10),
            ("add_actor",  "Adicionar Ator", 140),
            ("add_sprite", "Sprite",         70),
            ("add_emitter","Emitter",        78),
            ("add_filter", "Filter",         68),
        )
        for key, label, w in row1:
            if key.startswith("sep"):
                x += w
                continue
            self._top_btns[key] = pygame.Rect(x, y1, w, h1)
            x += w + 6

        self._top_btns["voltar"] = pygame.Rect(
            r.right - 82, y1, 74, h1)

        y2 = r.y + 44
        h2 = 26
        x = r.x + 200

        row2 = (
            ("play",     "Play",     66),
            ("stop",     "Stop",     60),
            ("loop",     "Loop",     70),
            ("sep2",     "",         10),
            ("autokey",  "Auto-Key", 92),
            ("onion",    "Onion",    76),
            ("sep3",     "",         10),
            ("zoom_out", "-",        30),
            ("zoom_reset","100%",    58),
            ("zoom_in",  "+",        30),
            ("zoom_fit", "Fit",      44),
            ("zoom_1_1", "1:1",      42),
            ("sep4",     "",         10),
            ("rescan",   "Re-Scan",  78),
            ("log",      "Log",      50),
        )
        for key, label, w in row2:
            if key.startswith("sep"):
                x += w
                continue
            self._top_btns[key] = pygame.Rect(x, y2, w, h2)
            x += w + 6

    def _layout_left_list(self):
        if not self.left_rect:
            return
        r = self.left_rect
        pad = 8

        add_h = 26
        add_y = r.bottom - add_h - 8

        self._left_clip_rect = pygame.Rect(
            r.x + pad, r.y + 40,
            r.width - pad * 2 - 8,
            add_y - (r.y + 40) - 8)

        items = self._left_items()
        row_h = self.ROW_H
        visible = max(1, self._left_clip_rect.height // row_h)

        track = pygame.Rect(r.right - 12, self._left_clip_rect.y,
                            8, self._left_clip_rect.height)
        self.left_scrollbar.set(track,
                                total=max(1, len(items)),
                                visible=visible,
                                wheel_area=self._left_clip_rect)
        self.left_scroll = self.left_scrollbar.scroll

        self._left_row_rects = []
        self._left_toggle_rects = []

        start = self.left_scrollbar.scroll
        for i in range(start, min(start + visible, len(items))):
            y = self._left_clip_rect.y + (i - start) * row_h
            rect = pygame.Rect(self._left_clip_rect.x, y,
                               self._left_clip_rect.width, row_h - 2)
            self._left_row_rects.append((i, items[i], rect))

            kind = items[i][0]
            if kind in ("actor", "layer") and len(items[i]) >= 3:
                obj = items[i][2]
                obj_id = getattr(obj, "id", None)
                if not obj_id:
                    continue
                btn = 18
                by = rect.centery - btn // 2
                hide_r = pygame.Rect(rect.right - btn - 2, by, btn, btn)
                lock_r = pygame.Rect(hide_r.left - btn - 2, by, btn, btn)
                self._left_toggle_rects.append(
                    (kind, obj_id, "hide", hide_r))
                self._left_toggle_rects.append(
                    (kind, obj_id, "lock", lock_r))

        self._left_add_rects = [
            ("add_actor", pygame.Rect(r.x + pad, add_y,
                                      r.width - pad * 2, add_h))
        ]

    def _left_items(self):
        out = []
        out.append(("header", "ATORES"))
        for i, a in enumerate(self.current_anim.actors):
            out.append(("actor", i, a))
        out.append(("header", "EFEITOS"))
        for i, l in enumerate(self.current_anim.layers):
            out.append(("layer", i, l))
        return out

    def _layout_right_panel(self):
        if not self.right_rect:
            return
        r = self.right_rect
        header_h = 40
        footer_h = 100

        self._right_clip_rect = pygame.Rect(
            r.x + 8, r.y + header_h,
            r.width - 24, r.height - header_h - footer_h)

        self._compute_right_content()

        track = pygame.Rect(r.right - 12, self._right_clip_rect.y,
                            8, self._right_clip_rect.height)
        self.right_scrollbar.set(track,
                                 total=max(1, self.right_content_height),
                                 visible=self._right_clip_rect.height,
                                 wheel_area=self._right_clip_rect)
        self.right_scroll = self.right_scrollbar.scroll
        self._recalc_right_fields()

        y = r.bottom - footer_h + 12
        actions = self._get_action_buttons()
        col_w = (r.width - 24 - 8) // 2
        self._right_action_rects = []
        for i, (name, label) in enumerate(actions):
            row = i // 2
            col = i % 2
            rect = pygame.Rect(r.x + 12 + col * (col_w + 6),
                               y + row * 30, col_w, 26)
            self._right_action_rects.append((name, rect))

    def _get_action_buttons(self):
        a = self.selected_actor()
        l = self.selected_layer()
        if a is not None:
            base = [
                ("actor_kf_add",  "+ Keyframe"),
                ("actor_kf_del",  "- Keyframe"),
                ("actor_dup",     "Duplicar ator"),
                ("actor_del",     "Remover ator"),
                ("actor_center",  "Centralizar"),
                ("actor_hide",    "Ocultar (alpha 0)"),
            ]
            return base
        if l is not None:
            return [
                ("layer_kf_add",  "+ Keyframe"),
                ("layer_kf_del",  "- Keyframe"),
                ("layer_dup",     "Duplicar layer"),
                ("layer_del",     "Remover layer"),
            ]
        return [
            ("add_actor",   "+ Ator"),
            ("add_sprite",  "+ Sprite"),
            ("add_emitter", "+ Emitter"),
            ("add_filter",  "+ Filter"),
            ("cam_kf_add",  "+ Keyframe da Camera"),
            ("cam_kf_del",  "- Keyframe da Camera"),
        ]

    def _compute_right_content(self):
        row_h = self.ROW_H
        gap = self.ROW_GAP
        h = 20
        for group in self._right_groups():
            keys = [k for k in self.fields if k[0] == group]
            if not keys:
                continue
            h += 26
            h += len(keys) * (row_h + gap)
            h += 10
        self.right_content_height = h

    def _right_groups(self):
        if self.selected_actor() is not None:
            return ("actor", "actor_kf")
        if self.selected_layer() is not None:
            return ("layer", "sheet", "layer_kf", "emitter")
        return ("anim", "background", "camera", "sound")

    def _recalc_right_fields(self):
        if not self.right_rect:
            return
        x0 = self.right_rect.x + 14
        label_w = 115
        field_x = x0 + label_w
        field_w = self.right_rect.width - label_w - 32

        y = self._right_clip_rect.y + 16 - self.right_scrollbar.scroll
        row_h = self.ROW_H
        gap = self.ROW_GAP

        self._right_field_rects = []
        for group in self._right_groups():
            keys = [(k, f) for (k, f) in self.fields.items()
                    if k[0] == group]
            if not keys:
                continue
            y += 26
            for key, f in keys:
                rect = pygame.Rect(field_x, y, field_w, row_h)
                f.rect = rect
                self._right_field_rects.append((key, rect))
                y += row_h + gap
            y += 10

    # =================================================================
    # FIELDS
    # =================================================================
    def _rebuild_fields(self):
        self.fields = {}

        actor = self.selected_actor()
        layer = self.selected_layer()

        # ==== ANIMACAO / BACKGROUND / CAMERA / SOM (nada selecionado) ====
        if actor is None and layer is None:
            for key, kind in (
                    ("name", "text"), ("category", "choice"),
                    ("fps", "int"), ("duration_frames", "int"),
                    ("loop", "bool"),
                    ("anchor", "choice"), ("space", "choice"),
            ):
                self.fields[("anim", key)] = InlineField(key, kind)

            for key, kind in (
                    ("bg_type", "text"), ("bg_color", "text"),
                    ("bg_image", "text"), ("bg_mode", "text"),
                    ("bg_dim", "int"),
            ):
                self.fields[("background", key)] = InlineField(key, kind)

            for key, kind in (
                    ("camera_enabled", "bool"),
                    ("camera_x", "float"),
                    ("camera_y", "float"),
                    ("camera_zoom", "float"),
                    ("camera_easing", "choice"),
                    ("camera_follow", "text"),
            ):
                self.fields[("camera", key)] = InlineField(key, kind)

            if self.current_anim.sound is not None:
                for key, kind in (
                        ("name", "text"), ("source", "choice"),
                        ("start_frame", "int"), ("volume", "float"),
                        ("loop", "bool"),
                ):
                    self.fields[("sound", key)] = InlineField(key, kind)

        # ==== ATOR ====
        if actor is not None:
            for key, kind in (
                    ("actor_id", "text"), ("source_type", "choice"),
                    ("pokemon_id", "int"), ("shiny", "bool"),
                    ("default_anim", "text"), ("default_dir", "text"),
                    ("item_id", "text"), ("sprite_path", "text"),
                    ("mock_label", "text"), ("mock_color", "text"),
                    ("display_scale", "float"),
                    ("size_px", "int"),
                    ("z", "int"), ("flip_x", "bool"),
                    ("vis_start", "int"), ("vis_end", "int"),
            ):
                self.fields[("actor", key)] = InlineField(key, kind)

            kf = actor.keyframe_at(int(self.current_frame))
            if kf is not None:
                for key, kind in (
                        ("f", "int"),
                        ("kf_x", "float"), ("kf_y", "float"),
                        ("kf_rot", "float"), ("kf_scale", "float"),
                        ("kf_alpha", "int"),
                        ("kf_anim", "text"), ("kf_dir", "text"),
                ):
                    self.fields[("actor_kf", key)] = InlineField(key, kind)

        # ==== LAYER ====
        if layer is not None:
            for key, kind in (
                    ("id", "text"), ("z", "int"),
                    ("blend", "choice"), ("pivot", "choice"),
                    ("offset_x", "float"), ("offset_y", "float"),
                    ("vis_start", "int"), ("vis_end", "int"),
                    ("anchor_actor", "text"),
                    ("aim_at", "text"),
            ):
                self.fields[("layer", key)] = InlineField(key, kind)

            if isinstance(layer, SpriteLayerDef):
                self.fields[("layer", "image_path")] = InlineField(
                    "image_path", "text")
                self.fields[("layer", "easing")] = InlineField(
                    "easing", "choice")
                for key in ("frame_width", "frame_height", "frame_index"):
                    self.fields[("sheet", key)] = InlineField(key, "int")
                kf = self._selected_layer_keyframe()
                if kf is not None:
                    for key, kind in (
                            ("f", "int"), ("x", "float"), ("y", "float"),
                            ("rot", "float"), ("scale", "float"),
                            ("alpha", "int"), ("tint", "text"),
                            ("frame_index", "int"),
                    ):
                        self.fields[("layer_kf", key)] = InlineField(key, kind)

            elif isinstance(layer, EmitterLayerDef):
                self.fields[("layer", "image_path")] = InlineField(
                    "image_path", "text")
                for key, kind in (
                        ("spawn_rate", "float"), ("max_particles", "int"),
                        ("gravity", "float"),
                        ("area_x", "float"), ("area_y", "float"),
                        ("area_w", "float"), ("area_h", "float"),
                        ("vel_x_min", "float"), ("vel_x_max", "float"),
                        ("vel_y_min", "float"), ("vel_y_max", "float"),
                        ("life_min", "float"), ("life_max", "float"),
                        ("scale_min", "float"), ("scale_max", "float"),
                        ("alpha_min", "int"), ("alpha_max", "int"),
                        ("rot_min", "float"), ("rot_max", "float"),
                        ("fade_out", "bool"), ("tints", "text"),
                ):
                    self.fields[("emitter", key)] = InlineField(key, kind)

    def _selected_layer_keyframe(self):
        layer = self.selected_layer()
        if not isinstance(layer, SpriteLayerDef):
            return None
        best = None
        for kf in layer.keyframes:
            if kf.f <= self.current_frame:
                if best is None or kf.f > best.f:
                    best = kf
        return best

    # =================================================================
    # GET / COMMIT
    # =================================================================
    def _get_field_value(self, field):
        for (group, key), f in self.fields.items():
            if f is not field:
                continue

            if group == "anim":
                v = getattr(self.current_anim, key, "")
                if key == "loop":
                    return "true" if v else "false"
                return v

            if group == "background":
                bg = self.current_anim.background or {}
                if key == "bg_dim":
                    return str(bg.get("dim", 0))
                return bg.get(key, "")

            if group == "camera":
                cam = self.current_anim.camera
                if cam is None:
                    return ""
                if key == "camera_enabled":
                    return "true" if cam.enabled else "false"
                if key == "camera_easing":
                    return cam.easing
                if key == "camera_follow":
                    return cam.follow
                kf = cam.keyframe_at(int(self.current_frame))
                if kf is None:
                    return ""
                if key == "camera_x":
                    return kf.x
                if key == "camera_y":
                    return kf.y
                if key == "camera_zoom":
                    return kf.zoom
                return ""

            if group == "sound":
                snd = self.current_anim.sound or {}
                v = snd.get(key, "")
                if key == "loop":
                    return "true" if v else "false"
                return v

            if group == "actor":
                a = self.selected_actor()
                if not a:
                    return ""
                if key == "actor_id":
                    return a.id
                if key == "vis_start":
                    return a.visible_frames[0] if a.visible_frames else 0
                if key == "vis_end":
                    return a.visible_frames[1] if len(a.visible_frames) > 1 else -1
                if key == "shiny":
                    return "true" if a.shiny else "false"
                if key == "flip_x":
                    return "true" if a.flip_x else "false"
                if key == "mock_color":
                    return "#{:02X}{:02X}{:02X}".format(*a.mock_color)
                if key == "size_px":
                    return getattr(a, "size_px", 0)
                return getattr(a, key, "")

            if group == "actor_kf":
                a = self.selected_actor()
                if not a:
                    return ""
                kf = a.keyframe_at(int(self.current_frame))
                if kf is None:
                    return ""
                if key == "f":
                    return kf.f
                sub = key[3:] if key.startswith("kf_") else key
                return getattr(kf, sub, "")

            if group == "layer":
                l = self.selected_layer()
                if not l:
                    return ""
                if key == "vis_start":
                    return l.visible_frames[0] if l.visible_frames else 0
                if key == "vis_end":
                    return l.visible_frames[1] if len(l.visible_frames) > 1 else -1
                return getattr(l, key, "")

            if group == "sheet":
                l = self.selected_layer()
                return getattr(l, key, 0) if l else 0

            if group == "layer_kf":
                kf = self._selected_layer_keyframe()
                if kf is None:
                    return ""
                if key == "tint":
                    return _to_hex_color(kf.tint)
                if key == "frame_index":
                    return "" if kf.frame_index < 0 else kf.frame_index
                return getattr(kf, key, "")

            if group == "emitter":
                l = self.selected_layer()
                if not isinstance(l, EmitterLayerDef):
                    return ""
                return self._get_emitter_flat(l, key)
        return ""

    def _get_emitter_flat(self, layer, key):
        p = layer.emitter_params or {}
        area = p.get("spawn_area") or {"x": 0, "y": 0, "w": 40, "h": 40}
        vel = p.get("velocity") or {"x": [0, 0], "y": [0, 0]}
        life = p.get("lifetime") or [0.5, 1.0]
        scale = p.get("scale") or [1.0, 1.0]
        alpha = p.get("alpha") or [255, 255]
        rot = p.get("rotation_speed") or [0, 0]
        return {
            "spawn_rate": p.get("spawn_rate", 10.0),
            "max_particles": p.get("max_particles", 50),
            "gravity": p.get("gravity", 0.0),
            "area_x": area["x"], "area_y": area["y"],
            "area_w": area["w"], "area_h": area["h"],
            "vel_x_min": vel["x"][0], "vel_x_max": vel["x"][1],
            "vel_y_min": vel["y"][0], "vel_y_max": vel["y"][1],
            "life_min": life[0], "life_max": life[1],
            "scale_min": scale[0], "scale_max": scale[1],
            "alpha_min": alpha[0], "alpha_max": alpha[1],
            "rot_min": rot[0], "rot_max": rot[1],
            "fade_out": "true" if p.get("fade_out", True) else "false",
            "tints": ",".join(p.get("tint_options", ["#FFFFFF"])),
        }.get(key, "")

    def _actor_size_auto(self):
        """Calcula o bbox real do sprite do ator selecionado e sugere
        um size_px que mantenha ele parecido com o tamanho atual."""
        a = self.selected_actor()
        if not a or a.source_type != "pokemon":
            return
        self._push_undo()
        rt = self._actor_runtime(a)
        props = rt.eval_at(self.current_frame)
        bbox = rt._get_union_bbox(props["anim"], props["dir"])
        if bbox is None or bbox[2] <= 0 or bbox[3] <= 0:
            self.status_text = "Nao foi possivel medir o sprite."
            return
        # Tamanho atual do bbox em pixels na tela
        current_scale = (rt.TARGET_BASE * a.display_scale
                        / max(bbox[2], bbox[3]))
        target_px = int(round(max(bbox[2], bbox[3]) * current_scale))
        a.size_px = max(4, target_px)
        a.display_scale = 1.0
        self._invalidate_actor(a.id)
        self.mark_dirty()
        self._rebuild_fields()
        self._layout_right_panel()
        self.status_text = f"size_px = {a.size_px}"
        self.logger.ok(f"auto size: {a.id} -> {a.size_px}px")

    def _commit_field(self, field):
        for (group, key), f in self.fields.items():
            if f is not field:
                continue
            # Snapshot ANTES da mutacao
            self._push_undo()
            try:
                if group == "anim":
                    self._apply_anim_field(key, field.buffer)
                elif group == "background":
                    self._apply_background_field(key, field.buffer)
                elif group == "camera":
                    self._apply_camera_field(key, field.buffer)
                elif group == "sound":
                    self._apply_sound_field(key, field.buffer)
                elif group == "actor":
                    self._apply_actor_field(key, field.buffer)
                elif group == "actor_kf":
                    self._apply_actor_kf_field(key, field.buffer)
                elif group == "layer":
                    self._apply_layer_field(key, field.buffer)
                elif group == "sheet":
                    self._apply_sheet_field(key, field.buffer)
                elif group == "layer_kf":
                    self._apply_layer_kf_field(key, field.buffer)
                elif group == "emitter":
                    self._apply_emitter_field(key, field.buffer)
                self.logger.ok(f"{group}.{key} = {field.buffer!r}")
            except Exception as e:
                self.logger.error(f"commit {group}.{key}: {e}")
            self.mark_dirty()
            f.cancel()
            self._rebuild_fields()
            self._layout_right_panel()
            return

    def _apply_anim_field(self, key, value):
        a = self.current_anim
        if key in ("fps", "duration_frames"):
            setattr(a, key, max(1, int(float(value))))
        elif key == "loop":
            a.loop = str(value).strip().lower() in ("1", "true", "yes",
                                                    "on", "sim")
        elif key == "category":
            if value in S.CATEGORIES:
                a.category = value
        elif key == "anchor":
            a.anchor = value
        elif key == "space":
            if value in S.SPACES:
                a.space = value
        else:
            setattr(a, key, value)

    def _apply_background_field(self, key, value):
        bg = dict(self.current_anim.background or {})
        v = str(value).strip()
        if key == "bg_type":
            bg["type"] = v
        elif key == "bg_color":
            bg["color"] = v
        elif key == "bg_image":
            bg["image"] = v
        elif key == "bg_mode":
            bg["image_mode"] = v
        elif key == "bg_dim":
            bg["dim"] = max(0, min(255, int(float(v))))
        self.current_anim.background = bg if bg else None

    def _apply_camera_field(self, key, value):
        v = str(value).strip()
        if self.current_anim.camera is None:
            self.current_anim.camera = CameraDef(enabled=True)
        cam = self.current_anim.camera

        if key == "camera_enabled":
            cam.enabled = v.lower() in ("1", "true", "yes", "on", "sim")
            if cam.enabled and not cam.keyframes:
                cam.keyframes.append(CameraKeyframe(f=0))
            if self._preview_animator is not None:
                self._preview_animator.set_camera_runtime(cam)
        elif key == "camera_easing":
            if v in S.EASINGS:
                cam.easing = v
        elif key == "camera_follow":
            cam.follow = v
        else:
            f = int(self.current_frame)
            kf = cam.ensure_keyframe_at(f)
            if key == "camera_x":
                kf.x = float(v)
            elif key == "camera_y":
                kf.y = float(v)
            elif key == "camera_zoom":
                kf.zoom = max(0.05, float(v))
            if self._preview_animator is not None:
                self._preview_animator.set_camera_runtime(cam)

    def _apply_sound_field(self, key, value):
        if self.current_anim.sound is None:
            self.current_anim.sound = {}
        snd = self.current_anim.sound
        if key == "start_frame":
            snd[key] = int(float(value))
        elif key == "volume":
            snd[key] = float(value)
        elif key == "loop":
            snd[key] = str(value).strip().lower() in ("1", "true", "yes",
                                                      "on", "sim")
        else:
            snd[key] = value

    def _apply_actor_field(self, key, value):
        a = self.selected_actor()
        if a is None:
            return
        v = str(value).strip()

        if key == "actor_id":
            a.id = v or a.id
        elif key == "source_type":
            if v in ("pokemon", "item", "sprite", "mock"):
                a.source_type = v
                self._invalidate_actor(a.id)
        elif key == "pokemon_id":
            a.pokemon_id = int(float(v)) if v else 25
            self._invalidate_actor(a.id)
        elif key == "shiny":
            a.shiny = v.lower() in ("1", "true", "yes", "on", "sim")
            self._invalidate_actor(a.id)
        elif key == "default_anim":
            a.default_anim = v or "idle"
            self._invalidate_actor(a.id)
        elif key == "default_dir":
            a.default_dir = v or "down"
            self._invalidate_actor(a.id)
        elif key == "item_id":
            a.item_id = v or "pokeball"
            self._invalidate_actor(a.id)
        elif key == "sprite_path":
            a.sprite_path = v
            self._invalidate_actor(a.id)
        elif key == "mock_label":
            a.mock_label = v
        elif key == "mock_color":
            a.mock_color = _parse_hex_color(v)
        elif key == "display_scale":
            a.display_scale = max(0.1, float(v))
        elif key == "size_px":
            a.size_px = max(0, int(float(v)))
            self._invalidate_actor(a.id)
        elif key == "z":
            a.z = int(float(v))
        elif key == "flip_x":
            a.flip_x = v.lower() in ("1", "true", "yes", "on", "sim")
        elif key == "vis_start":
            end = a.visible_frames[1] if len(a.visible_frames) > 1 else -1
            a.visible_frames = (int(float(v)), end)
        elif key == "vis_end":
            start = a.visible_frames[0] if a.visible_frames else 0
            a.visible_frames = (start, int(float(v)))
        else:
            setattr(a, key, v)

    def _apply_actor_kf_field(self, key, value):
        a = self.selected_actor()
        if a is None:
            return
        f = int(self.current_frame)
        kf = a.ensure_keyframe_at(f)

        if key == "f":
            kf.f = max(0, int(float(value)))
            a.keyframes.sort(key=lambda k: k.f)
        elif key == "kf_x":
            kf.x = float(value)
        elif key == "kf_y":
            kf.y = float(value)
        elif key == "kf_rot":
            kf.rot = float(value)
        elif key == "kf_scale":
            kf.scale = max(0.01, float(value))
        elif key == "kf_alpha":
            kf.alpha = max(0, min(255, int(float(value))))
        elif key == "kf_anim":
            kf.anim = str(value).strip() or kf.anim
        elif key == "kf_dir":
            kf.dir = str(value).strip() or kf.dir

    def _apply_layer_field(self, key, value):
        l = self.selected_layer()
        if l is None:
            return
        if key == "z":
            l.z = int(float(value))
        elif key in ("offset_x", "offset_y"):
            setattr(l, key, float(value))
        elif key == "vis_start":
            end = l.visible_frames[1] if len(l.visible_frames) > 1 else -1
            l.visible_frames = (int(float(value)), end)
        elif key == "vis_end":
            start = l.visible_frames[0] if l.visible_frames else 0
            l.visible_frames = (start, int(float(value)))
        elif key == "anchor_actor":
            l.anchor_actor = str(value).strip()
        elif key == "aim_at":
            l.aim_at = str(value).strip()
        elif key in ("blend", "pivot", "id", "image_path", "easing"):
            if key == "blend" and value not in S.BLENDS: return
            if key == "pivot" and value not in S.PIVOTS: return
            if key == "easing" and value not in S.EASINGS: return
            setattr(l, key, value)

    def _apply_sheet_field(self, key, value):
        l = self.selected_layer()
        if not isinstance(l, SpriteLayerDef):
            return
        setattr(l, key, max(0, int(float(value))))

    def _apply_layer_kf_field(self, key, value):
        kf = self._selected_layer_keyframe()
        if kf is None:
            return
        if key == "f":
            kf.f = max(0, int(float(value)))
            l = self.selected_layer()
            l.keyframes.sort(key=lambda k: k.f)
        elif key in ("x", "y", "rot", "scale"):
            setattr(kf, key, float(value))
        elif key == "alpha":
            kf.alpha = max(0, min(255, int(float(value))))
        elif key == "tint":
            kf.tint = _parse_hex_color(value)
        elif key == "frame_index":
            v = str(value).strip()
            if v == "" or v == "-1":
                kf.frame_index = -1
            else:
                kf.frame_index = max(0, int(float(v)))

    def _apply_emitter_field(self, key, value):
        l = self.selected_layer()
        if not isinstance(l, EmitterLayerDef):
            return
        p = dict(l.emitter_params or {})

        def _f(v): return float(v)
        def _i(v): return int(float(v))
        def _b(v): return str(v).strip().lower() in ("1", "true",
                                                     "yes", "on", "sim")

        area = dict(p.get("spawn_area") or {"x": 0, "y": 0, "w": 40, "h": 40})
        vel = dict(p.get("velocity") or {"x": [0, 0], "y": [0, 0]})
        vel["x"] = list(vel["x"]); vel["y"] = list(vel["y"])
        life = list(p.get("lifetime") or [0.5, 1.0])
        scale = list(p.get("scale") or [1.0, 1.0])
        alpha = list(p.get("alpha") or [255, 255])
        rot = list(p.get("rotation_speed") or [0, 0])

        if key == "spawn_rate":
            p["spawn_rate"] = _f(value)
        elif key == "max_particles":
            p["max_particles"] = max(1, _i(value))
        elif key == "gravity":
            p["gravity"] = _f(value)
        elif key == "area_x":
            area["x"] = _f(value)
        elif key == "area_y":
            area["y"] = _f(value)
        elif key == "area_w":
            area["w"] = max(1, _f(value))
        elif key == "area_h":
            area["h"] = max(1, _f(value))
        elif key == "vel_x_min":
            vel["x"][0] = _f(value)
        elif key == "vel_x_max":
            vel["x"][1] = _f(value)
        elif key == "vel_y_min":
            vel["y"][0] = _f(value)
        elif key == "vel_y_max":
            vel["y"][1] = _f(value)
        elif key == "life_min":
            life[0] = max(0.01, _f(value))
        elif key == "life_max":
            life[1] = max(0.01, _f(value))
        elif key == "scale_min":
            scale[0] = _f(value)
        elif key == "scale_max":
            scale[1] = _f(value)
        elif key == "alpha_min":
            alpha[0] = max(0, min(255, _i(value)))
        elif key == "alpha_max":
            alpha[1] = max(0, min(255, _i(value)))
        elif key == "rot_min":
            rot[0] = _f(value)
        elif key == "rot_max":
            rot[1] = _f(value)
        elif key == "fade_out":
            p["fade_out"] = _b(value)
        elif key == "tints":
            parts = [x.strip() for x in str(value).split(",") if x.strip()]
            p["tint_options"] = parts or ["#FFFFFF"]

        p["spawn_area"] = area
        p["velocity"] = vel
        p["lifetime"] = life
        p["scale"] = scale
        p["alpha"] = alpha
        p["rotation_speed"] = rot
        l.emitter_params = p

        if self._preview_animator:
            self._preview_animator._emitter_runners.clear()

    # =================================================================
    # PREVIEW ANIMATOR
    # =================================================================
    def _ensure_preview_animator(self):
        key = (id(self.current_anim),
               self._preview_revision,
               round(self.canvas_zoom, 3),
               self.canvas_rect.centerx,
               self.canvas_rect.centery)
        if (self._preview_animator_key == key
                and self._preview_animator is not None):
            return self._preview_animator

        old_actor_rts = {}
        if (self._preview_animator is not None
                and self._preview_animator.defn is self.current_anim):
            old_actor_rts = dict(self._preview_animator._actor_runtimes)

        self._preview_animator = Animator(
            definition=self.current_anim,
            anchor_target=None,
            anchor_attacker=None,
            screen_pos=(self.canvas_rect.centerx, self.canvas_rect.centery),
            loop_override=True,
            zoom=self.canvas_zoom,
        )
        for actor_id, rt in old_actor_rts.items():
            cur = self.current_anim.get_actor(actor_id)
            if cur is not None and rt.defn is cur:
                self._preview_animator._actor_runtimes[actor_id] = rt

        self._preview_animator_key = key
        return self._preview_animator

    def _invalidate_actor(self, actor_id=None):
        if self._preview_animator:
            self._preview_animator.invalidate_actor(actor_id)

    def _actor_runtime(self, actor_def):
        preview = self._ensure_preview_animator()
        rt = preview.get_actor_runtime(actor_def.id)
        if rt is None or rt.defn is not actor_def:
            rt = ActorRuntime(actor_def)
            preview._actor_runtimes[actor_def.id] = rt
        return rt

    # =================================================================
    # ZOOM
    # =================================================================
    def _zoom_apply(self, delta):
        self._zoom_set(self.canvas_zoom + delta)

    def _zoom_set(self, value):
        old = self.canvas_zoom
        self.canvas_zoom = max(0.25, min(3.0, float(value)))
        if abs(self.canvas_zoom - old) < 0.001:
            return
        if self._preview_animator:
            self._preview_animator.set_zoom(self.canvas_zoom)
        self._layout_top_buttons()

    def _zoom_fit(self):
        self.canvas_cam_x = 0.0
        self.canvas_cam_y = 0.0
        self._zoom_set(1.0)

    def _zoom_reset(self):
        self.canvas_cam_x = 0.0
        self.canvas_cam_y = 0.0
        self._zoom_set(1.0)

    # =================================================================
    # EVENTOS
    # =================================================================
    def handle_event(self, event):
        if self.preview_mode:
            if self._handle_preview_event(event):
                return
            return

        if self.open_picker.open:
            if self.open_picker.handle_event(event):
                return

        if self.pokemon_picker.open:
            if self.pokemon_picker.handle_event(event):
                return

        focused = self._focused_field()
        if focused and event.type == pygame.KEYDOWN:
            r = focused.handle_key(event)
            if r == "commit":
                self._commit_field(focused)
            elif r == "cancel":
                focused.cancel()
            return

        if event.type == pygame.KEYDOWN and self._handle_hotkey(event):
            return

        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 2 and self.canvas_rect.collidepoint(event.pos):
                self._canvas_panning = True
                self._pan_start = event.pos
                pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_SIZEALL)
                return
            if event.button == 1:
                if self.left_scrollbar.handle_event(event):
                    self.left_scroll = self.left_scrollbar.scroll
                    self._layout_left_list()
                    return
                if self.right_scrollbar.handle_event(event):
                    self.right_scroll = self.right_scrollbar.scroll
                    self._recalc_right_fields()
                    return
                if self._handle_top_click(event.pos):
                    return
                if self._handle_left_click(event.pos):
                    return
                if self._handle_right_click(event.pos):
                    return
                if self.timeline.handle_event(event):
                    return
                if self._handle_canvas_click(event.pos):
                    return

        if event.type == pygame.MOUSEMOTION:
            if self._canvas_panning:
                dx = event.pos[0] - self._pan_start[0]
                dy = event.pos[1] - self._pan_start[1]
                self.canvas_cam_x -= dx / self.canvas_zoom
                self.canvas_cam_y -= dy / self.canvas_zoom
                self._pan_start = event.pos
                return
            if self._drag_actor:
                self._handle_actor_drag(event.pos)
                return
            if self.left_scrollbar.handle_event(event):
                self.left_scroll = self.left_scrollbar.scroll
                self._layout_left_list()
                return
            if self.right_scrollbar.handle_event(event):
                self.right_scroll = self.right_scrollbar.scroll
                self._recalc_right_fields()
                return
            if self.timeline.handle_event(event):
                return

        if event.type == pygame.MOUSEBUTTONUP:
            if event.button == 2 and self._canvas_panning:
                self._canvas_panning = False
                pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_ARROW)
                return
            if event.button == 1:
                self.left_scrollbar.handle_event(event)
                self.right_scrollbar.handle_event(event)
                self.timeline.handle_event(event)
                self._drag_actor = None

        if event.type == pygame.MOUSEWHEEL:
            mouse = pygame.mouse.get_pos()
            mods = pygame.key.get_mods()
            ctrl = bool(mods & pygame.KMOD_CTRL)

            if ctrl and self.canvas_rect.collidepoint(mouse):
                self._zoom_apply(0.05 * event.y)
                return

            if self.left_scrollbar.handle_wheel(event.y, mouse):
                self.left_scroll = self.left_scrollbar.scroll
                self._layout_left_list()
                return
            if self.right_scrollbar.handle_wheel(event.y, mouse):
                self.right_scroll = self.right_scrollbar.scroll
                self._recalc_right_fields()
                return
            if self.timeline.scrollbar.handle_wheel(event.y, mouse):
                self.timeline._recalc_tracks()
                return

    def _focused_field(self):
        for f in self.fields.values():
            if f.focused:
                return f
        return None

    # =================================================================
    # HOTKEYS
    # =================================================================
    def _handle_hotkey(self, event) -> bool:
        mods = pygame.key.get_mods()
        ctrl = bool(mods & pygame.KMOD_CTRL)
        shift = bool(mods & pygame.KMOD_SHIFT)

        if event.key == pygame.K_ESCAPE:
            self.game.current_scene = self.game.menu_scene
            return True

        if event.key == pygame.K_SPACE:
            self._toggle_play()
            return True

        if event.key == pygame.K_LEFT:
            step = 10 if shift else 1
            self.current_frame = max(0, self.current_frame - step)
            self._on_frame_changed()
            return True

        if event.key == pygame.K_RIGHT:
            step = 10 if shift else 1
            self.current_frame = min(self.current_anim.duration_frames,
                                     self.current_frame + step)
            self._on_frame_changed()
            return True

        if event.key == pygame.K_HOME:
            self.current_frame = 0.0
            self._on_frame_changed()
            return True

        if event.key == pygame.K_END:
            self.current_frame = float(self.current_anim.duration_frames)
            self._on_frame_changed()
            return True

        # UNDO / REDO
        if ctrl and event.key == pygame.K_z:
            if shift:
                self._redo()
            else:
                self._undo()
            return True
        if ctrl and event.key == pygame.K_y:
            self._redo()
            return True

        if ctrl and event.key == pygame.K_s:
            self._save_current(); return True
        if ctrl and event.key == pygame.K_n:
            self._new_anim(); return True
        if ctrl and event.key == pygame.K_l:
            self.logger.visible = not self.logger.visible
            return True

        if event.key == pygame.K_g:
            self.show_grid = not self.show_grid; return True
        if event.key == pygame.K_o:
            self.show_onion = not self.show_onion
            self.logger.info(f"onion = {self.show_onion}")
            return True
        if event.key == pygame.K_k:
            self.auto_key = not self.auto_key
            self.logger.info(f"auto-key = {self.auto_key}")
            return True
        if event.key == pygame.K_p:
            self._enter_preview()
            return True
        if event.key == pygame.K_f:
            self._zoom_fit(); return True

        if event.key == pygame.K_DELETE:
            self._delete_selected(); return True
        if event.key == pygame.K_F5:
            self._reload_assets(); return True

        if event.key in (pygame.K_PLUS, pygame.K_EQUALS, pygame.K_KP_PLUS):
            self._zoom_apply(0.1); return True
        if event.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
            self._zoom_apply(-0.1); return True

        return False

    def _on_frame_changed(self):
        self._rebuild_fields()
        self._layout_right_panel()

    def _toggle_play(self):
        if self.is_playing:
            self.is_playing = False
        else:
            if self.current_frame >= self.current_anim.duration_frames - 0.001:
                self.current_frame = 0.0
                self._bump_preview()
            self.is_playing = True
        self._layout_top_buttons()

    def _bump_preview(self):
        self._preview_revision += 1

    def mark_dirty(self):
        self.dirty = True
        self._bump_preview()

    # =================================================================
    # PREVIEW FULLSCREEN
    # =================================================================
    def _enter_preview(self):
        self.preview_mode = True
        self.preview_playing = True
        self.preview_hud_hidden = False
        self.current_frame = 0.0
        self._drag_actor = None
        self._drag_kf = None
        self.logger.info("entrou em modo preview (P/ESC pra sair)")

    def _exit_preview(self):
        self.preview_mode = False
        self.logger.info("saiu do modo preview")

    def _handle_preview_event(self, event) -> bool:
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_ESCAPE, pygame.K_p):
                self._exit_preview()
                return True
            if event.key == pygame.K_SPACE:
                self.preview_playing = not self.preview_playing
                return True
            if event.key == pygame.K_LEFT:
                self.preview_playing = False
                self.current_frame = max(0.0, self.current_frame - 1)
                return True
            if event.key == pygame.K_RIGHT:
                self.preview_playing = False
                self.current_frame = min(
                    float(self.current_anim.duration_frames),
                    self.current_frame + 1)
                return True
            if event.key in (pygame.K_HOME, pygame.K_r):
                self.current_frame = 0.0
                return True
            if event.key == pygame.K_END:
                self.current_frame = float(self.current_anim.duration_frames)
                return True
            if event.key == pygame.K_h:
                self.preview_hud_hidden = not self.preview_hud_hidden
                return True
            return True
        if event.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP,
                          pygame.MOUSEMOTION, pygame.MOUSEWHEEL):
            return True
        return False

    # =================================================================
    # TOP BAR
    # =================================================================
    def _handle_top_click(self, pos) -> bool:
        for name, rect in self._top_btns.items():
            if not rect.collidepoint(pos):
                continue

            if name == "novo":
                self._new_anim()
            elif name == "salvar":
                self._save_current()
            elif name == "abrir":
                self._open_load()
            elif name == "voltar":
                self.game.current_scene = self.game.menu_scene
            elif name == "play":
                self._toggle_play()
            elif name == "stop":
                self.is_playing = False
                self.current_frame = 0.0
                self._bump_preview()
                self._layout_top_buttons()
            elif name == "loop":
                self._push_undo()
                self.current_anim.loop = not self.current_anim.loop
                self.mark_dirty()
            elif name == "autokey":
                self.auto_key = not self.auto_key
                self.logger.info(f"auto-key = {self.auto_key}")
            elif name == "onion":
                self.show_onion = not self.show_onion
            elif name == "zoom_in":
                self._zoom_apply(0.1)
            elif name == "zoom_out":
                self._zoom_apply(-0.1)
            elif name == "zoom_reset":
                self._zoom_reset()
            elif name == "zoom_fit":
                self._zoom_fit()
            elif name == "zoom_1_1":
                self._zoom_set(1.0)
            elif name == "rescan":
                self._reload_assets()
            elif name == "log":
                self.logger.visible = not self.logger.visible
            elif name == "add_actor":
                self._add_actor()
            elif name == "add_sprite":
                self._add_layer_of_type("sprite")
            elif name == "add_emitter":
                self._add_layer_of_type("emitter")
            elif name == "add_filter":
                self._add_layer_of_type("filter")
            return True
        return False

    # =================================================================
    # LEFT PANEL
    # =================================================================
    def _handle_left_click(self, pos) -> bool:
        if not self.left_rect.collidepoint(pos):
            return False

        # Toggle lock/hide primeiro
        for kind, obj_id, flag, rect in self._left_toggle_rects:
            if rect.collidepoint(pos):
                if flag == "lock":
                    self.toggle_lock(kind, obj_id)
                else:
                    self.toggle_hide(kind, obj_id)
                return True

        for name, rect in self._left_add_rects:
            if rect.collidepoint(pos):
                if name == "add_actor":
                    self._add_actor()
                return True

        for i, item, rect in self._left_row_rects:
            if not rect.collidepoint(pos):
                continue
            kind = item[0]
            if kind == "actor":
                self.select_actor(item[1])
            elif kind == "layer":
                self.select_layer(item[1])
            return True
        return True

    # =================================================================
    # RIGHT PANEL
    # =================================================================
    def _handle_right_click(self, pos) -> bool:
        if not self.right_rect.collidepoint(pos):
            return False

        for key, rect in self._right_field_rects:
            if rect.collidepoint(pos):
                for f in self.fields.values():
                    f.cancel()
                f = self.fields.get(key)
                if f is not None:
                    f.begin(self._get_field_value(f))
                return True

        for name, rect in self._right_action_rects:
            if rect.collidepoint(pos):
                self._handle_action(name)
                return True

        for f in self.fields.values():
            f.cancel()
        return True

    def _handle_action(self, name):
        if name == "add_actor":
            self._add_actor()
        elif name == "add_sprite":
            self._add_layer_of_type("sprite")
        elif name == "add_emitter":
            self._add_layer_of_type("emitter")
        elif name == "add_filter":
            self._add_layer_of_type("filter")
        elif name == "actor_kf_add":
            self._actor_kf_add()
        elif name == "actor_kf_del":
            self._actor_kf_del()
        elif name == "actor_dup":
            self._actor_dup()
        elif name == "actor_del":
            self._actor_del()
        elif name == "actor_center":
            self._actor_center()
        elif name == "actor_hide":
            self._actor_hide()
        elif name == "actor_size_auto":
            self._actor_size_auto()
        elif name == "layer_kf_add":
            self._layer_kf_add()
        elif name == "layer_kf_del":
            self._layer_kf_del()
        elif name == "layer_dup":
            self._layer_dup()
        elif name == "layer_del":
            self._layer_del()
        elif name == "cam_kf_add":
            self._camera_kf_add()
        elif name == "cam_kf_del":
            self._camera_kf_del()

    # =================================================================
    # CANVAS
    # =================================================================
    def _actor_origin(self):
        return (self.canvas_rect.centerx, self.canvas_rect.centery)

    def _get_preview_camera_state(self):
        preview = self._ensure_preview_animator()
        if getattr(preview, "camera_runtime", None) is None:
            return 0.0, 0.0, 1.0
        c = preview.camera_runtime.eval_at(self.current_frame)
        return c["x"], c["y"], c["zoom"]

    def _actor_screen_pos_canvas(self, props):
        cr = self.canvas_rect
        cam_x, cam_y, cam_zoom = self._get_preview_camera_state()
        eff = self.canvas_zoom * cam_zoom
        sx = cr.centerx + (props["x"] - cam_x) * eff
        sy = cr.centery + (props["y"] - cam_y) * eff
        return sx, sy, eff

    def _handle_canvas_click(self, pos) -> bool:
        if not self.canvas_rect.collidepoint(pos):
            return False

        hit = self._hit_test_actor(pos)
        if hit is not None:
            self.select_actor(hit)
            actor = self.current_anim.actors[hit]
            rt = self._actor_runtime(actor)
            props = rt.eval_at(self.current_frame)
            # Snapshot ANTES do drag (o drag vai mutar keyframes)
            self._push_undo()
            self._drag_actor = {
                "idx": hit,
                "start_x": props["x"],
                "start_y": props["y"],
                "mouse_x": pos[0],
                "mouse_y": pos[1],
            }
            return True

        self.selection = None
        self._rebuild_fields()
        self._layout_right_panel()
        return True

    def _handle_actor_drag(self, pos):
        idx = self._drag_actor["idx"]
        if not (0 <= idx < len(self.current_anim.actors)):
            self._drag_actor = None
            return
        actor = self.current_anim.actors[idx]

        _, _, cam_zoom = self._get_preview_camera_state()
        eff = self.canvas_zoom * cam_zoom
        if eff <= 0.0001:
            eff = 0.0001

        dx = (pos[0] - self._drag_actor["mouse_x"]) / eff
        dy = (pos[1] - self._drag_actor["mouse_y"]) / eff
        new_x = self._drag_actor["start_x"] + dx
        new_y = self._drag_actor["start_y"] + dy

        if self.auto_key:
            kf = actor.ensure_keyframe_at(int(self.current_frame))
            if kf.x == 0.0 and kf.y == 0.0 and \
               self._drag_actor["start_x"] != 0.0:
                kf.x = self._drag_actor["start_x"]
                kf.y = self._drag_actor["start_y"]
            kf.x = new_x
            kf.y = new_y
        else:
            kf = actor.keyframe_at(int(self.current_frame))
            if kf is not None:
                kf.x = new_x
                kf.y = new_y

        self.mark_dirty()

    def _hit_test_actor(self, pos):
        actors = sorted(
            enumerate(self.current_anim.actors),
            key=lambda t: -getattr(t[1], "z", 0))
        for idx, actor in actors:
            # Pula travados e escondidos
            if self.is_locked("actor", actor.id):
                continue
            if self.is_hidden("actor", actor.id):
                continue

            vf = actor.visible_frames
            f = self.current_frame
            if vf:
                start = int(vf[0]) if len(vf) > 0 else 0
                end = int(vf[1]) if len(vf) > 1 else -1
                if f < start or (end >= 0 and f > end):
                    continue
            rt = self._actor_runtime(actor)
            props = rt.eval_at(self.current_frame)
            if props["alpha"] <= 0:
                continue
            ax, ay, eff = self._actor_screen_pos_canvas(props)
            half = (48 * actor.display_scale * props["scale"]
                    * eff / 2) + 10
            if abs(pos[0] - ax) < half and abs(pos[1] - ay) < half:
                return idx
        return None

    # =================================================================
    # ACOES
    # =================================================================
    def _reload_assets(self, initial=False):
        self.asset_list = SL.list_shared_sprites()
        self.item_list = SL.list_items()
        self.pokemon_list = SL.list_pokemon()
        if self.left_rect:
            self._layout_left_list()

    def _new_anim(self):
        self.current_anim = self._make_default_anim()
        self.current_path = None
        self.current_frame = 0.0
        self.is_playing = False
        self.selection = None
        self._drag_kf = None
        self.right_scrollbar.scroll = 0
        self.left_scrollbar.scroll = 0
        self._locked.clear()
        self._hidden.clear()
        self._undo_stack.clear()
        self._redo_stack.clear()
        self._rebuild_fields()
        self._layout_right_panel()
        self._layout_left_list()
        self.timeline._recalc_tracks()
        self._bump_preview()
        self.status_text = "Nova animacao."
        self.logger.info("nova animacao")

    def _save_current(self):
        try:
            SL.save_animation(self.current_anim)
            self.status_text = (
                f"Salvo: {self.current_anim.category}/"
                f"{self.current_anim.name}.json")
            self.dirty = False
            self._reload_assets()
            self.logger.ok(
                f"salvo: {self.current_anim.category}/"
                f"{self.current_anim.name}")
        except Exception as e:
            self.status_text = f"Erro: {e}"
            self.logger.error(str(e))

    def _open_load(self):
        anims = SL.list_all_animations()
        if not anims:
            self.status_text = "Nenhuma animacao salva em res/animations/"
            self.logger.warn("nenhuma animacao salva")
            return
        self.open_picker.open_with(
            on_select=self._on_open_selected,
            center=(self.canvas_rect.centerx, self.canvas_rect.centery))

    def _on_open_selected(self, category, name):
        self._load_existing(category, name)

    def _load_existing(self, category, name):
        try:
            self.current_anim = SL.load_animation(category, name)
            self.current_frame = 0.0
            self.is_playing = False
            self.selection = None
            self._drag_kf = None
            if self.current_anim.actors:
                self.selection = ("actor", 0)
            elif self.current_anim.layers:
                self.selection = ("layer", 0)

            self.right_scrollbar.scroll = 0
            self.left_scrollbar.scroll = 0
            self._locked.clear()
            self._hidden.clear()
            self._undo_stack.clear()
            self._redo_stack.clear()

            # Reseta preview animator
            if self._preview_animator is not None:
                self._preview_animator.stop()
            self._preview_animator = None
            self._preview_animator_key = None
            self._preview_revision += 1

            self._rebuild_fields()
            self._layout_right_panel()
            self._layout_left_list()
            self.timeline._recalc_tracks()
            self.status_text = f"Carregada: {category}/{name}"
            self.logger.ok(f"carregada: {category}/{name}")
        except Exception as e:
            self.status_text = f"Erro: {e}"
            self.logger.error(f"carregar {category}/{name}: {e}")

    # ---------------- Atores ----------------
    def _add_actor(self):
        self._push_undo()
        idx = len(self.current_anim.actors)
        a = ActorDef(
            id=f"ator_{idx}",
            source_type="mock",
            mock_label=f"ATOR {idx}",
            mock_color=(200, 140, 100),
            display_scale=2.0,
            z=10,
        )
        a.ensure_keyframe_at(0)
        if self.current_anim.duration_frames > 0:
            a.ensure_keyframe_at(self.current_anim.duration_frames)

        self.current_anim.actors.append(a)
        self.select_actor(idx)
        self.timeline._recalc_tracks()
        self.mark_dirty()
        self.status_text = f"Ator '{a.id}' adicionado."
        self.logger.info(f"+ator {a.id}")

    def _actor_dup(self):
        a = self.selected_actor()
        if not a:
            return
        self._push_undo()
        idx = len(self.current_anim.actors)
        dup = a.copy()
        dup.id = f"{a.id}_copia"
        self.current_anim.actors.append(dup)
        self.select_actor(idx)
        self.timeline._recalc_tracks()
        self.mark_dirty()

    def _actor_del(self):
        if not self.selection or self.selection[0] != "actor":
            return
        idx = self.selection[1]
        if not (0 <= idx < len(self.current_anim.actors)):
            return
        self._push_undo()
        name = self.current_anim.actors[idx].id
        self.current_anim.actors.pop(idx)
        self.selection = None
        self._rebuild_fields()
        self._layout_right_panel()
        self._layout_left_list()
        self.timeline._recalc_tracks()
        self.mark_dirty()
        self.logger.info(f"-ator {name}")

    def _actor_kf_add(self):
        a = self.selected_actor()
        if not a:
            return
        self._push_undo()
        f = int(self.current_frame)
        prev = None
        for kf in a.keyframes:
            if kf.f <= f:
                prev = kf
        if prev is not None:
            kf = ActorKeyframe(
                f=f, x=prev.x, y=prev.y, rot=prev.rot, scale=prev.scale,
                alpha=prev.alpha, anim=prev.anim, dir=prev.dir)
            if a.keyframe_at(f) is None:
                a.keyframes.append(kf)
                a.keyframes.sort(key=lambda k: k.f)
        else:
            a.ensure_keyframe_at(f)
        self._rebuild_fields()
        self._layout_right_panel()
        self.timeline._recalc_tracks()
        self.mark_dirty()

    def _actor_kf_del(self):
        a = self.selected_actor()
        if not a:
            return
        self._push_undo()
        if a.remove_keyframe_at(int(self.current_frame)):
            self._rebuild_fields()
            self._layout_right_panel()
            self.timeline._recalc_tracks()
            self.mark_dirty()

    def _actor_center(self):
        a = self.selected_actor()
        if not a:
            return
        self._push_undo()
        kf = a.ensure_keyframe_at(int(self.current_frame))
        kf.x = 0.0
        kf.y = 0.0
        self.mark_dirty()

    def _actor_hide(self):
        a = self.selected_actor()
        if not a:
            return
        self._push_undo()
        kf = a.ensure_keyframe_at(int(self.current_frame))
        kf.alpha = 0
        self.mark_dirty()

    # ---------------- Layers ----------------
    def _add_layer_of_type(self, ttype):
        self._push_undo()
        idx = len(self.current_anim.layers)
        base = dict(id=f"{ttype}_{idx}", type=ttype, z=idx,
                    visible_frames=(0, -1))

        if ttype == "sprite":
            new = SpriteLayerDef(
                **base, image_path="_shared/sparkle.png",
                keyframes=[
                    Keyframe(f=0, alpha=0, scale=1.0),
                    Keyframe(f=30, alpha=255, scale=1.0),
                    Keyframe(f=60, alpha=0, scale=1.0),
                ],
                easing="linear")
        elif ttype == "emitter":
            new = EmitterLayerDef(
                **base, image_path="_shared/sparkle.png",
                emitter_params={
                    "spawn_area": {"x": -20, "y": -20, "w": 40, "h": 40},
                    "spawn_rate": 12.0,
                    "max_particles": 25,
                    "lifetime": [0.5, 1.0],
                    "velocity": {"x": [-15, 15], "y": [-40, -10]},
                    "gravity": 30.0,
                    "scale": [0.4, 0.9],
                    "alpha": [180, 255],
                    "rotation_speed": [-45, 45],
                    "fade_out": True,
                    "tint_options": ["#FFFFFF"],
                })
        elif ttype == "filter":
            new = FilterLayerDef(
                **base, color=(0, 0, 0), alpha=140,
                fade_in_frames=10, fade_out_frames=20)
        else:
            return

        actor = self.selected_actor()
        if actor:
            new.anchor_actor = actor.id

        self.current_anim.layers.append(new)
        self.select_layer(idx)
        self.timeline._recalc_tracks()
        self.mark_dirty()
        self.status_text = f"Layer '{new.id}' adicionado."

    def _layer_dup(self):
        l = self.selected_layer()
        if not l:
            return
        self._push_undo()
        idx = len(self.current_anim.layers)
        self.current_anim.layers.append(l.copy())
        self.select_layer(idx)
        self.timeline._recalc_tracks()
        self.mark_dirty()

    def _layer_del(self):
        if not self.selection or self.selection[0] != "layer":
            return
        idx = self.selection[1]
        if not (0 <= idx < len(self.current_anim.layers)):
            return
        self._push_undo()
        name = self.current_anim.layers[idx].id
        self.current_anim.layers.pop(idx)
        self.selection = None
        self._rebuild_fields()
        self._layout_right_panel()
        self._layout_left_list()
        self.timeline._recalc_tracks()
        self.mark_dirty()
        self.logger.info(f"-layer {name}")

    def _layer_kf_add(self):
        l = self.selected_layer()
        if not isinstance(l, SpriteLayerDef):
            return
        self._push_undo()
        f = int(self.current_frame)
        prev = None
        for kf in l.keyframes:
            if kf.f <= f:
                prev = kf
        if prev is not None:
            kf = prev.copy()
            kf.f = f
            l.keyframes.append(kf)
            l.keyframes.sort(key=lambda k: k.f)
        else:
            l.keyframes.append(Keyframe(f=f, alpha=255, scale=1.0))
            l.keyframes.sort(key=lambda k: k.f)
        self._rebuild_fields()
        self._layout_right_panel()
        self.timeline._recalc_tracks()
        self.mark_dirty()

    def _layer_kf_del(self):
        l = self.selected_layer()
        if not isinstance(l, SpriteLayerDef):
            return
        kf = self._selected_layer_keyframe()
        if kf is None:
            return
        self._push_undo()
        try:
            l.keyframes.remove(kf)
        except ValueError:
            return
        self._rebuild_fields()
        self._layout_right_panel()
        self.timeline._recalc_tracks()
        self.mark_dirty()

    # ---------------- Camera ----------------
    def _camera_kf_add(self):
        self._push_undo()
        cam = self.current_anim.camera
        if cam is None:
            self.current_anim.camera = CameraDef(enabled=True)
            cam = self.current_anim.camera
        f = int(self.current_frame)
        prev = None
        for kf in cam.sorted_keyframes():
            if kf.f <= f:
                prev = kf
        if prev is not None:
            cam.ensure_keyframe_at(f, defaults={
                "x": prev.x, "y": prev.y, "zoom": prev.zoom,
            })
        else:
            cam.ensure_keyframe_at(f)
        if self._preview_animator is not None:
            self._preview_animator.set_camera_runtime(cam)
        self.mark_dirty()
        self._rebuild_fields()
        self._layout_right_panel()

    def _camera_kf_del(self):
        cam = self.current_anim.camera
        if cam is None:
            return
        self._push_undo()
        if cam.remove_keyframe_at(int(self.current_frame)):
            if self._preview_animator is not None:
                self._preview_animator.set_camera_runtime(cam)
            self.mark_dirty()
            self._rebuild_fields()
            self._layout_right_panel()

    def _delete_selected(self):
        if self.selection:
            if self.selection[0] == "actor":
                self._actor_kf_del()
            else:
                self._layer_kf_del()

    # =================================================================
    # SELECAO
    # =================================================================
    def select_actor(self, idx):
        self.selection = ("actor", idx)
        self._rebuild_fields()
        self._layout_right_panel()

    def select_layer(self, idx):
        self.selection = ("layer", idx)
        self._rebuild_fields()
        self._layout_right_panel()

    # =================================================================
    # UPDATE / RENDER
    # =================================================================
    def on_resize(self):
        self._layout()

    def fixed_update(self, dt):
        cur = (self.screen_manager.window_width,
               self.screen_manager.window_height)
        if self._last_size != cur:
            self._last_size = cur
            self._layout()

        if self.preview_mode:
            fps = max(1, self.current_anim.fps)
            total = max(1, self.current_anim.duration_frames)
            if self.preview_playing:
                self.current_frame += dt * fps
                if self.current_frame >= total:
                    self.current_frame = self.current_frame % total
            preview = self._ensure_preview_animator()
            preview.current_frame = self.current_frame
            preview.update_emitters_only(dt)
            return

        if self.is_playing:
            fps = max(1, self.current_anim.fps)
            self.current_frame += dt * fps
            total = max(1, self.current_anim.duration_frames)
            if self.current_frame >= total:
                if self.current_anim.loop:
                    self.current_frame %= total
                else:
                    self.current_frame = total
                    self.is_playing = False
                    self._layout_top_buttons()

        preview = self._ensure_preview_animator()
        preview.current_frame = self.current_frame
        preview.update_emitters_only(dt)

    def render(self, screen):
        if self.preview_mode:
            self._render_preview_fullscreen(screen)
            return

        self._render_top(screen)
        self._render_left(screen)
        self._render_canvas(screen)
        self._render_right(screen)
        self.timeline.render(screen)
        self._render_status(screen)
        self._render_log_panel(screen)
        self.pokemon_picker.render(screen)
        self.open_picker.render(screen)