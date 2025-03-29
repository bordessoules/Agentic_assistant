# agents/deep_search.py
"""Deep search agent with atomic ID tracking."""

from agentic_assistant.chat_controller import ChatController
from .registry import agent

@agent(
    name="deep_search",
    description="Performs comprehensive web research on specific topics",
    system_prompt="""You are a specialized deep search agent. Your task is to gather comprehensive information from the web on specific topics.

For each research task:
1. Break down the topic into 2-3 key aspects to investigate
2. Formulate precise search queries for each aspect
3. Analyze search results to extract relevant information
4. Synthesize findings into a coherent summary
5. Include all relevant sources

Focus on being thorough and objective in your research."""
)
class DeepSearchAgent:
    def __init__(self, system_prompt):
        """Initialize with a dedicated chat controller"""
        self.controller = ChatController()
        self.controller.add_system_prompt(system_prompt)
    
    def process(self, topic, parent_call_id=None, depth=0, **kwargs):
        """Process a deep search task with atomic ID tracking"""
        try:
            print(f"\n[Deep search agent processing: \"{topic}\"]")
            
            # Planning phase
            planning_prompt = f"Break down this research topic into 2-3 key aspects to investigate: '{topic}'"
            planning_response = self.controller.process_message(planning_prompt)
            
            # Verify planning response exists
            if not planning_response or not hasattr(planning_response, 'content'):
                return {
                    "error": "Failed to plan research aspects",
                    "topic": topic
                }
            
            # Extract search aspects
            aspects_text = planning_response.content
            aspects = [line.strip().replace('- ', '') for line in aspects_text.split('\n') if line.strip()]
            aspects = aspects[:3]  # Limit to 3 aspects
            
            if not aspects:
                aspects = [topic]  # Use the original topic if no aspects were identified
            
            # Log the aspects that will be researched
            print(f"\n[Deep search identified {len(aspects)} aspects to research:]")
            for i, aspect in enumerate(aspects):
                print(f"  {i+1}. {aspect}")
            
            # Research each aspect
            results = []
            
            for i, aspect in enumerate(aspects):
                print(f"\n[Researching aspect {i+1}/{len(aspects)}: \"{aspect}\"]")
                
                # Pass tracking information
                search_args = {"query": aspect, "count": 3}
                if parent_call_id:
                    search_args['_parent_call_id'] = parent_call_id
                    search_args['_depth'] = depth
                
                # Execute search
                search_result = self.controller.tool_manager.execute_tool(
                    "search_web", 
                    search_args
                )
                
                if "error" not in search_result and "results" in search_result:
                    # Process the top 2 results
                    for j, result in enumerate(search_result.get("results", [])[:2]):
                        try:
                            # Pass tracking information
                            url_args = {"url": result["url"]}
                            if parent_call_id:
                                url_args['_parent_call_id'] = parent_call_id
                                url_args['_depth'] = depth
                            
                            # Extract content
                            content_result = self.controller.tool_manager.execute_tool(
                                "webpage_reader", 
                                url_args
                            )
                            
                            if "error" not in content_result:
                                results.append({
                                    "aspect": aspect,
                                    "title": result.get("title", "Unknown title"),
                                    "url": result.get("url", "Unknown URL"),
                                    "content": content_result.get("content", "")[:1500]  # Limit content size
                                })
                        except Exception as e:
                            print(f"Error extracting content: {str(e)}")
            
            # Create a synthesis prompt with the gathered information
            synthesis_prompt = f"""Based on the following research, provide a comprehensive summary about: {topic}

Research findings:
"""
            
            for i, result in enumerate(results):
                synthesis_prompt += f"\n\nSOURCE {i+1}: {result['title']} ({result['url']})\nAspect: {result['aspect']}\n{result['content'][:500]}...\n"
            
            print(f"\n[Synthesizing findings from {len(results)} sources]")
                
            # Generate the summary
            synthesis_response = self.controller.process_message(synthesis_prompt)
            
            # Get summary content safely
            summary = "No summary could be generated."
            if synthesis_response and hasattr(synthesis_response, 'content'):
                summary = synthesis_response.content
            
            # Calculate tokens used
            tokens_used = 0
            if hasattr(self.controller, 'total_tokens_used'):
                tokens_used = self.controller.total_tokens_used
            
            print(f"\n[Deep search completed on: \"{topic}\"]")
            
            return {
                "topic": topic,
                "summary": summary,
                "sources": [{"title": r.get("title", "Unknown"), "url": r.get("url", "Unknown")} for r in results],
                "aspects_researched": aspects,
                "tokens_used": tokens_used,
                "_tool_status": f"✓ Completed deep search on '{topic}' with {len(results)} sources"
            }
        except Exception as e:
            print(f"Deep search error: {e}")
            return {
                "error": f"Error in deep_search: {str(e)}",
                "topic": topic,
                "_tool_status": f"❌ Deep search failed: {str(e)}"
            }
