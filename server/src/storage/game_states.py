
from models.Player import Player
from models.Room import Room

# Game state
players: dict[str, Player] = {}         # Store player data by SID
rooms: dict[str, Room] = {}           # Store players in each room
active_room_names = set()  # Track all active room names for proper cleanup
