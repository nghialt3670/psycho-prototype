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

### Running with Docker

1. Pull and run the Docker image:
   ```
   docker run -d --name labyrinth-server -p 5000:5000/tcp -p 5000:5000/udp --restart unless-stopped yourusername/labyrinth-server:latest
   ```

2. Stop the container:
   ```
   docker stop labyrinth-server
   ```

3. Remove the container:
   ```
   docker rm labyrinth-server
   ```

## GitHub Actions Automated Deployment

This project includes a GitHub Actions workflow that automatically:
1. Builds the Docker image
2. Pushes it to Docker Hub
3. Deploys to an AWS server

### Setup Requirements

To use the automated deployment, you need to add the following secrets to your GitHub repository:

1. `DOCKERHUB_USERNAME`: Your Docker Hub username
2. `DOCKERHUB_TOKEN`: A Docker Hub access token
3. `AWS_HOST`: Your AWS server's IP address or domain name
4. `AWS_USERNAME`: SSH username for your AWS server (typically 'ec2-user', 'ubuntu', or 'admin')
5. `AWS_SSH_KEY`: The content of your AWS PEM private key file (cat your-key.pem)

### How It Works

1. When you push to the main/master branch, the workflow automatically triggers
2. The Docker image is built and pushed to Docker Hub
3. The workflow connects to your AWS server via SSH using your PEM key
4. It stops any existing container, pulls the latest image, and runs a new container with both TCP and UDP ports mapped

### Manual Deployment

You can also manually trigger the workflow from the "Actions" tab in your GitHub repository.

## Connecting Clients

The server will be accessible at:
- Local: http://localhost:5000
- Network: http://<your-ip-address>:5000

To connect from other machines, make sure to update the `.env` file on the client side to point to your server's IP address:
```
SERVER_URL=http://<your-ip-address>:5000
```

**Important:** Always use `http://` and not `https://` in the SERVER_URL since this server doesn't have SSL configured.

## Troubleshooting

- If the server doesn't start, check Docker logs:
  ```
  docker logs labyrinth-server
  ```

- Make sure port 5000 is not already in use on your system.

- If you see SSL errors like `[SSL: WRONG_VERSION_NUMBER] wrong version number`, make sure your client's `.env` file uses `http://` and not `https://` in the SERVER_URL:
  ```
  # Correct
  SERVER_URL=http://3.27.193.248:5000
  
  # Wrong (will cause SSL errors)
  SERVER_URL=https://3.27.193.248:5000
  ```