"""
Process Utilities for App_SUITE Launcher

Cross-platform utilities for managing processes on specific ports:
- Finding processes by port number
- Graceful/forceful process termination
- Safety checks for localhost-only operations
"""

import logging
import platform
import subprocess
import time
from typing import Optional, List, Dict, Tuple
import psutil

logger = logging.getLogger(__name__)


class PortProcessInfo:
    """Information about a process using a port"""

    def __init__(self, pid: int, port: int, process_name: str = "Unknown",
                 local_addr: str = "127.0.0.1", status: str = "LISTEN"):
        self.pid = pid
        self.port = port
        self.process_name = process_name
        self.local_addr = local_addr
        self.status = status

    def __repr__(self):
        return f"PortProcessInfo(pid={self.pid}, port={self.port}, name='{self.process_name}')"


class ProcessCleanupResult:
    """Result of process cleanup operation"""

    def __init__(self, success: bool, pid: Optional[int] = None,
                 method: str = "", message: str = "", error: Optional[str] = None):
        self.success = success
        self.pid = pid
        self.method = method  # e.g., "psutil", "lsof", "netstat", "graceful", "force"
        self.message = message
        self.error = error

    def __repr__(self):
        status = "SUCCESS" if self.success else "FAILED"
        return f"ProcessCleanupResult({status}, pid={self.pid}, method='{self.method}')"


def find_process_on_port(port: int, localhost_only: bool = True) -> Optional[PortProcessInfo]:
    """
    Find process listening on specified port using psutil (cross-platform)

    Args:
        port: Port number to check
        localhost_only: Only return processes on 127.0.0.1 (safety feature)

    Returns:
        PortProcessInfo if found, None otherwise

    Example:
        >>> info = find_process_on_port(9999)
        >>> if info:
        >>>     print(f"Found {info.process_name} (PID {info.pid}) on port {info.port}")
    """
    try:
        logger.debug(f"Searching for process on port {port} using psutil...")

        # Get all network connections
        for conn in psutil.net_connections(kind='inet'):
            # Check if connection matches our port and is in LISTEN state
            if conn.status == 'LISTEN' and conn.laddr.port == port:
                # Safety: Only handle localhost processes unless explicitly allowed
                if localhost_only and conn.laddr.ip not in ('127.0.0.1', '::1', '0.0.0.0', '::'):
                    logger.warning(f"Process on port {port} is not localhost: {conn.laddr.ip}")
                    continue

                pid = conn.pid
                if pid is None:
                    logger.warning(f"Found connection on port {port} but PID is None")
                    continue

                # Get process details
                try:
                    proc = psutil.Process(pid)
                    process_name = proc.name()
                    logger.info(f"Found process: {process_name} (PID {pid}) on port {port}")

                    return PortProcessInfo(
                        pid=pid,
                        port=port,
                        process_name=process_name,
                        local_addr=conn.laddr.ip,
                        status=conn.status
                    )
                except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
                    logger.warning(f"Cannot access process {pid}: {e}")
                    continue

        logger.debug(f"No process found on port {port}")
        return None

    except psutil.AccessDenied as e:
        logger.warning(f"Access denied when checking port {port} with psutil: {e}")
        logger.info(f"Falling back to system commands...")
        return find_process_on_port_fallback(port)
    except Exception as e:
        logger.error(f"Error finding process on port {port}: {e}")
        logger.info(f"Trying fallback method...")
        return find_process_on_port_fallback(port)


def find_process_on_port_fallback(port: int) -> Optional[PortProcessInfo]:
    """
    Fallback method using system commands (lsof/netstat) when psutil fails

    Args:
        port: Port number to check

    Returns:
        PortProcessInfo if found, None otherwise
    """
    system = platform.system()

    try:
        if system in ("Darwin", "Linux"):
            # Use lsof on Unix/Mac
            return _find_process_lsof(port)
        elif system == "Windows":
            # Use netstat on Windows
            return _find_process_netstat(port)
        else:
            logger.warning(f"Unsupported platform: {system}")
            return None

    except Exception as e:
        logger.error(f"Fallback method failed: {e}")
        return None


