class HackathonException(Exception):
    """Base exception for the project."""
    pass

class NetworkException(HackathonException):
    """Raised when socket operations fail."""
    pass

class ProtocolException(HackathonException):
    """Raised when packet parsing fails (bad cookie, wrong size)."""
    pass

class GameException(HackathonException):
    """Raised for game logic errors (deck empty, invalid state)."""
    pass