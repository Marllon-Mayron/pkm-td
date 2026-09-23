# src/scenes/profile_scene/profile_scene.py

"""
Cena de Perfil do Jogador (v3 - responsivo, sem sobreposicao)
- Layout calculado em stack de cima pra baixo (cada painel sabe sua posicao)
- Legendas em areas reservadas (nunca sobre conteudo)
- Titulos truncados automaticamente para nao invadir badges
- Sem botoes extras: clique direto nos campos
"""
import pygame
import random

from src.config.paths import SPRITES_PATH, ITEMS_PATH
from src.scenes.base_scene import BaseScene
from src.managers.sounds.sound_manager import sound_manager, SoundEffect
from src.data.achievement_data import ACHIEVEMENTS, AchievementRarity
from src.data.pokedex import Pokedex
from src.config.progress import progress_manager
from src.managers.save_manager import save_manager


# =====================================================================
# CONSTANTES
# =====================================================================
GYM_PHASES = {
    "1-5": 1, "2-8": 2, "3-4": 3, "4-5": 4,
    "5-5": 5, "6-5": 6, "6-10": 7, "7-4": 8,
}

BADGE_SPRITES = [
    "rock-badge.png", "water-badge.png", "thunder-badge.png",
    "rainbow-badge.png", "poison-badge.png", "marsh-badge.png",
    "volcano-badge.png", "earth-badge.png",
]

BADGE_COLORS = {
    1: (180, 140, 80), 2: (80, 140, 220), 3: (240, 200, 60),
    4: (220, 120, 200), 5: (160, 80, 200), 6: (140, 100, 60),
    7: (220, 80, 40), 8: (140, 100, 60),
}

NEUTRAL_BORDER = (90, 100, 130)
NEUTRAL_ACCENT = (200, 210, 230)
NEUTRAL_VALUE = (240, 245, 255)

BACKGROUND_OPTIONS = {
    "default": {"name": "Padrao",     "top": (15, 18, 30), "bottom": (30, 38, 60), "accent": (80, 100, 160)},
    "forest":  {"name": "Floresta",   "top": (10, 22, 15), "bottom": (25, 55, 35), "accent": (80, 160, 100)},
    "ocean":   {"name": "Oceano",     "top": (8, 18, 32),  "bottom": (20, 50, 85), "accent": (80, 160, 220)},
    "volcano": {"name": "Vulcao",     "top": (28, 12, 10), "bottom": (60, 25, 20), "accent": (220, 100, 60)},
    "royal":   {"name": "Real",       "top": (25, 15, 38), "bottom": (55, 30, 75), "accent": (180, 120, 220)},
    "sunset":  {"name": "Por do Sol", "top": (32, 18, 15), "bottom": (75, 45, 30), "accent": (240, 160, 80)},
}
BACKGROUND_ORDER = ["default", "forest", "ocean", "volcano", "royal", "sunset"]

MAX_FEATURED_ACH = 3

# Cores de destaque
HIGHLIGHT = (255, 215, 0)


# =====================================================================
# UTIL
# =====================================================================
def truncate_text(text, font, max_width, ellipsis="..."):
    """Corta o texto com '...' se ultrapassar max_width."""
    if font.size(text)[0] <= max_width:
        return text
    ell_w = font.size(ellipsis)[0]
    if ell_w >= max_width:
        return ellipsis
    lo, hi = 0, len(text)
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if font.size(text[:mid])[0] + ell_w <= max_width:
            lo = mid
        else:
            hi = mid - 1
    return text[:lo] + ellipsis

def wrap_lines(text, font, max_width, max_lines=None):
    """
    Quebra o texto em linhas que caibam em max_width.
    Se max_lines for passado e o texto exceder, trunca a ultima linha com '...'.
    """
    words = (text or "").split()
    lines = []
    cur = ""
    for w in words:
        test = (cur + " " + w).strip()
        if font.size(test)[0] <= max_width:
            cur = test
        else:
            if cur:
                lines.append(cur)
                if max_lines is not None and len(lines) >= max_lines:
                    # Trunca a ultima linha ate caber com '...'
                    last = lines[-1]
                    while last and font.size(last + "...")[0] > max_width:
                        last = last[:-1]
                    lines[-1] = last + "..."
                    return lines
            cur = w
    if cur:
        lines.append(cur)
    return lines[:max_lines] if max_lines is not None else lines


def draw_panel(screen, rect, fill=(20, 25, 40, 220), border=(80, 100, 160),
               border_w=2, radius=12):
    """Desenha um painel com fundo semi-transparente e borda."""
    surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
    surf.fill(fill)
    screen.blit(surf, rect)
    if border:
        pygame.draw.rect(screen, border, rect, border_w, border_radius=radius)


