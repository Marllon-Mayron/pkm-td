# src/scenes/starter_select_scene.py
"""
Cena de seleção de Pokémon inicial com 3 vitrines inmap externas (uma por card),
cada uma com rotação de 8 direções, barra de progresso e informações.
"""
import pygame
import string
from src.scenes.base_scene import BaseScene
from src.data.pokedex import Pokedex


class StarterSelectScene(BaseScene):
    """Tela para escolher o Pokémon inicial com vitrine inmap externa para cada card"""

    # ===== INICIAIS POR GERAÇÃO =====
    GENERATIONS = {
        1: [{"id": 1, "name": "Bulbasaur"}, {"id": 4, "name": "Charmander"}, {"id": 7, "name": "Squirtle"}],
        2: [{"id": 152, "name": "Chikorita"}, {"id": 155, "name": "Cyndaquil"}, {"id": 158, "name": "Totodile"}],
        # Adicione mais gerações aqui
    }

    def __init__(self, game):
        super().__init__(game)

        self.pokedex = Pokedex()
        self.current_generation = 1
        self.starters = self._get_starters_for_generation(self.current_generation)
        self.selected_index = 0
        self.confirmed = False

        # Nickname dialog
        self.show_nickname_dialog = False
        self.nickname_input = ""
        self.nickname_active = True

        # Layout dos cards e áreas inmap
        self.card_width = 200
        self.card_height = 250  # AUMENTADO para dar mais espaço ao sprite frontal
        self.card_spacing = 40
        self.card_positions = []

        # Áreas inmap (uma abaixo de cada card) - mais estreitas
        self.inmap_areas = []  # lista de pygame.Rect

        self.confirm_button = None
        self.confirm_hover = False

        # Botões de geração
        self.gen_buttons = []

        # Animação de seleção (pulse)
        self.selection_animation = 0
        self.animation_direction = 1

        # Diálogo de nickname
        self.nickname_dialog_rect = None
        self.nickname_input_rect = None
        self.confirm_nick_button = None
        self.skip_nick_button = None
        self.confirm_nick_hover = False
        self.skip_nick_hover = False

        # Fontes
        self.title_font = None
        self.subtitle_font = None

        # Fundo
        self.bg_gradient = None

        # ===== ANIMAÇÃO INMAP (8 DIREÇÕES) POR CARD =====
        self.directions = [
            "down", "down-right", "right", "up-right",
            "up", "up-left", "left", "down-left"
        ]
        self.direction_change_interval = 1.5  # segundos
        self.animation_speed = 0.15           # segundos por frame
        self.inmap_scale_multiplier = 3.0     # multiplicador para o tamanho do sprite

        # Estado de animação para cada card (índice 0,1,2)
        self.inmap_states = [
            {"direction_index": 0, "frame": 0, "timer": 0, "dir_timer": 0}
            for _ in range(3)
        ]

        # Cache de frames (por pokemon_id + direção)
        self._inmap_frames_cache = {}
        self._inmap_size_cache = {}

    def _get_starters_for_generation(self, gen):
        return self.GENERATIONS.get(gen, self.GENERATIONS[1])

    def enter(self):
        print(f"[STARTER_SELECT] Geração {self.current_generation}")

    def _update_layout(self):
        vp_w = self.screen_manager.viewport_width
        vp_h = self.screen_manager.viewport_height
        vp_x = self.screen_manager.viewport_x
        vp_y = self.screen_manager.viewport_y

        # ===== TÍTULO E SUBTÍTULO =====
        title_size = max(32, int(vp_h * 0.055))
        subtitle_size = max(20, int(vp_h * 0.028))
        self.title_font = pygame.font.Font(None, title_size)
        self.subtitle_font = pygame.font.Font(None, subtitle_size)

        title_y = vp_y + int(vp_h * 0.06)

        # ===== BOTÕES DE GERAÇÃO (abaixo do subtítulo) =====
        btn_width = int(vp_w * 0.07)
        btn_height = int(vp_h * 0.04)
        spacing = int(vp_w * 0.01)
        total_btns = len(self.GENERATIONS)
        total_width = total_btns * btn_width + (total_btns - 1) * spacing
        start_x = vp_x + (vp_w - total_width) // 2
        btn_y = vp_y + int(vp_h * 0.16)

        self.gen_buttons = []
        for i, gen in enumerate(sorted(self.GENERATIONS.keys())):
            x = start_x + i * (btn_width + spacing)
            rect = pygame.Rect(x, btn_y, btn_width, btn_height)
            self.gen_buttons.append({
                "rect": rect,
                "generation": gen,
                "active": gen == self.current_generation,
                "hover": False
            })

        # ===== CARDS (sprite frontal + nome/tipo) - ALTURA AUMENTADA =====
        card_top_y = btn_y + btn_height + int(vp_h * 0.02)
        # Altura do card: aumentada para 30% da altura da viewport
        self.card_height = int(vp_h * 0.30)
        self.card_width = min(int(vp_w * 0.18), int(vp_w * 0.22))
        self.card_spacing = int(vp_w * 0.025)

        total_cards_width = self.card_width * 3 + self.card_spacing * 2
        start_x = vp_x + (vp_w - total_cards_width) // 2

        self.card_positions = []
        for i in range(3):
            x = start_x + (self.card_width + self.card_spacing) * i
            y = card_top_y
            self.card_positions.append(pygame.Rect(x, y, self.card_width, self.card_height))

        # ===== ÁREAS INMAP (abaixo de cada card) - LARGURA REDUZIDA =====
        # A largura da área inmap será 80% da largura do card (mais estreita)
        inmap_width = int(self.card_width * 0.80)
        inmap_height = int(vp_h * 0.18)  # altura fixa
        inmap_spacing = self.card_spacing

        self.inmap_areas = []
        for i, card_rect in enumerate(self.card_positions):
            # Centraliza a área inmap horizontalmente em relação ao card
            x = card_rect.x + (card_rect.width - inmap_width) // 2
            y = card_rect.bottom + int(vp_h * 0.01)
            rect = pygame.Rect(x, y, inmap_width, inmap_height)
            self.inmap_areas.append(rect)

        # ===== BOTÃO CONFIRMAR (abaixo da última área inmap) =====
        last_inmap = self.inmap_areas[-1]
        confirm_width = int(vp_w * 0.12)
        confirm_height = int(vp_h * 0.06)
        confirm_x = vp_x + (vp_w - confirm_width) // 2
        confirm_y = last_inmap.bottom + int(vp_h * 0.02)
        self.confirm_button = pygame.Rect(confirm_x, confirm_y, confirm_width, confirm_height)

        # ===== DIÁLOGO DE NICKNAME =====
        dialog_w = int(vp_w * 0.4)
        dialog_h = int(vp_h * 0.35)
        dialog_x = vp_x + (vp_w - dialog_w) // 2
        dialog_y = vp_y + (vp_h - dialog_h) // 2
        self.nickname_dialog_rect = pygame.Rect(dialog_x, dialog_y, dialog_w, dialog_h)

        input_w = int(dialog_w * 0.8)
        input_h = int(dialog_h * 0.2)
        input_x = dialog_x + (dialog_w - input_w) // 2
        input_y = dialog_y + int(dialog_h * 0.4)
        self.nickname_input_rect = pygame.Rect(input_x, input_y, input_w, input_h)

        btn_w = int(dialog_w * 0.3)
        btn_h = int(dialog_h * 0.15)
        btn_y_dialog = dialog_y + dialog_h - btn_h - int(dialog_h * 0.08)
        self.confirm_nick_button = pygame.Rect(dialog_x + int(dialog_w * 0.1), btn_y_dialog, btn_w, btn_h)
        self.skip_nick_button = pygame.Rect(dialog_x + dialog_w - btn_w - int(dialog_w * 0.1), btn_y_dialog, btn_w, btn_h)

    def handle_event(self, event):
        if self.show_nickname_dialog:
            self._handle_nickname_dialog_event(event)
            return

        if self.confirmed:
            return

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_LEFT:
                self.selected_index = (self.selected_index - 1) % 3
                self._reset_inmap_animation(self.selected_index)
                self._play_select_sound()
            elif event.key == pygame.K_RIGHT:
                self.selected_index = (self.selected_index + 1) % 3
                self._reset_inmap_animation(self.selected_index)
                self._play_select_sound()
            elif event.key == pygame.K_RETURN or event.key == pygame.K_SPACE:
                self._confirm_selection()

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mouse_pos = event.pos

            for i, rect in enumerate(self.card_positions):
                if rect.collidepoint(mouse_pos):
                    self.selected_index = i
                    self._reset_inmap_animation(i)
                    self._play_select_sound()

            if self.confirm_button and self.confirm_button.collidepoint(mouse_pos):
                self._confirm_selection()

            for btn in self.gen_buttons:
                if btn["rect"].collidepoint(mouse_pos):
                    if btn["generation"] != self.current_generation:
                        self.current_generation = btn["generation"]
                        self.starters = self._get_starters_for_generation(self.current_generation)
                        self.selected_index = 0
                        self.confirmed = False
                        self._inmap_frames_cache.clear()
                        self._inmap_size_cache.clear()
                        for i in range(3):
                            self._reset_inmap_animation(i)
                        print(f"[STARTER_SELECT] Geracao {self.current_generation}")
                    return

        elif event.type == pygame.MOUSEMOTION:
            if self.confirm_button:
                self.confirm_hover = self.confirm_button.collidepoint(event.pos)
            for btn in self.gen_buttons:
                btn["hover"] = btn["rect"].collidepoint(event.pos)

    def _reset_inmap_animation(self, index):
        if 0 <= index < len(self.inmap_states):
            self.inmap_states[index]["direction_index"] = 0
            self.inmap_states[index]["frame"] = 0
            self.inmap_states[index]["timer"] = 0
            self.inmap_states[index]["dir_timer"] = 0

    def _handle_nickname_dialog_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN:
                self._apply_nickname()
            elif event.key == pygame.K_ESCAPE:
                self._skip_nickname()
            elif event.key == pygame.K_BACKSPACE:
                self.nickname_input = self.nickname_input[:-1]
            else:
                char = event.unicode
                if char in string.ascii_letters + string.digits + " _-" and len(self.nickname_input) < 12:
                    self.nickname_input += char

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mouse_pos = event.pos
            if self.nickname_input_rect.collidepoint(mouse_pos):
                self.nickname_active = True
            else:
                self.nickname_active = False

            if self.confirm_nick_button and self.confirm_nick_button.collidepoint(mouse_pos):
                self._apply_nickname()
            if self.skip_nick_button and self.skip_nick_button.collidepoint(mouse_pos):
                self._skip_nickname()

        elif event.type == pygame.MOUSEMOTION:
            if self.confirm_nick_button:
                self.confirm_nick_hover = self.confirm_nick_button.collidepoint(event.pos)
            if self.skip_nick_button:
                self.skip_nick_hover = self.skip_nick_button.collidepoint(event.pos)

    def _apply_nickname(self):
        nickname = self.nickname_input.strip() or None
        starter = self.starters[self.selected_index]
        pokemon = self.game.player.add_starter(starter["id"])
        if pokemon and nickname:
            pokemon.nickname = nickname
            pokemon.name = nickname
        if pokemon:
            self.game.player.save_game(1)
            from src.scenes.phase_selector.phase_select_scene import PhaseSelectScene
            self.game.current_scene = PhaseSelectScene(self.game)
        else:
            self.confirmed = False
            self.show_nickname_dialog = False

    def _skip_nickname(self):
        self._apply_nickname()

    def _play_select_sound(self):
        pass

    def _confirm_selection(self):
        if self.confirmed:
            return
        self.confirmed = True
        self.show_nickname_dialog = True
        self.nickname_input = ""
        self.nickname_active = True

    def fixed_update(self, dt):
        # Pulse do card selecionado
        if not self.show_nickname_dialog and not self.confirmed:
            self.selection_animation += dt * 3 * self.animation_direction
            if self.selection_animation >= 1:
                self.selection_animation = 1
                self.animation_direction = -1
            elif self.selection_animation <= 0:
                self.selection_animation = 0
                self.animation_direction = 1

        # Atualiza animação inmap de cada card
        self._update_inmap_animations(dt)

    def _update_inmap_animations(self, dt):
        for idx, state in enumerate(self.inmap_states):
            # Muda direção periodicamente
            state["dir_timer"] += dt
            if state["dir_timer"] >= self.direction_change_interval:
                state["dir_timer"] = 0
                state["direction_index"] = (state["direction_index"] + 1) % len(self.directions)
                state["frame"] = 0
                state["timer"] = 0

            # Avança frame da direção atual
            pokemon_id = self.starters[idx]["id"]
            frames = self._get_animation_frames(pokemon_id, state["direction_index"])
            if frames and len(frames) > 1:
                state["timer"] += dt
                if state["timer"] >= self.animation_speed:
                    state["timer"] = 0
                    state["frame"] = (state["frame"] + 1) % len(frames)
            else:
                state["frame"] = 0

    def _get_animation_frames(self, pokemon_id, dir_index):
        direction = self.directions[dir_index]
        cache_key = f"{pokemon_id}_{direction}"
        if cache_key in self._inmap_frames_cache:
            return self._inmap_frames_cache[cache_key]

        anim = self.pokedex.get_inmap_animation(pokemon_id, shiny=False)
        frames = anim.get(direction, [])

        if not frames:
            fallback_map = {
                "down-right": ["down", "right"],
                "up-right": ["up", "right"],
                "up-left": ["up", "left"],
                "down-left": ["down", "left"]
            }
            if direction in fallback_map:
                for fb in fallback_map[direction]:
                    frames = anim.get(fb, [])
                    if frames:
                        break

        if not frames:
            for d in self.directions:
                frames = anim.get(d, [])
                if frames:
                    break

        self._inmap_frames_cache[cache_key] = frames
        return frames

    def _get_inmap_sprite_size(self, pokemon_id):
        cache_key = f"{pokemon_id}_size"
        if cache_key in self._inmap_size_cache:
            return self._inmap_size_cache[cache_key]

        try:
            size = self.pokedex.get_map_sprite_size(pokemon_id, shiny=False)
            if size > 0:
                scaled = int(size * self.inmap_scale_multiplier)
                self._inmap_size_cache[cache_key] = scaled
                return scaled
        except:
            pass

        for d in range(len(self.directions)):
            frames = self._get_animation_frames(pokemon_id, d)
            if frames and len(frames) > 0:
                frame = frames[0]
                if frame:
                    w, h = frame.get_width(), frame.get_height()
                    size = max(w, h)
                    scaled = int(size * self.inmap_scale_multiplier)
                    self._inmap_size_cache[cache_key] = scaled
                    return scaled

        default = 32 * int(self.inmap_scale_multiplier)
        self._inmap_size_cache[cache_key] = default
        return default

    def render(self, screen):
        self._draw_gradient_background(screen)
        self._update_layout()

        if self.show_nickname_dialog:
            self._render_nickname_dialog(screen)
            return

        vx = self.screen_manager.viewport_x
        vy = self.screen_manager.viewport_y
        vw = self.screen_manager.viewport_width
        vh = self.screen_manager.viewport_height

        # ===== TÍTULO =====
        title_text = self.title_font.render("ESCOLHA SEU POKÉMON INICIAL", True, (255, 255, 255))
        title_x = vx + (vw - title_text.get_width()) // 2
        title_y = vy + int(vh * 0.06)
        screen.blit(title_text, (title_x, title_y))

        # ===== SUBTÍTULO =====
        subtitle_text = self.subtitle_font.render("Use <- -> ou clique para escolher", True, (200, 200, 200))
        subtitle_x = vx + (vw - subtitle_text.get_width()) // 2
        subtitle_y = title_y + title_text.get_height() + 8
        screen.blit(subtitle_text, (subtitle_x, subtitle_y))

        # ===== BOTÕES DE GERAÇÃO =====
        self._render_generation_buttons(screen)

        # ===== CARDS (sprite frontal + nome + tipo) =====
        for i, starter in enumerate(self.starters):
            rect = self.card_positions[i]
            is_selected = (i == self.selected_index)

            # Fundo do card
            border_color = (255, 215, 0) if is_selected else (100, 100, 100)
            border_width = 4 if is_selected else 2
            card_bg = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
            card_bg.fill((30, 30, 40, 220))
            screen.blit(card_bg, rect)
            pygame.draw.rect(screen, border_color, rect, border_width, border_radius=10)

            if is_selected:
                glow = rect.inflate(10, 10)
                pygame.draw.rect(screen, (255, 215, 0, 50), glow, 2, border_radius=12)

            # ===== SPRITE FRONTAL (AUMENTADO) =====
            sprite = self.pokedex.get_sprite(starter["id"], "front", shiny=False)
            if sprite:
                # O sprite ocupa até 60% da altura do card (aumentado)
                max_size = min(rect.width * 0.85, rect.height * 0.55)
                scale = max_size / max(sprite.get_width(), sprite.get_height())
                new_w = int(sprite.get_width() * scale)
                new_h = int(sprite.get_height() * scale)
                scaled = pygame.transform.scale(sprite, (new_w, new_h))
                sprite_x = rect.x + (rect.width - new_w) // 2
                sprite_y = rect.y + int(rect.height * 0.05)  # margem superior
                screen.blit(scaled, (sprite_x, sprite_y))

            # ===== NOME =====
            name_font = pygame.font.Font(None, int(rect.height * 0.11))
            name_color = (255, 255, 255) if not is_selected else (255, 215, 0)
            name_text = name_font.render(starter["name"], True, name_color)
            name_x = rect.x + (rect.width - name_text.get_width()) // 2
            name_y = rect.y + int(rect.height * 0.70)  # posicionado após o sprite
            screen.blit(name_text, (name_x, name_y))

            # ===== TIPO (da Pokédex) =====
            types = self.pokedex.get_types(starter["id"])
            type_font = pygame.font.Font(None, int(rect.height * 0.07))
            if types:
                type_name = types[0].upper()
                type_color = self.pokedex.get_type_color(types[0])
                type_text = type_font.render(type_name, True, type_color)
                type_x = rect.x + (rect.width - type_text.get_width()) // 2
                type_y = name_y + name_text.get_height() + 4
                screen.blit(type_text, (type_x, type_y))

            # ===== INDICADOR DE SELEÇÃO =====
            if is_selected:
                ind_size = 14
                ind_y = rect.bottom - ind_size - 8
                pygame.draw.polygon(screen, (255, 215, 0), [
                    (rect.centerx, ind_y),
                    (rect.centerx - ind_size // 2, ind_y + ind_size),
                    (rect.centerx + ind_size // 2, ind_y + ind_size)
                ])

        # ===== ÁREAS INMAP (uma abaixo de cada card) =====
        for idx, inmap_rect in enumerate(self.inmap_areas):
            pokemon_id = self.starters[idx]["id"]
            self._render_inmap_area(screen, inmap_rect, idx, pokemon_id)

        # ===== BOTÃO CONFIRMAR =====
        if self.confirm_button:
            color = (60, 120, 60) if self.confirm_hover else (40, 80, 40)
            pygame.draw.rect(screen, color, self.confirm_button, border_radius=8)
            pygame.draw.rect(screen, (100, 180, 100), self.confirm_button, 2, border_radius=8)
            font = pygame.font.Font(None, int(self.confirm_button.height * 0.5))
            text = font.render("CONFIRMAR", True, (255, 255, 255))
            tx = self.confirm_button.x + (self.confirm_button.width - text.get_width()) // 2
            ty = self.confirm_button.y + (self.confirm_button.height - text.get_height()) // 2
            screen.blit(text, (tx, ty))

        # ===== DICA DE TECLADO =====
        tip_font = pygame.font.Font(None, int(vh * 0.02))
        tip_text = tip_font.render("<-  ->  navegar | ENTER confirmar", True, (150, 150, 150))
        tip_x = vx + (vw - tip_text.get_width()) // 2
        tip_y = vy + vh - int(vh * 0.035)
        screen.blit(tip_text, (tip_x, tip_y))

    def _render_inmap_area(self, screen, rect, card_index, pokemon_id):
        """Renderiza uma área inmap externa com fundo, sprite, barra e informações"""
        state = self.inmap_states[card_index]

        # Fundo da área
        pygame.draw.rect(screen, (20, 20, 30, 200), rect, border_radius=8)
        pygame.draw.rect(screen, (80, 80, 90), rect, 2, border_radius=8)

        # Obtém o frame atual
        frames = self._get_animation_frames(pokemon_id, state["direction_index"])
        if not frames:
            # Placeholder
            font = pygame.font.Font(None, 20)
            text = font.render("No inmap", True, (150, 150, 150))
            screen.blit(text, text.get_rect(center=rect.center))
            return

        frame_idx = min(state["frame"], len(frames) - 1)
        sprite = frames[frame_idx]
        if not sprite:
            return

        # Tamanho do sprite (escalado)
        sprite_size = self._get_inmap_sprite_size(pokemon_id)
        max_display = min(rect.width - 20, rect.height - 40)  # reserva espaço para textos
        if sprite_size > max_display:
            scale = max_display / sprite_size
            display_size = int(sprite_size * scale)
        else:
            display_size = sprite_size

        scaled_sprite = pygame.transform.scale(sprite, (display_size, display_size))
        x = rect.x + (rect.width - display_size) // 2
        y = rect.y + 10  # margem superior
        screen.blit(scaled_sprite, (x, y))

        # ===== INFORMAÇÕES =====
        info_font = pygame.font.Font(None, 14)
        current_dir = self.directions[state["direction_index"]].upper()
        dir_text = f"{current_dir}  {state['frame']+1}/{len(frames)}"
        dir_surf = info_font.render(dir_text, True, (200, 200, 200))
        screen.blit(dir_surf, (rect.x + 8, rect.y + 8))

        # Barra de progresso da rotação
        progress = state["dir_timer"] / self.direction_change_interval
        bar_width = rect.width - 16
        bar_height = 4
        bar_x = rect.x + 8
        bar_y = rect.bottom - 12
        pygame.draw.rect(screen, (60, 60, 70), (bar_x, bar_y, bar_width, bar_height), border_radius=2)
        if progress > 0:
            fill_width = int(bar_width * progress)
            pygame.draw.rect(screen, (255, 215, 0), (bar_x, bar_y, fill_width, bar_height), border_radius=2)

        # Rótulo "INMAP"
        label_font = pygame.font.Font(None, 12)
        label = label_font.render("INMAP", True, (150, 150, 180))
        screen.blit(label, (rect.right - label.get_width() - 8, rect.y + 8))

    def _render_generation_buttons(self, screen):
        for btn in self.gen_buttons:
            rect = btn["rect"]
            if btn["active"]:
                bg = (60, 120, 60)
                border = (255, 215, 0)
                color = (255, 255, 255)
            elif btn["hover"]:
                bg = (50, 50, 60)
                border = (180, 180, 180)
                color = (255, 255, 255)
            else:
                bg = (30, 30, 40)
                border = (80, 80, 80)
                color = (200, 200, 200)

            pygame.draw.rect(screen, bg, rect, border_radius=6)
            pygame.draw.rect(screen, border, rect, 2, border_radius=6)
            font = pygame.font.Font(None, int(rect.height * 0.5))
            text = font.render(f"G{btn['generation']}", True, color)
            screen.blit(text, text.get_rect(center=rect.center))

    def _render_nickname_dialog(self, screen):
        overlay = pygame.Surface((self.screen_manager.window_width, self.screen_manager.window_height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        screen.blit(overlay, (0, 0))

        starter = self.starters[self.selected_index]
        rect = self.nickname_dialog_rect
        pygame.draw.rect(screen, (40, 40, 60), rect, border_radius=15)
        pygame.draw.rect(screen, (255, 215, 0), rect, 3, border_radius=15)

        font = self._get_font(int(rect.height * 0.12), bold=True)
        title = font.render(f"DÊ UM APELIDO PARA {starter['name']}", True, (255, 215, 0))
        tx = rect.x + (rect.width - title.get_width()) // 2
        ty = rect.y + int(rect.height * 0.08)
        screen.blit(title, (tx, ty))

        sub_font = self._get_font(int(rect.height * 0.06))
        sub = sub_font.render("(deixe em branco para manter o nome original)", True, (180, 180, 200))
        sx = rect.x + (rect.width - sub.get_width()) // 2
        sy = ty + title.get_height() + 8
        screen.blit(sub, (sx, sy))

        # Input
        input_color = (60, 60, 80) if self.nickname_active else (40, 40, 60)
        pygame.draw.rect(screen, input_color, self.nickname_input_rect, border_radius=8)
        pygame.draw.rect(screen, (255, 215, 0) if self.nickname_active else (100, 100, 120),
                         self.nickname_input_rect, 2, border_radius=8)

        display = self.nickname_input if self.nickname_input else "Digite o apelido..."
        text_color = (255, 255, 255) if self.nickname_input else (120, 120, 140)
        input_font = self._get_font(int(self.nickname_input_rect.height * 0.5))
        while input_font.size(display)[0] > self.nickname_input_rect.width - 20 and len(display) > 0:
            display = display[:-1]
        text_surf = input_font.render(display, True, text_color)
        text_x = self.nickname_input_rect.x + 10
        text_y = self.nickname_input_rect.y + (self.nickname_input_rect.height - text_surf.get_height()) // 2
        screen.blit(text_surf, (text_x, text_y))

        if self.nickname_active and int(pygame.time.get_ticks() / 500) % 2 == 0:
            cursor_x = text_x + text_surf.get_width() + 2
            cursor_y = text_y
            cursor_h = text_surf.get_height()
            pygame.draw.line(screen, (255, 215, 0), (cursor_x, cursor_y), (cursor_x, cursor_y + cursor_h), 2)

        limit_font = self._get_font(int(self.nickname_input_rect.height * 0.25))
        limit = limit_font.render(f"{len(self.nickname_input)}/12", True, (100, 100, 120))
        lx = self.nickname_input_rect.right - limit.get_width() - 10
        ly = self.nickname_input_rect.bottom - limit.get_height() - 5
        screen.blit(limit, (lx, ly))

        # Botões
        btn_color = (60, 120, 60) if self.confirm_nick_hover else (40, 80, 40)
        pygame.draw.rect(screen, btn_color, self.confirm_nick_button, border_radius=8)
        pygame.draw.rect(screen, (100, 180, 100), self.confirm_nick_button, 2, border_radius=8)
        btn_font = self._get_font(int(self.confirm_nick_button.height * 0.5))
        ctext = btn_font.render("CONFIRMAR", True, (255, 255, 255))
        cx = self.confirm_nick_button.x + (self.confirm_nick_button.width - ctext.get_width()) // 2
        cy = self.confirm_nick_button.y + (self.confirm_nick_button.height - ctext.get_height()) // 2
        screen.blit(ctext, (cx, cy))

        skip_color = (80, 60, 60) if self.skip_nick_hover else (60, 40, 40)
        pygame.draw.rect(screen, skip_color, self.skip_nick_button, border_radius=8)
        pygame.draw.rect(screen, (180, 100, 100), self.skip_nick_button, 2, border_radius=8)
        stext = btn_font.render("PULAR", True, (255, 255, 255))
        sx2 = self.skip_nick_button.x + (self.skip_nick_button.width - stext.get_width()) // 2
        sy2 = self.skip_nick_button.y + (self.skip_nick_button.height - stext.get_height()) // 2
        screen.blit(stext, (sx2, sy2))

    def _draw_gradient_background(self, screen):
        w = self.screen_manager.window_width
        h = self.screen_manager.window_height
        if self.bg_gradient is None or self.bg_gradient.get_width() != w or self.bg_gradient.get_height() != h:
            self.bg_gradient = pygame.Surface((w, h))
            for i in range(h):
                t = i / h
                r = int(20 + t * 60)
                g = int(20 + t * 30)
                b = int(60 + t * 100)
                pygame.draw.line(self.bg_gradient, (r, g, b), (0, i), (w, i))
        screen.blit(self.bg_gradient, (0, 0))

    def _get_font(self, size, bold=False):
        from src.core.render_context import render_context
        return render_context.get_font(size, bold)