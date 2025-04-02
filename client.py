import pygame
import socketio
import sys
import time

# Initialize Pygame
pygame.init()

# Screen dimensions
WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Multiplayer Labyrinth Game")

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (200, 200, 200)
BROWN = (139, 69, 19)  # Color for walls
DARK_BROWN = (101, 67, 33)  # Darker color for wall edges

# Player settings
PLAYER_SIZE = 40  # Slightly smaller player for easier navigation
player_x, player_y = WIDTH // 2, HEIGHT // 2
player_speed = 5
player_color = None

# Other player's position
other_players = {}

# Walls
walls = []

# Game state
connected = False
in_room = False
room_name = ""

# Font
font = pygame.font.SysFont('Arial', 24)
title_font = pygame.font.SysFont('Arial', 32, True)  # Bold font for title

# Connect to the server
sio = socketio.Client()

def connect_to_server():
    try:
        sio.connect('http://localhost:5000')
        return True
    except Exception as e:
        print(f"Connection error: {e}")
        return False

@sio.event
def connect():
    global connected
    connected = True
    print("Connected to server")

@sio.event
def disconnect():
    global connected, in_room
    connected = False
    in_room = False
    print("Disconnected from server")

@sio.event
def player_joined(data):
    print("Another player joined the room")

@sio.event
def game_state(data):
    global other_players
    other_players = data

def check_wall_collision(new_x, new_y):
    """Check if the player would collide with any wall at the new position"""
    player_rect = pygame.Rect(new_x, new_y, PLAYER_SIZE, PLAYER_SIZE)
    
    for wall in walls:
        wall_rect = pygame.Rect(wall.get('x', 0), wall.get('y', 0), 
                               wall.get('width', 50), wall.get('height', 50))
        if player_rect.colliderect(wall_rect):
            return True
    
    return False

def draw_wall(wall):
    """Draw a single wall with a 3D effect"""
    x = wall.get('x', 0)
    y = wall.get('y', 0)
    width = wall.get('width', 50)
    height = wall.get('height', 50)
    
    # Main wall
    pygame.draw.rect(screen, BROWN, (x, y, width, height))
    
    # Dark edge for 3D effect
    edge_size = 3
    if width > height:  # Horizontal wall
        pygame.draw.rect(screen, DARK_BROWN, (x, y, width, edge_size))  # Top edge
        pygame.draw.rect(screen, DARK_BROWN, (x, y + height - edge_size, width, edge_size))  # Bottom edge
    else:  # Vertical wall
        pygame.draw.rect(screen, DARK_BROWN, (x, y, edge_size, height))  # Left edge
        pygame.draw.rect(screen, DARK_BROWN, (x + width - edge_size, y, edge_size, height))  # Right edge

