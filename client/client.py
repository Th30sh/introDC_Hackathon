import socket
import sys

sys.path.append('../')
from shared.protocol import *
from shared.exceptions import NetworkException

class Client:
    def __init__(self):
        self.tcp_socket = None
        self.server_ip = None
        self.server_port = None
        self.status = 0

    def listen_for_offers(self):
        """Blocking: waits for UDP offer."""
        print("Client started, listening for offer requests...")
        udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        try:
            udp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        except AttributeError:
            pass 
            
        udp_sock.bind(('', UDP_PORT))

        while True:
            data, addr = udp_sock.recvfrom(1024)
            try:
                port, name = unpack_offer(data)
                self.server_ip = addr[0]
                self.server_port = port
                print(f"Received offer from {name} at {self.server_ip}:{self.server_port}")
                break
            except ProtocolException:
                continue # Ignore bad packets
        udp_sock.close()

    def connect(self):
        """Connects to the discovered server via TCP."""
        if not self.server_ip or not self.server_port:
            raise NetworkException("No server found via UDP yet.")
        
        try:
            self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.tcp_socket.connect((self.server_ip, self.server_port))
            return True
        except Exception as e:
            self.status = f"Connection failed: {e}"
            return False

    def run(self, callback):
        """Runs the game session."""
        if self.tcp_socket:
            try:
                callback(self.tcp_socket)
            except Exception as e:
                # Re-raise so main.py can handle the error (print it and loop back)
                raise e 
            finally:
                self.close()

    def close(self):
        if self.tcp_socket:
            self.tcp_socket.close()