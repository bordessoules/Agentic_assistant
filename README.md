# Agentic Assistant

A powerful assistant framework with tool integration and specialized agent capabilities.

## Features

- 🔍 **Web Search**: Search the web for current information using SearxNG
- 📄 **Webpage Reading**: Extract clean, readable content from webpages
- 🤖 **Specialized Agents**: Delegate tasks to purpose-built agents
- 🔧 **Extensible Tool System**: Easily add new tools via decorators
- 🖥️ **Interactive Console**: Simple interface for testing and usage

## Installation

### Prerequisites

- Python 3.8 or higher
- SearxNG instance (local or remote)

### Install from Source

```bash
# Clone the repository
git clone https://github.com/yourusername/agentic_assistant.git
cd agentic_assistant

# Install the package
pip install -e .

# Install Playwright dependencies
playwright install firefox
```

## Configuration

Edit `agentic_assistant/config.py` to configure:

- SearxNG URL
- LLM provider settings
- HTTP request settings
- UI preferences

## Usage

### Basic Usage

```python
from agentic_assistant.assistant import Assistant

# Create an assistant instance
assistant = Assistant()

# Ask a question
response = assistant.ask("What's the latest on renewable energy?")
print(response)

# Get tool usage report
print(assistant.get_tool_report())
```

### Interactive Mode

```bash
# Run the interactive console
python run.py
```

### Using Specific Tools

```python
from agentic_assistant.tool_manager import ToolManager

# Create a tool manager
tool_manager = ToolManager()

# Use the webpage reader
result = tool_manager.execute_tool(
    "webpage_reader", 
    {"url": "https://example.com"}
)

# Use the web search
search_results = tool_manager.execute_tool(
    "search_web", 
    {"query": "renewable energy advances site:.gov"}
)
```

## System Architecture

### Core Components

- **Assistant**: Main interface for interactions
- **ChatController**: Manages conversation with LLM providers
- **LLMClient**: Handles direct interaction with language model APIs
- **ToolManager**: Manages tool execution and reporting

### Tool System

- **Registry**: Decorator-based system for registering tools
- **Web Search**: Implements SearxNG-based web searching
- **Webpage Reader**: Extracts content from webpages
- **Agent Delegation**: Allows delegating tasks to specialized agents

### Agent System

- **Registry**: Similar decorator-based system for registering agents
- **Deep Search**: Specialized agent for comprehensive web research
- **Query Improver**: Agent for improving search queries

## Extending

- [Creating New Tools](tools/README.md)
- [Creating New Agents](agents/README.md)

## License

[MIT License](LICENSE)
