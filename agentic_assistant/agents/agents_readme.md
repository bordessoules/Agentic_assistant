# Creating Custom Agents

This guide explains how to create and integrate specialized agents into the Agentic Assistant framework.

## Agent System Overview

Agents in Agentic Assistant:
- Are specialized modules that handle complex tasks
- Have their own conversation context and system prompt
- Can use tools via a dedicated tool manager
- Are registered using a decorator pattern
- Are invoked through the delegate_agent tool

## Creating a New Agent

### Step 1: Create an Agent File

Create a new Python file in the `agents` directory. For example, `my_custom_agent.py`:

```python
# agents/my_custom_agent.py
"""Description of what your agent does."""

from agentic_assistant.chat_controller import ChatController
from .registry import agent

@agent(
    name="my_custom_agent",
    description="A clear description of what this agent does and when to use it",
    system_prompt="""You are a specialized agent that [describe specific purpose].

Your task is to:
1. First step
2. Second step 
3. Third step

Focus on [primary goal/objective].
"""
)
class MyCustomAgent:
    def __init__(self, system_prompt):
        """Initialize with a dedicated chat controller"""
        self.controller = ChatController()
        self.controller.add_system_prompt(system_prompt)
    
    def process(self, input_text, parent_call_id=None, depth=0, **kwargs):
        """Process the input with tracking"""
        try:
            print(f"\n[MyCustomAgent processing: \"{input_text}\"]")
            
            # Your agent's processing logic here
            # For example, you might need to:
            # 1. Break down the task
            # 2. Use tools via self.controller.tool_manager
            # 3. Analyze results
            # 4. Generate a response
            
            # Example of calling the LLM
            response = self.controller.process_message(
                f"Process this input and generate a response: {input_text}"
            )
            
            # Example of using a tool
            # search_result = self.controller.tool_manager.execute_tool(
            #     "search_web", 
            #     {"query": input_text, "_parent_call_id": parent_call_id, "_depth": depth + 1}
            # )
            
            # Construct the result
            result = {
                "input": input_text,
                "output": response.content if hasattr(response, 'content') else "No response",
                "_tool_status": f"✓ Agent 'my_custom_agent' completed the task"
            }
            
            print(f"\n[MyCustomAgent completed task]")
            return result
            
        except Exception as e:
            print(f"MyCustomAgent error: {e}")
            return {
                "error": f"Error in my_custom_agent: {str(e)}",
                "input": input_text,
                "_tool_status": f"❌ MyCustomAgent failed: {str(e)}"
            }
```

### Step 2: Agent Registration

The `@agent` decorator automatically registers your agent with the system. The decorator takes these arguments:

- `name`: A unique name for your agent (used for delegation)
- `description`: A detailed description explaining what the agent does
- `system_prompt`: The specialized system prompt used for this agent's LLM interactions

### Step 3: Return Format

Agents should return a dictionary with:

- `input`: The original input received
- Any output fields relevant to your agent
- Error information if an error occurred
- A `_tool_status` key with a status message

## Best Practices

### 1. System Prompt Design

The system prompt is crucial for agent specialization. It should:
- Clearly define the agent's role and purpose
- Provide specific instructions for handling tasks
- Include any constraints or considerations
- Define the expected output format

### 2. Task Decomposition

For complex tasks, break them down into subtasks:

```python
def process(self, input_text, parent_call_id=None, depth=0, **kwargs):
    # 1. Analyze and plan
    planning_prompt = f"Analyze this task and create a plan: {input_text}"
    plan_response = self.controller.process_message(planning_prompt)
    
    # 2. Execute subtasks
    # ...
    
    # 3. Synthesize results
    synthesis_prompt = "Based on the gathered information, provide a comprehensive response..."
    final_response = self.controller.process_message(synthesis_prompt)
    
    return {
        "input": input_text,
        "output": final_response.content,
        "_tool_status": f"✓ Agent task completed"
    }
```

### 3. Verbose Logging

