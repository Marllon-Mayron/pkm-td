# src/scenes/game_scene/components/overlays/level_complete_scene/level_complete_scene.py
"""
Overlay Fase Completa — estilo FireRed (pergaminho).

Layout (~70% da tela):
  - Banner "FASE COMPLETA!" + estrelas + nome da fase
  - Coluna esquerda: POKÉMON DA FASE (3 colunas, scrollable, sprites grandes)
  - Coluna direita: cards (OURO/EXP/ITENS) + itens em card + nível + XP
  - Barra de XP do jogador ancorada no rodapé do painel (dourada)
  - Botões: REJOGAR / PRÓXIMA FASE / CONTINUAR
"""
import pygame

from src.ui.screen_template import StandardScreen
from src.ui.screen_loader import ScreenLoader
from src.ui.theme import FontBook
from src.ui.layout import fit_font, split_wrap
from src.data.item_bag_catalog import item_bag_catalog
from src.scenes.game_scene.components.overlays.level_complete_scene.level_complete_logic import (
    LevelCompleteLogic,
)


LAYOUT_PATH = "res/ui_layouts/level_complete.json"

# Grid de pokémon dentro do ListView — SEMPRE 3 colunas
POKEMON_COLS = 3
POKEMON_ROW_H = 130   # sprite + nome com folga


