# Multiplayer Square Game

A basic multiplayer top-down game where 2 players control squares and move around a map with random walls. Players can create or join a lobby to play together.

## Features
- Create and join game rooms
- Simple square-based player representation
- Real-time multiplayer interaction
- Basic lobby system
- Random walls that players can't pass through

## Requirements
- Python 3.7+
- Required libraries specified in requirements.txt

## Installation

1. Clone this repository
2. Install the required packages:
```
pip install -r requirements.txt
```

## Running the Game

1. Start the server:
```
python server.py
```

2. Start the client (in a separate terminal):
```
python client.py
```

3. For multiplayer, run another client instance in a different terminal.

## How to Play

1. Enter a room name in the input field
2. Click "Create Room" to create a new room or "Join Room" to join an existing room
3. Use the arrow keys to move your square
4. Navigate around the randomly generated walls that block your path
5. The other player's square will be visible when they join and move around

## Game Controls
- Arrow keys: Move your square
- Enter: Confirm room name input