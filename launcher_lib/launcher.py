#!/usr/bin/env python3
"""
App_SUITE Launcher

Professional launcher for the App_SUITE application with:
- Automatic port rotation (8005-8050)
- System resource monitoring
- GitHub-based automatic updates
- Rollback capability
- Modern customtkinter UI

Usage:
    python3 launcher.py

Author: App_SUITE Team
Version: 2.0.2
"""

import sys
import logging
from pathlib import Path

# Configure logging
log_file = Path(__file__).parent / "launcher.log"
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


def check_dependencies():
    """Check if all required dependencies are installed"""
    missing = []

    try:
        import customtkinter
    except ImportError:
        missing.append("customtkinter")

    try:
        import psutil
    except ImportError:
        missing.append("psutil")

    try:
        import packaging
    except ImportError:
        missing.append("packaging")

    try:
        import PIL
    except ImportError:
        missing.append("Pillow")

    try:
        import requests
    except ImportError:
        missing.append("requests")

    if missing:
        logger.error(f"Missing required dependencies: {', '.join(missing)}")
        print("\n❌ Missing required dependencies!")
        print("\nPlease install them with:")
        print(f"    pip install {' '.join(missing)}")
        print("\nOr install all dependencies:")
        print("    pip install -r requirements_server.txt")
        return False

    return True


def check_python_version():
    """Check if Python version is compatible"""
    if sys.version_info < (3, 10):
        logger.error(f"Python 3.10+ required, got {sys.version}")
        print(f"\n❌ Python 3.10 or higher is required!")
        print(f"Current version: {sys.version}")
        print("\nPlease upgrade Python:")
        print("    https://www.python.org/downloads/")
        return False

    return True


def main():
    """Main entry point"""
    logger.info("="*60)
    logger.info("App_SUITE Launcher starting...")
    logger.info("="*60)

    # Check Python version
    if not check_python_version():
        sys.exit(1)

    # Check dependencies
    if not check_dependencies():
        sys.exit(1)

    try:
        # Import and run launcher
        from launcher_lib.app import SuiteLauncher

        logger.info("Creating SuiteLauncher instance")
        launcher = SuiteLauncher()

        logger.info("Starting launcher GUI")
        launcher.run()

        logger.info("Launcher exited normally")

    except KeyboardInterrupt:
        logger.info("Launcher interrupted by user")
        sys.exit(0)

    except Exception as e:
        logger.exception("Fatal error in launcher")
        print(f"\n❌ Fatal error: {e}")
        print(f"\nCheck logs at: {log_file}")
        sys.exit(1)


if __name__ == "__main__":
    main()
