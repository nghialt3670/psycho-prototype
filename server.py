"""
Multiplayer Game Server using Socket.IO

This server implements a push-based multiplayer model:
- The server maintains the authoritative game state
- Every player movement or state change is broadcast to ALL players immediately
- No pull requests needed - clients simply react to server broadcasts
- This ensures all clients have the same view of the game state at all times
"""

import os
import random
import socketio
from aiohttp import web
import eventlet
from eventlet import wsgi
import json
import time

# Create a Socket.IO server
sio = socketio.Server(cors_allowed_origins='*')
app = socketio.WSGIApp(sio)

# Game state
players = {}         # Store player data by SID
rooms = {}           # Store players in each room
room_walls = {}      # Store walls for each room
room_hosts = {}      # Store the host SID for each room
game_started = {}    # Track whether game has started in each room
active_room_names = set()  # Track all active room names for proper cleanup
room_creation_times = {}  # Track when rooms were created

# Room cleanup settings
ROOM_CLEANUP_INTERVAL = 60 * 60  # Clean up old empty rooms after 1 hour
INACTIVE_ROOM_THRESHOLD = 2 * 60 * 60  # Consider rooms inactive after 2 hours

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
MAP_WIDTH = 2400  # 1600 * 1.5
MAP_HEIGHT = 1800  # 1200 * 1.5

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
    """Generate a labyrinth-style maze of walls for a larger map"""
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
    
    # Create internal maze walls - now with more walls for a larger map
    
    # Horizontal internal walls - Row 1
    walls.append({
        'x': margin + 100,
        'y': margin + 80,
        'width': 300,
        'height': thickness
    })
    
    walls.append({
        'x': margin + 500,
        'y': margin + 80,
        'width': 500,
        'height': thickness
    })
    
    walls.append({
        'x': margin + 1200,
        'y': margin + 80,
        'width': 300,
        'height': thickness
    })
    
    # Row 2
    walls.append({
        'x': margin + 200,
        'y': margin + 200,
        'width': 400,
        'height': thickness
    })
    
    walls.append({
        'x': margin + 800,
        'y': margin + 200,
        'width': 400,
        'height': thickness
    })
    
    # Row 3
    walls.append({
        'x': margin + 100,
        'y': margin + 350,
        'width': 250,
        'height': thickness
    })
    
    walls.append({
        'x': margin + 500,
        'y': margin + 350,
        'width': 400,
        'height': thickness
    })
    
    walls.append({
        'x': margin + 1050,
        'y': margin + 350,
        'width': 450,
        'height': thickness
    })
    
    # Row 4
    walls.append({
        'x': margin + 300,
        'y': margin + 500,
        'width': 500,
        'height': thickness
    })
    
    walls.append({
        'x': margin + 900,
        'y': margin + 500,
        'width': 400,
        'height': thickness
    })
    
    # Row 5
    walls.append({
        'x': margin + 150,
        'y': margin + 650,
        'width': 350,
        'height': thickness
    })
    
    walls.append({
        'x': margin + 700,
        'y': margin + 650,
        'width': 450,
        'height': thickness
    })
    
    walls.append({
        'x': margin + 1200,
        'y': margin + 650,
        'width': 300,
        'height': thickness
    })
    
    # Row 6
    walls.append({
        'x': margin + 250,
        'y': margin + 800,
        'width': 550,
        'height': thickness
    })
    
    walls.append({
        'x': margin + 950,
        'y': margin + 800,
        'width': 350,
        'height': thickness
    })
    
    # Row 7
    walls.append({
        'x': margin + 150,
        'y': margin + 950,
        'width': 300,
        'height': thickness
    })
    
    walls.append({
        'x': margin + 600,
        'y': margin + 950,
        'width': 600,
        'height': thickness
    })
    
    # Vertical internal walls - Column 1
    walls.append({
        'x': margin + 200,
        'y': margin + 80,
        'width': thickness,
        'height': 180
    })
    
    # Column 2
    walls.append({
        'x': margin + 400,
        'y': margin + 200,
        'width': thickness,
        'height': 300
    })
    
    # Column 3
    walls.append({
        'x': margin + 550,
        'y': margin + 80,
        'width': thickness,
        'height': 200
    })
    
    # Column 4
    walls.append({
        'x': margin + 700,
        'y': margin + 350,
        'width': thickness,
        'height': 300
    })
    
    # Column 5
    walls.append({
        'x': margin + 900,
        'y': margin + 150,
        'width': thickness,
        'height': 350
    })
    
    # Column 6
    walls.append({
        'x': margin + 1050,
        'y': margin + 500,
        'width': thickness,
        'height': 300
    })
    
    # Column 7
    walls.append({
        'x': margin + 1200,
        'y': margin + 350,
        'width': thickness,
        'height': 450
    })
    
    # Column 8
    walls.append({
        'x': margin + 350,
        'y': margin + 650,
        'width': thickness,
        'height': 300
    })
    
    # Column 9
    walls.append({
        'x': margin + 500,
        'y': margin + 800,
        'width': thickness,
        'height': 270
    })
    
    # Column 10
    walls.append({
        'x': margin + 800,
        'y': margin + 650,
        'width': thickness,
        'height': 300
    })
    
    # Column 11
    walls.append({
        'x': margin + 1100,
        'y': margin + 800,
        'width': thickness,
        'height': 220
    })
    
    # Make sure to leave space around all possible starting points
    for start_pos in PLAYER_STARTS:
        walls = [w for w in walls if not is_near_start(w, start_pos, 100)]
    
    print(f"Generated {len(walls)} labyrinth walls for {MAP_WIDTH}x{MAP_HEIGHT} map")
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
                'position_index': players[player_sid]['position_index'],  # Include position index
                'username': players[player_sid]['username'],  # Include username
                'is_host': player_sid == room_hosts.get(room_name)  # Include host status
            }
    
    return game_state

