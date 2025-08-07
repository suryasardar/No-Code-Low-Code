from typing import Dict, Any, List, Optional, Tuple
import time
import asyncio
from services.llm_service import get_llm_service
from services.embeddings_service import get_embeddings_service
from services.web_search import get_web_search_service
from services.encryption import decrypt_api_keys_dict
from db.supabase import APIKeysDB, WorkflowDB
from utils.helpers import EdgeNavigator

class WorkflowOrchestrator:
    def __init__(self):
        self.llm_service = get_llm_service()
        self.embeddings_service = get_embeddings_service()
        self.web_search_service = get_web_search_service()
    
    async def execute_workflow(self, stack_id: str, query: str) -> Dict[str, Any]:
        """Execute workflow based on stack configuration"""
        start_time = time.time()
        
        try:
            workflow_data = await WorkflowDB.get_workflow_by_stack_id(stack_id)
            if not workflow_data:
                raise ValueError(f"No workflow found for stack {stack_id}")
            
            workflow_id = workflow_data["id"]
            nodes = workflow_data["nodes"]
            edges = workflow_data["edges"]
            
            encrypted_key_data = await APIKeysDB.get_api_keys_by_workflow_id(workflow_id)
            api_keys = decrypt_api_keys_dict(encrypted_key_data) if encrypted_key_data else {}
            
            print(f"🚀 Executing workflow for stack: {stack_id}")
            print(f"📝 Query: {query}")
            print(f"🔧 Available nodes: {list(nodes.keys())}")
            
            # Determine execution flow
            execution_flow = self.get_execution_flow(nodes, edges)
            print(f"🔄 Execution flow: {[node['type'] for node in execution_flow]}")
            
            # Execute workflow
            result = await self.execute_flow(
                execution_flow, nodes, query, stack_id, api_keys
            )
            
            execution_time = time.time() - start_time
            
            return {
                "result": result["output"],
                "execution_time": execution_time,
                "sources_used": result.get("sources_used", []),
                "context_chunks": result.get("context_chunks", []),
                "execution_flow": [node["type"] for node in execution_flow]
            }
            
        except Exception as e:
            execution_time = time.time() - start_time
            print(f"❌ Workflow execution error: {str(e)}")
            return {
                "result": f"Error executing workflow: {str(e)}",
                "execution_time": execution_time,
                "error": True
            }

    def get_execution_flow(self, nodes: Dict, edges: Dict) -> List[Dict]:
        """Determine the execution flow using a topological sort."""
        navigator = EdgeNavigator(nodes, edges)
        
        execution_path_ids = navigator.get_topological_order()
        
        if not execution_path_ids:
            raise ValueError("Cannot determine a valid execution order for the workflow. Please check for cycles.")
        
        flow = []
        for node_id in execution_path_ids:
            node = {"id": node_id, **nodes[node_id]}
            if "type" not in node and "data" in node and "type" in node["data"]:
                node["type"] = node["data"]["type"]
            flow.append(node)
            
        return flow

    async def execute_flow(self, execution_flow: List[Dict], nodes: Dict, 
                          query: str, stack_id: str, api_keys: Dict) -> Dict[str, Any]:
        """Execute the flow using a shared context."""
        context = {"query": query, "stack_id": stack_id}
        sources_used = []
        context_chunks = []

        print(f"🎯 Starting flow execution with a shared context model.")
        
        for i, node in enumerate(execution_flow):
            node_type = node.get("type") or node.get("data", {}).get("type")
            
            print(f"📍 Processing node {i+1}/{len(execution_flow)}: {node_type}")
            
            if node_type == "userQuery":
                context = await self.process_user_query_node(node, context)
                
            elif node_type == "knowledgeBase":
                result = await self.process_knowledge_base_node(node, context, api_keys)
                context["knowledge_context"] = result.get("knowledge_context", "")
                context_chunks.extend(result.get("chunks", []))
                
            elif node_type == "webSearch":
                result = await self.process_web_search_node(node, context, api_keys)
                context["web_search_context"] = result.get("web_search_context", "")
                sources_used.extend(result.get("sources", []))
                
            elif node_type == "llmEngine":
                result = await self.process_llm_node(node, context, api_keys)
                context.update(result)
                
            elif node_type == "output":
                result = await self.process_output_node(node, context)
                context.update(result)
                
        return {
            "output": context.get("final_output", context.get("llm_response", context.get("query", ""))),
            "sources_used": sources_used,
            "context_chunks": [self.format_chunk_for_response(chunk) for chunk in context_chunks]
        }
    
    async def process_user_query_node(self, node: Dict, context: Dict) -> Dict:
        """Process UserQuery node"""
        print(f"✅ UserQuery processed: {context.get('query', '')}")
        return context

    async def process_knowledge_base_node(self, node: Dict, context: Dict, 
                                        api_keys: Dict) -> Dict:
        """Process KnowledgeBase node - Updated for your data structure"""
        
        # Add a safety check for 'data' and 'config'
        node_data = node.get("data", {})
        if not isinstance(node_data, dict):
            node_data = {}

        config_data = node_data.get("config", {})
        if not isinstance(config_data, dict):
            config_data = {}
        
        query = context.get("query", "")
        stack_id = context.get("stack_id", "")
        
        # Get configuration - check both locations
        embedding_model = (
            config_data.get("embeddingModel") or 
            node_data.get("embedding_model", "text-embedding-3-large")
        )
        
        # Convert Gemini model format if needed
        if embedding_model == "models/embedding-001":
            embedding_model = "models/embedding-001"  # Keep Gemini format
        
        top_k = node_data.get("top_k") or config_data.get("max_chunks", 5)
        similarity_threshold = node_data.get("similarity_threshold") or config_data.get("similarity_threshold", 0.7)
        
        # Get API key - check multiple locations
        api_key = (
            config_data.get("apiKey") or          # Your format
            node_data.get("api_key") or           # Standard format
            api_keys.get("knowledge", "")         # Encrypted keys
        )
        
        if not api_key:
            print("❌ No API key found for knowledge base")
            return {"knowledge_context": "No API key found for knowledge base", "chunks": []}
        
        try:
            # The rest of your existing logic goes here
            print(f"🔍 Searching knowledge base with:")
            print(f"  - Query: {query}")
            print(f"  - Stack ID: {stack_id}")
            print(f"  - Model: {embedding_model}")
            print(f"  - API Key type: {'Gemini' if api_key.startswith('AIzaSy') else 'OpenAI'}")
            
            # Search for relevant chunks
            chunks = await self.embeddings_service.search_similar_chunks(
                stack_id=stack_id,
                query=query,
                api_key=api_key,
                model=embedding_model,
                top_k=top_k,
                similarity_threshold=similarity_threshold
            )
            
            print(f"✅ Found {len(chunks)} chunks from knowledge base")
            
            # Format context from chunks
            knowledge_context = self.format_chunks_for_context(chunks)
            
            return {
                "knowledge_context": knowledge_context,
                "chunks": chunks
            }
            
        except Exception as e:
            print(f"❌ Knowledge base search failed: {str(e)}")
            return {
                "knowledge_context": f"Error retrieving knowledge: {str(e)}",
                "chunks": []
            }

    def format_chunk_for_response(self, chunk: Dict) -> str:
        """Format chunk object into string for API response"""
        try:
            content = chunk.get("content", "")
            source = chunk.get("source", "Unknown")
            score = chunk.get("score", 0)
            
            # Format as a readable string
            return f"[Score: {score:.3f}] Source: {source} - {content[:200]}{'...' if len(content) > 200 else ''}"
        except Exception:
            # Fallback to string representation
            return str(chunk)

    def format_chunks_for_context(self, chunks: List) -> str:
        """Format chunks into context string"""
        if not chunks:
            return ""
        
        context_parts = []
        for i, chunk in enumerate(chunks, 1):
            content = chunk.get("content", "")
            source = chunk.get("source", "Unknown")
            context_parts.append(f"[{i}] Source: {source}\nContent: {content}")
        
        return "\n\n".join(context_parts)

    async def process_web_search_node(self, node: Dict, context: Dict, api_keys: Dict) -> Dict:
        """Process WebSearch node"""
        # Implementation would go here
        return {"web_search_context": "", "sources": []}

    async def process_llm_node(self, node: Dict, context: Dict, api_keys: Dict) -> Dict:
        """Process LLM node"""
        try:
            # Get node configuration
            node_data = node.get("data", {})
            config_data = node_data.get("config", {})
            
            # Get API key
            api_key = (
                config_data.get("apiKey") or
                node_data.get("api_key") or
                api_keys.get("llm", "")
            )
            
            if not api_key:
                return {"llm_response": "No API key found for LLM"}
            
            # Build the prompt with context
            query = context.get("query", "")
            knowledge_context = context.get("knowledge_context", "")
            web_context = context.get("web_search_context", "")
            
            # Create system prompt
            system_prompt = """You are a helpful assistant. Use the provided context to answer the user's question accurately and comprehensively. If the context doesn't contain enough information, say so clearly."""
            
            # Get model configuration with proper type conversion and validation
            model = config_data.get("model", "gpt-4o-mini")
            
            # Validate and correct model name for API key type
            api_key_type = "gemini" if api_key.startswith("AIzaSy") else "openai"
            
            # Fix invalid model names
            if api_key_type == "gemini":
                valid_gemini_models = ["gemini-1.5-pro", "gemini-1.5-flash", "gemini-pro"]
                # Fix common invalid model names
                if model in ["Gemini API", "gemini", "Gemini", "gemini-api"] or model not in valid_gemini_models:
                    model = "gemini-1.5-flash"  # Default Gemini model
                    print(f"🔄 Corrected invalid model '{config_data.get('model')}' to '{model}' for Gemini API")
            else:
                valid_openai_models = ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"]
                
                # Fix common invalid OpenAI model names (case issues)
                model_fixes = {
                    "GPT-4o": "gpt-4o",
                    "GPT-4o-Mini": "gpt-4o-mini", 
                    "GPT-4": "gpt-4o",
                    "GPT-3.5-Turbo": "gpt-3.5-turbo",
                    "gpt-4": "gpt-4o"
                }
                
                if model in model_fixes:
                    model = model_fixes[model]
                    print(f"🔄 Corrected model name '{config_data.get('model')}' to '{model}' for OpenAI API")
                elif model not in valid_openai_models:
                    model = "gpt-4o-mini"  # Default OpenAI model
                    print(f"🔄 Corrected invalid model '{config_data.get('model')}' to '{model}' for OpenAI API")
            
            # Ensure temperature is a float and within valid range
            try:
                temperature = float(config_data.get("temperature", 0.7))
                # Clamp temperature to valid range (0.0 to 2.0 for most models)
                temperature = max(0.0, min(2.0, temperature))
            except (ValueError, TypeError):
                temperature = 0.7
                print(f"⚠️ Invalid temperature value, defaulting to 0.7")
            
            print(f"🔧 LLM Config - API Type: {api_key_type}, Model: {model}, Temperature: {temperature}")
            
            # Prepare context for the LLM service
            context_for_llm = ""
            if knowledge_context:
                context_for_llm += f"Knowledge Base Context:\n{knowledge_context}\n\n"
            if web_context:
                context_for_llm += f"Web Search Context:\n{web_context}\n\n"
            
            # Call LLM service with the correct parameters
            response = await self.llm_service.generate_response(
                query=query,
                context=context_for_llm if context_for_llm else None,
                api_key=api_key,
                model=model,
                temperature=temperature,
                system_prompt=system_prompt,
                web_search_results=web_context if web_context else None
            )
            
            print(f"✅ LLM generated response: {response[:100]}...")
            
            return {"llm_response": response}
            
        except Exception as e:
            print(f"❌ LLM processing failed: {str(e)}")
            return {"llm_response": f"Error processing LLM request: {str(e)}"}

    async def process_output_node(self, node: Dict, context: Dict) -> Dict:
        """Process Output node"""
        try:
            # Get the LLM response as the final output
            llm_response = context.get("llm_response", "")
            
            if not llm_response:
                # Fallback to knowledge context if no LLM response
                knowledge_context = context.get("knowledge_context", "")
                if knowledge_context:
                    final_output = f"Based on the available information:\n\n{knowledge_context}"
                else:
                    final_output = "No relevant information found to answer your question."
            else:
                final_output = llm_response
            
            print(f"✅ Output node processed: {final_output[:100]}...")
            
            return {"final_output": final_output}
            
        except Exception as e:
            print(f"❌ Output processing failed: {str(e)}")
            return {"final_output": f"Error processing output: {str(e)}"}


# Global instance
workflow_orchestrator = WorkflowOrchestrator()

def get_workflow_orchestrator() -> WorkflowOrchestrator:
    """Get workflow orchestrator instance"""
    return workflow_orchestrator