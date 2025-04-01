# tools/search_web.py
"""Web search implementation using SearXNG. """

import requests
from .registry import tool
from agentic_assistant.config import SEARXNG_URL, SEARCH_RESULTS_COUNT, HTTP_TIMEOUT

@tool(
    name="search_web",
    description="""Search the web using a customized SearXNG metasearch instance that aggregates results from over 40 specialized search engines.

The search supports these operator categories:

1. CONTENT REFINEMENT:
    "exact phrase" - Match an exact sequence of words
    term1 AND term2 - Require both terms (AND is uppercase)
    term1 OR term2 - Either term can appear (OR is uppercase)
    -excludeterm - Exclude results containing this term
    (term1 OR term2) AND term3 - Group operators for complex queries

2. SITE FILTERING:
    site:example.com - Limit search to specific website
    -site:example.com - Exclude a specific website
    site:.edu - Limit to educational domains
    site:.gov - Limit to government domains

3. TIME FILTERING:
    after:YYYY-MM-DD - Results after a specific date
    before:YYYY-MM-DD - Results before a specific date
    month: - Content from past month
    year: - Content from past year
    week: - Content from past week 

4. CONTENT TARGETING:
    intitle:term - Find pages with term in the title
    inurl:term - Find pages with term in the URL
    intext:term - Find pages with term in the content

5. SPECIALIZED CATEGORIES:
   For broader multi-engine searches by topic area:
    news: - News articles and current events
    map: - Map data, locations, and geographic information
    science: - Scientific papers, research, and academic content
    it: - Programming resources, documentation, and tech discussions
    files: - Document downloads, PDFs, eBooks, and academic papers
    weather: - Weather forecasts and climate information
    music: - Song lyrics, artist information, and music discussions
    tools: - Currency conversion, unit calculations, and online utilities

6. SPECIAL ENGINES:
   For searching specific sources directly:
    !wa - Wolfram Alpha for calculations, conversions, facts, and data comparisons
    !gh - GitHub for code repositories and programming projects
""",
    parameters={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The search query with optional operators or engine prefixes. Be specific and combine operators for better results.",
                "examples": [
                    "\"renewable energy\" AND efficiency site:.gov after:2024-01-01",
                    "!wa population of France compared to Germany",
                    "!gh python web framework stars:>1000",
                    "science: machine learning healthcare after:2025-01-15",
                    "it: \"python flask\" tutorial -beginner",
                    "tools: convert 100 USD to EUR",
                    "music: \"bohemian rhapsody\" lyrics"
                ]
            },
            "count": {
                "type": "number", 
                "description": "Number of results to return (default: 10, max: 30)",
                "default": 10
            }
        },
        "required": ["query"]
    }
)
def execute(query, count=None):
    """Search the web using SearXNG."""
    # Use default count from config if not provided
    if count is None:
        count = SEARCH_RESULTS_COUNT
        
    try:
        # Send request to SearXNG
        response = requests.get(
            f"{SEARXNG_URL}/search",
            params={
                "q": query,
                "format": "json"
            },
            timeout=HTTP_TIMEOUT
        )
        
        # Parse response data
        data = response.json()
        
        # Format results if available
        results = []
        if data.get("results"):
            # Get the configured number of results
            for item in data["results"][:count]:
                result = {
                    "title": item.get("title", "No title"),
                    "url": item.get("url", "No URL"),
                    "snippet": item.get("content", "No content")
                }
                results.append(result)
            
            return {
                "results": results,
                "query": query,
                "count": len(results),
                "_tool_status": f"✓ Successfully searched for \"{query}\" and found {len(results)} results."
            }
        
        return {
            "error": "No search results found", 
            "query": query
        }
    
    except Exception as e:
        return {
            "error": f"Search error: {str(e)}", 
            "query": query
        }
