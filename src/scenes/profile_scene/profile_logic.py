# src/scenes/profile_scene/profile_logic.py
"""Dados da tela de perfil — sem render."""
import pygame
from typing import Optional, List, Dict

from src.data.achievement_data import ACHIEVEMENTS, AchievementRarity
from src.data.pokedex import Pokedex
from src.config.progress import progress_manager
from src.config.paths import SPRITES_PATH, ITEMS_PATH
from src.managers.save_manager import save_manager
from src.ui.utils.type_bar_loader import rarity_bar_loader

# =====================================================================
# GINÁSIOS
# =====================================================================
# Chave = (chapter, phase) → número da badge.
# O phase_id COMPLETO é montado como f"{region}:{chapter}:{phase}",
# igual ao game_scene.py (make_phase_id). NUNCA compare com "5-4".
GYM_PHASES = {
    (1, 5): 1,   # 1º Ginásio — Rock
    (2, 6): 2,   # 2º Ginásio — Water
    (3, 4): 3,   # 3º Ginásio — Thunder
    (4, 6): 4,   # 4º Ginásio — Rainbow
    (5, 4): 5,   # 5º Ginásio — Poison
    (6, 4): 6,   # 6º Ginásio — Marsh
    (7, 4): 7,   # 7º Ginásio — Volcano
    (8, 2): 8,   # 8º Ginásio — Earth
}

BADGE_SPRITES = ["rock-badge.png", "water-badge.png", "thunder-badge.png",
                 "rainbow-badge.png", "poison-badge.png", "marsh-badge.png",
                 "volcano-badge.png", "earth-badge.png"]

BADGE_COLORS = {1: (180, 140, 80), 2: (80, 140, 220), 3: (240, 200, 60),
                4: (220, 120, 200), 5: (160, 80, 200), 6: (140, 100, 60),
                7: (220, 80, 40), 8: (140, 100, 60)}

MAX_FEATURED = 3

# ====== ARMÁRIO ======
WARDROBE_SLOTS    = ["skin", "eyes", "hair", "torso", "pants", "hat"]
WARDROBE_LABELS   = ["PELE", "OLHOS", "CABELO", "TOPO", "CALCA", "CHAPEU"]
WARDROBE_OPTIONAL = {"hair", "torso", "pants", "hat"}
WARDROBE_REQUIRED = {"skin", "eyes"}

DEFAULT_APPEARANCE = {
    "skin":  "skin_1",
    "eyes":  "eyes_1",
    "hair":  None,
    "torso": None,
    "pants": None,
    "hat":   None,
}

# ====== RARIDADE ======
RARITY_ORDER  = ["common", "uncommon", "rare", "epic", "legendary"]
RARITY_LABELS = {
    "common": "COMUM", "uncommon": "INCOMUM", "rare": "RARO",
    "epic": "EPICO", "legendary": "LENDARIO",
}
RARITY_COLORS = {
    "common": "#C8C8C8", "uncommon": "#64DC78", "rare": "#5096FF",
    "epic": "#C864F0", "legendary": "#FFC83C",
}

# ====== ORDEM DE RARIDADE DE ACHIEVEMENTS (menor = mais raro) ======
_ACH_RARITY_ORDER = {
    AchievementRarity.LEGENDARY: 0,
    AchievementRarity.EPIC:      1,
    AchievementRarity.RARE:      2,
    AchievementRarity.UNCOMMON:  3,
    AchievementRarity.COMMON:    4,
}


# =====================================================================
# HELPERS DE BOUNDING BOX
# =====================================================================
def _bounding_box(surf):
    """
    Retorna um pygame.Rect dos pixels NÃO-transparentes da surface.
    Retorna None se a surface for completamente vazia.
    """
    try:
        mask = pygame.mask.from_surface(surf)
    except Exception:
        return None
    rects = mask.get_bounding_rects()
    if not rects:
        return None
    x1 = min(r.x for r in rects)
    y1 = min(r.y for r in rects)
    x2 = max(r.x + r.w for r in rects)
    y2 = max(r.y + r.h for r in rects)
    return pygame.Rect(x1, y1, x2 - x1, y2 - y1)


