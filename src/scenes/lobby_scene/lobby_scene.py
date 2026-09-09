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
        self.players = {}  # id_conexão -> nome
        self.my_conn_id = None  # será definido quando receber a lista

        # Chat
        self.chat_messages = []
        self.chat_input = ""
        self.chat_active = False
        self.chat_scroll = 0

        # Solicitação de troca pendente
        self.pending_trade_request = None  # nome do solicitante
        self.trade_request_from = None  # conn_id

        # UI
        self.back_btn = pygame.Rect(0, 0, 150, 40)
        self.chat_input_rect = pygame.Rect(0, 0, 400, 30)
        self.send_btn = pygame.Rect(0, 0, 80, 30)
        self._center_ui()

        # Fonte
        self.font = pygame.font.Font(None, 28)
        self.font_small = pygame.font.Font(None, 22)

    def _center_ui(self):
        vw = self.screen_manager.viewport_width
        vh = self.screen_manager.viewport_height
        vx = self.screen_manager.viewport_x
        vy = self.screen_manager.viewport_y

        self.back_btn.topleft = (vx + 20, vy + 20)
        self.chat_input_rect.topleft = (vx + 20, vy + vh - 50)
        self.send_btn.topleft = (vx + 440, vy + vh - 50)

    def _on_network_message(self, msg, conn=None):
        msg_type = msg.get("type")
        payload = msg.get("payload", {})

        if msg_type == "PLAYER_INFO":
            # Recebe nome de um jogador (se for host, já atualiza lista)
            name = payload.get("name", "Desconhecido")
            if self.is_host:
                # O host já atualizou no manager, mas podemos sincronizar
                pass
            else:
                # Cliente recebe info do host
                self.network.opponent_name = name
                toast_info(f"{name} entrou na sala!")
                # Envia seu próprio nome de volta
                self.network.send_to_all(create_message("PLAYER_INFO", {"name": self.network.my_name}))
        elif msg_type == "PLAYER_LIST":
            # Atualiza lista de jogadores
            players_data = payload.get("players", {})
            self.players = players_data
            # Identifica qual é o próprio jogador (pelo nome)
            for conn_id, name in self.players.items():
                if name == self.network.my_name:
                    self.my_conn_id = conn_id
                    break
            toast_info(f"Jogadores na sala: {len(self.players)}")
        elif msg_type == "CHAT_MESSAGE":
            sender = payload.get("sender", "Desconhecido")
            text = payload.get("text", "")
            self.chat_messages.append(f"{sender}: {text}")
            if len(self.chat_messages) > 50:
                self.chat_messages.pop(0)
        elif msg_type == "TRADE_REQUEST":
            # Alguém solicitou troca
            from_name = payload.get("from", "Desconhecido")
            from_conn = payload.get("from_conn")
            self.pending_trade_request = from_name
            self.trade_request_from = from_conn
            toast_info(f"{from_name} quer trocar com você! Use o botão para aceitar.")
        elif msg_type == "TRADE_RESPONSE":
            accepted = payload.get("accepted", False)
            if accepted:
                toast_info("Troca aceita! Abrindo tela de troca...")
                self._open_trade_scene()
            else:
                toast_info("O outro jogador recusou a troca.")
                self.pending_trade_request = None
                self.trade_request_from = None
        elif msg_type == "DISCONNECT":
            toast_warning("Um jogador desconectou.")
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
        self.network.send_to_all(create_message("CHAT_MESSAGE", {"sender": self.network.my_name, "text": text}))
        self.chat_messages.append(f"{self.network.my_name}: {text}")

    def _request_trade(self, target_conn_id):
        # Envia solicitação para o alvo
        target_name = self.players.get(target_conn_id)
        if not target_name:
            toast_warning("Jogador não encontrado.")
            return
        self.network.send_to_all(create_message("TRADE_REQUEST", {"from": self.network.my_name, "from_conn": self.my_conn_id, "target": target_conn_id}))
        toast_info(f"Solicitação de troca enviada para {target_name}.")

    def handle_event(self, event):
        if event.type == pygame.VIDEORESIZE:
            self._center_ui()
            return

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self._return_to_menu()
            if self.chat_active:
                if event.key == pygame.K_RETURN:
                    self._send_chat()
                elif event.key == pygame.K_BACKSPACE:
                    self.chat_input = self.chat_input[:-1]
                else:
                    if len(self.chat_input) < 60 and event.unicode.isprintable():
                        self.chat_input += event.unicode
                return
            else:
                # Teclas de atalho
                if event.key == pygame.K_c:  # Foco no chat
                    self.chat_active = True
                elif event.key == pygame.K_t:  # Solicitar troca (selecionar alvo)
                    # Escolhe o primeiro jogador que não seja ele mesmo
                    for conn_id, name in self.players.items():
                        if conn_id != self.my_conn_id:
                            self._request_trade(conn_id)
                            break

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.back_btn.collidepoint(event.pos):
                sound_manager.play_effect(SoundEffect.CLICK)
                self.network.send_to_all(create_message("DISCONNECT"))
                self._return_to_menu()
                return

            if self.send_btn.collidepoint(event.pos):
                self._send_chat()
                return

            if self.chat_input_rect.collidepoint(event.pos):
                self.chat_active = True
                return

            # Clique em um jogador da lista (para solicitar troca)
            list_start_x = self.screen_manager.viewport_x + 20
            list_start_y = self.screen_manager.viewport_y + 120
            item_height = 30
            for i, (conn_id, name) in enumerate(self.players.items()):
                if conn_id == self.my_conn_id:
                    continue
                rect = pygame.Rect(list_start_x, list_start_y + i * item_height, 200, item_height)
                if rect.collidepoint(event.pos):
                    self._request_trade(conn_id)
                    break

            # Se clicar fora, desativa chat
            self.chat_active = False

    def fixed_update(self, dt):
        # Processa mensagens da fila
        while not self.network.incoming_queue.empty():
            item = self.network.incoming_queue.get()
            if self.is_host:
                msg, conn = item
                self._on_network_message(msg, conn)
            else:
                msg, _ = item
                self._on_network_message(msg, None)

    def render(self, screen):
        screen.fill((25, 25, 40))

        vw = self.screen_manager.viewport_width
        vh = self.screen_manager.viewport_height
        vx = self.screen_manager.viewport_x
        vy = self.screen_manager.viewport_y

        # Título
        title = self.font.render("LOBBY", True, (255, 215, 0))
        screen.blit(title, (vx + vw//2 - title.get_width()//2, vy + 30))

        # Lista de jogadores
        list_title = self.font_small.render("Jogadores:", True, (200, 200, 200))
        screen.blit(list_title, (vx + 20, vy + 90))
        list_start_y = vy + 120
        for i, (conn_id, name) in enumerate(self.players.items()):
            color = (100, 255, 100) if conn_id == self.my_conn_id else (255, 255, 255)
            text = f"{name} {'(você)' if conn_id == self.my_conn_id else ''}"
            txt = self.font_small.render(text, True, color)
            screen.blit(txt, (vx + 20, list_start_y + i * 30))

            if conn_id != self.my_conn_id:
                # Botão "Trocar" pequeno ao lado
                btn_rect = pygame.Rect(vx + 180, list_start_y + i * 30, 60, 25)
                self._draw_button(screen, btn_rect, "Trocar", (50, 100, 50), (100, 150, 100))

        # Área de chat
        chat_rect = pygame.Rect(vx + 250, vy + 90, vw - 300, vh - 200)
        pygame.draw.rect(screen, (40, 40, 60), chat_rect, border_radius=5)
        pygame.draw.rect(screen, (100, 100, 120), chat_rect, 1, border_radius=5)

        # Mensagens do chat (mostra últimas 10)
        chat_font = pygame.font.Font(None, 20)
        y_offset = chat_rect.y + 10
        for msg in self.chat_messages[-10:]:
            txt = chat_font.render(msg, True, (220, 220, 220))
            screen.blit(txt, (chat_rect.x + 10, y_offset))
            y_offset += 25

        # Campo de input do chat
        pygame.draw.rect(screen, (60, 60, 80), self.chat_input_rect, border_radius=5)
        pygame.draw.rect(screen, (200, 200, 200), self.chat_input_rect, 2, border_radius=5)
        input_display = self.chat_input if self.chat_input else "Digite sua mensagem..."
        color = (255, 255, 255) if self.chat_input else (150, 150, 150)
        txt = self.font_small.render(input_display, True, color)
        screen.blit(txt, (self.chat_input_rect.x + 10, self.chat_input_rect.y + 5))

        # Botão enviar
        self._draw_button(screen, self.send_btn, "Enviar", (50, 100, 50), (100, 150, 100))

        # Botão voltar
        self._draw_button(screen, self.back_btn, "VOLTAR", (100, 50, 50), (150, 80, 80))

        # Indicação de solicitação pendente
        if self.pending_trade_request:
            req_text = f"{self.pending_trade_request} quer trocar com você!"
            req_color = (255, 200, 100)
            txt = self.font_small.render(req_text, True, req_color)
            screen.blit(txt, (vx + vw//2 - txt.get_width()//2, vy + vh - 100))
            # Botões Aceitar / Recusar
            accept_btn = pygame.Rect(vx + vw//2 - 120, vy + vh - 70, 100, 30)
            decline_btn = pygame.Rect(vx + vw//2 + 20, vy + vh - 70, 100, 30)
            self._draw_button(screen, accept_btn, "Aceitar", (50, 150, 50), (100, 200, 100))
            self._draw_button(screen, decline_btn, "Recusar", (150, 50, 50), (200, 80, 80))
            # Armazenar para eventos
            self._accept_btn_rect = accept_btn
            self._decline_btn_rect = decline_btn
        else:
            self._accept_btn_rect = None
            self._decline_btn_rect = None

        # Instruções
        instr = self.font_small.render("Clique em um jogador para solicitar troca. Pressione 'C' para chat.", True, (180, 180, 180))
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

    def _handle_trade_response(self, accepted):
        if self.trade_request_from:
            self.network.send_to_all(create_message("TRADE_RESPONSE", {"accepted": accepted}))
            if accepted:
                self._open_trade_scene()
            else:
                self.pending_trade_request = None
                self.trade_request_from = None

    # Sobrescrever handle_event para capturar clique nos botões Aceitar/Recusar
    def handle_event(self, event):
        # Primeiro, processa os botões de resposta
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._accept_btn_rect and self._accept_btn_rect.collidepoint(event.pos):
                self._handle_trade_response(True)
                return
            if self._decline_btn_rect and self._decline_btn_rect.collidepoint(event.pos):
                self._handle_trade_response(False)
                return

        # Depois chama o handle original
        super().handle_event(event)