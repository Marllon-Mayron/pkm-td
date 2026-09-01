# src/scenes/editor/components/wave_config_dialog.py

import pygame
import random
from src.editor.wave_config import WaveEnemy, WaveTemplate, WaveVariant, WaveTemplateManager


class WaveConfigDialog:
    """Diálogo para configurar waves de inimigos"""

    def __init__(self, x, y, width, height, wave_manager, path_manager, pokedex):
        # Dimensões do diálogo
        self.rect = pygame.Rect(x, y, max(width, 820), max(height, 640))
        self.visible = True
        self.wave_manager = wave_manager
        self.path_manager = path_manager
        self.pokedex = pokedex

        self.margin = 20
        self.selected_wave_index = wave_manager.selected_wave
        self.selected_tab = "waves"
        self.dragging = False
        self.drag_offset_x = 0
        self.drag_offset_y = 0
        self.hovered_button = None

        self.active_input = None
        self.input_texts = {}
        self.input_errors = {}

        # Opções de template
        self.template_options = []
        self.template_selected_index = 0
        self.template_dropdown_open = False
        self.template_hovered_index = -1

        # Opções de condição (período)
        self.condition_options = [
            {"id": "any", "label": "Qualquer"},
            {"id": "day", "label": "Dia"},
            {"id": "night", "label": "Noite"},
            {"id": "dusk", "label": "Entardecer"},
            {"id": "dawn", "label": "Amanhecer"},
            {"id": "cave", "label": "Caverna"},
            {"id": "deep", "label": "Fundo do Mar"},
        ]
        self.condition_selected_index = 0
        self.condition_dropdown_open = False
        self.condition_hovered_index = -1

        # Editores
        self.template_editor_open = False
        self.editing_template_id = None

        self.selected_variant_index = -1
        self.variant_editor_open = False
        self.editing_variant_index = -1

        # ===== SELETOR DE POKÉMON =====
        self.showing_pokemon_selector = False
        self.pokemon_selector_target = None  # "enemy", "variant", "template"
        self.pokemon_selector_index = 0  # índice do inimigo na lista
        self.pokemon_selector_scroll = 0
        self.pokemon_search = ""

        # Controles de arraste para scroll
        self.pokemon_dragging_scroll = False
        self.pokemon_drag_start_y = 0
        self.pokemon_drag_start_scroll = 0

        # Scroll na barra (arraste do thumb)
        self.pokemon_dragging_thumb = False
        self.pokemon_thumb_start_y = 0
        self.pokemon_thumb_start_scroll = 0

        # ===== SELETOR DE PATH =====
        self.path_dropdown_open = False
        self.path_hovered_index = -1
        self.path_selected_index = 0

        # ===== SELETOR DE TEMPLATE (na aba composição) =====
        self.template_combo_open = False
        self.template_combo_hovered_index = -1
        self.template_combo_selected_index = 0

        # ===== SELETOR DE TEMPLATE NA VARIANT =====
        self.variant_template_combo_open = False
        self.variant_template_hovered_index = -1
        self.variant_template_rect = None
        self.variant_clear_template_rect = None
        self.variant_add_rect = None
        self.variant_equalize_rect = None
        self.variant_clear_enemies_rect = None

        # Scroll
        self.waves_scroll = 0
        self.enemies_scroll = 0
        self.variants_scroll = 0
        self.templates_scroll = 0

        self.waves_per_page = 5
        self.wave_item_height = 32
        self.enemies_per_page = 4
        self.enemy_item_height = 56
        self.variants_per_page = 3
        self.variant_item_height = 65
        self.templates_per_page = 3
        self.template_item_height = 55

        self.available_pokemon_ids = self.pokedex.get_all_ids()
        self.sprite_cache = {}
        self._font_cache = {}

        # Paleta de cores
        self.colors = {
            'bg': (30, 33, 42),
            'bg_light': (40, 44, 55),
            'bg_dark': (25, 28, 36),
            'bg_input': (45, 49, 60),
            'bg_dropdown': (35, 39, 50),
            'bg_dropdown_hover': (50, 55, 70),
            'border': (60, 65, 80),
            'border_light': (75, 80, 95),
            'border_active': (100, 160, 255),
            'border_dropdown': (70, 75, 90),
            'text': (235, 238, 245),
            'text_dim': (180, 185, 200),
            'text_muted': (120, 125, 145),
            'title': (255, 215, 0),
            'accent': (70, 110, 190),
            'success': (70, 190, 70),
            'danger': (210, 70, 70),
            'warning': (210, 180, 70),
            'info': (70, 160, 210),
            'radio_selected': (100, 160, 255),
            'radio_unselected': (70, 75, 90),
            'dropdown_item_hover': (55, 60, 80),
            'tab_active': (70, 110, 190),
            'tab_inactive': (40, 44, 55),
            'separator': (50, 55, 70),
            'editor_bg': (20, 22, 30, 200),
            'scrollbar_bg': (50, 50, 60),
            'scrollbar_thumb': (100, 150, 255),
            'selector_bg': (25, 28, 36, 230),
        }

        self._sync_template_dropdown()
        self._sync_path_dropdown()
        self._calculate_positions()
        self._update_template_options()

    # --- Fontes ---
    def _get_font(self, size, bold=False):
        key = (size, bold)
        if key not in self._font_cache:
            font = pygame.font.Font(None, size)
            if bold:
                font.set_bold(True)
            self._font_cache[key] = font
        return self._font_cache[key]

    # --- Sincronização ---
    def _sync_template_dropdown(self):
        wave = self.wave_manager.get_current_wave()
        if wave and wave.template_id:
            templates = WaveTemplateManager.get_all_templates()
            for i, t in enumerate(templates):
                if t.template_id == wave.template_id:
                    self.template_selected_index = i + 1
                    return
        self.template_selected_index = 0

        # Sincroniza o path também
        self._sync_path_dropdown()

    def _sync_path_dropdown(self):
        """Sincroniza o dropdown de path com a wave atual"""
        wave = self.wave_manager.get_current_wave()
        if not wave:
            self.path_selected_index = 0
            return

        path_count = len(self.path_manager.paths)
        if path_count == 0:
            self.path_selected_index = 0
            return

        # Encontra o índice do path atual
        current_path_idx = wave.path_index if hasattr(wave, 'path_index') else 0
        self.path_selected_index = max(0, min(current_path_idx, path_count - 1))

    def _update_template_options(self):
        self.template_options = [{"id": None, "label": "Nenhum"}]
        for t in WaveTemplateManager.get_all_templates():
            self.template_options.append({"id": t.template_id, "label": t.name})

    # --- Cálculo de posições ---
    def _calculate_positions(self):
        x, y, w, h = self.rect
        m = self.margin
        content_top = y + 50

        # Abas
        tab_width = 105
        tab_spacing = 6
        tabs_total_width = (tab_width * 4) + (tab_spacing * 3)
        tabs_start_x = x + (w - tabs_total_width) // 2
        self.tab_buttons = []
        tab_names = ["Waves", "Composicao", "Variants", "Templates"]
        for i, name in enumerate(tab_names):
            self.tab_buttons.append(pygame.Rect(
                tabs_start_x + i * (tab_width + tab_spacing),
                y + 45,
                tab_width,
                30
            ))

        # Botões Salvar/Cancelar
        button_width = 95
        button_height = 32
        total_buttons_width = button_width * 2 + 15
        button_x = x + (w - total_buttons_width) // 2
        button_y = y + h - 55
        self.save_button = pygame.Rect(button_x, button_y, button_width, button_height)
        self.cancel_button = pygame.Rect(button_x + button_width + 15, button_y, button_width, button_height)

        # ===== WAVES TAB =====
        waves_y = content_top + 10
        self.waves_label = pygame.Rect(x + m, waves_y, 120, 22)

        btn_y = waves_y + 28
        self.add_wave_button = pygame.Rect(x + m, btn_y, 85, 26)
        self.remove_wave_button = pygame.Rect(x + m + 95, btn_y, 85, 26)
        self.duplicate_wave_button = pygame.Rect(x + m + 190, btn_y, 95, 26)

        # Seletor de Path (ao lado do botão Duplicar)
        self.path_label = pygame.Rect(x + m + 295, btn_y + 2, 35, 22)
        self.path_selector_rect = pygame.Rect(x + m + 330, btn_y, 140, 26)

        list_y = btn_y + 34
        self.waves_list_area = pygame.Rect(
            x + m,
            list_y,
            w - m * 2,
            self.waves_per_page * self.wave_item_height + 4
        )

        # ===== COMPOSITION TAB =====
        comp_y = content_top + 10
        self.comp_info_rect = pygame.Rect(x + m, comp_y, w - m * 2, 22)

        btn_y = comp_y + 28
        self.add_enemy_button = pygame.Rect(x + m, btn_y, 130, 26)
        self.equalize_button = pygame.Rect(x + m + 140, btn_y, 110, 26)
        self.clear_enemies_button = pygame.Rect(x + m + 260, btn_y, 95, 26)

        # Seletor de Template (ao lado do botão Limpar)
        self.template_label = pygame.Rect(x + m + 365, btn_y + 2, 60, 22)
        self.template_selector_rect = pygame.Rect(x + m + 425, btn_y, 150, 26)
        self.clear_template_rect = pygame.Rect(x + m + 585, btn_y, 70, 26)

        list_y = btn_y + 34
        self.enemies_list_area = pygame.Rect(
            x + m,
            list_y,
            w - m * 2,
            self.enemies_per_page * self.enemy_item_height + 4
        )
        self.total_rect = pygame.Rect(x + m, self.enemies_list_area.bottom + 6, 200, 22)

        # ===== VARIANTS TAB =====
        var_y = content_top + 10
        self.variant_info_rect = pygame.Rect(x + m, var_y, w - m * 2, 28)
        btn_y = var_y + 34
        self.add_variant_button = pygame.Rect(x + m, btn_y, 120, 26)
        self.remove_variant_button = pygame.Rect(x + m + 130, btn_y, 95, 26)
        self.edit_variant_button = pygame.Rect(x + m + 235, btn_y, 110, 26)
        list_y = btn_y + 34
        self.variants_list_area = pygame.Rect(
            x + m,
            list_y,
            w - m * 2,
            self.variants_per_page * self.variant_item_height + 4
        )

        # ===== TEMPLATES TAB =====
        temp_y = content_top + 10
        self.template_info_rect = pygame.Rect(x + m, temp_y, w - m * 2, 28)
        btn_y = temp_y + 34
        self.new_template_button = pygame.Rect(x + m, btn_y, 130, 26)
        self.delete_template_button = pygame.Rect(x + m + 140, btn_y, 95, 26)
        self.edit_template_button = pygame.Rect(x + m + 245, btn_y, 110, 26)

        # Botões do editor de templates (quando aberto)
        self.template_editor_equalize_rect = pygame.Rect(x + m + 365, btn_y, 110, 26)
        self.template_editor_clear_rect = pygame.Rect(x + m + 485, btn_y, 95, 26)

        list_y = btn_y + 34
        self.templates_list_area = pygame.Rect(
            x + m,
            list_y,
            w - m * 2,
            self.templates_per_page * self.template_item_height + 4
        )

        # ===== VARIANT EDITOR (posições internas) =====
        # Estas posições serão usadas dentro do editor de variant
        self.variant_editor_template_label = None
        self.variant_editor_template_selector = None
        self.variant_editor_clear_template = None

    def _update_button_positions(self):
        self._calculate_positions()
        self._sync_path_dropdown()

    # --- Sprites de Pokémon ---
    def _get_pokemon_sprite(self, pokemon_id, size=32):
        try:
            pokemon_id = int(pokemon_id)
        except:
            pokemon_id = 1

        cache_key = (pokemon_id, size)
        if cache_key in self.sprite_cache:
            return self.sprite_cache[cache_key]

        sprite = None
        try:
            portrait = self.pokedex.get_portrait(pokemon_id, "normal", shiny=False)
            if portrait:
                sprite = portrait
        except:
            pass

        if sprite is None:
            try:
                inmap = self.pokedex.get_inmap_animation(pokemon_id, shiny=False)
                if inmap and "down" in inmap and inmap["down"]:
                    sprite = inmap["down"][0]
            except:
                pass

        if sprite is None:
            try:
                sprite = self.pokedex.get_sprite(pokemon_id, "front", shiny=False)
            except:
                pass

        if sprite is None:
            sprite = self._create_placeholder(pokemon_id, size)

        orig_w, orig_h = sprite.get_width(), sprite.get_height()
        if orig_w > orig_h:
            target_w, target_h = size, int(orig_h * (size / orig_w))
        else:
            target_h, target_w = size, int(orig_w * (size / orig_h))

        if target_w > 0 and target_h > 0:
            scaled = pygame.transform.smoothscale(sprite, (target_w, target_h))
            final = pygame.Surface((size, size), pygame.SRCALPHA)
            final.fill((0, 0, 0, 0))
            final.blit(scaled, ((size - target_w) // 2, (size - target_h) // 2))
            sprite = final

        self.sprite_cache[cache_key] = sprite
        return sprite

    def _create_placeholder(self, pokemon_id, size):
        placeholder = pygame.Surface((size, size), pygame.SRCALPHA)
        colors = [(255, 99, 71), (135, 206, 235), (144, 238, 144), (255, 215, 0)]
        color = colors[pokemon_id % len(colors)]
        pygame.draw.rect(placeholder, color, (0, 0, size, size), border_radius=8)
        pygame.draw.rect(placeholder, (100, 100, 100), (0, 0, size, size), 2, border_radius=8)
        return placeholder

    # --- Eventos principais ---
    def handle_event(self, event):
        if not self.visible:
            return False

        mouse_pos = pygame.mouse.get_pos()
        mouse_x, mouse_y = mouse_pos

        # Prioridade 1: Seletor de Pokémon (consome TODOS os eventos)
        if self.showing_pokemon_selector:
            self._handle_pokemon_selector_event(event, mouse_x, mouse_y)
            return True  # Evento sempre consumido

        # Prioridade 2: Editores abertos
        if self.variant_editor_open:
            result = self._handle_variant_editor_event(event, mouse_x, mouse_y)
            if result is not None:
                return result

        if self.template_editor_open:
            result = self._handle_template_editor_event(event, mouse_x, mouse_y)
            if result is not None:
                return result

        # Eventos gerais
        if event.type == pygame.MOUSEMOTION:
            self._update_hover(mouse_x, mouse_y)

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if not self.rect.collidepoint(mouse_x, mouse_y):
                self.visible = False
                return True

            # Arrastar pela barra de título
            title_rect = pygame.Rect(self.rect.x, self.rect.y, self.rect.width, 30)
            if title_rect.collidepoint(mouse_x, mouse_y):
                self.dragging = True
                self.drag_offset_x = mouse_x - self.rect.x
                self.drag_offset_y = mouse_y - self.rect.y
                return True

            if self.save_button.collidepoint(mouse_x, mouse_y):
                self.visible = False
                return "saved"
            if self.cancel_button.collidepoint(mouse_x, mouse_y):
                self.visible = False
                return True

            # Abas
            for i, tab_button in enumerate(self.tab_buttons):
                if tab_button.collidepoint(mouse_x, mouse_y):
                    tabs = ["waves", "composition", "variants", "templates"]
                    self.selected_tab = tabs[i]
                    self.variant_editor_open = False
                    self.template_editor_open = False
                    self.condition_dropdown_open = False
                    return True

            # Clique na aba atual
            if self.selected_tab == "waves":
                return self._handle_waves_tab_click(mouse_x, mouse_y)
            elif self.selected_tab == "composition":
                return self._handle_composition_tab_click(mouse_x, mouse_y)
            elif self.selected_tab == "variants":
                return self._handle_variants_tab_click(mouse_x, mouse_y)
            elif self.selected_tab == "templates":
                return self._handle_templates_tab_click(mouse_x, mouse_y)

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button in (4, 5):
            direction = -1 if event.button == 4 else 1
            return self._handle_scroll(direction)

        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.dragging = False
            return True

        elif event.type == pygame.MOUSEMOTION and self.dragging:
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
        buttons = [
            (self.save_button, "save"),
            (self.cancel_button, "cancel"),
            (self.add_wave_button, "add_wave"),
            (self.remove_wave_button, "remove_wave"),
            (self.duplicate_wave_button, "duplicate_wave"),
            (self.add_enemy_button, "add_enemy"),
            (self.equalize_button, "equalize"),
            (self.clear_enemies_button, "clear_enemies"),
            (self.add_variant_button, "add_variant"),
            (self.remove_variant_button, "remove_variant"),
            (self.edit_variant_button, "edit_variant"),
            (self.new_template_button, "new_template"),
            (self.delete_template_button, "delete_template"),
            (self.edit_template_button, "edit_template"),
            (self.clear_template_rect, "clear_template"),
        ]

        # Botões do editor de templates (se estiver aberto)
        if self.template_editor_open:
            editor_rect = pygame.Rect(
                self.rect.x + 50,
                self.rect.y + 100,
                self.rect.width - 100,
                self.rect.height - 160
            )
            # Botão Adicionar
            add_rect = pygame.Rect(editor_rect.x + 20, editor_rect.y + 88, 120, 26)
            if add_rect.collidepoint(mouse_x, mouse_y):
                self.hovered_button = "template_add_enemy"
                return
            # Botão Distribuir
            equalize_rect = pygame.Rect(editor_rect.x + 150, editor_rect.y + 88, 110, 26)
            if equalize_rect.collidepoint(mouse_x, mouse_y):
                self.hovered_button = "template_equalize"
                return
            # Botão Limpar
            clear_rect = pygame.Rect(editor_rect.x + 270, editor_rect.y + 88, 95, 26)
            if clear_rect.collidepoint(mouse_x, mouse_y):
                self.hovered_button = "template_clear"
                return

        for button, name in buttons:
            if button.collidepoint(mouse_x, mouse_y):
                self.hovered_button = name
                self._update_dropdown_hovers(mouse_x, mouse_y)
                return
        self.hovered_button = None
        self._update_dropdown_hovers(mouse_x, mouse_y)

    def _update_dropdown_hovers(self, mouse_x, mouse_y):
        """Atualiza hovers dos dropdowns separadamente"""
        # Atualiza hover do dropdown de paths
        if self.path_dropdown_open:
            list_rect = self._get_path_dropdown_rect()
            if list_rect.collidepoint(mouse_x, mouse_y):
                relative_y = mouse_y - list_rect.y - 2
                index = int(relative_y // 26)
                if 0 <= index < len(self.path_manager.paths):
                    self.path_hovered_index = index
                else:
                    self.path_hovered_index = -1
            else:
                self.path_hovered_index = -1

        # Atualiza hover do dropdown de templates
        if self.template_combo_open:
            list_rect = self._get_template_dropdown_rect()
            templates = WaveTemplateManager.get_all_templates()
            if list_rect.collidepoint(mouse_x, mouse_y):
                relative_y = mouse_y - list_rect.y - 2
                index = int(relative_y // 28)
                if 0 <= index < len(templates):
                    self.template_combo_hovered_index = index
                else:
                    self.template_combo_hovered_index = -1
            else:
                self.template_combo_hovered_index = -1

    # --- Manipuladores de abas ---
    def _handle_waves_tab_click(self, mouse_x, mouse_y):
        if self.add_wave_button.collidepoint(mouse_x, mouse_y):
            self.wave_manager.add_wave()
            self.selected_wave_index = self.wave_manager.selected_wave
            self._sync_template_dropdown()
            self._sync_path_dropdown()
            return True

        if self.remove_wave_button.collidepoint(mouse_x, mouse_y):
            if self.wave_manager.waves:
                self.wave_manager.remove_wave(self.selected_wave_index)
                self.selected_wave_index = self.wave_manager.selected_wave
                self._sync_template_dropdown()
                self._sync_path_dropdown()
            return True

        if self.duplicate_wave_button.collidepoint(mouse_x, mouse_y):
            wave = self.wave_manager.get_current_wave()
            if wave:
                self.wave_manager.add_wave()
                new_wave = self.wave_manager.get_current_wave()
                if new_wave:
                    new_wave.path_index = wave.path_index
                    new_wave.name = f"{wave.name} (copia)"
                    new_wave.enemies = [WaveEnemy(e.pokemon_id, e.percentage) for e in wave.enemies]
                    new_wave.min_level = wave.min_level
                    new_wave.max_level = wave.max_level
                    new_wave.wave_size = wave.wave_size
                    new_wave.spawn_interval = wave.spawn_interval
                    new_wave.initial_delay = wave.initial_delay
                    new_wave.repeat_wave = wave.repeat_wave
                    new_wave.repeat_count = wave.repeat_count
                    new_wave.template_id = wave.template_id
                    new_wave.use_variants = wave.use_variants
                    new_wave.variants = []
                    for v in wave.variants:
                        new_v = WaveVariant(v.condition, [WaveEnemy(e.pokemon_id, e.percentage) for e in v.enemies])
                        new_v.min_level = v.min_level
                        new_v.max_level = v.max_level
                        new_wave.variants.append(new_v)
                    self.selected_wave_index = len(self.wave_manager.waves) - 1
                    self.wave_manager.selected_wave = self.selected_wave_index
                    self._sync_template_dropdown()
                    self._sync_path_dropdown()
            return True

        # Clique no seletor de path
        if self.path_selector_rect.collidepoint(mouse_x, mouse_y):
            self.path_dropdown_open = not self.path_dropdown_open
            return True

        # Clique na lista de paths (dropdown aberto)
        if self.path_dropdown_open:
            list_rect = self._get_path_dropdown_rect()
            if list_rect.collidepoint(mouse_x, mouse_y):
                relative_y = mouse_y - list_rect.y - 2
                index = int(relative_y // 26)
                if 0 <= index < len(self.path_manager.paths):
                    self.path_selected_index = index
                    wave = self.wave_manager.get_current_wave()
                    if wave:
                        wave.path_index = index
                    self.path_dropdown_open = False
                    return True
            # Clicou fora do dropdown
            if not self.path_selector_rect.collidepoint(mouse_x, mouse_y):
                self.path_dropdown_open = False
                return True

        if self.waves_list_area.collidepoint(mouse_x, mouse_y):
            relative_y = mouse_y - self.waves_list_area.y
            item_index = (relative_y // self.wave_item_height) + self.waves_scroll
            if 0 <= item_index < len(self.wave_manager.waves):
                self.selected_wave_index = item_index
                self.wave_manager.selected_wave = item_index
                self._sync_template_dropdown()
                self._sync_path_dropdown()
                self.enemies_scroll = 0
                return True
        return True

    def _handle_composition_tab_click(self, mouse_x, mouse_y):
        wave = self.wave_manager.get_current_wave()
        if not wave:
            return True

        # ===== SELETOR DE TEMPLATE =====
        # Clique no seletor de template
        if self.template_selector_rect.collidepoint(mouse_x, mouse_y):
            self.template_combo_open = not self.template_combo_open
            return True

        # Clique no botão "Limpar"
        if self.clear_template_rect.collidepoint(mouse_x, mouse_y):
            wave.template_id = None
            wave.enemies = []
            wave.use_variants = False
            wave.variants = []
            self.template_combo_open = False
            self._check_total_percentage(wave)
            return True

        # Clique no dropdown de templates
        if self.template_combo_open:
            list_rect = self._get_template_dropdown_rect()
            templates = WaveTemplateManager.get_all_templates()

            if list_rect.collidepoint(mouse_x, mouse_y):
                relative_y = mouse_y - list_rect.y - 2
                index = int(relative_y // 28)
                if 0 <= index < len(templates):
                    template = templates[index]

                    # ===== APLICA O TEMPLATE NA WAVE =====
                    wave.template_id = template.template_id

                    # Limpa enemies e variants antigos
                    wave.enemies = []
                    wave.use_variants = False
                    wave.variants = []

                    # Copia os inimigos do template
                    for enemy in template.enemies:
                        wave.enemies.append(WaveEnemy(enemy.pokemon_id, enemy.percentage))

                    # Copia os níveis
                    wave.min_level = template.min_level
                    wave.max_level = template.max_level

                    # Fecha o dropdown
                    self.template_combo_open = False
                    self._check_total_percentage(wave)
                    return True

            # Clicou fora do dropdown
            if not self.template_selector_rect.collidepoint(mouse_x, mouse_y):
                self.template_combo_open = False
                return True

        # Se tem template, não permite edição manual
        if wave.template_id:
            return True

        if self.add_enemy_button.collidepoint(mouse_x, mouse_y):
            if len(wave.enemies) < 12:
                first_id = self.available_pokemon_ids[0] if self.available_pokemon_ids else 1
                wave.enemies.append(WaveEnemy(first_id, 0.0))
            return True

        if self.equalize_button.collidepoint(mouse_x, mouse_y) and wave.enemies:
            equal_percent = 100.0 / len(wave.enemies)
            for enemy in wave.enemies:
                enemy.percentage = equal_percent
            total = sum(e.percentage for e in wave.enemies)
            if abs(total - 100.0) > 0.01:
                wave.enemies[-1].percentage += (100.0 - total)
            self._check_total_percentage(wave)
            return True

        if self.clear_enemies_button.collidepoint(mouse_x, mouse_y):
            wave.enemies.clear()
            wave.template_id = None  # Também limpa o template
            self.input_errors.pop("total", None)
            return True

        if self.enemies_list_area.collidepoint(mouse_x, mouse_y):
            relative_y = mouse_y - self.enemies_list_area.y
            item_index = (relative_y // self.enemy_item_height) + self.enemies_scroll
            if 0 <= item_index < len(wave.enemies):
                enemy = wave.enemies[item_index]
                item_y = self.enemies_list_area.y + 2 + (item_index - self.enemies_scroll) * self.enemy_item_height

                remove_rect = pygame.Rect(self.enemies_list_area.right - 28, item_y + 4, 18, 18)
                if remove_rect.collidepoint(mouse_x, mouse_y):
                    del wave.enemies[item_index]
                    # Se não tiver mais inimigos, limpa o template
                    if not wave.enemies:
                        wave.template_id = None
                    self._check_total_percentage(wave)
                    return True

                pokemon_rect = pygame.Rect(self.enemies_list_area.x + 38, item_y + 4, 120, 22)
                if pokemon_rect.collidepoint(mouse_x, mouse_y):
                    self.showing_pokemon_selector = True
                    self.pokemon_selector_target = "enemy"
                    self.pokemon_selector_index = item_index
                    self.pokemon_selector_scroll = 0
                    self.pokemon_search = ""
                    return True

                percent_rect = pygame.Rect(self.enemies_list_area.right - 88, item_y + 8, 50, 20)
                if percent_rect.collidepoint(mouse_x, mouse_y):
                    self.active_input = f"percent_{item_index}"
                    self.input_texts[self.active_input] = f"{enemy.percentage:.1f}"
                    return True
        return True

    def _handle_variants_tab_click(self, mouse_x, mouse_y):
        wave = self.wave_manager.get_current_wave()
        if not wave:
            return True

        if self.add_variant_button.collidepoint(mouse_x, mouse_y):
            if len(wave.variants) < 6:
                new_variant = WaveVariant("any", [])
                new_variant.min_level = wave.min_level
                new_variant.max_level = wave.max_level
                wave.variants.append(new_variant)
                wave.use_variants = True
                self.selected_variant_index = len(wave.variants) - 1
                self.variant_editor_open = True
                self.editing_variant_index = self.selected_variant_index
                for i, opt in enumerate(self.condition_options):
                    if opt["id"] == "any":
                        self.condition_selected_index = i
                        break
            return True

        if self.remove_variant_button.collidepoint(mouse_x, mouse_y):
            if self.selected_variant_index >= 0 and self.selected_variant_index < len(wave.variants):
                del wave.variants[self.selected_variant_index]
                self.selected_variant_index = -1
                self.variant_editor_open = False
                if not wave.variants:
                    wave.use_variants = False
            return True

        if self.edit_variant_button.collidepoint(mouse_x, mouse_y):
            if self.selected_variant_index >= 0 and self.selected_variant_index < len(wave.variants):
                self.variant_editor_open = True
                self.editing_variant_index = self.selected_variant_index
                variant = wave.variants[self.selected_variant_index]
                for i, opt in enumerate(self.condition_options):
                    if opt["id"] == variant.condition:
                        self.condition_selected_index = i
                        break
            return True

        if self.variants_list_area.collidepoint(mouse_x, mouse_y):
            relative_y = mouse_y - self.variants_list_area.y
            item_index = (relative_y // self.variant_item_height) + self.variants_scroll
            if 0 <= item_index < len(wave.variants):
                self.selected_variant_index = item_index
                return True

        return True

    def _handle_templates_tab_click(self, mouse_x, mouse_y):
        if self.new_template_button.collidepoint(mouse_x, mouse_y):
            wave = self.wave_manager.get_current_wave()
            if wave and wave.enemies:
                template_id = f"template_{random.randint(1000, 9999)}"
                template = WaveTemplate(template_id, f"Template {len(WaveTemplateManager.get_all_templates()) + 1}")
                template.enemies = [WaveEnemy(e.pokemon_id, e.percentage) for e in wave.enemies]
                template.min_level = wave.min_level
                template.max_level = wave.max_level
                WaveTemplateManager.add_template(template)
                self._update_template_options()
                self._sync_template_dropdown()
                self.template_selected_index = len(WaveTemplateManager.get_all_templates())
            return True

        if self.delete_template_button.collidepoint(mouse_x, mouse_y):
            if self.template_selected_index > 0:
                templates = WaveTemplateManager.get_all_templates()
                if self.template_selected_index - 1 < len(templates):
                    template = templates[self.template_selected_index - 1]
                    WaveTemplateManager.remove_template(template.template_id)
                    self.template_selected_index = 0
                    self._update_template_options()
                    self._sync_template_dropdown()
            return True

        if self.edit_template_button.collidepoint(mouse_x, mouse_y):
            if self.template_selected_index > 0:
                self.template_editor_open = True
            return True

        if self.templates_list_area.collidepoint(mouse_x, mouse_y):
            relative_y = mouse_y - self.templates_list_area.y
            item_index = (relative_y // self.template_item_height) + self.templates_scroll
            templates = WaveTemplateManager.get_all_templates()
            if 0 <= item_index < len(templates):
                self.template_selected_index = item_index + 1
                wave = self.wave_manager.get_current_wave()
                if wave:
                    wave.template_id = templates[item_index].template_id
                self._sync_template_dropdown()
                return True
        return True

    # --- Editor de Variant ---
    def _handle_variant_editor_event(self, event, mouse_x, mouse_y):
        wave = self.wave_manager.get_current_wave()
        if not wave or self.editing_variant_index < 0 or self.editing_variant_index >= len(wave.variants):
            self.variant_editor_open = False
            return None

        variant = wave.variants[self.editing_variant_index]
        editor_rect = pygame.Rect(
            self.rect.x + 50,
            self.rect.y + 100,
            self.rect.width - 100,
            self.rect.height - 160
        )

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if not editor_rect.collidepoint(mouse_x, mouse_y):
                self.variant_editor_open = False
                self.condition_dropdown_open = False
                self.variant_template_combo_open = False
                return True

            # Fechar
            close_rect = pygame.Rect(editor_rect.right - 35, editor_rect.y + 8, 28, 28)
            if close_rect.collidepoint(mouse_x, mouse_y):
                self.variant_editor_open = False
                self.condition_dropdown_open = False
                self.variant_template_combo_open = False
                return True

            # Dropdown de condição
            cond_rect = pygame.Rect(editor_rect.x + 140, editor_rect.y + 50, 180, 26)
            if self.condition_dropdown_open:
                list_rect = self._get_dropdown_list_rect(cond_rect, self.condition_options)
                if list_rect.collidepoint(mouse_x, mouse_y):
                    relative_y = mouse_y - list_rect.y - 2
                    index = int(relative_y // 26)
                    if 0 <= index < len(self.condition_options):
                        variant.condition = self.condition_options[index]["id"]
                        self.condition_selected_index = index
                        self.condition_dropdown_open = False
                        return True
                self.condition_dropdown_open = False
                if cond_rect.collidepoint(mouse_x, mouse_y):
                    self.condition_dropdown_open = True
                    return True
                return True

            if cond_rect.collidepoint(mouse_x, mouse_y):
                self.condition_dropdown_open = not self.condition_dropdown_open
                return True

            # ===== SELETOR DE TEMPLATE NA VARIANT =====
            template_rect = pygame.Rect(editor_rect.x + 100, editor_rect.y + 86, 150, 26)

            # Clique no seletor de template
            if template_rect.collidepoint(mouse_x, mouse_y):
                self.variant_template_combo_open = not self.variant_template_combo_open
                return True

            # Clique no botão "Limpar" do template
            clear_template_rect = pygame.Rect(template_rect.right + 10, template_rect.y, 70, 26)
            if clear_template_rect.collidepoint(mouse_x, mouse_y):
                if hasattr(variant, 'template_id'):
                    variant.template_id = None
                variant.enemies = []
                self.variant_template_combo_open = False
                return True

            # Clique no dropdown de templates
            if self.variant_template_combo_open:
                templates = WaveTemplateManager.get_all_templates()
                item_height = 28
                list_height = min(len(templates) * item_height + 4, 160)
                list_rect = pygame.Rect(
                    template_rect.x,
                    template_rect.bottom + 2,
                    template_rect.width,
                    list_height
                )
                # Ajusta para não sobrepor
                if list_rect.bottom > editor_rect.bottom - 10:
                    list_rect.y = template_rect.top - list_height - 2
                    if list_rect.top < editor_rect.top + 40:
                        list_rect.y = template_rect.bottom + 2

                if list_rect.collidepoint(mouse_x, mouse_y):
                    relative_y = mouse_y - list_rect.y - 2
                    index = int(relative_y // item_height)
                    if 0 <= index < len(templates):
                        template = templates[index]
                        variant.template_id = template.template_id
                        # Copia os inimigos do template
                        variant.enemies = [WaveEnemy(e.pokemon_id, e.percentage) for e in template.enemies]
                        variant.min_level = template.min_level
                        variant.max_level = template.max_level
                        self.variant_template_combo_open = False
                        return True

                # Clicou fora do dropdown
                if not template_rect.collidepoint(mouse_x, mouse_y):
                    self.variant_template_combo_open = False
                    return True

            # ===== BOTÕES DA VARIANT =====
            # Adicionar inimigo
            add_rect = pygame.Rect(editor_rect.x + 20, editor_rect.y + 122, 120, 26)
            if add_rect.collidepoint(mouse_x, mouse_y):
                if len(variant.enemies) < 8 and not (hasattr(variant, 'template_id') and variant.template_id):
                    first_id = self.available_pokemon_ids[0] if self.available_pokemon_ids else 1
                    variant.enemies.append(WaveEnemy(first_id, 0.0))
                return True

            # Distribuir
            equalize_rect = pygame.Rect(editor_rect.x + 150, editor_rect.y + 122, 110, 26)
            if equalize_rect.collidepoint(mouse_x, mouse_y):
                enemies = variant.enemies
                if not (hasattr(variant, 'template_id') and variant.template_id) and enemies:
                    equal_percent = 100.0 / len(enemies)
                    for enemy in enemies:
                        enemy.percentage = equal_percent
                    total = sum(e.percentage for e in enemies)
                    if abs(total - 100.0) > 0.01:
                        enemies[-1].percentage += (100.0 - total)
                return True

            # Limpar inimigos
            clear_enemies_rect = pygame.Rect(editor_rect.x + 270, editor_rect.y + 122, 95, 26)
            if clear_enemies_rect.collidepoint(mouse_x, mouse_y):
                if not (hasattr(variant, 'template_id') and variant.template_id):
                    variant.enemies.clear()
                return True

            # Lista de inimigos
            list_rect = pygame.Rect(editor_rect.x + 20, editor_rect.y + 156, editor_rect.width - 40, 160)
            if list_rect.collidepoint(mouse_x, mouse_y):
                # Pega os inimigos (do template ou da variant)
                if hasattr(variant, 'template_id') and variant.template_id:
                    template = WaveTemplateManager.get_template(variant.template_id)
                    enemies = template.enemies if template else []
                else:
                    enemies = variant.enemies

                relative_y = mouse_y - list_rect.y
                item_index = int(relative_y // 32)
                if 0 <= item_index < len(enemies):
                    enemy = enemies[item_index]
                    item_y = list_rect.y + item_index * 32

                    # Botão remover (só se não tiver template)
                    if not (hasattr(variant, 'template_id') and variant.template_id):
                        remove_rect = pygame.Rect(list_rect.right - 28, item_y + 4, 18, 18)
                        if remove_rect.collidepoint(mouse_x, mouse_y):
                            del variant.enemies[item_index]
                            return True

                    # Selecionar Pokémon
                    pokemon_rect = pygame.Rect(list_rect.x + 38, item_y + 4, 120, 22)
                    if pokemon_rect.collidepoint(mouse_x, mouse_y):
                        self.showing_pokemon_selector = True
                        self.pokemon_selector_target = "variant"
                        self.pokemon_selector_index = item_index
                        self.pokemon_selector_scroll = 0
                        self.pokemon_search = ""
                        return True

                    # Editar percentual (só se não tiver template)
                    if not (hasattr(variant, 'template_id') and variant.template_id):
                        percent_rect = pygame.Rect(list_rect.right - 85, item_y + 4, 50, 20)
                        if percent_rect.collidepoint(mouse_x, mouse_y):
                            self.active_input = f"variant_percent_{item_index}"
                            self.input_texts[self.active_input] = f"{enemy.percentage:.1f}"
                            return True

        if event.type == pygame.MOUSEMOTION and self.condition_dropdown_open:
            cond_rect = pygame.Rect(editor_rect.x + 140, editor_rect.y + 50, 180, 26)
            list_rect = self._get_dropdown_list_rect(cond_rect, self.condition_options)
            if list_rect.collidepoint(mouse_x, mouse_y):
                relative_y = mouse_y - list_rect.y - 2
                index = int(relative_y // 26)
                if 0 <= index < len(self.condition_options):
                    self.condition_hovered_index = index
                else:
                    self.condition_hovered_index = -1
            else:
                self.condition_hovered_index = -1

        # Hover do dropdown de templates na variant
        if event.type == pygame.MOUSEMOTION and self.variant_template_combo_open:
            templates = WaveTemplateManager.get_all_templates()
            template_rect = pygame.Rect(editor_rect.x + 100, editor_rect.y + 86, 150, 26)
            item_height = 28
            list_height = min(len(templates) * item_height + 4, 160)
            list_rect = pygame.Rect(
                template_rect.x,
                template_rect.bottom + 2,
                template_rect.width,
                list_height
            )
            if list_rect.bottom > editor_rect.bottom - 10:
                list_rect.y = template_rect.top - list_height - 2
                if list_rect.top < editor_rect.top + 40:
                    list_rect.y = template_rect.bottom + 2

            if list_rect.collidepoint(mouse_x, mouse_y):
                relative_y = mouse_y - list_rect.y - 2
                index = int(relative_y // item_height)
                if 0 <= index < len(templates):
                    self.variant_template_hovered_index = index
                else:
                    self.variant_template_hovered_index = -1
            else:
                self.variant_template_hovered_index = -1

        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.variant_editor_open = False
            self.condition_dropdown_open = False
            self.variant_template_combo_open = False
            return True

        return None

    def _render_variant_editor(self, screen):
        wave = self.wave_manager.get_current_wave()
        if not wave or self.editing_variant_index < 0 or self.editing_variant_index >= len(wave.variants):
            return

        variant = wave.variants[self.editing_variant_index]
        editor_rect = pygame.Rect(
            self.rect.x + 50,
            self.rect.y + 100,
            self.rect.width - 100,
            self.rect.height - 160
        )

        # Sombra
        shadow = pygame.Surface((editor_rect.width + 10, editor_rect.height + 10), pygame.SRCALPHA)
        shadow.fill((0, 0, 0, 120))
        screen.blit(shadow, (editor_rect.x - 5, editor_rect.y - 5))

        # Fundo
        pygame.draw.rect(screen, self.colors['bg_light'], editor_rect, border_radius=10)
        pygame.draw.rect(screen, self.colors['border_active'], editor_rect, 2, border_radius=10)

        # Título
        title = self._get_font(18, True).render("Editor de Variant", True, self.colors['title'])
        screen.blit(title, (editor_rect.x + 20, editor_rect.y + 10))

        # Fechar
        close_rect = pygame.Rect(editor_rect.right - 35, editor_rect.y + 8, 28, 28)
        pygame.draw.rect(screen, self.colors['danger'], close_rect, border_radius=6)
        close_text = self._get_font(18).render("X", True, self.colors['text'])
        screen.blit(close_text, (close_rect.x + 8, close_rect.y + 4))

        # Condição
        cond_label = self._get_font(14).render("Período:", True, self.colors['text_dim'])
        screen.blit(cond_label, (editor_rect.x + 20, editor_rect.y + 52))

        cond_rect = pygame.Rect(editor_rect.x + 140, editor_rect.y + 50, 180, 26)
        cond_border = self.colors['border_active'] if self.condition_dropdown_open else self.colors['border']
        pygame.draw.rect(screen, self.colors['bg_input'], cond_rect, border_radius=5)
        pygame.draw.rect(screen, cond_border, cond_rect, 1, border_radius=5)

        cond_labels = {c["id"]: c["label"] for c in self.condition_options}
        cond_text = self._get_font(14).render(cond_labels.get(variant.condition, "Qualquer"), True, self.colors['text'])
        screen.blit(cond_text, (cond_rect.x + 8, cond_rect.y + 3))
        arrow = self._get_font(14).render("▼" if not self.condition_dropdown_open else "▲", True,
                                          self.colors['text_muted'])
        screen.blit(arrow, (cond_rect.right - 20, cond_rect.y + 3))

        # ===== SELETOR DE TEMPLATE (NOVO) =====
        templates = WaveTemplateManager.get_all_templates()

        template_label = self._get_font(13).render("Template:", True, self.colors['text_dim'])
        template_label_pos = (editor_rect.x + 20, editor_rect.y + 88)
        screen.blit(template_label, template_label_pos)

        # Posiciona o seletor ao lado do label
        template_rect = pygame.Rect(editor_rect.x + 100, editor_rect.y + 86, 150, 26)
        border = self.colors['border_active'] if self.variant_template_combo_open else self.colors['border']
        pygame.draw.rect(screen, self.colors['bg_input'], template_rect, border_radius=5)
        pygame.draw.rect(screen, border, template_rect, 1, border_radius=5)

        # Texto do template selecionado (se houver)
        template_name = "Nenhum"
        if hasattr(variant, 'template_id') and variant.template_id:
            template = WaveTemplateManager.get_template(variant.template_id)
            if template:
                template_name = template.name

        text = self._get_font(13).render(template_name, True, self.colors['text'])
        screen.blit(text, (template_rect.x + 8, template_rect.y + 4))

        arrow = self._get_font(13).render("▼" if not self.variant_template_combo_open else "▲", True,
                                          self.colors['text_muted'])
        screen.blit(arrow, (template_rect.right - 18, template_rect.y + 4))

        # Botão "Limpar template" na variant
        clear_template_rect = pygame.Rect(template_rect.right + 10, template_rect.y, 70, 26)
        self._render_button(screen, clear_template_rect, "variant_clear_template", "Limpar")

        # Guarda as referências para usar no clique
        self.variant_template_rect = template_rect
        self.variant_clear_template_rect = clear_template_rect

        # Dropdown de templates (se aberto)
        if self.variant_template_combo_open:
            item_height = 28
            list_height = min(len(templates) * item_height + 4, 160)
            list_rect = pygame.Rect(
                template_rect.x,
                template_rect.bottom + 2,
                template_rect.width,
                list_height
            )
            # Ajusta para não sobrepor
            if list_rect.bottom > editor_rect.bottom - 10:
                list_rect.y = template_rect.top - list_height - 2
                if list_rect.top < editor_rect.top + 40:
                    list_rect.y = template_rect.bottom + 2

            pygame.draw.rect(screen, self.colors['bg_dropdown'], list_rect, border_radius=5)
            pygame.draw.rect(screen, self.colors['border_dropdown'], list_rect, 1, border_radius=5)

            for i, template in enumerate(templates):
                item_rect = pygame.Rect(list_rect.x + 4, list_rect.y + 2 + i * item_height, list_rect.width - 8, 22)
                is_hover = (i == self.variant_template_hovered_index)
                is_sel = (hasattr(variant, 'template_id') and template.template_id == variant.template_id)

                bg = self.colors['dropdown_item_hover'] if is_hover else self.colors['bg_dropdown']
                if is_sel:
                    bg = self.colors['accent']
                pygame.draw.rect(screen, bg, item_rect, border_radius=4)

                text = self._get_font(13).render(template.name, True, self.colors['text'])
                screen.blit(text, (item_rect.x + 8, item_rect.y + 3))
                if is_sel:
                    check = self._get_font(13).render("✓", True, self.colors['radio_selected'])
                    screen.blit(check, (item_rect.right - 20, item_rect.y + 3))

        # Botão Adicionar (abaixo do seletor de template)
        add_rect = pygame.Rect(editor_rect.x + 20, editor_rect.y + 122, 120, 26)
        self._render_button(screen, add_rect, "variant_add_enemy", "+ Adicionar")

        # Botão Distribuir
        equalize_rect = pygame.Rect(editor_rect.x + 150, editor_rect.y + 122, 110, 26)
        self._render_button(screen, equalize_rect, "variant_equalize", "Distribuir")

        # Botão Limpar
        clear_enemies_rect = pygame.Rect(editor_rect.x + 270, editor_rect.y + 122, 95, 26)
        self._render_button(screen, clear_enemies_rect, "variant_clear_enemies", "Limpar")

        # Guarda referências
        self.variant_add_rect = add_rect
        self.variant_equalize_rect = equalize_rect
        self.variant_clear_enemies_rect = clear_enemies_rect

        # Lista de inimigos
        list_rect = pygame.Rect(editor_rect.x + 20, editor_rect.y + 156, editor_rect.width - 40, 160)
        pygame.draw.rect(screen, self.colors['bg_dark'], list_rect, border_radius=6)

        old_clip = screen.get_clip()
        screen.set_clip(list_rect)

        # Pega os inimigos (do template ou da variant)
        if hasattr(variant, 'template_id') and variant.template_id:
            template = WaveTemplateManager.get_template(variant.template_id)
            enemies = template.enemies if template else []
        else:
            enemies = variant.enemies

        for i, enemy in enumerate(enemies):
            item_y = list_rect.y + i * 32
            if item_y + 32 < list_rect.y or item_y > list_rect.y + list_rect.height:
                continue

            item_rect = pygame.Rect(list_rect.x + 4, item_y, list_rect.width - 8, 32)
            bg_color = self.colors['bg_light'] if i % 2 == 0 else self.colors['bg_dark']
            pygame.draw.rect(screen, bg_color, item_rect)

            sprite = self._get_pokemon_sprite(enemy.pokemon_id, 22)
            screen.blit(sprite, (item_rect.x + 2, item_rect.y + 5))

            name = self.pokedex.get_name(enemy.pokemon_id)
            name_text = self._get_font(13).render(name, True, self.colors['text'])
            screen.blit(name_text, (item_rect.x + 28, item_rect.y + 8))

            # Campo de percentual
            percent_rect = pygame.Rect(list_rect.right - 78, item_y + 6, 45, 20)
            is_active = self.active_input == f"variant_percent_{i}"
            border = self.colors['border_active'] if is_active else self.colors['border']
            pygame.draw.rect(screen, self.colors['bg_input'], percent_rect, border_radius=3)
            pygame.draw.rect(screen, border, percent_rect, 1, border_radius=3)

            display = self.input_texts.get(f"variant_percent_{i}",
                                           f"{enemy.percentage:.1f}") if is_active else f"{enemy.percentage:.1f}"
            pct_text = self._get_font(12).render(display, True, self.colors['text'])
            screen.blit(pct_text, (percent_rect.x + 3, percent_rect.y + 3))
            pct_symbol = self._get_font(10).render("%", True, self.colors['text_muted'])
            screen.blit(pct_symbol, (percent_rect.right + 2, percent_rect.y + 3))

            # Botão remover (só se não tiver template)
            if not (hasattr(variant, 'template_id') and variant.template_id):
                remove_rect = pygame.Rect(list_rect.right - 22, item_y + 7, 14, 14)
                pygame.draw.rect(screen, self.colors['danger'], remove_rect, border_radius=3)
                pygame.draw.line(screen, self.colors['text'],
                                 (remove_rect.x + 3, remove_rect.y + 3),
                                 (remove_rect.right - 3, remove_rect.bottom - 3), 2)
                pygame.draw.line(screen, self.colors['text'],
                                 (remove_rect.right - 3, remove_rect.y + 3),
                                 (remove_rect.x + 3, remove_rect.bottom - 3), 2)

        screen.set_clip(old_clip)

        # Total
        total = sum(e.percentage for e in enemies)
        color = (100, 255, 100) if abs(total - 100.0) < 0.01 else (255, 100, 100)
        total_text = self._get_font(13).render(f"Total: {total:.1f}%", True, color)
        screen.blit(total_text, (list_rect.x, list_rect.bottom + 6))

        # Dropdown de condição (sobreposto)
        if self.condition_dropdown_open:
            list_rect_drop = self._get_dropdown_list_rect(cond_rect, self.condition_options)
            if list_rect_drop.bottom > list_rect.y and list_rect_drop.y < list_rect.bottom:
                list_rect_drop.y = cond_rect.top - list_rect_drop.height - 2
                if list_rect_drop.top < editor_rect.top:
                    list_rect_drop.y = cond_rect.bottom + 2

            pygame.draw.rect(screen, self.colors['bg_dropdown'], list_rect_drop, border_radius=5)
            pygame.draw.rect(screen, self.colors['border_dropdown'], list_rect_drop, 1, border_radius=5)

            for i, opt in enumerate(self.condition_options):
                item_rect = pygame.Rect(list_rect_drop.x + 4, list_rect_drop.y + 2 + i * 26, list_rect_drop.width - 8,
                                        22)
                is_hover = (i == self.condition_hovered_index)
                is_sel = opt["id"] == variant.condition

                bg = self.colors['dropdown_item_hover'] if is_hover else self.colors['bg_dropdown']
                if is_sel:
                    bg = self.colors['accent']
                pygame.draw.rect(screen, bg, item_rect, border_radius=4)

                text = self._get_font(13).render(opt["label"], True, self.colors['text'])
                screen.blit(text, (item_rect.x + 8, item_rect.y + 3))
                if is_sel:
                    check = self._get_font(13).render("✓", True, self.colors['radio_selected'])
                    screen.blit(check, (item_rect.right - 20, item_rect.y + 3))

    # --- Editor de Template ---
    def _handle_template_editor_event(self, event, mouse_x, mouse_y):
        templates = WaveTemplateManager.get_all_templates()
        if self.template_selected_index <= 0 or self.template_selected_index - 1 >= len(templates):
            self.template_editor_open = False
            return None

        template = templates[self.template_selected_index - 1]
        editor_rect = pygame.Rect(
            self.rect.x + 50,
            self.rect.y + 100,
            self.rect.width - 100,
            self.rect.height - 160
        )

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if not editor_rect.collidepoint(mouse_x, mouse_y):
                self.template_editor_open = False
                return True

            # Fechar
            close_rect = pygame.Rect(editor_rect.right - 35, editor_rect.y + 8, 28, 28)
            if close_rect.collidepoint(mouse_x, mouse_y):
                self.template_editor_open = False
                return True

            # Nome
            name_rect = pygame.Rect(editor_rect.x + 140, editor_rect.y + 15, 200, 26)
            if name_rect.collidepoint(mouse_x, mouse_y):
                self.active_input = "template_name"
                self.input_texts["template_name"] = template.name
                return True

            # ===== BOTÃO ADICIONAR =====
            add_rect = pygame.Rect(editor_rect.x + 20, editor_rect.y + 88, 120, 26)
            if add_rect.collidepoint(mouse_x, mouse_y):
                if len(template.enemies) < 8:
                    first_id = self.available_pokemon_ids[0] if self.available_pokemon_ids else 1
                    template.enemies.append(WaveEnemy(first_id, 0.0))
                return True

            # ===== BOTÃO DISTRIBUIR =====
            equalize_rect = pygame.Rect(editor_rect.x + 150, editor_rect.y + 88, 110, 26)
            if equalize_rect.collidepoint(mouse_x, mouse_y):
                if template.enemies:
                    equal_percent = 100.0 / len(template.enemies)
                    for enemy in template.enemies:
                        enemy.percentage = equal_percent
                    total = sum(e.percentage for e in template.enemies)
                    if abs(total - 100.0) > 0.01:
                        template.enemies[-1].percentage += (100.0 - total)
                return True

            # ===== BOTÃO LIMPAR =====
            clear_rect = pygame.Rect(editor_rect.x + 270, editor_rect.y + 88, 95, 26)
            if clear_rect.collidepoint(mouse_x, mouse_y):
                template.enemies.clear()
                return True

            # Lista de inimigos
            list_rect = pygame.Rect(editor_rect.x + 20, editor_rect.y + 122, editor_rect.width - 40, 195)
            if list_rect.collidepoint(mouse_x, mouse_y):
                relative_y = mouse_y - list_rect.y
                item_index = int(relative_y // 32)
                if 0 <= item_index < len(template.enemies):
                    enemy = template.enemies[item_index]
                    item_y = list_rect.y + item_index * 32

                    # Botão remover
                    remove_rect = pygame.Rect(list_rect.right - 28, item_y + 4, 18, 18)
                    if remove_rect.collidepoint(mouse_x, mouse_y):
                        del template.enemies[item_index]
                        return True

                    # Selecionar Pokémon
                    pokemon_rect = pygame.Rect(list_rect.x + 38, item_y + 4, 120, 22)
                    if pokemon_rect.collidepoint(mouse_x, mouse_y):
                        self.showing_pokemon_selector = True
                        self.pokemon_selector_target = "template"
                        self.pokemon_selector_index = item_index
                        self.pokemon_selector_scroll = 0
                        self.pokemon_search = ""
                        return True

                    # Editar percentual
                    percent_rect = pygame.Rect(list_rect.right - 85, item_y + 4, 50, 20)
                    if percent_rect.collidepoint(mouse_x, mouse_y):
                        self.active_input = f"template_percent_{item_index}"
                        self.input_texts[self.active_input] = f"{enemy.percentage:.1f}"
                        return True

        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.template_editor_open = False
            return True

        return None

    def _render_template_editor(self, screen):
        templates = WaveTemplateManager.get_all_templates()
        if self.template_selected_index <= 0 or self.template_selected_index - 1 >= len(templates):
            return

        template = templates[self.template_selected_index - 1]

        editor_rect = pygame.Rect(
            self.rect.x + 50,
            self.rect.y + 100,
            self.rect.width - 100,
            self.rect.height - 160
        )

        # Sombra
        shadow = pygame.Surface((editor_rect.width + 10, editor_rect.height + 10), pygame.SRCALPHA)
        shadow.fill((0, 0, 0, 120))
        screen.blit(shadow, (editor_rect.x - 5, editor_rect.y - 5))

        # Fundo
        pygame.draw.rect(screen, self.colors['bg_light'], editor_rect, border_radius=10)
        pygame.draw.rect(screen, self.colors['border_active'], editor_rect, 2, border_radius=10)

        # Título
        title = self._get_font(18, True).render("Editor de Template", True, self.colors['title'])
        screen.blit(title, (editor_rect.x + 20, editor_rect.y + 10))

        # Fechar
        close_rect = pygame.Rect(editor_rect.right - 35, editor_rect.y + 8, 28, 28)
        pygame.draw.rect(screen, self.colors['danger'], close_rect, border_radius=6)
        close_text = self._get_font(18).render("X", True, self.colors['text'])
        screen.blit(close_text, (close_rect.x + 8, close_rect.y + 4))

        # Nome
        name_label = self._get_font(14).render("Nome:", True, self.colors['text_dim'])
        screen.blit(name_label, (editor_rect.x + 20, editor_rect.y + 52))

        name_rect = pygame.Rect(editor_rect.x + 140, editor_rect.y + 50, 200, 26)
        is_active = self.active_input == "template_name"
        border = self.colors['border_active'] if is_active else self.colors['border']
        pygame.draw.rect(screen, self.colors['bg_input'], name_rect, border_radius=5)
        pygame.draw.rect(screen, border, name_rect, 1, border_radius=5)

        display = self.input_texts.get("template_name", template.name) if is_active else template.name
        name_text = self._get_font(14).render(display, True, self.colors['text'])
        screen.blit(name_text, (name_rect.x + 8, name_rect.y + 3))

        # ===== BOTÕES DO EDITOR =====
        # Botão Adicionar
        add_rect = pygame.Rect(editor_rect.x + 20, editor_rect.y + 88, 120, 26)
        self._render_button(screen, add_rect, "template_add_enemy", "+ Adicionar")

        # Botão Distribuir
        equalize_rect = pygame.Rect(editor_rect.x + 150, editor_rect.y + 88, 110, 26)
        self._render_button(screen, equalize_rect, "template_equalize", "Distribuir")

        # Botão Limpar
        clear_rect = pygame.Rect(editor_rect.x + 270, editor_rect.y + 88, 95, 26)
        self._render_button(screen, clear_rect, "template_clear", "Limpar")

        # Lista de inimigos
        list_rect = pygame.Rect(editor_rect.x + 20, editor_rect.y + 122, editor_rect.width - 40, 195)
        pygame.draw.rect(screen, self.colors['bg_dark'], list_rect, border_radius=6)

        old_clip = screen.get_clip()
        screen.set_clip(list_rect)

        for i, enemy in enumerate(template.enemies):
            item_y = list_rect.y + i * 32
            if item_y + 32 < list_rect.y or item_y > list_rect.y + list_rect.height:
                continue

            item_rect = pygame.Rect(list_rect.x + 4, item_y, list_rect.width - 8, 32)
            bg_color = self.colors['bg_light'] if i % 2 == 0 else self.colors['bg_dark']
            pygame.draw.rect(screen, bg_color, item_rect)

            sprite = self._get_pokemon_sprite(enemy.pokemon_id, 22)
            screen.blit(sprite, (item_rect.x + 2, item_rect.y + 5))

            name = self.pokedex.get_name(enemy.pokemon_id)
            name_text = self._get_font(13).render(name, True, self.colors['text'])
            screen.blit(name_text, (item_rect.x + 28, item_rect.y + 8))

            # Campo de percentual
            percent_rect = pygame.Rect(list_rect.right - 78, item_y + 6, 45, 20)
            is_active = self.active_input == f"template_percent_{i}"
            border = self.colors['border_active'] if is_active else self.colors['border']
            pygame.draw.rect(screen, self.colors['bg_input'], percent_rect, border_radius=3)
            pygame.draw.rect(screen, border, percent_rect, 1, border_radius=3)

            display = self.input_texts.get(f"template_percent_{i}",
                                           f"{enemy.percentage:.1f}") if is_active else f"{enemy.percentage:.1f}"
            pct_text = self._get_font(12).render(display, True, self.colors['text'])
            screen.blit(pct_text, (percent_rect.x + 3, percent_rect.y + 3))
            pct_symbol = self._get_font(10).render("%", True, self.colors['text_muted'])
            screen.blit(pct_symbol, (percent_rect.right + 2, percent_rect.y + 3))

            # Botão remover
            remove_rect = pygame.Rect(list_rect.right - 22, item_y + 7, 14, 14)
            pygame.draw.rect(screen, self.colors['danger'], remove_rect, border_radius=3)
            pygame.draw.line(screen, self.colors['text'],
                             (remove_rect.x + 3, remove_rect.y + 3),
                             (remove_rect.right - 3, remove_rect.bottom - 3), 2)
            pygame.draw.line(screen, self.colors['text'],
                             (remove_rect.right - 3, remove_rect.y + 3),
                             (remove_rect.x + 3, remove_rect.bottom - 3), 2)

        screen.set_clip(old_clip)

        # Total
        total = sum(e.percentage for e in template.enemies)
        color = (100, 255, 100) if abs(total - 100.0) < 0.01 else (255, 100, 100)
        total_text = self._get_font(13).render(f"Total: {total:.1f}%", True, color)
        screen.blit(total_text, (list_rect.x, list_rect.bottom + 6))

    # --- Utilitários ---
    def _get_dropdown_list_rect(self, dropdown_rect, options):
        item_height = 28
        list_height = min(len(options) * item_height + 4, 180)
        return pygame.Rect(
            dropdown_rect.x,
            dropdown_rect.bottom + 2,
            dropdown_rect.width,
            list_height
        )

    def _get_path_dropdown_rect(self):
        """Retorna o retângulo do dropdown de paths"""
        item_height = 28
        path_count = len(self.path_manager.paths)
        list_height = min(path_count * item_height + 4, 160)

        # Posiciona abaixo do seletor, mas se não couber, vai para cima
        rect = pygame.Rect(
            self.path_selector_rect.x,
            self.path_selector_rect.bottom + 2,
            self.path_selector_rect.width,
            list_height
        )

        # Verifica se vai sobrepor a lista de waves
        if rect.bottom > self.waves_list_area.y:
            rect.y = self.path_selector_rect.top - rect.height - 2
            if rect.top < self.rect.y + 80:
                rect.y = self.path_selector_rect.bottom + 2

        return rect

    def _get_template_dropdown_rect(self):
        """Retorna o retângulo do dropdown de templates"""
        templates = WaveTemplateManager.get_all_templates()
        item_height = 28
        list_height = min(len(templates) * item_height + 4, 160)

        # Posiciona abaixo do seletor, mas se não couber, vai para cima
        rect = pygame.Rect(
            self.template_selector_rect.x,
            self.template_selector_rect.bottom + 2,
            self.template_selector_rect.width,
            list_height
        )

        # Verifica se vai sobrepor a lista de inimigos
        if rect.bottom > self.enemies_list_area.y:
            rect.y = self.template_selector_rect.top - rect.height - 2
            if rect.top < self.rect.y + 80:
                rect.y = self.template_selector_rect.bottom + 2

        return rect

    def _check_total_percentage(self, wave):
        total = sum(e.percentage for e in wave.enemies)
        if abs(total - 100.0) > 0.01:
            self.input_errors["total"] = f"Total deve ser 100% (atual: {total:.1f}%)"
        else:
            self.input_errors.pop("total", None)

    def _handle_keydown(self, event):
        if event.key == pygame.K_RETURN:
            return self._apply_input()
        elif event.key == pygame.K_ESCAPE:
            self.active_input = None
            return True
        elif event.key == pygame.K_BACKSPACE:
            if self.active_input in self.input_texts:
                self.input_texts[self.active_input] = self.input_texts[self.active_input][:-1]
            return True
        elif event.unicode in "0123456789." or (
                self.active_input in ["template_name", "wave_name"] and event.unicode.isprintable()):
            if self.active_input in self.input_texts:
                self.input_texts[self.active_input] += event.unicode
            return True
        return False

    def _apply_input(self):
        wave = self.wave_manager.get_current_wave()
        if not wave or not self.active_input:
            return False

        try:
            value = self.input_texts.get(self.active_input, "")

            if self.active_input.startswith("percent_"):
                index = int(self.active_input.split("_")[1])
                if 0 <= index < len(wave.enemies):
                    new_percent = float(value) if value else 0.0
                    new_percent = max(0.0, min(100.0, new_percent))
                    wave.enemies[index].percentage = new_percent
                    self._check_total_percentage(wave)

            elif self.active_input == "wave_name":
                wave.name = value

            elif self.active_input == "wave_size":
                wave.wave_size = max(1, int(float(value)) if value else 1)

            elif self.active_input.startswith("variant_percent_"):
                index = int(self.active_input.split("_")[2])
                if self.editing_variant_index >= 0:
                    variant = wave.variants[self.editing_variant_index]
                    if 0 <= index < len(variant.enemies):
                        new_percent = float(value) if value else 0.0
                        new_percent = max(0.0, min(100.0, new_percent))
                        variant.enemies[index].percentage = new_percent

            elif self.active_input.startswith("template_percent_"):
                index = int(self.active_input.split("_")[2])
                templates = WaveTemplateManager.get_all_templates()
                if self.template_selected_index > 0 and self.template_selected_index - 1 < len(templates):
                    template = templates[self.template_selected_index - 1]
                    if 0 <= index < len(template.enemies):
                        new_percent = float(value) if value else 0.0
                        new_percent = max(0.0, min(100.0, new_percent))
                        template.enemies[index].percentage = new_percent

            elif self.active_input == "template_name":
                templates = WaveTemplateManager.get_all_templates()
                if self.template_selected_index > 0 and self.template_selected_index - 1 < len(templates):
                    templates[self.template_selected_index - 1].name = value
                    self._update_template_options()

            self.active_input = None
            return True

        except ValueError:
            self.active_input = None
            return False

    def _handle_scroll(self, direction):
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
        elif self.selected_tab == "variants":
            wave = self.wave_manager.get_current_wave()
            if wave:
                max_scroll = max(0, len(wave.variants) - self.variants_per_page)
                self.variants_scroll = max(0, min(max_scroll, self.variants_scroll + direction))
            return True
        elif self.selected_tab == "templates":
            templates = WaveTemplateManager.get_all_templates()
            max_scroll = max(0, len(templates) - self.templates_per_page)
            self.templates_scroll = max(0, min(max_scroll, self.templates_scroll + direction))
            return True
        return False

    # ========================================================================
    # NOVO SELETOR DE POKÉMON (totalmente reformulado)
    # ========================================================================

    def _handle_pokemon_selector_event(self, event, mouse_x, mouse_y):
        """Processa eventos exclusivamente do seletor de Pokémon."""
        selector_rect = self._get_selector_rect()
        list_area = pygame.Rect(
            selector_rect.x + 10,
            selector_rect.y + 70,
            selector_rect.width - 30,
            selector_rect.height - 110
        )
        ITEM_HEIGHT = 36
        filtered = self._filter_pokemon()
        max_scroll = max(0, len(filtered) - (list_area.height // ITEM_HEIGHT))

        # --- MOUSEWHEEL ---
        if event.type == pygame.MOUSEWHEEL:
            if selector_rect.collidepoint(mouse_x, mouse_y):
                self.pokemon_selector_scroll = max(0, min(max_scroll, self.pokemon_selector_scroll - event.y))
                return

        # --- MOUSEBUTTONDOWN ---
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            # Clicou fora do seletor? Fecha.
            if not selector_rect.collidepoint(mouse_x, mouse_y):
                self.showing_pokemon_selector = False
                return

            # Campo de busca
            search_rect = pygame.Rect(selector_rect.x + 10, selector_rect.y + 40, 200, 26)
            if search_rect.collidepoint(mouse_x, mouse_y):
                self.active_input = "pokemon_search"
                return

            # Área da lista (inicia arraste)
            if list_area.collidepoint(mouse_x, mouse_y):
                self.pokemon_dragging_scroll = True
                self.pokemon_drag_start_y = mouse_y
                self.pokemon_drag_start_scroll = self.pokemon_selector_scroll
                return

            # Barra de rolagem (arraste do thumb)
            if self._scrollbar_rect(selector_rect).collidepoint(mouse_x, mouse_y):
                self.pokemon_dragging_thumb = True
                self.pokemon_thumb_start_y = mouse_y
                self.pokemon_thumb_start_scroll = self.pokemon_selector_scroll
                return

            # ===== CLIQUE EM ITEM DA LISTA (CORRIGIDO) =====
            # Calcula a posição relativa ao início da lista (incluindo a margem de 4px)
            relative_y = mouse_y - list_area.y - 4  # margem superior de 4px
            if relative_y >= 0:
                item_index = (relative_y // ITEM_HEIGHT) + self.pokemon_selector_scroll
                if 0 <= item_index < len(filtered):
                    self._select_pokemon(filtered[item_index])
                    self.showing_pokemon_selector = False
                    return

        # --- MOUSEMOTION (arraste) ---
        if event.type == pygame.MOUSEMOTION:
            if self.pokemon_dragging_scroll:
                delta_y = mouse_y - self.pokemon_drag_start_y
                scroll_delta = delta_y // ITEM_HEIGHT
                new_scroll = self.pokemon_drag_start_scroll + scroll_delta
                self.pokemon_selector_scroll = max(0, min(max_scroll, new_scroll))
                return

            if self.pokemon_dragging_thumb:
                delta_y = mouse_y - self.pokemon_thumb_start_y
                scrollbar_height = list_area.height - 20
                if scrollbar_height > 0:
                    thumb_ratio = list_area.height / (len(filtered) * ITEM_HEIGHT) if filtered else 1
                    thumb_height = max(20, int(scrollbar_height * thumb_ratio))
                    max_thumb_y = scrollbar_height - thumb_height
                    if max_thumb_y > 0:
                        scroll_delta = (delta_y / max_thumb_y) * max_scroll
                        new_scroll = self.pokemon_thumb_start_scroll + int(scroll_delta)
                        self.pokemon_selector_scroll = max(0, min(max_scroll, new_scroll))
                return

        # --- MOUSEBUTTONUP ---
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.pokemon_dragging_scroll = False
            self.pokemon_dragging_thumb = False
            return

        # --- KEYDOWN ---
        if event.type == pygame.KEYDOWN:
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
                return
            elif event.key == pygame.K_ESCAPE:
                self.showing_pokemon_selector = False
                return

    def _select_pokemon(self, pokemon_id):
        """Aplica a seleção do Pokémon ao alvo correspondente."""
        wave = self.wave_manager.get_current_wave()

        if self.pokemon_selector_target == "enemy":
            if wave and self.pokemon_selector_index < len(wave.enemies):
                wave.enemies[self.pokemon_selector_index].pokemon_id = pokemon_id

        elif self.pokemon_selector_target == "variant":
            if wave and self.editing_variant_index >= 0 and self.editing_variant_index < len(wave.variants):
                variant = wave.variants[self.editing_variant_index]
                if self.pokemon_selector_index < len(variant.enemies):
                    variant.enemies[self.pokemon_selector_index].pokemon_id = pokemon_id

        elif self.pokemon_selector_target == "template":
            templates = WaveTemplateManager.get_all_templates()
            if self.template_selected_index > 0 and self.template_selected_index - 1 < len(templates):
                template = templates[self.template_selected_index - 1]
                if self.pokemon_selector_index < len(template.enemies):
                    template.enemies[self.pokemon_selector_index].pokemon_id = pokemon_id

    def _get_selector_rect(self):
        """Retorna o retângulo do seletor, centralizado no diálogo."""
        sel_w, sel_h = 500, 420
        x = self.rect.x + (self.rect.width - sel_w) // 2
        y = self.rect.y + (self.rect.height - sel_h) // 2
        return pygame.Rect(x, y, sel_w, sel_h)

    def _scrollbar_rect(self, selector_rect):
        """Retorna o retângulo da barra de rolagem."""
        return pygame.Rect(
            selector_rect.right - 18,
            selector_rect.y + 70,
            12,
            selector_rect.height - 110
        )

    def _filter_pokemon(self):
        if not self.pokemon_search:
            return self.available_pokemon_ids
        search_lower = self.pokemon_search.lower()
        filtered = []
        for pid in self.available_pokemon_ids:
            name = self.pokedex.get_name(pid).lower()
            if search_lower in str(pid) or search_lower in name:
                filtered.append(pid)
        return filtered

    def _render_pokemon_selector(self, screen):
        selector_rect = self._get_selector_rect()
        list_area = pygame.Rect(
            selector_rect.x + 10,
            selector_rect.y + 70,
            selector_rect.width - 30,
            selector_rect.height - 110
        )
        ITEM_HEIGHT = 36
        filtered = self._filter_pokemon()
        max_scroll = max(0, len(filtered) - (list_area.height // ITEM_HEIGHT))
        self.pokemon_selector_scroll = max(0, min(max_scroll, self.pokemon_selector_scroll))

        # --- Fundo semi-transparente (overlay) ---
        overlay = pygame.Surface((screen.get_width(), screen.get_height()), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        screen.blit(overlay, (0, 0))

        # --- Fundo do seletor ---
        pygame.draw.rect(screen, self.colors['bg_light'], selector_rect, border_radius=12)
        pygame.draw.rect(screen, self.colors['border_active'], selector_rect, 2, border_radius=12)

        # Título
        title = self._get_font(20, True).render("Selecionar Pokémon", True, self.colors['title'])
        screen.blit(title, (selector_rect.x + 10, selector_rect.y + 8))

        # Botão fechar (X)
        close_rect = pygame.Rect(selector_rect.right - 35, selector_rect.y + 8, 28, 28)
        pygame.draw.rect(screen, self.colors['danger'], close_rect, border_radius=6)
        close_text = self._get_font(18).render("X", True, self.colors['text'])
        screen.blit(close_text, (close_rect.x + 8, close_rect.y + 4))

        # Campo de busca
        search_rect = pygame.Rect(selector_rect.x + 10, selector_rect.y + 40, 200, 26)
        is_search_active = (self.active_input == "pokemon_search")
        border = self.colors['border_active'] if is_search_active else self.colors['border']
        pygame.draw.rect(screen, self.colors['bg_input'], search_rect, border_radius=5)
        pygame.draw.rect(screen, border, search_rect, 1, border_radius=5)

        display = self.pokemon_search if self.pokemon_search else "Buscar..."
        color = self.colors['text'] if self.pokemon_search else self.colors['text_muted']
        search_text = self._get_font(14).render(display, True, color)
        screen.blit(search_text, (search_rect.x + 8, search_rect.y + 4))

        # Contador
        counter = self._get_font(13).render(f"{len(filtered)} Pokémon", True, self.colors['text_dim'])
        screen.blit(counter, (selector_rect.right - 110, selector_rect.y + 44))

        # --- Lista ---
        pygame.draw.rect(screen, self.colors['bg_dark'], list_area, border_radius=6)

        old_clip = screen.get_clip()
        screen.set_clip(list_area)

        list_x = list_area.x + 4
        list_start_y = list_area.y + 4 - self.pokemon_selector_scroll * ITEM_HEIGHT

        for i, pid in enumerate(filtered):
            item_y = list_start_y + i * ITEM_HEIGHT
            if item_y + ITEM_HEIGHT < list_area.y or item_y > list_area.y + list_area.height:
                continue

            item_rect = pygame.Rect(list_x, item_y, list_area.width - 8, ITEM_HEIGHT - 2)
            bg_color = self.colors['bg_light'] if i % 2 == 0 else self.colors['bg_dark']
            pygame.draw.rect(screen, bg_color, item_rect)

            # Sprite
            sprite = self._get_pokemon_sprite(pid, 24)
            screen.blit(sprite, (item_rect.x + 2, item_rect.y + 4))

            # Nome e ID
            name = self.pokedex.get_name(pid)
            text = self._get_font(15).render(f"#{pid:03d} {name}", True, self.colors['text'])
            screen.blit(text, (item_rect.x + 32, item_rect.y + 6))

        screen.set_clip(old_clip)

        # --- Barra de rolagem ---
        total_items = len(filtered)
        visible_items = list_area.height // ITEM_HEIGHT
        if total_items > visible_items:
            scrollbar_rect = self._scrollbar_rect(selector_rect)
            # Fundo
            pygame.draw.rect(screen, self.colors['scrollbar_bg'], scrollbar_rect, border_radius=4)

            # Thumb
            thumb_ratio = visible_items / total_items
            thumb_height = max(20, int(scrollbar_rect.height * thumb_ratio))
            max_scroll = max(0, total_items - visible_items)
            scroll_ratio = self.pokemon_selector_scroll / max_scroll if max_scroll > 0 else 0
            thumb_y = scrollbar_rect.y + int(scroll_ratio * (scrollbar_rect.height - thumb_height))
            thumb_rect = pygame.Rect(scrollbar_rect.x, thumb_y, scrollbar_rect.width, thumb_height)
            pygame.draw.rect(screen, self.colors['scrollbar_thumb'], thumb_rect, border_radius=4)

        # Instruções
        info = self._get_font(12).render("Roda do mouse para rolar | Clique no Pokémon para selecionar", True, self.colors['text_muted'])
        screen.blit(info, (selector_rect.x + 10, selector_rect.bottom - 22))

    # --- Render principal ---
    def render(self, screen):
        if not self.visible:
            return

        # Overlay escuro fora do diálogo
        if not self.showing_pokemon_selector:
            overlay = pygame.Surface((screen.get_width(), screen.get_height()))
            overlay.set_alpha(180)
            overlay.fill((0, 0, 0))
            screen.blit(overlay, (0, 0))

        # Fundo do diálogo
        pygame.draw.rect(screen, self.colors['bg'], self.rect, border_radius=12)
        pygame.draw.rect(screen, self.colors['border'], self.rect, 2, border_radius=12)

        # Barra de título
        title_bar = pygame.Rect(self.rect.x, self.rect.y, self.rect.width, 38)
        pygame.draw.rect(screen, self.colors['bg_light'], title_bar, border_top_left_radius=12,
                         border_top_right_radius=12)

        title = self._get_font(22, True).render("Configuração de Waves", True, self.colors['title'])
        screen.blit(title, (self.rect.x + self.margin, self.rect.y + 10))

        # Abas
        tab_names = ["Waves", "Composição", "Variants", "Templates"]
        for i, name in enumerate(tab_names):
            tab_button = self.tab_buttons[i]
            is_active = self.selected_tab == ["waves", "composition", "variants", "templates"][i]

            if is_active:
                color = self.colors['tab_active']
                border = self.colors['border_active']
            else:
                color = self.colors['tab_inactive']
                border = self.colors['border']

            pygame.draw.rect(screen, color, tab_button, border_radius=6)
            pygame.draw.rect(screen, border, tab_button, 1, border_radius=6)

            text = self._get_font(15).render(name, True, self.colors['text'])
            text_x = tab_button.x + (tab_button.width - text.get_width()) // 2
            text_y = tab_button.y + (tab_button.height - text.get_height()) // 2
            screen.blit(text, (text_x, text_y))

        # ===== CONTEÚDO DA ABA (primeiro) =====
        if self.selected_tab == "waves":
            self._render_waves_tab(screen)
        elif self.selected_tab == "composition":
            self._render_composition_tab(screen)
        elif self.selected_tab == "variants":
            self._render_variants_tab(screen)
        elif self.selected_tab == "templates":
            self._render_templates_tab(screen)

        # ===== DROPDOWNS (por cima do conteúdo) =====
        # Dropdown de Paths
        if self.path_dropdown_open and self.selected_tab == "waves":
            self._render_path_dropdown(screen)

        # Dropdown de Templates
        if self.template_combo_open and self.selected_tab == "composition":
            self._render_template_dropdown(screen)

        # ===== EDITORES (por cima) =====
        if self.variant_editor_open:
            self._render_variant_editor(screen)
        if self.template_editor_open:
            self._render_template_editor(screen)

        # ===== SELETOR DE POKÉMON (por cima de TUDO) =====
        if self.showing_pokemon_selector:
            self._render_pokemon_selector(screen)

        # Botões Salvar/Cancelar
        self._render_buttons(screen)

        if "total" in self.input_errors:
            error_text = self._get_font(14).render(self.input_errors["total"], True, (255, 100, 100))
            screen.blit(error_text, (self.rect.x + 20, self.rect.bottom - 60))

    def _render_path_dropdown(self, screen):
        """Renderiza o dropdown de paths (separado para ficar por cima)"""
        path_count = len(self.path_manager.paths)
        if path_count == 0:
            return

        list_rect = self._get_path_dropdown_rect()

        # Sombra do dropdown
        shadow = pygame.Surface((list_rect.width + 4, list_rect.height + 4), pygame.SRCALPHA)
        shadow.fill((0, 0, 0, 160))
        screen.blit(shadow, (list_rect.x - 2, list_rect.y - 2))

        pygame.draw.rect(screen, self.colors['bg_dropdown'], list_rect, border_radius=5)
        pygame.draw.rect(screen, self.colors['border_dropdown'], list_rect, 2, border_radius=5)

        for i in range(path_count):
            item_rect = pygame.Rect(list_rect.x + 4, list_rect.y + 2 + i * 26, list_rect.width - 8, 22)
            is_hover = (i == self.path_hovered_index)
            is_sel = (i == self.path_selected_index)

            bg = self.colors['dropdown_item_hover'] if is_hover else self.colors['bg_dropdown']
            if is_sel:
                bg = self.colors['accent']
            pygame.draw.rect(screen, bg, item_rect, border_radius=4)

            text = self._get_font(13).render(f"Path {i + 1}", True, self.colors['text'])
            screen.blit(text, (item_rect.x + 8, item_rect.y + 3))
            if is_sel:
                check = self._get_font(13).render("✓", True, self.colors['radio_selected'])
                screen.blit(check, (item_rect.right - 20, item_rect.y + 3))

    def _render_template_dropdown(self, screen):
        """Renderiza o dropdown de templates (separado para ficar por cima)"""
        templates = WaveTemplateManager.get_all_templates()
        if not templates:
            return

        list_rect = self._get_template_dropdown_rect()

        # Sombra do dropdown
        shadow = pygame.Surface((list_rect.width + 4, list_rect.height + 4), pygame.SRCALPHA)
        shadow.fill((0, 0, 0, 160))
        screen.blit(shadow, (list_rect.x - 2, list_rect.y - 2))

        pygame.draw.rect(screen, self.colors['bg_dropdown'], list_rect, border_radius=5)
        pygame.draw.rect(screen, self.colors['border_dropdown'], list_rect, 2, border_radius=5)

        wave = self.wave_manager.get_current_wave()

        for i, template in enumerate(templates):
            item_rect = pygame.Rect(list_rect.x + 4, list_rect.y + 2 + i * 28, list_rect.width - 8, 22)
            is_hover = (i == self.template_combo_hovered_index)
            is_sel = (wave and template.template_id == wave.template_id)

            bg = self.colors['dropdown_item_hover'] if is_hover else self.colors['bg_dropdown']
            if is_sel:
                bg = self.colors['accent']
            pygame.draw.rect(screen, bg, item_rect, border_radius=4)

            text = self._get_font(13).render(template.name, True, self.colors['text'])
            screen.blit(text, (item_rect.x + 8, item_rect.y + 3))
            if is_sel:
                check = self._get_font(13).render("✓", True, self.colors['radio_selected'])
                screen.blit(check, (item_rect.right - 20, item_rect.y + 3))

    # --- Render de abas ---
    def _render_buttons(self, screen):
        color = self.colors['success'] if self.hovered_button == "save" else (50, 150, 50)
        pygame.draw.rect(screen, color, self.save_button, border_radius=8)
        pygame.draw.rect(screen, (255, 255, 255), self.save_button, 1, border_radius=8)
        text = self._get_font(18).render("Salvar", True, (255, 255, 255))
        text_x = self.save_button.x + (self.save_button.width - text.get_width()) // 2
        text_y = self.save_button.y + (self.save_button.height - text.get_height()) // 2
        screen.blit(text, (text_x, text_y))

        color = self.colors['danger'] if self.hovered_button == "cancel" else (180, 50, 50)
        pygame.draw.rect(screen, color, self.cancel_button, border_radius=8)
        pygame.draw.rect(screen, (255, 255, 255), self.cancel_button, 1, border_radius=8)
        text = self._get_font(18).render("Cancelar", True, (255, 255, 255))
        text_x = self.cancel_button.x + (self.cancel_button.width - text.get_width()) // 2
        text_y = self.cancel_button.y + (self.cancel_button.height - text.get_height()) // 2
        screen.blit(text, (text_x, text_y))

    def _render_button(self, screen, rect, button_id, label, disabled=False):
        is_hovered = self.hovered_button == button_id
        if disabled:
            color = (50, 50, 60)
            text_color = self.colors['text_muted']
        else:
            color = self.colors['bg_light'] if is_hovered else self.colors['bg_dark']
            text_color = self.colors['text']

        pygame.draw.rect(screen, color, rect, border_radius=5)
        pygame.draw.rect(screen, self.colors['border'], rect, 1, border_radius=5)

        text = self._get_font(13).render(label, True, text_color)
        text_x = rect.x + (rect.width - text.get_width()) // 2
        text_y = rect.y + (rect.height - text.get_height()) // 2
        screen.blit(text, (text_x, text_y))

    def _render_waves_tab(self, screen):
        label = self._get_font(15).render("Lista de Waves:", True, self.colors['text_dim'])
        screen.blit(label, (self.waves_label.x, self.waves_label.y))

        self._render_button(screen, self.add_wave_button, "add_wave", "+ Nova")
        self._render_button(screen, self.remove_wave_button, "remove_wave", "- Remover")
        self._render_button(screen, self.duplicate_wave_button, "duplicate_wave", "Duplicar")

        # Seletor de Path (apenas o botão, sem o dropdown)
        path_label = self._get_font(13).render("Path:", True, self.colors['text_dim'])
        screen.blit(path_label, (self.path_label.x, self.path_label.y))

        path_count = len(self.path_manager.paths)
        path_text = f"P{self.path_selected_index + 1}" if path_count > 0 else "Nenhum"

        border = self.colors['border_active'] if self.path_dropdown_open else self.colors['border']
        pygame.draw.rect(screen, self.colors['bg_input'], self.path_selector_rect, border_radius=5)
        pygame.draw.rect(screen, border, self.path_selector_rect, 1, border_radius=5)

        text = self._get_font(13).render(path_text, True, self.colors['text'])
        screen.blit(text, (self.path_selector_rect.x + 8, self.path_selector_rect.y + 4))

        arrow = self._get_font(13).render("▼" if not self.path_dropdown_open else "▲", True, self.colors['text_muted'])
        screen.blit(arrow, (self.path_selector_rect.right - 18, self.path_selector_rect.y + 4))

        # Lista de waves
        pygame.draw.rect(screen, self.colors['bg_dark'], self.waves_list_area, border_radius=6)

        old_clip = screen.get_clip()
        screen.set_clip(self.waves_list_area)

        list_x = self.waves_list_area.x + 4
        list_start_y = self.waves_list_area.y + 2 - self.waves_scroll * self.wave_item_height

        for i, wave in enumerate(self.wave_manager.waves):
            item_y = list_start_y + i * self.wave_item_height
            if item_y + self.wave_item_height < self.waves_list_area.y or \
                    item_y > self.waves_list_area.y + self.waves_list_area.height:
                continue

            item_rect = pygame.Rect(list_x, item_y, self.waves_list_area.width - 8, self.wave_item_height - 2)
            is_selected = (i == self.selected_wave_index)
            bg_color = self.colors['accent'] if is_selected else \
                (self.colors['bg_light'] if i % 2 == 0 else self.colors['bg_dark'])

            pygame.draw.rect(screen, bg_color, item_rect)
            if is_selected:
                pygame.draw.rect(screen, self.colors['border_active'], item_rect, 1)

            wave_name = wave.name
            indicators = []
            if wave.template_id:
                indicators.append("[T]")
            if wave.use_variants and wave.variants:
                indicators.append("[V]")
            if indicators:
                wave_name += " " + " ".join(indicators)

            # Mostra o path da wave
            path_idx = wave.path_index if hasattr(wave, 'path_index') else 0
            wave_name += f" (P{path_idx + 1})"

            name_text = self._get_font(14).render(wave_name, True, self.colors['text'])
            screen.blit(name_text, (item_rect.x + 5, item_rect.y + 2))

            info = f"{wave.wave_size} inim | Lv.{wave.min_level}-{wave.max_level}"
            info_text = self._get_font(12).render(info, True, self.colors['text_dim'])
            screen.blit(info_text, (item_rect.x + 5, item_rect.y + 17))

        screen.set_clip(old_clip)

        if len(self.wave_manager.waves) > self.waves_per_page:
            info = f"{self.waves_scroll + 1}-{min(self.waves_scroll + self.waves_per_page, len(self.wave_manager.waves))} de {len(self.wave_manager.waves)}"
            text = self._get_font(12).render(info, True, self.colors['text_muted'])
            text_x = self.waves_list_area.x + (self.waves_list_area.width - text.get_width()) // 2
            screen.blit(text, (text_x, self.waves_list_area.bottom + 4))

    def _render_composition_tab(self, screen):
        wave = self.wave_manager.get_current_wave()
        if not wave:
            no_text = self._get_font(18).render("Selecione uma wave na aba Waves", True, self.colors['text_dim'])
            text_x = self.rect.x + (self.rect.width - no_text.get_width()) // 2
            text_y = self.rect.y + 250
            screen.blit(no_text, (text_x, text_y))
            return

        info_text = ""
        if wave.template_id:
            template = WaveTemplateManager.get_template(wave.template_id)
            template_name = template.name if template else "desconhecido"
            info_text = f"Usando template: {template_name}"
            color = self.colors['warning']
        elif wave.use_variants and wave.variants:
            info_text = "Usando Variants"
            color = self.colors['info']
        else:
            info_text = "Composição própria"
            color = self.colors['text_dim']

        info = self._get_font(13).render(info_text, True, color)
        screen.blit(info, (self.comp_info_rect.x, self.comp_info_rect.y + 2))

        can_edit = not wave.template_id
        self._render_button(screen, self.add_enemy_button, "add_enemy", "+ Adicionar", not can_edit)
        self._render_button(screen, self.equalize_button, "equalize", "Distribuir", not can_edit)
        self._render_button(screen, self.clear_enemies_button, "clear_enemies", "Limpar", not can_edit)

        # ===== SELETOR DE TEMPLATE =====
        templates = WaveTemplateManager.get_all_templates()

        template_label = self._get_font(13).render("Template:", True, self.colors['text_dim'])
        screen.blit(template_label, (self.template_label.x, self.template_label.y))

        border = self.colors['border_active'] if self.template_combo_open else self.colors['border']
        pygame.draw.rect(screen, self.colors['bg_input'], self.template_selector_rect, border_radius=5)
        pygame.draw.rect(screen, border, self.template_selector_rect, 1, border_radius=5)

        # Texto do template selecionado
        if wave.template_id:
            template = WaveTemplateManager.get_template(wave.template_id)
            template_name = template.name if template else "Template removido"
        else:
            template_name = "Nenhum"

        text = self._get_font(13).render(template_name, True, self.colors['text'])
        screen.blit(text, (self.template_selector_rect.x + 8, self.template_selector_rect.y + 4))

        arrow = self._get_font(13).render("▼" if not self.template_combo_open else "▲", True, self.colors['text_muted'])
        screen.blit(arrow, (self.template_selector_rect.right - 18, self.template_selector_rect.y + 4))

        # Botão "Limpar"
        self._render_button(screen, self.clear_template_rect, "clear_template", "Limpar")

        # Lista de inimigos
        pygame.draw.rect(screen, self.colors['bg_dark'], self.enemies_list_area, border_radius=6)

        old_clip = screen.get_clip()
        screen.set_clip(self.enemies_list_area)

        list_x = self.enemies_list_area.x + 4
        list_start_y = self.enemies_list_area.y + 2 - self.enemies_scroll * self.enemy_item_height

        # ===== PEGA OS INIMIGOS CORRETAMENTE =====
        # Se tem template, usa os inimigos do template
        # Senão, usa os inimigos da wave
        if wave.template_id:
            template = WaveTemplateManager.get_template(wave.template_id)
            enemies = template.enemies if template else []
        else:
            enemies = wave.enemies

        for i, enemy in enumerate(enemies):
            item_y = list_start_y + i * self.enemy_item_height
            if item_y + self.enemy_item_height < self.enemies_list_area.y or \
                    item_y > self.enemies_list_area.y + self.enemies_list_area.height:
                continue

            item_rect = pygame.Rect(list_x, item_y, self.enemies_list_area.width - 8, self.enemy_item_height - 2)
            bg_color = self.colors['bg_light'] if i % 2 == 0 else self.colors['bg_dark']
            pygame.draw.rect(screen, bg_color, item_rect)
            pygame.draw.rect(screen, self.colors['border_light'], item_rect, 1)

            sprite = self._get_pokemon_sprite(enemy.pokemon_id, 28)
            screen.blit(sprite, (item_rect.x + 4, item_rect.y + 2))

            name = self.pokedex.get_name(enemy.pokemon_id)
            name_text = self._get_font(14).render(name, True, self.colors['text'])
            screen.blit(name_text, (item_rect.x + 36, item_rect.y + 2))

            id_text = self._get_font(11).render(f"#{enemy.pokemon_id}", True, self.colors['text_muted'])
            screen.blit(id_text, (item_rect.x + 36, item_rect.y + 20))

            percent_rect = pygame.Rect(self.enemies_list_area.right - 88, item_y + 8, 50, 20)
            is_active = self.active_input == f"percent_{i}"
            border = self.colors['border_active'] if is_active else self.colors['border']
            pygame.draw.rect(screen, self.colors['bg_input'], percent_rect, border_radius=4)
            pygame.draw.rect(screen, border, percent_rect, 1, border_radius=4)

            display = self.input_texts.get(f"percent_{i}",
                                           f"{enemy.percentage:.1f}") if is_active else f"{enemy.percentage:.1f}"
            pct_text = self._get_font(13).render(display, True, self.colors['text'])
            screen.blit(pct_text, (percent_rect.x + 4, percent_rect.y + 2))

            pct_symbol = self._get_font(11).render("%", True, self.colors['text_muted'])
            screen.blit(pct_symbol, (percent_rect.right + 2, percent_rect.y + 3))

            # Só mostra o botão remover se não tiver template
            if can_edit:
                remove_rect = pygame.Rect(self.enemies_list_area.right - 28, item_y + 4, 18, 18)
                pygame.draw.rect(screen, self.colors['danger'], remove_rect, border_radius=4)
                pygame.draw.line(screen, self.colors['text'],
                                 (remove_rect.x + 4, remove_rect.y + 4),
                                 (remove_rect.right - 4, remove_rect.bottom - 4), 2)
                pygame.draw.line(screen, self.colors['text'],
                                 (remove_rect.right - 4, remove_rect.y + 4),
                                 (remove_rect.x + 4, remove_rect.bottom - 4), 2)

        screen.set_clip(old_clip)

        # ===== CALCULA TOTAL CORRETAMENTE =====
        if wave.template_id:
            template = WaveTemplateManager.get_template(wave.template_id)
            enemies = template.enemies if template else []
            total = sum(e.percentage for e in enemies)
            is_valid = abs(total - 100.0) < 0.01
            color = (100, 255, 100) if is_valid else (255, 100, 100)
            total_text = self._get_font(14).render(f"Total: {total:.1f}%", True, color)
            screen.blit(total_text, (self.total_rect.x, self.total_rect.y))
        else:
            total = sum(e.percentage for e in wave.enemies)
            is_valid = abs(total - 100.0) < 0.01
            color = (100, 255, 100) if is_valid else (255, 100, 100)
            total_text = self._get_font(14).render(f"Total: {total:.1f}%", True, color)
            screen.blit(total_text, (self.total_rect.x, self.total_rect.y))

            if not is_valid:
                warn = self._get_font(12).render("(Deve ser 100%)", True, (255, 100, 100))
                screen.blit(warn, (self.total_rect.x + 120, self.total_rect.y))

    def _render_variants_tab(self, screen):
        wave = self.wave_manager.get_current_wave()
        if not wave:
            no_text = self._get_font(18).render("Selecione uma wave na aba Waves", True, self.colors['text_dim'])
            text_x = self.rect.x + (self.rect.width - no_text.get_width()) // 2
            text_y = self.rect.y + 250
            screen.blit(no_text, (text_x, text_y))
            return

        info_lines = [
            "Variants: Versões diferentes da wave para cada período.",
            "Crie uma variant e edite para configurar os Pokémon."
        ]
        for i, line in enumerate(info_lines):
            color = self.colors['text_dim'] if i == 0 else self.colors['text_muted']
            text = self._get_font(12).render(line, True, color)
            screen.blit(text, (self.variant_info_rect.x, self.variant_info_rect.y + i * 16))

        self._render_button(screen, self.add_variant_button, "add_variant", "+ Nova Variant")
        self._render_button(screen, self.remove_variant_button, "remove_variant", "- Remover")
        self._render_button(screen, self.edit_variant_button, "edit_variant", "Editar")

        status_text = "ATIVO" if wave.use_variants else "INATIVO"
        color = self.colors['success'] if wave.use_variants else self.colors['text_muted']
        status = self._get_font(14).render(f"Status: {status_text}", True, color)
        screen.blit(status, (self.rect.x + self.margin, self.variants_list_area.bottom + 6))

        pygame.draw.rect(screen, self.colors['bg_dark'], self.variants_list_area, border_radius=6)

        old_clip = screen.get_clip()
        screen.set_clip(self.variants_list_area)

        list_x = self.variants_list_area.x + 4
        list_start_y = self.variants_list_area.y + 2 - self.variants_scroll * self.variant_item_height

        cond_labels = {c["id"]: c["label"] for c in self.condition_options}

        for i, variant in enumerate(wave.variants):
            item_y = list_start_y + i * self.variant_item_height
            if item_y + self.variant_item_height < self.variants_list_area.y or \
                    item_y > self.variants_list_area.y + self.variants_list_area.height:
                continue

            item_rect = pygame.Rect(list_x, item_y, self.variants_list_area.width - 8, self.variant_item_height - 2)
            is_selected = (i == self.selected_variant_index)
            bg_color = self.colors['accent'] if is_selected else \
                (self.colors['bg_light'] if i % 2 == 0 else self.colors['bg_dark'])

            pygame.draw.rect(screen, bg_color, item_rect)
            if is_selected:
                pygame.draw.rect(screen, self.colors['border_active'], item_rect, 1)

            cond_label = cond_labels.get(variant.condition, "Qualquer")
            cond_text = self._get_font(14).render(f"Período: {cond_label}", True, self.colors['text'])
            screen.blit(cond_text, (item_rect.x + 5, item_rect.y + 3))

            enemy_count = len(variant.enemies)
            info = f"{enemy_count} Pokémon | Nível: {variant.min_level}-{variant.max_level}"
            info_text = self._get_font(12).render(info, True, self.colors['text_dim'])
            screen.blit(info_text, (item_rect.x + 5, item_rect.y + 22))

        screen.set_clip(old_clip)

        if len(wave.variants) > self.variants_per_page:
            info = f"{self.variants_scroll + 1}-{min(self.variants_scroll + self.variants_per_page, len(wave.variants))} de {len(wave.variants)}"
            text = self._get_font(12).render(info, True, self.colors['text_muted'])
            text_x = self.variants_list_area.x + (self.variants_list_area.width - text.get_width()) // 2
            screen.blit(text, (text_x, self.variants_list_area.bottom + 4))

    def _render_templates_tab(self, screen):
        templates = WaveTemplateManager.get_all_templates()

        info_lines = [
            "Templates: Listas de Pokémon reutilizáveis.",
            "Crie um template e use em qualquer wave."
        ]
        for i, line in enumerate(info_lines):
            color = self.colors['text_dim'] if i == 0 else self.colors['text_muted']
            text = self._get_font(12).render(line, True, color)
            screen.blit(text, (self.template_info_rect.x, self.template_info_rect.y + i * 16))

        self._render_button(screen, self.new_template_button, "new_template", "+ Novo Template")
        self._render_button(screen, self.delete_template_button, "delete_template", "- Remover")
        self._render_button(screen, self.edit_template_button, "edit_template", "Editar")

        total_text = self._get_font(13).render(f"Templates: {len(templates)}", True, self.colors['text_dim'])
        screen.blit(total_text, (self.rect.x + self.margin, self.templates_list_area.bottom + 6))

        pygame.draw.rect(screen, self.colors['bg_dark'], self.templates_list_area, border_radius=6)

        old_clip = screen.get_clip()
        screen.set_clip(self.templates_list_area)

        list_x = self.templates_list_area.x + 4
        list_start_y = self.templates_list_area.y + 2 - self.templates_scroll * self.template_item_height

        for i, template in enumerate(templates):
            item_y = list_start_y + i * self.template_item_height
            if item_y + self.template_item_height < self.templates_list_area.y or \
                    item_y > self.templates_list_area.y + self.templates_list_area.height:
                continue

            item_rect = pygame.Rect(list_x, item_y, self.templates_list_area.width - 8, self.template_item_height - 2)
            is_selected = (i + 1 == self.template_selected_index)
            bg_color = self.colors['accent'] if is_selected else \
                (self.colors['bg_light'] if i % 2 == 0 else self.colors['bg_dark'])

            pygame.draw.rect(screen, bg_color, item_rect)
            if is_selected:
                pygame.draw.rect(screen, self.colors['border_active'], item_rect, 1)

            name_text = self._get_font(14).render(template.name, True, self.colors['text'])
            screen.blit(name_text, (item_rect.x + 5, item_rect.y + 2))

            enemy_count = len(template.enemies)
            info = f"{enemy_count} Pokémon | Nível: {template.min_level}-{template.max_level}"
            info_text = self._get_font(12).render(info, True, self.colors['text_dim'])
            screen.blit(info_text, (item_rect.x + 5, item_rect.y + 20))

        screen.set_clip(old_clip)

        if len(templates) > self.templates_per_page:
            info = f"{self.templates_scroll + 1}-{min(self.templates_scroll + self.templates_per_page, len(templates))} de {len(templates)}"
            text = self._get_font(12).render(info, True, self.colors['text_muted'])
            text_x = self.templates_list_area.x + (self.templates_list_area.width - text.get_width()) // 2
            screen.blit(text, (text_x, self.templates_list_area.bottom + 4))