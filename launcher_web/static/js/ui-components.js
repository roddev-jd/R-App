/**
 * UI Components for Launcher Web
 * Manages UI state and updates
 */

class UIComponents {
  constructor() {
    this.elements = this.cacheElements();
    this.state = {
      serverRunning: false,
      autoScroll: true,
      logsExpanded: false
    };
  }

  /**
   * Cache all DOM elements for efficient access
   */
  cacheElements() {
    return {
      // Status
      statusIndicator: document.getElementById('status-indicator'),
      statusText: document.getElementById('status-text'),
      uptimeText: document.getElementById('uptime-text'),
      urlLink: document.getElementById('url-link'),
      urlDisplay: document.getElementById('url-display'),

      // Buttons
      startStopBtn: document.getElementById('start-stop-btn'),
      reopenBrowserBtn: document.getElementById('reopen-browser-btn'),
      checkUpdatesBtn: document.getElementById('check-updates-btn'),
      installUpdateBtn: document.getElementById('install-update-btn'),
      rollbackBtn: document.getElementById('rollback-btn'),
      clearLogsBtn: document.getElementById('clear-logs-btn'),

      // Monitoring
      cpuBar: document.getElementById('cpu-bar'),
      cpuValue: document.getElementById('cpu-value'),
      memBar: document.getElementById('mem-bar'),
      memValue: document.getElementById('mem-value'),

      // Updates
      lastChecked: document.getElementById('last-checked'),
      updateStatus: document.getElementById('update-status'),
      updateAvailablePanel: document.getElementById('update-available-panel'),
      newVersion: document.getElementById('new-version'),

      // Logs
      logsHeader: document.getElementById('logs-header'),
      logsContent: document.getElementById('logs-content'),
      logsChevron: document.getElementById('logs-chevron'),
      logsOutput: document.getElementById('logs-output'),
      autoScrollCheckbox: document.getElementById('auto-scroll-checkbox'),

      // Loading
      loadingOverlay: document.getElementById('loading-overlay'),
      loadingText: document.getElementById('loading-text')
    };
  }

  // ===== Server Status Methods =====

  /**
   * Update UI to show server running state
   */
  setServerRunning(port, url, pid) {
    this.state.serverRunning = true;

    // Update status indicator
    this.elements.statusIndicator.className = 'status-indicator running';

    // Update status text
    this.elements.statusText.textContent = `Servidor ejecutándose en puerto ${port} (PID: ${pid})`;

    // Show URL link
    this.elements.urlLink.href = url;
    this.elements.urlDisplay.textContent = url;
    this.elements.urlLink.style.display = 'inline-flex';

    // Update button
    const btn = this.elements.startStopBtn;
    btn.innerHTML = '<i class="bi bi-stop-circle-fill"></i><span>Detener Servidor</span>';
    btn.classList.add('btn-stop');

    // Enable reopen button
    this.elements.reopenBrowserBtn.disabled = false;

    // Show info banner
    const infoBanner = document.getElementById('info-banner');
    if (infoBanner) {
      infoBanner.style.display = 'block';
    }
  }

  /**
   * Update UI to show server stopped state
   */
  setServerStopped() {
    this.state.serverRunning = false;

    // Update status indicator
    this.elements.statusIndicator.className = 'status-indicator stopped';

    // Update status text
    this.elements.statusText.textContent = 'Servidor detenido';
    this.elements.uptimeText.textContent = 'Uptime: --:--:--';

    // Hide URL link
    this.elements.urlLink.style.display = 'none';

    // Update button
    const btn = this.elements.startStopBtn;
    btn.innerHTML = '<i class="bi bi-play-circle-fill"></i><span>Iniciar Servidor</span>';
    btn.classList.remove('btn-stop');

    // Disable reopen button
    this.elements.reopenBrowserBtn.disabled = true;

    // Hide info banner
    const infoBanner = document.getElementById('info-banner');
    if (infoBanner) {
      infoBanner.style.display = 'none';
    }

    // Reset monitoring
    this.resetMonitoring();
  }

  /**
   * Update uptime display
   */
  updateUptime(uptimeFormatted) {
    this.elements.uptimeText.textContent = `Uptime: ${uptimeFormatted}`;
  }

  // ===== Monitoring Methods =====

