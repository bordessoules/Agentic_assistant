# assistant.py
"""Core assistant with tool integration and agent capabilities."""

import datetime
import sys
from typing import Dict, List, Any, Optional, Tuple

from agentic_assistant.chat_controller import ChatController
from agentic_assistant.tool_manager import ToolManager
from agentic_assistant.prompt import SYSTEM_PROMPT
from agentic_assistant.config import CHAT_PROVIDER, UI_SETTINGS
from agentic_assistant.callbacks import callbacks, Events


class Assistant:
    """Assistant with tool and agent capabilities."""
    
    def __init__(self):
        """Initialize the assistant."""
        # Create chat controller and tool manager
        self.controller = ChatController()
        self.tool_manager = ToolManager()
        self.controller.tool_manager = self.tool_manager
        
        # Initialize system prompt
        self._setup_system_prompt()
        
        # Response state
        self.current_response = None
        
        # System stats
        self.total_questions = 0
        self.total_tools_used = 0
        
        # Register callbacks
        callbacks.register(Events.RESPONSE_COMPLETE, self._on_response_complete)
        callbacks.register(Events.TOOL_END, self._on_tool_end)
        callbacks.register(Events.TOKEN_USAGE, self._on_token_usage)
    
    def _setup_system_prompt(self):
        """Set up the system prompt with agent capabilities."""
        try:
            from agentic_assistant.agents.registry import discover_agents, get_agents_description
            discover_agents()
            agent_descriptions = get_agents_description()
        except ImportError:
            agent_descriptions = "No specialized agents available."
            
        # Format and add system prompt
        formatted_prompt = SYSTEM_PROMPT.format(
            current_date=datetime.datetime.now().strftime('%A, %B %d, %Y'),
            agent_descriptions=agent_descriptions
        )
        self.controller.add_system_prompt(formatted_prompt)
    
    def _on_response_complete(self, content, **kwargs):
        """Callback when a response is complete."""
        self.current_response = content
        self.total_questions += 1
    
    def _on_tool_end(self, **kwargs):
        """Callback when a tool completes execution."""
        self.total_tools_used += 1
        
    def _on_token_usage(self, total_tokens, prompt_tokens, completion_tokens, **kwargs):
        """Callback when token usage is reported."""
        # This callback provides a hook for future token usage tracking
        # We don't need to do anything here as the controller tracks tokens directly
    
    def ask(self, question: str) -> str:
        """Process a question and return the assistant's response."""
        # Reset tool manager for new conversation turn
        self.tool_manager.reset()
        
        # Reset current response
        self.current_response = None
        
        # Process the message through the controller
        response = self.controller.process_message(question)
        
        # Update current response
        self.current_response = response.content
        
        return response.content
    
    def print_response(self, text: str):
        """Print the response."""
        print(text)
    
    def get_tool_report(self, colored: bool = True) -> str:
        """Get the current tool usage report."""
        return self.tool_manager.get_report(colored=colored)
    
    def display_tool_report(self):
        """Display the current tool usage report."""
        if UI_SETTINGS.get("show_tool_reports", True):
            report = self.get_tool_report()
            print(f"\n{report}")
    
    def get_context_usage_info(self) -> str:
        """Get formatted context usage information."""
        tokens_used = self.controller.total_tokens_used
        context_size = self.controller.context_size
        percentage = (tokens_used / context_size) * 100 if context_size > 0 else 0
        
        # Create visual bar
        bar_length = 20
        filled_length = int(bar_length * percentage / 100)
        bar = '█' * filled_length + '░' * (bar_length - filled_length)
        
        return f"Context: {bar} {tokens_used}/{context_size} tokens ({percentage:.1f}%)"
    
    def get_system_report(self) -> str:
        """Generate a system usage report."""
        model_name = CHAT_PROVIDER.get("model", "unknown")
        context_size = CHAT_PROVIDER.get("context_size", 4096)
        
        report = [
            "📊 System Report",
            "=" * 40,
            f"Model: {model_name}",
            f"Context size: {context_size} tokens",
            f"Current context usage: {self.controller.total_tokens_used} tokens",
            f"Questions processed: {self.total_questions}",
            f"Tools executed: {self.total_tools_used}",
            "🔧 Tool Usage Details:",
            self.get_tool_report(colored=False),
            "=" * 40
        ]
        return "\n".join(report)
    
    def clear_conversation(self):
        """Clear the conversation history but keep the system prompt."""
        self.controller.clear_conversation()
        self.tool_manager.clear_history()
    
    def start_interactive(self):
        """Start an interactive chat session in the console."""
        model_name = CHAT_PROVIDER.get("model", "unknown")
        context_size = CHAT_PROVIDER.get("context_size", 4096)
        
        print("\n📚 Agentic Assistant - with tools and agent capabilities")
        print("=" * 80)
        print(f"🤖 Model: {model_name} (Context window: {context_size} tokens)")
        print(f"🔧 Tool reports: {'ENABLED' if UI_SETTINGS.get('show_tool_reports') else 'DISABLED'}")
        print("📊 Context usage: 0/0 tokens (0.0%)")
        print("Type 'exit' to quit, 'clear' to reset, 'help' for more commands")
        print("=" * 80)
        
        while True:
            # Get user input
            user_input = input("\n🙋 You: ").strip()
            
            # Handle commands
            if user_input.lower() in ["exit", "quit"]:
                print("👋 Goodbye!")
                break
            elif user_input.lower() == "clear":
                self.clear_conversation()
                print("🧹 Conversation cleared.")
                continue
            elif user_input.lower() == "help":
                self._print_help()
                continue
            elif user_input.lower() == "toggle_reports":
                UI_SETTINGS["show_tool_reports"] = not UI_SETTINGS.get("show_tool_reports", True)
                print(f"🔧 Tool reports are now {'ENABLED' if UI_SETTINGS['show_tool_reports'] else 'DISABLED'}")
                continue
            elif user_input.lower() == "reports":
                print(self.get_system_report())
                continue
            elif not user_input:
                continue
            
            # Process message
            print("⏳ Thinking...")
            
            try:
                # Get response
                response = self.ask(user_input)
                
                # Print response
                print("\n🤖 Assistant:", end=" ")
                self.print_response(response)
                
                # Display tool report
                self.display_tool_report()
                
                # Display context usage
                print(f"\n{self.get_context_usage_info()}")
            except Exception as e:
                print(f"\n❌ Error: {str(e)}")
    
    def _print_help(self):
        """Print help information for interactive mode."""
        print("\n=== Available Commands ===")
        print("exit, quit - Exit the application")
        print("clear - Clear conversation history")
        print("toggle_reports - Toggle tool usage reports")
        print("reports - Show system usage statistics")
        print("help - Show this help message")


def main():
    """Entry point for the agentic assistant console application."""
    assistant = Assistant()
    assistant.start_interactive()
