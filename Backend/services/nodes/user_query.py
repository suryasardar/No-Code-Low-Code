# services/nodes/user_query.py
from typing import Dict, Any

class UserQueryNode:
    """Processes UserQuery node - entry point for user queries"""
    
    @staticmethod
    async def process(node_data: Dict, context: Dict) -> Dict:
        """Process user query node"""
        # UserQuery node simply passes through the query
        query = context.get("query", "")
        
        # Extract any placeholder text or validation
        placeholder = node_data.get("data", {}).get("placeholder", "")
        
        # Basic validation
        if not query.strip():
            return {
                "error": "Empty query provided",
                "processed_query": ""
            }
        
        return {
            "processed_query": query.strip(),
            "placeholder": placeholder,
            "query_length": len(query.strip())
        }