def broadcast_game_state(room_name):
    """Broadcast current game state to all players in the room"""
    if room_name not in rooms:
        return
    
    # Get the current state of all players in this room
    game_state = get_room_game_state(room_name)
    
    # Broadcast to all clients in the room - push-based model ensures
    # everyone gets the same state at the same time
    for sid in rooms[room_name]:
        sio.emit('game_state', game_state, room=sid)

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
    players[sid] = {
        'x': 0,  # Will be set when joining a room
        'y': 0,
        'room': None,
        'color': None,
        'size': PLAYER_SIZE,
        'position_index': -1,  # Will be set when joining a room
        'username': None,  # Will be set when joining a room
        'is_host': False  # Default to not a host
    }

@sio.event
def disconnect(sid):
    print('Client disconnected:', sid)
    if sid in players:
        room = players[sid]['room']
        if room and room in rooms:
            # Handle as a leave_room action
            leave_room(sid)
        
        # Clean up player data
        del players[sid]

@sio.event
def create_room(sid, data):
    room_name = data.get('room_name')
    username = data.get('username', f'Player {sid[:5]}')  # Get username or use default
    
    if not room_name:
        return {'success': False, 'message': 'Room name is required'}
    
    if room_name in active_room_names:
        return {'success': False, 'message': 'Room already exists'}
    
    # Create new room with this player as first member and host
    rooms[room_name] = [sid]
    room_hosts[room_name] = sid  # Set creator as host
    game_started[room_name] = False  # Game not started yet
    active_room_names.add(room_name)  # Add to active room names
    room_creation_times[room_name] = time.time()  # Record creation time
    
    players[sid]['room'] = room_name
    players[sid]['username'] = username  # Store the username
    players[sid]['is_host'] = True  # Mark as host
    
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
    
    # Create initial player list for waiting lobby
    player_list = [{
        'id': sid,
        'username': username,
        'is_host': True
    }]
    
    print(f"Room '{room_name}' created by {username} (SID: {sid}, position {position_index})")
    
    # Return success with room data
    return {
        'success': True, 
        'message': 'Room created', 
        'color': player_colors[color_index],
        'walls': room_walls[room_name],
        'x': start_x,
        'y': start_y,
        'position_index': position_index,
        'is_host': True,
        'player_list': player_list,
        'game_started': False
    }

