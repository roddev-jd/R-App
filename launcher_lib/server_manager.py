"""
Server Manager for App_SUITE Launcher

Manages FastAPI server lifecycle including:
- Starting/stopping server process
- Health monitoring
- Uptime tracking
- Process management
"""

import sys
import subprocess
import time
import signal
import logging
import requests
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional
from collections import deque
import platform

from .config_manager import ConfigManager

logger = logging.getLogger(__name__)


class ServerManager:
    """Manages FastAPI server process lifecycle"""

    def __init__(self, config_manager: ConfigManager):
        """
        Initialize ServerManager

        Args:
            config_manager: ConfigManager instance
        """
        self.config = config_manager
        self.process: Optional[subprocess.Popen] = None
        self.port: Optional[int] = None
        self.start_time: Optional[datetime] = None
        self.project_root = Path(__file__).parent.parent

        # Log capture
        self.log_buffer = deque(maxlen=1000)  # Keep last 1000 log lines
        self.log_threads = []
        self.stop_log_capture = threading.Event()

        logger.info("ServerManager initialized")

    def _capture_output(self, stream, prefix: str):
        """
        Capture output from stdout/stderr stream in background thread

        Args:
            stream: The stream to read from (stdout or stderr)
            prefix: Prefix for log lines (e.g., "[STDOUT]" or "[STDERR]")
        """
        try:
            for line in iter(stream.readline, ''):
                if self.stop_log_capture.is_set():
                    break
                if line:
                    timestamp = datetime.now().strftime("%H:%M:%S")
                    log_line = f"[{timestamp}] {prefix} {line.rstrip()}"
                    self.log_buffer.append(log_line)
        except Exception as e:
            logger.error(f"Error capturing output from {prefix}: {e}")

    def start_server(self, port: int) -> bool:
        """
        Start FastAPI server on specified port

        Args:
            port: Port number to bind server to

        Returns:
            True if server started successfully, False otherwise
        """
        if self.is_running():
            logger.warning("Server is already running")
            return False

        try:
            # Build uvicorn command
            cmd = [
                sys.executable, "-m", "uvicorn",
                "FlexStart.backend.app:app",
                "--host", "127.0.0.1",
                "--port", str(port)
            ]

            logger.info(f"Starting server on port {port}: {' '.join(cmd)}")

            # Start process
            self.process = subprocess.Popen(
                cmd,
                cwd=self.project_root,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1
            )

            self.port = port
            self.start_time = datetime.now()

            # Clear log buffer and reset stop event
            self.log_buffer.clear()
            self.stop_log_capture.clear()

            # Start log capture threads
            stdout_thread = threading.Thread(
                target=self._capture_output,
                args=(self.process.stdout, "[OUT]"),
                daemon=True
            )
            stderr_thread = threading.Thread(
                target=self._capture_output,
                args=(self.process.stderr, "[ERR]"),
                daemon=True
            )

            stdout_thread.start()
            stderr_thread.start()

            self.log_threads = [stdout_thread, stderr_thread]
            logger.info("Log capture threads started")

            # Wait for server startup
            startup_delay = self.config.get_server_startup_delay()
            logger.info(f"Waiting {startup_delay}s for server startup...")
            time.sleep(startup_delay)

            # Verify server health
            if self.health_check():
                logger.info(f"Server started successfully on port {port} (PID: {self.process.pid})")
                return True
            else:
                logger.error("Server failed health check")
                self.stop_server()
                return False

        except Exception as e:
            logger.error(f"Failed to start server: {e}")
            self.process = None
            self.port = None
            self.start_time = None
            return False

    def stop_server(self) -> bool:
        """
        Stop running server process

        Returns:
            True if server stopped successfully, False otherwise
        """
        if not self.is_running():
            logger.warning("No server process to stop")
            return True

        try:
            logger.info(f"Stopping server (PID: {self.process.pid})...")

            # Signal log capture threads to stop
            self.stop_log_capture.set()

            # Send SIGTERM for graceful shutdown
            if platform.system() == "Windows":
                self.process.terminate()
            else:
                self.process.send_signal(signal.SIGTERM)

            # Wait up to 5 seconds for graceful shutdown
            try:
                self.process.wait(timeout=5)
                logger.info("Server stopped gracefully")
            except subprocess.TimeoutExpired:
                # Force kill if not stopped
                logger.warning("Server did not stop gracefully, forcing termination...")
                self.process.kill()
                self.process.wait()
                logger.info("Server force stopped")

            # Wait for log threads to finish (with timeout)
            for thread in self.log_threads:
                thread.join(timeout=1)
            self.log_threads.clear()
            logger.info("Log capture threads stopped")

            self.process = None
            self.port = None
            self.start_time = None
            return True

        except Exception as e:
            logger.error(f"Error stopping server: {e}")
            return False

    def is_running(self) -> bool:
        """
        Check if server process is running

        Returns:
            True if server is running, False otherwise
        """
        if self.process is None:
            return False

        # Check if process is still alive
        return self.process.poll() is None

    def health_check(self, timeout: float = 2.0) -> bool:
        """
        Perform health check on running server

        Args:
            timeout: Request timeout in seconds

        Returns:
            True if server is healthy, False otherwise
        """
        if not self.is_running() or self.port is None:
            return False

        try:
            url = f"http://127.0.0.1:{self.port}/"
            response = requests.get(url, timeout=timeout)
            is_healthy = response.status_code == 200

            if is_healthy:
                logger.debug(f"Health check passed (status: {response.status_code})")
            else:
                logger.warning(f"Health check failed (status: {response.status_code})")

            return is_healthy

        except requests.exceptions.RequestException as e:
            logger.debug(f"Health check failed: {e}")
            return False

    def get_pid(self) -> Optional[int]:
        """
        Get server process PID

        Returns:
            Process PID or None if not running
        """
        if self.process:
            return self.process.pid
        return None

    def get_port(self) -> Optional[int]:
        """
        Get server port number

        Returns:
            Port number or None if not running
        """
        return self.port

    def get_url(self) -> Optional[str]:
        """
        Get server URL

        Returns:
            Full server URL or None if not running
        """
        if self.port:
            return f"http://127.0.0.1:{self.port}"
        return None

    def get_uptime(self) -> Optional[float]:
        """
        Get server uptime in seconds

        Returns:
            Uptime in seconds or None if not running
        """
        if self.start_time and self.is_running():
            return (datetime.now() - self.start_time).total_seconds()
        return None

    def get_uptime_formatted(self) -> str:
        """
        Get formatted uptime string

        Returns:
            Formatted uptime (HH:MM:SS) or "Not running"
        """
        uptime = self.get_uptime()
        if uptime is None:
            return "Not running"

        hours = int(uptime // 3600)
        minutes = int((uptime % 3600) // 60)
        seconds = int(uptime % 60)

        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    def get_exit_code(self) -> Optional[int]:
        """
        Get process exit code (only available after process ends)

        Returns:
            Exit code or None if process still running
        """
        if self.process:
            return self.process.poll()
        return None

    def restart_server(self, port: Optional[int] = None) -> bool:
        """
        Restart server (stop then start)

        Args:
            port: Port to use (uses current port if None)

        Returns:
            True if restart successful, False otherwise
        """
        logger.info("Restarting server...")

        # Use current port if not specified
        if port is None:
            port = self.port

        if port is None:
            logger.error("Cannot restart: no port specified and no current port")
            return False

        # Stop current server
        if not self.stop_server():
            logger.error("Failed to stop server for restart")
            return False

        # Wait a moment before restart
        time.sleep(1)

        # Start server again
        return self.start_server(port)

    def get_server_logs(self, lines: Optional[int] = None) -> list:
        """
        Get recent server output (stdout/stderr)

        Args:
            lines: Number of recent lines to retrieve (None for all available)

        Returns:
            List of log lines
        """
        if lines is None:
            return list(self.log_buffer)
        else:
            # Get last N lines
            all_logs = list(self.log_buffer)
            return all_logs[-lines:] if len(all_logs) > lines else all_logs

    def get_log_count(self) -> int:
        """
        Get total number of log lines in buffer

        Returns:
            Number of log lines
        """
        return len(self.log_buffer)
