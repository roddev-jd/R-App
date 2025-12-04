"""
Main Window for App_SUITE Launcher

Primary user interface with sections for:
- Server status and control
- System resource monitoring
- Update management
- Application settings
"""

import logging
import webbrowser
from pathlib import Path
import customtkinter as ctk
from typing import Optional, Callable, Dict

from .styles import COLORS, FONTS, DIMENSIONS, get_monitor_color

logger = logging.getLogger(__name__)


class MainWindow(ctk.CTk):
    """Main launcher window"""

    def __init__(self, version: str = "2.0.2"):
        """
        Initialize MainWindow

        Args:
            version: Application version string
        """
        super().__init__()

        self.version = version
        self.current_port: Optional[int] = None
        self.server_url: Optional[str] = None
        self.update_available = False
        self.backup_available = False

        # Callbacks (to be set by SuiteLauncher)
        self.on_start_server: Optional[Callable] = None
        self.on_stop_server: Optional[Callable] = None
        self.on_reopen_browser: Optional[Callable] = None
        self.on_check_updates: Optional[Callable] = None
        self.on_perform_update: Optional[Callable] = None
        self.on_rollback: Optional[Callable] = None
        self.on_close: Optional[Callable] = None

        # Configure window
        self.title(f"App_SUITE Launcher v{version}")
        self.geometry(f"{DIMENSIONS['window_width']}x{DIMENSIONS['window_height']}")
        self.resizable(False, False)

        # Center on screen
        self._center_on_screen()

        # Try to load logo
        self.logo_image = self._load_logo()

        # Build UI
        self._create_widgets()

        # Configure close window protocol
        self.protocol("WM_DELETE_WINDOW", self._on_closing)

        logger.info("MainWindow initialized")

    def _center_on_screen(self):
        """Center window on screen"""
        self.update_idletasks()
        width = DIMENSIONS['window_width']
        height = DIMENSIONS['window_height']

        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()

        x = (screen_width - width) // 2
        y = (screen_height - height) // 2

        self.geometry(f"{width}x{height}+{x}+{y}")

    def _load_logo(self) -> Optional[ctk.CTkImage]:
        """Load application logo"""
        try:
            logo_path = Path(__file__).parent.parent.parent / "FlexStart" / "assets" / "img" / "logo.png"
            if logo_path.exists():
                from PIL import Image
                logo_img = Image.open(logo_path)
                return ctk.CTkImage(light_image=logo_img, dark_image=logo_img, size=(40, 40))
        except Exception as e:
            logger.warning(f"Failed to load logo: {e}")

        return None

    def _create_widgets(self):
        """Create all window widgets"""
        # Main container
        main_frame = ctk.CTkFrame(self, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=15, pady=15)

        # Header
        self._create_header(main_frame)

        # Status section
        self._create_status_section(main_frame)

        # Control buttons
        self._create_control_buttons(main_frame)

        # System monitor
        self._create_system_monitor(main_frame)

        # Update center
        self._create_update_center(main_frame)

    def _create_header(self, parent):
        """Create header with logo and title"""
        header_frame = ctk.CTkFrame(parent, fg_color="transparent", height=60)
        header_frame.pack(fill="x", pady=(0, DIMENSIONS['spacing_large']))
        header_frame.pack_propagate(False)

        # Logo (if available)
        if self.logo_image:
            logo_label = ctk.CTkLabel(header_frame, image=self.logo_image, text="")
            logo_label.pack(side="left", padx=(0, 10))

        # Title
        title_label = ctk.CTkLabel(
            header_frame,
            text="App_SUITE Launcher",
            font=FONTS['title'],
            text_color=COLORS['primary_pink']
        )
        title_label.pack(side="left")

        # Version
        version_label = ctk.CTkLabel(
            header_frame,
            text=f"v{self.version}",
            font=FONTS['default'],
            text_color=COLORS['gray_medium']
        )
        version_label.pack(side="right")

    def _create_status_section(self, parent):
        """Create server status display section"""
        # Section label
        ctk.CTkLabel(
            parent,
            text="SERVER STATUS",
            font=FONTS['heading'],
            text_color=COLORS['text_heading']
        ).pack(anchor="w", pady=(0, 5))

        # Status card
        self.status_card = ctk.CTkFrame(
            parent,
            fg_color=COLORS['bg_light'],
            corner_radius=DIMENSIONS['corner_radius_medium'],
            border_width=DIMENSIONS['border_width_thin'],
            border_color=COLORS['border_light']
        )
        self.status_card.pack(fill="x", pady=(0, DIMENSIONS['spacing_medium']))

        # Status indicator and text
        status_top_frame = ctk.CTkFrame(self.status_card, fg_color="transparent")
        status_top_frame.pack(fill="x", padx=15, pady=(15, 5))

        self.status_indicator = ctk.CTkLabel(
            status_top_frame,
            text="●",
            font=('Roboto', 20),
            text_color=COLORS['gray_medium']
        )
        self.status_indicator.pack(side="left", padx=(0, 5))

        self.status_text = ctk.CTkLabel(
            status_top_frame,
            text="Server not running",
            font=FONTS['button'],
            text_color=COLORS['text_dark']
        )
        self.status_text.pack(side="left")

        # Uptime
        self.uptime_label = ctk.CTkLabel(
            self.status_card,
            text="Uptime: --:--:--",
            font=FONTS['default'],
            text_color=COLORS['gray_medium']
        )
        self.uptime_label.pack(anchor="w", padx=15, pady=2)

        # URL (clickable)
        self.url_label = ctk.CTkLabel(
            self.status_card,
            text="",
            font=FONTS['default'],
            text_color=COLORS['blue'],
            cursor="hand2"
        )
        self.url_label.pack(anchor="w", padx=15, pady=(2, 15))
        self.url_label.bind("<Button-1>", lambda e: self._open_url())

    def _create_control_buttons(self, parent):
        """Create server control buttons"""
        button_frame = ctk.CTkFrame(parent, fg_color="transparent")
        button_frame.pack(fill="x", pady=DIMENSIONS['spacing_medium'])

        # Start/Stop button
        self.start_stop_button = ctk.CTkButton(
            button_frame,
            text="Start Server",
            font=FONTS['button_large'],
            fg_color=COLORS['primary_pink'],
            hover_color=COLORS['primary_pink_hover'],
            width=DIMENSIONS['button_primary_width'],
            height=DIMENSIONS['button_primary_height'],
            corner_radius=DIMENSIONS['corner_radius_large'],
            command=self._on_start_stop_clicked
        )
        self.start_stop_button.pack(side="left", padx=(0, DIMENSIONS['spacing_medium']))

        # Reopen browser button
        self.reopen_button = ctk.CTkButton(
            button_frame,
            text="Reopen Browser",
            font=FONTS['button'],
            fg_color=COLORS['cyan'],
            hover_color=COLORS['cyan_hover'],
            width=DIMENSIONS['button_secondary_width'],
            height=DIMENSIONS['button_secondary_height'],
            corner_radius=DIMENSIONS['corner_radius_large'],
            command=self._on_reopen_browser_clicked,
            state="disabled"
        )
        self.reopen_button.pack(side="left")

    def _create_system_monitor(self, parent):
        """Create system resource monitor section"""
        # Section label
        ctk.CTkLabel(
            parent,
            text="SYSTEM MONITOR",
            font=FONTS['heading'],
            text_color=COLORS['text_heading']
        ).pack(anchor="w", pady=(DIMENSIONS['spacing_large'], 5))

        # Monitor card
        monitor_card = ctk.CTkFrame(
            parent,
            fg_color=COLORS['bg_light'],
            corner_radius=DIMENSIONS['corner_radius_medium'],
            border_width=DIMENSIONS['border_width_thin'],
            border_color=COLORS['border_light']
        )
        monitor_card.pack(fill="x", pady=(0, DIMENSIONS['spacing_medium']))

        monitor_content = ctk.CTkFrame(monitor_card, fg_color="transparent")
        monitor_content.pack(fill="x", padx=15, pady=15)

        # CPU usage
        cpu_frame = ctk.CTkFrame(monitor_content, fg_color="transparent")
        cpu_frame.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(
            cpu_frame,
            text="CPU Usage:",
            font=FONTS['default'],
            text_color=COLORS['text_dark'],
            width=100,
            anchor="w"
        ).pack(side="left")

        self.cpu_progress = ctk.CTkProgressBar(
            cpu_frame,
            width=DIMENSIONS['progress_width'],
            height=DIMENSIONS['progress_height'],
            progress_color=COLORS['success']
        )
        self.cpu_progress.set(0)
        self.cpu_progress.pack(side="left", padx=10)

        self.cpu_label = ctk.CTkLabel(
            cpu_frame,
            text="0%",
            font=FONTS['default'],
            text_color=COLORS['text_dark'],
            width=50
        )
        self.cpu_label.pack(side="left")

        # Memory usage
        mem_frame = ctk.CTkFrame(monitor_content, fg_color="transparent")
        mem_frame.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(
            mem_frame,
            text="Memory:",
            font=FONTS['default'],
            text_color=COLORS['text_dark'],
            width=100,
            anchor="w"
        ).pack(side="left")

        self.mem_progress = ctk.CTkProgressBar(
            mem_frame,
            width=DIMENSIONS['progress_width'],
            height=DIMENSIONS['progress_height'],
            progress_color=COLORS['success']
        )
        self.mem_progress.set(0)
        self.mem_progress.pack(side="left", padx=10)

        self.mem_label = ctk.CTkLabel(
            mem_frame,
            text="0%",
            font=FONTS['default'],
            text_color=COLORS['text_dark'],
            width=100
        )
        self.mem_label.pack(side="left")

        # Process PID
        self.pid_label = ctk.CTkLabel(
            monitor_content,
            text="Process PID: --",
            font=FONTS['small'],
            text_color=COLORS['gray_medium']
        )
        self.pid_label.pack(anchor="w")

    def _create_update_center(self, parent):
        """Create update management section"""
        # Section label
        ctk.CTkLabel(
            parent,
            text="UPDATE CENTER",
            font=FONTS['heading'],
            text_color=COLORS['text_heading']
        ).pack(anchor="w", pady=(DIMENSIONS['spacing_large'], 5))

        # Update card
        update_card = ctk.CTkFrame(
            parent,
            fg_color=COLORS['bg_light'],
            corner_radius=DIMENSIONS['corner_radius_medium'],
            border_width=DIMENSIONS['border_width_thin'],
            border_color=COLORS['border_light']
        )
        update_card.pack(fill="x", pady=(0, DIMENSIONS['spacing_medium']))

        update_content = ctk.CTkFrame(update_card, fg_color="transparent")
        update_content.pack(fill="both", expand=True, padx=15, pady=15)

        # Status indicator
        self.update_status_label = ctk.CTkLabel(
            update_content,
            text="✓ You are running the latest version",
            font=FONTS['default'],
            text_color=COLORS['success']
        )
        self.update_status_label.pack(anchor="w", pady=(0, 5))

        # Last checked
        self.last_checked_label = ctk.CTkLabel(
            update_content,
            text="Last checked: Never",
            font=FONTS['small'],
            text_color=COLORS['gray_medium']
        )
        self.last_checked_label.pack(anchor="w", pady=(0, 10))

        # Buttons
        button_frame = ctk.CTkFrame(update_content, fg_color="transparent")
        button_frame.pack(fill="x")

        # Update/Check button
        self.update_button = ctk.CTkButton(
            button_frame,
            text="Check for Updates",
            font=FONTS['button'],
            fg_color=COLORS['gray_medium'],
            hover_color=COLORS['gray_dark'],
            width=DIMENSIONS['button_tertiary_width'],
            height=DIMENSIONS['button_tertiary_height'],
            corner_radius=DIMENSIONS['corner_radius_medium'],
            command=self._on_update_clicked
        )
        self.update_button.pack(side="left", padx=(0, DIMENSIONS['spacing_small']))

        # Rollback button
        self.rollback_button = ctk.CTkButton(
            button_frame,
            text="Rollback",
            font=FONTS['button'],
            fg_color="transparent",
            border_width=DIMENSIONS['border_width'],
            border_color=COLORS['red'],
            text_color=COLORS['red'],
            hover_color=COLORS['bg_gray'],
            width=DIMENSIONS['button_utility_width'],
            height=DIMENSIONS['button_utility_height'],
            corner_radius=DIMENSIONS['corner_radius_medium'],
            command=self._on_rollback_clicked,
            state="disabled"
        )
        self.rollback_button.pack(side="left")

    # Event handlers

    def _on_start_stop_clicked(self):
        """Handle start/stop button click"""
        current_text = self.start_stop_button.cget("text")
        if current_text == "Start Server":
            if self.on_start_server:
                self.on_start_server()
        else:
            if self.on_stop_server:
                self.on_stop_server()

    def _on_reopen_browser_clicked(self):
        """Handle reopen browser button click"""
        if self.on_reopen_browser:
            self.on_reopen_browser()

    def _on_update_clicked(self):
        """Handle update button click"""
        if self.update_available:
            if self.on_perform_update:
                self.on_perform_update()
        else:
            if self.on_check_updates:
                self.on_check_updates()

    def _on_rollback_clicked(self):
        """Handle rollback button click"""
        if self.on_rollback:
            self.on_rollback()

    def _open_url(self):
        """Open server URL in browser"""
        if self.server_url:
            webbrowser.open(self.server_url)

    # Public methods for updating UI state

    def set_server_running(self, port: int, url: str, pid: int):
        """
        Update UI to show server as running

        Args:
            port: Server port
            url: Server URL
            pid: Process PID
        """
        self.current_port = port
        self.server_url = url

        self.status_indicator.configure(text_color=COLORS['success'])
        self.status_text.configure(text=f"Running on port {port}")
        self.url_label.configure(text=url)
        self.pid_label.configure(text=f"Process PID: {pid}")

        self.start_stop_button.configure(
            text="Stop Server",
            fg_color=COLORS['red'],
            hover_color=COLORS['red_hover']
        )
        self.reopen_button.configure(state="normal")

    def set_server_stopped(self):
        """Update UI to show server as stopped"""
        self.current_port = None
        self.server_url = None

        self.status_indicator.configure(text_color=COLORS['gray_medium'])
        self.status_text.configure(text="Server not running")
        self.url_label.configure(text="")
        self.uptime_label.configure(text="Uptime: --:--:--")
        self.pid_label.configure(text="Process PID: --")

        # Reset monitors
        self.cpu_progress.set(0)
        self.cpu_label.configure(text="0%")
        self.mem_progress.set(0)
        self.mem_label.configure(text="0%")

        self.start_stop_button.configure(
            text="Start Server",
            fg_color=COLORS['primary_pink'],
            hover_color=COLORS['primary_pink_hover']
        )
        self.reopen_button.configure(state="disabled")

    def update_uptime(self, uptime_str: str):
        """Update uptime display"""
        self.uptime_label.configure(text=f"Uptime: {uptime_str}")

    def update_system_metrics(self, cpu_percent: float, memory_percent: float, memory_text: str):
        """
        Update system monitor displays

        Args:
            cpu_percent: CPU usage (0-100)
            memory_percent: Memory usage (0-100)
            memory_text: Formatted memory text (e.g., "2.1 GB")
        """
        # Update CPU
        cpu_value = cpu_percent / 100.0
        self.cpu_progress.set(cpu_value)
        self.cpu_progress.configure(progress_color=get_monitor_color(cpu_percent))
        self.cpu_label.configure(text=f"{int(cpu_percent)}%")

        # Update memory
        mem_value = memory_percent / 100.0
        self.mem_progress.set(mem_value)
        self.mem_progress.configure(progress_color=get_monitor_color(memory_percent))
        self.mem_label.configure(text=f"{int(memory_percent)}% ({memory_text})")

    def set_update_available(self, version: str):
        """
        Show update available state

        Args:
            version: New version string
        """
        self.update_available = True
        self.update_status_label.configure(
            text=f"⚠ Update available: v{version}",
            text_color=COLORS['blue']
        )
        self.update_button.configure(
            text=f"Update to v{version}",
            fg_color=COLORS['blue'],
            hover_color=COLORS['blue_hover'],
            font=('Roboto', 14, 'bold')
        )

    def set_update_checking(self):
        """Show checking for updates state"""
        self.update_button.configure(text="Checking...", state="disabled")

    def set_update_checked(self, last_check_text: str):
        """
        Update last checked timestamp

        Args:
            last_check_text: Formatted last check time
        """
        self.last_checked_label.configure(text=f"Last checked: {last_check_text}")
        self.update_button.configure(state="normal")

    def set_update_up_to_date(self):
        """Show up to date state"""
        self.update_available = False
        self.update_status_label.configure(
            text="✓ You are running the latest version",
            text_color=COLORS['success']
        )
        self.update_button.configure(
            text="Check for Updates",
            fg_color=COLORS['gray_medium'],
            hover_color=COLORS['gray_dark'],
            font=FONTS['button']
        )

    def set_backup_available(self, available: bool, version: str = ""):
        """
        Set backup availability for rollback button

        Args:
            available: Whether backup is available
            version: Backup version string
        """
        self.backup_available = available
        if available:
            self.rollback_button.configure(state="normal")
            if version:
                self.rollback_button.configure(text=f"Rollback to v{version}")
        else:
            self.rollback_button.configure(state="disabled")

    def _on_closing(self):
        """Handle window close event with confirmation"""
        from tkinter import messagebox

        result = messagebox.askyesno(
            "Confirmar cierre",
            "Si cierras este lanzador los servicios de la aplicación se detendrán, "
            "¿estás seguro de que lo quieres cerrar?",
            icon="warning"
        )

        if result:  # User clicked "Yes/Aceptar"
            # Trigger close callback to let SuiteLauncher handle cleanup
            if self.on_close:
                self.on_close()
            else:
                # Fallback if callback not set
                self.destroy()
