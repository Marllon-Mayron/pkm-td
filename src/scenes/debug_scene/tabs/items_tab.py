# src/scenes/debug_scene/tabs/items_tab.py
"""
Aba ITENS — adicionar / remover itens da bag. Layout maior.
"""

import pygame

from src.data.item_bag_catalog import item_bag_catalog
from src.managers.sounds.sound_manager import sound_manager, SoundEffect


# Tamanhos
ROW_H = 72
SPRITE_SIZE = 56
SEARCH_H = 44
DETAIL_SPRITE = 132


class ItemsTab:
    INPUT_NAMES = {"item_search"}

    # ------------------------------------------------------------------
    def __init__(self, parent):
        self.parent = parent
        self.focused_input = None

        self.entries = self._load_entries()
        self.filtered = list(self.entries)
        self.search_text = ""
        self.scroll = 0
        self.selected = 0
        self.quantity = 1

    # ==================================================================
    # CARREGAMENTO
    # ==================================================================
    def _load_entries(self):
        try:
            all_items = item_bag_catalog.get_all_items()
        except Exception:
            return []

        entries = []
        for item in all_items:
            entries.append({
                "id": item["id"],
                "name": item.get("name", item["id"]),
                "category": item.get("category", "items"),
                "description": item.get("description", ""),
                "price": item.get("price", 0),
                "owned": 0,
            })
        entries.sort(key=lambda e: (e["category"], e["name"].lower()))
        return entries

    def refresh_owned(self):
        bag_items = getattr(self.parent.game.player.bag, "items", {}) or {}
        for e in self.entries:
            e["owned"] = int(bag_items.get(e["id"], 0))

    def _apply_search(self):
        q = self.search_text.strip().lower()
        if not q:
            self.filtered = list(self.entries)
        else:
            self.filtered = [
                e for e in self.entries
                if q in e["name"].lower()
                or q in e["id"].lower()
                or q in e["category"].lower()
            ]
        self.scroll = 0
        self.selected = 0

    def _current_entry(self):
        if not self.filtered:
            return None
        if 0 <= self.selected < len(self.filtered):
            return self.filtered[self.selected]
        return None

    # ==================================================================
    # INTERFACE COM O PAI
    # ==================================================================
    def has_focus(self):
        return self.focused_input is not None

    def get_focus(self):
        return self.focused_input

    def clear_focus(self):
        self.focused_input = None

    # ==================================================================
    # EVENTOS
    # ==================================================================
    def handle_event(self, event):
        if event.type == pygame.MOUSEWHEEL:
            max_s = max(0, len(self.filtered) - self._visible())
            self.scroll = max(0, min(max_s, self.scroll - event.y))
            return

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            clicked = self.parent.find_click_at(event.pos)
            if clicked not in self.INPUT_NAMES:
                self.focused_input = None
            if clicked:
                self.on_click(clicked)
            return

        if event.type == pygame.KEYDOWN and self.focused_input == "item_search":
            if event.key == pygame.K_BACKSPACE:
                self.search_text = self.search_text[:-1]
                self._apply_search()
            elif event.key in (pygame.K_RETURN, pygame.K_TAB):
                self.focused_input = None
            elif event.unicode and event.unicode.isprintable():
                if len(self.search_text) < 24:
                    self.search_text += event.unicode
                    self._apply_search()

    def _visible(self):
        return 8

    def on_click(self, name):
        if name.startswith("item_row_"):
            try:
                idx = int(name[len("item_row_"):])
            except ValueError:
                return
            if 0 <= idx < len(self.filtered):
                self.selected = idx
                self.quantity = 1
            return

        if name == "item_search":
            self.focused_input = "item_search"; return
        if name == "item_search_clear":
            self.search_text = ""
            self._apply_search()
            return

        if name == "item_qty_minus10":
            self.quantity = max(1, self.quantity - 10); return
        if name == "item_qty_minus":
            self.quantity = max(1, self.quantity - 1); return
        if name == "item_qty_plus":
            self.quantity = min(999, self.quantity + 1); return
        if name == "item_qty_plus10":
            self.quantity = min(999, self.quantity + 10); return
        if name == "item_qty_max":
            e = self._current_entry()
            self.quantity = 999; return

        if name == "action_item_add":
            self._action_add(); return
        if name == "action_item_remove":
            self._action_remove(); return
        if name == "action_item_clear":
            self._action_clear(); return

    # ==================================================================
    # AÇÕES
    # ==================================================================
    def _action_add(self):
        e = self._current_entry()
        if not e:
            self.parent.show_message("Nenhum item selecionado.")
            return
        try:
            self.parent.game.player.bag.add_item(e["id"], self.quantity)
        except Exception as ex:
            self.parent.show_message(f"Erro: {ex}")
            return
        self.refresh_owned()
        self.parent.save_game()
        self.parent.show_message(f"+{self.quantity}x {e['name']}")
        sound_manager.play_effect(SoundEffect.CLICK, volume=0.3)

    def _action_remove(self):
        e = self._current_entry()
        if not e:
            self.parent.show_message("Nenhum item selecionado.")
            return
        try:
            current = self.parent.game.player.bag.get_quantity(e["id"])
            to_remove = min(current, self.quantity)
            if to_remove <= 0:
                self.parent.show_message("Você não possui este item.")
                return
            self.parent.game.player.bag.remove_item(e["id"], to_remove)
        except Exception as ex:
            self.parent.show_message(f"Erro: {ex}")
            return
        self.refresh_owned()
        self.parent.save_game()
        self.parent.show_message(f"-{to_remove}x {e['name']}")
        sound_manager.play_effect(SoundEffect.CLICK, volume=0.3)

    def _action_clear(self):
        e = self._current_entry()
        if not e:
            return
        try:
            current = self.parent.game.player.bag.get_quantity(e["id"])
            if current <= 0:
                self.parent.show_message("Você não possui este item.")
                return
            self.parent.game.player.bag.remove_item(e["id"], current)
        except Exception as ex:
            self.parent.show_message(f"Erro: {ex}")
            return
        self.refresh_owned()
        self.parent.save_game()
        self.parent.show_message(f"Removido tudo de {e['name']}.")
        sound_manager.play_effect(SoundEffect.CLICK, volume=0.3)

    def fixed_update(self, dt):
        pass

    # ==================================================================
    # RENDER
    # ==================================================================
    def render(self, screen, left_rect, right_rect):
        self.refresh_owned()
        p = self.parent

        # ===== Search =====
        search_rect = pygame.Rect(left_rect.x + 10, left_rect.y + 10,
                                  left_rect.width - 20, SEARCH_H)
        p.register_click("item_search", search_rect)
        pygame.draw.rect(screen, (15, 15, 25), search_rect, border_radius=6)
        border = (255, 200, 60) if self.focused_input == "item_search" else (80, 80, 110)
        pygame.draw.rect(screen, border, search_rect, 2, border_radius=6)

        f = p.get_font(16)
        display = self.search_text if self.search_text else "Buscar item..."
        color = (220, 220, 230) if self.search_text else (110, 110, 130)
        if self.focused_input == "item_search":
            display += "_"
        t = f.render(display, True, color)
        screen.blit(t, (search_rect.x + 12,
                        search_rect.y + (search_rect.height - t.get_height()) // 2))

        if self.search_text:
            clr = pygame.Rect(search_rect.right - 32, search_rect.y + 8, 28, 28)
            p.register_click("item_search_clear", clr)
            p.draw_button(screen, clr, "x", font_size=15)

        # ===== Lista =====
        list_y = search_rect.bottom + 10
        list_h = left_rect.bottom - list_y - 10
        row_h = ROW_H
        visible = max(1, list_h // row_h)
        self._visible = lambda: visible

        # resumo
        summary_f = p.get_font(13)
        summary = summary_f.render(f"{len(self.filtered)} itens",
                                   True, (150, 160, 190))
        screen.blit(summary, (left_rect.x + 12, list_y - 14))

        if not self.filtered:
            f = p.get_font(16)
            t = f.render("Nenhum item encontrado", True, (160, 160, 180))
            screen.blit(t, (left_rect.centerx - t.get_width() // 2,
                            left_rect.centery - t.get_height() // 2))
            self._render_detail(screen, right_rect)
            return

        start = self.scroll
        end = min(len(self.filtered), start + visible)

        for i in range(start, end):
            idx = i - start
            row = pygame.Rect(left_rect.x + 10, list_y + idx * row_h,
                              left_rect.width - 20, row_h - 4)
            e = self.filtered[i]
            selected = (i == self.selected)
            hovered = row.collidepoint(pygame.mouse.get_pos())

            if selected:
                bg, border = (55, 60, 95), (160, 190, 255)
            elif hovered:
                bg, border = (42, 46, 68), (110, 130, 170)
            else:
                bg, border = (30, 32, 48), (55, 55, 75)

            pygame.draw.rect(screen, bg, row, border_radius=6)
            pygame.draw.rect(screen, border, row, 2 if selected else 1, border_radius=6)
            p.register_click(f"item_row_{i}", row)

            # Sprite grande
            try:
                sprite = item_bag_catalog.get_sprite(e["id"], scaled=True)
            except Exception:
                sprite = None
            if sprite:
                ss = SPRITE_SIZE
                try:
                    sp = pygame.transform.smoothscale(sprite, (ss, ss))
                except Exception:
                    sp = sprite
                box = pygame.Rect(row.x + 8, row.y + (row.height - ss) // 2, ss, ss)
                pygame.draw.rect(screen, (18, 20, 32), box, border_radius=6)
                pygame.draw.rect(screen, (70, 75, 100), box, 1, border_radius=6)
                screen.blit(sp, (box.x + (ss - sp.get_width()) // 2,
                                 box.y + (ss - sp.get_height()) // 2))

            # Nome
            nf = p.get_font(18)
            clr = (255, 255, 255) if selected else (215, 220, 235)
            ns = nf.render(e["name"], True, clr)
            screen.blit(ns, (row.x + SPRITE_SIZE + 24, row.y + 12))

            # Categoria
            cat_f = p.get_font(12)
            cs = cat_f.render(e["category"].upper(), True, (140, 150, 180))
            screen.blit(cs, (row.x + SPRITE_SIZE + 24,
                             row.y + row.height - cs.get_height() - 12))

            # Quantidade
            qty_color = (150, 220, 150) if e["owned"] > 0 else (120, 120, 140)
            qf = p.get_font(18)
            qs = qf.render(f"x{e['owned']}", True, qty_color)
            screen.blit(qs, (row.right - qs.get_width() - 16,
                             row.y + (row.height - qs.get_height()) // 2))

        if len(self.filtered) > visible:
            bar_x = left_rect.right - 8
            thumb_h = max(24, int(list_h * visible / len(self.filtered)))
            max_s = max(1, len(self.filtered) - visible)
            thumb_y = list_y + int((list_h - thumb_h) * self.scroll / max_s)
            pygame.draw.rect(screen, (40, 40, 60), (bar_x, list_y, 5, list_h), border_radius=3)
            pygame.draw.rect(screen, (140, 110, 180),
                             (bar_x, thumb_y, 5, thumb_h), border_radius=3)

        self._render_detail(screen, right_rect)

    def _render_detail(self, screen, panel):
        e = self._current_entry()
        p = self.parent
        if not e:
            f = p.get_font(16)
            t = f.render("Selecione um item", True, (160, 160, 180))
            screen.blit(t, (panel.centerx - t.get_width() // 2,
                            panel.centery - t.get_height() // 2))
            return

        pad = 20
        y = panel.y + pad
        inner_w = panel.width - pad * 2

        # ===== Cabeçalho grande =====
        header_h = DETAIL_SPRITE + 16
        header_rect = pygame.Rect(panel.x + pad, y, inner_w, header_h)
        pygame.draw.rect(screen, (26, 30, 48), header_rect, border_radius=10)
        pygame.draw.rect(screen, (90, 80, 130), header_rect, 2, border_radius=10)

        # Sprite grande
        try:
            sprite = item_bag_catalog.get_sprite(e["id"], scaled=True)
        except Exception:
            sprite = None

        ss = DETAIL_SPRITE
        sprite_box = pygame.Rect(header_rect.x + 8,
                                 header_rect.y + (header_h - ss) // 2, ss, ss)
        pygame.draw.rect(screen, (18, 20, 32), sprite_box, border_radius=8)
        pygame.draw.rect(screen, (70, 75, 100), sprite_box, 2, border_radius=8)
        if sprite:
            try:
                sc = pygame.transform.smoothscale(sprite, (ss - 16, ss - 16))
            except Exception:
                sc = pygame.transform.scale(sprite, (ss - 16, ss - 16))
            screen.blit(sc, (sprite_box.x + (ss - sc.get_width()) // 2,
                             sprite_box.y + (ss - sc.get_height()) // 2))

        # Nome + categoria + preço
        name_f = p.get_font(28)
        ns = name_f.render(e["name"], True, (255, 255, 255))
        tx = header_rect.x + ss + 24
        ty = header_rect.y + 20
        screen.blit(ns, (tx, ty))

        cat_f = p.get_font(15)
        cs = cat_f.render(f"Categoria: {e['category'].upper()}",
                          True, (170, 180, 210))
        screen.blit(cs, (tx, ty + ns.get_height() + 6))

        if e.get("price"):
            pf = p.get_font(15)
            ps = pf.render(f"Preço base: ${e['price']}",
                           True, (200, 220, 200))
            screen.blit(ps, (tx, ty + ns.get_height() + 6 + cs.get_height() + 4))

        # Quantidade possuída (badge grande)
        owned_f = p.get_font(22)
        owned_text = f"x{e['owned']}"
        owned_color = (150, 220, 150) if e["owned"] > 0 else (120, 120, 140)
        os_ = owned_f.render(owned_text, True, owned_color)
        ob = pygame.Rect(header_rect.right - os_.get_width() - 40,
                         header_rect.y + 20, os_.get_width() + 24,
                         os_.get_height() + 8)
        pygame.draw.rect(screen, (18, 24, 20) if e["owned"] > 0 else (28, 28, 34),
                         ob, border_radius=6)
        pygame.draw.rect(screen, owned_color, ob, 2, border_radius=6)
        screen.blit(os_, (ob.x + 12, ob.y + 4))

        y = header_rect.bottom + 18

        # ===== Descrição =====
        p.draw_section_title(screen, panel.x + pad, y, inner_w, "DESCRIÇÃO")
        y += 24

        desc_f = p.get_font(15)
        desc = e.get("description", "") or "(sem descrição)"
        lines = p.wrap_text(desc, desc_f, inner_w)
        for line in lines[:4]:
            ls = desc_f.render(line, True, (200, 205, 220))
            screen.blit(ls, (panel.x + pad, y))
            y += desc_f.get_height() + 4
        y += 8

        # ===== Quantidade =====
        p.draw_section_title(screen, panel.x + pad, y, inner_w, "QUANTIDADE")
        y += 26

        qty_h = 34
        btn_w = 52
        total_btns_w = btn_w * 3 + 12

        # Linha: -10 | - | [slider] | + | +10
        # Layout: [-10] [-] [slider] [+] [+10]
        minus10 = pygame.Rect(panel.x + pad, y, btn_w, qty_h)
        minus1 = pygame.Rect(minus10.right + 8, y, btn_w, qty_h)

        plus10 = pygame.Rect(panel.right - pad - btn_w, y, btn_w, qty_h)
        plus1 = pygame.Rect(plus10.x - btn_w - 8, y, btn_w, qty_h)

        p.register_click("item_qty_minus10", minus10)
        p.register_click("item_qty_minus", minus1)
        p.register_click("item_qty_plus", plus1)
        p.register_click("item_qty_plus10", plus10)

        p.draw_button(screen, minus10, "-10", font_size=15)
        p.draw_button(screen, minus1, "-", font_size=18)
        p.draw_button(screen, plus1, "+", font_size=18)
        p.draw_button(screen, plus10, "+10", font_size=15)

        slider_x = minus1.right + 12
        slider_w = plus1.x - slider_x - 12
        p.render_slider(screen, slider_x, y, slider_w, qty_h,
                        "", self.quantity, 1, 999, "item_qty_slider",
                        on_change=lambda v: setattr(self, "quantity", v))
        y += qty_h + 18

        # ===== Ações =====
        action_h = 46
        gap = 12
        add_w = (inner_w - gap * 2) // 3
        remove_w = add_w
        clear_w = inner_w - add_w - remove_w - gap * 2

        add_rect = pygame.Rect(panel.x + pad, y, add_w, action_h)
        remove_rect = pygame.Rect(add_rect.right + gap, y, remove_w, action_h)
        clear_rect = pygame.Rect(remove_rect.right + gap, y, clear_w, action_h)

        p.register_click("action_item_add", add_rect)
        p.register_click("action_item_remove", remove_rect)
        p.register_click("action_item_clear", clear_rect)

        p.draw_button(screen, add_rect, "ADICIONAR", success=True, font_size=17)
        p.draw_button(screen, remove_rect, "REMOVER", danger=True, font_size=17)
        p.draw_button(screen, clear_rect, "LIMPAR TUDO", font_size=15)

    # ---------- FOOTER ----------
    def render_footer(self, screen, footer_rect):
        p = self.parent
        hint_f = p.get_font(14)
        hint = hint_f.render(
            "ESC: voltar   ·   Scroll: navegar   ·   Alterações são salvas automaticamente",
            True, (140, 140, 160))
        screen.blit(hint, (footer_rect.right - hint.get_width() - 24,
                           footer_rect.y + (footer_rect.height - hint.get_height()) // 2))