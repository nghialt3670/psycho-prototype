// Configuration
const SERVER_URL = 'https://psycho.vuhuydiet.xyz';

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
let inLobby = true; // Start in lobby screen
let inWaitingLobby = false; // New state for waiting lobby
let inRoom = false;
let roomName = "";
let clientSid = null;
let walls = [];
let isHost = false; // Whether the player is the host
let gameStarted = false; // Whether the game has started

// Player settings
const PLAYER_SIZE = 40;
let playerX = MAP_WIDTH / 4;
let playerY = MAP_HEIGHT / 4;
const playerSpeed = 3;
let playerColor = null;
let playerUsername = ""; // Added player username

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
    positionIndex: -1,
    username: "" // Added username field
};

// Movement and rendering settings
const REMOTE_PLAYER_SPEED = 8; // Balanced constant speed (pixels per frame)
const MOVEMENT_SMOOTHING = 0.15; // Only used for minor adjustments
const MIN_SMOOTHING = 0.1; 
const MAX_SMOOTHING = 0.4;
let lastPositionUpdateTime = 0;

// Remote player tracking
const remotePositions = {}; // Latest server positions
const remotePlayerRendering = {}; // Current render positions with smoothing
const remotePlayerVelocity = {}; // Track velocity for each player

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
let lastUpdateTime = 0;

// Ping measurement
let ping = 0;
let lastPingTime = 0;
const PING_INTERVAL = 2000; // Check ping every 2 seconds

// Debug display
let networkDebugEnabled = false;
document.addEventListener('keydown', (e) => {
    if (e.key === 'F2') {
        networkDebugEnabled = !networkDebugEnabled;
    }
});

// DOM elements - Get references just once at startup
const lobbyScreen = document.getElementById('lobby');
const waitingLobbyScreen = document.getElementById('waiting-lobby'); // New waiting lobby screen
const gameScreen = document.getElementById('game');
const roomNameInput = document.getElementById('room-name');
const usernameInput = document.getElementById('username'); // Add username input reference
const createRoomBtn = document.getElementById('create-room');
const joinRoomBtn = document.getElementById('join-room');
const connectionStatus = document.getElementById('connection-status');
const currentRoomDisplay = document.getElementById('current-room');
const lobbyRoomNameDisplay = document.getElementById('lobby-room-name'); // Room name in waiting lobby
const waitingPlayersList = document.getElementById('waiting-players-list'); // List of waiting players
const hostControls = document.getElementById('host-controls'); // Host-only controls
const guestWaitingMessage = document.getElementById('guest-waiting-message'); // Guest waiting message
const startGameBtn = document.getElementById('start-game'); // Start game button
const leaveRoomBtn = document.getElementById('leave-room'); // Leave room button
const playerCountDisplay = document.getElementById('player-count');
const fpsDisplay = document.getElementById('fps');
const pingDisplay = document.getElementById('ping');

console.log("Initializing UI elements:", {
    lobbyScreen, waitingLobbyScreen, gameScreen, roomNameInput, usernameInput,
    createRoomBtn, joinRoomBtn, startGameBtn, leaveRoomBtn,
    connectionStatus, currentRoomDisplay, lobbyRoomNameDisplay, waitingPlayersList
});

// =============================================
// Socket.IO connection and events (Push Model)
// =============================================

// Create the socket connection

const socket = io(SERVER_URL, {
    // Recommended configuration options:
    secure: true, // Ensures HTTPS connection
    // transports: ['websocket'], // Force WebSocket transport
    rejectUnauthorized: true // Verify SSL certificate (default)
  });

// Connection events
socket.on('connect', () => {
    console.log("Connected to server!");
    connected = true;
    clientSid = socket.id;
    inLobby = true;
    connectionStatus.textContent = 'Status: Connected';
    
    // Measure ping on connection
    console.log("Starting ping measurements after connection");
    measurePing();
    
    // Make sure we're showing the lobby screen
    showLobby();
});

