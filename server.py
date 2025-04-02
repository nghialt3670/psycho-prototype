import socketio
import eventlet
from eventlet import wsgi
import json
import random

# Create a Socket.IO server
sio = socketio.Server(cors_allowed_origins='*')
app = socketio.WSGIApp(sio)

# Game state
players = {}
rooms = {}
room_walls = {}  # Store walls for each room

# Expanded player colors for more than 2 players
player_colors = [
    (255, 0, 0),    # Red
    (0, 0, 255),    # Blue
    (0, 255, 0),    # Green
    (255, 255, 0),  # Yellow
    (255, 0, 255),  # Magenta
    (0, 255, 255),  # Cyan
    (255, 165, 0),  # Orange
    (128, 0, 128)   # Purple
]

# Wall settings
WALL_WIDTH = 20
MAP_WIDTH = 800
MAP_HEIGHT = 600

# Player settings
PLAYER_SIZE = 40

# Starting positions for different players
PLAYER_STARTS = [
    (80, 80),                        # Top left
    (MAP_WIDTH - 120, MAP_HEIGHT - 120),  # Bottom right
    (80, MAP_HEIGHT - 120),          # Bottom left
    (MAP_WIDTH - 120, 80),           # Top right
    (MAP_WIDTH // 2, 80),            # Top middle
    (MAP_WIDTH // 2, MAP_HEIGHT - 120),  # Bottom middle
    (80, MAP_HEIGHT // 2),           # Left middle
    (MAP_WIDTH - 120, MAP_HEIGHT // 2)    # Right middle
]

def generate_walls():
    """Generate a labyrinth-style maze of walls"""
    walls = []
    
    # Wall thickness
    thickness = 20
    
    # Create outer boundary walls
    margin = 50  # Margin from screen edges
    
    # Top wall
    walls.append({
        'x': margin,
        'y': margin,
        'width': MAP_WIDTH - 2 * margin,
        'height': thickness
    })
    
    # Bottom wall
    walls.append({
        'x': margin,
        'y': MAP_HEIGHT - margin - thickness,
        'width': MAP_WIDTH - 2 * margin,
        'height': thickness
    })
    
    # Left wall
    walls.append({
        'x': margin,
        'y': margin,
        'width': thickness,
        'height': MAP_HEIGHT - 2 * margin
    })
    
    # Right wall
    walls.append({
        'x': MAP_WIDTH - margin - thickness,
        'y': margin,
        'width': thickness,
        'height': MAP_HEIGHT - 2 * margin
    })
    
    # Create internal maze walls
    
    # Horizontal internal walls
    # Row 1
    walls.append({
        'x': margin + 100,
        'y': margin + 80,
        'width': 200,
        'height': thickness
    })
    
    walls.append({
        'x': margin + 400,
        'y': margin + 80,
        'width': 200,
        'height': thickness
    })
    
    # Row 2
    walls.append({
        'x': margin + 150,
        'y': margin + 200,
        'width': 300,
        'height': thickness
    })
    
    # Row 3
    walls.append({
        'x': margin + 80,
        'y': margin + 320,
        'width': 150,
        'height': thickness
    })
    
    walls.append({
        'x': margin + 350,
        'y': margin + 320,
        'width': 250,
        'height': thickness
    })
    
    # Row 4
    walls.append({
        'x': margin + 200,
        'y': margin + 420,
        'width': 400,
        'height': thickness
    })
    
    # Vertical internal walls
    # Column 1
    walls.append({
        'x': margin + 150,
        'y': margin + 80,
        'width': thickness,
        'height': 120
    })
    
    # Column 2
    walls.append({
        'x': margin + 250,
        'y': margin + 200,
        'width': thickness,
        'height': 220
    })
    
    # Column 3
    walls.append({
        'x': margin + 350,
        'y': margin + 80,
        'width': thickness,
        'height': 120
    })
    
    # Column 4
    walls.append({
        'x': margin + 450,
        'y': margin + 200,
        'width': thickness,
        'height': 120
    })
    
    # Column 5
    walls.append({
        'x': margin + 550,
        'y': margin + 320,
        'width': thickness,
        'height': 150
    })
    
    # Make sure to leave space around all possible starting points
    for start_pos in PLAYER_STARTS:
        walls = [w for w in walls if not is_near_start(w, start_pos, 100)]
    
    print(f"Generated {len(walls)} labyrinth walls")
    return walls

def is_near_start(wall, start_pos, clearance):
    """Check if a wall is too close to a starting position"""
    start_x, start_y = start_pos
    wall_x = wall['x']
    wall_y = wall['y']
    wall_width = wall['width']
    wall_height = wall['height']
    
    # Create rectangles for the wall and the clear zone
    wall_rect = {
        'x': wall_x, 
        'y': wall_y, 
        'width': wall_width, 
        'height': wall_height
    }
    
    clear_rect = {
        'x': start_x - clearance//2, 
        'y': start_y - clearance//2, 
        'width': clearance, 
        'height': clearance
    }
    
    # Check if rectangles overlap
    return (clear_rect['x'] < wall_rect['x'] + wall_rect['width'] and
            clear_rect['x'] + clear_rect['width'] > wall_rect['x'] and
            clear_rect['y'] < wall_rect['y'] + wall_rect['height'] and
            clear_rect['y'] + clear_rect['height'] > wall_rect['y'])

def get_room_game_state(room_name):
    """Generate a complete game state for a room"""
    if room_name not in rooms:
        return {}
    
    # Create a clean game state with all players
    game_state = {}
    for player_sid in rooms[room_name]:
        if player_sid in players:  # Make sure player still exists
            game_state[player_sid] = {
                'x': players[player_sid]['x'],
                'y': players[player_sid]['y'],
                'color': players[player_sid]['color'],
                'position_index': players[player_sid]['position_index']  # Include position index
            }
    
    return game_state

def broadcast_game_state(room_name, exclude_sid=None):
    """Send game state to all players in a room, optionally excluding one player"""
    if room_name not in rooms:
        return
    
    game_state = get_room_game_state(room_name)
    
    for player_sid in rooms[room_name]:
        if player_sid != exclude_sid and player_sid in players:
            sio.emit('game_state', game_state, room=player_sid)

def get_next_player_position(room_name):
    """Get the next available player position and color index for a room"""
    if room_name not in rooms:
        return 0, 0
    
    # The position index is the same as the number of players already in the room
    position_index = len(rooms[room_name]) - 1  # -1 because the player was already added to the room
    
    # Make sure we don't exceed our defined positions
    if position_index >= len(PLAYER_STARTS):
        position_index = position_index % len(PLAYER_STARTS)
    
    # Same for color
    color_index = position_index
    if color_index >= len(player_colors):
        color_index = color_index % len(player_colors)
    
    return position_index, color_index

@sio.event
def connect(sid, environ):
    print('Client connected:', sid)
    players[sid] = {
        'x': 0,  # Will be set when joining a room
        'y': 0,
        'room': None,
        'color': None,
        'size': PLAYER_SIZE,
        'position_index': -1  # Will be set when joining a room
    }

@sio.event
def disconnect(sid):
    print('Client disconnected:', sid)
    if sid in players:
        room = players[sid]['room']
        if room and room in rooms:
            # Remove player from the room
            rooms[room].remove(sid)
            print(f"Player {sid} removed from room {room}, {len(rooms[room])} players left")
            
            # Clean up room if empty
            if not rooms[room]:
                print(f"Room {room} is now empty, cleaning up")
                del rooms[room]
                if room in room_walls:
                    del room_walls[room]
            else:
                # Notify other players that someone left
                for player_sid in rooms[room]:
                    sio.emit('player_left', {}, room=player_sid)
                
                # If room still has players, broadcast updated game state
                broadcast_game_state(room)
        
        # Clean up player data
        del players[sid]

@sio.event
def create_room(sid, data):
    room_name = data.get('room_name')
    if not room_name:
        return {'success': False, 'message': 'Room name is required'}
    
    if room_name in rooms:
        return {'success': False, 'message': 'Room already exists'}
    
    # Create new room with this player as first member
    rooms[room_name] = [sid]
    players[sid]['room'] = room_name
    
    # Assign first position and color
    position_index, color_index = 0, 0  # First player gets first position/color
    players[sid]['position_index'] = position_index
    players[sid]['color'] = player_colors[color_index]
    
    # Set starting position
    start_x, start_y = PLAYER_STARTS[position_index]
    players[sid]['x'] = start_x
    players[sid]['y'] = start_y
    
    # Generate walls for this room
    room_walls[room_name] = generate_walls()
    
    # Create initial game state with just this player
    game_state = {
        sid: {
            'x': start_x,
            'y': start_y,
            'color': player_colors[color_index],
            'position_index': position_index
        }
    }
    
    print(f"Room '{room_name}' created by {sid} (position {position_index})")
    
    # Return success with room data
    return {
        'success': True, 
        'message': 'Room created', 
        'color': player_colors[color_index],
        'walls': room_walls[room_name],
        'x': start_x,
        'y': start_y,
        'position_index': position_index,
        'game_state': game_state
    }

@sio.event
def join_room(sid, data):
    room_name = data.get('room_name')
    if not room_name:
        return {'success': False, 'message': 'Room name is required'}
    
    if room_name not in rooms:
        return {'success': False, 'message': 'Room does not exist'}
    
    # Add player to room
    rooms[room_name].append(sid)
    players[sid]['room'] = room_name
    
    # Determine position and color based on existing players
    position_index, color_index = get_next_player_position(room_name)
    players[sid]['color'] = player_colors[color_index]
    players[sid]['position_index'] = position_index
    
    # Set starting position
    start_x, start_y = PLAYER_STARTS[position_index]
    players[sid]['x'] = start_x
    players[sid]['y'] = start_y
    
    # Generate a clean game state including this player
    game_state = get_room_game_state(room_name)
    
    # Notify all other players that someone joined and send updated game state
    for player_sid in rooms[room_name]:
        if player_sid != sid:
            sio.emit('player_joined', {}, room=player_sid)
    
    # Broadcast game state to all OTHER players
    broadcast_game_state(room_name, exclude_sid=sid)
    
    print(f"Player {sid} joined room '{room_name}' as position {position_index} with {len(rooms[room_name])} total players")
    
    # Return success with room data
    return {
        'success': True, 
        'message': 'Joined room', 
        'color': player_colors[color_index],
        'walls': room_walls.get(room_name, []),
        'x': start_x,
        'y': start_y,
        'position_index': position_index,
        'game_state': game_state
    }

@sio.event
def list_rooms(sid):
    room_info = {}
    for room, players_list in rooms.items():
        room_info[room] = len(players_list)
    return room_info

@sio.event
def update_position(sid, data):
    """Update a player's position"""
    if sid not in players:
        return {'success': False, 'message': 'Player not found'}
    
    # Get new position
    new_x = data.get('x', players[sid]['x'])
    new_y = data.get('y', players[sid]['y'])
    
    # Validate room
    room = players[sid]['room']
    if not room or room not in rooms or sid not in rooms[room]:
        return {'success': False, 'message': 'Not in a valid room'}
    
    # Update position (no collision detection on server - client handles this)
    players[sid]['x'] = new_x
    players[sid]['y'] = new_y
    
    # Broadcast updated game state to all other players
    broadcast_game_state(room, exclude_sid=sid)
    
    return {'success': True}

@sio.event
def get_game_state(sid, data=None):
    """Request the current game state for the player's room"""
    if sid not in players:
        return {'success': False, 'message': 'Player not found'}
    
    room = players[sid]['room']
    if not room or room not in rooms:
        return {'success': False, 'message': 'Not in a room'}
    
    # Get the complete game state for this room
    game_state = get_room_game_state(room)
    
    return {'success': True, 'game_state': game_state}

if __name__ == '__main__':
    port = 5000
    print(f"Starting server on port {port}")
    wsgi.server(eventlet.listen(('', port)), app) 