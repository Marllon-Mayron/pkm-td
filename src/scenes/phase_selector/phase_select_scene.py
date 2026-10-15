# src/scenes/phase_selector/phase_select_scene.py
"""
Tela de Seleção de Fase — padrão Editor.

- Layout 100% em `res/ui_layouts/phase_select.json`
- Lógica 100% em `PhaseSelectLogic`
- Aqui só liga widgets <-> dados e reage a eventos.
"""
import pygame

from src.ui.screen_template import StandardScreen
from src.ui.screen_loader import ScreenLoader

from src.scenes.phase_selector.phase_select_logic import PhaseSelectLogic
from src.config.regions import RegionCatalog
from src.config.global_settings import DEBUG_MODE
from src.managers.sounds.sound_manager import sound_manager, SoundEffect

LAYOUT_PATH = "res/ui_layouts/phase_select.json"


class PhaseSelectScene(StandardScreen):
    title = ""
    show_back_button = False

    def __init__(self, game):
        self.logic = PhaseSelectLogic(game)
        self._music_started = False
        super().__init__(game)

    # =================================================================
    # BUILD
    # =================================================================
    def build(self):
        ScreenLoader.load(self, LAYOUT_PATH)
        self._populate_static()

    def get_actions(self):
        return {
            "back":               self._on_back,
            "region_changed":     self._on_region_changed,
            "chapter_changed":    self._on_chapter_changed,
            "phase_selected":     self._on_phase_selected,
            "play":               self._on_play,

            "open_shop":          self._open_shop,
            "open_npc_hall":      self._open_npc_hall,
            "open_minigame":      self._open_minigame,
            "open_pokedex":       self._open_pokedex,
            "open_achievements":  self._open_achievements,
            "open_incubator":     self._open_incubator,
            "open_profile":       self._open_profile,
            "open_mystery_gift":  self._open_mystery_gift,
            "open_chests": self._on_open_chests,
        }

    # =================================================================
    # População inicial
    # =================================================================
    def _populate_static(self):
        rt = self.get("region_tabs")
        if rt is not None:
            rt.tabs = self.logic.region_tab_labels()
            rt.current_tab = self.logic.current_region_label()

        ct = self.get("chapter_tabs")
        if ct is not None:
            ct.tabs = self.logic.chapter_tab_labels()
            ct.current_tab = self.logic.current_chapter_label()

        self._update_region_badge()
        self._update_incubator_button()
        self._feed_grid()
        self._update_detail()

    def _update_region_badge(self):
        badge = self.get("lbl_region_badge")
        if badge is None:
            return
        name = RegionCatalog.get_name(self.logic.current_region_id)
        badge.text = f"REGIAO {self.logic.current_region_id}: {name.upper()}"

    def _update_incubator_button(self):
        btn = self.get("btn_incubator")
        if btn is None:
            return
        unlocked = self.logic.is_incubator_unlocked()
        btn.enabled = unlocked
        btn.label = "INCUBADORA" if unlocked else "INCUBADORA (BLOQ)"
        if unlocked:
            btn.fill_color = (42, 51, 88)
            btn.border_color = (74, 90, 138)
            btn.text_color = (232, 232, 240)
        else:
            btn.fill_color = (40, 40, 45)
            btn.border_color = (60, 60, 65)
            btn.text_color = (110, 110, 120)

    # =================================================================
    # Feed do CardGrid
    # =================================================================
    def _feed_grid(self):
        grid = self.get("phases_grid")
        if grid is None:
            return
        grid.items = [
            self.logic.item_dict(i) for i in range(len(self.logic.phases))
        ]

    # =================================================================
    # Detail Panel
    # =================================================================
    def _update_detail(self):
        state = self.logic.get_detail_state()

        img = self.get("detail_image")
        if img is not None:
            img.surface = state["image"]

        lbl = self.get("detail_number")
        if lbl is not None:
            lbl.text = state.get("number", "")

        lbl = self.get("detail_name")
        if lbl is not None:
            lbl.text = state["name"]

        badge = self.get("detail_status")
        if badge is not None:
            badge.text = state["status_text"]
            badge.bg_color = (26, 35, 64)
            badge.text_color = state["status_color"]
            badge.border_color = state["status_color"]

        # Estrelas do detalhe (3 imagens: filled/empty)
        for i in range(1, 4):
            star_img = self.get(f"detail_star_{i}")
            if star_img is not None:
                star_img.surface = state.get(f"star_{i}")

        lbl = self.get("detail_desc")
        if lbl is not None:
            lbl.text = state["description"]

        btn = self.get("btn_play")
        if btn is not None:
            btn.enabled = state["can_play"]
            btn.label = "JOGAR" if state["can_play"] else "BLOQUEADA"

    # =================================================================
    # Callbacks — Tabs
    # =================================================================
    def _on_region_changed(self, label):
        rid = self.logic.region_id_from_label(label)
        if rid is None or rid == self.logic.current_region_id:
            return

        self.logic.set_region(rid)

        ct = self.get("chapter_tabs")
        if ct is not None:
            ct.tabs = self.logic.chapter_tab_labels()
            ct.current_tab = self.logic.current_chapter_label()

        self._update_region_badge()
        self._feed_grid()
        self._update_detail()

    def _on_chapter_changed(self, label):
        ch = self.logic.chapter_id_from_label(label)
        if ch is None or ch == self.logic.current_chapter_id:
            return

        self.logic.set_chapter(ch)
        self._feed_grid()
        self._update_detail()

    # =================================================================
    # Callbacks — Cards / Play
    # =================================================================
    def _on_phase_selected(self, idx):
        if 0 <= idx < len(self.logic.phases):
            self.logic.select_phase(self.logic.phases[idx]["number"])
            self._feed_grid()
            self._update_detail()

    def _on_play(self, *_):
        state = self.logic.get_detail_state()
        if not state["valid"] or not state["can_play"]:
            sound_manager.play_effect(SoundEffect.ERROR)
            return

        self.start_phase(self.logic.selected_phase_number)

    # =================================================================
    # Navegação / Ações
    # =================================================================
    def _on_back(self, *_):
        sound_manager.play_effect(SoundEffect.CLICK)
        sound_manager.stop_music(fade_ms=300)
        self._music_started = False
        self.game.current_scene = self.game.menu_scene

    def _open_shop(self, *_):
        sound_manager.play_effect(SoundEffect.CLICK)
        from src.scenes.shop_scene.shop_scene import ShopScene
        self.game.shop_scene = ShopScene(self.game)
        self.game.current_scene = self.game.shop_scene

    def _open_npc_hall(self, *_):
        sound_manager.play_effect(SoundEffect.CLICK)
        from src.scenes.npc_hall_scene.npc_hall_scene import NpcHallScene
        self.game.current_scene = NpcHallScene(self.game)

    def _open_minigame(self, *_):
        sound_manager.play_effect(SoundEffect.CLICK)
        from src.scenes.minigame_select_scene.minigame_select_scene import MinigameSelectScene
        self.game.current_scene = MinigameSelectScene(self.game)

    def _open_pokedex(self, *_):
        sound_manager.play_effect(SoundEffect.CLICK)
        from src.scenes.pokedex_scene.pokedex_scene import PokedexScene
        self.game.pokedex_scene = PokedexScene(self.game)
        self.game.current_scene = self.game.pokedex_scene

    def _on_open_chests(self, *_):
        try:
            sound_manager.play_effect(SoundEffect.CLICK, volume=0.5)
        except Exception:
            pass
        from src.scenes.chest_scene.chest_scene import ChestScene
        self.game.current_scene = ChestScene(
            self.game, return_scene="phase_select"
        )

    def _open_achievements(self, *_):
        sound_manager.play_effect(SoundEffect.CLICK)
        from src.scenes.achievement_scene.achievement_scene import AchievementScene
        self.game.achievement_scene = AchievementScene(self.game)
        self.game.current_scene = self.game.achievement_scene

    def _open_incubator(self, *_):
        if not self.logic.is_incubator_unlocked():
            sound_manager.play_effect(SoundEffect.ERROR)
            return
        sound_manager.play_effect(SoundEffect.CLICK)
        from src.scenes.incubator_scene.incubator_scene import IncubatorScene
        self.game.incubator_scene = IncubatorScene(self.game)
        self.game.current_scene = self.game.incubator_scene

    def _open_profile(self, *_):
        sound_manager.play_effect(SoundEffect.CLICK)
        from src.scenes.profile_scene.profile_scene import ProfileScene
        sound_manager.stop_music(fade_ms=300)
        self._music_started = False
        self.game.current_scene = ProfileScene(self.game, return_scene="phase_select")

    def _open_mystery_gift(self, *_):
        sound_manager.play_effect(SoundEffect.CLICK)
        sound_manager.stop_music(fade_ms=300)
        self._music_started = False
        from src.scenes.mystery_gift_scene.mystery_gift_scene import MysteryGiftScene
        self.game.current_scene = MysteryGiftScene(self.game)

    # =================================================================
    # Iniciar fase
    # =================================================================
    def start_phase(self, phase_number):
        sound_manager.play_effect(SoundEffect.CLICK)
        sound_manager.stop_music(fade_ms=300)
        self._music_started = False

        from src.scenes.team_select_scene.team_select_scene import TeamSelectScene

        try:
            ts = TeamSelectScene(
                self.game,
                self.logic.current_chapter_id,
                phase_number,
                region_id=self.logic.current_region_id,
            )
        except TypeError:
            ts = TeamSelectScene(
                self.game, self.logic.current_chapter_id, phase_number
            )

        self.game.team_select_scene = ts
        self.game.current_scene = ts

    # =================================================================
    # Eventos / Atalhos
    # =================================================================
    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self._on_back()
                return True
            if event.key == pygame.K_p:
                self.toggle_pause()
                return True
            if event.key == pygame.K_LEFT:
                self._cycle_region(-1)
                return True
            if event.key == pygame.K_RIGHT:
                self._cycle_region(+1)
                return True
            if event.key == pygame.K_RETURN:
                self._on_play()
                return True

            if DEBUG_MODE:
                if event.key == pygame.K_r and (pygame.key.get_mods() & pygame.KMOD_CTRL):
                    self.logic.reset_progress()
                    self._populate_static()
                    return True
                if event.key == pygame.K_u:
                    self.logic.debug_unlock_next()
                    self._feed_grid()
                    self._update_detail()
                    return True
                if event.key == pygame.K_a:
                    self.logic.debug_unlock_all()
                    self._feed_grid()
                    self._update_detail()
                    return True

            if event.key == pygame.K_s:
                self._open_shop(); return True
            if event.key == pygame.K_m:
                self._open_minigame(); return True
            if event.key == pygame.K_x:
                self._open_pokedex(); return True
            if event.key == pygame.K_c:
                self._open_achievements(); return True
            if event.key == pygame.K_i:
                self._open_incubator(); return True
            if event.key == pygame.K_v:
                self._open_profile(); return True

        super().handle_event(event)

    def _cycle_region(self, delta: int):
        ids = self.logic.available_regions
        if not ids:
            return
        try:
            i = ids.index(self.logic.current_region_id)
        except ValueError:
            return
        ni = max(0, min(len(ids) - 1, i + delta))
        if ni == i:
            return

        self.logic.set_region(ids[ni])

        rt = self.get("region_tabs")
        if rt is not None:
            rt.current_tab = self.logic.current_region_label()

        ct = self.get("chapter_tabs")
        if ct is not None:
            ct.tabs = self.logic.chapter_tab_labels()
            ct.current_tab = self.logic.current_chapter_label()

        self._update_region_badge()
        self._feed_grid()
        self._update_detail()

    def on_back(self):
        self._on_back()

    # =================================================================
    # Ciclo de vida
    # =================================================================
    def on_enter(self):
        # Recarrega progresso (pode ter mudado após voltar de uma fase)
        self.logic.refresh_all()
        self._populate_static()

        if not self._music_started or not pygame.mixer.music.get_busy():
            self._start_phase_select_music()

    def on_exit(self):
        sound_manager.stop_music(fade_ms=300)
        self._music_started = False

    def _start_phase_select_music(self):
        if self._music_started:
            return
        if sound_manager.play_team_select_music(loop=True):
            self._music_started = True
        elif sound_manager.play_menu_music("Title_Theme", loop=True):
            self._music_started = True

    # =================================================================
    # Resize — repopula bindings após rebuild dos widgets
    # =================================================================
    def on_resize(self):
        super().on_resize()
        self._populate_static()