// Hardcoded configuration values
window.ENV = {
    // Server configuration
    SERVER_URL: 'http://localhost:5000',
    
    // Game configuration
    DEBUG: false,
    
    // Version information
    VERSION: '1.0.0'
};

// Check URL parameters (these override the hardcoded values)
const urlParams = new URLSearchParams(window.location.search);
const serverParam = urlParams.get('server');
if (serverParam) {
    window.ENV.SERVER_URL = serverParam;
    console.log('Server URL overridden by URL parameter');
}

// Check if we have a global config override
if (window.SERVER_CONFIG && window.SERVER_CONFIG.serverUrl) {
    window.ENV.SERVER_URL = window.SERVER_CONFIG.serverUrl;
    console.log('Server URL overridden by SERVER_CONFIG');
}

// Update the UI with server URL
if (document.getElementById('server-url')) {
    document.getElementById('server-url').textContent = window.ENV.SERVER_URL;
}

// Dispatch an event to notify the game that config is loaded
document.dispatchEvent(new Event('configLoaded')); 