# src/scenes/lobby_scene/lobby_scene.py

import pygame
import tkinter as tk
from src.scenes.base_scene import BaseScene
from src.ui.toast_renderer import toast_info, toast_warning
from src.managers.sounds.sound_manager import sound_manager, SoundEffect
from src.network.protocol import create_message


# =========================================================
# Paleta
# =========================================================
COL_BG           = (16, 18, 30)
COL_PANEL        = (26, 29, 48)
COL_PANEL_DARK   = (20, 22, 38)
COL_BORDER       = (55, 58, 82)
COL_BORDER_HL    = (110, 115, 150)
COL_DIVIDER      = (45, 48, 70)

COL_ACCENT       = (255, 215, 0)
COL_TEXT         = (235, 235, 245)
COL_TEXT_DIM     = (170, 175, 200)
COL_TEXT_MUTED   = (95, 100, 130)

COL_SUCCESS      = (105, 220, 130)
COL_WARN         = (255, 185, 100)
COL_DANGER       = (230, 90, 90)
COL_INFO         = (110, 170, 255)

COL_BTN_PRIMARY       = (52, 100, 180)
COL_BTN_PRIMARY_H     = (76, 142, 232)
COL_BTN_SUCCESS       = (44, 128, 74)
COL_BTN_SUCCESS_H     = (70, 178, 104)
COL_BTN_DANGER        = (128, 48, 54)
COL_BTN_DANGER_H      = (180, 70, 76)
COL_BTN_RAID          = (110, 70, 170)
COL_BTN_RAID_H        = (150, 100, 220)
COL_BTN_PVP           = (150, 70, 100)
COL_BTN_PVP_H         = (200, 100, 140)
COL_BTN_DISABLED      = (40, 43, 58)


# Whitelist de tipos que o lobby trata. Desconhecidos: descartados.
_LOBBY_HANDLED_TYPES = {
    "PLAYER_INFO", "PLAYER_LIST",
    "CHAT_MESSAGE",
    "TRADE_REQUEST", "TRADE_RESPONSE",
    "RAID_JOIN", "RAID_RETURN_LOBBY",
    "PVP_JOIN",
    "DISCONNECT",
}


