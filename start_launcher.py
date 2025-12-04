#!/usr/bin/env python3
"""
App_SUITE Web Launcher Entry Point

Starts the web-based launcher on port 9999 and opens browser.
This is the main entry point for launching the application suite.
"""

import sys
import time
import webbrowser
import subprocess
import socket
import requests
from pathlib import Path


def is_port_in_use(port: int) -> bool:
    """
    Check if a port is already in use

    Args:
        port: Port number to check

    Returns:
        True if port is occupied, False if available
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind(('127.0.0.1', port))
            return False  # Port is available
    except socket.error:
        return True  # Port is occupied


def check_server_health(port: int, timeout: float = 1.5) -> bool:
    """
    Check if there's a valid launcher server running on the port

    Args:
        port: Port number to check
        timeout: Request timeout in seconds (default: 1.5)

    Returns:
        True if server is responding correctly, False otherwise
    """
    try:
        url = f"http://127.0.0.1:{port}/api/server/status"
        response = requests.get(url, timeout=timeout)
        return response.status_code == 200
    except requests.exceptions.RequestException:
        return False


def main():
    """Main entry point for the web launcher"""
    print("=" * 70)
    print("  App_SUITE Web Launcher")
    print("  Ripley Product & Category Team")
    print("=" * 70)
    print()

    # Get launcher directory
    launcher_dir = Path(__file__).parent / "launcher_web"
    server_file = launcher_dir / "launcher_web_server.py"

    if not server_file.exists():
        print(f"❌ ERROR: Server file not found: {server_file}")
        print()
        print("Please ensure the launcher_web directory exists.")
        return 1

    port = 9999
    url = f"http://127.0.0.1:{port}"

    # Check if port is already in use
    if is_port_in_use(port):
        print(f"⚠️  Port {port} is already in use")
        print(f"🔍 Checking if it's a valid launcher server...")
        print()

        # Perform health check
        if check_server_health(port):
            # Valid launcher server found - reopen browser
            print(f"✅ Found active launcher server on port {port}")
            print(f"🌐 Reopening browser to existing session...")
            print()
            webbrowser.open(url)
            print(f"✅ Browser opened to existing session!")
            print()
            print(f"   Access the launcher at: {url}")
            print()
            print("The launcher server is already running.")
            print("Close the terminal where the server is running to stop it.")
            print("=" * 70)
            return 0  # Success
        else:
            # Port occupied by another process
            print(f"❌ ERROR: Port {port} is occupied by another process")
            print()
            print("Please stop the other process or check if it's a stale launcher process.")
            print(f"You can find the process using: lsof -i :{port}")
            print()
            return 1  # Error

    # Port is free - proceed with normal startup
    print(f"🚀 Starting launcher web server on port {port}...")
    print()

    # Start server process
    try:
        proc = subprocess.Popen(
            [sys.executable, str(server_file)],
            cwd=Path(__file__).parent,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        # Wait for server to start
        print("⏳ Waiting for server to initialize...")
        time.sleep(2)

        # Check if process is still running
        if proc.poll() is not None:
            # Process died
            stdout, stderr = proc.communicate()
            print("❌ ERROR: Server failed to start")
            print()
            if stdout:
                print("STDOUT:", stdout.decode())
            if stderr:
                print("STDERR:", stderr.decode())
            return 1

        # Open browser
        print(f"🌐 Opening browser to {url}")
        print()
        webbrowser.open(url)

        print("✅ Launcher is running!")
        print()
        print(f"   Access the launcher at: {url}")
        print()
        print("Press Ctrl+C to stop the launcher")
        print("=" * 70)
        print()

        # Wait for process
        proc.wait()

    except KeyboardInterrupt:
        print()
        print()
        print("🛑 Shutting down launcher...")
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
        print("✅ Launcher stopped")
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
