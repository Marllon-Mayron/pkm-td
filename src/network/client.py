# src/network/client.py

import socket
import json
import threading

from src.network.protocol import create_message


class TradeClient:
    """Cliente TCP que se conecta ao TradeServer."""

    def __init__(self, host='localhost', port=12345, on_message=None, on_disconnect=None):
        self.host = host
        self.port = port
        self.socket = None
        self.connected = False
        self.on_message = on_message
        self.on_disconnect = on_disconnect
        self.receive_thread = None
        self.lock = threading.Lock()
        self._disconnect_notified = False

        # ★ Handshake
        self._handshake_event = threading.Event()
        self._handshake_accepted = False
        self._handshake_reason = ""

    @property
    def rejection_reason(self):
        return self._handshake_reason

    def connect(self, wait_for_handshake=True, timeout=5.0):
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(5)
            self.socket.connect((self.host, self.port))
            self.socket.settimeout(None)

            self.connected = True
            self._disconnect_notified = False
            self._handshake_event.clear()
            self._handshake_accepted = False
            self._handshake_reason = ""

            print(f"[CLIENT] Conectado ao servidor {self.host}:{self.port}")
            self.receive_thread = threading.Thread(
                target=self._receive_loop, daemon=True
            )
            self.receive_thread.start()

            # ★ Aguarda o HANDSHAKE (aceito ou recusado)
            if wait_for_handshake:
                if not self._handshake_event.wait(timeout):
                    print("[CLIENT] Timeout aguardando handshake.")
                    self._handshake_reason = "O servidor nao respondeu."
                    self.disconnect()
                    return False
                if not self._handshake_accepted:
                    print(f"[CLIENT] Conexao recusada: {self._handshake_reason}")
                    self.disconnect()
                    return False

            return True
        except Exception as e:
            print(f"[CLIENT] Falha ao conectar: {e}")
            return False

    def _receive_loop(self):
        buffer = ""
        while self.connected:
            try:
                data = self.socket.recv(4096).decode('utf-8')
                if not data:
                    break
                buffer += data
                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    if line.strip():
                        try:
                            msg = json.loads(line)
                            msg_type = msg.get("type")

                            # ★ Intercepta HANDSHAKE (não vai para a cena)
                            if msg_type == "HANDSHAKE":
                                payload = msg.get("payload", {})
                                self._handshake_accepted = payload.get("accepted", True)
                                self._handshake_reason = payload.get("reason", "")
                                self._handshake_event.set()
                                continue

                            if self.on_message:
                                self.on_message(msg)
                        except json.JSONDecodeError as e:
                            print(f"[CLIENT] JSON inválido: {e}")
            except Exception as e:
                print(f"[CLIENT] Erro ao receber: {e}")
                break
        self.disconnect()

    def send(self, msg):
        if self.connected and self.socket:
            with self.lock:
                try:
                    self.socket.send((json.dumps(msg) + '\n').encode('utf-8'))
                    return True
                except Exception as e:
                    print(f"[CLIENT] Falha ao enviar: {e}")
                    return False
        return False

    def disconnect(self):
        if self.connected:
            self.connected = False
            if self.socket:
                try:
                    self.socket.close()
                except Exception:
                    pass
            if self.on_disconnect and not self._disconnect_notified:
                self._disconnect_notified = True
                self.on_disconnect()