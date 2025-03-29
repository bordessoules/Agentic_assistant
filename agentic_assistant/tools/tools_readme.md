# Creating Custom Tools

This guide explains how to create and integrate new tools into the Agentic Assistant framework.

## Tool System Overview

Tools in Agentic Assistant:
- Are functions that perform specific tasks
- Are registered using a decorator pattern
- Can be discovered automatically
- Support atomic ID tracking for debugging
- Are invoked by the LLM through function calling

## Creating a New Tool

### Step 1: Create a Tool File

Create a new Python file in the `tools` directory. For example, `my_custom_tool.py`:

```python
# tools/my_custom_tool.py
"""Description of what your tool does."""

from .registry import tool

@tool(
    name="my_custom_tool",
    description="A clear description of what this tool does and when to use it",
    parameters={
        "param1": {
            "type": "string",
            "description": "Description of the first parameter"
        },
        "param2": {
            "type": "number",
            "description": "Description of the second parameter",
            "optional": True
        }
    }
)
def execute(param1, param2=None, **kwargs):
    """
    Execute the custom tool functionality.
    
    Args:
        param1: First parameter
        param2: Optional second parameter
        **kwargs: Additional arguments passed by the system
        
    Returns:
        Dict containing the results and a status message
    """
    try:
        # Your tool implementation here
        result = f"Processed {param1}"
        
        if param2:
            result += f" with value {param2}"
            
        # Return result with status message
        return {
            "result": result,
            "_tool_status": f"✓ my_custom_tool: Completed successfully"
        }
        
    except Exception as e:
        return {
            "error": f"Error in my_custom_tool: {str(e)}",
            "_tool_status": f"❌ Error: {str(e)}"
        }
```

### Step 2: Tool Registration

The `@tool` decorator automatically registers your tool with the system. The decorator takes these arguments:

- `name`: A unique name for your tool (used for invoking it)
- `description`: A detailed description explaining what the tool does and when to use it
- `parameters`: A JSON Schema object describing the expected parameters

### Step 3: Return Format

Tools should return a dictionary with:

- Result data relevant to your tool
- A `_tool_status` key with a status message formatted as `✓ tool_name: Status details`
- For errors, include an `error` key and format `_tool_status` as `❌ Error: Error details`

## Best Practices

### 1. Error Handling

Always wrap your core functionality in try/except blocks and return meaningful error messages.

```python
try:
    # Tool functionality
    return {"result": result, "_tool_status": f"✓ my_tool: Success"}
except Exception as e:
    return {"error": str(e), "_tool_status": f"❌ Error: {str(e)}"}
```

### 2. Resource Management

If your tool uses external resources (files, network connections), ensure they're properly closed:

```python
resource = None
try:
    resource = open_resource()
    # Use resource
finally:
    if resource:
        close_resource(resource)
```

### 3. Parameter Validation

Validate parameters early to provide clear error messages:

```python
def execute(url, timeout=30, **kwargs):
    # Validate URL
    if not url.startswith(('http://', 'https://')):
        return {
            "error": "Invalid URL: URL must start with http:// or https://",
            "_tool_status": "❌ Error: Invalid URL format"
        }
    
    # Continue with processing...
```

### 4. Status Messages

Use consistent status message formatting:

- Success: `✓ tool_name: Specific success details`
- Error: `❌ Error: Specific error details`

### 5. Tracking Information

The `**kwargs` parameter will contain system tracking information. Don't remove it even if you don't directly use it.

## Advanced: Tool Categories

You can create specialized categories of tools by organizing them in subdirectories. For more complex tools, consider creating a class-based implementation with the execute function as a method.

## Example: Weather Tool

```python
# tools/weather_tool.py
"""Tool for retrieving weather information."""

import requests
from .registry import tool

@tool(
    name="weather",
    description="Get current weather information for a location",
    parameters={
        "location": {
            "type": "string",
            "description": "City name or location"
        },
        "units": {
            "type": "string",
            "description": "Temperature units (celsius or fahrenheit)",
            "optional": True,
            "default": "celsius"
        }
    }
)
def execute(location, units="celsius", **kwargs):
    """Get weather for a location."""
    try:
        # Simulate API call
        response = {
            "temperature": 22,
            "conditions": "Partly Cloudy",
            "humidity": 65,
            "wind_speed": 12
        }
        
        # Convert units if needed
        temp = response["temperature"]
        if units.lower() == "fahrenheit":
            temp = (temp * 9/5) + 32
        
        return {
            "location": location,
            "temperature": temp,
            "unit": "C" if units.lower() == "celsius" else "F",
            "conditions": response["conditions"],
            "humidity": response["humidity"],
            "wind_speed": response["wind_speed"],
            "_tool_status": f"✓ weather: Retrieved weather for {location}"
        }
        
    except Exception as e:
        return {
            "error": f"Weather retrieval error: {str(e)}",
            "_tool_status": f"❌ Error: {str(e)}"
        }
```
