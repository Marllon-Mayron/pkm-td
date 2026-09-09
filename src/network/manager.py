# src/network/manager.py

import queue
import threading
import random
import string
from src.network.server import TradeServer
from src.network.client import TradeClient
from src.network.protocol import create_message, MSG_TYPES

class NetworkManager:
    def __init__(self):
        self.is_host = False
        self.server = None
        self.client = None
        self.incoming_queue = queue.Queue()
        self.connected_players = {}
        self.my_name = "Jogador"
        self.opponent_name = None
        self.connection_established = False
        self.room_code = None  # código gerado pelo host

    def set_name(self, name):
        self.my_name = name

    def start_host(self, port=12345):
        self.is_host = True
        self.room_code = self._generate_room_code()
        self.server = TradeServer(
            host='0.0.0.0',
            port=port,
            on_message=self._on_server_message,
            on_connect=self._on_server_connect,
            on_disconnect=self._on_server_disconnect
        )
        self.server.start()
        return True

    def _generate_room_code(self):
        return ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))

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
        self.incoming_queue.put((msg, conn))

    def _on_server_connect(self, conn, addr):
        self.connection_established = True
        # Envia handshake com código da sala
        self.server.send_to_client(conn, create_message("HANDSHAKE", {"role": "host", "room_code": self.room_code}))

    def _on_server_disconnect(self, conn, addr):
        self.connection_established = False
        # Avisa a cena
        self.incoming_queue.put(({"type": "DISCONNECT"}, None))

    def _on_client_message(self, msg):
        self.incoming_queue.put((msg, None))

    def _on_client_disconnect(self):
        self.connection_established = False
        self.incoming_queue.put(({"type": "DISCONNECT"}, None))

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