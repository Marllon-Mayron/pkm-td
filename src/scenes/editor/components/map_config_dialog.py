# src/scenes/editor/components/map_config_dialog.py

import pygame
import os

from src.config.regions import RegionCatalog, DEFAULT_REGION_ID


class MapConfigDialog:
    """Diálogo de configuração do mapa — Suporta REGIÕES."""

    # ---------- dimensões internas ----------
    TITLE_H = 38
    ROW_H = 30
    ROW_GAP = 8
    SECTION_GAP = 14
    MARGIN = 18
    LABEL_W = 90
    DROPDOWN_MAX_H = 180

    def __init__(self, x, y, width, height,
                 current_width, current_height,
                 current_chapter=1, current_phase=1, current_name="Fase",
                 current_localization_type="default",
                 current_custom_folder="",
                 current_unlock_chapter=1, current_unlock_phase=1,
                 current_day_night_mode="random", current_base_weather="random",
                 current_region=DEFAULT_REGION_ID,
                 current_unlock_region=DEFAULT_REGION_ID):

        self.rect = pygame.Rect(x, y, width, height)
        self.visible = True

        # ===== Valores atuais =====
        self.current_width = current_width
        self.current_height = current_height
        self.current_chapter = current_chapter
        self.current_phase = current_phase
        self.current_name = current_name
        self.current_localization_type = current_localization_type
        self.current_custom_folder = current_custom_folder
        self.current_unlock_chapter = current_unlock_chapter
        self.current_unlock_phase = current_unlock_phase
        self.current_day_night_mode = current_day_night_mode
        self.current_base_weather = current_base_weather
        self.current_region = int(current_region) if current_region else DEFAULT_REGION_ID
        self.current_unlock_region = int(current_unlock_region) if current_unlock_region else DEFAULT_REGION_ID

        # ===== Temporários =====
        self.temp_width = str(current_width)
        self.temp_height = str(current_height)
        self.temp_chapter = str(current_chapter)
        self.temp_phase = str(current_phase)
        self.temp_name = current_name
        self.temp_localization_type = current_localization_type
        self.temp_custom_folder = current_custom_folder
        self.temp_unlock_chapter = str(current_unlock_chapter)
        self.temp_unlock_phase = str(current_unlock_phase)
        self.temp_day_night_mode = current_day_night_mode
        self.temp_base_weather = current_base_weather
        self.temp_region = self.current_region
        self.temp_unlock_region = self.current_unlock_region

        self.active_input = "name"

        # ===== Dropdowns =====
        self.region_options = [
            {"id": r.id, "label": r.name} for r in RegionCatalog.get_all()
        ]
        self.region_selected_index = self._find_index(self.region_options, self.temp_region)
        self.region_hovered_index = -1
        self.region_dropdown_open = False

        self.unlock_region_selected_index = self._find_index(self.region_options, self.temp_unlock_region)
        self.unlock_region_hovered_index = -1
        self.unlock_region_dropdown_open = False

        self.environment_options = [
            {"id": "random", "label": "Aleatorio"},
            {"id": "day",    "label": "Dia"},
            {"id": "night",  "label": "Noite"},
            {"id": "dusk",   "label": "Entardecer"},
            {"id": "dawn",   "label": "Amanhecer"},
            {"id": "cave",   "label": "Caverna"},
            {"id": "deep",   "label": "Fundo do Mar"},
        ]
        self.environment_selected_index = self._find_index(self.environment_options, self.temp_day_night_mode)
        self.environment_hovered_index = -1
        self.environment_dropdown_open = False

        self.weather_options = [
            {"id": "random", "label": "Aleatorio"},
            {"id": "none",   "label": "Normal"},
            {"id": "sunny",  "label": "Sol Forte"},
            {"id": "rain",   "label": "Chuva"},
        ]
        self.weather_selected_index = self._find_index(self.weather_options, self.temp_base_weather)
        self.weather_hovered_index = -1
        self.weather_dropdown_open = False

        # ===== Botões =====
        btn_w, btn_h, gap = 110, 34, 15
        total = btn_w * 2 + gap
        bx = x + (width - total) // 2
        by = y + height - 50
        self.confirm_rect = pygame.Rect(bx, by, btn_w, btn_h)
        self.cancel_rect  = pygame.Rect(bx + btn_w + gap, by, btn_w, btn_h)

        # ===== UI state =====
        self.dragging = False
        self.drag_offset_x = 0
        self.drag_offset_y = 0
        self.hovered_button = None

        self._font_cache = {}

        # ===== Cores =====
        self.colors = {
            'bg':               (45, 48, 60),
            'bg_header':        (55, 58, 72),
            'bg_input':         (55, 58, 72),
            'bg_dropdown':      (50, 53, 68),
            'bg_dropdown_hover':(65, 70, 90),
            'border':           (80, 85, 105),
            'border_active':    (100, 150, 255),
            'border_dropdown':  (90, 95, 115),
            'text':             (235, 235, 245),
            'text_dim':         (180, 185, 200),
            'text_muted':       (130, 135, 155),
            'title':            (255, 215, 0),
            'section':          (150, 200, 255),
            'accent':           (80, 110, 180),
            'success':          (60, 180, 60),
            'danger':           (200, 60, 60),
            'radio_on':         (100, 150, 255),
            'radio_off':        (80, 85, 105),
            'divider':          (65, 70, 90),
        }

        self._calculate_positions()

    # ==================================================================
    # HELPERS
    # ==================================================================
    def _find_index(self, options, target_id):
        for i, opt in enumerate(options):
            if opt["id"] == target_id:
                return i
        return 0

    def _get_font(self, size, bold=False):
        key = (size, bold)
        if key not in self._font_cache:
            f = pygame.font.Font(None, size)
            if bold:
                f.set_bold(True)
            self._font_cache[key] = f
        return self._font_cache[key]

    # ==================================================================
    # LAYOUT
    # ==================================================================
    def _calculate_positions(self):
        x, y, w, h = self.rect
        m = self.MARGIN
        lw = self.LABEL_W
        rh = self.ROW_H
        sp = self.ROW_GAP
        gap = self.SECTION_GAP

        cursor = y + self.TITLE_H + 10

        # -------- Seção: Identificação --------
        self.section_id_rect = pygame.Rect(x + m, cursor, w - m * 2, 14)
        cursor += 16

        # Nome (full width)
        self.name_label_rect = pygame.Rect(x + m, cursor, 55, rh)
        self.name_input_rect = pygame.Rect(x + m + 60, cursor, w - m * 2 - 60, rh)
        cursor += rh + sp

        # Região | Capítulo | Fase
        col = (w - m * 2 - 16) // 3
        self.region_label_rect = pygame.Rect(x + m, cursor, 55, rh)
        self.region_dropdown_rect = pygame.Rect(x + m + 55, cursor + 1, col - 55, rh - 2)

        self.chapter_label_rect = pygame.Rect(x + m + col + 8, cursor, 55, rh)
        self.chapter_input_rect = pygame.Rect(x + m + col + 63, cursor, col - 63, rh)

        self.phase_label_rect = pygame.Rect(x + m + col * 2 + 16, cursor, 45, rh)
        self.phase_input_rect = pygame.Rect(x + m + col * 2 + 61, cursor, col - 61, rh)
        cursor += rh + sp

        # Largura | Altura
        half = (w - m * 2 - 10) // 2
        self.width_label_rect = pygame.Rect(x + m, cursor, 70, rh)
        self.width_input_rect = pygame.Rect(x + m + 75, cursor, 70, rh)
        self.height_label_rect = pygame.Rect(x + m + half + 10, cursor, 60, rh)
        self.height_input_rect = pygame.Rect(x + m + half + 70, cursor, 70, rh)
        cursor += rh + gap

        # -------- Seção: Localização --------
        self.section_loc_rect = pygame.Rect(x + m, cursor, w - m * 2, 14)
        cursor += 16

        self.loc_label_rect = pygame.Rect(x + m, cursor, lw, rh)
        radio_size = 18
        ry = cursor + (rh - radio_size) // 2
        self.default_radio_rect = pygame.Rect(x + m + lw + 5, ry, radio_size, radio_size)
        self.custom_radio_rect  = pygame.Rect(x + m + lw + 130, ry, radio_size, radio_size)
        cursor += rh + sp

        # Pasta custom
        self.folder_label_rect = pygame.Rect(x + m, cursor, 60, rh)
        self.folder_input_rect = pygame.Rect(x + m + 65, cursor, w - m * 2 - 65 - 50, rh)
        self.browse_button_rect = pygame.Rect(x + m + (w - m * 2) - 45, cursor, 45, rh)
        cursor += rh + sp

        # Unlock (região | cap | fase)
        self.unlock_label_rect = pygame.Rect(x + m, cursor, 95, rh)

        uc_col = (w - m * 2 - 95 - 20) // 3
        self.unlock_region_label_rect = pygame.Rect(x + m + 100, cursor, 55, rh)
        self.unlock_region_dropdown_rect = pygame.Rect(x + m + 100, cursor + 1,
                                                        uc_col, rh - 2)
        self.unlock_chapter_label_rect = pygame.Rect(x + m + 100 + uc_col + 10, cursor, 40, rh)
        self.unlock_chapter_input_rect = pygame.Rect(x + m + 100 + uc_col + 55, cursor,
                                                      uc_col - 55, rh)
        self.unlock_phase_label_rect = pygame.Rect(x + m + 100 + uc_col * 2 + 20, cursor, 40, rh)
        self.unlock_phase_input_rect = pygame.Rect(x + m + 100 + uc_col * 2 + 65, cursor,
                                                    uc_col - 65, rh)
        cursor += rh + gap

        # -------- Seção: Ambiente --------
        self.section_env_rect = pygame.Rect(x + m, cursor, w - m * 2, 14)
        cursor += 16

        self.environment_label_rect = pygame.Rect(x + m, cursor, lw, rh)
        self.environment_dropdown_rect = pygame.Rect(x + m + lw + 5, cursor + 1, 200, rh - 2)
        cursor += rh + sp

        self.weather_label_rect = pygame.Rect(x + m, cursor, lw, rh)
        self.weather_dropdown_rect = pygame.Rect(x + m + lw + 5, cursor + 1, 200, rh - 2)
        cursor += rh + sp

        self._content_bottom = cursor

    def _update_button_positions(self):
        btn_w, btn_h, gap = 110, 34, 15
        total = btn_w * 2 + gap
        bx = self.rect.x + (self.rect.width - total) // 2
        by = self.rect.y + self.rect.height - 50
        self.confirm_rect.x = bx
        self.confirm_rect.y = by
        self.cancel_rect.x = bx + btn_w + gap
        self.cancel_rect.y = by

    def _get_dropdown_list_rect(self, dropdown_rect, num_items):
        item_h = 28
        list_h = min(num_items * item_h + 4, self.DROPDOWN_MAX_H)
        r = pygame.Rect(dropdown_rect.x, dropdown_rect.bottom + 2,
                        dropdown_rect.width, list_h)

        bottom_limit = self.rect.bottom - 55
        if r.bottom > bottom_limit:
            r.y = dropdown_rect.top - list_h - 2
            if r.top < self.rect.top + self.TITLE_H + 5:
                r.y = dropdown_rect.bottom + 2
                r.height = max(60, bottom_limit - r.y)
        return r

    # ==================================================================
    # STATE HELPERS (dropdowns)
    # ==================================================================
    def _dropdown_get(self, key):
        return {
            'region':        (self.region_selected_index,
                              self.region_hovered_index,
                              self.region_dropdown_open),
            'unlock_region': (self.unlock_region_selected_index,
                              self.unlock_region_hovered_index,
                              self.unlock_region_dropdown_open),
            'environment':   (self.environment_selected_index,
                              self.environment_hovered_index,
                              self.environment_dropdown_open),
            'weather':       (self.weather_selected_index,
                              self.weather_hovered_index,
                              self.weather_dropdown_open),
        }[key]

    def _dropdown_set(self, key, selected=None, hovered=None, opened=None):
        if key == 'region':
            if selected is not None: self.region_selected_index = selected
            if hovered  is not None: self.region_hovered_index  = hovered
            if opened   is not None: self.region_dropdown_open  = opened
        elif key == 'unlock_region':
            if selected is not None: self.unlock_region_selected_index = selected
            if hovered  is not None: self.unlock_region_hovered_index  = hovered
            if opened   is not None: self.unlock_region_dropdown_open  = opened
        elif key == 'environment':
            if selected is not None: self.environment_selected_index = selected
            if hovered  is not None: self.environment_hovered_index  = hovered
            if opened   is not None: self.environment_dropdown_open  = opened
        elif key == 'weather':
            if selected is not None: self.weather_selected_index = selected
            if hovered  is not None: self.weather_hovered_index  = hovered
            if opened   is not None: self.weather_dropdown_open  = opened

    def _dropdown_commit(self, key, option_id):
        if key == 'region':        self.temp_region = option_id
        elif key == 'unlock_region': self.temp_unlock_region = option_id
        elif key == 'environment': self.temp_day_night_mode = option_id
        elif key == 'weather':     self.temp_base_weather = option_id

    def _dropdown_options_for(self, key):
        return {
            'region':        self.region_options,
            'unlock_region': self.region_options,
            'environment':   self.environment_options,
            'weather':       self.weather_options,
        }[key]

    def _dropdown_rect_for(self, key):
        return {
            'region':        self.region_dropdown_rect,
            'unlock_region': self.unlock_region_dropdown_rect,
            'environment':   self.environment_dropdown_rect,
            'weather':       self.weather_dropdown_rect,
        }[key]

    def _close_all_dropdowns(self, except_key=None):
        for k in ('region', 'unlock_region', 'environment', 'weather'):
            if k != except_key:
                self._dropdown_set(k, opened=False)

    # ==================================================================
    # EVENTS
    # ==================================================================
    def handle_event(self, event):
        if not self.visible:
            return None

        # Se algum dropdown está aberto, trata primeiro
        for key in ('region', 'unlock_region', 'environment', 'weather'):
            _, _, opened = self._dropdown_get(key)
            if opened:
                res = self._handle_dropdown_event(event, key)
                if res is not None:
                    return res

        if event.type == pygame.KEYDOWN:
            return self._handle_keydown(event)

        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                return self._handle_mousedown(event)
            elif event.button == 2:
                mp = pygame.mouse.get_pos()
                if self.rect.collidepoint(mp):
                    self.dragging = True
                    self.drag_offset_x = mp[0] - self.rect.x
                    self.drag_offset_y = mp[1] - self.rect.y
                    return None

        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 2 and self.dragging:
                self.dragging = False
                return None

        elif event.type == pygame.MOUSEMOTION:
            if self.dragging:
                mp = pygame.mouse.get_pos()
                self.rect.x = mp[0] - self.drag_offset_x
                self.rect.y = mp[1] - self.drag_offset_y
                self._calculate_positions()
                self._update_button_positions()
                return None

            mp = pygame.mouse.get_pos()
            self.hovered_button = None
            if self.confirm_rect.collidepoint(mp):   self.hovered_button = "confirm"
            elif self.cancel_rect.collidepoint(mp):  self.hovered_button = "cancel"
            elif self.browse_button_rect.collidepoint(mp): self.hovered_button = "browse"

        return None

    def _handle_dropdown_event(self, event, key):
        options = self._dropdown_options_for(key)
        dr = self._dropdown_rect_for(key)
        sel, hov, _ = self._dropdown_get(key)

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mp = pygame.mouse.get_pos()
            list_rect = self._get_dropdown_list_rect(dr, len(options))

            if list_rect.collidepoint(mp):
                item_h = 28
                rel = mp[1] - list_rect.y - 2
                idx = int(rel // item_h)
                if 0 <= idx < len(options):
                    self._dropdown_set(key, selected=idx, opened=False)
                    self._dropdown_commit(key, options[idx]["id"])
                    return None

            if not dr.collidepoint(mp):
                self._dropdown_set(key, opened=False)
                return None
            else:
                self._dropdown_set(key, opened=False)
                return None

        elif event.type == pygame.MOUSEMOTION:
            list_rect = self._get_dropdown_list_rect(dr, len(options))
            if list_rect.collidepoint(event.pos):
                item_h = 28
                rel = event.pos[1] - list_rect.y - 2
                idx = int(rel // item_h)
                if 0 <= idx < len(options):
                    self._dropdown_set(key, hovered=idx)
                else:
                    self._dropdown_set(key, hovered=-1)
            else:
                self._dropdown_set(key, hovered=-1)

        elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self._dropdown_set(key, opened=False)
            return None

        return None

    def _handle_keydown(self, event):
        if event.key == pygame.K_RETURN:
            return self.confirm()
        if event.key == pygame.K_ESCAPE:
            self.visible = False
            return None
        if event.key == pygame.K_TAB:
            inputs = ["name", "width", "height", "chapter", "phase"]
            if self.temp_localization_type == "custom":
                inputs.extend(["custom_folder", "unlock_chapter", "unlock_phase"])
            cur = inputs.index(self.active_input) if self.active_input in inputs else 0
            self.active_input = inputs[(cur + 1) % len(inputs)]
            return None
        if event.key == pygame.K_BACKSPACE:
            if   self.active_input == "name":            self.temp_name = self.temp_name[:-1]
            elif self.active_input == "width":           self.temp_width = self.temp_width[:-1]
            elif self.active_input == "height":          self.temp_height = self.temp_height[:-1]
            elif self.active_input == "chapter":         self.temp_chapter = self.temp_chapter[:-1]
            elif self.active_input == "phase":           self.temp_phase = self.temp_phase[:-1]
            elif self.active_input == "custom_folder":   self.temp_custom_folder = self.temp_custom_folder[:-1]
            elif self.active_input == "unlock_chapter":  self.temp_unlock_chapter = self.temp_unlock_chapter[:-1]
            elif self.active_input == "unlock_phase":    self.temp_unlock_phase = self.temp_unlock_phase[:-1]
            return None

        # Digitação
        if self.active_input == "name":
            if event.unicode.isprintable() and event.unicode not in ['/', '\\', ':', '*', '?', '"', '<', '>', '|']:
                self.temp_name += event.unicode
        elif self.active_input == "custom_folder":
            if event.unicode.isalnum() or event.unicode in ['_', '-']:
                self.temp_custom_folder += event.unicode
        elif event.unicode.isdigit():
            if   self.active_input == "width":           self.temp_width += event.unicode
            elif self.active_input == "height":          self.temp_height += event.unicode
            elif self.active_input == "chapter":         self.temp_chapter += event.unicode
            elif self.active_input == "phase":           self.temp_phase += event.unicode
            elif self.active_input == "unlock_chapter":  self.temp_unlock_chapter += event.unicode
            elif self.active_input == "unlock_phase":    self.temp_unlock_phase += event.unicode
        return None

    def _handle_mousedown(self, event):
        mp = pygame.mouse.get_pos()

        if self.confirm_rect.collidepoint(mp):
            return self.confirm()
        if self.cancel_rect.collidepoint(mp):
            self.visible = False
            return None

        # Inputs
        for rect, key in (
            (self.name_input_rect,     "name"),
            (self.width_input_rect,    "width"),
            (self.height_input_rect,   "height"),
            (self.chapter_input_rect,  "chapter"),
            (self.phase_input_rect,    "phase"),
        ):
            if rect.collidepoint(mp):
                self.active_input = key
                return None

        # Radios
        if self.default_radio_rect.collidepoint(mp):
            self.temp_localization_type = "default"
            self.temp_custom_folder = ""
            self.active_input = "name"
            return None
        if self.custom_radio_rect.collidepoint(mp):
            self.temp_localization_type = "custom"
            self.active_input = "custom_folder"
            return None

        if self.temp_localization_type == "custom":
            if self.browse_button_rect.collidepoint(mp):
                from tkinter import filedialog, Tk
                root = Tk(); root.withdraw()
                folder = filedialog.askdirectory(title="Selecione a pasta")
                if folder:
                    self.temp_custom_folder = os.path.basename(folder)
                return None
            if self.folder_input_rect.collidepoint(mp):
                self.active_input = "custom_folder"
                return None
            if self.unlock_chapter_input_rect.collidepoint(mp):
                self.active_input = "unlock_chapter"
                return None
            if self.unlock_phase_input_rect.collidepoint(mp):
                self.active_input = "unlock_phase"
                return None

        # Dropdowns
        for key in ('region', 'unlock_region', 'environment', 'weather'):
            dr = self._dropdown_rect_for(key)
            if dr.collidepoint(mp):
                _, _, opened = self._dropdown_get(key)
                self._close_all_dropdowns(except_key=key)
                self._dropdown_set(key, opened=not opened)
                return None

        if not self.rect.collidepoint(mp):
            self.visible = False
            return None

        return None

    def confirm(self):
        try:
            new_width = max(5, min(500, int(self.temp_width or 10)))
            new_height = max(5, min(500, int(self.temp_height or 10)))
            new_chapter = max(1, min(99, int(self.temp_chapter or 1)))
            new_phase = max(1, min(99, int(self.temp_phase or 1)))
            new_name = self.temp_name.strip() or f"Fase {new_chapter}-{new_phase}"

            new_region = int(self.temp_region or DEFAULT_REGION_ID)

            custom_folder = self.temp_custom_folder.strip()
            if self.temp_localization_type == "custom" and not custom_folder:
                loc_type = "default"
                custom_folder = ""
                unlock_region = DEFAULT_REGION_ID
                unlock_chapter = 1
                unlock_phase = 1
            else:
                loc_type = self.temp_localization_type
                if loc_type == "custom":
                    unlock_region = int(self.temp_unlock_region or DEFAULT_REGION_ID)
                    unlock_chapter = max(1, min(99, int(self.temp_unlock_chapter or 1)))
                    unlock_phase = max(1, min(99, int(self.temp_unlock_phase or 1)))
                else:
                    custom_folder = ""
                    unlock_region = DEFAULT_REGION_ID
                    unlock_chapter = 1
                    unlock_phase = 1

            self.visible = False
            return {
                'width': new_width,
                'height': new_height,
                'region': new_region,
                'chapter': new_chapter,
                'phase': new_phase,
                'name': new_name,
                'localization_type': loc_type,
                'custom_folder': custom_folder,
                'day_night_mode': self.temp_day_night_mode,
                'base_weather': self.temp_base_weather,
                'unlock_region': unlock_region,
                'unlock_chapter': unlock_chapter,
                'unlock_phase': unlock_phase,
            }
        except ValueError:
            return None

    # ==================================================================
    # RENDER
    # ==================================================================
    def render(self, screen):
        if not self.visible:
            return

        # Overlay
        ov = pygame.Surface((screen.get_width(), screen.get_height()))
        ov.set_alpha(180)
        ov.fill((0, 0, 0))
        screen.blit(ov, (0, 0))

        # Fundo
        pygame.draw.rect(screen, self.colors['bg'], self.rect, border_radius=12)
        pygame.draw.rect(screen, self.colors['border'], self.rect, 2, border_radius=12)

        # Header
        title_bar = pygame.Rect(self.rect.x, self.rect.y, self.rect.width, self.TITLE_H)
        pygame.draw.rect(screen, self.colors['bg_header'], title_bar,
                         border_top_left_radius=12, border_top_right_radius=12)
        t = self._get_font(22, True).render("Configuracoes do Mapa", True, self.colors['title'])
        screen.blit(t, (self.rect.x + self.MARGIN, self.rect.y + 10))
        pygame.draw.line(screen, self.colors['divider'],
                         (self.rect.x + 8, title_bar.bottom),
                         (self.rect.right - 8, title_bar.bottom), 1)

        # ---- Seção: Identificação ----
        self._render_section(screen, self.section_id_rect, "IDENTIFICACAO")
        self._render_label(screen, self.name_label_rect, "Nome:", self.colors['text_dim'])
        self._render_input(screen, self.name_input_rect, self.temp_name, "name",
                           self.active_input == "name")

        # Região
        self._render_label(screen, self.region_label_rect, "Regiao:", self.colors['text_dim'])
        self._render_dropdown(screen, self.region_dropdown_rect,
                              self.region_options, self.region_selected_index,
                              self.region_dropdown_open, self.region_hovered_index,
                              'region')

        # Capítulo / Fase
        self._render_label(screen, self.chapter_label_rect, "Capitulo:", self.colors['text_dim'])
        self._render_input(screen, self.chapter_input_rect, self.temp_chapter,
                           "chapter", self.active_input == "chapter")
        self._render_label(screen, self.phase_label_rect, "Fase:", self.colors['text_dim'])
        self._render_input(screen, self.phase_input_rect, self.temp_phase,
                           "phase", self.active_input == "phase")

        # Largura / Altura
        self._render_label(screen, self.width_label_rect, "Largura:", self.colors['text_dim'])
        self._render_input(screen, self.width_input_rect, self.temp_width,
                           "width", self.active_input == "width")
        self._render_label(screen, self.height_label_rect, "Altura:", self.colors['text_dim'])
        self._render_input(screen, self.height_input_rect, self.temp_height,
                           "height", self.active_input == "height")

        # ---- Seção: Localização ----
        self._render_section(screen, self.section_loc_rect, "LOCALIZACAO")
        self._render_label(screen, self.loc_label_rect, "Tipo:", self.colors['text_dim'])

        self._render_radio(screen, self.default_radio_rect,
                           self.temp_localization_type == "default")
        dt = self._get_font(16).render("Capitulos (normal)", True, self.colors['text'])
        screen.blit(dt, (self.default_radio_rect.right + 6, self.default_radio_rect.y - 1))

        self._render_radio(screen, self.custom_radio_rect,
                           self.temp_localization_type == "custom")
        ct = self._get_font(16).render("Minigame", True, self.colors['text'])
        screen.blit(ct, (self.custom_radio_rect.right + 6, self.custom_radio_rect.y - 1))

        if self.temp_localization_type == "custom":
            self._render_label(screen, self.folder_label_rect, "Pasta:", self.colors['text_dim'])
            color = self.colors['border_active'] if self.active_input == "custom_folder" else self.colors['border']
            pygame.draw.rect(screen, self.colors['bg_input'], self.folder_input_rect, border_radius=6)
            pygame.draw.rect(screen, color, self.folder_input_rect, 2, border_radius=6)
            disp = self.temp_custom_folder or "Selecione uma pasta..."
            tcol = self.colors['text'] if self.temp_custom_folder else self.colors['text_muted']
            fs = self._get_font(15)
            if fs.size(disp)[0] > self.folder_input_rect.width - 12:
                while fs.size(disp + "...")[0] > self.folder_input_rect.width - 12 and len(disp) > 3:
                    disp = disp[:-1]
                disp += "..."
            fs = fs.render(disp, True, tcol)
            screen.blit(fs, (self.folder_input_rect.x + 8, self.folder_input_rect.y + 6))

            hv = self.hovered_button == "browse"
            bc = self.colors['accent'] if hv else (70, 80, 110)
            pygame.draw.rect(screen, bc, self.browse_button_rect, border_radius=6)
            pygame.draw.rect(screen, self.colors['border'], self.browse_button_rect, 1, border_radius=6)
            bt = self._get_font(16).render("...", True, self.colors['text'])
            screen.blit(bt, (self.browse_button_rect.centerx - bt.get_width() // 2,
                             self.browse_button_rect.centery - bt.get_height() // 2))

            # Unlock
            self._render_label(screen, self.unlock_label_rect, "Desbloqueio:", self.colors['text_dim'])
            self._render_label(screen, self.unlock_region_label_rect, "Regiao:", self.colors['text_muted'])
            self._render_dropdown(screen, self.unlock_region_dropdown_rect,
                                  self.region_options, self.unlock_region_selected_index,
                                  self.unlock_region_dropdown_open,
                                  self.unlock_region_hovered_index, 'unlock_region')
            self._render_label(screen, self.unlock_chapter_label_rect, "Cap:", self.colors['text_muted'])
            self._render_input(screen, self.unlock_chapter_input_rect,
                               self.temp_unlock_chapter, "unlock_chapter",
                               self.active_input == "unlock_chapter", small=True)
            self._render_label(screen, self.unlock_phase_label_rect, "Fase:", self.colors['text_muted'])
            self._render_input(screen, self.unlock_phase_input_rect,
                               self.temp_unlock_phase, "unlock_phase",
                               self.active_input == "unlock_phase", small=True)

        # ---- Seção: Ambiente ----
        self._render_section(screen, self.section_env_rect, "AMBIENTE")
        self._render_label(screen, self.environment_label_rect, "Dia/Noite:", self.colors['text_dim'])
        self._render_dropdown(screen, self.environment_dropdown_rect,
                              self.environment_options, self.environment_selected_index,
                              self.environment_dropdown_open, self.environment_hovered_index,
                              'environment')

        self._render_label(screen, self.weather_label_rect, "Clima:", self.colors['text_dim'])
        self._render_dropdown(screen, self.weather_dropdown_rect,
                              self.weather_options, self.weather_selected_index,
                              self.weather_dropdown_open, self.weather_hovered_index,
                              'weather')

        # ---- Botões ----
        cc = self.colors['success'] if self.hovered_button == "confirm" else (40, 140, 40)
        pygame.draw.rect(screen, cc, self.confirm_rect, border_radius=8)
        pygame.draw.rect(screen, (255, 255, 255), self.confirm_rect, 1, border_radius=8)
        cf = self._get_font(18).render("Confirmar", True, (255, 255, 255))
        screen.blit(cf, (self.confirm_rect.centerx - cf.get_width() // 2,
                         self.confirm_rect.centery - cf.get_height() // 2))

        dc = self.colors['danger'] if self.hovered_button == "cancel" else (160, 40, 40)
        pygame.draw.rect(screen, dc, self.cancel_rect, border_radius=8)
        pygame.draw.rect(screen, (255, 255, 255), self.cancel_rect, 1, border_radius=8)
        ct2 = self._get_font(18).render("Cancelar", True, (255, 255, 255))
        screen.blit(ct2, (self.cancel_rect.centerx - ct2.get_width() // 2,
                          self.cancel_rect.centery - ct2.get_height() // 2))

    # ---------- helpers de render ----------
    def _render_section(self, screen, rect, text):
        pygame.draw.line(screen, self.colors['divider'],
                         (rect.x, rect.y + rect.height // 2),
                         (rect.right, rect.y + rect.height // 2), 1)
        fs = self._get_font(13, True).render(text, True, self.colors['section'])
        bg = pygame.Rect(rect.x + 6, rect.y + rect.height // 2 - fs.get_height() // 2,
                        fs.get_width() + 10, fs.get_height())
        pygame.draw.rect(screen, self.colors['bg'], bg)
        screen.blit(fs, (rect.x + 11, rect.y + rect.height // 2 - fs.get_height() // 2))

    def _render_label(self, screen, rect, text, color):
        f = self._get_font(16).render(text, True, color)
        screen.blit(f, (rect.x, rect.y + (rect.height - f.get_height()) // 2))

    def _render_input(self, screen, rect, text, field, active, small=False):
        size = 15 if small else 17
        color = self.colors['border_active'] if active else self.colors['border']
        pygame.draw.rect(screen, self.colors['bg_input'], rect, border_radius=6)
        pygame.draw.rect(screen, color, rect, 2, border_radius=6)
        f = self._get_font(size)
        disp = text
        if f.size(disp)[0] > rect.width - 12:
            while f.size(disp + "...")[0] > rect.width - 12 and len(disp) > 2:
                disp = disp[:-1]
            disp += "..."
        fs = f.render(disp, True, self.colors['text'])
        screen.blit(fs, (rect.x + 6, rect.y + (rect.height - fs.get_height()) // 2))

    def _render_radio(self, screen, rect, selected):
        center = (rect.centerx, rect.centery)
        r = rect.width // 2
        color = self.colors['radio_on'] if selected else self.colors['radio_off']
        pygame.draw.circle(screen, color, center, r)
        pygame.draw.circle(screen, (255, 255, 255), center, r - 2)
        if selected:
            pygame.draw.circle(screen, color, center, r - 5)

    def _render_dropdown(self, screen, rect, options, sel_idx, is_open, hover_idx, key):
        pygame.draw.rect(screen, self.colors['bg_input'], rect, border_radius=6)
        pygame.draw.rect(screen,
                         self.colors['border_active'] if is_open else self.colors['border'],
                         rect, 2, border_radius=6)

        if 0 <= sel_idx < len(options):
            t = self._get_font(16).render(options[sel_idx]["label"], True, self.colors['text'])
            screen.blit(t, (rect.x + 8, rect.y + (rect.height - t.get_height()) // 2))

        arrow = "^" if is_open else "v"
        a = self._get_font(14).render(arrow, True, self.colors['text_muted'])
        screen.blit(a, (rect.right - 18, rect.y + (rect.height - a.get_height()) // 2))

        if is_open:
            list_rect = self._get_dropdown_list_rect(rect, len(options))
            pygame.draw.rect(screen, self.colors['bg_dropdown'], list_rect, border_radius=6)
            pygame.draw.rect(screen, self.colors['border_dropdown'], list_rect, 1, border_radius=6)

            item_h = 28
            visible = min(len(options), list_rect.height // item_h)
            for i in range(visible):
                ir = pygame.Rect(list_rect.x + 4, list_rect.y + 2 + i * item_h,
                                 list_rect.width - 8, item_h - 2)
                is_sel = (i == sel_idx)
                is_hov = (i == hover_idx)
                bg = self.colors['accent'] if is_sel else (
                    self.colors['bg_dropdown_hover'] if is_hov else self.colors['bg_dropdown'])
                pygame.draw.rect(screen, bg, ir, border_radius=4)
                tc = self.colors['text'] if (is_sel or is_hov) else self.colors['text_dim']
                f = self._get_font(15).render(options[i]["label"], True, tc)
                screen.blit(f, (ir.x + 8, ir.y + (ir.height - f.get_height()) // 2))
                if is_sel:
                    ck = self._get_font(14).render("X", True, self.colors['radio_on'])
                    screen.blit(ck, (ir.right - 18, ir.y + (ir.height - ck.get_height()) // 2))