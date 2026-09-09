# src/network/server.py

import socket
import threading
import json
import time
from src.network.protocol import create_message

# src/network/server.py (trecho modificado)

class TradeServer(threading.Thread):
    def __init__(self, host='0.0.0.0', port=12345, on_message=None, on_connect=None, on_disconnect=None, max_clients=2):
        super().__init__(daemon=True)
        self.host = host
        self.port = port
        self.max_clients = max_clients
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.clients = []  # lista de (conn, addr)
        self.running = False
        self.on_message = on_message
        self.on_connect = on_connect
        self.on_disconnect = on_disconnect
        self.lock = threading.Lock()

    def run(self):
        try:
            self.socket.bind((self.host, self.port))
            self.socket.listen(self.max_clients)
            self.running = True
            print(f"[SERVER] Aguardando até {self.max_clients} conexões em {self.host}:{self.port}")
            while self.running:
                try:
                    conn, addr = self.socket.accept()
                    if len(self.clients) >= self.max_clients:
                        print(f"[SERVER] Máximo de clientes atingido, recusando {addr}")
                        conn.close()
                        continue
                    print(f"[SERVER] Cliente conectado: {addr}")
                    with self.lock:
                        self.clients.append((conn, addr))
                    if self.on_connect:
                        self.on_connect(conn, addr)
                    client_thread = threading.Thread(target=self._handle_client, args=(conn, addr), daemon=True)
                    client_thread.start()
                except socket.error:
                    break
        except Exception as e:
            print(f"[SERVER] Erro: {e}")
        finally:
            self.stop()

    def _handle_client(self, conn, addr):
        while self.running:
            try:
                data = conn.recv(4096).decode('utf-8')
                if not data:
                    break
                # Pode receber múltiplas mensagens separadas por \n
                for line in data.split('\n'):
                    if line.strip():
                        msg = json.loads(line)
                        if self.on_message:
                            self.on_message(msg, conn, addr)
            except json.JSONDecodeError:
                pass
            except Exception as e:
                print(f"[SERVER] Erro ao receber: {e}")
                break
        conn.close()
        with self.lock:
            if (conn, addr) in self.clients:
                self.clients.remove((conn, addr))
        if self.on_disconnect:
            self.on_disconnect(conn, addr)

    def send_to_client(self, conn, msg):
        try:
            conn.send((json.dumps(msg) + '\n').encode('utf-8'))
        except:
            pass

    def send_to_all(self, msg):
        with self.lock:
            for conn, _ in self.clients:
                self.send_to_client(conn, msg)

    def stop(self):
        self.running = False
        try:
            self.socket.close()
        except:
            pass
        # Fecha conexões ativas
        with self.lock:
            for conn, _ in self.clients:
                try:
                    conn.close()
                except:
                    pass
            self.clients.clear()