# tools/delegate_agent.py
"""Tool for delegating tasks to specialized agents with atomic ID tracking."""

from agentic_assistant.tools.registry import tool

@tool(
    name="delegate_agent",
    description="Delegates a task to a specialized agent",
    parameters={
        "agent_name": {
            "type": "string",
            "description": "Name of the agent to delegate to (e.g., 'deep_search', 'query_improver')"
        },
        "task": {
            "type": "string",
            "description": "Task description or query to send to the agent"
        }
    }
)
def delegate_agent(agent_name, task, **kwargs):
    """
    Delegate a task to a specialized agent.
    
    Args:
        agent_name: Name of the agent to use
        task: Task description or query
        **kwargs: Additional arguments including tracking info
        
    Returns:
        Agent's response
    """
    try:
        # Import here to avoid circular imports
        from agentic_assistant.agents.registry import get_agent
        
        # Get the parent call ID for tracking
        parent_call_id = kwargs.get('_parent_call_id')
        current_depth = kwargs.get('_depth', 0)
        
        # Get the agent instance
        agent = get_agent(agent_name)
        
        if not agent:
            return {
                "error": f"Agent not found: {agent_name}",
                "_tool_status": f"❌ Error: Agent '{agent_name}' not found"
            }
        
        # REMOVED the duplicate print statement here
        # The tool_manager will handle logging this
        
        # Process the task using the agent, passing the tracking information
        result = agent.process(
            task,
            parent_call_id=parent_call_id,
            depth=current_depth + 1
        )
        
        # Return the result
        return {
            "agent": agent_name,
            "task": task,
            "result": result,
            "_tool_status": f"✓ Agent '{agent_name}' completed the task"
        }
    except Exception as e:
        print(f"\n[Error in agent delegation: {str(e)}]")
        return {
            "error": f"Error in agent execution: {str(e)}",
            "_tool_status": f"❌ Error: {str(e)}"
        }
