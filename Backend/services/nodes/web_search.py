# services/nodes/web_search.py (if needed as separate node)
from typing import Dict, Any
from services.web_search import get_web_search_service

class WebSearchNode:
    """Processes WebSearch node - performs web searches"""
    
    @staticmethod
    async def process(node_data: Dict, context: Dict, api_key: str) -> Dict:
        """Process web search node"""
        query = context.get("query", "")
        
        if not query:
            return {
                "error": "No query provided for web search",
                "web_search_context": "",
                "sources": []
            }
        
        # Get node configuration
        config = node_data.get("data", {})
        provider = config.get("provider", "serpapi")
        num_results = config.get("num_results", 5)
        
        try:
            web_search_service = get_web_search_service()
            
            # Perform search
            search_results = await web_search_service.search(
                query=query,
                provider=provider,
                api_key=api_key,
                num_results=num_results
            )
            
            # Format for LLM context
            search_context = web_search_service.format_search_results_for_llm(search_results)
            
            # Extract sources
            sources = web_search_service.extract_search_sources(search_results)
            
            return {
                "web_search_context": search_context,
                "sources": sources,
                "provider_used": provider,
                "results_count": len(search_results.get("results", []))
            }
            
        except Exception as e:
            return {
                "error": f"Web search failed: {str(e)}",
                "web_search_context": "",
                "sources": []
            }