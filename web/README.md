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
2. Make sure to update the `SERVER_URL` in `game.js` to point to your actual Socket.IO server address

## Configuration

In `game.js`, update the `SERVER_URL` constant to point to your Socket.IO server:

```javascript
const SERVER_URL = 'http://your-server-address:5000';
```

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