# src/network/manager.py

import queue
import socket

from src.config.global_settings import DEBUG_MODE
from src.network.server import TradeServer
from src.network.client import TradeClient
from src.network.protocol import create_message


_RELAY_TYPES = {
    "CHAT_MESSAGE",
    "TRADE_REQUEST",
    "TRADE_RESPONSE",
    "TRADE_OFFER",
    "TRADE_CANCEL",
    "TRADE_ACCEPT",
    "TRADE_DECLINE",
    "TRADE_CONFIRM",
    "TRADE_COMPLETE",
    # ===== RAID =====
    "RAID_JOIN",
    "RAID_PLAYER_LIST",
    "RAID_START_SELECTION",
    "RAID_TEAM_SUBMIT",
    "RAID_TEAM_UPDATE",
    "RAID_PLAYER_READY",
    "RAID_COUNTDOWN",
    "RAID_START",
    "RAID_LEAVE",
    "RAID_CANCEL",
    # INRAID
    "RAID_PLACEMENT",
    "RAID_BOSS_SPAWN",
    "RAID_BOSS_SYNC",
    "RAID_BOSS_DEAD",
    "RAID_POKEMON_STATE",
    "RAID_ATTACK_BOSS",
    "RAID_POKEMON_DAMAGE",
    "RAID_ALL_DEFEATED",
    "RAID_WEATHER_CHANGE",
    "RAID_BOSS_ATTACK",
    "RAID_POKEMON_ATTACK",
    "RAID_RETURN_LOBBY",
    # =================

}
_ARENA_TYPES = {
    "ARENA_JOIN", "ARENA_PLAYER_LIST", "ARENA_START", "ARENA_LEAVE",
    "ARENA_PLACEMENT", "ARENA_POKEMON_STATE", "ARENA_POKEMON_ATTACK",
    "ARENA_POKEMON_DAMAGE", "ARENA_END",
}

_RELAY_TYPES = _RELAY_TYPES | _ARENA_TYPES

_PVP_TYPES = {
    "PVP_JOIN", "PVP_PLAYER_LIST", "PVP_SELECT_FORMAT",
    "PVP_TEAM_SUBMIT", "PVP_READY", "PVP_START_SELECTION",
    "PVP_COUNTDOWN", "PVP_START", "PVP_LEAVE", "PVP_CANCEL",
    "PVP_PLACEMENT", "PVP_POKEMON_STATE", "PVP_POKEMON_ATTACK",
    "PVP_POKEMON_DAMAGE", "PVP_END", "PVP_TEAM_ASSIGN",
    "PVP_WEATHER_CHANGE",
    "PVP_POKEMON_REMOVE",
    "PVP_DAY_NIGHT",
}
_RELAY_TYPES = _RELAY_TYPES | _PVP_TYPES

_LOOPBACK_IPS = {"127.0.0.1", "localhost", "::1"}


