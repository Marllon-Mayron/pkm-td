# src/scenes/multiplayer_menu_scene/multiplayer_menu_scene.py

import pygame
import socket
from src.scenes.base_scene import BaseScene
from src.managers.sounds.sound_manager import sound_manager, SoundEffect
from src.network.manager import NetworkManager
from src.network.firewall_utils import request_firewall_permission
from src.ui.toast_renderer import toast_info, toast_warning


class MultiplayerMenuScene(BaseScene):
    def __init__(self, game):
        super().__init__(game)
        self.network = NetworkManager()
        self.network.set_name("Jogador")

        self.host_ip = self._get_local_ip()
        self.port = 12345

        # Botões
        self.create_btn = pygame.Rect(0, 0, 250, 50)
        self.join_btn = pygame.Rect(0, 0, 250, 50)
        self.connect_btn = pygame.Rect(0, 0, 120, 40)
        self.back_btn = pygame.Rect(0, 0, 150, 40)

        # Campo de IP
        self.ip_input = ""
        self.input_active = False
        self.input_rect = pygame.Rect(0, 0, 300, 40)

        self._center_buttons()

        self.mode = None
        self.connecting = False

        # Feedback visual
        self.status_message = ""
        self.status_timer = 0

    def _get_local_ip(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return "127.0.0.1"

    def _center_buttons(self):
        vw = self.screen_manager.viewport_width
        vh = self.screen_manager.viewport_height
        vx = self.screen_manager.viewport_x
        vy = self.screen_manager.viewport_y

        self.create_btn.center = (vx + vw//2, vy + vh//2 - 80)
        self.join_btn.center = (vx + vw//2, vy + vh//2 - 20)
        self.input_rect.center = (vx + vw//2 - 70, vy + vh//2 + 40)
        self.connect_btn.center = (vx + vw//2 + 160, vy + vh//2 + 40)
        self.back_btn.center = (vx + vw//2, vy + vh//2 + 120)

    def handle_event(self, event):
        if event.type == pygame.VIDEORESIZE:
            self._center_buttons()
            return

        if event.type == pygame.KEYDOWN:
            if self.input_active:
                if event.key == pygame.K_RETURN:
                    self._try_join()
                elif event.key == pygame.K_BACKSPACE:
                    self.ip_input = self.ip_input[:-1]
                else:
                    if len(self.ip_input) < 20 and event.unicode.isprintable():
                        self.ip_input += event.unicode
                return

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mouse_pos = event.pos

            if self.create_btn.collidepoint(mouse_pos):
                self._create_room()
                return

            if self.connect_btn.collidepoint(mouse_pos):
                self._try_join()
                return

            if self.join_btn.collidepoint(mouse_pos):
                self.input_active = True
                self.status_message = "Digite o IP e clique em CONECTAR"
                self.status_timer = 3.0
                return

            if self.back_btn.collidepoint(mouse_pos):
                sound_manager.play_effect(SoundEffect.CLICK)
                self.game.current_scene = self.game.menu_scene
                return

            if self.input_rect.collidepoint(mouse_pos):
                self.input_active = True
                return

            self.input_active = False

    def _create_room(self):
        self.status_message = "Criando sala..."
        self.status_timer = 2.0

        request_firewall_permission(self.port, "Pokemon TD Multiplayer")
        if self.network.start_host(self.port):
            toast_info(f"Sala criada! IP: {self.host_ip}:{self.port}")
            from src.scenes.lobby_scene.lobby_scene import LobbyScene
            self.game.current_scene = LobbyScene(self.game, is_host=True, network=self.network)
        else:
            self.status_message = "Falha ao criar sala!"
            self.status_timer = 3.0
            toast_warning("Falha ao criar sala. Verifique a porta.")

    def _try_join(self):
        if not self.ip_input:
            self.status_message = "Digite um IP válido!"
            self.status_timer = 2.0
            toast_warning("Digite um IP válido.")
            return

        # Remove espaços e possível porta
        clean_ip = self.ip_input.strip()
        if ':' in clean_ip:
            clean_ip = clean_ip.split(':')[0]
            self.ip_input = clean_ip
            toast_info(f"IP ajustado para: {clean_ip}")

        self.status_message = f"Conectando a {clean_ip}..."
        self.status_timer = 2.0
        self.input_active = False

        if self.network.connect_to_host(clean_ip, self.port):
            toast_info(f"Conectado ao servidor {clean_ip}:{self.port}")
            from src.scenes.lobby_scene.lobby_scene import LobbyScene
            self.game.current_scene = LobbyScene(self.game, is_host=False, network=self.network)
        else:
            self.status_message = "Falha ao conectar!"
            self.status_timer = 3.0
            toast_warning("Não foi possível conectar. Verifique IP e se o servidor está rodando.")

    def fixed_update(self, dt):
        if self.status_timer > 0:
            self.status_timer -= dt

    def render(self, screen):
        screen.fill((20, 20, 30))

        vw = self.screen_manager.viewport_width
        vh = self.screen_manager.viewport_height
        vx = self.screen_manager.viewport_x
        vy = self.screen_manager.viewport_y

        font = pygame.font.Font(None, 48)
        title = font.render("MULTIPLAYER", True, (255, 215, 0))
        title_rect = title.get_rect(center=(vx + vw//2, vy + 80))
        screen.blit(title, title_rect)

        font_small = pygame.font.Font(None, 24)
        if self.network.is_host:
            status_text = f"🟢 Servidor rodando em: {self.host_ip}:{self.port}"
            screen.blit(font_small.render(status_text, True, (100, 255, 100)), (vx + 30, vy + 130))

        font_btn = pygame.font.Font(None, 32)
        self._draw_button(screen, self.create_btn, "CRIAR SALA", (50, 150, 50), (100, 200, 100))
        self._draw_button(screen, self.join_btn, "ENTRAR EM SALA", (50, 50, 150), (100, 100, 200))

        border_color = (200, 200, 50) if self.input_active else (200, 200, 200)
        pygame.draw.rect(screen, (60, 60, 80), self.input_rect, border_radius=5)
        pygame.draw.rect(screen, border_color, self.input_rect, 2, border_radius=5)

        ip_display = self.ip_input if self.ip_input else "Digite o IP..."
        color = (255, 255, 255) if self.ip_input else (150, 150, 150)
        ip_text = font_btn.render(ip_display, True, color)
        screen.blit(ip_text, (self.input_rect.x + 10, self.input_rect.y + 8))

        self._draw_button(screen, self.connect_btn, "CONECTAR", (50, 100, 50), (100, 150, 100))
        self._draw_button(screen, self.back_btn, "VOLTAR", (100, 50, 50), (150, 80, 80))

        if self.status_timer > 0 and self.status_message:
            status_font = pygame.font.Font(None, 24)
            color = (255, 200, 100) if "Falha" not in self.status_message else (255, 100, 100)
            status_text = status_font.render(self.status_message, True, color)
            screen.blit(status_text, (vx + vw//2 - status_text.get_width()//2, vy + vh - 80))

        small_font = pygame.font.Font(None, 18)
        info = small_font.render("Certifique-se de que ambos estão na mesma rede (VPN ou LAN).", True, (180, 180, 180))
        screen.blit(info, (vx + vw//2 - info.get_width()//2, vy + vh - 30))

    def _draw_button(self, screen, rect, text, color, hover_color):
        mouse = pygame.mouse.get_pos()
        hover = rect.collidepoint(mouse)
        pygame.draw.rect(screen, hover_color if hover else color, rect, border_radius=10)
        pygame.draw.rect(screen, (255, 255, 255), rect, 2, border_radius=10)
        font = pygame.font.Font(None, 28 if len(text) > 8 else 32)
        txt = font.render(text, True, (255, 255, 255))
        txt_rect = txt.get_rect(center=rect.center)
        screen.blit(txt, txt_rect)