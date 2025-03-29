# agents/query_improver.py
"""Query improvement agent with atomic ID tracking."""

from agentic_assistant.chat_controller import ChatController
from .registry import agent

@agent(
    name="query_improver",
    description="Improves queries with better grammar, clarity, and precision",
    system_prompt="""You are a query improvement specialist. Enhance queries by:
1. Fixing grammar and spelling errors
2. Improving clarity and precision
3. Adjusting style as requested
4. Preserving the original intent

Return only the improved query without explanations or commentary."""
)
class QueryImproverAgent:
    def __init__(self, system_prompt):
        """Initialize with a dedicated chat controller"""
        self.controller = ChatController()
        self.controller.add_system_prompt(system_prompt)
    
    def process(self, query, parent_call_id=None, depth=0, **kwargs):
        """Process a query improvement task with atomic ID tracking"""
        # Extract style if specified
        style = "neutral"
        if "style:" in query.lower():
            parts = query.split("style:", 1)
            content = parts[0].strip()
            style_part = parts[1].strip().lower()
            
            if "formal" in style_part:
                style = "formal"
            elif "professional" in style_part:
                style = "professional"
            elif "casual" in style_part:
                style = "casual"
        else:
            content = query
        
        # Process the query
        prompt = f"""Please improve this query: "{content}"
Use a {style} style.
Return only the improved query."""
        
        response = self.controller.process_message(prompt)
        
        # Return formatted result
        return {
            "original_query": content,
            "improved_query": response.content.strip().strip('"').strip(),
            "style": style,
            "tokens_used": self.controller.total_tokens_used,
            "_tool_status": f"✓ Query improved using {style} style"
        }
