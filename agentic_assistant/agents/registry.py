# agents/registry.py
"""Registry for agent discovery and management with atomic ID tracking."""

import os
import importlib

# Storage for registered agents
AGENTS = {}
_agents_discovered = False

def agent(name, description, system_prompt):
    """
    Decorator to register an agent class.
    
    Args:
        name: Unique name for the agent
        description: Description of the agent's capabilities
        system_prompt: System prompt for the agent
        
    Returns:
        Decorator function
    """
    def decorator(agent_class):
        AGENTS[name] = {
            "class": agent_class,
            "description": description,
            "system_prompt": system_prompt,
            "instance": None
        }
        return agent_class
    return decorator

def get_agent(name):
    """
    Get an agent instance by name.
    
    Args:
        name: Name of the agent to retrieve
        
    Returns:
        Agent instance or None if not found
    """
    if name not in AGENTS:
        return None
    
    # Create instance if needed
    if AGENTS[name]["instance"] is None:
        AGENTS[name]["instance"] = AGENTS[name]["class"](AGENTS[name]["system_prompt"])
    
    return AGENTS[name]["instance"]

def get_agents_description():
    """
    Get formatted descriptions of all agents.
    
    Returns:
        String with all agent descriptions
    """
    return "\n".join([f"- {name}: {info['description']}" 
                     for name, info in AGENTS.items()])

def discover_agents():
    """Automatically discover agent implementations."""
    global _agents_discovered
    if _agents_discovered:
        return
    
    # Get the agent directory
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Import all Python files in the directory
    for filename in os.listdir(current_dir):
        if filename.endswith('.py') and filename != '__init__.py' and filename != 'registry.py' and filename != 'base_agent.py':
            # Import the module
            module_name = filename[:-3]
            try:
                importlib.import_module(f".{module_name}", package="agentic_assistant.agents")
                print(f"✓ Registered agent module: {module_name}")
            except Exception as e:
                print(f"❌ Error importing agent module {module_name}: {str(e)}")
    
    _agents_discovered = True

# Auto-discover agents on import
discover_agents()
