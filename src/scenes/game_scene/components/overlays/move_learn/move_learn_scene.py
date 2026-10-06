# src/scenes/game_scene/components/overlays/move_learn_scene.py
"""
Overlay MoveLearn — StandardScreen. Carrega JSON, popula dinamicamente.
"""
import pygame

from src.ui.screen_template import StandardScreen
from src.ui.screen_loader import ScreenLoader
from src.ui.theme import FontBook, parse_color
from src.scenes.game_scene.components.overlays.move_learn.move_learn_logic import (
    MoveLearnLogic,
)


LAYOUT_PATH = "res/ui_layouts/move_learn.json"


class MoveLearnScene(StandardScreen):
    title = ""
    show_back_button = False

    # =================================================================
    def __init__(self, game, game_scene, pokemon, new_move_name):
        self.game_scene = game_scene
        self.pokemon = pokemon
        self.new_move_name = new_move_name
        self.logic = MoveLearnLogic(game, pokemon, new_move_name)

        # Snapshot do game_scene como fundo
        try:
            w = game.screen_manager.window_width
            h = game.screen_manager.window_height
            self.background_image = pygame.Surface((w, h))
            game_scene.render(self.background_image)
            self.background_dim = 170
        except Exception as e:
            print(f"[MoveLearnScene] snapshot falhou: {e}")
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
        self._wire()

    def get_actions(self):
        return {
            "confirm":       self._on_confirm,
            "cancel":        self._on_cancel,
            "select_cancel": self._on_select_cancel,
        }

    # =================================================================
    # População
    # =================================================================
    def _populate_dynamic(self):
        # ----- Sprite -----
        spr = self.get("poke_sprite")
        if spr is not None:
            spr.surface = getattr(self.pokemon, "sprite", None)

        # ----- Nome / Nível -----
        name_lbl = self.get("poke_name")
        if name_lbl is not None:
            name_lbl.text = getattr(self.pokemon, "name", "?")

        lvl_lbl = self.get("poke_level")
        if lvl_lbl is not None:
            lvl_lbl.text = f"Nivel {getattr(self.pokemon, 'level', 1)}"

        # ----- HP -----
        hp = self.get("poke_hp")
        if hp is not None:
            hp.max_value = float(getattr(self.pokemon, "max_hp", 100) or 100)
            hp.value = float(getattr(self.pokemon, "current_hp", 0) or 0)

        # ----- Tipos -----
        types = list(getattr(self.pokemon, "types", []) or [])
        t1 = self.get("type_1")
        t2 = self.get("type_2")
        card = self.get("poke_card")

        if t1 is not None:
            if types:
                t1.visible = True
                t1.text = types[0].upper()
                t1.bg_color = parse_color(
                    self.logic.TYPE_COLORS.get(types[0].lower(), "#A8A878"))
            else:
                t1.visible = False

        if t2 is not None:
            if len(types) >= 2:
                t2.visible = True
                t2.text = types[1].upper()
                t2.bg_color = parse_color(
                    self.logic.TYPE_COLORS.get(types[1].lower(), "#A8A878"))
            else:
                t2.visible = False

        # 1 tipo só → centraliza no card
        if (t1 is not None and t2 is not None
                and t1.visible and not t2.visible
                and card is not None):
            t1.rect.centerx = card.rect.centerx

        # ----- Novo move (card destaque) -----
        self._populate_new_move()

        # ----- Grid de moves -----
        grid = self.get("moves_grid")
        if grid is not None:
            moves = self.logic.get_moves()
            n = len(moves)
            grid.items = list(range(n))
            grid.cols = 2
            grid.rows = max(1, (n + 1) // 2)
            grid.render_callback = self._render_move_cell

        # ----- Botão cancelar (estilo depende da seleção) -----
        self._refresh_cancel_button()

    def _populate_new_move(self):
        nm = self.logic.new_move
        if nm is None:
            return

        # Tipo (badge)
        type_lbl = self.get("new_move_type")
        if type_lbl is not None:
            type_lbl.text = str(nm.type).upper()
            type_lbl.bg_color = parse_color(
                self.logic.TYPE_COLORS.get(str(nm.type).lower(),
                                           "#A8A878"))

        # Nome
        name_lbl = self.get("new_move_name")
        if name_lbl is not None:
            name_lbl.text = nm.name.upper()

        # Categoria
        cat_lbl = self.get("new_move_cat")
        if cat_lbl is not None:
            cat = str(getattr(nm, "category", "physical")).upper()
            cat_lbl.text = cat
            cat_lbl.text_color = ((255, 120, 120) if cat == "PHYSICAL"
                                  else (120, 120, 255))

        # PWR / PP
        pwr_lbl = self.get("new_move_power")
        if pwr_lbl is not None:
            power = getattr(nm, "power", 0) or 0
            pwr_lbl.text = f"PWR: {power}" if power > 0 else "PWR: --"

        pp_lbl = self.get("new_move_pp")
        if pp_lbl is not None:
            pp = getattr(nm, "current_pp", 0) or 0
            pp_max = getattr(nm, "max_pp", 0) or 0
            pp_lbl.text = f"PP: {pp}/{pp_max}"

        # Descrição
        desc_lbl = self.get("new_move_desc")
        if desc_lbl is not None:
            desc = self.logic.get_move_description(nm)
            if len(desc) > 72:
                desc = desc[:69] + "..."
            desc_lbl.text = desc

    def _wire(self):
        grid = self.get("moves_grid")
        if grid is not None:
            grid.on_select = self._on_move_selected

    def _refresh_cancel_button(self):
        btn = self.get("btn_cancel")
        if btn is None:
            return
        # Selecionado: danger (vermelho vivo). Não selecionado: ghost (bege)
        btn.style_name = "danger" if self.logic.is_cancel_selected() else "ghost"

    # =================================================================
    # Callbacks
    # =================================================================
    def _on_move_selected(self, idx):
        self.logic.on_move_selected(idx)
        self._refresh_cancel_button()

    def _on_select_cancel(self, btn=None):
        self.logic.select_cancel()
        self._refresh_cancel_button()

    def _on_confirm(self, btn=None):
        self.logic.confirm_selection()
        self._close()

    def _on_cancel(self, btn=None):
        self.logic.cancel_selection()
        self._close()

    # =================================================================
    # Render customizado de cada célula do grid
    # =================================================================
    def _render_move_cell(self, idx, item, screen, rect):
        moves = self.logic.get_moves()
        if idx >= len(moves):
            return True
        move = moves[idx]

        is_sel = (idx == self.logic.selected_index)
        grid = self.get("moves_grid")
        is_hover = (grid is not None and idx == grid._hover_index)

        # ---- Fundo (pergaminho) ----
        if is_sel:
            bg = (200, 160, 100)
            border = (90, 60, 20)
            bw = 3
        elif is_hover:
            bg = (220, 200, 160)
            border = (140, 100, 50)
            bw = 2
        else:
            bg = (240, 226, 184)
            border = (138, 106, 42)
            bw = 1

        pygame.draw.rect(screen, bg, rect, border_radius=6)
        pygame.draw.rect(screen, border, rect, bw, border_radius=6)

        pad = 8

        # ---- Badge do tipo (esquerda) ----
        type_name = str(getattr(move, "type", "normal")).lower()
        type_color = parse_color(
            self.logic.TYPE_COLORS.get(type_name, "#A8A878"))

        badge_w = 48
        badge_h = rect.height - pad * 2
        badge_rect = pygame.Rect(rect.x + pad,
                                 rect.y + pad,
                                 badge_w, badge_h)
        pygame.draw.rect(screen, type_color, badge_rect, border_radius=6)
        pygame.draw.rect(screen, (58, 34, 16), badge_rect, 1, border_radius=6)

        short = type_name.upper()[:8]
        bf = FontBook.get(12, bold=True,
                          name="pokemon-firered-leafgreen-font-recreation")
        bt = bf.render(short, True, (255, 255, 255))
        screen.blit(bt, bt.get_rect(center=badge_rect.center))

        # ---- Info à direita do badge ----
        info_x = badge_rect.right + 8
        info_w = rect.right - info_x - pad

        # Nome
        nf = FontBook.get(15, bold=is_sel,
                          name="pokemon-firered-leafgreen-font-recreation")
        name_color = (58, 34, 16) if is_sel else (58, 34, 16)
        nt = nf.render(str(getattr(move, "name", "?")).upper(), True,
                       name_color)
        screen.blit(nt, (info_x, rect.y + pad))

        # Linha de stats
        sf = FontBook.get(11,
                          name="pokemon-firered-leafgreen-font-recreation")
        power = getattr(move, "power", 0) or 0
        pp = getattr(move, "current_pp", 0) or 0
        pp_max = getattr(move, "max_pp", 0) or 0
        cat = str(getattr(move, "category", "physical")).upper()

        pwr_txt = f"PWR: {power}" if power > 0 else "PWR: --"
        cat_color = ((200, 60, 60) if cat == "PHYSICAL" else (60, 60, 200))

        t1 = sf.render(pwr_txt, True, (58, 34, 16))
        t2 = sf.render(f"PP: {pp}/{pp_max}", True, (58, 34, 16))
        t3 = sf.render(cat, True, cat_color)

        cx = info_x
        cy = rect.y + pad + 22
        screen.blit(t1, (cx, cy)); cx += t1.get_width() + 10
        screen.blit(t2, (cx, cy)); cx += t2.get_width() + 10
        screen.blit(t3, (cx, cy))

        # Descrição curta
        desc = self.logic.get_move_description(move)
        if len(desc) > 40:
            desc = desc[:37] + "..."
        df = FontBook.get(10,
                          name="pokemon-firered-leafgreen-font-recreation")
        dt = df.render(desc, True, (110, 80, 40))
        screen.blit(dt, (info_x, rect.y + pad + 42))

        return True

    # =================================================================
    # Teclado
    # =================================================================
    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self._on_cancel()
                return
            if event.key == pygame.K_RETURN:
                self._on_confirm()
                return

            moves = self.logic.get_moves()
            n = len(moves)
            if n == 0:
                super().handle_event(event)
                return

            cur = self.logic.selected_index

            # CIMA / BAIXO navega entre "linhas" (no grid 2 colunas)
            if event.key == pygame.K_UP:
                if cur == -1:
                    self.logic.on_move_selected(0)
                elif cur - 2 >= 0:
                    self.logic.on_move_selected(cur - 2)
                self._refresh_cancel_button()
                return

            if event.key == pygame.K_DOWN:
                if cur == -1:
                    self.logic.on_move_selected(0)
                elif cur + 2 < n:
                    self.logic.on_move_selected(cur + 2)
                else:
                    self.logic.select_cancel()
                self._refresh_cancel_button()
                return

            if event.key == pygame.K_LEFT:
                if cur == -1:
                    pass
                elif cur % 2 == 1:
                    self.logic.on_move_selected(cur - 1)
                self._refresh_cancel_button()
                return

            if event.key == pygame.K_RIGHT:
                if cur == -1:
                    self.logic.on_move_selected(0)
                elif cur % 2 == 0 and cur + 1 < n:
                    self.logic.on_move_selected(cur + 1)
                self._refresh_cancel_button()
                return

        super().handle_event(event)

    # =================================================================
    # Ciclo de vida
    # =================================================================
    def on_back(self):
        self._on_cancel()

    def _close(self):
        try:
            self.game_scene.game_paused = False
            self.game_scene.paused = False
            if hasattr(self.game_scene, "wave_manager"):
                self.game_scene.wave_manager.paused = False
        except Exception as e:
            print(f"[MoveLearnScene] unpause: {e}")

        self.game.current_scene = self.game_scene