# src/scenes/editor/components/map_config_dialog.py

import pygame
import os


class MapConfigDialog:
    def __init__(self, x, y, width, height, current_width, current_height,
                 current_chapter=1, current_phase=1, current_name="Fase",
                 current_localization_type="default", current_custom_folder="",
                 current_unlock_chapter=1, current_unlock_phase=1):
        self.rect = pygame.Rect(x, y, width, height)
        self.visible = True
        self.focused = True
        self.current_width = current_width
        self.current_height = current_height
        self.current_chapter = current_chapter
        self.current_phase = current_phase
        self.current_name = current_name
        self.current_localization_type = current_localization_type  # "default" ou "custom"
        self.current_custom_folder = current_custom_folder
        self.current_unlock_chapter = current_unlock_chapter
        self.current_unlock_phase = current_unlock_phase

        # Valores temporários
        self.temp_width = str(current_width)
        self.temp_height = str(current_height)
        self.temp_chapter = str(current_chapter)
        self.temp_phase = str(current_phase)
        self.temp_name = current_name
        self.temp_localization_type = current_localization_type
        self.temp_custom_folder = current_custom_folder
        self.temp_unlock_chapter = str(current_unlock_chapter)
        self.temp_unlock_phase = str(current_unlock_phase)

        self.active_input = "name"  # "name", "width", "height", "chapter", "phase", "custom_folder", "unlock_chapter", "unlock_phase"

        # Botões
        button_width = 80
        button_height = 30
        self.confirm_rect = pygame.Rect(
            x + (width - button_width * 2 - 10) // 2,
            y + height - 50,
            button_width,
            button_height
        )
        self.cancel_rect = pygame.Rect(
            x + (width - button_width * 2 - 10) // 2 + button_width + 10,
            y + height - 50,
            button_width,
            button_height
        )

        # Input boxes
        self.name_rect = pygame.Rect(x + 150, y + 40, 200, 30)
        self.width_rect = pygame.Rect(x + 150, y + 80, 100, 30)
        self.height_rect = pygame.Rect(x + 150, y + 120, 100, 30)
        self.chapter_rect = pygame.Rect(x + 150, y + 160, 100, 30)
        self.phase_rect = pygame.Rect(x + 150, y + 200, 100, 30)

        # Radio buttons para tipo de localização
        self.default_radio_rect = pygame.Rect(x + 150, y + 240, 20, 20)
        self.custom_radio_rect = pygame.Rect(x + 300, y + 240, 20, 20)

        # Input para pasta customizada (só aparece se custom estiver selecionado)
        self.custom_folder_rect = pygame.Rect(x + 150, y + 280, 200, 30)
        self.browse_button_rect = pygame.Rect(x + 360, y + 280, 30, 30)

        # Campos para requisito de desbloqueio (só aparecem se custom estiver selecionado)
        self.unlock_chapter_label = pygame.Rect(x + 20, y + 325, 100, 25)
        self.unlock_chapter_input = pygame.Rect(x + 150, y + 325, 80, 25)
        self.unlock_phase_label = pygame.Rect(x + 250, y + 325, 60, 25)
        self.unlock_phase_input = pygame.Rect(x + 310, y + 325, 80, 25)

        # Ajusta altura do diálogo baseado no tipo
        if current_localization_type == "custom":
            self.rect.height = 400
        else:
            self.rect.height = 330

    def handle_event(self, event):
        """Processa eventos do diálogo"""
        if not self.visible:
            return None

        if event.type == pygame.KEYDOWN:
            return self._handle_keydown(event)
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                return self._handle_mousedown(event)

        return None

    def _handle_keydown(self, event):
        """Processa teclas pressionadas"""
        if event.key == pygame.K_RETURN:
            return self.confirm()
        elif event.key == pygame.K_ESCAPE:
            self.visible = False
            return None
        elif event.key == pygame.K_TAB:
            # Alterna entre os inputs
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
            # Adiciona caracteres
            if self.active_input == "name":
                # Permite letras, números e espaços no nome
                if event.unicode.isprintable() and event.unicode not in ['/', '\\', ':', '*', '?', '"', '<', '>', '|']:
                    self.temp_name += event.unicode
            elif self.active_input == "custom_folder":
                # Permite letras, números, underscore e hífen para nome de pasta
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

        # Verifica cliques nos inputs
        if self.name_rect.collidepoint(mouse_pos):
            self.active_input = "name"
            return None
        elif self.width_rect.collidepoint(mouse_pos):
            self.active_input = "width"
            return None
        elif self.height_rect.collidepoint(mouse_pos):
            self.active_input = "height"
            return None
        elif self.chapter_rect.collidepoint(mouse_pos):
            self.active_input = "chapter"
            return None
        elif self.phase_rect.collidepoint(mouse_pos):
            self.active_input = "phase"
            return None
        # Radio buttons
        elif self.default_radio_rect.collidepoint(mouse_pos):
            self.temp_localization_type = "default"
            self.temp_custom_folder = ""
            self.active_input = "name"
            self.rect.height = 330  # Altura padrão
            return None
        elif self.custom_radio_rect.collidepoint(mouse_pos):
            self.temp_localization_type = "custom"
            self.active_input = "custom_folder"
            self.rect.height = 400  # Altura maior para unlock
            return None
        # Botão browse
        elif self.browse_button_rect.collidepoint(mouse_pos):
            from tkinter import filedialog, Tk
            root = Tk()
            root.withdraw()
            folder = filedialog.askdirectory(title="Selecione a pasta para salvar minigames")
            if folder:
                # Extrai apenas o nome da pasta
                self.temp_custom_folder = os.path.basename(folder)
            return None
        # Input da pasta customizada
        elif self.custom_folder_rect.collidepoint(mouse_pos) and self.temp_localization_type == "custom":
            self.active_input = "custom_folder"
            return None
        # Inputs de unlock
        elif self.unlock_chapter_input.collidepoint(mouse_pos) and self.temp_localization_type == "custom":
            self.active_input = "unlock_chapter"
            return None
        elif self.unlock_phase_input.collidepoint(mouse_pos) and self.temp_localization_type == "custom":
            self.active_input = "unlock_phase"
            return None
        elif self.confirm_rect.collidepoint(mouse_pos):
            return self.confirm()
        elif self.cancel_rect.collidepoint(mouse_pos):
            self.visible = False
            return None
        elif not self.rect.collidepoint(mouse_pos):
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

            # Valida pasta customizada
            new_custom_folder = self.temp_custom_folder.strip()
            if self.temp_localization_type == "custom" and not new_custom_folder:
                # Se selecionou custom mas não deu nome, volta pra default
                localization_type = "default"
                custom_folder = ""
                unlock_chapter = 1
                unlock_phase = 1
            else:
                localization_type = self.temp_localization_type
                custom_folder = new_custom_folder if localization_type == "custom" else ""

                # Valores de unlock (apenas para custom)
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
                'custom_folder': custom_folder
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

        # Fundo semi-transparente
        overlay = pygame.Surface((screen.get_width(), screen.get_height()))
        overlay.set_alpha(128)
        overlay.fill((0, 0, 0))
        screen.blit(overlay, (0, 0))

        # Caixa de diálogo
        pygame.draw.rect(screen, (60, 60, 70), self.rect, border_radius=10)
        pygame.draw.rect(screen, (255, 215, 0), self.rect, 2, border_radius=10)

        # Título
        font_title = pygame.font.Font(None, 28)
        title = font_title.render("Configurações do Mapa", True, (255, 255, 255))
        title_x = self.rect.x + (self.rect.width - title.get_width()) // 2
        screen.blit(title, (title_x, self.rect.y + 10))

        # Labels e inputs
        font = pygame.font.Font(None, 20)
        label_x = self.rect.x + 20
        value_x = self.rect.x + 150

        # Nome da Fase
        name_label = font.render("Nome da Fase:", True, (200, 200, 200))
        screen.blit(name_label, (label_x, self.rect.y + 45))
        color = (100, 150, 255) if self.active_input == "name" else (80, 80, 90)
        pygame.draw.rect(screen, color, self.name_rect, 2)
        display_name = self.temp_name
        if font.size(display_name)[0] > self.name_rect.width - 10:
            while font.size(display_name + "...")[0] > self.name_rect.width - 10 and len(display_name) > 3:
                display_name = display_name[:-1]
            display_name += "..."
        name_surf = font.render(display_name, True, (255, 255, 255))
        screen.blit(name_surf, (self.name_rect.x + 5, self.name_rect.y + 5))

        # Largura
        width_label = font.render("Largura (tiles):", True, (200, 200, 200))
        screen.blit(width_label, (label_x, self.rect.y + 85))
        color = (100, 150, 255) if self.active_input == "width" else (80, 80, 90)
        pygame.draw.rect(screen, color, self.width_rect, 2)
        width_surf = font.render(self.temp_width, True, (255, 255, 255))
        screen.blit(width_surf, (self.width_rect.x + 5, self.width_rect.y + 5))

        # Altura
        height_label = font.render("Altura (tiles):", True, (200, 200, 200))
        screen.blit(height_label, (label_x, self.rect.y + 125))
        color = (100, 150, 255) if self.active_input == "height" else (80, 80, 90)
        pygame.draw.rect(screen, color, self.height_rect, 2)
        height_surf = font.render(self.temp_height, True, (255, 255, 255))
        screen.blit(height_surf, (self.height_rect.x + 5, self.height_rect.y + 5))

        # Capítulo
        chapter_label = font.render("Capítulo:", True, (200, 200, 200))
        screen.blit(chapter_label, (label_x, self.rect.y + 165))
        color = (100, 150, 255) if self.active_input == "chapter" else (80, 80, 90)
        pygame.draw.rect(screen, color, self.chapter_rect, 2)
        chapter_surf = font.render(self.temp_chapter, True, (255, 255, 255))
        screen.blit(chapter_surf, (self.chapter_rect.x + 5, self.chapter_rect.y + 5))

        # Fase
        phase_label = font.render("Fase:", True, (200, 200, 200))
        screen.blit(phase_label, (label_x, self.rect.y + 205))
        color = (100, 150, 255) if self.active_input == "phase" else (80, 80, 90)
        pygame.draw.rect(screen, color, self.phase_rect, 2)
        phase_surf = font.render(self.temp_phase, True, (255, 255, 255))
        screen.blit(phase_surf, (self.phase_rect.x + 5, self.phase_rect.y + 5))

        # Localização
        loc_label = font.render("Localização:", True, (200, 200, 200))
        screen.blit(loc_label, (label_x, self.rect.y + 245))

        # Radio button Default
        pygame.draw.circle(screen, (100, 150, 255) if self.temp_localization_type == "default" else (80, 80, 90),
                           (self.default_radio_rect.centerx, self.default_radio_rect.centery), 10)
        pygame.draw.circle(screen, (255, 255, 255),
                           (self.default_radio_rect.centerx, self.default_radio_rect.centery), 8)
        if self.temp_localization_type == "default":
            pygame.draw.circle(screen, (100, 150, 255),
                               (self.default_radio_rect.centerx, self.default_radio_rect.centery), 5)

        default_text = font.render("Default (capítulos)", True, (200, 200, 200))
        screen.blit(default_text, (self.default_radio_rect.right + 5, self.rect.y + 241))

        # Radio button Custom
        pygame.draw.circle(screen, (100, 150, 255) if self.temp_localization_type == "custom" else (80, 80, 90),
                           (self.custom_radio_rect.centerx, self.custom_radio_rect.centery), 10)
        pygame.draw.circle(screen, (255, 255, 255),
                           (self.custom_radio_rect.centerx, self.custom_radio_rect.centery), 8)
        if self.temp_localization_type == "custom":
            pygame.draw.circle(screen, (100, 150, 255),
                               (self.custom_radio_rect.centerx, self.custom_radio_rect.centery), 5)

        custom_text = font.render("Custom (minigames)", True, (200, 200, 200))
        screen.blit(custom_text, (self.custom_radio_rect.right + 5, self.rect.y + 241))

        # Pasta customizada e requisitos (só aparece se custom estiver selecionado)
        if self.temp_localization_type == "custom":
            # Pasta
            folder_label = font.render("Pasta:", True, (200, 200, 200))
            screen.blit(folder_label, (label_x, self.rect.y + 285))

            color = (100, 150, 255) if self.active_input == "custom_folder" else (80, 80, 90)
            pygame.draw.rect(screen, (50, 50, 60), self.custom_folder_rect, border_radius=5)
            pygame.draw.rect(screen, color, self.custom_folder_rect, 2, border_radius=5)

            # Limita o texto visível
            display_folder = self.temp_custom_folder
            if font.size(display_folder)[0] > self.custom_folder_rect.width - 10:
                while font.size(display_folder + "...")[0] > self.custom_folder_rect.width - 10 and len(
                        display_folder) > 3:
                    display_folder = display_folder[:-1]
                display_folder += "..."

            folder_surf = font.render(display_folder, True, (255, 255, 255))
            screen.blit(folder_surf, (self.custom_folder_rect.x + 5, self.custom_folder_rect.y + 5))

            # Botão Browse
            pygame.draw.rect(screen, (80, 80, 90), self.browse_button_rect, border_radius=5)
            browse_text = font.render("...", True, (255, 255, 255))
            browse_x = self.browse_button_rect.x + (self.browse_button_rect.width - browse_text.get_width()) // 2
            browse_y = self.browse_button_rect.y + (self.browse_button_rect.height - browse_text.get_height()) // 2
            screen.blit(browse_text, (browse_x, browse_y))

            # Seção de requisito de desbloqueio
            unlock_title = font.render("Requisito para Desbloquear:", True, (255, 215, 0))
            screen.blit(unlock_title, (label_x, self.rect.y + 325))

            # Capítulo necessário
            chapter_unlock_label = font.render("Capítulo:", True, (200, 200, 200))
            screen.blit(chapter_unlock_label, (self.unlock_chapter_label.x, self.unlock_chapter_label.y + 3))

            color = (100, 150, 255) if self.active_input == "unlock_chapter" else (80, 80, 90)
            pygame.draw.rect(screen, (50, 50, 60), self.unlock_chapter_input, border_radius=5)
            pygame.draw.rect(screen, color, self.unlock_chapter_input, 2, border_radius=5)
            unlock_chapter_surf = font.render(self.temp_unlock_chapter, True, (255, 255, 255))
            screen.blit(unlock_chapter_surf, (self.unlock_chapter_input.x + 5, self.unlock_chapter_input.y + 3))

            # Fase necessária
            phase_unlock_label = font.render("Fase:", True, (200, 200, 200))
            screen.blit(phase_unlock_label, (self.unlock_phase_label.x, self.unlock_phase_label.y + 3))

            color = (100, 150, 255) if self.active_input == "unlock_phase" else (80, 80, 90)
            pygame.draw.rect(screen, (50, 50, 60), self.unlock_phase_input, border_radius=5)
            pygame.draw.rect(screen, color, self.unlock_phase_input, 2, border_radius=5)
            unlock_phase_surf = font.render(self.temp_unlock_phase, True, (255, 255, 255))
            screen.blit(unlock_phase_surf, (self.unlock_phase_input.x + 5, self.unlock_phase_input.y + 3))

            # Informação extra
            info_y = self.rect.y + 365
        else:
            info_y = self.rect.y + 285

        # Informação
        info = font.render("TAB para alternar | Min: 5, Max: 500 tiles", True, (150, 150, 150))
        info_x = self.rect.x + (self.rect.width - info.get_width()) // 2
        screen.blit(info, (info_x, info_y))

        # Botões
        self._render_buttons(screen, font)

    def _render_buttons(self, screen, font):
        """Renderiza os botões"""
        # Confirmar
        pygame.draw.rect(screen, (0, 150, 0), self.confirm_rect, border_radius=5)
        pygame.draw.rect(screen, (255, 255, 255), self.confirm_rect, 1, border_radius=5)
        confirm_text = font.render("Confirmar", True, (255, 255, 255))
        confirm_x = self.confirm_rect.x + (self.confirm_rect.width - confirm_text.get_width()) // 2
        confirm_y = self.confirm_rect.y + (self.confirm_rect.height - confirm_text.get_height()) // 2
        screen.blit(confirm_text, (confirm_x, confirm_y))

        # Cancelar
        pygame.draw.rect(screen, (150, 0, 0), self.cancel_rect, border_radius=5)
        pygame.draw.rect(screen, (255, 255, 255), self.cancel_rect, 1, border_radius=5)
        cancel_text = font.render("Cancelar", True, (255, 255, 255))
        cancel_x = self.cancel_rect.x + (self.cancel_rect.width - cancel_text.get_width()) // 2
        cancel_y = self.cancel_rect.y + (self.cancel_rect.height - cancel_text.get_height()) // 2
        screen.blit(cancel_text, (cancel_x, cancel_y))