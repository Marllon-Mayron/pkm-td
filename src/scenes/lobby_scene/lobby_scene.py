# src/scenes/lobby_scene/lobby_scene.py

import pygame
from src.scenes.base_scene import BaseScene
from src.ui.toast_renderer import toast_info, toast_warning
from src.managers.sounds.sound_manager import sound_manager, SoundEffect
from src.network.protocol import create_message


class LobbyScene(BaseScene):
    def __init__(self, game, is_host, network):
        super().__init__(game)
        self.network = network
        self.is_host = is_host
        self.network.current_scene_callback = self._on_network_message

        # Dados dos jogadores
        self.players = []  # lista de nomes
        self.my_name = network.my_name
        self.opponent_name = None

        # Chat
        self.chat_messages = []
        self.chat_input = ""
        self.chat_active = False

        # Solicitação de troca pendente
        self.pending_trade_from = None

        # UI
        self.back_btn = pygame.Rect(0, 0, 150, 40)
        self.chat_input_rect = pygame.Rect(0, 0, 400, 30)
        self.send_btn = pygame.Rect(0, 0, 80, 30)

        # Botões de resposta a solicitação
        self.accept_trade_btn = pygame.Rect(0, 0, 100, 30)
        self.decline_trade_btn = pygame.Rect(0, 0, 100, 30)

        self._center_ui()

        # Envia o nome do jogador ao entrar
        self.network.send_to_all(create_message("PLAYER_INFO", {"name": self.my_name}))
        print(f"[LOBBY] {self.my_name} entrou no lobby (host={self.is_host})")

        # Fontes
        self.font_title = pygame.font.Font(None, 48)
        self.font = pygame.font.Font(None, 28)
        self.font_small = pygame.font.Font(None, 22)
        self.font_chat = pygame.font.Font(None, 20)

    def _center_ui(self):
        vw = self.screen_manager.viewport_width
        vh = self.screen_manager.viewport_height
        vx = self.screen_manager.viewport_x
        vy = self.screen_manager.viewport_y

        self.back_btn.topleft = (vx + 20, vy + 20)
        self.chat_input_rect.topleft = (vx + 250, vy + vh - 50)
        self.send_btn.topleft = (vx + 670, vy + vh - 50)

        # Botões de resposta (centralizados)
        center_x = vx + vw // 2
        center_y = vy + vh // 2 + 50
        self.accept_trade_btn.center = (center_x - 110, center_y)
        self.decline_trade_btn.center = (center_x + 110, center_y)

    def _on_network_message(self, msg, conn=None):
        msg_type = msg.get("type")
        payload = msg.get("payload", {})

        print(f"[LOBBY] Mensagem recebida: {msg_type}")

        if msg_type == "PLAYER_INFO":
            name = payload.get("name", "Desconhecido")
            if name not in self.players and name != self.my_name:
                self.players.append(name)
                self.opponent_name = name
                toast_info(f"{name} entrou na sala!")
                print(f"[LOBBY] Jogadores: {self.players}")
                # Se for host, envia lista atualizada para todos
                if self.is_host:
                    self.network.send_to_all(create_message("PLAYER_LIST", {"players": self.players}))
            elif name == self.my_name and not self.is_host:
                # Cliente recebe o próprio nome de volta? Não adiciona duplicado
                pass

        elif msg_type == "PLAYER_LIST":
            players = payload.get("players", [])
            self.players = players
            print(f"[LOBBY] Lista de jogadores atualizada: {self.players}")
            toast_info(f"Jogadores na sala: {len(self.players)}")

        elif msg_type == "CHAT_MESSAGE":
            sender = payload.get("sender", "Desconhecido")
            text = payload.get("text", "")
            self.chat_messages.append(f"{sender}: {text}")
            if len(self.chat_messages) > 50:
                self.chat_messages.pop(0)

        elif msg_type == "TRADE_REQUEST":
            from_name = payload.get("from", "Desconhecido")
            self.pending_trade_from = from_name
            toast_info(f"{from_name} quer trocar com você!")

        elif msg_type == "TRADE_RESPONSE":
            accepted = payload.get("accepted", False)
            if accepted:
                toast_info("Troca aceita! Abrindo tela de troca...")
                self._open_trade_scene()
            else:
                toast_info("O outro jogador recusou a troca.")
                self.pending_trade_from = None

        elif msg_type == "DISCONNECT":
            toast_warning("O outro jogador desconectou.")
            self._return_to_menu()

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
        toast_info(f"Solicitação enviada para {self.opponent_name}.")

    def _handle_trade_response(self, accepted):
        self.network.send_to_all(create_message("TRADE_RESPONSE", {"accepted": accepted}))
        if accepted:
            self._open_trade_scene()
        else:
            self.pending_trade_from = None

    def handle_event(self, event):
        if event.type == pygame.VIDEORESIZE:
            self._center_ui()
            return

        # ===== EVENTOS DE TECLADO =====
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self._return_to_menu()
                return

            # Se o chat está ativo, captura todas as teclas
            if self.chat_active:
                if event.key == pygame.K_RETURN:
                    self._send_chat()
                elif event.key == pygame.K_BACKSPACE:
                    self.chat_input = self.chat_input[:-1]
                else:
                    if len(self.chat_input) < 60 and event.unicode.isprintable():
                        self.chat_input += event.unicode
                return  # Não processa mais eventos enquanto digitando

            # Teclas de atalho (chat não ativo)
            if event.key == pygame.K_c:
                self.chat_active = True
                return
            if event.key == pygame.K_t:
                self._request_trade()
                return

        # ===== EVENTOS DE MOUSE =====
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mouse_pos = event.pos

            # Botão voltar
            if self.back_btn.collidepoint(mouse_pos):
                sound_manager.play_effect(SoundEffect.CLICK)
                self.network.send_to_all(create_message("DISCONNECT"))
                self._return_to_menu()
                return

            # Botão enviar chat
            if self.send_btn.collidepoint(mouse_pos):
                self._send_chat()
                return

            # Campo de chat
            if self.chat_input_rect.collidepoint(mouse_pos):
                self.chat_active = True
                return

            # Botão "Solicitar Troca" (se houver oponente)
            trade_btn = pygame.Rect(
                self.screen_manager.viewport_x + 20,
                self.screen_manager.viewport_y + 150,
                150, 30
            )
            if trade_btn.collidepoint(mouse_pos) and self.opponent_name:
                self._request_trade()
                return

            # Botões de resposta (Aceitar/Recusar)
            if self.pending_trade_from:
                if self.accept_trade_btn.collidepoint(mouse_pos):
                    self._handle_trade_response(True)
                    return
                if self.decline_trade_btn.collidepoint(mouse_pos):
                    self._handle_trade_response(False)
                    return

            # Clique fora = desativa chat
            self.chat_active = False

    def fixed_update(self, dt):
        # Processa mensagens da fila
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

    def render(self, screen):
        screen.fill((25, 25, 40))

        vw = self.screen_manager.viewport_width
        vh = self.screen_manager.viewport_height
        vx = self.screen_manager.viewport_x
        vy = self.screen_manager.viewport_y

        # ===== TÍTULO =====
        title = self.font_title.render("LOBBY", True, (255, 215, 0))
        screen.blit(title, (vx + vw//2 - title.get_width()//2, vy + 30))

        # ===== LISTA DE JOGADORES =====
        list_title = self.font.render("Jogadores Conectados:", True, (200, 200, 200))
        screen.blit(list_title, (vx + 20, vy + 90))

        y_pos = vy + 130
        if self.players:
            for i, name in enumerate(self.players):
                is_me = name == self.my_name
                color = (100, 255, 100) if is_me else (255, 255, 255)
                text = f"{name} {'(você)' if is_me else ''}"
                txt = self.font.render(text, True, color)
                screen.blit(txt, (vx + 20, y_pos + i * 35))
        else:
            txt = self.font_small.render("Aguardando jogadores...", True, (150, 150, 150))
            screen.blit(txt, (vx + 20, y_pos))

        # ===== BOTÃO SOLICITAR TROCA =====
        trade_btn = pygame.Rect(vx + 20, vy + 150 + (len(self.players) * 35) + 20, 200, 30)
        if self.opponent_name:
            self._draw_button(screen, trade_btn, "SOLICITAR TROCA (T)", (50, 100, 50), (100, 150, 100))
        else:
            self._draw_button(screen, trade_btn, "AGUARDANDO OPONENTE", (60, 60, 60), (60, 60, 60))

        # ===== CHAT =====
        # Área do chat (caixa)
        chat_rect = pygame.Rect(vx + 250, vy + 90, vw - 300, vh - 200)
        pygame.draw.rect(screen, (40, 40, 60), chat_rect, border_radius=5)
        pygame.draw.rect(screen, (100, 100, 120), chat_rect, 1, border_radius=5)

        # Mensagens do chat
        y_offset = chat_rect.y + 10
        for msg in self.chat_messages[-12:]:
            txt = self.font_chat.render(msg, True, (220, 220, 220))
            screen.blit(txt, (chat_rect.x + 10, y_offset))
            y_offset += 25

        # Campo de input do chat
        pygame.draw.rect(screen, (60, 60, 80), self.chat_input_rect, border_radius=5)
        border_color = (200, 200, 50) if self.chat_active else (200, 200, 200)
        pygame.draw.rect(screen, border_color, self.chat_input_rect, 2, border_radius=5)

        input_display = self.chat_input if self.chat_input else "Pressione 'C' para chat..."
        color = (255, 255, 255) if self.chat_input else (150, 150, 150)
        txt = self.font_small.render(input_display, True, color)
        screen.blit(txt, (self.chat_input_rect.x + 10, self.chat_input_rect.y + 5))

        # Botão enviar chat
        self._draw_button(screen, self.send_btn, "Enviar", (50, 100, 50), (100, 150, 100))

        # ===== SOLICITAÇÃO DE TROCA PENDENTE =====
        if self.pending_trade_from:
            # Overlay semi-transparente
            overlay = pygame.Surface((vw, vh), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 180))
            screen.blit(overlay, (vx, vy))

            # Caixa de diálogo
            dialog_rect = pygame.Rect(vx + vw//2 - 200, vy + vh//2 - 80, 400, 160)
            pygame.draw.rect(screen, (50, 50, 70), dialog_rect, border_radius=15)
            pygame.draw.rect(screen, (255, 215, 0), dialog_rect, 2, border_radius=15)

            # Texto
            txt = self.font.render(f"{self.pending_trade_from} quer trocar com você!", True, (255, 255, 255))
            screen.blit(txt, (dialog_rect.x + 20, dialog_rect.y + 20))

            # Botões Aceitar / Recusar
            self._draw_button(screen, self.accept_trade_btn, "ACEITAR", (50, 150, 50), (100, 200, 100))
            self._draw_button(screen, self.decline_trade_btn, "RECUSAR", (150, 50, 50), (200, 80, 80))

        # ===== BOTÃO VOLTAR =====
        self._draw_button(screen, self.back_btn, "VOLTAR", (100, 50, 50), (150, 80, 80))

        # ===== INSTRUÇÕES =====
        instr = self.font_small.render("'C' para chat | 'T' para solicitar troca", True, (180, 180, 180))
        screen.blit(instr, (vx + 20, vy + vh - 30))

    def _draw_button(self, screen, rect, text, color, hover_color):
        mouse = pygame.mouse.get_pos()
        hover = rect.collidepoint(mouse)
        pygame.draw.rect(screen, hover_color if hover else color, rect, border_radius=8)
        pygame.draw.rect(screen, (255, 255, 255), rect, 1, border_radius=8)
        font = pygame.font.Font(None, 22)
        txt = font.render(text, True, (255, 255, 255))
        txt_rect = txt.get_rect(center=rect.center)
        screen.blit(txt, txt_rect)