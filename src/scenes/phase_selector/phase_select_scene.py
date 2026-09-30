# src/scenes/phase_selector/phase_select_scene.py

"""
Tela de selecao de fases - Layout reformulado com REGIOES
"""
import pygame
import math

from src.scenes.base_scene import BaseScene
from src.scenes.team_select_scene.team_select_scene import TeamSelectScene
from src.config.progress import progress_manager
from src.config.phase_catalog import phase_catalog
from src.config.global_settings import DEBUG_MODE
from src.scenes.incubator_scene.incubator_scene import IncubatorScene
from src.scenes.shop_scene.shop_scene import ShopScene
from src.scenes.pokedex_scene import PokedexScene
from src.scenes.achievement_scene.achievement_scene import AchievementScene
from src.managers.sounds.sound_manager import sound_manager, SoundEffect

from src.config.regions import (
    RegionCatalog, DEFAULT_REGION_ID, make_phase_id, parse_phase_id
)


# ======================================================================
# FASE CARD
# ======================================================================
class PhaseCard:
    def __init__(self, phase_data, unlocked=False, completed=False, mythical_id=None,
                 region_id=DEFAULT_REGION_ID):
        self.phase_data = phase_data
        self.phase_number = phase_data["number"]
        self.phase_name = phase_data.get("name", f"Fase {phase_data['number']}")
        self.chapter_id = phase_data["chapter"]
        self.region_id = region_id
        self.phase_id = make_phase_id(region_id, self.chapter_id, self.phase_number)

        self.unlocked = unlocked
        self.completed = completed
        self.mythical_id = mythical_id

        self.rect = pygame.Rect(0, 0, 0, 0)
        self.is_hovered = False
        self.scale = 1.0
        self.target_scale = 1.0
        self.glow_alpha = 0
        self.glow_direction = 1

        self._update_colors()

    def _update_colors(self):
        if not self.unlocked:
            self.bg_color = (30, 30, 35)
            self.border_color = (50, 50, 55)
            self.text_color = (80, 80, 85)
            self.name_color = (100, 100, 105)
            self.status_color = (80, 80, 85)
            self.status_text = "BLOQUEADA"
        elif self.completed:
            self.bg_color = (35, 50, 35)
            self.border_color = (70, 120, 70)
            self.text_color = (180, 220, 180)
            self.name_color = (200, 240, 200)
            self.status_color = (140, 200, 140)
            self.status_text = "CONCLUIDA"
        else:
            self.bg_color = (40, 45, 55)
            self.border_color = (80, 100, 140)
            self.text_color = (220, 220, 240)
            self.name_color = (200, 200, 220)
            self.status_color = (140, 140, 200)
            self.status_text = "DISPONIVEL"

    def update(self, dt):
        self.scale += (self.target_scale - self.scale) * 0.1
        if self.is_hovered and self.unlocked:
            self.glow_alpha += self.glow_direction * 3
            if self.glow_alpha >= 120:
                self.glow_alpha = 120
                self.glow_direction = -1
            elif self.glow_alpha <= 0:
                self.glow_alpha = 0
                self.glow_direction = 1
        else:
            self.glow_alpha = max(0, self.glow_alpha - 5)

    def update_position(self, x, y, width, height):
        self.rect = pygame.Rect(x, y, width, height)

    def handle_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            was = self.is_hovered
            self.is_hovered = self.rect.collidepoint(event.pos)
            if self.is_hovered and not was and self.unlocked:
                self.target_scale = 1.05
                sound_manager.play_effect(SoundEffect.CLICK)
            elif not self.is_hovered and was:
                self.target_scale = 1.0
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.is_hovered and self.unlocked:
                sound_manager.play_effect(SoundEffect.CLICK)
                self.target_scale = 0.95
                return self.phase_number
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self.is_hovered:
                self.target_scale = 1.05
        return None

    def render(self, screen, font_large, font_small, font_name):
        scaled_rect = self.rect.copy()
        if self.scale != 1.0:
            wo = (self.rect.width * (self.scale - 1)) // 2
            ho = (self.rect.height * (self.scale - 1)) // 2
            scaled_rect = self.rect.inflate(wo * 2, ho * 2)
            scaled_rect.center = self.rect.center

        shadow = scaled_rect.copy()
        shadow.x += 4
        shadow.y += 4
        pygame.draw.rect(screen, (10, 10, 15), shadow, border_radius=12)

        if self.is_hovered and self.unlocked:
            color = tuple(min(255, c + 20) for c in self.bg_color)
            border = tuple(min(255, c + 30) for c in self.border_color)
            name_color = tuple(min(255, c + 40) for c in self.name_color)
        else:
            color = self.bg_color
            border = self.border_color
            name_color = self.name_color

        pygame.draw.rect(screen, color, scaled_rect, border_radius=12)
        pygame.draw.rect(screen, border, scaled_rect, 2, border_radius=12)

        if self.is_hovered and self.unlocked and self.glow_alpha > 0:
            glow = pygame.Surface((scaled_rect.width, scaled_rect.height), pygame.SRCALPHA)
            pygame.draw.rect(glow, (*border[:3], self.glow_alpha),
                             glow.get_rect(), border_radius=12)
            screen.blit(glow, scaled_rect)

        # Número
        num = font_small.render(f"{self.phase_id}", True, self.text_color)
        screen.blit(num, (scaled_rect.x + 10, scaled_rect.y + 10))

        # Nome
        self._render_wrapped_text(screen, self.phase_name, font_name, name_color,
                                  scaled_rect.centerx, scaled_rect.centery - 12)

        # Status
        status = font_small.render(self.status_text, True, self.status_color)
        sr = status.get_rect(center=(scaled_rect.centerx, scaled_rect.centery + 28))
        screen.blit(status, sr)

        if self.mythical_id is not None and self.unlocked:
            self._render_mythical_icon(screen, scaled_rect)

        if not self.unlocked:
            ov = pygame.Surface((scaled_rect.width, scaled_rect.height), pygame.SRCALPHA)
            ov.fill((0, 0, 0, 160))
            screen.blit(ov, scaled_rect)

    def _render_mythical_icon(self, screen, scaled_rect):
        try:
            from src.data.pokedex import Pokedex
            portrait = Pokedex().get_portrait(self.mythical_id, "happy", False)
            if portrait is None:
                return
            size = 34
            portrait_scaled = pygame.transform.scale(portrait, (size, size))
            icon_x = scaled_rect.centerx - size // 2
            icon_y = scaled_rect.top + 6

            pulse = int(80 + 40 * (0.5 + 0.5 * math.sin(pygame.time.get_ticks() * 0.005)))
            bg_rect = pygame.Rect(icon_x - 4, icon_y - 4, size + 8, size + 8)
            bg = pygame.Surface((bg_rect.width, bg_rect.height), pygame.SRCALPHA)
            bg.fill((255, 215, 0, pulse))
            screen.blit(bg, bg_rect)
            pygame.draw.rect(screen, (255, 215, 0), bg_rect, 2, border_radius=6)
            screen.blit(portrait_scaled, (icon_x, icon_y))
        except Exception as e:
            print(f"[MYTHICAL] {e}")

    def _render_wrapped_text(self, screen, text, font, color, cx, cy):
        words = text.split()
        if not words:
            return
        single = font.render(text, True, color)
        if single.get_width() <= self.rect.width - 30:
            screen.blit(single, single.get_rect(center=(cx, cy)))
            return
        if len(words) == 1:
            while words[0] and font.size(words[0] + "...")[0] > self.rect.width - 30:
                words[0] = words[0][:-1]
            t = font.render(words[0] + "...", True, color)
            screen.blit(t, t.get_rect(center=(cx, cy)))
            return
        mid = len(words) // 2
        l1 = " ".join(words[:mid])
        l2 = " ".join(words[mid:])
        while l1 and font.size(l1)[0] > self.rect.width - 30:
            l1 = l1[:-1]
        while l2 and font.size(l2)[0] > self.rect.width - 30:
            l2 = l2[:-1]
        if l1:
            s1 = font.render(l1, True, color)
            screen.blit(s1, s1.get_rect(center=(cx, cy - 10)))
        if l2:
            s2 = font.render(l2, True, color)
            screen.blit(s2, s2.get_rect(center=(cx, cy + 10)))


