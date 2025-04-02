import pygame
import socketio
import sys
import time
import threading
import json
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get server address from environment variables or use default
SERVER_URL = os.getenv('SERVER_URL', 'http://localhost:5000')

# Initialize Pygame
pygame.init()

# Screen dimensions (viewport size)
SCREEN_WIDTH, SCREEN_HEIGHT = 800, 600
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Multiplayer Labyrinth Game")

# Map dimensions (larger than screen)
MAP_WIDTH, MAP_HEIGHT = 2400, 1800  # 1600*1.5, 1200*1.5

# Camera system
camera_x, camera_y = 0, 0

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (200, 200, 200)
BROWN = (139, 69, 19)  # Color for walls
DARK_BROWN = (101, 67, 33)  # Darker color for wall edges
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)  # Blue color for other players on mini-map

# Player settings
PLAYER_SIZE = 40  # Slightly smaller player for easier navigation
player_x, player_y = MAP_WIDTH // 4, MAP_HEIGHT // 4
player_speed = 5
player_color = None

# Game state
connected = False
in_lobby = True  # Start in lobby
in_room = False
room_name = ""
client_sid = None  # Our Socket.IO session ID

# Player tracking - completely separating local and remote player data
local_player = {
    'x': 0,
    'y': 0,
    'color': None,
    'position_index': -1
}

# Store remote players by their position_index rather than sid to avoid ghost players
remote_positions = {}  # Maps position_index -> player data

# Remote player interpolation
remote_player_buffer = {}  # position_index -> {current: {x,y}, target: {x,y}, last_update: time}
INTERPOLATION_DURATION = 200  # ms to interpolate between positions

# Walls
walls = []

# Font
font = pygame.font.SysFont('Arial', 24)
title_font = pygame.font.SysFont('Arial', 32, True)  # Bold font for title

# Connect to the server
sio = socketio.Client()

# Lock for thread safety
lock = threading.Lock()

def update_camera():
    """Update the camera position to center on the player"""
    global camera_x, camera_y
    
    # Center the camera on the player with some boundary checks
    camera_x = player_x - SCREEN_WIDTH // 2
    camera_y = player_y - SCREEN_HEIGHT // 2
    
    # Make sure camera doesn't go out of bounds
    camera_x = max(0, min(camera_x, MAP_WIDTH - SCREEN_WIDTH))
    camera_y = max(0, min(camera_y, MAP_HEIGHT - SCREEN_HEIGHT))

def world_to_screen(world_x, world_y):
    """Convert world coordinates to screen coordinates"""
    return world_x - camera_x, world_y - camera_y

def screen_to_world(screen_x, screen_y):
    """Convert screen coordinates to world coordinates"""
    return screen_x + camera_x, screen_y + camera_y

def reset_game_state():
    """Reset all game state when changing rooms or disconnecting"""
    global in_room, in_lobby, remote_positions, walls, local_player, camera_x, camera_y, remote_player_buffer
    in_room = False
    in_lobby = True
    remote_positions = {}  # Clear all remote player data
    remote_player_buffer = {}  # Clear interpolation buffer
    walls = []
    camera_x, camera_y = 0, 0
    
    # Reset local player data
    local_player = {
        'x': 0,
        'y': 0,
        'color': None,
        'position_index': -1
    }

def connect_to_server():
    try:
        sio.connect(SERVER_URL)
        return True
    except Exception as e:
        print(f"Connection error: {e}")
        return False

@sio.event
def connect():
    global connected, client_sid, in_lobby
    connected = True
    client_sid = sio.sid
    in_lobby = True  # Always start in lobby when connecting

@sio.event
def disconnect():
    global connected, in_lobby, in_room
    connected = False
    in_lobby = True
    in_room = False
    # Clear all game state
    reset_game_state()

