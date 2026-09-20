# src/scenes/game_scene/components/managers/move_quick_switch_manager.py

"""
Move Quick Switch — dropdown de troca rápida de golpes.

Cada slot de Pokémon no time (HUD inferior, onde você arrasta para o mapa)
ganha um botão logo ACIMA dele mostrando o golpe atual e seu PP
(ex: "Flamethrower 12/15"). Ao clicar, abre um dropdown UP com todos os
golpes do Pokémon, permitindo trocar sem pausar o jogo.

Sempre visível, mesmo com a HUD oculta (tecla H).
"""

import pygame

_FONT_CACHE = {}

# ===== DEBUG =====
# Coloque True para imprimir logs no console.
DEBUG_QUICK_SWITCH = False


def _get_font(size):
    size = max(10, int(size))
    if size not in _FONT_CACHE:
        _FONT_CACHE[size] = pygame.font.Font(None, size)
    return _FONT_CACHE[size]


TYPE_COLORS = {
    'normal': (168, 168, 120), 'fire': (240, 128, 48), 'water': (104, 144, 240),
    'electric': (248, 208, 48), 'grass': (120, 200, 80), 'ice': (152, 216, 216),
    'fighting': (192, 48, 40), 'poison': (160, 64, 160), 'ground': (224, 192, 104),
    'flying': (168, 144, 240), 'psychic': (248, 88, 136), 'bug': (168, 184, 32),
    'rock': (184, 160, 56), 'ghost': (112, 88, 152), 'dragon': (112, 56, 248),
    'dark': (112, 88, 72), 'steel': (184, 184, 208), 'fairy': (238, 153, 238),
}


