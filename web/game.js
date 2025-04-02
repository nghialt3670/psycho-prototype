// Configuration
const SERVER_URL = 'http://localhost:5000';

// Canvas setup
const canvas = document.getElementById('game-canvas');
const ctx = canvas.getContext('2d');
const SCREEN_WIDTH = canvas.width;
const SCREEN_HEIGHT = canvas.height;

// Map dimensions
const MAP_WIDTH = 2400;
const MAP_HEIGHT = 1800;

// Game state
let connected = false;
let inLobby = true;
let inRoom = false;
let roomName = "";
let clientSid = null;
let walls = [];

// Player settings
const PLAYER_SIZE = 40;
let playerX = MAP_WIDTH / 4;
let playerY = MAP_HEIGHT / 4;
const playerSpeed = 5;
let playerColor = null;

// Camera system
let cameraX = 0;
let cameraY = 0;

// Colors
const WHITE = '#FFFFFF';
const BLACK = '#000000';
const GRAY = '#C8C8C8';
const BROWN = '#8B4513';
const DARK_BROWN = '#654321';
const RED = '#FF0000';
const GREEN = '#00FF00';
const BLUE = '#0000FF';

// Player tracking
const localPlayer = {
    x: 0,
    y: 0,
    color: null,
    positionIndex: -1
};

// Remote players
const remotePositions = {};
const remotePlayerBuffer = {};
const INTERPOLATION_DURATION = 200;

// Key state
const keys = {
    ArrowLeft: false,
    ArrowRight: false,
    ArrowUp: false,
    ArrowDown: false,
    Escape: false
};

// FPS calculation
let fps = 0;
let lastFpsUpdateTime = 0;
let frameCount = 0;

// Ping measurement
let ping = 0;
let lastPingTime = 0;
const PING_INTERVAL = 2000; // Check ping every 2 seconds

// Socket.IO setup
const socket = io(SERVER_URL);

// DOM elements
const lobbyScreen = document.getElementById('lobby');
const gameScreen = document.getElementById('game');
const roomNameInput = document.getElementById('room-name');
const createRoomBtn = document.getElementById('create-room');
const joinRoomBtn = document.getElementById('join-room');
const connectionStatus = document.getElementById('connection-status');
const currentRoomDisplay = document.getElementById('current-room');
const playerCountDisplay = document.getElementById('player-count');
const fpsDisplay = document.getElementById('fps');
const pingDisplay = document.getElementById('ping');

// Socket.IO event handlers
socket.on('connect', () => {
    connected = true;
    clientSid = socket.id;
    inLobby = true;
    connectionStatus.textContent = 'Status: Connected';
    
    // Start measuring ping
    measurePing();
});

socket.on('disconnect', () => {
    connected = false;
    inLobby = true;
    inRoom = false;
    resetGameState();
    connectionStatus.textContent = 'Status: Disconnected';
    showLobby();
    
    // Reset ping display
    ping = 0;
    updatePingDisplay();
});

socket.on('game_state', (data) => {
    processGameState(data);
});

socket.on('player_joined', (data) => {
    // Server will broadcast updated game state
});

socket.on('player_left', (data) => {
    // Server will broadcast updated game state
});

// Ping response handler
socket.on('pong', () => {
    // Calculate ping based on how long it took to get a response
    const endTime = performance.now();
    ping = Math.round(endTime - lastPingTime);
    updatePingDisplay();
});

// Game functions
function resetGameState() {
    inRoom = false;
    inLobby = true;
    Object.keys(remotePositions).forEach(key => delete remotePositions[key]);
    Object.keys(remotePlayerBuffer).forEach(key => delete remotePlayerBuffer[key]);
    walls = [];
    cameraX = 0;
    cameraY = 0;
    
    localPlayer.x = 0;
    localPlayer.y = 0;
    localPlayer.color = null;
    localPlayer.positionIndex = -1;
}