# ======================================================================
# CHAPTER TAB
# ======================================================================
class ChapterTab:
    def __init__(self, chapter_id, name, progress):
        self.chapter_id = chapter_id
        self.name = name
        self.progress = progress
        self.rect = pygame.Rect(0, 0, 0, 0)
        self.is_hovered = False
        self.active = False
        self.scale = 1.0
        self.target_scale = 1.0

    def update(self, dt):
        self.scale += (self.target_scale - self.scale) * 0.1

    def update_position(self, x, y, w, h):
        self.rect = pygame.Rect(x, y, w, h)

    def handle_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            was = self.is_hovered
            self.is_hovered = self.rect.collidepoint(event.pos)
            if self.is_hovered and not was:
                self.target_scale = 1.05
                sound_manager.play_effect(SoundEffect.CLICK)
            elif not self.is_hovered and was:
                self.target_scale = 1.0
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.is_hovered:
                sound_manager.play_effect(SoundEffect.CLICK)
                self.target_scale = 0.95
                return self.chapter_id
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self.is_hovered:
                self.target_scale = 1.05
        return None

    def render(self, screen, font):
        scaled = self.rect.copy()
        if self.scale != 1.0:
            wo = (self.rect.width * (self.scale - 1)) // 2
            ho = (self.rect.height * (self.scale - 1)) // 2
            scaled = self.rect.inflate(wo * 2, ho * 2)
            scaled.center = self.rect.center

        if self.active:
            color, border, text_color = (55, 55, 70), (140, 140, 170), (255, 255, 255)
        elif self.is_hovered:
            color, border, text_color = (50, 50, 60), (110, 110, 140), (230, 230, 240)
        else:
            color, border, text_color = (35, 35, 42), (60, 60, 75), (160, 160, 180)

        sh = scaled.copy(); sh.y += 3
        pygame.draw.rect(screen, (10, 10, 15), sh, border_radius=8)
        pygame.draw.rect(screen, color, scaled, border_radius=8)
        pygame.draw.rect(screen, border, scaled, 2, border_radius=8)

        text = font.render(self.name, True, text_color)
        screen.blit(text, text.get_rect(center=(scaled.centerx, scaled.centery - 8)))
        pt = font.render(f"{self.progress['completed']}/{self.progress['total']}",
                         True, text_color)
        screen.blit(pt, pt.get_rect(center=(scaled.centerx, scaled.centery + 14)))

        if self.active and self.progress['total'] > 0:
            bw = scaled.width - 20
            bh = 3
            bx = scaled.x + 10
            by = scaled.bottom - 8
            pygame.draw.rect(screen, (30, 30, 40), (bx, by, bw, bh), border_radius=2)
            ratio = self.progress['completed'] / self.progress['total']
            if ratio > 0:
                c = (100, 180, 100) if ratio >= 1 else (80, 120, 200)
                pygame.draw.rect(screen, c, (bx, by, int(bw * ratio), bh), border_radius=2)


