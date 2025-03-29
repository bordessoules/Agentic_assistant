# tools/registry.py
"""Registry for tools with improved context support for tracking."""

import os
import importlib
import inspect
import json
import re
from typing import Dict, List, Any, Callable, Optional
from functools import wraps

# Storage for registered tools and tool context
TOOLS = {}
_tool_context = {}
_tools_discovered = False

def get_tool_context():
    """Get the current tool context."""
    return _tool_context

def set_tool_context(context):
    """Set the current tool context."""
    global _tool_context
    _tool_context = context

def tool(name, description, parameters=None):
    """
    Decorator to register a tool function.
    
    Args:
        name: Unique name for the tool
        description: Description of the tool's capabilities
        parameters: Parameter schema (JSON Schema format)
        
    Returns:
        Decorator function
    """
    def decorator(func):
        # Register the tool
        TOOLS[name] = {
            "function": func,
            "description": description,
            "parameters": parameters or {}
        }
        
        # Wrap the function to access the tool context
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Include the tool manager in kwargs if available
            if 'tool_manager' in _tool_context:
                kwargs['_tool_manager'] = _tool_context['tool_manager']
            
            # Call the original function
            return func(*args, **kwargs)
        
        return wrapper
    
    return decorator

def get_tool_function(name):
    """
    Get a tool function by name.
    
    Args:
        name: Name of the tool to retrieve
        
    Returns:
        Function or None if not found
    """
    if name in TOOLS:
        return TOOLS[name]["function"]
    return None

def get_all_schemas():
    """
    Get all tool schemas for function calling.
    
    Returns:
        List of tool schemas
    """
    schemas = []
    
    for name, info in TOOLS.items():
        # Ensure the parameters schema is correct
        parameters_schema = {
            "type": "object",  # This is crucial - parameters must be an object
            "properties": {},
            "required": []
        }
        
        # Add properties from the tool definition
        if info["parameters"]:
            for param_name, param_info in info["parameters"].items():
                parameters_schema["properties"][param_name] = param_info
                
                # Add to required list if not marked as optional
                if not (isinstance(param_info, dict) and param_info.get("optional", False)):
                    parameters_schema["required"].append(param_name)
        
        # Create the full schema
        schema = {
            "type": "function",
            "function": {
                "name": name,
                "description": info["description"],
                "parameters": parameters_schema
            }
        }
        schemas.append(schema)
    
    return schemas

def discover_tools():
    """Automatically discover tool implementations."""
    global _tools_discovered
    if _tools_discovered:
        return
    
    # Get the tools directory
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Import all Python files in the directory
    for filename in os.listdir(current_dir):
        if filename.endswith('.py') and filename != '__init__.py' and filename != 'registry.py':
            # Import the module
            module_name = filename[:-3]
            try:
                importlib.import_module(f".{module_name}", package="agentic_assistant.tools")
                print(f"✓ Registered tool module: {module_name}")
            except Exception as e:
                print(f"❌ Error importing tool module {module_name}: {str(e)}")
    
    _tools_discovered = True

# Auto-discover tools on import
discover_tools()