function processGameState(data) {
    // Clear remote positions first to avoid ghost players
    Object.keys(remotePositions).forEach(key => delete remotePositions[key]);
    const currentTime = performance.now();
    
    if (!data || typeof data !== 'object') {
        console.error("Received invalid game state data");
        return;
    }
    
    // Process all players from the received state
    Object.entries(data).forEach(([sid, playerInfo]) => {
        // Skip our own player by SID
        if (sid === clientSid) {
            return;
        }
        
        // Skip any player with the same position index as local player
        if (playerInfo && playerInfo.position_index === localPlayer.positionIndex) {
            return;
        }
        
        // Only add valid player data
        if (playerInfo && 
            'x' in playerInfo && 
            'y' in playerInfo && 
            'color' in playerInfo && 
            'position_index' in playerInfo) {
            
            const positionIndex = playerInfo.position_index;
            
            // Update the remote player buffer for smooth interpolation
            if (!remotePlayerBuffer[positionIndex]) {
                // First time seeing this player, initialize buffer
                remotePlayerBuffer[positionIndex] = {
                    current: {x: playerInfo.x, y: playerInfo.y},
                    target: {x: playerInfo.x, y: playerInfo.y},
                    lastUpdate: currentTime
                };
            } else {
                // Update target position for existing player
                remotePlayerBuffer[positionIndex].target = {
                    x: playerInfo.x,
                    y: playerInfo.y
                };
                remotePlayerBuffer[positionIndex].lastUpdate = currentTime;
            }
            
            // Store remote player data for rendering
            remotePositions[positionIndex] = {
                x: playerInfo.x,
                y: playerInfo.y,
                color: playerInfo.color
            };
        }
    });
    
    // Update player count display
    updatePlayerCount();
}

function updatePlayerCount() {
    const count = Object.keys(remotePositions).length + 1;
    playerCountDisplay.textContent = `Players: ${count}`;
}

function updatePingDisplay() {
    pingDisplay.textContent = `Ping: ${ping}ms`;
    
    // Add color coding based on ping value
    if (ping < 50) {
        pingDisplay.className = 'good-ping';
    } else if (ping < 100) {
        pingDisplay.className = 'ok-ping';
    } else {
        pingDisplay.className = 'bad-ping';
    }
}

function measurePing() {
    if (connected) {
        lastPingTime = performance.now();
        socket.emit('ping');
        
        // Schedule next ping measurement
        setTimeout(measurePing, PING_INTERVAL);
    }
}

function updateCamera() {
    // Center the camera on the player
    cameraX = playerX - SCREEN_WIDTH / 2;
    cameraY = playerY - SCREEN_HEIGHT / 2;
    
    // Make sure camera doesn't go out of bounds
    cameraX = Math.max(0, Math.min(cameraX, MAP_WIDTH - SCREEN_WIDTH));
    cameraY = Math.max(0, Math.min(cameraY, MAP_HEIGHT - SCREEN_HEIGHT));
}

function worldToScreen(worldX, worldY) {
    return {
        x: worldX - cameraX,
        y: worldY - cameraY
    };
}

function checkWallCollision(newX, newY) {
    // First check map boundaries
    if (newX < 0 || newX > MAP_WIDTH - PLAYER_SIZE || newY < 0 || newY > MAP_HEIGHT - PLAYER_SIZE) {
        return true;
    }
    
    // Check collision with walls
    for (const wall of walls) {
        if (!wall) continue;
        
        const wallX = wall.x || 0;
        const wallY = wall.y || 0;
        const wallWidth = wall.width || 50;
        const wallHeight = wall.height || 50;
        
        if (newX < wallX + wallWidth &&
            newX + PLAYER_SIZE > wallX &&
            newY < wallY + wallHeight &&
            newY + PLAYER_SIZE > wallY) {
            return true;
        }
    }
    
    return false;
}

