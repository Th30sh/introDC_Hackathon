import sys
import time
sys.path.append('../')

from client import Client
from util import GameClient, Stats
from shared.exceptions import HackathonException


def main():
    print("Client application started...")
    print("Looking for server...")
    
    # Initialize client and stats
    client = Client()
    stats = Stats()
    
    try:
        client.listen_for_offers()
    except KeyboardInterrupt:
        return
    
    # Get team name
    team_name = GameClient.get_user_input("Enter your team name: ") or "TeamPython"
    game_client = GameClient(team_name, stats)
    
    while True:
        try:
            # Check if user wants to play
            if not game_client.check_start_game():
                break
            
            # Get number of rounds
            num_rounds = GameClient.get_num_rounds()
            
            # Connect and play all rounds
            if client.connect():
                client.run(lambda sock: game_client.play_session(sock, num_rounds))
            else:
                print("Failed to connect. Retrying discovery...")
                client.listen_for_offers()

        except KeyboardInterrupt:
            print("\nGame interrupted.")
            if stats.rounds_played > 0:
                stats.print_summary(team_name)
            break
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(1)
    
    print("Exiting...")


if __name__ == "__main__":
    main()