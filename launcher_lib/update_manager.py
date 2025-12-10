"""
Update Manager for App_SUITE Launcher

Handles application updates from GitHub releases:
- Version checking and comparison
- Download and installation
- Backup and rollback
- Dependency management
"""

import os
import sys
import json
import shutil
import subprocess
import tempfile
import zipfile
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Callable
from packaging import version as pkg_version
import requests
import urllib3

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from .config_manager import ConfigManager

logger = logging.getLogger(__name__)


class UpdateManager:
    """Manages application updates from GitHub releases"""

    def __init__(self, config_manager: ConfigManager):
        """
        Initialize UpdateManager

        Args:
            config_manager: ConfigManager instance
        """
        self.config = config_manager
        self.project_root = Path(__file__).parent.parent
        self.backup_dir = self.config.get_backup_directory()
        self.github_repo = self.config.get_github_repo()
        self.latest_release: Optional[Dict] = None

        logger.info(f"UpdateManager initialized (repo: {self.github_repo})")

    def check_for_updates(self) -> Optional[Dict]:
        """
        Check GitHub for new releases

        Returns:
            Release info dict if update available, None otherwise
        """
        try:
            # Build API URL
            api_url = f"https://api.github.com/repos/{self.github_repo}/releases/latest"

            logger.info(f"Checking for updates: {api_url}")

            # Make request
            headers = {'Accept': 'application/vnd.github.v3+json'}
            response = requests.get(api_url, headers=headers, timeout=10, verify=False)
            response.raise_for_status()

            release = response.json()
            remote_version = release['tag_name'].lstrip('v')

            # Update last check timestamp
            self.config.set_last_update_check(datetime.now())

            # Compare versions
            local_version = self.config.get_current_version()
            comparison = self.compare_versions(local_version, remote_version)

            if comparison < 0:
                # Update available
                self.latest_release = release
                logger.info(f"Update available: {local_version} -> {remote_version}")
                return {
                    'available': True,
                    'current_version': local_version,
                    'latest_version': remote_version,
                    'release_url': release['html_url'],
                    'release_notes': release.get('body', 'No release notes available'),
                    'published_at': release['published_at'],
                    'download_url': self._get_download_url(release),
                }
            else:
                logger.info(f"Already up to date (version: {local_version})")
                return None

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to check for updates: {e}")
            return None
        except Exception as e:
            logger.error(f"Error checking for updates: {e}")
            return None

    def compare_versions(self, local: str, remote: str) -> int:
        """
        Compare two semantic versions

        Args:
            local: Local version string
            remote: Remote version string

        Returns:
            -1 if local < remote (update available)
             0 if local == remote (up to date)
             1 if local > remote (dev version)
        """
        try:
            local_ver = pkg_version.parse(local)
            remote_ver = pkg_version.parse(remote)

            if local_ver < remote_ver:
                return -1
            elif local_ver > remote_ver:
                return 1
            else:
                return 0
        except Exception as e:
            logger.error(f"Error comparing versions: {e}")
            return 0

    def _get_download_url(self, release: Dict) -> Optional[str]:
        """
        Extract download URL from release assets

        Args:
            release: GitHub release dict

        Returns:
            Download URL or None
        """
        # Look for ZIP asset first
        assets = release.get('assets', [])
        for asset in assets:
            if asset['name'].endswith('.zip'):
                return asset['browser_download_url']

        # Fallback to zipball_url
        return release.get('zipball_url')

    def download_release(
        self,
        download_url: str,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> Optional[Path]:
        """
        Download release ZIP file

        Args:
            download_url: URL to download from
            progress_callback: Optional callback(bytes_downloaded, total_bytes)

        Returns:
            Path to downloaded file or None on error
        """
        try:
            logger.info(f"Downloading release from {download_url}")

            # Create temp directory
            temp_dir = Path(tempfile.mkdtemp(prefix='suite_update_'))
            download_path = temp_dir / "update.zip"

            # Stream download with progress
            response = requests.get(download_url, stream=True, timeout=30, verify=False)
            response.raise_for_status()

            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0

            with open(download_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)

                        if progress_callback and total_size > 0:
                            progress_callback(downloaded, total_size)

            logger.info(f"Downloaded {downloaded} bytes to {download_path}")

            # Verify download
            if total_size > 0 and downloaded != total_size:
                logger.error(f"Download incomplete: {downloaded}/{total_size} bytes")
                return None

            return download_path

        except Exception as e:
            logger.error(f"Failed to download release: {e}")
            return None

    def extract_release(self, zip_path: Path) -> Optional[Path]:
        """
        Extract release ZIP to temporary directory

        Args:
            zip_path: Path to ZIP file

        Returns:
            Path to extracted directory or None on error
        """
        try:
            logger.info(f"Extracting {zip_path}")

            extract_dir = zip_path.parent / "extracted"
            extract_dir.mkdir(exist_ok=True)

            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)

            logger.info(f"Extracted to {extract_dir}")

            # Find root directory (GitHub zips have a single root folder)
            subdirs = list(extract_dir.iterdir())
            if len(subdirs) == 1 and subdirs[0].is_dir():
                return subdirs[0]
            else:
                return extract_dir

        except Exception as e:
            logger.error(f"Failed to extract release: {e}")
            return None

    def create_backup(self) -> bool:
        """
        Create backup of current installation

        Returns:
            True if backup successful, False otherwise
        """
        try:
            # Create backup directory
            self.backup_dir.mkdir(parents=True, exist_ok=True)

            # Generate backup name with timestamp
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_name = f"backup_{timestamp}"
            backup_path = self.backup_dir / backup_name

            logger.info(f"Creating backup at {backup_path}")

            # Copy FlexStart directory
            source_dir = self.project_root / "FlexStart"
            if not source_dir.exists():
                logger.error(f"Source directory not found: {source_dir}")
                return False

            shutil.copytree(source_dir, backup_path / "FlexStart")

            # Calculate backup size
            backup_size_bytes = sum(
                f.stat().st_size for f in backup_path.rglob('*') if f.is_file()
            )
            backup_size_mb = backup_size_bytes / (1024 ** 2)

            # Save backup metadata
            current_version = self.config.get_current_version()
            self.config.set_backup_info(
                version=current_version,
                timestamp=timestamp,
                path=str(backup_path),
                size_mb=backup_size_mb
            )

            logger.info(f"Backup created: {backup_size_mb:.1f} MB")

            # Cleanup old backups (keep only 1)
            self._cleanup_old_backups()

            return True

        except Exception as e:
            logger.error(f"Failed to create backup: {e}")
            return False

    def _cleanup_old_backups(self):
        """Remove old backups (keep only max_backups_to_keep)"""
        try:
            max_backups = self.config.get_int('Backup', 'max_backups_to_keep', 1)

            if not self.backup_dir.exists():
                return

            # Get all backup directories
            backups = sorted(
                [d for d in self.backup_dir.iterdir() if d.is_dir()],
                key=lambda x: x.stat().st_mtime,
                reverse=True  # Newest first
            )

            # Remove old backups
            for old_backup in backups[max_backups:]:
                logger.info(f"Removing old backup: {old_backup}")
                shutil.rmtree(old_backup)

        except Exception as e:
            logger.warning(f"Failed to cleanup old backups: {e}")

    def install_update(self, source_dir: Path) -> bool:
        """
        Install update from extracted source directory

        Args:
            source_dir: Path to extracted update files

        Returns:
            True if installation successful, False otherwise
        """
        try:
            logger.info(f"Installing update from {source_dir}")

            # Verify FlexStart directory exists in source
            source_flexstart = source_dir / "FlexStart"
            if not source_flexstart.exists():
                logger.error(f"FlexStart directory not found in update: {source_dir}")
                return False

            target_flexstart = self.project_root / "FlexStart"

            # Backup important files to preserve
            preserve_files = [
                "FlexStart/backend/launcher_config.ini",
                "FlexStart/apps/reportes/backend/config.ini",
                "FlexStart/apps/prod_peru/backend/config.ini",
                "FlexStart/data/birthdays.json",
            ]

            preserved = {}
            for rel_path in preserve_files:
                full_path = self.project_root / rel_path
                if full_path.exists():
                    preserved[rel_path] = full_path.read_text()
                    logger.debug(f"Preserved: {rel_path}")

            # Remove old FlexStart directory
            if target_flexstart.exists():
                shutil.rmtree(target_flexstart)

            # Copy new files
            shutil.copytree(source_flexstart, target_flexstart)
            logger.info("Files copied successfully")

            # Restore preserved files
            for rel_path, content in preserved.items():
                full_path = self.project_root / rel_path
                full_path.parent.mkdir(parents=True, exist_ok=True)
                full_path.write_text(content)
                logger.debug(f"Restored: {rel_path}")

            # Install dependencies
            self.install_dependencies()

            logger.info("Update installed successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to install update: {e}")
            return False

    def install_dependencies(self) -> bool:
        """
        Install Python dependencies from requirements file

        Returns:
            True if successful, False otherwise
        """
        try:
            requirements_file = self.project_root / "requirements_server.txt"

            if not requirements_file.exists():
                logger.warning(f"Requirements file not found: {requirements_file}")
                return True  # Not a critical error

            logger.info(f"Installing dependencies from {requirements_file}")

            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", "-r", str(requirements_file), "--upgrade"],
                capture_output=True,
                text=True,
                timeout=300  # 5 minutes timeout
            )

            if result.returncode == 0:
                logger.info("Dependencies installed successfully")
                return True
            else:
                logger.warning(f"Dependency installation had issues: {result.stderr}")
                return True  # Continue anyway, not critical

        except Exception as e:
            logger.error(f"Failed to install dependencies: {e}")
            return True  # Continue anyway

    def rollback(self) -> bool:
        """
        Rollback to previous backup

        Returns:
            True if rollback successful, False otherwise
        """
        try:
            backup_info = self.config.get_backup_info()
            backup_path = Path(backup_info['path'])

            if not backup_path or not backup_path.exists():
                logger.error("No backup available for rollback")
                return False

            logger.info(f"Rolling back to backup: {backup_path}")

            # Remove current FlexStart directory
            target_flexstart = self.project_root / "FlexStart"
            if target_flexstart.exists():
                shutil.rmtree(target_flexstart)

            # Restore from backup
            backup_flexstart = backup_path / "FlexStart"
            shutil.copytree(backup_flexstart, target_flexstart)

            # Update version in config
            backup_version = backup_info['version']
            self.config.set_current_version(backup_version)

            logger.info(f"Rollback complete to version {backup_version}")
            return True

        except Exception as e:
            logger.error(f"Failed to rollback: {e}")
            return False

    def has_backup(self) -> bool:
        """
        Check if backup is available

        Returns:
            True if backup exists
        """
        backup_info = self.config.get_backup_info()
        backup_path = backup_info.get('path', '')

        if not backup_path:
            return False

        return Path(backup_path).exists()

    def perform_full_update(
        self,
        update_info: Dict,
        progress_callback: Optional[Callable[[str, int], None]] = None
    ) -> bool:
        """
        Perform complete update process

        Args:
            update_info: Update information from check_for_updates()
            progress_callback: Optional callback(status_message, progress_percent)

        Returns:
            True if update successful, False otherwise
        """
        try:
            download_url = update_info['download_url']
            new_version = update_info['latest_version']

            # Step 1: Create backup
            if progress_callback:
                progress_callback("Creating backup...", 10)

            if not self.create_backup():
                logger.error("Failed to create backup, aborting update")
                return False

            # Step 2: Download release
            if progress_callback:
                progress_callback("Downloading update...", 20)

            def download_progress(downloaded, total):
                if progress_callback and total > 0:
                    percent = 20 + int((downloaded / total) * 40)  # 20-60%
                    progress_callback(f"Downloading... {downloaded}/{total} bytes", percent)

            zip_path = self.download_release(download_url, download_progress)
            if not zip_path:
                logger.error("Download failed, aborting update")
                return False

            # Step 3: Extract
            if progress_callback:
                progress_callback("Extracting files...", 65)

            source_dir = self.extract_release(zip_path)
            if not source_dir:
                logger.error("Extraction failed, aborting update")
                return False

            # Step 4: Install
            if progress_callback:
                progress_callback("Installing update...", 75)

            if not self.install_update(source_dir):
                logger.error("Installation failed, rolling back...")
                if progress_callback:
                    progress_callback("Installation failed, rolling back...", 80)
                self.rollback()
                return False

            # Step 5: Update version
            if progress_callback:
                progress_callback("Finalizing...", 95)

            self.config.set_current_version(new_version)

            # Cleanup temp files
            try:
                shutil.rmtree(zip_path.parent)
            except:
                pass

            if progress_callback:
                progress_callback("Update complete!", 100)

            logger.info(f"Update to version {new_version} completed successfully")
            return True

        except Exception as e:
            logger.error(f"Update failed: {e}")
            if progress_callback:
                progress_callback(f"Update failed: {e}", 0)
            return False
