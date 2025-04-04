from storage.game_states import players, rooms, active_room_names
from models.Player import Player
from models.Vec2 import Vec2
from models.Room import Room
import time

MAX_PLAYERS = 8  # Maximum number of players in a room

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

INACTIVE_ROOM_THRESHOLD = 2 * 60 * 60  # Consider rooms inactive after 2 hours


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


def get_player_list(room):
    player_list = []
    for player_sid in room.get_players():
        if not room.is_player_in_room(player_sid):
            continue
        player_list.append({
            'id': player_sid,
            'username': players[player_sid].username,
            'is_host': player_sid == room.get_hostSid()
        })
    return player_list

def register_lobby_events(sio):
    @sio.event
    def connect(sid, environ):
        players[sid] = Player(sid, Vec2(0, 0))

    @sio.event
    def disconnect(sid):
        print('Client disconnected:', sid)
        if sid not in players:
            return

        room_name = players[sid].room
        if room_name and room_name in rooms:
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
        sio.enter_room(sid, room_name)
        rooms[room_name] = Room(generate_walls(), sid)
        active_room_names.add(room_name)  # Add to active room names
        
        position_index, color_index = 0, 0  # First player gets first position/color
        start_x, start_y = PLAYER_STARTS[position_index]
        
        players[sid].position = Vec2(start_x, start_y)
        players[sid].username = username  # Store the username
        players[sid].color = player_colors[color_index]
        players[sid].room = room_name
        
        print(f"Room '{room_name}' created by {username} (SID: {sid}, position {position_index})")
        
        # Return success with room data
        return {
            'success': True, 
            'message': 'Room created', 
            'color': player_colors[color_index],
            'walls': rooms[room_name].get_walls(),
            'x': start_x,
            'y': start_y,
            'position_index': position_index,
            'is_host': True,
            'player_list': get_player_list(rooms[room_name]),
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
        
        room = rooms[room_name]
        
        if room.is_game_started() and not room.is_player_in_room(sid):
            return {'success': False, 'message': 'Game already started'}
        
        # Check if the game has already started
        if room.is_game_started() and room.is_player_in_room(sid):
            room.activate_player(sid)
        elif not room.is_game_started():
            # Add player to room
            current_player_count = room.get_num_players()
            if current_player_count >= MAX_PLAYERS:
                return {'success': False, 'message': 'Room is full'}

            start_x, start_y = PLAYER_STARTS[current_player_count]
            players[sid].position = Vec2(start_x, start_y)
            players[sid].color = player_colors[current_player_count]
            players[sid].room = room_name
            players[sid].username = username  # Store the username
            room.add_player(sid)
            new_player_count = current_player_count + 1
            
            
        player_list = get_player_list(room)
            
        # Notify all players in the room that someone joined
        sio.enter_room(sid, room_name)
        sio.emit('player_joined', {
            'player_list': player_list,
        }, room=room_name)
        
        print(f"Player {username} (SID: {sid}) joined room '{room_name}' as position {current_player_count} with {new_player_count} total players")
        
        # Return success with room data
        return {
            'success': True, 
            'message': 'Joined room', 
            'color': player_colors[current_player_count],
            'walls': rooms[room_name].get_walls(),
            'x': start_x,
            'y': start_y,
            'position_index': current_player_count,
            'is_host': False,
            'player_list': player_list,
            'game_started': False
        }

    @sio.event
    def leave_room(sid, data, callback=None):
        """Allow a player to leave a room with proper callback"""
        print(f"Player {sid} attempting to leave room")
        
        if sid not in players:
            print(f"Player {sid} not found in players dictionary")
            if callback:
                callback({'success': False, 'message': 'Player not found'})
            return {'success': False, 'message': 'Player not found'}
        
        room_name = players[sid].room
        
        # Check if player has a room value at all
        if room_name == None:
            print(f"Player {sid} has no room assigned")
            if callback:
                callback({'success': True, 'message': 'Already left room'})
            return {'success': True, 'message': 'Already left room'}
        
        print(f"Player {sid} attempting to leave room: {room_name}")
        
        if not room_name:
            # Player has empty room name - consider them already out of room
            print(f"Player {sid} has empty room name")
            players[sid].room = None
            if callback:
                callback({'success': True, 'message': 'Already left room'})
            return {'success': True, 'message': 'Already left room'}
        
        # Check if room exists
        if room_name not in rooms:
            print(f"Room {room_name} does not exist")
            # Room doesn't exist - reset player's room status and return success
            players[sid].room = None
            if callback:
                callback({'success': True, 'message': 'Room no longer exists'})
            return {'success': True, 'message': 'Room no longer exists'}
        
        room = rooms[room_name]
        
        # Check if player is actually in the room they're trying to leave
        if not room.is_player_in_room(sid):
            print(f"Player {sid} not found in room {room_name}")
            # Player not in the specified room - fix their state and return success
            players[sid].room = None
            if callback:
                callback({'success': True, 'message': 'Already left room'})
            return {'success': True, 'message': 'Already left room'}
        
        
        # Remove player from room
        players[sid].room = None
        if room.is_game_started():
            room.deactivate_player(sid)
        else:
            room.remove_player(sid)
            
            # If room is now empty, delete it and free the room name
            if room.get_num_players() == 0:
                del rooms[room_name]
                if room_name in active_room_names:
                    active_room_names.remove(room_name)
                print(f"Room {room_name} deleted and name freed - no players left")

        player_list = get_player_list(room)
                
        sio.emit('player_left', {
            'player_list': player_list,
            'new_host': room.get_hostSid()
        }, room=room_name)
        sio.leave_room(sid, room_name)
        
        print(f"Player {sid} ({players[sid].username}) successfully left room {room_name}")
        
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
        
        room_name = players[sid].room
        if not room_name or room_name not in rooms:
            if callback:
                callback({'success': False, 'message': 'Not in a room'})
            return {'success': False, 'message': 'Not in a room'}
        
        # Only host can start the game
        room = rooms[room_name]
        if sid != room.get_hostSid():
            if callback:
                callback({'success': False, 'message': 'Only the host can start the game'})
            return {'success': False, 'message': 'Only the host can start the game'}
        
        # Mark game as started
        room.start_game()
        
        # Notify all players that the game is starting
        sio.emit('game_started', {
            'walls': room.get_walls(),
        }, room=room_name)
        
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
                room_info[room] = rooms[room].get_num_players()
        return room_info


# Function to clean up inactive rooms
def cleanup_inactive_rooms():
    """Clean up inactive rooms that have been empty for too long"""
    current_time = time.time()
    
    # Find rooms that are empty and haven't been used for a while
    rooms_to_clean = []
    for room_name in active_room_names.copy():
        # Check if room is empty
        if room_name in rooms and rooms[room_name].is_empty():
            # Check if room has been inactive for too long
            if (current_time - rooms[room_name].get_creation_time() > INACTIVE_ROOM_THRESHOLD):
                rooms_to_clean.append(room_name)
    
    # Clean up each identified room
    for room_name in rooms_to_clean:
        if room_name in rooms:
            del rooms[room_name]
        active_room_names.remove(room_name)
        print(f"Cleaned up inactive room: {room_name}")
