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

        # Lista de jogadores (nome, is_ready, etc)
        self.players = []  # lista de dicts: {"name": str, "is_ready": bool, "conn": conn}
        self.my_name = self.network.my_name
        self.selected_player_index = -1

        # Estado de solicitação de troca
        self.trade_request_from = None  # nome do jogador que solicitou
        self.trade_request_timer = 0

        # Botões
        self.back_btn = pygame.Rect(0, 0, 150, 40)
        self.trade_btn = pygame.Rect(0, 0, 200, 50)
        self.accept_btn = pygame.Rect(0, 0, 120, 40)
        self.decline_btn = pygame.Rect(0, 0, 120, 40)

        self._center_ui()

    def _center_ui(self):
        vw = self.screen_manager.viewport_width
        vh = self.screen_manager.viewport_height
        vx = self.screen_manager.viewport_x
        vy = self.screen_manager.viewport_y
        self.back_btn.topleft = (vx + 20, vy + 20)
        self.trade_btn.center = (vx + vw//2, vy + vh - 80)
        self.accept_btn.center = (vx + vw//2 - 80, vy + vh - 80)
        self.decline_btn.center = (vx + vw//2 + 80, vy + vh - 80)

    def _on_network_message(self, msg, conn=None):
        msg_type = msg.get("type")
        payload = msg.get("payload", {})

        if msg_type == "PLAYER_INFO":
            name = payload.get("name", "Oponente")
            # Adiciona jogador à lista se não existir
            if not any(p["name"] == name for p in self.players):
                self.players.append({"name": name, "is_ready": False, "conn": conn})
                toast_info(f"{name} entrou na sala!")
            # Se for host, envia a lista atualizada para todos
            if self.is_host:
                self._broadcast_player_list()

        elif msg_type == "PLAYER_LIST":
            # Atualiza a lista de jogadores (recebida do host)
            self.players = payload.get("players", [])
            # Remove o próprio nome da lista (já está separado)
            self.players = [p for p in self.players if p["name"] != self.my_name]

        elif msg_type == "TRADE_REQUEST":
            from_name = payload.get("from")
            if from_name and from_name != self.my_name:
                self.trade_request_from = from_name
                self.trade_request_timer = 10.0  # timeout de 10 segundos
                toast_info(f"{from_name} quer trocar Pokémon! Aceita?")

        elif msg_type == "TRADE_RESPONSE":
            accepted = payload.get("accepted", False)
            from_name = payload.get("from")
            if accepted:
                toast_info(f"{from_name} aceitou a troca! Abrindo tela...")
                # Abre a tela de troca para ambos
                from src.scenes.trade_scene.trade_scene import TradeScene
                self.game.current_scene = TradeScene(self.game, is_host=self.is_host, network=self.network)
            else:
                toast_info(f"{from_name} recusou a troca.")

        elif msg_type == "DISCONNECT":
            # Remove jogador da lista
            for p in self.players[:]:
                if p["conn"] == conn:
                    self.players.remove(p)
                    toast_info(f"{p['name']} desconectou.")
                    break
            if self.is_host:
                self._broadcast_player_list()

    def _broadcast_player_list(self):
        # Envia a lista de jogadores (exceto o próprio host) para todos
        player_list = [{"name": p["name"], "is_ready": p["is_ready"]} for p in self.players]
        self.network.send_to_all(create_message("PLAYER_LIST", {"players": player_list}))

    def handle_event(self, event):
        if event.type == pygame.VIDEORESIZE:
            self._center_ui()
            return

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_UP:
                self.selected_player_index = max(0, self.selected_player_index - 1)
            elif event.key == pygame.K_DOWN:
                self.selected_player_index = min(len(self.players) - 1, self.selected_player_index + 1)
            elif event.key == pygame.K_RETURN:
                self._request_trade()
            elif event.key == pygame.K_ESCAPE:
                self._return_to_menu()

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mouse_pos = event.pos

            if self.back_btn.collidepoint(mouse_pos):
                sound_manager.play_effect(SoundEffect.CLICK)
                self.network.send_to_all(create_message("DISCONNECT"))
                self._return_to_menu()
                return

            # Botão de troca
            if self.trade_btn.collidepoint(mouse_pos):
                self._request_trade()
                return

            # Botões de aceitar/recusar solicitação
            if self.trade_request_from:
                if self.accept_btn.collidepoint(mouse_pos):
                    self._respond_to_trade(True)
                    return
                if self.decline_btn.collidepoint(mouse_pos):
                    self._respond_to_trade(False)
                    return

            # Selecionar jogador na lista (clique)
            for i, player in enumerate(self.players):
                rect = self._get_player_rect(i)
                if rect.collidepoint(mouse_pos):
                    self.selected_player_index = i
                    break

    def _request_trade(self):
        if self.selected_player_index < 0 or self.selected_player_index >= len(self.players):
            toast_warning("Selecione um jogador primeiro!")
            return
        target = self.players[self.selected_player_index]
        # Envia solicitação de troca para o alvo
        self.network.send_to_all(create_message("TRADE_REQUEST", {"from": self.my_name, "target": target["name"]}))
        toast_info(f"Solicitação de troca enviada para {target['name']}")

    def _respond_to_trade(self, accepted):
        if not self.trade_request_from:
            return
        self.network.send_to_all(create_message("TRADE_RESPONSE", {
            "from": self.my_name,
            "accepted": accepted,
            "target": self.trade_request_from
        }))
        if accepted:
            # Abre a tela de troca
            from src.scenes.trade_scene.trade_scene import TradeScene
            self.game.current_scene = TradeScene(self.game, is_host=self.is_host, network=self.network)
        else:
            toast_info("Você recusou a troca.")
        self.trade_request_from = None

    def _return_to_menu(self):
        self.network.stop()
        self.game.current_scene = self.game.menu_scene

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

        # Timeout da solicitação de troca
        if self.trade_request_timer > 0:
            self.trade_request_timer -= dt
            if self.trade_request_timer <= 0:
                self.trade_request_from = None

    def _get_player_rect(self, index):
        vw = self.screen_manager.viewport_width
        vh = self.screen_manager.viewport_height
        vx = self.screen_manager.viewport_x
        vy = self.screen_manager.viewport_y

        width = 300
        height = 40
        start_x = vx + (vw - width) // 2
        start_y = vy + 150 + index * 50
        return pygame.Rect(start_x, start_y, width, height)

    def render(self, screen):
        screen.fill((20, 20, 35))

        vw = self.screen_manager.viewport_width
        vh = self.screen_manager.viewport_height
        vx = self.screen_manager.viewport_x
        vy = self.screen_manager.viewport_y

        # Título
        font = pygame.font.Font(None, 48)
        title = font.render("LOBBY", True, (255, 215, 0))
        screen.blit(title, (vx + vw//2 - title.get_width()//2, vy + 50))

        # Lista de jogadores
        font_small = pygame.font.Font(None, 28)
        # Mostra o próprio jogador
        self._draw_player_entry(screen, self.my_name, is_self=True)

        # Mostra os outros jogadores
        for i, player in enumerate(self.players):
            rect = self._get_player_rect(i)
            color = (60, 60, 80) if i != self.selected_player_index else (80, 80, 120)
            pygame.draw.rect(screen, color, rect, border_radius=8)
            pygame.draw.rect(screen, (200, 200, 200), rect, 2, border_radius=8)

            status = "🟢" if player.get("is_ready", False) else "⚪"
            name_text = f"{status} {player['name']}"
            txt = font_small.render(name_text, True, (255, 255, 255))
            screen.blit(txt, (rect.x + 15, rect.y + 8))

            # Ícone de seleção
            if i == self.selected_player_index:
                sel = font_small.render("▶", True, (255, 215, 0))
                screen.blit(sel, (rect.x - 25, rect.y + 8))

        # Instruções
        font_tiny = pygame.font.Font(None, 18)
        instr = "Use SETAS ↑↓ para selecionar, ENTER para solicitar troca."
        screen.blit(font_tiny.render(instr, True, (180, 180, 180)), (vx + vw//2 - 200, vy + vh - 120))

        # Botões
        self._draw_button(screen, self.back_btn, "VOLTAR", (100, 50, 50), (150, 80, 80))
        self._draw_button(screen, self.trade_btn, "SOLICITAR TROCA", (50, 80, 150), (100, 130, 200))

        # Solicitação de troca recebida
        if self.trade_request_from:
            # Mostra overlay de solicitação
            overlay = pygame.Surface((vw, vh), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 180))
            screen.blit(overlay, (vx, vy))

            # Caixa de diálogo
            box_w, box_h = 400, 150
            box_x = vx + (vw - box_w) // 2
            box_y = vy + (vh - box_h) // 2
            box_rect = pygame.Rect(box_x, box_y, box_w, box_h)
            pygame.draw.rect(screen, (40, 40, 60), box_rect, border_radius=15)
            pygame.draw.rect(screen, (255, 215, 0), box_rect, 3, border_radius=15)

            msg_font = pygame.font.Font(None, 30)
            msg_text = msg_font.render(f"{self.trade_request_from} quer trocar!", True, (255, 255, 255))
            screen.blit(msg_text, (box_x + (box_w - msg_text.get_width())//2, box_y + 30))

            # Botões Aceitar/Recusar
            self.accept_btn.center = (box_x + box_w//2 - 80, box_y + box_h - 40)
            self.decline_btn.center = (box_x + box_w//2 + 80, box_y + box_h - 40)
            self._draw_button(screen, self.accept_btn, "ACEITAR", (50, 150, 50), (100, 200, 100))
            self._draw_button(screen, self.decline_btn, "RECUSAR", (150, 50, 50), (200, 80, 80))

    def _draw_player_entry(self, screen, name, is_self=False):
        vw = self.screen_manager.viewport_width
        vh = self.screen_manager.viewport_height
        vx = self.screen_manager.viewport_x
        vy = self.screen_manager.viewport_y

        rect = pygame.Rect(vx + (vw - 300)//2, vy + 100, 300, 40)
        color = (40, 60, 40) if is_self else (60, 60, 80)
        pygame.draw.rect(screen, color, rect, border_radius=8)
        pygame.draw.rect(screen, (200, 200, 200), rect, 2, border_radius=8)

        font = pygame.font.Font(None, 28)
        status = "🟢 (Você)"
        txt = font.render(f"{status} {name}", True, (100, 255, 100))
        screen.blit(txt, (rect.x + 15, rect.y + 8))

    def _draw_button(self, screen, rect, text, color, hover_color):
        mouse = pygame.mouse.get_pos()
        hover = rect.collidepoint(mouse)
        pygame.draw.rect(screen, hover_color if hover else color, rect, border_radius=10)
        pygame.draw.rect(screen, (255, 255, 255), rect, 2, border_radius=10)
        font = pygame.font.Font(None, 28)
        txt = font.render(text, True, (255, 255, 255))
        txt_rect = txt.get_rect(center=rect.center)
        screen.blit(txt, txt_rect)