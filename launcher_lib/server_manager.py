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
from datetime import datetime
from pathlib import Path
from typing import Optional
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

        logger.info("ServerManager initialized")

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

    def get_server_logs(self, lines: int = 50) -> str:
        """
        Get recent server output (stdout/stderr)

        Args:
            lines: Number of recent lines to retrieve

        Returns:
            Server log output
        """
        if not self.process:
            return "No server process running"

        try:
            # This is a simplified version - in production, you'd want to
            # capture logs to a file and read from there
            return "Server logs not available in this implementation"
        except Exception as e:
            logger.error(f"Failed to get server logs: {e}")
            return f"Error retrieving logs: {e}"
