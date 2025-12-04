/**
 * API Client for Launcher Web
 * Handles all REST API communication with the backend
 */

class LauncherAPI {
  constructor(baseURL = '') {
    this.baseURL = baseURL;
  }

  /**
   * Generic request method with error handling
   */
  async request(endpoint, options = {}) {
    try {
      const response = await fetch(`${this.baseURL}${endpoint}`, {
        ...options,
        headers: {
          'Content-Type': 'application/json',
          ...options.headers
        }
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || data.error || `Request failed with status ${response.status}`);
      }

      return data;
    } catch (error) {
      console.error(`API Error [${endpoint}]:`, error);
      throw error;
    }
  }

  // ===== Server Control Methods =====

  /**
   * Start the main FastAPI server
   * @returns {Promise<Object>} Server start response
   */
  async startServer() {
    return this.request('/api/server/start', { method: 'POST' });
  }

  /**
   * Stop the main FastAPI server
   * @returns {Promise<Object>} Server stop response
   */
  async stopServer() {
    return this.request('/api/server/stop', { method: 'POST' });
  }

  /**
   * Get current server status
   * @returns {Promise<Object>} Server status
   */
  async getServerStatus() {
    return this.request('/api/server/status');
  }

  /**
   * Restart the main FastAPI server
   * @returns {Promise<Object>} Server restart response
   */
  async restartServer() {
    return this.request('/api/server/restart', { method: 'POST' });
  }

  // ===== Configuration Methods =====

  /**
   * Get launcher configuration
   * @returns {Promise<Object>} Configuration object
   */
  async getConfig() {
    return this.request('/api/config');
  }

  /**
   * Update launcher configuration
   * @param {Object} config - Configuration updates
   * @returns {Promise<Object>} Updated configuration
   */
  async updateConfig(config) {
    return this.request('/api/config', {
      method: 'PATCH',
      body: JSON.stringify(config)
    });
  }

  // ===== Update Methods =====

  /**
   * Check for available updates from GitHub
   * @returns {Promise<Object>} Update check response
   */
  async checkForUpdates() {
    return this.request('/api/updates/check');
  }

  /**
   * Install available update
   * @returns {Promise<Object>} Installation response
   */
  async installUpdate() {
    return this.request('/api/updates/install', { method: 'POST' });
  }

  /**
   * Rollback to previous version
   * @returns {Promise<Object>} Rollback response
   */
  async rollback() {
    return this.request('/api/updates/rollback', { method: 'POST' });
  }

  /**
   * Get backup status
   * @returns {Promise<Object>} Backup status
   */
  async getBackupStatus() {
    return this.request('/api/updates/backup-status');
  }

  // ===== Monitoring Methods =====

  /**
   * Get current system metrics
   * @returns {Promise<Object>} System metrics
   */
  async getMetrics() {
    return this.request('/api/monitor/metrics');
  }
}

// Export for use in other scripts
window.LauncherAPI = LauncherAPI;
