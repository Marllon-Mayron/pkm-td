# src/scenes/editor/components/load_phase_dialog.py

import pygame
import os
from tkinter import filedialog, Tk

from src.config.regions import RegionCatalog, DEFAULT_REGION_ID


class LoadPhaseDialog:
    """Diálogo para carregar fase/minigame — Suporta REGIÕES."""

    HEADER_H = 32
    ROW_H = 28

    def __init__(self, x, y, width, height, exporter):
        self.rect = pygame.Rect(x, y, width, height)
        self.visible = True
        self.exporter = exporter

        # UI state
        self.dragging = False
        self.drag_offset_x = 0
        self.drag_offset_y = 0
        self.hovered_button = None
        self.hovered_phase_idx = -1
        self.hovered_region_idx = -1

        # Modo
        self.load_type = "default"       # "default" | "custom"
        self.selected_custom_folder = ""

        # Regiões
        self.available_regions = []
        self.selected_region = DEFAULT_REGION_ID
        self.region_scroll = 0
        self.max_region_scroll = 0

        # Fases
        self.filtered_phases = []        # [(region, chapter, phase)]
        self.selected_chapter = 1
        self.selected_phase = 1
        self.temp_chapter = "1"
        self.temp_phase = "1"
        self.phase_scroll = 0
        self.max_phase_scroll = 0
        self.items_per_page = 8

        # Minigames
        self.available_custom_folders = []

        # Inputs
        self.active_input = None

        # Fontes
        self.font_title = pygame.font.Font(None, 22)
        self.font = pygame.font.Font(None, 18)
        self.font_small = pygame.font.Font(None, 15)

        # Cores
        self.colors = {
            'bg': (45, 48, 60),
            'bg_header': (55, 58, 72),
            'bg_list': (35, 38, 50),
            'bg_row': (45, 48, 60),
            'bg_row_alt': (42, 45, 56),
            'bg_row_sel': (80, 110, 160),
            'bg_row_hover': (60, 70, 90),
            'border': (80, 85, 105),
            'border_sel': (140, 180, 240),
            'text': (235, 235, 245),
            'text_dim': (180, 185, 200),
            'text_muted': (130, 135, 155),
            'title': (255, 215, 0),
            'accent': (80, 110, 180),
            'success': (60, 180, 60),
            'danger': (200, 60, 60),
        }

        self._load_regions()
        self._load_minigame_folders()
        self._refresh_phase_list()
        self._init_buttons()

    # ==================================================================
    # DADOS
    # ==================================================================
    def _load_regions(self):
        try:
            self.available_regions = self.exporter.list_regions_with_phases()
        except Exception:
            self.available_regions = []
        if not self.available_regions:
            self.available_regions = [DEFAULT_REGION_ID]
        if self.selected_region not in self.available_regions:
            self.selected_region = self.available_regions[0]

    def _load_minigame_folders(self):
        try:
            self.available_custom_folders = self.exporter.list_minigame_folders()
        except Exception:
            self.available_custom_folders = []
        if self.available_custom_folders and self.selected_custom_folder not in self.available_custom_folders:
            self.selected_custom_folder = self.available_custom_folders[0]

    def _refresh_phase_list(self):
        if self.load_type == "default":
            try:
                all_phases = self.exporter.list_phases(region=self.selected_region)
            except Exception:
                all_phases = []
            # all_phases agora é [(chapter, phase), ...]
            self.filtered_phases = sorted(all_phases, key=lambda x: (x[0], x[1]))
        else:
            if self.selected_custom_folder:
                try:
                    levels = self.exporter.list_phases(
                        localization_type="custom",
                        custom_folder=self.selected_custom_folder,
                        region=None,  # todas
                    )
                except Exception:
                    levels = []
                # levels é [(region, chapter, phase), ...]
                self.filtered_phases = sorted(levels, key=lambda x: (x[0], x[1], x[2]))
            else:
                self.filtered_phases = []

        if self.filtered_phases:
            if self.load_type == "default":
                self.selected_chapter, self.selected_phase = self.filtered_phases[0]
            else:
                _, self.selected_chapter, self.selected_phase = self.filtered_phases[0]
            self.temp_chapter = str(self.selected_chapter)
            self.temp_phase = str(self.selected_phase)

        self.phase_scroll = 0
        self.max_phase_scroll = max(0, len(self.filtered_phases) - self.items_per_page)
        self.max_region_scroll = max(0, len(self.available_regions) - 6)

    # ==================================================================
    # BOTÕES
    # ==================================================================
    def _init_buttons(self):
        self._recompute_rects()

    def _recompute_rects(self):
        x, y, w, h = self.rect

        # Toggle tipo
        self.default_btn = pygame.Rect(x + 15, y + 42, 110, 28)
        self.custom_btn  = pygame.Rect(x + 130, y + 42, 110, 28)

        # Refresh
        self.refresh_btn = pygame.Rect(x + w - 90, y + 42, 75, 28)

        # Layout principal (duas colunas)
        col_left_w = 140
        content_y = y + 80
        content_h = h - 80 - 90

        self.region_list_rect = pygame.Rect(x + 15, content_y + 20,
                                            col_left_w, content_h - 20)
        self.phase_list_rect = pygame.Rect(x + 15 + col_left_w + 15,
                                           content_y + 20,
                                           w - 30 - col_left_w - 15,
                                           content_h - 20)

        # Inputs (default)
        bottom_y = y + h - 85
        self.chapter_input = pygame.Rect(x + 60, bottom_y, 60, 26)
        self.phase_input   = pygame.Rect(x + 170, bottom_y, 60, 26)

        # Botões inferiores
        btn_w, btn_h = 110, 32
        gap = 15
        total = btn_w * 2 + gap
        bx = x + (w - total) // 2
        by = y + h - 46
        self.load_button = pygame.Rect(bx, by, btn_w, btn_h)
        self.cancel_button = pygame.Rect(bx + btn_w + gap, by, btn_w, btn_h)

        # "Buscar pasta" para minigames
        self.browse_btn = pygame.Rect(x + w - 60, content_y - 4, 45, 22)

    def _update_button_positions(self):
        self._recompute_rects()

    # ==================================================================
    # EVENTOS
    # ==================================================================
    def handle_event(self, event):
        if not self.visible:
            return None

        mp = pygame.mouse.get_pos()

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if not self.rect.collidepoint(mp):
                self.visible = False
                return None

        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                return self._handle_left_click(mp)
            elif event.button == 4:
                if self.phase_list_rect.collidepoint(mp):
                    self.phase_scroll = max(0, self.phase_scroll - 1)
                elif self.region_list_rect.collidepoint(mp):
                    self.region_scroll = max(0, self.region_scroll - 1)
                return None
            elif event.button == 5:
                if self.phase_list_rect.collidepoint(mp):
                    self.phase_scroll = min(self.max_phase_scroll, self.phase_scroll + 1)
                elif self.region_list_rect.collidepoint(mp):
                    self.region_scroll = min(self.max_region_scroll, self.region_scroll + 1)
                return None

        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1:
                self.dragging = False
                return None

        elif event.type == pygame.MOUSEMOTION:
            self._update_hover(mp)
            if self.dragging:
                self.rect.x = mp[0] - self.drag_offset_x
                self.rect.y = mp[1] - self.drag_offset_y
                self._update_button_positions()
                return None

        elif event.type == pygame.KEYDOWN:
            return self._handle_keydown(event)

        return None

    def _update_hover(self, mp):
        self.hovered_button = None
        self.hovered_phase_idx = -1
        self.hovered_region_idx = -1

        for name, rect in (
            ("load", self.load_button), ("cancel", self.cancel_button),
            ("refresh", self.refresh_btn),
            ("default", self.default_btn), ("custom", self.custom_btn),
            ("browse", self.browse_btn),
        ):
            if rect.collidepoint(mp):
                self.hovered_button = name
                break

        if self.phase_list_rect.collidepoint(mp):
            rel_y = mp[1] - self.phase_list_rect.y - 2
            idx = int(rel_y // self.ROW_H) + self.phase_scroll
            if 0 <= idx < len(self.filtered_phases):
                self.hovered_phase_idx = idx

        if self.region_list_rect.collidepoint(mp):
            rel_y = mp[1] - self.region_list_rect.y - 2
            idx = int(rel_y // self.ROW_H) + self.region_scroll
            if 0 <= idx < len(self.available_regions):
                self.hovered_region_idx = idx

    def _handle_left_click(self, mp):
        # Título (drag)
        title_rect = pygame.Rect(self.rect.x, self.rect.y, self.rect.width, self.HEADER_H)
        if title_rect.collidepoint(mp):
            self.dragging = True
            self.drag_offset_x = mp[0] - self.rect.x
            self.drag_offset_y = mp[1] - self.rect.y
            return None

        if self.load_button.collidepoint(mp):
            return self._confirm_load()

        if self.cancel_button.collidepoint(mp):
            self.visible = False
            return None

        if self.refresh_btn.collidepoint(mp):
            self._load_regions()
            self._load_minigame_folders()
            self._refresh_phase_list()
            return None

        if self.default_btn.collidepoint(mp):
            if self.load_type != "default":
                self.load_type = "default"
                self._refresh_phase_list()
            return None

        if self.custom_btn.collidepoint(mp):
            if self.load_type != "custom":
                self.load_type = "custom"
                self._refresh_phase_list()
            return None

        if self.load_type == "custom" and self.browse_btn.collidepoint(mp):
            root = Tk(); root.withdraw()
            folder = filedialog.askdirectory(title="Selecione a pasta do minigame")
            if folder:
                name = os.path.basename(folder)
                if name in self.available_custom_folders:
                    self.selected_custom_folder = name
                    self._refresh_phase_list()
                else:
                    print(f"Pasta '{name}' nao encontrada em src/data/minigames/")
            return None

        # Lista de regiões (só modo default)
        if self.load_type == "default" and self.region_list_rect.collidepoint(mp):
            rel_y = mp[1] - self.region_list_rect.y - 2
            idx = int(rel_y // self.ROW_H) + self.region_scroll
            if 0 <= idx < len(self.available_regions):
                new_region = self.available_regions[idx]
                if new_region != self.selected_region:
                    self.selected_region = new_region
                    self._refresh_phase_list()
            return None

        # Lista de fases
        if self.phase_list_rect.collidepoint(mp):
            rel_y = mp[1] - self.phase_list_rect.y - 2
            idx = int(rel_y // self.ROW_H) + self.phase_scroll
            if 0 <= idx < len(self.filtered_phases):
                entry = self.filtered_phases[idx]
                if self.load_type == "default":
                    self.selected_chapter, self.selected_phase = entry
                else:
                    _, self.selected_chapter, self.selected_phase = entry
                self.temp_chapter = str(self.selected_chapter)
                self.temp_phase = str(self.selected_phase)
            return None

        # Inputs
        if self.load_type == "default":
            if self.chapter_input.collidepoint(mp):
                self.active_input = "chapter"
                return None
            if self.phase_input.collidepoint(mp):
                self.active_input = "phase"
                return None
            self.active_input = None

        return None

    def _handle_keydown(self, event):
        if event.key == pygame.K_ESCAPE:
            self.visible = False
            return None
        if event.key == pygame.K_RETURN:
            return self._confirm_load()
        if not self.active_input:
            return None

        if event.key == pygame.K_BACKSPACE:
            if self.active_input == "chapter":
                self.temp_chapter = self.temp_chapter[:-1]
            else:
                self.temp_phase = self.temp_phase[:-1]
            return None
        if event.unicode.isdigit():
            if self.active_input == "chapter":
                self.temp_chapter += event.unicode
            else:
                self.temp_phase += event.unicode
            return None
        return None

    def _confirm_load(self):
        try:
            chapter = int(self.temp_chapter or 1)
            phase = int(self.temp_phase or 1)

            if self.load_type == "default":
                if (chapter, phase) in self.filtered_phases:
                    self.visible = False
                    return {
                        'action': 'load',
                        'region': int(self.selected_region),
                        'chapter': chapter,
                        'phase': phase,
                        'localization_type': 'default',
                        'custom_folder': '',
                    }
                print(f"Fase {chapter}-{phase} nao encontrada na regiao {self.selected_region}")
                return None
            else:
                if not self.selected_custom_folder:
                    print("Nenhuma pasta de minigame selecionada!")
                    return None
                for entry in self.filtered_phases:
                    r, c, p = entry
                    if c == chapter and p == phase:
                        self.visible = False
                        return {
                            'action': 'load',
                            'region': int(r),
                            'chapter': chapter,
                            'phase': phase,
                            'localization_type': 'custom',
                            'custom_folder': self.selected_custom_folder,
                        }
                print(f"Nivel {chapter}-{phase} nao encontrado no minigame!")
                return None
        except ValueError:
            return None

    # ==================================================================
    # RENDER
    # ==================================================================
    def render(self, screen):
        if not self.visible:
            return

        ov = pygame.Surface((screen.get_width(), screen.get_height()))
        ov.set_alpha(180)
        ov.fill((0, 0, 0))
        screen.blit(ov, (0, 0))

        pygame.draw.rect(screen, self.colors['bg'], self.rect, border_radius=10)
        pygame.draw.rect(screen, self.colors['title'], self.rect, 2, border_radius=10)

        # Header
        tb = pygame.Rect(self.rect.x, self.rect.y, self.rect.width, self.HEADER_H)
        pygame.draw.rect(screen, self.colors['bg_header'], tb,
                         border_top_left_radius=10, border_top_right_radius=10)
        t = self.font_title.render("Carregar Fase / Minigame", True, (255, 255, 255))
        screen.blit(t, (self.rect.x + 12, self.rect.y + 7))

        # Toggle tipo
        self._draw_toggle(screen, self.default_btn, "Capitulos",
                          self.load_type == "default", "default")
        self._draw_toggle(screen, self.custom_btn, "Minigames",
                          self.load_type == "custom", "custom")

        # Refresh
        rc = (80, 100, 120) if self.hovered_button == "refresh" else (60, 60, 80)
        pygame.draw.rect(screen, rc, self.refresh_btn, border_radius=5)
        pygame.draw.rect(screen, self.colors['title'], self.refresh_btn, 1, border_radius=5)
        rt = self.font_small.render("Atualizar", True, (255, 255, 255))
        screen.blit(rt, (self.refresh_btn.centerx - rt.get_width() // 2,
                         self.refresh_btn.centery - rt.get_height() // 2))

        # ===== Coluna esquerda =====
        if self.load_type == "default":
            lbl = self.font_small.render("Regiao", True, self.colors['title'])
            screen.blit(lbl, (self.region_list_rect.x, self.region_list_rect.y - 18))
            self._render_region_list(screen)
        else:
            lbl = self.font_small.render("Minigame", True, self.colors['title'])
            screen.blit(lbl, (self.region_list_rect.x, self.region_list_rect.y - 18))

            # Caixa do minigame atual
            box = pygame.Rect(self.region_list_rect.x, self.region_list_rect.y,
                              self.region_list_rect.width, 30)
            pygame.draw.rect(screen, self.colors['bg_list'], box, border_radius=5)
            pygame.draw.rect(screen, self.colors['border'], box, 1, border_radius=5)
            name = self.selected_custom_folder or "-"
            if self.font_small.size(name)[0] > box.width - 10:
                name = name[:12] + "..."
            nt = self.font_small.render(name, True, self.colors['text'])
            screen.blit(nt, (box.x + 6, box.y + (box.height - nt.get_height()) // 2))

            # Botão browse
            bc = (80, 100, 120) if self.hovered_button == "browse" else (60, 60, 80)
            pygame.draw.rect(screen, bc, self.browse_btn, border_radius=5)
            pygame.draw.rect(screen, self.colors['title'], self.browse_btn, 1, border_radius=5)
            bt = self.font_small.render("...", True, (255, 255, 255))
            screen.blit(bt, (self.browse_btn.centerx - bt.get_width() // 2,
                             self.browse_btn.centery - bt.get_height() // 2))

            # Lista de pastas abaixo
            folder_y = box.bottom + 8
            folder_h = self.region_list_rect.bottom - folder_y
            folder_rect = pygame.Rect(self.region_list_rect.x, folder_y,
                                      self.region_list_rect.width, folder_h)
            pygame.draw.rect(screen, self.colors['bg_list'], folder_rect, border_radius=5)

            for i, fld in enumerate(self.available_custom_folders):
                if i >= 6:
                    break
                iy = folder_y + 2 + i * self.ROW_H
                ir = pygame.Rect(folder_rect.x + 2, iy, folder_rect.width - 4, self.ROW_H - 2)
                is_sel = (fld == self.selected_custom_folder)
                bg = self.colors['bg_row_sel'] if is_sel else self.colors['bg_row']
                pygame.draw.rect(screen, bg, ir, border_radius=3)
                tc = (255, 255, 255) if is_sel else self.colors['text_dim']
                ft = self.font_small.render(fld[:18], True, tc)
                screen.blit(ft, (ir.x + 6, ir.y + (ir.height - ft.get_height()) // 2))

                # Detect click
                if pygame.mouse.get_pressed()[0] and ir.collidepoint(pygame.mouse.get_pos()):
                    if fld != self.selected_custom_folder:
                        self.selected_custom_folder = fld
                        self._refresh_phase_list()

        # ===== Coluna direita: fases =====
        lbl = self.font_small.render("Niveis", True, self.colors['title'])
        screen.blit(lbl, (self.phase_list_rect.x, self.phase_list_rect.y - 18))

        pygame.draw.rect(screen, self.colors['bg_list'], self.phase_list_rect, border_radius=5)

        old_clip = screen.get_clip()
        screen.set_clip(self.phase_list_rect)

        list_start_y = self.phase_list_rect.y + 2 - self.phase_scroll * self.ROW_H
        for i, entry in enumerate(self.filtered_phases):
            iy = list_start_y + i * self.ROW_H
            if iy + self.ROW_H < self.phase_list_rect.y or iy > self.phase_list_rect.bottom:
                continue

            ir = pygame.Rect(self.phase_list_rect.x + 2, iy,
                             self.phase_list_rect.width - 4, self.ROW_H - 2)

            if self.load_type == "default":
                ch, ph = entry
                is_sel = (ch == self.selected_chapter and ph == self.selected_phase)
                text = f"Cap {ch:02d} - Fase {ph:02d}"
            else:
                r, ch, ph = entry
                is_sel = (ch == self.selected_chapter and ph == self.selected_phase)
                region_name = RegionCatalog.get_short(r)
                text = f"[{region_name}] Cap {ch:02d} - Niv {ph:02d}"

            is_hov = (i == self.hovered_phase_idx)

            if is_sel:
                bg = self.colors['bg_row_sel']
            elif is_hov:
                bg = self.colors['bg_row_hover']
            else:
                bg = self.colors['bg_row'] if i % 2 == 0 else self.colors['bg_row_alt']

            pygame.draw.rect(screen, bg, ir, border_radius=3)
            if is_sel:
                pygame.draw.rect(screen, self.colors['border_sel'], ir, 1, border_radius=3)

            tc = (255, 255, 255) if is_sel else self.colors['text_dim']
            ft = self.font_small.render(text, True, tc)
            screen.blit(ft, (ir.x + 6, ir.y + (ir.height - ft.get_height()) // 2))

        screen.set_clip(old_clip)

        # Scrollbar
        if self.max_phase_scroll > 0:
            ratio = self.phase_scroll / self.max_phase_scroll
            sh = max(20, int(self.phase_list_rect.height *
                             (self.items_per_page / len(self.filtered_phases))))
            sy = self.phase_list_rect.y + int((self.phase_list_rect.height - sh) * ratio)
            pygame.draw.rect(screen, (70, 80, 100),
                             (self.phase_list_rect.right - 5, self.phase_list_rect.y + 2,
                              3, self.phase_list_rect.height - 4), border_radius=2)
            pygame.draw.rect(screen, (150, 160, 180),
                             (self.phase_list_rect.right - 5, sy, 3, sh), border_radius=2)

        # Contador
        cnt = self.font_small.render(
            f"{len(self.filtered_phases)} {'fase(s)' if self.load_type == 'default' else 'nivel(is)'}",
            True, self.colors['text_muted'])
        screen.blit(cnt, (self.phase_list_rect.x, self.phase_list_rect.bottom + 3))

        # ===== Inputs (só default) =====
        if self.load_type == "default":
            lbl = self.font_small.render("Cap:", True, self.colors['text_dim'])
            screen.blit(lbl, (self.chapter_input.x - 30, self.chapter_input.y + 6))

            col = self.colors['border_sel'] if self.active_input == "chapter" else self.colors['border']
            pygame.draw.rect(screen, self.colors['bg_list'], self.chapter_input, border_radius=4)
            pygame.draw.rect(screen, col, self.chapter_input, 2, border_radius=4)
            t = self.font_small.render(self.temp_chapter, True, self.colors['text'])
            screen.blit(t, (self.chapter_input.x + 5, self.chapter_input.y + 6))

            lbl2 = self.font_small.render("Fase:", True, self.colors['text_dim'])
            screen.blit(lbl2, (self.phase_input.x - 35, self.phase_input.y + 6))

            col = self.colors['border_sel'] if self.active_input == "phase" else self.colors['border']
            pygame.draw.rect(screen, self.colors['bg_list'], self.phase_input, border_radius=4)
            pygame.draw.rect(screen, col, self.phase_input, 2, border_radius=4)
            t2 = self.font_small.render(self.temp_phase, True, self.colors['text'])
            screen.blit(t2, (self.phase_input.x + 5, self.phase_input.y + 6))

        # ===== Botões inferiores =====
        lc = (0, 150, 0) if self.hovered_button == "load" else (0, 120, 0)
        pygame.draw.rect(screen, lc, self.load_button, border_radius=6)
        pygame.draw.rect(screen, (255, 255, 255), self.load_button, 1, border_radius=6)
        lt = self.font.render("Carregar", True, (255, 255, 255))
        screen.blit(lt, (self.load_button.centerx - lt.get_width() // 2,
                         self.load_button.centery - lt.get_height() // 2))

        cc = (150, 0, 0) if self.hovered_button == "cancel" else (120, 0, 0)
        pygame.draw.rect(screen, cc, self.cancel_button, border_radius=6)
        pygame.draw.rect(screen, (255, 255, 255), self.cancel_button, 1, border_radius=6)
        ct = self.font.render("Cancelar", True, (255, 255, 255))
        screen.blit(ct, (self.cancel_button.centerx - ct.get_width() // 2,
                         self.cancel_button.centery - ct.get_height() // 2))

    def _draw_toggle(self, screen, rect, text, active, key):
        if active:
            bg, bc = (80, 120, 80), (255, 215, 0)
        else:
            bg = (80, 100, 120) if self.hovered_button == key else (60, 60, 80)
            bc = (100, 100, 100)
        pygame.draw.rect(screen, bg, rect, border_radius=5)
        pygame.draw.rect(screen, bc, rect, 2 if active else 1, border_radius=5)
        t = self.font_small.render(text, True, (255, 255, 255))
        screen.blit(t, (rect.centerx - t.get_width() // 2,
                        rect.centery - t.get_height() // 2))

    def _render_region_list(self, screen):
        pygame.draw.rect(screen, self.colors['bg_list'], self.region_list_rect, border_radius=5)

        old_clip = screen.get_clip()
        screen.set_clip(self.region_list_rect)

        list_start_y = self.region_list_rect.y + 2 - self.region_scroll * self.ROW_H
        for i, rid in enumerate(self.available_regions):
            iy = list_start_y + i * self.ROW_H
            if iy + self.ROW_H < self.region_list_rect.y or iy > self.region_list_rect.bottom:
                continue

            ir = pygame.Rect(self.region_list_rect.x + 2, iy,
                             self.region_list_rect.width - 4, self.ROW_H - 2)
            is_sel = (rid == self.selected_region)
            is_hov = (i == self.hovered_region_idx)

            if is_sel:
                bg = self.colors['bg_row_sel']
            elif is_hov:
                bg = self.colors['bg_row_hover']
            else:
                bg = self.colors['bg_row'] if i % 2 == 0 else self.colors['bg_row_alt']

            pygame.draw.rect(screen, bg, ir, border_radius=3)
            if is_sel:
                pygame.draw.rect(screen, self.colors['border_sel'], ir, 1, border_radius=3)

            tc = (255, 255, 255) if is_sel else self.colors['text_dim']
            t = self.font_small.render(RegionCatalog.get_name(rid), True, tc)
            screen.blit(t, (ir.x + 6, ir.y + (ir.height - t.get_height()) // 2))

        screen.set_clip(old_clip)