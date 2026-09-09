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
        self.players = {}  # Dicionário de jogadores {conn_id: name}
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
        # Processa mensagens do servidor
        msg_type = msg.get("type")

        # Se for PLAYER_INFO, atualiza a lista de jogadores
        if msg_type == "PLAYER_INFO":
            name = msg.get("payload", {}).get("name", "Desconhecido")
            # Armazena o nome do jogador pela conexão
            self.players[conn] = name
            print(f"[SERVER] Jogador '{name}' registrado. Total: {len(self.players)}")
            # Envia lista atualizada para todos
            self._broadcast_player_list()

        # Coloca na fila para a UI processar
        self.incoming_queue.put((msg, conn))

    def _on_server_connect(self, conn, addr):
        # Envia handshake para o cliente
        self.server.send_to_client(conn, create_message("HANDSHAKE", {"role": "host"}))

    def _on_server_disconnect(self, conn, addr):
        # Remove jogador da lista
        if conn in self.players:
            name = self.players.pop(conn)
            print(f"[SERVER] Jogador '{name}' desconectou.")
            # Notifica todos sobre a nova lista
            self._broadcast_player_list()

    def _on_client_message(self, msg):
        # Processa mensagens do cliente
        msg_type = msg.get("type")

        # Se for PLAYER_LIST, atualiza a lista local
        if msg_type == "PLAYER_LIST":
            players_data = msg.get("payload", {}).get("players", {})
            # Converte de dict para lista de nomes
            self.players = list(players_data.values())
            print(f"[CLIENT] Lista de jogadores atualizada: {self.players}")

        # Coloca na fila para a UI processar
        self.incoming_queue.put((msg, None))

    def _on_client_disconnect(self):
        self.connection_established = False
        print("[CLIENT] Desconectado do servidor")

    def _broadcast_player_list(self):
        """Envia a lista de jogadores para todos os clientes"""
        # Converte para um formato serializável (dict com chaves string)
        players_dict = {}
        for conn, name in self.players.items():
            # Usa o id da conexão como chave
            players_dict[str(id(conn))] = name

        msg = create_message("PLAYER_LIST", {"players": players_dict})
        if self.is_host and self.server:
            self.server.send_to_all(msg)
            print(f"[SERVER] Lista de jogadores enviada: {list(players_dict.values())}")

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