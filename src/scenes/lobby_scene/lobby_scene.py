# src/scenes/lobby_scene/lobby_scene.py

import pygame
import random
import tkinter as tk
from src.scenes.base_scene import BaseScene
from src.ui.toast_renderer import toast_info, toast_warning
from src.managers.sounds.sound_manager import sound_manager, SoundEffect
from src.network.protocol import create_message


class LobbyScene(BaseScene):
    """Lobby multiplayer com design limpo e funcional"""

    def __init__(self, game, is_host, network):
        super().__init__(game)
        self.network = network
        self.is_host = is_host
        self.network.current_scene_callback = self._on_network_message

        # ===== DADOS =====
        self.my_name = network.my_name
        self.players = [self.my_name]  # Começa com o próprio nome
        self.opponent_name = None
        self.chat_messages = []
        self.chat_input = ""
        self.chat_active = False
        self.pending_trade_from = None
        self._animation_timer = 0
        self.players_received = False

        # ===== UI =====
        self.back_btn = pygame.Rect(0, 0, 120, 40)
        self.trade_btn = pygame.Rect(0, 0, 220, 35)
        self.send_btn = pygame.Rect(0, 0, 80, 32)
        self.chat_input_rect = pygame.Rect(0, 0, 0, 0)

        # Botões de resposta
        self.accept_btn = pygame.Rect(0, 0, 100, 40)
        self.decline_btn = pygame.Rect(0, 0, 100, 40)

        self._update_button_positions()

        # ===== CLIPBOARD =====
        self._init_clipboard()

        # ===== FONTES =====
        self.font_title = pygame.font.Font(None, 42)
        self.font = pygame.font.Font(None, 26)
        self.font_small = pygame.font.Font(None, 20)
        self.font_chat = pygame.font.Font(None, 18)

        # ===== ENVIA O NOME DO JOGADOR =====
        self.network.send_to_all(create_message("PLAYER_INFO", {"name": self.my_name}))
        print(f"[LOBBY] {self.my_name} entrou no lobby (host={self.is_host})")

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

    def _paste_from_clipboard(self):
        if not self._clipboard_available:
            return ""
        try:
            return self._root.clipboard_get()
        except:
            return ""

    def _update_button_positions(self):
        vw = self.screen_manager.viewport_width
        vh = self.screen_manager.viewport_height
        vx = self.screen_manager.viewport_x
        vy = self.screen_manager.viewport_y

        self.back_btn.topleft = (vx + 15, vy + 15)
        self.trade_btn.topleft = (vx + 25, vy + 200)
        self.chat_input_rect = pygame.Rect(vx + 280, vy + vh - 45, vw - 410, 32)
        self.send_btn.topleft = (self.chat_input_rect.right + 10, self.chat_input_rect.y)

        center_x = vx + vw // 2
        center_y = vy + vh // 2 + 60
        self.accept_btn.center = (center_x - 110, center_y)
        self.decline_btn.center = (center_x + 110, center_y)

    # ======================================================================
    # NETWORK
    # ======================================================================

    def _on_network_message(self, msg, conn=None):
        msg_type = msg.get("type")
        payload = msg.get("payload", {})

        if msg_type == "PLAYER_INFO":
            name = payload.get("name", "Desconhecido")
            if name != self.my_name and name not in self.players:
                self.players.append(name)
                self.opponent_name = name
                toast_info(f"{name} entrou na sala!")
                print(f"[LOBBY] Lista atualizada: {self.players}")

        elif msg_type == "PLAYER_LIST":
            players_data = payload.get("players", [])
            # Se for dicionário, converte para lista
            if isinstance(players_data, dict):
                new_players = list(players_data.values())
            else:
                new_players = players_data

            # Mantém o próprio nome e adiciona os outros
            self.players = [self.my_name]
            for name in new_players:
                if name != self.my_name and name not in self.players:
                    self.players.append(name)

            # Encontra o oponente
            for name in self.players:
                if name != self.my_name:
                    self.opponent_name = name
                    break

            print(f"[LOBBY] Lista recebida: {self.players}")
            if len(self.players) > 1:
                toast_info(f"Jogadores na sala: {len(self.players)}")

    def _open_trade_scene(self):
        from src.scenes.trade_scene.trade_scene import TradeScene
        self.game.current_scene = TradeScene(self.game, is_host=self.is_host, network=self.network)

    def _return_to_menu(self):
        self.network.stop()
        self.game.current_scene = self.game.menu_scene

    def _send_chat(self):
        if not self.chat_input.strip():
            return
        text = self.chat_input.strip()
        self.chat_input = ""
        self.network.send_to_all(create_message("CHAT_MESSAGE", {"sender": self.my_name, "text": text}))
        self.chat_messages.append(f"{self.my_name}: {text}")

    def _request_trade(self):
        if not self.opponent_name:
            toast_warning("Nenhum oponente conectado.")
            return
        self.network.send_to_all(create_message("TRADE_REQUEST", {"from": self.my_name}))
        toast_info(f"Solicitacao enviada para {self.opponent_name}.")

    def _handle_trade_response(self, accepted):
        self.network.send_to_all(create_message("TRADE_RESPONSE", {"accepted": accepted}))
        if accepted:
            self._open_trade_scene()
        else:
            self.pending_trade_from = None

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

            if self.chat_active:
                if event.key == pygame.K_RETURN:
                    self._send_chat()
                elif event.key == pygame.K_BACKSPACE:
                    self.chat_input = self.chat_input[:-1]
                elif event.key == pygame.K_v and (pygame.key.get_mods() & pygame.KMOD_CTRL):
                    pasted = self._paste_from_clipboard()
                    if pasted:
                        self.chat_input += pasted
                        toast_info("Texto colado!")
                else:
                    if len(self.chat_input) < 60 and event.unicode.isprintable():
                        self.chat_input += event.unicode
                return

            if event.key == pygame.K_c:
                self.chat_active = True
                return
            if event.key == pygame.K_t:
                self._request_trade()
                return

        # ===== MOUSE =====
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mouse_pos = event.pos

            if self.back_btn.collidepoint(mouse_pos):
                sound_manager.play_effect(SoundEffect.CLICK)
                self.network.send_to_all(create_message("DISCONNECT"))
                self._return_to_menu()
                return

            if self.trade_btn.collidepoint(mouse_pos) and self.opponent_name:
                self._request_trade()
                return

            if self.send_btn.collidepoint(mouse_pos):
                self._send_chat()
                return

            if self.chat_input_rect.collidepoint(mouse_pos):
                self.chat_active = True
                return

            if self.pending_trade_from:
                if self.accept_btn.collidepoint(mouse_pos):
                    self._handle_trade_response(True)
                    return
                if self.decline_btn.collidepoint(mouse_pos):
                    self._handle_trade_response(False)
                    return

            self.chat_active = False

    # ======================================================================
    # UPDATE
    # ======================================================================

    def fixed_update(self, dt):
        self._animation_timer += dt

        try:
            while not self.network.incoming_queue.empty():
                item = self.network.incoming_queue.get_nowait()
                if self.is_host:
                    msg, conn = item
                    self._on_network_message(msg, conn)
                else:
                    msg, _ = item
                    self._on_network_message(msg, None)
        except:
            pass

    # ======================================================================
    # RENDERIZAÇÃO
    # ======================================================================

    def render(self, screen):
        screen.fill((18, 20, 35))

        vw = self.screen_manager.viewport_width
        vh = self.screen_manager.viewport_height
        vx = self.screen_manager.viewport_x
        vy = self.screen_manager.viewport_y

        self._update_button_positions()

        # ===== TÍTULO =====
        title = self.font_title.render("LOBBY", True, (255, 215, 0))
        title_rect = title.get_rect(center=(vx + vw // 2, vy + 40))
        screen.blit(title, title_rect)

        pygame.draw.line(screen, (60, 60, 80),
                         (vx + vw // 4, vy + 65),
                         (vx + vw * 3 // 4, vy + 65), 2)

        # ===== LISTA DE JOGADORES =====
        list_rect = pygame.Rect(vx + 15, vy + 90, 240, 250)
        pygame.draw.rect(screen, (25, 27, 45), list_rect, border_radius=8)
        pygame.draw.rect(screen, (60, 60, 80), list_rect, 1, border_radius=8)

        list_title = self.font.render("Jogadores", True, (200, 200, 200))
        screen.blit(list_title, (vx + 25, vy + 100))

        if self.players:
            y_pos = vy + 135
            for name in self.players:
                is_me = name == self.my_name
                color = (100, 255, 100) if is_me else (255, 255, 255)
                text = f"{name} (voce)" if is_me else name
                txt = self.font.render(text, True, color)
                screen.blit(txt, (vx + 25, y_pos))
                y_pos += 28
        else:
            txt = self.font_small.render("Aguardando jogadores...", True, (120, 120, 150))
            screen.blit(txt, (vx + 25, vy + 135))

        # ===== BOTÃO SOLICITAR TROCA =====
        if self.opponent_name:
            btn_text = f"Solicitar Troca com {self.opponent_name}"
            color = (50, 100, 50)
            hover_color = (80, 160, 80)
        else:
            btn_text = "Aguardando oponente..."
            color = (50, 50, 60)
            hover_color = (50, 50, 60)

        self.trade_btn = pygame.Rect(vx + 25, vy + 200, 220, 35)
        self._draw_button(screen, self.trade_btn, btn_text, color, hover_color)

        # ===== PAINEL DO CHAT =====
        chat_rect = pygame.Rect(vx + 280, vy + 90, vw - 310, vh - 150)
        pygame.draw.rect(screen, (25, 27, 45), chat_rect, border_radius=8)
        pygame.draw.rect(screen, (60, 60, 80), chat_rect, 1, border_radius=8)

        chat_title = self.font_small.render("Chat", True, (200, 200, 200))
        screen.blit(chat_title, (chat_rect.x + 12, chat_rect.y + 8))

        pygame.draw.line(screen, (50, 50, 70),
                         (chat_rect.x + 10, chat_rect.y + 32),
                         (chat_rect.right - 10, chat_rect.y + 32), 1)

        y_offset = chat_rect.y + 40
        for msg in self.chat_messages[-14:]:
            color = (255, 215, 0) if msg.startswith(self.my_name + ":") else (220, 220, 220)
            txt = self.font_chat.render(msg, True, color)
            if txt.get_width() > chat_rect.width - 24:
                msg_short = msg[:35] + "..."
                txt = self.font_chat.render(msg_short, True, color)
            screen.blit(txt, (chat_rect.x + 12, y_offset))
            y_offset += 22

        # ===== CAMPO DE INPUT DO CHAT =====
        border_color = (255, 215, 0) if self.chat_active else (60, 60, 80)
        pygame.draw.rect(screen, (20, 22, 40), self.chat_input_rect, border_radius=6)
        pygame.draw.rect(screen, border_color, self.chat_input_rect, 2, border_radius=6)

        if self.chat_active:
            display_text = self.chat_input if self.chat_input else "Digite... (Ctrl+V para colar)"
            color = (255, 255, 255) if self.chat_input else (120, 120, 150)
        else:
            display_text = "Pressione C para chat..."
            color = (80, 80, 110)

        txt = self.font_small.render(display_text, True, color)
        screen.blit(txt, (self.chat_input_rect.x + 10, self.chat_input_rect.y + 7))

        # ===== BOTÕES =====
        self._draw_button(screen, self.send_btn, "Enviar", (50, 100, 50), (80, 160, 80))
        self._draw_button(screen, self.back_btn, "Voltar", (80, 40, 40), (140, 60, 60))

        # ===== SOLICITAÇÃO DE TROCA PENDENTE =====
        if self.pending_trade_from:
            self._render_trade_request(screen)

        # ===== INSTRUÇÕES =====
        instr = self.font_small.render("C = chat | T = solicitar troca | Ctrl+V = colar", True, (80, 80, 110))
        screen.blit(instr, (vx + 25, vy + vh - 25))

    def _draw_button(self, screen, rect, text, color, hover_color):
        mouse = pygame.mouse.get_pos()
        hover = rect.collidepoint(mouse)
        pygame.draw.rect(screen, hover_color if hover else color, rect, border_radius=8)
        pygame.draw.rect(screen, (200, 200, 200), rect, 1, border_radius=8)

        font_size = 20 if len(text) < 20 else 16
        font = pygame.font.Font(None, font_size)
        txt = font.render(text, True, (255, 255, 255))
        txt_rect = txt.get_rect(center=rect.center)
        screen.blit(txt, txt_rect)

    def _render_trade_request(self, screen):
        vw = self.screen_manager.viewport_width
        vh = self.screen_manager.viewport_height
        vx = self.screen_manager.viewport_x
        vy = self.screen_manager.viewport_y

        overlay = pygame.Surface((vw, vh))
        overlay.set_alpha(180)
        overlay.fill((0, 0, 0))
        screen.blit(overlay, (vx, vy))

        dialog_rect = pygame.Rect(vx + vw // 2 - 220, vy + vh // 2 - 80, 440, 160)
        pygame.draw.rect(screen, (35, 30, 50), dialog_rect, border_radius=12)
        pygame.draw.rect(screen, (255, 215, 0), dialog_rect, 2, border_radius=12)

        txt = self.font.render(f"{self.pending_trade_from} quer trocar com voce!", True, (255, 255, 255))
        screen.blit(txt, (dialog_rect.x + 20, dialog_rect.y + 25))

        txt2 = self.font_small.render("Selecione uma opcao:", True, (180, 180, 200))
        screen.blit(txt2, (dialog_rect.x + 20, dialog_rect.y + 60))

        self.accept_btn.center = (dialog_rect.centerx - 110, dialog_rect.bottom - 45)
        self.decline_btn.center = (dialog_rect.centerx + 110, dialog_rect.bottom - 45)

        self._draw_button(screen, self.accept_btn, "Aceitar", (50, 150, 50), (80, 200, 80))
        self._draw_button(screen, self.decline_btn, "Recusar", (150, 50, 50), (200, 80, 80))

    # ======================================================================
    # CICLO DE VIDA
    # ======================================================================

    def on_enter(self):
        pass

    def on_exit(self):
        pass