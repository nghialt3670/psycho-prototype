"""
Multiplayer Game Server using Socket.IO

This server implements a push-based multiplayer model:
- The server maintains the authoritative game state
- Every player movement or state change is broadcast to ALL players immediately
- No pull requests needed - clients simply react to server broadcasts
- This ensures all clients have the same view of the game state at all times
"""

import eventlet
from eventlet import wsgi
import socketio

sio = socketio.Server(cors_allowed_origins='*')
app = socketio.WSGIApp(sio)

from services import (
    lobby,
    movement
)

lobby.register_lobby_events(sio)
movement.register_movement_events(sio)

# Create a Socket.IO server

# Room cleanup settings
ROOM_CLEANUP_INTERVAL = 60 * 60  # Clean up old empty rooms after 1 hour
FPS = 60  # Frames per second for game updates
UPDATE_PLAYERS_INTERVAL = 1 / FPS  # Update players every 100ms

@sio.event
def ping(sid, data):
    """Respond to ping requests from clients"""
    # Simply respond to the event, client will calculate ping based on round-trip time
    return {"status": "pong"}

# Periodically run the cleanup function
def start_cleanup_task():
    """Start the periodic room cleanup task"""
    while True:
        eventlet.sleep(ROOM_CLEANUP_INTERVAL)
        lobby.cleanup_inactive_rooms()

def start_update_players_task():
    """Start the periodic player update task"""
    while True:
        eventlet.sleep(UPDATE_PLAYERS_INTERVAL)
        movement.broadcast_games_state(sio)
        

if __name__ == '__main__':
    # Start the room cleanup task in a background thread
    eventlet.spawn(start_cleanup_task)
    eventlet.spawn(start_update_players_task)
    
    port = 5000
    print(f"Server starting on port {port}")
    wsgi.server(eventlet.listen(('', port)), app) 