def process_game_state(data):
    """Process game state data into remote_positions dictionary
    Completely separates local player from remote players."""
    global remote_positions, remote_player_buffer
    
    # CRITICAL: Clear remote_positions first to avoid ghost players
    remote_positions = {}
    current_time = pygame.time.get_ticks()
    
    if not data or not isinstance(data, dict):
        print("Received invalid game state data")
        return
    
    # Process all players from the received state
    for sid, player_info in data.items():
        # Skip our own player by SID - this is the correct approach
        if sid == client_sid:
            print(f"Skipping own player data with SID: {sid}")
            continue
            
        # Also skip any player with the same position_index as local player
        # This ensures we never render our own player twice
        if isinstance(player_info, dict) and 'position_index' in player_info:
            if player_info['position_index'] == local_player['position_index']:
                print(f"Skipping player with same position index as local: {player_info['position_index']}")
                continue
                
        # Only add valid player data
        if isinstance(player_info, dict) and all(key in player_info for key in ['x', 'y', 'color', 'position_index']):
            position_index = player_info['position_index']
            
            # Update the remote player buffer for smooth interpolation
            if position_index not in remote_player_buffer:
                # First time seeing this player, initialize buffer
                remote_player_buffer[position_index] = {
                    'current': {'x': player_info['x'], 'y': player_info['y']},
                    'target': {'x': player_info['x'], 'y': player_info['y']},
                    'last_update': current_time
                }
            else:
                # Update target position for existing player
                remote_player_buffer[position_index]['target'] = {
                    'x': player_info['x'], 
                    'y': player_info['y']
                }
                remote_player_buffer[position_index]['last_update'] = current_time
            
            # Store remote player data in standard position dict for rendering
            remote_positions[position_index] = {
                'x': player_info['x'],
                'y': player_info['y'],
                'color': player_info['color']
            }
    
    print(f"Processed game state: {len(remote_positions)} remote players")

@sio.event
def game_state(data):
    """Handle game state updates from server broadcasts"""
    with lock:
        process_game_state(data)

@sio.event
def player_joined(data):
    """Handle notification that a player joined the room"""
    # The server will broadcast the updated game state, so we don't need to request it

@sio.event
def player_left(data):
    """Handle notification that a player left the room"""
    # The server will broadcast the updated game state, so we don't need to request it

def check_wall_collision(new_x, new_y):
    """Check if the player would collide with any wall at the new position"""
    # First check map boundaries
    if new_x < 0 or new_x > MAP_WIDTH - PLAYER_SIZE or new_y < 0 or new_y > MAP_HEIGHT - PLAYER_SIZE:
        return True
        
    player_rect = pygame.Rect(new_x, new_y, PLAYER_SIZE, PLAYER_SIZE)
    
    # Check collision with walls
    for wall in walls:
        if not isinstance(wall, dict):
            continue  # Skip invalid walls
        
        # Get wall properties with defaults if missing
        wall_x = wall.get('x', 0)
        wall_y = wall.get('y', 0)
        wall_width = wall.get('width', 50)
        wall_height = wall.get('height', 50)
            
        wall_rect = pygame.Rect(wall_x, wall_y, wall_width, wall_height)
        if player_rect.colliderect(wall_rect):
            return True
    
    # Optionally check collision with other players
    # This is optional and can be commented out if you don't want player-player collisions
    for idx, remote_player in remote_positions.items():
        if idx == local_player['position_index']:
            continue  # Skip self
            
        remote_x = remote_player.get('x', 0)
        remote_y = remote_player.get('y', 0)
        remote_rect = pygame.Rect(remote_x, remote_y, PLAYER_SIZE, PLAYER_SIZE)
        
        if player_rect.colliderect(remote_rect):
            return True
    
    return False

