# src/scenes/achievement_scene/achievement_scene.py

import pygame
from typing import List, Optional

from src.scenes.base_scene import BaseScene
from src.data.achievement_data import Achievement, AchievementRarity
from src.managers.achievement_manager import AchievementManager
from src.data.item_bag_catalog import item_bag_catalog
from src.data.pokedex import Pokedex

from src.config.regions import (
    RegionCatalog, DEFAULT_REGION_ID,
    parse_phase_id, make_phase_id,
)


class AchievementScene(BaseScene):
    """Tela de conquistas do jogador — com suporte a REGIOES."""

    def __init__(self, game):
        super().__init__(game)
        self.player = game.player
        self.achievement_manager = self.player.achievement_manager
        self.pokedex = Pokedex()
        self.item_catalog = item_bag_catalog

        # Layout
        self.card_height = 190
        self.card_spacing = 10
        self.padding = 20
        self.top_margin = 140

        # Scroll
        self.scroll_offset = 0
        self.max_scroll = 0
        self.scroll_speed = 20

        # Botão voltar
        self.back_button_rect = None
        self.back_hovered = False

        # ===== FILTRO DE RARIDADE =====
        self.rarity_options = [
            {"id": None, "label": "Todas as raridades"},
            {"id": AchievementRarity.COMMON,    "label": "Comum"},
            {"id": AchievementRarity.UNCOMMON,  "label": "Incomum"},
            {"id": AchievementRarity.RARE,      "label": "Raro"},
            {"id": AchievementRarity.EPIC,      "label": "Epico"},
            {"id": AchievementRarity.LEGENDARY, "label": "Lendario"},
        ]
        self.selected_rarity_index = 0
        self.dropdown_open = False
        self.dropdown_rect = None
        self.dropdown_items_rects = []
        self.dropdown_hovered_index = -1

        # ===== FILTRO DE REGIAO =====
        self.region_options = []          # {"id": None|int, "label": str}
        self.selected_region_index = 0
        self.region_dropdown_open = False
        self.region_dropdown_rect = None
        self.region_items_rects = []
        self.region_hovered_index = -1
        self._build_region_options()

        # ===== FILTRO DE TEXTO =====
        self.filter_text: str = ""
        self.filter_input_rect = None
        self.filter_input_active = False
        self.filter_cursor_timer = 0

        # Lista
        self.achievements: List[Achievement] = []
        self._refresh_achievements()

        # ===== CORES =====
        self.colors = {
            'bg': (12, 15, 30),
            'bg_secondary': (20, 24, 45),
            'bg_card': (30, 34, 58),
            'bg_card_hover': (40, 44, 68),
            'bg_card_unlocked': (30, 50, 40),
            'text': (235, 235, 245),
            'text_dim': (180, 185, 200),
            'text_muted': (120, 125, 145),
            'border': (50, 60, 90),
            'border_accent': (80, 120, 200),
            'locked': (70, 75, 90),
            'unlocked': (100, 220, 100),
            'dropdown_bg': (25, 28, 50),
            'dropdown_hover': (40, 50, 80),
            'dropdown_border': (60, 70, 100),
            'input_bg': (22, 26, 45),
            'input_border': (50, 60, 90),
            'input_active': (80, 120, 200),
            'scroll_bg': (20, 24, 42),
            'scroll_thumb': (60, 80, 140),
            'filter_active': (50, 70, 120),
            'scroll_thumb_hover': (80, 110, 180),
            'reward_bg': (20, 25, 42),
            'reward_border': (50, 60, 85),
            'reward_text': (180, 190, 210),
            'divider': (40, 45, 65),
            'region_badge_bg': (30, 45, 75),
            'region_badge_border': (90, 130, 200),
            'region_badge_text': (200, 220, 255),
        }

        # Caches
        self._font_cache = {}
        self._rarity_colors_cache = {}
        self._region_name_cache = {}
        self._item_icon_cache = {}
        self._pokemon_portrait_cache = {}

        # Scroll drag
        self.dragging_scroll = False
        self._scroll_bar_rect = None
        self._scroll_bar_area = None

    # ==================================================================
    # REGIOES
    # ==================================================================
    def _build_region_options(self):
        """Descobre regioes que aparecem em alguma conquista desbloqueada.
        Se nenhuma conquista tem regiao, adiciona somente Kanto."""
        self.region_options = [{"id": None, "label": "Todas as regioes"}]
        self._region_name_cache = {}

        # Coleta regioes das conquistas desbloqueadas
        used_regions = set()
        try:
            for ach in self.achievement_manager.get_all_achievements():
                if not ach.unlocked:
                    continue
                # Nova API (futura): ach.region_id
                rid = getattr(ach, 'region_id', None)
                if rid is None and ach.unlocked_phase:
                    rid, _, _ = parse_phase_id(ach.unlocked_phase)
                if rid is not None:
                    used_regions.add(int(rid))
        except Exception:
            pass

        # Fallback: se ninguém declarou região, garante Kanto
        if not used_regions:
            used_regions.add(DEFAULT_REGION_ID)

        for rid in sorted(used_regions):
            self.region_options.append({
                "id": rid,
                "label": RegionCatalog.get_name(rid),
            })

        # Mantém índice válido se a lista mudou
        if self.selected_region_index >= len(self.region_options):
            self.selected_region_index = 0

    def _get_region_name(self, region_id: int) -> str:
        if region_id in self._region_name_cache:
            return self._region_name_cache[region_id]
        name = RegionCatalog.get_name(region_id)
        self._region_name_cache[region_id] = name
        return name

    def _get_achievement_region_id(self, achievement: Achievement) -> Optional[int]:
        rid = getattr(achievement, 'region_id', None)
        if rid is not None:
            return int(rid)
        raw = getattr(achievement, 'unlocked_phase', None)
        if raw:
            r, _, _ = parse_phase_id(raw)
            return r
        return None

    def _format_phase_id(self, phase_id) -> str:
        """Formata '1:1:1' -> 'Kanto · Cap 1 Fase 1'.
        Aceita formatos antigos ('1-1') e retorna fallback legível."""
        if not phase_id:
            return "Desconhecida"

        s = str(phase_id).strip()
        # Se não parece um phase_id válido, devolve como está
        if s.lower() in ("desconhecida", "none", ""):
            return "Desconhecida"

        try:
            r, c, p = parse_phase_id(s)
            rname = self._get_region_name(r)
            return f"{rname} · Cap {c} Fase {p}"
        except Exception:
            return s

    # ==================================================================
    # FONTS / ICONS
    # ==================================================================
    def _get_font(self, size, bold=False):
        key = (size, bold)
        if key not in self._font_cache:
            f = pygame.font.Font(None, size)
            if bold:
                f.set_bold(True)
            self._font_cache[key] = f
        return self._font_cache[key]

    def _get_rarity_color(self, rarity: AchievementRarity) -> tuple:
        if rarity == AchievementRarity.COMMON:    return (150, 150, 150)
        if rarity == AchievementRarity.UNCOMMON:  return (100, 200, 100)
        if rarity == AchievementRarity.RARE:      return (100, 150, 255)
        if rarity == AchievementRarity.EPIC:      return (200, 100, 255)
        if rarity == AchievementRarity.LEGENDARY: return (255, 215, 0)
        return (150, 150, 150)

    def _get_item_icon(self, item_id: str, size: int = 56) -> Optional[pygame.Surface]:
        key = f"{item_id}_{size}"
        if key in self._item_icon_cache:
            return self._item_icon_cache[key]
        sprite = self.item_catalog.get_sprite(item_id, scaled=True)
        if sprite:
            icon = pygame.transform.scale(sprite, (size, size))
            self._item_icon_cache[key] = icon
            return icon
        return None

    def _get_pokemon_portrait(self, pokemon_id: int, size: int = 72) -> Optional[pygame.Surface]:
        key = f"{pokemon_id}_{size}"
        if key in self._pokemon_portrait_cache:
            return self._pokemon_portrait_cache[key]
        portrait = self.pokedex.get_portrait(pokemon_id, "normal", shiny=False)
        if portrait:
            icon = pygame.transform.scale(portrait, (size, size))
            self._pokemon_portrait_cache[key] = icon
            return icon
        return None

    # ==================================================================
    # FILTRO
    # ==================================================================
    def _refresh_achievements(self):
        # Região selecionada
        sel_region = None
        if self.region_options and self.selected_region_index < len(self.region_options):
            sel_region = self.region_options[self.selected_region_index]["id"]

        # Se "Todas", varre todas as regiões que existem
        if sel_region is None:
            regions_to_scan = [opt["id"] for opt in self.region_options if opt["id"] is not None]
            if not regions_to_scan:
                regions_to_scan = [self.achievement_manager.get_current_region()]
            all_achievements = []
            for rid in regions_to_scan:
                all_achievements.extend(
                    self.achievement_manager.get_all_achievements(region_id=rid)
                )
        else:
            all_achievements = self.achievement_manager.get_all_achievements(region_id=sel_region)

        # Filtro raridade
        sel_rarity = self.rarity_options[self.selected_rarity_index]["id"]
        if sel_rarity:
            all_achievements = [a for a in all_achievements if a.rarity == sel_rarity]

        # Filtro texto
        if self.filter_text.strip():
            s = self.filter_text.lower().strip()
            all_achievements = [
                a for a in all_achievements
                if s in a.title.lower() or s in a.description.lower()
            ]

        # Deduplica por (region_id, id) — evita repetição se "Todas" incluir a mesma
        seen = set()
        unique = []
        for a in all_achievements:
            key = (getattr(a, 'region_id', 1), a.id)
            if key in seen:
                continue
            seen.add(key)
            unique.append(a)

        unique.sort(key=lambda a: (0 if a.unlocked else 1, self._rarity_order(a.rarity)))
        self.achievements = unique

        total_h = len(self.achievements) * (self.card_height + self.card_spacing)
        clip = self._get_clip_rect()
        self.max_scroll = max(0, total_h - clip.height)
        self.scroll_offset = min(self.scroll_offset, self.max_scroll)

    def _rarity_order(self, rarity) -> int:
        return {
            AchievementRarity.COMMON: 0,
            AchievementRarity.UNCOMMON: 1,
            AchievementRarity.RARE: 2,
            AchievementRarity.EPIC: 3,
            AchievementRarity.LEGENDARY: 4,
        }.get(rarity, 0)

    def _get_clip_rect(self):
        # topo reserva: header (80) + filtros (48) + margem (18)
        start_y = 80 + 48 + 18
        return pygame.Rect(
            20, start_y,
            self.game.screen_manager.window_width - 50,
            self.game.screen_manager.window_height - start_y - 30,
        )

    def _build_region_options(self):
        self.region_options = [{"id": None, "label": "Todas as regioes"}]
        used = set()

        raw_unlocked = getattr(self.player, 'achievements', {}).get("unlocked", []) or []
        for k in raw_unlocked:
            s = str(k)
            parts = s.split(":")
            if len(parts) == 2:
                try:
                    used.add(int(parts[0]))
                except (TypeError, ValueError):
                    pass

        # Garante região atual sempre disponível
        try:
            used.add(self.achievement_manager.get_current_region())
        except Exception:
            pass

        if not used:
            used.add(DEFAULT_REGION_ID)

        for rid in sorted(used):
            self.region_options.append({
                "id": rid,
                "label": RegionCatalog.get_name(rid),
            })

        if self.selected_region_index >= len(self.region_options):
            self.selected_region_index = 0

    # ==================================================================
    # EVENTOS
    # ==================================================================
    def handle_event(self, event):
        # ----- Input de texto -----
        if self.filter_input_active:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    self.filter_input_active = False
                    self._refresh_achievements()
                    return True
                if event.key == pygame.K_ESCAPE:
                    self.filter_input_active = False
                    self.filter_text = ""
                    self._refresh_achievements()
                    return True
                if event.key == pygame.K_BACKSPACE:
                    self.filter_text = self.filter_text[:-1]
                    self._refresh_achievements()
                elif event.unicode.isprintable():
                    self.filter_text += event.unicode
                    self._refresh_achievements()
                return True
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self.filter_input_rect and not self.filter_input_rect.collidepoint(event.pos):
                    self.filter_input_active = False
                    return True
            return False

        # ----- Dropdown raridade -----
        if self.dropdown_open:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for i, r in enumerate(self.dropdown_items_rects):
                    if r.collidepoint(event.pos):
                        self.selected_rarity_index = i
                        self.dropdown_open = False
                        self._refresh_achievements()
                        return True
                if self.dropdown_rect and not self.dropdown_rect.collidepoint(event.pos):
                    self.dropdown_open = False
                    return True
            elif event.type == pygame.MOUSEMOTION:
                self.dropdown_hovered_index = -1
                for i, r in enumerate(self.dropdown_items_rects):
                    if r.collidepoint(event.pos):
                        self.dropdown_hovered_index = i
                        break

        # ----- Dropdown regiao -----
        if self.region_dropdown_open:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for i, r in enumerate(self.region_items_rects):
                    if r.collidepoint(event.pos):
                        self.selected_region_index = i
                        self.region_dropdown_open = False
                        self._refresh_achievements()
                        return True
                if self.region_dropdown_rect and not self.region_dropdown_rect.collidepoint(event.pos):
                    self.region_dropdown_open = False
                    return True
            elif event.type == pygame.MOUSEMOTION:
                self.region_hovered_index = -1
                for i, r in enumerate(self.region_items_rects):
                    if r.collidepoint(event.pos):
                        self.region_hovered_index = i
                        break

        # ----- Scroll -----
        if event.type == pygame.MOUSEWHEEL:
            self.scroll_offset -= event.y * self.scroll_speed
            self.scroll_offset = max(0, min(self.max_scroll, self.scroll_offset))
            return True

        elif event.type == pygame.MOUSEMOTION:
            if self.back_button_rect:
                self.back_hovered = self.back_button_rect.collidepoint(event.pos)

            if self.dragging_scroll:
                clip = self._get_clip_rect()
                sb = pygame.Rect(clip.right + 5, clip.y, 12, clip.height)
                rel_y = event.pos[1] - sb.y
                ratio = max(0, min(1, rel_y / sb.height))
                self.scroll_offset = ratio * self.max_scroll

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.back_button_rect and self.back_button_rect.collidepoint(event.pos):
                self._go_back()
                return True

            if self.dropdown_rect and self.dropdown_rect.collidepoint(event.pos):
                self.dropdown_open = not self.dropdown_open
                self.region_dropdown_open = False
                return True

            if self.region_dropdown_rect and self.region_dropdown_rect.collidepoint(event.pos):
                self.region_dropdown_open = not self.region_dropdown_open
                self.dropdown_open = False
                return True

            if self.filter_input_rect and self.filter_input_rect.collidepoint(event.pos):
                self.filter_input_active = True
                return True

            clip = self._get_clip_rect()
            sb = pygame.Rect(clip.right + 5, clip.y, 12, clip.height)
            if sb.collidepoint(event.pos):
                self.dragging_scroll = True
                rel_y = event.pos[1] - sb.y
                ratio = max(0, min(1, rel_y / sb.height))
                self.scroll_offset = ratio * self.max_scroll
                return True

        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1 and self.dragging_scroll:
                self.dragging_scroll = False

        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                if self.dropdown_open or self.region_dropdown_open:
                    self.dropdown_open = False
                    self.region_dropdown_open = False
                    return True
                self._go_back()
                return True
            elif event.key == pygame.K_f:
                self.filter_input_active = True
                return True

        return False

    def _go_back(self):
        from src.scenes.phase_selector.phase_select_scene import PhaseSelectScene
        self.game.phase_select_scene = PhaseSelectScene(self.game)
        self.game.current_scene = self.game.phase_select_scene

    def fixed_update(self, dt):
        self.filter_cursor_timer += dt

    # ==================================================================
    # RENDER
    # ==================================================================
    def render(self, screen):
        screen.fill(self.colors['bg'])

        # Título
        title_font = self._get_font(44, True)
        title = title_font.render("CONQUISTAS", True, self.colors['text'])
        tx = (self.game.screen_manager.window_width - title.get_width()) // 2
        screen.blit(title, (tx, 18))

        # Linha
        pygame.draw.line(
            screen, self.colors['border'],
            (50, 68), (self.game.screen_manager.window_width - 50, 68), 2,
        )

        # Stats
        stat_font = self._get_font(20, True)
        unlocked = self.achievement_manager.get_unlocked_count()
        total = self.achievement_manager.get_total_count()
        stat_text = f"{unlocked} / {total} desbloqueadas"
        stat = stat_font.render(stat_text, True, self.colors['text_dim'])
        screen.blit(stat, (self.game.screen_manager.window_width - stat.get_width() - 30, 30))

        self._render_back_button(screen)

        # Lista / vazio
        if self.achievements:
            self._render_achievement_list(screen)
        else:
            self._render_empty_message(screen)

        # Filtros por cima
        self._render_filters(screen)

    def _render_back_button(self, screen):
        self.back_button_rect = pygame.Rect(20, 20, 120, 44)

        if self.back_hovered:
            bg = self.colors['bg_card_hover']
            border = self.colors['border_accent']
        else:
            bg = self.colors['bg_card']
            border = self.colors['border']

        pygame.draw.rect(screen, bg, self.back_button_rect, border_radius=8)
        pygame.draw.rect(screen, border, self.back_button_rect, 2, border_radius=8)

        f = self._get_font(20, True)
        t = f.render("VOLTAR", True, self.colors['text'])
        screen.blit(t, (
            self.back_button_rect.centerx - t.get_width() // 2,
            self.back_button_rect.centery - t.get_height() // 2,
        ))

    # ------------------------------------------------------------------
    # FILTROS
    # ------------------------------------------------------------------
    def _render_filters(self, screen):
        y = 80
        x = 30
        filter_h = 40

        # ---------- RARIDADE ----------
        label = self._get_font(18, True).render("Raridade:", True, self.colors['text_dim'])
        screen.blit(label, (x, y + 8))
        x += label.get_width() + 12

        self.dropdown_rect = pygame.Rect(x, y, 180, filter_h)
        self._render_dropdown(
            screen, self.dropdown_rect, self.rarity_options,
            self.selected_rarity_index, self.dropdown_open,
            self.dropdown_hovered_index, self.dropdown_items_rects,
        )
        x = self.dropdown_rect.right + 20

        # ---------- REGIAO ----------
        label2 = self._get_font(18, True).render("Regiao:", True, self.colors['text_dim'])
        screen.blit(label2, (x, y + 8))
        x += label2.get_width() + 12

        self.region_dropdown_rect = pygame.Rect(x, y, 180, filter_h)
        self._render_dropdown(
            screen, self.region_dropdown_rect, self.region_options,
            self.selected_region_index, self.region_dropdown_open,
            self.region_hovered_index, self.region_items_rects,
        )
        x = self.region_dropdown_rect.right + 20

        # ---------- BUSCA ----------
        self.filter_input_rect = pygame.Rect(x, y, 240, filter_h)

        if self.filter_input_active:
            border = self.colors['input_active']
            bg = self.colors['bg_card_hover']
        else:
            border = self.colors['input_border']
            bg = self.colors['input_bg']

        sh = self.filter_input_rect.copy(); sh.x += 2; sh.y += 2
        pygame.draw.rect(screen, (0, 0, 0, 60), sh, border_radius=8)
        pygame.draw.rect(screen, bg, self.filter_input_rect, border_radius=8)
        pygame.draw.rect(screen, border, self.filter_input_rect, 2, border_radius=8)

        f = self._get_font(17)
        disp = self.filter_text
        if self.filter_input_active and int(self.filter_cursor_timer * 2) % 2 == 0:
            disp += "|"
        tcol = self.colors['text'] if disp else self.colors['text_muted']
        t = f.render(disp or "Buscar conquista...", True, tcol)
        screen.blit(t, (
            self.filter_input_rect.x + 12,
            self.filter_input_rect.centery - t.get_height() // 2,
        ))

        # Linha separadora
        line_y = y + filter_h + 14
        pygame.draw.line(
            screen, self.colors['border'],
            (20, line_y), (self.game.screen_manager.window_width - 20, line_y), 2,
        )

    def _render_dropdown(self, screen, rect, options, selected_idx, is_open,
                         hovered_idx, items_rects_list):
        # Fechar lista antiga
        items_rects_list.clear()

        sh = rect.copy(); sh.x += 2; sh.y += 2
        pygame.draw.rect(screen, (0, 0, 0, 60), sh, border_radius=8)
        pygame.draw.rect(screen, self.colors['dropdown_bg'], rect, border_radius=8)
        pygame.draw.rect(screen, self.colors['dropdown_border'], rect, 2, border_radius=8)

        sel_label = options[selected_idx]["label"] if 0 <= selected_idx < len(options) else ""
        f = self._get_font(17)
        t = f.render(sel_label, True, self.colors['text'])
        screen.blit(t, (rect.x + 12, rect.centery - t.get_height() // 2))

        arrow = "^" if is_open else "v"
        a = f.render(arrow, True, self.colors['text_muted'])
        screen.blit(a, (rect.right - 22, rect.centery - a.get_height() // 2))

        if not is_open:
            return

        item_h = 36
        list_rect = pygame.Rect(
            rect.x, rect.bottom + 2, rect.width,
            len(options) * item_h + 4,
        )

        pygame.draw.rect(screen, self.colors['dropdown_bg'], list_rect, border_radius=8)
        pygame.draw.rect(screen, self.colors['dropdown_border'], list_rect, 2, border_radius=8)

        for i, opt in enumerate(options):
            ir = pygame.Rect(
                list_rect.x + 4,
                list_rect.y + 2 + i * item_h,
                list_rect.width - 8,
                item_h - 2,
            )
            items_rects_list.append(ir)

            if i == selected_idx:
                bg, tc = self.colors['filter_active'], self.colors['text']
            elif i == hovered_idx:
                bg, tc = self.colors['dropdown_hover'], self.colors['text']
            else:
                bg, tc = self.colors['dropdown_bg'], self.colors['text_dim']

            pygame.draw.rect(screen, bg, ir, border_radius=6)

            it = self._get_font(16).render(opt["label"], True, tc)
            screen.blit(it, (ir.x + 12, ir.centery - it.get_height() // 2))

            if i == selected_idx:
                ck = self._get_font(16).render("X", True, self.colors['unlocked'])
                screen.blit(ck, (ir.right - 25, ir.centery - ck.get_height() // 2))

    # ------------------------------------------------------------------
    # LISTA / VAZIO
    # ------------------------------------------------------------------
    def _render_empty_message(self, screen):
        clip = self._get_clip_rect()
        y = clip.y + 60
        f = self._get_font(28)
        if self.filter_text or self.selected_rarity_index > 0 or self.selected_region_index > 0:
            t = f.render("Nenhuma conquista encontrada com esses filtros", True, self.colors['text_muted'])
        else:
            t = f.render("Nenhuma conquista disponivel", True, self.colors['text_muted'])
        tx = (self.game.screen_manager.window_width - t.get_width()) // 2
        screen.blit(t, (tx, y))

    def _render_achievement_list(self, screen):
        clip = self._get_clip_rect()

        list_h = len(self.achievements) * (self.card_height + self.card_spacing)
        surface = pygame.Surface((clip.width, list_h), pygame.SRCALPHA)

        y = 0
        for ach in self.achievements:
            card_rect = pygame.Rect(0, y, clip.width, self.card_height)
            self._render_achievement_card(surface, card_rect, ach)
            y += self.card_height + self.card_spacing

        scroll_y = int(self.scroll_offset)
        old = screen.get_clip()
        screen.set_clip(clip)
        screen.blit(surface, (clip.x, clip.y - scroll_y))
        screen.set_clip(old)

        if self.max_scroll > 0:
            self._render_scrollbar(screen, clip)

    # ------------------------------------------------------------------
    # CARD
    # ------------------------------------------------------------------
    def _render_achievement_card(self, surface, rect: pygame.Rect, achievement: Achievement):
        is_unlocked = achievement.unlocked
        rarity_color = self._get_rarity_color(achievement.rarity)

        if is_unlocked:
            bg_color = self.colors['bg_card_unlocked']
            border_color = rarity_color
        else:
            bg_color = self.colors['bg_card']
            border_color = self.colors['locked']

        sh = rect.copy(); sh.x += 3; sh.y += 3
        pygame.draw.rect(surface, (0, 0, 0, 80), sh, border_radius=10)
        pygame.draw.rect(surface, bg_color, rect, border_radius=10)
        pygame.draw.rect(surface, border_color, rect, 3, border_radius=10)

        # ===== Lado esquerdo =====
        info_rect = pygame.Rect(rect.x + 15, rect.y + 8, rect.width - 320, rect.height - 16)

        # Status
        status_font = self._get_font(15, True)
        if is_unlocked:
            status_text, status_color = "DESBLOQUEADA", self.colors['unlocked']
        else:
            prog = self.achievement_manager.get_progress(achievement.id)
            if prog[1] > 1:
                status_text = f"PROGRESSO: {prog[0]}/{prog[1]}"
                status_color = self.colors['text_dim']
            else:
                status_text = "BLOQUEADA"
                status_color = self.colors['locked']

        st = status_font.render(status_text, True, status_color)
        surface.blit(st, (info_rect.right - st.get_width(), info_rect.y))

        # Raridade
        rf = self._get_font(13, True)
        rarity_names = {
            AchievementRarity.COMMON:    "COMUM",
            AchievementRarity.UNCOMMON:  "INCOMUM",
            AchievementRarity.RARE:      "RARO",
            AchievementRarity.EPIC:      "EPICO",
            AchievementRarity.LEGENDARY: "LENDARIO",
        }
        rtext = rarity_names.get(achievement.rarity, "---")
        rcol = rarity_color if is_unlocked else self.colors['locked']
        surface.blit(rf.render(rtext, True, rcol), (info_rect.x, info_rect.y))

        # Título
        title_font = self._get_font(24, True)
        title_color = self.colors['text'] if is_unlocked else self.colors['locked']
        surface.blit(title_font.render(achievement.title, True, title_color),
                     (info_rect.x, info_rect.y + 22))

        # Descrição
        desc_font = self._get_font(17)
        desc_color = self.colors['text_dim'] if is_unlocked else self.colors['text_muted']
        surface.blit(desc_font.render(achievement.description, True, desc_color),
                     (info_rect.x, info_rect.y + 52))

        # Progresso / Info
        if not is_unlocked:
            prog = self.achievement_manager.get_progress(achievement.id)
            if prog[1] > 1:
                bar_x = info_rect.x
                bar_y = info_rect.y + 80
                bar_w = min(350, info_rect.width - 20)
                bar_h = 10

                pygame.draw.rect(surface, (40, 45, 60),
                                 (bar_x, bar_y, bar_w, bar_h), border_radius=5)
                if prog[0] > 0:
                    pw = int((prog[0] / prog[1]) * bar_w)
                    if pw > 0:
                        pygame.draw.rect(surface, rarity_color,
                                         (bar_x, bar_y, pw, bar_h), border_radius=5)

                pf = self._get_font(13, True)
                pt = pf.render(f"{prog[0]} / {prog[1]}", True, self.colors['text_muted'])
                surface.blit(pt, (bar_x + bar_w + 12, bar_y - 2))

        # Data / Fase (só quando desbloqueada)
        if is_unlocked and achievement.unlocked_at:
            info_f = self._get_font(13)
            info_c = self.colors['text_muted']

            # Data
            base = f"Obtido em {achievement.unlocked_at}"

            # Fase formatada com regiao
            phase_display = None
            if achievement.unlocked_phase:
                phase_display = self._format_phase_id(achievement.unlocked_phase)

            if phase_display:
                full = f"{base}   |   {phase_display}"
            else:
                full = base

            # Se estourar, trunca a fase
            max_w = info_rect.width - 4
            t = info_f.render(full, True, info_c)
            if t.get_width() > max_w and phase_display:
                # Tenta só a fase
                full = phase_display
                t = info_f.render(full, True, info_c)

            surface.blit(t, (info_rect.x, info_rect.y + 82))

        # ===== Badge de região (canto superior direito do card) =====
        region_id = self._get_achievement_region_id(achievement)
        if region_id is not None and is_unlocked:
            badge_text = RegionCatalog.get_short(region_id)
            bf = self._get_font(12, True)
            bt = bf.render(badge_text, True, self.colors['region_badge_text'])
            bw = bt.get_width() + 14
            bh = 20
            bx = rect.right - bw - 12
            by = rect.y + 10

            pygame.draw.rect(surface, self.colors['region_badge_bg'],
                             (bx, by, bw, bh), border_radius=10)
            pygame.draw.rect(surface, self.colors['region_badge_border'],
                             (bx, by, bw, bh), 2, border_radius=10)
            surface.blit(bt, (bx + 7, by + (bh - bt.get_height()) // 2))

        # ===== Divisor vertical =====
        divider_x = rect.right - 300
        pygame.draw.line(surface, self.colors['divider'],
                         (divider_x, rect.y + 10),
                         (divider_x, rect.y + rect.height - 10), 2)

        # ===== Lado direito: recompensas =====
        reward_rect = pygame.Rect(divider_x + 12, rect.y + 8, 280, rect.height - 16)

        rtitle_f = self._get_font(15, True)
        rtitle = rtitle_f.render("RECOMPENSAS", True, self.colors['text_muted'])
        rtitle_x = reward_rect.x + (reward_rect.width - rtitle.get_width()) // 2
        surface.blit(rtitle, (rtitle_x, reward_rect.y))

        rbg = pygame.Rect(
            reward_rect.x + 5,
            reward_rect.y + 22,
            reward_rect.width - 10,
            reward_rect.height - 30,
        )
        pygame.draw.rect(surface, self.colors['reward_bg'], rbg, border_radius=6)
        pygame.draw.rect(surface, self.colors['reward_border'], rbg, 2, border_radius=6)

        rewards = achievement.rewards
        reward_y = rbg.y + 12
        center_x = rbg.x + (rbg.width - 10) // 2

        reward_texts = []

        if "gold" in rewards:
            reward_texts.append(
                self._get_font(20, True).render(f"$ {rewards['gold']}", True, (255, 215, 0))
            )
        if "xp" in rewards:
            reward_texts.append(
                self._get_font(20, True).render(f"XP +{rewards['xp']}", True, (100, 200, 255))
            )
        if "items" in rewards:
            for item_id, qty in rewards["items"].items():
                nm = self.item_catalog.get_item(item_id)["name"]
                reward_texts.append(
                    self._get_font(20, True).render(f"{qty}x {nm}", True, self.colors['reward_text'])
                )
        if "pokemon" in rewards:
            pid = rewards["pokemon"]
            nm = self.pokedex.get_name(pid)
            reward_texts.append(
                self._get_font(20, True).render(f"{nm} Lv.5", True, (255, 200, 150))
            )

        if reward_texts:
            # Se muitos textos, empilha em até 2 linhas
            spacing = 22
            total_w = sum(t.get_width() for t in reward_texts) + (len(reward_texts) - 1) * spacing
            if total_w <= rbg.width - 12:
                # Uma linha
                cx = center_x - total_w // 2
                for t in reward_texts:
                    surface.blit(t, (cx, reward_y))
                    cx += t.get_width() + spacing
                reward_y += reward_texts[0].get_height() + 14
            else:
                # Duas linhas (divide no meio)
                mid = (len(reward_texts) + 1) // 2
                for line_texts in (reward_texts[:mid], reward_texts[mid:]):
                    lw = sum(t.get_width() for t in line_texts) + (len(line_texts) - 1) * spacing
                    cx = center_x - lw // 2
                    for t in line_texts:
                        surface.blit(t, (cx, reward_y))
                        cx += t.get_width() + spacing
                    reward_y += line_texts[0].get_height() + 4
                reward_y += 10

        # Ícones
        if "items" in rewards:
            for item_id, qty in rewards["items"].items():
                icon_size = 52
                icon = self._get_item_icon(item_id, icon_size)
                if icon:
                    surface.blit(icon, (center_x - icon_size // 2, reward_y))
                    reward_y += icon_size + 10

        if "pokemon" in rewards:
            pid = rewards["pokemon"]
            psize = 68
            portrait = self._get_pokemon_portrait(pid, psize)
            if portrait:
                surface.blit(portrait, (center_x - psize // 2, reward_y))
                reward_y += psize + 10

    # ------------------------------------------------------------------
    # SCROLLBAR
    # ------------------------------------------------------------------
    def _render_scrollbar(self, screen, clip_rect):
        w = 10
        x = clip_rect.right + 5
        h = clip_rect.height

        bar = pygame.Rect(x, clip_rect.y, w, h)
        self._scroll_bar_area = bar
        pygame.draw.rect(screen, self.colors['scroll_bg'], bar, border_radius=5)
        pygame.draw.rect(screen, self.colors['border'], bar, 2, border_radius=5)

        if self.max_scroll > 0:
            visible_ratio = clip_rect.height / (self.max_scroll + clip_rect.height)
            thumb_h = max(35, int(h * visible_ratio))
            thumb_y = clip_rect.y + (self.scroll_offset / self.max_scroll) * (h - thumb_h)

            thumb = pygame.Rect(x + 2, thumb_y, w - 4, thumb_h)
            self._scroll_bar_rect = thumb

            color = self.colors['scroll_thumb_hover'] if self.dragging_scroll else self.colors['scroll_thumb']
            pygame.draw.rect(screen, color, thumb, border_radius=4)

            glow = thumb.inflate(-2, -2)
            pygame.draw.rect(screen, (100, 120, 180, 30), glow, border_radius=3)