Add detailed logging to help with debugging:

```python
print(f"\n[Step 1: Planning for input: \"{input_text}\"]")
# Planning code
print(f"\n[Step 2: Executing subtasks ({len(subtasks)} identified)]")
# Execution code
print(f"\n[Step 3: Synthesizing final response]")
# Synthesis code
```

### 4. Tracking Parent Calls

When using tools, propagate tracking information:

```python
tool_args = {
    "param1": "value1",
    "_parent_call_id": parent_call_id,
    "_depth": depth + 1
}
result = self.controller.tool_manager.execute_tool("tool_name", tool_args)
```

### 5. Error Handling

Implement robust error handling at each step:

```python
try:
    # Agent step
except Exception as e:
    print(f"Error in step: {str(e)}")
    # Fallback behavior or return error
```

## Example: Content Summarizer Agent

```python
# agents/content_summarizer.py
"""Agent for summarizing content with customizable options."""

from agentic_assistant.chat_controller import ChatController
from .registry import agent

@agent(
    name="content_summarizer",
    description="Summarizes content with customizable length and focus",
    system_prompt="""You are a specialized content summarization agent. Your task is to create concise, informative summaries of content.

For each summarization task:
1. Identify the key points and main ideas
2. Create a structured summary that captures the essence of the content
3. Adjust the length and detail level based on the specified parameters
4. Maintain the original meaning and important nuances

Focus on clarity, accuracy, and preserving the most important information."""
)
class ContentSummarizerAgent:
    def __init__(self, system_prompt):
        """Initialize with a dedicated chat controller"""
        self.controller = ChatController()
        self.controller.add_system_prompt(system_prompt)
    
    def process(self, input_text, parent_call_id=None, depth=0, **kwargs):
        """Process a summarization task"""
        try:
            print(f"\n[ContentSummarizer processing content: {len(input_text)} characters]")
            
            # Extract parameters if provided
            parameters = {}
            if ":" in input_text:
                command_parts = input_text.split(":", 1)
                if len(command_parts) == 2:
                    param_text, content = command_parts
                    
                    # Parse parameters
                    param_pairs = [p.strip() for p in param_text.split(",")]
                    for pair in param_pairs:
                        if "=" in pair:
                            key, value = pair.split("=", 1)
                            parameters[key.strip()] = value.strip()
                    
                    # Use the rest as content
                    content = content.strip()
                else:
                    content = input_text
            else:
                content = input_text
            
            # Set default parameters
            length = parameters.get("length", "medium")
            focus = parameters.get("focus", "general")
            
            # Create the summary prompt
            summary_prompt = f"""Summarize the following content:

Content:
{content}

Parameters:
- Length: {length} (short/medium/long)
- Focus: {focus} (general/technical/business/etc.)

Provide a structured, clear summary that captures the key points.
"""
            
            # Get the summary
            response = self.controller.process_message(summary_prompt)
            
            # Check if we got a valid response
            if not response or not hasattr(response, 'content'):
                raise Exception("Failed to generate summary")
            
            # Return the result
            return {
                "original_length": len(content),
                "summary": response.content,
                "parameters": parameters,
                "_tool_status": f"✓ Content summarized ({len(content)} chars to {len(response.content)} chars)"
            }
            
        except Exception as e:
            print(f"ContentSummarizer error: {e}")
            return {
                "error": f"Error in summarization: {str(e)}",
                "input": input_text[:100] + "..." if len(input_text) > 100 else input_text,
                "_tool_status": f"❌ Summarization failed: {str(e)}"
            }
```

## Usage Example

Once registered, your agent can be called using the `delegate_agent` tool:

```python
from agentic_assistant.tool_manager import ToolManager

# Create a tool manager
tool_manager = ToolManager()

# Delegate to your custom agent
result = tool_manager.execute_tool(
    "delegate_agent", 
    {
        "agent_name": "my_custom_agent",
        "task": "The task or query to process"
    }
)

# Access the result
print(result["result"]["output"])
```
