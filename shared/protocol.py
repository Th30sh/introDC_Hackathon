import struct
from .exceptions import ProtocolException

# Constants
UDP_PORT = 13122  # Hardcoded per assignment [cite: 114]
MAGIC_COOKIE = 0xabcddcba
MSG_TYPE_OFFER = 0x2
MSG_TYPE_REQUEST = 0x3
MSG_TYPE_PAYLOAD = 0x4

# Payloads
PAYLOAD_WIN = 0x3
PAYLOAD_LOSS = 0x2
PAYLOAD_TIE = 0x1
PAYLOAD_CONTINUE = 0x0

def pack_offer(server_port, server_name):
    """Packs the UDP Offer message."""
    # !IBH32s: Network Endian, Int, Byte, Short, 32-char string
    server_name_bytes = server_name.encode('utf-8')[:32].ljust(32, b'\x00')
    return struct.pack('!IBH32s', MAGIC_COOKIE, MSG_TYPE_OFFER, server_port, server_name_bytes)

def unpack_offer(data):
    """Unpacks UDP Offer. Returns (server_port, server_name)."""
    if len(data) != 39:
        raise ProtocolException("Invalid offer packet size.")
    
    cookie, msg_type, port, name_bytes = struct.unpack('!IBH32s', data)
    
    if cookie != MAGIC_COOKIE:
        raise ProtocolException("Invalid Magic Cookie.")
    if msg_type != MSG_TYPE_OFFER:
        raise ProtocolException("Invalid Message Type (Expected Offer).")
        
    return port, name_bytes.decode('utf-8').strip('\x00')

def pack_request(num_rounds, team_name):
    """Packs the TCP Request message."""
    team_name_bytes = team_name.encode('utf-8')[:32].ljust(32, b'\x00')
    return struct.pack('!IBB32s', MAGIC_COOKIE, MSG_TYPE_REQUEST, num_rounds, team_name_bytes)

def unpack_request(data):
    """Unpacks TCP Request. Returns (num_rounds, team_name)."""
    if len(data) != 38:
        raise ProtocolException("Invalid request packet size.")
    
    cookie, msg_type, rounds, name_bytes = struct.unpack('!IBB32s', data)
    
    if cookie != MAGIC_COOKIE:
        raise ProtocolException("Invalid Magic Cookie.")
    if msg_type != MSG_TYPE_REQUEST:
        raise ProtocolException("Invalid Message Type (Expected Request).")
        
    return rounds, name_bytes.decode('utf-8').strip('\x00')

def pack_payload(data_str=None, result_code=0, card_rank=0, card_suit=0):
    """
    Generic packer for both Client (text) and Server (result/card) payloads.
    """
    if data_str: # Client sending "Hit" or "Stand"
        decision_bytes = data_str.encode('utf-8')[:5].ljust(5, b'\x00')
        return struct.pack('!IB5s', MAGIC_COOKIE, MSG_TYPE_PAYLOAD, decision_bytes)
    else: # Server sending State
        return struct.pack('!IBBHB', MAGIC_COOKIE, MSG_TYPE_PAYLOAD, result_code, card_rank, card_suit)

def unpack_payload_server(data):
    """Unpacks payload FROM Server (Result + Card)."""
    # Expected: Cookie(4) + Type(1) + Result(1) + Rank(2) + Suit(1) = 9 bytes
    if len(data) < 9: # Simple check
         raise ProtocolException("Payload too small.")
    
    cookie, msg_type, result, rank, suit = struct.unpack('!IBBHB', data)
    if cookie != MAGIC_COOKIE: raise ProtocolException("Invalid Magic Cookie.")
    return result, rank, suit

def unpack_payload_client(data):
    """Unpacks payload FROM Client (Decision string)."""
    # Expected: Cookie(4) + Type(1) + String(5) = 10 bytes
    if len(data) < 10:
        raise ProtocolException("Payload too small.")
    
    cookie, msg_type, decision = struct.unpack('!IB5s', data)
    if cookie != MAGIC_COOKIE: raise ProtocolException("Invalid Magic Cookie.")
    return decision.decode('utf-8').strip('\x00')

def format_card(rank, suit):
    """
    Converts rank (1-13) and suit (0-3) into a human-readable string.
    Rank: 1=Ace, 11=Jack, 12=Queen, 13=King
    Suit: 0=Hearts, 1=Diamonds, 2=Clubs, 3=Spades (HDCS order from assignment)
    """
    rank_map = {1: 'Ace', 11: 'Jack', 12: 'Queen', 13: 'King'}
    suit_map = {0: 'Hearts', 1: 'Diamonds', 2: 'Clubs', 3: 'Spades'}
    
    rank_str = rank_map.get(rank, str(rank))
    suit_str = suit_map.get(suit, 'Unknown')
    
    return f"{rank_str} of {suit_str}"