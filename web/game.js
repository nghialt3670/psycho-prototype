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

// Remote player tracking - use simpler buffer approach to match client.py
const remotePositions = {};  // Maps position_index -> player data
const remotePlayerBuffer = {};  // position_index -> {current: {x,y}, target: {x,y}, last_update: time}
const INTERPOLATION_DURATION = 200;  // ms to interpolate between positions

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

// Network/Simulation settings
const POSITION_UPDATE_RATE = 33; // ~30 updates per second (was 50)
const GAME_STATE_REQUEST_RATE = 150; // Request state more frequently (was 200)
let lastPositionUpdateTime = 0;
let lastStateRequestTime = 0;
let serverTimeOffset = 0; // Estimated difference between client and server time

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

// Network settings display
let networkDebugEnabled = false;
document.addEventListener('keydown', (e) => {
    if (e.key === 'F2') {
        networkDebugEnabled = !networkDebugEnabled;
    }
});

// Socket.IO event handlers
socket.on('connect', () => {
    connected = true;
    clientSid = socket.id;
    inLobby = true;
    connectionStatus.textContent = 'Status: Connected';
    
    // Request a short burst of pings to establish server-client time difference
    measurePingBurst();
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
    // Immediately request fresh state to see new player
    requestGameState();
});

socket.on('player_left', (data) => {
    // Server will broadcast updated game state
    // Immediately request fresh state to update player list
    requestGameState();
});

// Ping response handler (no longer used in burst mode)
socket.on('pong', () => {
    // Only used if server sends a broadcast pong (fallback)
    if (lastPingTime > 0) {
        const endTime = performance.now();
        ping = Math.round(endTime - lastPingTime);
        updatePingDisplay();
    }
});

function measurePing() {
    if (connected) {
        lastPingTime = performance.now();
        socket.emit('ping', {}, (response) => {
            const endTime = performance.now();
            ping = Math.round(endTime - lastPingTime);
            updatePingDisplay();
            
            // Progressive adjustment of server time offset (weighted average)
            // Give 80% weight to existing value, 20% to new measurement
            serverTimeOffset = Math.round(serverTimeOffset * 0.8 + (ping / 2) * 0.2);
            
            // Schedule next ping measurement
            setTimeout(measurePing, PING_INTERVAL);
        });
    }
}

// Game functions
function resetGameState() {
    inRoom = false;
    inLobby = true;
    
    // Clear all remote player data
    for (const key in remotePositions) {
        delete remotePositions[key];
    }
    
    // Clear interpolation buffer
    for (const key in remotePlayerBuffer) {
        delete remotePlayerBuffer[key];
    }
    
    walls = [];
    cameraX = 0;
    cameraY = 0;
    
    localPlayer.x = 0;
    localPlayer.y = 0;
    localPlayer.color = null;
    localPlayer.positionIndex = -1;
}

// Request the full game state from server
function requestGameState() {
    if (connected && inRoom) {
        socket.emit('get_game_state', {}, (result) => {
            if (result && result.success && result.game_state) {
                processGameState(result.game_state);
            }
        });
    }
}

