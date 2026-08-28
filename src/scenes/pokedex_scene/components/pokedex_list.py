# src/scenes/pokedex_scene/components/pokedex_list.py

import pygame
from pathlib import Path
from src.scenes.pokedex_scene.utils.constants import COLORS, SIZES


class PokemonListItem:
    """Item da lista de Pokémon """

    def __init__(self, pokemon_id, pokemon_data, is_caught, is_seen):
        self.pokemon_id = pokemon_id
        self.name = pokemon_data.get("name", f"Pokemon {pokemon_id}")
        self.is_caught = is_caught
        self.is_seen = is_seen
        self.rect = pygame.Rect(0, 0, 0, SIZES['list_item_height'])
        self.is_hovered = False
        self.is_selected = False
        self._portrait_cache = None
        self._unknown_portrait = None

    def _get_unknown_portrait(self):
        if self._unknown_portrait is None:
            possible_paths = [
                Path("res/PokemonSprites/Portrait/Unknow.png"),
                Path("../res/PokemonSprites/Portrait/Unknow.png"),
                Path(__file__).parent.parent.parent.parent / "res" / "PokemonSprites" / "Portrait" / "Unknow.png",
            ]

            for path in possible_paths:
                try:
                    if path.exists():
                        unknown_img = pygame.image.load(str(path)).convert_alpha()
                        self._unknown_portrait = pygame.transform.scale(unknown_img, (60, 60))
                        break
                except Exception:
                    continue

            if self._unknown_portrait is None:
                self._unknown_portrait = self._create_unknown_fallback()

        return self._unknown_portrait

    def _create_unknown_fallback(self):
        surf = pygame.Surface((60, 60), pygame.SRCALPHA)
        surf.fill((40, 40, 50))
        pygame.draw.rect(surf, (60, 60, 70), (0, 0, 60, 60), 2)
        font = pygame.font.Font(None, 30)
        text = font.render("?", True, (100, 100, 110))
        text_rect = text.get_rect(center=(30, 30))
        surf.blit(text, text_rect)
        return surf

    def _get_portrait(self, pokedex):
        if self._portrait_cache is None:
            if not self.is_seen and not self.is_caught:
                self._portrait_cache = self._get_unknown_portrait()
            else:
                portrait = pokedex.get_portrait(self.pokemon_id, "normal", shiny=False)
                if portrait is None:
                    portrait = pokedex.get_sprite(self.pokemon_id, "front", shiny=False)
                    if portrait:
                        portrait = pygame.transform.scale(portrait, (60, 60))
                else:
                    portrait = pygame.transform.scale(portrait, (60, 60))

                if portrait is None:
                    self._portrait_cache = self._get_unknown_portrait()
                else:
                    self._portrait_cache = portrait
        return self._portrait_cache

    def update_position(self, x, y, width):
        self.rect = pygame.Rect(x, y, width, SIZES['list_item_height'])

    def render(self, screen, pokedex, font_medium, font_small):
        # Fundo
        if self.is_selected:
            bg_color = COLORS['bg_list_item_selected']
            border_color = COLORS['text_accent']
        elif self.is_hovered:
            bg_color = COLORS['bg_list_item_hover']
            border_color = COLORS['border_light']
        elif not self.is_seen and not self.is_caught:
            bg_color = COLORS['bg_list_item_unseen']
            border_color = (40, 40, 45)
        else:
            bg_color = COLORS['bg_list_item']
            border_color = COLORS['border']

        pygame.draw.rect(screen, bg_color, self.rect, border_radius=4)
        pygame.draw.rect(screen, border_color, self.rect, 1, border_radius=4)

        # Portrait (60x60)
        portrait = self._get_portrait(pokedex)
        portrait_size = 60
        portrait_x = self.rect.x + 6
        portrait_y = self.rect.y + (self.rect.height - portrait_size) // 2

        if portrait:
            if portrait.get_width() != portrait_size or portrait.get_height() != portrait_size:
                portrait = pygame.transform.scale(portrait, (portrait_size, portrait_size))
            screen.blit(portrait, (portrait_x, portrait_y))

        # ID e Nome
        text_x = self.rect.x + 75
        id_y = self.rect.y + 12

        id_text = font_small.render(f"#{self.pokemon_id:03d}", True, COLORS['text_secondary'])
        screen.blit(id_text, (text_x, id_y))

        if self.is_caught:
            name_color = COLORS['text_caught']
            display_name = self.name
            status_color = COLORS['text_caught']
            status_text = "CAPTURADO"
        elif self.is_seen:
            name_color = COLORS['text_secondary']
            display_name = self.name
            status_color = COLORS['text_secondary']
            status_text = "VISTO"
        else:
            name_color = COLORS['text_unseen']
            display_name = "????"
            status_color = COLORS['text_unseen']
            status_text = "DESCONHECIDO"

        name_text = font_medium.render(display_name, True, name_color)
        name_y = self.rect.y + (self.rect.height - name_text.get_height()) // 2
        screen.blit(name_text, (text_x, name_y))

        # Status (abaixo do nome)
        status_font = pygame.font.Font(None, 12)
        status_surf = status_font.render(status_text, True, status_color)
        status_y = name_y + name_text.get_height() + 2
        screen.blit(status_surf, (text_x, status_y))


