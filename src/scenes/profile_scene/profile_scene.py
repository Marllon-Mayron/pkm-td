# src/scenes/profile_scene/profile_scene.py

"""
Cena de Perfil do Jogador
- Insignias centralizadas em linha horizontal
- Cards neutros (sem cor)
- Destaques com cores de raridade
- Painel de Estatisticas com contadores de acoes
"""
import pygame
import random

from config.paths import SPRITES_PATH, ITEMS_PATH
from src.scenes.base_scene import BaseScene
from src.managers.sounds.sound_manager import sound_manager, SoundEffect
from src.data.achievement_data import ACHIEVEMENTS, AchievementRarity
from src.data.pokedex import Pokedex
from src.config.progress import progress_manager


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

# Cores neutras para os cards superiores
NEUTRAL_BORDER = (90, 100, 130)
NEUTRAL_ACCENT = (200, 210, 230)
NEUTRAL_VALUE = (240, 245, 255)


# =====================================================================
# BOTÃO
# =====================================================================
class ProfileButton:
    def __init__(self, x, y, width, height, text, color, hover_color,
                 callback, volume=0.3):
        self.relative_x = x
        self.relative_y = y
        self.relative_width = width
        self.relative_height = height

        self.rect = pygame.Rect(0, 0, 0, 0)
        self.text = text
        self.color = color
        self.hover_color = hover_color
        self.callback = callback
        self.is_hovered = False
        self.volume = volume

        self._font = None
        self._text_surface = None
        self.scale = 1.0
        self.target_scale = 1.0
        self.glow_alpha = 0
        self.glow_dir = 1

    def update_absolute_position(self, vw, vh, vx, vy):
        abs_x = vx + int(self.relative_x * vw)
        abs_y = vy + int(self.relative_y * vh)
        abs_width = int(self.relative_width * vw)
        abs_height = int(self.relative_height * vh)
        self.rect = pygame.Rect(abs_x, abs_y, abs_width, abs_height)

        font_size = max(14, int(vh * 0.022))
        self._font = pygame.font.Font(None, font_size)
        self._text_surface = self._font.render(self.text, True, (255, 255, 255))

    def update(self, dt):
        self.glow_alpha += self.glow_dir * 3
        if self.glow_alpha >= 100:
            self.glow_alpha = 100
            self.glow_dir = -1
        elif self.glow_alpha <= 0:
            self.glow_alpha = 0
            self.glow_dir = 1
        self.scale += (self.target_scale - self.scale) * min(1, dt * 15)

    def handle_event(self, event, consume=True):
        if event.type == pygame.MOUSEMOTION:
            was = self.is_hovered
            self.is_hovered = self.rect.collidepoint(event.pos)
            if self.is_hovered and not was:
                self.target_scale = 1.04
                sound_manager.play_effect(SoundEffect.CLICK, volume=self.volume)
            elif not self.is_hovered and was:
                self.target_scale = 1.0

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.is_hovered:
                sound_manager.play_effect(SoundEffect.CLICK, volume=self.volume)
                self.target_scale = 0.96
                return consume

        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self.is_hovered:
                self.target_scale = 1.04
                if self.callback:
                    self.callback()
                return consume

        return False

    def render(self, screen):
        if not self._text_surface:
            return

        scaled_rect = self.rect.copy()
        if self.scale != 1.0:
            w_off = int(self.rect.width * (self.scale - 1) / 2)
            h_off = int(self.rect.height * (self.scale - 1) / 2)
            scaled_rect = self.rect.inflate(w_off * 2, h_off * 2)
            scaled_rect.center = self.rect.center

        shadow = scaled_rect.copy()
        shadow.y += 3
        pygame.draw.rect(screen, (0, 0, 0), shadow, border_radius=8)

        color = self.hover_color if self.is_hovered else self.color

        if self.is_hovered:
            glow = pygame.Surface((scaled_rect.width, scaled_rect.height), pygame.SRCALPHA)
            pygame.draw.rect(glow, (*color[:3], self.glow_alpha),
                             glow.get_rect(), border_radius=8)
            screen.blit(glow, scaled_rect)

        pygame.draw.rect(screen, color, scaled_rect, border_radius=8)
        border_col = (255, 215, 0) if self.is_hovered else (90, 100, 130)
        pygame.draw.rect(screen, border_col, scaled_rect, 2, border_radius=8)

        text_scaled = pygame.transform.scale(
            self._text_surface,
            (int(self._text_surface.get_width() * self.scale),
             int(self._text_surface.get_height() * self.scale))
        )
        text_rect = text_scaled.get_rect(center=scaled_rect.center)
        screen.blit(text_scaled, text_rect)


