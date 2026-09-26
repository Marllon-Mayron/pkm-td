# src/scenes/pvp_scene/pvp_matchmaking_scene.py
"""
Sala de espera PvP entre jogadores.

IMPORTANTE: NÃO re-enfileira mensagens desconhecidas — isso causaria
loop infinito (o put nunca deixa a fila vazia). Mensagens que a cena
não conhece são descartadas silenciosamente.
"""
import math
import pygame

from src.scenes.base_scene import BaseScene
from src.data.pvp_catalog import (
    get_pvp_format, get_pvp_total_players,
)
from src.network.protocol import create_message
from src.managers.sounds.sound_manager import sound_manager, SoundEffect


COL_BG         = (16, 18, 30)
COL_PANEL      = (26, 29, 48)
COL_PANEL_DARK = (20, 22, 38)
COL_BORDER     = (55, 58, 82)
COL_DIVIDER    = (45, 48, 70)
COL_ACCENT     = (255, 215, 0)
COL_TEXT       = (235, 235, 245)
COL_TEXT_DIM   = (170, 175, 200)
COL_TEXT_MUTED = (95, 100, 130)
COL_SUCCESS    = (105, 220, 130)
COL_DANGER     = (230, 90, 90)
COL_INFO       = (110, 170, 255)
COL_WARN       = (255, 185, 100)

COL_BTN_DANGER = (128, 48, 54)
COL_BTN_DANGER_H = (180, 70, 76)


# Tipos que o PvP_MM trata. Qualquer outro é descartado.
_PVP_MM_HANDLED_TYPES = {
    "PVP_JOIN",
    "PVP_PLAYER_LIST",
    "PVP_TEAM_ASSIGN",
    "PVP_START",
    "PVP_CANCEL",
    "PVP_LEAVE",
    "DISCONNECT",
}


