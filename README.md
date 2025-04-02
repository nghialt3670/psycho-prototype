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

# Multiplayer Labyrinth Game Server

A Socket.IO based server for the multiplayer labyrinth game.

## Docker Setup

### Prerequisites
- [Docker](https://docs.docker.com/get-docker/)
- [Docker Compose](https://docs.docker.com/compose/install/) (optional, but recommended)

### Running with Docker Compose (Recommended)

1. Build and start the server:
   ```
   docker-compose up -d
   ```

2. Stop the server:
   ```
   docker-compose down
   ```

### Running with Docker (Alternative)

1. Build the Docker image:
   ```
   docker build -t labyrinth-server .
   ```

2. Run the container:
   ```
   docker run -p 5000:5000 labyrinth-server
   ```

## Connecting Clients

The server will be accessible at:
- Local: http://localhost:5000
- Network: http://<your-ip-address>:5000

To connect from other machines, make sure to update the `.env` file on the client side to point to your server's IP address:
```
SERVER_URL=http://<your-ip-address>:5000
```

## Development

If you want to modify the server code during development, use the volume mount in docker-compose.yml, which enables automatic code updates.

## Troubleshooting

- If the server doesn't start, check Docker logs:
  ```
  docker-compose logs
  ```

- Make sure port 5000 is not already in use on your system.