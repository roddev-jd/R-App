"""
Web-Based Launcher Backend for App_SUITE
FastAPI server providing REST API and SSE for launcher control
"""

import asyncio
import json
import logging
import sys
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import StreamingResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import uvicorn

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import existing managers (reuse!)
from launcher_lib.config_manager import ConfigManager
from launcher_lib.port_manager import PortManager
from launcher_lib.server_manager import ServerManager
from launcher_lib.update_manager import UpdateManager
from launcher_lib.system_monitor import SystemMonitor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global manager instances
config: Optional[ConfigManager] = None
port_manager: Optional[PortManager] = None
server_manager: Optional[ServerManager] = None
update_manager: Optional[UpdateManager] = None
system_monitor: Optional[SystemMonitor] = None

# Queues for SSE streaming
log_queue: Optional[asyncio.Queue] = None
metrics_queue: Optional[asyncio.Queue] = None
update_progress_queue: Optional[asyncio.Queue] = None

# Background task handles
log_task = None
metrics_task = None


# Pydantic models
class ServerStatus(BaseModel):
    running: bool
    port: Optional[int] = None
    url: Optional[str] = None
    pid: Optional[int] = None
    uptime_seconds: Optional[float] = None
    uptime_formatted: str = "Not running"


class ServerStartResponse(BaseModel):
    success: bool
    port: Optional[int] = None
    url: Optional[str] = None
    pid: Optional[int] = None
    message: str


class ConfigResponse(BaseModel):
    version: str
    last_used_port: int
    port_range: dict
    auto_start_server: bool
    auto_open_browser: bool
    auto_check_updates: bool


class UpdateCheckResponse(BaseModel):
    checking: bool = False
    update_available: bool = False
    current_version: str
    latest_version: Optional[str] = None
    release_notes: Optional[str] = None
    download_url: Optional[str] = None
    last_checked: str


class MetricsResponse(BaseModel):
    attached: bool
    cpu_percent: float = 0.0
    memory_mb: float = 0.0
    memory_formatted: str = "0 MB"
    memory_percent: float = 0.0
    num_threads: int = 0


# Background tasks
async def log_stream_task():
    """Background task to capture logs from server_manager"""
    last_count = 0
    while True:
        await asyncio.sleep(0.5)
        if server_manager and server_manager.is_running():
            try:
                logs = server_manager.get_server_logs()
                if len(logs) > last_count:
                    new_logs = logs[last_count:]
                    for log in new_logs:
                        parsed = parse_log_line(log)
                        await log_queue.put(parsed)
                    last_count = len(logs)
            except Exception as e:
                logger.error(f"Error in log stream task: {e}")


async def metrics_stream_task():
    """Background task to capture system metrics"""
    while True:
        await asyncio.sleep(2.0)
        if system_monitor and system_monitor.is_attached():
            try:
                metrics = system_monitor.get_all_metrics()
                await metrics_queue.put(metrics)
            except Exception as e:
                logger.error(f"Error in metrics stream task: {e}")


def parse_log_line(log_line: str) -> dict:
    """Parse log line into structured format"""
    # Simple parsing - extract timestamp if present
    timestamp = datetime.now().strftime("%H:%M:%S")
    level = "OUT"
    message = log_line.strip()

    # Try to extract timestamp and level if formatted
    if log_line.startswith('['):
        parts = log_line.split(']', 2)
        if len(parts) >= 2:
            timestamp = parts[0].strip('[')
            if len(parts) >= 3:
                level = parts[1].strip('[ ')
                message = parts[2].strip()

    return {"timestamp": timestamp, "level": level, "message": message}


# Lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize managers on startup, cleanup on shutdown"""
    global config, port_manager, server_manager, update_manager, system_monitor
    global log_queue, metrics_queue, update_progress_queue
    global log_task, metrics_task

    logger.info("Starting launcher web server...")

    # Initialize managers
    config = ConfigManager()
    port_manager = PortManager(config)
    server_manager = ServerManager(config)
    update_manager = UpdateManager(config)
    system_monitor = SystemMonitor()

    # Initialize queues
    log_queue = asyncio.Queue()
    metrics_queue = asyncio.Queue()
    update_progress_queue = asyncio.Queue()

    # Start background tasks
    log_task = asyncio.create_task(log_stream_task())
    metrics_task = asyncio.create_task(metrics_stream_task())

    logger.info("Launcher web server initialized")

    yield

    # Cleanup
    logger.info("Shutting down launcher web server...")
    if log_task:
        log_task.cancel()
    if metrics_task:
        metrics_task.cancel()
    if server_manager and server_manager.is_running():
        server_manager.stop_server()
    logger.info("Launcher web server stopped")


