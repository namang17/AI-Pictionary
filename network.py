import socket
import threading
import json
import time

class PictionaryNetwork:
    def __init__(self, callback):
        self.callback = callback # Callback for received messages: function(dict)
        self.socket = None
        self.conn = None # Used by client
        self.clients = [] # Used by server
        self.is_server = False
        self.running = True

    def start_server(self, port=5555):
        self.is_server = True
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind(('0.0.0.0', port))
        self.socket.listen(10)
        
        def accept_clients():
            while self.running:
                try:
                    self.socket.settimeout(1.0)
                    conn, addr = self.socket.accept()
                    self.clients.append(conn)
                    threading.Thread(target=self.receive_loop, args=(conn, addr), daemon=True).start()
                    self.callback({'type': 'CLIENT_CONNECTED', 'addr': addr})
                except socket.timeout:
                    continue
                except Exception as e:
                    if self.running: print(f"Server accept error: {e}")
        
        threading.Thread(target=accept_clients, daemon=True).start()

    def connect_to_server(self, ip, port=5555):
        self.is_server = False
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.settimeout(3.0)
        try:
            self.socket.connect((ip, port))
            self.socket.settimeout(None)
            self.conn = self.socket
            threading.Thread(target=self.receive_loop, args=(self.conn,), daemon=True).start()
            self.callback({'type': 'CONNECTED_TO_SERVER'})
            return True
        except Exception as e:
            print(f"Connection error: {e}")
            return False

    def receive_loop(self, conn, addr=None):
        client_id = f"{addr[0]}:{addr[1]}" if addr else "client"
        buffer = ""
        while self.running:
            try:
                data = conn.recv(4096).decode('utf-8')
                if not data:
                    break
                buffer += data
                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    if line.strip():
                        try:
                            msg = json.loads(line)
                            if self.is_server:
                                msg['_client_id'] = client_id
                            self.callback(msg)
                        except json.JSONDecodeError:
                            print(f"Failed to decode message: {line}")
            except socket.timeout:
                continue
            except Exception as e:
                break
        
        if self.is_server:
            if conn in self.clients:
                self.clients.remove(conn)
                if self.running:
                    self.callback({'type': 'CLIENT_DISCONNECTED', '_client_id': client_id})
        else:
            self.conn = None
            if self.running:
                self.callback({'type': 'DISCONNECTED_FROM_SERVER'})

    def send(self, data):
        msg = json.dumps(data) + '\n'
        encoded_msg = msg.encode('utf-8')
        
        if self.is_server:
            # Broadcast to all connected clients
            dead_clients = []
            for c in self.clients:
                try:
                    c.sendall(encoded_msg)
                except Exception:
                    dead_clients.append(c)
            for c in dead_clients:
                if c in self.clients:
                    self.clients.remove(c)
        else:
            # Client sends to server
            if self.conn:
                try:
                    self.conn.sendall(encoded_msg)
                except Exception as e:
                    print(f"Send error: {e}")
                    self.conn = None
                    self.callback({'type': 'DISCONNECTED_FROM_SERVER'})

    def close(self):
        self.running = False
        if self.conn:
            try: self.conn.close()
            except: pass
        for c in self.clients:
            try: c.close()
            except: pass
        self.clients.clear()
        if self.socket:
            try: self.socket.close()
            except: pass
