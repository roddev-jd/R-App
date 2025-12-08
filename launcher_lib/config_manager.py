"""
Configuration Manager for App_SUITE Launcher

Manages persistent configuration for the launcher including:
- Port management
- Version tracking
- Update settings
- Backup metadata
"""

import os
import configparser
from pathlib import Path
from datetime import datetime
from typing import Any, Optional
import logging

logger = logging.getLogger(__name__)


class ConfigManager:
    """Manages launcher configuration using INI file format"""

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize ConfigManager

        Args:
            config_path: Path to config file. If None, uses default location.
        """
        if config_path is None:
            # Default location: FlexStart/backend/launcher_config.ini
            project_root = Path(__file__).parent.parent
            config_path = project_root / "FlexStart" / "backend" / "launcher_config.ini"

        self.config_path = Path(config_path)
        self.config = configparser.ConfigParser()

        # Ensure config directory exists
        self.config_path.parent.mkdir(parents=True, exist_ok=True)

        # Load or create config
        if self.config_path.exists():
            self.load()
        else:
            self._create_default_config()
            self.save()

    def _create_default_config(self):
        """Create default configuration"""
        self.config['Launcher'] = {
            'current_version': '2.0.3',
            'installation_date': datetime.now().isoformat(),
            'last_used_port': '8005',
            'port_range_min': '8005',
            'port_range_max': '8050',
            'auto_start_server': 'false',
            'auto_open_browser': 'true',
            'server_startup_delay': '2.0',  # Legacy - kept for compatibility
            'server_startup_max_wait': '300.0',  # Increased from 10.0 to 300.0 (5 minutes) for slower systems
            'server_startup_initial_delay': '1.0',  # Increased from 0.5 to 1.0 second
            'health_check_max_retries': '60',  # Increased from 5 to 60 attempts
            'health_check_backoff_factor': '2.0',
            'health_check_base_timeout': '5.0',  # Increased from 2.0 to 5.0 seconds
            'port_reservation_timeout': '5.0',
        }

        self.config['UpdateSettings'] = {
            'last_update_check': '',
            'update_check_interval_hours': '4',
            'auto_check_updates': 'true',
            'github_repo': 'roddev-jd/R-App',
        }

        self.config['Backup'] = {
            'backup_directory': '.backups',
            'max_backups_to_keep': '1',
            'backup_version': '',
            'backup_timestamp': '',
            'backup_path': '',
            'backup_size_mb': '',
        }

        self.config['UI'] = {
            'window_position_x': 'center',
            'window_position_y': 'center',
            'theme_mode': 'System',
            'last_opened': '',
        }

        logger.info(f"Created default configuration at {self.config_path}")

    def load(self):
        """Load configuration from file"""
        try:
            self.config.read(self.config_path)
            logger.info(f"Loaded configuration from {self.config_path}")
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            raise

    def save(self):
        """Save configuration to file"""
        try:
            with open(self.config_path, 'w') as f:
                self.config.write(f)
            logger.debug(f"Saved configuration to {self.config_path}")
        except Exception as e:
            logger.error(f"Failed to save configuration: {e}")
            raise

    def get(self, section: str, key: str, default: Any = None) -> Any:
        """
        Get configuration value

        Args:
            section: Config section name
            key: Config key name
            default: Default value if key not found

        Returns:
            Configuration value or default
        """
        try:
            return self.config.get(section, key)
        except (configparser.NoSectionError, configparser.NoOptionError):
            return default

    def get_int(self, section: str, key: str, default: int = 0) -> int:
        """Get configuration value as integer"""
        try:
            return self.config.getint(section, key)
        except (configparser.NoSectionError, configparser.NoOptionError, ValueError):
            return default

    def get_float(self, section: str, key: str, default: float = 0.0) -> float:
        """Get configuration value as float"""
        try:
            return self.config.getfloat(section, key)
        except (configparser.NoSectionError, configparser.NoOptionError, ValueError):
            return default

    def get_bool(self, section: str, key: str, default: bool = False) -> bool:
        """Get configuration value as boolean"""
        try:
            return self.config.getboolean(section, key)
        except (configparser.NoSectionError, configparser.NoOptionError, ValueError):
            return default

    def set(self, section: str, key: str, value: Any):
        """
        Set configuration value

        Args:
            section: Config section name
            key: Config key name
            value: Value to set
        """
        # Ensure section exists
        if not self.config.has_section(section):
            self.config.add_section(section)

        self.config.set(section, key, str(value))
        self.save()

    # Convenience methods for common operations

    def get_last_used_port(self) -> int:
        """Get last used port"""
        return self.get_int('Launcher', 'last_used_port', 8005)

    def set_last_used_port(self, port: int):
        """Set last used port"""
        self.set('Launcher', 'last_used_port', port)
        logger.info(f"Updated last used port to {port}")

    def get_port_range(self) -> tuple[int, int]:
        """Get port range (min, max)"""
        min_port = self.get_int('Launcher', 'port_range_min', 8005)
        max_port = self.get_int('Launcher', 'port_range_max', 8050)
        return (min_port, max_port)

    def get_current_version(self) -> str:
        """Get current application version"""
        return self.get('Launcher', 'current_version', '2.0.2')

    def set_current_version(self, version: str):
        """Set current application version"""
        self.set('Launcher', 'current_version', version)
        logger.info(f"Updated version to {version}")

    def get_github_repo(self) -> str:
        """Get GitHub repository (owner/repo format)"""
        return self.get('UpdateSettings', 'github_repo', 'roddev-jd/R-App')

    def get_last_update_check(self) -> Optional[datetime]:
        """Get timestamp of last update check"""
        timestamp_str = self.get('UpdateSettings', 'last_update_check', '')
        if not timestamp_str:
            return None
        try:
            return datetime.fromisoformat(timestamp_str)
        except ValueError:
            return None

    def set_last_update_check(self, timestamp: datetime):
        """Set timestamp of last update check"""
        self.set('UpdateSettings', 'last_update_check', timestamp.isoformat())

    def get_update_check_interval(self) -> int:
        """Get update check interval in hours"""
        return self.get_int('UpdateSettings', 'update_check_interval_hours', 4)

    def should_check_for_updates(self) -> bool:
        """Check if it's time to check for updates"""
        if not self.get_bool('UpdateSettings', 'auto_check_updates', True):
            return False

        last_check = self.get_last_update_check()
        if last_check is None:
            return True

        interval_hours = self.get_update_check_interval()
        time_since_check = datetime.now() - last_check
        return time_since_check.total_seconds() > (interval_hours * 3600)

    def get_backup_info(self) -> dict:
        """Get backup metadata"""
        return {
            'version': self.get('Backup', 'backup_version', ''),
            'timestamp': self.get('Backup', 'backup_timestamp', ''),
            'path': self.get('Backup', 'backup_path', ''),
            'size_mb': self.get_float('Backup', 'backup_size_mb', 0.0),
        }

    def set_backup_info(self, version: str, timestamp: str, path: str, size_mb: float):
        """Set backup metadata"""
        self.set('Backup', 'backup_version', version)
        self.set('Backup', 'backup_timestamp', timestamp)
        self.set('Backup', 'backup_path', path)
        self.set('Backup', 'backup_size_mb', f'{size_mb:.2f}')
        logger.info(f"Recorded backup: v{version} at {path}")

    def get_backup_directory(self) -> Path:
        """Get backup directory path"""
        project_root = Path(__file__).parent.parent
        backup_dir = self.get('Backup', 'backup_directory', '.backups')
        return project_root / backup_dir

    def get_auto_open_browser(self) -> bool:
        """Check if browser should auto-open on server start"""
        return self.get_bool('Launcher', 'auto_open_browser', True)

    def get_server_startup_delay(self) -> float:
        """Get server startup delay in seconds (legacy)"""
        return self.get_float('Launcher', 'server_startup_delay', 2.0)

    def get_server_startup_max_wait(self) -> float:
        """Get maximum time to wait for server startup in seconds"""
        return self.get_float('Launcher', 'server_startup_max_wait', 10.0)

    def get_server_startup_initial_delay(self) -> float:
        """Get initial delay before starting health check polls in seconds"""
        return self.get_float('Launcher', 'server_startup_initial_delay', 0.5)

    def get_health_check_max_retries(self) -> int:
        """Get maximum number of health check retries"""
        return self.get_int('Launcher', 'health_check_max_retries', 5)

    def get_health_check_backoff_factor(self) -> float:
        """Get exponential backoff factor for health check retries"""
        return self.get_float('Launcher', 'health_check_backoff_factor', 2.0)

    def get_health_check_base_timeout(self) -> float:
        """Get base timeout for health checks in seconds"""
        return self.get_float('Launcher', 'health_check_base_timeout', 2.0)

    def get_port_reservation_timeout(self) -> float:
        """Get port reservation timeout in seconds"""
        return self.get_float('Launcher', 'port_reservation_timeout', 5.0)