class NetworkManager:
    """Abstrai servidor/cliente e expõe uma API unificada para as cenas."""

    def __init__(self):
        self.is_host = False
        self.server = None
        self.client = None
        self.incoming_queue = queue.Queue()
        self.players = {}
        self.players_list = []
        self.my_name = "Jogador"
        self.my_uuid = "unknown"
        self.opponent_name = None
        self.opponent_uuid = None
        self.connection_established = False
        self.current_scene_callback = None

        self.local_ip = self._detect_local_ip()
        self.remote_ips = []
        self._last_rejection_reason = ""

        # False (padrão): não permite duas conexões do mesmo IP.
        # True: útil apenas para TESTES locais na mesma máquina.
        self.allow_same_ip_players = DEBUG_MODE

        self.local_ip = self._detect_local_ip()
        self.remote_ips = []
        self._last_rejection_reason = ""

    def set_name(self, name):
        self.my_name = name

    def set_uuid(self, uuid_str):
        """Define o UUID do jogador local (chamado pelo menu/lobby)."""
        self.my_uuid = uuid_str or "unknown"
    # ------------------------------------------------------------------
    # Detecção de IP / validação
    # ------------------------------------------------------------------
    def _detect_local_ip(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"

    def _is_local_ip(self, ip):
        if not ip:
            return False
        ip = ip.strip().lower()
        if ip in _LOOPBACK_IPS:
            return True
        return ip == self.local_ip

    def is_opponent_same_machine(self):
        return any(self._is_local_ip(ip) for ip in self.remote_ips)

    def can_trade(self):
        """Segurança extra: bloqueia trocas entre mesmo IP se a flag estiver off."""
        if self.allow_same_ip_players:
            return True, None
        if self.is_opponent_same_machine():
            return False, "Troca bloqueada: o oponente esta na mesma maquina."
        return True, None

    def set_allow_same_ip_players(self, allow: bool):
        self.allow_same_ip_players = bool(allow)

    def get_last_rejection_reason(self):
        return self._last_rejection_reason

    # ------------------------------------------------------------------
    # Configuração
    # ------------------------------------------------------------------
    def set_name(self, name):
        self.my_name = name

    # ------------------------------------------------------------------
    # Host / cliente
    # ------------------------------------------------------------------
    def start_host(self, port=12345):
        self.is_host = True
        self.remote_ips = []
        self.server = TradeServer(
            host='0.0.0.0',
            port=port,
            on_message=self._on_server_message,
            on_connect=self._on_server_connect,
            on_disconnect=self._on_server_disconnect,
            max_clients=5,
        )
        self.server.start()
        self.players_list = [self.my_name]
        return True

    def connect_to_host(self, host='localhost', port=12345):
        self.is_host = False
        self.remote_ips = [host]
        self._last_rejection_reason = ""
        self.client = TradeClient(
            host=host,
            port=port,
            on_message=self._on_client_message,
            on_disconnect=self._on_client_disconnect,
        )
        ok = self.client.connect()
        if not ok:
            self._last_rejection_reason = self.client.rejection_reason or ""
        return ok

    # ------------------------------------------------------------------
    # Callbacks do servidor
    # ------------------------------------------------------------------
    def _get_full_player_list(self):
        """
        Retorna a lista completa de jogadores como dicts {name, uuid}.
        O host inclui a si mesmo + os clientes conectados.
        """
        if not self.is_host:
            return self.players_list

        players = [{"name": self.my_name, "uuid": self.my_uuid}]
        for conn, info in self.players.items():
            if isinstance(info, dict):
                players.append({"name": info.get("name", "?"), "uuid": info.get("uuid", "unknown")})
            else:
                # Compatibilidade retroativa: info era só string (nome)
                players.append({"name": info, "uuid": "unknown"})
        return players

    def _on_server_connect(self, conn, addr):
        """
        Retorna:
          True  -> aceita conexão
          False -> recusa conexão (fecha o socket e remove da lista)
        """
        client_ip = addr[0] if addr else None
        print(f"[SERVER] Validando conexao de {addr} "
              f"(ip={client_ip}, allow_same_ip={self.allow_same_ip_players})")

        if not self.allow_same_ip_players:
            # 1) Mesma máquina que o host?
            if self._is_local_ip(client_ip):
                reason = "Conexao recusada: voce ja esta jogando nesta maquina."
                print(f"[SERVER] {reason}")
                self.server.send_to_client(conn, create_message(
                    "HANDSHAKE",
                    {"role": "host", "accepted": False, "reason": reason},
                ))
                return False

            # 2) IP já conectado (duplicado)?
            existing_ips = [
                c_addr[0]
                for c, c_addr in self.server.clients
                if c is not conn
            ]
            if client_ip in existing_ips:
                reason = "Conexao recusada: ja existe um jogador deste IP."
                print(f"[SERVER] {reason}")
                self.server.send_to_client(conn, create_message(
                    "HANDSHAKE",
                    {"role": "host", "accepted": False, "reason": reason},
                ))
                return False

        # Aceito
        if client_ip and client_ip not in self.remote_ips:
            self.remote_ips.append(client_ip)

        self.server.send_to_client(conn, create_message(
            "HANDSHAKE", {"role": "host", "accepted": True}
        ))
        self._broadcast_player_list()
        return True

    def _on_server_message(self, msg, conn, addr):
        msg_type = msg.get("type")

        if msg_type == "PLAYER_INFO":
            payload = msg.get("payload", {})
            name = payload.get("name", "Desconhecido")
            uuid_str = payload.get("uuid", "unknown")

            current = self.players.get(conn)
            if not isinstance(current, dict) or current.get("name") != name or current.get("uuid") != uuid_str:
                self.players[conn] = {"name": name, "uuid": uuid_str}
                self.players_list = self._get_full_player_list()
                print(f"[SERVER] Jogador '{name}' (UUID: {uuid_str}) registrado. Total: {len(self.players)}")
                self._broadcast_player_list()

        if msg_type in _RELAY_TYPES and self.server:
            self.server.send_to_others(conn, msg)

        self.incoming_queue.put((msg, conn))

    def _on_server_disconnect(self, conn, addr):
        if conn in self.players:
            info = self.players.pop(conn)
            name = info.get("name", "?") if isinstance(info, dict) else info
            self.players_list = self._get_full_player_list()
            print(f"[SERVER] Jogador '{name}' desconectou.")
            if self.server:
                self.server.send_to_all(create_message("DISCONNECT", {"name": name}))
            self._broadcast_player_list()

        client_ip = addr[0] if addr else None
        if client_ip in self.remote_ips:
            still_here = False
            if self.server:
                still_here = any(
                    c_addr[0] == client_ip for _, c_addr in self.server.clients
                )
            if not still_here:
                self.remote_ips.remove(client_ip)

    # ------------------------------------------------------------------
    # Callbacks do cliente
    # ------------------------------------------------------------------
    def _on_client_message(self, msg):
        msg_type = msg.get("type")

        if msg_type == "PLAYER_LIST":
            players_data = msg.get("payload", {}).get("players", [])

            # Normaliza para lista de dicts {name, uuid}
            normalized = []
            if isinstance(players_data, list):
                for entry in players_data:
                    if isinstance(entry, dict):
                        normalized.append({
                            "name": entry.get("name", "?"),
                            "uuid": entry.get("uuid", "unknown"),
                        })
                    else:
                        # Compatibilidade: entradas antigas eram só strings
                        normalized.append({"name": str(entry), "uuid": "unknown"})

            self.players_list = normalized

            # Descobre o oponente (primeiro da lista cujo name != my_name)
            self.opponent_name = None
            self.opponent_uuid = None
            for entry in normalized:
                if entry["name"] != self.my_name:
                    self.opponent_name = entry["name"]
                    self.opponent_uuid = entry["uuid"]
                    break

            print(f"[CLIENT] Lista de jogadores: {[p['name'] for p in normalized]}")
        self.incoming_queue.put((msg, None))

    def _on_client_disconnect(self):
        self.connection_established = False
        print("[CLIENT] Desconectado do servidor")

    # ------------------------------------------------------------------
    # Envio
    # ------------------------------------------------------------------
    def _broadcast_player_list(self):
        if self.is_host and self.server:
            players = self._get_full_player_list()
            self.players_list = players
            self.server.send_to_all(create_message("PLAYER_LIST", {"players": players}))

    def send_to_all(self, msg):
        if self.is_host and self.server:
            self.server.send_to_all(msg)
        elif self.client:
            self.client.send(msg)

    def send_to_client(self, conn, msg):
        if self.is_host and self.server:
            self.server.send_to_client(conn, msg)

    # ------------------------------------------------------------------
    # Encerramento / estado
    # ------------------------------------------------------------------
    def stop(self):
        if self.server:
            self.server.stop()
            self.server = None
        if self.client:
            self.client.disconnect()
            self.client = None
        self.connection_established = False
        self.players = {}
        self.players_list = []
        self.remote_ips = []
        self.opponent_name = None
        self.opponent_uuid = None

    def is_connected(self):
        if self.is_host:
            return self.server is not None and self.server.running and len(self.server.clients) > 0
        return self.client is not None and self.client.connected