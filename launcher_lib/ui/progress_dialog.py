"""
Progress Dialog for App_SUITE Launcher

Modal dialog for displaying progress during:
- Update downloads
- Update installation
- Other long-running operations
"""

import logging
import customtkinter as ctk
from typing import Optional, Callable

from .styles import COLORS, FONTS, DIMENSIONS

logger = logging.getLogger(__name__)


class ProgressDialog(ctk.CTkToplevel):
    """Modal progress dialog with progress bar and status"""

    def __init__(
        self,
        parent: ctk.CTk,
        title: str = "Processing...",
        allow_cancel: bool = False
    ):
        """
        Initialize ProgressDialog

        Args:
            parent: Parent window
            title: Dialog title
            allow_cancel: Whether to show cancel button
        """
        super().__init__(parent)

        self.parent = parent
        self.allow_cancel = allow_cancel
        self.cancel_callback: Optional[Callable] = None
        self.cancelled = False

        # Configure window
        self.title(title)
        self.geometry("450x250")
        self.resizable(False, False)

        # Make modal
        self.transient(parent)
        self.grab_set()

        # Center on parent
        self._center_on_parent()

        # Build UI
        self._create_widgets()

        logger.debug(f"ProgressDialog created: {title}")

    def _center_on_parent(self):
        """Center dialog on parent window"""
        self.update_idletasks()

        parent_x = self.parent.winfo_x()
        parent_y = self.parent.winfo_y()
        parent_width = self.parent.winfo_width()
        parent_height = self.parent.winfo_height()

        dialog_width = 450
        dialog_height = 250

        x = parent_x + (parent_width - dialog_width) // 2
        y = parent_y + (parent_height - dialog_height) // 2

        self.geometry(f"{dialog_width}x{dialog_height}+{x}+{y}")

    def _create_widgets(self):
        """Create dialog widgets"""
        # Main frame
        main_frame = ctk.CTkFrame(self, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=DIMENSIONS['padding_large'], pady=DIMENSIONS['padding_large'])

        # Title label
        self.title_label = ctk.CTkLabel(
            main_frame,
            text="Please wait...",
            font=FONTS['heading'],
            text_color=COLORS['text_dark']
        )
        self.title_label.pack(pady=(0, DIMENSIONS['spacing_large']))

        # Progress bar
        self.progress_bar = ctk.CTkProgressBar(
            main_frame,
            width=400,
            height=DIMENSIONS['progress_height'],
            progress_color=COLORS['primary_pink']
        )
        self.progress_bar.set(0)
        self.progress_bar.pack(pady=DIMENSIONS['spacing_medium'])

        # Percentage label
        self.percentage_label = ctk.CTkLabel(
            main_frame,
            text="0%",
            font=FONTS['button'],
            text_color=COLORS['gray_dark']
        )
        self.percentage_label.pack()

        # Status label
        self.status_label = ctk.CTkLabel(
            main_frame,
            text="Initializing...",
            font=FONTS['default'],
            text_color=COLORS['gray_medium']
        )
        self.status_label.pack(pady=(DIMENSIONS['spacing_medium'], 0))

        # Details label (for file sizes, etc.)
        self.details_label = ctk.CTkLabel(
            main_frame,
            text="",
            font=FONTS['small'],
            text_color=COLORS['gray_medium']
        )
        self.details_label.pack(pady=(DIMENSIONS['spacing_small'], 0))

        # Spacer
        ctk.CTkFrame(main_frame, fg_color="transparent", height=20).pack()

        # Cancel button (if allowed)
        if self.allow_cancel:
            self.cancel_button = ctk.CTkButton(
                main_frame,
                text="Cancel",
                font=FONTS['button'],
                fg_color=COLORS['gray_medium'],
                hover_color=COLORS['gray_dark'],
                width=120,
                height=DIMENSIONS['button_utility_height'],
                corner_radius=DIMENSIONS['corner_radius_medium'],
                command=self._on_cancel
            )
            self.cancel_button.pack()

    def set_progress(self, progress: float):
        """
        Set progress bar value

        Args:
            progress: Progress value (0.0 to 1.0)
        """
        progress = max(0.0, min(1.0, progress))  # Clamp to 0-1
        self.progress_bar.set(progress)
        self.percentage_label.configure(text=f"{int(progress * 100)}%")
        self.update()

    def set_progress_percent(self, percent: int):
        """
        Set progress by percentage

        Args:
            percent: Percentage (0 to 100)
        """
        self.set_progress(percent / 100.0)

    def set_status(self, status: str):
        """
        Set status message

        Args:
            status: Status text
        """
        self.status_label.configure(text=status)
        self.update()

    def set_details(self, details: str):
        """
        Set details message

        Args:
            details: Details text
        """
        self.details_label.configure(text=details)
        self.update()

    def set_title_text(self, text: str):
        """
        Set title text

        Args:
            text: Title text
        """
        self.title_label.configure(text=text)
        self.update()

    def set_cancel_callback(self, callback: Callable):
        """
        Set callback function for cancel button

        Args:
            callback: Function to call when cancelled
        """
        self.cancel_callback = callback

    def disable_cancel(self):
        """Disable cancel button during critical operations"""
        if self.allow_cancel and hasattr(self, 'cancel_button'):
            self.cancel_button.configure(state="disabled")

    def enable_cancel(self):
        """Enable cancel button"""
        if self.allow_cancel and hasattr(self, 'cancel_button'):
            self.cancel_button.configure(state="normal")

    def _on_cancel(self):
        """Handle cancel button click"""
        self.cancelled = True
        if self.cancel_callback:
            self.cancel_callback()
        self.close()

    def is_cancelled(self) -> bool:
        """
        Check if dialog was cancelled

        Returns:
            True if cancelled
        """
        return self.cancelled

    def close(self):
        """Close dialog"""
        self.grab_release()
        self.destroy()


class SimpleProgressDialog:
    """
    Simplified progress dialog interface for easy usage

    Example:
        with SimpleProgressDialog(parent, "Downloading...") as dialog:
            for i in range(100):
                dialog.set_progress(i / 100)
                # do work
    """

    def __init__(
        self,
        parent: ctk.CTk,
        title: str = "Processing...",
        allow_cancel: bool = False
    ):
        """
        Initialize SimpleProgressDialog

        Args:
            parent: Parent window
            title: Dialog title
            allow_cancel: Whether to allow cancellation
        """
        self.dialog = ProgressDialog(parent, title, allow_cancel)

    def __enter__(self):
        """Context manager enter"""
        return self.dialog

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.dialog.close()
        return False

    def set_progress(self, progress: float):
        """Set progress (0.0 to 1.0)"""
        self.dialog.set_progress(progress)

    def set_status(self, status: str):
        """Set status message"""
        self.dialog.set_status(status)
