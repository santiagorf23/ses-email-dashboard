/**
 * Configuración centralizada del SES Mail Dashboard
 * 
 * Cambiar API_BASE_URL si el backend está en otra dirección/puerto.
 * En producción, esta variable debería ser inyectada por el servidor web.
 */
const CONFIG = {
    API_BASE_URL: window.location.hostname === 'localhost' 
        ? 'http://localhost:8000/api' 
        : `${window.location.protocol}//${window.location.hostname}:8000/api`,
    
    AUTO_REFRESH_INTERVAL: 60000, // 60 segundos
    
    // Límites de paginación
    DEFAULT_PAGE_SIZE: 25,
    MAX_PAGE_SIZE: 100,
    
    // Timeouts
    REQUEST_TIMEOUT: 30000, // 30 segundos

    // Auth
    TOKEN_KEY: 'ses_token',

    // Timezone
    TIMEZONE: 'America/Bogota',

    // Debug mode
    DEBUG: false,
};

// Conditional logger - only outputs when DEBUG is true
const logger = {
    log: (...args) => { if (CONFIG.DEBUG) console.log(...args); },
    warn: (...args) => { if (CONFIG.DEBUG) console.warn(...args); },
    error: (...args) => { if (CONFIG.DEBUG) console.error(...args); },
};

// Exportar para uso en módulos
if (typeof module !== 'undefined' && module.exports) {
    module.exports = CONFIG;
}
