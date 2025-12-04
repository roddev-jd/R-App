"""Utility functions for environment variables and Server-Sent Events formatting."""

# Standard library
import logging
import os
from typing import AsyncGenerator, AsyncIterator, Union

# Constants
TRUTHY_VALUES = {"1", "true", "yes", "on"}

def getenv_int(name: str, default: int) -> int:
    """Get environment variable as integer with fallback.
    
    Args:
        name: Environment variable name
        default: Default value if variable is missing or invalid
        
    Returns:
        Integer value from environment or default
    """
    value = os.getenv(name)
    if value is None:
        return default
    
    try:
        return int(value)
    except ValueError:
        logging.warning("Invalid integer for %s: %s. Using default %s", name, value, default)
        return default

def getenv_bool(name: str, default: bool = False) -> bool:
    """Get environment variable as boolean.
    
    Args:
        name: Environment variable name
        default: Default value if variable is missing
        
    Returns:
        Boolean interpretation of environment variable
    """
    value = os.getenv(name)
    if value is None:
        return default
    
    return value.strip().lower() in TRUTHY_VALUES

def getenv_str(name: str, default: str = "") -> str:
    """Get environment variable as string with fallback.
    
    Args:
        name: Environment variable name
        default: Default value if variable is missing
        
    Returns:
        String value from environment or default
    """
    return os.getenv(name, default)

async def sse_format(iterator: AsyncIterator[str]) -> AsyncGenerator[str, None]:
    """Format async iterator messages for Server-Sent Events.
    
    Args:
        iterator: Async iterator yielding string messages
        
    Yields:
        SSE-formatted strings with 'data: ' prefix and double newlines
    """
    async for message in iterator:
        yield f"data: {message}\n\n"

async def sse_keepalive() -> str:
    """Generate SSE keep-alive message.
    
    Returns:
        SSE keep-alive formatted string
    """
    return ": keep-alive\n\n"

def safe_int_convert(value: Union[str, int, None], default: int = 0) -> int:
    """Safely convert value to integer.
    
    Args:
        value: Value to convert
        default: Default if conversion fails
        
    Returns:
        Integer value or default
    """
    if value is None:
        return default
    
    if isinstance(value, int):
        return value
    
    try:
        return int(value)
    except (ValueError, TypeError):
        return default
