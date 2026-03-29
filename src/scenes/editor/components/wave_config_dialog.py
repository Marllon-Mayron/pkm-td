# src/scenes/editor/components/wave_config_dialog.py

import pygame
from src.editor.wave_config import WaveEnemy


class WaveConfigDialog:
    """Diálogo para configurar waves de inimigos"""

    # Cores padronizadas
    COLORS = {
        'bg': (40, 40, 50),
        'bg_light': (50, 50, 60),
        'bg_dark': (30, 30, 40),
        'border': (255, 215, 0),
        'border_light': (80, 80, 90),
        'text': (255, 255, 255),
        'text_dim': (200, 200, 200),
        'text_dark': (150, 150, 150),
        'accent': (80, 100, 120),
        'accent_hover': (100, 120, 140),
        'input_bg': (50, 50, 60),
        'input_border': (80, 80, 90),
        'input_active': (100, 150, 255),
        'success': (0, 120, 0),
        'danger': (120, 0, 0),
        'warning': (120, 120, 0),
    }

    def __init__(self, x, y, width, height, wave_manager, path_manager, pokedex):
        self.rect = pygame.Rect(x, y, width, height)
        self.visible = True
        self.wave_manager = wave_manager
        self.path_manager = path_manager
        self.pokedex = pokedex

        # Estado da UI
        self.selected_wave_index = wave_manager.selected_wave
        self.selected_tab = "waves"
        self.dragging = False
        self.drag_offset_x = 0
        self.drag_offset_y = 0
        self.hovered_button = None

        # Fontes
        self.font_title = pygame.font.Font(None, 24)
        self.font = pygame.font.Font(None, 20)
        self.font_small = pygame.font.Font(None, 16)

        # Campos de entrada ativos
        self.active_input = None
        self.input_texts = {}
        self.input_errors = {}

        # Seletor de Pokémon
        self.showing_pokemon_selector = False
        self.pokemon_selector_enemy_index = 0
        self.pokemon_selector_scroll = 0
        self.pokemon_search = ""

        # Scroll
        self.waves_scroll = 0
        self.enemies_scroll = 0

        # Items por página
        self.waves_per_page = 6
        self.wave_item_height = 35
        self.enemies_per_page = 4
        self.enemy_item_height = 70

        # Carrega lista completa de Pokémon
        self.available_pokemon_ids = self.pokedex.get_all_ids()

        # Cache de sprites
        self.sprite_cache = {}

        # Inicializa UI
        self._init_ui()

    def _init_ui(self):
        """Inicializa todos os elementos da UI com posições centralizadas"""
        x, y, w, h = self.rect

        # Margens internas
        margin = 20
        content_width = w - (margin * 2)
        content_x = x + margin
        content_y = y + 45  # Espaço para título e abas

        # Abas - centralizadas
        tab_width = 100
        tab_spacing = 10
        tabs_total_width = (tab_width * 3) + (tab_spacing * 2)
        tabs_start_x = x + (w - tabs_total_width) // 2

        self.tab_buttons = []
        for i in range(3):
            self.tab_buttons.append(pygame.Rect(
                tabs_start_x + i * (tab_width + tab_spacing),
                y + 45,
                tab_width,
                25
            ))

        # Botões de ação (Salvar/Cancelar) - centralizados
        button_width = 80
        button_spacing = 15
        buttons_total_width = (button_width * 2) + button_spacing
        buttons_start_x = x + (w - buttons_total_width) // 2

        self.save_button = pygame.Rect(buttons_start_x, y + h - 40, button_width, 30)
        self.cancel_button = pygame.Rect(buttons_start_x + button_width + button_spacing, y + h - 40, button_width, 30)

        # Elementos da aba Waves - CENTRALIZADOS
        # Calcula largura da lista de waves para centralizar
        waves_list_width = 300
        waves_list_x = x + (w - waves_list_width) // 2

        self.add_wave_button = pygame.Rect(waves_list_x, content_y + 30, 90, 25)
        self.remove_wave_button = pygame.Rect(waves_list_x + 100, content_y + 30, 90, 25)

        self.waves_list_area = pygame.Rect(
            waves_list_x,
            content_y + 65,
            waves_list_width,
            self.waves_per_page * self.wave_item_height + 5
        )

        # Elementos da aba Composition
        self.add_enemy_button = pygame.Rect(content_x, y + h - 90, 140, 25)
        self.equalize_button = pygame.Rect(content_x + 150, y + h - 90, 120, 25)

        self.enemies_list_area = pygame.Rect(
            content_x,
            content_y + 35,
            content_width,
            self.enemies_per_page * self.enemy_item_height + 5
        )

        # Elementos da aba Settings - Organizados em grid padronizado
        self._init_settings_ui(content_x, content_y, content_width)

    def _init_settings_ui(self, content_x, content_y, content_width):
        """Inicializa elementos da aba Settings em grid padronizado"""
        x, y, w = content_x, content_y, content_width

        # Configuração do grid padronizado
        label_width = 100  # Largura fixa para labels
        input_width = 80  # Largura fixa para inputs
        spacing = 20  # Espaçamento entre colunas
        row_height = 35  # Altura fixa por linha

        # Colunas
        col1_x = x
        col2_x = x + (w // 2) + spacing

        # Altura inicial
        start_y = y + 35

        # LINHA 0: Nome da Wave (ocupa largura total)
        name_label_rect = pygame.Rect(col1_x, start_y, label_width, 25)
        self.name_label = name_label_rect
        self.name_input = pygame.Rect(col1_x + label_width + 5, start_y, w - label_width - 5, 25)

        # LINHA 1: Path
        path_label_rect = pygame.Rect(col1_x, start_y + row_height, label_width, 25)
        self.path_label = path_label_rect

        # Área do path com botões
        path_value_x = col1_x + label_width + 5
        self.path_text_rect = pygame.Rect(path_value_x, start_y + row_height, 80, 25)
        self.path_prev_button = pygame.Rect(path_value_x + 85, start_y + row_height, 25, 25)
        self.path_next_button = pygame.Rect(path_value_x + 115, start_y + row_height, 25, 25)

        # LINHA 2: Tamanho
        size_label_rect = pygame.Rect(col1_x, start_y + row_height * 2, label_width, 25)
        self.size_label = size_label_rect
        self.size_input = pygame.Rect(col1_x + label_width + 5, start_y + row_height * 2, input_width, 25)

        # LINHA 3: Nível Mínimo
        min_label_rect = pygame.Rect(col1_x, start_y + row_height * 3, label_width, 25)
        self.min_label = min_label_rect
        self.min_level_input = pygame.Rect(col1_x + label_width + 5, start_y + row_height * 3, input_width, 25)

        # LINHA 4: Nível Máximo
        max_label_rect = pygame.Rect(col1_x, start_y + row_height * 4, label_width, 25)
        self.max_label = max_label_rect
        self.max_level_input = pygame.Rect(col1_x + label_width + 5, start_y + row_height * 4, input_width, 25)

        # COLUNA 2 - LINHA 1: Intervalo
        interval_label_rect = pygame.Rect(col2_x, start_y + row_height, label_width, 25)
        self.interval_label = interval_label_rect
        self.interval_input = pygame.Rect(col2_x + label_width + 5, start_y + row_height, input_width, 25)

        # COLUNA 2 - LINHA 2: Delay
        delay_label_rect = pygame.Rect(col2_x, start_y + row_height * 2, label_width, 25)
        self.delay_label = delay_label_rect
        self.delay_input = pygame.Rect(col2_x + label_width + 5, start_y + row_height * 2, input_width, 25)

        # COLUNA 2 - LINHA 3: Repeat
        repeat_label_rect = pygame.Rect(col2_x, start_y + row_height * 3, label_width, 25)
        self.repeat_label = repeat_label_rect
        self.repeat_checkbox = pygame.Rect(col2_x + label_width + 5, start_y + row_height * 3, 18, 18)

        # COLUNA 2 - LINHA 4: Repeat Count
        repeat_count_label_rect = pygame.Rect(col2_x, start_y + row_height * 4, label_width, 25)
        self.repeat_count_label = repeat_count_label_rect

        repeat_count_value_x = col2_x + label_width + 5
        self.repeat_count_text = pygame.Rect(repeat_count_value_x, start_y + row_height * 4, 30, 25)
        self.repeat_minus_button = pygame.Rect(repeat_count_value_x + 35, start_y + row_height * 4, 25, 25)
        self.repeat_plus_button = pygame.Rect(repeat_count_value_x + 65, start_y + row_height * 4, 25, 25)

    def _update_button_positions(self):
        """Atualiza posições dos botões após arrastar"""
        x, y, w, h = self.rect
        margin = 20
        content_x = x + margin
        content_y = y + 45

        # Abas - centralizadas
        tab_width = 100
        tab_spacing = 10
        tabs_total_width = (tab_width * 3) + (tab_spacing * 2)
        tabs_start_x = x + (w - tabs_total_width) // 2

        for i, button in enumerate(self.tab_buttons):
            button.x = tabs_start_x + i * (tab_width + tab_spacing)
            button.y = y + 45

        # Botões de ação - centralizados
        button_width = 80
        button_spacing = 15
        buttons_total_width = (button_width * 2) + button_spacing
        buttons_start_x = x + (w - buttons_total_width) // 2

        self.save_button.x = buttons_start_x
        self.save_button.y = y + h - 40
        self.cancel_button.x = buttons_start_x + button_width + button_spacing
        self.cancel_button.y = y + h - 40

        # Waves tab - centralizada
        waves_list_width = 300
        waves_list_x = x + (w - waves_list_width) // 2

        self.add_wave_button.x = waves_list_x
        self.add_wave_button.y = content_y + 30
        self.remove_wave_button.x = waves_list_x + 100
        self.remove_wave_button.y = content_y + 30
        self.waves_list_area.x = waves_list_x
        self.waves_list_area.y = content_y + 65

        # Composition tab
        self.add_enemy_button.x = content_x
        self.add_enemy_button.y = y + h - 90
        self.equalize_button.x = content_x + 150
        self.equalize_button.y = y + h - 90
        self.enemies_list_area.x = content_x
        self.enemies_list_area.y = content_y + 35

        # Settings tab - atualiza todas as posições
        self._init_settings_ui(content_x, content_y, w - (margin * 2))

    def _get_pokemon_sprite(self, pokemon_id, size=32, expression="normal"):
        """
        Obtém o sprite/retrato do Pokémon.
        Prioriza o retrato (portrait), fallback para InMap, depois frontal.

        Args:
            pokemon_id: ID do Pokémon
            size: Tamanho desejado (largura e altura)
            expression: "normal", "happy", "angry" (usado apenas para retratos)
        """
        try:
            pokemon_id = int(pokemon_id)
        except (ValueError, TypeError):
            pokemon_id = 1

        cache_key = (pokemon_id, size, expression, "portrait")  # Inclui expression no cache

        if cache_key in self.sprite_cache:
            return self.sprite_cache[cache_key]

        sprite = None

        # ===== TENTA PRIMEIRO CARREGAR RETRATO (PORTRAIT) =====
        try:
            # Tenta carregar o retrato com a expressão solicitada
            portrait = self.pokedex.get_portrait(pokemon_id, expression, shiny=False)
            if portrait:
                sprite = portrait
                print(f"[WAVE_CONFIG] Retrato carregado: #{pokemon_id} ({expression})")
        except Exception as e:
            print(f"[WAVE_CONFIG] Erro ao carregar retrato: {e}")

        # ===== SE NÃO TEM RETRATO, TENTA INMAP =====
        if sprite is None:
            try:
                inmap_frames = self.pokedex.get_inmap_animation(pokemon_id, shiny=False)
                if inmap_frames and "down" in inmap_frames and inmap_frames["down"]:
                    sprite = inmap_frames["down"][0]
                    print(f"[WAVE_CONFIG] Fallback InMap: #{pokemon_id}")
            except Exception as e:
                print(f"[WAVE_CONFIG] Erro ao carregar InMap: {e}")

        # ===== SE NÃO TEM INMAP, TENTA FRONTAL =====
        if sprite is None:
            try:
                sprite = self.pokedex.get_sprite(pokemon_id, "front", shiny=False)
                if sprite:
                    print(f"[WAVE_CONFIG] Fallback front: #{pokemon_id}")
            except Exception as e:
                print(f"[WAVE_CONFIG] Erro ao carregar front: {e}")

        # ===== SE NADA FUNCIONOU, CRIA PLACEHOLDER =====
        if sprite is None:
            print(f"[WAVE_CONFIG] Criando placeholder para #{pokemon_id}")
            sprite = self._create_pokemon_placeholder(pokemon_id, size)

        # Escala mantendo proporção
        orig_width = sprite.get_width()
        orig_height = sprite.get_height()

        # Calcula a escala mantendo a proporção
        if orig_width > orig_height:
            target_width = size
            target_height = int(orig_height * (size / orig_width))
        else:
            target_height = size
            target_width = int(orig_width * (size / orig_height))

        # Escala suavemente
        if target_width > 0 and target_height > 0:
            scaled_sprite = pygame.transform.smoothscale(sprite, (target_width, target_height))

            # Centraliza em uma superfície quadrada
            final_surface = pygame.Surface((size, size), pygame.SRCALPHA)
            final_surface.fill((0, 0, 0, 0))
            offset_x = (size - target_width) // 2
            offset_y = (size - target_height) // 2
            final_surface.blit(scaled_sprite, (offset_x, offset_y))
            sprite = final_surface

        self.sprite_cache[cache_key] = sprite
        return sprite

    def _create_pokemon_placeholder(self, pokemon_id, size):
        """Cria um placeholder para Pokémon sem sprite"""
        placeholder = pygame.Surface((size, size), pygame.SRCALPHA)

        # Cores baseadas no ID
        colors = [
            (255, 99, 71),  # Tomato
            (135, 206, 235),  # Sky Blue
            (144, 238, 144),  # Light Green
            (255, 215, 0),  # Gold
            (221, 160, 221),  # Plum
            (255, 182, 193),  # Light Pink
            (176, 224, 230),  # Powder Blue
            (255, 228, 181),  # Moccasin
        ]
        color = colors[pokemon_id % len(colors)]

        # Fundo
        pygame.draw.rect(placeholder, color, (0, 0, size, size), border_radius=8)
        pygame.draw.rect(placeholder, (100, 100, 100), (0, 0, size, size), 2, border_radius=8)

        # Primeira letra do nome
        try:
            pokemon_name = self.pokedex.get_name(pokemon_id)
            first_letter = pokemon_name[0].upper() if pokemon_name else "?"
        except:
            first_letter = "?"

        font_size = max(12, size // 2)
        font = pygame.font.Font(None, font_size)
        text = font.render(first_letter, True, (255, 255, 255))
        text_rect = text.get_rect(center=(size // 2, size // 2))
        placeholder.blit(text, text_rect)

        # ID pequeno no canto
        small_font = pygame.font.Font(None, max(8, size // 4))
        id_text = small_font.render(f"#{pokemon_id}", True, (200, 200, 200))
        id_rect = id_text.get_rect(bottomright=(size - 3, size - 3))
        placeholder.blit(id_text, id_rect)

        return placeholder

    def _get_pokemon_sprite_with_expression(self, pokemon_id, size=32, expression="normal"):
        """
        Obtém sprite do Pokémon com expressão específica.
        Útil para mostrar diferentes emoções no diálogo.
        """
        return self._get_pokemon_sprite(pokemon_id, size, expression)

    def handle_event(self, event):
        """Processa eventos do diálogo"""
        if not self.visible:
            return False

        mouse_pos = pygame.mouse.get_pos()
        mouse_x, mouse_y = mouse_pos

        # Reset hover
        self.hovered_button = None

        # Se clicou fora do diálogo, fecha
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if not self.rect.collidepoint(mouse_x, mouse_y) and not self.showing_pokemon_selector:
                self.visible = False
                return True

        # Seletor de Pokémon tem prioridade
        if self.showing_pokemon_selector:
            return self._handle_pokemon_selector_event(event, mouse_x, mouse_y)

        # Atualiza hover dos botões
        if event.type == pygame.MOUSEMOTION:
            self._update_hover(mouse_x, mouse_y)

        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                return self._handle_left_click(mouse_x, mouse_y)
            elif event.button == 4:  # Scroll up
                return self._handle_scroll(-1)
            elif event.button == 5:  # Scroll down
                return self._handle_scroll(1)

        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1:
                self.dragging = False
                return True

        elif event.type == pygame.MOUSEMOTION:
            if self.dragging:
                self.rect.x = mouse_x - self.drag_offset_x
                self.rect.y = mouse_y - self.drag_offset_y
                self._update_button_positions()
                return True

        elif event.type == pygame.KEYDOWN:
            if self.active_input:
                return self._handle_keydown(event)
            elif event.key == pygame.K_ESCAPE:
                self.visible = False
                return True

        return True

    def _update_hover(self, mouse_x, mouse_y):
        """Atualiza estado de hover dos botões"""
        buttons = [
            (self.save_button, "save"),
            (self.cancel_button, "cancel"),
            (self.add_wave_button, "add_wave"),
            (self.remove_wave_button, "remove_wave"),
            (self.add_enemy_button, "add_enemy"),
            (self.equalize_button, "equalize"),
            (self.path_prev_button, "path_prev"),
            (self.path_next_button, "path_next"),
            (self.repeat_minus_button, "repeat_minus"),
            (self.repeat_plus_button, "repeat_plus"),
        ]

        for button, name in buttons:
            if button.collidepoint(mouse_x, mouse_y):
                self.hovered_button = name
                return

    def _handle_left_click(self, mouse_x, mouse_y):
        """Processa clique esquerdo"""
        # Título para arrastar
        title_rect = pygame.Rect(self.rect.x, self.rect.y, self.rect.width, 30)
        if title_rect.collidepoint(mouse_x, mouse_y):
            self.dragging = True
            self.drag_offset_x = mouse_x - self.rect.x
            self.drag_offset_y = mouse_y - self.rect.y
            return True

        # Botões Salvar/Cancelar
        if self.save_button.collidepoint(mouse_x, mouse_y):
            # Valida total de % antes de salvar
            if self.selected_tab == "composition":
                wave = self.wave_manager.get_current_wave()
                if wave:
                    total = sum(e.percentage for e in wave.enemies)
                    if total != 100:
                        self.input_errors["total"] = f"Total deve ser 100% (atual: {total}%)"
                        return True
                    elif not wave.enemies:
                        self.input_errors["total"] = "Adicione pelo menos um Pokémon"
                        return True

            self.visible = False
            return "saved"

        if self.cancel_button.collidepoint(mouse_x, mouse_y):
            self.visible = False
            return True

        # Abas
        for i, tab_button in enumerate(self.tab_buttons):
            if tab_button.collidepoint(mouse_x, mouse_y):
                tabs = ["waves", "composition", "settings"]
                self.selected_tab = tabs[i]
                return True

        # Processa baseado na aba
        if self.selected_tab == "waves":
            return self._handle_waves_tab_click(mouse_x, mouse_y)
        elif self.selected_tab == "composition":
            return self._handle_composition_tab_click(mouse_x, mouse_y)
        elif self.selected_tab == "settings":
            return self._handle_settings_tab_click(mouse_x, mouse_y)

        return True

    def _handle_waves_tab_click(self, mouse_x, mouse_y):
        """Processa cliques na aba de waves"""
        if self.add_wave_button.collidepoint(mouse_x, mouse_y):
            self.wave_manager.add_wave()
            self.selected_wave_index = self.wave_manager.selected_wave
            self.enemies_scroll = 0
            self.input_errors.pop("total", None)
            return True

        if self.remove_wave_button.collidepoint(mouse_x, mouse_y):
            if self.wave_manager.waves:
                self.wave_manager.remove_wave(self.selected_wave_index)
                self.selected_wave_index = self.wave_manager.selected_wave
                self.enemies_scroll = 0
                self.input_errors.pop("total", None)
            return True

        # Seleção de wave na lista
        if self.waves_list_area.collidepoint(mouse_x, mouse_y):
            relative_y = mouse_y - self.waves_list_area.y
            item_index = (relative_y // self.wave_item_height) + self.waves_scroll

            if 0 <= item_index < len(self.wave_manager.waves):
                self.selected_wave_index = item_index
                self.wave_manager.selected_wave = item_index
                self.enemies_scroll = 0
                self.input_errors.pop("total", None)
                return True

        return True

    def _handle_composition_tab_click(self, mouse_x, mouse_y):
        """Processa cliques na aba de composição"""
        wave = self.wave_manager.get_current_wave()
        if not wave:
            return True

        # Botão adicionar inimigo
        if self.add_enemy_button.collidepoint(mouse_x, mouse_y):
            if len(wave.enemies) < 8:
                first_id = self.available_pokemon_ids[0] if self.available_pokemon_ids else 1
                wave.enemies.append(WaveEnemy(first_id, 0))
                self.input_errors.pop("total", None)
            return True

        # Botão distribuir igualmente
        if self.equalize_button.collidepoint(mouse_x, mouse_y) and wave.enemies:
            equal_percent = 100 // len(wave.enemies)
            remainder = 100 - (equal_percent * len(wave.enemies))
            for i, enemy in enumerate(wave.enemies):
                enemy.percentage = equal_percent + (1 if i < remainder else 0)
            self.input_errors.pop("total", None)
            return True

        # Cliques na lista de inimigos
        if self.enemies_list_area.collidepoint(mouse_x, mouse_y):
            relative_y = mouse_y - self.enemies_list_area.y
            item_index = (relative_y // self.enemy_item_height) + self.enemies_scroll

            print(f"DEBUG: Clicou na área da lista, relative_y={relative_y}, item_index={item_index}")

            if 0 <= item_index < len(wave.enemies):
                enemy = wave.enemies[item_index]

                # Calcula posição do item na tela (considerando scroll)
                item_y = self.enemies_list_area.y + 2 + (item_index - self.enemies_scroll) * self.enemy_item_height

                # Calcula posição do botão remover
                remove_rect = pygame.Rect(self.enemies_list_area.right - 30, item_y + 5, 20, 20)

                # Verifica se clicou no botão remover
                if remove_rect.collidepoint(mouse_x, mouse_y):
                    print(f"DEBUG: Clicou no botão remover do inimigo {item_index}")
                    del wave.enemies[item_index]
                    total = sum(e.percentage for e in wave.enemies)
                    if total != 100 and wave.enemies:
                        self.input_errors["total"] = f"Total deve ser 100% (atual: {total}%)"
                    elif not wave.enemies:
                        self.input_errors["total"] = "Adicione pelo menos um Pokémon"
                    else:
                        self.input_errors.pop("total", None)
                    return True

                # Área do Pokémon (para selecionar)
                pokemon_rect = pygame.Rect(self.enemies_list_area.x + 40, item_y + 5, 150, 25)
                if pokemon_rect.collidepoint(mouse_x, mouse_y):
                    print(f"DEBUG: Clicou na área do Pokémon {item_index}")
                    self.showing_pokemon_selector = True
                    self.pokemon_selector_enemy_index = item_index
                    self.pokemon_selector_scroll = 0
                    self.pokemon_search = ""
                    return True

                # Campo de porcentagem - CORRIGIDO
                percent_rect = pygame.Rect(self.enemies_list_area.right - 90, item_y + 10, 45, 22)
                print(
                    f"DEBUG: Verificando campo % em ({percent_rect.x}, {percent_rect.y}) - mouse em ({mouse_x}, {mouse_y})")

                if percent_rect.collidepoint(mouse_x, mouse_y):
                    print(f"DEBUG: Clicou no campo % do inimigo {item_index}")
                    self.active_input = f"percent_{item_index}"
                    self.input_texts[self.active_input] = str(enemy.percentage)
                    return True
                else:
                    print(f"DEBUG: Mouse NÃO está sobre o campo % (x: {mouse_x}, y: {mouse_y})")
            else:
                print(f"DEBUG: item_index {item_index} fora do range (0-{len(wave.enemies) - 1})")

        return True

    def _handle_settings_tab_click(self, mouse_x, mouse_y):
        """Processa cliques na aba de configurações"""
        wave = self.wave_manager.get_current_wave()
        if not wave:
            return True

        # Campo nome
        if self.name_input.collidepoint(mouse_x, mouse_y):
            self.active_input = "wave_name"
            self.input_texts["wave_name"] = wave.name
            return True

        # Botões de path
        if self.path_prev_button.collidepoint(mouse_x, mouse_y):
            wave.path_index = max(0, wave.path_index - 1)
            return True

        if self.path_next_button.collidepoint(mouse_x, mouse_y):
            max_path = max(0, len(self.path_manager.paths) - 1)
            wave.path_index = min(max_path, wave.path_index + 1)
            return True

        # Input fields
        fields = [
            (self.size_input, "wave_size"),
            (self.min_level_input, "min_level"),
            (self.max_level_input, "max_level"),
            (self.interval_input, "spawn_interval"),
            (self.delay_input, "initial_delay"),
        ]

        for rect, field_name in fields:
            if rect.collidepoint(mouse_x, mouse_y):
                self.active_input = field_name
                current_value = getattr(wave, field_name)
                self.input_texts[field_name] = str(current_value)
                return True

        # Checkbox repeat
        if self.repeat_checkbox.collidepoint(mouse_x, mouse_y):
            wave.repeat_wave = not wave.repeat_wave
            return True

        # Botões de repeat count
        if wave.repeat_wave:
            if self.repeat_minus_button.collidepoint(mouse_x, mouse_y):
                wave.repeat_count = max(1, wave.repeat_count - 1)
                return True

            if self.repeat_plus_button.collidepoint(mouse_x, mouse_y):
                wave.repeat_count = min(10, wave.repeat_count + 1)
                return True

        return True

    def _handle_pokemon_selector_event(self, event, mouse_x, mouse_y):
        """Processa eventos do seletor de Pokémon"""
        selector_rect = pygame.Rect(
            self.rect.x + 80,
            self.rect.y + 120,
            440,
            360
        )

        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                # Clique fora do seletor
                if not selector_rect.collidepoint(mouse_x, mouse_y):
                    self.showing_pokemon_selector = False
                    return True

                # Campo de busca
                search_rect = pygame.Rect(selector_rect.x + 10, selector_rect.y + 40, 250, 25)
                if search_rect.collidepoint(mouse_x, mouse_y):
                    self.active_input = "pokemon_search"
                    return True

                # Lista de Pokémon
                list_area = pygame.Rect(selector_rect.x + 5, selector_rect.y + 75, selector_rect.width - 10, 240)
                if list_area.collidepoint(mouse_x, mouse_y):
                    relative_y = mouse_y - list_area.y
                    item_index = (relative_y // 35) + self.pokemon_selector_scroll

                    filtered_ids = self._filter_pokemon()
                    if 0 <= item_index < len(filtered_ids):
                        wave = self.wave_manager.get_current_wave()
                        if wave and self.pokemon_selector_enemy_index < len(wave.enemies):
                            wave.enemies[self.pokemon_selector_enemy_index].pokemon_id = filtered_ids[item_index]
                            cache_key = (filtered_ids[item_index], 32)
                            if cache_key in self.sprite_cache:
                                del self.sprite_cache[cache_key]
                            self.showing_pokemon_selector = False
                        return True

            elif event.button == 4:  # Scroll up
                self.pokemon_selector_scroll = max(0, self.pokemon_selector_scroll - 1)
                return True
            elif event.button == 5:  # Scroll down
                filtered_count = len(self._filter_pokemon())
                max_scroll = max(0, filtered_count - 7)
                self.pokemon_selector_scroll = min(max_scroll, self.pokemon_selector_scroll + 1)
                return True

        elif event.type == pygame.KEYDOWN:
            if self.active_input == "pokemon_search":
                if event.key == pygame.K_BACKSPACE:
                    self.pokemon_search = self.pokemon_search[:-1]
                    self.pokemon_selector_scroll = 0
                elif event.key == pygame.K_RETURN:
                    self.active_input = None
                elif event.key == pygame.K_ESCAPE:
                    self.showing_pokemon_selector = False
                elif event.unicode.isprintable():
                    self.pokemon_search += event.unicode
                    self.pokemon_selector_scroll = 0
                return True
            elif event.key == pygame.K_ESCAPE:
                self.showing_pokemon_selector = False
                return True

        return True

    def _filter_pokemon(self):
        """Filtra Pokémon por busca"""
        if not self.pokemon_search:
            return self.available_pokemon_ids

        search_lower = self.pokemon_search.lower()
        filtered = []

        for pid in self.available_pokemon_ids:
            name = self.pokedex.get_name(pid).lower()
            if search_lower in str(pid) or search_lower in name:
                filtered.append(pid)

        return filtered

    def _handle_keydown(self, event):
        """Processa teclas pressionadas em inputs"""
        if event.key == pygame.K_RETURN:
            return self._apply_input()
        elif event.key == pygame.K_ESCAPE:
            self.active_input = None
            return True
        elif event.key == pygame.K_BACKSPACE:
            if self.active_input in self.input_texts:
                self.input_texts[self.active_input] = self.input_texts[self.active_input][:-1]
            return True
        elif event.unicode.isdigit() or event.unicode == '.' or (
                self.active_input == "wave_name" and event.unicode.isprintable()):
            if self.active_input in self.input_texts:
                self.input_texts[self.active_input] += event.unicode
            return True
        return False

    def _apply_input(self):
        """Aplica o valor do input atual"""
        wave = self.wave_manager.get_current_wave()
        if not wave or not self.active_input:
            return False

        try:
            value = self.input_texts.get(self.active_input, "")

            # Nome da wave
            if self.active_input == "wave_name":
                wave.name = value

            # Porcentagem dos inimigos
            elif self.active_input.startswith("percent_"):
                index = int(self.active_input.split("_")[1])
                if 0 <= index < len(wave.enemies):
                    new_percent = int(float(value)) if value else 0
                    new_percent = max(0, min(100, new_percent))
                    wave.enemies[index].percentage = new_percent

                    total = sum(e.percentage for e in wave.enemies)
                    if total != 100:
                        self.input_errors["total"] = f"Total deve ser 100% (atual: {total}%)"
                    else:
                        self.input_errors.pop("total", None)

            # Campos numéricos
            elif self.active_input == "wave_size":
                wave.wave_size = max(1, int(float(value)) if value else 1)
            elif self.active_input == "min_level":
                wave.min_level = max(1, int(float(value)) if value else 1)
            elif self.active_input == "max_level":
                new_max = int(float(value)) if value else wave.min_level
                wave.max_level = max(wave.min_level, new_max)
            elif self.active_input == "spawn_interval":
                wave.spawn_interval = max(0.1, float(value) if value else 0.1)
            elif self.active_input == "initial_delay":
                wave.initial_delay = max(0, float(value) if value else 0)

            self.active_input = None
            return True

        except ValueError:
            self.active_input = None
            return False

    def _handle_scroll(self, direction):
        """Processa scroll do mouse"""
        if self.selected_tab == "waves":
            max_scroll = max(0, len(self.wave_manager.waves) - self.waves_per_page)
            self.waves_scroll = max(0, min(max_scroll, self.waves_scroll + direction))
            return True
        elif self.selected_tab == "composition":
            wave = self.wave_manager.get_current_wave()
            if wave:
                max_scroll = max(0, len(wave.enemies) - self.enemies_per_page)
                self.enemies_scroll = max(0, min(max_scroll, self.enemies_scroll + direction))
            return True
        return False

    def render(self, screen):
        """Renderiza o diálogo"""
        if not self.visible:
            return

        # Overlay
        overlay = pygame.Surface((screen.get_width(), screen.get_height()))
        overlay.set_alpha(180)
        overlay.fill((0, 0, 0))
        screen.blit(overlay, (0, 0))

        # Fundo da janela
        pygame.draw.rect(screen, self.COLORS['bg'], self.rect, border_radius=10)
        pygame.draw.rect(screen, self.COLORS['border'], self.rect, 2, border_radius=10)

        # Título (arrastável)
        title_bar = pygame.Rect(self.rect.x, self.rect.y, self.rect.width, 30)
        pygame.draw.rect(screen, self.COLORS['bg_light'], title_bar, border_top_left_radius=10,
                         border_top_right_radius=10)

        title = self.font_title.render("Configuração de Waves", True, self.COLORS['text'])
        screen.blit(title, (self.rect.x + 10, self.rect.y + 8))

        # Abas
        tabs = ["Waves", "Composição", "Configurações"]
        for i, tab_name in enumerate(tabs):
            tab_button = self.tab_buttons[i]

            if (i == 0 and self.selected_tab == "waves") or \
                    (i == 1 and self.selected_tab == "composition") or \
                    (i == 2 and self.selected_tab == "settings"):
                color = self.COLORS['accent']
                border = self.COLORS['border']
            else:
                color = self.COLORS['bg_light']
                border = self.COLORS['border_light']

            pygame.draw.rect(screen, color, tab_button, border_radius=5)
            pygame.draw.rect(screen, border, tab_button, 1, border_radius=5)

            tab_text = self.font_small.render(tab_name, True, self.COLORS['text'])
            text_x = tab_button.x + (tab_button.width - tab_text.get_width()) // 2
            text_y = tab_button.y + (tab_button.height - tab_text.get_height()) // 2
            screen.blit(tab_text, (text_x, text_y))

        # Renderiza aba atual
        if self.selected_tab == "waves":
            self._render_waves_tab(screen)
        elif self.selected_tab == "composition":
            self._render_composition_tab(screen)
        elif self.selected_tab == "settings":
            self._render_settings_tab(screen)

        # Seletor de Pokémon
        if self.showing_pokemon_selector:
            self._render_pokemon_selector(screen)

        # Botões Salvar/Cancelar
        # Salvar
        save_color = self.COLORS['success'] if self.hovered_button == "save" else (0, 100, 0)
        pygame.draw.rect(screen, save_color, self.save_button, border_radius=5)
        pygame.draw.rect(screen, self.COLORS['text'], self.save_button, 1, border_radius=5)
        save_text = self.font.render("Salvar", True, self.COLORS['text'])
        save_x = self.save_button.x + (self.save_button.width - save_text.get_width()) // 2
        save_y = self.save_button.y + (self.save_button.height - save_text.get_height()) // 2
        screen.blit(save_text, (save_x, save_y))

        # Cancelar
        cancel_color = self.COLORS['danger'] if self.hovered_button == "cancel" else (100, 0, 0)
        pygame.draw.rect(screen, cancel_color, self.cancel_button, border_radius=5)
        pygame.draw.rect(screen, self.COLORS['text'], self.cancel_button, 1, border_radius=5)
        cancel_text = self.font.render("Cancelar", True, self.COLORS['text'])
        cancel_x = self.cancel_button.x + (self.cancel_button.width - cancel_text.get_width()) // 2
        cancel_y = self.cancel_button.y + (self.cancel_button.height - cancel_text.get_height()) // 2
        screen.blit(cancel_text, (cancel_x, cancel_y))

        # Mensagem de erro
        if "total" in self.input_errors and self.selected_tab == "composition":
            error_text = self.font_small.render(self.input_errors["total"], True, (255, 100, 100))
            screen.blit(error_text, (self.rect.x + 20, self.rect.bottom - 60))

    def _render_waves_tab(self, screen):
        """Renderiza a aba de lista de waves - CENTRALIZADA"""
        # Botões centralizados
        add_color = self.COLORS['success'] if self.hovered_button == "add_wave" else (0, 80, 0)
        pygame.draw.rect(screen, add_color, self.add_wave_button, border_radius=5)
        add_text = self.font_small.render("+ Nova", True, self.COLORS['text'])
        add_text_x = self.add_wave_button.x + (self.add_wave_button.width - add_text.get_width()) // 2
        add_text_y = self.add_wave_button.y + (self.add_wave_button.height - add_text.get_height()) // 2
        screen.blit(add_text, (add_text_x, add_text_y))

        remove_color = self.COLORS['danger'] if self.hovered_button == "remove_wave" else (80, 0, 0)
        pygame.draw.rect(screen, remove_color, self.remove_wave_button, border_radius=5)
        remove_text = self.font_small.render("- Remover", True, self.COLORS['text'])
        remove_text_x = self.remove_wave_button.x + (self.remove_wave_button.width - remove_text.get_width()) // 2
        remove_text_y = self.remove_wave_button.y + (self.remove_wave_button.height - remove_text.get_height()) // 2
        screen.blit(remove_text, (remove_text_x, remove_text_y))

        # Área da lista
        pygame.draw.rect(screen, self.COLORS['bg_dark'], self.waves_list_area, border_radius=5)

        # Clipping
        old_clip = screen.get_clip()
        screen.set_clip(self.waves_list_area)

        list_x = self.waves_list_area.x + 5
        list_start_y = self.waves_list_area.y + 2 - self.waves_scroll * self.wave_item_height

        for i, wave in enumerate(self.wave_manager.waves):
            item_y = list_start_y + i * self.wave_item_height

            if item_y + self.wave_item_height < self.waves_list_area.y or item_y > self.waves_list_area.y + self.waves_list_area.height:
                continue

            item_rect = pygame.Rect(list_x, item_y, self.waves_list_area.width - 10, self.wave_item_height - 4)

            # Cor de fundo
            is_selected = (i == self.selected_wave_index)
            if is_selected:
                bg_color = self.COLORS['accent']
            else:
                bg_color = self.COLORS['bg_light'] if i % 2 == 0 else self.COLORS['bg']

            pygame.draw.rect(screen, bg_color, item_rect)

            if is_selected:
                pygame.draw.rect(screen, self.COLORS['border'], item_rect, 1)

            # Nome da wave
            wave_name = f"{wave.name} (P{wave.path_index + 1})"
            if not wave.enabled:
                wave_name = f"[X] {wave_name}"

            name_text = self.font_small.render(wave_name, True, self.COLORS['text'])
            screen.blit(name_text, (item_rect.x + 5, item_rect.y + 7))

            # Quantidade
            count_text = self.font_small.render(f"{wave.wave_size}", True, self.COLORS['text_dim'])
            screen.blit(count_text, (item_rect.right - 25, item_rect.y + 7))

        screen.set_clip(old_clip)

        # Scroll indicator
        if len(self.wave_manager.waves) > self.waves_per_page:
            scroll_text = self.font_small.render(
                f"{self.waves_scroll + 1}-{min(self.waves_scroll + self.waves_per_page, len(self.wave_manager.waves))} de {len(self.wave_manager.waves)}",
                True, self.COLORS['text_dark']
            )
            text_x = self.waves_list_area.x + (self.waves_list_area.width - scroll_text.get_width()) // 2
            screen.blit(scroll_text, (text_x, self.waves_list_area.bottom + 5))

    def _render_composition_tab(self, screen):
        """Renderiza a aba de composição"""
        wave = self.wave_manager.get_current_wave()
        if not wave:
            no_wave_text = self.font.render("Selecione uma wave na aba 'Waves'", True, self.COLORS['text_dim'])
            text_x = self.rect.x + (self.rect.width - no_wave_text.get_width()) // 2
            text_y = self.rect.y + 250
            screen.blit(no_wave_text, (text_x, text_y))
            return

        # Título da wave
        title = self.font.render(f"Composição: {wave.name}", True, self.COLORS['border'])
        screen.blit(title, (self.rect.x + 20, self.rect.y + 80))

        # Área da lista
        pygame.draw.rect(screen, self.COLORS['bg_dark'], self.enemies_list_area, border_radius=5)

        # Clipping
        old_clip = screen.get_clip()
        screen.set_clip(self.enemies_list_area)

        list_x = self.enemies_list_area.x + 5
        list_start_y = self.enemies_list_area.y + 2 - self.enemies_scroll * self.enemy_item_height

        for i, enemy in enumerate(wave.enemies):
            item_y = list_start_y + i * self.enemy_item_height

            if item_y + self.enemy_item_height < self.enemies_list_area.y or item_y > self.enemies_list_area.y + self.enemies_list_area.height:
                continue

            item_rect = pygame.Rect(list_x, item_y, self.enemies_list_area.width - 10, self.enemy_item_height - 4)

            # Fundo
            bg_color = self.COLORS['bg_light'] if i % 2 == 0 else self.COLORS['bg']
            pygame.draw.rect(screen, bg_color, item_rect)
            pygame.draw.rect(screen, self.COLORS['border_light'], item_rect, 1)

            # ===== SPRITE DO POKÉMON (USANDO RETRATO) =====
            # Usa o retrato com expressão normal (pode ser "normal", "happy", "angry")
            sprite = self._get_pokemon_sprite(enemy.pokemon_id, 32, "normal")
            screen.blit(sprite, (item_rect.x + 5, item_rect.y + 5))

            # Nome
            pokemon_name = self.pokedex.get_name(enemy.pokemon_id)
            name_text = self.font_small.render(pokemon_name, True, self.COLORS['text'])
            screen.blit(name_text, (item_rect.x + 42, item_rect.y + 8))

            # Tipos
            types = self.pokedex.get_types(enemy.pokemon_id)
            if types:
                type_text = self.font_small.render("/".join(types), True, self.COLORS['text_dim'])
                screen.blit(type_text, (item_rect.x + 42, item_rect.y + 24))

            # Botão remover
            remove_rect = pygame.Rect(self.enemies_list_area.right - 30, item_y + 5, 20, 20)
            pygame.draw.rect(screen, self.COLORS['danger'], remove_rect)
            pygame.draw.line(screen, self.COLORS['text'],
                             (remove_rect.x + 5, remove_rect.y + 5),
                             (remove_rect.right - 5, remove_rect.bottom - 5), 1)
            pygame.draw.line(screen, self.COLORS['text'],
                             (remove_rect.right - 5, remove_rect.y + 5),
                             (remove_rect.x + 5, remove_rect.bottom - 5), 1)

            # Campo de porcentagem
            percent_rect = pygame.Rect(self.enemies_list_area.right - 90, item_y + 10, 45, 22)

            if self.active_input == f"percent_{i}":
                border_color = self.COLORS['input_active']
                display_text = self.input_texts.get(f"percent_{i}", str(enemy.percentage))
            else:
                border_color = self.COLORS['input_border']
                display_text = str(enemy.percentage)

            pygame.draw.rect(screen, self.COLORS['input_bg'], percent_rect)
            pygame.draw.rect(screen, border_color, percent_rect, 1)

            percent_text = self.font_small.render(display_text, True, self.COLORS['text'])
            screen.blit(percent_text, (percent_rect.x + 5, percent_rect.y + 4))

            # Símbolo %
            percent_symbol = self.font_small.render("%", True, self.COLORS['text_dim'])
            screen.blit(percent_symbol, (percent_rect.right + 2, percent_rect.y + 4))

        screen.set_clip(old_clip)

        # Scroll indicator
        if len(wave.enemies) > self.enemies_per_page:
            scroll_text = self.font_small.render(
                f"{self.enemies_scroll + 1}-{min(self.enemies_scroll + self.enemies_per_page, len(wave.enemies))} de {len(wave.enemies)}",
                True, self.COLORS['text_dark']
            )
            screen.blit(scroll_text, (self.enemies_list_area.x + 10, self.enemies_list_area.bottom + 5))

        # Botões de ação
        add_color = self.COLORS['success'] if self.hovered_button == "add_enemy" else (0, 80, 0)
        pygame.draw.rect(screen, add_color, self.add_enemy_button, border_radius=5)
        add_text = self.font_small.render("+ Adicionar", True, self.COLORS['text'])
        add_text_x = self.add_enemy_button.x + (self.add_enemy_button.width - add_text.get_width()) // 2
        add_text_y = self.add_enemy_button.y + (self.add_enemy_button.height - add_text.get_height()) // 2
        screen.blit(add_text, (add_text_x, add_text_y))

        if wave.enemies:
            eq_color = self.COLORS['warning'] if self.hovered_button == "equalize" else (80, 80, 0)
            pygame.draw.rect(screen, eq_color, self.equalize_button, border_radius=5)
            equalize_text = self.font_small.render("Distribuir", True, self.COLORS['text'])
            eq_text_x = self.equalize_button.x + (self.equalize_button.width - equalize_text.get_width()) // 2
            eq_text_y = self.equalize_button.y + (self.equalize_button.height - equalize_text.get_height()) // 2
            screen.blit(equalize_text, (eq_text_x, eq_text_y))

        # Total
        total = sum(e.percentage for e in wave.enemies)
        total_color = (100, 255, 100) if total == 100 else (255, 100, 100)
        total_text = self.font.render(f"Total: {total}%", True, total_color)
        screen.blit(total_text, (self.rect.x + 320, self.rect.y + 435))

    def _render_settings_tab(self, screen):
        """Renderiza a aba de configurações em grid padronizado"""
        wave = self.wave_manager.get_current_wave()
        if not wave:
            no_wave_text = self.font.render("Selecione uma wave na aba 'Waves'", True, self.COLORS['text_dim'])
            text_x = self.rect.x + (self.rect.width - no_wave_text.get_width()) // 2
            text_y = self.rect.y + 250
            screen.blit(no_wave_text, (text_x, text_y))
            return

        # LINHA 0: Nome da Wave
        name_label = self.font_small.render("Nome:", True, self.COLORS['text_dim'])
        screen.blit(name_label, (self.name_label.x, self.name_label.y))

        pygame.draw.rect(screen, self.COLORS['input_bg'], self.name_input)
        border_color = self.COLORS['input_active'] if self.active_input == "wave_name" else self.COLORS['input_border']
        pygame.draw.rect(screen, border_color, self.name_input, 1)

        display_text = self.input_texts.get("wave_name", wave.name) if self.active_input == "wave_name" else wave.name
        name_text = self.font_small.render(display_text, True, self.COLORS['text'])
        screen.blit(name_text, (self.name_input.x + 5, self.name_input.y + 4))

        # LINHA 1: Path
        path_label = self.font_small.render("Path:", True, self.COLORS['text_dim'])
        screen.blit(path_label, (self.path_label.x, self.path_label.y))

        # Texto do path
        path_text = self.font_small.render(f"Path {wave.path_index + 1}", True, self.COLORS['text'])
        screen.blit(path_text, (self.path_text_rect.x, self.path_text_rect.y + 4))

        # Botões path
        prev_color = self.COLORS['bg_light'] if self.hovered_button == "path_prev" else (60, 60, 70)
        next_color = self.COLORS['bg_light'] if self.hovered_button == "path_next" else (60, 60, 70)

        pygame.draw.rect(screen, prev_color, self.path_prev_button)
        pygame.draw.rect(screen, next_color, self.path_next_button)
        pygame.draw.rect(screen, self.COLORS['border_light'], self.path_prev_button, 1)
        pygame.draw.rect(screen, self.COLORS['border_light'], self.path_next_button, 1)

        prev_text = self.font_small.render("<", True, self.COLORS['text'])
        next_text = self.font_small.render(">", True, self.COLORS['text'])
        prev_text_x = self.path_prev_button.x + (self.path_prev_button.width - prev_text.get_width()) // 2
        prev_text_y = self.path_prev_button.y + (self.path_prev_button.height - prev_text.get_height()) // 2
        next_text_x = self.path_next_button.x + (self.path_next_button.width - next_text.get_width()) // 2
        next_text_y = self.path_next_button.y + (self.path_next_button.height - next_text.get_height()) // 2
        screen.blit(prev_text, (prev_text_x, prev_text_y))
        screen.blit(next_text, (next_text_x, next_text_y))

        # LINHA 2: Tamanho
        size_label = self.font_small.render("Tamanho:", True, self.COLORS['text_dim'])
        screen.blit(size_label, (self.size_label.x, self.size_label.y))
        self._render_input_field(screen, "wave_size", str(wave.wave_size), self.size_input)

        # LINHA 3: Nível Mínimo
        min_label = self.font_small.render("Nível Mín:", True, self.COLORS['text_dim'])
        screen.blit(min_label, (self.min_label.x, self.min_label.y))
        self._render_input_field(screen, "min_level", str(wave.min_level), self.min_level_input)

        # LINHA 4: Nível Máximo
        max_label = self.font_small.render("Nível Máx:", True, self.COLORS['text_dim'])
        screen.blit(max_label, (self.max_label.x, self.max_label.y))
        self._render_input_field(screen, "max_level", str(wave.max_level), self.max_level_input)

        # COLUNA 2 - LINHA 1: Intervalo
        interval_label = self.font_small.render("Intervalo (s):", True, self.COLORS['text_dim'])
        screen.blit(interval_label, (self.interval_label.x, self.interval_label.y))
        self._render_input_field(screen, "spawn_interval", f"{wave.spawn_interval:.1f}", self.interval_input)

        # COLUNA 2 - LINHA 2: Delay
        delay_label = self.font_small.render("Delay (s):", True, self.COLORS['text_dim'])
        screen.blit(delay_label, (self.delay_label.x, self.delay_label.y))
        self._render_input_field(screen, "initial_delay", f"{wave.initial_delay:.1f}", self.delay_input)

        # COLUNA 2 - LINHA 3: Repeat
        repeat_label = self.font_small.render("Repetir:", True, self.COLORS['text_dim'])
        screen.blit(repeat_label, (self.repeat_label.x, self.repeat_label.y))

        # Checkbox
        if wave.repeat_wave:
            pygame.draw.rect(screen, self.COLORS['success'], self.repeat_checkbox)
            check_text = self.font_small.render("✓", True, self.COLORS['text'])
            check_text_x = self.repeat_checkbox.x + (self.repeat_checkbox.width - check_text.get_width()) // 2
            check_text_y = self.repeat_checkbox.y + (self.repeat_checkbox.height - check_text.get_height()) // 2
            screen.blit(check_text, (check_text_x, check_text_y))
        else:
            pygame.draw.rect(screen, self.COLORS['input_bg'], self.repeat_checkbox)
        pygame.draw.rect(screen, self.COLORS['border_light'], self.repeat_checkbox, 1)

        # COLUNA 2 - LINHA 4: Repeat Count
        if wave.repeat_wave:
            count_label = self.font_small.render("Vezes:", True, self.COLORS['text_dim'])
            screen.blit(count_label, (self.repeat_count_label.x, self.repeat_count_label.y))

            # Texto do contador
            count_text = self.font_small.render(str(wave.repeat_count), True, self.COLORS['text'])
            screen.blit(count_text, (self.repeat_count_text.x, self.repeat_count_text.y + 4))

            # Botões +/-
            minus_color = self.COLORS['bg_light'] if self.hovered_button == "repeat_minus" else (60, 60, 70)
            plus_color = self.COLORS['bg_light'] if self.hovered_button == "repeat_plus" else (60, 60, 70)

            pygame.draw.rect(screen, minus_color, self.repeat_minus_button)
            pygame.draw.rect(screen, plus_color, self.repeat_plus_button)
            pygame.draw.rect(screen, self.COLORS['border_light'], self.repeat_minus_button, 1)
            pygame.draw.rect(screen, self.COLORS['border_light'], self.repeat_plus_button, 1)

            minus_text = self.font_small.render("-", True, self.COLORS['text'])
            plus_text = self.font_small.render("+", True, self.COLORS['text'])
            minus_text_x = self.repeat_minus_button.x + (self.repeat_minus_button.width - minus_text.get_width()) // 2
            minus_text_y = self.repeat_minus_button.y + (self.repeat_minus_button.height - minus_text.get_height()) // 2
            plus_text_x = self.repeat_plus_button.x + (self.repeat_plus_button.width - plus_text.get_width()) // 2
            plus_text_y = self.repeat_plus_button.y + (self.repeat_plus_button.height - plus_text.get_height()) // 2
            screen.blit(minus_text, (minus_text_x, minus_text_y))
            screen.blit(plus_text, (plus_text_x, plus_text_y))

    def _render_input_field(self, screen, field_name, value, rect):
        """Renderiza um campo de input"""
        if self.active_input == field_name:
            border_color = self.COLORS['input_active']
            display_text = self.input_texts.get(field_name, value)
        else:
            border_color = self.COLORS['input_border']
            display_text = value

        pygame.draw.rect(screen, self.COLORS['input_bg'], rect)
        pygame.draw.rect(screen, border_color, rect, 1)

        text = self.font_small.render(display_text, True, self.COLORS['text'])
        screen.blit(text, (rect.x + 5, rect.y + 4))

    def _render_pokemon_selector(self, screen):
        """Renderiza o seletor de Pokémon"""
        selector_rect = pygame.Rect(
            self.rect.x + 80,
            self.rect.y + 120,
            440,
            360
        )

        # Fundo
        pygame.draw.rect(screen, self.COLORS['bg_light'], selector_rect, border_radius=10)
        pygame.draw.rect(screen, self.COLORS['border'], selector_rect, 2, border_radius=10)

        # Título
        title = self.font_title.render("Selecionar Pokémon", True, self.COLORS['text'])
        screen.blit(title, (selector_rect.x + 10, selector_rect.y + 10))

        # Campo de busca
        search_rect = pygame.Rect(selector_rect.x + 10, selector_rect.y + 40, 250, 25)

        if self.active_input == "pokemon_search":
            border_color = self.COLORS['input_active']
            search_display = self.pokemon_search
        else:
            border_color = self.COLORS['input_border']
            search_display = self.pokemon_search if self.pokemon_search else "Buscar..."

        pygame.draw.rect(screen, self.COLORS['input_bg'], search_rect)
        pygame.draw.rect(screen, border_color, search_rect, 1)

        search_color = self.COLORS['text'] if self.pokemon_search else self.COLORS['text_dark']
        search_text = self.font_small.render(search_display, True, search_color)
        screen.blit(search_text, (search_rect.x + 5, search_rect.y + 5))

        # Contador
        count_text = self.font_small.render(f"{len(self.available_pokemon_ids)} disponíveis", True,
                                            self.COLORS['text_dark'])
        screen.blit(count_text, (selector_rect.x + 270, selector_rect.y + 45))

        # Área da lista
        list_area = pygame.Rect(selector_rect.x + 5, selector_rect.y + 75, selector_rect.width - 10, 240)
        pygame.draw.rect(screen, self.COLORS['bg_dark'], list_area)

        # Clipping
        old_clip = screen.get_clip()
        screen.set_clip(list_area)

        list_x = list_area.x + 5
        list_start_y = list_area.y + 2 - self.pokemon_selector_scroll * 35

        filtered_ids = self._filter_pokemon()

        for i, pokemon_id in enumerate(filtered_ids):
            item_y = list_start_y + i * 35

            if item_y + 35 < list_area.y or item_y > list_area.y + list_area.height:
                continue

            item_rect = pygame.Rect(list_x, item_y, list_area.width - 10, 31)

            # Fundo alternado
            bg_color = self.COLORS['bg_light'] if i % 2 == 0 else self.COLORS['bg']
            pygame.draw.rect(screen, bg_color, item_rect)

            # Sprite
            sprite = self._get_pokemon_sprite(pokemon_id, 24)
            screen.blit(sprite, (item_rect.x + 2, item_rect.y + 3))

            # ID e nome
            pokemon_name = self.pokedex.get_name(pokemon_id)
            text = self.font_small.render(f"#{pokemon_id:03d} {pokemon_name}", True, self.COLORS['text'])
            screen.blit(text, (item_rect.x + 30, item_rect.y + 8))

        screen.set_clip(old_clip)

        # Scroll info
        if len(filtered_ids) > 7:
            scroll_text = self.font_small.render(
                f"{self.pokemon_selector_scroll + 1}-{min(self.pokemon_selector_scroll + 7, len(filtered_ids))} de {len(filtered_ids)}",
                True, self.COLORS['text_dark']
            )
            screen.blit(scroll_text, (selector_rect.x + 10, selector_rect.bottom - 20))