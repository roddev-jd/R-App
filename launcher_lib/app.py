"""
Suite Launcher Main Application

Integrates all managers and UI components to provide the complete launcher experience.
"""

import logging
import webbrowser
import threading
from datetime import datetime
from typing import Optional

import customtkinter as ctk

from .config_manager import ConfigManager
from .port_manager import PortManager
from .server_manager import ServerManager
from .update_manager import UpdateManager
from .system_monitor import SystemMonitor
from .ui.main_window import MainWindow
from .ui.update_dialog import UpdateDialog, UpdateCompleteDialog
from .ui.progress_dialog import ProgressDialog
from .ui.styles import configure_customtkinter_theme

logger = logging.getLogger(__name__)


class SuiteLauncher:
    """Main launcher application controller"""

    def __init__(self):
        """Initialize SuiteLauncher"""
        logger.info("Initializing SuiteLauncher")

        # Configure customtkinter theme
        configure_customtkinter_theme()

        # Initialize managers
        self.config = ConfigManager()
        self.port_manager = PortManager(self.config)
        self.server_manager = ServerManager(self.config)
        self.update_manager = UpdateManager(self.config)
        self.system_monitor = SystemMonitor()

        # Get current version
        self.version = self.config.get_current_version()

        # Create main window
        self.window = MainWindow(version=self.version)

        # Connect UI callbacks
        self._connect_callbacks()

        # UI update timers
        self.uptime_timer_id: Optional[str] = None
        self.monitor_timer_id: Optional[str] = None
        self.logs_timer_id: Optional[str] = None
        self.last_log_count: int = 0  # Track number of logs already displayed

        # Check for updates on startup (async)
        if self.config.should_check_for_updates():
            self.window.after(2000, self._check_for_updates_async)

        # Update backup availability
        self._update_backup_status()

        logger.info("SuiteLauncher initialized")

    def _connect_callbacks(self):
        """Connect UI callbacks to handler methods"""
        self.window.on_start_server = self.start_server
        self.window.on_stop_server = self.stop_server
        self.window.on_reopen_browser = self.reopen_browser
        self.window.on_check_updates = self.check_for_updates
        self.window.on_perform_update = self.perform_update
        self.window.on_rollback = self.perform_rollback
        self.window.on_close = self.on_close

    def run(self):
        """Run the launcher application"""
        logger.info("Starting launcher main loop")
        self.window.mainloop()

    # Server control methods

    def start_server(self):
        """Start the FastAPI server"""
        try:
            logger.info("Starting server...")

            # Find available port
            port = self.port_manager.find_available_port()
            logger.info(f"Selected port: {port}")

            # Start server
            if self.server_manager.start_server(port):
                # Update UI
                pid = self.server_manager.get_pid()
                url = self.server_manager.get_url()
                self.window.set_server_running(port, url, pid)

                # Attach system monitor
                self.system_monitor.attach_to_process(pid)

                # Start update timers
                self._start_update_timers()

                # Auto-open browser if configured
                if self.config.get_auto_open_browser():
                    self.window.after(1000, lambda: webbrowser.open(url))

                logger.info(f"Server started successfully on port {port}")
            else:
                logger.error("Failed to start server")
                self._show_error("Failed to Start Server", "Could not start the server. Check logs for details.")

        except RuntimeError as e:
            # All ports occupied
            logger.error(f"Port allocation failed: {e}")
            self._show_error(
                "No Ports Available",
                f"All ports in range {self.port_manager.min_port}-{self.port_manager.max_port} are occupied.\n\n"
                "Please close other applications using these ports and try again."
            )
        except Exception as e:
            logger.error(f"Error starting server: {e}")
            self._show_error("Error", f"An unexpected error occurred:\n{e}")

    def stop_server(self):
        """Stop the FastAPI server"""
        try:
            logger.info("Stopping server...")

            # Stop server
            if self.server_manager.stop_server():
                # Stop update timers
                self._stop_update_timers()

                # Detach system monitor
                self.system_monitor.detach()

                # Update UI
                self.window.set_server_stopped()

                logger.info("Server stopped successfully")
            else:
                logger.error("Failed to stop server")
                self._show_error("Failed to Stop Server", "Could not stop the server. Check logs for details.")

        except Exception as e:
            logger.error(f"Error stopping server: {e}")
            self._show_error("Error", f"An unexpected error occurred:\n{e}")

    def reopen_browser(self):
        """Reopen browser to server URL"""
        url = self.server_manager.get_url()
        if url:
            logger.info(f"Opening browser to {url}")
            webbrowser.open(url)
        else:
            logger.warning("Cannot reopen browser: server not running")

    # Update methods

    def check_for_updates(self):
        """Check for updates (user-triggered)"""
        self.window.set_update_checking()
        self.window.after(100, self._check_for_updates_async)

    def _check_for_updates_async(self):
        """Check for updates asynchronously"""
        def check():
            try:
                logger.info("Checking for updates...")
                update_info = self.update_manager.check_for_updates()

                # Update UI on main thread
                self.window.after(0, lambda: self._handle_update_check_result(update_info))

            except Exception as e:
                logger.error(f"Error checking for updates: {e}")
                self.window.after(0, lambda: self._handle_update_check_error(str(e)))

        thread = threading.Thread(target=check, daemon=True)
        thread.start()

    def _handle_update_check_result(self, update_info: Optional[dict]):
        """Handle update check result on main thread"""
        # Update last checked time
        now = datetime.now()
        time_str = now.strftime("%B %d, %Y at %I:%M %p")
        self.window.set_update_checked(time_str)

        if update_info:
            # Update available
            logger.info(f"Update available: {update_info['latest_version']}")
            self.window.set_update_available(update_info['latest_version'])

            # Show update dialog
            self._show_update_dialog(update_info)
        else:
            # Up to date
            logger.info("No updates available")
            self.window.set_update_up_to_date()

    def _handle_update_check_error(self, error: str):
        """Handle update check error on main thread"""
        self.window.set_update_checked("Error")
        self.window.set_update_up_to_date()
        logger.error(f"Update check failed: {error}")

    def _show_update_dialog(self, update_info: dict):
        """Show update notification dialog"""
        UpdateDialog(
            self.window,
            update_info,
            update_callback=lambda info: self.perform_update(),
            ignore_callback=None
        )

    def perform_update(self):
        """Perform full update process"""
        try:
            # Stop server if running
            was_running = self.server_manager.is_running()
            if was_running:
                self.stop_server()

            # Get latest update info
            if not self.update_manager.latest_release:
                logger.error("No update information available")
                return

            update_info = {
                'latest_version': self.update_manager.latest_release['tag_name'].lstrip('v'),
                'download_url': self.update_manager._get_download_url(self.update_manager.latest_release),
            }

            # Create progress dialog
            progress = ProgressDialog(self.window, "Updating App_SUITE", allow_cancel=False)

            def update_progress(status: str, percent: int):
                progress.set_status(status)
                progress.set_progress_percent(percent)

            # Perform update in thread
            def do_update():
                try:
                    success = self.update_manager.perform_full_update(update_info, update_progress)

                    # Close progress dialog
                    self.window.after(0, progress.close)

                    if success:
                        # Show success dialog
                        self.window.after(0, lambda: self._show_update_complete(update_info['latest_version']))

                        # Restart server if it was running
                        if was_running:
                            self.window.after(3000, self.start_server)
                    else:
                        self.window.after(0, lambda: self._show_error(
                            "Update Failed",
                            "The update failed to install. The application has been rolled back to the previous version."
                        ))

                except Exception as e:
                    logger.error(f"Update failed: {e}")
                    self.window.after(0, progress.close)
                    self.window.after(0, lambda: self._show_error("Update Error", f"An error occurred during update:\n{e}"))

            thread = threading.Thread(target=do_update, daemon=True)
            thread.start()

        except Exception as e:
            logger.error(f"Error initiating update: {e}")
            self._show_error("Error", f"Could not start update:\n{e}")

    def _show_update_complete(self, version: str):
        """Show update complete dialog"""
        UpdateCompleteDialog(self.window, version)
        self.window.set_update_up_to_date()
        self._update_backup_status()

    def perform_rollback(self):
        """Perform rollback to previous version"""
        try:
            # Confirm with user
            from tkinter import messagebox
            confirm = messagebox.askyesno(
                "Confirm Rollback",
                "Are you sure you want to rollback to the previous version?\n\n"
                "The server will be stopped and restarted.",
                icon="warning"
            )

            if not confirm:
                return

            # Stop server if running
            was_running = self.server_manager.is_running()
            if was_running:
                self.stop_server()

            # Create progress dialog
            progress = ProgressDialog(self.window, "Rolling Back", allow_cancel=False)
            progress.set_status("Restoring previous version...")
            progress.set_progress_percent(50)

            def do_rollback():
                try:
                    success = self.update_manager.rollback()

                    self.window.after(0, progress.close)

                    if success:
                        backup_version = self.config.get_backup_info()['version']
                        logger.info(f"Rollback successful to version {backup_version}")

                        self.window.after(0, lambda: self._show_info(
                            "Rollback Complete",
                            f"Successfully rolled back to version {backup_version}"
                        ))

                        # Update UI
                        self.version = backup_version
                        self.window.title(f"App SUITE Launcher v{backup_version}")

                        # Restart server if it was running
                        if was_running:
                            self.window.after(1000, self.start_server)
                    else:
                        self.window.after(0, lambda: self._show_error(
                            "Rollback Failed",
                            "Could not rollback to previous version. Check logs for details."
                        ))

                except Exception as e:
                    logger.error(f"Rollback failed: {e}")
                    self.window.after(0, progress.close)
                    self.window.after(0, lambda: self._show_error("Rollback Error", f"An error occurred:\n{e}"))

            thread = threading.Thread(target=do_rollback, daemon=True)
            thread.start()

        except Exception as e:
            logger.error(f"Error initiating rollback: {e}")
            self._show_error("Error", f"Could not start rollback:\n{e}")

    def _update_backup_status(self):
        """Update backup availability in UI"""
        has_backup = self.update_manager.has_backup()
        if has_backup:
            backup_version = self.config.get_backup_info().get('version', '')
            self.window.set_backup_available(True, backup_version)
        else:
            self.window.set_backup_available(False)

    def on_close(self):
        """Handle application close with cleanup"""
        try:
            # Stop server if running
            if self.server_manager.is_running():
                logger.info("Stopping server before closing...")
                self.stop_server()

            # Stop update timers
            self._stop_update_timers()

            # Destroy window
            logger.info("Closing launcher...")
            self.window.destroy()

        except Exception as e:
            logger.error(f"Error during close: {e}")
            # Force close even if error
            self.window.destroy()

    # UI update timers

    def _start_update_timers(self):
        """Start periodic UI update timers"""
        self._update_uptime()
        self._update_system_monitor()
        self._update_logs()

    def _stop_update_timers(self):
        """Stop periodic UI update timers"""
        if self.uptime_timer_id:
            self.window.after_cancel(self.uptime_timer_id)
            self.uptime_timer_id = None

        if self.monitor_timer_id:
            self.window.after_cancel(self.monitor_timer_id)
            self.monitor_timer_id = None

        if self.logs_timer_id:
            self.window.after_cancel(self.logs_timer_id)
            self.logs_timer_id = None
            self.last_log_count = 0

    def _update_uptime(self):
        """Update uptime display"""
        if self.server_manager.is_running():
            uptime_str = self.server_manager.get_uptime_formatted()
            self.window.update_uptime(uptime_str)

            # Schedule next update (every 1 second)
            self.uptime_timer_id = self.window.after(1000, self._update_uptime)

    def _update_system_monitor(self):
        """Update system monitor displays"""
        if self.system_monitor.is_attached():
            try:
                metrics = self.system_monitor.get_all_metrics()
                self.window.update_system_metrics(
                    cpu_percent=metrics['cpu_percent'],
                    memory_percent=metrics['memory_percent'],
                    memory_text=metrics['memory_formatted']
                )
            except Exception as e:
                logger.warning(f"Failed to update system metrics: {e}")

            # Schedule next update (every 2 seconds)
            self.monitor_timer_id = self.window.after(2000, self._update_system_monitor)

    def _update_logs(self):
        """Update logs display with new log lines"""
        if self.server_manager.is_running():
            try:
                # Get current log count
                current_count = self.server_manager.get_log_count()

                # Only update if there are new logs
                if current_count > self.last_log_count:
                    # Get all logs and extract only new ones
                    all_logs = self.server_manager.get_server_logs()
                    new_logs = all_logs[self.last_log_count:]

                    # Update UI with new logs
                    self.window.update_logs(new_logs)

                    # Update counter
                    self.last_log_count = current_count

            except Exception as e:
                logger.warning(f"Failed to update logs: {e}")

            # Schedule next update (every 1 second for more responsive logs)
            self.logs_timer_id = self.window.after(1000, self._update_logs)

    # Utility methods

    def _show_error(self, title: str, message: str):
        """Show error message dialog"""
        from tkinter import messagebox
        messagebox.showerror(title, message)

    def _show_info(self, title: str, message: str):
        """Show info message dialog"""
        from tkinter import messagebox
        messagebox.showinfo(title, message)