# =====================================================================
# SCENE
# =====================================================================
class ProfileScene(BaseScene):
    """Cena de perfil do jogador"""

    def __init__(self, game, return_scene=None):
        super().__init__(game)
        self.player = game.player
        self.return_scene = return_scene or "menu"

        self.pokedex = Pokedex()

        self.badge_sprites = {}
        self._load_badge_sprites()

        self.buttons = []
        self._create_buttons()

        self._anim_timer = 0

        self.particles = []
        self._create_particles()

        # Painel
        self.show_stats_panel = False
        self._stats_scroll = 0.0
        self._stats_scroll_target = 0.0
        self._stats_panel_rect = None
        self._stats_close_rect = None

        # Bloqueio pós-fechamento (evita reabrir no mesmo frame)
        self._block_next_button_event = False

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
        self.total_pokemon = (
            len(self.pokedex.pokemon_data)
            if hasattr(self.pokedex, 'pokemon_data') else 151
        )

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

        self.featured_achievements = self._load_featured_achievements()

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

        unlocked_ids = self.player.achievements.get("unlocked", [])
        if not unlocked_ids:
            return [None, None, None]

        rarity_order = {
            AchievementRarity.LEGENDARY: 0,
            AchievementRarity.EPIC: 1,
            AchievementRarity.RARE: 2,
            AchievementRarity.UNCOMMON: 3,
            AchievementRarity.COMMON: 4,
        }
        unlocked = [ACHIEVEMENTS[i] for i in unlocked_ids if i in ACHIEVEMENTS]
        unlocked.sort(key=lambda a: rarity_order.get(a.rarity, 5))

        return [unlocked[i] if i < len(unlocked) else None for i in range(3)]

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

        result = []
        for key, value in counters.items():
            if value > 0:
                result.append({
                    "label": labels.get(key, key.replace("_", " ").title()),
                    "value": value,
                })
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
                            str(path)
                        ).convert_alpha()
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
        pygame.draw.circle(surf, (255, 255, 255), (size // 2, size // 2), size // 2 - 4, 3)
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

    # ==================================================================
    # BOTÕES / PARTÍCULAS
    # ==================================================================

    def _create_buttons(self):
        self.buttons = [
            ProfileButton(
                0.03, 0.93, 0.10, 0.05, "Voltar",
                (45, 45, 65), (75, 75, 105), self.go_back, volume=0.3
            ),
            ProfileButton(
                0.14, 0.93, 0.16, 0.05, "Galeria de Fotos",
                (55, 35, 75), (95, 55, 125), self.open_photo_gallery, volume=0.3
            ),
            ProfileButton(
                0.31, 0.93, 0.16, 0.05, "Estatisticas",
                (35, 55, 35), (65, 105, 65), self.open_stats_panel, volume=0.3
            ),
        ]

    def _create_particles(self):
        for _ in range(25):
            self.particles.append({
                'x': random.uniform(0, 1),
                'y': random.uniform(0, 1),
                'speed': random.uniform(0.2, 0.6),
                'size': random.randint(1, 3),
                'alpha': random.randint(40, 120),
                'phase': random.uniform(0, 6.28),
                'color': (
                    random.randint(150, 255),
                    random.randint(150, 255),
                    random.randint(200, 255),
                )
            })

    # ==================================================================
    # NAVEGAÇÃO
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
            self.game, return_scene=self.return_scene
        )

    def open_stats_panel(self):
        self.show_stats_panel = True
        self._stats_scroll = 0.0
        self._stats_scroll_target = 0.0

    def _close_stats_panel(self):
        self.show_stats_panel = False
        self._block_next_button_event = True

    # ==================================================================
    # EVENTOS
    # ==================================================================

    def handle_event(self, event):
        if self._block_next_button_event:
            self._block_next_button_event = False
            return

        if self.show_stats_panel:
            self._handle_stats_panel_event(event)
            return

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.go_back()
                return

        for button in self.buttons:
            if button.handle_event(event):
                return

    def _handle_stats_panel_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self._close_stats_panel()
                return
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
                self._close_stats_panel()
                return
            if self._stats_panel_rect and not self._stats_panel_rect.collidepoint(event.pos):
                self._close_stats_panel()
                return

    # ==================================================================
    # UPDATE
    # ==================================================================

    def fixed_update(self, dt):
        self._anim_timer += dt

        for button in self.buttons:
            button.update(dt)

        for p in self.particles:
            p['y'] += p['speed'] * dt * 0.03
            p['phase'] += dt * 0.5
            if p['y'] > 1:
                p['y'] = 0

        self.total_playtime = getattr(self.player, 'total_playtime', 0.0)

        if abs(self._stats_scroll - self._stats_scroll_target) > 0.5:
            self._stats_scroll += (
                self._stats_scroll_target - self._stats_scroll
            ) * min(1, dt * 12)
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

        for button in self.buttons:
            button.update_absolute_position(vw, vh, vx, vy)

        self._render_header(screen, vx, vy, vw, vh)

        # 4 cards (largura total)
        cards_y = vy + int(vh * 0.185)
        self._render_info_cards(screen, vx + 15, cards_y,
                                vw - 30, int(vh * 0.10))

        # Insignias (horizontal)
        badges_y = vy + int(vh * 0.30)
        self._render_badges_horizontal(screen, vx + 15, badges_y,
                                       vw - 30, int(vh * 0.12))

        # Destaques (largura total)
        featured_y = vy + int(vh * 0.45)
        self._render_featured_full_width(screen, vx + 15, featured_y,
                                         vw - 30, int(vh * 0.44))

        for button in self.buttons:
            button.render(screen)

        hint_font = pygame.font.Font(None, 16)
        hint = hint_font.render("ESC para voltar", True, (100, 100, 130))
        screen.blit(hint, (vx + vw - hint.get_width() - 15, vy + vh - 18))

        if self.show_stats_panel:
            self._render_stats_panel(screen, vx, vy, vw, vh)

    # ------------------------------------------------------------------
    # FUNDO
    # ------------------------------------------------------------------
    def _render_background(self, screen, vx, vy, vw, vh):
        for i in range(vh):
            t = i / vh
            r = int(15 + t * 15)
            g = int(18 + t * 20)
            b = int(30 + t * 30)
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
    # CABEÇALHO
    # ------------------------------------------------------------------
    def _render_header(self, screen, vx, vy, vw, vh):
        header_h = int(vh * 0.15)
        header_rect = pygame.Rect(vx + 15, vy + 12, vw - 30, header_h)

        surf = pygame.Surface((header_rect.width, header_rect.height), pygame.SRCALPHA)
        surf.fill((20, 25, 40, 220))
        screen.blit(surf, header_rect)
        pygame.draw.rect(screen, (80, 100, 160), header_rect, 2, border_radius=12)

        # Avatar
        av_size = min(header_h - 24, 84)
        av_x = header_rect.x + 18
        av_y = header_rect.y + (header_h - av_size) // 2

        av_rect = pygame.Rect(av_x, av_y, av_size, av_size)
        pygame.draw.rect(screen, (10, 14, 24), av_rect, border_radius=8)
        pygame.draw.rect(screen, (70, 90, 150), av_rect, 2, border_radius=8)

        letter_font = pygame.font.Font(None, int(av_size * 0.7))
        letter = letter_font.render("T", True, (70, 100, 170))
        screen.blit(letter, letter.get_rect(center=av_rect.center))

        # Nome / ID
        info_x = av_x + av_size + 18
        info_y = header_rect.y + 10

        name_font = pygame.font.Font(None, int(vh * 0.034))
        screen.blit(name_font.render("TREINADOR", True, (255, 215, 0)),
                    (info_x, info_y))

        id_font = pygame.font.Font(None, int(vh * 0.015))
        screen.blit(
            id_font.render(f"ID: {self.player_uuid[:16]}", True, (120, 130, 160)),
            (info_x, info_y + int(vh * 0.038))
        )

        total = self.total_playtime
        h = int(total // 3600)
        m = int((total % 3600) // 60)
        s = int(total % 60)

        stat_y = info_y + int(vh * 0.065)
        stat_font = pygame.font.Font(None, int(vh * 0.021))

        screen.blit(
            stat_font.render(f"Tempo: {h:02d}h {m:02d}m {s:02d}s",
                             True, (200, 210, 230)),
            (info_x, stat_y)
        )

        # XP à direita
        right_x = header_rect.right - 20
        xp_font = pygame.font.Font(None, int(vh * 0.024))
        xp_text = xp_font.render(
            f"XP: {self.player_xp:,}".replace(",", "."), True, (180, 220, 255)
        )
        screen.blit(xp_text, (right_x - xp_text.get_width(),
                              header_rect.y + 15))

        money_text = xp_font.render(
            f"$ {self.player_money:,}".replace(",", "."), True, (255, 215, 0)
        )
        screen.blit(money_text, (right_x - money_text.get_width(),
                                 header_rect.y + 15 + int(vh * 0.030)))

        team_font = pygame.font.Font(None, int(vh * 0.020))
        team = team_font.render(
            f"Time: {self.team_size}/6  |  Box: {self.pc_box_size}",
            True, (150, 200, 150)
        )
        screen.blit(team, (right_x - team.get_width(),
                           header_rect.y + 15 + int(vh * 0.060)))

    # ------------------------------------------------------------------
    # 4 CARDS (NEUTROS, SEM COR)
    # ------------------------------------------------------------------
    def _render_info_cards(self, screen, x, y, w, h):
        num = 4
        gap = 10
        card_w = (w - gap * (num - 1)) // num

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
            cx = x + i * (card_w + gap)
            self._draw_info_card(screen, cx, y, card_w, h, card)

    def _draw_info_card(self, screen, x, y, w, h, card):
        """Card neutro: borda cinza-azulada, valor branco"""
        rect = pygame.Rect(x, y, w, h)

        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        surf.fill((25, 30, 50, 220))
        screen.blit(surf, rect)

        # Borda neutra
        pygame.draw.rect(screen, NEUTRAL_BORDER, rect, 2, border_radius=10)

        # Faixa neutra no topo
        pygame.draw.rect(screen, NEUTRAL_ACCENT,
                         (x + 5, y + 5, w - 10, 3), border_radius=2)

        # Título
        title_font = pygame.font.Font(None, int(h * 0.18))
        title = title_font.render(card["title"], True, (180, 190, 210))
        screen.blit(title, (x + 12, y + 10))

        # Valor (branco neutro)
        value_font = pygame.font.Font(None, int(h * 0.42))
        value = value_font.render(str(card["value"]), True, NEUTRAL_VALUE)
        screen.blit(value, (x + 12, y + int(h * 0.34)))

        # Total
        if card["total"] is not None:
            total_font = pygame.font.Font(None, int(h * 0.20))
            total = total_font.render(f"/ {card['total']}", True, (120, 130, 150))
            screen.blit(
                total,
                (x + 15 + value.get_width(),
                 y + int(h * 0.34) + value.get_height() - total.get_height())
            )

            # Barra de progresso neutra
            if card["total"] > 0:
                progress = min(1.0, card["value"] / card["total"])
                bar_x = x + 12
                bar_y = y + h - 14
                bar_w = w - 24
                bar_h = 5
                pygame.draw.rect(screen, (40, 45, 60),
                                 (bar_x, bar_y, bar_w, bar_h), border_radius=3)
                if progress > 0:
                    pygame.draw.rect(
                        screen, NEUTRAL_ACCENT,
                        (bar_x, bar_y, int(bar_w * progress), bar_h),
                        border_radius=3
                    )

    # ------------------------------------------------------------------
    # INSÍGNIAS (HORIZONTAL, CENTRALIZADAS)
    # ------------------------------------------------------------------
    def _render_badges_horizontal(self, screen, x, y, w, h):
        """
        8 insignias em uma linha horizontal, todas CENTRALIZADAS no painel.
        O titulo fica no canto, mas os slots sao centralizados.
        """
        # Painel
        panel_rect = pygame.Rect(x, y, w, h)
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        surf.fill((20, 25, 40, 220))
        screen.blit(surf, panel_rect)
        pygame.draw.rect(screen, (80, 100, 160), panel_rect, 2, border_radius=12)

        # Titulo no canto superior esquerdo
        title_font = pygame.font.Font(None, int(h * 0.22))
        title = title_font.render("INSIGNIAS", True, (255, 215, 0))
        screen.blit(title, (x + 15, y + int(h * 0.15)))

        # Contador ao lado do titulo
        count_font = pygame.font.Font(None, int(h * 0.20))
        count = count_font.render(
            f"{self.badges_earned} / {self.total_badges}", True, (255, 215, 0)
        )
        screen.blit(count, (x + 15 + title.get_width() + 15, y + int(h * 0.15)))

        # ===== SLOTS CENTRALIZADOS NA ÁREA DO PAINEL =====
        # Area util: toda a largura do painel, com margens
        inner_padding = int(w * 0.02)
        slots_area_x = x + inner_padding
        slots_area_w = w - inner_padding * 2
        slots_area_h = h - int(h * 0.30)  # espaço abaixo do título

        gap = max(6, int(w * 0.005))

        # Slot size = altura disponivel, limitado pela largura
        slot_size_from_w = (slots_area_w - gap * 7) // 8
        slot_size_from_h = int(slots_area_h * 0.85)  # usa 85% da altura util
        slot_size = min(slot_size_from_w, slot_size_from_h)
        slot_size = max(slot_size, 40)

        # Centraliza horizontalmente: total dos slots + gaps
        total_w = slot_size * 8 + gap * 7
        start_x = x + (w - total_w) // 2  # <-- centralizado no painel inteiro

        # Centraliza verticalmente no espaço abaixo do título
        slots_area_y = y + int(h * 0.28)
        slots_y = slots_area_y + (h - (slots_area_y - y)) // 2 - slot_size // 2
        # ajuste fino para ficar mais no centro vertical do espaço restante
        slots_y = y + int(h * 0.30) + (h - int(h * 0.30) - slot_size) // 2

        for i in range(8):
            num = i + 1
            sx = start_x + i * (slot_size + gap)
            sy = slots_y

            slot_rect = pygame.Rect(sx, sy, slot_size, slot_size)
            has = num <= self.badges_earned

            if has:
                pygame.draw.rect(screen, (30, 42, 62), slot_rect, border_radius=6)
                pygame.draw.rect(screen, (255, 215, 0), slot_rect, 2, border_radius=6)

                inner = slot_size - 8
                scaled = self._scaled_badge(num, inner)
                if scaled:
                    # Centraliza o sprite dentro do slot
                    off_x = sx + (slot_size - inner) // 2
                    off_y = sy + (slot_size - inner) // 2
                    screen.blit(scaled, (off_x, off_y))
            else:
                pygame.draw.rect(screen, (22, 26, 36), slot_rect, border_radius=6)
                pygame.draw.rect(screen, (50, 55, 75), slot_rect, 1, border_radius=6)

                num_font = pygame.font.Font(None, int(slot_size * 0.45))
                num_text = num_font.render(str(num), True, (55, 60, 80))
                screen.blit(num_text, num_text.get_rect(center=slot_rect.center))

    # ------------------------------------------------------------------
    # DESTAQUES (LARGURA TOTAL, COM CORES DE RARIDADE)
    # ------------------------------------------------------------------
    def _render_featured_full_width(self, screen, x, y, w, h):
        # Titulo
        title_font = pygame.font.Font(None, int(h * 0.055))
        title = title_font.render("CONQUISTAS EM DESTAQUE", True, (255, 215, 0))
        screen.blit(title, (x, y))

        # Linha decorativa
        line_y = y + int(h * 0.09)
        pygame.draw.line(screen, (80, 100, 160),
                         (x, line_y), (x + w, line_y), 1)

        # Banners
        banners_y = line_y + int(h * 0.03)
        banners_h = h - (banners_y - y)

        gap = 15
        banner_w = (w - gap * 2) // 3

        for i, ach in enumerate(self.featured_achievements):
            bx = x + i * (banner_w + gap)
            self._draw_featured_banner(
                screen, bx, banners_y, banner_w, banners_h, ach
            )

    def _draw_featured_banner(self, screen, x, y, w, h, achievement):
        if achievement is None:
            rect = pygame.Rect(x, y, w, h)
            surf = pygame.Surface((w, h), pygame.SRCALPHA)
            surf.fill((20, 22, 35, 180))
            screen.blit(surf, rect)
            pygame.draw.rect(screen, (60, 65, 80), rect, 2, border_radius=12)

            font = pygame.font.Font(None, int(h * 0.15))
            text = font.render("Nenhuma conquista", True, (80, 85, 100))
            screen.blit(text, text.get_rect(
                center=(x + w // 2, y + h // 2 - 12)
            ))
            hint = pygame.font.Font(None, int(h * 0.10))
            h_text = hint.render("em destaque", True, (60, 65, 80))
            screen.blit(h_text, h_text.get_rect(
                center=(x + w // 2, y + h // 2 + 14)
            ))
            return

        rarity_color = achievement.rarity.color

        # Fundo com gradiente usando a cor da raridade (bem sutil)
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        for j in range(h):
            t = j / h
            r = int(25 + (rarity_color[0] - 25) * t * 0.35)
            g = int(30 + (rarity_color[1] - 30) * t * 0.35)
            b = int(45 + (rarity_color[2] - 45) * t * 0.35)
            pygame.draw.line(surf, (r, g, b, 230), (0, j), (w, j))
        screen.blit(surf, (x, y))

        rect = pygame.Rect(x, y, w, h)
        pygame.draw.rect(screen, rarity_color, rect, 3, border_radius=12)

        # ===== LEGENDA DE RARIDADE (badge colorida com texto branco) =====
        rarity_font = pygame.font.Font(None, int(h * 0.075))
        rarity_text = rarity_font.render(
            achievement.rarity.display_name.upper(), True, (255, 255, 255)
        )
        r_bg = pygame.Rect(
            x + w - rarity_text.get_width() - 24,
            y + 12,
            rarity_text.get_width() + 16,
            rarity_text.get_height() + 8
        )
        # Fundo colorido com a cor da raridade
        pygame.draw.rect(screen, rarity_color, r_bg, border_radius=6)
        # Borda mais clara
        bright_border = tuple(min(255, c + 60) for c in rarity_color)
        pygame.draw.rect(screen, bright_border, r_bg, 2, border_radius=6)
        # Texto branco
        screen.blit(rarity_text, (r_bg.x + 8, r_bg.y + 4))

        # Título
        t_font = pygame.font.Font(None, int(h * 0.12))
        t_text = t_font.render(achievement.title, True, (255, 255, 255))
        screen.blit(t_text, (x + 18, y + 18))

        # Descrição (wrap)
        d_font = pygame.font.Font(None, int(h * 0.075))
        desc = achievement.description
        max_chars = max(10, int(w / (h * 0.045)))
        words = desc.split()
        lines = []
        current = ""
        for word in words:
            if len(current + " " + word) <= max_chars:
                current += (" " if current else "") + word
            else:
                lines.append(current)
                current = word
        if current:
            lines.append(current)

        desc_y = y + int(h * 0.32)
        for i, line in enumerate(lines[:4]):
            l_text = d_font.render(line, True, (210, 220, 240))
            screen.blit(l_text, (x + 18, desc_y + i * int(h * 0.10)))

        # Data
        unlocked_data = self.player.achievements.get(
            "unlocked_data", {}
        ).get(achievement.id, {})
        if unlocked_data:
            date_font = pygame.font.Font(None, int(h * 0.065))
            date = date_font.render(
                f"Desbloqueado: {unlocked_data.get('unlocked_at', 'N/A')[:16]}",
                True, (170, 180, 200)
            )
            screen.blit(date, (x + 18, y + h - date.get_height() - 12))

    # ------------------------------------------------------------------
    # PAINEL DE ESTATÍSTICAS
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
        title = title_font.render("ESTATISTICAS DO TREINADOR",
                                  True, (255, 215, 0))
        screen.blit(title, (px + (pw - title.get_width()) // 2, py + 18))

        sub_font = pygame.font.Font(None, int(ph * 0.022))
        sub = sub_font.render(
            f"{len(self.achievement_counters)} registros de ações",
            True, (180, 200, 230)
        )
        screen.blit(sub, (px + (pw - sub.get_width()) // 2,
                          py + 18 + title.get_height() + 4))

        close_size = int(ph * 0.045)
        close_rect = pygame.Rect(
            panel_rect.right - close_size - 15,
            panel_rect.y + 15,
            close_size, close_size
        )
        self._stats_close_rect = close_rect

        mouse_pos = pygame.mouse.get_pos()
        close_hover = close_rect.collidepoint(mouse_pos)

        pygame.draw.rect(
            screen,
            (220, 70, 70) if close_hover else (140, 45, 45),
            close_rect, border_radius=8
        )
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
            empty_font = pygame.font.Font(None, int(ph * 0.028))
            empty = empty_font.render(
                "Nenhuma acao registrada ainda", True, (120, 130, 160)
            )
            screen.blit(empty, empty.get_rect(center=list_rect.center))
        else:
            visible_rows = max(1, list_h // row_h)
            total_rows = (len(counters) + cols - 1) // cols
            max_scroll = max(0, (total_rows - visible_rows) * row_h)

            self._stats_scroll_target = max(0, min(self._stats_scroll_target, max_scroll))
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
                v_text = v_font.render(str(counter["value"]), True, (255, 215, 0))
                screen.blit(v_text,
                            (cx + col_w - v_text.get_width() - 15, cy + 6))

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
            True, (120, 130, 160)
        )
        screen.blit(hint, (
            px + (pw - hint.get_width()) // 2,
            py + ph - hint.get_height() - 10
        ))