def draw_player(x, y, color):
    """Draw a player with a face on it"""
    # Draw the square body
    pygame.draw.rect(screen, color, (x, y, PLAYER_SIZE, PLAYER_SIZE))
    
    # Draw a black border
    pygame.draw.rect(screen, BLACK, (x, y, PLAYER_SIZE, PLAYER_SIZE), 2)
    
    # Draw eyes (white with black pupils)
    eye_size = PLAYER_SIZE // 5
    eye_y = y + PLAYER_SIZE // 3
    # Left eye
    pygame.draw.circle(screen, WHITE, (x + PLAYER_SIZE // 3, eye_y), eye_size)
    pygame.draw.circle(screen, BLACK, (x + PLAYER_SIZE // 3, eye_y), eye_size // 2)
    # Right eye
    pygame.draw.circle(screen, WHITE, (x + 2 * PLAYER_SIZE // 3, eye_y), eye_size)
    pygame.draw.circle(screen, BLACK, (x + 2 * PLAYER_SIZE // 3, eye_y), eye_size // 2)
    
    # Draw smile
    smile_y = y + 2 * PLAYER_SIZE // 3
    smile_width = PLAYER_SIZE // 2
    pygame.draw.arc(screen, BLACK, 
                    (x + PLAYER_SIZE // 4, smile_y, smile_width, PLAYER_SIZE // 4),
                    0, 3.14, 2)

def draw_lobby():
    screen.fill(WHITE)
    
    # Draw title
    title = title_font.render("Multiplayer Labyrinth Game", True, BLACK)
    screen.blit(title, (WIDTH // 2 - title.get_width() // 2, 50))
    
    # Draw input box for room name
    pygame.draw.rect(screen, GRAY, (WIDTH // 2 - 150, 150, 300, 40))
    room_text = font.render(room_name, True, BLACK)
    screen.blit(room_text, (WIDTH // 2 - 145, 155))
    
    # Draw create room button
    pygame.draw.rect(screen, GRAY, (WIDTH // 2 - 150, 220, 300, 40))
    create_text = font.render("Create Room", True, BLACK)
    screen.blit(create_text, (WIDTH // 2 - create_text.get_width() // 2, 225))
    
    # Draw join room button
    pygame.draw.rect(screen, GRAY, (WIDTH // 2 - 150, 280, 300, 40))
    join_text = font.render("Join Room", True, BLACK)
    screen.blit(join_text, (WIDTH // 2 - join_text.get_width() // 2, 285))
    
    # Connection status
    status_text = font.render(f"Status: {'Connected' if connected else 'Disconnected'}", True, BLACK)
    screen.blit(status_text, (20, HEIGHT - 40))

def draw_game():
    # Clear the screen at the start of each frame
    screen.fill(WHITE)
    
    # Draw all walls
    for wall in walls:
        draw_wall(wall)
    
    # Room info
    room_text = font.render(f"Room: {room_name}", True, BLACK)
    screen.blit(room_text, (20, 20))
    
    # Draw other players first (so current player is on top)
    for sid, data in other_players.items():
        draw_player(data['x'], data['y'], data['color'])
    
    # Draw current player last
    draw_player(player_x, player_y, player_color)
    
    # Instructions
    instr_text = font.render("Use arrow keys to navigate the maze", True, BLACK)
    screen.blit(instr_text, (WIDTH // 2 - instr_text.get_width() // 2, HEIGHT - 40))

def main():
    global player_x, player_y, connected, in_room, room_name, player_color, other_players, walls
    
    clock = pygame.time.Clock()
    input_active = False
    
    # Initial connection attempt
    connected = connect_to_server()
    
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                
            if not in_room:
                # Handle lobby events
                if event.type == pygame.MOUSEBUTTONDOWN:
                    # Check if room name input box is clicked
                    if WIDTH // 2 - 150 <= event.pos[0] <= WIDTH // 2 + 150 and 150 <= event.pos[1] <= 190:
                        input_active = True
                    else:
                        input_active = False
                    
                    # Check if create room button is clicked
                    if WIDTH // 2 - 150 <= event.pos[0] <= WIDTH // 2 + 150 and 220 <= event.pos[1] <= 260:
                        if connected and room_name:
                            result = sio.call('create_room', {'room_name': room_name})
                            if result.get('success'):
                                in_room = True
                                player_color = result.get('color')
                                walls = result.get('walls', [])
                                # Use starting position from server
                                player_x = result.get('x', 80)
                                player_y = result.get('y', 80)
                                print(f"Created room: {room_name}")
                                print(f"Received {len(walls)} walls")
                            else:
                                print(f"Failed to create room: {result.get('message')}")
                    
                    # Check if join room button is clicked
                    if WIDTH // 2 - 150 <= event.pos[0] <= WIDTH // 2 + 150 and 280 <= event.pos[1] <= 320:
                        if connected and room_name:
                            result = sio.call('join_room', {'room_name': room_name})
                            if result.get('success'):
                                in_room = True
                                player_color = result.get('color')
                                walls = result.get('walls', [])
                                # Use starting position from server
                                player_x = result.get('x', WIDTH - 120)
                                player_y = result.get('y', HEIGHT - 120)
                                print(f"Joined room: {room_name}")
                                print(f"Received {len(walls)} walls")
                            else:
                                print(f"Failed to join room: {result.get('message')}")
                
                if event.type == pygame.KEYDOWN and input_active:
                    if event.key == pygame.K_RETURN:
                        input_active = False
                    elif event.key == pygame.K_BACKSPACE:
                        room_name = room_name[:-1]
                    else:
                        room_name += event.unicode
        
        if in_room:
            # Game logic
            keys = pygame.key.get_pressed()
            moved = False
            
            new_x, new_y = player_x, player_y
            
            if keys[pygame.K_LEFT] and player_x > 0:
                new_x = player_x - player_speed
            if keys[pygame.K_RIGHT] and player_x < WIDTH - PLAYER_SIZE:
                new_x = player_x + player_speed
            if keys[pygame.K_UP] and player_y > 0:
                new_y = player_y - player_speed
            if keys[pygame.K_DOWN] and player_y < HEIGHT - PLAYER_SIZE:
                new_y = player_y + player_speed
            
            # Check wall collision locally first
            if not check_wall_collision(new_x, new_y):
                if new_x != player_x or new_y != player_y:
                    moved = True
                    # Update local position
                    player_x, player_y = new_x, new_y
            
            # Send position update to server if moved
            if moved and connected:
                try:
                    result = sio.call('update_position', {'x': player_x, 'y': player_y})
                    # If server reports a collision, revert movement
                    if result and not result.get('success', True):
                        # Revert to previous position
                        player_x = player_x - (new_x - player_x)
                        player_y = player_y - (new_y - player_y)
                except Exception as e:
                    print(f"Error sending position update: {e}")
            
            draw_game()
        else:
            draw_lobby()
        
        pygame.display.flip()
        clock.tick(60)
    
    # Clean up
    if connected:
        sio.disconnect()
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main() 