class PokedexList:
    """Lista completa da Pokédex """

    def __init__(self, x, y, width, height):
        self.rect = pygame.Rect(x, y, width, height)
        self.items = []
        self.filtered_items = []
        self.selected_id = None
        self.scroll_y = 0
        self.scroll_target = 0
        self.max_scroll = 0
        self.dragging_scroll = False
        self.last_mouse_y = 0
        self.on_item_click = None
        print(f"[POKEDEX_LIST] Inicializada em: {x}, {y}, {width}x{height}")

    def update_items(self, pokedex_data, player, search_text="", filter_type="all"):
        print(f"[POKEDEX_LIST] update_items chamado - filtro: {filter_type}, busca: '{search_text}'")
        self.items = []

        for pokemon_id, data in pokedex_data.items():
            is_caught = pokemon_id in player.caught_pokemon
            is_seen = pokemon_id in player.seen_pokemon
            item = PokemonListItem(pokemon_id, data, is_caught, is_seen)
            self.items.append(item)

        self.filtered_items = self._apply_filters(search_text, filter_type)
        self.filtered_items.sort(key=lambda x: x.pokemon_id)
        print(f"[POKEDEX_LIST] {len(self.filtered_items)} itens após filtros")

        visible_height = self.rect.height
        total_height = len(self.filtered_items) * SIZES['list_item_height']
        self.max_scroll = max(0, total_height - visible_height)
        self.scroll_target = min(self.scroll_target, self.max_scroll)
        print(f"[POKEDEX_LIST] max_scroll: {self.max_scroll}")

        if self.filtered_items and not self.selected_id:
            self.selected_id = self.filtered_items[0].pokemon_id
            print(f"[POKEDEX_LIST] Selecionado automaticamente: {self.selected_id}")

    def _apply_filters(self, search_text, filter_type):
        filtered = self.items

        if filter_type == "caught":
            filtered = [item for item in filtered if item.is_caught]
            print(f"[POKEDEX_LIST] Filtro CAPTURADOS: {len(filtered)} itens")
        elif filter_type == "seen":
            filtered = [item for item in filtered if item.is_seen]
            print(f"[POKEDEX_LIST] Filtro VISTOS: {len(filtered)} itens")
        elif filter_type == "unseen":
            filtered = [item for item in filtered if not item.is_seen and not item.is_caught]
            print(f"[POKEDEX_LIST] Filtro NÃO VISTOS: {len(filtered)} itens")

        if search_text:
            filtered = [
                item for item in filtered
                if search_text in item.name.lower() or
                   str(item.pokemon_id) == search_text
            ]
            print(f"[POKEDEX_LIST] Após busca '{search_text}': {len(filtered)} itens")

        return filtered

    def _update_item_positions(self):
        """Atualiza as posições de todos os itens da lista"""
        item_height = SIZES['list_item_height']
        y_offset = self.rect.y + 4 - self.scroll_y

        for item in self.filtered_items:
            item.update_position(
                self.rect.x + 4,
                y_offset,
                self.rect.width - 12
            )
            item.is_selected = (item.pokemon_id == self.selected_id)
            y_offset += item_height

    def handle_event(self, event):
        # ===== MOUSEWHEEL =====
        if event.type == pygame.MOUSEWHEEL:
            if self.rect.collidepoint(pygame.mouse.get_pos()):
                print(f"[POKEDEX_LIST] Mousewheel: {event.y}")
                self.scroll_target += event.y * -25
                self.scroll_target = max(0, min(self.max_scroll, self.scroll_target))
                # Atualiza posições após scroll
                self._update_item_positions()
                return None

        # ===== MOUSE MOTION =====
        if event.type == pygame.MOUSEMOTION:
            # ATUALIZA POSIÇÕES ANTES DE VERIFICAR HOVER
            self._update_item_positions()

            mouse_pos = event.pos
            for item in self.filtered_items:
                item.is_hovered = item.rect.collidepoint(mouse_pos)

            if self.dragging_scroll:
                dy = event.pos[1] - self.last_mouse_y
                if self.max_scroll > 0:
                    scroll_ratio = self.max_scroll / (self.rect.height - 20)
                    self.scroll_target += dy * scroll_ratio
                    self.scroll_target = max(0, min(self.max_scroll, self.scroll_target))
                    # Atualiza posições após drag
                    self._update_item_positions()
                self.last_mouse_y = event.pos[1]

        # ===== MOUSE BUTTON DOWN =====
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mouse_pos = event.pos
            print(f"[POKEDEX_LIST] Clique detectado em: {mouse_pos}")

            # Verifica se o clique está dentro da área da lista
            if not self.rect.collidepoint(mouse_pos):
                print(f"[POKEDEX_LIST] Clique FORA da lista")
                return None

            print(f"[POKEDEX_LIST] Clique DENTRO da lista")

            # ===== ANTES DE VERIFICAR CLIQUE, ATUALIZA POSIÇÕES DOS ITENS =====
            self._update_item_positions()

            # Verifica clique na barra de scroll
            if self.max_scroll > 0:
                scroll_bar_rect = self._get_scroll_bar_rect()
                if scroll_bar_rect and scroll_bar_rect.collidepoint(mouse_pos):
                    print(f"[POKEDEX_LIST] Clique na barra de scroll")
                    self.dragging_scroll = True
                    self.last_mouse_y = mouse_pos[1]
                    return None

            # ===== VERIFICA CLIQUE NOS ITENS =====
            print(f"[POKEDEX_LIST] Verificando {len(self.filtered_items)} itens...")

            # Mostra os primeiros 5 itens para debug
            for i in range(min(5, len(self.filtered_items))):
                item = self.filtered_items[i]
                print(f"[POKEDEX_LIST] Item {i}: ID={item.pokemon_id}, rect={item.rect}")

            # PERCORRE TODOS OS ITENS DA LISTA
            for i, item in enumerate(self.filtered_items):
                if item.rect.collidepoint(mouse_pos):
                    print(f"[POKEDEX_LIST] COLLIDE DETECTADO no item {i}: ID={item.pokemon_id}")
                    print(f"[POKEDEX_LIST] Item rect: {item.rect}")
                    print(f"[POKEDEX_LIST] Mouse pos: {mouse_pos}")
                    print(f"[POKEDEX_LIST] is_seen: {item.is_seen}, is_caught: {item.is_caught}")

                    # Só permite clique em Pokemons vistos ou capturados
                    if not item.is_seen and not item.is_caught:
                        print(f"[POKEDEX_LIST] Pokemon {item.pokemon_id} nao visto - clique bloqueado")
                        return None

                    print(f"[POKEDEX_LIST] CLIQUE VALIDADO: {item.pokemon_id} - {item.name}")

                    # ATUALIZA A SELEÇÃO
                    self.selected_id = item.pokemon_id

                    # CHAMA O CALLBACK
                    if self.on_item_click:
                        print(f"[POKEDEX_LIST] Chamando on_item_click para {item.pokemon_id}")
                        self.on_item_click(item.pokemon_id)
                    else:
                        print(f"[POKEDEX_LIST] on_item_click é None!")

                    # RETORNA O ID
                    return item.pokemon_id

            print(f"[POKEDEX_LIST] Nenhum item colidiu com o clique")

        # ===== MOUSE BUTTON UP =====
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self.dragging_scroll:
                print(f"[POKEDEX_LIST] Drag finalizado")
            self.dragging_scroll = False

        return None

    def _get_scroll_bar_rect(self):
        if self.max_scroll <= 0:
            return None

        bar_x = self.rect.right - 6
        bar_y = self.rect.y + 4
        bar_height = self.rect.height - 8

        visible_ratio = self.rect.height / (self.rect.height + self.max_scroll)
        scroll_height = max(30, bar_height * visible_ratio)

        scroll_progress = self.scroll_y / self.max_scroll if self.max_scroll > 0 else 0
        scroll_pos = bar_y + scroll_progress * (bar_height - scroll_height)

        return pygame.Rect(bar_x, scroll_pos, 4, scroll_height)

    def update(self, dt):
        if abs(self.scroll_y - self.scroll_target) > 0.5:
            self.scroll_y += (self.scroll_target - self.scroll_y) * min(1, dt * 12)
        else:
            self.scroll_y = self.scroll_target

        # Atualiza posições dos itens
        self._update_item_positions()

    def render(self, screen, pokedex, font_medium, font_small):
        # Fundo da lista
        pygame.draw.rect(screen, COLORS['bg_secondary'], self.rect, border_radius=8)
        pygame.draw.rect(screen, COLORS['border'], self.rect, 2, border_radius=8)

        old_clip = screen.get_clip()
        clip_rect = pygame.Rect(
            self.rect.x + 2,
            self.rect.y + 2,
            self.rect.width - 12,
            self.rect.height - 4
        )
        screen.set_clip(clip_rect)

        for item in self.filtered_items:
            if item.rect.bottom > clip_rect.top and item.rect.top < clip_rect.bottom:
                item.render(screen, pokedex, font_medium, font_small)

        screen.set_clip(old_clip)

        if self.max_scroll > 0:
            self._render_scroll_bar(screen)

        if not self.filtered_items:
            no_result_font = pygame.font.Font(None, 20)
            no_text = no_result_font.render("Nenhum Pokemon encontrado", True, COLORS['text_secondary'])
            text_rect = no_text.get_rect(center=self.rect.center)
            screen.blit(no_text, text_rect)

    def _render_scroll_bar(self, screen):
        if self.max_scroll <= 0:
            return

        bar_rect = self._get_scroll_bar_rect()
        if bar_rect:
            pygame.draw.rect(screen, (40, 40, 45),
                             (self.rect.right - 5, self.rect.y + 4, 3, self.rect.height - 8))

            if self.dragging_scroll:
                color = COLORS['text_accent']
            else:
                color = COLORS['border_light']

            pygame.draw.rect(screen, color, bar_rect, border_radius=2)

    def get_selected_item(self):
        for item in self.filtered_items:
            if item.pokemon_id == self.selected_id:
                return item
        return self.filtered_items[0] if self.filtered_items else None

    def get_selected_id(self):
        return self.selected_id

    def get_count(self):
        return len(self.filtered_items)