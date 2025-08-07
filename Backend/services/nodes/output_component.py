# services/nodes/output_component.py
from typing import Dict, Any
import json

class OutputNode:
    """Processes Output node - formats final response"""
    
    @staticmethod
    async def process(node_data: Dict, context: Dict) -> Dict:
        """Process output node"""
        
        # Get node configuration
        config = node_data.get("data", {})
        output_format = config.get("format", "text")
        include_metadata = config.get("include_metadata", False)
        
        # Determine what to output based on available context
        output_content = ""
        metadata = {}
        
        # Priority order: LLM response > Knowledge context > Web search > Raw query
        if context.get("llm_response"):
            output_content = context["llm_response"]
            metadata["source"] = "llm"
            metadata["model_used"] = context.get("model_used", "unknown")
        elif context.get("knowledge_context"):
            output_content = context["knowledge_context"]
            metadata["source"] = "knowledge_base"
            metadata["chunks_count"] = context.get("chunks_found", 0)
        elif context.get("web_search_context"):
            output_content = context["web_search_context"]
            metadata["source"] = "web_search"
        else:
            output_content = context.get("query", "No output generated")
            metadata["source"] = "raw_query"
        
        # Add execution metadata
        metadata.update({
            "execution_flow": context.get("execution_flow", []),
            "context_chunks_used": len(context.get("chunks", [])),
            "web_sources_used": len(context.get("sources", [])),
            "has_knowledge_context": bool(context.get("knowledge_context")),
            "has_web_context": bool(context.get("web_search_context"))
        })
        
        # Format output based on specified format
        if output_format == "json":
            final_output = {
                "response": output_content,
                "metadata": metadata if include_metadata else None
            }
        elif output_format == "markdown":
            final_output = f"# Response\n\n{output_content}"
            if include_metadata and metadata:
                final_output += f"\n\n---\n\n**Metadata:** {json.dumps(metadata, indent=2)}"
        else:  # text format
            final_output = output_content
            if include_metadata and metadata:
                final_output += f"\n\n---\nGenerated using: {metadata.get('source', 'unknown')}"
        
        return {
            "final_output": final_output,
            "output_format": output_format,
            "metadata": metadata,
            "content_length": len(str(output_content))
        }