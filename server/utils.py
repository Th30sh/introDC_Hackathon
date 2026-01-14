import random
from shared.protocol import *

class Card:
    SUIT_MAP = {'Hearts': 0, 'Diamonds': 1, 'Clubs': 2, 'Spades': 3}
    RANK_MAP = {'2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9, '10': 10, 'J': 11, 'Q': 12, 'K': 13, 'A': 1}

    def __init__(self, suit, rank):
        self.__suit = suit
        self.__rank = rank
        self.__hidden = True

    def __str__(self):
        return f"{self.__rank} of {self.__suit}"
    
    def get_raw_value(self):
        """Returns standard blackjack value. Ace is 11 by default."""
        if self.__rank in ['J', 'Q', 'K']: return 10
        elif self.__rank == 'A': return 11
        else: return int(self.__rank)
        
    def serialize(self):
        """Returns (rank_int, suit_int) for protocol."""
        return self.RANK_MAP[self.__rank], self.SUIT_MAP[self.__suit]
    
    def show(self): self.__hidden = False
    def hide(self): self.__hidden = True
    def is_hidden(self): return self.__hidden

class Deck:
    __suits = ['Hearts', 'Diamonds', 'Clubs', 'Spades']
    __ranks = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']

    def __init__(self):
        self.__cards = [Card(s, r) for s in self.__suits for r in self.__ranks]
        random.shuffle(self.__cards)

    def deal(self):
        return self.__cards.pop() if self.__cards else None

class Round:
    def __init__(self):
        self.__deck = Deck()
        self.__player_hand = []
        self.__dealer_hand = []
        
    def deal_initial(self):
        p1 = self.__deck.deal(); p1.show()
        p2 = self.__deck.deal(); p2.show()
        d1 = self.__deck.deal(); d1.show()
        d2 = self.__deck.deal(); # d2 starts hidden
        
        self.__player_hand = [p1, p2]
        self.__dealer_hand = [d1, d2]
        return p1, p2, d1 # Return visible cards to send to client

    def _calculate_hand(self, hand):
        """Calculates hand value handling Aces as 1 or 11."""
        total = sum(c.get_raw_value() for c in hand)
        ace_count = sum(1 for c in hand if c.get_raw_value() == 11)
        
        while total > 21 and ace_count > 0:
            total -= 10 # Turn an Ace (11) into a 1
            ace_count -= 1
            
        return total

    def get_player_points(self):
        return self._calculate_hand(self.__player_hand)

    def get_dealer_points(self):
        return self._calculate_hand(self.__dealer_hand)

    def player_hit(self):
        card = self.__deck.deal()
        if card:
            card.show()
            self.__player_hand.append(card)
        return card

    def dealer_turn(self):
        """
        Reveal hidden card and play dealer turn.
        Returns: (hidden_card, list_of_new_drawn_cards)
        """
        hidden_card = self.__dealer_hand[1]
        hidden_card.show() # Reveal
        
        drawn_cards = [] 
        
        # Dealer logic: Hit if < 17 [cite: 54], Stand if >= 17 [cite: 55]
        while self.get_dealer_points() < 17:
            card = self.__deck.deal()
            if card:
                card.show()
                self.__dealer_hand.append(card)
                drawn_cards.append(card)
            else:
                break
        return hidden_card, drawn_cards

    def get_winner(self):
        p = self.get_player_points()
        d = self.get_dealer_points()
        
        # Logic matches assignment [cite: 57-63]
        if p > 21: return "Dealer" # Client busts
        if d > 21: return "Player" # Dealer busts
        if p > d: return "Player"
        if d > p: return "Dealer"
        return "Tie"

class Game:
    """Handles game logic for blackjack rounds."""
    
    @staticmethod
    def start(client_socket):
        """Entry point for handling a client connection."""
        # 1. Wait for Request Message (Name + Rounds)
        data = client_socket.recv(1024)
        try:
            num_rounds, team_name = unpack_request(data)
            print(f"Client {team_name} requested {num_rounds} rounds.")
        except ProtocolException as e:
            print(f"Protocol Error: {e}")
            return

        # 2. Play all requested rounds over the same connection
        for i in range(1, num_rounds + 1):
            print(f"--- Round {i} of {num_rounds} with {team_name} ---")
            Game._play_single_round(client_socket, team_name)

    @staticmethod
    def _play_single_round(sock, team_name):
        """Plays a single round of blackjack."""
        game = Round()
        
        # Deal Initial
        p1, p2, d1 = game.deal_initial()
        
        # Send initial cards
        Game._send_card(sock, p1)  # Player 1
        Game._send_card(sock, p2)  # Player 2
        Game._send_card(sock, d1)  # Dealer Visible
        
        # Player Turn Loop
        while True:
            try:
                data = sock.recv(1024)
                if not data: break

                decision = unpack_payload_client(data)  # "Hit" or "Stand"
                
                if "Hit" in decision:
                    print(f"{team_name} decided to Hit.")
                    card = game.player_hit()
                    if card:
                        Game._send_card(sock, card)
                        if game.get_player_points() > 21:
                            print(f"{team_name} Busted!")
                            break  # End player turn immediately
                else:
                    print(f"{team_name} decided to Stand.")
                    break  # Stand
            except Exception as e:
                print(f"Error processing client move: {e}")
                break

        # Dealer Turn (Logic runs even if player busted, to show the hidden card)
        hidden_card = None
        drawn_cards = []
        
        if game.get_player_points() <= 21:
            # Normal play: reveal and draw to 17
            hidden_card, drawn_cards = game.dealer_turn()
        else:
            # Player busted: Just reveal the hidden card so user sees it
            game._Round__dealer_hand[1].show()
            hidden_card = game._Round__dealer_hand[1]
            
        # Send Dealer Hidden Card
        Game._send_card(sock, hidden_card)
        
        # Send any extra cards dealer drew
        for c in drawn_cards:
            Game._send_card(sock, c)
                
        # Determine Winner
        
        winner = game.get_winner()
        if (winner == "Player"): winner = team_name
        
        print(f"Round winner: {winner}")
        
        res_code = PAYLOAD_TIE
        if winner == team_name: res_code = PAYLOAD_WIN
        elif winner == "Dealer": res_code = PAYLOAD_LOSS
        
        # Send Final Result
        packet = pack_payload(result_code=res_code)
        sock.send(packet)

    @staticmethod
    def _send_card(sock, card):
        """Sends a card to the client."""
        rank, suit = card.serialize()
        packet = pack_payload(result_code=PAYLOAD_CONTINUE, card_rank=rank, card_suit=suit)
        sock.send(packet)