function updateLocalPlayerPosition() {
    // Initial assumption: we haven't moved
    let moved = false;
    
    // Store original position to check if we moved
    const origX = playerX;
    const origY = playerY;
    
    // Track which directions are being pressed
    let dx = 0;
    let dy = 0;
    
    // Process key presses to determine direction vector
    if (keys.ArrowLeft && playerX > 0) {
        dx = -1;
    } else if (keys.ArrowRight && playerX < MAP_WIDTH - PLAYER_SIZE) {
        dx = 1;
    }
    
    if (keys.ArrowUp && playerY > 0) {
        dy = -1;
    } else if (keys.ArrowDown && playerY < MAP_HEIGHT - PLAYER_SIZE) {
        dy = 1;
    }
    
    // Normalize diagonal movement
    if (dx !== 0 && dy !== 0) {
        dx *= 0.7071;
        dy *= 0.7071;
    }
    
    // Apply movement speed
    const newX = playerX + (dx * playerSpeed);
    const newY = playerY + (dy * playerSpeed);
    
    // Only consider it a move if position actually changed
    if (Math.abs(newX - origX) > 0.01 || Math.abs(newY - origY) > 0.01) {
        // Try moving in X direction only first
        if (!checkWallCollision(newX, origY)) {
            playerX = newX;
            moved = true;
        }
        
        // Then try moving in Y direction
        if (!checkWallCollision(playerX, newY)) {
            playerY = newY;
            moved = true;
        }
    }
    
    return {
        moved,
        newX: playerX,
        newY: playerY
    };
}

function updateRemotePlayerPositions(currentTime) {
    Object.keys(remotePlayerBuffer).forEach(idx => {
        const playerData = remotePlayerBuffer[idx];
        
        // Calculate how far we are through the interpolation
        const timeElapsed = currentTime - playerData.lastUpdate;
        
        if (timeElapsed >= INTERPOLATION_DURATION) {
            // Interpolation complete, set current to target
            playerData.current.x = playerData.target.x;
            playerData.current.y = playerData.target.y;
        } else {
            // Calculate interpolation progress (0 to 1)
            const progress = timeElapsed / INTERPOLATION_DURATION;
            
            // Interpolate between current and target
            playerData.current.x = playerData.current.x + (playerData.target.x - playerData.current.x) * progress;
            playerData.current.y = playerData.current.y + (playerData.target.y - playerData.current.y) * progress;
        }
    });
}

function sendPositionUpdate(x, y) {
    if (connected && inRoom) {
        try {
            // Update the local player dict for consistency
            localPlayer.x = x;
            localPlayer.y = y;
            
            // Send to server asynchronously
            socket.emit('update_position', {x, y});
        } catch (e) {
            console.error("Error sending position update:", e);
        }
    }
}

// Drawing functions
function drawWall(wall) {
    const x = wall.x || 0;
    const y = wall.y || 0;
    const width = wall.width || 50;
    const height = wall.height || 50;
    
    // Convert to screen coordinates
    const screen = worldToScreen(x, y);
    
    // Skip walls outside the screen
    if (screen.x + width < 0 || screen.x > SCREEN_WIDTH ||
        screen.y + height < 0 || screen.y > SCREEN_HEIGHT) {
        return;
    }
    
    // Main wall
    ctx.fillStyle = BROWN;
    ctx.fillRect(screen.x, screen.y, width, height);
    
    // Dark edge for 3D effect
    const edgeSize = 3;
    ctx.fillStyle = DARK_BROWN;
    
    if (width > height) { // Horizontal wall
        ctx.fillRect(screen.x, screen.y, width, edgeSize); // Top edge
        ctx.fillRect(screen.x, screen.y + height - edgeSize, width, edgeSize); // Bottom edge
    } else { // Vertical wall
        ctx.fillRect(screen.x, screen.y, edgeSize, height); // Left edge
        ctx.fillRect(screen.x + width - edgeSize, screen.y, edgeSize, height); // Right edge
    }
}

