import socket
import threading
import time
import sys

sys.path.append('../')

from shared.protocol import *
from shared.exceptions import NetworkException

class Server:
    def __init__(self, tcp_port=12000, server_name="MysticDealer"):
        self.tcp_port = tcp_port
        self.server_name = server_name
        self.tcp_socket = None
        self.udp_socket = None
        self.running = True
        self.broadcast_thread = None

    def start(self):
        """Initializes sockets and starts threads."""
        try:
            # 1. Setup TCP
            self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.tcp_socket.bind(('', self.tcp_port))
            self.tcp_socket.listen(5)
            
            # 2. Setup UDP Broadcast
            self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            
            # 3. Start Broadcast Thread
            self.broadcast_thread = threading.Thread(target=self._broadcast_offers, daemon=True)
            self.broadcast_thread.start()
            
            print(f"Server started, listening on IP address {self._get_ip()}")
            
        except Exception as e:
            raise NetworkException(f"Failed to start server: {e}")

    def _get_ip(self):
        # Helper to find local IP
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return "127.0.0.1"

    def _broadcast_offers(self):
        """Background thread sending UDP offers."""
        print("Server started broadcasting offers...")
        packet = pack_offer(self.tcp_port, self.server_name)
        while self.running:
            try:
                self.udp_socket.sendto(packet, ('<broadcast>', UDP_PORT))
                time.sleep(1)
            except Exception as e:
                print(f"Broadcast error: {e}")

    def run(self, game_callback):
        """Main loop: Accepts TCP connections and spawns threads."""
        try:
            while self.running:
                client_sock, addr = self.tcp_socket.accept()
                print(f"Connection from {addr} established!")
                
                # Handle client in separate thread
                client_thread = threading.Thread(
                    target=self._handle_client, 
                    args=(client_sock, game_callback)
                )
                client_thread.start()
        except KeyboardInterrupt:
            self.close()

    def _handle_client(self, conn, callback):
        """Wrapper to safely run the game logic and close socket."""
        try:
            callback(conn)
        except Exception as e:
            print(f"Error handling client: {e}")
        finally:
            conn.close()
            print("Connection closed.")

    def close(self):
        self.running = False
        if self.tcp_socket: self.tcp_socket.close()
        if self.udp_socket: self.udp_socket.close()
        print("Server offline.")