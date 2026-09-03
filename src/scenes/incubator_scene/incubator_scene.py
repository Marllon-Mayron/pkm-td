# src/scenes/incubator_scene/incubator_scene.py
import pygame
from src.scenes.base_scene import BaseScene
from src.data.item_bag_catalog import item_bag_catalog
from src.data.pokedex import Pokedex


class IncubatorScene(BaseScene):
    def __init__(self, game):
        super().__init__(game)
        self.player = game.player
        self.catalog = item_bag_catalog
        self.pokedex = Pokedex()

        # Garante que o jogador tem pelo menos um desfossilizador
        if not self.player.desfossilizadores:
            self.player._add_initial_desfossilizador()

        self.back_button_rect = None
        self.buy_button_rect = None
        self.fonts = self._create_fonts()
        self.layout_initialized = False
        self.selected_index = -1
        self.feedback_message = ""
        self.feedback_timer = 0.0

        # Dialog de seleção de fóssil
        self.fossil_dialog_active = False
        self.fossil_dialog_index = -1
        self.fossil_options = []
        self.selected_fossil_index = 0
        self.fossil_dialog_rect = None
        self.fossil_dialog_hover = -1
        self.fossil_scroll_offset = 0
        self.fossil_max_scroll = 0

        # ===== OVERLAY DE REVELAÇÃO =====
        self.reveal_active = False
        self.reveal_pokemon = None
        self.reveal_direction_index = 0
        self.reveal_direction_timer = 0
        self.reveal_direction_interval = 1.5
        self.reveal_frame_index = 0
        self.reveal_frame_timer = 0
        self.reveal_animation_speed = 0.15
        self.reveal_show_name = False
        self.reveal_timer = 0
        self.reveal_continue_button = None
        self.reveal_continue_hovered = False
        self._reveal_cached_frames = {}
        self._reveal_sprite_size_cache = {}
        self.reveal_directions = ["down", "down-right", "right", "up-right", "up", "up-left", "left", "down-left"]

        # Timer para auto-save
        self.auto_save_timer = 0.0
        self.auto_save_interval = 10.0

        # Preço do desfossilizador
        self.desfossilizador_price = 15000

        # Slots (fixos)
        self.max_slots = 3

    def _create_fonts(self):
        base = max(16, self.screen_manager.window_height // 45)
        return {
            'title': pygame.font.Font(None, base * 2),
            'large': pygame.font.Font(None, base),
            'medium': pygame.font.Font(None, base - 2),
            'small': pygame.font.Font(None, base - 4)
        }

    # ===== MÉTODOS DO OVERLAY DE REVELAÇÃO =====
    def _get_reveal_frames(self, pokemon_id, direction):
        """Obtém os frames da animação para o overlay de revelação"""
        cache_key = f"{pokemon_id}_{direction}"

        if cache_key in self._reveal_cached_frames:
            return self._reveal_cached_frames[cache_key]

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
            for d in self.reveal_directions:
                frames = anim.get(d, [])
                if frames:
                    break

        self._reveal_cached_frames[cache_key] = frames
        return frames

    def _get_reveal_sprite_size(self, pokemon_id):
        """Obtém o tamanho do sprite para o overlay"""
        cache_key = f"{pokemon_id}_reveal_size"

        if cache_key in self._reveal_sprite_size_cache:
            return self._reveal_sprite_size_cache[cache_key]

        try:
            size = self.pokedex.get_map_sprite_size(pokemon_id, shiny=False)
            if size > 0:
                scaled_size = int(size * 4.0)
                self._reveal_sprite_size_cache[cache_key] = scaled_size
                return scaled_size
        except:
            pass

        default_size = 32 * 4
        self._reveal_sprite_size_cache[cache_key] = default_size
        return default_size

    def _open_reveal_overlay(self, pokemon):
        """Abre o overlay de revelação do Pokémon"""
        self.reveal_active = True
        self.reveal_pokemon = pokemon
        self.reveal_direction_index = 0
        self.reveal_direction_timer = 0
        self.reveal_frame_index = 0
        self.reveal_frame_timer = 0
        self.reveal_show_name = False
        self.reveal_timer = 0
        self.reveal_continue_button = None
        self.reveal_continue_hovered = False
        self._reveal_cached_frames = {}
        self._reveal_sprite_size_cache = {}

    def _render_reveal_overlay(self, screen):
        """Renderiza o overlay de revelação"""
        vp_x = self.screen_manager.viewport_x
        vp_y = self.screen_manager.viewport_y
        vp_w = self.screen_manager.viewport_width
        vp_h = self.screen_manager.viewport_height

        # Overlay escuro
        overlay = pygame.Surface((vp_w, vp_h))
        overlay.set_alpha(220)
        overlay.fill((0, 0, 0))
        screen.blit(overlay, (vp_x, vp_y))

        # Área do overlay (centralizada)
        overlay_width = min(500, vp_w - 100)
        overlay_height = min(500, vp_h - 100)
        overlay_x = vp_x + (vp_w - overlay_width) // 2
        overlay_y = vp_y + (vp_h - overlay_height) // 2

        reveal_rect = pygame.Rect(overlay_x, overlay_y, overlay_width, overlay_height)
        pygame.draw.rect(screen, (30, 35, 50), reveal_rect, border_radius=16)
        pygame.draw.rect(screen, (255, 215, 0), reveal_rect, 2, border_radius=16)

        # ===== NOME DO POKEMON (MAIS PARA CIMA) =====
        name_y_offset = 30
        if self.reveal_show_name:
            name_font = self.fonts['title']
            display_name = self.reveal_pokemon.custom_name if self.reveal_pokemon.custom_name else self.reveal_pokemon.name
            name_text = name_font.render(display_name, True, (255, 255, 255))

            # Sombra do nome
            shadow = name_font.render(display_name, True, (0, 0, 0))
            screen.blit(shadow,
                        (reveal_rect.centerx - name_text.get_width() // 2 + 2, reveal_rect.y + name_y_offset + 2))
            screen.blit(name_text, (reveal_rect.centerx - name_text.get_width() // 2, reveal_rect.y + name_y_offset))

            # Informações adicionais (nível)
            info_font = self.fonts['medium']

            info_text = f"Nv.{self.reveal_pokemon.level}"
            info_surf = info_font.render(info_text, True, (200, 200, 200))
            screen.blit(info_surf,
                        (reveal_rect.centerx - info_surf.get_width() // 2, reveal_rect.y + name_y_offset + 40))

        # ===== SPRITE DO POKEMON =====
        sprite_size = self._get_reveal_sprite_size(self.reveal_pokemon.id)
        max_display = min(overlay_width - 80, overlay_height - 200)
        display_size = min(sprite_size, max_display)

        direction = self.reveal_directions[self.reveal_direction_index]
        frames = self._get_reveal_frames(self.reveal_pokemon.id, direction)
        frame_idx = min(self.reveal_frame_index, len(frames) - 1) if frames else 0
        sprite = frames[frame_idx] if frames and frame_idx < len(frames) else None

        if sprite:
            scaled_sprite = pygame.transform.scale(sprite, (display_size, display_size))
            sprite_x = reveal_rect.centerx - display_size // 2
            sprite_y = reveal_rect.y + 120
            screen.blit(scaled_sprite, (sprite_x, sprite_y))

            # Efeito shiny
            if self.reveal_pokemon.is_shiny:
                glow = pygame.Surface((display_size, display_size), pygame.SRCALPHA)
                glow.fill((255, 215, 0, 60))
                screen.blit(glow, (sprite_x, sprite_y))

                shiny_font = pygame.font.Font(None, 24)
                shiny_text = shiny_font.render("★ SHINY ★", True, (255, 215, 0))
                screen.blit(shiny_text,
                            (reveal_rect.centerx - shiny_text.get_width() // 2, sprite_y + display_size + 10))
        else:
            # Placeholder
            font = pygame.font.Font(None, 60)
            text = font.render("?", True, (150, 150, 150))
            screen.blit(text, (reveal_rect.centerx - text.get_width() // 2, reveal_rect.centery - 30))

        # ===== INDICADOR DE DIREÇÃO =====
        dir_font = pygame.font.Font(None, 14)
        direction_names = ["DOWN", "D-R", "RIGHT", "U-R", "UP", "U-L", "LEFT", "D-L"]

        total_width = 0
        text_surfaces = []
        for i, d in enumerate(direction_names):
            if i == self.reveal_direction_index:
                color = (255, 215, 0)
                text = f"[{d}]"
            else:
                color = (100, 100, 120)
                text = d
            surf = dir_font.render(text, True, color)
            text_surfaces.append((surf, i == self.reveal_direction_index))
            total_width += surf.get_width() + 4

        start_x = reveal_rect.centerx - total_width // 2
        current_x = start_x
        y_pos = reveal_rect.y + overlay_height - 80

        for surf, is_active in text_surfaces:
            screen.blit(surf, (current_x, y_pos))
            current_x += surf.get_width() + 4

        # ===== BARRA DE PROGRESSO DA ROTAÇÃO =====
        progress = self.reveal_direction_timer / self.reveal_direction_interval
        bar_width = 200
        bar_height = 4
        bar_x = reveal_rect.centerx - bar_width // 2
        bar_y = y_pos + 22

        pygame.draw.rect(screen, (40, 40, 50), (bar_x, bar_y, bar_width, bar_height), border_radius=2)
        if progress > 0:
            fill_width = int(bar_width * progress)
            pygame.draw.rect(screen, (255, 215, 0), (bar_x, bar_y, fill_width, bar_height), border_radius=2)

        # ===== BOTÃO CONTINUAR =====
        btn_width = 160
        btn_height = 40
        self.reveal_continue_button = pygame.Rect(
            reveal_rect.centerx - btn_width // 2,
            bar_y + 30,
            btn_width, btn_height
        )

        color = (60, 120, 60) if self.reveal_continue_hovered else (40, 80, 40)
        border_color = (100, 180, 100) if self.reveal_continue_hovered else (80, 120, 80)

        shadow_rect = self.reveal_continue_button.copy()
        shadow_rect.x += 2
        shadow_rect.y += 2
        pygame.draw.rect(screen, (0, 0, 0, 60), shadow_rect, border_radius=8)

        pygame.draw.rect(screen, color, self.reveal_continue_button, border_radius=8)
        pygame.draw.rect(screen, border_color, self.reveal_continue_button, 2, border_radius=8)

        btn_font = self.fonts['medium']
        btn_text = btn_font.render("CONTINUAR", True, (255, 255, 255))
        screen.blit(btn_text, (self.reveal_continue_button.x + (btn_width - btn_text.get_width()) // 2,
                               self.reveal_continue_button.y + (btn_height - btn_text.get_height()) // 2))

    # ===== MÉTODOS PRINCIPAIS =====
    def handle_event(self, event):
        # ===== OVERLAY DE REVELAÇÃO =====
        if self.reveal_active:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE or event.key == pygame.K_RETURN or event.key == pygame.K_SPACE:
                    self.reveal_active = False
                    return True

            if event.type == pygame.MOUSEMOTION:
                if self.reveal_continue_button:
                    self.reveal_continue_hovered = self.reveal_continue_button.collidepoint(event.pos)

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self.reveal_continue_button and self.reveal_continue_button.collidepoint(event.pos):
                    self.reveal_active = False
                    return True

            return False

        if self.fossil_dialog_active:
            return self._handle_fossil_dialog_event(event)

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self._go_back()
                return True

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.back_button_rect and self.back_button_rect.collidepoint(event.pos):
                self._go_back()
                return True

            if self.buy_button_rect and self.buy_button_rect.collidepoint(event.pos):
                self._buy_desfossilizador()
                return True

            # ===== VERIFICA CLIQUE NOS BOTÕES DE UPGRADE PRIMEIRO =====
            for i in range(self.max_slots):
                if i < len(self.player.desfossilizadores):
                    d = self.player.desfossilizadores[i]
                    if d["status"] == "empty" and d["level"] < 3:
                        slot_rect = self._get_slot_rect(i)
                        # Calcula a posição do botão de upgrade (igual ao render)
                        up_rect = pygame.Rect(
                            slot_rect.x + (slot_rect.width - 110) // 2,
                            slot_rect.bottom - 95,
                            110, 28
                        )
                        if up_rect.collidepoint(event.pos):
                            self._upgrade_desfossilizador(i)
                            return True

            # ===== VERIFICA CLIQUE NOS SLOTS =====
            for i in range(self.max_slots):
                slot_rect = self._get_slot_rect(i)
                if slot_rect and slot_rect.collidepoint(event.pos):
                    if i < len(self.player.desfossilizadores):
                        self.selected_index = i
                        self._handle_slot_click(i)
                    return True

        return False

    def _handle_fossil_dialog_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.fossil_dialog_active = False
                return True
            elif event.key == pygame.K_UP:
                self.selected_fossil_index = max(0, self.selected_fossil_index - 1)
                return True
            elif event.key == pygame.K_DOWN:
                self.selected_fossil_index = min(len(self.fossil_options) - 1, self.selected_fossil_index + 1)
                return True
            elif event.key == pygame.K_RETURN:
                self._confirm_fossil_selection()
                return True

        if event.type == pygame.MOUSEWHEEL:
            if self.fossil_dialog_active:
                self.fossil_scroll_offset -= event.y * 30
                self.fossil_scroll_offset = max(0, min(self.fossil_max_scroll, self.fossil_scroll_offset))
                return True

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for i in range(len(self.fossil_options)):
                item_rect = self._get_fossil_item_rect(i)
                if item_rect and item_rect.collidepoint(event.pos):
                    self.selected_fossil_index = i
                    self._confirm_fossil_selection()
                    return True

            if self.fossil_dialog_rect and not self.fossil_dialog_rect.collidepoint(event.pos):
                self.fossil_dialog_active = False
                return True

        if event.type == pygame.MOUSEMOTION:
            self.fossil_dialog_hover = -1
            for i in range(len(self.fossil_options)):
                item_rect = self._get_fossil_item_rect(i)
                if item_rect and item_rect.collidepoint(event.pos):
                    self.fossil_dialog_hover = i
                    break

        return False

    def _get_fossil_item_rect(self, index):
        if not self.fossil_dialog_rect:
            return None
        x = self.fossil_dialog_rect.x + 20
        y = self.fossil_dialog_rect.y + 80 + index * 60 - self.fossil_scroll_offset
        width = self.fossil_dialog_rect.width - 40
        height = 50
        return pygame.Rect(x, y, width, height)

    def _buy_desfossilizador(self):
        if len(self.player.desfossilizadores) >= self.max_slots:
            self.feedback_message = "Voce ja tem o maximo de 3 desfossilizadores!"
            self.feedback_timer = 2.0
            return

        if self.player.money < self.desfossilizador_price:
            self.feedback_message = f"Voce precisa de ${self.desfossilizador_price} para comprar um desfossilizador!"
            self.feedback_timer = 2.0
            return

        self.player.money -= self.desfossilizador_price
        self.player.add_desfossilizador(1)
        self.feedback_message = "Novo desfossilizador comprado!"
        self.feedback_timer = 2.0
        self.game.player.auto_save()

    def _go_back(self):
        from src.scenes.phase_selector.phase_select_scene import PhaseSelectScene
        self.game.current_scene = PhaseSelectScene(self.game)

    def _get_slot_rect(self, index):
        vp_x = self.screen_manager.viewport_x
        vp_y = self.screen_manager.viewport_y
        vp_w = self.screen_manager.viewport_width
        vp_h = self.screen_manager.viewport_height

        slot_width = min(250, (vp_w - 120) // 3)
        slot_height = min(350, vp_h - 220)

        total_width = slot_width * 3 + 40 * 2
        start_x = vp_x + (vp_w - total_width) // 2
        start_y = vp_y + 120

        x = start_x + index * (slot_width + 40)
        y = start_y

        return pygame.Rect(x, y, slot_width, slot_height)

    def _handle_slot_click(self, index):
        if index >= len(self.player.desfossilizadores):
            return

        desfossilizador = self.player.desfossilizadores[index]
        if desfossilizador["status"] == "empty":
            self._open_fossil_selection(index)
        elif desfossilizador["status"] == "ready":
            self._collect_pokemon(index)
        elif desfossilizador["status"] == "processing":
            pass

    def _open_fossil_selection(self, index):
        self.fossil_options = []
        for item_id, qty in self.player.bag.items.items():
            item_data = self.catalog.get_item(item_id)
            if item_data and item_data.get("category") == "fossil" and qty > 0:
                self.fossil_options.append({
                    "id": item_id,
                    "name": item_data["name"],
                    "qty": qty,
                    "pokemon_id": self._get_pokemon_from_fossil(item_id)
                })

        if not self.fossil_options:
            self.feedback_message = "Voce nao possui fosseis!"
            self.feedback_timer = 2.0
            return

        self.fossil_dialog_active = True
        self.fossil_dialog_index = index
        self.selected_fossil_index = 0
        self.fossil_scroll_offset = 0

        vp_w = self.screen_manager.viewport_width
        vp_h = self.screen_manager.viewport_height
        dialog_w = min(500, vp_w - 100)
        max_dialog_h = min(500, vp_h - 100)

        item_height = 60
        total_items_height = len(self.fossil_options) * item_height + 100
        dialog_h = min(max_dialog_h, total_items_height)
        self.fossil_max_scroll = max(0, total_items_height - dialog_h + 20)

        self.fossil_dialog_rect = pygame.Rect(
            (vp_w - dialog_w) // 2,
            (vp_h - dialog_h) // 2,
            dialog_w,
            dialog_h
        )

    def _get_pokemon_from_fossil(self, fossil_id):
        fossil_to_pokemon = {
            "helix_fossil": 138,
            "dome_fossil": 140,
            "old_amber": 142
        }
        return fossil_to_pokemon.get(fossil_id)

    def _confirm_fossil_selection(self):
        if self.selected_fossil_index < 0 or self.selected_fossil_index >= len(self.fossil_options):
            return

        option = self.fossil_options[self.selected_fossil_index]
        fossil_id = option["id"]
        pokemon_id = option["pokemon_id"]

        if not pokemon_id:
            self.feedback_message = "Fossil invalido!"
            self.feedback_timer = 2.0
            self.fossil_dialog_active = False
            return

        if self.player.money < 2500:
            self.feedback_message = "Voce precisa de $2500 para a energia!"
            self.feedback_timer = 2.0
            self.fossil_dialog_active = False
            return

        self.player.bag.remove_item(fossil_id, 1)
        self.player.money -= 2

        self.player.start_desfossilizacao(self.fossil_dialog_index, fossil_id, pokemon_id)
        pokemon_name = self.pokedex.get_name(pokemon_id)
        self.feedback_message = f"Iniciando desfossilizacao de {pokemon_name}!"
        self.feedback_timer = 2.0
        self.fossil_dialog_active = False
        self.game.player.auto_save()

    def _collect_pokemon(self, index):
        pokemon = self.player.collect_pokemon_from_desfossilizador(index)
        if pokemon:
            self.feedback_message = f"{pokemon.name} foi revivido!"
            self.feedback_timer = 2.0
            self.game.player.auto_save()
            self._open_reveal_overlay(pokemon)
        else:
            self.feedback_message = "Erro ao coletar Pokemon!"
            self.feedback_timer = 2.0

    def _upgrade_desfossilizador(self, index):
        """Faz upgrade do desfossilizador"""
        if index >= len(self.player.desfossilizadores):
            return

        desfossilizador = self.player.desfossilizadores[index]
        if desfossilizador["level"] >= 3:
            self.feedback_message = "Nivel maximo atingido!"
            self.feedback_timer = 2.0
            return

        new_level = desfossilizador["level"] + 1
        cost = 30000 if desfossilizador["level"] == 1 else 50000

        if self.player.money < cost:
            self.feedback_message = f"Voce precisa de ${cost} para o upgrade!"
            self.feedback_timer = 2.0
            return

        # Faz o upgrade
        self.player.money -= cost
        desfossilizador["level"] = new_level
        desfossilizador["duration_minutes"] = self.player._get_duration_for_level(new_level)

        self.feedback_message = f"Desfossilizador #{desfossilizador['id']} agora esta no nivel {new_level}!"
        self.feedback_timer = 2.0
        self.game.player.auto_save()

    def fixed_update(self, dt):
        if not self.layout_initialized:
            self._create_layout()
            self.layout_initialized = True

        self.player.total_playtime += dt
        self.player.update_desfossilizadores(dt)

        # ===== OVERLAY DE REVELAÇÃO =====
        if self.reveal_active and self.reveal_pokemon:
            self.reveal_timer += dt

            if self.reveal_timer >= 0.5:
                self.reveal_show_name = True

            self.reveal_direction_timer += dt
            if self.reveal_direction_timer >= self.reveal_direction_interval:
                self.reveal_direction_timer = 0
                self.reveal_direction_index = (self.reveal_direction_index + 1) % 8

            direction = self.reveal_directions[self.reveal_direction_index]
            frames = self._get_reveal_frames(self.reveal_pokemon.id, direction)
            if frames and len(frames) > 1:
                self.reveal_frame_timer += dt
                if self.reveal_frame_timer >= self.reveal_animation_speed:
                    self.reveal_frame_timer = 0
                    self.reveal_frame_index = (self.reveal_frame_index + 1) % len(frames)
            else:
                self.reveal_frame_index = 0

        # Auto-save durante processamento
        has_processing = any(d["status"] == "processing" for d in self.player.desfossilizadores)
        if has_processing:
            self.auto_save_timer += dt
            if self.auto_save_timer >= self.auto_save_interval:
                self.auto_save_timer = 0.0
                self.game.player.auto_save()

        if self.feedback_timer > 0:
            self.feedback_timer -= dt
            if self.feedback_timer < 0:
                self.feedback_timer = 0

        # Notifica quando pronto
        for i, d in enumerate(self.player.desfossilizadores):
            if d["status"] == "ready":
                if not hasattr(self, '_ready_notified'):
                    self._ready_notified = set()
                if i not in self._ready_notified:
                    self._ready_notified.add(i)
                    pokemon_name = self.pokedex.get_name(d["pokemon_id"])
                    self.feedback_message = f"{pokemon_name} esta pronto para ser coletado!"
                    self.feedback_timer = 3.0
                    self.game.player.auto_save()

    def render(self, screen):
        self._draw_background(screen)
        vp_x = self.screen_manager.viewport_x
        vp_y = self.screen_manager.viewport_y
        vp_w = self.screen_manager.viewport_width
        vp_h = self.screen_manager.viewport_height

        # Título
        title = self.fonts['title'].render("DESFOSSILIZADOR", True, (255, 215, 0))
        screen.blit(title, (vp_x + (vp_w - title.get_width()) // 2, vp_y + 20))

        # Botão voltar
        self.back_button_rect = pygame.Rect(vp_x + 20, vp_y + 20, 100, 40)
        pygame.draw.rect(screen, (40, 40, 45), self.back_button_rect, border_radius=8)
        pygame.draw.rect(screen, (100, 100, 120), self.back_button_rect, 2, border_radius=8)
        back_text = self.fonts['medium'].render("Voltar", True, (200, 200, 210))
        screen.blit(back_text, (self.back_button_rect.x + 20, self.back_button_rect.y + 8))

        # Botão comprar desfossilizador
        can_buy = len(self.player.desfossilizadores) < self.max_slots
        buy_x = vp_x + vp_w - 200
        self.buy_button_rect = pygame.Rect(buy_x, vp_y + 20, 170, 40)

        if can_buy and self.player.money >= self.desfossilizador_price:
            color = (60, 120, 60)
            border_color = (100, 180, 100)
            text_color = (255, 255, 255)
        else:
            color = (60, 60, 60)
            border_color = (80, 80, 80)
            text_color = (150, 150, 150)

        shadow_rect = self.buy_button_rect.copy()
        shadow_rect.x += 2
        shadow_rect.y += 2
        pygame.draw.rect(screen, (0, 0, 0, 60), shadow_rect, border_radius=8)

        pygame.draw.rect(screen, color, self.buy_button_rect, border_radius=8)
        pygame.draw.rect(screen, border_color, self.buy_button_rect, 2, border_radius=8)

        if can_buy:
            buy_text = self.fonts['small'].render(f"Comprar ${self.desfossilizador_price}", True, text_color)
        else:
            buy_text = self.fonts['small'].render("Maximo 3", True, text_color)
        screen.blit(buy_text, (self.buy_button_rect.x + 10, self.buy_button_rect.y + 10))

        # Renderiza os 3 slots
        self._render_slots(screen, vp_x, vp_y, vp_w, vp_h)

        # Feedback
        if self.feedback_timer > 0:
            self._render_feedback(screen, vp_x, vp_y, vp_w, vp_h)

        # Dialog de seleção de fóssil
        if self.fossil_dialog_active:
            self._render_fossil_dialog(screen)

        # Overlay de revelação (por cima de tudo)
        if self.reveal_active:
            self._render_reveal_overlay(screen)

    def _render_slots(self, screen, vp_x, vp_y, vp_w, vp_h):
        for i in range(self.max_slots):
            slot_rect = self._get_slot_rect(i)

            has_desfossilizador = i < len(self.player.desfossilizadores)

            if has_desfossilizador:
                d = self.player.desfossilizadores[i]

                if d["status"] == "empty":
                    bg_color = (35, 40, 55)
                elif d["status"] == "processing":
                    bg_color = (45, 55, 70)
                elif d["status"] == "ready":
                    bg_color = (40, 70, 50)

                shadow_rect = slot_rect.copy()
                shadow_rect.x += 4
                shadow_rect.y += 4
                pygame.draw.rect(screen, (0, 0, 0, 60), shadow_rect, border_radius=12)

                pygame.draw.rect(screen, bg_color, slot_rect, border_radius=12)
                pygame.draw.rect(screen, (100, 120, 180), slot_rect, 2, border_radius=12)

                num_font = self.fonts['small']
                num_text = num_font.render(f"#{d['id']} - Nivel {d['level']}", True, (200, 200, 220))
                screen.blit(num_text, (slot_rect.x + 15, slot_rect.y + 10))

                # SPRITE DO FÓSSIL NO CENTRO
                if d["fossil_id"]:
                    sprite = self.catalog.get_sprite(d["fossil_id"], scaled=True)
                    if sprite:
                        sprite_size = min(slot_rect.width - 60, slot_rect.height - 120)
                        scaled_sprite = pygame.transform.scale(sprite, (sprite_size, sprite_size))
                        sprite_x = slot_rect.x + (slot_rect.width - sprite_size) // 2
                        sprite_y = slot_rect.y + 60
                        screen.blit(scaled_sprite, (sprite_x, sprite_y))
                    else:
                        self._draw_fossil_placeholder(screen, slot_rect)
                else:
                    self._draw_fossil_placeholder(screen, slot_rect)

                # STATUS E INFORMAÇÕES
                if d["status"] == "empty":
                    status_text = "VAZIO"
                    status_color = (180, 180, 180)

                    # Botão "Colocar Fóssil"
                    btn_rect = pygame.Rect(
                        slot_rect.x + (slot_rect.width - 140) // 2,
                        slot_rect.bottom - 50,
                        140, 35
                    )
                    pygame.draw.rect(screen, (60, 120, 200), btn_rect, border_radius=6)
                    btn_text = self.fonts['small'].render("COLOCAR FOSSIL", True, (255, 255, 255))
                    screen.blit(btn_text, (btn_rect.x + 10, btn_rect.y + 8))

                    # Botão Upgrade - AGORA COM UM RETÂNGULO MAIS VISÍVEL
                    if d["level"] < 3:
                        cost = 30000 if d["level"] == 1 else 50000
                        up_rect = pygame.Rect(
                            slot_rect.x + (slot_rect.width - 110) // 2,
                            slot_rect.bottom - 95,
                            110, 28
                        )
                        can_upgrade = self.player.money >= cost
                        color_up = (200, 160, 50) if can_upgrade else (100, 100, 100)
                        pygame.draw.rect(screen, color_up, up_rect, border_radius=4)
                        # Borda mais visível para indicar que é clicável
                        border_up = (255, 200, 100) if can_upgrade else (80, 80, 80)
                        pygame.draw.rect(screen, border_up, up_rect, 1, border_radius=4)

                        up_text = self.fonts['small'].render(f"UPGRADE ${cost}", True, (255, 255, 255))
                        screen.blit(up_text, (up_rect.x + (up_rect.width - up_text.get_width()) // 2, up_rect.y + 5))

                elif d["status"] == "processing":
                    progress = d["time_elapsed"] / d["duration_minutes"]
                    progress = min(1.0, progress)
                    status_text = f"{int(progress * 100)}%"
                    status_color = (255, 215, 0)

                    bar_rect = pygame.Rect(
                        slot_rect.x + 20,
                        slot_rect.bottom - 35,
                        slot_rect.width - 40,
                        12
                    )
                    pygame.draw.rect(screen, (50, 50, 60), bar_rect, border_radius=6)
                    if progress > 0:
                        fill_w = int(bar_rect.width * progress)
                        pygame.draw.rect(screen, (0, 200, 100), (bar_rect.x, bar_rect.y, fill_w, bar_rect.height),
                                         border_radius=6)

                    remaining = max(0, d["duration_minutes"] - d["time_elapsed"])
                    mins = int(remaining // 60)
                    secs = int(remaining % 60)
                    time_text = self.fonts['medium'].render(f"{mins:02d}:{secs:02d}", True, (255, 255, 255))
                    screen.blit(time_text,
                                (slot_rect.x + (slot_rect.width - time_text.get_width()) // 2, slot_rect.bottom - 70))

                elif d["status"] == "ready":
                    status_text = "PRONTO!"
                    status_color = (0, 255, 0)

                    btn_rect = pygame.Rect(
                        slot_rect.x + (slot_rect.width - 140) // 2,
                        slot_rect.bottom - 50,
                        140, 35
                    )
                    pygame.draw.rect(screen, (50, 200, 50), btn_rect, border_radius=6)
                    btn_text = self.fonts['small'].render("COLETAR", True, (0, 0, 0))
                    screen.blit(btn_text, (btn_rect.x + 35, btn_rect.y + 8))

                status_surf = self.fonts['large'].render(status_text, True, status_color)
                screen.blit(status_surf,
                            (slot_rect.x + (slot_rect.width - status_surf.get_width()) // 2, slot_rect.y + 35))

            else:
                # Slot vazio
                shadow_rect = slot_rect.copy()
                shadow_rect.x += 4
                shadow_rect.y += 4
                pygame.draw.rect(screen, (0, 0, 0, 40), shadow_rect, border_radius=12)

                pygame.draw.rect(screen, (20, 22, 30), slot_rect, border_radius=12)
                pygame.draw.rect(screen, (50, 50, 60), slot_rect, 2, border_radius=12)

                empty_text = self.fonts['large'].render("VAZIO", True, (80, 80, 90))
                screen.blit(empty_text, (slot_rect.x + (slot_rect.width - empty_text.get_width()) // 2,
                                         slot_rect.y + (slot_rect.height - empty_text.get_height()) // 2))

    def _draw_fossil_placeholder(self, screen, slot_rect):
        center_x = slot_rect.x + slot_rect.width // 2
        center_y = slot_rect.y + 60 + (slot_rect.height - 120) // 2
        radius = min(slot_rect.width - 60, slot_rect.height - 120) // 2

        pygame.draw.circle(screen, (50, 55, 70), (center_x, center_y), radius)
        pygame.draw.circle(screen, (80, 85, 100), (center_x, center_y), radius, 2)

        font = pygame.font.Font(None, radius)
        text = font.render("?", True, (80, 85, 100))
        screen.blit(text, (center_x - text.get_width() // 2, center_y - text.get_height() // 2))

    def _render_fossil_dialog(self, screen):
        overlay = pygame.Surface((self.screen_manager.window_width, self.screen_manager.window_height))
        overlay.set_alpha(180)
        overlay.fill((0, 0, 0))
        screen.blit(overlay, (0, 0))

        rect = self.fossil_dialog_rect
        pygame.draw.rect(screen, (40, 45, 60), rect, border_radius=12)
        pygame.draw.rect(screen, (255, 215, 0), rect, 2, border_radius=12)

        title_font = self.fonts['medium']
        title = title_font.render("SELECIONE UM FOSSIL", True, (255, 215, 0))
        screen.blit(title, (rect.x + (rect.width - title.get_width()) // 2, rect.y + 15))

        old_clip = screen.get_clip()
        clip_rect = pygame.Rect(
            rect.x + 15,
            rect.y + 60,
            rect.width - 30,
            rect.height - 90
        )
        screen.set_clip(clip_rect)

        for i, option in enumerate(self.fossil_options):
            item_rect = self._get_fossil_item_rect(i)
            if not item_rect:
                continue

            if item_rect.bottom < clip_rect.top or item_rect.top > clip_rect.bottom:
                continue

            is_selected = (i == self.selected_fossil_index)
            is_hovered = (i == self.fossil_dialog_hover)

            if is_selected:
                bg_color = (60, 80, 120)
                border_color = (255, 215, 0)
            elif is_hovered:
                bg_color = (50, 60, 80)
                border_color = (100, 120, 180)
            else:
                bg_color = (30, 35, 50)
                border_color = (70, 75, 90)

            pygame.draw.rect(screen, bg_color, item_rect, border_radius=6)
            pygame.draw.rect(screen, border_color, item_rect, 2, border_radius=6)

            sprite = self.catalog.get_sprite(option["id"], scaled=True)
            if sprite:
                sprite_size = 36
                scaled_sprite = pygame.transform.scale(sprite, (sprite_size, sprite_size))
                screen.blit(scaled_sprite, (item_rect.x + 10, item_rect.y + 7))

            text_x = item_rect.x + 56
            text = self.fonts['medium'].render(option["name"], True, (255, 255, 255))
            screen.blit(text, (text_x, item_rect.y + 6))

            pokemon_name = self.pokedex.get_name(option["pokemon_id"]) if option["pokemon_id"] else "?"
            poke_text = self.fonts['small'].render(f"-> {pokemon_name}", True, (180, 200, 220))
            screen.blit(poke_text, (text_x, item_rect.y + 30))

            qty_text = self.fonts['small'].render(f"x{option['qty']}", True, (200, 200, 200))
            screen.blit(qty_text, (item_rect.right - 40, item_rect.y + 15))

            if is_selected:
                check = self.fonts['large'].render(">", True, (0, 255, 0))
                screen.blit(check, (item_rect.x + 6, item_rect.y + 12))

        screen.set_clip(old_clip)

        if self.fossil_max_scroll > 0:
            bar_x = rect.right - 12
            bar_y = rect.y + 60
            bar_height = rect.height - 80

            pygame.draw.rect(screen, (40, 40, 50), (bar_x, bar_y, 4, bar_height))

            thumb_height = max(30, bar_height * (bar_height / (bar_height + self.fossil_max_scroll)))
            thumb_y = bar_y + (self.fossil_scroll_offset / self.fossil_max_scroll) * (bar_height - thumb_height)
            pygame.draw.rect(screen, (100, 120, 180), (bar_x, thumb_y, 4, thumb_height))

        tip = self.fonts['small'].render("Setas navegar | ENTER confirmar | ESC cancelar", True, (150, 150, 150))
        screen.blit(tip, (rect.x + (rect.width - tip.get_width()) // 2, rect.bottom - 22))

    def _render_feedback(self, screen, vp_x, vp_y, vp_w, vp_h):
        alpha = min(255, int(255 * self.feedback_timer * 2))
        if alpha <= 0:
            return
        surf = self.fonts['medium'].render(self.feedback_message, True, (255, 255, 255))
        bg = pygame.Surface((surf.get_width() + 30, surf.get_height() + 12), pygame.SRCALPHA)
        bg.fill((0, 0, 0, 180))
        bg_rect = bg.get_rect(center=(vp_x + vp_w // 2, vp_y + vp_h - 50))
        screen.blit(bg, bg_rect)
        screen.blit(surf, (bg_rect.x + 15, bg_rect.y + 6))

    def _draw_background(self, screen):
        w, h = self.screen_manager.window_width, self.screen_manager.window_height
        for i in range(h):
            value = int(15 + (i / h) * 20)
            pygame.draw.line(screen, (value, value, value + 5), (0, i), (w, i))

    def _create_layout(self):
        pass