  /**
   * Update system metrics display
   */
  updateMetrics(cpu, memory, memoryFormatted) {
    const cpuPercent = Math.min(Math.max(cpu, 0), 100);
    const memPercent = Math.min(Math.max(memory, 0), 100);

    // Update CPU
    this.elements.cpuBar.style.width = `${cpuPercent}%`;
    this.elements.cpuValue.textContent = `${cpuPercent.toFixed(1)}%`;
    this.elements.cpuBar.className = `progress-bar ${this.getProgressClass(cpuPercent)}`;

    // Update Memory
    this.elements.memBar.style.width = `${memPercent}%`;
    this.elements.memValue.textContent = memoryFormatted;
    this.elements.memBar.className = `progress-bar ${this.getProgressClass(memPercent)}`;
  }

  /**
   * Get progress bar class based on percentage
   */
  getProgressClass(percent) {
    if (percent < 50) return 'low';
    if (percent < 80) return 'medium';
    return 'high';
  }

  /**
   * Reset monitoring displays to zero
   */
  resetMonitoring() {
    this.elements.cpuBar.style.width = '0%';
    this.elements.cpuValue.textContent = '0%';
    this.elements.cpuBar.className = 'progress-bar low';

    this.elements.memBar.style.width = '0%';
    this.elements.memValue.textContent = '0 MB';
    this.elements.memBar.className = 'progress-bar low';
  }

  // ===== Logs Methods =====

  /**
   * Append a log line to the output
   */
  appendLog(timestamp, level, message) {
    const logLine = document.createElement('div');
    logLine.className = `log-line log-${level.toLowerCase()}`;
    logLine.textContent = `[${timestamp}] ${level} ${message}`;

    this.elements.logsOutput.appendChild(logLine);

    // Auto-scroll if enabled
    if (this.state.autoScroll) {
      this.elements.logsOutput.scrollTop = this.elements.logsOutput.scrollHeight;
    }

    // Limit log lines to 1000
    const lines = this.elements.logsOutput.children;
    if (lines.length > 1000) {
      this.elements.logsOutput.removeChild(lines[0]);
    }
  }

  /**
   * Clear all logs
   */
  clearLogs() {
    this.elements.logsOutput.innerHTML = '';
  }

  /**
   * Toggle logs section visibility
   */
  toggleLogs() {
    this.state.logsExpanded = !this.state.logsExpanded;

    if (this.state.logsExpanded) {
      this.elements.logsContent.style.display = 'block';
      this.elements.logsChevron.className = 'bi bi-chevron-down';
    } else {
      this.elements.logsContent.style.display = 'none';
      this.elements.logsChevron.className = 'bi bi-chevron-right';
    }
  }

  // ===== Update Methods =====

  /**
   * Update "last checked" timestamp
   */
  updateLastChecked(timestamp) {
    const date = new Date(timestamp);
    this.elements.lastChecked.textContent = date.toLocaleString();
  }

  /**
   * Show update available banner
   */
  showUpdateAvailable(version) {
    this.elements.updateStatus.textContent = 'Actualización disponible';
    this.elements.updateStatus.className = 'badge-update-available';
    this.elements.newVersion.textContent = version;
    this.elements.updateAvailablePanel.style.display = 'block';
    this.elements.installUpdateBtn.style.display = 'inline-flex';
  }

  /**
   * Show up to date status
   */
  showUpToDate() {
    this.elements.updateStatus.textContent = 'Actualizado';
    this.elements.updateStatus.className = 'badge-up-to-date';
    this.elements.updateAvailablePanel.style.display = 'none';
    this.elements.installUpdateBtn.style.display = 'none';
  }

  /**
   * Update rollback button state
   */
  updateRollbackButton(enabled) {
    this.elements.rollbackBtn.disabled = !enabled;
  }

  // ===== Loading Overlay Methods =====

  /**
   * Show loading overlay
   */
  showLoading(message = 'Procesando...') {
    this.elements.loadingText.textContent = message;
    this.elements.loadingOverlay.style.display = 'flex';
  }

  /**
   * Hide loading overlay
   */
  hideLoading() {
    this.elements.loadingOverlay.style.display = 'none';
  }

  // ===== Dialog Methods =====

  /**
   * Show error dialog
   */
  showError(title, message) {
    alert(`❌ ${title}\n\n${message}`);
  }

  /**
   * Show success dialog
   */
  showSuccess(title, message) {
    alert(`✅ ${title}\n\n${message}`);
  }

  /**
   * Show confirmation dialog
   */
  confirm(message) {
    return confirm(message);
  }
}

// Export for use in other scripts
window.UIComponents = UIComponents;
