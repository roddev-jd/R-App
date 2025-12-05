"""
Port Manager for App_SUITE Launcher

Handles port allocation with round-robin rotation to avoid conflicts.
Supports port range 8005-8050 with automatic availability detection.
"""

import socket
import logging
import time
from typing import Dict, Optional

from .config_manager import ConfigManager

logger = logging.getLogger(__name__)


class PortManager:
    """Manages port allocation with round-robin rotation"""

    def __init__(self, config_manager: ConfigManager):
        """
        Initialize PortManager

        Args:
            config_manager: ConfigManager instance for persistence
        """
        self.config = config_manager
        self.min_port, self.max_port = self.config.get_port_range()
        self.reserved_ports: Dict[int, float] = {}  # {port: expiration_timestamp}
        logger.info(f"PortManager initialized with range {self.min_port}-{self.max_port}")

    def _reserve_port(self, port: int, duration: Optional[float] = None):
        """
        Reserve a port to prevent race conditions during server startup

        Args:
            port: Port number to reserve
            duration: Reservation duration in seconds (uses config default if None)
        """
        if duration is None:
            duration = self.config.get_port_reservation_timeout()

        expiration = time.time() + duration
        self.reserved_ports[port] = expiration
        logger.debug(f"Reserved port {port} for {duration}s (until {expiration:.2f})")

    def _is_reserved(self, port: int) -> bool:
        """
        Check if a port is currently reserved

        Args:
            port: Port number to check

        Returns:
            True if port is reserved and not expired, False otherwise
        """
        if port not in self.reserved_ports:
            return False

        # Check if reservation expired
        if time.time() > self.reserved_ports[port]:
            # Cleanup expired reservation
            del self.reserved_ports[port]
            logger.debug(f"Port {port} reservation expired and removed")
            return False

        logger.debug(f"Port {port} is reserved until {self.reserved_ports[port]:.2f}")
        return True

    def is_port_available(self, port: int, strict: bool = False) -> bool:
        """
        Check if a port is available for binding

        Args:
            port: Port number to check
            strict: If True, check without SO_REUSEADDR (stricter, matches uvicorn default)

        Returns:
            True if port is available and not reserved, False otherwise
        """
        # Check reservation status first (fast path)
        if self._is_reserved(port):
            logger.debug(f"Port {port} is reserved")
            return False

        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                if not strict:
                    # Allow TIME_WAIT reuse (faster restarts)
                    # This matches uvicorn's default behavior on most systems
                    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind(('127.0.0.1', port))
                logger.debug(f"Port {port} is available")
                return True
        except OSError as e:
            logger.debug(f"Port {port} is occupied: {e}")
            return False

    def find_available_port(self) -> int:
        """
        Find next available port using round-robin algorithm

        The algorithm:
        1. Get last used port from config
        2. Start checking from (last_port + 1)
        3. If port > max_port, wrap around to min_port
        4. Check each port for availability
        5. Return first available port
        6. Raise exception if all ports occupied

        Returns:
            Available port number

        Raises:
            RuntimeError: If no ports available in range
        """
        last_port = self.config.get_last_used_port()

        # Calculate starting port (next after last used)
        start_port = last_port + 1
        if start_port > self.max_port:
            start_port = self.min_port

        logger.info(f"Searching for available port (last used: {last_port}, starting at: {start_port})")

        # Try all ports in range using round-robin
        port_count = self.max_port - self.min_port + 1

        for offset in range(port_count):
            test_port = start_port + offset

            # Wrap around if exceeded max
            if test_port > self.max_port:
                test_port = self.min_port + (test_port - self.max_port - 1)

            if self.is_port_available(test_port):
                # Reserve port immediately to prevent race conditions
                self._reserve_port(test_port)
                # Save selected port
                self.config.set_last_used_port(test_port)
                logger.info(f"Found and reserved available port: {test_port}")
                return test_port

        # All ports occupied
        error_msg = f"No available ports in range {self.min_port}-{self.max_port}"
        logger.error(error_msg)
        raise RuntimeError(error_msg)

    def get_current_port(self) -> int:
        """
        Get the currently configured port (last used)

        Returns:
            Last used port number
        """
        return self.config.get_last_used_port()

    def verify_port(self, port: int) -> bool:
        """
        Verify if a specific port is within valid range and available

        Args:
            port: Port number to verify

        Returns:
            True if port is valid and available
        """
        if port < self.min_port or port > self.max_port:
            logger.warning(f"Port {port} is outside valid range {self.min_port}-{self.max_port}")
            return False

        return self.is_port_available(port)

    def set_port_range(self, min_port: int, max_port: int):
        """
        Update port range (updates config)

        Args:
            min_port: Minimum port number
            max_port: Maximum port number

        Raises:
            ValueError: If range is invalid
        """
        if min_port >= max_port:
            raise ValueError("min_port must be less than max_port")

        if min_port < 1024:
            raise ValueError("Port numbers below 1024 require elevated privileges")

        if max_port > 65535:
            raise ValueError("Port numbers cannot exceed 65535")

        self.config.set('Launcher', 'port_range_min', min_port)
        self.config.set('Launcher', 'port_range_max', max_port)
        self.min_port = min_port
        self.max_port = max_port

        logger.info(f"Port range updated to {min_port}-{max_port}")