# ======================================================================
# REGION TAB
# ======================================================================
class RegionTab:
    def __init__(self, region_id, name):
        self.region_id = region_id
        self.name = name
        self.rect = pygame.Rect(0, 0, 0, 0)
        self.is_hovered = False
        self.active = False
        self.scale = 1.0
        self.target_scale = 1.0

    def update(self, dt):
        self.scale += (self.target_scale - self.scale) * 0.1

    def update_position(self, x, y, w, h):
        self.rect = pygame.Rect(x, y, w, h)

    def handle_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            was = self.is_hovered
            self.is_hovered = self.rect.collidepoint(event.pos)
            if self.is_hovered and not was:
                self.target_scale = 1.05
            elif not self.is_hovered and was:
                self.target_scale = 1.0
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.is_hovered:
                return self.region_id
        return None

    def render(self, screen, font):
        scaled = self.rect.copy()
        if self.scale != 1.0:
            wo = (self.rect.width * (self.scale - 1)) // 2
            ho = (self.rect.height * (self.scale - 1)) // 2
            scaled = self.rect.inflate(wo * 2, ho * 2)
            scaled.center = self.rect.center

        if self.active:
            color, border, text_color = (70, 90, 140), (140, 180, 240), (255, 255, 255)
        elif self.is_hovered:
            color, border, text_color = (55, 60, 80), (110, 130, 170), (230, 230, 240)
        else:
            color, border, text_color = (40, 42, 58), (70, 75, 100), (180, 185, 210)

        sh = scaled.copy(); sh.y += 2
        pygame.draw.rect(screen, (10, 10, 15), sh, border_radius=8)
        pygame.draw.rect(screen, color, scaled, border_radius=8)
        pygame.draw.rect(screen, border, scaled, 2, border_radius=8)

        text = font.render(self.name.upper(), True, text_color)
        screen.blit(text, text.get_rect(center=scaled.center))


