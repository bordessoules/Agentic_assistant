# callbacks.py
"""
Simple callback registry for the agent system.
Provides a lightweight alternative to a full event system.
"""

from typing import Dict, List, Callable, Any


class CallbackManager:
    """Manages callback functions for various events in the system."""
    
    def __init__(self):
        """Initialize an empty callback registry."""
        self._callbacks: Dict[str, List[Callable]] = {}
    
    def register(self, event_name: str, callback_fn: Callable) -> None:
        """Register a callback function for a specific event."""
        if event_name not in self._callbacks:
            self._callbacks[event_name] = []
        self._callbacks[event_name].append(callback_fn)
    
    def trigger(self, event_name: str, **data) -> None:
        """Trigger an event with the given data."""
        for callback in self._callbacks.get(event_name, []):
            try:
                callback(**data)
            except Exception as e:
                print(f"Error in callback for {event_name}: {str(e)}")
    
    def clear(self, event_name: str = None) -> None:
        """Clear callbacks for a specific event or all events."""
        if event_name is None:
            self._callbacks = {}
        elif event_name in self._callbacks:
            self._callbacks[event_name] = []


# Global callback manager instance for convenience
callbacks = CallbackManager()


# Common event names used in the system
class Events:
    """Common event names used throughout the system."""
    # Tool events
    TOOL_START = "tool_start"
    TOOL_END = "tool_end"
    TOOL_ERROR = "tool_error"
    
    # Response events
    RESPONSE_COMPLETE = "response_complete"
    
    # Token usage events
    TOKEN_USAGE = "token_usage"
