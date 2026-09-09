# src/scenes/multiplayer_menu_scene/multiplayer_menu_scene.py

import pygame
import socket
import tkinter as tk
from src.scenes.base_scene import BaseScene
from src.managers.sounds.sound_manager import sound_manager, SoundEffect
from src.network.manager import NetworkManager
from src.network.firewall_utils import request_firewall_permission
from src.ui.toast_renderer import toast_info, toast_warning


class MultiplayerMenuScene(BaseScene):
    """Tela de multiplayer com escolha de nome"""

    def __init__(self, game):
        super().__init__(game)
        self.network = NetworkManager()

        # ===== NOME DO JOGADOR =====
        self.player_name = "Jogador"
        self.name_input = ""
        self.name_active = True  # Começa editando o nome
        self.network.set_name("Jogador")

        self.host_ip = self._get_local_ip()
        self.port = 12345

        # ===== ESTADO =====
        self.ip_input = ""
        self.input_active = False
        self.status_message = ""
        self.status_timer = 0
        self.connecting = False

        # ===== UI =====
        self.create_btn = pygame.Rect(0, 0, 220, 45)
        self.join_btn = pygame.Rect(0, 0, 220, 45)
        self.connect_btn = pygame.Rect(0, 0, 120, 40)
        self.copy_btn = pygame.Rect(0, 0, 150, 32)
        self.back_btn = pygame.Rect(0, 0, 120, 40)
        self.input_rect = pygame.Rect(0, 0, 280, 38)
        self.name_rect = pygame.Rect(0, 0, 200, 35)

        self._update_button_positions()

        # ===== CLIPBOARD =====
        self._init_clipboard()

        # ===== FONTES =====
        self.font_title = pygame.font.Font(None, 42)
        self.font = pygame.font.Font(None, 26)
        self.font_small = pygame.font.Font(None, 20)
        self.font_btn = pygame.font.Font(None, 24)

        # Status inicial
        self._update_status("Digite seu nome e pressione ENTER", (255, 215, 0))

    # ======================================================================
    # INICIALIZAÇÃO
    # ======================================================================

    def _init_clipboard(self):
        try:
            self._root = tk.Tk()
            self._root.withdraw()
            self._clipboard_available = True
        except:
            self._clipboard_available = False

    def _copy_to_clipboard(self, text):
        if not self._clipboard_available:
            return False
        try:
            self._root.clipboard_clear()
            self._root.clipboard_append(text)
            self._root.update()
            return True
        except:
            return False

    def _paste_from_clipboard(self):
        if not self._clipboard_available:
            return ""
        try:
            return self._root.clipboard_get()
        except:
            return ""

    def _get_local_ip(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return "127.0.0.1"

    def _update_status(self, text, color=(180, 180, 200)):
        self.status_message = text
        self.status_color = color
        self.status_timer = 3.0

    def _update_button_positions(self):
        vw = self.screen_manager.viewport_width
        vh = self.screen_manager.viewport_height
        vx = self.screen_manager.viewport_x
        vy = self.screen_manager.viewport_y

        # Botão Voltar (canto superior esquerdo)
        self.back_btn.topleft = (vx + 15, vy + 15)

        # Campo de nome
        center_x = vx + vw // 2
        center_y = vy + vh // 2

        # Campo de nome (acima dos botões)
        self.name_rect.center = (center_x, center_y - 160)

        # Botão Criar Sala
        self.create_btn.center = (center_x, center_y - 100)

        # Botão Entrar em Sala
        self.join_btn.center = (center_x, center_y - 40)

        # Campo de IP
        self.input_rect.center = (center_x - 80, center_y + 25)

        # Botão Conectar
        self.connect_btn.center = (center_x + 160, center_y + 25)

        # Botão Copiar IP (abaixo)
        self.copy_btn.center = (center_x, center_y + 85)

    # ======================================================================
    # AÇÕES
    # ======================================================================

    def _confirm_name(self):
        """Confirma o nome do jogador"""
        name = self.name_input.strip()
        if name:
            self.player_name = name
            self.network.set_name(name)
            self.name_active = False
            self._update_status(f"Bem-vindo, {name}!", (100, 255, 100))
            toast_info(f"Seu nome: {name}")
        else:
            self._update_status("Digite um nome valido!", (255, 200, 100))

    def _create_room(self):
        if self.name_active:
            self._update_status("Confirme seu nome primeiro!", (255, 200, 100))
            return

        self._update_status("Criando sala...", (255, 215, 0))
        self.connecting = True

        request_firewall_permission(self.port, "Pokemon TD Multiplayer")
        if self.network.start_host(self.port):
            toast_info(f"Sala criada! IP: {self.host_ip}:{self.port}")
            self._update_status(f"Sala criada em {self.host_ip}:{self.port}", (100, 255, 100))
            from src.scenes.lobby_scene.lobby_scene import LobbyScene
            self.game.current_scene = LobbyScene(self.game, is_host=True, network=self.network)
        else:
            self._update_status("Falha ao criar sala!", (255, 100, 100))
            toast_warning("Falha ao criar sala. Verifique a porta.")
            self.connecting = False

    def _try_join(self):
        if self.name_active:
            self._update_status("Confirme seu nome primeiro!", (255, 200, 100))
            return

        if not self.ip_input:
            self._update_status("Digite um IP valido!", (255, 200, 100))
            toast_warning("Digite um IP valido.")
            return

        clean_ip = self.ip_input.strip()
        if ':' in clean_ip:
            clean_ip = clean_ip.split(':')[0]
            self.ip_input = clean_ip
            toast_info(f"IP ajustado para: {clean_ip}")

        self._update_status(f"Conectando a {clean_ip}...", (255, 215, 0))
        self.input_active = False
        self.connecting = True

        if self.network.connect_to_host(clean_ip, self.port):
            toast_info(f"Conectado ao servidor {clean_ip}:{self.port}")
            self._update_status(f"Conectado a {clean_ip}!", (100, 255, 100))
            from src.scenes.lobby_scene.lobby_scene import LobbyScene
            self.game.current_scene = LobbyScene(self.game, is_host=False, network=self.network)
        else:
            self._update_status("Falha ao conectar!", (255, 100, 100))
            toast_warning("Nao foi possivel conectar. Verifique IP e se o servidor esta rodando.")
            self.connecting = False

    def _copy_ip(self):
        if self._copy_to_clipboard(self.host_ip):
            self._update_status(f"IP {self.host_ip} copiado!", (100, 255, 100))
            toast_info(f"IP {self.host_ip} copiado para a area de transferencia!")
        else:
            self._update_status("Nao foi possivel copiar o IP", (255, 200, 100))
            toast_warning("Nao foi possivel copiar o IP.")

    # ======================================================================
    # EVENTOS
    # ======================================================================

    def handle_event(self, event):
        if event.type == pygame.VIDEORESIZE:
            self._update_button_positions()
            return

        # ===== TECLADO =====
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self._return_to_menu()
                return

            # ===== EDITANDO NOME =====
            if self.name_active:
                if event.key == pygame.K_RETURN:
                    self._confirm_name()
                elif event.key == pygame.K_BACKSPACE:
                    self.name_input = self.name_input[:-1]
                else:
                    if len(self.name_input) < 20 and event.unicode.isprintable():
                        self.name_input += event.unicode
                return

            # ===== EDITANDO IP =====
            if self.input_active:
                if event.key == pygame.K_RETURN:
                    self._try_join()
                elif event.key == pygame.K_BACKSPACE:
                    self.ip_input = self.ip_input[:-1]
                elif event.key == pygame.K_v and (pygame.key.get_mods() & pygame.KMOD_CTRL):
                    pasted = self._paste_from_clipboard()
                    if pasted:
                        self.ip_input += pasted
                        self._update_status("IP colado!", (100, 255, 100))
                else:
                    if len(self.ip_input) < 20 and event.unicode.isprintable():
                        self.ip_input += event.unicode
                return

            # Atalhos
            if event.key == pygame.K_c and not self.connecting:
                self._copy_ip()

        # ===== MOUSE =====
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mouse_pos = event.pos

            # Botão Voltar
            if self.back_btn.collidepoint(mouse_pos):
                sound_manager.play_effect(SoundEffect.CLICK)
                self._return_to_menu()
                return

            # Campo de nome
            if self.name_rect.collidepoint(mouse_pos):
                self.name_active = True
                return

            # Botão Criar Sala
            if self.create_btn.collidepoint(mouse_pos) and not self.connecting:
                self._create_room()
                return

            # Botão Entrar em Sala
            if self.join_btn.collidepoint(mouse_pos) and not self.connecting:
                self.input_active = True
                self._update_status("Digite o IP e clique em Conectar", (255, 215, 0))
                return

            # Botão Conectar
            if self.connect_btn.collidepoint(mouse_pos) and not self.connecting:
                self._try_join()
                return

            # Botão Copiar IP
            if self.copy_btn.collidepoint(mouse_pos) and not self.connecting:
                self._copy_ip()
                return

            # Campo de IP
            if self.input_rect.collidepoint(mouse_pos):
                self.input_active = True
                return

            # Clique fora = desativa inputs
            self.input_active = False
            self.name_active = False

    def _return_to_menu(self):
        self.network.stop()
        self.game.current_scene = self.game.menu_scene

    # ======================================================================
    # UPDATE
    # ======================================================================

    def fixed_update(self, dt):
        if self.status_timer > 0:
            self.status_timer -= dt

    # ======================================================================
    # RENDERIZAÇÃO
    # ======================================================================

    def render(self, screen):
        # Fundo
        screen.fill((18, 20, 35))

        vw = self.screen_manager.viewport_width
        vh = self.screen_manager.viewport_height
        vx = self.screen_manager.viewport_x
        vy = self.screen_manager.viewport_y

        self._update_button_positions()

        # ===== TÍTULO =====
        title = self.font_title.render("MULTIPLAYER", True, (255, 215, 0))
        title_rect = title.get_rect(center=(vx + vw // 2, vy + 55))
        screen.blit(title, title_rect)

        # Linha decorativa
        pygame.draw.line(screen, (60, 60, 80),
                         (vx + vw // 4, vy + 80),
                         (vx + vw * 3 // 4, vy + 80), 2)

        # ===== CAMPO DE NOME =====
        name_label = self.font_small.render("Seu nome:", True, (180, 180, 200))
        screen.blit(name_label, (self.name_rect.x, self.name_rect.y - 25))

        border_color = (255, 215, 0) if self.name_active else (60, 60, 80)
        pygame.draw.rect(screen, (20, 22, 40), self.name_rect, border_radius=6)
        pygame.draw.rect(screen, border_color, self.name_rect, 2, border_radius=6)

        display_name = self.name_input if self.name_input else self.player_name
        if self.name_active:
            display_text = display_name + ("|" if pygame.time.get_ticks() % 1000 < 500 else " ")
            color = (255, 255, 255)
        else:
            display_text = f"✓ {self.player_name}"
            color = (100, 255, 100)

        txt = self.font.render(display_text, True, color)
        screen.blit(txt, (self.name_rect.x + 12, self.name_rect.y + 7))

        # ===== STATUS DO SERVIDOR =====
        if self.network.is_host:
            status_text = f"Servidor: {self.host_ip}:{self.port}"
            color = (100, 255, 100)
            status = self.font_small.render(status_text, True, color)
            screen.blit(status, (vx + 25, vy + 100))

        # ===== BOTÕES =====
        self._draw_button(screen, self.create_btn, "Criar Sala", (50, 100, 50), (80, 160, 80))
        self._draw_button(screen, self.join_btn, "Entrar em Sala", (50, 50, 120), (80, 80, 180))

        # ===== CAMPO DE IP =====
        border_color = (255, 215, 0) if self.input_active else (60, 60, 80)
        pygame.draw.rect(screen, (20, 22, 40), self.input_rect, border_radius=6)
        pygame.draw.rect(screen, border_color, self.input_rect, 2, border_radius=6)

        if self.input_active:
            display_text = self.ip_input if self.ip_input else "Digite o IP... (Ctrl+V)"
            color = (255, 255, 255) if self.ip_input else (120, 120, 150)
        else:
            display_text = self.ip_input if self.ip_input else "Clique para digitar..."
            color = (255, 255, 255) if self.ip_input else (80, 80, 110)

        txt = self.font_small.render(display_text, True, color)
        screen.blit(txt, (self.input_rect.x + 12, self.input_rect.y + 9))

        # ===== BOTÕES =====
        self._draw_button(screen, self.connect_btn, "Conectar", (50, 100, 50), (80, 160, 80))
        self._draw_button(screen, self.copy_btn, "Copiar IP", (60, 60, 100), (100, 100, 160))
        self._draw_button(screen, self.back_btn, "Voltar", (80, 40, 40), (140, 60, 60))

        # ===== STATUS =====
        if self.status_timer > 0 and self.status_message:
            color = self.status_color if hasattr(self, 'status_color') else (180, 180, 200)
            txt = self.font_small.render(self.status_message, True, color)
            txt_rect = txt.get_rect(center=(vx + vw // 2, vy + vh - 60))
            screen.blit(txt, txt_rect)

        # ===== INSTRUÇÕES =====
        instr = self.font_small.render("ENTER = confirmar | C = copiar IP | Ctrl+V = colar", True, (80, 80, 110))
        screen.blit(instr, (vx + 25, vy + vh - 25))

    def _draw_button(self, screen, rect, text, color, hover_color):
        mouse = pygame.mouse.get_pos()
        hover = rect.collidepoint(mouse)
        pygame.draw.rect(screen, hover_color if hover else color, rect, border_radius=8)
        pygame.draw.rect(screen, (200, 200, 200), rect, 1, border_radius=8)

        font_size = 22 if len(text) < 12 else 18
        font = pygame.font.Font(None, font_size)
        txt = font.render(text, True, (255, 255, 255))
        txt_rect = txt.get_rect(center=rect.center)
        screen.blit(txt, txt_rect)

    # ======================================================================
    # CICLO DE VIDA
    # ======================================================================

    def on_enter(self):
        pass

    def on_exit(self):
        pass