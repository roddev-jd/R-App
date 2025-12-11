"""
Server Manager for App_SUITE Launcher

Manages FastAPI server lifecycle including:
- Starting/stopping server process
- Health monitoring
- Uptime tracking
- Process management
"""

import sys
import os
import subprocess
import time
import signal
import logging
import requests
import threading
import asyncio
import select
import queue
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

    def _capture_output_windows(self, stream, prefix: str):
        """
        Windows-specific log capture usando queue con timeout.

        Strategy:
        1. Reader thread lee del stream y pone líneas en queue
        2. Main thread lee de queue con timeout 0.5s
        3. Stop signal revisado cada 0.5s

        Args:
            stream: The stream to read from
            prefix: Prefix for log lines
        """
        line_queue = queue.Queue(maxsize=1000)

        def reader_thread():
            """Thread que lee del pipe sin bloquear el main thread."""
            try:
                for line in iter(stream.readline, ''):
                    if not line:
                        break
                    try:
                        line_queue.put(line, timeout=0.1)
                    except queue.Full:
                        # Queue llena, descartar línea vieja
                        try:
                            line_queue.get_nowait()
                            line_queue.put(line, timeout=0.1)
                        except:
                            pass
            except Exception as e:
                logger.error(f"[LOG_CAPTURE] Reader thread error ({prefix}): {e}")
            finally:
                line_queue.put(None)  # Sentinel para indicar EOF

        # Start reader thread (daemon para auto-cleanup)
        reader = threading.Thread(target=reader_thread, daemon=True)
        reader.start()

        # Main loop con timeout
        while not self.stop_log_capture.is_set():
            try:
                line = line_queue.get(timeout=0.5)
                if line is None:  # Sentinel (EOF)
                    break
                if isinstance(line, str) and line.strip():
                    timestamp = datetime.now().strftime("%H:%M:%S")
                    log_line = f"[{timestamp}] {prefix} {line.rstrip()}"
                    self.log_buffer.append(log_line)
            except queue.Empty:
                continue  # Timeout, check stop signal
            except Exception as e:
                logger.error(f"[LOG_CAPTURE] Error processing line ({prefix}): {e}")

        logger.debug(f"[LOG_CAPTURE] {prefix} capture stopped cleanly")

    def _capture_output(self, stream, prefix: str):
        """
        Capture output from stdout/stderr stream in background thread with non-blocking reads

        Args:
            stream: The stream to read from (stdout or stderr)
            prefix: Prefix for log lines (e.g., "[STDOUT]" or "[STDERR]")
        """
        try:
            # Windows uses queue-based approach, Unix/Mac uses select
            if platform.system() == "Windows":
                self._capture_output_windows(stream, prefix)
            else:
                # Unix/Mac: Use select for non-blocking check
                while not self.stop_log_capture.is_set():
                    ready, _, _ = select.select([stream], [], [], 0.5)

                    if not ready:
                        # No data available, check stop signal and continue
                        continue

                    line = stream.readline()
                    if not line:  # EOF
                        break

                    timestamp = datetime.now().strftime("%H:%M:%S")
                    log_line = f"[{timestamp}] {prefix} {line.rstrip()}"
                    self.log_buffer.append(log_line)

                logger.debug(f"{prefix} capture thread stopping cleanly")

        except Exception as e:
            logger.error(f"Error capturing output from {prefix}: {e}")

    async def start_server(self, port: int) -> bool:
        """
        Start FastAPI server on specified port (async)

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

            # Copiar entorno actual para heredar todas las variables
            # Funciona en Windows, macOS y Linux
            env = os.environ.copy()

            # Start process
            self.process = subprocess.Popen(
                cmd,
                cwd=self.project_root,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                env=env
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

            # Wait for server startup with dynamic polling
            logger.info(f"Waiting for server startup (max {self.config.get_server_startup_max_wait()}s)...")
            if await self._wait_for_startup(port):
                logger.info(f"Server started successfully on port {port} (PID: {self.process.pid})")
                return True
            else:
                logger.error("Server failed to become ready within timeout")
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

                # Wait for force kill with timeout (2 seconds)
                try:
                    self.process.wait(timeout=2)
                    logger.info("Server force stopped")
                except subprocess.TimeoutExpired:
                    logger.error("Server did not respond to SIGKILL! Process may be in uninterruptible state.")
                    # Last resort: orphan the process and continue
                    self.process = None
                    self.port = None
                    self.start_time = None
                    return False

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
            url = f"http://127.0.0.1:{self.port}/health"
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

    async def health_check_async(self, timeout: float = 2.0) -> bool:
        """
        Perform async health check on running server using aiohttp

        Args:
            timeout: Request timeout in seconds

        Returns:
            True if server is healthy, False otherwise
        """
        if not self.is_running() or self.port is None:
            return False

        try:
            import aiohttp
            url = f"http://127.0.0.1:{self.port}/health"

            timeout_obj = aiohttp.ClientTimeout(total=timeout)
            async with aiohttp.ClientSession(timeout=timeout_obj) as session:
                async with session.get(url) as response:
                    is_healthy = response.status == 200

                    if is_healthy:
                        logger.debug(f"Async health check passed (status: {response.status})")
                    else:
                        logger.warning(f"Async health check failed (status: {response.status})")

                    return is_healthy

        except Exception as e:
            logger.debug(f"Async health check failed: {e}")
            return False

    async def health_check_with_retry(self, max_retries: Optional[int] = None, base_timeout: Optional[float] = None) -> bool:
        """
        Health check with exponential backoff retry logic

        Args:
            max_retries: Maximum retry attempts (uses config default if None)
            base_timeout: Base timeout for health checks (uses config default if None)

        Returns:
            True if health check eventually succeeds, False if all retries exhausted
        """
        if max_retries is None:
            max_retries = self.config.get_health_check_max_retries()
        if base_timeout is None:
            base_timeout = self.config.get_health_check_base_timeout()

        backoff_factor = self.config.get_health_check_backoff_factor()

        for attempt in range(max_retries):
            # Increase timeout on later attempts
            timeout = base_timeout * (1 + attempt * 0.5)

            if await self.health_check_async(timeout=timeout):
                if attempt > 0:
                    logger.info(f"Health check passed on attempt {attempt + 1}/{max_retries}")
                return True

            # Don't wait after last attempt
            if attempt < max_retries - 1:
                # Exponential backoff: 0.5s, 1s, 2s, 4s, 8s
                backoff = 0.5 * (backoff_factor ** attempt)
                logger.debug(f"Health check failed (attempt {attempt + 1}/{max_retries}), retrying in {backoff}s")
                await asyncio.sleep(backoff)

        logger.error(f"Health check failed after {max_retries} attempts")
        return False

    async def _wait_for_startup(self, port: int, max_wait: Optional[float] = None, initial_delay: Optional[float] = None) -> bool:
        """
        Poll health endpoint with dynamic backoff until server ready or timeout

        Args:
            port: Port to check
            max_wait: Maximum wait time in seconds (uses config default if None)
            initial_delay: Initial delay before first poll (uses config default if None)

        Returns:
            True if server becomes healthy within timeout, False otherwise
        """
        if max_wait is None:
            max_wait = self.config.get_server_startup_max_wait()
        if initial_delay is None:
            initial_delay = self.config.get_server_startup_initial_delay()

        # Wait initial delay before starting polls
        await asyncio.sleep(initial_delay)

        start_time = time.time()
        poll_interval = 0.1  # Start with 100ms

        while time.time() - start_time < max_wait:
            # Check if process is still alive
            if self.process and self.process.poll() is not None:
                logger.error("Server process died during startup")
                # Get exit code and logs for debugging
                exit_code = self.process.poll()
                recent_logs = self.get_server_logs(lines=10)
                logger.error(f"Process exit code: {exit_code}")
                if recent_logs:
                    logger.error(f"Last logs:\n" + "\n".join(recent_logs))
                return False

            if await self.health_check_async(timeout=2.0):
                elapsed = time.time() - start_time
                logger.info(f"Server ready after {elapsed:.2f}s")
                return True

            # Exponential backoff, capped at 1 second
            await asyncio.sleep(poll_interval)
            poll_interval = min(poll_interval * 1.5, 1.0)

        elapsed = time.time() - start_time
        logger.error(f"Server not ready after {elapsed:.2f}s (timeout: {max_wait}s)")
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

    async def restart_server(self, port: Optional[int] = None) -> bool:
        """
        Restart server (stop then start) - async

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
        await asyncio.sleep(1)

        # Start server again
        return await self.start_server(port)

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
