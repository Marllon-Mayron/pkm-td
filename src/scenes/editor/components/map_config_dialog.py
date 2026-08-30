# src/scenes/editor/components/map_config_dialog.py

import pygame
import os


class MapConfigDialog:
    def __init__(self, x, y, width, height, current_width, current_height,
                 current_chapter=1, current_phase=1, current_name="Fase",
                 current_localization_type="default", current_custom_folder="",
                 current_unlock_chapter=1, current_unlock_phase=1,
                 current_day_night_mode="random", current_base_weather="random"):

        # ===== DIMENSÕES DO DIÁLOGO =====
        self.rect = pygame.Rect(x, y, width, height)
        self.visible = True
        self.focused = True

        # ===== MARGENS E ESPAÇAMENTOS =====
        self.margin = 20
        self.label_width = 130
        self.input_width = 150
        self.row_height = 32
        self.section_spacing = 10

        # ===== VALORES ATUAIS =====
        self.current_width = current_width
        self.current_height = current_height
        self.current_chapter = current_chapter
        self.current_phase = current_phase
        self.current_name = current_name
        self.current_localization_type = current_localization_type
        self.current_custom_folder = current_custom_folder
        self.current_unlock_chapter = current_unlock_chapter
        self.current_unlock_phase = current_unlock_phase
        self.current_day_night_mode = current_day_night_mode
        self.current_base_weather = current_base_weather

        # ===== VALORES TEMPORÁRIOS =====
        self.temp_width = str(current_width)
        self.temp_height = str(current_height)
        self.temp_chapter = str(current_chapter)
        self.temp_phase = str(current_phase)
        self.temp_name = current_name
        self.temp_localization_type = current_localization_type
        self.temp_custom_folder = current_custom_folder
        self.temp_unlock_chapter = str(current_unlock_chapter)
        self.temp_unlock_phase = str(current_unlock_phase)
        self.temp_day_night_mode = current_day_night_mode
        self.temp_base_weather = current_base_weather

        self.active_input = "name"

        # ===== CALCULA POSIÇÕES =====
        self._calculate_positions()

        # ===== BOTÕES =====
        button_width = 90
        button_height = 32
        total_buttons_width = button_width * 2 + 15
        button_x = self.rect.x + (self.rect.width - total_buttons_width) // 2
        button_y = self.rect.y + self.rect.height - 55

        self.confirm_rect = pygame.Rect(button_x, button_y, button_width, button_height)
        self.cancel_rect = pygame.Rect(button_x + button_width + 15, button_y, button_width, button_height)

        # ===== VARIÁVEIS DE UI =====
        self.dragging = False
        self.drag_offset_x = 0
        self.drag_offset_y = 0
        self.hovered_button = None

        # Cache de fontes
        self._font_cache = {}

        # ===== CORES =====
        self.colors = {
            'bg': (45, 48, 60),
            'bg_input': (55, 58, 72),
            'border': (80, 85, 105),
            'border_active': (100, 150, 255),
            'border_hover': (120, 170, 255),
            'text': (235, 235, 245),
            'text_dim': (180, 185, 200),
            'text_muted': (130, 135, 155),
            'title': (255, 215, 0),
            'accent': (80, 110, 180),
            'success': (60, 180, 60),
            'danger': (200, 60, 60),
            'radio_selected': (100, 150, 255),
            'radio_unselected': (80, 85, 105),
        }

    def _get_font(self, size, bold=False):
        """Obtém fonte do cache"""
        key = (size, bold)
        if key not in self._font_cache:
            font = pygame.font.Font(None, size)
            if bold:
                font.set_bold(True)
            self._font_cache[key] = font
        return self._font_cache[key]

    def _calculate_positions(self):
        """Calcula posições de todos os elementos baseado no tamanho do diálogo"""
        x, y, w, h = self.rect
        m = self.margin
        label_w = self.label_width
        input_w = self.input_width

        # Altura disponível para conteúdo (excluindo título e botões)
        content_top = y + 50
        content_bottom = y + h - 60
        content_height = content_bottom - content_top

        # ===== LINHA 1: Nome =====
        row1_y = content_top
        self.name_label_rect = pygame.Rect(x + m, row1_y, label_w, self.row_height)
        self.name_input_rect = pygame.Rect(x + m + label_w + 5, row1_y, w - m * 2 - label_w - 5, self.row_height)

        # ===== LINHA 2: Largura e Altura (lado a lado) =====
        row2_y = row1_y + self.row_height + 8
        half_width = (w - m * 2 - 10) // 2

        self.width_label_rect = pygame.Rect(x + m, row2_y, 80, self.row_height)
        self.width_input_rect = pygame.Rect(x + m + 85, row2_y, 70, self.row_height)

        self.height_label_rect = pygame.Rect(x + m + half_width, row2_y, 80, self.row_height)
        self.height_input_rect = pygame.Rect(x + m + half_width + 85, row2_y, 70, self.row_height)

        # ===== LINHA 3: Capítulo e Fase (lado a lado) =====
        row3_y = row2_y + self.row_height + 8

        self.chapter_label_rect = pygame.Rect(x + m, row3_y, 80, self.row_height)
        self.chapter_input_rect = pygame.Rect(x + m + 85, row3_y, 70, self.row_height)

        self.phase_label_rect = pygame.Rect(x + m + half_width, row3_y, 80, self.row_height)
        self.phase_input_rect = pygame.Rect(x + m + half_width + 85, row3_y, 70, self.row_height)

        # ===== LINHA 4: Localização (radio buttons) =====
        row4_y = row3_y + self.row_height + 12

        self.loc_label_rect = pygame.Rect(x + m, row4_y, self.label_width, self.row_height)

        # Radio buttons na mesma linha
        radio_y = row4_y + 4
        radio_size = 18

        self.default_radio_rect = pygame.Rect(x + m + self.label_width + 5, radio_y, radio_size, radio_size)
        self.custom_radio_rect = pygame.Rect(x + m + self.label_width + 120, radio_y, radio_size, radio_size)

        # ===== LINHA 5: Pasta Custom (aparece apenas se custom) =====
        row5_y = row4_y + self.row_height + 6

        self.folder_label_rect = pygame.Rect(x + m, row5_y, 60, self.row_height)
        self.folder_input_rect = pygame.Rect(x + m + 65, row5_y, 230, self.row_height)
        self.browse_button_rect = pygame.Rect(x + m + 300, row5_y, 40, self.row_height)

        # ===== LINHA 6: Unlock (aparece apenas se custom) =====
        row6_y = row5_y + self.row_height + 6

        self.unlock_label_rect = pygame.Rect(x + m, row6_y, 110, self.row_height)

        # Capítulo unlock
        self.unlock_chapter_label_rect = pygame.Rect(x + m + 115, row6_y, 60, self.row_height)
        self.unlock_chapter_input_rect = pygame.Rect(x + m + 180, row6_y, 50, self.row_height)

        # Fase unlock
        self.unlock_phase_label_rect = pygame.Rect(x + m + 240, row6_y, 50, self.row_height)
        self.unlock_phase_input_rect = pygame.Rect(x + m + 295, row6_y, 50, self.row_height)

        # ===== LINHA 7: Dia/Noite =====
        row7_y = row6_y + self.row_height + 12

        self.day_night_label_rect = pygame.Rect(x + m, row7_y, 90, self.row_height)

        # Radio buttons de dia/noite na mesma linha
        dn_radio_y = row7_y + 4
        dn_spacing = 90

        self.day_night_random_rect = pygame.Rect(x + m + 95, dn_radio_y, radio_size, radio_size)
        self.day_night_day_rect = pygame.Rect(x + m + 95 + dn_spacing, dn_radio_y, radio_size, radio_size)
        self.day_night_night_rect = pygame.Rect(x + m + 95 + dn_spacing * 2, dn_radio_y, radio_size, radio_size)

        # ===== LINHA 8: Clima Base =====
        row8_y = row7_y + self.row_height + 6

        self.weather_label_rect = pygame.Rect(x + m, row8_y, 90, self.row_height)

        # Radio buttons de clima na mesma linha
        w_radio_y = row8_y + 4
        w_spacing = 80

        self.weather_random_rect = pygame.Rect(x + m + 95, w_radio_y, radio_size, radio_size)
        self.weather_none_rect = pygame.Rect(x + m + 95 + w_spacing, w_radio_y, radio_size, radio_size)
        self.weather_sunny_rect = pygame.Rect(x + m + 95 + w_spacing * 2, w_radio_y, radio_size, radio_size)
        self.weather_rain_rect = pygame.Rect(x + m + 95 + w_spacing * 3, w_radio_y, radio_size, radio_size)

    def _update_button_positions(self):
        """Atualiza posições dos botões após arrastar"""
        button_width = 90
        button_height = 32
        total_buttons_width = button_width * 2 + 15
        button_x = self.rect.x + (self.rect.width - total_buttons_width) // 2
        button_y = self.rect.y + self.rect.height - 55

        self.confirm_rect.x = button_x
        self.confirm_rect.y = button_y
        self.cancel_rect.x = button_x + button_width + 15
        self.cancel_rect.y = button_y

    def handle_event(self, event):
        """Processa eventos do diálogo"""
        if not self.visible:
            return None

        if event.type == pygame.KEYDOWN:
            return self._handle_keydown(event)
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                return self._handle_mousedown(event)
            elif event.button == 2:  # Middle click - arrastar
                mouse_pos = pygame.mouse.get_pos()
                if self.rect.collidepoint(mouse_pos):
                    self.dragging = True
                    self.drag_offset_x = mouse_pos[0] - self.rect.x
                    self.drag_offset_y = mouse_pos[1] - self.rect.y
                    return None
        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 2 and self.dragging:
                self.dragging = False
                return None
        elif event.type == pygame.MOUSEMOTION:
            if self.dragging:
                mouse_pos = pygame.mouse.get_pos()
                self.rect.x = mouse_pos[0] - self.drag_offset_x
                self.rect.y = mouse_pos[1] - self.drag_offset_y
                self._calculate_positions()
                self._update_button_positions()
                return None

            # Atualiza hover dos botões
            mouse_pos = pygame.mouse.get_pos()
            self.hovered_button = None
            if self.confirm_rect.collidepoint(mouse_pos):
                self.hovered_button = "confirm"
            elif self.cancel_rect.collidepoint(mouse_pos):
                self.hovered_button = "cancel"

        return None

    def _handle_keydown(self, event):
        """Processa teclas pressionadas"""
        if event.key == pygame.K_RETURN:
            return self.confirm()
        elif event.key == pygame.K_ESCAPE:
            self.visible = False
            return None
        elif event.key == pygame.K_TAB:
            inputs = ["name", "width", "height", "chapter", "phase"]
            if self.temp_localization_type == "custom":
                inputs.extend(["custom_folder", "unlock_chapter", "unlock_phase"])
            current_index = inputs.index(self.active_input) if self.active_input in inputs else 0
            self.active_input = inputs[(current_index + 1) % len(inputs)]
            return None
        elif event.key == pygame.K_BACKSPACE:
            if self.active_input == "name":
                self.temp_name = self.temp_name[:-1]
            elif self.active_input == "width":
                self.temp_width = self.temp_width[:-1]
            elif self.active_input == "height":
                self.temp_height = self.temp_height[:-1]
            elif self.active_input == "chapter":
                self.temp_chapter = self.temp_chapter[:-1]
            elif self.active_input == "phase":
                self.temp_phase = self.temp_phase[:-1]
            elif self.active_input == "custom_folder":
                self.temp_custom_folder = self.temp_custom_folder[:-1]
            elif self.active_input == "unlock_chapter":
                self.temp_unlock_chapter = self.temp_unlock_chapter[:-1]
            elif self.active_input == "unlock_phase":
                self.temp_unlock_phase = self.temp_unlock_phase[:-1]
            return None
        else:
            if self.active_input == "name":
                if event.unicode.isprintable() and event.unicode not in ['/', '\\', ':', '*', '?', '"', '<', '>', '|']:
                    self.temp_name += event.unicode
            elif self.active_input == "custom_folder":
                if event.unicode.isalnum() or event.unicode in ['_', '-']:
                    self.temp_custom_folder += event.unicode
            elif event.unicode.isdigit():
                if self.active_input == "width":
                    self.temp_width += event.unicode
                elif self.active_input == "height":
                    self.temp_height += event.unicode
                elif self.active_input == "chapter":
                    self.temp_chapter += event.unicode
                elif self.active_input == "phase":
                    self.temp_phase += event.unicode
                elif self.active_input == "unlock_chapter":
                    self.temp_unlock_chapter += event.unicode
                elif self.active_input == "unlock_phase":
                    self.temp_unlock_phase += event.unicode
            return None

    def _handle_mousedown(self, event):
        """Processa clique do mouse"""
        mouse_pos = pygame.mouse.get_pos()

        # ===== BOTÕES DE AÇÃO =====
        if self.confirm_rect.collidepoint(mouse_pos):
            return self.confirm()
        if self.cancel_rect.collidepoint(mouse_pos):
            self.visible = False
            return None

        # ===== INPUTS =====
        if self.name_input_rect.collidepoint(mouse_pos):
            self.active_input = "name"
            return None
        elif self.width_input_rect.collidepoint(mouse_pos):
            self.active_input = "width"
            return None
        elif self.height_input_rect.collidepoint(mouse_pos):
            self.active_input = "height"
            return None
        elif self.chapter_input_rect.collidepoint(mouse_pos):
            self.active_input = "chapter"
            return None
        elif self.phase_input_rect.collidepoint(mouse_pos):
            self.active_input = "phase"
            return None

        # ===== LOCALIZAÇÃO =====
        if self.default_radio_rect.collidepoint(mouse_pos):
            self.temp_localization_type = "default"
            self.temp_custom_folder = ""
            self.active_input = "name"
            return None
        if self.custom_radio_rect.collidepoint(mouse_pos):
            self.temp_localization_type = "custom"
            self.active_input = "custom_folder"
            return None

        # ===== PASTA CUSTOM =====
        if self.browse_button_rect.collidepoint(mouse_pos) and self.temp_localization_type == "custom":
            from tkinter import filedialog, Tk
            root = Tk()
            root.withdraw()
            folder = filedialog.askdirectory(title="Selecione a pasta para salvar minigames")
            if folder:
                self.temp_custom_folder = os.path.basename(folder)
            return None

        if self.folder_input_rect.collidepoint(mouse_pos) and self.temp_localization_type == "custom":
            self.active_input = "custom_folder"
            return None

        # ===== UNLOCK (SÓ SE CUSTOM) =====
        if self.temp_localization_type == "custom":
            if self.unlock_chapter_input_rect.collidepoint(mouse_pos):
                self.active_input = "unlock_chapter"
                return None
            if self.unlock_phase_input_rect.collidepoint(mouse_pos):
                self.active_input = "unlock_phase"
                return None

        # ===== DIA/NOITE =====
        if self.day_night_random_rect.collidepoint(mouse_pos):
            self.temp_day_night_mode = "random"
            return None
        if self.day_night_day_rect.collidepoint(mouse_pos):
            self.temp_day_night_mode = "day"
            return None
        if self.day_night_night_rect.collidepoint(mouse_pos):
            self.temp_day_night_mode = "night"
            return None

        # ===== CLIMA =====
        if self.weather_random_rect.collidepoint(mouse_pos):
            self.temp_base_weather = "random"
            return None
        if self.weather_none_rect.collidepoint(mouse_pos):
            self.temp_base_weather = "none"
            return None
        if self.weather_sunny_rect.collidepoint(mouse_pos):
            self.temp_base_weather = "sunny"
            return None
        if self.weather_rain_rect.collidepoint(mouse_pos):
            self.temp_base_weather = "rain"
            return None

        # Clicou fora do diálogo
        if not self.rect.collidepoint(mouse_pos):
            self.visible = False
            return None

        return None

    def confirm(self):
        """Confirma a operação e retorna os novos valores"""
        try:
            new_width = max(5, min(500, int(self.temp_width) if self.temp_width else 10))
            new_height = max(5, min(500, int(self.temp_height) if self.temp_height else 10))
            new_chapter = max(1, min(99, int(self.temp_chapter) if self.temp_chapter else 1))
            new_phase = max(1, min(99, int(self.temp_phase) if self.temp_phase else 1))
            new_name = self.temp_name.strip() or f"Fase {new_chapter}-{new_phase}"

            new_custom_folder = self.temp_custom_folder.strip()
            if self.temp_localization_type == "custom" and not new_custom_folder:
                localization_type = "default"
                custom_folder = ""
                unlock_chapter = 1
                unlock_phase = 1
            else:
                localization_type = self.temp_localization_type
                custom_folder = new_custom_folder if localization_type == "custom" else ""

                if localization_type == "custom":
                    try:
                        unlock_chapter = max(1,
                                             min(99, int(self.temp_unlock_chapter) if self.temp_unlock_chapter else 1))
                        unlock_phase = max(1, min(99, int(self.temp_unlock_phase) if self.temp_unlock_phase else 1))
                    except ValueError:
                        unlock_chapter = 1
                        unlock_phase = 1
                else:
                    unlock_chapter = 1
                    unlock_phase = 1

            self.visible = False

            result = {
                'width': new_width,
                'height': new_height,
                'chapter': new_chapter,
                'phase': new_phase,
                'name': new_name,
                'localization_type': localization_type,
                'custom_folder': custom_folder,
                'day_night_mode': self.temp_day_night_mode,
                'base_weather': self.temp_base_weather,
            }

            if localization_type == "custom":
                result['unlock_chapter'] = unlock_chapter
                result['unlock_phase'] = unlock_phase

            return result
        except ValueError:
            return None

    def render(self, screen):
        """Renderiza o diálogo"""
        if not self.visible:
            return

        # ===== OVERLAY =====
        overlay = pygame.Surface((screen.get_width(), screen.get_height()))
        overlay.set_alpha(180)
        overlay.fill((0, 0, 0))
        screen.blit(overlay, (0, 0))

        # ===== FUNDO =====
        pygame.draw.rect(screen, self.colors['bg'], self.rect, border_radius=12)
        pygame.draw.rect(screen, self.colors['border'], self.rect, 2, border_radius=12)

        # ===== BARRA DE TÍTULO =====
        title_bar = pygame.Rect(self.rect.x, self.rect.y, self.rect.width, 38)
        pygame.draw.rect(screen, (55, 58, 72), title_bar, border_top_left_radius=12, border_top_right_radius=12)

        # Título
        font_title = self._get_font(22, True)
        title = font_title.render("Configurações do Mapa", True, self.colors['title'])
        screen.blit(title, (self.rect.x + self.margin, self.rect.y + 10))

        # ===== LINHA 1: Nome =====
        self._render_label(screen, self.name_label_rect, "Nome:", self.colors['text_dim'])
        self._render_input(screen, self.name_input_rect, self.temp_name, "name", self.active_input == "name")

        # ===== LINHA 2: Largura e Altura =====
        self._render_label(screen, self.width_label_rect, "Largura:", self.colors['text_dim'])
        self._render_input(screen, self.width_input_rect, self.temp_width, "width", self.active_input == "width")

        self._render_label(screen, self.height_label_rect, "Altura:", self.colors['text_dim'])
        self._render_input(screen, self.height_input_rect, self.temp_height, "height", self.active_input == "height")

        # ===== LINHA 3: Capítulo e Fase =====
        self._render_label(screen, self.chapter_label_rect, "Capítulo:", self.colors['text_dim'])
        self._render_input(screen, self.chapter_input_rect, self.temp_chapter, "chapter",
                           self.active_input == "chapter")

        self._render_label(screen, self.phase_label_rect, "Fase:", self.colors['text_dim'])
        self._render_input(screen, self.phase_input_rect, self.temp_phase, "phase", self.active_input == "phase")

        # ===== LINHA 4: Localização =====
        self._render_label(screen, self.loc_label_rect, "Localização:", self.colors['text_dim'])

        # Radio Default
        self._render_radio(screen, self.default_radio_rect, self.temp_localization_type == "default")
        default_text = self._get_font(16).render("Default", True, self.colors['text'])
        screen.blit(default_text, (self.default_radio_rect.right + 6, self.default_radio_rect.y - 1))

        # Radio Custom
        self._render_radio(screen, self.custom_radio_rect, self.temp_localization_type == "custom")
        custom_text = self._get_font(16).render("Custom", True, self.colors['text'])
        screen.blit(custom_text, (self.custom_radio_rect.right + 6, self.custom_radio_rect.y - 1))

        # ===== LINHA 5: Pasta Custom (só se custom) =====
        if self.temp_localization_type == "custom":
            self._render_label(screen, self.folder_label_rect, "Pasta:", self.colors['text_dim'])

            # Input da pasta
            color = self.colors['border_active'] if self.active_input == "custom_folder" else self.colors['border']
            pygame.draw.rect(screen, self.colors['bg_input'], self.folder_input_rect, border_radius=6)
            pygame.draw.rect(screen, color, self.folder_input_rect, 2, border_radius=6)

            display_text = self.temp_custom_folder if self.temp_custom_folder else "Selecione uma pasta..."
            text_color = self.colors['text'] if self.temp_custom_folder else self.colors['text_muted']
            folder_surf = self._get_font(16).render(display_text, True, text_color)

            # Corta texto se necessário
            if folder_surf.get_width() > self.folder_input_rect.width - 10:
                folder_surf = self._get_font(14).render(display_text[:20] + "...", True, text_color)

            screen.blit(folder_surf, (self.folder_input_rect.x + 8, self.folder_input_rect.y + 6))

            # Botão Browse
            hover = self.hovered_button == "browse"
            browse_color = self.colors['accent'] if hover else (70, 80, 110)
            pygame.draw.rect(screen, browse_color, self.browse_button_rect, border_radius=6)
            pygame.draw.rect(screen, self.colors['border'], self.browse_button_rect, 1, border_radius=6)

            browse_text = self._get_font(16).render("...", True, self.colors['text'])
            browse_x = self.browse_button_rect.x + (self.browse_button_rect.width - browse_text.get_width()) // 2
            browse_y = self.browse_button_rect.y + (self.browse_button_rect.height - browse_text.get_height()) // 2
            screen.blit(browse_text, (browse_x, browse_y))

            # ===== LINHA 6: Unlock (só se custom) =====
            self._render_label(screen, self.unlock_label_rect, "Desbloqueio:", self.colors['text_dim'])

            self._render_label(screen, self.unlock_chapter_label_rect, "Cap:", self.colors['text_muted'])
            self._render_input(screen, self.unlock_chapter_input_rect, self.temp_unlock_chapter, "unlock_chapter",
                               self.active_input == "unlock_chapter", small=True)

            self._render_label(screen, self.unlock_phase_label_rect, "Fase:", self.colors['text_muted'])
            self._render_input(screen, self.unlock_phase_input_rect, self.temp_unlock_phase, "unlock_phase",
                               self.active_input == "unlock_phase", small=True)

        # ===== LINHA 7: Dia/Noite =====
        self._render_label(screen, self.day_night_label_rect, "Período:", self.colors['text_dim'])

        # Radio Random
        self._render_radio(screen, self.day_night_random_rect, self.temp_day_night_mode == "random")
        random_text = self._get_font(15).render("Aleatório", True, self.colors['text'])
        screen.blit(random_text, (self.day_night_random_rect.right + 5, self.day_night_random_rect.y - 1))

        # Radio Dia
        self._render_radio(screen, self.day_night_day_rect, self.temp_day_night_mode == "day")
        day_text = self._get_font(15).render("Dia", True, self.colors['text'])
        screen.blit(day_text, (self.day_night_day_rect.right + 5, self.day_night_day_rect.y - 1))

        # Radio Noite
        self._render_radio(screen, self.day_night_night_rect, self.temp_day_night_mode == "night")
        night_text = self._get_font(15).render("Noite", True, self.colors['text'])
        screen.blit(night_text, (self.day_night_night_rect.right + 5, self.day_night_night_rect.y - 1))

        # ===== LINHA 8: Clima Base =====
        self._render_label(screen, self.weather_label_rect, "Clima Base:", self.colors['text_dim'])

        # Radio Random
        self._render_radio(screen, self.weather_random_rect, self.temp_base_weather == "random")
        random_text = self._get_font(15).render("Aleatório", True, self.colors['text'])
        screen.blit(random_text, (self.weather_random_rect.right + 5, self.weather_random_rect.y - 1))

        # Radio Normal
        self._render_radio(screen, self.weather_none_rect, self.temp_base_weather == "none")
        none_text = self._get_font(15).render("Normal", True, self.colors['text'])
        screen.blit(none_text, (self.weather_none_rect.right + 5, self.weather_none_rect.y - 1))

        # Radio Sol
        self._render_radio(screen, self.weather_sunny_rect, self.temp_base_weather == "sunny")
        sunny_text = self._get_font(15).render("Sol", True, self.colors['text'])
        screen.blit(sunny_text, (self.weather_sunny_rect.right + 5, self.weather_sunny_rect.y - 1))

        # Radio Chuva
        self._render_radio(screen, self.weather_rain_rect, self.temp_base_weather == "rain")
        rain_text = self._get_font(15).render("Chuva", True, self.colors['text'])
        screen.blit(rain_text, (self.weather_rain_rect.right + 5, self.weather_rain_rect.y - 1))

        # ===== BOTÕES =====
        # Confirmar
        confirm_color = self.colors['success'] if self.hovered_button == "confirm" else (40, 140, 40)
        pygame.draw.rect(screen, confirm_color, self.confirm_rect, border_radius=8)
        pygame.draw.rect(screen, (255, 255, 255), self.confirm_rect, 1, border_radius=8)
        confirm_text = self._get_font(18).render("Confirmar", True, (255, 255, 255))
        confirm_x = self.confirm_rect.x + (self.confirm_rect.width - confirm_text.get_width()) // 2
        confirm_y = self.confirm_rect.y + (self.confirm_rect.height - confirm_text.get_height()) // 2
        screen.blit(confirm_text, (confirm_x, confirm_y))

        # Cancelar
        cancel_color = self.colors['danger'] if self.hovered_button == "cancel" else (160, 40, 40)
        pygame.draw.rect(screen, cancel_color, self.cancel_rect, border_radius=8)
        pygame.draw.rect(screen, (255, 255, 255), self.cancel_rect, 1, border_radius=8)
        cancel_text = self._get_font(18).render("Cancelar", True, (255, 255, 255))
        cancel_x = self.cancel_rect.x + (self.cancel_rect.width - cancel_text.get_width()) // 2
        cancel_y = self.cancel_rect.y + (self.cancel_rect.height - cancel_text.get_height()) // 2
        screen.blit(cancel_text, (cancel_x, cancel_y))

        # ===== INFORMAÇÃO =====
        info_font = self._get_font(13)
        info = info_font.render("TAB para alternar campos | Min: 5, Max: 500 tiles", True, self.colors['text_muted'])
        info_x = self.rect.x + (self.rect.width - info.get_width()) // 2
        info_y = self.rect.y + self.rect.height - 32
        screen.blit(info, (info_x, info_y))

    def _render_label(self, screen, rect, text, color):
        """Renderiza um label"""
        label = self._get_font(16).render(text, True, color)
        label_y = rect.y + (rect.height - label.get_height()) // 2
        screen.blit(label, (rect.x, label_y))

    def _render_input(self, screen, rect, text, field_name, active, small=False):
        """Renderiza um campo de input"""
        font_size = 15 if small else 17
        color = self.colors['border_active'] if active else self.colors['border']

        pygame.draw.rect(screen, self.colors['bg_input'], rect, border_radius=6)
        pygame.draw.rect(screen, color, rect, 2, border_radius=6)

        display_text = text
        text_surf = self._get_font(font_size).render(display_text, True, self.colors['text'])

        # Corta se necessário
        if text_surf.get_width() > rect.width - 12:
            display_text = display_text[:8] + "..."
            text_surf = self._get_font(font_size).render(display_text, True, self.colors['text'])

        text_x = rect.x + 6
        text_y = rect.y + (rect.height - text_surf.get_height()) // 2
        screen.blit(text_surf, (text_x, text_y))

    def _render_radio(self, screen, rect, selected):
        """Renderiza um radio button"""
        center = (rect.centerx, rect.centery)
        radius = rect.width // 2

        # Fundo
        color = self.colors['radio_selected'] if selected else self.colors['radio_unselected']
        pygame.draw.circle(screen, color, center, radius)
        pygame.draw.circle(screen, (255, 255, 255), center, radius - 2)

        if selected:
            pygame.draw.circle(screen, color, center, radius - 5)