# src/scenes/lobby_scene.py

import pygame
from src.scenes.base_scene import BaseScene
from src.network.protocol import create_message
from src.ui.toast_renderer import toast_info, toast_warning
from src.managers.sounds.sound_manager import sound_manager, SoundEffect


class LobbyScene(BaseScene):
    def __init__(self, game, is_host, network):
        super().__init__(game)
        self.network = network
        self.is_host = is_host
        self.network.current_scene_callback = self._on_network_message

        # Estado do lobby
        self.players = []
        self.my_name = self.network.my_name
        self.opponent_name = None
        self.selected_mode = None  # "trade", "battle", "event"

        # Opções disponíveis (apenas troca por enquanto)
        self.modes = [
            {"id": "trade", "label": "TROCAR POKÉMON", "enabled": True},
            {"id": "battle", "label": "BATALHAR", "enabled": False},
            {"id": "event", "label": "EVENTO", "enabled": False},
        ]

        # UI
        self.back_btn = pygame.Rect(0, 0, 120, 40)
        self.start_btn = pygame.Rect(0, 0, 150, 40)
        self.mode_buttons = []
        self.selected_index = -1

        self._center_ui()
        self._create_mode_buttons()

        # Envia informações do jogador ao entrar
        self.network.send_to_all(create_message("PLAYER_INFO", {"name": self.my_name}))

    def _center_ui(self):
        vw = self.screen_manager.viewport_width
        vh = self.screen_manager.viewport_height
        vx = self.screen_manager.viewport_x
        vy = self.screen_manager.viewport_y

        self.back_btn.topleft = (vx + 20, vy + 20)
        self.start_btn.center = (vx + vw//2, vy + vh - 60)

    def _create_mode_buttons(self):
        vw = self.screen_manager.viewport_width
        vh = self.screen_manager.viewport_height
        vx = self.screen_manager.viewport_x
        vy = self.screen_manager.viewport_y

        self.mode_buttons = []
        total_height = len(self.modes) * 70
        start_y = (vh - total_height) // 2 + vy

        for i, mode in enumerate(self.modes):
            rect = pygame.Rect(0, 0, 300, 50)
            rect.center = (vx + vw//2, start_y + i * 70)
            self.mode_buttons.append({
                "rect": rect,
                "mode": mode,
                "hover": False
            })

    def _on_network_message(self, msg, conn=None):
        msg_type = msg.get("type")
        payload = msg.get("payload", {})

        if msg_type == "PLAYER_INFO":
            name = payload.get("name", "Jogador")
            if name != self.my_name:
                self.opponent_name = name
                toast_info(f"{name} entrou na sala!")
                # Atualiza a lista de jogadores
                self.players = [self.my_name, self.opponent_name]
        elif msg_type == "GAME_MODE_SELECT":
            mode = payload.get("mode")
            if mode == "trade":
                # Inicia a troca
                toast_info("Iniciando troca...")
                from src.scenes.trade_scene.trade_scene import TradeScene
                self.game.current_scene = TradeScene(self.game, is_host=self.is_host, network=self.network)
        elif msg_type == "DISCONNECT":
            toast_warning("O outro jogador desconectou.")
            self._return_to_menu()

    def handle_event(self, event):
        if event.type == pygame.VIDEORESIZE:
            self._center_ui()
            self._create_mode_buttons()
            return

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            # Botão voltar
            if self.back_btn.collidepoint(event.pos):
                sound_manager.play_effect(SoundEffect.CLICK)
                self.network.send_to_all(create_message("DISCONNECT"))
                self.network.stop()
                self.game.current_scene = self.game.menu_scene
                return

            # Botão iniciar (apenas host)
            if self.is_host and self.start_btn.collidepoint(event.pos):
                if self.selected_mode:
                    self.network.send_to_all(create_message("GAME_MODE_SELECT", {"mode": self.selected_mode}))
                    # Inicia imediatamente para o host também
                    if self.selected_mode == "trade":
                        from src.scenes.trade_scene.trade_scene import TradeScene
                        self.game.current_scene = TradeScene(self.game, is_host=True, network=self.network)
                else:
                    toast_warning("Selecione um modo primeiro!")

            # Seleção de modo
            for btn in self.mode_buttons:
                if btn["rect"].collidepoint(event.pos):
                    if btn["mode"]["enabled"]:
                        self.selected_index = self.mode_buttons.index(btn)
                        self.selected_mode = btn["mode"]["id"]
                        toast_info(f"Modo selecionado: {btn['mode']['label']}")
                    else:
                        toast_warning("Este modo ainda não está disponível!")

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self._return_to_menu()

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
        font = pygame.font.Font(None, 48)
        title = font.render("LOBBY", True, (255, 215, 0))
        title_rect = title.get_rect(center=(vx + vw//2, vy + 60))
        screen.blit(title, title_rect)

        # Informações dos jogadores
        font_small = pygame.font.Font(None, 28)
        if self.opponent_name:
            info_text = f"Jogadores: {self.my_name} x {self.opponent_name}"
        else:
            info_text = f"Aguardando oponente... (você: {self.my_name})"
        info_surf = font_small.render(info_text, True, (200, 200, 200))
        screen.blit(info_surf, (vx + vw//2 - info_surf.get_width()//2, vy + 110))

        # Botões de modo
        for btn in self.mode_buttons:
            mode = btn["mode"]
            rect = btn["rect"]
            hover = rect.collidepoint(pygame.mouse.get_pos())
            btn["hover"] = hover

            # Cor base
            if mode["enabled"]:
                color = (60, 60, 80) if not hover else (80, 80, 120)
                if self.selected_mode == mode["id"]:
                    color = (50, 120, 50)  # verde para selecionado
            else:
                color = (40, 40, 40)  # cinza escuro para bloqueado

            pygame.draw.rect(screen, color, rect, border_radius=10)
            pygame.draw.rect(screen, (200, 200, 200) if mode["enabled"] else (100, 100, 100), rect, 2, border_radius=10)

            # Texto
            font_mode = pygame.font.Font(None, 30)
            label = mode["label"]
            if not mode["enabled"]:
                label += " (em breve)"
            text_color = (255, 255, 255) if mode["enabled"] else (150, 150, 150)
            txt = font_mode.render(label, True, text_color)
            txt_rect = txt.get_rect(center=rect.center)
            screen.blit(txt, txt_rect)

        # Botão Iniciar (apenas host)
        if self.is_host and self.opponent_name:
            self._draw_button(screen, self.start_btn, "INICIAR", (50, 150, 50), (100, 200, 100))
        elif self.is_host:
            self._draw_button(screen, self.start_btn, "AGUARDANDO...", (80, 80, 80), (80, 80, 80))

        # Botão voltar
        self._draw_button(screen, self.back_btn, "VOLTAR", (100, 50, 50), (150, 80, 80))

        # Status
        if not self.is_host:
            status = "Aguardando o host iniciar..."
            status_font = pygame.font.Font(None, 24)
            status_surf = status_font.render(status, True, (180, 180, 180))
            screen.blit(status_surf, (vx + vw//2 - status_surf.get_width()//2, vy + vh - 40))

        # Instruções
        if self.is_host and self.opponent_name and not self.selected_mode:
            inst = "Selecione um modo e clique em INICIAR"
            inst_font = pygame.font.Font(None, 22)
            inst_surf = inst_font.render(inst, True, (255, 200, 100))
            screen.blit(inst_surf, (vx + vw//2 - inst_surf.get_width()//2, vy + vh - 80))

    def _return_to_menu(self):
        self.network.stop()
        self.game.current_scene = self.game.menu_scene

    def _draw_button(self, screen, rect, text, color, hover_color):
        mouse = pygame.mouse.get_pos()
        hover = rect.collidepoint(mouse)
        pygame.draw.rect(screen, hover_color if hover else color, rect, border_radius=10)
        pygame.draw.rect(screen, (255, 255, 255), rect, 2, border_radius=10)
        font = pygame.font.Font(None, 28)
        txt = font.render(text, True, (255, 255, 255))
        txt_rect = txt.get_rect(center=rect.center)
        screen.blit(txt, txt_rect)