socket.on('disconnect', () => {
    console.log("Disconnected from server");
    connected = false;
    inLobby = true;
    inRoom = false;
    resetGameState();
    connectionStatus.textContent = 'Status: Disconnected';
    
    // Return to lobby UI
    showLobby();
    
    // Reset ping display
    ping = 0;
    updatePingDisplay();
});

// Game state pushed from server
socket.on('game_state', (data) => {
    console.log("Received game state update from server");
    processGameState(data);
});

// Player joined event
socket.on('player_joined', (data) => {
    console.log("Player joined the room", data);
    if (data && data.player_list) {
        updatePlayerListUI(data.player_list);
    }
});

// Player left event
socket.on('player_left', (data) => {
    console.log("Player left the room", data);
    if (data && data.player_list) {
        updatePlayerListUI(data.player_list);
        
        // If host was transferred to this player
        if (data.new_host === clientSid) {
            isHost = true;
            updateHostUI();
        }
    }
});

socket.on('game_started', (data) => {
    console.log("Game starting", data);
    gameStarted = true;
    
    // Process game state if provided
    if (data.game_state) {
        processGameState(data.game_state);
    }
    
    // Store walls if provided
    if (data.walls) {
        walls = data.walls;
    }
    
    // Move from waiting lobby to game
    inWaitingLobby = false;
    inRoom = true;
    
    // Switch to game screen
    showGame();
});

// =============================================
// Game State Management
// =============================================

function resetGameState() {
    console.log("Resetting game state");
    
    // Reset game state
    inRoom = false;
    inWaitingLobby = false;
    inLobby = true;
    isHost = false;
    gameStarted = false;
    
    // Clear remote player data
    for (const key in remotePositions) {
        delete remotePositions[key];
    }
    
    // Clear smoothing data
    for (const key in remotePlayerRendering) {
        delete remotePlayerRendering[key];
    }
    
    // Reset local data
    walls = [];
    cameraX = 0;
    cameraY = 0;
    
    // Reset local player
    localPlayer.x = 0;
    localPlayer.y = 0;
    localPlayer.color = null;
    localPlayer.positionIndex = -1;
    localPlayer.username = "";
}

function processGameState(data) {
    // Skip processing if not in a room
    if (!inRoom) return;
    
    if (!data || typeof data !== 'object') {
        console.error("Received invalid game state data");
        return;
    }
    
    const now = performance.now(); // Current time for timestamping
    
    // Process all players from the game state
    Object.entries(data).forEach(([sid, playerInfo]) => {
        // Skip our own player by checking SID
        if (sid === clientSid) {
            return;
        }
        
        // Skip any player with same position index as local player
        if (playerInfo && playerInfo.position_index === localPlayer.positionIndex) {
            return;
        }
        
        // Ensure valid player data
        if (playerInfo && 
            'x' in playerInfo && 
            'y' in playerInfo && 
            'color' in playerInfo && 
            'position_index' in playerInfo) {
            
            const positionIndex = playerInfo.position_index;
            
            // Convert color array to CSS color
            const colorArray = playerInfo.color;
            const cssColor = `rgb(${colorArray[0]}, ${colorArray[1]}, ${colorArray[2]})`;
            
            // Get username from player info, with default if not provided
            const username = playerInfo.username || `Player ${positionIndex + 1}`;
            
            // Initialize rendering position if this is a new player
            if (!remotePlayerRendering[positionIndex]) {
                remotePlayerRendering[positionIndex] = {
                    x: playerInfo.x,
                    y: playerInfo.y,
                    color: cssColor,
                    lastX: playerInfo.x,
                    lastY: playerInfo.y,
                    lastUpdateTime: now,
                    username: username
                };
            } else {
                // Update color and username in case they changed
                remotePlayerRendering[positionIndex].color = cssColor;
                remotePlayerRendering[positionIndex].username = username;
                
                // For fast-moving players, update position history
                const renderPos = remotePlayerRendering[positionIndex];
                renderPos.lastX = renderPos.x;
                renderPos.lastY = renderPos.y;
                renderPos.lastUpdateTime = now;
            }
            
            // Store latest position from server with timestamp
            remotePositions[positionIndex] = {
                x: playerInfo.x,
                y: playerInfo.y,
                color: cssColor,
                username: username,
                time: now
            };
        }
    });
    
    // Clean up any missing players
    Object.keys(remotePositions).forEach(idx => {
        if (!Object.entries(data).some(([_, info]) => 
            info && info.position_index == idx && 
            info.position_index !== localPlayer.positionIndex)) {
            delete remotePositions[idx];
            delete remotePlayerRendering[idx];
        }
    });
    
    // Update player count on UI
    updatePlayerCount();
}

