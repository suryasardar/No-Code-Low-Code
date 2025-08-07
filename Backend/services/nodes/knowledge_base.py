# services/nodes/knowledge_base.py
from typing import Dict, Any, List
from services.embeddings_service import get_embeddings_service

class KnowledgeBaseNode:
    """Processes KnowledgeBase node - retrieves document context"""
    
    @staticmethod
    async def process(node_data: Dict, context: Dict, api_key: str) -> Dict:
        """Process knowledge base node"""
        query = context.get("query", "")
        stack_id = context.get("stack_id", "")
        
        if not query or not stack_id:
            return {
                "error": "Missing query or stack_id",
                "knowledge_context": "",
                "chunks": []
            }
        
        # Get node configuration
        config = node_data.get("data", {})
        embedding_model = config.get("embedding_model", "text-embedding-3-large")
        similarity_threshold = config.get("similarity_threshold", 0.7)
        max_chunks = config.get("max_chunks", 5)
        
        try:
            embeddings_service = get_embeddings_service()
            
            # Search for relevant chunks
            chunks = await embeddings_service.search_similar_chunks(
                stack_id=stack_id,
                query=query,
                api_key=api_key,
                model=embedding_model,
                top_k=max_chunks,
                similarity_threshold=similarity_threshold
            )
            
            # Format context
            if chunks:
                context_text = "Relevant document context:\n\n"
                for i, chunk in enumerate(chunks, 1):
                    context_text += f"[{i}] {chunk['text']}\n"
                    if chunk.get('metadata', {}).get('file_name'):
                        context_text += f"Source: {chunk['metadata']['file_name']}\n"
                    context_text += "\n"
            else:
                context_text = "No relevant document context found."
            
            return {
                "knowledge_context": context_text,
                "chunks": chunks,
                "chunks_found": len(chunks),
                "embedding_model_used": embedding_model
            }
            
        except Exception as e:
            return {
                "error": f"Knowledge retrieval failed: {str(e)}",
                "knowledge_context": "",
                "chunks": []
            }