def _find_process_lsof(port: int) -> Optional[PortProcessInfo]:
    """Find process using lsof (Mac/Linux)"""
    try:
        # lsof -ti :9999 returns PIDs using that port
        result = subprocess.run(
            ['lsof', '-ti', f':{port}'],
            capture_output=True,
            text=True,
            timeout=5
        )

        if result.returncode == 0 and result.stdout.strip():
            pid_str = result.stdout.strip().split('\n')[0]  # First PID
            pid = int(pid_str)

            # Get process name
            try:
                proc = psutil.Process(pid)
                process_name = proc.name()
            except:
                process_name = "Unknown"

            logger.info(f"lsof found process: {process_name} (PID {pid}) on port {port}")
            return PortProcessInfo(pid=pid, port=port, process_name=process_name)

        return None

    except subprocess.TimeoutExpired:
        logger.error("lsof command timed out")
        return None
    except Exception as e:
        logger.error(f"lsof failed: {e}")
        return None


def _find_process_netstat(port: int) -> Optional[PortProcessInfo]:
    """Find process using netstat (Windows)"""
    try:
        # netstat -ano | findstr :9999
        result = subprocess.run(
            ['netstat', '-ano'],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode == 0:
            # Parse output to find port
            for line in result.stdout.split('\n'):
                if f':{port}' in line and 'LISTENING' in line:
                    # Extract PID (last column)
                    parts = line.split()
                    if len(parts) >= 5:
                        pid = int(parts[-1])

                        # Get process name
                        try:
                            proc = psutil.Process(pid)
                            process_name = proc.name()
                        except:
                            process_name = "Unknown"

                        logger.info(f"netstat found process: {process_name} (PID {pid}) on port {port}")
                        return PortProcessInfo(pid=pid, port=port, process_name=process_name)

        return None

    except subprocess.TimeoutExpired:
        logger.error("netstat command timed out")
        return None
    except Exception as e:
        logger.error(f"netstat failed: {e}")
        return None


def kill_process_on_port(port: int, timeout: float = 5.0,
                         force: bool = True) -> ProcessCleanupResult:
    """
    Kill process occupying specified port (graceful first, then forceful)

    Args:
        port: Port number
        timeout: Seconds to wait for graceful shutdown before force kill
        force: Whether to force kill if graceful fails

    Returns:
        ProcessCleanupResult with operation details

    Example:
        >>> result = kill_process_on_port(9999)
        >>> if result.success:
        >>>     print(f"Killed process {result.pid} using {result.method}")
    """
    # Find process
    process_info = find_process_on_port(port)

    if process_info is None:
        # Try fallback method
        process_info = find_process_on_port_fallback(port)

    if process_info is None:
        logger.info(f"No process found on port {port}")
        return ProcessCleanupResult(
            success=True,  # Success - port is free
            message=f"No process on port {port}"
        )

    pid = process_info.pid
    process_name = process_info.process_name

    logger.info(f"Attempting to kill {process_name} (PID {pid}) on port {port}")

    # Try graceful termination first
    graceful_result = _kill_process_graceful(pid, process_name, timeout)
    if graceful_result.success:
        return graceful_result

    # Graceful failed - try force kill if allowed
    if force:
        logger.warning(f"Graceful termination failed, attempting force kill...")
        return _kill_process_force(pid, process_name)
    else:
        return ProcessCleanupResult(
            success=False,
            pid=pid,
            method="graceful",
            message=f"Graceful termination failed and force=False",
            error=graceful_result.error
        )


def _kill_process_graceful(pid: int, process_name: str, timeout: float) -> ProcessCleanupResult:
    """
    Attempt graceful process termination (SIGTERM / terminate)

    Args:
        pid: Process ID
        process_name: Process name (for logging)
        timeout: Seconds to wait for termination

    Returns:
        ProcessCleanupResult
    """
    try:
        proc = psutil.Process(pid)

        # Send SIGTERM (graceful shutdown signal)
        logger.info(f"Sending SIGTERM to {process_name} (PID {pid})")
        proc.terminate()

        # Wait for process to exit
        try:
            proc.wait(timeout=timeout)
            logger.info(f"Process {pid} terminated gracefully")
            return ProcessCleanupResult(
                success=True,
                pid=pid,
                method="graceful",
                message=f"Process {pid} ({process_name}) terminated gracefully"
            )
        except psutil.TimeoutExpired:
            logger.warning(f"Process {pid} did not terminate within {timeout}s")
            return ProcessCleanupResult(
                success=False,
                pid=pid,
                method="graceful",
                message=f"Process did not terminate within {timeout}s",
                error="timeout"
            )

    except psutil.NoSuchProcess:
        # Process already gone
        logger.info(f"Process {pid} already terminated")
        return ProcessCleanupResult(
            success=True,
            pid=pid,
            method="graceful",
            message=f"Process {pid} already terminated"
        )
    except psutil.AccessDenied as e:
        logger.error(f"Access denied when terminating process {pid}: {e}")
        return ProcessCleanupResult(
            success=False,
            pid=pid,
            method="graceful",
            message="Access denied",
            error=str(e)
        )
    except Exception as e:
        logger.error(f"Error terminating process {pid}: {e}")
        return ProcessCleanupResult(
            success=False,
            pid=pid,
            method="graceful",
            message="Unexpected error",
            error=str(e)
        )


def _kill_process_force(pid: int, process_name: str) -> ProcessCleanupResult:
    """
    Force kill process (SIGKILL / kill)

    Args:
        pid: Process ID
        process_name: Process name (for logging)

    Returns:
        ProcessCleanupResult
    """
    try:
        proc = psutil.Process(pid)

        # Send SIGKILL (force kill)
        logger.warning(f"Force killing {process_name} (PID {pid})")
        proc.kill()

        # Wait up to 2 seconds for force kill to complete
        try:
            proc.wait(timeout=2)
            logger.info(f"Process {pid} force killed successfully")
            return ProcessCleanupResult(
                success=True,
                pid=pid,
                method="force",
                message=f"Process {pid} ({process_name}) force killed"
            )
        except psutil.TimeoutExpired:
            # This should rarely happen - SIGKILL is immediate
            logger.error(f"Process {pid} did not respond to SIGKILL!")
            return ProcessCleanupResult(
                success=False,
                pid=pid,
                method="force",
                message="Process did not respond to SIGKILL",
                error="sigkill_timeout"
            )

    except psutil.NoSuchProcess:
        logger.info(f"Process {pid} already terminated")
        return ProcessCleanupResult(
            success=True,
            pid=pid,
            method="force",
            message=f"Process {pid} already terminated"
        )
    except psutil.AccessDenied as e:
        logger.error(f"Access denied when force killing process {pid}: {e}")
        return ProcessCleanupResult(
            success=False,
            pid=pid,
            method="force",
            message="Access denied (requires elevated privileges?)",
            error=str(e)
        )
    except Exception as e:
        logger.error(f"Error force killing process {pid}: {e}")
        return ProcessCleanupResult(
            success=False,
            pid=pid,
            method="force",
            message="Unexpected error",
            error=str(e)
        )


def cleanup_port(port: int, timeout: float = 5.0) -> ProcessCleanupResult:
    """
    High-level function to clean up a port (convenience wrapper)

    This is the main function to use from other modules.

    Args:
        port: Port to clean up
        timeout: Timeout for graceful shutdown

    Returns:
        ProcessCleanupResult

    Example:
        >>> from launcher_lib.process_utils import cleanup_port
        >>> result = cleanup_port(9999)
        >>> if result.success:
        >>>     print(f"Port 9999 is now free")
    """
    logger.info(f"Cleaning up port {port}...")
    return kill_process_on_port(port, timeout=timeout, force=True)