def draw_wall(wall):
    """Draw a single wall with a 3D effect, converting world coords to screen coords"""
    x = wall.get('x', 0)
    y = wall.get('y', 0)
    width = wall.get('width', 50)
    height = wall.get('height', 50)
    
    # Convert world coordinates to screen coordinates
    screen_x, screen_y = world_to_screen(x, y)
    
    # Skip walls that are completely outside the screen
    if (screen_x + width < 0 or screen_x > SCREEN_WIDTH or
        screen_y + height < 0 or screen_y > SCREEN_HEIGHT):
        return
    
    # Main wall
    pygame.draw.rect(screen, BROWN, (screen_x, screen_y, width, height))
    
    # Dark edge for 3D effect
    edge_size = 3
    if width > height:  # Horizontal wall
        pygame.draw.rect(screen, DARK_BROWN, (screen_x, screen_y, width, edge_size))  # Top edge
        pygame.draw.rect(screen, DARK_BROWN, (screen_x, screen_y + height - edge_size, width, edge_size))  # Bottom edge
    else:  # Vertical wall
        pygame.draw.rect(screen, DARK_BROWN, (screen_x, screen_y, edge_size, height))  # Left edge
        pygame.draw.rect(screen, DARK_BROWN, (screen_x + width - edge_size, screen_y, edge_size, height))  # Right edge

