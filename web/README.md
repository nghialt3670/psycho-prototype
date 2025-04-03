# Multiplayer Labyrinth Game - Web Version

This is a web-based version of the Multiplayer Labyrinth Game, allowing players to join and play directly from their browsers without needing to install Python or any dependencies.

## Features

- Play directly in your web browser
- Same multiplayer functionality as the Python version
- Smooth player movement with client-side prediction
- Responsive design
- Compatible with all modern browsers

## How to Play

1. Open the `index.html` file in a web browser, or deploy the web folder to a web server
2. Enter a room name in the input field
3. Click "Create Room" to create a new room or "Join Room" to join an existing room
4. Use the arrow keys to navigate the maze
5. Press ESC to return to the lobby

## Running the Web Version

### Local Development

The simplest way to run the web version locally is to use Python's built-in HTTP server:

```bash
# Navigate to the web directory
cd web

# Start a simple HTTP server
python -m http.server 8000
```

Then open your browser and go to: http://localhost:8000

Alternatively, you can use any local development server like Live Server for VS Code.

### Deploying to a Web Server

To deploy the game to a web server:

1. Upload all files in the `web` directory to your web server
2. Configure the server URL (see below)

## Server Configuration

There are multiple ways to configure the server URL:

### 1. Edit .env File (Recommended)

The easiest way is to edit the `.env` file:

```
# Server configuration
SERVER_URL=http://your-server-address:5000

# Game configuration
DEBUG=false

# Version information
VERSION=1.0.0
```

Make sure the `.env` file is accessible via HTTP from your web server.

### 2. URL Parameter

You can also specify the server URL using a URL parameter:

```
http://your-game-site.com/?server=http://your-server-address:5000
```

### 3. Inject Configuration in HTML

For deployment scenarios, you can inject a SERVER_CONFIG variable before loading the game:

```html
<script>
window.SERVER_CONFIG = {
    serverUrl: 'http://your-server-address:5000'
};
</script>
<!-- Then include config-loader.js -->
<script src="config-loader.js"></script>
```

## How the Configuration System Works

The game loads configuration in the following order:

1. Default values
2. Values from the `.env` file
3. URL parameters (override .env)
4. Global SERVER_CONFIG variable (highest priority)

This gives you flexibility for different deployment scenarios.

## Compatibility with the Original Server

This web version is designed to work with the same Socket.IO server as the Python version. No changes to the server are required.

## Browser Compatibility

- Chrome 60+
- Firefox 55+
- Safari 11+
- Edge 79+

## Notes for Development

- The game uses Canvas API for rendering
- Socket.IO is used for real-time communication
- Player movement uses client-side prediction for smooth gameplay
- Remote player positions are interpolated to reduce jitter 