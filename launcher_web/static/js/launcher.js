/**
 * Main Launcher Application
 * Orchestrates all components and manages application flow
 */

class LauncherApp {
  constructor() {
    this.api = new LauncherAPI();
    this.sse = new SSEHandler();
    this.ui = new UIComponents();

    this.statusPollInterval = null;
    this.uptimePollInterval = null;
    this.currentUrl = null;

    // Bind beforeunload warning
    this.bindBeforeUnloadWarning();
  }

  /**
   * Initialize the application
   */
  async init() {
    console.log('Initializing Launcher...');

    // Bind event listeners
    this.bindEvents();

    // Load initial state
    await this.loadInitialState();

    // Start status polling
    this.startStatusPolling();

    console.log('Launcher initialized');
  }

  /**
   * Bind all event listeners
   */
  bindEvents() {
    // Server control
    this.ui.elements.startStopBtn.addEventListener('click', () => this.toggleServer());
    this.ui.elements.reopenBrowserBtn.addEventListener('click', () => this.reopenBrowser());

    // Updates
    this.ui.elements.checkUpdatesBtn.addEventListener('click', () => this.checkForUpdates());
    this.ui.elements.installUpdateBtn.addEventListener('click', () => this.installUpdate());
    this.ui.elements.rollbackBtn.addEventListener('click', () => this.rollback());

    // Logs
    this.ui.elements.logsHeader.addEventListener('click', () => this.ui.toggleLogs());
    this.ui.elements.autoScrollCheckbox.addEventListener('change', (e) => {
      this.ui.state.autoScroll = e.target.checked;
    });
    this.ui.elements.clearLogsBtn.addEventListener('click', () => this.ui.clearLogs());

    // URL link
    this.ui.elements.urlLink.addEventListener('click', (e) => {
      e.preventDefault();
      window.open(this.currentUrl, '_blank');
    });
  }

  /**
   * Bind beforeunload warning
   * Shows a confirmation dialog when user tries to close the tab while server is running
   */
  bindBeforeUnloadWarning() {
    window.addEventListener('beforeunload', (event) => {
      // Solo advertir si el servidor está corriendo
      if (this.ui.state.serverRunning) {
        // Prevenir cierre sin confirmación
        event.preventDefault();

        // Chrome requiere returnValue para mostrar diálogo
        event.returnValue = '';

        // Mensaje (no se muestra en navegadores modernos por seguridad,
        // pero el diálogo de confirmación sí aparece)
        return '¿Seguro que quieres cerrar? El servidor seguirá ejecutándose.';
      }
    });
  }

  /**
   * Load initial application state
   */
  async loadInitialState() {
    try {
      // Get server status
      const status = await this.api.getServerStatus();
      if (status.running) {
        this.currentUrl = status.url;
        this.ui.setServerRunning(status.port, status.url, status.pid);
        this.ui.updateUptime(status.uptime_formatted);
        this.startServerMonitoring();
      }

      // Get backup status
      const backup = await this.api.getBackupStatus();
      this.ui.updateRollbackButton(backup.has_backup);

      console.log('Initial state loaded');
    } catch (error) {
      console.error('Failed to load initial state:', error);
      this.ui.showError('Error de Inicialización', 'No se pudo cargar el estado inicial.');
    }
  }

  /**
   * Start polling server status
   */
  startStatusPolling() {
    // Poll server status every 5 seconds
    this.statusPollInterval = setInterval(async () => {
      try {
        const status = await this.api.getServerStatus();

        // Server started externally
        if (status.running && !this.ui.state.serverRunning) {
          this.currentUrl = status.url;
          this.ui.setServerRunning(status.port, status.url, status.pid);
          this.startServerMonitoring();
        }
        // Server stopped externally
        else if (!status.running && this.ui.state.serverRunning) {
          this.ui.setServerStopped();
          this.stopServerMonitoring();
          this.currentUrl = null;
        }
      } catch (error) {
        console.error('Status poll error:', error);
      }
    }, 5000);
  }

  /**
   * Start server monitoring (SSE + uptime polling)
   */
  startServerMonitoring() {
    // Start SSE for logs
    this.sse.connect('/api/sse/logs', (data) => {
      this.ui.appendLog(data.timestamp, data.level, data.message);
    });

    // Start SSE for metrics
    this.sse.connect('/api/sse/metrics', (data) => {
      this.ui.updateMetrics(
        data.cpu_percent,
        data.memory_percent,
        data.memory_formatted
      );
    });

    // Poll uptime every second
    this.uptimePollInterval = setInterval(async () => {
      try {
        const status = await this.api.getServerStatus();
        if (status.running) {
          this.ui.updateUptime(status.uptime_formatted);
        }
      } catch (error) {
        console.error('Uptime poll error:', error);
      }
    }, 1000);
  }

  /**
   * Stop server monitoring
   */
  stopServerMonitoring() {
    this.sse.disconnectAll();

    if (this.uptimePollInterval) {
      clearInterval(this.uptimePollInterval);
      this.uptimePollInterval = null;
    }
  }

