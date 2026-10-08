"""Todos os _render_* do editor."""
import pygame

from src.ui.theme import Palette, FontBook
from src.anim.layer import SpriteLayerDef, EmitterLayerDef, FilterLayerDef


class _PreviewScreenManager:
    def __init__(self, rect):
        self.viewport_x = rect.x
        self.viewport_y = rect.y
        self.viewport_width = rect.width
        self.viewport_height = rect.height
        self.render_scale = 1.0
        self.render_width = rect.width
        self.render_height = rect.height


class _FullscreenScreenManager:
    def __init__(self, rect):
        self.viewport_x = rect.x
        self.viewport_y = rect.y
        self.viewport_width = rect.width
        self.viewport_height = rect.height
        self.render_scale = 1.0
        self.render_width = rect.width
        self.render_height = rect.height


class AnimEditorRenderMixin:

    # =================================================================
    def _font(self, size, bold=False):
        return FontBook.get(size, bold=bold)

    def _paint_button(self, screen, rect, label, style="primary", active=False):
        hover = rect.collidepoint(pygame.mouse.get_pos())
        if active:
            bg = (76, 150, 96) if not hover else (100, 180, 118)
            border = Palette.GOLD
        elif style == "danger":
            bg = (130, 55, 55) if not hover else (170, 75, 75)
            border = Palette.GOLD if hover else (170, 90, 90)
        elif style == "success":
            bg = (60, 135, 75) if not hover else (88, 170, 100)
            border = Palette.GOLD if hover else (105, 165, 115)
        else:
            bg = (56, 72, 106) if not hover else (86, 116, 166)
            border = Palette.GOLD if hover else (105, 125, 165)
        pygame.draw.rect(screen, bg, rect, border_radius=5)
        pygame.draw.rect(screen, border, rect, 1, border_radius=5)
        txt = self._font(self.FONT_BASE, bold=True).render(
            label, True, (240, 240, 250))
        screen.blit(txt, txt.get_rect(center=rect.center))

    def _paint_chip(self, screen, rect, label, color=(120, 140, 180)):
        pygame.draw.rect(screen, color, rect, border_radius=3)
        t = self._font(10, bold=True).render(label, True, (20, 24, 36))
        screen.blit(t, t.get_rect(center=rect.center))

    def _paint_toggle(self, screen, rect, letter, active,
                      active_color=(200, 60, 60)):
        """Botao pequeno de toggle (L / H)."""
        hover = rect.collidepoint(pygame.mouse.get_pos())
        if active:
            bg = active_color if not hover else (
                min(255, active_color[0] + 30),
                min(255, active_color[1] + 30),
                min(255, active_color[2] + 30))
            border = (255, 255, 255)
            txt_col = (255, 255, 255)
        else:
            bg = (44, 52, 74) if not hover else (60, 72, 100)
            border = (100, 120, 160) if hover else (70, 88, 128)
            txt_col = (170, 185, 210)
        pygame.draw.rect(screen, bg, rect, border_radius=3)
        pygame.draw.rect(screen, border, rect, 1, border_radius=3)
        t = self._font(11, bold=True).render(letter, True, txt_col)
        screen.blit(t, t.get_rect(center=rect.center))

    # =================================================================
    # TOP BAR
    # =================================================================
    def _render_top(self, screen):
        pygame.draw.rect(screen, (22, 28, 44), self.top_rect)
        pygame.draw.rect(screen, (70, 88, 128), self.top_rect, 2)

        title = self._font(self.FONT_TITLE, bold=True).render(
            "ANIM EDITOR", True, Palette.GOLD)
        screen.blit(title, (self.top_rect.x + 14, self.top_rect.y + 8))

        name_col = Palette.GOLD if self.dirty else (190, 200, 220)
        info = f"{self.current_anim.category}/{self.current_anim.name}"
        if self.dirty:
            info += "  *"
        screen.blit(self._font(self.FONT_BASE, bold=True).render(
            info, True, name_col),
            (self.top_rect.x + 14, self.top_rect.y + 32))

        stats = (f"{len(self.current_anim.actors)} atores  "
                 f"{len(self.current_anim.layers)} efeitos  "
                 f"{int(self.current_frame)}/{self.current_anim.duration_frames}f  "
                 f"U:{len(self._undo_stack)} R:{len(self._redo_stack)}")
        screen.blit(self._font(self.FONT_SM).render(
            stats, True, (140, 155, 185)),
            (self.top_rect.x + 14, self.top_rect.y + 52))

        labels = {
            "novo": "Novo", "salvar": "Salvar", "abrir": "Abrir",
            "add_actor": "Adicionar Ator",
            "add_sprite": "Sprite", "add_emitter": "Emitter",
            "add_filter": "Filter",
            "add_message": "Mensagem",
            "voltar": "Voltar",
            "play": "Pausar" if self.is_playing else "Play",
            "stop": "Stop",
            "loop": "Loop ON" if self.current_anim.loop else "Loop",
            "autokey": f"Auto-Key {'ON' if self.auto_key else 'OFF'}",
            "onion": f"Onion {'ON' if self.show_onion else 'OFF'}",
            "zoom_out": "-",
            "zoom_reset": f"{int(self.canvas_zoom * 100)}%",
            "zoom_in": "+",
            "zoom_fit": "Fit",
            "zoom_1_1": "1:1",
            "rescan": "Re-Scan",
            "log": "Log",
            "add_parallax": "Parallax",
            "exp_mp4": "Export MP4",
            "exp_yt": "YT",
            "exp_tt": "TikTok",
            "exp_sq": "1:1",
        }
        for key, rect in self._top_btns.items():
            label = labels.get(key, key)
            active = (
                (key == "play" and self.is_playing) or
                (key == "autokey" and self.auto_key) or
                (key == "onion" and self.show_onion) or
                (key == "log" and self.logger.visible) or
                (key == "loop" and self.current_anim.loop)
            )
            style = "danger" if key == "voltar" else "primary"
            if key == "play":
                style = "success" if self.is_playing else "primary"
            self._paint_button(screen, rect, label, style=style, active=active)

    # =================================================================
    # LEFT PANEL
    # =================================================================
    def _render_left(self, screen):
        pygame.draw.rect(screen, (20, 26, 40), self.left_rect)
        pygame.draw.rect(screen, (70, 88, 128), self.left_rect, 2)

        title = self._font(self.FONT_HEADER, bold=True).render(
            "CENA", True, Palette.GOLD)
        screen.blit(title, (self.left_rect.x + 14, self.left_rect.y + 10))

        sub = self._font(self.FONT_SM).render(
            "L=travar  H=esconder", True, (140, 155, 185))
        screen.blit(sub, (self.left_rect.x + 14, self.left_rect.y + 26))

        old = screen.get_clip()
        screen.set_clip(self._left_clip_rect)

        if not self._left_row_rects:
            t = self._font(self.FONT_BASE).render(
                "Nada aqui ainda.", True, (150, 160, 190))
            screen.blit(t, (self._left_clip_rect.x + 12,
                            self._left_clip_rect.y + 12))

        for i, item, rect in self._left_row_rects:
            self._render_left_row(screen, item, rect)

        screen.set_clip(old)

        for name, rect in self._left_add_rects:
            label = "Adicionar Ator" if name == "add_actor" else name
            self._paint_button(screen, rect, label, style="success")

        self.left_scrollbar.render(screen)

    def _render_left_row(self, screen, item, rect):
        hover = rect.collidepoint(pygame.mouse.get_pos())
        kind = item[0]

        if kind == "header":
            pygame.draw.rect(screen, (30, 38, 58), rect, border_radius=3)
            t = self._font(self.FONT_SM, bold=True).render(
                item[1], True, (150, 170, 210))
            screen.blit(t, (rect.x + 8, rect.centery - t.get_height() // 2))
            return

        idx = item[1]
        obj = item[2]
        obj_id = getattr(obj, "id", "")
        selected = (self.selection == (kind, idx))
        is_locked = self.is_locked(kind, obj_id) if obj_id else False
        is_hidden = self.is_hidden(kind, obj_id) if obj_id else False

        if selected:
            pygame.draw.rect(screen, (72, 108, 148), rect, border_radius=4)
            pygame.draw.rect(screen, Palette.GOLD, rect, 2, border_radius=4)
        elif hover:
            pygame.draw.rect(screen, (48, 62, 92), rect, border_radius=4)

        chip_w = 26
        chip = pygame.Rect(rect.x + 4, rect.centery - chip_w // 2 + 1,
                           chip_w, chip_w - 4)
        if kind == "actor":
            self._paint_chip(screen, chip, "AT", (120, 200, 160))
        else:
            ltype = getattr(obj, "type", "?")
            # ===== MESSAGE ===== (adicionado "message")
            color = {"sprite": (120, 170, 240),
                     "emitter": (250, 180, 90),
                     "filter": (200, 130, 240),
                     "message": (150, 230, 170),
                     "parallax": (130, 200, 250)}.get(ltype, (150, 150, 150))
            code = {"sprite": "SP", "emitter": "EM",
                    "filter": "FI", "message": "MS",
                    "parallax": "PX"}.get(ltype, "?")
            self._paint_chip(screen, chip, code, color)


        # Toggles (L e H) na direita da linha
        btn = 18
        by = rect.centery - btn // 2
        hide_r = pygame.Rect(rect.right - btn - 2, by, btn, btn)
        lock_r = pygame.Rect(hide_r.left - btn - 2, by, btn, btn)

        if obj_id:
            self._paint_toggle(screen, lock_r, "L", is_locked,
                               active_color=(200, 70, 70))
            self._paint_toggle(screen, hide_r, "H", is_hidden,
                               active_color=(150, 70, 200))
            name_right = lock_r.left - 6
        else:
            name_right = rect.right - 6

        name = obj_id or "?"
        col = Palette.GOLD if selected else (220, 228, 240)
        if is_hidden:
            col = (150, 150, 170)
        elif is_locked:
            col = (200, 180, 150)

        t = self._font(self.FONT_BASE).render(name, True, col)
        max_w = name_right - (chip.right + 8)
        if t.get_width() > max_w:
            while name and self._font(self.FONT_BASE).size(name)[0] > max_w:
                name = name[:-1]
            if name != obj_id:
                name = name[:-1] + "…"
            t = self._font(self.FONT_BASE).render(name, True, col)

        screen.blit(t, (chip.right + 8, rect.centery - t.get_height() // 2))

        # Overlay visual se invisivel pelo frame
        vf = getattr(obj, "visible_frames", (0, -1))
        visible = True
        f = self.current_frame
        if vf:
            s = int(vf[0]) if len(vf) > 0 else 0
            e = int(vf[1]) if len(vf) > 1 else -1
            if f < s or (e >= 0 and f > e):
                visible = False
        if not visible:
            ov = pygame.Surface(rect.size, pygame.SRCALPHA)
            ov.fill((14, 18, 26, 120))
            screen.blit(ov, rect.topleft)

    # =================================================================
    # CANVAS
    # =================================================================
    def _render_canvas(self, screen):
        cr = self.canvas_rect
        pygame.draw.rect(screen, (10, 14, 24), cr)

        self._render_canvas_bg(screen, cr)

        if self.show_grid:
            step = max(20, int(50 * self.canvas_zoom))
            gs = pygame.Surface(cr.size, pygame.SRCALPHA)
            ox = int((-self.canvas_cam_x * self.canvas_zoom) % step)
            oy = int((-self.canvas_cam_y * self.canvas_zoom) % step)
            for x in range(ox, cr.width, step):
                pygame.draw.line(gs, (48, 60, 88, 90), (x, 0), (x, cr.height))
            for y in range(oy, cr.height, step):
                pygame.draw.line(gs, (48, 60, 88, 90), (0, y), (cr.width, y))
            cx = cr.centerx + int(-self.canvas_cam_x * self.canvas_zoom)
            cy = cr.centery + int(-self.canvas_cam_y * self.canvas_zoom)
            if 0 <= cx < cr.width:
                pygame.draw.line(gs, (248, 176, 48, 130),
                                 (cx, 0), (cx, cr.height))
            if 0 <= cy < cr.height:
                pygame.draw.line(gs, (248, 176, 48, 130),
                                 (0, cy), (cr.width, cy))
            screen.blit(gs, cr.topleft)

        old = screen.get_clip()
        screen.set_clip(cr)

        if self.show_onion:
            self._render_onion(screen)

        self._render_current_frame(screen)

        self._render_actor_selection(screen)

        screen.set_clip(old)

        pygame.draw.rect(screen, (80, 100, 140), cr, 2)

        hint = (f"anchor: {self.current_anim.anchor}   "
                f"space: {self.current_anim.space}   "
                f"Ctrl+scroll: zoom   Middle: pan   "
                f"O: onion   K: auto-key   P: preview   "
                f"Ctrl+Z/Y: undo/redo")
        t = self._font(self.FONT_SM).render(hint, True, (150, 170, 210))
        screen.blit(t, (cr.x + 10, cr.bottom - 18))

    def _render_current_frame(self, screen):
        original_space = self.current_anim.space
        self.current_anim.space = "screen"
        try:
            preview = self._ensure_preview_animator()
            preview.current_frame = self.current_frame
            hidden = self._hidden_actor_ids()
            preview.render(
                screen, camera=None,
                screen_manager=_PreviewScreenManager(self.canvas_rect),
                hidden_actors=hidden)
        except Exception as e:
            self.logger.error(f"preview: {e}")
        finally:
            self.current_anim.space = original_space

    def _render_onion(self, screen):
        if not self.current_anim.actors:
            return
        cr = self.canvas_rect
        fps = max(1, self.current_anim.fps)

        cam_x, cam_y, cam_zoom = self._get_preview_camera_state()
        eff = self.canvas_zoom * cam_zoom
        ox = cr.centerx - cam_x * eff
        oy = cr.centery - cam_y * eff

        for i, offset in enumerate(self.onion_offsets):
            f = self.current_frame + offset
            if f < 0 or f > self.current_anim.duration_frames:
                continue
            ts = f / fps
            alpha_mult = 0.32 if i == 0 else 0.15
            for actor_def in sorted(self.current_anim.actors,
                                    key=lambda a: getattr(a, "z", 0)):
                if self.is_hidden("actor", actor_def.id):
                    continue
                vf = getattr(actor_def, "visible_frames", None)
                if vf:
                    s = int(vf[0]) if len(vf) > 0 else 0
                    e = int(vf[1]) if len(vf) > 1 else -1
                    if f < s or (e >= 0 and f > e):
                        continue
                rt = self._actor_runtime(actor_def)
                try:
                    rt.render(screen, ox, oy, f, ts, eff,
                              alpha_mult=alpha_mult)
                except Exception:
                    pass

    def _render_actor_selection(self, screen):
        a = self.selected_actor()
        if not a:
            return
        if self.is_hidden("actor", a.id):
            return

        rt = self._actor_runtime(a)
        props = rt.eval_at(self.current_frame)

        ax, ay, eff = self._actor_screen_pos_canvas(props)
        half = (48 * a.display_scale * props["scale"] * eff / 2) + 10

        rect = pygame.Rect(int(ax - half), int(ay - half),
                           int(half * 2), int(half * 2))

        is_locked = self.is_locked("actor", a.id)
        box_color = (255, 130, 130) if is_locked else Palette.GOLD

        pygame.draw.rect(screen, box_color, rect, 2)
        for corner in (rect.topleft, rect.topright,
                       rect.bottomleft, rect.bottomright):
            pygame.draw.circle(screen, box_color, corner, 4)
        pygame.draw.circle(screen, box_color, (int(ax), int(ay)), 3)

        if is_locked:
            t = self._font(12, bold=True).render("L", True, box_color)
            screen.blit(t, (rect.x + 4, rect.y + 2))

    # -----------------------------------------------------------------
    def _render_canvas_bg(self, screen, rect):
        bg = self.current_anim.background or {}
        t = bg.get("type", "none")

        if t == "color":
            col = self._parse_color_safe(bg.get("color", "#101828"))
            pygame.draw.rect(screen, col, rect)
        elif t == "image":
            surface = self._load_bg_surface(bg.get("image", ""))
            if surface is None:
                pygame.draw.rect(screen, (18, 22, 34), rect)
            else:
                try:
                    from src.ui.image_draw import draw_image_in_rect
                    draw_image_in_rect(screen, surface, rect,
                                       mode=bg.get("image_mode", "cover"),
                                       smooth=False)
                except Exception:
                    pygame.draw.rect(screen, (18, 22, 34), rect)
        else:
            pygame.draw.rect(screen, (18, 22, 34), rect)

        try:
            dim = int(bg.get("dim", 0))
        except (TypeError, ValueError):
            dim = 0
        if dim > 0:
            ov = pygame.Surface(rect.size, pygame.SRCALPHA)
            ov.fill((0, 0, 0, dim))
            screen.blit(ov, rect.topleft)

    def _parse_color_safe(self, s):
        try:
            from src.ui.theme import parse_color
            c = parse_color(s, None)
            if c is None:
                return (18, 22, 34)
            return (c[0], c[1], c[2]) if len(c) >= 3 else (18, 22, 34)
        except Exception:
            return (18, 22, 34)

    def _load_bg_surface(self, img_path):
        if not img_path:
            return None
        cache = getattr(self, "_bg_cache", None)
        if cache is None:
            cache = {}
            self._bg_cache = cache
        if img_path in cache:
            return cache[img_path]
        try:
            from src.config.paths import RES_PATH
            p = RES_PATH / "animations" / img_path
            if not p.exists():
                cache[img_path] = None
                return None
            img = pygame.image.load(str(p))
            try:
                img = img.convert_alpha()
            except pygame.error:
                pass
            cache[img_path] = img
            return img
        except Exception:
            cache[img_path] = None
            return None

    # =================================================================
    # RIGHT PANEL
    # =================================================================
    def _render_right(self, screen):
        pygame.draw.rect(screen, (20, 26, 40), self.right_rect)
        pygame.draw.rect(screen, (70, 88, 128), self.right_rect, 2)

        a = self.selected_actor()
        l = self.selected_layer()
        if a is not None:
            header = f"ATOR: {a.id}"
            tags = []
            if self.is_locked("actor", a.id):
                tags.append("TRAVADO")
            if self.is_hidden("actor", a.id):
                tags.append("ESCONDIDO")
            sub = f"fonte: {a.source_type}"
            if tags:
                sub += "  [" + " | ".join(tags) + "]"
        elif l is not None:
            header = f"LAYER: {l.id}"
            tags = []
            if self.is_locked("layer", l.id):
                tags.append("TRAVADO")
            if self.is_hidden("layer", l.id):
                tags.append("ESCONDIDO")
            sub = f"tipo: {getattr(l, 'type', '?')}"
            if tags:
                sub += "  [" + " | ".join(tags) + "]"
        else:
            header = "ANIMACAO"
            sub = "nenhum item selecionado"

        t = self._font(self.FONT_HEADER, bold=True).render(
            header, True, Palette.GOLD)
        screen.blit(t, (self.right_rect.x + 14, self.right_rect.y + 10))

        st = self._font(self.FONT_SM).render(sub, True, (150, 170, 205))
        screen.blit(st, (self.right_rect.x + 14, self.right_rect.y + 28))

        pygame.draw.line(screen, (60, 76, 110),
                         (self.right_rect.x + 10, self.right_rect.y + 46),
                         (self.right_rect.right - 10, self.right_rect.y + 46),
                         1)

        old = screen.get_clip()
        screen.set_clip(self._right_clip_rect)

        groups_drawn = set()
        titles = {
            "anim": "ANIMACAO",
            "background": "BACKGROUND",
            "camera": "CAMERA",
            "sound": "SOM",
            "actor": "ATRIBUTOS DO ATOR",
            "actor_kf": "KEYFRAME DO ATOR",
            "layer": "ATRIBUTOS DO LAYER",
            "sheet": "SPRITESHEET",
            "layer_kf": "KEYFRAME DO LAYER",
            "emitter": "EMITTER",
            "message": "MENSAGEM",
            "parallax": "PARALLAX",
        }

        for key, rect in self._right_field_rects:
            group, fname = key
            if group not in groups_drawn:
                groups_drawn.add(group)
                label = titles.get(group, "")
                if label:
                    y = rect.y - 20
                    lt = self._font(self.FONT_BASE, bold=True).render(
                        label, True, (255, 205, 100))
                    screen.blit(lt, (self.right_rect.x + 14, y))
                    pygame.draw.line(
                        screen, (90, 108, 150),
                        (self.right_rect.x + 10, y + 16),
                        (self.right_rect.right - 10, y + 16), 1)

            f = self.fields.get(key)
            if f is None:
                continue

            display = self._FIELD_LABELS.get(fname, fname)
            lbl = self._font(self.FONT_BASE).render(
                display, True, (200, 210, 230))
            screen.blit(lbl, (self.right_rect.x + 14,
                              rect.centery - lbl.get_height() // 2))

            value = f.buffer if f.focused else str(self._get_field_value(f))

            if f.focused:
                bg = (44, 58, 88)
                border = Palette.GOLD
                bw = 2
            else:
                bg = (24, 28, 42)
                border = (72, 88, 128)
                bw = 1

            pygame.draw.rect(screen, bg, rect, border_radius=4)
            pygame.draw.rect(screen, border, rect, bw, border_radius=4)

            # Trunca valores longos (ex: texto de mensagem) pra nao estourar
            vt = self._font(self.FONT_VALUE).render(
                value, True, (220, 230, 250))
            if vt.get_width() > rect.width - 12:
                # Corte por caractere respeitando a largura
                shown = value
                while shown and self._font(self.FONT_VALUE).size(shown)[0] \
                        > rect.width - 16:
                    shown = shown[:-1]
                if shown != value:
                    shown = shown[:-1] + "…"
                vt = self._font(self.FONT_VALUE).render(
                    shown, True, (220, 230, 250))
            screen.blit(vt, (rect.x + 8,
                             rect.centery - vt.get_height() // 2))

            if f.focused and (pygame.time.get_ticks() // 500) % 2 == 0:
                cx = rect.x + 8 + vt.get_width() + 1
                pygame.draw.line(screen, (220, 230, 250),
                                 (cx, rect.y + 4),
                                 (cx, rect.bottom - 4), 1)

        screen.set_clip(old)

        labels = {
            "actor_kf_add": "+ Keyframe",
            "actor_kf_del": "- Keyframe",
            "actor_dup": "Duplicar ator",
            "actor_del": "Remover ator",
            "actor_center": "Centralizar",
            "actor_hide": "Ocultar (alpha 0)",
            "layer_kf_add": "+ Keyframe",
            "layer_kf_del": "- Keyframe",
            "layer_dup": "Duplicar layer",
            "layer_del": "Remover layer",
            "add_actor": "+ Ator",
            "add_sprite": "+ Sprite",
            "add_emitter": "+ Emitter",
            "add_filter": "+ Filter",
            "add_message": "+ Mensagem",   # ===== MESSAGE =====
            "cam_kf_add": "+ Keyframe da Camera",
            "cam_kf_del": "- Keyframe da Camera",
        }
        for name, rect in self._right_action_rects:
            style = "danger" if name.endswith("_del") else "primary"
            self._paint_button(screen, rect, labels.get(name, name),
                               style=style)

        self.right_scrollbar.render(screen)

    # =================================================================
    # STATUS
    # =================================================================
    def _render_status(self, screen):
        pygame.draw.rect(screen, (14, 18, 30), self.status_rect)
        pygame.draw.line(screen, (70, 88, 128),
                         self.status_rect.topleft,
                         (self.status_rect.right, self.status_rect.y), 1)

        t = self._font(self.FONT_BASE).render(
            self.status_text, True, (200, 210, 230))
        screen.blit(t, (self.status_rect.x + 10,
                        self.status_rect.centery - t.get_height() // 2))

        hints = ("[Space] play   [setas] frame   "
                 "[Ctrl+Z/Y] undo/redo   [Ctrl+S] salvar   "
                 "[G] grid   [O] onion   [K] auto-key   [P] preview   "
                 "[Del] keyframe   [Middle] pan   [Esc] sair")
        ht = self._font(self.FONT_SM).render(hints, True, (120, 130, 150))
        screen.blit(ht, (self.status_rect.right - ht.get_width() - 10,
                         self.status_rect.centery - ht.get_height() // 2))

    # =================================================================
    # LOG
    # =================================================================
    def _render_log_panel(self, screen):
        if not self.logger.visible:
            return
        w, h = 700, 280
        x = self.canvas_rect.x + (self.canvas_rect.width - w) // 2
        y = self.canvas_rect.y + 40
        r = pygame.Rect(x, y, w, h)

        bg = pygame.Surface((w, h), pygame.SRCALPHA)
        bg.fill((14, 18, 30, 240))
        screen.blit(bg, r.topleft)
        pygame.draw.rect(screen, Palette.GOLD, r, 2, border_radius=6)

        title = self._font(self.FONT_BASE, bold=True).render(
            "LOG  (Ctrl+L fecha)", True, Palette.GOLD)
        screen.blit(title, (r.x + 12, r.y + 8))
        pygame.draw.line(screen, (70, 88, 128),
                         (r.x + 10, r.y + 30),
                         (r.right - 10, r.y + 30), 1)

        clip = pygame.Rect(r.x + 8, r.y + 36, r.width - 16, r.height - 44)
        old = screen.get_clip()
        screen.set_clip(clip)

        line_h = 17
        visible = clip.height // line_h
        total = len(self.logger.lines)
        scroll = max(0, total - visible)
        for i in range(visible):
            idx = scroll + i
            if idx >= total:
                break
            level, text, ts = self.logger.lines[idx]
            col = self.logger.LEVEL_COLORS.get(level, (220, 220, 220))
            t = self._font(self.FONT_SM).render(
                f"{ts} [{level:<5}] {text}", True, col)
            screen.blit(t, (clip.x + 2, clip.y + i * line_h))

        screen.set_clip(old)

    # =================================================================
    # PREVIEW FULLSCREEN
    # =================================================================
    def _render_preview_fullscreen(self, screen):
        rect = screen.get_rect()
        screen.fill((8, 8, 12))

        render_rect = self._preview_render_rect(rect)

        # background so dentro do rect de render
        self._render_canvas_bg(screen, render_rect)

        try:
            preview = self._ensure_preview_animator()
            preview.current_frame = self.current_frame
            preview.render(
                screen, camera=None,
                screen_manager=_FullscreenScreenManager(render_rect),
                hidden_actors=self._hidden_actor_ids())
        except Exception as e:
            self.logger.error(f"preview: {e}")

        # moldura de celular quando nao e 16:9
        if render_rect != rect:
            # escurece fora do frame
            mask = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
            mask.fill((0, 0, 0, 180))
            mask.fill((0, 0, 0, 0), render_rect)
            screen.blit(mask, (0, 0))

            # borda branca grossa
            pygame.draw.rect(screen, (240, 240, 240), render_rect, 3)

            # "notch" fake no topo (opcional, charme de celular)
            notch_w, notch_h = 120, 16
            notch = pygame.Rect(0, 0, notch_w, notch_h)
            notch.center = (render_rect.centerx, render_rect.top + 8)
            pygame.draw.rect(screen, (20, 20, 24), notch, border_radius=8)

        if not getattr(self, "preview_hud_hidden", False):
            self._render_preview_hud(screen, rect)

    def _render_preview_hud(self, screen, rect):
        font = self._font(self.FONT_SM, bold=True)
        font_big = self._font(self.FONT_BASE, bold=True)

        state = ">> PLAY" if getattr(self, "preview_playing", True) else "|| PAUSE"
        info = (f"{int(self.current_frame):>4} / "
                f"{self.current_anim.duration_frames}   {state}")
        bg_w = font_big.size(info)[0] + 22
        bg_h = 26
        bg_rect = pygame.Rect(rect.x + 16, rect.bottom - bg_h - 16,
                              bg_w, bg_h)
        bg_surf = pygame.Surface(bg_rect.size, pygame.SRCALPHA)
        bg_surf.fill((0, 0, 0, 140))
        screen.blit(bg_surf, bg_rect.topleft)
        pygame.draw.rect(screen, (255, 255, 255, 60),
                         bg_rect, 1, border_radius=4)
        txt = font_big.render(info, True, (255, 255, 255))
        screen.blit(txt, txt.get_rect(center=bg_rect.center))

        name = f"{self.current_anim.category}/{self.current_anim.name}"
        nt = font.render(name, True, (240, 240, 240))
        nrect = pygame.Rect(rect.x + 16, rect.y + 16,
                            nt.get_width() + 20, 24)
        nbg = pygame.Surface(nrect.size, pygame.SRCALPHA)
        nbg.fill((0, 0, 0, 130))
        screen.blit(nbg, nrect.topleft)
        pygame.draw.rect(screen, (255, 255, 255, 45),
                         nrect, 1, border_radius=4)
        screen.blit(nt, (nrect.x + 10, nrect.y + 5))

        hints = (f"[{self.preview_aspect}]  A: aspect   "
                 "P/ESC: sair   Space: play/pause   "
                 "< >: frame   R: reiniciar   H: HUD")
        ht = font.render(hints, True, (200, 200, 200))
        hrect = pygame.Rect(rect.right - ht.get_width() - 32,
                            rect.bottom - 32,
                            ht.get_width() + 16, 22)
        hbg = pygame.Surface(hrect.size, pygame.SRCALPHA)
        hbg.fill((0, 0, 0, 120))
        screen.blit(hbg, hrect.topleft)
        screen.blit(ht, (hrect.x + 8, hrect.y + 4))