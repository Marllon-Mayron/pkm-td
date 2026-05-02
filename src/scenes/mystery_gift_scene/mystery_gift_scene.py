# src/scenes/mystery_gift_scene/mystery_gift_scene.py

"""
Tela de Mystery Gift
Permite ao jogador resgatar códigos para ganhar Pokémon especiais
"""

import pygame
import string
import time

from src.scenes.base_scene import BaseScene


class MysteryGiftScene(BaseScene):
    def __init__(self, game):
        super().__init__(game)

        # Estado da tela
        self.state = "input"  # input, success, error, loading, blocked
        self.code_input = ""
        self.error_message = ""
        self.success_message = ""
        self.redeemed_pokemon = None
        self.animation_timer = 0
        self.animation_scale = 1.0

        # Botão de voltar
        self.back_button = None

        # Campo de input
        self.input_active = True

        # Partículas de celebração
        self.particles = []

        # Timer para auto-fechar mensagem de sucesso
        self.success_timer = 0

        # Controle de clique
        self._last_error_click = 0

        # ===== VERIFICA SE HÁ SAVE CARREGADO =====
        self.has_save = self._check_save_loaded()

        if not self.has_save:
            self.state = "blocked"
            print("[MYSTERY_GIFT] Acesso bloqueado: nenhum save carregado!")

        # Inicializa UI
        self._init_ui()

    def _check_save_loaded(self):
        """Verifica se o jogador tem um save carregado"""
        # Verifica se existe pelo menos um Pokémon no time ou na box
        has_pokemon = len(self.game.player.team) > 0 or len(self.game.player.pc_box) > 0

        # Verifica se existe um arquivo de save
        import os
        save_file = os.path.join("saves", "save_1.json")
        has_save_file = os.path.exists(save_file)

        # Verifica se o save_manager tem um save carregado
        has_save_manager = self.game.player.save_manager.current_save_file is not None

        print(f"[MYSTERY_GIFT] Verificação de save:")
        print(f"  - Pokémon no time/box: {has_pokemon}")
        print(f"  - Arquivo de save existe: {has_save_file}")
        print(f"  - SaveManager tem save: {has_save_manager}")

        # Retorna True se tiver Pokémon OU se tiver arquivo de save
        return has_pokemon or (has_save_file and has_save_manager)

    def _init_ui(self):
        """Inicializa elementos de UI"""

        class Button:
            def __init__(self, x, y, width, height, text, color, hover_color, callback):
                self.x = x
                self.y = y
                self.width = width
                self.height = height
                self.text = text
                self.color = color
                self.hover_color = hover_color
                self.callback = callback
                self.is_hovered = False
                self.rect = pygame.Rect(x, y, width, height)
                self.text_surface = None
                self.text_rect = None

            def update_position(self, viewport_x, viewport_y):
                self.rect = pygame.Rect(
                    viewport_x + self.x,
                    viewport_y + self.y,
                    self.width,
                    self.height
                )
                self.text_surface = None

            def handle_event(self, event):
                if event.type == pygame.MOUSEMOTION:
                    self.is_hovered = self.rect.collidepoint(event.pos)
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if self.is_hovered:
                        self.callback()

            def render(self, screen, font):
                color = self.hover_color if self.is_hovered else self.color
                pygame.draw.rect(screen, color, self.rect)
                pygame.draw.rect(screen, (255, 255, 255), self.rect, 3)

                if self.text_surface is None:
                    self.text_surface = font.render(self.text, True, (255, 255, 255))
                    self.text_rect = self.text_surface.get_rect(center=self.rect.center)
                screen.blit(self.text_surface, self.text_rect)

        # Botão Voltar (canto inferior esquerdo)
        self.back_button = Button(
            20, 0, 120, 40, "Voltar", (80, 80, 80), (120, 120, 120), self.go_back
        )

        # Atualiza posição inicial do botão voltar
        self.back_button.y = self.screen_manager.viewport_height - 60
        self.back_button.update_position(
            self.screen_manager.viewport_x,
            self.screen_manager.viewport_y
        )

        # Botão Resgatar
        self.redeem_button = None

    def _update_button_positions(self):
        """Atualiza posições dos botões baseado no viewport"""
        viewport_h = self.screen_manager.viewport_height
        viewport_y = self.screen_manager.viewport_y

        # Atualiza posição do botão voltar
        if self.back_button:
            self.back_button.y = viewport_h - 60
            self.back_button.update_position(self.screen_manager.viewport_x, viewport_y)

        # Só cria botão de resgate se tiver save e estiver no estado input
        if self.state == "input" and self.has_save:
            button_width = 200
            button_height = 50
            button_x = (self.screen_manager.viewport_width - button_width) // 2
            button_y = self.screen_manager.viewport_height // 2 + 80

            if self.redeem_button is None:
                self._create_redeem_button()
            else:
                self.redeem_button.x = button_x
                self.redeem_button.y = button_y
                self.redeem_button.width = button_width
                self.redeem_button.height = button_height
                self.redeem_button.update_position(self.screen_manager.viewport_x, viewport_y)

    def _create_redeem_button(self):
        """Cria o botão de resgate"""
        button_width = 200
        button_height = 50
        button_x = (self.screen_manager.viewport_width - button_width) // 2
        button_y = self.screen_manager.viewport_height // 2 + 80

        class Button:
            def __init__(self, x, y, width, height, text, color, hover_color, callback):
                self.x = x
                self.y = y
                self.width = width
                self.height = height
                self.text = text
                self.color = color
                self.hover_color = hover_color
                self.callback = callback
                self.is_hovered = False
                self.rect = pygame.Rect(x, y, width, height)
                self.text_surface = None
                self.text_rect = None

            def update_position(self, viewport_x, viewport_y):
                self.rect = pygame.Rect(
                    viewport_x + self.x,
                    viewport_y + self.y,
                    self.width,
                    self.height
                )
                self.text_surface = None

            def handle_event(self, event):
                if event.type == pygame.MOUSEMOTION:
                    self.is_hovered = self.rect.collidepoint(event.pos)
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if self.is_hovered:
                        self.callback()

            def render(self, screen, font):
                color = self.hover_color if self.is_hovered else self.color
                pygame.draw.rect(screen, color, self.rect)
                pygame.draw.rect(screen, (255, 255, 255), self.rect, 3)

                if self.text_surface is None:
                    self.text_surface = font.render(self.text, True, (255, 255, 255))
                    self.text_rect = self.text_surface.get_rect(center=self.rect.center)
                screen.blit(self.text_surface, self.text_rect)

        self.redeem_button = Button(
            button_x, button_y, button_width, button_height,
            "RESGATAR", (50, 100, 50), (80, 150, 80), self.redeem_code
        )
        self.redeem_button.update_position(self.screen_manager.viewport_x, self.screen_manager.viewport_y)

    def _create_celebration_particles(self):
        """Cria partículas de celebração"""
        import random
        self.particles = []
        center_x = self.screen_manager.viewport_width // 2
        center_y = self.screen_manager.viewport_height // 2

        for _ in range(50):
            self.particles.append({
                'x': center_x,
                'y': center_y,
                'vx': random.uniform(-200, 200),
                'vy': random.uniform(-300, -50),
                'life': random.uniform(0.5, 1.5),
                'color': (random.randint(100, 255), random.randint(100, 255), random.randint(100, 255)),
                'size': random.randint(3, 8)
            })

    def handle_event(self, event):
        """Processa eventos"""
        # Se está bloqueado, só permite voltar
        if self.state == "blocked":
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self.go_back()
            self.back_button.handle_event(event)
            return

        # Processa eventos de teclado para o input
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.go_back()
            elif event.key == pygame.K_RETURN and self.state == "input":
                self.redeem_code()
            elif self.state == "input":
                # Processa Ctrl+V (colar)
                if event.mod & pygame.KMOD_CTRL and event.key == pygame.K_v:
                    self._paste_from_clipboard()
                # Backspace
                elif event.key == pygame.K_BACKSPACE:
                    self.code_input = self.code_input[:-1]
                # Caracteres normais
                else:
                    char = event.unicode.upper()
                    # Permite letras (A-Z), números (0-9), hífen e underline
                    if char in string.ascii_uppercase + string.digits + "-_" and len(self.code_input) < 20:
                        self.code_input += char

        # Botões
        self.back_button.handle_event(event)
        if self.redeem_button and self.state == "input":
            self.redeem_button.handle_event(event)

    def _paste_from_clipboard(self):
        """Pega o texto da área de transferência e cola no campo de código"""
        clipboard_text = None

        # Método 1: Usar tkinter (mais confiável no Windows)
        try:
            import tkinter as tk
            root = tk.Tk()
            root.withdraw()  # Esconde a janela
            # Tenta pegar o texto do clipboard
            clipboard_text = root.clipboard_get()
            root.destroy()
            if clipboard_text:
                print("[MYSTERY_GIFT] Texto obtido via tkinter")
        except Exception as e:
            print(f"[MYSTERY_GIFT] Erro no tkinter: {e}")

        # Método 2: Fallback usando pyperclip se disponível
        if not clipboard_text:
            try:
                import pyperclip
                clipboard_text = pyperclip.paste()
                if clipboard_text:
                    print("[MYSTERY_GIFT] Texto obtido via pyperclip")
            except ImportError:
                pass
            except Exception as e:
                print(f"[MYSTERY_GIFT] Erro no pyperclip: {e}")

        # Processa o texto se conseguiu pegar algo
        if clipboard_text and isinstance(clipboard_text, str):
            # Limpa o texto (remove espaços, quebras de linha, etc)
            clipboard_text = clipboard_text.strip().upper()

            # Remove caracteres inválidos (só permite letras, números, hífen e underline)
            valid_chars = set(string.ascii_uppercase + string.digits + "-_")
            clean_code = ''.join(c for c in clipboard_text if c in valid_chars)

            # Limita ao tamanho máximo
            if len(clean_code) > 20:
                clean_code = clean_code[:20]

            # Atualiza o input
            if clean_code:
                self.code_input = clean_code
                print(f"[MYSTERY_GIFT] Código colado com sucesso: {self.code_input}")
            else:
                print(f"[MYSTERY_GIFT] Clipboard continha apenas caracteres inválidos")
        else:
            print("[MYSTERY_GIFT] Não foi possível acessar a área de transferência ou o texto não é uma string válida")

    def redeem_code(self):
        """Tenta resgatar o código"""
        # Verifica novamente se tem save
        if not self._check_save_loaded():
            self.state = "blocked"
            self.error_message = "Você precisa iniciar um jogo primeiro!"
            return

        if not self.code_input.strip():
            self.error_message = "Digite um código!"
            self.state = "error"
            return

        from src.managers.mystery_gift_manager import MysteryGiftManager

        # Recarrega o save antes de resgatar
        self.game.player.load_game(1)

        mg_manager = MysteryGiftManager(self.game.player)
        success, message, pokemon = mg_manager.redeem_code(self.code_input)

        if success:
            self.state = "success"
            self.success_message = message
            self.redeemed_pokemon = pokemon
            self.success_timer = 5.0
            self._create_celebration_particles()
            self.animation_scale = 1.5
            self.animation_timer = 0.5
        else:
            self.state = "error"
            self.error_message = message

    def go_back(self):
        """Volta ao menu anterior"""
        from src.scenes.menu_scene import MenuScene
        self.game.current_scene = MenuScene(self.game)

    def fixed_update(self, dt):
        """Atualiza animações"""
        if self.state == "success" and self.success_timer > 0:
            self.success_timer -= dt
            if self.success_timer <= 0:
                self.go_back()

        if self.animation_timer > 0:
            self.animation_timer -= dt
            if self.animation_timer > 0:
                self.animation_scale = 1.0 + (self.animation_timer * 1.5)
            else:
                self.animation_scale = 1.0

        for particle in self.particles[:]:
            particle['x'] += particle['vx'] * dt
            particle['y'] += particle['vy'] * dt
            particle['life'] -= dt
            if particle['life'] <= 0:
                self.particles.remove(particle)

    def render(self, screen):
        """Renderiza a tela"""
        self._draw_gradient_background(screen)
        self._update_button_positions()
        self._render_title(screen)

        if self.state == "input":
            self._render_input_screen(screen)
        elif self.state == "success":
            self._render_success_screen(screen)
        elif self.state == "error":
            self._render_error_screen(screen)
        elif self.state == "blocked":
            self._render_blocked_screen(screen)

        # Botão Voltar
        if self.back_button:
            self.back_button.render(screen, self._get_font(20))

    def _render_blocked_screen(self, screen):
        """Renderiza tela de acesso bloqueado (sem save)"""
        viewport_x = self.screen_manager.viewport_x
        viewport_y = self.screen_manager.viewport_y
        viewport_w = self.screen_manager.viewport_width
        viewport_h = self.screen_manager.viewport_height

        # Container
        container_width = 500
        container_height = 280
        container_x = viewport_x + (viewport_w - container_width) // 2
        container_y = viewport_y + (viewport_h - container_height) // 2 - 50

        # Fundo
        container_rect = pygame.Rect(container_x, container_y, container_width, container_height)
        pygame.draw.rect(screen, (40, 40, 60), container_rect)
        pygame.draw.rect(screen, (255, 200, 0), container_rect, 3, border_radius=15)

        # Título
        title_font = self._get_font(28, bold=True)
        title_text = title_font.render("ACESSO BLOQUEADO", True, (255, 200, 100))
        title_x = container_x + (container_width - title_text.get_width()) // 2
        title_y = container_y + 20
        screen.blit(title_text, (title_x, title_y))

        # Mensagem
        msg_font = self._get_font(20)
        lines = [
            "Você precisa iniciar um jogo primeiro!",
            "",
            "Volte ao menu principal e selecione:",
            "INICIAR JOGO",
        ]

        line_y = title_y + 50
        for line in lines:
            if line:
                msg_text = msg_font.render(line, True, (200, 200, 220))
            else:
                msg_text = msg_font.render("", True, (200, 200, 220))
            msg_x = container_x + (container_width - msg_text.get_width()) // 2
            screen.blit(msg_text, (msg_x, line_y))
            line_y += 35

    def _render_title(self, screen):
        """Renderiza o título"""
        title_font = self._get_font(48, bold=True)
        title_text = title_font.render("MYSTERY GIFT", True, (255, 215, 0))
        title_x = self.screen_manager.viewport_x + (self.screen_manager.viewport_width - title_text.get_width()) // 2
        title_y = self.screen_manager.viewport_y + 50
        screen.blit(title_text, (title_x, title_y))

        sub_font = self._get_font(20)
        sub_text = sub_font.render("Resgate Pokémon especiais com códigos!", True, (200, 200, 200))
        sub_x = self.screen_manager.viewport_x + (self.screen_manager.viewport_width - sub_text.get_width()) // 2
        sub_y = title_y + 50
        screen.blit(sub_text, (sub_x, sub_y))

    def _render_input_screen(self, screen):
        """Renderiza a tela de input de código"""
        viewport_x = self.screen_manager.viewport_x
        viewport_y = self.screen_manager.viewport_y
        viewport_w = self.screen_manager.viewport_width
        viewport_h = self.screen_manager.viewport_height

        container_width = 400
        container_height = 150
        container_x = viewport_x + (viewport_w - container_width) // 2
        container_y = viewport_y + viewport_h // 3

        container_rect = pygame.Rect(container_x, container_y, container_width, container_height)
        pygame.draw.rect(screen, (30, 30, 40), container_rect)
        pygame.draw.rect(screen, (100, 100, 120), container_rect, 3, border_radius=10)

        label_font = self._get_font(18)
        label_text = label_font.render("Digite seu código:", True, (200, 200, 200))
        label_x = container_x + 20
        label_y = container_y + 20
        screen.blit(label_text, (label_x, label_y))

        # Dica de colar
        hint_font = self._get_font(12)
        hint_text = hint_font.render("(Ctrl+V para colar)", True, (150, 150, 150))
        hint_x = container_x + container_width - hint_text.get_width() - 20
        hint_y = container_y + 25
        screen.blit(hint_text, (hint_x, hint_y))

        input_width = container_width - 40
        input_height = 50
        input_x = container_x + 20
        input_y = container_y + 60

        input_rect = pygame.Rect(input_x, input_y, input_width, input_height)
        pygame.draw.rect(screen, (20, 20, 30), input_rect)
        pygame.draw.rect(screen, (255, 215, 0), input_rect, 2)

        display_text = self.code_input if self.code_input else "XXXX-XXXX"
        color = (255, 255, 255) if self.code_input else (100, 100, 100)
        input_font = self._get_font(28, bold=True)
        text_surface = input_font.render(display_text, True, color)
        text_x = input_x + (input_width - text_surface.get_width()) // 2
        text_y = input_y + (input_height - text_surface.get_height()) // 2
        screen.blit(text_surface, (text_x, text_y))

        if int(time.time() * 2) % 2 < 1 and self.code_input:
            cursor_x = text_x + text_surface.get_width() + 2
            cursor_y = text_y
            cursor_height = text_surface.get_height()
            pygame.draw.line(screen, (255, 215, 0),
                             (cursor_x, cursor_y),
                             (cursor_x, cursor_y + cursor_height), 2)

        info_font = self._get_font(14)
        info_text = info_font.render("Códigos são case-insensitive (ex: ABC123)", True, (120, 120, 120))
        info_x = container_x + (container_width - info_text.get_width()) // 2
        info_y = input_y + input_height + 10
        screen.blit(info_text, (info_x, info_y))

        if self.redeem_button:
            self.redeem_button.render(screen, self._get_font(24))

    def _render_success_screen(self, screen):
        """Renderiza a tela de sucesso"""
        viewport_x = self.screen_manager.viewport_x
        viewport_y = self.screen_manager.viewport_y
        viewport_w = self.screen_manager.viewport_width
        viewport_h = self.screen_manager.viewport_height

        overlay = pygame.Surface((viewport_w, viewport_h), pygame.SRCALPHA)
        overlay.fill((0, 200, 0, 30))
        screen.blit(overlay, (viewport_x, viewport_y))

        container_width = 450
        container_height = 420
        container_x = viewport_x + (viewport_w - container_width) // 2
        container_y = viewport_y + (viewport_h - container_height) // 2 - 50

        container_rect = pygame.Rect(container_x, container_y, container_width, container_height)
        pygame.draw.rect(screen, (30, 60, 30), container_rect)
        pygame.draw.rect(screen, (255, 215, 0), container_rect, 3, border_radius=15)

        success_font = self._get_font(32, bold=True)
        success_text = success_font.render("RESGATE REALIZADO!", True, (255, 215, 0))
        text_x = container_x + (container_width - success_text.get_width()) // 2
        text_y = container_y + 20
        screen.blit(success_text, (text_x, text_y))

        msg_font = self._get_font(18)
        msg_text = msg_font.render(self.success_message, True, (200, 255, 200))
        msg_x = container_x + (container_width - msg_text.get_width()) // 2
        msg_y = text_y + 45
        screen.blit(msg_text, (msg_x, msg_y))

        if self.redeemed_pokemon:
            sprite = self.redeemed_pokemon.pokedex.get_sprite(
                self.redeemed_pokemon.id, "front", self.redeemed_pokemon.is_shiny
            )

            if sprite:
                sprite_width = int(sprite.get_width() * self.animation_scale)
                sprite_height = int(sprite.get_height() * self.animation_scale)
                scaled_sprite = pygame.transform.scale(sprite, (sprite_width, sprite_height))

                sprite_x = container_x + (container_width - scaled_sprite.get_width()) // 2
                sprite_y = container_y + 100
                screen.blit(scaled_sprite, (sprite_x, sprite_y))

                name_font = self._get_font(24, bold=True)
                shiny_text = " SHINY" if self.redeemed_pokemon.is_shiny else ""
                name_text = name_font.render(f"{self.redeemed_pokemon.name} Lv.5{shiny_text}",
                                             True, (255, 255, 255))
                name_x = container_x + (container_width - name_text.get_width()) // 2
                name_y = sprite_y + scaled_sprite.get_height() + 10
                screen.blit(name_text, (name_x, name_y))

                type_font = self._get_font(16)
                type_text = type_font.render(f"Tipo: {' / '.join(self.redeemed_pokemon.types)}",
                                             True, (180, 180, 180))
                type_x = container_x + (container_width - type_text.get_width()) // 2
                type_y = name_y + 30
                screen.blit(type_text, (type_x, type_y))

        info_font = self._get_font(14)
        info_text = info_font.render("Voltando ao menu em alguns segundos...", True, (150, 150, 150))
        info_x = container_x + (container_width - info_text.get_width()) // 2
        info_y = container_y + container_height - 35
        screen.blit(info_text, (info_x, info_y))

        for particle in self.particles:
            particle_x = viewport_x + int(particle['x'])
            particle_y = viewport_y + int(particle['y'])
            pygame.draw.circle(screen, particle['color'], (particle_x, particle_y), particle['size'])

    def _render_error_screen(self, screen):
        """Renderiza a tela de erro"""
        viewport_x = self.screen_manager.viewport_x
        viewport_y = self.screen_manager.viewport_y
        viewport_w = self.screen_manager.viewport_width
        viewport_h = self.screen_manager.viewport_height

        container_width = 450
        container_height = 280
        container_x = viewport_x + (viewport_w - container_width) // 2
        container_y = viewport_y + viewport_h // 3 + 50

        container_rect = pygame.Rect(container_x, container_y, container_width, container_height)
        pygame.draw.rect(screen, (60, 30, 30), container_rect)
        pygame.draw.rect(screen, (255, 100, 100), container_rect, 3, border_radius=10)

        from src.data.mystery_gift_data import is_code_invalid, get_code_info

        is_invalid_code = is_code_invalid(self.code_input) if self.code_input else False
        code_info = get_code_info(self.code_input) if is_invalid_code else None

        error_font = self._get_font(28, bold=True)
        if is_invalid_code:
            error_text = error_font.render("EVENTO ENCERRADO!", True, (255, 150, 100))
        else:
            error_text = error_font.render("ERRO!", True, (255, 100, 100))

        text_x = container_x + (container_width - error_text.get_width()) // 2
        text_y = container_y + 25
        screen.blit(error_text, (text_x, text_y))

        msg_font = self._get_font(18)

        if is_invalid_code and code_info:
            event_name = code_info.get("event_name", "Evento")
            event_date = code_info.get("event_date", "Data desconhecida")
            lines = [
                f"O código {self.code_input} pertence ao evento:",
                f"\"{event_name}\" ({event_date})",
                "",
                "Este evento já foi encerrado e não está mais disponível.",
                "Fique ligado para novos eventos!"
            ]

            line_y = container_y + 80
            for line in lines:
                if line:
                    msg_text = msg_font.render(line, True, (255, 200, 200))
                else:
                    msg_text = msg_font.render("", True, (255, 200, 200))
                msg_x = container_x + (container_width - msg_text.get_width()) // 2
                screen.blit(msg_text, (msg_x, line_y))
                line_y += 25
        else:
            msg_text = msg_font.render(self.error_message, True, (255, 200, 200))
            msg_x = container_x + (container_width - msg_text.get_width()) // 2
            msg_y = container_y + 100
            screen.blit(msg_text, (msg_x, msg_y))

        try_again_x = container_x + (container_width - 140) // 2
        try_again_y = container_y + container_height - 60

        try_again_rect = pygame.Rect(try_again_x, try_again_y, 140, 40)
        mouse_pos = pygame.mouse.get_pos()
        is_hovered = try_again_rect.collidepoint(mouse_pos)

        color = (80, 100, 80) if is_hovered else (50, 70, 50)
        pygame.draw.rect(screen, color, try_again_rect)
        pygame.draw.rect(screen, (255, 255, 255), try_again_rect, 2)

        btn_font = self._get_font(20)
        btn_text = btn_font.render("Tentar Novamente", True, (255, 255, 255))
        btn_x = try_again_x + (140 - btn_text.get_width()) // 2
        btn_y = try_again_y + (40 - btn_text.get_height()) // 2
        screen.blit(btn_text, (btn_x, btn_y))

        mouse_buttons = pygame.mouse.get_pressed()
        if mouse_buttons[0] and is_hovered:
            current_time = time.time()
            if current_time - self._last_error_click > 0.3:
                self._last_error_click = current_time
                self.state = "input"
                self.error_message = ""
                self.code_input = ""

    def _draw_gradient_background(self, screen):
        """Desenha fundo com gradiente"""
        for i in range(self.screen_manager.window_height):
            color_value = int(20 + (i / self.screen_manager.window_height) * 30)
            color = (color_value, color_value, color_value + 40)
            pygame.draw.line(screen, color, (0, i), (self.screen_manager.window_width, i))

    def on_resize(self):
        """Chamado quando a janela é redimensionada"""
        if self.back_button:
            self.back_button.y = self.screen_manager.viewport_height - 60
            self.back_button.update_position(
                self.screen_manager.viewport_x,
                self.screen_manager.viewport_y
            )

        if self.state == "input" and self.has_save:
            self.redeem_button = None

        if self.particles and self.state == "success":
            center_x = self.screen_manager.viewport_width // 2
            center_y = self.screen_manager.viewport_height // 2
            for particle in self.particles:
                particle['x'] = center_x
                particle['y'] = center_y

    def _get_font(self, size, bold=False):
        """Obtém uma fonte com cache"""
        from src.core.render_context import render_context
        return render_context.get_font(size, bold)