class ProfileLogic:
    # ================================================================
    # CONSTANTES DO PET — mesmas do game scene
    # ================================================================
    PET_TILE_SCALE = 16 / 24  # ≈ 0.6667
    PET_CAMERA_ZOOM = 3.0

    def __init__(self, game):
        self.game = game
        self.player = game.player
        self.pokedex = Pokedex()

        self.badge_sprites: Dict[int, Optional[pygame.Surface]] = {}
        self._avatar_cache: Dict[int, Optional[pygame.Surface]] = {}
        self._fav_cache: Dict[tuple, Optional[pygame.Surface]] = {}
        self._pet_frames_cache: Dict[tuple, dict] = {}

        self._load_badge_sprites()
        self._ensure_customization()

    # ================================================================
    def _ensure_customization(self):
        pc = self.player.profile_customization
        pc.setdefault("featured_achievements", [])
        pc.setdefault("favorite_pokemon_id", None)
        app = pc.setdefault("appearance", {})
        for k, v in DEFAULT_APPEARANCE.items():
            app.setdefault(k, v)

    def _load_badge_sprites(self):
        d = ITEMS_PATH / "badge"
        for i, fname in enumerate(BADGE_SPRITES):
            num = i + 1
            for path in (d / fname, d / fname.lower(), d / fname.upper()):
                if path.exists():
                    try:
                        self.badge_sprites[num] = pygame.image.load(
                            str(path)).convert_alpha()
                        break
                    except Exception:
                        pass
            if num not in self.badge_sprites:
                self.badge_sprites[num] = self._fallback_badge(num)

    def _fallback_badge(self, num):
        size = 64
        s = pygame.Surface((size, size), pygame.SRCALPHA)
        color = BADGE_COLORS.get(num, (200, 200, 200))
        pygame.draw.circle(s, color, (size // 2, size // 2), size // 2 - 2)
        pygame.draw.circle(s, (255, 255, 255), (size // 2, size // 2),
                           size // 2 - 2, 2)
        f = pygame.font.Font(None, 32)
        t = f.render(str(num), True, (255, 255, 255))
        s.blit(t, t.get_rect(center=(size // 2, size // 2)))
        return s

    # ================================================================
    # TEXTOS DO HEADER
    # ================================================================
    def save_name(self) -> str:
        try:
            return save_manager.save_data.get("meta", {}).get("save_name", "Novo Jogo")
        except Exception:
            return "Novo Jogo"

    def uuid_short(self) -> str:
        return f"ID: {getattr(self.player, 'uuid', 'N/A')[:12]}"

    def playtime_text(self) -> str:
        t = getattr(self.player, "total_playtime", 0.0)
        return f"{int(t // 3600):02d}h {int((t % 3600) // 60):02d}m"

    def money_text(self) -> str:
        return f"$ {int(getattr(self.player, 'money', 0)):,}".replace(",", ".")

    def team_box_text(self) -> str:
        return (f"Time {len(getattr(self.player, 'team', []))}/6  "
                f"Box {len(getattr(self.player, 'pc_box', []))}")

    def level_info(self):
        try:
            return self.player.get_level_progress()
        except Exception:
            return (1, 0, 100, 0.0)

    def level_text(self) -> str:
        return f"Nivel {self.level_info()[0]}"

    def xp_text(self) -> str:
        _, xp_in, xp_span, _ = self.level_info()
        return f"{xp_in}/{xp_span} XP"

    # ================================================================
    # STATS CARD
    # ================================================================
    def stat_items(self) -> List[dict]:
        p = self.player
        total_p = (len(self.pokedex.pokemon_data)
                   if hasattr(self.pokedex, "pokemon_data") else 151)
        seen = len(getattr(p, "seen_pokemon", set()))
        caught = len(getattr(p, "caught_pokemon", set()))
        badges = self.badges_earned()
        am = getattr(p, "achievement_manager", None)
        ach_u = am.get_unlocked_count() if am else 0
        ach_t = am.get_total_count() if am else 100
        photos = self._count_photos()

        return [
            {"title": "VISTOS",     "value_str": f"{seen}/{total_p}",
             "color": "#7A90C8", "bg_color": "#121A30"},
            {"title": "CAPTURADOS", "value_str": f"{caught}/{total_p}",
             "color": "#90D090", "bg_color": "#101A24"},
            {"title": "INSIGNIAS",  "value_str": f"{badges}/8",
             "color": "#FFD24A", "bg_color": "#1A1710"},
            {"title": "CONQUISTAS", "value_str": f"{ach_u}/{ach_t}",
             "color": "#FFB060", "bg_color": "#1A1410"},
            {"title": "FOTOS",      "value_str": str(photos),
             "color": "#E8C8FF", "bg_color": "#181025"},
        ]

    # ----------------------------------------------------------------
    # GINÁSIOS — CADA UM VERIFICADO INDIVIDUALMENTE
    # ----------------------------------------------------------------
    def _current_region(self) -> int:
        """Região atual do jogador (fallback 1)."""
        r = getattr(self.player, "current_region", None)
        if r is None:
            try:
                r = save_manager.save_data.get("game_state", {}).get("current_region", 1)
            except Exception:
                r = 1
        try:
            return int(r) if r is not None else 1
        except Exception:
            return 1

    def _gym_completed(self, chapter: int, phase: int,
                       region: Optional[int] = None) -> bool:
        """
        Verifica se o ginásio (chapter, phase) foi concluído.

        O phase_id real é f"{region}:{chapter}:{phase}" (ex: "1:5:4"),
        igual ao game_scene.make_phase_id().
        """
        if region is None:
            region = self._current_region()
        pid = f"{region}:{chapter}:{phase}"
        try:
            return bool(progress_manager.is_phase_completed(pid))
        except Exception as e:
            print(f"[PROFILE] _gym_completed({pid}) erro: {e}")
            return False

    def _gym_completed_in_any_region(self, chapter: int, phase: int) -> bool:
        """
        Fallback: procura o ginásio em QUALQUER região (1..8).
        Cobre saves antigos/migrados cujo current_region não bate.
        """
        if self._gym_completed(chapter, phase):
            return True
        for region in range(1, 9):
            if self._gym_completed(chapter, phase, region=region):
                return True
        return False

    def badges_earned(self) -> int:
        """Conta quantas badges o jogador JÁ POSSUI (não é sequencial)."""
        n = 0
        for (chapter, phase) in GYM_PHASES:
            if self._gym_completed_in_any_region(chapter, phase):
                n += 1
        return n

    def _count_photos(self) -> int:
        d = SPRITES_PATH / "screenshots" / "player_screenshots"
        return len(list(d.glob("photo_*.png"))) if d.exists() else 0

    def badge_items(self) -> List[dict]:
        """
        Retorna os 8 slots de badge, marcando CADA UM individualmente
        como obtido/não obtido — sem lógica sequencial.
        """
        out = []
        for (chapter, phase), num in GYM_PHASES.items():
            has = self._gym_completed_in_any_region(chapter, phase)
            out.append({
                "badge_surface": self.badge_sprites.get(num) if has else None,
                "has_badge":     has,
                "number":        str(num),
                "bg_color":      "#1A2340" if has else "#0E1424",
                "border_color":  "#FFD24A" if has else "#2E3856",
            })
        out.sort(key=lambda d: int(d["number"]))
        return out

    # ================================================================
    # HELPERS DE ACHIEVEMENTS DESBLOQUEADAS
    # ================================================================
    def _unlocked_ids(self) -> List[str]:
        """
        Retorna IDs de conquistas desbloqueadas SEM o prefixo de região.

        O save guarda no formato "region:id" (ex: "1:first_capture"),
        mas ACHIEVEMENTS é indexado só pelo id ("first_capture").
        Sem esse parse, `k in ACHIEVEMENTS` sempre retorna False.
        """
        raw = self.player.achievements.get("unlocked", []) or []
        out: List[str] = []
        for k in raw:
            s = str(k)
            if ":" in s:
                # "1:first_capture" → "first_capture"
                _, _, aid = s.partition(":")
                out.append(aid)
            else:
                out.append(s)
        return out

    # ================================================================
    # TROFÉUS / CONQUISTAS
    # ================================================================
    def _featured_keys(self) -> List[str]:
        cur = self.player.profile_customization.get("featured_achievements", [])
        if cur:
            # também normaliza as chaves salvas (defensivo)
            return [str(k).partition(":")[2] if ":" in str(k) else str(k)
                    for k in list(cur)[:MAX_FEATURED]]

        unlocked_ids = [k for k in self._unlocked_ids() if k in ACHIEVEMENTS]
        if not unlocked_ids:
            return []

        unlocked_ids.sort(
            key=lambda k: _ACH_RARITY_ORDER.get(ACHIEVEMENTS[k].rarity, 5)
        )
        return unlocked_ids[:MAX_FEATURED]

    def featured_items(self) -> List[dict]:
        keys = self._featured_keys()
        items = []
        for k in keys:
            a = ACHIEVEMENTS.get(k)
            if a is None:
                continue
            col = getattr(a.rarity, "color", (150, 150, 150))
            dark = tuple(max(15, c // 6) for c in col)
            items.append({
                "title": a.title,
                "description": a.description or "",
                "rarity_name": getattr(a.rarity, "display_name", "").upper(),
                "rarity_color": self._hex(col),
                "bg_color": self._hex(dark),
            })
        while len(items) < MAX_FEATURED:
            items.append({"title": "—",
                          "description": "Nenhuma conquista em destaque",
                          "rarity_name": "—", "rarity_color": "#3A4870",
                          "bg_color": "#101828"})
        return items

    def achievement_items(self, selected_keys) -> List[dict]:
        unlocked_ids = [k for k in self._unlocked_ids() if k in ACHIEVEMENTS]
        keys = sorted(
            unlocked_ids,
            key=lambda k: _ACH_RARITY_ORDER.get(ACHIEVEMENTS[k].rarity, 5)
        )
        # normaliza as chaves selecionadas (defensivo)
        sel = {
            str(k).partition(":")[2] if ":" in str(k) else str(k)
            for k in (selected_keys or [])
        }
        out = []
        for k in keys:
            a = ACHIEVEMENTS[k]
            col = getattr(a.rarity, "color", (150, 150, 150))
            out.append({
                "key": k,
                "title": a.title,
                "description": a.description or "",
                "rarity_name": getattr(a.rarity, "display_name", "").upper(),
                "rarity_color": self._hex(col),
                "bg_color": "#4A6E90" if k in sel else "#1E2438",
                "border_color": "#FFD24A" if k in sel else "#3A4870",
                "check_mark": "✓" if k in sel else "",
            })
        return out

    # ================================================================
    # FAVORITO / TIME
    # ================================================================
    def favorite_pokemon(self):
        fid = self.player.profile_customization.get("favorite_pokemon_id")
        if not fid:
            return None
        for pk in getattr(self.player, "team", []):
            if getattr(pk, "unique_id", None) == fid:
                return pk
        return None

    def favorite_surface(self, target=160):
        fav = self.favorite_pokemon()
        if fav is None:
            return None
        shiny = getattr(fav, "is_shiny", False)
        key = (fav.id, shiny, target)
        if key in self._fav_cache:
            return self._fav_cache[key]
        surf = None
        try:
            surf = self.pokedex.get_sprite(fav.id, "front", shiny)
            if surf is None:
                surf = self.pokedex.get_portrait(fav.id, "normal", shiny)
            if surf:
                w, h = surf.get_size()
                sc = min(target / max(1, w), target / max(1, h))
                surf = pygame.transform.smoothscale(
                    surf, (max(1, int(w * sc)), max(1, int(h * sc))))
        except Exception:
            surf = None
        self._fav_cache[key] = surf
        return surf

    def favorite_name(self) -> str:
        fav = self.favorite_pokemon()
        if fav is None:
            return "—"
        nm = getattr(fav, "custom_name", None) or fav.name
        if getattr(fav, "is_shiny", False):
            nm += " *"
        return nm

    def favorite_level(self) -> str:
        fav = self.favorite_pokemon()
        return f"Lv. {fav.level}" if fav else ""

    def favorite_hp(self):
        fav = self.favorite_pokemon()
        if fav is None:
            return (0, 1)
        return (getattr(fav, "current_hp", 0), max(1, getattr(fav, "max_hp", 1)))

    def team_items(self, current_id) -> List[dict]:
        out = []
        for pk in getattr(self.player, "team", []):
            uid = getattr(pk, "unique_id", None)
            nm = getattr(pk, "custom_name", None) or pk.name
            if getattr(pk, "is_shiny", False):
                nm += " *"
            surf = None
            try:
                surf = self.pokedex.get_sprite(pk.id, "front",
                                               getattr(pk, "is_shiny", False))
            except Exception:
                pass
            out.append({
                "uid": uid,
                "portrait": surf,
                "name": nm,
                "level": f"Lv.{pk.level}  HP {pk.current_hp}/{pk.max_hp}",
                "is_selected": uid == current_id,
                "border_color": "#FFD24A" if uid == current_id else "#3A4870",
                "bg_color": "#3A2C58" if uid == current_id else "#1E2438",
            })
        return out

    # ================================================================
    # WARDROBE
    # ================================================================
    def owned_clothing_by_slot(self) -> Dict[str, list]:
        result = {s: [] for s in WARDROBE_SLOTS}
        try:
            from src.data.item_bag_catalog import item_bag_catalog
            bag = getattr(self.player.bag, "items", {})
            for iid, qty in bag.items():
                if qty <= 0:
                    continue
                data = item_bag_catalog.items.get(iid)
                if not data or data.get("category") != "clothing":
                    continue
                slot = data.get("slot")
                if slot in result:
                    result[slot].append(iid)
        except Exception as e:
            print(f"[PROFILE] owned_clothing erro: {e}")
        for s in result:
            result[s].sort(key=self._rarity_index)
        return result

    def get_clothing_name(self, item_id) -> str:
        if item_id is None:
            return "NENHUM"
        try:
            from src.data.item_bag_catalog import item_bag_catalog
            return item_bag_catalog.items.get(item_id, {}).get("name", item_id)
        except Exception:
            return str(item_id)

    def _rarity_index(self, item_id) -> int:
        try:
            from src.data.item_bag_catalog import item_bag_catalog
            rar = item_bag_catalog.items.get(item_id, {}).get("rarity", "common")
            return RARITY_ORDER.index(rar) if rar in RARITY_ORDER else 0
        except Exception:
            return 0

    def get_clothing_rarity(self, item_id) -> Optional[dict]:
        """Retorna {'key','name','color'} da raridade da peça ou None."""
        if item_id is None:
            return None
        try:
            from src.data.item_bag_catalog import item_bag_catalog
            data = item_bag_catalog.items.get(item_id, {})
            rar = data.get("rarity", "common")
            return {
                "key":   rar,
                "name":  data.get("rarity_name") or RARITY_LABELS.get(rar, ""),
                "color": data.get("rarity_color") or RARITY_COLORS.get(rar, "#3A4870"),
            }
        except Exception:
            return None

    def wardrobe_options(self, slot, owned) -> list:
        items = list(owned.get(slot, []))
        items.sort(key=self._rarity_index)
        if slot in WARDROBE_OPTIONAL:
            return [None] + items
        return items

    def wardrobe_items(self, slot, owned, selected_idx,
                       current_equipped) -> List[dict]:

        opts = self.wardrobe_options(slot, owned)
        out = []
        for i, iid in enumerate(opts):
            if iid is None:
                name, rar_key = "NENHUM", None
                rar_name, rar_color = "", "#3A4870"
                rar_surf = None
            else:
                name = self.get_clothing_name(iid)
                rar = self.get_clothing_rarity(iid)
                rar_key   = rar["key"]   if rar else None
                rar_name  = rar["name"]  if rar else ""
                rar_color = rar["color"] if rar else "#3A4870"
                rar_surf = (rarity_bar_loader.get_original(rar_key)
                            if rar_key else None)

            selected = (i == selected_idx)
            equipped = (iid == current_equipped)
            if iid is None and current_equipped is None:
                equipped = True

            if selected:
                border = "#FFD24A"
            elif equipped:
                border = "#9AD870"
            elif iid is not None:
                border = rar_color
            else:
                border = "#3A4870"

            out.append({
                "index":          i,
                "name":           name,
                "rarity_name":    rar_name,
                "rarity_color":   rar_color,
                "rarity_surface": rar_surf,
                "selected_label": "►" if selected else "",
                "equipped_label": "EQUIPADO" if equipped else "",
                "bg_color":       "#4A6E90" if selected else
                                  ("#243A28" if equipped else "#1E2438"),
                "border_color":   border,
            })
        return out

    def random_outfit(self) -> dict:
        import random as _random
        owned = self.owned_clothing_by_slot()
        result = {}
        for slot in WARDROBE_SLOTS:
            items = owned.get(slot, [])
            if not items:
                continue
            if slot in WARDROBE_OPTIONAL:
                if _random.random() < 0.7:
                    result[slot] = _random.choice(items)
                else:
                    result[slot] = None
            else:
                result[slot] = _random.choice(items)
        return result

    def get_appearance(self) -> dict:
        app = self.player.profile_customization.setdefault("appearance", {})
        for k, v in DEFAULT_APPEARANCE.items():
            app.setdefault(k, v)
        return app

    def set_appearance(self, **kwargs):
        app = self.get_appearance()
        app.update(kwargs)
        self._avatar_cache.clear()
        self._fav_cache.clear()
        try:
            from src.utils.player_sprite import clear_cache
            clear_cache()
        except Exception:
            pass

    # ================================================================
    # SPRITE DO JOGADOR
    # ================================================================
    def avatar_surface(self, target=96) -> Optional[pygame.Surface]:
        """
        Retorna o sprite do jogador num canvas target×target.

        O render_player_sprite entrega um canvas 32×32 com o conteúdo
        real (16×16) centralizado. Escalamos o canvas INTEIRO por fator
        inteiro (mesmo critério do código antigo), então o conteúdo
        aparece em (target / 2) px — ex: target=96 → conteúdo 48×48.
        """
        if target in self._avatar_cache:
            return self._avatar_cache[target]

        surf = None
        try:
            from src.utils.player_sprite import render_player_sprite

            base = render_player_sprite(self.get_appearance(), size=(32, 32))

            n = max(1, target // 32)
            scaled_size = 32 * n
            scaled = pygame.transform.scale(base, (scaled_size, scaled_size))

            canvas = pygame.Surface((target, target), pygame.SRCALPHA)
            ox = (target - scaled_size) // 2
            oy = (target - scaled_size) // 2
            canvas.blit(scaled, (ox, oy))
            surf = canvas
        except Exception as e:
            print(f"[PROFILE] avatar erro: {e}")

        self._avatar_cache[target] = surf
        return surf

    # ================================================================
    # PET — mesma fórmula do game scene
    # ================================================================
    def pet_frames(self, target_size: int = 192):
        """
        Retorna (frames_by_anim, pid, shiny).

        Reproduz EXATAMENTE a fórmula do game scene:
            tamanho_no_canvas = frame_size × zoom × TILE_SCALE
        """
        fav = self.favorite_pokemon()
        if fav is None:
            return {}, None, False

        pid = fav.id
        shiny = getattr(fav, "is_shiny", False)
        key = (pid, shiny, target_size)
        if key in self._pet_frames_cache:
            return self._pet_frames_cache[key], pid, shiny

        # 1. frame_size real do pokémon (AnimData.xml)
        frame_size = 32
        try:
            raw_data = self.pokedex.get_raw_inmap_data(pid, shiny)
            anim_data = raw_data.get("anim_data", {}) or {}
            for info in anim_data.values():
                fw = info.get("frame_width")
                if fw:
                    frame_size = int(fw)
                    break
        except Exception as e:
            print(f"[PROFILE] pet_frames frame_size erro: {e}")

        # 2. Coleta frames disponíveis
        raw: dict = {}
        for anim_name in ("sleep", "idle", "walk", "hop", "dance"):
            frames = self._try_pet_anim(pid, shiny, anim_name)
            if frames:
                raw[anim_name] = list(frames)

        if not raw:
            try:
                anims = self.pokedex.get_inmap_animation(pid, shiny)
                walk = anims.get("down") or anims.get("up") or []
                if walk:
                    raw["walk"] = list(walk)
                    raw["idle"] = list(walk)
            except Exception as e:
                print(f"[PROFILE] fallback inmap falhou: {e}")

        if not raw:
            return {}, None, False

        # 3. Escala
        scale = self.PET_CAMERA_ZOOM * self.PET_TILE_SCALE

        # 4. Normaliza
        def _normalize(surf: pygame.Surface) -> pygame.Surface:
            fw, fh = surf.get_size()

            if fw > frame_size or fh > frame_size:
                crop = pygame.Rect(0, 0, min(fw, frame_size),
                                   min(fh, frame_size))
                try:
                    surf = surf.subsurface(crop).copy()
                except ValueError:
                    surf = surf.copy()
                fw, fh = surf.get_size()

            nw = max(1, int(fw * scale))
            nh = max(1, int(fh * scale))

            if nw > target_size or nh > target_size:
                ratio = min(target_size / nw, target_size / nh)
                nw = max(1, int(nw * ratio))
                nh = max(1, int(nh * ratio))

            scaled = pygame.transform.scale(surf, (nw, nh))

            canvas = pygame.Surface((target_size, target_size),
                                    pygame.SRCALPHA)
            cx = (target_size - nw) // 2
            cy = (target_size - nh) // 2
            canvas.blit(scaled, (cx, cy))
            return canvas

        out = {name: [_normalize(f) for f in frames]
               for name, frames in raw.items()}

        self._pet_frames_cache[key] = out
        return out, pid, shiny

    def _try_pet_anim(self, pid: int, shiny: bool, anim_name: str) -> list:
        """Tenta pegar frames de uma animação em qualquer direção."""
        try:
            mgr = self.pokedex.sprite_manager
        except Exception:
            return []
        for d in ("down", "up", "left", "right"):
            try:
                frames = mgr.get_animation_frames(pid, shiny, anim_name, d)
            except Exception:
                frames = []
            if frames:
                return frames
        return []

    def clear_pet_cache(self):
        self._pet_frames_cache.clear()

    # ================================================================
    # SAVE
    # ================================================================
    def save_customization(self):
        try:
            meta = save_manager.save_data.setdefault("meta", {})
            slot = save_manager.current_save_file or 1
            name = meta.get("save_name", self.save_name())
            save_manager.save_game(self.player, save_name=name, slot=slot)
        except Exception as e:
            print(f"[PROFILE] save erro: {e}")

    @staticmethod
    def _hex(c) -> str:
        if not c:
            return "#000000"
        return f"#{c[0]:02X}{c[1]:02X}{c[2]:02X}"