"""
Update Dialog for App_SUITE Launcher

Modal dialog for displaying update information and prompting user action.
Shows version info, release notes, and update/ignore options.
"""

import logging
import customtkinter as ctk
from typing import Dict, Optional, Callable

from .styles import COLORS, FONTS, DIMENSIONS

logger = logging.getLogger(__name__)


class UpdateDialog(ctk.CTkToplevel):
    """Modal dialog for update notifications"""

    def __init__(
        self,
        parent: ctk.CTk,
        update_info: Dict,
        update_callback: Optional[Callable] = None,
        ignore_callback: Optional[Callable] = None
    ):
        """
        Initialize UpdateDialog

        Args:
            parent: Parent window
            update_info: Update information dict from UpdateManager
            update_callback: Callback for "Update Now" button
            ignore_callback: Callback for "Ignore" button
        """
        super().__init__(parent)

        self.parent = parent
        self.update_info = update_info
        self.update_callback = update_callback
        self.ignore_callback = ignore_callback
        self.user_choice = None  # 'update', 'ignore', or None

        # Configure window
        self.title("Update Available")
        self.geometry("500x450")
        self.resizable(False, False)

        # Make modal
        self.transient(parent)
        self.grab_set()

        # Center on parent
        self._center_on_parent()

        # Build UI
        self._create_widgets()

        logger.debug(f"UpdateDialog created for version {update_info.get('latest_version')}")

    def _center_on_parent(self):
        """Center dialog on parent window"""
        self.update_idletasks()

        parent_x = self.parent.winfo_x()
        parent_y = self.parent.winfo_y()
        parent_width = self.parent.winfo_width()
        parent_height = self.parent.winfo_height()

        dialog_width = 500
        dialog_height = 450

        x = parent_x + (parent_width - dialog_width) // 2
        y = parent_y + (parent_height - dialog_height) // 2

        self.geometry(f"{dialog_width}x{dialog_height}+{x}+{y}")

    def _create_widgets(self):
        """Create dialog widgets"""
        # Main frame
        main_frame = ctk.CTkFrame(self, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=DIMENSIONS['padding_large'], pady=DIMENSIONS['padding_large'])

        # Title
        title_label = ctk.CTkLabel(
            main_frame,
            text="🎉 Update Available!",
            font=FONTS['title'],
            text_color=COLORS['primary_pink']
        )
        title_label.pack(pady=(0, DIMENSIONS['spacing_medium']))

        # Version info frame
        version_frame = ctk.CTkFrame(main_frame, fg_color=COLORS['bg_light'], corner_radius=DIMENSIONS['corner_radius_medium'])
        version_frame.pack(fill="x", pady=DIMENSIONS['spacing_medium'])

        current_version = self.update_info.get('current_version', 'Unknown')
        latest_version = self.update_info.get('latest_version', 'Unknown')

        ctk.CTkLabel(
            version_frame,
            text=f"Current version: {current_version}",
            font=FONTS['default'],
            text_color=COLORS['text_dark']
        ).pack(pady=(10, 5), padx=10, anchor="w")

        ctk.CTkLabel(
            version_frame,
            text=f"Latest version: {latest_version}",
            font=('Roboto', 14, 'bold'),
            text_color=COLORS['blue']
        ).pack(pady=(0, 10), padx=10, anchor="w")

        # Release notes section
        notes_label = ctk.CTkLabel(
            main_frame,
            text="Release Notes:",
            font=FONTS['heading'],
            text_color=COLORS['text_heading']
        )
        notes_label.pack(pady=(DIMENSIONS['spacing_medium'], DIMENSIONS['spacing_small']), anchor="w")

        # Scrollable text for release notes
        notes_frame = ctk.CTkFrame(main_frame, fg_color=COLORS['bg_light'], corner_radius=DIMENSIONS['corner_radius_medium'])
        notes_frame.pack(fill="both", expand=True, pady=(0, DIMENSIONS['spacing_medium']))

        notes_text = ctk.CTkTextbox(
            notes_frame,
            font=FONTS['default'],
            fg_color=COLORS['bg_light'],
            text_color=COLORS['text_dark'],
            wrap="word",
            activate_scrollbars=True
        )
        notes_text.pack(fill="both", expand=True, padx=5, pady=5)

        # Insert release notes
        release_notes = self.update_info.get('release_notes', 'No release notes available.')
        # Truncate if too long
        if len(release_notes) > 1000:
            release_notes = release_notes[:1000] + "\n\n... (truncated)"

        notes_text.insert("1.0", release_notes)
        notes_text.configure(state="disabled")  # Make read-only

        # Download size (if available)
        # Note: GitHub API doesn't always provide size, so this is optional
        size_label = ctk.CTkLabel(
            main_frame,
            text="Download size: Calculating...",
            font=FONTS['small'],
            text_color=COLORS['gray_medium']
        )
        size_label.pack(pady=(0, DIMENSIONS['spacing_medium']))

        # Button frame
        button_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        button_frame.pack(pady=(DIMENSIONS['spacing_medium'], 0))

        # Update Now button
        update_button = ctk.CTkButton(
            button_frame,
            text="Update Now",
            font=FONTS['button'],
            fg_color=COLORS['blue'],
            hover_color=COLORS['blue_hover'],
            width=150,
            height=40,
            corner_radius=DIMENSIONS['corner_radius_medium'],
            command=self._on_update
        )
        update_button.pack(side="left", padx=(0, DIMENSIONS['spacing_small']))

        # Ignore button
        ignore_button = ctk.CTkButton(
            button_frame,
            text="Ignore",
            font=FONTS['button'],
            fg_color=COLORS['gray_medium'],
            hover_color=COLORS['gray_dark'],
            width=100,
            height=40,
            corner_radius=DIMENSIONS['corner_radius_medium'],
            command=self._on_ignore
        )
        ignore_button.pack(side="left")

    def _on_update(self):
        """Handle Update Now button click"""
        logger.info("User chose to update")
        self.user_choice = 'update'

        if self.update_callback:
            self.update_callback(self.update_info)

        self.close()

    def _on_ignore(self):
        """Handle Ignore button click"""
        logger.info("User chose to ignore update")
        self.user_choice = 'ignore'

        if self.ignore_callback:
            self.ignore_callback()

        self.close()

    def close(self):
        """Close dialog"""
        self.grab_release()
        self.destroy()