# Create FastAPI app
app = FastAPI(
    title="App_SUITE Web Launcher",
    version="1.0.0",
    lifespan=lifespan
)

# Mount static files and templates
launcher_dir = Path(__file__).parent
app.mount("/static", StaticFiles(directory=launcher_dir / "static"), name="static")

# Mount FlexStart assets (reuse!)
flexstart_assets = launcher_dir.parent / "FlexStart" / "assets"
if flexstart_assets.exists():
    app.mount("/assets_flexstart", StaticFiles(directory=flexstart_assets), name="flexstart_assets")

templates = Jinja2Templates(directory=launcher_dir / "templates")


# Routes
@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Serve main launcher page"""
    version = config.get_current_version() if config else "2.0.2"
    return templates.TemplateResponse("launcher.html", {
        "request": request,
        "version": version
    })


# Server control endpoints
@app.post("/api/server/start")
async def start_server() -> ServerStartResponse:
    """Start the main FastAPI server"""
    try:
        if server_manager.is_running():
            raise HTTPException(400, "Server is already running")

        # Find available port
        port = port_manager.find_available_port()

        # Start server (now async with retry logic)
        if await server_manager.start_server(port):
            pid = server_manager.get_pid()
            url = server_manager.get_url()

            # Attach system monitor
            if pid:
                system_monitor.attach_to_process(pid)

            return ServerStartResponse(
                success=True,
                port=port,
                url=url,
                pid=pid,
                message=f"Server started on port {port}"
            )
        else:
            # Better error message with health check context
            raise HTTPException(
                500,
                "Failed to start server: health check did not pass after dynamic polling with retries"
            )

    except RuntimeError as e:
        # No ports available
        raise HTTPException(503, str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting server: {e}", exc_info=True)
        raise HTTPException(500, f"Error: {str(e)}")


@app.post("/api/server/stop")
async def stop_server():
    """Stop the main FastAPI server"""
    try:
        if not server_manager.is_running():
            raise HTTPException(400, "Server is not running")

        if server_manager.stop_server():
            system_monitor.detach()
            return {"success": True, "message": "Server stopped"}
        else:
            raise HTTPException(500, "Failed to stop server")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error stopping server: {e}", exc_info=True)
        raise HTTPException(500, f"Error: {str(e)}")


@app.get("/api/server/status")
async def get_server_status() -> ServerStatus:
    """Get current server status"""
    if server_manager.is_running():
        return ServerStatus(
            running=True,
            port=server_manager.get_port(),
            url=server_manager.get_url(),
            pid=server_manager.get_pid(),
            uptime_seconds=server_manager.get_uptime(),
            uptime_formatted=server_manager.get_uptime_formatted()
        )
    else:
        return ServerStatus(running=False)


# Configuration endpoints
@app.get("/api/config")
async def get_config() -> ConfigResponse:
    """Get launcher configuration"""
    min_port, max_port = config.get_port_range()
    return ConfigResponse(
        version=config.get_current_version(),
        last_used_port=config.get_last_used_port(),
        port_range={"min": min_port, "max": max_port},
        auto_start_server=config.get_bool('Launcher', 'auto_start_server', False),
        auto_open_browser=config.get_auto_open_browser(),
        auto_check_updates=config.get_bool('UpdateSettings', 'auto_check_updates', True)
    )


@app.patch("/api/config")
async def update_config(updates: dict):
    """Update launcher configuration"""
    # Update config values
    for key, value in updates.items():
        if key in ['auto_start_server', 'auto_open_browser']:
            config.set('Launcher', key, str(value).lower())
        elif key == 'auto_check_updates':
            config.set('UpdateSettings', key, str(value).lower())

    # Return updated config
    return await get_config()


# Update endpoints
@app.get("/api/updates/check")
async def check_for_updates() -> UpdateCheckResponse:
    """Check for updates from GitHub"""
    try:
        update_info = update_manager.check_for_updates()
        last_check = config.get_last_update_check()
        last_check_str = last_check.isoformat() if last_check else datetime.now().isoformat()

        if update_info:
            return UpdateCheckResponse(
                update_available=True,
                current_version=update_info['current_version'],
                latest_version=update_info['latest_version'],
                release_notes=update_info.get('release_notes', ''),
                download_url=update_info.get('download_url', ''),
                last_checked=last_check_str
            )
        else:
            return UpdateCheckResponse(
                update_available=False,
                current_version=config.get_current_version(),
                last_checked=last_check_str
            )

    except Exception as e:
        logger.error(f"Update check failed: {e}", exc_info=True)
        raise HTTPException(500, f"Update check failed: {str(e)}")


@app.post("/api/updates/install")
async def install_update():
    """Install available update"""
    try:
        # Stop server if running
        was_running = server_manager.is_running()
        if was_running:
            server_manager.stop_server()
            system_monitor.detach()

        if not update_manager.latest_release:
            raise HTTPException(400, "No update available. Check for updates first.")

        update_info = {
            'latest_version': update_manager.latest_release['tag_name'].lstrip('v'),
            'download_url': update_manager._get_download_url(update_manager.latest_release),
        }

        def progress_callback(status: str, percent: int):
            """Callback for update progress"""
            try:
                asyncio.run(update_progress_queue.put({"status": status, "percent": percent}))
            except:
                pass

        # Perform update in thread to avoid blocking
        def do_update():
            return update_manager.perform_full_update(update_info, progress_callback)

        result = await asyncio.to_thread(do_update)

        if result:
            return {"success": True, "message": "Update installed successfully"}
        else:
            raise HTTPException(500, "Update installation failed")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update installation error: {e}", exc_info=True)
        raise HTTPException(500, f"Error: {str(e)}")


@app.post("/api/updates/rollback")
async def rollback_update():
    """Rollback to previous version"""
    try:
        # Stop server if running
        was_running = server_manager.is_running()
        if was_running:
            server_manager.stop_server()
            system_monitor.detach()

        if update_manager.rollback():
            backup_info = config.get_backup_info()
            backup_version = backup_info.get('version', 'Unknown')
            return {
                "success": True,
                "message": f"Rolled back to version {backup_version}",
                "backup_version": backup_version
            }
        else:
            raise HTTPException(500, "Rollback failed. No backup available.")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Rollback error: {e}", exc_info=True)
        raise HTTPException(500, f"Error: {str(e)}")


@app.get("/api/updates/backup-status")
async def get_backup_status():
    """Get backup availability status"""
    try:
        has_backup = update_manager.has_backup()
        if has_backup:
            backup_info = config.get_backup_info()
            return {
                "has_backup": True,
                "backup_version": backup_info.get('version'),
                "backup_timestamp": backup_info.get('timestamp'),
                "backup_size_mb": backup_info.get('size_mb')
            }
        else:
            return {"has_backup": False}
    except Exception as e:
        logger.error(f"Error getting backup status: {e}")
        return {"has_backup": False}


# Monitoring endpoints
@app.get("/api/monitor/metrics")
async def get_metrics() -> MetricsResponse:
    """Get current system metrics"""
    if system_monitor.is_attached():
        try:
            metrics = system_monitor.get_all_metrics()
            return MetricsResponse(
                attached=True,
                cpu_percent=metrics['cpu_percent'],
                memory_mb=metrics['memory_mb'],
                memory_formatted=metrics['memory_formatted'],
                memory_percent=metrics['memory_percent'],
                num_threads=metrics['num_threads']
            )
        except Exception as e:
            logger.error(f"Error getting metrics: {e}")
            return MetricsResponse(attached=False)
    else:
        return MetricsResponse(attached=False)


# SSE endpoints
@app.get("/api/sse/logs")
async def sse_logs():
    """Stream server logs via SSE"""
    async def event_generator():
        try:
            while True:
                log = await log_queue.get()
                yield f"data: {json.dumps(log)}\n\n"
        except asyncio.CancelledError:
            pass

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.get("/api/sse/metrics")
async def sse_metrics():
    """Stream system metrics via SSE"""
    async def event_generator():
        try:
            while True:
                metrics = await metrics_queue.get()
                data = {
                    "cpu_percent": metrics['cpu_percent'],
                    "memory_mb": metrics['memory_mb'],
                    "memory_formatted": metrics['memory_formatted'],
                    "memory_percent": metrics['memory_percent']
                }
                yield f"data: {json.dumps(data)}\n\n"
        except asyncio.CancelledError:
            pass

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.get("/api/sse/update-progress")
async def sse_update_progress():
    """Stream update progress via SSE"""
    async def event_generator():
        try:
            while True:
                progress = await update_progress_queue.get()
                yield f"data: {json.dumps(progress)}\n\n"
        except asyncio.CancelledError:
            pass

    return StreamingResponse(event_generator(), media_type="text/event-stream")


# Entry point
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="App_SUITE Web Launcher Server")
    parser.add_argument("--port", type=int, default=9999, help="Port to run on (default: 9999)")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host to bind to (default: 127.0.0.1)")
    args = parser.parse_args()

    uvicorn.run(
        "launcher_web_server:app",
        host=args.host,
        port=args.port,
        log_level="info",
        reload=False
    )
