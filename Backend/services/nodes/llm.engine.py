# services/nodes/llm_engine.py
from typing import Dict, Any
from services.llm_service import get_llm_service

class LLMEngineNode:
    """Processes LLM node - generates responses using language models"""
    
    @staticmethod
    async def process(node_data: Dict, context: Dict, api_key: str) -> Dict:
        """Process LLM engine node"""
        query = context.get("query", "")
        
        if not query:
            return {
                "error": "No query provided to LLM",
                "llm_response": ""
            }
        
        # Get node configuration
        config = node_data.get("data", {})
        model = config.get("model", "gpt-4o-mini")
        temperature = config.get("temperature", 0.75)
        system_prompt = config.get("prompt", "You are a helpful AI assistant.")
        max_tokens = config.get("max_tokens")
        web_search_enabled = config.get("web_search_enabled", False)
        
        # Build context from previous nodes
        knowledge_context = context.get("knowledge_context", "")
        web_search_context = context.get("web_search_context", "")
        
        # Combine contexts
        combined_context = ""
        if knowledge_context and knowledge_context != "No relevant document context found.":
            combined_context += f"Document Context:\n{knowledge_context}\n\n"
        
        web_search_results = None
        if web_search_enabled and web_search_context:
            web_search_results = web_search_context
        
        try:
            llm_service = get_llm_service()
            
            response = await llm_service.generate_response(
                query=query,
                context=combined_context if combined_context else None,
                api_key=api_key,
                model=model,
                temperature=temperature,
                system_prompt=system_prompt,
                web_search_results=web_search_results
            )
            
            return {
                "llm_response": response,
                "model_used": model,
                "temperature": temperature,
                "context_provided": bool(combined_context),
                "web_search_used": bool(web_search_results)
            }
            
        except Exception as e:
            return {
                "error": f"LLM generation failed: {str(e)}",
                "llm_response": f"Sorry, I encountered an error: {str(e)}"
            }
