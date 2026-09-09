# src/scenes/multiplayer_menu_scene/multiplayer_menu_scene.py

import pygame
import socket
import subprocess
import sys
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
        self.back_btn = pygame.Rect(0, 0, 150, 40)
        self.copy_btn = pygame.Rect(0, 0, 150, 30)  # Botão de copiar IP

        # Campo de IP
        self.ip_input = ""
        self.input_active = False
        self.input_rect = pygame.Rect(0, 0, 300, 40)

        self._center_buttons()

        self.mode = None
        self.connecting = False

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

        self.create_btn.center = (vx + vw//2, vy + vh//2 - 60)
        self.join_btn.center = (vx + vw//2, vy + vh//2)
        self.back_btn.center = (vx + vw//2, vy + vh//2 + 120)
        self.input_rect.center = (vx + vw//2, vy + vh//2 + 60)
        self.copy_btn.center = (vx + vw//2, vy + vh//2 - 110)  # acima do criar sala

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
            if self.create_btn.collidepoint(event.pos):
                self._create_room()
            elif self.join_btn.collidepoint(event.pos):
                self.input_active = True
            elif self.back_btn.collidepoint(event.pos):
                sound_manager.play_effect(SoundEffect.CLICK)
                self.game.current_scene = self.game.menu_scene
            elif self.copy_btn.collidepoint(event.pos):
                self._copy_ip_to_clipboard()
            elif self.input_rect.collidepoint(event.pos):
                self.input_active = True
            else:
                self.input_active = False

    def _create_room(self):
        request_firewall_permission(self.port, "Pokemon TD Multiplayer")
        if self.network.start_host(self.port):
            toast_info(f"Sala criada! IP: {self.host_ip}:{self.port}")
            from src.scenes.lobby_scene.lobby_scene import LobbyScene
            self.game.current_scene = LobbyScene(self.game, is_host=True, network=self.network)
        else:
            toast_warning("Falha ao criar sala. Verifique a porta.")

    def _try_join(self):
        if not self.ip_input:
            toast_warning("Digite um IP válido.")
            return
        self.input_active = False
        if self.network.connect_to_host(self.ip_input, self.port):
            toast_info(f"Conectado ao servidor {self.ip_input}:{self.port}")
            from src.scenes.lobby_scene.lobby_scene import LobbyScene
            self.game.current_scene = LobbyScene(self.game, is_host=False, network=self.network)
        else:
            toast_warning("Não foi possível conectar. Verifique IP e se o servidor está rodando.")

    def _copy_ip_to_clipboard(self):
        ip_port = f"{self.host_ip}:{self.port}"
        try:
            if sys.platform == "win32":
                subprocess.run(["clip"], input=ip_port.encode('utf-8'), check=True)
            elif sys.platform == "darwin":
                subprocess.run(["pbcopy"], input=ip_port.encode('utf-8'), check=True)
            else:
                # Linux: tenta xclip ou xsel
                try:
                    subprocess.run(["xclip", "-selection", "clipboard"], input=ip_port.encode('utf-8'), check=True)
                except:
                    subprocess.run(["xsel", "--clipboard", "--input"], input=ip_port.encode('utf-8'), check=True)
            toast_info("IP copiado para a área de transferência!")
        except Exception as e:
            toast_warning(f"Não foi possível copiar: {e}")

    def fixed_update(self, dt):
        pass

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

        font_btn = pygame.font.Font(None, 32)
        self._draw_button(screen, self.create_btn, "CRIAR SALA", (50, 150, 50), (100, 200, 100))
        self._draw_button(screen, self.join_btn, "ENTRAR EM SALA", (50, 50, 150), (100, 100, 200))
        self._draw_button(screen, self.copy_btn, "COPIAR IP", (80, 80, 80), (120, 120, 120))

        pygame.draw.rect(screen, (60, 60, 80), self.input_rect, border_radius=5)
        pygame.draw.rect(screen, (200, 200, 200), self.input_rect, 2, border_radius=5)
        ip_text = font_btn.render(self.ip_input or "Digite o IP...", True, (255, 255, 255))
        screen.blit(ip_text, (self.input_rect.x + 10, self.input_rect.y + 8))

        self._draw_button(screen, self.back_btn, "VOLTAR", (100, 50, 50), (150, 80, 80))

        small_font = pygame.font.Font(None, 20)
        info = small_font.render("Certifique-se de que ambos estão na mesma rede.", True, (180, 180, 180))
        screen.blit(info, (vx + vw//2 - info.get_width()//2, vy + vh - 40))

    def _draw_button(self, screen, rect, text, color, hover_color):
        mouse = pygame.mouse.get_pos()
        hover = rect.collidepoint(mouse)
        pygame.draw.rect(screen, hover_color if hover else color, rect, border_radius=10)
        pygame.draw.rect(screen, (255, 255, 255), rect, 2, border_radius=10)
        font = pygame.font.Font(None, 32)
        txt = font.render(text, True, (255, 255, 255))
        txt_rect = txt.get_rect(center=rect.center)
        screen.blit(txt, txt_rect)