class PvPMatchmakingScene(BaseScene):
    REBROADCAST_INTERVAL = 1.0
    RETRY_JOIN_INTERVAL = 1.5
    MAX_PROCESS_PER_FRAME = 200   # proteção contra loop

    def __init__(self, game, network, format_chapter, my_team_data,
                 on_back=None, on_ready=None):
        super().__init__(game)
        self.network = network
        self.format_chapter = format_chapter
        self.my_team_data = my_team_data
        self._on_back = on_back
        self._on_ready = on_ready

        (self.players_per_team,
         self.pokemon_per_player,
         self.spots_per_player,
         self.format_name) = get_pvp_format(format_chapter)

        self.total_players = get_pvp_total_players(format_chapter)

        self.players = {}
        self.countdown = 0
        self.countdown_timer = 0.0
        self._started = False
        self._rebroadcast_timer = 0.0
        self._retry_join_timer = 0.0

        if hasattr(network, '_ensure_session_uuid'):
            network._ensure_session_uuid()

        self.my_uuid = (
                getattr(network, "my_uuid", None)
                or getattr(game.player, "uuid", None)
                or "unknown"
        )
        network.set_uuid(self.my_uuid)
        print(f"[PVP_MM] UUID local: {self.my_uuid[:8]}")
        network.set_uuid(self.my_uuid)

        self.players[self.my_uuid] = {
            "name": network.my_name,
            "team_data": my_team_data,
            "team_side": None,
            "ready": False,
        }

        self.font_title = pygame.font.Font(None, 44)
        self.font_h1 = pygame.font.Font(None, 28)
        self.font_h2 = pygame.font.Font(None, 22)
        self.font = pygame.font.Font(None, 20)
        self.font_small = pygame.font.Font(None, 18)
        self.font_tiny = pygame.font.Font(None, 16)

        self.leave_btn = pygame.Rect(0, 0, 200, 44)
        self._layout()

        self._prev_callback = network.current_scene_callback
        network.current_scene_callback = self._on_network_message

        # Processa fila antes de qualquer coisa
        self._process_incoming()

        if network.is_host:
            self._broadcast_list()
            self._check_full()
        else:
            self._send_join()

        print(f"[PVP_MM] {network.my_name} entrou "
              f"(host={network.is_host}) formato={self.format_name} "
              f"total={self.total_players} uuid={self.my_uuid[:8]}")

    # ==================================================================
    def _layout(self):
        sm = self.screen_manager
        vx = sm.viewport_x
        vy = sm.viewport_y
        vh = sm.viewport_height
        self.leave_btn = pygame.Rect(vx + 30, vy + vh - 60, 200, 44)

    # ==================================================================
    def _send_join(self):
        try:
            self.network.send_to_all(create_message("PVP_JOIN", {
                "uuid": self.my_uuid,
                "name": self.network.my_name,
                "format_chapter": self.format_chapter,
                "team_data": self.my_team_data,
            }))
        except Exception as e:
            print(f"[PVP_MM] erro enviar JOIN: {e}")

    # ==================================================================
    # REDE — SEM LOOP
    # ==================================================================
    def _process_incoming(self):
        """
        Processa a fila de rede de forma SEGURA.

        - NÃO re-enfileira nada (evita loop infinito).
        - Limite de mensagens por frame (defesa em profundidade).
        - Exceções por mensagem não travam a fila.
        """
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

            # Só processa tipos conhecidos. Desconhecidos: descarta.
            msg_type = msg.get("type") if isinstance(msg, dict) else None
            if msg_type not in _PVP_MM_HANDLED_TYPES:
                # print para debug (útil pra ver mensagens perdidas)
                # print(f"[PVP_MM] descartando: {msg_type}")
                continue

            try:
                self._on_network_message(msg, conn)
            except Exception as e:
                print(f"[PVP_MM] erro handler {msg_type}: {e}")

    def _on_network_message(self, msg, conn=None):
        t = msg.get("type")
        p = msg.get("payload", {})

        if t == "PVP_JOIN":
            u = p.get("uuid")
            if not u or u == self.my_uuid:
                return

            is_new = u not in self.players
            if is_new:
                self.players[u] = {
                    "name": p.get("name", "?"),
                    "team_data": p.get("team_data", []),
                    "team_side": None,
                    "ready": False,
                }
                print(f"[PVP_MM] + {p.get('name')} "
                      f"({len(self.players)}/{self.total_players})")

            if self.network.is_host:
                self._broadcast_list()
                self._check_full()

        elif t == "PVP_PLAYER_LIST":
            players = p.get("players", {})
            added = False
            for u, info in players.items():
                if u not in self.players:
                    self.players[u] = {
                        "name": info.get("name", "?"),
                        "team_data": info.get("team_data", []),
                        "team_side": None,
                        "ready": False,
                    }
                    added = True
                    print(f"[PVP_MM] (lista) + {info.get('name')} "
                          f"({len(self.players)}/{self.total_players})")

            if self.network.is_host and added:
                self._check_full()

        elif t == "PVP_TEAM_ASSIGN":
            assignments = p.get("assignments", {})
            for u, side in assignments.items():
                if u in self.players:
                    self.players[u]["team_side"] = side

            self.countdown = int(p.get("countdown", 5))
            self.countdown_timer = 0.0
            print(f"[PVP_MM] Team assign: {assignments}")

        elif t == "PVP_START":
            self._launch_battle()

        elif t == "PVP_CANCEL":
            print(f"[PVP_MM] Cancelado: {p.get('reason', '?')}")
            self._go_back()

        elif t == "PVP_LEAVE":
            u = p.get("uuid")
            if u and u in self.players and u != self.my_uuid:
                name = self.players[u].get("name", "?")
                del self.players[u]
                print(f"[PVP_MM] - {name} "
                      f"({len(self.players)}/{self.total_players})")
                if self.network.is_host:
                    self._broadcast_list()

        elif t == "DISCONNECT":
            print(f"[PVP_MM] Desconexão: {p.get('name', '?')}")
            self._go_back()

    def _broadcast_list(self):
        payload = {
            "players": {
                u: {"name": info["name"], "team_data": info["team_data"]}
                for u, info in self.players.items()
            }
        }
        self.network.send_to_all(create_message("PVP_PLAYER_LIST", payload))

    def _check_full(self):
        if not self.network.is_host:
            return
        if self.countdown > 0:
            return
        if len(self.players) < self.total_players:
            return

        uuids = sorted(self.players.keys())
        mid = len(uuids) // 2
        assignments = {}
        for i, u in enumerate(uuids):
            assignments[u] = "a" if i < mid else "b"

        for u, side in assignments.items():
            self.players[u]["team_side"] = side

        self.network.send_to_all(create_message("PVP_TEAM_ASSIGN", {
            "assignments": assignments,
            "countdown": 5,
        }))
        self.countdown = 5
        self.countdown_timer = 0.0
        print(f"[PVP_MM] Times definidos: {assignments}")

    # ==================================================================
    # UPDATE
    # ==================================================================
    def fixed_update(self, dt):
        self._process_incoming()

        if self.network.is_host and self.countdown <= 0:
            self._rebroadcast_timer += dt
            if self._rebroadcast_timer >= self.REBROADCAST_INTERVAL:
                self._rebroadcast_timer = 0.0
                if len(self.players) < self.total_players:
                    self._broadcast_list()

        if (not self.network.is_host
                and self.countdown <= 0
                and len(self.players) < self.total_players):
            self._retry_join_timer += dt
            if self._retry_join_timer >= self.RETRY_JOIN_INTERVAL:
                self._retry_join_timer = 0.0
                self._send_join()
                print(f"[PVP_MM] retry PVP_JOIN "
                      f"({len(self.players)}/{self.total_players})")

        if self.countdown > 0:
            self.countdown_timer += dt
            if self.countdown_timer >= 1.0:
                self.countdown_timer -= 1.0
                self.countdown -= 1

                if self.countdown <= 0 and not self._started:
                    self._started = True
                    if self.network.is_host:
                        self.network.send_to_all(
                            create_message("PVP_START", {})
                        )
                    self._launch_battle()

    # ==================================================================
    def _launch_battle(self):
        if self._on_ready is None:
            return

        my_side = self.players.get(self.my_uuid, {}).get("team_side", "a")

        all_teams = {}
        for u, info in self.players.items():
            all_teams[u] = {
                "name": info["name"],
                "team_side": info.get("team_side", "a"),
                "pokemon": info.get("team_data", []),
            }

        print(f"[PVP_MM] Lançando batalha | meu lado={my_side} | "
              f"times={len(all_teams)}")

        self._on_ready(all_teams, my_side)

    # ==================================================================
    def _go_back(self):
        try:
            self.network.send_to_all(create_message("PVP_LEAVE", {
                "uuid": self.my_uuid,
                "name": self.network.my_name,
            }))
        except Exception:
            pass
        self.network.current_scene_callback = self._prev_callback
        if self._on_back:
            self._on_back()

    # ==================================================================
    # EVENTOS
    # ==================================================================
    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self._go_back()
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.leave_btn.collidepoint(event.pos):
                self._go_back()
                return

    # ==================================================================
    # RENDER
    # ==================================================================
    def render(self, screen):
        screen.fill(COL_BG)

        sm = self.screen_manager
        vx = sm.viewport_x
        vy = sm.viewport_y
        vw = sm.viewport_width
        vh = sm.viewport_height
        cx = vx + vw // 2

        title = self.font_title.render(
            f"SALA PVP — {self.format_name}", True, COL_ACCENT)
        screen.blit(title, title.get_rect(center=(cx, vy + 50)))

        count_txt = f"Jogadores: {len(self.players)}/{self.total_players}"
        color = COL_SUCCESS if len(self.players) >= self.total_players else COL_TEXT_DIM
        s = self.font_h2.render(count_txt, True, color)
        screen.blit(s, s.get_rect(center=(cx, vy + 92)))

        panel = pygame.Rect(vx + 60, vy + 130, vw - 120, vh - 240)
        pygame.draw.rect(screen, COL_PANEL, panel, border_radius=12)
        pygame.draw.rect(screen, COL_BORDER, panel, 1, border_radius=12)

        y = panel.y + 22
        for u, info in self.players.items():
            is_me = (u == self.my_uuid)
            side = info.get("team_side")

            if side == "a":
                side_tag = "  [TIME A]"
                side_color = COL_INFO
            elif side == "b":
                side_tag = "  [TIME B]"
                side_color = COL_WARN
            else:
                side_tag = "  [aguardando...]"
                side_color = COL_TEXT_MUTED

            name_color = COL_SUCCESS if is_me else COL_TEXT
            nm = self.font_h1.render(
                f"{info['name']}{' (você)' if is_me else ''}",
                True, name_color)
            screen.blit(nm, (panel.x + 24, y))

            tag = self.font_small.render(side_tag, True, side_color)
            screen.blit(tag, (panel.x + 24 + nm.get_width() + 8, y + 8))

            team_count = len(info.get("team_data", []))
            sub = self.font_small.render(
                f"{team_count} pokémon", True, COL_TEXT_DIM)
            screen.blit(sub, (panel.x + 24, y + 30))

            y += 58

        if self.countdown > 0:
            frac = self.countdown_timer % 1.0
            scale = 1.0 + 0.25 * math.sin(math.pi * frac)
            num_font = pygame.font.Font(None, int(160 * scale))

            num = num_font.render(str(self.countdown), True, COL_ACCENT)
            screen.blit(num, num.get_rect(center=(cx, vy + vh // 2)))

            sub = self.font_h2.render("Prepare-se!", True, COL_TEXT_DIM)
            screen.blit(sub, sub.get_rect(center=(cx, vy + vh // 2 + 90)))

        mouse = pygame.mouse.get_pos()
        hover = self.leave_btn.collidepoint(mouse)
        bg = COL_BTN_DANGER_H if hover else COL_BTN_DANGER
        pygame.draw.rect(screen, bg, self.leave_btn, border_radius=10)
        pygame.draw.rect(screen, (200, 200, 200), self.leave_btn, 1, border_radius=10)
        bt = self.font.render("Sair", True, COL_TEXT)
        screen.blit(bt, bt.get_rect(center=self.leave_btn.center))