# src/network/client.py

import socket
import json
import threading
import time
from src.network.protocol import create_message

class TradeClient:
    def __init__(self, host='localhost', port=12345, on_message=None, on_disconnect=None):
        self.host = host
        self.port = port
        self.socket = None
        self.connected = False
        self.on_message = on_message
        self.on_disconnect = on_disconnect
        self.receive_thread = None
        self.lock = threading.Lock()

    def connect(self):
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(5)  # timeout para conexão
            self.socket.connect((self.host, self.port))
            self.socket.settimeout(None)
            self.connected = True
            print(f"[CLIENT] Conectado ao servidor {self.host}:{self.port}")
            self.receive_thread = threading.Thread(target=self._receive_loop, daemon=True)
            self.receive_thread.start()
            return True
        except Exception as e:
            print(f"[CLIENT] Falha ao conectar: {e}")
            return False

    def _receive_loop(self):
        while self.connected:
            try:
                data = self.socket.recv(4096).decode('utf-8')
                if not data:
                    break
                for line in data.split('\n'):
                    if line.strip():
                        msg = json.loads(line)
                        if self.on_message:
                            self.on_message(msg)
            except json.JSONDecodeError:
                pass
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
                except:
                    return False
        return False

    def disconnect(self):
        if self.connected:
            self.connected = False
            if self.socket:
                try:
                    self.socket.close()
                except:
                    pass
            if self.on_disconnect:
                self.on_disconnect()