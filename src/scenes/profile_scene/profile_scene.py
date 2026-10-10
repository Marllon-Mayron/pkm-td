# src/scenes/profile_scene/profile_scene.py
"""Tela de Perfil — orquestrador. Nada de pygame.draw."""
import pygame

from src.ui.screen_template import StandardScreen
from src.ui.screen_loader import ScreenLoader
from src.managers.sounds.sound_manager import sound_manager, SoundEffect

from src.utils.pet_sprite import PetAnimator

from .profile_logic import (
    ProfileLogic, MAX_FEATURED,
    WARDROBE_SLOTS, WARDROBE_LABELS, WARDROBE_REQUIRED,
    DEFAULT_APPEARANCE,
)


MAIN_JSON = "res/ui_layouts/profile.json"


class ProfileScene(StandardScreen):
    title = ""
    show_back_button = False

    # =================================================================
    def __init__(self, game, return_scene=None):
        self.player = game.player
        self.logic = ProfileLogic(game)
        self.return_scene = return_scene or "menu"

        self._open_modal: str = ""
        self._name_buffer = ""
        self._ach_draft: set = set()
        self._poke_draft = None

        self._wd_slot_idx = 0
        self._wd_item_idx = 0
        self._wd_options: list = []

        self._pet = PetAnimator(direction="down")
        self._pet_pid = None
        self._pet_shiny = False

        super().__init__(game)

    # =================================================================
    def build(self):
        ScreenLoader.load(self, MAIN_JSON)
        self._refresh_main()

    def enter(self):
        self._refresh_main()
        self._pet.set_frames({}, None, False, reset_state=True)
        self._pet_pid = None
        self._refresh_pet()

    def get_actions(self):
        return {
            "back":               self._on_back,
            "open_photo_gallery": self._on_gallery,
            "open_stats":         lambda *_: self._open("stats"),
            "open_name":          lambda *_: self._open("name"),
            "open_ach":           lambda *_: self._open("ach"),
            "open_poke":          lambda *_: self._open("poke"),
            "open_wardrobe":      lambda *_: self._open("wardrobe"),

            "close_modal":  lambda *_: self._close(),
            "save_name":    lambda *_: self._apply_name(),
            "save_ach":     lambda *_: self._apply_ach(),
            "save_poke":    lambda *_: self._apply_poke(),
            "remove_poke":  lambda *_: self._remove_poke(),

            "wd_slot_0": lambda *_: self._wd_slot(0),
            "wd_slot_1": lambda *_: self._wd_slot(1),
            "wd_slot_2": lambda *_: self._wd_slot(2),
            "wd_slot_3": lambda *_: self._wd_slot(3),
            "wd_slot_4": lambda *_: self._wd_slot(4),
            "wd_slot_5": lambda *_: self._wd_slot(5),
            "wd_prev":   lambda *_: self._wd_prev(),
            "wd_next":   lambda *_: self._wd_next(),
            "wd_random": lambda *_: self._wd_random(),
            "wd_equip":  lambda *_: self._wd_equip(),

            "ach_click":  lambda idx: self._ach_click(idx),
            "poke_click": lambda idx: self._poke_click(idx),
            "wd_click":   lambda idx: self._wd_click(idx),
        }

    # =================================================================
    # REFRESH MAIN
    # =================================================================
    def _refresh_main(self):
        l = self.logic
        self._set("lbl_name",     l.save_name())
        self._set("lbl_meta",
                  f"ID {l.uuid_short().replace('ID: ', '')}  -  {l.playtime_text()}")
        self._set("lbl_team_box", l.team_box_text())
        self._set("lbl_money",    l.money_text())
        self._set("lbl_level",    l.level_text())
        self._set("lbl_xp_text",  l.xp_text())
        self._set("player_name",  l.save_name())

        _, xp_in, xp_span, _ = l.level_info()
        bar = self.get("xp_bar")
        if bar is not None:
            bar.max_value = max(1, xp_span)
            bar.value = xp_in

        self._set_surface("player_sprite", l.avatar_surface(192))

        self._set("pet_name",  l.favorite_name())
        self._set("pet_level", l.favorite_level())

        self._feed("stats_grid",    l.stat_items())
        self._feed("featured_grid", l.featured_items())
        self._feed("badges_grid",   l.badge_items())

        self._refresh_pet()

    def _set(self, wid, text):
        w = self.get(wid)
        if w is not None and hasattr(w, "text"):
            w.text = text

    def _set_surface(self, wid, surf):
        w = self.get(wid)
        if w is not None and hasattr(w, "surface"):
            w.surface = surf

    def _feed(self, wid, items):
        w = self.get(wid)
        if w is not None:
            w.items = items

    def _play_click(self, v=0.3):
        try:
            sound_manager.play_effect(SoundEffect.CLICK, volume=v)
        except Exception:
            pass

    # =================================================================
    # PET
    # =================================================================
    def _refresh_pet(self):
        """Pede ao logic os frames do favorito e alimenta o animator."""
        try:
            frames, pid, shiny = self.logic.pet_frames(192)
        except Exception as e:
            print(f"[PROFILE] pet_frames erro: {e}")
            frames, pid, shiny = {}, None, False

        if frames and pid is not None:
            self._pet.set_frames(frames, pid, shiny, reset_state=True)
            self._pet_pid = pid
            self._pet_shiny = shiny
        else:
            self._pet.set_frames({}, None, False, reset_state=True)
            self._pet_pid = None
            self._pet_shiny = False

        self._apply_pet_surface()

    def _apply_pet_surface(self):
        img = self.get("pet_sprite")
        if img is None:
            return
        frame = self._pet.get_frame()
        if frame is None:
            img.surface = None
            return
        off_y = self._pet.get_offset_y()
        if off_y == 0:
            img.surface = frame
        else:
            w, h = frame.get_size()
            canvas = pygame.Surface((w, h), pygame.SRCALPHA)
            canvas.blit(frame, (0, off_y))
            img.surface = canvas

    # =================================================================
    # MODAIS — infra
    # =================================================================
    def _prefix(self, modal):
        return f"m_{modal}_"

    def _open(self, modal_name):
        self._play_click()
        self._close(silent=True)

        self._open_modal = modal_name

        if modal_name == "name":
            self._name_buffer = self.logic.save_name()
        elif modal_name == "ach":
            self._ach_draft = set(
                self.player.profile_customization.get("featured_achievements", []))
        elif modal_name == "poke":
            self._poke_draft = self.player.profile_customization.get(
                "favorite_pokemon_id")
        elif modal_name == "wardrobe":
            self._wd_slot_idx = 0
            self._wd_item_idx = 0
            self._wd_options = []

        self._feed_modal(modal_name)
        self._set_modal_visible(modal_name, True)

    def _close(self, silent=False):
        if self._open_modal:
            self._set_modal_visible(self._open_modal, False)
        self._open_modal = ""
        if not silent:
            self._play_click()

    def _set_modal_visible(self, modal, visible):
        prefix = self._prefix(modal)
        for w in self.widgets:
            if w.id and w.id.startswith(prefix):
                w.visible = visible

    # =================================================================
    # FEED POR MODAL
    # =================================================================
    def _feed_modal(self, modal):
        l = self.logic
        if modal == "stats":
            self._feed("m_stats_grid", self._stats_items())

        elif modal == "name":
            self._set("m_name_value", self._name_buffer or "|")
            self._set("m_name_counter", f"{len(self._name_buffer)}/24")

        elif modal == "ach":
            self._feed("m_ach_grid", l.achievement_items(self._ach_draft))
            self._set("m_ach_title",
                      f"CONQUISTAS EM DESTAQUE  ({len(self._ach_draft)}/{MAX_FEATURED})")

        elif modal == "poke":
            self._feed("m_poke_grid", l.team_items(self._poke_draft))

        elif modal == "wardrobe":
            self._refresh_wardrobe()

    def _stats_items(self):
        am = getattr(self.player, "achievement_manager", None)
        if not am:
            return []
        counters = am._counters if hasattr(am, "_counters") else {}
        labels = {
            "capture_count": "Pokemon capturados",
            "heal_count": "Curas usadas",
            "evolution_count": "Evolucoes totais",
            "shiny_capture_count": "Shinies",
            "boss_defeated_count": "Chefes derrotados",
            "perfect_phase_count": "Fases perfeitas",
            "revive_count": "Revives usados",
            "rare_candy_count": "Rare Candies",
            "escaperope_use_count": "Escape Ropes",
            "move_taught_count": "Movimentos ensinados",
            "battle_item_use_count": "Itens de batalha",
            "friendball_capture_count": "Friend Balls",
            "incubator_revive_count": "Fosseis revividos",
            "incubator_upgrade_count": "Upgrades incubadora",
            "weather_change_count": "Climas alterados",
            "badge_count": "Insignias conquistadas",
            "trade_count": "Trocas realizadas",
            "berry_consumed_count": "Berries consumidas",
            "capture_with_item_count": "Capturas com item",
        }
        out = [{"label": labels.get(k, k.replace("_", " ").title()),
                "value": str(v)}
               for k, v in counters.items() if v > 0]
        out.sort(key=lambda x: -int(x["value"]))
        return out

    # =================================================================
    # AÇÕES — cliques em cards
    # =================================================================
    def _ach_click(self, idx):
        try:
            grid = self.get("m_ach_grid")
            if grid is None or idx >= len(grid.items):
                return
            key = grid.items[idx]["key"]
            if key in self._ach_draft:
                self._ach_draft.discard(key)
            else:
                if len(self._ach_draft) >= MAX_FEATURED:
                    self._ach_draft.pop()
                self._ach_draft.add(key)
            self._play_click(0.25)
            self._feed("m_ach_grid", self.logic.achievement_items(self._ach_draft))
            self._set("m_ach_title",
                      f"CONQUISTAS EM DESTAQUE  ({len(self._ach_draft)}/{MAX_FEATURED})")
        except Exception as e:
            print(f"[PROFILE] ach_click erro: {e}")

    def _poke_click(self, idx):
        try:
            grid = self.get("m_poke_grid")
            if grid is None or idx >= len(grid.items):
                return
            self._poke_draft = grid.items[idx]["uid"]
            self._play_click(0.25)
            self._feed("m_poke_grid", self.logic.team_items(self._poke_draft))
        except Exception:
            pass

    # =================================================================
    # WARDROBE
    # =================================================================
    def _refresh_wardrobe(self):
        l = self.logic
        owned = l.owned_clothing_by_slot()
        slot = WARDROBE_SLOTS[self._wd_slot_idx]
        current_equipped = l.get_appearance().get(slot)

        self._wd_options = l.wardrobe_options(slot, owned)
        if not self._wd_options:
            self._wd_item_idx = -1
        else:
            self._wd_item_idx = max(0, min(self._wd_item_idx,
                                           len(self._wd_options) - 1))

        self._set_surface("m_wardrobe_preview", l.avatar_surface(192))

        for i, sid in enumerate(WARDROBE_SLOTS):
            w = self.get(f"m_wardrobe_slot_{i}")
            if w is None:
                continue
            count = len(owned.get(sid, []))
            w.label = f"{WARDROBE_LABELS[i]} ({count})"
            if i == self._wd_slot_idx:
                w.fill_color = (90, 130, 200)
                w.border_color = (255, 210, 74)
                w.text_color = (255, 255, 255)
            else:
                w.fill_color = (40, 50, 72)
                w.border_color = (70, 88, 128)
                w.text_color = (200, 210, 230)

        if self._wd_item_idx >= 0 and self._wd_options:
            cur = self._wd_options[self._wd_item_idx]
            name = "NENHUM" if cur is None else l.get_clothing_name(cur)
            total = len(self._wd_options)
            self._set("m_wardrobe_current",
                      f"{name}   ({self._wd_item_idx + 1}/{total})")
        else:
            self._set("m_wardrobe_current", "-")

        self._feed("m_wardrobe_grid",
                   l.wardrobe_items(slot, owned,
                                    self._wd_item_idx, current_equipped))

    def _wd_slot(self, i):
        self._wd_slot_idx = i
        self._wd_item_idx = 0
        self._play_click(0.25)
        self._refresh_wardrobe()

    def _wd_prev(self):
        if not self._wd_options:
            return
        self._wd_item_idx = (self._wd_item_idx - 1) % len(self._wd_options)
        self._play_click(0.2)
        self._refresh_wardrobe()

    def _wd_next(self):
        if not self._wd_options:
            return
        self._wd_item_idx = (self._wd_item_idx + 1) % len(self._wd_options)
        self._play_click(0.2)
        self._refresh_wardrobe()

    def _wd_click(self, idx):
        try:
            grid = self.get("m_wardrobe_grid")
            if grid is None or idx >= len(grid.items):
                return
            self._wd_item_idx = grid.items[idx].get("index", idx)
            self._play_click(0.25)
            self._wd_equip()
        except Exception as e:
            print(f"[PROFILE] wd_click erro: {e}")

    def _wd_equip(self):
        if not self._wd_options:
            return
        if self._wd_item_idx < 0:
            return
        iid = self._wd_options[self._wd_item_idx]
        slot = WARDROBE_SLOTS[self._wd_slot_idx]
        self.logic.set_appearance(**{slot: iid})
        self.logic.save_customization()
        self._play_click()
        self._refresh_main()
        self._refresh_wardrobe()

    def _wd_random(self):
        outfit = self.logic.random_outfit()
        for req in WARDROBE_REQUIRED:
            if req not in outfit or outfit[req] is None:
                app = self.logic.get_appearance()
                outfit[req] = app.get(req) or DEFAULT_APPEARANCE[req]
        self.logic.set_appearance(**outfit)
        self.logic.save_customization()
        self._play_click()
        self._refresh_main()
        self._refresh_wardrobe()

    # =================================================================
    # APLICAR MODAIS
    # =================================================================
    def _apply_name(self):
        name = (self._name_buffer or "").strip() or "Novo Jogo"
        name = name[:24]
        try:
            from src.managers.save_manager import save_manager
            save_manager.save_data.setdefault("meta", {})["save_name"] = name
        except Exception:
            pass
        self.logic.save_customization()
        self._refresh_main()
        self._close(silent=True)

    def _apply_ach(self):
        self.player.profile_customization["featured_achievements"] = \
            list(self._ach_draft)[:MAX_FEATURED]
        self.logic.save_customization()
        self._refresh_main()
        self._close(silent=True)

    def _apply_poke(self):
        self.player.profile_customization["favorite_pokemon_id"] = self._poke_draft
        self.logic.save_customization()
        try:
            self.logic.clear_pet_cache()
        except Exception:
            pass
        self._refresh_main()
        self._close(silent=True)

    def _remove_poke(self):
        self._poke_draft = None
        self._feed("m_poke_grid", self.logic.team_items(None))
        self._play_click(0.25)

    # =================================================================
    # NAV
    # =================================================================
    def _on_back(self, *_):
        self._play_click()
        try:
            sound_manager.stop_music(fade_ms=300)
        except Exception:
            pass
        if self.return_scene == "phase_select":
            from src.scenes.phase_selector.phase_select_scene import PhaseSelectScene
            self.game.phase_select_scene = PhaseSelectScene(self.game)
            self.game.current_scene = self.game.phase_select_scene
        else:
            from src.scenes.menu_scene import MenuScene
            self.game.current_scene = MenuScene(self.game)

    def _on_gallery(self, *_):
        self._play_click()
        from src.scenes.profile_scene.photo_gallery_scene import PhotoGalleryScene
        self.game.current_scene = PhotoGalleryScene(
            self.game, return_scene=self.return_scene)

    # =================================================================
    # EVENTOS
    # =================================================================
    def handle_event(self, event):
        if self._open_modal == "name" and event.type == pygame.KEYDOWN:
            self._name_keydown(event)
            return

        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            if self._open_modal:
                self._close()
                return
            self._on_back()
            return

        if self._open_modal:
            prefix = self._prefix(self._open_modal)
            for w in sorted(self.widgets, key=lambda x: -getattr(x, "z", 0)):
                if w.id and w.id.startswith(prefix):
                    if w.handle_event(event):
                        return
            return

        super().handle_event(event)

    def _name_keydown(self, event):
        if event.key == pygame.K_RETURN:
            self._apply_name()
            return
        if event.key == pygame.K_BACKSPACE:
            self._name_buffer = self._name_buffer[:-1]
        elif event.key == pygame.K_DELETE:
            self._name_buffer = ""
        elif event.unicode and event.unicode.isprintable():
            if len(self._name_buffer) < 24:
                self._name_buffer += event.unicode
        self._set("m_name_value", self._name_buffer or "|")
        self._set("m_name_counter", f"{len(self._name_buffer)}/24")

    # =================================================================
    # UPDATE
    # =================================================================
    def fixed_update(self, dt):
        if self._pet_pid is not None:
            self._pet.update(dt)
            self._apply_pet_surface()

        self._set("lbl_meta",
                  f"ID {self.logic.uuid_short().replace('ID: ', '')}  -  "
                  f"{self.logic.playtime_text()}")

        super().fixed_update(dt)

    # =================================================================
    def on_back(self):
        self._on_back()