def show_update_dialog(
    parent: ctk.CTk,
    update_info: Dict,
    update_callback: Optional[Callable] = None,
    ignore_callback: Optional[Callable] = None
) -> UpdateDialog:
    """
    Convenience function to show update dialog

    Args:
        parent: Parent window
        update_info: Update information dict
        update_callback: Callback for update action
        ignore_callback: Callback for ignore action

    Returns:
        UpdateDialog instance
    """
    dialog = UpdateDialog(parent, update_info, update_callback, ignore_callback)
    return dialog


class UpdateCompleteDialog(ctk.CTkToplevel):
    """Simple dialog showing update completion"""

    def __init__(self, parent: ctk.CTk, version: str):
        """
        Initialize UpdateCompleteDialog

        Args:
            parent: Parent window
            version: New version string
        """
        super().__init__(parent)

        self.title("Update Complete")
        self.geometry("400x200")
        self.resizable(False, False)

        self.transient(parent)
        self.grab_set()

        # Center on parent
        self.update_idletasks()
        parent_x = parent.winfo_x()
        parent_y = parent.winfo_y()
        parent_width = parent.winfo_width()
        parent_height = parent.winfo_height()

        x = parent_x + (parent_width - 400) // 2
        y = parent_y + (parent_height - 200) // 2
        self.geometry(f"400x200+{x}+{y}")

        # Create widgets
        main_frame = ctk.CTkFrame(self, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(
            main_frame,
            text="✅ Update Complete!",
            font=FONTS['title'],
            text_color=COLORS['success']
        ).pack(pady=(0, 10))

        ctk.CTkLabel(
            main_frame,
            text=f"App_SUITE v{version} has been installed successfully.",
            font=FONTS['default'],
            text_color=COLORS['text_dark'],
            wraplength=350
        ).pack(pady=10)

        ctk.CTkLabel(
            main_frame,
            text="The application will restart shortly...",
            font=FONTS['small'],
            text_color=COLORS['gray_medium']
        ).pack(pady=5)

        ctk.CTkButton(
            main_frame,
            text="OK",
            font=FONTS['button'],
            fg_color=COLORS['primary_pink'],
            hover_color=COLORS['primary_pink_hover'],
            width=120,
            height=40,
            command=self.destroy
        ).pack(pady=(15, 0))