@sio.event
def join_room(sid, data):
    room_name = data.get('room_name')
    username = data.get('username', f'Player {sid[:5]}')  # Get username or use default
    
    if not room_name:
        return {'success': False, 'message': 'Room name is required'}
    
    if room_name not in active_room_names:
        return {'success': False, 'message': 'Room does not exist'}
    
    # Check if the game has already started
    if game_started.get(room_name, False):
        return {'success': False, 'message': 'Game has already started'}
    
    # Add player to room
    rooms[room_name].append(sid)
    players[sid]['room'] = room_name
    players[sid]['username'] = username  # Store the username
    players[sid]['is_host'] = False  # Not a host
    
    # Determine position and color based on existing players
    position_index, color_index = get_next_player_position(room_name)
    players[sid]['color'] = player_colors[color_index]
    players[sid]['position_index'] = position_index
    
    # Set starting position
    start_x, start_y = PLAYER_STARTS[position_index]
    players[sid]['x'] = start_x
    players[sid]['y'] = start_y
    
    # Generate player list for waiting lobby
    player_list = []
    for player_sid in rooms[room_name]:
        if player_sid in players:
            player_list.append({
                'id': player_sid,
                'username': players[player_sid]['username'],
                'is_host': player_sid == room_hosts.get(room_name)
            })
    
    # Notify all players in the room that someone joined
    for player_sid in rooms[room_name]:
        sio.emit('player_joined', {
            'player_list': player_list
        }, room=player_sid)
    
    print(f"Player {username} (SID: {sid}) joined room '{room_name}' as position {position_index} with {len(rooms[room_name])} total players")
    
    # Return success with room data
    return {
        'success': True, 
        'message': 'Joined room', 
        'color': player_colors[color_index],
        'walls': room_walls.get(room_name, []),
        'x': start_x,
        'y': start_y,
        'position_index': position_index,
        'is_host': False,
        'player_list': player_list,
        'game_started': False
    }

@sio.event
def leave_room(sid, data, callback=None):
    """Allow a player to leave a room with proper callback"""
    if sid not in players:
        if callback:
            callback({'success': False, 'message': 'Player not found'})
        return {'success': False, 'message': 'Player not found'}
    
    # Check if player has a room value at all
    if 'room' not in players[sid] or players[sid]['room'] is None:
        if callback:
            callback({'success': True, 'message': 'Already left room'})
        return {'success': True, 'message': 'Already left room'}
    
    room_name = players[sid]['room']
    if not room_name:
        # Player has empty room name - consider them already out of room
        players[sid]['room'] = None
        players[sid]['is_host'] = False
        if callback:
            callback({'success': True, 'message': 'Already left room'})
        return {'success': True, 'message': 'Already left room'}
    
    # Check if room exists
    if room_name not in rooms:
        # Room doesn't exist - reset player's room status and return success
        players[sid]['room'] = None
        players[sid]['is_host'] = False
        if callback:
            callback({'success': True, 'message': 'Room no longer exists'})
        return {'success': True, 'message': 'Room no longer exists'}
    
    # Remove player from room
    rooms[room_name].remove(sid)
    is_host = sid == room_hosts.get(room_name)
    
    # If room is now empty, delete it and free the room name
    if len(rooms[room_name]) == 0:
        del rooms[room_name]
        if room_name in room_walls:
            del room_walls[room_name]
        if room_name in room_hosts:
            del room_hosts[room_name]
        if room_name in game_started:
            del game_started[room_name]
        if room_name in active_room_names:
            active_room_names.remove(room_name)
        if room_name in room_creation_times:
            del room_creation_times[room_name]
        print(f"Room {room_name} deleted and name freed - no players left")
    else:
        # Transfer host if current host is leaving
        if is_host:
            room_hosts[room_name] = rooms[room_name][0]  # Make the first player the new host
            players[room_hosts[room_name]]['is_host'] = True
            print(f"Host transferred to {players[room_hosts[room_name]]['username']}")
        
        # Generate updated player list
        player_list = []
        for player_sid in rooms[room_name]:
            if player_sid in players:
                player_list.append({
                    'id': player_sid,
                    'username': players[player_sid]['username'],
                    'is_host': player_sid == room_hosts.get(room_name)
                })
        
        # Notify remaining players that someone left and send updated player list
        for player_sid in rooms[room_name]:
            sio.emit('player_left', {
                'player_list': player_list,
                'new_host': room_hosts.get(room_name) if is_host else None
            }, room=player_sid)
    
    # Reset player's room status
    players[sid]['room'] = None
    players[sid]['is_host'] = False
    
    print(f"Player {players[sid]['username']} left room {room_name}")
    
    # Send success response via callback if provided
    if callback:
        callback({'success': True, 'message': 'Left room'})
    return {'success': True, 'message': 'Left room'}

