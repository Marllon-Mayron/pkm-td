# src/network/manager.py

import queue
import threading
from src.network.server import TradeServer
from src.network.client import TradeClient
from src.network.protocol import create_message, MSG_TYPES


class NetworkManager:
    def __init__(self):
        self.is_host = False
        self.server = None
        self.client = None
        self.incoming_queue = queue.Queue()
        self.players = {}  # {conn: name}
        self.players_list = []  # Lista simples de nomes para exibição
        self.my_name = "Jogador"
        self.opponent_name = None
        self.connection_established = False
        self.current_scene_callback = None

    def set_name(self, name):
        self.my_name = name

    def start_host(self, port=12345):
        self.is_host = True
        self.server = TradeServer(
            host='0.0.0.0',
            port=port,
            on_message=self._on_server_message,
            on_connect=self._on_server_connect,
            on_disconnect=self._on_server_disconnect,
            max_clients=2
        )
        self.server.start()
        return True

    def connect_to_host(self, host='localhost', port=12345):
        self.is_host = False
        self.client = TradeClient(
            host=host,
            port=port,
            on_message=self._on_client_message,
            on_disconnect=self._on_client_disconnect
        )
        return self.client.connect()

    def _on_server_message(self, msg, conn, addr):
        msg_type = msg.get("type")

        if msg_type == "PLAYER_INFO":
            name = msg.get("payload", {}).get("name", "Desconhecido")
            self.players[conn] = name
            self.players_list = list(self.players.values())
            print(f"[SERVER] Jogador '{name}' registrado. Total: {len(self.players)}")
            self._broadcast_player_list()

        self.incoming_queue.put((msg, conn))

    def _on_server_connect(self, conn, addr):
        self.server.send_to_client(conn, create_message("HANDSHAKE", {"role": "host"}))

    def _on_server_disconnect(self, conn, addr):
        if conn in self.players:
            name = self.players.pop(conn)
            self.players_list = list(self.players.values())
            print(f"[SERVER] Jogador '{name}' desconectou.")
            self._broadcast_player_list()

    def _on_client_message(self, msg):
        msg_type = msg.get("type")

        if msg_type == "PLAYER_LIST":
            players_data = msg.get("payload", {}).get("players", [])
            # Pode vir como lista ou dicionário - tratamos ambos
            if isinstance(players_data, dict):
                self.players_list = list(players_data.values())
            else:
                self.players_list = players_data
            print(f"[CLIENT] Lista de jogadores atualizada: {self.players_list}")

        self.incoming_queue.put((msg, None))

    def _on_client_disconnect(self):
        self.connection_established = False
        print("[CLIENT] Desconectado do servidor")

    def _broadcast_player_list(self):
        """Envia a lista de jogadores para todos os clientes"""
        # Envia como uma LISTA simples
        msg = create_message("PLAYER_LIST", {"players": self.players_list})
        if self.is_host and self.server:
            self.server.send_to_all(msg)
            print(f"[SERVER] Lista enviada: {self.players_list}")

    def send_to_all(self, msg):
        if self.is_host and self.server:
            self.server.send_to_all(msg)
        elif self.client:
            self.client.send(msg)

    def send_to_client(self, conn, msg):
        if self.is_host and self.server:
            self.server.send_to_client(conn, msg)

    def stop(self):
        if self.server:
            self.server.stop()
        if self.client:
            self.client.disconnect()
        self.connection_established = False

    def is_connected(self):
        if self.is_host:
            return self.server is not None and self.server.running and len(self.server.clients) > 0
        else:
            return self.client is not None and self.client.connected