function processGameState(data) {
    const currentTime = performance.now();
    
    if (!data || typeof data !== 'object') {
        console.error("Received invalid game state data");
        return;
    }
    
    // CRITICAL: Clear remote positions first to avoid ghost players
    for (const key in remotePositions) {
        delete remotePositions[key];
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
            
            // Convert color array to CSS color
            const colorArray = playerInfo.color;
            const cssColor = `rgb(${colorArray[0]}, ${colorArray[1]}, ${colorArray[2]})`;
            
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
            
            // Store remote player data in standard position dict for rendering
            remotePositions[positionIndex] = {
                x: playerInfo.x,
                y: playerInfo.y,
                color: cssColor
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

function measurePingBurst(sampleCount = 5) {
    let samples = 0;
    let totalOffset = 0;
    
    function samplePing() {
        if (connected && samples < sampleCount) {
            lastPingTime = performance.now();
            socket.emit('ping', {}, (response) => {
                const endTime = performance.now();
                ping = Math.round(endTime - lastPingTime);
                
                // Update running average of server time offset
                totalOffset += ping / 2;
                samples++;
                
                // Schedule next sample
                setTimeout(samplePing, 200);
                
                // Update display
                updatePingDisplay();
            });
        } else {
            // All samples collected, calculate average
            if (samples > 0) {
                serverTimeOffset = Math.round(totalOffset / samples);
            }
            
            // Schedule regular ping measurement
            setTimeout(measurePing, PING_INTERVAL);
        }
    }
    
    // Start the burst sampling
    samplePing();
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

function updateRemotePlayers(currentTime) {
    // Update interpolated positions for all remote players in buffer
    for (const idx in remotePlayerBuffer) {
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
            
            // Simple linear interpolation between current and target
            playerData.current.x = playerData.current.x + (playerData.target.x - playerData.current.x) * progress;
            playerData.current.y = playerData.current.y + (playerData.target.y - playerData.current.y) * progress;
        }
    }
}

function sendPositionUpdate(x, y) {
    if (connected && inRoom) {
        try {
            // Update the local player dict for consistency
            localPlayer.x = x;
            localPlayer.y = y;
            
            // Get more accurate time with the server offset
            const clientTime = performance.now();
            const estimatedServerTime = clientTime + serverTimeOffset;
            
            // Send to server asynchronously with metadata
            socket.emit('update_position', {
                x, 
                y,
                timestamp: estimatedServerTime,
                client_time: clientTime,
                ping: ping
            });
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

function drawNetworkDebug() {
    if (!networkDebugEnabled) return;
    
    const remotePlayerCount = Object.keys(remotePositions).length;
    
    const debugX = 10;
    const debugY = SCREEN_HEIGHT - 100;
    const lineHeight = 15;
    
    ctx.fillStyle = 'rgba(0, 0, 0, 0.7)';
    ctx.fillRect(debugX, debugY, 300, 90);
    
    ctx.fillStyle = 'white';
    ctx.font = '12px monospace';
    ctx.fillText(`Ping: ${ping}ms | Server Time Offset: ${Math.round(serverTimeOffset)}ms`, debugX + 10, debugY + lineHeight);
    ctx.fillText(`Remote Players: ${remotePlayerCount}`, debugX + 10, debugY + lineHeight * 2);
    ctx.fillText(`Last Position Update: ${Math.round(performance.now() - lastPositionUpdateTime)}ms ago`, debugX + 10, debugY + lineHeight * 3);
    ctx.fillText(`Last State Request: ${Math.round(performance.now() - lastStateRequestTime)}ms ago`, debugX + 10, debugY + lineHeight * 4);
    
    const updateRate = 1000 / POSITION_UPDATE_RATE;
    const requestRate = 1000 / GAME_STATE_REQUEST_RATE;
    ctx.fillText(`Update Rate: ${updateRate}ms | Request Rate: ${requestRate}ms`, debugX + 10, debugY + lineHeight * 5);
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
    
    // Draw ONLY remote players using their interpolated positions
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
            drawPlayer(interpolatedX, interpolatedY, playerData.color, false);
        }
    }
    
    // Draw local player last (on top)
    if (localPlayer.color) {
        drawPlayer(playerX, playerY, localPlayer.color, true);
    }
    
    // Draw mini-map
    drawMiniMap();
    
    // Draw network debug info if enabled
    if (networkDebugEnabled) {
        drawNetworkDebug();
    }
}

// Game loop
let lastUpdateTime = 0;

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
        
        // More frequent position updates when moving
        if (movement.moved && connected && currentTime - lastPositionUpdateTime > POSITION_UPDATE_RATE) {
            sendPositionUpdate(movement.newX, movement.newY);
            lastPositionUpdateTime = currentTime;
        }
        
        // Regularly request game state for accurate remote player positions
        if (currentTime - lastStateRequestTime > GAME_STATE_REQUEST_RATE) {
            requestGameState();
            lastStateRequestTime = currentTime;
        }
        
        // Update interpolated positions for remote players
        updateRemotePlayers(currentTime);
        
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
                // Make sure color is properly formatted as CSS color
                if (Array.isArray(result.color)) {
                    localPlayer.color = `rgb(${result.color[0]}, ${result.color[1]}, ${result.color[2]})`;
                } else {
                    localPlayer.color = result.color;
                }
                
                localPlayer.positionIndex = result.position_index || 0;
                walls = result.walls || [];
                playerX = result.x || 80;
                playerY = result.y || 80;
                localPlayer.x = playerX;
                localPlayer.y = playerY;
                
                // Process initial game state if provided
                if (result.game_state) {
                    processGameState(result.game_state);
                }
                
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
                // Make sure color is properly formatted as CSS color
                if (Array.isArray(result.color)) {
                    localPlayer.color = `rgb(${result.color[0]}, ${result.color[1]}, ${result.color[2]})`;
                } else {
                    localPlayer.color = result.color;
                }
                
                localPlayer.positionIndex = result.position_index || 0;
                walls = result.walls || [];
                playerX = result.x || (MAP_WIDTH - 120);
                playerY = result.y || (MAP_HEIGHT - 120);
                localPlayer.x = playerX;
                localPlayer.y = playerY;
                
                // Process initial game state if provided
                if (result.game_state) {
                    processGameState(result.game_state);
                }
                
                // Show game screen
                showGame();
            } else {
                alert(`Failed to join room: ${result?.message || 'Unknown error'}`);
            }
        });
    }
});

function showLobby() {
    console.log("Showing lobby screen");
    if (lobbyScreen && gameScreen) {
        lobbyScreen.style.display = 'flex';
        lobbyScreen.classList.remove('hidden');
        
        gameScreen.style.display = 'none';
        gameScreen.classList.add('hidden');
        
        console.log("Updated: Lobby:", lobbyScreen.className, lobbyScreen.style.display);
        console.log("Updated: Game:", gameScreen.className, gameScreen.style.display);
    } else {
        console.error("Screen elements not found!", lobbyScreen, gameScreen);
    }
}

function showGame() {
    console.log("Showing game screen");
    if (lobbyScreen && gameScreen) {
        gameScreen.style.display = 'flex';
        gameScreen.classList.remove('hidden');
        
        lobbyScreen.style.display = 'none';
        lobbyScreen.classList.add('hidden');
        
        console.log("Updated: Lobby:", lobbyScreen.className, lobbyScreen.style.display);
        console.log("Updated: Game:", gameScreen.className, gameScreen.style.display);
    } else {
        console.error("Screen elements not found!", lobbyScreen, gameScreen);
    }
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

// Add a check at the beginning of the game function to ensure UI is correctly displayed
document.addEventListener('DOMContentLoaded', function() {
    console.log("DOM fully loaded");
    
    // Check that our UI elements are correctly initialized
    if (!lobbyScreen) {
        console.error("Lobby screen element not found!");
        lobbyScreen = document.getElementById('lobby');
    }
    
    if (!gameScreen) {
        console.error("Game screen element not found!");
        gameScreen = document.getElementById('game');
    }
    
    // Log initial state
    console.log("Initial lobby display:", lobbyScreen?.className);
    console.log("Initial game display:", gameScreen?.className);
    
    // Force initial display state
    showLobby();
});

// Initialize game
requestAnimationFrame(gameLoop); 