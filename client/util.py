import sys
from time import sleep
sys.path.append('../')

from shared.protocol import *
from shared.exceptions import HackathonException


class Stats:
    """Manages game statistics."""
    
    def __init__(self):
        self.wins = 0
        self.losses = 0
        self.ties = 0
        self.rounds_played = 0
    
    def add_win(self):
        """Records a win."""
        self.wins += 1
        self.rounds_played += 1
    
    def add_loss(self):
        """Records a loss."""
        self.losses += 1
        self.rounds_played += 1
    
    def add_tie(self):
        """Records a tie."""
        self.ties += 1
        self.rounds_played += 1
    
    def get_win_rate(self):
        """Calculates win rate percentage."""
        if self.rounds_played > 0:
            return (self.wins / self.rounds_played) * 100
        return 0.0
    
    def print_summary(self, team_name):
        """Prints the game session summary."""
        print("\n" + "="*40)
        print("       GAME SESSION SUMMARY")
        print("="*40)
        
        print(f" {'Total Rounds Played:':<25}{self.rounds_played:>13}")
        wins_label = f"{team_name} Won:"
        print(f" {wins_label:<25}{self.wins:>13}")
        print(f" {'Dealer Won:':<25}{self.losses:>13}")
        print(f" {'Ties:':<25}{self.ties:>13}")
        
        win_rate = self.get_win_rate()
        print(f" {'Win Rate:':<25}{f'{win_rate:.2f}%':>13}")
        print("="*40 + "\n")
    
    def print_current_stats(self):
        """Prints current stats between rounds."""
        print(f"\n[Current Stats: Wins: {self.wins} | Losses: {self.losses} | Ties: {self.ties}]")