function drawPlayer(x, y, color, isLocal = false) {
    // Convert to screen coordinates
    const screen = worldToScreen(x, y);
    
    // Skip players outside the screen
    if (screen.x + PLAYER_SIZE < 0 || screen.x > SCREEN_WIDTH ||
        screen.y + PLAYER_SIZE < 0 || screen.y > SCREEN_HEIGHT) {
        return;
    }
    
    // Draw square body
    ctx.fillStyle = color;
    ctx.fillRect(screen.x, screen.y, PLAYER_SIZE, PLAYER_SIZE);
    
    // Draw border
    ctx.lineWidth = isLocal ? 3 : 2;
    ctx.strokeStyle = BLACK;
    ctx.strokeRect(screen.x, screen.y, PLAYER_SIZE, PLAYER_SIZE);
    
    // Draw eyes
    const eyeSize = PLAYER_SIZE / 5;
    const eyeY = screen.y + PLAYER_SIZE / 3;
    
    // Left eye
    ctx.fillStyle = WHITE;
    ctx.beginPath();
    ctx.arc(screen.x + PLAYER_SIZE / 3, eyeY, eyeSize, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = BLACK;
    ctx.beginPath();
    ctx.arc(screen.x + PLAYER_SIZE / 3, eyeY, eyeSize / 2, 0, Math.PI * 2);
    ctx.fill();
    
    // Right eye
    ctx.fillStyle = WHITE;
    ctx.beginPath();
    ctx.arc(screen.x + 2 * PLAYER_SIZE / 3, eyeY, eyeSize, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = BLACK;
    ctx.beginPath();
    ctx.arc(screen.x + 2 * PLAYER_SIZE / 3, eyeY, eyeSize / 2, 0, Math.PI * 2);
    ctx.fill();
    
    // Draw smile
    const smileY = screen.y + 2 * PLAYER_SIZE / 3;
    const smileWidth = PLAYER_SIZE / 2;
    ctx.strokeStyle = BLACK;
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.arc(screen.x + PLAYER_SIZE / 2, smileY, smileWidth / 2, 0, Math.PI);
    ctx.stroke();
}

function drawMiniMap() {
    const miniMapSize = 150;
    const miniMapX = SCREEN_WIDTH - miniMapSize - 10;
    const miniMapY = 10;
    
    // Draw background
    ctx.fillStyle = WHITE;
    ctx.fillRect(miniMapX, miniMapY, miniMapSize, miniMapSize);
    ctx.strokeStyle = BLACK;
    ctx.lineWidth = 2;
    ctx.strokeRect(miniMapX, miniMapY, miniMapSize, miniMapSize);
    
    // Calculate scale factors
    const scaleX = miniMapSize / MAP_WIDTH;
    const scaleY = miniMapSize / MAP_HEIGHT;
    
    // Draw walls on minimap
    ctx.fillStyle = BROWN;
    for (const wall of walls) {
        if (!wall) continue;
        
        const wallX = wall.x || 0;
        const wallY = wall.y || 0;
        const wallWidth = wall.width || 50;
        const wallHeight = wall.height || 50;
        
        // Scale to minimap
        const miniWallX = miniMapX + wallX * scaleX;
        const miniWallY = miniMapY + wallY * scaleY;
        const miniWallWidth = Math.max(1, wallWidth * scaleX);
        const miniWallHeight = Math.max(1, wallHeight * scaleY);
        
        ctx.fillRect(miniWallX, miniWallY, miniWallWidth, miniWallHeight);
    }
    
    // Draw viewport rectangle
    ctx.strokeStyle = 'rgba(200, 200, 255, 0.8)';
    const viewX = miniMapX + cameraX * scaleX;
    const viewY = miniMapY + cameraY * scaleY;
    const viewWidth = SCREEN_WIDTH * scaleX;
    const viewHeight = SCREEN_HEIGHT * scaleY;
    ctx.strokeRect(viewX, viewY, viewWidth, viewHeight);
    
    // Draw player on minimap
    ctx.fillStyle = RED;
    const playerMiniX = miniMapX + playerX * scaleX;
    const playerMiniY = miniMapY + playerY * scaleY;
    ctx.beginPath();
    ctx.arc(playerMiniX, playerMiniY, 4, 0, Math.PI * 2);
    ctx.fill();
}

function drawGame() {
    // Clear the screen at the start of each frame
    ctx.fillStyle = WHITE;
    ctx.fillRect(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT);
    
    // Update camera
    updateCamera();
    
    // Draw walls
    for (const wall of walls) {
        drawWall(wall);
    }
    
    // Draw room info and player count handled by HTML elements
    currentRoomDisplay.textContent = roomName;
    
    // Draw remote players
    for (const positionIndex in remotePositions) {
        // Skip players with same index as local
        if (parseInt(positionIndex) === localPlayer.positionIndex) {
            continue;
        }
        
        // Get interpolated position from buffer if available
        if (remotePlayerBuffer[positionIndex]) {
            const interpolatedX = remotePlayerBuffer[positionIndex].current.x;
            const interpolatedY = remotePlayerBuffer[positionIndex].current.y;
            
            const playerData = remotePositions[positionIndex];
            if (playerData.color) {
                drawPlayer(interpolatedX, interpolatedY, playerData.color, false);
            }
        }
    }
    
    // Draw local player last (on top)
    if (localPlayer.color) {
        drawPlayer(playerX, playerY, localPlayer.color, true);
    }
    
    // Draw mini-map
    drawMiniMap();
}

// Game loop
let lastUpdateTime = 0;
let lastPositionUpdateTime = 0;
const POSITION_UPDATE_INTERVAL = 100;

function gameLoop(currentTime) {
    // Calculate delta time
    const deltaTime = lastUpdateTime ? (currentTime - lastUpdateTime) / 1000 : 0;
    lastUpdateTime = currentTime;
    
    // Calculate FPS
    frameCount++;
    if (currentTime - lastFpsUpdateTime >= 1000) {
        fps = Math.round(frameCount * 1000 / (currentTime - lastFpsUpdateTime));
        frameCount = 0;
        lastFpsUpdateTime = currentTime;
        fpsDisplay.textContent = `FPS: ${fps}`;
    }
    
    if (inRoom) {
        // Handle player movement
        const movement = updateLocalPlayerPosition();
        
        // Only send position updates periodically
        if (movement.moved && connected && currentTime - lastPositionUpdateTime > POSITION_UPDATE_INTERVAL) {
            sendPositionUpdate(movement.newX, movement.newY);
            lastPositionUpdateTime = currentTime;
        }
        
        // Update interpolated positions for remote players
        updateRemotePlayerPositions(currentTime);
        
        // Draw the game
        drawGame();
    }
    
    // Request next frame
    requestAnimationFrame(gameLoop);
}

// UI event handlers
createRoomBtn.addEventListener('click', () => {
    if (connected && roomNameInput.value.trim()) {
        resetGameState();
        roomName = roomNameInput.value.trim();
        
        socket.emit('create_room', {room_name: roomName}, (result) => {
            if (result && result.success) {
                inRoom = true;
                inLobby = false;
                
                // Store local player data
                localPlayer.color = result.color;
                localPlayer.positionIndex = result.position_index || 0;
                walls = result.walls || [];
                playerX = result.x || 80;
                playerY = result.y || 80;
                localPlayer.x = playerX;
                localPlayer.y = playerY;
                
                // Reset remote player tracking
                Object.keys(remotePositions).forEach(key => delete remotePositions[key]);
                
                // Show game screen
                showGame();
            } else {
                alert(`Failed to create room: ${result?.message || 'Unknown error'}`);
            }
        });
    }
});

joinRoomBtn.addEventListener('click', () => {
    if (connected && roomNameInput.value.trim()) {
        resetGameState();
        roomName = roomNameInput.value.trim();
        
        socket.emit('join_room', {room_name: roomName}, (result) => {
            if (result && result.success) {
                inRoom = true;
                inLobby = false;
                
                // Store local player data
                localPlayer.color = result.color;
                localPlayer.positionIndex = result.position_index || 0;
                walls = result.walls || [];
                playerX = result.x || (MAP_WIDTH - 120);
                playerY = result.y || (MAP_HEIGHT - 120);
                localPlayer.x = playerX;
                localPlayer.y = playerY;
                
                // Reset remote player tracking
                Object.keys(remotePositions).forEach(key => delete remotePositions[key]);
                
                // Show game screen
                showGame();
            } else {
                alert(`Failed to join room: ${result?.message || 'Unknown error'}`);
            }
        });
    }
});

function showLobby() {
    lobbyScreen.classList.remove('hidden');
    gameScreen.classList.add('hidden');
}

function showGame() {
    lobbyScreen.classList.add('hidden');
    gameScreen.classList.remove('hidden');
}

// Keyboard input
document.addEventListener('keydown', (event) => {
    if (event.key in keys) {
        keys[event.key] = true;
    }
    
    if (event.key === 'Escape' && inRoom) {
        resetGameState();
        showLobby();
    }
});

document.addEventListener('keyup', (event) => {
    if (event.key in keys) {
        keys[event.key] = false;
    }
});

// Initialize game
showLobby();
requestAnimationFrame(gameLoop); 