# =====================================================================
# NAV BUTTON
# =====================================================================
class NavButton:
    def __init__(self, x, y, w, h, text, callback,
                 base_color=(45, 45, 65), hover_color=(75, 75, 105)):
        self.rel = (x, y, w, h)
        self.text = text
        self.callback = callback
        self.base_color = base_color
        self.hover_color = hover_color
        self.rect = pygame.Rect(0, 0, 0, 0)
        self.hovered = False
        self._font = None
        self._text_surf = None

    def update_pos(self, vw, vh, vx, vy):
        x, y, w, h = self.rel
        self.rect = pygame.Rect(
            vx + int(x * vw), vy + int(y * vh),
            int(w * vw), int(h * vh),
        )
        fs = max(13, int(vh * 0.021))
        self._font = pygame.font.Font(None, fs)
        self._text_surf = self._font.render(self.text, True, (255, 255, 255))

    def handle_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            self.hovered = self.rect.collidepoint(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                try:
                    sound_manager.play_effect(SoundEffect.CLICK, volume=0.3)
                except Exception:
                    pass
                return True
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self.rect.collidepoint(event.pos):
                if self.callback:
                    self.callback()
                return True
        return False

    def render(self, screen):
        if not self._text_surf:
            return
        color = self.hover_color if self.hovered else self.base_color
        shadow = self.rect.copy()
        shadow.y += 3
        pygame.draw.rect(screen, (0, 0, 0, 120), shadow, border_radius=8)
        pygame.draw.rect(screen, color, self.rect, border_radius=8)
        border = HIGHLIGHT if self.hovered else (90, 100, 130)
        pygame.draw.rect(screen, border, self.rect, 2, border_radius=8)
        screen.blit(self._text_surf,
                    self._text_surf.get_rect(center=self.rect.center))

class ProfileButton(NavButton):
    """
    Wrapper retrocompativel para NavButton.

    Mantem a assinatura antiga (x, y, w, h, text, color, hover_color, callback)
    usada por outras cenas (ex: photo_gallery_scene). Tambem expoe os
    metodos que o gallery chama (update_absolute_position, update).
    """
    def __init__(self, x, y, width, height, text, color, hover_color,
                 callback, volume=0.3):
        # NavButton espera: (x, y, w, h, text, callback, base_color, hover_color)
        super().__init__(x, y, width, height, text, callback, color, hover_color)
        self.volume = volume  # preserva o atributo para quem inspecionar

    def update_absolute_position(self, vw, vh, vx, vy):
        self.update_pos(vw, vh, vx, vy)

    def update(self, dt):
        # NavButton nao tem animacao propria — no-op mantem compatibilidade
        pass
# =====================================================================
# SCENE
# =====================================================================
class ProfileScene(BaseScene):
    def __init__(self, game, return_scene=None):
        super().__init__(game)
        self.player = game.player
        self.return_scene = return_scene or "menu"

        if not hasattr(self.player, 'profile_customization') or \
                not isinstance(self.player.profile_customization, dict):
            self.player.profile_customization = {
                "featured_achievements": [],
                "background_color": "default",
                "favorite_pokemon_id": None,
            }
        self.player.profile_customization.setdefault("featured_achievements", [])
        self.player.profile_customization.setdefault("background_color", "default")
        self.player.profile_customization.setdefault("favorite_pokemon_id", None)

        self.pokedex = Pokedex()
        self.badge_sprites = {}
        self._load_badge_sprites()

        self.nav_buttons = [
            NavButton(0.03, 0.936, 0.10, 0.046, "Voltar",
                      self.go_back, (45, 45, 65), (75, 75, 105)),
            NavButton(0.14, 0.936, 0.16, 0.046, "Galeria de Fotos",
                      self.open_photo_gallery, (55, 35, 75), (95, 55, 125)),
            NavButton(0.31, 0.936, 0.16, 0.046, "Estatisticas",
                      self.open_stats_panel, (35, 55, 35), (65, 105, 65)),
        ]

        self._anim_timer = 0
        self.particles = []
        self._create_particles()

        # Estados de modal
        self.show_stats_panel = False
        self.show_ach_picker = False
        self.show_bg_picker = False
        self.show_poke_picker = False
        self.show_name_input = False

        # Stats
        self._stats_scroll = 0.0
        self._stats_scroll_target = 0.0
        self._stats_panel_rect = None
        self._stats_close_rect = None

        # Name
        self._name_text = ""
        self._name_cursor = 0
        self._name_save_rect = None
        self._name_cancel_rect = None

        # Ach picker
        self._ach_draft = set()
        self._ach_scroll = 0.0
        self._ach_row_rects = []
        self._ach_save_rect = None
        self._ach_cancel_rect = None

        self._ach_dragging = False
        self._ach_drag_offset = 0
        self._ach_bar_rect = None
        self._ach_track_rect = None
        self._ach_bar_h = 0
        self._ach_max_scroll = 0.0

        # BG
        self._bg_draft = "default"
        self._bg_cell_rects = []
        self._bg_save_rect = None
        self._bg_cancel_rect = None

        # Poke picker
        self._poke_draft_id = None
        self._poke_scroll = 0.0
        self._poke_row_rects = []
        self._poke_save_rect = None
        self._poke_cancel_rect = None
        self._poke_remove_rect = None

        self._block_next_button_event = False

        # Hit areas — sempre as mesmas do ultimo render
        self._hit_name = pygame.Rect(0, 0, 0, 0)
        self._hit_avatar = pygame.Rect(0, 0, 0, 0)
        self._hit_palette = pygame.Rect(0, 0, 0, 0)
        self._hit_featured = pygame.Rect(0, 0, 0, 0)
        self._hit_favorite_card = pygame.Rect(0, 0, 0, 0)

        self._load_player_data()

    # ==================================================================
    # DADOS
    # ==================================================================
    def _load_player_data(self):
        p = self.player
        self.player_uuid = getattr(p, 'uuid', 'N/A')
        self.total_playtime = getattr(p, 'total_playtime', 0.0)
        self.seen_count = len(getattr(p, 'seen_pokemon', set()))
        self.caught_count = len(getattr(p, 'caught_pokemon', set()))
        self.total_pokemon = (len(self.pokedex.pokemon_data)
                              if hasattr(self.pokedex, 'pokemon_data') else 151)
        self.badges_earned = self._compute_badges_earned()
        self.total_badges = 8

        if hasattr(p, 'achievement_manager'):
            self.achievements_unlocked = p.achievement_manager.get_unlocked_count()
            self.achievements_total = p.achievement_manager.get_total_count()
        else:
            self.achievements_unlocked = 0
            self.achievements_total = len(ACHIEVEMENTS)

        self.player_xp = getattr(p, 'score', 0)
        self.player_money = getattr(p, 'money', 0)
        self.team_size = len(getattr(p, 'team', []))
        self.pc_box_size = len(getattr(p, 'pc_box', []))
        self.photo_count = self._count_photos()

        try:
            self.save_name = save_manager.save_data.get("meta", {}).get(
                "save_name", "Novo Jogo")
        except Exception:
            self.save_name = "Novo Jogo"

        self.featured_achievements = self._load_featured_achievements()
        self.favorite_pokemon = self._get_favorite_pokemon()
        self.achievement_counters = self._collect_achievement_counters()

    def _compute_badges_earned(self):
        earned = 0
        for phase_id in GYM_PHASES.keys():
            try:
                if progress_manager.is_phase_completed(phase_id):
                    earned += 1
            except Exception:
                pass
        return earned

    def _count_photos(self):
        photos_dir = SPRITES_PATH / "screenshots" / "player_screenshots"
        if not photos_dir.exists():
            return 0
        return len(list(photos_dir.glob("photo_*.png")))

    def _load_featured_achievements(self):
        if not hasattr(self.player, 'achievements'):
            return [None, None, None]
        custom = self.player.profile_customization.get("featured_achievements", [])
        if custom:
            result = [ACHIEVEMENTS.get(k, None) for k in custom[:MAX_FEATURED_ACH]]
            while len(result) < MAX_FEATURED_ACH:
                result.append(None)
            return result
        unlocked_ids = self.player.achievements.get("unlocked", [])
        if not unlocked_ids:
            return [None, None, None]
        rarity_order = {
            AchievementRarity.LEGENDARY: 0, AchievementRarity.EPIC: 1,
            AchievementRarity.RARE: 2, AchievementRarity.UNCOMMON: 3,
            AchievementRarity.COMMON: 4,
        }
        unlocked = [ACHIEVEMENTS[i] for i in unlocked_ids if i in ACHIEVEMENTS]
        unlocked.sort(key=lambda a: rarity_order.get(a.rarity, 5))
        return [unlocked[i] if i < len(unlocked) else None
                for i in range(MAX_FEATURED_ACH)]

    def _get_favorite_pokemon(self):
        fav_id = self.player.profile_customization.get("favorite_pokemon_id")
        if not fav_id:
            return None
        for p in getattr(self.player, 'team', []):
            if getattr(p, 'unique_id', None) == fav_id:
                return p
        return None

    def _get_front_sprite(self, pid, shiny, target_size):
        try:
            try:
                sprite = self.pokedex.get_sprite(pid, "front", shiny)
            except Exception:
                sprite = None
            if sprite is None:
                try:
                    sprite = self.pokedex.get_portrait(pid, "normal", shiny)
                except Exception:
                    sprite = None
            if sprite is None:
                return None
            w, h = sprite.get_size()
            scale = min(target_size / max(1, w), target_size / max(1, h))
            return pygame.transform.smoothscale(
                sprite, (max(1, int(w * scale)), max(1, int(h * scale))))
        except Exception:
            return None

    def _get_avatar_sprite(self, target_size):
        fav = self.favorite_pokemon
        if fav is None:
            return None
        return self._get_front_sprite(fav.id, getattr(fav, 'is_shiny', False),
                                      target_size)

    def _collect_achievement_counters(self):
        if not hasattr(self.player, 'achievement_manager'):
            return []
        am = self.player.achievement_manager
        counters = am._counters if hasattr(am, '_counters') else {}
        labels = {
            "capture_count": "Pokemon capturados",
            "heal_count": "Curas usadas",
            "evolution_count": "Evolucoes totais",
            "level_evolution_count": "Evolucoes por nivel",
            "stone_evolution_count": "Evolucoes por pedra",
            "happiness_evolution_count": "Evolucoes por felicidade",
            "weather_evolution_count": "Evolucoes por clima",
            "trade_evolution_count": "Evolucoes por troca",
            "shiny_capture_count": "Shinies capturados",
            "boss_defeated_count": "Chefes derrotados",
            "perfect_phase_count": "Fases perfeitas",
            "revive_count": "Revives usados",
            "rare_candy_count": "Rare Candies usados",
            "escaperope_use_count": "Escape Ropes usados",
            "escaperope_last_stand_count": "Fugas no ultimo momento",
            "move_taught_count": "Movimentos ensinados",
            "antidote_count": "Antidotos usados",
            "awake_count": "Awakenings usados",
            "paralyze_heal_count": "Paralyze Heals usados",
            "burn_heal_count": "Burn Heals usados",
            "freeze_heal_count": "Ice Heals usados",
            "battle_item_use_count": "Itens de batalha usados",
            "battle_item_replace_count": "Itens substituidos",
            "friendball_capture_count": "Capturas com Friend Ball",
            "incubator_revive_count": "Fosseis revividos",
            "incubator_upgrade_count": "Upgrades de incubadora",
            "second_incubator_bought": "Incubadoras compradas",
            "weather_change_count": "Climas alterados",
            "weather_boosted_attack_count": "Ataques com boost de clima",
            "badge_count": "Insignias conquistadas (total)",
            "trade_count": "Trocas realizadas",
            "berry_consumed_count": "Berries consumidas",
            "capture_with_item_count": "Capturas com item",
            "evolution_blocked_count": "Evolucoes canceladas",
            "accuracy_buff_miss_count": "Erros com X Accuracy",
        }
        result = [{"label": labels.get(k, k.replace("_", " ").title()),
                   "value": v}
                  for k, v in counters.items() if v > 0]
        result.sort(key=lambda x: -x["value"])
        return result

    # ==================================================================
    # BADGES
    # ==================================================================
    def _load_badge_sprites(self):
        badge_path = ITEMS_PATH / "badge"
        for idx, filename in enumerate(BADGE_SPRITES):
            num = idx + 1
            for path in [badge_path / filename,
                         badge_path / filename.lower(),
                         badge_path / filename.upper()]:
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
        size = 128
        surf = pygame.Surface((size, size), pygame.SRCALPHA)
        color = BADGE_COLORS.get(num, (200, 200, 200))
        pygame.draw.circle(surf, color, (size // 2, size // 2), size // 2 - 4)
        pygame.draw.circle(surf, (255, 255, 255), (size // 2, size // 2),
                           size // 2 - 4, 3)
        font = pygame.font.Font(None, 64)
        text = font.render(str(num), True, (255, 255, 255))
        surf.blit(text, text.get_rect(center=(size // 2, size // 2)))
        return surf

    def _scaled_badge(self, num, target):
        sprite = self.badge_sprites.get(num)
        if not sprite:
            return None
        w, h = sprite.get_size()
        if w == target and h == target:
            return sprite
        if w >= target or h >= target:
            return pygame.transform.smoothscale(sprite, (target, target))
        factor = max(1, target // max(w, h))
        new_size = (w * factor, h * factor)
        scaled = pygame.transform.scale(sprite, new_size)
        result = pygame.Surface((target, target), pygame.SRCALPHA)
        result.blit(scaled, ((target - new_size[0]) // 2,
                             (target - new_size[1]) // 2))
        return result

    def _create_particles(self):
        for _ in range(25):
            self.particles.append({
                'x': random.uniform(0, 1), 'y': random.uniform(0, 1),
                'speed': random.uniform(0.2, 0.6), 'size': random.randint(1, 3),
                'alpha': random.randint(40, 120),
                'phase': random.uniform(0, 6.28),
                'color': (random.randint(150, 255), random.randint(150, 255),
                          random.randint(200, 255)),
            })

    # ==================================================================
    # NAV
    # ==================================================================
    def go_back(self):
        sound_manager.stop_music(fade_ms=300)
        if self.return_scene == "phase_select":
            from src.scenes.phase_selector.phase_select_scene import PhaseSelectScene
            self.game.phase_select_scene = PhaseSelectScene(self.game)
            self.game.current_scene = self.game.phase_select_scene
        else:
            from src.scenes.menu_scene import MenuScene
            self.game.current_scene = MenuScene(self.game)

    def open_photo_gallery(self):
        from src.scenes.profile_scene.photo_gallery_scene import PhotoGalleryScene
        self.game.current_scene = PhotoGalleryScene(
            self.game, return_scene=self.return_scene)

    def open_stats_panel(self):
        self.show_stats_panel = True
        self._stats_scroll = 0.0
        self._stats_scroll_target = 0.0

    # ==================================================================
    # MODAIS — ABRIR
    # ==================================================================
    def open_name_input(self):
        self.show_name_input = True
        self._name_text = self.save_name or "Novo Jogo"
        self._name_cursor = len(self._name_text)

    def open_ach_picker(self):
        self.show_ach_picker = True
        current = self.player.profile_customization.get("featured_achievements", [])
        self._ach_draft = set(k for k in current if k in ACHIEVEMENTS)
        self._ach_scroll = 0.0

    def open_bg_picker(self):
        self.show_bg_picker = True
        self._bg_draft = self.player.profile_customization.get(
            "background_color", "default")
        if self._bg_draft not in BACKGROUND_OPTIONS:
            self._bg_draft = "default"

    def open_poke_picker(self):
        self.show_poke_picker = True
        self._poke_draft_id = self.player.profile_customization.get(
            "favorite_pokemon_id")
        self._poke_scroll = 0.0

    # ==================================================================
    # MODAIS — APLICAR
    # ==================================================================
    def _save_customization(self):
        try:
            meta = save_manager.save_data.setdefault("meta", {})
            slot = save_manager.current_save_file or 1
            current_name = meta.get("save_name", self.save_name or "Novo Jogo")
            save_manager.save_game(self.player, save_name=current_name, slot=slot)
            self._load_player_data()
        except Exception as e:
            print(f"[PROFILE] Erro ao salvar customizacao: {e}")

    def _apply_name_input(self):
        new_name = (self._name_text or "").strip() or "Novo Jogo"
        new_name = new_name[:24]
        try:
            save_manager.save_data.setdefault("meta", {})["save_name"] = new_name
        except Exception as e:
            print(f"[PROFILE] Erro ao setar nome: {e}")
        self._save_customization()
        self.save_name = new_name
        self.show_name_input = False
        self._block_next_button_event = True

    def _apply_ach_picker(self):
        self.player.profile_customization["featured_achievements"] = \
            list(self._ach_draft)[:MAX_FEATURED_ACH]
        self._save_customization()
        self.show_ach_picker = False
        self._block_next_button_event = True

    def _apply_bg_picker(self):
        if self._bg_draft in BACKGROUND_OPTIONS:
            self.player.profile_customization["background_color"] = self._bg_draft
            self._save_customization()
        self.show_bg_picker = False
        self._block_next_button_event = True

    def _apply_poke_picker(self):
        self.player.profile_customization["favorite_pokemon_id"] = self._poke_draft_id
        self._save_customization()
        self.show_poke_picker = False
        self._block_next_button_event = True

    def _close_modal(self):
        self.show_stats_panel = False
        self.show_name_input = False
        self.show_ach_picker = False
        self.show_bg_picker = False
        self.show_poke_picker = False
        self._block_next_button_event = True

    # ==================================================================
    # LAYOUT (calculado em stack)
    # ==================================================================
    def _compute_layout(self, vx, vy, vw, vh):
        """Retorna dict com rects de cada painel. Tudo calculado em stack
        de cima pra baixo, sem sobreposicao."""
        margin_x = int(vw * 0.018)
        margin_y = int(vh * 0.020)
        gap = max(8, int(vh * 0.012))

        content_x = vx + margin_x
        content_w = vw - margin_x * 2

        y = vy + margin_y

        header_h = int(vh * 0.150)
        header = pygame.Rect(content_x, y, content_w, header_h)
        y = header.bottom + gap

        cards_h = int(vh * 0.100)
        cards = pygame.Rect(content_x, y, content_w, cards_h)
        y = cards.bottom + gap

        badges_h = int(vh * 0.115)
        badges = pygame.Rect(content_x, y, content_w, badges_h)
        y = badges.bottom + gap

        # Nav reserva
        nav_h = int(vh * 0.046)
        nav_y = vy + vh - margin_y - nav_h

        # Bottom area: preenche o espaco restante
        bottom_y = y
        bottom_h = nav_y - gap - bottom_y
        if bottom_h < int(vh * 0.20):
            bottom_h = int(vh * 0.20)

        fav_w = int(content_w * 0.24)
        inner_gap = max(8, int(vw * 0.010))

        favorite = pygame.Rect(content_x, bottom_y, fav_w, bottom_h)
        featured = pygame.Rect(favorite.right + inner_gap, bottom_y,
                               content_w - fav_w - inner_gap, bottom_h)

        return {
            "header": header,
            "cards": cards,
            "badges": badges,
            "favorite": favorite,
            "featured": featured,
            "nav_y": nav_y,
            "nav_h": nav_h,
        }

    # ==================================================================
    # EVENTOS
    # ==================================================================
    def handle_event(self, event):
        if self._block_next_button_event:
            self._block_next_button_event = False
            return

        if self.show_stats_panel:
            self._handle_stats_panel_event(event); return
        if self.show_name_input:
            self._handle_name_input_event(event); return
        if self.show_ach_picker:
            self._handle_ach_picker_event(event); return
        if self.show_bg_picker:
            self._handle_bg_picker_event(event); return
        if self.show_poke_picker:
            self._handle_poke_picker_event(event); return

        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.go_back(); return

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = event.pos
            if self._hit_palette.collidepoint(pos):
                self.open_bg_picker(); return
            if self._hit_avatar.collidepoint(pos):
                self.open_poke_picker(); return
            if self._hit_name.collidepoint(pos):
                self.open_name_input(); return
            if self._hit_favorite_card.collidepoint(pos):
                self.open_poke_picker(); return
            if self._hit_featured.collidepoint(pos):
                self.open_ach_picker(); return

        for b in self.nav_buttons:
            if b.handle_event(event):
                return

    def _handle_stats_panel_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self._close_modal(); return
            elif event.key == pygame.K_DOWN:
                self._stats_scroll_target += 40
            elif event.key == pygame.K_UP:
                self._stats_scroll_target -= 40
            elif event.key == pygame.K_PAGEDOWN:
                self._stats_scroll_target += 300
            elif event.key == pygame.K_PAGEUP:
                self._stats_scroll_target -= 300
        elif event.type == pygame.MOUSEWHEEL:
            self._stats_scroll_target -= event.y * 40
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._stats_close_rect and self._stats_close_rect.collidepoint(event.pos):
                self._close_modal(); return
            if self._stats_panel_rect and not self._stats_panel_rect.collidepoint(event.pos):
                self._close_modal(); return

    def _handle_name_input_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self._close_modal(); return
            if event.key == pygame.K_RETURN:
                self._apply_name_input(); return
            if event.key == pygame.K_BACKSPACE:
                if self._name_cursor > 0:
                    self._name_text = (self._name_text[:self._name_cursor - 1] +
                                       self._name_text[self._name_cursor:])
                    self._name_cursor -= 1
                return
            if event.key == pygame.K_DELETE:
                if self._name_cursor < len(self._name_text):
                    self._name_text = (self._name_text[:self._name_cursor] +
                                       self._name_text[self._name_cursor + 1:])
                return
            if event.key == pygame.K_LEFT:
                self._name_cursor = max(0, self._name_cursor - 1); return
            if event.key == pygame.K_RIGHT:
                self._name_cursor = min(len(self._name_text),
                                        self._name_cursor + 1); return
            if event.key == pygame.K_HOME:
                self._name_cursor = 0; return
            if event.key == pygame.K_END:
                self._name_cursor = len(self._name_text); return
            if event.unicode and event.unicode.isprintable():
                if len(self._name_text) < 24:
                    self._name_text = (self._name_text[:self._name_cursor] +
                                       event.unicode +
                                       self._name_text[self._name_cursor:])
                    self._name_cursor += 1
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._name_save_rect and self._name_save_rect.collidepoint(event.pos):
                self._apply_name_input(); return
            if self._name_cancel_rect and self._name_cancel_rect.collidepoint(event.pos):
                self._close_modal(); return

    def _handle_ach_picker_event(self, event):
        # Drag em andamento tem prioridade sobre qualquer outra coisa
        if self._ach_dragging:
            if event.type == pygame.MOUSEMOTION:
                self._drag_ach_scroll(event.pos[1])
                return
            if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                self._ach_dragging = False
                return

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self._close_modal();
                return
            if event.key == pygame.K_DOWN:
                self._ach_scroll = min(self._ach_scroll + 40,
                                       self._ach_max_scroll)
            elif event.key == pygame.K_UP:
                self._ach_scroll = max(0, self._ach_scroll - 40)
            return
        if event.type == pygame.MOUSEWHEEL:
            self._ach_scroll = max(0, min(self._ach_scroll - event.y * 40,
                                          self._ach_max_scroll))
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            # 1) Clique na barra -> inicia drag
            if self._ach_bar_rect and self._ach_bar_rect.collidepoint(event.pos):
                self._ach_dragging = True
                self._ach_drag_offset = event.pos[1] - self._ach_bar_rect.y
                try:
                    sound_manager.play_effect(SoundEffect.CLICK, volume=0.2)
                except Exception:
                    pass
                return
            # 2) Clique na track (fora da barra) -> salta + inicia drag
            if self._ach_track_rect and self._ach_track_rect.collidepoint(event.pos):
                self._ach_drag_offset = self._ach_bar_h // 2
                self._drag_ach_scroll(event.pos[1])
                self._ach_dragging = True
                return
            # 3) Botoes
            if self._ach_save_rect and self._ach_save_rect.collidepoint(event.pos):
                self._apply_ach_picker();
                return
            if self._ach_cancel_rect and self._ach_cancel_rect.collidepoint(event.pos):
                self._close_modal();
                return
            # 4) Linhas
            for key, rect in self._ach_row_rects:
                if rect.collidepoint(event.pos):
                    if key in self._ach_draft:
                        self._ach_draft.discard(key)
                    else:
                        if len(self._ach_draft) >= MAX_FEATURED_ACH:
                            self._ach_draft.pop()
                        self._ach_draft.add(key)
                    try:
                        sound_manager.play_effect(SoundEffect.CLICK, volume=0.25)
                    except Exception:
                        pass
                    return
            return

    def _drag_ach_scroll(self, mouse_y):
        """Atualiza _ach_scroll baseado na posicao Y do mouse durante o drag."""
        if not self._ach_track_rect or self._ach_max_scroll <= 0:
            return
        track = self._ach_track_rect
        span = max(1, track.height - self._ach_bar_h)
        new_y = mouse_y - self._ach_drag_offset
        new_y = max(track.y, min(new_y, track.y + span))
        ratio = (new_y - track.y) / span
        self._ach_scroll = ratio * self._ach_max_scroll

    def _handle_bg_picker_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self._close_modal(); return
            if event.key == pygame.K_RETURN:
                self._apply_bg_picker(); return
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._bg_save_rect and self._bg_save_rect.collidepoint(event.pos):
                self._apply_bg_picker(); return
            if self._bg_cancel_rect and self._bg_cancel_rect.collidepoint(event.pos):
                self._close_modal(); return
            for key, rect in self._bg_cell_rects:
                if rect.collidepoint(event.pos):
                    self._bg_draft = key
                    try:
                        sound_manager.play_effect(SoundEffect.CLICK, volume=0.25)
                    except Exception:
                        pass
                    return
            return

    def _handle_poke_picker_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self._close_modal(); return
            if event.key == pygame.K_DOWN:
                self._poke_scroll += 40
            elif event.key == pygame.K_UP:
                self._poke_scroll = max(0, self._poke_scroll - 40)
            return
        if event.type == pygame.MOUSEWHEEL:
            self._poke_scroll = max(0, self._poke_scroll - event.y * 40); return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._poke_save_rect and self._poke_save_rect.collidepoint(event.pos):
                self._apply_poke_picker(); return
            if self._poke_cancel_rect and self._poke_cancel_rect.collidepoint(event.pos):
                self._close_modal(); return
            if self._poke_remove_rect and self._poke_remove_rect.collidepoint(event.pos):
                self._poke_draft_id = None
                try:
                    sound_manager.play_effect(SoundEffect.CLICK, volume=0.25)
                except Exception:
                    pass
                return
            for uid, rect in self._poke_row_rects:
                if rect.collidepoint(event.pos):
                    self._poke_draft_id = uid
                    try:
                        sound_manager.play_effect(SoundEffect.CLICK, volume=0.25)
                    except Exception:
                        pass
                    return

    # ==================================================================
    # UPDATE
    # ==================================================================
    def fixed_update(self, dt):
        self._anim_timer += dt
        for p in self.particles:
            p['y'] += p['speed'] * dt * 0.03
            p['phase'] += dt * 0.5
            if p['y'] > 1:
                p['y'] = 0
        self.total_playtime = getattr(self.player, 'total_playtime', 0.0)
        if abs(self._stats_scroll - self._stats_scroll_target) > 0.5:
            self._stats_scroll += (self._stats_scroll_target - self._stats_scroll) * \
                min(1, dt * 12)
        else:
            self._stats_scroll = self._stats_scroll_target

    # ==================================================================
    # RENDER
    # ==================================================================
    def render(self, screen):
        vx = self.screen_manager.viewport_x
        vy = self.screen_manager.viewport_y
        vw = self.screen_manager.viewport_width
        vh = self.screen_manager.viewport_height

        self._render_background(screen, vx, vy, vw, vh)

        mouse = pygame.mouse.get_pos()
        L = self._compute_layout(vx, vy, vw, vh)

        self._render_header(screen, L["header"], mouse)
        self._render_info_cards(screen, L["cards"])
        self._render_badges(screen, L["badges"])
        self._render_favorite_card(screen, L["favorite"], mouse)
        self._render_featured_area(screen, L["featured"], mouse)

        # Nav
        for b in self.nav_buttons:
            b.update_pos(vw, vh, vx, vy)
            b.render(screen)

        hint_font = pygame.font.Font(None, 16)
        hint = hint_font.render("ESC para voltar", True, (110, 120, 150))
        screen.blit(hint, (vx + vw - hint.get_width() - 15, vy + vh - 16))

        # Modais
        if self.show_stats_panel:
            self._render_stats_panel(screen, vx, vy, vw, vh)
        elif self.show_name_input:
            self._render_name_input(screen, vx, vy, vw, vh)
        elif self.show_ach_picker:
            self._render_ach_picker(screen, vx, vy, vw, vh)
        elif self.show_bg_picker:
            self._render_bg_picker(screen, vx, vy, vw, vh)
        elif self.show_poke_picker:
            self._render_poke_picker(screen, vx, vy, vw, vh)

    # ------------------------------------------------------------------
    def _render_background(self, screen, vx, vy, vw, vh):
        bg_key = self.player.profile_customization.get("background_color", "default")
        bg = BACKGROUND_OPTIONS.get(bg_key, BACKGROUND_OPTIONS["default"])
        top, bottom = bg["top"], bg["bottom"]
        for i in range(vh):
            t = i / vh
            r = int(top[0] + (bottom[0] - top[0]) * t)
            g = int(top[1] + (bottom[1] - top[1]) * t)
            b = int(top[2] + (bottom[2] - top[2]) * t)
            pygame.draw.line(screen, (r, g, b), (vx, vy + i), (vx + vw, vy + i))
        for p in self.particles:
            x = vx + int(p['x'] * vw)
            y = vy + int(p['y'] * vh)
            alpha = int(p['alpha'] * (0.5 + 0.5 * (p['phase'] % 1)))
            size = p['size']
            glow = pygame.Surface((size * 6, size * 6), pygame.SRCALPHA)
            pygame.draw.circle(glow, (*p['color'], alpha // 3),
                               (size * 3, size * 3), size * 3)
            screen.blit(glow, (x - size * 3, y - size * 3))
            pygame.draw.circle(screen, (*p['color'], alpha), (x, y), size)

    # ------------------------------------------------------------------
    # HOVER
    # ------------------------------------------------------------------
    def _hover_glow(self, screen, rect, mouse, active=True, radius=12):
        """Desenha borda dourada pulsante SE mouse em cima. Desenhada na
        borda (nao cobre conteudo)."""
        if not active or not rect.collidepoint(mouse):
            return
        pulse = 2 if (self._anim_timer * 2) % 1 > 0.5 else 3
        pygame.draw.rect(screen, HIGHLIGHT, rect, pulse, border_radius=radius)

    # ------------------------------------------------------------------
    # HEADER
    # ------------------------------------------------------------------
    def _render_header(self, screen, rect, mouse):
        draw_panel(screen, rect, (20, 25, 40, 220), (80, 100, 160), 2, 12)

        pad = max(10, int(rect.height * 0.10))
        inner_h = rect.height - pad * 2

        # ===== Avatar =====
        av_size = min(inner_h, int(rect.height * 0.78))
        av_rect = pygame.Rect(rect.x + pad, rect.y + (rect.height - av_size) // 2,
                              av_size, av_size)
        pygame.draw.rect(screen, (10, 14, 24), av_rect, border_radius=10)

        fav_sprite = self._get_avatar_sprite(av_size - 12)
        if fav_sprite is not None:
            pygame.draw.rect(screen, HIGHLIGHT, av_rect, 3, border_radius=10)
            screen.blit(fav_sprite, fav_sprite.get_rect(center=av_rect.center))
            star_f = pygame.font.Font(None, 22)
            st = star_f.render("*", True, HIGHLIGHT)
            screen.blit(st, (av_rect.right - 16, av_rect.y + 2))
        else:
            pygame.draw.rect(screen, (70, 90, 150), av_rect, 2, border_radius=10)
            letter_font = pygame.font.Font(None, int(av_size * 0.65))
            letter = letter_font.render("T", True, (70, 100, 170))
            screen.blit(letter, letter.get_rect(center=av_rect.center))

        # Hint de trocar favorito — SEMPRE visivel, dentro do avatar area
        if fav_sprite is not None or True:
            cap_f = pygame.font.Font(None, max(10, int(rect.height * 0.075)))
            cap = cap_f.render("trocar" if fav_sprite is not None else "escolher",
                              True, (200, 210, 235) if av_rect.collidepoint(mouse)
                              else (130, 140, 170))
            cap_rect = cap.get_rect(center=(av_rect.centerx,
                                            av_rect.bottom + int(rect.height * 0.05)))
            # Se nao couber, coloca em cima
            if cap_rect.bottom > rect.bottom - 4:
                cap_rect = cap.get_rect(center=(av_rect.centerx,
                                                av_rect.top - int(rect.height * 0.05)))
            screen.blit(cap, cap_rect)

        self._hover_glow(screen, av_rect, mouse, True, 10)
        self._hit_avatar = av_rect

        # ===== Nome (clicavel) =====
        info_x = av_rect.right + pad + 6
        name_y = rect.y + pad

        name_font = pygame.font.Font(None, max(18, int(rect.height * 0.22)))
        name_surf = name_font.render(self.save_name, True, HIGHLIGHT)

        # Rect do nome (com algum padding para o lapis)
        pencil_w = int(rect.height * 0.10)
        name_click_rect = pygame.Rect(
            info_x - 4, name_y - 2,
            name_surf.get_width() + pencil_w + 14,
            name_surf.get_height() + 4,
        )
        self._hit_name = name_click_rect

        # Fundo hover
        if name_click_rect.collidepoint(mouse):
            hl = pygame.Surface((name_click_rect.width, name_click_rect.height),
                                pygame.SRCALPHA)
            hl.fill((255, 215, 0, 30))
            screen.blit(hl, name_click_rect)
            pygame.draw.rect(screen, HIGHLIGHT, name_click_rect, 1, border_radius=6)

        screen.blit(name_surf, (info_x, name_y))

        # Lapis
        pencil_x = info_x + name_surf.get_width() + 10
        pencil_y = name_y + name_surf.get_height() // 2
        p_col = HIGHLIGHT if name_click_rect.collidepoint(mouse) else (150, 140, 100)
        pygame.draw.polygon(screen, p_col, [
            (pencil_x, pencil_y - 8), (pencil_x + 6, pencil_y - 8),
            (pencil_x + 6, pencil_y + 4), (pencil_x, pencil_y + 4)])
        pygame.draw.polygon(screen, p_col, [
            (pencil_x, pencil_y + 4), (pencil_x + 6, pencil_y + 4),
            (pencil_x + 3, pencil_y + 9)])

        # Hint de editar nome — SEMPRE visivel, embaixo do nome
        edit_hint_f = pygame.font.Font(None, max(10, int(rect.height * 0.075)))
        edit_hint = edit_hint_f.render(
            "clique para editar o nome",
            True,
            (200, 210, 235) if name_click_rect.collidepoint(mouse) else (130, 140, 170))
        screen.blit(edit_hint, (info_x,
                                name_y + name_surf.get_height() + 2))

        # ID
        sub_y = name_y + name_surf.get_height() + edit_hint.get_height() + 6
        id_font = pygame.font.Font(None, max(11, int(rect.height * 0.075)))
        screen.blit(
            id_font.render(f"ID: {self.player_uuid[:14]}", True, (120, 130, 160)),
            (info_x, sub_y))

        # Tempo
        total = self.total_playtime
        h = int(total // 3600)
        m = int((total % 3600) // 60)
        s = int(total % 60)
        stat_font = pygame.font.Font(None, max(12, int(rect.height * 0.10)))
        screen.blit(
            stat_font.render(f"Tempo: {h:02d}h {m:02d}m {s:02d}s",
                             True, (200, 210, 230)),
            (info_x, sub_y + int(rect.height * 0.09)))

        # Favorito (linha)
        fav = self.favorite_pokemon
        if fav is not None:
            fav_font = pygame.font.Font(None, max(12, int(rect.height * 0.095)))
            fav_name = getattr(fav, 'custom_name', None) or fav.name
            if getattr(fav, 'is_shiny', False):
                fav_name += " *"
            screen.blit(
                fav_font.render(f"Favorito: {fav_name}  Lv.{fav.level}",
                                True, (255, 220, 120)),
                (info_x, sub_y + int(rect.height * 0.185)))

        # ===== Info direita (XP, money, time/box) =====
        right_x = rect.right - pad
        # Reserva espaco para o botao COR no canto inferior direito
        palette_size = int(rect.height * 0.42)
        palette_rect = pygame.Rect(
            rect.right - palette_size - pad,
            rect.bottom - palette_size - pad,
            palette_size, palette_size,
        )
        self._hit_palette = palette_rect

        xp_font = pygame.font.Font(None, max(14, int(rect.height * 0.16)))
        line_y = rect.y + pad
        for txt, col in [
            (f"XP: {self.player_xp:,}".replace(",", "."), (180, 220, 255)),
            (f"$ {self.player_money:,}".replace(",", "."), HIGHLIGHT),
        ]:
            ts = xp_font.render(txt, True, col)
            screen.blit(ts, (right_x - ts.get_width(), line_y))
            line_y += ts.get_height() + 2

        team_font = pygame.font.Font(None, max(12, int(rect.height * 0.13)))
        team = team_font.render(
            f"Time: {self.team_size}/6  |  Box: {self.pc_box_size}",
            True, (150, 200, 150))
        screen.blit(team, (right_x - team.get_width(), line_y + 2))

        # Paleta
        self._draw_palette_icon(screen, palette_rect, mouse)
        # Label abaixo
        pl_f = pygame.font.Font(None, max(10, int(rect.height * 0.075)))
        pl = pl_f.render("cor de fundo", True,
                         (200, 210, 235) if palette_rect.collidepoint(mouse)
                         else (130, 140, 170))
        screen.blit(pl, (palette_rect.centerx - pl.get_width() // 2,
                         palette_rect.y - pl.get_height() - 2))

    def _draw_palette_icon(self, screen, rect, mouse):
        hovered = rect.collidepoint(mouse)
        bg = (70, 80, 110) if hovered else (45, 50, 75)
        pygame.draw.rect(screen, bg, rect, border_radius=8)
        border = HIGHLIGHT if hovered else (110, 130, 180)
        pygame.draw.rect(screen, border, rect, 2, border_radius=8)

        pad = max(3, rect.width // 6)
        inner = rect.inflate(-pad * 2, -pad * 2)
        half_w = inner.width // 2
        half_h = inner.height // 2
        colors = [(220, 90, 90), (90, 200, 90), (90, 140, 220), (240, 200, 60)]
        for (px, py), col in zip(
            [(inner.x, inner.y), (inner.x + half_w, inner.y),
             (inner.x, inner.y + half_h), (inner.x + half_w, inner.y + half_h)],
            colors,
        ):
            pygame.draw.rect(screen, col, (px, py, half_w - 1, half_h - 1))

    # ------------------------------------------------------------------
    # 4 CARDS
    # ------------------------------------------------------------------
    def _render_info_cards(self, screen, rect):
        num = 4
        gap = max(8, int(rect.width * 0.008))
        card_w = (rect.width - gap * (num - 1)) // num
        cards = [
            {"title": "POKEDEX VISTOS",
             "value": self.seen_count, "total": self.total_pokemon},
            {"title": "POKEDEX CAPTURADOS",
             "value": self.caught_count, "total": self.total_pokemon},
            {"title": "CONQUISTAS",
             "value": self.achievements_unlocked, "total": self.achievements_total},
            {"title": "FOTOS TIRADAS",
             "value": self.photo_count, "total": None},
        ]
        for i, card in enumerate(cards):
            cr = pygame.Rect(rect.x + i * (card_w + gap), rect.y, card_w, rect.height)
            self._draw_info_card(screen, cr, card)

    def _draw_info_card(self, screen, rect, card):
        draw_panel(screen, rect, (25, 30, 50, 220), NEUTRAL_BORDER, 2, 10)
        pygame.draw.rect(screen, NEUTRAL_ACCENT,
                         (rect.x + 5, rect.y + 5, rect.width - 10, 3),
                         border_radius=2)

        title_font = pygame.font.Font(None, max(11, int(rect.height * 0.18)))
        title_s = title_font.render(card["title"], True, (180, 190, 210))
        screen.blit(title_s, (rect.x + 12, rect.y + 10))

        value_font = pygame.font.Font(None, max(18, int(rect.height * 0.42)))
        value_s = value_font.render(str(card["value"]), True, NEUTRAL_VALUE)
        screen.blit(value_s, (rect.x + 12, rect.y + int(rect.height * 0.34)))

        if card["total"] is not None:
            total_font = pygame.font.Font(None, max(11, int(rect.height * 0.20)))
            total_s = total_font.render(f"/ {card['total']}", True, (120, 130, 150))
            screen.blit(total_s,
                        (rect.x + 15 + value_s.get_width(),
                         rect.y + int(rect.height * 0.34) +
                         value_s.get_height() - total_s.get_height()))
            if card["total"] > 0:
                progress = min(1.0, card["value"] / card["total"])
                bar_x = rect.x + 12
                bar_y = rect.bottom - 14
                bar_w = rect.width - 24
                bar_h = 5
                pygame.draw.rect(screen, (40, 45, 60),
                                 (bar_x, bar_y, bar_w, bar_h), border_radius=3)
                if progress > 0:
                    pygame.draw.rect(screen, NEUTRAL_ACCENT,
                                     (bar_x, bar_y, int(bar_w * progress), bar_h),
                                     border_radius=3)

    # ------------------------------------------------------------------
    # BADGES
    # ------------------------------------------------------------------
    def _render_badges(self, screen, rect):
        draw_panel(screen, rect, (20, 25, 40, 220), (80, 100, 160), 2, 12)

        # Titulo + contador no topo esquerdo
        title_font = pygame.font.Font(None, max(13, int(rect.height * 0.22)))
        title = title_font.render("INSIGNIAS", True, HIGHLIGHT)
        screen.blit(title, (rect.x + 15, rect.y + int(rect.height * 0.10)))

        count_font = pygame.font.Font(None, max(12, int(rect.height * 0.20)))
        count = count_font.render(
            f"{self.badges_earned} / {self.total_badges}", True, HIGHLIGHT)
        screen.blit(count, (rect.x + 15 + title.get_width() + 12,
                            rect.y + int(rect.height * 0.10)))

        # Slots
        title_h = title.get_height() + int(rect.height * 0.14)
        slots_y_top = rect.y + title_h
        slots_area_h = rect.bottom - slots_y_top - int(rect.height * 0.10)
        inner_pad = int(rect.width * 0.02)
        slots_area_w = rect.width - inner_pad * 2
        gap = max(5, int(rect.width * 0.005))

        size_from_w = (slots_area_w - gap * 7) // 8
        size_from_h = int(slots_area_h * 0.95)
        slot_size = max(min(size_from_w, size_from_h), 30)

        total_w = slot_size * 8 + gap * 7
        start_x = rect.x + (rect.width - total_w) // 2
        slots_y = slots_y_top + (slots_area_h - slot_size) // 2

        for i in range(8):
            num = i + 1
            slot_rect = pygame.Rect(start_x + i * (slot_size + gap), slots_y,
                                    slot_size, slot_size)
            has = num <= self.badges_earned
            if has:
                pygame.draw.rect(screen, (30, 42, 62), slot_rect, border_radius=6)
                pygame.draw.rect(screen, HIGHLIGHT, slot_rect, 2, border_radius=6)
                inner = slot_size - 8
                scaled = self._scaled_badge(num, inner)
                if scaled:
                    screen.blit(scaled, (slot_rect.x + (slot_size - inner) // 2,
                                         slot_rect.y + (slot_size - inner) // 2))
            else:
                pygame.draw.rect(screen, (22, 26, 36), slot_rect, border_radius=6)
                pygame.draw.rect(screen, (50, 55, 75), slot_rect, 1, border_radius=6)
                num_font = pygame.font.Font(None, max(11, int(slot_size * 0.45)))
                num_text = num_font.render(str(num), True, (55, 60, 80))
                screen.blit(num_text, num_text.get_rect(center=slot_rect.center))

    # ------------------------------------------------------------------
    # FAVORITO
    # ------------------------------------------------------------------
    def _render_favorite_card(self, screen, rect, mouse):
        has_fav = self.favorite_pokemon is not None
        border_col = HIGHLIGHT if has_fav else (90, 100, 130)
        draw_panel(screen, rect, (25, 30, 50, 220), border_col, 2, 12)
        self._hover_glow(screen, rect, mouse, True, 12)
        self._hit_favorite_card = rect

        pad = max(10, int(rect.width * 0.06))

        # --- Header: titulo + hint em linha reservada ---
        title_font = pygame.font.Font(None, max(12, int(rect.height * 0.055)))
        title = title_font.render("FAVORITO", True, HIGHLIGHT)
        screen.blit(title, (rect.x + (rect.width - title.get_width()) // 2,
                            rect.y + pad))

        hint_font = pygame.font.Font(None, max(10, int(rect.height * 0.040)))
        hint_txt = "clique para trocar" if has_fav else "clique para escolher"
        hint_col = HIGHLIGHT if rect.collidepoint(mouse) else (140, 155, 185)
        hint = hint_font.render(hint_txt, True, hint_col)
        screen.blit(hint, (rect.x + (rect.width - hint.get_width()) // 2,
                           rect.y + pad + title.get_height() + 2))

        top_y = rect.y + pad + title.get_height() + hint.get_height() + 10

        # --- Footer: HP bar reservado ---
        hp_bar_h = 8
        hp_bar_margin = max(8, int(rect.height * 0.05))
        hp_bar_y = rect.bottom - hp_bar_margin - hp_bar_h

        # --- Meio: sprite + nome + level ---
        mid_h = hp_bar_y - top_y - 8
        if mid_h < 20:
            mid_h = 20

        if not has_fav:
            center = (rect.centerx, top_y + mid_h // 2)
            big_f = pygame.font.Font(None, max(24, int(mid_h * 0.55)))
            plus = big_f.render("+", True, (120, 140, 190))
            screen.blit(plus, plus.get_rect(center=center))
            return

        # Sprite ocupa ~55% do mid_h
        fav = self.favorite_pokemon
        sprite_max = int(mid_h * 0.68)
        sprite = self._get_front_sprite(
            fav.id, getattr(fav, 'is_shiny', False), sprite_max)

        text_area_h = mid_h - sprite_max - 6

        if sprite is not None:
            sprite_center = (rect.centerx, top_y + sprite_max // 2 + 2)
            frame = pygame.Rect(0, 0, sprite_max + 8, sprite_max + 8)
            frame.center = sprite_center
            pygame.draw.rect(screen, (12, 15, 24), frame, border_radius=10)
            pygame.draw.rect(screen, HIGHLIGHT, frame, 2, border_radius=10)
            screen.blit(sprite, sprite.get_rect(center=sprite_center))
            if getattr(fav, 'is_shiny', False):
                star_f = pygame.font.Font(None, max(14, int(sprite_max * 0.18)))
                st = star_f.render("*", True, (255, 240, 120))
                screen.blit(st, (frame.right - st.get_width() - 2, frame.y + 2))

        name_y = top_y + sprite_max + 8
        name = getattr(fav, 'custom_name', None) or fav.name
        name_f = pygame.font.Font(None, max(13, int(mid_h * 0.16)))
        name_s = name_f.render(name, True, (255, 255, 255))
        screen.blit(name_s, (rect.centerx - name_s.get_width() // 2, name_y))

        lv_f = pygame.font.Font(None, max(11, int(mid_h * 0.13)))
        lv_s = lv_f.render(f"Lv.{fav.level}", True, (255, 220, 120))
        screen.blit(lv_s, (rect.centerx - lv_s.get_width() // 2,
                           name_y + name_s.get_height() + 1))

        # HP bar
        hp_ratio = fav.current_hp / max(1, fav.max_hp)
        hp_w = rect.width - hp_bar_margin * 2
        hp_bar = pygame.Rect(rect.x + hp_bar_margin, hp_bar_y, hp_w, hp_bar_h)
        pygame.draw.rect(screen, (40, 45, 60), hp_bar, border_radius=4)
        if hp_ratio > 0:
            col = (100, 220, 120) if hp_ratio > 0.5 else \
                  (240, 200, 80) if hp_ratio > 0.2 else (220, 80, 80)
            pygame.draw.rect(screen, col,
                             (hp_bar.x, hp_bar.y,
                              int(hp_bar.width * hp_ratio), hp_bar.height),
                             border_radius=4)
        pygame.draw.rect(screen, (90, 100, 130), hp_bar, 1, border_radius=4)

        # HP texto
        hp_txt_f = pygame.font.Font(None, max(9, int(rect.height * 0.035)))
        hp_txt = hp_txt_f.render(f"{fav.current_hp}/{fav.max_hp}",
                                 True, (200, 210, 230))
        screen.blit(hp_txt, (rect.centerx - hp_txt.get_width() // 2,
                             hp_bar.y - hp_txt.get_height() - 1))

    # ------------------------------------------------------------------
    # DESTAQUES
    # ------------------------------------------------------------------
    def _render_featured_area(self, screen, rect, mouse):
        # Painel de fundo (deixa claro que e clicavel)
        draw_panel(screen, rect, (20, 25, 40, 200), (70, 85, 130), 2, 12)
        self._hover_glow(screen, rect, mouse, True, 12)
        self._hit_featured = rect

        pad = max(10, int(rect.width * 0.012))

        # Header reservado: titulo (esq) + hint (dir)
        title_f = pygame.font.Font(None, max(13, int(rect.height * 0.055)))
        title = title_f.render("CONQUISTAS EM DESTAQUE", True, HIGHLIGHT)
        screen.blit(title, (rect.x + pad, rect.y + pad))

        hint_f = pygame.font.Font(None, max(10, int(rect.height * 0.040)))
        hint_col = HIGHLIGHT if rect.collidepoint(mouse) else (140, 155, 185)
        hint = hint_f.render("clique para escolher", True, hint_col)
        screen.blit(hint, (rect.right - pad - hint.get_width(),
                           rect.y + pad + 2))

        # Linha
        line_y = rect.y + pad + title.get_height() + 6
        pygame.draw.line(screen, (80, 100, 160),
                         (rect.x + pad, line_y),
                         (rect.right - pad, line_y), 1)

        # Banners
        banners_y = line_y + 8
        banners_h = rect.bottom - banners_y - pad
        if banners_h < 20:
            banners_h = 20

        gap = max(8, int(rect.width * 0.010))
        banner_w = (rect.width - pad * 2 - gap * 2) // 3

        for i, ach in enumerate(self.featured_achievements):
            bx = rect.x + pad + i * (banner_w + gap)
            self._draw_featured_banner(
                screen, pygame.Rect(bx, banners_y, banner_w, banners_h), ach)

    def _draw_featured_banner(self, screen, rect, achievement):
        # ===== Estado vazio =====
        if achievement is None:
            draw_panel(screen, rect, (20, 22, 35, 180), (60, 65, 80), 2, 12)
            f = pygame.font.Font(None, max(11, int(rect.height * 0.14)))
            t = f.render("Nenhuma conquista", True, (80, 85, 100))
            screen.blit(t, t.get_rect(center=(rect.centerx, rect.centery - 8)))
            h = pygame.font.Font(None, max(10, int(rect.height * 0.09)))
            h_t = h.render("em destaque", True, (60, 65, 80))
            screen.blit(h_t, h_t.get_rect(center=(rect.centerx, rect.centery + 12)))
            return

        rarity_color = achievement.rarity.color
        bright_color = tuple(min(255, c + 60) for c in rarity_color)

        # ===== Fundo com gradiente sutil =====
        surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        for j in range(rect.height):
            t = j / max(1, rect.height)
            r = int(25 + (rarity_color[0] - 25) * t * 0.35)
            g = int(30 + (rarity_color[1] - 30) * t * 0.35)
            b = int(45 + (rarity_color[2] - 45) * t * 0.35)
            pygame.draw.line(surf, (r, g, b, 230), (0, j), (rect.width, j))
        screen.blit(surf, rect)
        pygame.draw.rect(screen, rarity_color, rect, 3, border_radius=12)

        # ===== TOP STRIP — a "prancheta" =====
        # Faixa colorida no topo do banner com a raridade centralizada
        inner = rect.inflate(-4, -4)
        strip_h = max(20, int(rect.height * 0.10))

        # Desenha o strip como retangulo colorido com cantos arredondados so em cima
        strip_surf = pygame.Surface((inner.width, strip_h), pygame.SRCALPHA)
        pygame.draw.rect(
            strip_surf, rarity_color,
            (0, 0, inner.width, strip_h),
            border_top_left_radius=10, border_top_right_radius=10,
        )
        # Linhas decorativas horizontais nos lados do texto (estilo prancheta)
        pygame.draw.line(strip_surf, bright_color,
                         (0, strip_h - 1), (inner.width, strip_h - 1), 2)
        screen.blit(strip_surf, (inner.x, inner.y))

        # Texto da raridade centralizado no strip
        strip_f = pygame.font.Font(None, max(12, strip_h - 4))
        strip_txt = achievement.rarity.display_name.upper()
        strip_s = strip_f.render(strip_txt, True, (255, 255, 255))
        strip_text_rect = strip_s.get_rect(
            center=(inner.x + inner.width // 2, inner.y + strip_h // 2)
        )
        # "Linhas" laterais tipo prancheta (─[EPICO]─)
        line_pad = 10
        line_y = strip_text_rect.centery
        pygame.draw.line(screen, (255, 255, 255),
                         (inner.x + line_pad, line_y),
                         (strip_text_rect.left - line_pad, line_y), 1)
        pygame.draw.line(screen, (255, 255, 255),
                         (strip_text_rect.right + line_pad, line_y),
                         (inner.right - line_pad, line_y), 1)
        # Sombra leve do texto pra dar destaque
        shadow = strip_f.render(strip_txt, True, (0, 0, 0, 100))
        screen.blit(shadow, (strip_text_rect.x + 1, strip_text_rect.y + 1))
        screen.blit(strip_s, strip_text_rect)

        # ===== Conteudo abaixo do strip =====
        pad = max(8, int(rect.width * 0.055))
        content_x = rect.x + pad
        content_w = rect.width - pad * 2
        y = inner.y + strip_h + 8

        # ----- Titulo responsivo (largura total, ate 2 linhas) -----
        title_f = pygame.font.Font(None, max(12, int(rect.height * 0.105)))
        title_lines = wrap_lines(achievement.title, title_f, content_w, max_lines=2)
        for line in title_lines:
            ls = title_f.render(line, True, (255, 255, 255))
            screen.blit(ls, (content_x, y))
            y += ls.get_height() + 1
        y += 4

        # Linha divisoria fina
        pygame.draw.line(screen, tuple(min(255, c + 40) for c in rarity_color),
                         (content_x, y), (content_x + content_w, y), 1)
        y += 6

        # ----- Data (reserva espaco no fundo) -----
        date_s = None
        date_h = 0
        unlocked_data = self.player.achievements.get(
            "unlocked_data", {}).get(achievement.id, {})
        if unlocked_data:
            date_f = pygame.font.Font(None, max(10, int(rect.height * 0.062)))
            date_s = date_f.render(
                f"Desbloqueado: {unlocked_data.get('unlocked_at', 'N/A')[:16]}",
                True, (170, 180, 200))
            date_h = date_s.get_height() + 4

        # ----- Descricao com wrap — respeita espaco restante -----
        d_font = pygame.font.Font(None, max(10, int(rect.height * 0.072)))
        max_desc_h = rect.bottom - pad - date_h - y
        line_h = d_font.get_height() + 1
        max_lines = max(1, max_desc_h // line_h)
        desc_lines = wrap_lines(achievement.description or "",
                                d_font, content_w, max_lines=max_lines)
        for i, line in enumerate(desc_lines):
            ls = d_font.render(line, True, (210, 220, 240))
            screen.blit(ls, (content_x, y + i * line_h))

        # ----- Data no fundo -----
        if date_s is not None:
            screen.blit(date_s, (content_x,
                                 rect.bottom - pad - date_s.get_height()))

    # ==================================================================
    # MODAIS
    # ==================================================================
    def _render_modal_overlay(self, screen, vx, vy, vw, vh,
                              w_ratio=0.75, h_ratio=0.82):
        overlay = pygame.Surface((vw, vh), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 210))
        screen.blit(overlay, (vx, vy))

        pw = int(vw * w_ratio)
        ph = int(vh * h_ratio)
        px = vx + (vw - pw) // 2
        py = vy + (vh - ph) // 2
        panel_rect = pygame.Rect(px, py, pw, ph)

        bg = pygame.Surface((pw, ph), pygame.SRCALPHA)
        for j in range(ph):
            t = j / ph
            r = int(20 + t * 10)
            g = int(25 + t * 15)
            b = int(45 + t * 20)
            pygame.draw.line(bg, (r, g, b, 240), (0, j), (pw, j))
        screen.blit(bg, panel_rect)
        pygame.draw.rect(screen, (100, 130, 200), panel_rect, 3, border_radius=14)
        return panel_rect

    def _draw_modal_title(self, screen, panel_rect, title_text, subtitle=None):
        title_font = pygame.font.Font(None, int(panel_rect.height * 0.045))
        title = title_font.render(title_text, True, HIGHLIGHT)
        screen.blit(title, (panel_rect.x + (panel_rect.width - title.get_width()) // 2,
                            panel_rect.y + 18))
        if subtitle:
            sub_font = pygame.font.Font(None, int(panel_rect.height * 0.022))
            sub = sub_font.render(subtitle, True, (180, 200, 230))
            screen.blit(sub, (panel_rect.x + (panel_rect.width - sub.get_width()) // 2,
                              panel_rect.y + 18 + title.get_height() + 4))

    def _draw_modal_button(self, screen, rect, label,
                           base_color=(60, 80, 130),
                           hover_color=(90, 120, 180),
                           danger=False, success=False):
        hovered = rect.collidepoint(pygame.mouse.get_pos())
        if danger:
            base_color, hover_color = (140, 45, 45), (200, 70, 70)
        elif success:
            base_color, hover_color = (45, 120, 60), (70, 170, 90)
        color = hover_color if hovered else base_color
        pygame.draw.rect(screen, color, rect, border_radius=8)
        pygame.draw.rect(screen, (220, 230, 255), rect, 2, border_radius=8)
        f = pygame.font.Font(None, max(14, int(rect.height * 0.55)))
        t = f.render(label, True, (255, 255, 255))
        screen.blit(t, t.get_rect(center=rect.center))

    # ----- NOME -----
    def _render_name_input(self, screen, vx, vy, vw, vh):
        panel = self._render_modal_overlay(screen, vx, vy, vw, vh, 0.55, 0.42)
        self._draw_modal_title(screen, panel, "EDITAR NOME DO SAVE",
                               "Esse nome aparece na tela de perfil")

        pad = int(panel.width * 0.08)
        inp_h = int(panel.height * 0.20)
        inp_rect = pygame.Rect(panel.x + pad, panel.y + int(panel.height * 0.32),
                               panel.width - pad * 2, inp_h)
        pygame.draw.rect(screen, (15, 18, 30), inp_rect, border_radius=8)
        pygame.draw.rect(screen, HIGHLIGHT, inp_rect, 2, border_radius=8)

        f = pygame.font.Font(None, int(inp_h * 0.55))
        display = self._name_text if self._name_text else "(vazio)"
        color = (240, 245, 255) if self._name_text else (120, 130, 150)
        ts = f.render(display, True, color)
        screen.blit(ts, (inp_rect.x + 14,
                         inp_rect.y + (inp_h - ts.get_height()) // 2))

        try:
            prefix = self._name_text[:self._name_cursor]
            pw = f.size(prefix)[0] if prefix else 0
            cx = inp_rect.x + 14 + pw
            pygame.draw.line(screen, HIGHLIGHT, (cx, inp_rect.y + 10),
                             (cx, inp_rect.bottom - 10), 2)
        except Exception:
            pass

        cnt_f = pygame.font.Font(None, int(panel.height * 0.030))
        cnt = cnt_f.render(f"{len(self._name_text)}/24", True, (140, 150, 180))
        screen.blit(cnt, (inp_rect.right - cnt.get_width() - 12,
                          inp_rect.bottom + 6))

        btn_h = int(panel.height * 0.16)
        btn_w = int(panel.width * 0.32)
        gap = int(panel.width * 0.06)
        sx = panel.x + (panel.width - (btn_w * 2 + gap)) // 2
        by = panel.bottom - btn_h - int(panel.height * 0.08)

        save_rect = pygame.Rect(sx, by, btn_w, btn_h)
        cancel_rect = pygame.Rect(sx + btn_w + gap, by, btn_w, btn_h)
        self._name_save_rect = save_rect
        self._name_cancel_rect = cancel_rect
        self._draw_modal_button(screen, save_rect, "SALVAR", success=True)
        self._draw_modal_button(screen, cancel_rect, "CANCELAR",
                                base_color=(80, 60, 60), hover_color=(140, 80, 80))

        hint_f = pygame.font.Font(None, int(panel.height * 0.028))
        hint = hint_f.render("ENTER salva  |  ESC cancela", True, (120, 130, 160))
        screen.blit(hint, (panel.x + (panel.width - hint.get_width()) // 2,
                           panel.bottom - hint.get_height() - 8))

    # ----- ACH PICKER -----
    def _render_ach_picker(self, screen, vx, vy, vw, vh):
        panel = self._render_modal_overlay(screen, vx, vy, vw, vh, 0.78, 0.85)
        self._draw_modal_title(
            screen, panel, "CONQUISTAS EM DESTAQUE",
            f"Selecione ate {MAX_FEATURED_ACH}  ({len(self._ach_draft)}/{MAX_FEATURED_ACH})")

        unlocked_keys = [k for k in self.player.achievements.get("unlocked", [])
                         if k in ACHIEVEMENTS]
        rarity_order = {
            AchievementRarity.LEGENDARY: 0, AchievementRarity.EPIC: 1,
            AchievementRarity.RARE: 2, AchievementRarity.UNCOMMON: 3,
            AchievementRarity.COMMON: 4,
        }
        unlocked_keys.sort(key=lambda k: rarity_order.get(ACHIEVEMENTS[k].rarity, 5))

        list_y = panel.y + int(panel.height * 0.18)
        list_h = panel.height - (list_y - panel.y) - int(panel.height * 0.20)
        list_rect = pygame.Rect(panel.x + 20, list_y, panel.width - 40, list_h)
        pygame.draw.rect(screen, (15, 20, 35), list_rect, border_radius=10)
        pygame.draw.rect(screen, (60, 80, 130), list_rect, 2, border_radius=10)
        self._ach_row_rects = []
        self._ach_bar_rect = None
        self._ach_track_rect = None
        self._ach_bar_h = 0
        self._ach_max_scroll = 0.0

        row_h = int(panel.height * 0.075)
        total_h = len(unlocked_keys) * row_h + 10
        max_scroll = max(0, total_h - list_rect.height)
        self._ach_max_scroll = max_scroll
        self._ach_scroll = max(0, min(self._ach_scroll, max_scroll))

        # Reserva espaco nas linhas se a scrollbar existir
        scrollbar_reserve = 22 if max_scroll > 0 else 0

        if not unlocked_keys:
            f = pygame.font.Font(None, int(panel.height * 0.032))
            t = f.render("Nenhuma conquista desbloqueada ainda.",
                         True, (140, 150, 180))
            screen.blit(t, t.get_rect(center=list_rect.center))
        else:
            old_clip = screen.get_clip()
            screen.set_clip(list_rect.inflate(-4, -4))

            for i, key in enumerate(unlocked_keys):
                ach = ACHIEVEMENTS[key]
                ry = list_rect.y + 8 + i * row_h - self._ach_scroll
                if ry + row_h < list_rect.y or ry > list_rect.bottom:
                    continue
                row_rect = pygame.Rect(
                    list_rect.x + 8, ry,
                    list_rect.width - 16 - scrollbar_reserve, row_h - 4)
                selected = key in self._ach_draft
                try:
                    rcol = ach.rarity.color
                except Exception:
                    rcol = (120, 120, 140)

                bg = tuple(min(255, int(c * 0.35) + 20) for c in rcol) if selected \
                    else (28, 32, 48)
                border = rcol if selected else (60, 70, 95)
                pygame.draw.rect(screen, bg, row_rect, border_radius=8)
                pygame.draw.rect(screen, border, row_rect,
                                 2 if selected else 1, border_radius=8)

                cb_size = int(row_h * 0.55)
                cb_rect = pygame.Rect(row_rect.x + 12,
                                      row_rect.y + (row_rect.height - cb_size) // 2,
                                      cb_size, cb_size)
                pygame.draw.rect(screen, (15, 18, 30), cb_rect, border_radius=4)
                pygame.draw.rect(screen, rcol if selected else (90, 100, 130),
                                 cb_rect, 2, border_radius=4)
                if selected:
                    pygame.draw.rect(screen, rcol,
                                     (cb_rect.x + 4, cb_rect.y + 4,
                                      cb_rect.width - 8, cb_rect.height - 8),
                                     border_radius=2)

                try:
                    rt = ach.rarity.display_name.upper()
                except Exception:
                    rt = "?"
                rb_f = pygame.font.Font(None, int(row_h * 0.30))
                rb_s = rb_f.render(rt, True, (255, 255, 255))
                rb_rect = pygame.Rect(
                    row_rect.right - rb_s.get_width() - 24,
                    row_rect.y + (row_rect.height - rb_s.get_height() - 8) // 2,
                    rb_s.get_width() + 16, rb_s.get_height() + 8)
                pygame.draw.rect(screen, rcol, rb_rect, border_radius=5)
                pygame.draw.rect(screen, (0, 0, 0), rb_rect, 1, border_radius=5)
                screen.blit(rb_s, (rb_rect.x + 8, rb_rect.y + 4))

                t_f = pygame.font.Font(None, int(row_h * 0.42))
                avail_w = rb_rect.x - (cb_rect.right + 12) - 8
                title_txt = truncate_text(ach.title, t_f, avail_w)
                t_s = t_f.render(title_txt, True, (240, 245, 255))
                screen.blit(t_s, (cb_rect.right + 12, row_rect.y + 8))

                d_f = pygame.font.Font(None, int(row_h * 0.32))
                desc = ach.description or ""
                avail_desc_w = rb_rect.x - (cb_rect.right + 12) - 8
                desc = truncate_text(desc, d_f, avail_desc_w)
                d_s = d_f.render(desc, True, (180, 195, 220))
                screen.blit(d_s, (cb_rect.right + 12,
                                  row_rect.bottom - d_s.get_height() - 6))

                self._ach_row_rects.append((key, row_rect))

            screen.set_clip(old_clip)

        # Botoes
        btn_h = int(panel.height * 0.075)
        btn_w = int(panel.width * 0.22)
        gap = int(panel.width * 0.04)
        sx = panel.x + (panel.width - (btn_w * 2 + gap)) // 2
        by = panel.bottom - btn_h - int(panel.height * 0.06)
        save_rect = pygame.Rect(sx, by, btn_w, btn_h)
        cancel_rect = pygame.Rect(sx + btn_w + gap, by, btn_w, btn_h)
        self._ach_save_rect = save_rect
        self._ach_cancel_rect = cancel_rect
        self._draw_modal_button(screen, save_rect, "SALVAR", success=True)
        self._draw_modal_button(screen, cancel_rect, "CANCELAR",
                                base_color=(80, 60, 60), hover_color=(140, 80, 80))

        # ====== SCROLLBAR (larga e arrastavel) ======
        if max_scroll > 0:
            bar_w = 14  # <-- mais larga
            bar_x = list_rect.right - bar_w - 6
            bar_h = max(44, int(list_rect.height *
                                (list_rect.height / max(1, total_h))))
            bar_h = min(bar_h, list_rect.height - 8)

            track_rect = pygame.Rect(bar_x - 3, list_rect.y + 4,
                                     bar_w + 6, list_rect.height - 8)
            self._ach_track_rect = track_rect
            self._ach_bar_h = bar_h

            # Track de fundo
            pygame.draw.rect(screen, (22, 27, 44), track_rect, border_radius=9)
            pygame.draw.rect(screen, (55, 70, 105), track_rect, 1, border_radius=9)

            # Posicao da barra
            ratio = self._ach_scroll / max_scroll if max_scroll > 0 else 0
            bar_y = track_rect.y + int((track_rect.height - bar_h) * ratio)
            bar_rect = pygame.Rect(track_rect.x + 2, bar_y,
                                   track_rect.width - 4, bar_h)
            self._ach_bar_rect = bar_rect

            mouse_pos = pygame.mouse.get_pos()
            hovered = bar_rect.collidepoint(mouse_pos) or self._ach_dragging
            bar_color = (150, 180, 240) if hovered else (100, 130, 200)
            bar_border = (210, 225, 255) if hovered else (140, 160, 200)
            pygame.draw.rect(screen, bar_color, bar_rect, border_radius=7)
            pygame.draw.rect(screen, bar_border, bar_rect, 2, border_radius=7)

            # Grip (3 linhas no centro) — ajuda o usuario a ver que e arrastavel
            if bar_h >= 32:
                gc_x = bar_rect.centerx
                gc_y = bar_rect.centery
                for off in (-6, 0, 6):
                    pygame.draw.line(screen, (35, 45, 70),
                                     (gc_x - 4, gc_y + off),
                                     (gc_x + 4, gc_y + off), 2)

    # ----- BG -----
    def _render_bg_picker(self, screen, vx, vy, vw, vh):
        panel = self._render_modal_overlay(screen, vx, vy, vw, vh, 0.72, 0.72)
        self._draw_modal_title(screen, panel, "COR DE FUNDO",
                               "Escolha um tema para a tela de perfil")

        cols, rows = 3, 2
        pad_x = int(panel.width * 0.05)
        grid_y = panel.y + int(panel.height * 0.20)
        cell_w = (panel.width - pad_x * 2) // cols
        cell_h = (panel.height - (grid_y - panel.y) - int(panel.height * 0.22)) // rows
        self._bg_cell_rects = []

        for i, key in enumerate(BACKGROUND_ORDER):
            col, row = i % cols, i // cols
            cx = panel.x + pad_x + col * cell_w
            cy = grid_y + row * cell_h
            cell = pygame.Rect(cx + 6, cy + 6, cell_w - 12, cell_h - 12)

            opt = BACKGROUND_OPTIONS[key]
            selected = (key == self._bg_draft)

            preview = pygame.Surface((cell.width, cell.height), pygame.SRCALPHA)
            top, bottom = opt["top"], opt["bottom"]
            for j in range(cell.height):
                t = j / max(1, cell.height)
                r = int(top[0] + (bottom[0] - top[0]) * t)
                g = int(top[1] + (bottom[1] - top[1]) * t)
                b = int(top[2] + (bottom[2] - top[2]) * t)
                pygame.draw.line(preview, (r, g, b), (0, j), (cell.width, j))
            screen.blit(preview, cell)

            pygame.draw.rect(screen, opt["accent"],
                             (cell.x + 8, cell.y + 8, cell.width - 16, 4),
                             border_radius=2)

            f = pygame.font.Font(None, int(cell.height * 0.20))
            name_s = f.render(opt["name"], True, (255, 255, 255))
            screen.blit(name_s, (cell.x + 10,
                                 cell.y + cell.height - name_s.get_height() - 10))

            if selected:
                pygame.draw.rect(screen, HIGHLIGHT, cell, 4, border_radius=10)
                check_f = pygame.font.Font(None, int(cell.height * 0.28))
                chk = check_f.render("*", True, HIGHLIGHT)
                screen.blit(chk, (cell.right - chk.get_width() - 12, cell.y + 6))
            else:
                pygame.draw.rect(screen, (80, 95, 130), cell, 2, border_radius=10)

            self._bg_cell_rects.append((key, cell))

        btn_h = int(panel.height * 0.10)
        btn_w = int(panel.width * 0.22)
        gap = int(panel.width * 0.04)
        sx = panel.x + (panel.width - (btn_w * 2 + gap)) // 2
        by = panel.bottom - btn_h - int(panel.height * 0.04)
        save_rect = pygame.Rect(sx, by, btn_w, btn_h)
        cancel_rect = pygame.Rect(sx + btn_w + gap, by, btn_w, btn_h)
        self._bg_save_rect = save_rect
        self._bg_cancel_rect = cancel_rect
        self._draw_modal_button(screen, save_rect, "SALVAR", success=True)
        self._draw_modal_button(screen, cancel_rect, "CANCELAR",
                                base_color=(80, 60, 60), hover_color=(140, 80, 80))

    # ----- POKE PICKER -----
    def _render_poke_picker(self, screen, vx, vy, vw, vh):
        panel = self._render_modal_overlay(screen, vx, vy, vw, vh, 0.72, 0.85)
        self._draw_modal_title(screen, panel, "POKEMON FAVORITO",
                               "Escolha um Pokemon do seu TIME")

        team = list(getattr(self.player, 'team', []))
        list_y = panel.y + int(panel.height * 0.18)
        list_h = panel.height - (list_y - panel.y) - int(panel.height * 0.22)
        list_rect = pygame.Rect(panel.x + 20, list_y, panel.width - 40, list_h)
        pygame.draw.rect(screen, (15, 20, 35), list_rect, border_radius=10)
        pygame.draw.rect(screen, (60, 80, 130), list_rect, 2, border_radius=10)
        self._poke_row_rects = []

        if not team:
            f = pygame.font.Font(None, int(panel.height * 0.032))
            t = f.render("Seu time esta vazio.", True, (140, 150, 180))
            screen.blit(t, t.get_rect(center=list_rect.center))
        else:
            old_clip = screen.get_clip()
            screen.set_clip(list_rect.inflate(-4, -4))
            row_h = int(panel.height * 0.105)
            total_h = len(team) * row_h + 10
            max_scroll = max(0, total_h - list_rect.height)
            self._poke_scroll = max(0, min(self._poke_scroll, max_scroll))

            for i, pk in enumerate(team):
                ry = list_rect.y + 8 + i * row_h - self._poke_scroll
                if ry + row_h < list_rect.y or ry > list_rect.bottom:
                    continue
                row_rect = pygame.Rect(list_rect.x + 8, ry,
                                       list_rect.width - 16, row_h - 6)
                selected = (getattr(pk, 'unique_id', None) == self._poke_draft_id)

                bg = (60, 50, 90) if selected else (30, 34, 50)
                border = HIGHLIGHT if selected else (70, 80, 110)
                pygame.draw.rect(screen, bg, row_rect, border_radius=8)
                pygame.draw.rect(screen, border, row_rect,
                                 3 if selected else 1, border_radius=8)

                ps = row_rect.height - 12
                pb = pygame.Rect(row_rect.x + 8,
                                 row_rect.y + (row_rect.height - ps) // 2,
                                 ps, ps)
                pygame.draw.rect(screen, (18, 20, 32), pb, border_radius=6)
                pygame.draw.rect(screen, (70, 75, 100), pb, 1, border_radius=6)

                try:
                    sprite = None
                    try:
                        sprite = self.pokedex.get_portrait(
                            pk.id, "normal", getattr(pk, 'is_shiny', False))
                    except Exception:
                        sprite = None
                    if sprite is None:
                        sprite = self.pokedex.get_sprite(
                            pk.id, "front", getattr(pk, 'is_shiny', False))
                    if sprite:
                        sc = pygame.transform.smoothscale(sprite, (ps - 6, ps - 6))
                        screen.blit(sc, (pb.x + (ps - sc.get_width()) // 2,
                                         pb.y + (ps - sc.get_height()) // 2))
                except Exception:
                    pass

                tx = pb.right + 14
                name = getattr(pk, 'custom_name', None) or pk.name
                if getattr(pk, 'is_shiny', False):
                    name += " *"

                # Marca favorito reservada na direita
                star_w = int(row_h * 0.30) if selected else 0
                avail_name_w = row_rect.right - tx - star_w - 20

                name_f = pygame.font.Font(None, int(row_h * 0.42))
                name_txt = truncate_text(name, name_f, avail_name_w)
                name_s = name_f.render(name_txt, True, (255, 255, 255))
                screen.blit(name_s, (tx, row_rect.y + 8))

                lv_f = pygame.font.Font(None, int(row_h * 0.32))
                lv_s = lv_f.render(
                    f"Lv.{pk.level}  HP: {pk.current_hp}/{pk.max_hp}",
                    True, (180, 195, 220))
                screen.blit(lv_s, (tx, row_rect.bottom - lv_s.get_height() - 8))

                if selected:
                    star_f = pygame.font.Font(None, int(row_h * 0.55))
                    star = star_f.render("*", True, HIGHLIGHT)
                    screen.blit(star, (row_rect.right - star.get_width() - 14,
                                       row_rect.y + 6))

                self._poke_row_rects.append((getattr(pk, 'unique_id', None),
                                             row_rect))
            screen.set_clip(old_clip)

        btn_h = int(panel.height * 0.075)
        btn_w = int(panel.width * 0.22)
        gap = int(panel.width * 0.03)
        sx = panel.x + (panel.width - (btn_w * 3 + gap * 2)) // 2
        by = panel.bottom - btn_h - int(panel.height * 0.055)
        remove_rect = pygame.Rect(sx, by, btn_w, btn_h)
        cancel_rect = pygame.Rect(sx + btn_w + gap, by, btn_w, btn_h)
        save_rect = pygame.Rect(sx + btn_w * 2 + gap * 2, by, btn_w, btn_h)
        self._poke_remove_rect = remove_rect
        self._poke_cancel_rect = cancel_rect
        self._poke_save_rect = save_rect
        self._draw_modal_button(screen, remove_rect, "REMOVER",
                                base_color=(80, 60, 60), hover_color=(140, 80, 80))
        self._draw_modal_button(screen, cancel_rect, "CANCELAR",
                                base_color=(60, 60, 80), hover_color=(90, 90, 120))
        self._draw_modal_button(screen, save_rect, "SALVAR", success=True)

        if team and max_scroll > 0:
            bar_x = list_rect.right - 8
            bar_h = max(30, int(list_rect.height *
                                (list_rect.height / max(1, total_h))))
            ratio = self._poke_scroll / max_scroll if max_scroll > 0 else 0
            bar_y = list_rect.y + int((list_rect.height - bar_h) * ratio)
            pygame.draw.rect(screen, (100, 130, 200),
                             (bar_x, bar_y, 5, bar_h), border_radius=3)

    # ------------------------------------------------------------------
    # STATS PANEL
    # ------------------------------------------------------------------
    def _render_stats_panel(self, screen, vx, vy, vw, vh):
        overlay = pygame.Surface((vw, vh), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 210))
        screen.blit(overlay, (vx, vy))

        pw = int(vw * 0.75)
        ph = int(vh * 0.82)
        px = vx + (vw - pw) // 2
        py = vy + (vh - ph) // 2
        panel_rect = pygame.Rect(px, py, pw, ph)
        self._stats_panel_rect = panel_rect

        bg = pygame.Surface((pw, ph), pygame.SRCALPHA)
        for j in range(ph):
            t = j / ph
            r = int(20 + t * 10)
            g = int(25 + t * 15)
            b = int(45 + t * 20)
            pygame.draw.line(bg, (r, g, b, 240), (0, j), (pw, j))
        screen.blit(bg, panel_rect)
        pygame.draw.rect(screen, (100, 130, 200), panel_rect, 3, border_radius=14)

        title_font = pygame.font.Font(None, int(ph * 0.045))
        title = title_font.render("ESTATISTICAS DO TREINADOR", True, HIGHLIGHT)
        screen.blit(title, (px + (pw - title.get_width()) // 2, py + 18))

        sub_font = pygame.font.Font(None, int(ph * 0.022))
        sub = sub_font.render(f"{len(self.achievement_counters)} registros de acoes",
                              True, (180, 200, 230))
        screen.blit(sub, (px + (pw - sub.get_width()) // 2,
                          py + 18 + title.get_height() + 4))

        close_size = int(ph * 0.045)
        close_rect = pygame.Rect(panel_rect.right - close_size - 15,
                                 panel_rect.y + 15, close_size, close_size)
        self._stats_close_rect = close_rect
        close_hover = close_rect.collidepoint(pygame.mouse.get_pos())
        pygame.draw.rect(screen,
                         (220, 70, 70) if close_hover else (140, 45, 45),
                         close_rect, border_radius=8)
        pygame.draw.rect(screen, (255, 130, 130), close_rect, 2, border_radius=8)
        x_font = pygame.font.Font(None, int(close_size * 0.85))
        x_text = x_font.render("X", True, (255, 255, 255))
        screen.blit(x_text, x_text.get_rect(center=close_rect.center))

        list_y = py + int(ph * 0.14)
        list_h = ph - (list_y - py) - int(ph * 0.08)
        list_rect = pygame.Rect(px + 20, list_y, pw - 40, list_h)
        pygame.draw.rect(screen, (15, 20, 35), list_rect, border_radius=10)
        pygame.draw.rect(screen, (60, 80, 130), list_rect, 2, border_radius=10)

        old_clip = screen.get_clip()
        screen.set_clip(list_rect.inflate(-4, -4))

        cols = 2
        col_gap = 15
        col_w = (list_rect.width - 30 - col_gap) // cols
        row_h = int(ph * 0.052)
        counters = self.achievement_counters

        if not counters:
            f = pygame.font.Font(None, int(ph * 0.028))
            t = f.render("Nenhuma acao registrada ainda", True, (120, 130, 160))
            screen.blit(t, t.get_rect(center=list_rect.center))
        else:
            visible_rows = max(1, list_h // row_h)
            total_rows = (len(counters) + cols - 1) // cols
            max_scroll = max(0, (total_rows - visible_rows) * row_h)
            self._stats_scroll_target = max(0, min(self._stats_scroll_target,
                                                    max_scroll))
            self._stats_scroll = max(0, min(self._stats_scroll, max_scroll))

            for idx, counter in enumerate(counters):
                col = idx % cols
                row = idx // cols
                cx = list_rect.x + 15 + col * (col_w + col_gap)
                cy = list_rect.y + 10 + row * row_h - self._stats_scroll
                if cy + row_h < list_rect.y or cy > list_rect.bottom:
                    continue
                if idx % 4 < 2:
                    row_bg = pygame.Rect(cx - 6, cy, col_w, row_h - 4)
                    pygame.draw.rect(screen, (25, 32, 50), row_bg, border_radius=6)
                l_font = pygame.font.Font(None, int(ph * 0.024))
                l_text = l_font.render(counter["label"], True, (200, 215, 240))
                screen.blit(l_text, (cx, cy + 8))
                v_font = pygame.font.Font(None, int(ph * 0.030))
                v_text = v_font.render(str(counter["value"]), True, HIGHLIGHT)
                screen.blit(v_text, (cx + col_w - v_text.get_width() - 15, cy + 6))

        screen.set_clip(old_clip)

        if counters:
            visible_rows = max(1, list_h // row_h)
            total_rows = (len(counters) + cols - 1) // cols
            if total_rows > visible_rows:
                max_scroll = (total_rows - visible_rows) * row_h
                bar_h = max(30, list_h * (visible_rows / total_rows))
                ratio = self._stats_scroll / max_scroll if max_scroll > 0 else 0
                bar_y = list_rect.y + ratio * (list_h - bar_h)
                bar_rect = pygame.Rect(list_rect.right - 8, bar_y, 5, bar_h)
                pygame.draw.rect(screen, (100, 130, 200), bar_rect, border_radius=3)

        hint_font = pygame.font.Font(None, int(ph * 0.020))
        hint = hint_font.render(
            "Mouse wheel / Setas: scroll  |  ESC ou X: fechar",
            True, (120, 130, 160))
        screen.blit(hint, (px + (pw - hint.get_width()) // 2,
                           py + ph - hint.get_height() - 10))