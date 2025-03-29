# llm_client.py
"""Client for interacting with language model providers."""

from agentic_assistant.config import CHAT_PROVIDER
from agentic_assistant.callbacks import callbacks, Events

class LLMClient:
    """Client for language model interactions."""

    def __init__(self):
        """Initialize the LLM client."""
        self.messages = []
        self.total_tokens = 0
        self.context_size = CHAT_PROVIDER.get("context_size", 16384)
    
    def add_message(self, role, content, **kwargs):
        """
        Add a message to the conversation history.
        
        Args:
            role: The role of the message sender (system, user, assistant, tool)
            content: The message content
            **kwargs: Additional message attributes
            
        Returns:
            The added message
        """
        message = {"role": role, "content": content}
        message.update(kwargs)
        self.messages.append(message)
        return message
    
    def get_completion(self, tools=None):
        """
        Get a completion from the language model.
        
        Args:
            tools: Optional list of tool schemas
            
        Returns:
            The LLM's response message
        """
        try:
            from openai import OpenAI
            
            # Create client with provider-specific parameters
            client = OpenAI(
                base_url=CHAT_PROVIDER.get("api_url"),
                api_key=CHAT_PROVIDER.get("api_key")
            )
            
            # Make API call
            response = client.chat.completions.create(
                model=CHAT_PROVIDER.get("model"),
                messages=self.messages,
                tools=tools,
                tool_choice=CHAT_PROVIDER.get("tool_choice", "auto"),
                temperature=CHAT_PROVIDER.get("temperature"),
                timeout=CHAT_PROVIDER.get("timeout", 120)
            )
            
            # Track tokens and return the message
            if hasattr(response, 'usage'):
                self.total_tokens += response.usage.total_tokens
                
                # Trigger callback with token usage
                callbacks.trigger(
                    Events.TOKEN_USAGE,
                    total_tokens=self.total_tokens,
                    prompt_tokens=response.usage.prompt_tokens,
                    completion_tokens=response.usage.completion_tokens
                )
            
            return response.choices[0].message
            
        except Exception as e:
            print(f"Error calling LLM: {str(e)}")
            
            # Simple error response
            class ErrorResponse:
                def __init__(self, error):
                    self.content = f"Error: {error}"
                    self.tool_calls = []
            
            return ErrorResponse(str(e))