class GameClient:
    """Handles client-side game logic."""
    
    def __init__(self, team_name, stats):
        self.team_name = team_name
        self.stats = stats
    
    @staticmethod
    def get_user_input(prompt, args=None, error_msg=""):
        """Gets user input safely."""
        try:
            while True:
                usr_input = input(prompt)
                if args:
                    if usr_input.lower() in args:
                        return usr_input
                    else:
                        if error_msg != "":    
                            print(error_msg)
                        else:   
                            print(f"Invalid input. Please enter one of: {', '.join(args)}")
                else: 
                    return usr_input
        
        except EOFError:
            raise HackathonException("No input provided (EOF).")
        except KeyboardInterrupt:
            raise HackathonException("User interrupted input.")
    
    @staticmethod
    def get_num_rounds():
        """Asks user for number of rounds (1-255)."""
        while True:
            try:
                num_str = GameClient.get_user_input("How many rounds do you want to play? (1-255): ")
                num = int(num_str)
                if 1 <= num <= 255:
                    return num
                else:
                    print("Please enter a number between 1 and 255.")
            except ValueError:
                print("Invalid input. Please enter a number.")
    
    def check_start_game(self):
        """Checks if user wants to start/continue playing."""
        if self.stats.rounds_played == 0:
            user_input = self.get_user_input(
                f"Hi {self.team_name}! do you want to start a \"Black Jack\" game? (y/n): ", 
                ['y', 'n', 'yes', 'no']
            ).lower()
        else:
            self.stats.print_summary(self.team_name)
            user_input = self.get_user_input(
                f"Do you want to play again? (y/n): ", 
                ['y', 'n', 'yes', 'no']
            ).lower()
        
        if user_input == 'n' or user_input == 'no':
            if self.stats.rounds_played == 0:
                print("Ok, Goodbye!")
            return False
        
        return True
    
    @staticmethod
    def get_card_value(rank):
        """Helper to get blackjack value from rank."""
        if rank == 1: return 11  # Ace initially 11
        if rank >= 11: return 10  # Face cards
        return rank
    
    @staticmethod
    def calculate_score(current_score, aces, rank):
        """Updates score and handles Ace logic (11 -> 1)."""
        val = GameClient.get_card_value(rank)
        if val == 11: aces += 1
        current_score += val
        
        # If bust, try to convert Aces from 11 to 1
        while current_score > 21 and aces > 0:
            current_score -= 10
            aces -= 1
        return current_score, aces
    
    def play_single_round(self, sock):
        """Plays exactly ONE round within an existing connection."""
        packet_buffer = b""
        my_turn = True 
        
        player_cards = []
        dealer_cards = []
        
        # Track scores locally
        player_score = 0
        player_aces = 0
        
        dealer_score = 0
        dealer_aces = 0
        
        print("\n--- New Round Started ---")
        
        while True:
            try:
                data = sock.recv(1024)
                if not data: 
                    return False  # Connection closed
                
                packet_buffer += data
                
                while len(packet_buffer) >= 9:
                    packet = packet_buffer[:9]
                    packet_buffer = packet_buffer[9:]
                    
                    res, rank, suit = unpack_payload_server(packet)
                    
                    if res != PAYLOAD_CONTINUE:
                        # --- Round Over ---
                        sleep(1)
                        print("\n--- Round Results ---")
                        print(f"Your Hand:   {', '.join(player_cards)} (Score: {player_score})")
                        print(f"Dealer Hand: {', '.join(dealer_cards)} (Score: {dealer_score})")
                        
                        if res == PAYLOAD_WIN:
                            print(">> Result: YOU WON! <<")
                            self.stats.add_win()
                        elif res == PAYLOAD_LOSS:
                            print(">> Result: Dealer Won. <<")
                            self.stats.add_loss()
                        else:
                            print(">> Result: It's a Tie. <<")
                            self.stats.add_tie()
                        
                        return True  # Round complete
                            
                    else:
                        # --- Card Received ---
                        card_desc = format_card(rank, suit)
                        
                        if len(player_cards) < 2:
                            # Initial Deal: Player
                            player_cards.append(card_desc)
                            player_score, player_aces = self.calculate_score(player_score, player_aces, rank)
                            print(f"You were dealt: {card_desc}")
                            if len(player_cards) == 2:
                                print(f"   -> Your Score: {player_score}")
                            
                        elif len(dealer_cards) < 1:
                            # Initial Deal: Dealer
                            dealer_cards.append(card_desc)
                            dealer_score, dealer_aces = self.calculate_score(dealer_score, dealer_aces, rank)
                            print(f"Dealer showing: {card_desc}")
                            
                        else:
                            # Subsequent Cards
                            if my_turn:
                                player_cards.append(card_desc)
                                player_score, player_aces = self.calculate_score(player_score, player_aces, rank)
                                print(f"You were dealt: {card_desc}")
                                print(f"   -> Your Score: {player_score}")
                            else:
                                dealer_cards.append(card_desc)
                                dealer_score, dealer_aces = self.calculate_score(dealer_score, dealer_aces, rank)
                                
                                if len(dealer_cards) == 2: 
                                    print(f"Dealer revealed: {card_desc}")
                                else: 
                                    print(f"Dealer drew:    {card_desc}")
                                if dealer_score >= 17: 
                                    print(f"   -> Dealer Score: {dealer_score}")
                        
                        # --- Input Logic ---
                        if my_turn and len(player_cards) >= 2 and len(dealer_cards) >= 1:
                            
                            if player_score > 21:
                                print("   -> BUST! Waiting for result...")
                                my_turn = False
                                
                            if my_turn:
                                choice = self.get_user_input(
                                    "Your move (Hit/Stand): ", 
                                    ['hit', 'stand', 'h', 's']
                                ).strip().lower()
                                if choice == 'hit' or choice == 'h':
                                    sock.send(pack_payload(data_str="Hit"))
                                elif choice == 'stand' or choice == 's':
                                    sock.send(pack_payload(data_str="Stand"))
                                    my_turn = False
                                    print("Waiting for dealer's turn...")

            except Exception as e:
                raise e
    
    def play_session(self, sock, num_rounds):
        """Plays multiple rounds over a single connection."""
        # 1. Send Request with number of rounds
        req_packet = pack_request(num_rounds, self.team_name)
        sock.send(req_packet)
        
        # 2. Play all rounds
        for i in range(num_rounds):
            print(f"\n{'='*40}")
            print(f"  Round {i+1} of {num_rounds}")
            print(f"{'='*40}")
            
            if not self.play_single_round(sock):
                print("Connection lost during round.")
                break
            
            # Show current stats after each round
            if i < num_rounds - 1:  # Don't show for last round (summary will be shown)
                self.stats.print_current_stats()