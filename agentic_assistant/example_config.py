# example.config.py
"""
Example configuration file for the assistant system.
Copy this file to config.py and update with your actual values.
"""

# SearxNG settings
SEARXNG_URL = "http://localhost:8080"  # Update with your SearxNG instance URL
SEARCH_RESULTS_COUNT = 10

# HTTP request settings
HTTP_TIMEOUT = 10
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"

# Browser settings (for advanced webpage reader)
BROWSER_TIMEOUT = 300000
VIEWPORT_WIDTH = 1920
VIEWPORT_HEIGHT = 1080

# UI and display settings
UI_SETTINGS = {
    "show_tool_reports": True      # Whether to show tool reports after responses
}

# LLM Provider configurations
LOCAL_PROVIDER = {
    "api_url": "http://localhost:1234/v1",  # Update with your LLM API URL
    "api_key": "your-api-key-here",         # Update with your API key
    "model": "model-name-here",             # Update with your model name
    "temperature": 0.6,
    "timeout": 1500,
    "context_size": 128000,
    "tool_choice": "auto",
    "parallel_tool_calls": True
}

OPENROUTER_PROVIDER = {
    "api_url": "https://openrouter.ai/api/v1",
    "api_key": "your-openrouter-api-key-here",  # Update with your OpenRouter API key
    "model": "your-model-here",                 # Update with your preferred model
    "temperature": 0.7,
    "timeout": 600,
    "context_size": 131072,
    "tool_choice": "auto",
    "parallel_tool_calls": True
}

# System settings
CHAT_PROVIDER = LOCAL_PROVIDER  # Set this to your desired provider

# Tool settings
TOOL_SETTINGS = {
    "web_search": {
        "max_results": SEARCH_RESULTS_COUNT,
        "search_depth": 1
    },
    "webpage_reader": {
        "timeout": BROWSER_TIMEOUT // 1000,
        "max_length": 8000
    }
}