# =========================================================================
# WIDGET INDIVIDUAL (ancorado a um slot do time)
# =========================================================================
# =========================================================================
# WIDGET INDIVIDUAL (ancorado a um slot do time)
# =========================================================================
class MoveQuickSwitchWidget:
    """Widget de troca rápida de golpe — ancorado a um GameTeamSlot."""

    # ---- Tamanhos ----
    BTN_H = 30                 # altura do botão
    BTN_FONT_SIZE = 17         # fonte do botão
    DD_ROW_H = 34              # altura de cada linha do dropdown
    DD_FONT_SIZE = 16          # fonte das linhas
    DD_MIN_WIDTH = 260         # largura mínima do dropdown

    def __init__(self, pokemon, slot):
        self.pokemon = pokemon
        self.slot = slot                 # GameTeamSlot
        self.is_open = False
        self.hovered_row = -1
        self.hover_button = False
        self.button_rect = None
        self.dropdown_rect = None
        self.row_rects = []

    # ---------- HELPERS ----------
    def _get_current_move(self):
        if not self.pokemon or not self.pokemon.moves:
            return None
        idx = getattr(self.pokemon, 'current_move_index', 0)
        if 0 <= idx < len(self.pokemon.moves):
            return self.pokemon.moves[idx]
        return None

    def _format_label(self, move):
        return f"{move.name}  {move.current_pp}/{move.max_pp}"

    # ---------- GEOMETRIA ----------
    def update_position(self):
        """Recalcula o rect do botão com base no rect do slot do time."""
        if not self.slot or not hasattr(self.slot, 'rect'):
            self.button_rect = None
            self.dropdown_rect = None
            self.row_rects = []
            return

        move = self._get_current_move()
        if not move:
            self.button_rect = None
            self.dropdown_rect = None
            self.row_rects = []
            return

        slot_rect = self.slot.rect

        btn_h = self.BTN_H
        btn_w = max(90, slot_rect.width - 6)
        btn_x = slot_rect.x + (slot_rect.width - btn_w) // 2
        btn_y = slot_rect.y - btn_h - 5

        self.button_rect = pygame.Rect(btn_x, btn_y, btn_w, btn_h)

        if self.is_open:
            self._build_dropdown()

    def _build_dropdown(self):
        if not self.button_rect or not self.pokemon.moves:
            self.dropdown_rect = None
            self.row_rects = []
            return

        row_h = self.DD_ROW_H
        pad = 6

        # ===== Mesma largura do botão =====
        w = self.button_rect.width
        n = len(self.pokemon.moves)
        total_h = n * row_h + pad * 2

        dd_x = self.button_rect.x  # alinha com o botão
        dd_y = self.button_rect.top - total_h - 5  # abre para CIMA

        self.dropdown_rect = pygame.Rect(dd_x, dd_y, w, total_h)

        self.row_rects = []
        for i in range(n):
            r = pygame.Rect(
                dd_x + pad,
                dd_y + pad + i * row_h,
                w - pad * 2,
                row_h - 2,
            )
            self.row_rects.append(r)

    # ---------- INTERAÇÃO ----------
    def close(self):
        self.is_open = False
        self.hovered_row = -1

    def _select_move(self, index):
        if 0 <= index < len(self.pokemon.moves):
            old = getattr(self.pokemon, 'current_move_index', 0)
            self.pokemon.current_move_index = index
            new_move = self.pokemon.moves[index]
            print(f"[QUICK_SWITCH] {self.pokemon.name}: "
                  f"idx {old}->{index} ({new_move.name})")
        self.close()

    def update_hover(self, mouse_pos):
        self.hover_button = bool(
            self.button_rect and self.button_rect.collidepoint(mouse_pos)
        )
        if self.is_open:
            self.hovered_row = -1
            for i, r in enumerate(self.row_rects):
                if r.collidepoint(mouse_pos):
                    self.hovered_row = i
                    break

    # ---------- RENDER: BOTÃO ----------
    def render_button(self, screen):
        if not self.button_rect:
            return
        move = self._get_current_move()
        if not move:
            return

        r = self.button_rect
        pp_ratio = move.current_pp / max(1, move.max_pp)
        all_empty = all(m.current_pp <= 0 for m in self.pokemon.moves)

        # Cor por estado
        if all_empty:
            bg = (110, 30, 30); border = (240, 100, 100)
        elif move.current_pp <= 0:
            bg = (90, 35, 35); border = (230, 110, 110)
        elif pp_ratio <= 0.2:
            bg = (90, 55, 25); border = (255, 160, 60)
        elif self.hover_button or self.is_open:
            bg = (55, 70, 105); border = (150, 190, 255)
        else:
            bg = (28, 36, 52); border = (95, 115, 155)

        # Sombra
        shadow = r.copy()
        shadow.y += 2
        shadow_surf = pygame.Surface((shadow.width, shadow.height), pygame.SRCALPHA)
        shadow_surf.fill((0, 0, 0, 130))
        screen.blit(shadow_surf, shadow)

        # Fundo
        bg_surf = pygame.Surface((r.width, r.height), pygame.SRCALPHA)
        bg_surf.fill((*bg, 240))
        screen.blit(bg_surf, r)
        pygame.draw.rect(screen, border, r, 2, border_radius=8)

        # Barra lateral colorida pelo tipo
        move_type = getattr(move, 'type', 'normal')
        type_color = TYPE_COLORS.get(move_type, (150, 150, 150))
        pygame.draw.rect(
            screen, type_color,
            (r.x + 4, r.y + 4, 5, r.height - 8),
            border_radius=2,
        )

        # Texto
        font = _get_font(self.BTN_FONT_SIZE)
        label = self._format_label(move)

        if move.current_pp <= 0:
            text_color = (255, 130, 130)
        elif pp_ratio <= 0.2:
            text_color = (255, 200, 120)
        else:
            text_color = (240, 240, 250)

        max_text_w = r.width - 40  # reserva para a seta
        display = label
        while display and font.size(display)[0] > max_text_w and len(display) > 4:
            display = display[:-1]
        if display != label:
            display = display[:-3] + "..."

        text_s = font.render(display, True, text_color)
        tx = r.x + 14
        ty = r.centery - text_s.get_height() // 2
        screen.blit(text_s, (tx, ty))

        # Seta indicadora
        arrow_cx = r.right - 12
        arrow_cy = r.centery
        arrow_size = 5

        if self.is_open:
            # ▼ aberto
            pygame.draw.polygon(screen, (220, 230, 250), [
                (arrow_cx - arrow_size, arrow_cy - 2),
                (arrow_cx + arrow_size, arrow_cy - 2),
                (arrow_cx, arrow_cy + arrow_size - 1),
            ])
        else:
            # ▲ fechado (abre para cima)
            pygame.draw.polygon(screen, (220, 230, 250), [
                (arrow_cx - arrow_size, arrow_cy + 2),
                (arrow_cx + arrow_size, arrow_cy + 2),
                (arrow_cx, arrow_cy - arrow_size + 1),
            ])

    # ---------- RENDER: DROPDOWN ----------
    def render_dropdown(self, screen):
        if not self.is_open or not self.dropdown_rect:
            return

        # Sombra
        shadow = self.dropdown_rect.copy()
        shadow.x += 3
        shadow.y += 3
        shadow_surf = pygame.Surface((shadow.width, shadow.height), pygame.SRCALPHA)
        shadow_surf.fill((0, 0, 0, 150))
        screen.blit(shadow_surf, shadow)

        # Fundo
        bg_surf = pygame.Surface(
            (self.dropdown_rect.width, self.dropdown_rect.height),
            pygame.SRCALPHA,
        )
        bg_surf.fill((18, 22, 34, 250))
        screen.blit(bg_surf, self.dropdown_rect)

        pygame.draw.rect(
            screen, (120, 140, 190),
            self.dropdown_rect, 2, border_radius=10,
        )

        current_idx = getattr(self.pokemon, 'current_move_index', 0)

        for i, r in enumerate(self.row_rects):
            if i >= len(self.pokemon.moves):
                break

            move = self.pokemon.moves[i]
            is_current = (i == current_idx)
            is_hover = (i == self.hovered_row)

            if is_current:
                row_bg = (50, 65, 95); row_border = (255, 215, 100)
            elif is_hover:
                row_bg = (42, 52, 74); row_border = (130, 160, 220)
            else:
                row_bg = (26, 30, 44); row_border = (55, 65, 90)

            pygame.draw.rect(screen, row_bg, r, border_radius=5)
            pygame.draw.rect(screen, row_border, r, 1, border_radius=5)

            # Barra de tipo
            move_type = getattr(move, 'type', 'normal')
            type_color = TYPE_COLORS.get(move_type, (150, 150, 150))
            pygame.draw.rect(
                screen, type_color,
                (r.x + 4, r.y + 4, 5, r.height - 8),
                border_radius=2,
            )

            # Nome
            name_font = _get_font(self.DD_FONT_SIZE)
            name_s = name_font.render(move.name, True, (240, 240, 250))
            screen.blit(name_s, (r.x + 16, r.centery - name_s.get_height() // 2))

            # PP
            pp_ratio = move.current_pp / max(1, move.max_pp)
            if move.current_pp <= 0:
                pp_color = (240, 100, 100)
            elif pp_ratio <= 0.2:
                pp_color = (255, 180, 80)
            else:
                pp_color = (170, 220, 170)

            pp_text = f"{move.current_pp}/{move.max_pp}"
            pp_s = name_font.render(pp_text, True, pp_color)
            screen.blit(
                pp_s,
                (r.right - pp_s.get_width() - 12,
                 r.centery - pp_s.get_height() // 2),
            )


# =========================================================================
# MANAGER
# =========================================================================
class MoveQuickSwitchManager:
    """Gerencia todos os widgets de troca rápida ancorados nos slots do time."""

    def __init__(self, game_scene):
        self.game_scene = game_scene
        self.widgets = {}                # unique_id -> widget
        self._open_widget_id = None

    # ---------- FONTE DOS SLOTS ----------
    def _get_team_slots(self):
        tm = getattr(self.game_scene, 'team_manager', None)
        if tm is None:
            return []
        return getattr(tm, 'team_slots', []) or []

    # ---------- CICLO ----------
    def _ensure_widget(self, pokemon, slot):
        uid = getattr(pokemon, 'unique_id', None)
        if not uid:
            return None
        if uid not in self.widgets:
            self.widgets[uid] = MoveQuickSwitchWidget(pokemon, slot)
            if DEBUG_QUICK_SWITCH:
                print(f"[QUICK_SWITCH] Widget criado para {pokemon.name} (uid={uid})")
        else:
            # Atualiza referências (pokemon pode ter mudado de slot)
            self.widgets[uid].slot = slot
            self.widgets[uid].pokemon = pokemon
        return self.widgets[uid]

    def update(self, dt):
        """Remove widgets órfãos (pokémon saiu do time / slot ficou vazio)."""
        slots = self._get_team_slots()

        active_uids = set()
        for slot in slots:
            pokemon = getattr(slot, 'pokemon', None)
            if pokemon is None:
                continue
            if not pokemon.moves:
                continue
            uid = getattr(pokemon, 'unique_id', None)
            if uid:
                active_uids.add(uid)

        for uid in list(self.widgets.keys()):
            if uid not in active_uids:
                del self.widgets[uid]
                if self._open_widget_id == uid:
                    self._open_widget_id = None
                if DEBUG_QUICK_SWITCH:
                    print(f"[QUICK_SWITCH] Widget removido (uid={uid})")

    def _sync_widgets(self):
        """Garante que cada slot com pokémon tenha um widget."""
        slots = self._get_team_slots()
        for slot in slots:
            pokemon = getattr(slot, 'pokemon', None)
            if pokemon is None:
                continue
            if not pokemon.moves:
                continue
            self._ensure_widget(pokemon, slot)

    def _update_positions(self):
        for widget in self.widgets.values():
            widget.update_position()

    # ---------- EVENTOS ----------
    def handle_event(self, event, camera=None, screen_manager=None):
        self._sync_widgets()
        self._update_positions()

        # MOUSEMOTION: atualiza hover de todos
        if event.type == pygame.MOUSEMOTION:
            for widget in self.widgets.values():
                widget.update_hover(event.pos)
            return False

        # ESC fecha dropdown aberto
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            if self._open_widget_id is not None:
                w = self.widgets.get(self._open_widget_id)
                if w:
                    w.close()
                self._open_widget_id = None
                return True
            return False

        # Cliques
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            # 1) Clique em algum botão
            for uid, widget in self.widgets.items():
                if widget.button_rect and widget.button_rect.collidepoint(event.pos):
                    new_open = not widget.is_open
                    # Fecha todos os outros
                    for other in self.widgets.values():
                        other.close()
                    widget.is_open = new_open
                    widget.hovered_row = -1
                    self._open_widget_id = uid if new_open else None
                    return True

            # 2) Clique dentro do dropdown aberto
            if self._open_widget_id is not None:
                w = self.widgets.get(self._open_widget_id)
                if w and w.is_open:
                    # Row clicada?
                    for i, r in enumerate(w.row_rects):
                        if r.collidepoint(event.pos):
                            w._select_move(i)
                            self._open_widget_id = None
                            # Salva rapidamente
                            try:
                                player = getattr(self.game_scene, 'player', None)
                                if player:
                                    player.auto_save()
                            except Exception:
                                pass
                            return True

                    # Fundo do dropdown?
                    if w.dropdown_rect and w.dropdown_rect.collidepoint(event.pos):
                        return True

                    # Clique fora → fecha e consome
                    w.close()
                    self._open_widget_id = None
                    return True

        return False

    # ---------- RENDER ----------
    def render(self, screen, camera=None, screen_manager=None):
        state = getattr(self.game_scene, 'game_state', 'waiting')
        if state in ('completed', 'game_over'):
            return

        self._sync_widgets()
        self._update_positions()

        if DEBUG_QUICK_SWITCH:
            print(f"[QUICK_SWITCH] render: {len(self.widgets)} widgets")

        # Botões primeiro, dropdowns abertos por cima
        items = sorted(
            self.widgets.items(),
            key=lambda x: 1 if x[1].is_open else 0,
        )

        for uid, widget in items:
            widget.render_button(screen)

        for uid, widget in items:
            if widget.is_open:
                widget.render_dropdown(screen)