class LevelCompleteScene(StandardScreen):
    title = ""
    show_back_button = False

    # =================================================================
    def __init__(self, game, game_scene, stats=None):
        self.game_scene = game_scene
        self.logic = LevelCompleteLogic(game, game_scene, stats)

        # Snapshot do jogo como fundo
        try:
            w = game.screen_manager.window_width
            h = game.screen_manager.window_height
            self.background_image = pygame.Surface((w, h))
            game_scene.render(self.background_image)
            self.background_dim = 0
        except Exception as e:
            print(f"[LevelCompleteScene] snapshot falhou: {e}")
            self.background_image = None
            self.background_dim = 0

        # Pausa o game_scene
        game_scene.game_paused = True
        game_scene.paused = True
        if hasattr(game_scene, "wave_manager"):
            game_scene.wave_manager.paused = True

        super().__init__(game)

    # =================================================================
    def build(self):
        ScreenLoader.load(self, LAYOUT_PATH)
        self._populate_dynamic()
        self._wire_pokemon_list()
        self._wire_items_grid()

    def get_actions(self):
        return {
            "retry":      self._on_retry,
            "next_level": self._on_next,
            "menu":       self._on_menu,
        }

    # =================================================================
    # População
    # =================================================================
    def _populate_dynamic(self):
        # Título
        t = self.get("lbl_title")
        if t is not None:
            t.text = self.logic.get_title()

        # Nome da fase
        n = self.get("lbl_phase_name")
        if n is not None:
            n.text = self.logic.get_phase_name()

        # --- Cards ---
        gv = self.get("lbl_gold_val")
        if gv is not None:
            gv.text = self.logic.get_gold_text()

        bonus = self.get("lbl_bonus")
        if bonus is not None:
            bonus.text = self.logic.get_bonus_text()

        ev = self.get("lbl_exp_val")
        if ev is not None:
            ev.text = self.logic.get_exp_text()

        iv = self.get("lbl_items_val")
        if iv is not None:
            iv.text = self.logic.get_items_count_text()

        # --- Estrelas ---
        rating = self.get("rating_slots")
        if rating is not None:
            value, max_slots = self.logic.get_rating()
            rating.set_max(max_slots)
            rating.set_value(value)

        # --- Próxima fase ---
        nxt = self.get("lbl_next_phase")
        if nxt is not None:
            nxt.text = self.logic.get_next_phase_text()

        # --- Nível + Barra XP do jogador ---
        lvl = self.get("lbl_player_level")
        xp_bar = self.get("xp_bar")
        xp_txt = self.get("lbl_xp_text")
        lvl_up = self.get("lbl_levelup")

        try:
            level, xp_in, xp_span, ratio = self.game.player.get_level_progress()
        except Exception:
            level, xp_in, xp_span, ratio = 1, 0, 100, 0.0

        if lvl is not None:
            lvl.text = f"Nivel {level}"

        if xp_bar is not None:
            xp_bar.min_value = 0
            xp_bar.max_value = max(1, xp_span)
            xp_bar.value = xp_in

        if xp_txt is not None:
            xp_txt.text = f"{xp_in}/{xp_span} XP"

        if lvl_up is not None:
            lvl_up.text = ""

        # --- Esconde PRÓXIMA FASE se não houver ---
        btn_next = self.get("btn_next")
        btn_cont = self.get("btn_continue")
        if btn_next is not None and not self.logic.has_next_phase:
            btn_next.visible = False
            btn_next.enabled = False
            if btn_cont is not None:
                btn_cont.rect.centerx = btn_next.rect.centerx

    # =================================================================
    # Pokémon (ListView scrollable — SEMPRE 3 colunas)
    # =================================================================
    def _wire_pokemon_list(self):
        pl = self.get("pokemon_list")
        if pl is None:
            return

        ids = self.logic.get_pokemon_ids()
        n = len(ids)

        # Divide em linhas de POKEMON_COLS (=3)
        chunks = [ids[i:i + POKEMON_COLS]
                  for i in range(0, n, POKEMON_COLS)]

        pl.items = chunks
        pl.ROW_H = POKEMON_ROW_H
        pl.render_callback = self._render_pokemon_row
        pl.show_scrollbar = (n > POKEMON_COLS * 2)

        if n == 0:
            pl.visible = False
            t = self.get("lbl_pokemon_title")
            if t is not None:
                t.text = "SEM POKÉMON NA FASE"

    def _render_pokemon_row(self, idx, row_ids, screen, rect):
        if not row_ids:
            return True

        cell_w = rect.width // POKEMON_COLS
        for j, pid in enumerate(row_ids):
            cell = pygame.Rect(rect.x + j * cell_w, rect.y,
                               cell_w, rect.height)
            self._draw_pokemon_cell(screen, pid, cell)
        return True

    def _draw_pokemon_cell(self, screen, pid, cell):
        # Célula com margem interna
        inner = cell.inflate(-6, -6)

        pygame.draw.rect(screen, (232, 216, 168), inner, border_radius=8)
        pygame.draw.rect(screen, (138, 106, 42), inner, 2, border_radius=8)

        # Faixa interna clara (efeito de card)
        pygame.draw.rect(screen, (248, 236, 200),
                         (inner.x + 2, inner.y + 2,
                          inner.width - 4, inner.height - 4),
                         border_radius=6)

        player = self.game.player
        is_seen = (pid in getattr(player, "seen_pokemon", set())
                   or pid in getattr(player, "caught_pokemon", set()))

        portrait = None
        if is_seen:
            try:
                portrait = self.logic.pokedex.get_portrait(pid, "normal",
                                                           shiny=False)
            except Exception:
                portrait = None
            if portrait is None:
                try:
                    portrait = self.logic.pokedex.get_sprite(pid, "front",
                                                             shiny=False)
                except Exception:
                    portrait = None
        else:
            portrait = self._get_unknown_portrait()

        # Nome
        try:
            name = self.logic.pokedex.get_name(pid) if is_seen else "????"
        except Exception:
            name = "????"

        # Chip marrom embaixo pra ancorar o nome
        chip_h = max(20, int(inner.height * 0.18))
        chip = pygame.Rect(inner.x + 4,
                           inner.bottom - chip_h - 4,
                           inner.width - 8,
                           chip_h)
        pygame.draw.rect(screen, (90, 58, 24), chip, border_radius=5)
        pygame.draw.rect(screen, (138, 106, 42), chip, 1, border_radius=5)

        # ===== Ajuste automático do nome (sem cortar) =====
        def _font_factory(s):
            return FontBook.get(
                s, bold=True,
                name="pokemon-firered-leafgreen-font-recreation")

        start_size = max(11, int(chip_h * 0.72))
        font, _size = fit_font(
            name, _font_factory, start_size,
            chip.width - 8, chip.height - 2,
            min_size=9,
        )

        # Se ainda não couber em 1 linha, quebra
        if font.size(name)[0] > chip.width - 8:
            lines = split_wrap(name, font, chip.width - 8)
        else:
            lines = [name]

        line_h = font.get_height() + 1
        total_h = len(lines) * line_h - 1
        y0 = chip.centery - total_h // 2

        for i, ln in enumerate(lines):
            surf = font.render(ln, True, (240, 226, 184))
            screen.blit(surf, surf.get_rect(
                center=(chip.centerx, y0 + i * line_h + line_h // 2)))

        # Sprite ocupa TODO o espaço acima do chip
        sprite_area = pygame.Rect(
            inner.x + 6,
            inner.y + 6,
            inner.width - 12,
            chip.top - inner.y - 12,
        )
        sprite_size = min(sprite_area.width, sprite_area.height)
        if sprite_size < 24:
            sprite_size = 24

        if portrait:
            scaled = pygame.transform.scale(portrait,
                                            (sprite_size, sprite_size))
            pos = scaled.get_rect(center=sprite_area.center)
            screen.blit(scaled, pos)
        else:
            f = FontBook.get(int(sprite_size * 0.55), bold=True,
                             name="pokemon-firered-leafgreen-font-recreation")
            t = f.render("?", True, (90, 70, 40))
            screen.blit(t, t.get_rect(center=sprite_area.center))

    def _get_unknown_portrait(self):
        if getattr(self, "_unknown_cache", None) is not None:
            return self._unknown_cache
        try:
            from src.config.paths import RES_PATH
            p = RES_PATH / "PokemonSprites" / "Portrait" / "Unknow.png"
            if p.exists():
                self._unknown_cache = pygame.image.load(
                    str(p)).convert_alpha()
                return self._unknown_cache
        except Exception:
            pass
        surf = pygame.Surface((64, 64), pygame.SRCALPHA)
        surf.fill((200, 180, 140))
        pygame.draw.rect(surf, (138, 106, 42), (0, 0, 64, 64), 2)
        f = pygame.font.Font(None, 40)
        t = f.render("?", True, (90, 70, 40))
        surf.blit(t, t.get_rect(center=(32, 32)))
        self._unknown_cache = surf
        return surf

    # =================================================================
    # Grid de itens (cards com chip marrom + nome auto-ajustado)
    # =================================================================
    def _wire_items_grid(self):
        grid = self.get("grid_items")
        if grid is None:
            return

        items = self.logic.get_item_list()
        n = len(items)

        grid.items = list(range(n)) if n else []
        grid.render_callback = self._render_item_cell

        if n == 0:
            grid.visible = False
            t = self.get("lbl_items_title")
            if t is not None:
                t.text = "NENHUM ITEM RECEBIDO"
        elif n <= 5:
            grid.cols = max(1, n)
            grid.rows = 1
        elif n <= 10:
            grid.cols = 5
            grid.rows = 2
        else:
            grid.cols = 5
            grid.rows = (n + 4) // 5

    def _render_item_cell(self, idx, item, screen, rect):
        items = self.logic.get_item_list()
        if idx >= len(items):
            return True
        item_id, count = items[idx]

        inner = rect.inflate(-4, -4)

        # ---- Fundo do card ----
        pygame.draw.rect(screen, (232, 216, 168), inner, border_radius=8)
        pygame.draw.rect(screen, (138, 106, 42), inner, 2, border_radius=8)

        # ---- Faixa interna mais clara ----
        pygame.draw.rect(screen, (248, 236, 200),
                         (inner.x + 2, inner.y + 2,
                          inner.width - 4, inner.height - 4),
                         border_radius=6)

        # ---- Chip marrom (reserva espaço pro nome ANTES do sprite) ----
        chip_h = max(16, int(inner.height * 0.22))
        chip = pygame.Rect(inner.x + 3,
                           inner.bottom - chip_h - 3,
                           inner.width - 6,
                           chip_h)
        pygame.draw.rect(screen, (90, 58, 24), chip, border_radius=4)
        pygame.draw.rect(screen, (138, 106, 42), chip, 1, border_radius=4)

        # ---- Sprite (ocupa o espaço acima do chip) ----
        sprite_area = pygame.Rect(
            inner.x + 6,
            inner.y + 6,
            inner.width - 12,
            chip.top - inner.y - 12,
        )
        sprite_size = min(sprite_area.width, sprite_area.height)
        if sprite_size < 16:
            sprite_size = 16

        sprite = item_bag_catalog.get_sprite(item_id, scaled=True)
        if sprite:
            scaled = pygame.transform.scale(sprite,
                                            (sprite_size, sprite_size))
            pos = scaled.get_rect(center=sprite_area.center)
            screen.blit(scaled, pos)
        else:
            f = FontBook.get(11, bold=True,
                             name="pokemon-firered-leafgreen-font-recreation")
            t = f.render(item_id[:3].upper(), True, (90, 70, 40))
            screen.blit(t, t.get_rect(center=sprite_area.center))

        # ===== Nome do item — auto-fit (encolhe + quebra se preciso) =====
        data = item_bag_catalog.get_item(item_id)
        name = data["name"] if data else item_id

        def _font_factory(s):
            return FontBook.get(
                s, bold=True,
                name="pokemon-firered-leafgreen-font-recreation")

        start_size = max(10, int(chip_h * 0.72))
        font, _size = fit_font(
            name, _font_factory, start_size,
            chip.width - 6, chip.height - 2,
            min_size=8,
        )

        if font.size(name)[0] > chip.width - 6:
            lines = split_wrap(name, font, chip.width - 6)
        else:
            lines = [name]

        line_h = font.get_height() + 1
        total_h = len(lines) * line_h - 1
        y0 = chip.centery - total_h // 2

        for i, ln in enumerate(lines):
            surf = font.render(ln, True, (240, 226, 184))
            screen.blit(surf, surf.get_rect(
                center=(chip.centerx, y0 + i * line_h + line_h // 2)))

        # ---- Contador xN (canto superior direito) ----
        if count > 1:
            f = FontBook.get(max(10, int(inner.height * 0.16)), bold=True,
                             name="pokemon-firered-leafgreen-font-recreation")
            cs = f.render(f"x{count}", True, (255, 255, 255))
            pad_x, pad_y = 5, 2
            bg = pygame.Surface(
                (cs.get_width() + pad_x * 2, cs.get_height() + pad_y * 2),
                pygame.SRCALPHA)
            pygame.draw.rect(bg, (58, 34, 16, 230), bg.get_rect(),
                             border_radius=4)
            pygame.draw.rect(bg, (138, 106, 42, 255), bg.get_rect(),
                             1, border_radius=4)
            bx = inner.right - bg.get_width() + 2
            by = inner.top - 3
            screen.blit(bg, (bx, by))
            screen.blit(cs, (bx + pad_x, by + pad_y))

        return True

    # =================================================================
    # Ações
    # =================================================================
    def _on_retry(self, btn=None):
        self.logic.retry()

    def _on_next(self, btn=None):
        self.logic.advance()

    def _on_menu(self, btn=None):
        self.logic.quit_to_menu()

    # =================================================================
    # Ciclo de vida
    # =================================================================
    def on_back(self):
        self._on_menu()

    def _unpause(self):
        try:
            self.game_scene.game_paused = False
            self.game_scene.paused = False
            if hasattr(self.game_scene, "wave_manager"):
                self.game_scene.wave_manager.paused = False
        except Exception as e:
            print(f"[LevelCompleteScene] unpause: {e}")

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self._on_menu()
                return
        super().handle_event(event)