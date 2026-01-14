from server import Server
from utils import Game

def main():
    srv = Server(tcp_port=12000, server_name="BlackjackMaster")
    srv.start()
    srv.run(Game.start)

if __name__ == "__main__":
    main()