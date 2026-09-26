# src/scenes/team_select_scene/managers/drag_drop_manager.py

import pygame
from typing import Optional, Callable


class DragDropManager:
    """
    Gerencia drag & drop de Pokémon entre slots do time e grid da box.

    - Clique em um Pokémon + mover = inicia drag
    - Soltar em outro slot/posição = troca/move
    - Soltar fora = cancela

    Tipos de operação:
    - 'team_to_team': reordena dentro do time
    - 'team_to_box': remove do time (vai para box)
    - 'box_to_team': adiciona ao time
    - 'box_to_box': reordena dentro da box (troca posições visuais)
    """

    DRAG_THRESHOLD = 6  # pixels para considerar drag

    def __init__(self, game, pokemon_manager):
        self.game = game
        self.pokemon_manager = pokemon_manager

        # Estado do drag
        self.is_dragging = False
        self.source_type = None       # 'team' ou 'box'
        self.source_index = None      # índice do slot ou do item na grid
        self.source_pokemon = None    # dict ou instância
        self.drag_start_pos = None
        self.current_mouse_pos = None
        self._pending_drag = False    # clique registrado, aguardando movimento

        # Alvo atual
        self.hover_target_type = None
        self.hover_target_index = None

        # Callbacks
        self.on_drop: Optional[Callable] = None   # (op_type, data)
        self.on_cancel: Optional[Callable] = None

        # Elementos registrados (preenchidos a cada frame pelo scene)
        self.team_slots = []
        self.grid_items = []
        self.extra_drop_zones = []  # (rect, zone_id, extra_data)

    # =================================================================
    # REGISTRO
    # =================================================================
    def set_targets(self, team_slots, grid_items):
        self.team_slots = team_slots
        self.grid_items = grid_items

    def add_drop_zone(self, rect, zone_id, extra_data=None):
        self.extra_drop_zones.append((pygame.Rect(rect), zone_id, extra_data))

    def clear_extra_zones(self):
        self.extra_drop_zones.clear()

    # =================================================================
    # EVENTOS
    # =================================================================
    def handle_event(self, event) -> bool:
        """Retorna True se consumiu o evento."""
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            hit = self._hit_test(event.pos)
            if hit:
                kind, index, data = hit
                self._pending_drag = True
                self.source_type = kind
                self.source_index = index
                self.source_pokemon = data
                self.drag_start_pos = event.pos
                self.current_mouse_pos = event.pos
                return True
            return False

        elif event.type == pygame.MOUSEMOTION:
            self.current_mouse_pos = event.pos

            if self._pending_drag and not self.is_dragging:
                dx = event.pos[0] - self.drag_start_pos[0]
                dy = event.pos[1] - self.drag_start_pos[1]
                if (dx * dx + dy * dy) > (self.DRAG_THRESHOLD ** 2):
                    self.is_dragging = True
                    self._on_drag_start()

            if self.is_dragging:
                self._update_hover_target(event.pos)
                return True

            return False

        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self.is_dragging:
                self._finish_drag()
                return True
            elif self._pending_drag:
                # Clique simples: não é drag, deixa o clique passar
                self._reset()
                return False

        return False

    def _on_drag_start(self):
        """Marca os itens visuais como 'sendo arrastados'."""
        if self.source_type == 'team' and self.source_index < len(self.team_slots):
            self.team_slots[self.source_index].is_selected = True
        elif self.source_type == 'box' and self.source_index < len(self.grid_items):
            self.grid_items[self.source_index].is_being_dragged = True

    def _update_hover_target(self, pos):
        """Atualiza qual slot/item está sob o cursor."""
        # Reseta
        for s in self.team_slots:
            s.is_drag_hover = False
        for g in self.grid_items:
            g.is_drag_hover = False

        self.hover_target_type = None
        self.hover_target_index = None

        # Prioridade: team slots primeiro (para box -> team)
        for i, slot in enumerate(self.team_slots):
            if slot.rect.collidepoint(pos):
                slot.is_drag_hover = True
                self.hover_target_type = 'team'
                self.hover_target_index = i
                return

        for i, item in enumerate(self.grid_items):
            if item.rect.collidepoint(pos):
                item.is_drag_hover = True
                self.hover_target_type = 'box'
                self.hover_target_index = i
                return

        for rect, zone_id, _ in self.extra_drop_zones:
            if rect.collidepoint(pos):
                self.hover_target_type = zone_id
                self.hover_target_index = -1
                return

    def _finish_drag(self):
        """Executa a operação de drop."""
        if self.hover_target_type is None:
            # Soltou fora → cancela
            self._reset()
            if self.on_cancel:
                self.on_cancel()
            return

        op_type = self._resolve_op_type()
        if op_type and self.on_drop:
            self.on_drop(op_type, {
                'source_type': self.source_type,
                'source_index': self.source_index,
                'source_pokemon': self.source_pokemon,
                'target_type': self.hover_target_type,
                'target_index': self.hover_target_index,
            })

        self._reset()

    def _resolve_op_type(self):
        s = self.source_type
        t = self.hover_target_type

        if s == 'team' and t == 'team':
            if self.source_index == self.hover_target_index:
                return None
            return 'team_to_team'
        if s == 'team' and t == 'box':
            return 'team_to_box'
        if s == 'box' and t == 'team':
            return 'box_to_team'
        if s == 'box' and t == 'box':
            if self.source_index == self.hover_target_index:
                return None
            return 'box_to_box'
        if t in ('trash', 'release_zone'):
            return 'release'
        return None

    def _reset(self):
        # Limpa flags visuais
        for s in self.team_slots:
            s.is_drag_hover = False
        for g in self.grid_items:
            g.is_drag_hover = False
            g.is_being_dragged = False

        self.is_dragging = False
        self._pending_drag = False
        self.source_type = None
        self.source_index = None
        self.source_pokemon = None
        self.drag_start_pos = None
        self.hover_target_type = None
        self.hover_target_index = None

    def _hit_test(self, pos):
        """
        Detecta se o clique foi em um slot/item.
        Retorna (kind, index, data) ou None.
        """
        for i, slot in enumerate(self.team_slots):
            if slot.rect.collidepoint(pos) and slot.pokemon:
                return ('team', i, slot.pokemon)

        for i, item in enumerate(self.grid_items):
            if item.rect.collidepoint(pos):
                return ('box', i, item.pokemon_data)

        return None

    def consume_click_if_any(self, event):
        """
        Chamado no MOUSEBUTTONUP quando NÃO houve drag.
        Retorna o 'hit' (kind, index, data) se houve clique simples.
        """
        if event.type != pygame.MOUSEBUTTONUP or event.button != 1:
            return None
        if self.is_dragging:
            return None
        if not self._pending_drag:
            return None
        # Clique simples sem drag: retorna o alvo
        return (self.source_type, self.source_index, self.source_pokemon)

    # =================================================================
    # RENDER (o Pokémon "fantasma" seguindo o mouse)
    # =================================================================
    def render_drag_ghost(self, screen, pokedex):
        if not self.is_dragging or not self.source_pokemon:
            return
        if not self.current_mouse_pos:
            return

        from src.data.icon_loader import pokemon_icon_loader
        import pygame

        # Descobre ID
        if hasattr(self.source_pokemon, 'id'):
            pid = self.source_pokemon.id
        else:
            pid = self.source_pokemon.get('id', 0)

        size = 56
        try:
            icon = pokemon_icon_loader.get_animated_icon(
                pid, size, pygame.time.get_ticks(), frame_duration_ms=400
            )
        except Exception:
            icon = None

        mx, my = self.current_mouse_pos
        ghost_rect = pygame.Rect(mx - size // 2, my - size // 2, size, size)

        # Sombra
        sh = pygame.Surface((size + 8, size + 8), pygame.SRCALPHA)
        pygame.draw.rect(sh, (0, 0, 0, 100), (4, 4, size, size), border_radius=10)
        screen.blit(sh, (ghost_rect.x - 4, ghost_rect.y - 4))

        # Fundo
        pygame.draw.rect(screen, (40, 50, 75), ghost_rect, border_radius=10)
        pygame.draw.rect(screen, (180, 210, 255), ghost_rect, 2, border_radius=10)

        if icon:
            screen.blit(icon, (ghost_rect.x + 4, ghost_rect.y + 4))