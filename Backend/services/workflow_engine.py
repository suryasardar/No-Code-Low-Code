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
    
    def determine_relevance_threshold(self, query: str, stack_id: str = None) -> float:
        """Determine appropriate threshold based on query analysis"""
        query_lower = query.lower()
        
        # Check for specific person names that might be in your documents
        known_names = ['surya', 'suryaprakash', 'kammari', 'chary']
        
        if any(name in query_lower for name in known_names):
            return 0.7  # Medium threshold for personal queries about resume owner
        
        # Check for technical skill queries that should match resume content
        tech_terms = ['react', 'node', 'javascript', 'python', 'experience', 'skills', 'worked', 'projects', 'developer', 'programming']
        if any(term in query_lower for term in tech_terms):
            return 0.65  # Medium-low threshold for technical queries
        
        # Check for real-time/external information queries - these should use web search
        external_indicators = [
            'narendra modi', 'prime minister', 'news', 'today', 'current', 'latest', 
            'headlines', 'politician', 'government', 'india news', 'breaking news',
            'top 10 news', 'top news'
        ]
        if any(indicator in query_lower for indicator in external_indicators):
            return 0.95  # Very high threshold - should almost always trigger web search
        
        # Check for general questions that might accidentally match resume content
        general_questions = ['tell me about', 'who is', 'what is', 'how is', 'where is']
        if any(question in query_lower for question in general_questions):
            return 0.8  # Higher threshold for general questions
        
        return 0.75  # Default threshold
    
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
        """Execute the flow with conditional web search logic"""
        context = {"query": query, "stack_id": stack_id}
        sources_used = []
        context_chunks = []
        
        print(f"🎯 Starting conditional flow execution")
        
        # Step 1: Process User Query
        for node in execution_flow:
            node_type = node.get("type") or node.get("data", {}).get("type")
            if node_type == "userQuery":
                context = await self.process_user_query_node(node, context)
                break
        
        # Step 2: Try Knowledge Base first (if exists)
        knowledge_result = None
        knowledge_chunks_found = False
        
        for node in execution_flow:
            node_type = node.get("type") or node.get("data", {}).get("type")
            if node_type == "knowledgeBase":
                print("📚 Checking Knowledge Base first...")
                knowledge_result = await self.process_knowledge_base_node(node, context, api_keys)
                
                # Check if we found relevant chunks
                chunks = knowledge_result.get("chunks", [])
                if chunks and len(chunks) > 0:
                    knowledge_chunks_found = True
                    print(f"✅ Found {len(chunks)} relevant chunks in knowledge base")
                    context["knowledge_context"] = knowledge_result.get("knowledge_context", "")
                    context_chunks.extend(chunks)
                else:
                    print("⚠️ No relevant chunks found in knowledge base")
                break
        
        # Step 3: Check LLM node for web search settings (since web search is built into LLM node)
        web_search_enabled = False
        serp_api_key = ""
        
        for node in execution_flow:
            node_type = node.get("type") or node.get("data", {}).get("type")
            if node_type == "llmEngine":
                node_data = node.get("data", {})
                config_data = node_data.get("config", {})
                web_search_enabled = config_data.get("webSearchEnabled", False)
                serp_api_key = config_data.get("serpApiKey", "")
                if web_search_enabled:
                    print(f"🔍 Web search enabled in LLM node with API key: {'Yes' if serp_api_key else 'No'}")
                break
        
        # Decide whether to use web search based on conditions
        should_use_web_search = False
        if web_search_enabled and serp_api_key and not knowledge_chunks_found:
            should_use_web_search = True
            print("🌐 Web search enabled and no relevant knowledge found - will use web search")
        elif web_search_enabled and knowledge_chunks_found:
            print("📚 Knowledge base has relevant content - skipping web search")
        elif web_search_enabled and not serp_api_key:
            print("🔍 Web search enabled but no SerpAPI key configured")
        else:
            print("🔒 Web search is disabled - proceeding without web search")
        
        # Step 4: Process LLM with all available context (web search will be handled inside LLM processing)
        for node in execution_flow:
            node_type = node.get("type") or node.get("data", {}).get("type")
            if node_type == "llmEngine":
                print("🤖 Processing LLM with combined context...")
                # Add execution context for LLM to understand what happened
                context["execution_summary"] = {
                    "knowledge_chunks_found": knowledge_chunks_found,
                    "web_search_used": should_use_web_search,
                    "web_search_enabled": web_search_enabled,
                    "should_use_web_search": should_use_web_search  # Pass this to LLM processing
                }
                
                result = await self.process_llm_node(node, context, api_keys)
                context.update(result)
                
                # Get sources from LLM processing if web search was used
                if result.get("web_search_sources"):
                    sources_used.extend(result["web_search_sources"])
                break
        
        # Step 5: Process Output
        for node in execution_flow:
            node_type = node.get("type") or node.get("data", {}).get("type")
            if node_type == "output":
                result = await self.process_output_node(node, context)
                context.update(result)
                break
        
        return {
            "output": context.get("final_output", context.get("llm_response", context.get("query", ""))),
            "sources_used": sources_used,
            "context_chunks": [self.format_chunk_for_response(chunk) for chunk in context_chunks],
            "execution_summary": {
                "knowledge_base_used": knowledge_chunks_found,
                "web_search_used": context.get("web_search_actually_used", should_use_web_search),
                "web_search_enabled": web_search_enabled,
                "chunks_found": len(context_chunks)
            }
        }
    
    async def process_user_query_node(self, node: Dict, context: Dict) -> Dict:
        """Process UserQuery node"""
        print(f"✅ UserQuery processed: {context.get('query', '')}")
        return context

    async def process_knowledge_base_node(self, node: Dict, context: Dict, 
                                    api_keys: Dict) -> Dict:
        """Process KnowledgeBase node with dynamic relevance threshold"""
        
        node_data = node.get("data", {})
        if not isinstance(node_data, dict):
            node_data = {}

        config_data = node_data.get("config", {})
        if not isinstance(config_data, dict):
            config_data = {}
        
        query = context.get("query", "")
        stack_id = context.get("stack_id", "")
        
        # Get configuration with better defaults
        embedding_model = (
            config_data.get("embeddingModel") or 
            node_data.get("embedding_model", "text-embedding-3-large")
        )
        
        # Use dynamic relevance threshold based on query analysis
        search_similarity_threshold = 0.1  # Cast a wide net initially
        relevance_threshold = self.determine_relevance_threshold(query, stack_id)
        
        top_k = node_data.get("top_k") or config_data.get("max_chunks", 5)
        
        # Get API key
        api_key = (
            config_data.get("apiKey") or
            node_data.get("api_key") or
            api_keys.get("knowledge", "")
        )
        
        if not api_key:
            print("No API key found for knowledge base")
            return {
                "knowledge_context": "No API key configured for knowledge base", 
                "chunks": [],
                "relevant_chunks_found": False
            }
        
        try:
            print(f"Searching knowledge base:")
            print(f"  - Query: {query}")
            print(f"  - Model: {embedding_model}")
            print(f"  - Dynamic relevance threshold: {relevance_threshold}")
            
            # Search for chunks with low threshold to get more results
            all_chunks = await self.embeddings_service.search_similar_chunks(
                stack_id=stack_id,
                query=query,
                api_key=api_key,
                model=embedding_model,
                top_k=top_k * 2,  # Get more chunks to filter from
                similarity_threshold=search_similarity_threshold
            )
            
            # Filter for truly relevant chunks using dynamic threshold
            relevant_chunks = [
                chunk for chunk in all_chunks 
                if chunk.get("similarity_score", 0) >= relevance_threshold
            ]
            
            print(f"Found {len(all_chunks)} total chunks, {len(relevant_chunks)} above relevance threshold")
            
            # Format context from relevant chunks only
            if relevant_chunks:
                knowledge_context = self.format_chunks_for_context(relevant_chunks[:top_k])
                
                return {
                    "knowledge_context": knowledge_context,
                    "chunks": relevant_chunks[:top_k],
                    "relevant_chunks_found": True,
                    "total_chunks_searched": len(all_chunks),
                    "relevance_threshold_used": relevance_threshold
                }
            else:
                # No relevant chunks found
                return {
                    "knowledge_context": "No relevant information found in knowledge base",
                    "chunks": [],
                    "relevant_chunks_found": False,
                    "total_chunks_searched": len(all_chunks),
                    "relevance_threshold_used": relevance_threshold
                }
            
        except Exception as e:
            print(f"Knowledge base search failed: {str(e)}")
            return {
                "knowledge_context": f"Error retrieving knowledge: {str(e)}",
                "chunks": [],
                "relevant_chunks_found": False
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
        """This method is kept for backward compatibility but shouldn't be called"""
        print("⚠️ Warning: process_web_search_node called but web search is integrated into LLM node")
        return {"web_search_context": "", "sources": []}

    async def process_llm_node(self, node: Dict, context: Dict, api_keys: Dict) -> Dict:
        """Process LLM node with built-in web search capability"""
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
            execution_summary = context.get("execution_summary", {})
            
            # Check if web search should be used from execution summary
            should_use_web_search = execution_summary.get("should_use_web_search", False)
            web_search_enabled = config_data.get("webSearchEnabled", False)
            serp_api_key = config_data.get("serpApiKey", "")
            
            web_search_context = ""
            sources_used = []
            web_search_actually_used = False
            
            # Perform web search if conditions are met
            if should_use_web_search and web_search_enabled and serp_api_key:
                print(f"🔍 Performing web search from LLM node...")
                try:
                    # Use the web search service
                    search_results = await self.web_search_service.search(
                        query=query,
                        provider="serpapi",
                        api_key=serp_api_key,
                        num_results=5
                    )
                    
                    # Format results for LLM context
                    web_search_context = self.web_search_service.format_search_results_for_llm(search_results)
                    sources_used = self.web_search_service.extract_search_sources(search_results)
                    web_search_actually_used = True
                    
                    print(f"✅ Web search completed: {len(sources_used)} sources found")
                    
                except Exception as web_error:
                    print(f"⚠️ Web search failed: {str(web_error)}")
                    web_search_context = ""
            
            # Create enhanced system prompt based on available context
            base_prompt = config_data.get("prompt", "You are a helpful assistant.")
            enhanced_prompt = base_prompt
            
            if knowledge_context and web_search_context:
                enhanced_prompt += "\n\nYou have access to both relevant document context and current web search results. Use both sources to provide a comprehensive answer."
            elif knowledge_context and knowledge_context != "No relevant information found in knowledge base":
                enhanced_prompt += "\n\nYou have relevant information from the knowledge base. Use this context to provide an accurate answer based on the available documents."
            elif web_search_context:
                enhanced_prompt += "\n\nYou have current web search results. Use this real-time information to answer the question."
            else:
                enhanced_prompt += "\n\nProvide the best answer you can using your general knowledge."
            
            # Fix model name issues
            model = config_data.get("model", "gpt-4o-mini")
            api_key_type = "gemini" if api_key.startswith("AIzaSy") else "openai"
            print(f"DEBUG: API key type detected as: {api_key_type}")

            if api_key_type == "gemini":
                valid_gemini_models = ["gemini-1.5-pro", "gemini-1.5-flash", "gemini-pro"]
                if model not in valid_gemini_models:
                    model = "gemini-1.5-flash"
                    print(f"Corrected model to {model} for Gemini API")
            else:
                valid_openai_models = ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"]
                model_fixes = {
                    "GPT-4o": "gpt-4o",
                    "GPT-4o-Mini": "gpt-4o-mini", 
                    "GPT-4": "gpt-4o",
                    "GPT-3.5-Turbo": "gpt-3.5-turbo",
                    "gpt-4": "gpt-4o"
                }
                
                if model in model_fixes:
                    model = model_fixes[model]
                    print(f"Corrected model to {model} for OpenAI API")
                elif model not in valid_openai_models:
                    model = "gpt-4o-mini"
                    print(f"Corrected invalid model to {model} for OpenAI API")
            
            # Temperature handling
            try:
                temperature = float(config_data.get("temperature", 0.7))
                temperature = max(0.0, min(2.0, temperature))
            except (ValueError, TypeError):
                temperature = 0.7
            
            print(f"LLM Config - Model: {model}, Temperature: {temperature}")
            print(f"Context Available - Knowledge: {bool(knowledge_context and knowledge_context != 'No relevant information found in knowledge base')}, Web: {bool(web_search_context)}")
            
            # Prepare context for the LLM service
            context_for_llm = ""
            
            # Add knowledge base context if available
            if knowledge_context and knowledge_context != "No relevant information found in knowledge base":
                context_for_llm += f"Document Context:\n{knowledge_context}\n\n"
            
            # Add web search context if available
            if web_search_context:
                context_for_llm += f"Web Search Results:\n{web_search_context}\n\n"
            
            # Build final context message
            if context_for_llm:
                context_for_llm += f"Question: {query}"
            
            # Call LLM service
            response = await self.llm_service.generate_response(
                query=query,
                context=context_for_llm if context_for_llm else None,
                api_key=api_key,
                model=model,
                temperature=temperature,
                system_prompt=enhanced_prompt,
                web_search_results=web_search_context if web_search_context else None
            )
            
            print(f"LLM generated response: {response[:100]}...")
            
            return {
                "llm_response": response,
                "model_used": model,
                "web_search_sources": sources_used,
                "web_search_actually_used": web_search_actually_used,
                "context_used": {
                    "knowledge_base": bool(knowledge_context and knowledge_context != "No relevant information found in knowledge base"),
                    "web_search": bool(web_search_context),
                    "execution_flow": execution_summary
                }
            }
            
        except Exception as e:
            print(f"LLM processing failed: {str(e)}")
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