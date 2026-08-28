# src/scenes/pokedex_scene/components/pokemon_detail.py

import pygame
from src.scenes.pokedex_scene.utils.constants import COLORS, TYPE_COLORS, SIZES


class PokemonDetail:
    """Painel de detalhes do Pokemon """

    def __init__(self, x, y, width, height):
        self.rect = pygame.Rect(x, y, width, height)
        self.pokemon_id = None
        self.pokemon_data = None
        self.is_caught = False
        self.is_seen = False
        self.show_inmap = False
        self.inmap_frame = 0
        self.inmap_timer = 0
        self.animation_speed = 0.15

        # ===== ROTACAO AUTOMATICA EM SENTIDO HORARIO =====
        self.direction_index = 0
        self.directions = ["down", "right", "up", "left"]
        self.direction_change_timer = 0
        self.direction_change_interval = 1.5  # Muda de direcao a cada 1.5 segundos

        # Botoes (apenas navegacao de Pokemon)
        self.prev_button = None
        self.next_button = None
        self.toggle_view_button = None

        # Remove botoes de direcao
        self.dir_left_button = None
        self.dir_right_button = None

        self.hover_prev = False
        self.hover_next = False
        self.hover_toggle = False
        self.hover_dir_left = False
        self.hover_dir_right = False

        # Cache para o numero de frames da animacao atual
        self._current_frame_count = 0
        self._cached_frames = {}

    def set_pokemon(self, pokemon_id, pokemon_data, is_caught, is_seen):
        self.pokemon_id = pokemon_id
        self.pokemon_data = pokemon_data
        self.is_caught = is_caught
        self.is_seen = is_seen
        self.inmap_frame = 0
        self.inmap_timer = 0
        self.direction_index = 0
        self.direction_change_timer = 0
        self._current_frame_count = 0
        self._cached_frames = {}

    def _get_animation_frames(self, pokedex, direction):
        """Obtem os frames da animacao para uma direcao especifica com cache"""
        cache_key = f"{self.pokemon_id}_{direction}"

        if cache_key in self._cached_frames:
            return self._cached_frames[cache_key]

        # Tenta pegar os frames da animacao InMap
        anim = pokedex.get_inmap_animation(self.pokemon_id, shiny=False)
        frames = anim.get(direction, [])

        # Se nao encontrar, tenta outras direcoes como fallback
        if not frames:
            for fallback_dir in ["down", "right", "left", "up"]:
                frames = anim.get(fallback_dir, [])
                if frames:
                    break

        self._cached_frames[cache_key] = frames
        return frames

    def update(self, dt):
        """Atualiza a animacao com loop continuo e rotacao automatica"""
        if not self.pokemon_id or not self.show_inmap:
            return

        from src.data.pokedex import Pokedex
        pokedex = Pokedex()

        # ===== ATUALIZA O TIMER DE MUDANCA DE DIRECAO =====
        self.direction_change_timer += dt

        # Muda de direcao a cada intervalo (sentido horario)
        if self.direction_change_timer >= self.direction_change_interval:
            self.direction_change_timer = 0
            # Avanca para a proxima direcao (sentido horario)
            self.direction_index = (self.direction_index + 1) % len(self.directions)
            # Reseta o frame ao mudar de direcao
            self.inmap_frame = 0
            self.inmap_timer = 0

        # Obtem os frames da direcao atual
        direction = self.directions[self.direction_index]
        frames = self._get_animation_frames(pokedex, direction)
        frame_count = len(frames)

        # Atualiza o cache do numero de frames
        self._current_frame_count = frame_count

        # Se nao tem frames ou so tem 1, nao anima
        if frame_count <= 1:
            return

        # Atualiza o frame com loop
        self.inmap_timer += dt

        if self.inmap_timer >= self.animation_speed:
            self.inmap_timer = 0
            # LOOP INFINITO: incrementa e reseta usando modulo
            self.inmap_frame = (self.inmap_frame + 1) % frame_count

    def handle_event(self, event, pokedex):
        if not self.pokemon_id:
            return None

        if event.type == pygame.MOUSEMOTION:
            self.hover_prev = self.prev_button and self.prev_button.collidepoint(event.pos)
            self.hover_next = self.next_button and self.next_button.collidepoint(event.pos)
            self.hover_toggle = self.toggle_view_button and self.toggle_view_button.collidepoint(event.pos)

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            # Botao anterior (Pokemon)
            if self.prev_button and self.prev_button.collidepoint(event.pos):
                all_ids = sorted(pokedex.pokemon_data.keys())
                current_idx = all_ids.index(self.pokemon_id) if self.pokemon_id in all_ids else -1
                if current_idx > 0:
                    prev_id = all_ids[current_idx - 1]
                    return {"action": "navigate", "pokemon_id": prev_id}

            # Botao proximo (Pokemon)
            if self.next_button and self.next_button.collidepoint(event.pos):
                all_ids = sorted(pokedex.pokemon_data.keys())
                current_idx = all_ids.index(self.pokemon_id) if self.pokemon_id in all_ids else -1
                if current_idx < len(all_ids) - 1:
                    next_id = all_ids[current_idx + 1]
                    return {"action": "navigate", "pokemon_id": next_id}

            # Botao toggle (InMap/Sprite)
            if self.toggle_view_button and self.toggle_view_button.collidepoint(event.pos):
                if self.is_seen or self.is_caught:
                    self.show_inmap = not self.show_inmap
                    self.inmap_frame = 0
                    self.inmap_timer = 0
                    self.direction_index = 0
                    self.direction_change_timer = 0
                    return {"action": "toggle_view"}

        return None

    def _get_direction(self):
        return self.directions[self.direction_index]

    def _get_sprite(self, pokedex):
        if self.show_inmap:
            direction = self._get_direction()
            sprite = pokedex.get_sprite(
                self.pokemon_id,
                "inmap",
                shiny=False,
                direction=direction,
                frame=self.inmap_frame
            )
            if not sprite:
                sprite = pokedex.get_sprite(
                    self.pokemon_id,
                    "inmap",
                    shiny=False,
                    direction=direction,
                    frame=0
                )
            if not sprite:
                for fallback_dir in ["down", "right", "left", "up"]:
                    sprite = pokedex.get_sprite(
                        self.pokemon_id,
                        "inmap",
                        shiny=False,
                        direction=fallback_dir,
                        frame=0
                    )
                    if sprite:
                        break
            return sprite, SIZES['inmap_sprite_size']
        else:
            sprite = pokedex.get_sprite(self.pokemon_id, "front", shiny=False)
            return sprite, SIZES['sprite_size']

    def render(self, screen, pokedex, fonts):
        # Fundo do detalhe
        pygame.draw.rect(screen, COLORS['bg_secondary'], self.rect, border_radius=8)
        pygame.draw.rect(screen, COLORS['border'], self.rect, 2, border_radius=8)

        if not self.is_seen and not self.is_caught:
            self._render_unknown(screen, fonts)
            self._render_navigation_buttons(screen, pokedex, fonts)
            return

        padding = SIZES['detail_padding']

        # Area do sprite
        sprite_area_height = 220
        sprite_area = pygame.Rect(
            self.rect.x + padding,
            self.rect.y + padding,
            self.rect.width - padding * 2,
            sprite_area_height
        )

        pygame.draw.rect(screen, COLORS['bg_tertiary'], sprite_area, border_radius=8)
        pygame.draw.rect(screen, COLORS['border'], sprite_area, 1, border_radius=8)

        # Sprite do Pokemon
        sprite, sprite_size = self._get_sprite(pokedex)

        if sprite:
            scaled_sprite = pygame.transform.scale(sprite, (sprite_size, sprite_size))
            sprite_x = sprite_area.centerx - sprite_size // 2
            sprite_y = sprite_area.centery - sprite_size // 2
            screen.blit(scaled_sprite, (sprite_x, sprite_y))

            if self.is_caught and self.pokemon_data.get("is_shiny_available", False):
                glow = pygame.Surface((sprite_size, sprite_size), pygame.SRCALPHA)
                glow.fill((255, 215, 0, 40))
                screen.blit(glow, (sprite_x, sprite_y))
        else:
            placeholder_font = pygame.font.Font(None, 60)
            placeholder = placeholder_font.render("?", True, COLORS['text_secondary'])
            screen.blit(placeholder, placeholder.get_rect(center=sprite_area.center))

        # ===== INFORMACOES DA ANIMACAO (MODO AUTOMATICO) =====
        if self.show_inmap:
            info_font = pygame.font.Font(None, 11)

            # Mostra direcao atual e progresso da rotacao
            current_dir = self._get_direction().upper()

            # Calcula progresso da rotacao
            progress = self.direction_change_timer / self.direction_change_interval
            progress_bar = int(progress * 20)
            bar = "[" + "-" * progress_bar + " " * (20 - progress_bar) + "]"

            dir_text = f"{current_dir} {bar}"
            dir_surf = info_font.render(dir_text, True, COLORS['text_accent'])
            screen.blit(dir_surf, (sprite_area.x + 8, sprite_area.bottom - 18))

            # Mostra frame atual
            if self._current_frame_count > 0:
                frame_text = f"Frame: {self.inmap_frame + 1}/{self._current_frame_count}"
                frame_surf = info_font.render(frame_text, True, COLORS['text_secondary'])
                screen.blit(frame_surf, (sprite_area.right - frame_surf.get_width() - 8, sprite_area.bottom - 18))

            # ===== INDICADOR VISUAL DE ROTACAO AUTOMATICA =====
            dir_font = pygame.font.Font(None, 14)

            # Mostra todas as direcoes com a atual destacada
            direction_names = ["DOWN", "RIGHT", "UP", "LEFT"]

            # Renderiza cada direcao com a atual destacada
            current_x = sprite_area.centerx - 60

            for i, d in enumerate(direction_names):
                if i == self.direction_index:
                    color = COLORS['text_accent']
                    text = f"[{d}]"
                else:
                    color = COLORS['text_secondary']
                    text = d

                text_surf = dir_font.render(text, True, color)
                screen.blit(text_surf, (current_x, sprite_area.bottom + 4))
                current_x += text_surf.get_width() + 8

            # Texto "AUTO ROTATE" abaixo
            auto_font = pygame.font.Font(None, 10)
            auto_text = auto_font.render("AUTO ROTATE", True, COLORS['text_secondary'])
            screen.blit(auto_text, (sprite_area.centerx - auto_text.get_width() // 2, sprite_area.bottom + 22))

        # Botao toggle view
        toggle_rect = pygame.Rect(
            sprite_area.right - 85,
            sprite_area.y + 8,
            75, 26
        )
        self.toggle_view_button = toggle_rect

        if self.hover_toggle:
            bg_color = (60, 60, 70)
            border_color = COLORS['text_accent']
        else:
            bg_color = COLORS['bg_list_item']
            border_color = COLORS['border']

        pygame.draw.rect(screen, bg_color, toggle_rect, border_radius=6)
        pygame.draw.rect(screen, border_color, toggle_rect, 2, border_radius=6)

        toggle_text = "INMAP" if not self.show_inmap else "SPRITE"
        toggle_font = pygame.font.Font(None, 13)
        toggle_surf = toggle_font.render(toggle_text, True, COLORS['text_primary'])
        screen.blit(toggle_surf, toggle_surf.get_rect(center=toggle_rect.center))

        # Informacoes do Pokemon
        info_y = sprite_area.bottom + padding + 10  # Mais espaco para o indicador

        # Nome e ID
        if self.is_caught:
            name_color = COLORS['text_caught']
            display_name = self.pokemon_data['name']
            status_text = "CAPTURADO"
            status_color = COLORS['text_caught']
        else:
            name_color = COLORS['text_secondary']
            display_name = self.pokemon_data['name']
            status_text = "VISTO"
            status_color = COLORS['text_secondary']

        name_text = fonts['large'].render(
            f"#{self.pokemon_id:03d} {display_name}",
            True, name_color
        )
        screen.blit(name_text, (self.rect.x + padding, info_y))

        status_text_surf = fonts['small'].render(status_text, True, status_color)
        screen.blit(status_text_surf,
                    (self.rect.right - status_text_surf.get_width() - padding, info_y + 4))

        info_y += 35

        # Tipos
        if self.is_seen or self.is_caught:
            types = self.pokemon_data.get("types", ["normal"])
            type_x = self.rect.x + padding

            for type_name in types:
                type_color = TYPE_COLORS.get(type_name.lower(), (128, 128, 128))
                type_rect = pygame.Rect(type_x, info_y, 65, 24)
                pygame.draw.rect(screen, type_color, type_rect, border_radius=6)
                type_text = fonts['small'].render(type_name.upper(), True, (255, 255, 255))
                text_rect = type_text.get_rect(center=type_rect.center)
                screen.blit(type_text, text_rect)
                type_x += 75

            info_y += 35

        # Stats (apenas capturados)
        if self.is_caught:
            stats_label = fonts['medium'].render("BASE STATS", True, COLORS['text_accent'])
            screen.blit(stats_label, (self.rect.x + padding, info_y))
            info_y += 25

            base_stats = self.pokemon_data.get("base_stats", {})

            stat_names = {
                "hp": "HP",
                "attack": "ATK",
                "defense": "DEF",
                "special_attack": "SPA",
                "special_defense": "SPD",
                "speed": "SPE"
            }

            max_stat = max(base_stats.values()) if base_stats else 100
            stat_height = 16
            stat_gap = 6

            for stat_key, stat_name in stat_names.items():
                if stat_key in base_stats:
                    value = base_stats[stat_key]

                    # Nome do stat
                    name_surf = fonts['small'].render(stat_name, True, COLORS['text_secondary'])
                    screen.blit(name_surf, (self.rect.x + padding, info_y))

                    # Barra
                    bar_x = self.rect.x + padding + 55
                    bar_width = self.rect.width - padding * 2 - 85
                    bar_y = info_y + 2

                    pygame.draw.rect(screen, COLORS['icon_bg'],
                                     (bar_x, bar_y, bar_width, stat_height), border_radius=3)

                    percent = value / max_stat if max_stat > 0 else 0
                    if percent > 0:
                        # Cor baseada no valor
                        if percent > 0.7:
                            bar_color = (100, 200, 100)
                        elif percent > 0.4:
                            bar_color = (255, 200, 50)
                        else:
                            bar_color = (200, 80, 80)

                        pygame.draw.rect(screen, bar_color,
                                         (bar_x, bar_y, int(bar_width * percent), stat_height),
                                         border_radius=3)

                    # Valor
                    value_surf = fonts['small'].render(str(value), True, COLORS['text_primary'])
                    screen.blit(value_surf, (self.rect.right - padding - 20, info_y))

                    info_y += stat_height + stat_gap

        # Botoes de navegacao
        self._render_navigation_buttons(screen, pokedex, fonts)

    def _render_unknown(self, screen, fonts):
        """Renderiza mensagem para Pokemon desconhecido"""
        overlay = pygame.Surface((self.rect.width, self.rect.height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 120))
        screen.blit(overlay, self.rect)

        unknown_text = fonts['large'].render("POKEMON DESCONHECIDO", True, COLORS['text_unseen'])
        unknown_rect = unknown_text.get_rect(center=(self.rect.centerx, self.rect.centery - 30))
        screen.blit(unknown_text, unknown_rect)

        sub_text = fonts['small'].render("Encontre este Pokemon para ver seus dados", True, COLORS['text_secondary'])
        sub_rect = sub_text.get_rect(center=(self.rect.centerx, self.rect.centery + 30))
        screen.blit(sub_text, sub_rect)

        if self.pokemon_id is not None:
            id_text = fonts['medium'].render(f"ID: #{self.pokemon_id:03d}", True, COLORS['text_secondary'])
            id_rect = id_text.get_rect(center=(self.rect.centerx, self.rect.centery + 60))
            screen.blit(id_text, id_rect)

    def _render_navigation_buttons(self, screen, pokedex, fonts):
        """Renderiza os botoes de navegacao"""
        nav_y = self.rect.bottom - 45

        # Botao anterior
        prev_rect = pygame.Rect(
            self.rect.x + SIZES['detail_padding'],
            nav_y,
            55, 34
        )
        self.prev_button = prev_rect

        if self.hover_prev:
            bg_color = (60, 60, 70)
            border_color = COLORS['border_light']
        else:
            bg_color = COLORS['bg_list_item']
            border_color = COLORS['border']

        pygame.draw.rect(screen, bg_color, prev_rect, border_radius=6)
        pygame.draw.rect(screen, border_color, prev_rect, 2, border_radius=6)
        prev_text = pygame.font.Font(None, 22).render("<", True, COLORS['text_primary'])
        screen.blit(prev_text, prev_text.get_rect(center=prev_rect.center))

        # Botao proximo
        next_rect = pygame.Rect(
            self.rect.right - SIZES['detail_padding'] - 55,
            nav_y,
            55, 34
        )
        self.next_button = next_rect

        if self.hover_next:
            bg_color = (60, 60, 70)
            border_color = COLORS['border_light']
        else:
            bg_color = COLORS['bg_list_item']
            border_color = COLORS['border']

        pygame.draw.rect(screen, bg_color, next_rect, border_radius=6)
        pygame.draw.rect(screen, border_color, next_rect, 2, border_radius=6)
        next_text = pygame.font.Font(None, 22).render(">", True, COLORS['text_primary'])
        screen.blit(next_text, next_text.get_rect(center=next_rect.center))

        # Contador
        count_font = pygame.font.Font(None, 14)
        all_ids = sorted(pokedex.pokemon_data.keys())
        if self.pokemon_id in all_ids:
            current_idx = all_ids.index(self.pokemon_id)
            count_text = count_font.render(
                f"{current_idx + 1} / {len(all_ids)}",
                True, COLORS['text_secondary']
            )
            screen.blit(count_text, count_text.get_rect(center=(self.rect.centerx, nav_y + 17)))