# src/scenes/game_scene/components/overlays/move_select_scene.py
"""
Overlay MoveSelect — agora uma cena (StandardScreen).
Carrega o layout JSON e preenche com dados do pokemon.
"""
import pygame

from src.ui.screen_template import StandardScreen
from src.ui.screen_loader import ScreenLoader
from src.ui.theme import FontBook, parse_color
from src.scenes.game_scene.components.overlays.move_select.move_select_logic import (
    MoveSelectLogic,
)


LAYOUT_PATH = "res/ui_layouts/move_select.json"


class MoveSelectScene(StandardScreen):
    # Sem título nem back button — overlay puro
    title = ""
    show_back_button = False

    # =================================================================
    def __init__(self, game, game_scene, pokemon):
        self.game_scene = game_scene
        self.pokemon = pokemon
        self.logic = MoveSelectLogic(game, pokemon)

        # Snapshot do frame atual do game_scene (é o "fundo" do overlay)
        try:
            w = game.screen_manager.window_width
            h = game.screen_manager.window_height
            self.background_image = pygame.Surface((w, h))
            game_scene.render(self.background_image)
            self.background_dim = 170
        except Exception as e:
            print(f"[MoveSelectScene] snapshot falhou: {e}")
            self.background_image = None
            self.background_dim = 0

        # Pausa o game_scene (ele fica parado por trás)
        game_scene.game_paused = True
        game_scene.paused = True
        if hasattr(game_scene, "wave_manager"):
            game_scene.wave_manager.paused = True

        super().__init__(game)

    # =================================================================
    def build(self):
        ScreenLoader.load(self, LAYOUT_PATH)
        self._populate_static()
        self._populate_dynamic()
        self._wire_lists()

    def get_actions(self):
        return {
            "confirm": self._on_confirm,
            "cancel":  self._on_cancel,
        }

    # =================================================================
    # População
    # =================================================================
    def _populate_static(self):
        """Nada estático por enquanto — o JSON já define tudo."""
        pass

    def _populate_dynamic(self):
        # ---- Sprite ----
        spr = self.get("poke_sprite")
        if spr is not None:
            spr.surface = getattr(self.pokemon, "sprite", None)

        # ---- Nome / Nível ----
        name_lbl = self.get("poke_name")
        if name_lbl is not None:
            name_lbl.text = getattr(self.pokemon, "name", "?")

        lvl_lbl = self.get("poke_level")
        if lvl_lbl is not None:
            lvl_lbl.text = f"Lv.{getattr(self.pokemon, 'level', 1)}"

        # ---- HP bar ----
        hp = self.get("poke_hp")
        if hp is not None:
            hp.max_value = float(getattr(self.pokemon, "max_hp", 100) or 100)
            hp.value = float(getattr(self.pokemon, "current_hp", 0) or 0)

        # ---- Tipos (badges) ----
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

        # Se só tem 1 tipo, centraliza o type_1 NO CARD (não no viewport)
        if (t1 is not None and t2 is not None
                and t1.visible and not t2.visible
                and card is not None):
            t1.rect.centerx = card.rect.centerx

        # ---- Lista de prioridades ----
        prio = self.get("prio_list")
        if prio is not None:
            prio.items = self.logic.get_priority_labels()
            prio.ROW_H = 52

        # ---- Lista de moves ----
        mv = self.get("moves_list")
        if mv is not None:
            moves = self.logic.get_moves()
            mv.items = list(range(len(moves)))
            mv.ROW_H = 92
            mv.render_callback = self._render_move_row

        # ---- Atualiza seleção atual na label ----
        self._refresh_selected_label()

    def _wire_lists(self):
        """Liga on_select das listas à logic."""
        prio = self.get("prio_list")
        if prio is not None:
            prio.on_select = self._on_priority_clicked
            prio.render_callback = self._render_priority_row

        mv = self.get("moves_list")
        if mv is not None:
            mv.on_select = self._on_move_clicked

    def _refresh_selected_label(self):
        lbl = self.get("selected_move")
        if lbl is None:
            return
        moves = self.logic.get_moves()
        if not moves:
            lbl.text = "SELECIONADO: (nenhum)"
            return
        i = max(0, min(self.logic.selected_move_index, len(moves) - 1))
        move = moves[i]
        lbl.text = f"SELECIONADO: {getattr(move, 'name', '?').upper()}"

    # =================================================================
    # Callbacks dos clicks
    # =================================================================
    def _on_priority_clicked(self, idx):
        self.logic.on_priority_selected(idx)
        self._refresh_selected_label()

    def _on_move_clicked(self, idx):
        self.logic.on_move_selected(idx)
        self._refresh_selected_label()

    def _on_confirm(self, btn=None):
        self.logic.confirm_selection()
        self._close()

    def _on_cancel(self, btn=None):
        self.logic.cancel_selection()
        self._close()

    # =================================================================
    # Render customizado das linhas
    # =================================================================
    def _render_priority_row(self, idx, item, screen, rect):
        """Desenha um item da lista de prioridades."""
        try:
            p = self.logic.PRIORITY_OPTIONS[idx]
        except IndexError:
            return True

        is_sel = (idx == self.logic.selected_priority_index)
        list_w = self.get("prio_list")
        is_hover = (list_w is not None and idx == list_w._hover_index)

        if is_sel:
            bg = (40, 60, 100, 210)
            border = (255, 215, 0, 255)
        elif is_hover:
            bg = (32, 46, 72, 190)
            border = (100, 150, 255, 255)
        else:
            bg = (25, 30, 50, 150)
            border = (60, 80, 120, 200)

        surf = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.rect(surf, bg, surf.get_rect(), border_radius=8)
        pygame.draw.rect(surf, border, surf.get_rect(),
                         2 if is_sel else 1, border_radius=8)
        screen.blit(surf, rect.topleft)

        # Nome
        name_font = FontBook.get(18, bold=is_sel,
                                 name="pokemon-firered-leafgreen-font-recreation")
        name_text = self.logic.PRIORITY_NAMES.get(p, "?")
        name_color = (255, 215, 0) if is_sel else (255, 255, 255)
        name_surf = name_font.render(name_text, True, name_color)
        screen.blit(name_surf, (rect.x + 12, rect.y + 6))

        # Descrição
        desc_font = FontBook.get(13,
                                 name="pokemon-firered-leafgreen-font-recreation")
        desc_text = self.logic.PRIORITY_DESCRIPTIONS.get(p, "")
        if len(desc_text) > 40:
            desc_text = desc_text[:37] + "..."
        desc_surf = desc_font.render(desc_text, True, (180, 180, 200))
        screen.blit(desc_surf, (rect.x + 12, rect.y + 28))

        return True

    def _render_move_row(self, idx, item, screen, rect):
        """Desenha um item da lista de moves."""
        moves = self.logic.get_moves()
        if idx >= len(moves):
            return True
        move = moves[idx]

        is_sel = (idx == self.logic.selected_move_index)
        is_curr = (idx == getattr(self.pokemon, "current_move_index", -1))
        list_w = self.get("moves_list")
        is_hover = (list_w is not None and idx == list_w._hover_index)

        # Fundo
        if is_sel:
            bg = (40, 60, 100, 210)
            border = (255, 215, 0, 255)
        elif is_curr:
            bg = (32, 60, 40, 190)
            border = (100, 220, 100, 255)
        elif is_hover:
            bg = (32, 46, 72, 190)
            border = (100, 150, 255, 255)
        else:
            bg = (25, 30, 50, 150)
            border = (60, 80, 120, 200)

        surf = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.rect(surf, bg, surf.get_rect(), border_radius=8)
        pygame.draw.rect(surf, border, surf.get_rect(),
                         2 if (is_sel or is_curr) else 1, border_radius=8)
        screen.blit(surf, rect.topleft)

        # Badge do tipo à esquerda
        type_name = str(getattr(move, "type", "normal")).lower()
        type_color = parse_color(
            self.logic.TYPE_COLORS.get(type_name, "#A8A878"))
        badge_rect = pygame.Rect(rect.x + 8, rect.y + 8, 52, rect.height - 16)
        pygame.draw.rect(screen, type_color, badge_rect, border_radius=6)
        pygame.draw.rect(screen, (255, 255, 255),
                         badge_rect, 1, border_radius=6)

        short = type_name.upper()[:8]
        badge_font = FontBook.get(13, bold=True,
                                  name="pokemon-firered-leafgreen-font-recreation")
        txt = badge_font.render(short, True, (255, 255, 255))
        screen.blit(txt, (badge_rect.centerx - txt.get_width() // 2,
                          badge_rect.centery - txt.get_height() // 2))

        # Info à direita do badge
        info_x = badge_rect.right + 10

        # Nome
        name_font = FontBook.get(18, bold=is_sel or is_curr,
                                 name="pokemon-firered-leafgreen-font-recreation")
        name_color = (255, 215, 0) if is_sel else (
            (200, 255, 200) if is_curr else (255, 255, 255))
        name_surf = name_font.render(
            str(getattr(move, "name", "?")).upper(), True, name_color)
        screen.blit(name_surf, (info_x, rect.y + 6))

        # Linha de stats
        stats_font = FontBook.get(13,
                                  name="pokemon-firered-leafgreen-font-recreation")
        power = getattr(move, "power", 0) or 0
        pp = getattr(move, "current_pp", 0) or 0
        pp_max = getattr(move, "max_pp", 0) or 0
        acc = getattr(move, "accuracy", 0) or 0
        category = str(getattr(move, "category", "physical")).upper()

        pwr_txt = f"PWR: {power}" if power > 0 else "PWR: --"
        cat_color = (255, 120, 120) if category == "PHYSICAL" else (120, 120, 255)

        t1 = stats_font.render(pwr_txt, True, (230, 230, 240))
        t2 = stats_font.render(f"PP: {pp}/{pp_max}", True, (230, 230, 240))
        t3 = stats_font.render(f"ACC: {acc}%", True, (230, 230, 240))
        t4 = stats_font.render(category, True, cat_color)

        cx = info_x
        cy = rect.y + 30
        screen.blit(t1, (cx, cy)); cx += t1.get_width() + 12
        screen.blit(t2, (cx, cy)); cx += t2.get_width() + 12
        screen.blit(t3, (cx, cy)); cx += t3.get_width() + 12
        screen.blit(t4, (cx, cy))

        # Descrição (última linha)
        desc = self.logic.get_move_description(move)
        if len(desc) > 46:
            desc = desc[:43] + "..."
        desc_font = FontBook.get(12,
                                 name="pokemon-firered-leafgreen-font-recreation")
        desc_surf = desc_font.render(desc, True, (180, 180, 200))
        screen.blit(desc_surf, (info_x, rect.y + 54))

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
            if event.key == pygame.K_UP:
                self.logic.move_up()
                self._refresh_selected_label()
                return
            if event.key == pygame.K_DOWN:
                self.logic.move_down()
                self._refresh_selected_label()
                return
            if event.key == pygame.K_LEFT:
                self.logic.move_left()
                self._refresh_selected_label()
                return
            if event.key == pygame.K_RIGHT:
                self.logic.move_right()
                self._refresh_selected_label()
                return

        super().handle_event(event)

    # =================================================================
    # Ciclo de vida
    # =================================================================
    def on_back(self):
        self._on_cancel()

    def _close(self):
        """Volta pro game_scene e despausa."""
        try:
            self.game_scene.game_paused = False
            self.game_scene.paused = False
            if hasattr(self.game_scene, "wave_manager"):
                self.game_scene.wave_manager.paused = False
        except Exception as e:
            print(f"[MoveSelectScene] unpause: {e}")

        # Volta pra cena do jogo
        self.game.current_scene = self.game_scene