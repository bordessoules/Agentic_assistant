# chat_controller.py
"""Simplified chat controller for agent interactions with cleaner tool support."""

import datetime
import json
from agentic_assistant.llm_client import LLMClient
from agentic_assistant.tool_manager import ToolManager
from agentic_assistant.callbacks import callbacks, Events


class ChatController:
    """Controller for managing chat interactions with LLM providers"""
    
    def __init__(self):
        """Initialize the chat controller"""
        self.llm = LLMClient()
        self.tool_manager = ToolManager()
    
    def add_system_prompt(self, prompt):
        """
        Add or update the system prompt
        
        Args:
            prompt: The system prompt text to set
        """
        # Format and add system prompt
        current_date = datetime.datetime.now().strftime('%A, %B %d, %Y')
        formatted_prompt = prompt.format(current_date=current_date)
        self.llm.add_message("system", formatted_prompt)
    
    def process_message(self, user_message):
        """
        Process a user message and generate a response with support for function calls
        
        Args:
            user_message: Text message from the user
                
        Returns:
            Response object containing the assistant's message
        """
        # Add user message to conversation
        self.llm.add_message("user", user_message)
        
        # Use non-streaming approach with tool calling
        return self._process_message_with_tools(user_message)
    
    def _process_message_with_tools(self, user_message):
        """Process a user message using a simple, reliable tool calling approach."""
        # Loop for tool calling (with reasonable limit to prevent infinite loops)
        max_tool_rounds = 5
        
        for round_num in range(max_tool_rounds):
            # Get LLM response
            response = self.llm.get_completion(tools=self.tool_manager.tools)
            
            # Handle any tool calls
            if not hasattr(response, 'tool_calls') or not response.tool_calls:
                # No tool calls, add response and return
                self.llm.add_message("assistant", response.content)
                
                # Trigger response complete callback
                callbacks.trigger(
                    Events.RESPONSE_COMPLETE,
                    content=response.content
                )
                
                return response
                
            # Process tool calls
            tool_calls_data = [{
                "id": tc.id,
                "type": "function",
                "function": {
                    "name": tc.function.name,
                    "arguments": tc.function.arguments
                }
            } for tc in response.tool_calls]
            
            # Add assistant message with tool calls
            self.llm.add_message("assistant", response.content, tool_calls=tool_calls_data)
            
            # Execute tools and add responses
            tool_messages = self.tool_manager.handle_tool_calls(response.tool_calls)
            
            # Add tool messages to conversation
            for msg in tool_messages:
                self.llm.add_message("tool", msg["content"], tool_call_id=msg["tool_call_id"])
        
        # Final response after tool calls
        final_response = self.llm.get_completion()
        self.llm.add_message("assistant", final_response.content)
        
        # Trigger response complete callback
        callbacks.trigger(
            Events.RESPONSE_COMPLETE,
            content=final_response.content
        )
        
        return final_response
    
    @property
    def total_tokens_used(self):
        """Get the total tokens used in this conversation."""
        return self.llm.total_tokens
        
    @property
    def context_size(self):
        """Get the context size from the LLM client."""
        return self.llm.context_size
        
    def clear_conversation(self):
        """Clear the conversation history but keep the system prompt."""
        system_message = None
        if self.llm.messages and self.llm.messages[0]["role"] == "system":
            system_message = self.llm.messages[0]
        
        # Reset messages and add back system message if it existed
        self.llm.messages = []
        if system_message:
            self.llm.messages.append(system_message)
            
        # Reset token tracking
        self.llm.total_tokens = 0
