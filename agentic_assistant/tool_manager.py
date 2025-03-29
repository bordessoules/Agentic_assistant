# tool_manager.py
"""Improved tool manager that uses atomic ID tracking with better error handling."""

import json
import time
from typing import Dict, List, Any, Optional, Set
from colorama import Fore, Style

from agentic_assistant.id_service import id_service


class ToolManager:
    """Manager for tool execution with atomic ID tracking."""
    
    def __init__(self):
        """Initialize the tool manager."""
        # Import here to avoid circular imports
        from agentic_assistant.tools.registry import get_tool_function, get_all_schemas
        
        # Tool registry access
        self.get_tool = get_tool_function
        self.get_schemas = get_all_schemas
    
    def execute_tool(self, tool_name: str, tool_args: Dict[str, Any]) -> Any:
        """Execute a tool by name with arguments and track using atomic IDs."""
        # Extract tracking information
        parent_id = None
        current_depth = 0
        
        if isinstance(tool_args, dict):
            # Extract and remove tracking information from arguments
            parent_id = tool_args.pop('_parent_call_id', None) if '_parent_call_id' in tool_args else None
            current_depth = tool_args.pop('_depth', 0) if '_depth' in tool_args else 0
        
        # Generate unique ID for this call
        call_id = id_service.generate_id(prefix=tool_name)
        
        # Record the start of the call
        id_service.record_call_start(
            call_id=call_id,
            tool_name=tool_name,
            args=tool_args,
            parent_id=parent_id,
            depth=current_depth
        )
        
        start_time = time.time()
        
        try:
            # Get and execute the tool
            tool_func = self.get_tool(tool_name)
            
            if not tool_func:
                error_msg = f"Unknown tool: {tool_name}"
                id_service.record_call_error(call_id=call_id, error=error_msg)
                return self._format_error(tool_name, error_msg)
            
            # Special handling for agent delegation - standardized to only use delegate_agent name
            is_delegation = tool_name == "delegate_agent"
            if is_delegation and isinstance(tool_args, dict):
                agent_name = tool_args.get('agent_name', 'unknown')
                task = tool_args.get('task', 'unspecified task')
                task_preview = task[:50] + "..." if len(task) > 50 else task
                print(f"\n[Delegating to {agent_name} agent: \"{task_preview}\"]")
                
                # Pass the call_id as parent_id to the agent
                tool_args['_parent_call_id'] = call_id
                tool_args['_depth'] = current_depth + 1
            
            # Execute the tool
            result = tool_func(**tool_args)
            
            # Calculate duration
            duration = time.time() - start_time
            
            # Extract status message if provided
            status = f"✓ {tool_name}: Completed successfully"
            if isinstance(result, dict) and "_tool_status" in result:
                status = result.pop("_tool_status")
            
            # Record the successful completion
            id_service.record_call_end(
                call_id=call_id,
                result=result,
                status="success",
                summary=status
            )
            
            # Trigger tool end event for tracking
            from agentic_assistant.callbacks import callbacks, Events
            callbacks.trigger(
                Events.TOOL_END,
                tool_name=tool_name,
                call_id=call_id,
                result=result
            )
            
            return result
            
        except Exception as e:
            # Calculate duration
            duration = time.time() - start_time
            
            # Record the error
            id_service.record_call_error(
                call_id=call_id,
                error=str(e)
            )
            
            # Trigger tool end event even for errors
            from agentic_assistant.callbacks import callbacks, Events
            callbacks.trigger(
                Events.TOOL_END,
                tool_name=tool_name,
                call_id=call_id,
                error=str(e)
            )
            
            return self._format_error(tool_name, str(e))
    
    def _format_error(self, tool_name: str, error_msg: str) -> Dict[str, str]:
        """Format error responses consistently."""
        return {
            "error": f"{tool_name} error: {error_msg}",
            "_tool_status": f"❌ Error: {error_msg}"
        }
    
    def handle_tool_calls(self, tool_calls: List) -> List[Dict[str, str]]:
        """Process multiple tool calls from the LLM."""
        results = []
        
        # Convert tool calls to a standardized format
        standardized_tool_calls = self._standardize_tool_calls(tool_calls)
        
        # Process each tool call
        for tool_call in standardized_tool_calls:
            try:
                # Extract function details
                call_id = tool_call.get("id", f"call_{len(results)}")
                func_name = tool_call.get("function", {}).get("name", "unknown_function")
                
                try:
                    arguments = tool_call.get("function", {}).get("arguments", "{}")
                    func_args = json.loads(arguments)
                except json.JSONDecodeError:
                    print(f"\n[Warning: Invalid JSON in arguments for {func_name}]")
                    func_args = {}
                
                # Add tracking information
                func_args['_parent_call_id'] = call_id
                func_args['_depth'] = 0  # Top level
                
                # Special handling for delegate_agent tool to improve tracking
                is_agent_delegation = func_name == "delegate_agent"
                agent_name = None
                if is_agent_delegation and isinstance(func_args, dict):
                    agent_name = func_args.get('agent_name', None)
                    task = func_args.get('task', 'unspecified task')
                    # Do NOT log delegation here - it will be logged in execute_tool
                    # This prevents duplicate logging
                
                # Execute the tool
                result = self.execute_tool(func_name, func_args)
                
                # Format the result for the response
                result_str = json.dumps(result) if isinstance(result, (dict, list)) else str(result)
                
                # Add to results
                results.append({
                    "tool_call_id": call_id,
                    "content": result_str
                })
                
            except Exception as e:
                # Add error response
                call_id = tool_call.get("id", "unknown")
                error_response = self._format_error("tool_calls", str(e))
                results.append({
                    "tool_call_id": call_id,
                    "content": json.dumps(error_response)
                })
        
        return results
    
    def _standardize_tool_calls(self, tool_calls):
        """Convert tool calls to a standard format regardless of input format."""
        standardized = []
        
        for call in tool_calls:
            if hasattr(call, 'function'):
                # OpenAI format
                standardized.append({
                    "id": call.id,
                    "type": "function",
                    "function": {
                        "name": call.function.name,
                        "arguments": call.function.arguments
                    }
                })
            elif isinstance(call, dict):
                # Dictionary format
                if "function" in call:
                    standardized.append(call)
                elif "function" in call.get("function", {}):
                    # Handle nested function format
                    standardized.append({
                        "id": call.get("id", f"call_{len(standardized)}"),
                        "type": "function",
                        "function": call["function"]
                    })
        
        return standardized
    
    def get_report(self, colored: bool = True) -> str:
        """Generate a formatted report of tool usage."""
        # Get data from the central ID service
        records = id_service.get_all_records()
        parent_child_map = id_service.get_parent_child_map()
        
        if not records:
            return "No tools used in this conversation."
        
        lines = ["🔧 Tools used in this conversation:"]
        
        # Find top-level calls (no parent)
        top_level_calls = [call for call in records if call.get("parent_id") is None]
        
        # Process each top-level call
        for call in top_level_calls:
            self._format_call(call, lines, parent_child_map, records, indent=1, colored=colored)
        
        return "\n".join(lines)
    
    def _format_call(self, call, lines, parent_child_map, all_records, indent=0, colored=False, visited=None):
        """Format a single tool call for the report with cycle detection."""
        # Initialize visited set to prevent circular references
        if visited is None:
            visited = set()
            
        # Get call_id safely
        call_id = call.get("id", "unknown")
        
        # Check for circular references
        if call_id in visited:
            indent_str = "  " * indent
            lines.append(f"{indent_str}⚠️ Circular reference detected for ID: {call_id}")
            return
            
        # Add to visited set
        visited.add(call_id)
        
        indent_str = "  " * indent
        
        # Determine status formatting - safely access with .get()
        status = call.get("status", "unknown")
        if status == "success":
            status_emoji = "✅"
            color = Fore.GREEN if colored else ""
        elif status == "error":
            status_emoji = "❌"
            color = Fore.RED if colored else ""
        else:
            status_emoji = "⚠️"
            color = Fore.YELLOW if colored else ""
        
        # Format duration safely
        duration = call.get("duration", 0)
        
        # Build the line with safe attribute access
        tool_name = call.get("tool_name", "unknown")
        result_summary = call.get("result_summary", "No status available")
        depth = call.get("depth", 0)
        depth_indicator = f"[D{depth}]" if depth > 0 else ""
        
        # Special formatting for agent delegation
        is_delegation = tool_name == "delegate_agent"
        if is_delegation:
            args = call.get("args", {})
            agent_name = args.get("agent_name", "unknown")
            task = args.get("task", "")
            
            # Format as agent call rather than tool call
            lines.append(f"{indent_str}{status_emoji} {color}Agent: {agent_name}{Style.RESET_ALL if colored else ''} {depth_indicator} ({duration:.2f}s): {result_summary}")
            if task:
                lines.append(f"{indent_str}   Task: \"{task}\"")
        else:
            # Normal tool call formatting with standardized format
            lines.append(f"{indent_str}{status_emoji} {color}{tool_name}{Style.RESET_ALL if colored else''} {depth_indicator} ({duration:.2f}s): {result_summary}")
            
            # Add tool-specific details
            args = call.get("args", {})
            if tool_name == "search_web" and "query" in args:
                lines.append(f"{indent_str}   Query: \"{args['query']}\"")
            elif tool_name == "webpage_reader" and "url" in args:
                lines.append(f"{indent_str}   URL: {args['url']}")
        
        # Add child calls
        if call_id in parent_child_map:
            child_ids = parent_child_map[call_id]
            for child_id in child_ids:
                # Find the child call in all records
                for child_call in all_records:
                    if child_call.get("id") == child_id:
                        self._format_call(child_call, lines, parent_child_map, all_records, indent + 1, colored, visited)
                        break
    
    def reset(self) -> None:
        """Reset the tool manager state for a new conversation turn."""
        # No local state to reset, but may need to clean up resources
        pass

    def clear_history(self) -> None:
        """Clear tool history."""
        id_service.clear_history()

    @property
    def tools(self) -> List[Dict[str, Any]]:
        """Get all available tool schemas."""
        return self.get_schemas()
