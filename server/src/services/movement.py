from models.Vec2 import Vec2

from storage.game_states import players, rooms
from storage.game_states import active_room_names


def get_room_game_state(room_name):
    """Generate a complete game state for a room"""
    if room_name not in rooms:
        return {}
    
    room = rooms[room_name]
    
    # # Create a clean game state with all players
    # leaved_players = [sid for sid in room.get_players() if sid not in players]
    # for sid in leaved_players:
    #     del players[sid]
    
    game_state: dict[str, dict] = {}
    for i, player_sid in enumerate(room.get_players()):
        game_state[player_sid] = {
            'x': players[player_sid].position.x,
            'y': players[player_sid].position.y,
            'color': players[player_sid].color,
            'position_index': i,  # Include position index
            'username': players[player_sid].username,  # Include username
            'is_host': player_sid == room.get_hostSid(),  # Include host status
            'is_active': room.is_player_activated(player_sid),  # Include active status
        }
    
    return game_state

def broadcast_games_state(sio):
  for room_name in active_room_names:
    if rooms[room_name].is_empty() or not rooms[room_name].is_game_started():
        continue
    
    game_state = get_room_game_state(room_name)
    sio.emit('game_state', game_state, room=room_name)


def register_movement_events(sio):
    @sio.event
    def update_position(sid, data):
        """Update player position and velocity"""
        if sid not in players:
            return {'success': False, 'message': 'Player not found'}
        
        room_name = players[sid].room
        if not room_name or room_name not in rooms:
            return {'success': False, 'message': 'Player not in a room'}
        
        # Update player position
        new_x = data.get('x')
        new_y = data.get('y')
        
        # Update username if provided
        if 'username' in data and data['username']:
            players[sid].username = data['username']
        
        if new_x is not None and new_y is not None:
            players[sid].position = Vec2(new_x, new_y)
            
        return {'success': True}
