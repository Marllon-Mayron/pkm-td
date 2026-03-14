# src/scenes/team_select_scene.py
import pygame
import math
import random
from src.scenes.base_scene import BaseScene
from src.entities.pokemon import Pokemon
from src.data.pokedex import Pokedex


class TeamSlot:
    def __init__(self, x, y, width, height, slot_index):
        self.rect = pygame.Rect(x, y, width, height)
        self.slot_index = slot_index
        self.pokemon = None
        self.is_hovered = False
        self.is_selected = False

    def set_pokemon(self, pokemon):
        self.pokemon = pokemon

    def handle_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            self.is_hovered = self.rect.collidepoint(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.is_hovered:
                return self.slot_index
        return None

    def render(self, screen, font, pokedex):
        # Cor base
        if self.is_selected:
            color = (100, 150, 200)
            border_color = (150, 200, 250)
        elif self.is_hovered:
            color = (70, 70, 90)
            border_color = (120, 120, 140)
        else:
            color = (45, 45, 55)
            border_color = (80, 80, 100)

        # Sombra
        shadow_rect = self.rect.copy()
        shadow_rect.x += 3
        shadow_rect.y += 3
        pygame.draw.rect(screen, (20, 20, 25), shadow_rect, border_radius=8)

        # Slot principal
        pygame.draw.rect(screen, color, self.rect, border_radius=8)
        pygame.draw.rect(screen, border_color, self.rect, 2, border_radius=8)

        # Número do slot
        num_font = pygame.font.Font(None, 18)
        num_text = num_font.render(f"#{self.slot_index + 1}", True, (150, 150, 160))
        screen.blit(num_text, (self.rect.x + 5, self.rect.y + 5))

        # Se tem Pokémon
        if self.pokemon:
            # SPRITE - carrega do cache da Pokedex
            sprite = pokedex.get_sprite(self.pokemon.id, "inmap", self.pokemon.is_shiny)
            if sprite:
                # Redimensiona para caber no slot
                sprite_size = 48
                sprite_scaled = pygame.transform.scale(sprite, (sprite_size, sprite_size))
                screen.blit(sprite_scaled, (self.rect.x + 8, self.rect.y + 25))

            # Nome (encurtado)
            name_text = self.pokemon.name[:8]
            if len(self.pokemon.name) > 8:
                name_text += "."

            name_surf = font.render(name_text, True, (255, 255, 255))
            screen.blit(name_surf, (self.rect.x + 60, self.rect.y + 30))

            # Nível
            lvl_text = font.render(f"Lv.{self.pokemon.level}", True, (255, 255, 100))
            screen.blit(lvl_text, (self.rect.x + 60, self.rect.y + 50))

            # Mini barra de HP
            hp_percent = self.pokemon.current_hp / self.pokemon.max_hp
            bar_width = 60
            bar_height = 4
            bar_x = self.rect.x + 60
            bar_y = self.rect.y + 70

            # Fundo
            pygame.draw.rect(screen, (40, 40, 40), (bar_x, bar_y, bar_width, bar_height))

            # Barra
            if hp_percent > 0.5:
                hp_color = (0, 200, 0)
            elif hp_percent > 0.25:
                hp_color = (255, 255, 0)
            else:
                hp_color = (255, 0, 0)

            pygame.draw.rect(screen, hp_color,
                             (bar_x, bar_y, int(bar_width * hp_percent), bar_height))

            # Efeito shiny
            if self.pokemon.is_shiny:
                pygame.draw.rect(screen, (255, 255, 100), self.rect, 3, border_radius=8)

        else:
            # Slot vazio
            empty_text = pygame.font.Font(None, 40).render("+", True, (100, 100, 110))
            empty_rect = empty_text.get_rect(center=(self.rect.centerx, self.rect.centery))
            screen.blit(empty_text, empty_rect)


class PokemonGridItem:
    def __init__(self, pokemon, x, y, width, height):
        self.pokemon = pokemon
        self.rect = pygame.Rect(x, y, width, height)
        self.is_hovered = False

    def handle_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            self.is_hovered = self.rect.collidepoint(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.is_hovered and not self.pokemon.is_in_team:
                return self.pokemon
        return None

    def render(self, screen, font, pokedex):
        # Cor base
        if self.pokemon.is_in_team:
            color = (40, 60, 40)  # Verde escuro se já está no time
            border_color = (70, 120, 70)
        elif self.is_hovered:
            color = (60, 60, 80)
            border_color = (100, 100, 140)
        else:
            color = (35, 35, 45)
            border_color = (60, 60, 80)

        # Sombra
        shadow_rect = self.rect.copy()
        shadow_rect.x += 2
        shadow_rect.y += 2
        pygame.draw.rect(screen, (15, 15, 20), shadow_rect, border_radius=6)

        # Card
        pygame.draw.rect(screen, color, self.rect, border_radius=6)
        pygame.draw.rect(screen, border_color, self.rect, 1, border_radius=6)

        # SPRITE - carrega do cache da Pokedex
        sprite = pokedex.get_sprite(self.pokemon.id, "inmap", self.pokemon.is_shiny)
        if sprite:
            # Redimensiona para caber no card
            sprite_scaled = pygame.transform.scale(sprite, (48, 48))
            screen.blit(sprite_scaled, (self.rect.x + 5, self.rect.y + 5))

        # Nome
        name_text = font.render(self.pokemon.name, True, (255, 255, 255))
        screen.blit(name_text, (self.rect.x + 60, self.rect.y + 10))

        # Nível
        lvl_text = font.render(f"Lv.{self.pokemon.level}", True, (255, 255, 100))
        screen.blit(lvl_text, (self.rect.x + 60, self.rect.y + 30))

        # REMOVIDO: Tipos não aparecem mais aqui

        # Indicador shiny (apenas um ícone pequeno)
        if self.pokemon.is_shiny:
            star_font = pygame.font.Font(None, 20)
            star = star_font.render("⭐", True, (255, 255, 100))
            screen.blit(star, (self.rect.right - 25, self.rect.y + 5))

        # Overlay se já está no time
        if self.pokemon.is_in_team:
            overlay = pygame.Surface((self.rect.width, self.rect.height), pygame.SRCALPHA)
            overlay.fill((0, 50, 0, 100))
            screen.blit(overlay, self.rect)

            team_text = font.render("No time", True, (150, 255, 150))
            text_rect = team_text.get_rect(center=(self.rect.centerx, self.rect.centery + 20))
            screen.blit(team_text, text_rect)


class PokemonModal:
    def __init__(self, game, pokemon):
        self.game = game
        self.pokemon = pokemon
        self.pokedex = Pokedex()
        self.visible = True

        # Dimensões do modal (70% da tela)
        self.width = int(game.screen_manager.window_width * 0.7)
        self.height = int(game.screen_manager.window_height * 0.7)
        self.x = (game.screen_manager.window_width - self.width) // 2
        self.y = (game.screen_manager.window_height - self.height) // 2

        self.rect = pygame.Rect(self.x, self.y, self.width, self.height)

        # Botão fechar
        self.close_button = pygame.Rect(
            self.x + self.width - 40,
            self.y + 10,
            30, 30
        )

        # Botão adicionar/remover
        button_width = 150
        button_height = 40
        self.action_button = pygame.Rect(
            self.x + (self.width - button_width) // 2,
            self.y + self.height - 70,
            button_width,
            button_height
        )

    def handle_event(self, event):
        if not self.visible:
            return None

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            # Botão fechar
            if self.close_button.collidepoint(event.pos):
                self.visible = False
                return "close"

            # Botão de ação
            if self.action_button.collidepoint(event.pos):
                return "action"

            # Clique fora do modal fecha
            if not self.rect.collidepoint(event.pos):
                self.visible = False
                return "close"

        return None

    def render(self, screen):
        if not self.visible:
            return

        # Overlay escuro atrás
        overlay = pygame.Surface((self.game.screen_manager.window_width,
                                  self.game.screen_manager.window_height))
        overlay.set_alpha(180)
        overlay.fill((0, 0, 0))
        screen.blit(overlay, (0, 0))

        # Modal
        pygame.draw.rect(screen, (30, 30, 40), self.rect, border_radius=15)
        pygame.draw.rect(screen, (100, 100, 150), self.rect, 3, border_radius=15)

        # Botão fechar
        pygame.draw.rect(screen, (60, 60, 70), self.close_button, border_radius=5)
        pygame.draw.rect(screen, (150, 150, 150), self.close_button, 2, border_radius=5)
        close_font = pygame.font.Font(None, 24)
        close_text = close_font.render("X", True, (255, 255, 255))
        close_rect = close_text.get_rect(center=self.close_button.center)
        screen.blit(close_text, close_rect)

        # Sprite grande (carregado da Pokedex)
        sprite = self.pokedex.get_sprite(self.pokemon.id, "front", self.pokemon.is_shiny)
        if sprite:
            sprite_big = pygame.transform.scale(sprite, (120, 120))
            screen.blit(sprite_big, (self.x + 50, self.y + 50))

        # Informações
        info_font = pygame.font.Font(None, 28)
        info_font_small = pygame.font.Font(None, 22)

        # Nome e nível
        name_text = info_font.render(f"{self.pokemon.name}  Lv.{self.pokemon.level}",
                                      True, (255, 255, 255))
        screen.blit(name_text, (self.x + 200, self.y + 60))

        # Natureza
        nature_text = info_font_small.render(f"Natureza: {self.pokemon.nature}",
                                              True, (200, 200, 150))
        screen.blit(nature_text, (self.x + 200, self.y + 100))

        # Tipos - AGORA APARECEM AQUI NO MODAL
        type_x = self.x + 200
        type_y = self.y + 130
        for i, type_name in enumerate(self.pokemon.types):
            type_color = self.pokedex.get_type_color(type_name)
            pygame.draw.rect(screen, type_color, (type_x + (i * 80), type_y, 70, 25))
            pygame.draw.rect(screen, (200, 200, 200), (type_x + (i * 80), type_y, 70, 25), 1)

            type_text = info_font_small.render(type_name.upper(), True, (255, 255, 255))
            type_rect = type_text.get_rect(center=(type_x + (i * 80) + 35, type_y + 12))
            screen.blit(type_text, type_rect)

        # Stats
        stats_y = self.y + 180
        stats = [
            ("HP", self.pokemon.current_hp, self.pokemon.max_hp),
            ("Ataque", self.pokemon.attack, None),
            ("Defesa", self.pokemon.defense, None),
            ("Sp.Atk", self.pokemon.sp_attack, None),
            ("Sp.Def", self.pokemon.sp_defense, None),
            ("Vel.", self.pokemon.speed, None)
        ]

        for i, (stat_name, stat_value, stat_max) in enumerate(stats):
            col = i % 2
            row = i // 2

            stat_x = self.x + 50 + (col * 200)
            stat_y_pos = stats_y + (row * 40)

            stat_label = info_font_small.render(f"{stat_name}:", True, (180, 180, 180))
            screen.blit(stat_label, (stat_x, stat_y_pos))

            if stat_max:
                stat_value_text = info_font_small.render(f"{stat_value}/{stat_max}",
                                                          True, (255, 255, 255))
            else:
                stat_value_text = info_font_small.render(str(stat_value),
                                                          True, (255, 255, 255))
            screen.blit(stat_value_text, (stat_x + 80, stat_y_pos))

        # IVs
        iv_y = stats_y + 100
        iv_text = info_font_small.render("IVs:", True, (180, 180, 180))
        screen.blit(iv_text, (self.x + 50, iv_y))

        iv_values = [
            f"HP:{self.pokemon.ivs['hp']}",
            f"ATK:{self.pokemon.ivs['attack']}",
            f"DEF:{self.pokemon.ivs['defense']}",
            f"SPA:{self.pokemon.ivs['special_attack']}",
            f"SPD:{self.pokemon.ivs['special_defense']}",
            f"VEL:{self.pokemon.ivs['speed']}"
        ]

        for i, iv in enumerate(iv_values):
            col = i % 3
            row = i // 3
            iv_x = self.x + 100 + (col * 100)
            iv_y_pos = iv_y + 25 + (row * 25)

            iv_surf = info_font_small.render(iv, True, (200, 255, 200))
            screen.blit(iv_surf, (iv_x, iv_y_pos))

        # Botão de ação
        if self.pokemon.is_in_team:
            button_color = (150, 80, 80)
            button_text = "REMOVER DO TIME"
        else:
            if len(self.game.player.team) < 6:
                button_color = (80, 150, 80)
                button_text = "ADICIONAR AO TIME"
            else:
                button_color = (80, 80, 80)
                button_text = "TIME CHEIO"

        pygame.draw.rect(screen, button_color, self.action_button, border_radius=8)
        pygame.draw.rect(screen, (200, 200, 200), self.action_button, 2, border_radius=8)

        action_font = pygame.font.Font(None, 24)
        action_surf = action_font.render(button_text, True, (255, 255, 255))
        action_rect = action_surf.get_rect(center=self.action_button.center)
        screen.blit(action_surf, action_rect)

        # Shiny indicator
        if self.pokemon.is_shiny:
            shiny_text = info_font.render("✨ SHINY ✨", True, (255, 255, 100))
            shiny_rect = shiny_text.get_rect(center=(self.x + self.width - 100, self.y + 60))
            screen.blit(shiny_text, shiny_rect)


class TeamSelectScene(BaseScene):
    def __init__(self, game):
        super().__init__(game)

        self.pokedex = Pokedex()
        self.player = game.player

        # Layout
        self.team_slots = []
        self.grid_items = []
        self.modal = None

        # Paginação
        self.current_page = 0
        self.items_per_page = 18  # 6 colunas x 3 linhas
        self.total_pages = 1

        # Fontes
        self.title_font = pygame.font.Font(None, 48)
        self.slot_font = pygame.font.Font(None, 20)
        self.grid_font = pygame.font.Font(None, 18)
        self.page_font = pygame.font.Font(None, 24)

        # Botões
        self.back_button = None
        self.prev_page_button = None
        self.next_page_button = None
        self.start_button = None

        # Estado
        self.layout_initialized = False
        self.last_window_size = (game.screen_manager.window_width,
                                  game.screen_manager.window_height)

        # Inicializa lista de Pokémon
        self.available_pokemon = []
        self._populate_available_pokemon()

    def _populate_available_pokemon(self):
        """Popula lista de Pokémons disponíveis"""
        # Pokémons iniciais (todos os 151 para teste)
        # Em produção, isso viria do PC Box do jogador
        all_ids = list(range(1, 152))  # 1 a 151

        for poke_id in all_ids[:30]:  # Limite para teste
            # Verifica se já está no time
            already_in_team = any(p.id == poke_id for p in self.player.team)

            pokemon = Pokemon(
                x=0, y=0,
                pokemon_id=poke_id,
                level=random.randint(5, 20),
                is_wild=False,
                shiny=random.random() < 0.05  # 5% shiny
            )

            if already_in_team:
                pokemon.is_in_team = True

            self.available_pokemon.append(pokemon)

        # Adiciona da box do jogador
        for pokemon in self.player.pc_box:
            self.available_pokemon.append(pokemon)

        # Calcula total de páginas
        self.total_pages = max(1, math.ceil(len(self.available_pokemon) / self.items_per_page))

    def _check_resize(self):
        """Verifica se a tela foi redimensionada"""
        current_size = (self.game.screen_manager.window_width,
                        self.game.screen_manager.window_height)
        if current_size != self.last_window_size:
            self.last_window_size = current_size
            self.layout_initialized = False
            return True
        return False

    def _create_layout(self):
        """Cria layout responsivo"""
        screen_width = self.game.screen_manager.window_width
        screen_height = self.game.screen_manager.window_height

        # Margens
        margin = 30
        top_margin = 80

        # Slots do time (6 horizontais no topo)
        slot_width = min(160, (screen_width - 2 * margin) // 6 - 10)
        slot_height = 110
        slot_spacing = 10

        slots_total_width = 6 * slot_width + 5 * slot_spacing
        slots_start_x = (screen_width - slots_total_width) // 2

        self.team_slots = []
        for i in range(6):
            slot_x = slots_start_x + i * (slot_width + slot_spacing)
            slot_y = top_margin

            slot = TeamSlot(slot_x, slot_y, slot_width, slot_height, i)
            if i < len(self.player.team):
                slot.set_pokemon(self.player.team[i])

            self.team_slots.append(slot)

        # Área do grid (abaixo dos slots)
        grid_y = top_margin + slot_height + 40
        grid_height = screen_height - grid_y - 100

        # Configurações do grid
        self.grid_cols = 6
        card_width = min(140, (screen_width - 2 * margin - (self.grid_cols - 1) * 10) // self.grid_cols)
        card_height = 90
        card_spacing = 10

        grid_width = self.grid_cols * card_width + (self.grid_cols - 1) * card_spacing
        grid_start_x = (screen_width - grid_width) // 2

        # Calcula linhas por página baseado na altura disponível
        self.rows_per_page = max(1, grid_height // (card_height + card_spacing))
        self.items_per_page = self.grid_cols * self.rows_per_page

        # Atualiza total de páginas
        self.total_pages = max(1, math.ceil(len(self.available_pokemon) / self.items_per_page))
        self.current_page = min(self.current_page, self.total_pages - 1)

        # Cria grid items
        self.grid_items = []
        start_idx = self.current_page * self.items_per_page
        end_idx = min(start_idx + self.items_per_page, len(self.available_pokemon))

        for i in range(start_idx, end_idx):
            row = (i - start_idx) // self.grid_cols
            col = (i - start_idx) % self.grid_cols

            card_x = grid_start_x + col * (card_width + card_spacing)
            card_y = grid_y + row * (card_height + card_spacing)

            item = PokemonGridItem(
                self.available_pokemon[i],
                card_x, card_y,
                card_width, card_height
            )
            self.grid_items.append(item)

        # Botões de navegação
        button_width = 100
        button_height = 40
        button_y = screen_height - 60

        # Botão voltar
        self.back_button = pygame.Rect(
            margin,
            button_y,
            button_width,
            button_height
        )

        # Botão iniciar
        self.start_button = pygame.Rect(
            screen_width - button_width - margin,
            button_y,
            button_width,
            button_height
        )

        # Botões de página
        page_button_width = 80
        self.prev_page_button = pygame.Rect(
            screen_width // 2 - page_button_width - 10,
            button_y,
            page_button_width,
            button_height
        )

        self.next_page_button = pygame.Rect(
            screen_width // 2 + 10,
            button_y,
            page_button_width,
            button_height
        )

        self.layout_initialized = True

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                if self.modal:
                    self.modal.visible = False
                    self.modal = None
                else:
                    self.game.go_to_phase_select()

        elif event.type == pygame.VIDEORESIZE:
            self.layout_initialized = False
            if self.modal:
                # Recalcula posição do modal
                self.modal.width = int(self.game.screen_manager.window_width * 0.7)
                self.modal.height = int(self.game.screen_manager.window_height * 0.7)
                self.modal.x = (self.game.screen_manager.window_width - self.modal.width) // 2
                self.modal.y = (self.game.screen_manager.window_height - self.modal.height) // 2
                self.modal.rect = pygame.Rect(self.modal.x, self.modal.y,
                                               self.modal.width, self.modal.height)
                self.modal.close_button = pygame.Rect(
                    self.modal.x + self.modal.width - 40,
                    self.modal.y + 10, 30, 30
                )
                self.modal.action_button = pygame.Rect(
                    self.modal.x + (self.modal.width - 150) // 2,
                    self.modal.y + self.modal.height - 70,
                    150, 40
                )

        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:  # Left click
                # Se modal está aberto, passa evento pra ele
                if self.modal and self.modal.visible:
                    result = self.modal.handle_event(event)

                    if result == "action":
                        # Ação do botão
                        if self.modal.pokemon.is_in_team:
                            # Remover do time
                            for i, p in enumerate(self.player.team):
                                if p == self.modal.pokemon:
                                    self.player.remove_from_team(i)
                                    self.modal.pokemon.is_in_team = False
                                    break
                        else:
                            # Adicionar ao time
                            if len(self.player.team) < 6:
                                success, _ = self.player.add_to_team(self.modal.pokemon)
                                if success:
                                    self.modal.pokemon.is_in_team = True

                        # Atualiza slots
                        for i, slot in enumerate(self.team_slots):
                            if i < len(self.player.team):
                                slot.set_pokemon(self.player.team[i])
                            else:
                                slot.set_pokemon(None)

                        # Recria layout para atualizar grid
                        self._create_layout()

                    elif result == "close":
                        self.modal = None

                    return

                # Botões de navegação
                if self.back_button and self.back_button.collidepoint(event.pos):
                    self.game.go_to_phase_select()
                    return

                if self.start_button and self.start_button.collidepoint(event.pos):
                    if len(self.player.team) > 0:
                        print("Iniciando batalha com time:", [p.name for p in self.player.team])
                        # Aqui vai para a cena do jogo
                    return

                if self.prev_page_button and self.prev_page_button.collidepoint(event.pos):
                    if self.current_page > 0:
                        self.current_page -= 1
                        self._create_layout()
                    return

                if self.next_page_button and self.next_page_button.collidepoint(event.pos):
                    if self.current_page < self.total_pages - 1:
                        self.current_page += 1
                        self._create_layout()
                    return

                # Slots do time
                for slot in self.team_slots:
                    result = slot.handle_event(event)
                    if result is not None:
                        # Seleciona slot
                        for s in self.team_slots:
                            s.is_selected = (s.slot_index == result)

                        # Abre modal do Pokémon no slot se existir
                        if slot.pokemon:
                            self.modal = PokemonModal(self.game, slot.pokemon)
                        return

                # Grid items
                for item in self.grid_items:
                    result = item.handle_event(event)
                    if result:
                        self.modal = PokemonModal(self.game, result)
                        return

    def fixed_update(self, dt):
        if not self.layout_initialized or self._check_resize():
            self._create_layout()

    def render(self, screen):
        # Fundo
        self._draw_gradient_background(screen)

        if not self.layout_initialized:
            return

        # Título
        title = self.title_font.render("SELECIONAR TIME", True, (220, 220, 230))
        title_x = (self.game.screen_manager.window_width - title.get_width()) // 2
        screen.blit(title, (title_x, 20))

        # Linha separadora
        pygame.draw.line(screen, (60, 60, 70),
                         (50, 70), (self.game.screen_manager.window_width - 50, 70), 2)

        # Slots do time
        for slot in self.team_slots:
            slot.render(screen, self.slot_font, self.pokedex)

        # Label do grid
        grid_label = self.slot_font.render("POKÉMONS DISPONÍVEIS", True, (180, 180, 190))
        label_x = (self.game.screen_manager.window_width - grid_label.get_width()) // 2
        label_y = self.team_slots[0].rect.bottom + 20
        screen.blit(grid_label, (label_x, label_y))

        # Grid items
        for item in self.grid_items:
            item.render(screen, self.grid_font, self.pokedex)

        # Informação de página
        if self.total_pages > 1:
            page_text = self.page_font.render(f"Página {self.current_page + 1} de {self.total_pages}",
                                               True, (150, 150, 160))
            page_rect = page_text.get_rect(center=(self.game.screen_manager.window_width // 2,
                                                    self.prev_page_button.centery))
            screen.blit(page_text, page_rect)

        # Botões
        # Voltar
        pygame.draw.rect(screen, (50, 50, 55), self.back_button, border_radius=8)
        pygame.draw.rect(screen, (90, 90, 100), self.back_button, 2, border_radius=8)
        back_text = self.slot_font.render("VOLTAR", True, (200, 200, 210))
        back_rect = back_text.get_rect(center=self.back_button.center)
        screen.blit(back_text, back_rect)

        # Iniciar
        if len(self.player.team) > 0:
            button_color = (70, 120, 70)
        else:
            button_color = (50, 50, 55)

        pygame.draw.rect(screen, button_color, self.start_button, border_radius=8)
        pygame.draw.rect(screen, (150, 150, 150), self.start_button, 2, border_radius=8)
        start_text = self.slot_font.render("INICIAR", True, (255, 255, 255))
        start_rect = start_text.get_rect(center=self.start_button.center)
        screen.blit(start_text, start_rect)

        # Botões de página
        if self.total_pages > 1:
            # Anterior
            if self.current_page > 0:
                prev_color = (60, 60, 70)
            else:
                prev_color = (40, 40, 45)

            pygame.draw.rect(screen, prev_color, self.prev_page_button, border_radius=8)
            pygame.draw.rect(screen, (100, 100, 110), self.prev_page_button, 2, border_radius=8)
            prev_text = self.slot_font.render("ANTERIOR", True, (200, 200, 200))
            prev_rect = prev_text.get_rect(center=self.prev_page_button.center)
            screen.blit(prev_text, prev_rect)

            # Próxima
            if self.current_page < self.total_pages - 1:
                next_color = (60, 60, 70)
            else:
                next_color = (40, 40, 45)

            pygame.draw.rect(screen, next_color, self.next_page_button, border_radius=8)
            pygame.draw.rect(screen, (100, 100, 110), self.next_page_button, 2, border_radius=8)
            next_text = self.slot_font.render("PRÓXIMA", True, (200, 200, 200))
            next_rect = next_text.get_rect(center=self.next_page_button.center)
            screen.blit(next_text, next_rect)

        # Status do time
        team_status = f"Time: {len(self.player.team)}/6"
        status_color = (255, 255, 255) if len(self.player.team) > 0 else (150, 150, 150)
        status_text = self.slot_font.render(team_status, True, status_color)
        screen.blit(status_text, (20, self.game.screen_manager.window_height - 30))

        # Modal
        if self.modal and self.modal.visible:
            self.modal.render(screen)

    def _draw_gradient_background(self, screen):
        """Desenha fundo com gradiente"""
        for i in range(self.game.screen_manager.window_height):
            value = int(10 + (i / self.game.screen_manager.window_height) * 20)
            color = (value, value, value + 3)
            pygame.draw.line(screen, color, (0, i),
                             (self.game.screen_manager.window_width, i))