"""
UI Styles and Color Palette for App_SUITE Launcher

Colors match the frontend design system for visual consistency.
Extracted from FlexStart/assets/css/ stylesheets.
"""

# Color Palette (matching frontend)
COLORS = {
    # Brand Primary Colors
    'primary_pink': '#ea338c',       # Brand primary - buttons, links, hover states
    'primary_pink_hover': '#c42774',  # Darker pink for hover
    'blue': '#4154f1',               # Reportes feature
    'blue_hover': '#3343d4',         # Darker blue for hover
    'red': '#e63946',                # Prod Peru feature
    'red_hover': '#c1121f',          # Darker red for hover
    'cyan': '#0dcaf0',               # Design tools section
    'cyan_hover': '#0ab3d4',         # Darker cyan for hover

    # Text Colors
    'text_dark': '#444444',          # Main text content
    'text_heading': '#000000',       # Headings and titles
    'text_light': '#ffffff',         # Text on dark backgrounds

    # Background Colors
    'bg_white': '#ffffff',           # Main background
    'bg_light': '#f8f9fa',           # Light backgrounds
    'bg_gray': '#f9f9f9',            # Subtle gray backgrounds
    'bg_dark': '#2b2b2b',            # Dark mode background
    'bg_surface': '#252525',         # Dark mode surfaces

    # Status Colors
    'success': '#10b981',            # Success states, checkmarks
    'success_hover': '#059652',      # Darker success
    'warning': '#f59e0b',            # Warning states
    'warning_hover': '#e0a800',      # Darker warning
    'error': '#df1529',              # Error states, delete actions
    'error_hover': '#c1121f',        # Darker error

    # Utility Colors
    'gray_light': '#e0e0e0',         # Borders, dividers
    'gray_medium': '#6c757d',        # Disabled buttons, secondary text
    'gray_dark': '#495057',          # Dark gray text

    # Service Category Colors (for design tools)
    'category_cyan': '#0dcaf0',      # File administration tools
    'category_orange': '#fd7e14',    # Design improvement tools
    'category_teal': '#20c997',      # Image management tools
    'category_indigo': '#6610f2',    # Premium/special tools
    'category_purple': '#8e44ad',    # Additional category

    # Special Colors
    'transparent': 'transparent',
    'border_light': '#dee2e6',       # Light borders
    'shadow': 'rgba(0, 0, 0, 0.1)',  # Drop shadows
}

# Font Configurations
FONTS = {
    'default': ('Roboto', 12),       # Default font
    'heading': ('Montserrat', 14, 'bold'),  # Headings
    'title': ('Montserrat', 16, 'bold'),    # Main title
    'button': ('Roboto', 14),               # Button text
    'button_large': ('Roboto', 16, 'bold'), # Large button text
    'small': ('Roboto', 10),                # Small text
    'monospace': ('Monaco', 11),            # Code/logs
}

# Widget Dimensions
DIMENSIONS = {
    # Window
    'window_width': 700,
    'window_height': 700,

    # Buttons
    'button_primary_width': 250,
    'button_primary_height': 50,
    'button_secondary_width': 250,
    'button_secondary_height': 50,
    'button_tertiary_width': 220,
    'button_tertiary_height': 40,
    'button_utility_width': 120,
    'button_utility_height': 40,

    # Corner Radius
    'corner_radius_large': 10,
    'corner_radius_medium': 8,
    'corner_radius_small': 5,

    # Padding & Spacing
    'padding_large': 20,
    'padding_medium': 15,
    'padding_small': 10,
    'spacing_large': 20,
    'spacing_medium': 15,
    'spacing_small': 10,

    # Borders
    'border_width': 2,
    'border_width_thin': 1,

    # Progress Bars
    'progress_height': 12,
    'progress_width': 300,
}

# CPU/Memory color thresholds
MONITOR_THRESHOLDS = {
    'safe': (0, 60),         # Green range (0-60%)
    'warning': (60, 80),     # Yellow range (60-80%)
    'critical': (80, 100),   # Red range (80-100%)
}

def get_monitor_color(percentage: float) -> str:
    """
    Get color for CPU/Memory monitor based on usage percentage

    Args:
        percentage: Usage percentage (0-100)

    Returns:
        Color hex code
    """
    if percentage < MONITOR_THRESHOLDS['safe'][1]:
        return COLORS['success']
    elif percentage < MONITOR_THRESHOLDS['warning'][1]:
        return COLORS['warning']
    else:
        return COLORS['error']


# CustomTkinter Theme Configuration
def configure_customtkinter_theme():
    """
    Configure customtkinter default color theme

    Call this at application startup before creating any widgets
    """
    import customtkinter as ctk

    # Set appearance mode (System, Light, or Dark)
    ctk.set_appearance_mode("System")

    # Set default color theme
    # Using default blue theme as base, colors overridden in individual widgets
    ctk.set_default_color_theme("blue")
