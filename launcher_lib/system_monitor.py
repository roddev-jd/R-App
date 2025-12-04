"""
System Monitor for App_SUITE Launcher

Monitors system resources for the running server process:
- CPU usage
- Memory usage
- Process information
"""

import logging
from typing import Optional, Dict
import psutil

logger = logging.getLogger(__name__)


class SystemMonitor:
    """Monitors system resources for server process"""

    def __init__(self):
        """Initialize SystemMonitor"""
        self.process: Optional[psutil.Process] = None
        self.pid: Optional[int] = None
        logger.info("SystemMonitor initialized")

    def attach_to_process(self, pid: int) -> bool:
        """
        Attach monitor to a process by PID

        Args:
            pid: Process ID to monitor

        Returns:
            True if attached successfully, False otherwise
        """
        try:
            self.process = psutil.Process(pid)
            self.pid = pid
            logger.info(f"Attached to process {pid}")
            return True
        except psutil.NoSuchProcess:
            logger.error(f"Process {pid} does not exist")
            return False
        except psutil.AccessDenied:
            logger.error(f"Access denied to process {pid}")
            return False
        except Exception as e:
            logger.error(f"Failed to attach to process {pid}: {e}")
            return False

    def detach(self):
        """Detach from current process"""
        self.process = None
        self.pid = None
        logger.debug("Detached from process")

    def is_attached(self) -> bool:
        """
        Check if monitor is attached to a process

        Returns:
            True if attached to a running process
        """
        if self.process is None:
            return False

        try:
            # Check if process is still running
            return self.process.is_running()
        except:
            return False

    def get_cpu_percent(self, interval: float = 0.1) -> float:
        """
        Get CPU usage percentage

        Args:
            interval: Measurement interval in seconds

        Returns:
            CPU usage percentage (0-100), or 0 if not available
        """
        if not self.is_attached():
            return 0.0

        try:
            cpu = self.process.cpu_percent(interval=interval)
            logger.debug(f"CPU usage: {cpu:.1f}%")
            return cpu
        except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
            logger.warning(f"Cannot get CPU percent: {e}")
            return 0.0

    def get_memory_info(self) -> Dict[str, float]:
        """
        Get memory usage information

        Returns:
            Dictionary with memory metrics:
            - 'rss_bytes': Resident Set Size in bytes
            - 'rss_mb': RSS in megabytes
            - 'rss_gb': RSS in gigabytes
            - 'percent': Memory usage percentage
            - 'vms_bytes': Virtual Memory Size in bytes
        """
        if not self.is_attached():
            return {
                'rss_bytes': 0.0,
                'rss_mb': 0.0,
                'rss_gb': 0.0,
                'percent': 0.0,
                'vms_bytes': 0.0,
            }

        try:
            mem_info = self.process.memory_info()
            mem_percent = self.process.memory_percent()

            rss_bytes = mem_info.rss
            rss_mb = rss_bytes / (1024 ** 2)
            rss_gb = rss_bytes / (1024 ** 3)

            result = {
                'rss_bytes': rss_bytes,
                'rss_mb': rss_mb,
                'rss_gb': rss_gb,
                'percent': mem_percent,
                'vms_bytes': mem_info.vms,
            }

            logger.debug(f"Memory usage: {rss_mb:.1f} MB ({mem_percent:.1f}%)")
            return result

        except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
            logger.warning(f"Cannot get memory info: {e}")
            return {
                'rss_bytes': 0.0,
                'rss_mb': 0.0,
                'rss_gb': 0.0,
                'percent': 0.0,
                'vms_bytes': 0.0,
            }

    def format_memory(self, bytes_value: float, precision: int = 1) -> str:
        """
        Format memory size in human-readable form

        Args:
            bytes_value: Memory size in bytes
            precision: Decimal precision

        Returns:
            Formatted string (e.g., "2.5 GB", "512.0 MB")
        """
        if bytes_value >= 1024 ** 3:  # GB
            return f"{bytes_value / (1024 ** 3):.{precision}f} GB"
        elif bytes_value >= 1024 ** 2:  # MB
            return f"{bytes_value / (1024 ** 2):.{precision}f} MB"
        elif bytes_value >= 1024:  # KB
            return f"{bytes_value / 1024:.{precision}f} KB"
        else:  # Bytes
            return f"{bytes_value:.0f} B"

    def get_process_info(self) -> Dict[str, any]:
        """
        Get comprehensive process information

        Returns:
            Dictionary with process details
        """
        if not self.is_attached():
            return {
                'pid': None,
                'name': 'N/A',
                'status': 'Not attached',
                'create_time': None,
                'num_threads': 0,
            }

        try:
            return {
                'pid': self.process.pid,
                'name': self.process.name(),
                'status': self.process.status(),
                'create_time': self.process.create_time(),
                'num_threads': self.process.num_threads(),
            }
        except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
            logger.warning(f"Cannot get process info: {e}")
            return {
                'pid': self.pid,
                'name': 'Unknown',
                'status': 'Error',
                'create_time': None,
                'num_threads': 0,
            }

    def get_all_metrics(self) -> Dict[str, any]:
        """
        Get all available metrics in one call

        Returns:
            Dictionary with all metrics
        """
        memory = self.get_memory_info()
        cpu = self.get_cpu_percent()
        process_info = self.get_process_info()

        return {
            'cpu_percent': cpu,
            'memory_mb': memory['rss_mb'],
            'memory_gb': memory['rss_gb'],
            'memory_percent': memory['percent'],
            'memory_formatted': self.format_memory(memory['rss_bytes']),
            'pid': process_info['pid'],
            'name': process_info['name'],
            'status': process_info['status'],
            'num_threads': process_info['num_threads'],
        }

    @staticmethod
    def get_system_memory_info() -> Dict[str, float]:
        """
        Get system-wide memory information

        Returns:
            Dictionary with system memory metrics
        """
        try:
            mem = psutil.virtual_memory()
            return {
                'total_gb': mem.total / (1024 ** 3),
                'available_gb': mem.available / (1024 ** 3),
                'used_gb': mem.used / (1024 ** 3),
                'percent': mem.percent,
            }
        except Exception as e:
            logger.error(f"Cannot get system memory info: {e}")
            return {
                'total_gb': 0.0,
                'available_gb': 0.0,
                'used_gb': 0.0,
                'percent': 0.0,
            }

    @staticmethod
    def get_system_cpu_percent(interval: float = 0.1) -> float:
        """
        Get system-wide CPU usage

        Args:
            interval: Measurement interval in seconds

        Returns:
            System CPU usage percentage
        """
        try:
            return psutil.cpu_percent(interval=interval)
        except Exception as e:
            logger.error(f"Cannot get system CPU percent: {e}")
            return 0.0