  /**
   * Toggle server (start or stop)
   */
  async toggleServer() {
    if (this.ui.state.serverRunning) {
      await this.stopServer();
    } else {
      await this.startServer();
    }
  }

  /**
   * Start the main server
   */
  async startServer() {
    try {
      this.ui.showLoading('Iniciando servidor...');

      const result = await this.api.startServer();

      if (result.success) {
        this.currentUrl = result.url;
        this.ui.setServerRunning(result.port, result.url, result.pid);
        this.startServerMonitoring();

        // Get config to check auto-open
        const config = await this.api.getConfig();
        if (config.auto_open_browser) {
          setTimeout(() => window.open(result.url, '_blank'), 1000);
        }
      } else {
        this.ui.showError('Error al Iniciar', result.message);
      }
    } catch (error) {
      console.error('Start server error:', error);
      this.ui.showError('Error', `No se pudo iniciar el servidor:\n${error.message}`);
    } finally {
      this.ui.hideLoading();
    }
  }

  /**
   * Stop the main server
   */
  async stopServer() {
    try {
      this.ui.showLoading('Deteniendo servidor...');

      const result = await this.api.stopServer();

      if (result.success) {
        this.ui.setServerStopped();
        this.stopServerMonitoring();
        this.currentUrl = null;
      } else {
        this.ui.showError('Error al Detener', result.message);
      }
    } catch (error) {
      console.error('Stop server error:', error);
      this.ui.showError('Error', `No se pudo detener el servidor:\n${error.message}`);
    } finally {
      this.ui.hideLoading();
    }
  }

  /**
   * Reopen browser to main application
   */
  reopenBrowser() {
    if (this.currentUrl) {
      window.open(this.currentUrl, '_blank');
    }
  }

  /**
   * Check for updates
   */
  async checkForUpdates() {
    try {
      this.ui.showLoading('Verificando actualizaciones...');

      const result = await this.api.checkForUpdates();

      this.ui.updateLastChecked(result.last_checked);

      if (result.update_available) {
        this.ui.showUpdateAvailable(result.latest_version);
        this.ui.showSuccess(
          'Actualización Disponible',
          `La versión ${result.latest_version} está disponible.`
        );
      } else {
        this.ui.showUpToDate();
        this.ui.showSuccess('Actualizado', 'Estás usando la última versión.');
      }
    } catch (error) {
      console.error('Check updates error:', error);
      this.ui.showError('Error', `No se pudo verificar actualizaciones:\n${error.message}`);
      this.ui.updateLastChecked(new Date().toISOString());
    } finally {
      this.ui.hideLoading();
    }
  }

  /**
   * Install update
   */
  async installUpdate() {
    if (!this.ui.confirm('¿Instalar actualización?\n\nEl servidor se detendrá durante la instalación.')) {
      return;
    }

    try {
      this.ui.showLoading('Instalando actualización...');

      // Listen for update progress via SSE
      this.sse.connect('/api/sse/update-progress', (data) => {
        this.ui.showLoading(`${data.status} (${data.percent}%)`);
      });

      const result = await this.api.installUpdate();

      if (result.success) {
        this.ui.showSuccess(
          'Actualización Completa',
          '¡Aplicación actualizada exitosamente!\n\nLa página se recargará en 2 segundos.'
        );

        // Reload page to get new version
        setTimeout(() => location.reload(), 2000);
      } else {
        this.ui.showError('Actualización Fallida', result.message);
      }
    } catch (error) {
      console.error('Install update error:', error);
      this.ui.showError('Error', `No se pudo instalar la actualización:\n${error.message}`);
    } finally {
      this.sse.disconnect('/api/sse/update-progress');
      this.ui.hideLoading();
    }
  }

  /**
   * Rollback to previous version
   */
  async rollback() {
    if (!this.ui.confirm('¿Restaurar versión anterior?\n\nEsta acción no se puede deshacer.')) {
      return;
    }

    try {
      this.ui.showLoading('Restaurando versión anterior...');

      const result = await this.api.rollback();

      if (result.success) {
        this.ui.showSuccess(
          'Rollback Completo',
          `Restaurado a versión ${result.backup_version}\n\nLa página se recargará en 2 segundos.`
        );

        // Reload page
        setTimeout(() => location.reload(), 2000);
      } else {
        this.ui.showError('Rollback Fallido', result.message);
      }
    } catch (error) {
      console.error('Rollback error:', error);
      this.ui.showError('Error', `No se pudo restaurar la versión:\n${error.message}`);
    } finally {
      this.ui.hideLoading();
    }
  }

  /**
   * Cleanup when page unloads
   */
  cleanup() {
    if (this.statusPollInterval) {
      clearInterval(this.statusPollInterval);
    }
    if (this.uptimePollInterval) {
      clearInterval(this.uptimePollInterval);
    }
    this.sse.disconnectAll();
  }
}

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
  const app = new LauncherApp();
  app.init();

  // Cleanup on page unload
  window.addEventListener('beforeunload', () => app.cleanup());

  // Make app available globally for debugging
  window.launcherApp = app;
});
