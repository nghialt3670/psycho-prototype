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
player_colors = [(255, 0, 0), (0, 0, 255)]  # Red and Blue
rooms = {}
room_walls = {}  # Store walls for each room

# Wall settings
WALL_WIDTH = 20
WALL_COUNT = 10
MAP_WIDTH = 800
MAP_HEIGHT = 600

# Player settings
PLAYER_SIZE = 40

# Starting positions for players
PLAYER1_START = (80, 80)  # Top left
PLAYER2_START = (MAP_WIDTH - 120, MAP_HEIGHT - 120)  # Bottom right

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
    
    # Make sure to leave space around starting points
    # Clear area around Player 1 start position
    walls = [w for w in walls if not is_near_start(w, PLAYER1_START, 100)]
    # Clear area around Player 2 start position
    walls = [w for w in walls if not is_near_start(w, PLAYER2_START, 100)]
    
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

def check_wall_collision(x, y, size, walls):
    """Check if player collides with any wall"""
    player_rect = {'x': x, 'y': y, 'width': size, 'height': size}
    
    for wall in walls:
        # Simple rectangle collision check
        if (player_rect['x'] < wall['x'] + wall['width'] and
            player_rect['x'] + player_rect['width'] > wall['x'] and
            player_rect['y'] < wall['y'] + wall['height'] and
            player_rect['y'] + player_rect['height'] > wall['y']):
            return True
    
    return False

@sio.event
def connect(sid, environ):
    print('Client connected:', sid)
    players[sid] = {
        'x': PLAYER1_START[0],
        'y': PLAYER1_START[1],
        'room': None,
        'color': None,
        'size': PLAYER_SIZE
    }

@sio.event
def disconnect(sid):
    print('Client disconnected:', sid)
    if sid in players:
        room = players[sid]['room']
        if room and room in rooms:
            rooms[room].remove(sid)
            if not rooms[room]:
                del rooms[room]
                # Clean up walls when room is empty
                if room in room_walls:
                    del room_walls[room]
        del players[sid]

@sio.event
def create_room(sid, data):
    room_name = data.get('room_name')
    if room_name in rooms:
        return {'success': False, 'message': 'Room already exists'}
    
    rooms[room_name] = [sid]
    players[sid]['room'] = room_name
    players[sid]['color'] = player_colors[0]
    
    # Set player 1 starting position
    players[sid]['x'] = PLAYER1_START[0]
    players[sid]['y'] = PLAYER1_START[1]
    
    # Generate walls for this room
    room_walls[room_name] = generate_walls()
    
    # Debug print
    print(f"Creating room '{room_name}' with {len(room_walls[room_name])} walls")
    
    result = {
        'success': True, 
        'message': 'Room created', 
        'color': player_colors[0],
        'walls': room_walls[room_name],
        'x': PLAYER1_START[0],
        'y': PLAYER1_START[1]
    }
    
    # Debug print
    print(f"Sending {len(result['walls'])} walls to client")
    
    return result

@sio.event
def join_room(sid, data):
    room_name = data.get('room_name')
    if room_name not in rooms:
        return {'success': False, 'message': 'Room does not exist'}
    
    if len(rooms[room_name]) >= 2:
        return {'success': False, 'message': 'Room is full'}
    
    rooms[room_name].append(sid)
    players[sid]['room'] = room_name
    players[sid]['color'] = player_colors[1]
    
    # Set player 2 starting position
    players[sid]['x'] = PLAYER2_START[0]
    players[sid]['y'] = PLAYER2_START[1]
    
    # Notify the first player that someone joined
    sio.emit('player_joined', {}, room=rooms[room_name][0])
    
    # Debug print
    print(f"Player joined room '{room_name}' with {len(room_walls.get(room_name, []))} walls")
    
    result = {
        'success': True, 
        'message': 'Joined room', 
        'color': player_colors[1],
        'walls': room_walls.get(room_name, []),
        'x': PLAYER2_START[0],
        'y': PLAYER2_START[1]
    }
    
    # Debug print
    print(f"Sending {len(result['walls'])} walls to client")
    
    return result

@sio.event
def list_rooms(sid):
    available_rooms = {room: len(players) for room, players in rooms.items() if len(players) < 2}
    return available_rooms

@sio.event
def update_position(sid, data):
    if sid not in players:
        return
    
    new_x = data.get('x', players[sid]['x'])
    new_y = data.get('y', players[sid]['y'])
    
    # Check for wall collisions
    room = players[sid]['room']
    if room and room in room_walls:
        if check_wall_collision(new_x, new_y, players[sid]['size'], room_walls[room]):
            # If collision, don't update position and return
            return {'success': False, 'message': 'Wall collision'}
    
    # Update position if no collision
    players[sid]['x'] = new_x
    players[sid]['y'] = new_y
    
    if room and room in rooms:
        # Create game state with ALL players in the room
        game_state = {}
        for player_sid in rooms[room]:
            game_state[player_sid] = {
                'x': players[player_sid]['x'],
                'y': players[player_sid]['y'],
                'color': players[player_sid]['color']
            }
        
        # Send updated game state to all players EXCEPT the one who moved
        for player_sid in rooms[room]:
            if player_sid != sid:
                sio.emit('game_state', game_state, room=player_sid)
    
    return {'success': True}

if __name__ == '__main__':
    port = 5000
    print(f"Starting server on port {port}")
    wsgi.server(eventlet.listen(('', port)), app) 