# ======================================================================
# SCENE
# ======================================================================
class PhaseSelectScene(BaseScene):

    def __init__(self, game):
        super().__init__(game)

        self.progress = progress_manager
        self.catalog = phase_catalog
        self._phase_name_cache = {}

        # ===== REGIÕES =====
        self.available_regions = []
        self.current_region_id = DEFAULT_REGION_ID
        self.region_tabs = []

        # Estado do player
        if hasattr(game, 'player') and game.player:
            saved_region = getattr(game.player, 'current_region', DEFAULT_REGION_ID)
            self.current_region_id = saved_region

        # Elementos UI
        self.chapter_tabs = []
        self.phase_cards = []

        # Botões
        self.back_button_rect = None
        self.shop_button_rect = None
        self.minigame_button_rect = None
        self.pokedex_button_rect = None
        self.achievement_button_rect = None
        self.incubator_button_rect = None
        self.profile_button_rect = None
        self.npc_hall_button_rect = None

        # Hover states
        self.back_button_hovered = False
        self.shop_button_hovered = False
        self.minigame_button_hovered = False
        self.pokedex_button_hovered = False
        self.achievement_button_hovered = False
        self.incubator_button_hovered = False
        self.profile_button_hovered = False
        self.npc_hall_button_hovered = False

        # Scroll
        self.scroll_y = 0
        self.scroll_target = 0
        self.max_scroll = 0
        self.dragging_scroll = False
        self.last_mouse_y = 0

        # Estado
        self.layout_initialized = False
        self.last_window_size = (self.screen_manager.window_width,
                                 self.screen_manager.window_height)
        self.dev_mode = DEBUG_MODE
        self._animation_timer = 0
        self._music_started = False

        # Fontes
        self.title_font = pygame.font.Font(None, 52)
        self.tab_font = pygame.font.Font(None, 20)
        self.phase_font_large = pygame.font.Font(None, 34)
        self.phase_font_small = pygame.font.Font(None, 15)
        self.phase_font_name = pygame.font.Font(None, 17)
        self.button_font = pygame.font.Font(None, 22)

        # Capítulo atual
        self.current_chapter_id = 1
        self.available_chapters = [1]

        self.refresh_data()
        self._start_phase_select_music()

    # ======================================================================
    # DESCOBERTA DE DADOS
    # ======================================================================
    def _discover_regions(self):
        regions = []
        # Tenta via catálogo
        try:
            regions = self.catalog.get_all_regions()
        except (AttributeError, TypeError):
            regions = []
        if not regions:
            # Fallback via exporter
            try:
                from src.editor.phase_exporter import phase_exporter
                regions = phase_exporter.list_regions_with_phases()
            except Exception:
                regions = []
        if not regions:
            regions = [DEFAULT_REGION_ID]
        return sorted(set(int(r) for r in regions))

    def _discover_chapters(self, region_id):
        chapters = []
        try:
            all_phases = self.catalog.get_all_phases(region_id)
            if all_phases:
                chapters = sorted(int(c) for c in all_phases.keys())
        except (TypeError, AttributeError):
            chapters = []
        if not chapters:
            try:
                from src.editor.phase_exporter import phase_exporter
                # list_phases(region=X) retorna [(chapter, phase), ...]
                phases = phase_exporter.list_phases(region=region_id)
                chapters = sorted({int(c) for (c, p) in phases})
            except Exception:
                chapters = []
        if not chapters:
            chapters = [1]
        return chapters

    def _get_chapter_phases(self, region_id, chapter_id):
        """Retorna [(chapter, phase_num), ...] e nomes via cache."""
        # Tenta catálogo novo
        try:
            phases = self.catalog.get_chapter_phases(region_id, chapter_id)
            if phases:
                # espera lista de dicts com 'number' e 'name'
                if isinstance(phases[0], dict):
                    return phases
        except (TypeError, AttributeError):
            pass

        # Fallback: tenta catálogo antigo
        try:
            phases = self.catalog.get_chapter_phases(chapter_id)
            if phases:
                if isinstance(phases[0], dict):
                    # se for lista de dicts, retorna como está (assume formato consistente)
                    result = []
                    for p in phases:
                        result.append({
                            "number": p.get("number", 1),
                            "name": p.get("name", f"Fase {p.get('number', 1)}"),
                            "chapter": chapter_id,
                        })
                    return result
        except (TypeError, AttributeError):
            pass

        # Fallback final: exporter
        try:
            from src.editor.phase_exporter import phase_exporter
            phase_nums = phase_exporter.list_phases(region=region_id, chapter=chapter_id)
            result = []
            for p_num in phase_nums:
                name = self._get_phase_name_from_disk(region_id, chapter_id, p_num)
                result.append({
                    "number": p_num,
                    "name": name,
                    "chapter": chapter_id,
                })
            return result
        except Exception:
            return []

    def _get_phase_name_from_disk(self, region_id, chapter_id, phase_num):
        key = (region_id, chapter_id, phase_num)
        if key in self._phase_name_cache:
            return self._phase_name_cache[key]

        name = f"Fase {chapter_id}-{phase_num}"
        try:
            from src.editor.phase_exporter import phase_exporter
            data = phase_exporter.load_phase(chapter_id, phase_num, region=region_id)
            if data and data.get("name"):
                name = data["name"]
        except Exception:
            pass

        self._phase_name_cache[key] = name
        return name

    def _get_chapter_progress(self, region_id, chapter_id, phase_ids):
        """Retorna {'completed': n, 'total': n}."""
        completed = 0
        for pid in phase_ids:
            try:
                if self.progress.is_phase_completed(pid):
                    completed += 1
            except Exception:
                pass
        return {"completed": completed, "total": len(phase_ids)}

    # ======================================================================
    # REFRESH
    # ======================================================================
    def refresh_data(self):
        try:
            self.progress.reload_progress()
        except Exception:
            pass
        try:
            self.catalog.refresh()
        except Exception:
            pass

        # Regiões
        self.available_regions = self._discover_regions()

        # Região inicial
        if hasattr(self.game, 'player') and self.game.player:
            saved = getattr(self.game.player, 'current_region', DEFAULT_REGION_ID)
            if saved in self.available_regions:
                self.current_region_id = saved
            else:
                self.current_region_id = self.available_regions[0]
        else:
            self.current_region_id = self.available_regions[0]

        # Capítulos da região atual
        self.available_chapters = self._discover_chapters(self.current_region_id)

        # Capítulo inicial
        if self.available_chapters:
            self.current_chapter_id = self.available_chapters[0]
        else:
            self.current_chapter_id = 1

        self.layout_initialized = False

    def _check_resize(self):
        cur = (self.screen_manager.window_width, self.screen_manager.window_height)
        if cur != self.last_window_size:
            self.last_window_size = cur
            self.layout_initialized = False
            return True
        return False

    # ======================================================================
    # LAYOUT
    # ======================================================================
    def _create_layout(self):
        vx = self.screen_manager.viewport_x
        vy = self.screen_manager.viewport_y
        vw = self.screen_manager.viewport_width
        vh = self.screen_manager.viewport_height

        # Voltar
        bs = int(min(vw * 0.045, vh * 0.065, 40))
        self.back_button_rect = pygame.Rect(vx + 20, vy + 20, bs, bs)

        # Botões inferiores
        bw = int(vw * 0.09)
        bh = int(vh * 0.055)
        bsp = int(vw * 0.010)
        total = bw * 7 + bsp * 6
        sx = vx + (vw - total) // 2
        by = vy + vh - bh - int(vh * 0.06)

        self.shop_button_rect = pygame.Rect(sx, by, bw, bh)
        self.npc_hall_button_rect = pygame.Rect(sx + (bw + bsp), by, bw, bh)
        self.minigame_button_rect = pygame.Rect(sx + (bw + bsp) * 2, by, bw, bh)
        self.pokedex_button_rect = pygame.Rect(sx + (bw + bsp) * 3, by, bw, bh)
        self.achievement_button_rect = pygame.Rect(sx + (bw + bsp) * 4, by, bw, bh)
        self.incubator_button_rect = pygame.Rect(sx + (bw + bsp) * 5, by, bw, bh)
        self.profile_button_rect = pygame.Rect(sx + (bw + bsp) * 6, by, bw, bh)

        # ===== ABAS DE REGIÃO =====
        region_tab_w = int(vw * 0.11)
        region_tab_h = int(vh * 0.055)
        region_tab_sp = int(vw * 0.010)
        total_rw = len(self.available_regions) * (region_tab_w + region_tab_sp) - region_tab_sp
        region_start_x = vx + (vw - total_rw) // 2
        region_y = vy + int(vh * 0.045)

        self.region_tabs = []
        for i, rid in enumerate(self.available_regions):
            rx = region_start_x + i * (region_tab_w + region_tab_sp)
            tab = RegionTab(rid, RegionCatalog.get_name(rid))
            tab.update_position(rx, region_y, region_tab_w, region_tab_h)
            tab.active = (rid == self.current_region_id)
            self.region_tabs.append(tab)

        # ===== ABAS DE CAPÍTULO =====
        if self.available_chapters:
            tab_w = int(vw * 0.10)
            tab_h = int(vh * 0.075)
            tab_sp = int(vw * 0.012)
            total_tw = len(self.available_chapters) * (tab_w + tab_sp) - tab_sp
            tab_start_x = vx + (vw - total_tw) // 2
            tab_y = vy + int(vh * 0.045) + region_tab_h + int(vh * 0.015)

            self.chapter_tabs = []
            for i, ch_id in enumerate(self.available_chapters):
                tx = tab_start_x + i * (tab_w + tab_sp)
                phases_data = self._get_chapter_phases(self.current_region_id, ch_id)
                phase_ids = [make_phase_id(self.current_region_id, ch_id, p["number"])
                             for p in phases_data]
                prog = self._get_chapter_progress(self.current_region_id, ch_id, phase_ids)

                tab = ChapterTab(ch_id, f"CAP {ch_id}", prog)
                tab.update_position(tx, tab_y, tab_w, tab_h)
                tab.active = (ch_id == self.current_chapter_id)
                self.chapter_tabs.append(tab)

        self._create_phase_cards()

        if hasattr(self.game, 'player') and self.game.player:
            self.game.player.chapter_page_num = self.current_chapter_id
            self.game.player.current_region = self.current_region_id

        self.layout_initialized = True
        self.scroll_y = 0
        self.scroll_target = 0

    def _create_phase_cards(self):
        vx = self.screen_manager.viewport_x
        vy = self.screen_manager.viewport_y
        vw = self.screen_manager.viewport_width
        vh = self.screen_manager.viewport_height

        phases = self._get_chapter_phases(self.current_region_id, self.current_chapter_id)
        if not phases:
            self.phase_cards = []
            self.max_scroll = 0
            return

        card_base_w = int(vw * 0.10)
        card_margin = int(vw * 0.015)
        avail_w = vw - int(vw * 0.08)
        cols = max(2, min(5, avail_w // (card_base_w + card_margin)))
        card_w = (avail_w - (cols - 1) * card_margin) // cols
        card_w = max(int(vw * 0.07), min(int(vw * 0.12), card_w))
        card_h = int(card_w * 1.25)

        region_tab_h = int(vh * 0.055) if self.region_tabs else 0
        tab_h = int(vh * 0.075) if self.chapter_tabs else 0
        grid_start_y = vy + int(vh * 0.20) + region_tab_h + tab_h

        grid_w = cols * card_w + (cols - 1) * card_margin
        grid_start_x = vx + (vw - grid_w) // 2

        rows = math.ceil(len(phases) / cols)
        grid_h = rows * (card_h + card_margin)
        visible_h = vh - (grid_start_y - vy) - int(vh * 0.15)
        self.max_scroll = max(0, grid_h - visible_h)

        # Mítico
        from src.data.mythical_catalog import MythicalCatalog
        pending_mythical_entry = None
        if hasattr(self.game, 'player') and self.game.player:
            pending_id = getattr(self.game.player, 'pending_mythical_id', None)
            if pending_id is not None:
                pending_mythical_entry = MythicalCatalog.get_mythical(pending_id)

        self.phase_cards = []
        for i, phase_data in enumerate(phases):
            row = i // cols
            col = i % cols
            card_x = grid_start_x + col * (card_w + card_margin)
            card_y = grid_start_y + row * (card_h + card_margin) - self.scroll_y

            phase_id = make_phase_id(self.current_region_id, self.current_chapter_id,
                                     phase_data["number"])
            try:
                unlocked = self.progress.is_phase_unlocked(phase_id)
                completed = self.progress.is_phase_completed(phase_id)
            except Exception:
                unlocked = False
                completed = False

            mythical_id_for_card = None
            if pending_mythical_entry:
                # Simplificação: mostra em todas as fases da região do mítico
                if phase_id in pending_mythical_entry.phases:
                    mythical_id_for_card = pending_mythical_entry.pokemon_id

            card = PhaseCard(
                phase_data, unlocked, completed,
                mythical_id=mythical_id_for_card,
                region_id=self.current_region_id,
            )
            card.update_position(card_x, card_y, card_w, card_h)
            self.phase_cards.append(card)

    def _is_incubator_unlocked(self):
        try:
            return self.progress.is_phase_completed(make_phase_id(DEFAULT_REGION_ID, 1, 5))
        except Exception:
            try:
                return self.progress.is_phase_completed("1-5")
            except Exception:
                return False

    # ======================================================================
    # EVENTOS
    # ======================================================================
    def handle_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            self._update_hover_states(event.pos)

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_p:
                self.toggle_pause()
            elif event.key == pygame.K_ESCAPE:
                sound_manager.play_effect(SoundEffect.CLICK)
                sound_manager.stop_music(fade_ms=300)
                self.game.current_scene = self.game.menu_scene
            elif event.key == pygame.K_LEFT:
                self._prev_region()
            elif event.key == pygame.K_RIGHT:
                self._next_region()
            elif event.key == pygame.K_r and pygame.key.get_mods() & pygame.KMOD_CTRL:
                if DEBUG_MODE:
                    self._reset_progress()
            elif event.key == pygame.K_u:
                if DEBUG_MODE:
                    self._debug_unlock_next()
            elif event.key == pygame.K_a:
                if DEBUG_MODE:
                    self._debug_unlock_all()
            elif event.key == pygame.K_s:
                self._open_shop()
            elif event.key == pygame.K_m:
                self._open_minigames()
            elif event.key == pygame.K_x:
                self._open_pokedex()
            elif event.key == pygame.K_c:
                self._open_achievements()
            elif event.key == pygame.K_i:
                self._open_incubator()
            elif event.key == pygame.K_v:
                self._open_profile()

        elif event.type == pygame.VIDEORESIZE:
            self.layout_initialized = False

        elif event.type == pygame.MOUSEWHEEL:
            if self.phase_cards and self.max_scroll > 0:
                self.scroll_target += event.y * -30
                self.scroll_target = max(0, min(self.max_scroll, self.scroll_target))

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self._handle_click(event.pos)

        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.dragging_scroll = False

        if event.type == pygame.MOUSEMOTION:
            for card in self.phase_cards:
                card.handle_event(event)
            for tab in self.chapter_tabs:
                tab.handle_event(event)
            for rt in self.region_tabs:
                rt.handle_event(event)

            if self.dragging_scroll:
                dy = event.pos[1] - self.last_mouse_y
                speed = self.max_scroll / max(1, (self.screen_manager.viewport_height - 200))
                self.scroll_target += dy * speed * 1.5
                self.scroll_target = max(0, min(self.max_scroll, self.scroll_target))
                self.last_mouse_y = event.pos[1]

    def _update_hover_states(self, pos):
        def chk(r):
            return r.collidepoint(pos) if r else False
        self.back_button_hovered = chk(self.back_button_rect)
        self.shop_button_hovered = chk(self.shop_button_rect)
        self.minigame_button_hovered = chk(self.minigame_button_rect)
        self.pokedex_button_hovered = chk(self.pokedex_button_rect)
        self.achievement_button_hovered = chk(self.achievement_button_rect)
        self.incubator_button_hovered = chk(self.incubator_button_rect)
        self.profile_button_hovered = chk(self.profile_button_rect)
        self.npc_hall_button_hovered = chk(self.npc_hall_button_rect)

    def _handle_click(self, pos):
        if self.back_button_rect and self.back_button_rect.collidepoint(pos):
            sound_manager.play_effect(SoundEffect.CLICK)
            sound_manager.stop_music(fade_ms=300)
            self.game.current_scene = self.game.menu_scene
            return

        if self.shop_button_rect and self.shop_button_rect.collidepoint(pos):
            self._open_shop(); return
        if self.minigame_button_rect and self.minigame_button_rect.collidepoint(pos):
            self._open_minigames(); return
        if self.pokedex_button_rect and self.pokedex_button_rect.collidepoint(pos):
            self._open_pokedex(); return
        if self.achievement_button_rect and self.achievement_button_rect.collidepoint(pos):
            self._open_achievements(); return
        if self.incubator_button_rect and self.incubator_button_rect.collidepoint(pos):
            if self._is_incubator_unlocked():
                self._open_incubator()
            return
        if self.profile_button_rect and self.profile_button_rect.collidepoint(pos):
            self._open_profile(); return
        if self.npc_hall_button_rect and self.npc_hall_button_rect.collidepoint(pos):
            self._open_npc_hall(); return

        # Regiões
        for rt in self.region_tabs:
            res = rt.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=pos))
            if res:
                self._change_region(res)
                return

        # Capítulos
        for tab in self.chapter_tabs:
            res = tab.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=pos))
            if res:
                self.current_chapter_id = res
                if hasattr(self.game, 'player') and self.game.player:
                    self.game.player.chapter_page_num = self.current_chapter_id
                self._create_phase_cards()
                for t in self.chapter_tabs:
                    t.active = (t.chapter_id == self.current_chapter_id)
                return

        # Scroll bar
        if self.phase_cards and self.max_scroll > 0:
            sb = self._get_scroll_bar_rect()
            if sb and sb.collidepoint(pos):
                self.dragging_scroll = True
                self.last_mouse_y = pos[1]
                return

        # Cards
        for card in self.phase_cards:
            res = card.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=pos))
            if res:
                self.start_phase(res)
                return

    # ======================================================================
    # NAVEGAÇÃO
    # ======================================================================
    def _change_region(self, region_id):
        if region_id == self.current_region_id:
            return
        self.current_region_id = region_id
        if hasattr(self.game, 'player') and self.game.player:
            self.game.player.current_region = region_id

        self.available_chapters = self._discover_chapters(region_id)
        self.current_chapter_id = self.available_chapters[0] if self.available_chapters else 1

        # Recria abas de capítulo + cards
        self._create_layout()

    def _prev_region(self):
        if not self.available_regions:
            return
        try:
            idx = self.available_regions.index(self.current_region_id)
            if idx > 0:
                self._change_region(self.available_regions[idx - 1])
        except ValueError:
            pass

    def _next_region(self):
        if not self.available_regions:
            return
        try:
            idx = self.available_regions.index(self.current_region_id)
            if idx < len(self.available_regions) - 1:
                self._change_region(self.available_regions[idx + 1])
        except ValueError:
            pass

    def _reset_progress(self):
        if not DEBUG_MODE:
            return
        try:
            self.progress.reset_progress()
            self.catalog.refresh()
        except Exception:
            pass
        self.refresh_data()

    def _open_shop(self):
        sound_manager.play_effect(SoundEffect.CLICK)
        self.game.shop_scene = ShopScene(self.game)
        self.game.shop_scene.on_close_callback = self._on_shop_closed
        self.game.current_scene = self.game.shop_scene

    def _open_npc_hall(self):
        sound_manager.play_effect(SoundEffect.CLICK)
        from src.scenes.npc_hall_scene.npc_hall_scene import NpcHallScene
        self.game.current_scene = NpcHallScene(self.game)

    def _open_minigames(self):
        sound_manager.play_effect(SoundEffect.CLICK)
        from src.scenes.minigame_select_scene.minigame_select_scene import MinigameSelectScene
        self.game.current_scene = MinigameSelectScene(self.game)

    def _open_pokedex(self):
        sound_manager.play_effect(SoundEffect.CLICK)
        self.game.pokedex_scene = PokedexScene(self.game)
        self.game.current_scene = self.game.pokedex_scene

    def _open_achievements(self):
        sound_manager.play_effect(SoundEffect.CLICK)
        self.game.achievement_scene = AchievementScene(self.game)
        self.game.current_scene = self.game.achievement_scene

    def _open_incubator(self):
        sound_manager.play_effect(SoundEffect.CLICK)
        self.game.incubator_scene = IncubatorScene(self.game)
        self.game.current_scene = self.game.incubator_scene

    def _open_profile(self):
        sound_manager.play_effect(SoundEffect.CLICK)
        from src.scenes.profile_scene.profile_scene import ProfileScene
        sound_manager.stop_music(fade_ms=300)
        self.game.current_scene = ProfileScene(self.game, return_scene="phase_select")

    def _on_shop_closed(self):
        self.layout_initialized = False

    def start_phase(self, phase_number):
        sound_manager.play_effect(SoundEffect.CLICK)
        sound_manager.stop_music(fade_ms=300)

        try:
            ts = TeamSelectScene(
                self.game, self.current_chapter_id, phase_number,
                region_id=self.current_region_id,
            )
        except TypeError:
            # Fallback para assinatura antiga
            ts = TeamSelectScene(self.game, self.current_chapter_id, phase_number)

        self.game.team_select_scene = ts
        self.game.current_scene = ts

    # ======================================================================
    # DEBUG
    # ======================================================================
    def _debug_unlock_next(self):
        if not DEBUG_MODE or not self.phase_cards:
            return
        for card in self.phase_cards:
            if not card.unlocked:
                try:
                    self.progress.unlock_specific_phase(card.phase_id)
                except Exception:
                    pass
                self._create_phase_cards()
                return

    def _debug_unlock_all(self):
        if not DEBUG_MODE:
            return
        for rt in self.region_tabs:
            chapters = self._discover_chapters(rt.region_id)
            for ch in chapters:
                phases = self._get_chapter_phases(rt.region_id, ch)
                for p in phases:
                    pid = make_phase_id(rt.region_id, ch, p["number"])
                    try:
                        self.progress.unlock_specific_phase(pid)
                    except Exception:
                        pass
        self._create_phase_cards()

    # ======================================================================
    # UPDATE
    # ======================================================================
    def fixed_update(self, dt):
        if self.paused:
            return
        self._animation_timer += dt

        if abs(self.scroll_y - self.scroll_target) > 0.1:
            self.scroll_y += (self.scroll_target - self.scroll_y) * min(1, dt * 10)
            if self.phase_cards:
                self._update_cards_position()

        for card in self.phase_cards:
            card.update(dt)
        for tab in self.chapter_tabs:
            tab.update(dt)
        for rt in self.region_tabs:
            rt.update(dt)

    def _update_cards_position(self):
        vx = self.screen_manager.viewport_x
        vy = self.screen_manager.viewport_y
        vw = self.screen_manager.viewport_width
        vh = self.screen_manager.viewport_height

        phases = self._get_chapter_phases(self.current_region_id, self.current_chapter_id)
        if not phases or not self.phase_cards:
            return

        card_base_w = int(vw * 0.10)
        card_margin = int(vw * 0.015)
        avail_w = vw - int(vw * 0.08)
        cols = max(2, min(5, avail_w // (card_base_w + card_margin)))
        card_w = (avail_w - (cols - 1) * card_margin) // cols
        card_w = max(int(vw * 0.07), min(int(vw * 0.12), card_w))
        card_h = int(card_w * 1.25)

        region_tab_h = int(vh * 0.055) if self.region_tabs else 0
        tab_h = int(vh * 0.075) if self.chapter_tabs else 0
        grid_start_y = vy + int(vh * 0.20) + region_tab_h + tab_h
        grid_w = cols * card_w + (cols - 1) * card_margin
        grid_start_x = vx + (vw - grid_w) // 2

        for i, card in enumerate(self.phase_cards):
            row = i // cols
            col = i % cols
            card.rect.x = grid_start_x + col * (card_w + card_margin)
            card.rect.y = grid_start_y + row * (card_h + card_margin) - self.scroll_y

    # ======================================================================
    # RENDER
    # ======================================================================
    def render(self, screen):
        self._check_resize()
        self._draw_gradient_background(screen)

        if not self.layout_initialized:
            self._create_layout()

        vx = self.screen_manager.viewport_x
        vy = self.screen_manager.viewport_y
        vw = self.screen_manager.viewport_width
        vh = self.screen_manager.viewport_height

        # Título
        title = self.title_font.render("SELECIONAR FASE", True, (255, 255, 255))
        tsh = self.title_font.render("SELECIONAR FASE", True, (30, 30, 45))
        tx = vx + (vw - title.get_width()) // 2
        ty = vy + 15
        screen.blit(tsh, (tx + 2, ty + 2))
        screen.blit(title, (tx, ty))

        # Linha
        bw = int(vw * 0.15)
        bx = vx + (vw - bw) // 2
        by = ty + title.get_height() + 6
        pygame.draw.rect(screen, (100, 85, 55), (bx, by, bw, 3), border_radius=2)

        # Botão voltar
        self._render_button(screen, self.back_button_rect, "<", self.back_button_hovered)

        # Botões inferiores
        self._render_bottom_button(screen, self.shop_button_rect, "LOJA", self.shop_button_hovered)
        self._render_bottom_button(screen, self.minigame_button_rect, "MINIGAMES", self.minigame_button_hovered)
        self._render_bottom_button(screen, self.pokedex_button_rect, "POKEDEX", self.pokedex_button_hovered)
        self._render_bottom_button(screen, self.achievement_button_rect, "CONQUISTAS", self.achievement_button_hovered)
        self._render_bottom_button(screen, self.incubator_button_rect, "INCUBADORA", self.incubator_button_hovered, not self._is_incubator_unlocked())
        self._render_bottom_button(screen, self.profile_button_rect, "PERFIL", self.profile_button_hovered)
        self._render_bottom_button(screen, self.npc_hall_button_rect, "NPC HALL", self.npc_hall_button_hovered)

        # Abas de região
        for rt in self.region_tabs:
            rt.render(screen, self.tab_font)

        # Abas de capítulo
        for tab in self.chapter_tabs:
            tab.render(screen, self.tab_font)

        # Linha divisória
        if self.chapter_tabs:
            line_y = self.chapter_tabs[0].rect.bottom + 12
            line_w = int(vw * 0.3)
            line_x = vx + (vw - line_w) // 2
            pygame.draw.line(screen, (70, 70, 80),
                             (line_x, line_y), (line_x + line_w, line_y), 1)

            phases = self._get_chapter_phases(self.current_region_id, self.current_chapter_id)
            if phases:
                rname = RegionCatalog.get_name(self.current_region_id)
                total_text = f"{rname} - {len(phases)} fases disponiveis"
                total_s = self.tab_font.render(total_text, True, (180, 180, 190))
                total_x = vx + (vw - total_s.get_width()) // 2
                total_y = line_y + 8
                screen.blit(total_s, (total_x, total_y))

                l2_y = total_y + 20
                pygame.draw.line(screen, (70, 70, 80),
                                 (line_x, l2_y), (line_x + line_w, l2_y), 1)

        # Cards (clipping)
        region_tab_h = int(vh * 0.055) if self.region_tabs else 0
        tab_h = int(vh * 0.075) if self.chapter_tabs else 0
        clip_rect = pygame.Rect(
            vx,
            vy + int(vh * 0.20) + region_tab_h + tab_h,
            vw,
            vh - int(vh * 0.20) - region_tab_h - tab_h - int(vh * 0.12)
        )

        old_clip = screen.get_clip()
        screen.set_clip(clip_rect)
        for card in self.phase_cards:
            if card.rect.bottom > clip_rect.top and card.rect.top < clip_rect.bottom:
                card.render(screen, self.phase_font_large, self.phase_font_small, self.phase_font_name)
        screen.set_clip(old_clip)

        # Scrollbar
        if self.max_scroll > 0:
            self._render_scroll_bar(screen)

        # Instruções
        font_small = pygame.font.Font(None, 16)
        inst_text = "SETAS TROCAM REGIAO | CLIQUE NA FASE | ESC VOLTAR"
        if DEBUG_MODE:
            inst_text += " | [U] proxima | [A] todas"
        inst = font_small.render(inst_text, True, (100, 100, 120))
        ix = vx + (vw - inst.get_width()) // 2
        iy = vy + vh - 18
        screen.blit(inst, (ix, iy))

        if DEBUG_MODE:
            dbg = font_small.render("CTRL+R resetar progresso", True, (60, 60, 70))
            screen.blit(dbg, (vx + 15, vy + vh - 40))

        if self.paused:
            self._render_pause_overlay(screen)

    def _render_button(self, screen, rect, text, hovered):
        if not rect:
            return
        sh = rect.copy(); sh.y += 3
        pygame.draw.rect(screen, (10, 10, 15), sh, border_radius=8)
        if hovered:
            bg, bc, tc = (70, 70, 80), (160, 160, 180), (255, 255, 255)
        else:
            bg, bc, tc = (45, 45, 55), (90, 90, 105), (200, 200, 210)
        pygame.draw.rect(screen, bg, rect, border_radius=8)
        pygame.draw.rect(screen, bc, rect, 2, border_radius=8)
        f = pygame.font.Font(None, int(rect.height * 0.6))
        t = f.render(text, True, tc)
        screen.blit(t, t.get_rect(center=rect.center))

    def _render_bottom_button(self, screen, rect, text, hovered, locked=False):
        if not rect:
            return
        sh = rect.copy(); sh.y += 3
        pygame.draw.rect(screen, (10, 10, 15), sh, border_radius=8)
        if locked:
            bg, bc, tc = (35, 35, 40), (60, 60, 65), (80, 80, 85)
        elif hovered:
            bg, bc, tc = (70, 70, 85), (160, 160, 190), (255, 255, 255)
        else:
            bg, bc, tc = (50, 50, 60), (100, 100, 120), (220, 220, 230)
        pygame.draw.rect(screen, bg, rect, border_radius=8)
        pygame.draw.rect(screen, bc, rect, 2, border_radius=8)
        f = pygame.font.Font(None, int(rect.height * 0.4))
        t = f.render(text, True, tc)
        screen.blit(t, t.get_rect(center=rect.center))
        if locked:
            lf = pygame.font.Font(None, int(rect.height * 0.3))
            lt = lf.render("Complete 1-5", True, (70, 70, 75))
            screen.blit(lt, lt.get_rect(center=(rect.centerx, rect.bottom + 14)))

    def _render_scroll_bar(self, screen):
        if self.max_scroll <= 0:
            return
        x, y, width, height = self._get_scroll_bar_area()
        sh = max(30, height * (height / (height + self.max_scroll)))
        sp = y + (self.scroll_y / self.max_scroll) * (height - sh)
        pygame.draw.rect(screen, (30, 30, 38), (x, y, width, height), border_radius=4)
        sr = pygame.Rect(x, sp, width, sh)
        c = (120, 120, 140) if self.dragging_scroll else (80, 80, 95)
        pygame.draw.rect(screen, c, sr, border_radius=4)
        pygame.draw.rect(screen, (150, 150, 170), sr, 1, border_radius=4)

    def _get_scroll_bar_area(self):
        vx = self.screen_manager.viewport_x
        vy = self.screen_manager.viewport_y
        vw = self.screen_manager.viewport_width
        vh = self.screen_manager.viewport_height
        region_tab_h = int(vh * 0.055) if self.region_tabs else 0
        tab_h = int(vh * 0.075) if self.chapter_tabs else 0
        return (vx + vw - 14, vy + int(vh * 0.20) + region_tab_h + tab_h,
                8, vh - int(vh * 0.20) - region_tab_h - tab_h - int(vh * 0.15))

    def _get_scroll_bar_rect(self):
        if self.max_scroll <= 0:
            return None
        x, y, w, h = self._get_scroll_bar_area()
        sh = max(30, h * (h / (h + self.max_scroll)))
        sp = y + (self.scroll_y / self.max_scroll) * (h - sh)
        return pygame.Rect(x, sp, w, sh)

    def _draw_gradient_background(self, screen):
        width = self.screen_manager.window_width
        height = self.screen_manager.window_height
        for i in range(height):
            t = i / height
            r = int(10 + t * 20)
            g = int(12 + t * 25)
            b = int(25 + t * 35)
            pygame.draw.line(screen, (r, g, b), (0, i), (width, i))

        vx = self.screen_manager.viewport_x
        vy = self.screen_manager.viewport_y
        vw = self.screen_manager.viewport_width
        vh = self.screen_manager.viewport_height

        star_positions = [
            (0.03, 0.03), (0.08, 0.08), (0.15, 0.05), (0.22, 0.10),
            (0.30, 0.04), (0.38, 0.12), (0.45, 0.06), (0.52, 0.09),
            (0.60, 0.04), (0.68, 0.11), (0.75, 0.05), (0.82, 0.08),
            (0.90, 0.07), (0.95, 0.10), (0.05, 0.15), (0.12, 0.18),
            (0.88, 0.17), (0.93, 0.22), (0.02, 0.25), (0.98, 0.28),
        ]
        for i, (rx, ry) in enumerate(star_positions):
            x = vx + int(rx * vw)
            y = vy + int(ry * vh)
            size = 1 + int(((i * 5) % 2))
            color = (200 + int(55 * (self._animation_timer * 0.3 + i) % 1),
                     200 + int(55 * (self._animation_timer * 0.4 + i + 1) % 1),
                     255)
            pygame.draw.circle(screen, color, (x, y), size)

    def _render_pause_overlay(self, screen):
        ov = pygame.Surface((self.screen_manager.window_width,
                             self.screen_manager.window_height))
        ov.set_alpha(180)
        ov.fill((10, 10, 10))
        screen.blit(ov, (0, 0))
        f = pygame.font.Font(None, 74)
        t = f.render("PAUSADO", True, (200, 200, 200))
        screen.blit(t, t.get_rect(center=(self.screen_manager.window_width // 2,
                                          self.screen_manager.window_height // 2)))

    def _start_phase_select_music(self):
        if not self._music_started:
            if sound_manager.play_team_select_music(loop=True):
                self._music_started = True
            else:
                if sound_manager.play_menu_music("Title_Theme", loop=True):
                    self._music_started = True

    def on_enter(self):
        if not self._music_started or not pygame.mixer.music.get_busy():
            self._start_phase_select_music()
        self.layout_initialized = False

    def on_exit(self):
        sound_manager.stop_music(fade_ms=300)
        self._music_started = False