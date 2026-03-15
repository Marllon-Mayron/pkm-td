# src/scenes/editor/components/wave_config_dialog.py

import pygame
from src.editor.wave_config import WaveEnemy


class WaveConfigDialog:
    """Diálogo para configurar waves de inimigos"""

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

        # Fontes
        self.font = pygame.font.Font(None, 20)
        self.font_small = pygame.font.Font(None, 16)
        self.font_title = pygame.font.Font(None, 24)
        self.font_large = pygame.font.Font(None, 28)

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
        self.max_waves_scroll = 0
        self.enemies_scroll = 0
        self.max_enemies_scroll = 0

        # Carrega lista completa de Pokémon da Pokedex
        self.available_pokemon_ids = self.pokedex.get_all_ids()
        print(f"Carregados {len(self.available_pokemon_ids)} Pokémon da Pokedex")

        # Cache de sprites InMap para performance
        self.sprite_cache = {}

        # Inicializa botões
        self._init_buttons()

    def _init_buttons(self):
        """Inicializa todos os botões com posições relativas"""
        x, y, w, h = self.rect

        # Botões gerais
        self.close_button = pygame.Rect(x + w - 30, y + 5, 25, 25)
        self.save_button = pygame.Rect(x + w - 180, y + h - 40, 80, 30)
        self.cancel_button = pygame.Rect(x + w - 90, y + h - 40, 80, 30)

        # Abas
        self.tab_buttons = []
        for i in range(3):
            self.tab_buttons.append(pygame.Rect(x + 10 + i * 100, y + 70, 90, 25))

        # Botões da aba Waves
        self.add_wave_button = pygame.Rect(x + 10, y + 100, 100, 30)
        self.remove_wave_button = pygame.Rect(x + 120, y + 100, 100, 30)

        # Botões da aba Composition
        self.add_enemy_button = pygame.Rect(x + 10, y + 440, 150, 30)
        self.equalize_button = pygame.Rect(x + 170, y + 440, 150, 30)

        # Botões da aba Settings
        self.path_prev_button = pygame.Rect(x + 250, y + 95, 30, 30)
        self.path_next_button = pygame.Rect(x + 290, y + 95, 30, 30)
        self.repeat_checkbox = pygame.Rect(x + 150, y + 305, 20, 20)
        self.repeat_minus_button = pygame.Rect(x + 300, y + 295, 30, 30)
        self.repeat_plus_button = pygame.Rect(x + 340, y + 295, 30, 30)

    def _get_pokemon_sprite(self, pokemon_id, size=48):
        """Obtém sprite do Pokémon em tamanho adequado """
        # Garante que pokemon_id é inteiro
        try:
            if isinstance(pokemon_id, str):
                if pokemon_id.isdigit():
                    pokemon_id = int(pokemon_id)
                else:
                    # Se for string não numérica, tenta buscar na Pokedex pelo nome
                    for pid in self.available_pokemon_ids:
                        if self.pokedex.get_name(pid).lower() == pokemon_id.lower():
                            pokemon_id = pid
                            break
                    else:
                        pokemon_id = 1  # fallback para Bulbasaur
            else:
                pokemon_id = int(pokemon_id)
        except (ValueError, TypeError):
            pokemon_id = 1

        cache_key = (pokemon_id, size)

        if cache_key in self.sprite_cache:
            return self.sprite_cache[cache_key]

        # Tenta obter o sprite InMap
        sprite = self.pokedex.get_sprite(pokemon_id, "inmap", direction="down", frame=0)

        if sprite and sprite.get_width() > 0:
            # Redimensiona se necessário
            if sprite.get_width() != size:
                sprite = pygame.transform.scale(sprite, (size, size))
        else:
            # Cria placeholder se não encontrar
            sprite = pygame.Surface((size, size), pygame.SRCALPHA)
            types = self.pokedex.get_types(pokemon_id)
            color = self.pokedex.get_type_color(types[0])
            pygame.draw.rect(sprite, color, (0, 0, size, size))
            pygame.draw.rect(sprite, (100, 100, 100), (0, 0, size, size), 2)

            # Primeira letra do nome
            name = self.pokedex.get_name(pokemon_id)
            font = pygame.font.Font(None, size // 2)
            text = font.render(name[0].upper() if name else "?", True, (255, 255, 255))
            text_rect = text.get_rect(center=(size // 2, size // 2))
            sprite.blit(text, text_rect)

        self.sprite_cache[cache_key] = sprite
        return sprite

    def _update_button_positions(self):
        """Atualiza posições dos botões após mover o diálogo"""
        x, y, w, h = self.rect

        # Botões gerais
        self.close_button.x = x + w - 30
        self.close_button.y = y + 5

        self.save_button.x = x + w - 180
        self.save_button.y = y + h - 40

        self.cancel_button.x = x + w - 90
        self.cancel_button.y = y + h - 40

        # Abas
        for i, button in enumerate(self.tab_buttons):
            button.x = x + 10 + i * 100
            button.y = y + 70

        # Botões da aba Waves
        self.add_wave_button.x = x + 10
        self.add_wave_button.y = y + 100

        self.remove_wave_button.x = x + 120
        self.remove_wave_button.y = y + 100

        # Botões da aba Composition
        self.add_enemy_button.x = x + 10
        self.add_enemy_button.y = y + 440

        self.equalize_button.x = x + 170
        self.equalize_button.y = y + 440

        # Botões da aba Settings
        self.path_prev_button.x = x + 250
        self.path_prev_button.y = y + 95

        self.path_next_button.x = x + 290
        self.path_next_button.y = y + 95

        self.repeat_checkbox.x = x + 150
        self.repeat_checkbox.y = y + 305

        self.repeat_minus_button.x = x + 300
        self.repeat_minus_button.y = y + 295

        self.repeat_plus_button.x = x + 340
        self.repeat_plus_button.y = y + 295

    def handle_event(self, event):
        """Processa eventos do diálogo - RETORNA True se consumiu o evento"""
        if not self.visible:
            return False

        mouse_pos = pygame.mouse.get_pos()
        mouse_x, mouse_y = mouse_pos

        # SEMPRE captura todos os eventos quando visível
        if event.type == pygame.MOUSEBUTTONDOWN:
            if not self.rect.collidepoint(mouse_x, mouse_y) and not self.showing_pokemon_selector:
                self.visible = False
                return True

        # Seletor de Pokémon aberto tem prioridade
        if self.showing_pokemon_selector:
            return self._handle_pokemon_selector_event(event, mouse_x, mouse_y)

        # Processa eventos baseado no tipo
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                return self._handle_left_click(mouse_x, mouse_y)
            elif event.button == 4:  # Scroll up
                return self._handle_scroll(-30)
            elif event.button == 5:  # Scroll down
                return self._handle_scroll(30)

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

        # Se clicou dentro do diálogo, consome o evento
        if self.rect.collidepoint(mouse_x, mouse_y):
            return True

        return False

    def _handle_left_click(self, mouse_x, mouse_y):
        """Processa clique esquerdo - RETORNA True se consumiu"""
        # Título para arrastar
        title_rect = pygame.Rect(self.rect.x, self.rect.y, self.rect.width, 30)
        if title_rect.collidepoint(mouse_x, mouse_y):
            self.dragging = True
            self.drag_offset_x = mouse_x - self.rect.x
            self.drag_offset_y = mouse_y - self.rect.y
            return True

        # Botão fechar
        if self.close_button.collidepoint(mouse_x, mouse_y):
            self.visible = False
            return True

        # Botões de ação (Salvar/Cancelar) - SEMPRE verificados primeiro
        if self.save_button.collidepoint(mouse_x, mouse_y):
            # Valida se total de % é 100 antes de salvar
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

        # Processa baseado na aba atual
        if self.selected_tab == "waves":
            return self._handle_waves_tab_click(mouse_x, mouse_y)
        elif self.selected_tab == "composition":
            return self._handle_composition_tab_click(mouse_x, mouse_y)
        elif self.selected_tab == "settings":
            return self._handle_settings_tab_click(mouse_x, mouse_y)

        return True

    def _handle_waves_tab_click(self, mouse_x, mouse_y):
        """Processa cliques na aba de waves"""
        # Botão adicionar wave
        if self.add_wave_button.collidepoint(mouse_x, mouse_y):
            self.wave_manager.add_wave()
            self.selected_wave_index = self.wave_manager.selected_wave
            self.enemies_scroll = 0
            # Limpa erros ao mudar de wave
            self.input_errors.pop("total", None)
            return True

        # Botão remover wave
        if self.remove_wave_button.collidepoint(mouse_x, mouse_y):
            if self.wave_manager.waves:
                self.wave_manager.remove_wave(self.selected_wave_index)
                self.selected_wave_index = self.wave_manager.selected_wave
                self.enemies_scroll = 0
                self.input_errors.pop("total", None)
            return True

        # Seleção de wave na lista
        list_x = self.rect.x + 10
        list_y = self.rect.y + 140 - self.waves_scroll

        for i, wave in enumerate(self.wave_manager.waves):
            wave_rect = pygame.Rect(list_x, list_y + i * 40, 220, 35)
            if wave_rect.collidepoint(mouse_x, mouse_y):
                self.selected_wave_index = i
                self.wave_manager.selected_wave = i
                self.enemies_scroll = 0  # Reset scroll ao mudar de wave
                self.input_errors.pop("total", None)  # Limpa erro ao mudar de wave
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
                # Pega o primeiro Pokémon disponível
                first_id = self.available_pokemon_ids[0] if self.available_pokemon_ids else 1
                wave.enemies.append(WaveEnemy(first_id, 0))
                # NÃO normaliza automaticamente - deixa o usuário definir os valores
                self.input_errors.pop("total", None)  # Remove erro anterior, se houver
            return True

        # Botão distribuir igualmente - ÚNICA forma de redistribuir
        if self.equalize_button.collidepoint(mouse_x, mouse_y) and wave.enemies:
            equal_percent = 100 // len(wave.enemies)
            remainder = 100 - (equal_percent * len(wave.enemies))
            for i, enemy in enumerate(wave.enemies):
                enemy.percentage = equal_percent + (1 if i < remainder else 0)
            self.input_errors.pop("total", None)  # Remove erro pois agora total = 100
            return True

        # Cliques em inimigos
        list_x = self.rect.x + 10
        list_y = self.rect.y + 130 - self.enemies_scroll

        for i, enemy in enumerate(wave.enemies):
            if i > 8:
                break

            # Área completa do inimigo
            enemy_rect = pygame.Rect(list_x, list_y + i * 70, self.rect.width - 30, 65)

            if enemy_rect.collidepoint(mouse_x, mouse_y):
                # Botão remover (X) - VERIFICADO PRIMEIRO
                remove_rect = pygame.Rect(enemy_rect.right - 30, enemy_rect.y + 5, 25, 25)
                if remove_rect.collidepoint(mouse_x, mouse_y):
                    del wave.enemies[i]
                    # NÃO normaliza automaticamente - apenas atualiza o erro se necessário
                    total = sum(e.percentage for e in wave.enemies)
                    if total != 100 and wave.enemies:
                        self.input_errors["total"] = f"Total deve ser 100% (atual: {total}%)"
                    elif not wave.enemies:
                        self.input_errors["total"] = "Adicione pelo menos um Pokémon"
                    else:
                        self.input_errors.pop("total", None)
                    return True

                # Área do Pokémon (para selecionar)
                pokemon_rect = pygame.Rect(enemy_rect.x + 5, enemy_rect.y + 5, 150, 55)
                if pokemon_rect.collidepoint(mouse_x, mouse_y):
                    self.showing_pokemon_selector = True
                    self.pokemon_selector_enemy_index = i
                    self.pokemon_selector_scroll = 0
                    self.pokemon_search = ""
                    return True

                # Campo de porcentagem
                percent_rect = pygame.Rect(enemy_rect.x + 180, enemy_rect.y + 20, 50, 25)
                if percent_rect.collidepoint(mouse_x, mouse_y):
                    self.active_input = f"percent_{i}"
                    self.input_texts[self.active_input] = str(enemy.percentage)
                    return True

        return True

    def _handle_settings_tab_click(self, mouse_x, mouse_y):
        """Processa cliques na aba de configurações"""
        wave = self.wave_manager.get_current_wave()
        if not wave:
            return True

        # Botões de path
        if self.path_prev_button.collidepoint(mouse_x, mouse_y):
            wave.path_index = max(0, wave.path_index - 1)
            return True

        if self.path_next_button.collidepoint(mouse_x, mouse_y):
            max_path = max(0, len(self.path_manager.paths) - 1)
            wave.path_index = min(max_path, wave.path_index + 1)
            return True

        # Checkbox repeat wave
        if self.repeat_checkbox.collidepoint(mouse_x, mouse_y):
            wave.repeat_wave = not wave.repeat_wave
            return True

        # Botões de repeat count (só se repeat estiver ativado)
        if wave.repeat_wave:
            if self.repeat_minus_button.collidepoint(mouse_x, mouse_y):
                wave.repeat_count = max(1, wave.repeat_count - 1)
                return True

            if self.repeat_plus_button.collidepoint(mouse_x, mouse_y):
                wave.repeat_count = min(10, wave.repeat_count + 1)
                return True

        # Campos de input
        input_fields = [
            ("wave_size", self.rect.x + 250, self.rect.y + 180, 80, 25),
            ("min_level", self.rect.x + 250, self.rect.y + 220, 80, 25),
            ("max_level", self.rect.x + 250, self.rect.y + 260, 80, 25),
            ("spawn_interval", self.rect.x + 250, self.rect.y + 340, 80, 25),
            ("initial_delay", self.rect.x + 250, self.rect.y + 380, 80, 25),
        ]

        for field_name, fx, fy, fw, fh in input_fields:
            field_rect = pygame.Rect(fx, fy, fw, fh)
            if field_rect.collidepoint(mouse_x, mouse_y):
                self.active_input = field_name
                current_value = getattr(wave, field_name)
                self.input_texts[field_name] = str(current_value)
                return True

        return True

    def _handle_pokemon_selector_event(self, event, mouse_x, mouse_y):
        """Processa eventos do seletor de Pokémon"""
        selector_rect = pygame.Rect(
            self.rect.x + 100,
            self.rect.y + 150,
            400,
            400
        )

        # Botões do seletor
        close_selector_rect = pygame.Rect(selector_rect.right - 30, selector_rect.y + 5, 25, 25)
        search_rect = pygame.Rect(selector_rect.x + 10, selector_rect.y + 40, 250, 30)

        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                # Clique fora do seletor - fecha
                if not selector_rect.collidepoint(mouse_x, mouse_y):
                    self.showing_pokemon_selector = False
                    return True

                # Botão fechar do seletor
                if close_selector_rect.collidepoint(mouse_x, mouse_y):
                    self.showing_pokemon_selector = False
                    return True

                # Campo de busca
                if search_rect.collidepoint(mouse_x, mouse_y):
                    self.active_input = "pokemon_search"
                    return True

                # Lista de Pokémon
                list_x = selector_rect.x + 10
                list_y = selector_rect.y + 80 - self.pokemon_selector_scroll

                filtered_ids = self._filter_pokemon()

                for i, pokemon_id in enumerate(filtered_ids):
                    pokemon_rect = pygame.Rect(
                        list_x,
                        list_y + i * 40,
                        380,
                        35
                    )

                    if pokemon_rect.collidepoint(mouse_x, mouse_y):
                        wave = self.wave_manager.get_current_wave()
                        if wave and self.pokemon_selector_enemy_index < len(wave.enemies):
                            wave.enemies[self.pokemon_selector_enemy_index].pokemon_id = int(pokemon_id)
                            # Limpa o cache do sprite para este Pokémon
                            cache_key = (pokemon_id, 48)
                            if cache_key in self.sprite_cache:
                                del self.sprite_cache[cache_key]
                            self.showing_pokemon_selector = False
                        return True

            elif event.button == 4:  # Scroll up
                self.pokemon_selector_scroll = max(0, self.pokemon_selector_scroll - 40)
                return True
            elif event.button == 5:  # Scroll down
                filtered_count = len(self._filter_pokemon())
                max_scroll = max(0, filtered_count * 40 - 320)
                self.pokemon_selector_scroll = min(max_scroll, self.pokemon_selector_scroll + 40)
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
        if not self.active_input:
            return False

        if event.key == pygame.K_RETURN:
            return self._apply_input()
        elif event.key == pygame.K_ESCAPE:
            self.active_input = None
            return True
        elif event.key == pygame.K_BACKSPACE:
            self.input_texts[self.active_input] = self.input_texts[self.active_input][:-1]
            return True
        elif event.unicode.isdigit() or event.unicode == '.':
            self.input_texts[self.active_input] += event.unicode
            return True

        return False

    def _apply_input(self):
        """Aplica o valor do input atual"""
        wave = self.wave_manager.get_current_wave()
        if not wave or not self.active_input:
            return False

        try:
            value = self.input_texts[self.active_input]

            # Campos de porcentagem dos inimigos
            if self.active_input.startswith("percent_"):
                index = int(self.active_input.split("_")[1])
                if 0 <= index < len(wave.enemies):
                    new_percent = int(float(value))
                    new_percent = max(0, min(100, new_percent))
                    wave.enemies[index].percentage = new_percent

                    # Verifica total - APENAS VALIDA, NÃO MODIFICA
                    total = sum(e.percentage for e in wave.enemies)
                    if total != 100:
                        self.input_errors["total"] = f"Total deve ser 100% (atual: {total}%)"
                    else:
                        self.input_errors.pop("total", None)

            # Campos de configuração da wave
            elif self.active_input == "wave_size":
                wave.wave_size = max(1, int(float(value)))
            elif self.active_input == "min_level":
                wave.min_level = max(1, int(float(value)))
            elif self.active_input == "max_level":
                wave.max_level = max(wave.min_level, int(float(value)))
            elif self.active_input == "spawn_interval":
                wave.spawn_interval = max(0.1, float(value))
            elif self.active_input == "initial_delay":
                wave.initial_delay = max(0, float(value))

            self.active_input = None
            return True

        except ValueError:
            self.active_input = None
            return False

    def _handle_scroll(self, delta):
        """Processa scroll do mouse"""
        if self.selected_tab == "waves":
            total_height = len(self.wave_manager.waves) * 40
            visible_height = self.rect.height - 200
            self.max_waves_scroll = max(0, total_height - visible_height)
            self.waves_scroll = max(0, min(self.max_waves_scroll, self.waves_scroll + delta))
            return True
        elif self.selected_tab == "composition":
            wave = self.wave_manager.get_current_wave()
            if wave:
                total_height = len(wave.enemies) * 70
                visible_height = 300
                self.max_enemies_scroll = max(0, total_height - visible_height)
                self.enemies_scroll = max(0, min(self.max_enemies_scroll, self.enemies_scroll + delta))
            return True
        return False

    def render(self, screen):
        """Renderiza o diálogo"""
        if not self.visible:
            return

        # Overlay mais escuro
        overlay = pygame.Surface((screen.get_width(), screen.get_height()))
        overlay.set_alpha(180)
        overlay.fill((0, 0, 0))
        screen.blit(overlay, (0, 0))

        # Fundo da janela
        pygame.draw.rect(screen, (40, 40, 50), self.rect, border_radius=10)
        pygame.draw.rect(screen, (255, 215, 0), self.rect, 2, border_radius=10)

        # Título
        title = self.font_title.render("Configuração de Waves", True, (255, 255, 255))
        screen.blit(title, (self.rect.x + 10, self.rect.y + 10))

        # Botão fechar
        pygame.draw.rect(screen, (80, 80, 90), self.close_button)
        pygame.draw.line(screen, (255, 255, 255),
                         (self.close_button.x + 5, self.close_button.y + 5),
                         (self.close_button.right - 5, self.close_button.bottom - 5), 2)
        pygame.draw.line(screen, (255, 255, 255),
                         (self.close_button.right - 5, self.close_button.y + 5),
                         (self.close_button.x + 5, self.close_button.bottom - 5), 2)

        # Abas
        tabs = [("waves", "Waves"), ("composition", "Composição"), ("settings", "Configurações")]
        for i, (tab_id, tab_name) in enumerate(tabs):
            tab_button = self.tab_buttons[i]

            if self.selected_tab == tab_id:
                color = (100, 150, 200)
                border = (255, 255, 255)
            else:
                color = (60, 60, 70)
                border = (100, 100, 100)

            pygame.draw.rect(screen, color, tab_button, border_radius=5)
            pygame.draw.rect(screen, border, tab_button, 1, border_radius=5)

            tab_text = self.font_small.render(tab_name, True, (255, 255, 255))
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

        # Botões de ação
        pygame.draw.rect(screen, (0, 150, 0), self.save_button, border_radius=5)
        pygame.draw.rect(screen, (255, 255, 255), self.save_button, 1, border_radius=5)
        save_text = self.font.render("Salvar", True, (255, 255, 255))
        save_x = self.save_button.x + (self.save_button.width - save_text.get_width()) // 2
        save_y = self.save_button.y + (self.save_button.height - save_text.get_height()) // 2
        screen.blit(save_text, (save_x, save_y))

        pygame.draw.rect(screen, (150, 0, 0), self.cancel_button, border_radius=5)
        pygame.draw.rect(screen, (255, 255, 255), self.cancel_button, 1, border_radius=5)
        cancel_text = self.font.render("Cancelar", True, (255, 255, 255))
        cancel_x = self.cancel_button.x + (self.cancel_button.width - cancel_text.get_width()) // 2
        cancel_y = self.cancel_button.y + (self.cancel_button.height - cancel_text.get_height()) // 2
        screen.blit(cancel_text, (cancel_x, cancel_y))

        # Mensagem de erro se houver
        if "total" in self.input_errors and self.selected_tab == "composition":
            error_text = self.font_small.render(self.input_errors["total"], True, (255, 100, 100))
            screen.blit(error_text, (self.save_button.x - 200, self.save_button.y + 5))

    def _render_waves_tab(self, screen):
        """Renderiza a aba de lista de waves"""
        # Botões de ação
        pygame.draw.rect(screen, (0, 100, 0), self.add_wave_button, border_radius=5)
        add_text = self.font_small.render("+ Nova Wave", True, (255, 255, 255))
        screen.blit(add_text, (self.add_wave_button.x + 5, self.add_wave_button.y + 7))

        pygame.draw.rect(screen, (100, 0, 0), self.remove_wave_button, border_radius=5)
        remove_text = self.font_small.render("- Remover", True, (255, 255, 255))
        screen.blit(remove_text, (self.remove_wave_button.x + 5, self.remove_wave_button.y + 7))

        # Lista de waves
        list_x = self.rect.x + 10
        list_y = self.rect.y + 140 - self.waves_scroll

        # Área de clipping
        clip_rect = pygame.Rect(
            self.rect.x + 5,
            self.rect.y + 140,
            240,
            self.rect.height - 200
        )
        old_clip = screen.get_clip()
        screen.set_clip(clip_rect)

        for i, wave in enumerate(self.wave_manager.waves):
            wave_rect = pygame.Rect(list_x, list_y + i * 40, 220, 35)

            # Verifica visibilidade
            if wave_rect.bottom < clip_rect.top or wave_rect.top > clip_rect.bottom:
                continue

            # Fundo
            if i == self.selected_wave_index:
                color = (80, 100, 120)
                border = (255, 215, 0)
            else:
                color = (60, 60, 70)
                border = (80, 80, 90)

            pygame.draw.rect(screen, color, wave_rect, border_radius=5)
            pygame.draw.rect(screen, border, wave_rect, 1, border_radius=5)

            # Nome da wave
            wave_name = f"{wave.name} (P{wave.path_index + 1})"
            if not wave.enabled:
                wave_name = f"[X] {wave_name}"

            name_text = self.font_small.render(wave_name, True, (255, 255, 255))
            screen.blit(name_text, (wave_rect.x + 5, wave_rect.y + 10))

            # Quantidade de inimigos
            count_text = self.font_small.render(f"{wave.wave_size}", True, (200, 200, 200))
            screen.blit(count_text, (wave_rect.right - 25, wave_rect.y + 10))

        screen.set_clip(old_clip)

        # Informações detalhadas da wave selecionada
        if self.wave_manager.waves and self.selected_wave_index < len(self.wave_manager.waves):
            wave = self.wave_manager.waves[self.selected_wave_index]
            info_x = self.rect.x + 260
            info_y = self.rect.y + 140

            info_lines = [
                f"Path: {wave.path_index + 1}",
                f"Tamanho: {wave.wave_size} inimigos",
                f"Nível: {wave.min_level}-{wave.max_level}",
                f"Intervalo: {wave.spawn_interval}s",
                f"Delay: {wave.initial_delay}s",
                f"Repetição: {wave.repeat_count if wave.repeat_wave else 'Não'}",
                f"Composição: {len(wave.enemies)} tipos"
            ]

            for j, line in enumerate(info_lines):
                line_surf = self.font_small.render(line, True, (220, 220, 220))
                screen.blit(line_surf, (info_x, info_y + j * 20))

    def _render_composition_tab(self, screen):
        """Renderiza a aba de composição da wave"""
        wave = self.wave_manager.get_current_wave()
        if not wave:
            no_wave_text = self.font.render("Selecione uma wave na aba 'Waves'", True, (200, 200, 200))
            text_x = self.rect.x + (self.rect.width - no_wave_text.get_width()) // 2
            text_y = self.rect.y + (self.rect.height - no_wave_text.get_height()) // 2
            screen.blit(no_wave_text, (text_x, text_y))
            return

        # Título da wave
        title = self.font.render(f"Composição: {wave.name}", True, (255, 255, 255))
        screen.blit(title, (self.rect.x + 10, self.rect.y + 100))

        # Lista de inimigos
        list_x = self.rect.x + 10
        list_y = self.rect.y + 130 - self.enemies_scroll

        # Área de clipping
        clip_rect = pygame.Rect(
            self.rect.x + 5,
            self.rect.y + 130,
            self.rect.width - 20,
            300
        )
        old_clip = screen.get_clip()
        screen.set_clip(clip_rect)

        for i, enemy in enumerate(wave.enemies):
            enemy_rect = pygame.Rect(list_x, list_y + i * 70, self.rect.width - 30, 65)

            # Verifica visibilidade
            if enemy_rect.bottom < clip_rect.top or enemy_rect.top > clip_rect.bottom:
                continue

            # Fundo
            if i % 2 == 0:
                bg_color = (60, 60, 70)
            else:
                bg_color = (55, 55, 65)

            pygame.draw.rect(screen, bg_color, enemy_rect, border_radius=5)
            pygame.draw.rect(screen, (80, 80, 90), enemy_rect, 1, border_radius=5)

            # SPRITE DO POKÉMON - InMap em vez de círculo colorido
            pokemon_id = enemy.pokemon_id
            pokemon_name = self.pokedex.get_name(pokemon_id)
            types = self.pokedex.get_types(pokemon_id)

            # Obtém e desenha o sprite InMap (48x48)
            sprite = self._get_pokemon_sprite(pokemon_id, 48)
            screen.blit(sprite, (enemy_rect.x + 5, enemy_rect.y + 5))

            # Nome e tipos - ajustado posição por causa do sprite maior
            name_text = self.font.render(pokemon_name, True, (255, 255, 255))
            screen.blit(name_text, (enemy_rect.x + 60, enemy_rect.y + 10))

            types_text = self.font_small.render("/".join(types), True, (200, 200, 200))
            screen.blit(types_text, (enemy_rect.x + 60, enemy_rect.y + 30))

            # Botão remover (X)
            remove_rect = pygame.Rect(enemy_rect.right - 30, enemy_rect.y + 5, 25, 25)
            pygame.draw.rect(screen, (150, 50, 50), remove_rect)
            pygame.draw.line(screen, (255, 255, 255),
                             (remove_rect.x + 5, remove_rect.y + 5),
                             (remove_rect.right - 5, remove_rect.bottom - 5), 2)
            pygame.draw.line(screen, (255, 255, 255),
                             (remove_rect.right - 5, remove_rect.y + 5),
                             (remove_rect.x + 5, remove_rect.bottom - 5), 2)

            # Campo de porcentagem
            percent_label = self.font_small.render("%", True, (200, 200, 200))
            screen.blit(percent_label, (enemy_rect.x + 185, enemy_rect.y + 28))

            percent_rect = pygame.Rect(enemy_rect.x + 180, enemy_rect.y + 20, 50, 25)

            if self.active_input == f"percent_{i}":
                color = (100, 150, 255)
                display_text = self.input_texts.get(f"percent_{i}", str(enemy.percentage))
            else:
                color = (80, 80, 90)
                display_text = str(enemy.percentage)

            pygame.draw.rect(screen, color, percent_rect, 2)
            percent_text = self.font_small.render(display_text, True, (255, 255, 255))
            screen.blit(percent_text, (percent_rect.x + 5, percent_rect.y + 5))

        screen.set_clip(old_clip)

        # Totalizador e botões de ação
        total_y = self.rect.y + 440

        # Total de porcentagem
        total = sum(e.percentage for e in wave.enemies)
        total_color = (100, 255, 100) if total == 100 else (255, 100, 100)
        total_text = self.font_large.render(f"Total: {total}%", True, total_color)
        screen.blit(total_text, (self.rect.x + 10, total_y))

        # Botões
        pygame.draw.rect(screen, (0, 100, 0), self.add_enemy_button, border_radius=5)
        add_text = self.font_small.render("+ Adicionar Pokémon", True, (255, 255, 255))
        screen.blit(add_text, (self.add_enemy_button.x + 5, self.add_enemy_button.y + 7))

        if wave.enemies:
            pygame.draw.rect(screen, (100, 100, 0), self.equalize_button, border_radius=5)
            equalize_text = self.font_small.render("Distribuir Igual", True, (255, 255, 255))
            screen.blit(equalize_text, (self.equalize_button.x + 5, self.equalize_button.y + 7))

    def _render_settings_tab(self, screen):
        """Renderiza a aba de configurações"""
        wave = self.wave_manager.get_current_wave()
        if not wave:
            no_wave_text = self.font.render("Selecione uma wave na aba 'Waves'", True, (200, 200, 200))
            text_x = self.rect.x + (self.rect.width - no_wave_text.get_width()) // 2
            text_y = self.rect.y + (self.rect.height - no_wave_text.get_height()) // 2
            screen.blit(no_wave_text, (text_x, text_y))
            return

        y_offset = 100

        # Path
        label = self.font.render("Path:", True, (200, 200, 200))
        screen.blit(label, (self.rect.x + 20, self.rect.y + y_offset))

        path_text = self.font.render(f"Path {wave.path_index + 1}", True, (255, 255, 255))
        screen.blit(path_text, (self.rect.x + 150, self.rect.y + y_offset))

        # Botões path
        pygame.draw.rect(screen, (80, 80, 90), self.path_prev_button)
        pygame.draw.rect(screen, (80, 80, 90), self.path_next_button)

        prev_text = self.font.render("<", True, (255, 255, 255))
        next_text = self.font.render(">", True, (255, 255, 255))
        screen.blit(prev_text, (self.path_prev_button.x + 10, self.path_prev_button.y + 5))
        screen.blit(next_text, (self.path_next_button.x + 10, self.path_next_button.y + 5))

        y_offset += 40

        # Nome da wave
        label = self.font.render("Nome:", True, (200, 200, 200))
        screen.blit(label, (self.rect.x + 20, self.rect.y + y_offset))

        name_rect = pygame.Rect(self.rect.x + 150, self.rect.y + y_offset - 5, 200, 30)
        pygame.draw.rect(screen, (80, 80, 90), name_rect, 2)
        name_text = self.font.render(wave.name, True, (255, 255, 255))
        screen.blit(name_text, (name_rect.x + 5, name_rect.y + 5))

        y_offset += 40

        # Campos numéricos
        fields = [
            ("Tamanho da Wave:", "wave_size", wave.wave_size),
            ("Nível Mínimo:", "min_level", wave.min_level),
            ("Nível Máximo:", "max_level", wave.max_level),
            ("Intervalo (s):", "spawn_interval", wave.spawn_interval),
            ("Delay Inicial (s):", "initial_delay", wave.initial_delay),
        ]

        for label_text, field_name, value in fields:
            label = self.font.render(label_text, True, (200, 200, 200))
            screen.blit(label, (self.rect.x + 20, self.rect.y + y_offset))

            input_rect = pygame.Rect(self.rect.x + 250, self.rect.y + y_offset - 5, 80, 30)

            if self.active_input == field_name:
                color = (100, 150, 255)
                display_text = self.input_texts.get(field_name, str(value))
            else:
                color = (80, 80, 90)
                display_text = str(value)

            pygame.draw.rect(screen, color, input_rect, 2)

            text_surf = self.font.render(display_text, True, (255, 255, 255))
            screen.blit(text_surf, (input_rect.x + 5, input_rect.y + 5))

            y_offset += 40

        # Repeat wave
        label = self.font.render("Repetir Wave:", True, (200, 200, 200))
        screen.blit(label, (self.rect.x + 20, self.rect.y + y_offset))

        # Checkbox
        if wave.repeat_wave:
            pygame.draw.rect(screen, (0, 200, 0), self.repeat_checkbox)
            check_text = self.font.render("✓", True, (255, 255, 255))
            screen.blit(check_text, (self.repeat_checkbox.x + 2, self.repeat_checkbox.y - 2))
        else:
            pygame.draw.rect(screen, (80, 80, 90), self.repeat_checkbox, 2)

        pygame.draw.rect(screen, (100, 100, 100), self.repeat_checkbox, 1)

        if wave.repeat_wave:
            count_text = self.font.render(f"Vezes: {wave.repeat_count}", True, (255, 255, 255))
            screen.blit(count_text, (self.rect.x + 200, self.rect.y + y_offset))

            # Botões +/-
            pygame.draw.rect(screen, (80, 80, 90), self.repeat_minus_button)
            pygame.draw.rect(screen, (80, 80, 90), self.repeat_plus_button)

            minus_text = self.font.render("-", True, (255, 255, 255))
            plus_text = self.font.render("+", True, (255, 255, 255))
            screen.blit(minus_text, (self.repeat_minus_button.x + 10, self.repeat_minus_button.y + 5))
            screen.blit(plus_text, (self.repeat_plus_button.x + 10, self.repeat_plus_button.y + 5))

    def _render_pokemon_selector(self, screen):
        """Renderiza o seletor de Pokémon"""
        selector_rect = pygame.Rect(
            self.rect.x + 100,
            self.rect.y + 150,
            400,
            400
        )

        # Fundo
        pygame.draw.rect(screen, (50, 50, 60), selector_rect, border_radius=10)
        pygame.draw.rect(screen, (255, 215, 0), selector_rect, 2, border_radius=10)

        # Título
        title = self.font_title.render("Selecionar Pokémon", True, (255, 255, 255))
        screen.blit(title, (selector_rect.x + 10, selector_rect.y + 10))

        # Botão fechar do seletor
        close_selector_rect = pygame.Rect(selector_rect.right - 30, selector_rect.y + 5, 25, 25)
        pygame.draw.rect(screen, (150, 50, 50), close_selector_rect)
        pygame.draw.line(screen, (255, 255, 255),
                         (close_selector_rect.x + 5, close_selector_rect.y + 5),
                         (close_selector_rect.right - 5, close_selector_rect.bottom - 5), 2)
        pygame.draw.line(screen, (255, 255, 255),
                         (close_selector_rect.right - 5, close_selector_rect.y + 5),
                         (close_selector_rect.x + 5, close_selector_rect.bottom - 5), 2)

        # Campo de busca
        search_rect = pygame.Rect(selector_rect.x + 10, selector_rect.y + 40, 250, 30)

        if self.active_input == "pokemon_search":
            color = (100, 150, 255)
        else:
            color = (80, 80, 90)

        pygame.draw.rect(screen, color, search_rect, 2)

        search_display = self.pokemon_search
        if not search_display and self.active_input != "pokemon_search":
            search_display = "Buscar Pokémon..."
            search_color = (150, 150, 150)
        else:
            search_color = (255, 255, 255)

        search_text = self.font_small.render(search_display, True, search_color)
        screen.blit(search_text, (search_rect.x + 5, search_rect.y + 7))

        # Instrução
        info_text = self.font_small.render(f"{len(self.available_pokemon_ids)} Pokémon disponíveis", True,
                                           (200, 200, 200))
        screen.blit(info_text, (selector_rect.x + 270, selector_rect.y + 47))

        # Lista de Pokémon
        list_x = selector_rect.x + 10
        list_y = selector_rect.y + 80 - self.pokemon_selector_scroll

        # Área de clipping
        clip_rect = pygame.Rect(
            selector_rect.x + 5,
            selector_rect.y + 75,
            selector_rect.width - 10,
            selector_rect.height - 80
        )
        old_clip = screen.get_clip()
        screen.set_clip(clip_rect)

        filtered_ids = self._filter_pokemon()

        for i, pokemon_id in enumerate(filtered_ids):
            pokemon_rect = pygame.Rect(
                list_x,
                list_y + i * 40,
                380,
                35
            )

            # Verifica visibilidade
            if pokemon_rect.bottom < clip_rect.top or pokemon_rect.top > clip_rect.bottom:
                continue

            # Fundo
            if i % 2 == 0:
                bg_color = (60, 60, 70)
            else:
                bg_color = (55, 55, 65)

            pygame.draw.rect(screen, bg_color, pokemon_rect)

            # SPRITE DO POKÉMON NO SELETOR
            sprite = self._get_pokemon_sprite(pokemon_id, 32)
            screen.blit(sprite, (pokemon_rect.x + 5, pokemon_rect.y + 2))

            # ID e nome
            pokemon_name = self.pokedex.get_name(pokemon_id)
            text = self.font_small.render(f"#{pokemon_id:03d} {pokemon_name}", True, (255, 255, 255))
            screen.blit(text, (pokemon_rect.x + 45, pokemon_rect.y + 8))

            # Tipos (mini indicador)
            types = self.pokedex.get_types(pokemon_id)
            type_color = self.pokedex.get_type_color(types[0])
            pygame.draw.circle(screen, type_color, (pokemon_rect.x + 350, pokemon_rect.y + 15), 5)

        screen.set_clip(old_clip)

        # Scroll info
        if len(filtered_ids) > 10:
            scroll_text = self.font_small.render("Use scroll do mouse para ver mais", True, (150, 150, 150))
            screen.blit(scroll_text, (selector_rect.x + 10, selector_rect.bottom - 25))