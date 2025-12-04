/**
 * SSE (Server-Sent Events) Handler for Launcher Web
 * Manages real-time streaming connections for logs and metrics
 */

class SSEHandler {
  constructor() {
    this.connections = new Map();
  }

  /**
   * Connect to an SSE endpoint
   * @param {string} endpoint - The SSE endpoint URL
   * @param {function} onMessage - Callback for incoming messages
   * @param {function} onError - Optional callback for errors
   * @returns {EventSource} The EventSource instance
   */
  connect(endpoint, onMessage, onError = null) {
    // Close existing connection if any
    if (this.connections.has(endpoint)) {
      this.disconnect(endpoint);
    }

    console.log(`[SSE] Connecting to ${endpoint}`);

    const eventSource = new EventSource(endpoint);

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        onMessage(data);
      } catch (error) {
        console.error('[SSE] Parse error:', error, 'Raw data:', event.data);
      }
    };

    eventSource.onerror = (error) => {
      console.error('[SSE] Connection error:', endpoint, error);

      // Check if connection is closed
      if (eventSource.readyState === EventSource.CLOSED) {
        console.log(`[SSE] Connection closed: ${endpoint}`);
        this.disconnect(endpoint);
      }

      if (onError) {
        onError(error);
      }
    };

    eventSource.onopen = () => {
      console.log(`[SSE] Connection opened: ${endpoint}`);
    };

    this.connections.set(endpoint, eventSource);
    return eventSource;
  }

  /**
   * Disconnect from an SSE endpoint
   * @param {string} endpoint - The SSE endpoint URL
   */
  disconnect(endpoint) {
    const connection = this.connections.get(endpoint);
    if (connection) {
      console.log(`[SSE] Disconnecting from ${endpoint}`);
      connection.close();
      this.connections.delete(endpoint);
    }
  }

  /**
   * Disconnect from all SSE endpoints
   */
  disconnectAll() {
    console.log('[SSE] Disconnecting from all endpoints');
    this.connections.forEach((connection, endpoint) => {
      console.log(`[SSE] Closing ${endpoint}`);
      connection.close();
    });
    this.connections.clear();
  }

  /**
   * Check if connected to an endpoint
   * @param {string} endpoint - The SSE endpoint URL
   * @returns {boolean} True if connected
   */
  isConnected(endpoint) {
    const connection = this.connections.get(endpoint);
    return connection && connection.readyState === EventSource.OPEN;
  }

  /**
   * Get connection status for an endpoint
   * @param {string} endpoint - The SSE endpoint URL
   * @returns {string} Connection status (CONNECTING, OPEN, CLOSED, or NONE)
   */
  getConnectionStatus(endpoint) {
    const connection = this.connections.get(endpoint);
    if (!connection) return 'NONE';

    switch (connection.readyState) {
      case EventSource.CONNECTING:
        return 'CONNECTING';
      case EventSource.OPEN:
        return 'OPEN';
      case EventSource.CLOSED:
        return 'CLOSED';
      default:
        return 'UNKNOWN';
    }
  }
}

// Export for use in other scripts
window.SSEHandler = SSEHandler;