class LobbyScene(BaseScene):
    """Lobby multiplayer com chat, lista de jogadores e solicitação de troca."""

    LIST_W          = 260
    LIST_H          = 230
    BTN_W           = 260
    BTN_H           = 38
    BTN_GAP         = 8
    LEFT_MARGIN     = 20

    REBROADCAST_INTERVAL = 2.0
    MAX_PROCESS_PER_FRAME = 200

    def __init__(self, game, is_host, network):
        super().__init__(game)
        self.network = network
        self.is_host = is_host
        self.network.current_scene_callback = self._on_network_message

        self.my_name = network.my_name
        self.players = [self.my_name]
        self.opponent_name = None
        self.opponent_uuid = None
        self.chat_messages = []
        self.chat_input = ""
        self.chat_active = False
        self.pending_trade_from = None
        self._animation_timer = 0
        self._rebroadcast_timer = 0.0

        player_uuid = (
            getattr(self.game.player, 'uuid', None)
            or getattr(self.network, 'my_uuid', None)
            or "unknown"
        )
        if hasattr(self.network, 'set_uuid'):
            self.network.set_uuid(player_uuid)
        self._my_uuid = player_uuid

        self.back_btn = pygame.Rect(0, 0, 130, 42)
        self.trade_btn = pygame.Rect(0, 0, self.BTN_W, self.BTN_H)
        self.raid_btn = pygame.Rect(0, 0, self.BTN_W, self.BTN_H)
        self.pvp_btn = pygame.Rect(0, 0, self.BTN_W, self.BTN_H)
        self.send_btn = pygame.Rect(0, 0, 80, 32)
        self.chat_input_rect = pygame.Rect(0, 0, 0, 0)

        self.accept_btn = pygame.Rect(0, 0, 100, 40)
        self.decline_btn = pygame.Rect(0, 0, 100, 40)

        self._list_rect = pygame.Rect(0, 0, 0, 0)
        self._chat_rect = pygame.Rect(0, 0, 0, 0)

        self._update_button_positions()

        self._init_clipboard()

        self.font_title = pygame.font.Font(None, 42)
        self.font = pygame.font.Font(None, 26)
        self.font_small = pygame.font.Font(None, 20)
        self.font_tiny = pygame.font.Font(None, 17)
        self.font_chat = pygame.font.Font(None, 18)
        self.font_btn = pygame.font.Font(None, 22)

        # Processa a fila IMEDIATAMENTE para pegar PLAYER_LIST que
        # chegou durante a transição de cena
        self._process_incoming()

        # Resync
        if self.is_host:
            self._seed_from_network()
            self._broadcast_full_list()
        else:
            self.network.send_to_all(create_message("PLAYER_INFO", {
                "name": self.my_name, "uuid": self._my_uuid,
            }))

        print(f"[LOBBY] {self.my_name} (UUID: {self._my_uuid[:8]}) "
              f"entrou no lobby (host={self.is_host}) "
              f"| players={self.players}")

    # ==================================================================
    def _seed_from_network(self):
        try:
            full_list = self.network._get_full_player_list()
        except Exception as e:
            print(f"[LOBBY] erro _get_full_player_list: {e}")
            full_list = []

        for entry in full_list:
            if isinstance(entry, dict):
                name = entry.get("name")
                uuid_str = entry.get("uuid", "unknown")
            else:
                name = entry
                uuid_str = "unknown"
            if name and name != self.my_name and name not in self.players:
                self.players.append(name)
                if self.opponent_name is None:
                    self.opponent_name = name
                    self.opponent_uuid = uuid_str
                print(f"[LOBBY] seed: + {name} ({uuid_str[:8]})")

    def _broadcast_full_list(self):
        if not self.is_host:
            return
        try:
            players = self.network._get_full_player_list()
        except Exception:
            players = [{"name": self.my_name, "uuid": self._my_uuid}]
        self.network.send_to_all(create_message("PLAYER_LIST", {
            "players": players
        }))

    # ==================================================================
    def _init_clipboard(self):
        try:
            self._root = tk.Tk()
            self._root.withdraw()
            self._clipboard_available = True
        except Exception:
            self._clipboard_available = False

    def _paste_from_clipboard(self):
        if not self._clipboard_available:
            return ""
        try:
            return self._root.clipboard_get()
        except Exception:
            return ""

    # ------------------------------------------------------------------
    def _update_button_positions(self):
        vx = self.screen_manager.viewport_x
        vy = self.screen_manager.viewport_y
        vw = self.screen_manager.viewport_width
        vh = self.screen_manager.viewport_height

        self.back_btn = pygame.Rect(vx + 15, vy + 15, 130, 42)

        self._list_rect = pygame.Rect(
            vx + self.LEFT_MARGIN, vy + 90, self.LIST_W, self.LIST_H
        )

        bottom_margin = 34
        instr_h = 22
        pvp_y = vy + vh - bottom_margin - instr_h - self.BTN_H
        raid_y = pvp_y - self.BTN_GAP - self.BTN_H
        trade_y = raid_y - self.BTN_GAP - self.BTN_H

        self.trade_btn = pygame.Rect(vx + self.LEFT_MARGIN + 10, trade_y,
                                     self.BTN_W, self.BTN_H)
        self.raid_btn = pygame.Rect(vx + self.LEFT_MARGIN + 10, raid_y,
                                    self.BTN_W, self.BTN_H)
        self.pvp_btn = pygame.Rect(vx + self.LEFT_MARGIN + 10, pvp_y,
                                   self.BTN_W, self.BTN_H)

        chat_x = self._list_rect.right + 20
        self._chat_rect = pygame.Rect(
            chat_x, vy + 90,
            vw - (chat_x - vx) - 20,
            vh - 90 - 55,
        )

        self.chat_input_rect = pygame.Rect(
            self._chat_rect.x + 12,
            self._chat_rect.bottom - 42,
            self._chat_rect.width - 12 - 100, 32,
        )
        self.send_btn = pygame.Rect(
            self.chat_input_rect.right + 8,
            self.chat_input_rect.y,
            80,
            32,
        )

        cx = vx + vw // 2
        cy = vy + vh // 2 + 60
        self.accept_btn = pygame.Rect(0, 0, 100, 40)
        self.decline_btn = pygame.Rect(0, 0, 100, 40)
        self.accept_btn.center = (cx - 110, cy)
        self.decline_btn.center = (cx + 110, cy)

    # ==================================================================
    # REDE — SEM LOOP
    # ==================================================================
    def _process_incoming(self):
        """Processa fila com limite e sem re-enfileiramento."""
        count = 0
        while count < self.MAX_PROCESS_PER_FRAME:
            if self.network.incoming_queue.empty():
                break
            count += 1

            try:
                item = self.network.incoming_queue.get_nowait()
            except Exception:
                break

            if isinstance(item, tuple) and len(item) == 2:
                msg, conn = item
            else:
                msg, conn = item, None

            msg_type = msg.get("type") if isinstance(msg, dict) else None
            if msg_type not in _LOBBY_HANDLED_TYPES:
                # Descartado (mensagem de outra cena)
                continue

            try:
                self._on_network_message(msg, conn)
            except Exception as e:
                print(f"[LOBBY] erro handler {msg_type}: {e}")

    def _on_network_message(self, msg, conn=None):
        msg_type = msg.get("type")
        if msg_type not in _LOBBY_HANDLED_TYPES:
            return

        payload = msg.get("payload", {})

        if msg_type == "PLAYER_INFO":
            name = payload.get("name", "Desconhecido")
            uuid_str = payload.get("uuid", "unknown")
            if name == self.my_name:
                return

            was_new = name not in self.players
            if was_new:
                self.players.append(name)
                print(f"[LOBBY] + {name} ({uuid_str[:8]}) "
                      f"({len(self.players)} total)")
                toast_info(f"{name} entrou na sala!")

            if self.opponent_name is None or self.opponent_name == name:
                self.opponent_name = name
                self.opponent_uuid = uuid_str

            if self.is_host:
                self._broadcast_full_list()

        elif msg_type == "PLAYER_LIST":
            players_data = payload.get("players", [])
            normalized = []
            if isinstance(players_data, list):
                for entry in players_data:
                    if isinstance(entry, dict):
                        normalized.append({
                            "name": entry.get("name", "?"),
                            "uuid": entry.get("uuid", "unknown"),
                        })
                    else:
                        normalized.append({"name": str(entry), "uuid": "unknown"})
            elif isinstance(players_data, dict):
                for name in players_data.values():
                    normalized.append({"name": str(name), "uuid": "unknown"})

            self.players = [self.my_name]
            self.opponent_name = None
            self.opponent_uuid = None
            for entry in normalized:
                if entry["name"] != self.my_name and entry["name"] not in self.players:
                    self.players.append(entry["name"])
                    if self.opponent_name is None:
                        self.opponent_name = entry["name"]
                        self.opponent_uuid = entry["uuid"]

            if hasattr(self.network, 'opponent_name'):
                self.network.opponent_name = self.opponent_name
            if hasattr(self.network, 'opponent_uuid'):
                self.network.opponent_uuid = self.opponent_uuid

            print(f"[LOBBY] lista recebida: {self.players} | "
                  f"oponente={self.opponent_name}")

        elif msg_type == "CHAT_MESSAGE":
            sender = payload.get("sender", "?")
            text = payload.get("text", "")
            if sender != self.my_name and text:
                self.chat_messages.append(f"{sender}: {text}")

        elif msg_type == "TRADE_REQUEST":
            from_name = payload.get("from", "Desconhecido")
            if from_name != self.my_name:
                self.pending_trade_from = from_name
                toast_info(f"{from_name} quer trocar com voce!")

        elif msg_type == "TRADE_RESPONSE":
            accepted = payload.get("accepted", False)
            if accepted:
                toast_info("Oponente aceitou! Abrindo tela de troca...")
                self._open_trade_scene()
            else:
                toast_info("Oponente recusou a troca.")
                self.pending_trade_from = None

        elif msg_type == "RAID_JOIN":
            name = payload.get("name", "?")
            if name != self.my_name:
                toast_info(f"{name} entrou na raid.")

        elif msg_type == "RAID_RETURN_LOBBY":
            if self.is_host:
                self._broadcast_full_list()

        elif msg_type == "PVP_JOIN":
            # Só informativo. O PvP_MM trata o JOIN de verdade.
            name = payload.get("name", "?")
            if name != self.my_name:
                toast_info(f"{name} entrou no PvP.")

        elif msg_type == "DISCONNECT":
            who = payload.get("name", "O outro jogador")
            toast_warning(f"{who} desconectou.")
            self._return_to_menu()

    # ==================================================================
    # AÇÕES
    # ==================================================================
    def _open_trade_scene(self):
        from src.scenes.trade_scene.trade_scene import TradeScene
        if hasattr(self.network, 'opponent_name'):
            self.network.opponent_name = self.opponent_name
        if hasattr(self.network, 'opponent_uuid'):
            self.network.opponent_uuid = self.opponent_uuid
        self.game.current_scene = TradeScene(
            self.game, is_host=self.is_host, network=self.network
        )

    def _open_raid_scene(self):
        from src.scenes.raid_scene.raid_scene import RaidScene
        self.game.current_scene = RaidScene(
            self.game, is_host=self.is_host, network=self.network
        )

    def _open_pvp_scene(self):
        from src.scenes.pvp_scene.pvp_select_scene import PvPSelectScene
        self.game.current_scene = PvPSelectScene(
            self.game,
            self.network,
            on_back=lambda: setattr(
                self.game, 'current_scene',
                LobbyScene(self.game, self.is_host, self.network),
            ),
        )

    def _return_to_menu(self):
        self.network.stop()
        self.game.current_scene = self.game.menu_scene

    def _send_chat(self):
        text = self.chat_input.strip()
        if not text:
            return
        self.chat_input = ""
        self.network.send_to_all(
            create_message("CHAT_MESSAGE",
                           {"sender": self.my_name, "text": text})
        )
        self.chat_messages.append(f"{self.my_name}: {text}")

    def _request_trade(self):
        if not self.opponent_name:
            toast_warning("Nenhum oponente conectado.")
            return
        self.network.send_to_all(
            create_message("TRADE_REQUEST", {"from": self.my_name})
        )
        toast_info(f"Solicitacao enviada para {self.opponent_name}.")

    def _handle_trade_response(self, accepted):
        self.network.send_to_all(
            create_message("TRADE_RESPONSE", {"accepted": accepted})
        )
        if accepted:
            self._open_trade_scene()
        else:
            self.pending_trade_from = None

    # ==================================================================
    # EVENTOS
    # ==================================================================
    def handle_event(self, event):
        if event.type == pygame.VIDEORESIZE:
            self._update_button_positions()
            return

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

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mp = event.pos

            if self.back_btn.collidepoint(mp):
                sound_manager.play_effect(SoundEffect.CLICK)
                self.network.send_to_all(
                    create_message("DISCONNECT", {"name": self.my_name})
                )
                self._return_to_menu()
                return

            if self.trade_btn.collidepoint(mp) and self.opponent_name:
                sound_manager.play_effect(SoundEffect.CLICK)
                self._request_trade()
                return

            if self.raid_btn.collidepoint(mp) and self.opponent_name:
                sound_manager.play_effect(SoundEffect.CLICK)
                self._open_raid_scene()
                return

            if self.pvp_btn.collidepoint(mp) and self.opponent_name:
                sound_manager.play_effect(SoundEffect.CLICK)
                self._open_pvp_scene()
                return

            if self.send_btn.collidepoint(mp):
                self._send_chat()
                return

            if self.chat_input_rect.collidepoint(mp):
                self.chat_active = True
                return

            if self.pending_trade_from:
                if self.accept_btn.collidepoint(mp):
                    self._handle_trade_response(True)
                    return
                if self.decline_btn.collidepoint(mp):
                    self._handle_trade_response(False)
                    return

            self.chat_active = False

    # ==================================================================
    # UPDATE
    # ==================================================================
    def fixed_update(self, dt):
        self._animation_timer += dt
        self._process_incoming()

        if self.is_host:
            self._rebroadcast_timer += dt
            if self._rebroadcast_timer >= self.REBROADCAST_INTERVAL:
                self._rebroadcast_timer = 0.0
                self._broadcast_full_list()

    # ==================================================================
    # RENDER
    # ==================================================================
    def render(self, screen):
        screen.fill(COL_BG)

        vx = self.screen_manager.viewport_x
        vy = self.screen_manager.viewport_y
        vw = self.screen_manager.viewport_width
        vh = self.screen_manager.viewport_height

        self._update_button_positions()

        title = self.font_title.render("LOBBY", True, COL_ACCENT)
        title_rect = title.get_rect(center=(vx + vw // 2, vy + 40))
        screen.blit(title, title_rect)

        line_w = 320
        pygame.draw.line(screen, COL_DIVIDER,
                         (vx + vw // 2 - line_w // 2, vy + 65),
                         (vx + vw // 2 + line_w // 2, vy + 65), 2)

        self._draw_button(screen, self.back_btn, "Voltar",
                          COL_BTN_DANGER, COL_BTN_DANGER_H)

        self._render_players_list(screen)
        self._render_action_buttons(screen)

        instr = self.font_tiny.render(
            "C = chat  ·  T = trocar  ·  Ctrl+V = colar",
            True, COL_TEXT_MUTED)
        screen.blit(instr, (vx + self.LEFT_MARGIN, vy + vh - 26))

        self._render_chat(screen)

        if self.pending_trade_from:
            self._render_trade_request(screen)

    def _render_players_list(self, screen):
        rect = self._list_rect
        pygame.draw.rect(screen, COL_PANEL, rect, border_radius=10)
        pygame.draw.rect(screen, COL_BORDER, rect, 1, border_radius=10)

        t = self.font_small.render("Jogadores", True, COL_TEXT)
        screen.blit(t, (rect.x + 12, rect.y + 10))

        count = f"{len(self.players)}/6"
        cs = self.font_tiny.render(count, True, COL_TEXT_MUTED)
        screen.blit(cs, (rect.right - cs.get_width() - 12, rect.y + 12))

        pygame.draw.line(screen, COL_DIVIDER,
                         (rect.x + 8, rect.y + 34),
                         (rect.right - 8, rect.y + 34), 1)

        y = rect.y + 46
        for name in self.players[:6]:
            is_me = (name == self.my_name)

            dot_x = rect.x + 16
            dot_y = y + 10
            pygame.draw.circle(screen, COL_SUCCESS if is_me else COL_INFO,
                               (dot_x, dot_y), 5)

            label = f"{name} (você)" if is_me else name
            color = COL_SUCCESS if is_me else COL_TEXT
            ns = self.font_small.render(label, True, color)
            screen.blit(ns, (rect.x + 28, y))

            if is_me and self.is_host:
                badge = self.font_tiny.render("HOST", True, COL_ACCENT)
                bx = rect.right - badge.get_width() - 12
                screen.blit(badge, (bx, y + 2))

            y += 28

        if len(self.players) <= 1:
            hint = self.font_tiny.render(
                "Aguardando oponente...", True, COL_TEXT_MUTED)
            screen.blit(hint, (rect.x + 16, rect.bottom - 26))

    def _render_action_buttons(self, screen):
        has_opponent = bool(self.opponent_name)

        if has_opponent:
            self._draw_button(screen, self.trade_btn,
                              f"Trocar com {self.opponent_name}",
                              COL_BTN_PRIMARY, COL_BTN_PRIMARY_H)
        else:
            self._draw_button(screen, self.trade_btn,
                              "Trocar (aguardando...)",
                              COL_BTN_DISABLED, COL_BTN_DISABLED,
                              enabled=False)

        if has_opponent:
            self._draw_button(screen, self.raid_btn, "Entrar em Raid",
                              COL_BTN_RAID, COL_BTN_RAID_H)
        else:
            self._draw_button(screen, self.raid_btn,
                              "Raid (precisa 2+)",
                              COL_BTN_DISABLED, COL_BTN_DISABLED,
                              enabled=False)

        if has_opponent:
            self._draw_button(screen, self.pvp_btn, "Arena PvP",
                              COL_BTN_PVP, COL_BTN_PVP_H)
        else:
            self._draw_button(screen, self.pvp_btn,
                              "Arena PvP (precisa 2+)",
                              COL_BTN_DISABLED, COL_BTN_DISABLED,
                              enabled=False)

    def _render_chat(self, screen):
        rect = self._chat_rect
        pygame.draw.rect(screen, COL_PANEL, rect, border_radius=10)
        pygame.draw.rect(screen, COL_BORDER, rect, 1, border_radius=10)

        t = self.font_small.render("Chat", True, COL_TEXT)
        screen.blit(t, (rect.x + 12, rect.y + 10))

        pygame.draw.line(screen, COL_DIVIDER,
                         (rect.x + 10, rect.y + 34),
                         (rect.right - 10, rect.y + 34), 1)

        y = rect.y + 46
        max_lines = max(1, (self.chat_input_rect.y - y - 12) // 22)
        for msg in self.chat_messages[-max_lines:]:
            color = (COL_ACCENT if msg.startswith(self.my_name + ":")
                     else COL_TEXT)
            text = msg
            max_w = rect.width - 24
            while self.font_chat.size(text)[0] > max_w and len(text) > 8:
                text = text[:-1]
            if text != msg:
                text = text[:-2] + "..."
            txt = self.font_chat.render(text, True, color)
            screen.blit(txt, (rect.x + 12, y))
            y += 22

        border_color = COL_ACCENT if self.chat_active else COL_BORDER
        pygame.draw.rect(screen, COL_PANEL_DARK, self.chat_input_rect,
                         border_radius=6)
        pygame.draw.rect(screen, border_color, self.chat_input_rect, 2,
                         border_radius=6)

        if self.chat_active:
            display = self.chat_input if self.chat_input else "Digite... (Ctrl+V)"
            color = COL_TEXT if self.chat_input else COL_TEXT_MUTED
        else:
            display = "Pressione C para chat..."
            color = COL_TEXT_MUTED

        txt = self.font_small.render(display, True, color)
        screen.blit(txt, (self.chat_input_rect.x + 10,
                          self.chat_input_rect.y + 7))

        self._draw_button(screen, self.send_btn, "Enviar",
                          COL_BTN_SUCCESS, COL_BTN_SUCCESS_H)

    def _render_trade_request(self, screen):
        vx = self.screen_manager.viewport_x
        vy = self.screen_manager.viewport_y
        vw = self.screen_manager.viewport_width
        vh = self.screen_manager.viewport_height

        overlay = pygame.Surface((vw, vh))
        overlay.set_alpha(180)
        overlay.fill((0, 0, 0))
        screen.blit(overlay, (vx, vy))

        dialog = pygame.Rect(vx + vw // 2 - 220, vy + vh // 2 - 80, 440, 160)
        pygame.draw.rect(screen, (35, 30, 50), dialog, border_radius=12)
        pygame.draw.rect(screen, COL_ACCENT, dialog, 2, border_radius=12)

        txt = self.font.render(
            f"{self.pending_trade_from} quer trocar com voce!",
            True, COL_TEXT)
        screen.blit(txt, (dialog.x + 20, dialog.y + 25))

        txt2 = self.font_small.render("Selecione uma opcao:",
                                       True, COL_TEXT_DIM)
        screen.blit(txt2, (dialog.x + 20, dialog.y + 60))

        self.accept_btn.center = (dialog.centerx - 110, dialog.bottom - 45)
        self.decline_btn.center = (dialog.centerx + 110, dialog.bottom - 45)

        self._draw_button(screen, self.accept_btn, "Aceitar",
                          COL_BTN_SUCCESS, COL_BTN_SUCCESS_H)
        self._draw_button(screen, self.decline_btn, "Recusar",
                          COL_BTN_DANGER, COL_BTN_DANGER_H)

    def _draw_button(self, screen, rect, text, color, hover_color,
                     enabled=True):
        mouse = pygame.mouse.get_pos()
        hover = rect.collidepoint(mouse) and enabled
        bg = hover_color if hover else color

        pygame.draw.rect(screen, bg, rect, border_radius=8)

        if enabled:
            border = (200, 200, 200) if hover else COL_BORDER
        else:
            border = (60, 62, 78)
        pygame.draw.rect(screen, border, rect, 1, border_radius=8)

        text_color = (255, 255, 255) if enabled else COL_TEXT_MUTED
        size = 22 if len(text) < 20 else 16
        font = self.font_btn if size == 22 else self.font_tiny
        txt = font.render(text, True, text_color)
        screen.blit(txt, txt.get_rect(center=rect.center))

    def on_enter(self):
        pass

    def on_exit(self):
        pass