def draw_player(x, y, color, is_local=False):
    """Draw a player with a face on it, converting world coords to screen coords"""
    # Convert world coordinates to screen coordinates
    screen_x, screen_y = world_to_screen(x, y)
    
    # Skip players completely outside the screen
    if (screen_x + PLAYER_SIZE < 0 or screen_x > SCREEN_WIDTH or
        screen_y + PLAYER_SIZE < 0 or screen_y > SCREEN_HEIGHT):
        return
    
    # Draw the square body
    pygame.draw.rect(screen, color, (screen_x, screen_y, PLAYER_SIZE, PLAYER_SIZE))
    
    # Draw a black border (thicker for local player)
    border_width = 3 if is_local else 2
    pygame.draw.rect(screen, BLACK, (screen_x, screen_y, PLAYER_SIZE, PLAYER_SIZE), border_width)
    
    # Draw eyes (white with black pupils)
    eye_size = PLAYER_SIZE // 5
    eye_y = screen_y + PLAYER_SIZE // 3
    # Left eye
    pygame.draw.circle(screen, WHITE, (screen_x + PLAYER_SIZE // 3, eye_y), eye_size)
    pygame.draw.circle(screen, BLACK, (screen_x + PLAYER_SIZE // 3, eye_y), eye_size // 2)
    # Right eye
    pygame.draw.circle(screen, WHITE, (screen_x + 2 * PLAYER_SIZE // 3, eye_y), eye_size)
    pygame.draw.circle(screen, BLACK, (screen_x + 2 * PLAYER_SIZE // 3, eye_y), eye_size // 2)
    
    # Draw smile (bigger for local player)
    smile_y = screen_y + 2 * PLAYER_SIZE // 3
    smile_width = PLAYER_SIZE // 2
    pygame.draw.arc(screen, BLACK, 
                    (screen_x + PLAYER_SIZE // 4, smile_y, smile_width, PLAYER_SIZE // 4),
                    0, 3.14, 2)

def update_remote_player_positions(current_time):
    """Update interpolated positions for remote players"""
    for idx in list(remote_player_buffer.keys()):
        player_data = remote_player_buffer[idx]
        
        # Calculate how far we are through the interpolation
        time_elapsed = current_time - player_data['last_update']
        
        if time_elapsed >= INTERPOLATION_DURATION:
            # Interpolation complete, set current to target
            player_data['current']['x'] = player_data['target']['x']
            player_data['current']['y'] = player_data['target']['y']
        else:
            # Calculate interpolation progress (0 to 1)
            progress = time_elapsed / INTERPOLATION_DURATION
            
            # Interpolate between current and target
            player_data['current']['x'] = player_data['current']['x'] + (player_data['target']['x'] - player_data['current']['x']) * progress
            player_data['current']['y'] = player_data['current']['y'] + (player_data['target']['y'] - player_data['current']['y']) * progress

def draw_lobby():
    screen.fill(WHITE)
    
    # Draw title
    title = title_font.render("Multiplayer Labyrinth Game", True, BLACK)
    screen.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, 50))
    
    # Draw input box for room name
    pygame.draw.rect(screen, GRAY, (SCREEN_WIDTH // 2 - 150, 150, 300, 40))
    room_text = font.render(room_name, True, BLACK)
    screen.blit(room_text, (SCREEN_WIDTH // 2 - 145, 155))
    
    # Draw create room button
    pygame.draw.rect(screen, GRAY, (SCREEN_WIDTH // 2 - 150, 220, 300, 40))
    create_text = font.render("Create Room", True, BLACK)
    screen.blit(create_text, (SCREEN_WIDTH // 2 - create_text.get_width() // 2, 225))
    
    # Draw join room button
    pygame.draw.rect(screen, GRAY, (SCREEN_WIDTH // 2 - 150, 280, 300, 40))
    join_text = font.render("Join Room", True, BLACK)
    screen.blit(join_text, (SCREEN_WIDTH // 2 - join_text.get_width() // 2, 285))
    
    # Connection status
    status_text = font.render(f"Status: {'Connected' if connected else 'Disconnected'}", True, BLACK)
    screen.blit(status_text, (20, SCREEN_HEIGHT - 40))

def draw_mini_map():
    """Draw a mini-map in the corner to show the player's position in the larger map"""
    mini_map_size = 150
    mini_map_x = SCREEN_WIDTH - mini_map_size - 10
    mini_map_y = 10
    
    # Draw background
    pygame.draw.rect(screen, WHITE, (mini_map_x, mini_map_y, mini_map_size, mini_map_size))
    pygame.draw.rect(screen, BLACK, (mini_map_x, mini_map_y, mini_map_size, mini_map_size), 2)
    
    # Calculate scale factors
    scale_x = mini_map_size / MAP_WIDTH
    scale_y = mini_map_size / MAP_HEIGHT
    
    # Draw walls on minimap
    for wall in walls:
        if not isinstance(wall, dict):
            continue
        
        # Get wall properties
        wall_x = wall.get('x', 0)
        wall_y = wall.get('y', 0)
        wall_width = wall.get('width', 50)
        wall_height = wall.get('height', 50)
        
        # Scale wall to minimap size
        mini_wall_x = mini_map_x + wall_x * scale_x
        mini_wall_y = mini_map_y + wall_y * scale_y
        mini_wall_width = max(1, wall_width * scale_x)  # Ensure at least 1px wide
        mini_wall_height = max(1, wall_height * scale_y)  # Ensure at least 1px high
        
        # Draw wall on minimap
        pygame.draw.rect(screen, BROWN, (mini_wall_x, mini_wall_y, mini_wall_width, mini_wall_height))
    
    # Draw viewport rectangle (showing current camera view)
    view_x = mini_map_x + camera_x * scale_x
    view_y = mini_map_y + camera_y * scale_y
    view_width = SCREEN_WIDTH * scale_x
    view_height = SCREEN_HEIGHT * scale_y
    pygame.draw.rect(screen, (200, 200, 255), (view_x, view_y, view_width, view_height), 2)
    
    # Draw player position on mini-map
    player_mini_x = mini_map_x + player_x * scale_x
    player_mini_y = mini_map_y + player_y * scale_y
    pygame.draw.circle(screen, RED, (int(player_mini_x), int(player_mini_y)), 4)

def draw_game():
    # Clear the screen at the start of each frame
    screen.fill(WHITE)
    
    # Update camera to follow player
    update_camera()
    
    # Draw all walls
    for wall in walls:
        draw_wall(wall)
    
    # Room info and player count (fixed position on screen)
    room_text = font.render(f"Room: {room_name}", True, BLACK)
    screen.blit(room_text, (20, 20))
    
    # Display active player count
    player_count = len(remote_positions) + 1  # Count local player + remote players
    count_text = font.render(f"Players: {player_count}", True, BLACK)
    screen.blit(count_text, (20, 50))
    
    # Current FPS
    fps_text = font.render(f"FPS: {int(clock.get_fps())}", True, BLACK)
    screen.blit(fps_text, (20, 80))
    
    # Draw ONLY remote players using their interpolated positions
    for position_index, player_data in remote_positions.items():
        # Never render a remote player with same position index as local
        if position_index == local_player['position_index']:
            continue
        
        # Get interpolated position from buffer if available
        if position_index in remote_player_buffer:
            interpolated_x = remote_player_buffer[position_index]['current']['x']
            interpolated_y = remote_player_buffer[position_index]['current']['y']
            
            # Only render valid remote player data with color
            if 'color' in player_data:
                draw_player(interpolated_x, interpolated_y, player_data['color'], is_local=False)
    
    # Draw local player LAST (so it's always on top)
    # CRITICAL: Use the local player_x and player_y variables, NOT local_player dict
    if local_player['color'] is not None:
        draw_player(player_x, player_y, local_player['color'], is_local=True)
    
    # Draw mini-map
    draw_mini_map()
    
    # Instructions
    instr_text = font.render("Use arrow keys to navigate the maze, ESC to quit", True, BLACK)
    screen.blit(instr_text, (SCREEN_WIDTH // 2 - instr_text.get_width() // 2, SCREEN_HEIGHT - 40))

def send_position_update(x, y):
    """Send position update to server without waiting for response"""
    if connected and in_room:
        # Only send position updates if we're connected and in a room
        try:
            # Player's position is already updated in update_local_player_position
            # Just update the local_player dict for consistency
            local_player['x'] = x
            local_player['y'] = y
            
            # Send to server asynchronously (without waiting for response)
            sio.emit('update_position', {'x': x, 'y': y})
        except Exception as e:
            print(f"Error sending position update: {e}")

def update_local_player_position(keys):
    """Handle local player movement with collision detection"""
    global player_x, player_y
    
    # Initial assumption: we haven't moved
    moved = False
    
    # Store original position to check if we moved
    orig_x, orig_y = player_x, player_y
    
    # Track which directions are being pressed
    dx, dy = 0, 0
    
    # Process key presses to determine direction vector
    if keys[pygame.K_LEFT] and player_x > 0:
        dx = -1
    elif keys[pygame.K_RIGHT] and player_x < MAP_WIDTH - PLAYER_SIZE:
        dx = 1
        
    if keys[pygame.K_UP] and player_y > 0:
        dy = -1
    elif keys[pygame.K_DOWN] and player_y < MAP_HEIGHT - PLAYER_SIZE:
        dy = 1
    
    # Normalize diagonal movement to maintain consistent speed
    if dx != 0 and dy != 0:
        # Moving diagonally - normalize the diagonal speed
        # Multiply by approximately 0.7071 (1/sqrt(2)) to normalize
        dx *= 0.7071
        dy *= 0.7071
    
    # Apply movement speed
    new_x = player_x + (dx * player_speed)
    new_y = player_y + (dy * player_speed)
    
    # Only consider it a move if position actually changed
    if abs(new_x - orig_x) > 0.01 or abs(new_y - orig_y) > 0.01:  # Use a small epsilon for float comparison
        # Try moving in X direction only first (better collision handling)
        if not check_wall_collision(new_x, orig_y):
            player_x = new_x
            moved = True
        
        # Then try moving in Y direction
        if not check_wall_collision(player_x, new_y):
            player_y = new_y
            moved = True
    
    # Return whether we moved, and the new position to use
    return moved, player_x, player_y

# Add a debug function to show all players' positions
def print_debug_info():
    """Print debug information about player positions"""
    print("\n--- DEBUG INFO ---")
    print(f"Local player: ({player_x}, {player_y}) [index: {local_player['position_index']}] [SID: {client_sid}]")
    print(f"Camera: ({camera_x}, {camera_y})")
    print(f"Remote players: {len(remote_positions)}")
    for idx, data in remote_positions.items():
        print(f"  Remote[{idx}]: ({data['x']}, {data['y']})")
    print("-----------------\n")

def main():
    global player_x, player_y, connected, in_lobby, in_room, room_name, local_player, remote_positions, walls
    global clock
    
    clock = pygame.time.Clock()
    input_active = False
    
    # Initial connection attempt
    connected = connect_to_server()
    
    # Remove game state request tracking (we'll rely on server broadcasts)
    last_position_update = 0
    POSITION_UPDATE_INTERVAL = 100  # Send position updates less frequently than movement
    
    running = True
    while running:
        # Start of frame - get current time
        current_time = pygame.time.get_ticks()
        
        # Process events first
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                
            if in_lobby:  # Handle lobby events
                if event.type == pygame.MOUSEBUTTONDOWN:
                    # Check if room name input box is clicked
                    if SCREEN_WIDTH // 2 - 150 <= event.pos[0] <= SCREEN_WIDTH // 2 + 150 and 150 <= event.pos[1] <= 190:
                        input_active = True
                    else:
                        input_active = False
                    
                    # Check if create room button is clicked
                    if SCREEN_WIDTH // 2 - 150 <= event.pos[0] <= SCREEN_WIDTH // 2 + 150 and 220 <= event.pos[1] <= 260:
                        if connected and room_name:
                            # Reset game state BEFORE creating a room
                            reset_game_state()
                            in_lobby = True  # Make sure we're in lobby state
                            
                            result = sio.call('create_room', {'room_name': room_name})
                            if result and result.get('success'):
                                in_room = True
                                in_lobby = False  # Leave lobby when entering room
                                # Store local player data
                                local_player['color'] = result.get('color')
                                local_player['position_index'] = result.get('position_index', 0)
                                walls = result.get('walls', [])
                                player_x = result.get('x', 80)
                                player_y = result.get('y', 80)
                                local_player['x'] = player_x
                                local_player['y'] = player_y
                                
                                # Reset remote player tracking on room join
                                remote_positions = {}
                                
                                # No need to request initial game state as server will broadcast it
                                
                            else:
                                print(f"Failed to create room: {result.get('message', 'Unknown error')}")
                    
                    # Check if join room button is clicked
                    if SCREEN_WIDTH // 2 - 150 <= event.pos[0] <= SCREEN_WIDTH // 2 + 150 and 280 <= event.pos[1] <= 320:
                        if connected and room_name:
                            # Reset game state BEFORE joining a room
                            reset_game_state()
                            in_lobby = True  # Make sure we're in lobby state
                            
                            result = sio.call('join_room', {'room_name': room_name})
                            if result and result.get('success'):
                                in_room = True
                                in_lobby = False  # Leave lobby when entering room
                                # Store local player data
                                local_player['color'] = result.get('color')
                                local_player['position_index'] = result.get('position_index', 0)
                                walls = result.get('walls', [])
                                player_x = result.get('x', MAP_WIDTH - 120)
                                player_y = result.get('y', MAP_HEIGHT - 120)
                                local_player['x'] = player_x
                                local_player['y'] = player_y
                                
                                # Reset remote player tracking on room join
                                remote_positions = {}
                                
                                # No need to request initial game state as server will broadcast it
                                
                            else:
                                print(f"Failed to join room: {result.get('message', 'Unknown error')}")
                
                if event.type == pygame.KEYDOWN and input_active:
                    if event.key == pygame.K_RETURN:
                        input_active = False
                    elif event.key == pygame.K_BACKSPACE:
                        room_name = room_name[:-1]
                    else:
                        room_name += event.unicode
            
            # Add an escape key handler to return to lobby
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE and in_room:
                reset_game_state()  # This will set in_lobby to True and in_room to False
        
        # Then handle updates based on current state
        if in_room:
            # 1. Handle player movement EVERY frame for smooth movement
            # This updates the local position immediately without waiting for server
            keys = pygame.key.get_pressed()
            moved, new_x, new_y = update_local_player_position(keys)
            
            # 2. Only send position updates periodically to reduce network traffic
            if moved and connected and current_time - last_position_update > POSITION_UPDATE_INTERVAL:
                send_position_update(new_x, new_y)
                last_position_update = current_time
            
            # 3. Update interpolated positions for smooth remote player movement
            update_remote_player_positions(current_time)
        
        # Finally, draw everything
        # Clear screen at start of drawing
        screen.fill(BLACK if in_lobby else WHITE)
        
        # Draw appropriate screen
        if in_room:
            draw_game()
        else:
            draw_lobby()
        
        # Update display and control frame rate
        pygame.display.flip()
        clock.tick(60)
    
    # Clean up
    if connected:
        sio.disconnect()
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main() 