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
                'position_index': players[player_sid]['position_index']  # Include position index
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
        'game_state': game_state  # Include initial game state for immediate rendering
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
    
    # Notify all other players that someone joined
    for player_sid in rooms[room_name]:
        if player_sid != sid:
            sio.emit('player_joined', {}, room=player_sid)
    
    # Push-based model: Immediately broadcast the updated game state to all players
    broadcast_game_state(room_name)
    
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
        'game_state': game_state  # Include current game state for immediate rendering
    }

@sio.event
def list_rooms(sid):
    room_info = {}
    for room, players_list in rooms.items():
        room_info[room] = len(players_list)
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

if __name__ == '__main__':
    port = 5000
    wsgi.server(eventlet.listen(('', port)), app) 