// =============================================
// UI Updates
// =============================================

function updatePlayerCount() {
    const count = Object.keys(remotePositions).length + 1; // +1 for local player
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

function showLobby() {
    console.log("Showing lobby screen");
    if (lobbyScreen && waitingLobbyScreen && gameScreen) {
        lobbyScreen.style.display = 'flex';
        lobbyScreen.classList.remove('hidden');
        
        waitingLobbyScreen.style.display = 'none';
        waitingLobbyScreen.classList.add('hidden');
        
        gameScreen.style.display = 'none';
        gameScreen.classList.add('hidden');
        
        console.log("All screens updated: Lobby visible, waiting lobby and game hidden");
    } else {
        console.error("Screen elements not found!", lobbyScreen, waitingLobbyScreen, gameScreen);
    }
}

function showGame() {
    console.log("Showing game screen");
    if (lobbyScreen && gameScreen) {
        gameScreen.style.display = 'flex';
        gameScreen.classList.remove('hidden');
        
        lobbyScreen.style.display = 'none';
        lobbyScreen.classList.add('hidden');
    } else {
        console.error("Screen elements not found!", lobbyScreen, gameScreen);
    }
}

function showWaitingLobby() {
    console.log("Showing waiting lobby screen");
    if (lobbyScreen && waitingLobbyScreen && gameScreen) {
        lobbyScreen.style.display = 'none';
        lobbyScreen.classList.add('hidden');
        
        waitingLobbyScreen.style.display = 'flex';
        waitingLobbyScreen.classList.remove('hidden');
        
        gameScreen.style.display = 'none';
        gameScreen.classList.add('hidden');
        
        // Update room name display
        if (lobbyRoomNameDisplay) {
            lobbyRoomNameDisplay.textContent = roomName;
        }
        
        // Update host/guest UI
        updateHostUI();
    } else {
        console.error("Screen elements not found!", lobbyScreen, waitingLobbyScreen, gameScreen);
    }
}

// =============================================
// Networking and Measurement
// =============================================

function measurePing() {
    if (connected) {
        console.log("Measuring ping...");
        lastPingTime = performance.now();
        socket.emit('ping', {}, (response) => {
            if (!response) {
                console.error("No response received from ping");
                ping = 0;
            } else {
                const endTime = performance.now();
                ping = Math.round(endTime - lastPingTime);
                console.log(`Received ping response: ${JSON.stringify(response)}`);
                console.log(`Round-trip time: ${ping}ms`);
                updatePingDisplay();
            }
            
            // Schedule next ping measurement
            setTimeout(measurePing, PING_INTERVAL);
        });
    } else {
        // If not connected, try again later when we might be connected
        console.log("Not connected, scheduling ping measurement retry");
        setTimeout(measurePing, PING_INTERVAL);
    }
}

function sendPositionUpdate(x, y) {
    if (connected && inRoom) {
        try {
            // Update the local player state
            localPlayer.x = x;
            localPlayer.y = y;
            
            // Send to server (push model) with username
            socket.emit('update_position', { 
                x, 
                y,
                username: playerUsername 
            });
            lastPositionUpdateTime = performance.now();
        } catch (e) {
            console.error("Error sending position update:", e);
        }
    }
}

// =============================================
// Game Mechanics
// =============================================

function updateCamera() {
    // Center camera on player
    cameraX = playerX - SCREEN_WIDTH / 2;
    cameraY = playerY - SCREEN_HEIGHT / 2;
    
    // Prevent camera from going outside map boundaries
    cameraX = Math.max(0, Math.min(cameraX, MAP_WIDTH - SCREEN_WIDTH));
    cameraY = Math.max(0, Math.min(cameraY, MAP_HEIGHT - SCREEN_HEIGHT));
}

function worldToScreen(worldX, worldY) {
    return {
        x: worldX - cameraX,
        y: worldY - cameraY
    };
}

function checkWallCollision(newX, newY, size) {
    // First check map boundaries
    if (newX < 0 || newX > MAP_WIDTH - size || newY < 0 || newY > MAP_HEIGHT - size) {
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
            newX + size > wallX &&
            newY < wallY + wallHeight &&
            newY + size > wallY) {
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
        if (!checkWallCollision(newX, origY, PLAYER_SIZE)) {
            playerX = newX;
            moved = true;
        }
        
        // Then try moving in Y direction
        if (!checkWallCollision(playerX, newY, PLAYER_SIZE)) {
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

function updateRemotePlayers(deltaTime) {
    // Process movement updates with constant speed
    if (!inRoom) return;
    
    // Smooth movement for all remote players
    for (const idx in remotePositions) {
        // Get the current rendering position and the target position
        const renderPos = remotePlayerRendering[idx];
        const targetPos = remotePositions[idx];
        
        if (renderPos && targetPos) {
            // Calculate distance to target
            const dx = targetPos.x - renderPos.x;
            const dy = targetPos.y - renderPos.y;
            const distance = Math.sqrt(dx*dx + dy*dy);
            
            // If very close to target, just snap to it
            if (distance <= 1) {
                renderPos.x = targetPos.x;
                renderPos.y = targetPos.y;
                continue;
            }
            
            // Calculate movement for this frame with constant speed
            // Normalize for consistent frame rate (60fps)
            const moveDistance = REMOTE_PLAYER_SPEED * (deltaTime * 60);
            
            // If we can reach target this frame, just go there
            if (moveDistance >= distance) {
                renderPos.x = targetPos.x;
                renderPos.y = targetPos.y;
            } else {
                // Otherwise move with constant speed in direction of target
                // This ensures perfectly uniform movement speed
                const moveRatio = moveDistance / distance;
                renderPos.x += dx * moveRatio;
                renderPos.y += dy * moveRatio;
            }
        }
    }
}

// =============================================
// Drawing Functions
// =============================================

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

function drawPlayer(x, y, color, isLocal = false, username) {
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
    
    // Draw username above player
    if (username) {
        const nameX = screen.x + PLAYER_SIZE / 2;
        const nameY = screen.y;
        
        // Create name tag
        ctx.fillStyle = 'rgba(0, 0, 0, 0.5)';
        ctx.font = 'bold 14px Arial';
        const textWidth = ctx.measureText(username).width;
        
        // Draw name tag background
        ctx.fillRect(nameX - textWidth / 2 - 4, nameY - 25, textWidth + 8, 20);
        
        // Draw name text
        ctx.fillStyle = 'white';
        ctx.textAlign = 'center';
        ctx.fillText(username, nameX, nameY - 10);
        ctx.textAlign = 'left'; // Reset text alignment
    }
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

function drawNetworkDebug() {
    if (!networkDebugEnabled) return;
    
    const remotePlayerCount = Object.keys(remotePositions).length;
    
    const debugX = 10;
    const debugY = SCREEN_HEIGHT - 100;
    const lineHeight = 15;
    
    ctx.fillStyle = 'rgba(0, 0, 0, 0.7)';
    ctx.fillRect(debugX, debugY, 300, 100);
    
    ctx.fillStyle = 'white';
    ctx.font = '12px monospace';
    ctx.fillText(`Ping: ${ping}ms`, debugX + 10, debugY + lineHeight);
    ctx.fillText(`Remote Players: ${remotePlayerCount}`, debugX + 10, debugY + lineHeight * 2);
    ctx.fillText(`Position Updates: Immediate`, debugX + 10, debugY + lineHeight * 3);
    ctx.fillText(`Server Model: Push-based (Broadcast)`, debugX + 10, debugY + lineHeight * 4);
    ctx.fillText(`Movement: Uniform ${REMOTE_PLAYER_SPEED}px/frame`, debugX + 10, debugY + lineHeight * 5);
}

function drawGame() {
    if (!inRoom) return;
    
    // Clear the screen
    ctx.fillStyle = WHITE;
    ctx.fillRect(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT);
    
    // Update camera to follow player
    updateCamera();
    
    // Draw all walls
    for (const wall of walls) {
        drawWall(wall);
    }
    
    // Update room info on HTML elements
    if (currentRoomDisplay) {
        currentRoomDisplay.textContent = roomName;
    }
    
    // Draw remote players using smoothed positions
    for (const positionIndex in remotePlayerRendering) {
        // Skip players with same index as local
        if (parseInt(positionIndex) === localPlayer.positionIndex) {
            continue;
        }
        
        const renderPos = remotePlayerRendering[positionIndex];
        if (renderPos) {
            drawPlayer(
                renderPos.x, 
                renderPos.y, 
                renderPos.color, 
                false,
                renderPos.username // Pass username to draw function
            );
        }
    }
    
    // Draw local player last (on top)
    if (localPlayer.color) {
        drawPlayer(playerX, playerY, localPlayer.color, true, localPlayer.username);
    }
    
    // Draw mini-map
    drawMiniMap();
    
    // Draw network debug info if enabled
    if (networkDebugEnabled) {
        drawNetworkDebug();
    }
}

// =============================================
// Game Loop
// =============================================

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
        if (fpsDisplay) {
            fpsDisplay.textContent = `FPS: ${fps}`;
        }
    }
    
    if (inRoom) {
        // Handle player movement
        const movement = updateLocalPlayerPosition();
        
        // Send position updates IMMEDIATELY on movement
        if (movement.moved && connected) {
            sendPositionUpdate(movement.newX, movement.newY);
        }
        
        // Update remote player positions with smoothing
        updateRemotePlayers(deltaTime);
        
        // Draw the game - only if we're actually in the game
        drawGame();
    }
    
    // Request next frame
    requestAnimationFrame(gameLoop);
}

// =============================================
// Event Handlers
// =============================================

// UI Button event handlers
createRoomBtn.addEventListener('click', () => {
    if (connected && roomNameInput.value.trim()) {
        // Get username, default if empty
        playerUsername = usernameInput.value.trim() || `Player${Math.floor(Math.random() * 1000)}`;
        localPlayer.username = playerUsername;
        
        resetGameState();
        roomName = roomNameInput.value.trim();
        
        socket.emit('create_room', {
            room_name: roomName,
            username: playerUsername
        }, (result) => {
            if (result && result.success) {
                console.log("Room created successfully:", result);
                
                // Store local player data
                if (Array.isArray(result.color)) {
                    localPlayer.color = `rgb(${result.color[0]}, ${result.color[1]}, ${result.color[2]})`;
                } else {
                    localPlayer.color = result.color;
                }
                
                // Set player as host
                isHost = result.is_host;
                
                // Store state
                inLobby = false;
                inWaitingLobby = true;
                
                localPlayer.positionIndex = result.position_index || 0;
                walls = result.walls || [];
                playerX = result.x || 80;
                playerY = result.y || 80;
                localPlayer.x = playerX;
                localPlayer.y = playerY;
                
                // Update player list if provided
                if (result.player_list) {
                    updatePlayerListUI(result.player_list);
                }
                
                // Switch to waiting lobby screen
                showWaitingLobby();
            } else {
                alert(`Failed to create room: ${result?.message || 'Unknown error'}`);
            }
        });
    } else if (!usernameInput.value.trim()) {
        alert("Please enter a username");
    } else if (!roomNameInput.value.trim()) {
        alert("Please enter a room name");
    }
});

joinRoomBtn.addEventListener('click', () => {
    if (connected && roomNameInput.value.trim()) {
        // Get username, default if empty
        playerUsername = usernameInput.value.trim() || `Player${Math.floor(Math.random() * 1000)}`;
        localPlayer.username = playerUsername;
        
        resetGameState();
        roomName = roomNameInput.value.trim();
        
        socket.emit('join_room', {
            room_name: roomName,
            username: playerUsername
        }, (result) => {
            if (result && result.success) {
                console.log("Room joined successfully:", result);
                
                // Store local player data
                if (Array.isArray(result.color)) {
                    localPlayer.color = `rgb(${result.color[0]}, ${result.color[1]}, ${result.color[2]})`;
                } else {
                    localPlayer.color = result.color;
                }
                
                // Set host status
                isHost = result.is_host;
                
                localPlayer.positionIndex = result.position_index || 0;
                walls = result.walls || [];
                playerX = result.x || (MAP_WIDTH - 120);
                playerY = result.y || (MAP_HEIGHT - 120);
                localPlayer.x = playerX;
                localPlayer.y = playerY;
                
                // Update player list if provided
                if (result.player_list) {
                    updatePlayerListUI(result.player_list);
                }
                
                // Always go to waiting lobby first regardless of whether we're host or not
                // The game_started event will move us to the game when the host starts it
                inLobby = false;
                inWaitingLobby = true;
                inRoom = false; // Make sure we're not in game mode
                gameStarted = false; // Game not started yet for this client
                
                // Show the waiting lobby screen
                showWaitingLobby();
            } else {
                alert(`Failed to join room: ${result?.message || 'Unknown error'}`);
            }
        });
    } else if (!usernameInput.value.trim()) {
        alert("Please enter a username");
    } else if (!roomNameInput.value.trim()) {
        alert("Please enter a room name");
    }
});

// Start game button (host only)
startGameBtn.addEventListener('click', () => {
    console.log("Start Game button clicked", { connected, inWaitingLobby, isHost });
    
    if (connected && inWaitingLobby && isHost) {
        console.log("Emitting start_game event");
        socket.emit('start_game', {}, (result) => {
            console.log("Received start_game response:", result);
            if (result && result.success) {
                console.log("Starting game:", result);
                // Server will send game_started event to all players
            } else {
                console.error("Failed to start game:", result);
                alert(`Failed to start game: ${result?.message || 'Unknown error'}`);
            }
        });
    } else {
        console.warn("Cannot start game: conditions not met", { connected, inWaitingLobby, isHost });
    }
});

// Leave room button
leaveRoomBtn.addEventListener('click', () => {
    console.log("Leave Room button clicked", { connected, inWaitingLobby, inRoom });
    
    // Always attempt to leave regardless of client state to ensure sync with server
    if (connected) {
        console.log("Emitting leave_room event");
        socket.emit('leave_room', {}, (result) => {
            console.log("Received leave_room response:", result);
            if (result && result.success) {
                console.log("Left room successfully:", result);
                // Force state reset and show lobby
                resetGameState();
                inLobby = true;
                inWaitingLobby = false;
                inRoom = false;
                showLobby();
            } else {
                console.error("Failed to leave room:", result);
                
                // If we get a "Not in a room" error, assume we're already out
                // and reset the client state anyway to prevent UI getting stuck
                if (result && result.message === "Not in a room" || 
                    result && result.message === "Already left room") {
                    console.log("Resetting client state to lobby");
                    resetGameState();
                    inLobby = true;
                    inWaitingLobby = false;
                    inRoom = false;
                    showLobby();
                } else {
                    alert(`Failed to leave room: ${result?.message || 'Unknown error'}`);
                }
            }
        });
    } else {
        console.warn("Cannot leave room: not connected to server");
    }
});

// Keyboard input
document.addEventListener('keydown', (event) => {
    if (event.key in keys) {
        keys[event.key] = true;
    }
    
    if (event.key === 'Escape') {
        if (inRoom) {
            // If in game, return to waiting lobby
            inRoom = false;
            inWaitingLobby = true;
            showWaitingLobby();
        } else if (inWaitingLobby) {
            // If in waiting lobby, leave room and return to main lobby
            console.log("Escape key pressed to leave room");
            socket.emit('leave_room', {}, (result) => {
                console.log("Escape key leave room result:", result);
                if (result && result.success) {
                    resetGameState();
                    inLobby = true;
                    inWaitingLobby = false;
                    inRoom = false;
                    showLobby();
                } else {
                    // If we get a "Not in a room" error, assume we're already out
                    // and reset the client state anyway to prevent UI getting stuck
                    if (result && result.message === "Not in a room" || 
                        result && result.message === "Already left room") {
                        console.log("Resetting client state to lobby from Escape key");
                        resetGameState();
                        inLobby = true;
                        inWaitingLobby = false;
                        inRoom = false;
                        showLobby();
                    } else {
                        alert(`Failed to leave room: ${result?.message || 'Unknown error'}`);
                    }
                }
            });
        }
    }
});

document.addEventListener('keyup', (event) => {
    if (event.key in keys) {
        keys[event.key] = false;
    }
});

// DOM ready check
document.addEventListener('DOMContentLoaded', function() {
    console.log("DOM fully loaded");
    
    // Debug DOM elements existence
    console.log("Checking critical DOM elements:");
    console.log("Start Game button:", startGameBtn);
    console.log("Leave Room button:", leaveRoomBtn);
    console.log("Host controls:", hostControls);
    console.log("Guest waiting message:", guestWaitingMessage);
    console.log("Waiting players list:", waitingPlayersList);
    
    // Reinitialize button event listeners
    if (startGameBtn) {
        console.log("Adding event listener to Start Game button");
        startGameBtn.addEventListener('click', function() {
            console.log("Start Game button clicked through direct binding");
            if (connected && inWaitingLobby && isHost) {
                socket.emit('start_game', {}, (result) => {
                    console.log("Start game result:", result);
                    if (result && result.success) {
                        console.log("Game starting initiated");
                    } else {
                        alert(`Failed to start game: ${result?.message || 'Unknown error'}`);
                    }
                });
            } else {
                console.warn("Cannot start game: conditions not met", { connected, inWaitingLobby, isHost });
            }
        });
    } else {
        console.error("Start Game button not found in DOM");
    }
    
    // Just verify the Leave Room button exists but don't add another event listener
    // since we already have one defined above
    if (leaveRoomBtn) {
        console.log("Leave Room button exists and is ready", leaveRoomBtn);
    } else {
        console.error("Leave Room button not found in DOM");
    }
    
    // Force initial display state
    showLobby();
    
    // Start the game loop
    requestAnimationFrame(gameLoop);
});

// New UI update functions
function updatePlayerListUI(playerList) {
    // Clear current list
    waitingPlayersList.innerHTML = '';
    
    // Add each player to the list
    playerList.forEach(player => {
        const listItem = document.createElement('li');
        listItem.textContent = player.username;
        
        // Add host badge if player is the host
        if (player.is_host) {
            const hostBadge = document.createElement('span');
            hostBadge.className = 'host-badge';
            hostBadge.textContent = 'HOST';
            listItem.appendChild(hostBadge);
        }
        
        waitingPlayersList.appendChild(listItem);
    });
    
    // Update start game button state (if we're the host)
    if (isHost && startGameBtn) {
        startGameBtn.disabled = playerList.length < 1; // Enable if at least 1 player
    }
}

function updateHostUI() {
    if (isHost) {
        hostControls.classList.remove('hidden');
        guestWaitingMessage.classList.add('hidden');
    } else {
        hostControls.classList.add('hidden');
        guestWaitingMessage.classList.remove('hidden');
    }
} 