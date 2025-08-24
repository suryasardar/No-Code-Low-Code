import httpx
import os
from typing import List, Dict, Optional
import json

class WebSearchService:
    def __init__(self):
        self.serpapi_base_url = "https://serpapi.com/search"
        self.brave_base_url = "https://api.search.brave.com/res/v1/web/search"
    
    async def search_with_serpapi(self, query: str, api_key: str, 
                                num_results: int = 5) -> Dict:
        """Search using SerpAPI"""
        params = {
            "q": query,
            "api_key": api_key,
            "engine": "google",
            "num": num_results,
            "output": "json"
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(self.serpapi_base_url, params=params)
                response.raise_for_status()
                data = response.json()
                
                return self.format_serpapi_results(data)
                
        except Exception as e:
            raise ValueError(f"SerpAPI search failed: {e}")
    
    async def search_with_brave(self, query: str, api_key: str,
                              num_results: int = 5) -> Dict:
        """Search using Brave Search API"""
        headers = {
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
            "X-Subscription-Token": api_key
        }
        
        params = {
            "q": query,
            "count": num_results,
            "offset": 0,
            "mkt": "en-US",
            "safesearch": "moderate",
            "textDecorations": False,
            "textFormat": "Raw"
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    self.brave_base_url, 
                    headers=headers, 
                    params=params
                )
                response.raise_for_status()
                data = response.json()
                
                return self.format_brave_results(data)
                
        except Exception as e:
            raise ValueError(f"Brave search failed: {e}")
    
    def format_serpapi_results(self, data: Dict) -> Dict:
        """Format SerpAPI results into standardized format"""
        results = []
        
        # Extract organic results
        organic_results = data.get("organic_results", [])
        for result in organic_results:
            formatted_result = {
                "title": result.get("title", ""),
                "url": result.get("link", ""),
                "snippet": result.get("snippet", ""),
                "source": "serpapi"
            }
            results.append(formatted_result)
        
        # Extract answer box if available
        answer_box = data.get("answer_box", {})
        if answer_box:
            answer_result = {
                "title": "Answer Box",
                "url": answer_box.get("link", ""),
                "snippet": answer_box.get("answer", answer_box.get("snippet", "")),
                "source": "serpapi_answer_box"
            }
            results.insert(0, answer_result)
        
        return {
            "query": data.get("search_parameters", {}).get("q", ""),
            "results": results,
            "total_results": len(results),
            "search_engine": "google_via_serpapi"
        }
    
    def format_brave_results(self, data: Dict) -> Dict:
        """Format Brave search results into standardized format"""
        results = []
        
        # Extract web results
        web_results = data.get("web", {}).get("results", [])
        for result in web_results:
            formatted_result = {
                "title": result.get("title", ""),
                "url": result.get("url", ""),
                "snippet": result.get("description", ""),
                "source": "brave"
            }
            results.append(formatted_result)
        
        return {
            "query": data.get("query", {}).get("original", ""),
            "results": results,
            "total_results": len(results),
            "search_engine": "brave"
        }
    
    async def search(self, query: str, provider: str = "serpapi", 
                   api_key: str = "", num_results: int = 5) -> Dict:
        """Search using specified provider"""
        if not api_key:
            # Try to get default API key
            if provider == "serpapi":
                api_key = os.getenv("DEFAULT_SERPAPI_KEY", "")
            elif provider == "brave":
                api_key = os.getenv("DEFAULT_BRAVE_API_KEY", "")
        
        if not api_key:
            raise ValueError(f"API key required for {provider} search")
        
        if provider == "serpapi":
            return await self.search_with_serpapi(query, api_key, num_results)
        elif provider == "brave":
            return await self.search_with_brave(query, api_key, num_results)
        else:
            raise ValueError(f"Unsupported search provider: {provider}")
    
    def format_search_results_for_llm(self, search_results: Dict) -> str:
        """Format search results for LLM context"""
        if not search_results.get("results"):
            return "No search results found."
        
        formatted = f"Search Query: {search_results['query']}\n\n"
        formatted += "Search Results:\n"
        
        for i, result in enumerate(search_results["results"], 1):
            formatted += f"{i}. {result['title']}\n"
            formatted += f"   URL: {result['url']}\n"
            formatted += f"   Summary: {result['snippet']}\n\n"
        
        return formatted
    
    def extract_search_sources(self, search_results: Dict) -> List[str]:
        """Extract source URLs from search results"""
        if not search_results.get("results"):
            return []
        
        return [result["url"] for result in search_results["results"] if result.get("url")]
    
    
# Global instance
web_search_service = WebSearchService()

def get_web_search_service() -> WebSearchService:
    """Get web search service instance"""
    return web_search_service