@sio.event
def start_game(sid, data, callback=None):
    """Start the game in a room with proper callback"""
    if sid not in players:
        if callback:
            callback({'success': False, 'message': 'Player not found'})
        return {'success': False, 'message': 'Player not found'}
    
    room_name = players[sid]['room']
    if not room_name or room_name not in rooms:
        if callback:
            callback({'success': False, 'message': 'Not in a room'})
        return {'success': False, 'message': 'Not in a room'}
    
    # Only host can start the game
    if sid != room_hosts.get(room_name):
        if callback:
            callback({'success': False, 'message': 'Only the host can start the game'})
        return {'success': False, 'message': 'Only the host can start the game'}
    
    # Mark game as started
    game_started[room_name] = True
    
    # Generate game state
    game_state = get_room_game_state(room_name)
    
    # Notify all players that the game is starting
    for player_sid in rooms[room_name]:
        sio.emit('game_started', {
            'game_state': game_state,
            'walls': room_walls.get(room_name, [])
        }, room=player_sid)
    
    print(f"Game started in room {room_name} by host {players[sid]['username']}")
    
    # Send success response via callback
    if callback:
        callback({'success': True, 'message': 'Game started'})
    return {'success': True, 'message': 'Game started'}

@sio.event
def list_rooms(sid):
    """List all available rooms that can be joined"""
    room_info = {}
    for room in active_room_names:
        if room in rooms:
            room_info[room] = len(rooms[room])
    return room_info

@sio.event
def update_position(sid, data):
    """Update player position and velocity"""
    if sid not in players:
        return {'success': False, 'message': 'Player not found'}
    
    room_name = players[sid]['room']
    if not room_name or room_name not in rooms:
        return {'success': False, 'message': 'Player not in a room'}
    
    # Update player position
    new_x = data.get('x')
    new_y = data.get('y')
    velocity_x = data.get('vx', 0)
    velocity_y = data.get('vy', 0)
    
    # Update username if provided
    if 'username' in data and data['username']:
        players[sid]['username'] = data['username']
    
    if new_x is not None and new_y is not None:
        players[sid]['x'] = new_x
        players[sid]['y'] = new_y
        players[sid]['vx'] = velocity_x
        players[sid]['vy'] = velocity_y
        
        # Push-based model: Broadcast updated game state to ALL players
        # This ensures everyone has the most current positions
        broadcast_game_state(room_name)
            
    return {'success': True}

@sio.event
def ping(sid):
    """Respond to ping requests from clients"""
    # Simply respond to the event, client will calculate ping based on round-trip time
    return {"status": "pong"}

# Function to clean up inactive rooms
def cleanup_inactive_rooms():
    """Clean up inactive rooms that have been empty for too long"""
    current_time = time.time()
    
    # Find rooms that are empty and haven't been used for a while
    rooms_to_clean = []
    for room_name in active_room_names.copy():
        # Check if room is empty
        if room_name not in rooms or not rooms[room_name]:
            # Check if room has been inactive for too long
            if (room_name in room_creation_times and 
                current_time - room_creation_times[room_name] > INACTIVE_ROOM_THRESHOLD):
                rooms_to_clean.append(room_name)
    
    # Clean up each identified room
    for room_name in rooms_to_clean:
        if room_name in rooms:
            del rooms[room_name]
        if room_name in room_walls:
            del room_walls[room_name]
        if room_name in room_hosts:
            del room_hosts[room_name]
        if room_name in game_started:
            del game_started[room_name]
        if room_name in room_creation_times:
            del room_creation_times[room_name]
        active_room_names.remove(room_name)
        print(f"Cleaned up inactive room: {room_name}")

# Periodically run the cleanup function
def start_cleanup_task():
    """Start the periodic room cleanup task"""
    while True:
        eventlet.sleep(ROOM_CLEANUP_INTERVAL)
        cleanup_inactive_rooms()

if __name__ == '__main__':
    # Start the room cleanup task in a background thread
    eventlet.spawn(start_cleanup_task)
    
    port = 5000
    print(f"Server starting on port {port}")
    wsgi.server(eventlet.listen(('', port)), app) 