from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field
from datetime import datetime
from db.supabase import StackDB, WorkflowDB, get_supabase
from services.workflow_engine import get_workflow_orchestrator
import logging
import uuid

router = APIRouter()
logger = logging.getLogger(__name__)

# Enhanced Chat Models
class ChatRequest(BaseModel):
    stack_id: str
    query: str

class ChatResponse(BaseModel):
    response: str
    sources_used: List[str] = []
    context_chunks: List[Dict[str, Any]] = []  # More specific type for chunks
    execution_time: float
    chunk_count: int
    execution_flow: List[str] = []
    workflow_used: bool = True

class ChatMessage(BaseModel):
    stack_id: str
    user_query: str
    assistant_response: str
    execution_time: Optional[float] = None
    sources_used: Optional[List[str]] = []
    context_chunks_count: Optional[int] = 0

class ChatLogResponse(BaseModel):
    id: str
    stack_id: str
    user_query: str
    assistant_response: str
    execution_time: Optional[float]
    sources_used: Optional[List[str]] = []
    context_chunks_count: Optional[int] = 0
    created_at: datetime

class ChatHistoryRequest(BaseModel):
    stack_id: str
    limit: int = Field(default=50, ge=1, le=200)
    offset: int = Field(default=0, ge=0)

@router.post("/chat", response_model=ChatResponse)
async def chat_with_workflow(chat_request: ChatRequest):
    """Main chat endpoint using workflow orchestrator"""
    try:
        # Validate stack exists
        stack = await StackDB.get_stack_by_id(chat_request.stack_id)
        if not stack:
            raise HTTPException(
                status_code=404,
                detail=f"Stack with ID {chat_request.stack_id} not found"
            )
        
        # Execute workflow using the orchestrator
        orchestrator = get_workflow_orchestrator()
        workflow_result = await orchestrator.execute_workflow(
            stack_id=chat_request.stack_id,
            query=chat_request.query
        )
        
        # Check if workflow execution failed
        if workflow_result.get("error"):
            raise HTTPException(
                status_code=500,
                detail=f"Workflow execution failed: {workflow_result['result']}"
            )
        
        # Extract results with proper defaults and type conversion
        response_text = str(workflow_result.get("result", ""))
        execution_time = float(workflow_result.get("execution_time", 0))
        sources_used = list(workflow_result.get("sources_used", []))
        raw_context_chunks = workflow_result.get("context_chunks", [])
        execution_flow = list(workflow_result.get("execution_flow", []))
        
        # Convert context_chunks to proper format for API response
        context_chunks = []
        if isinstance(raw_context_chunks, list):
            for chunk in raw_context_chunks:
                try:
                    if isinstance(chunk, str):
                        # Handle string chunks
                        context_chunks.append({
                            "content": chunk[:500],  # Limit content length
                            "source": "Document",
                            "score": 0.0
                        })
                    elif isinstance(chunk, dict):
                        # Handle dict chunks - extract key fields safely
                        content = str(chunk.get("content", chunk.get("text", "")))
                        source = str(chunk.get("source", chunk.get("metadata", {}).get("file_name", "Document")))
                        score = float(chunk.get("score", chunk.get("similarity_score", 0)))
                        section = str(chunk.get("section", chunk.get("metadata", {}).get("section_type", "")))
                        
                        context_chunks.append({
                            "id": str(chunk.get("id", "")),
                            "content": content[:500],  # Limit content length
                            "source": source,
                            "score": score,
                            "section": section
                        })
                    else:
                        # Fallback for unexpected types
                        context_chunks.append({
                            "content": str(chunk)[:500],
                            "source": "Document",
                            "score": 0.0
                        })
                except Exception as chunk_error:
                    logger.warning(f"Failed to process chunk: {chunk_error}")
                    context_chunks.append({
                        "content": "Error processing chunk",
                        "source": "Document",
                        "score": 0.0
                    })
        
        # Ensure sources_used contains only strings
        sources_used = [str(source) for source in sources_used if source]
        
        # Ensure execution_flow contains only strings
        execution_flow = [str(step) for step in execution_flow if step]
        
        # Log the chat message with improved error handling
        try:
            chat_data = {
                "stack_id": chat_request.stack_id,
                "user_query": chat_request.query,
                "assistant_response": response_text,
                "execution_time": execution_time,
                "sources_used": sources_used,
                "context_chunks_count": len(context_chunks)
            }
            
            supabase = get_supabase()
            result = supabase.table("chat_logs").insert(chat_data).execute()
            logger.info(f"✅ Logged chat message for stack: {chat_request.stack_id}")
            
        except Exception as log_error:
            logger.warning(f"⚠️ Failed to log chat message: {log_error}")
        
        return ChatResponse(
            response=response_text,
            sources_used=sources_used,
            context_chunks=context_chunks,
            execution_time=execution_time,
            chunk_count=len(context_chunks),
            execution_flow=execution_flow,
            workflow_used=True
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error in chat endpoint: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process chat request: {str(e)}"
        )

@router.post("/chat/preview", response_model=dict)
async def preview_chat_workflow(chat_request: ChatRequest):
    """Preview what workflow would be executed without running it"""
    try:
        # Validate stack exists
        stack = await StackDB.get_stack_by_id(chat_request.stack_id)
        if not stack:
            raise HTTPException(
                status_code=404,
                detail=f"Stack with ID {chat_request.stack_id} not found"
            )
        
        # Get workflow data
        workflow_data = await WorkflowDB.get_workflow_by_stack_id(chat_request.stack_id)
        if not workflow_data:
            raise HTTPException(
                status_code=404,
                detail=f"No workflow found for stack {chat_request.stack_id}"
            )
        
        # Get workflow preview information
        nodes = workflow_data.get("nodes", {})
        edges = workflow_data.get("edges", {})
        
        # Analyze workflow structure
        node_types = {}
        for node_id, node_data in nodes.items():
            node_type = node_data.get("type", node_data.get("data", {}).get("type", "unknown"))
            node_types[node_type] = node_types.get(node_type, 0) + 1
        
        # Determine execution flow
        orchestrator = get_workflow_orchestrator()
        try:
            execution_flow = orchestrator.get_execution_flow(nodes, edges)
            flow_types = [node.get("type") for node in execution_flow]
        except:
            flow_types = list(node_types.keys())
        
        preview = {
            "query": chat_request.query,
            "preview_mode": True,
            "workflow_info": {
                "total_nodes": len(nodes),
                "node_types": node_types,
                "execution_flow": flow_types,
                "has_llm": "llmEngine" in node_types,
                "has_knowledge_base": "knowledgeBase" in node_types,
                "has_web_search": "webSearch" in node_types,
                "estimated_execution_time": len(nodes) * 0.5  # Rough estimate
            }
        }
        
        return preview
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting chat workflow preview: {str(e)}")
        return {
            "error": f"Failed to get workflow preview: {str(e)}",
            "query": chat_request.query,
            "preview_mode": True
        }

@router.post("/chat/validate", response_model=dict)
async def validate_chat_workflow(stack_id: str):
    """Validate if the workflow is properly configured for chat"""
    try:
        # Validate stack exists
        stack = await StackDB.get_stack_by_id(stack_id)
        if not stack:
            raise HTTPException(
                status_code=404,
                detail=f"Stack with ID {stack_id} not found"
            )
        
        # Get workflow data
        workflow_data = await WorkflowDB.get_workflow_by_stack_id(stack_id)
        if not workflow_data:
            return {
                "is_chat_ready": False,
                "error": f"No workflow found for stack {stack_id}",
                "chat_requirements": {
                    "has_user_query": False,
                    "has_output": False,
                    "has_llm_engine": False,
                    "has_context_source": False
                },
                "recommendations": ["Create a workflow first"]
            }
        
        # Analyze workflow structure
        nodes = workflow_data.get("nodes", {})
        node_types = set()
        
        for node_data in nodes.values():
            node_type = node_data.get("type", node_data.get("data", {}).get("type"))
            if node_type:
                node_types.add(node_type)
        
        # Check chat requirements
        chat_requirements = {
            "has_user_query": "userQuery" in node_types,
            "has_output": "output" in node_types,
            "has_llm_engine": "llmEngine" in node_types,
            "has_context_source": "knowledgeBase" in node_types or "webSearch" in node_types
        }
        
        # Generate recommendations
        recommendations = []
        if not chat_requirements["has_user_query"]:
            recommendations.append("Add a UserQuery node to accept user input")
        if not chat_requirements["has_output"]:
            recommendations.append("Add an Output node to return responses")
        if not chat_requirements["has_llm_engine"]:
            recommendations.append("Add an LLM Engine node for AI responses")
        if not chat_requirements["has_context_source"]:
            recommendations.append("Add a Knowledge Base or Web Search node for context")
        
        # Final chat readiness check
        is_chat_ready = all(chat_requirements.values())
        
        return {
            "is_chat_ready": is_chat_ready,
            "chat_requirements": chat_requirements,
            "recommendations": recommendations,
            "workflow_info": {
                "total_nodes": len(nodes),
                "node_types": list(node_types),
                "stack_id": stack_id
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error validating chat workflow: {str(e)}")
        return {
            "is_chat_ready": False,
            "error": str(e),
            "chat_requirements": {
                "has_user_query": False,
                "has_output": False,
                "has_llm_engine": False,
                "has_context_source": False
            },
            "recommendations": ["Fix workflow configuration errors"]
        }

@router.post("/chat/test", response_model=dict)
async def test_chat_workflow(stack_id: str, test_query: str = "Hello, this is a test message."):
    """Test the chat workflow with a simple query"""
    try:
        # Execute workflow with test query
        orchestrator = get_workflow_orchestrator()
        result = await orchestrator.execute_workflow(stack_id, test_query)
        
        # Format test result
        test_passed = not result.get("error", False)
        response_text = result.get("result", "")
        
        chat_test_result = {
            "test_passed": test_passed,
            "test_query": test_query,
            "response_preview": response_text[:200] + "..." if len(response_text) > 200 else response_text,
            "full_response": response_text,
            "execution_time": result.get("execution_time", 0),
            "sources_found": len(result.get("sources_used", [])),
            "context_chunks": len(result.get("context_chunks", [])),
            "execution_flow": result.get("execution_flow", [])
        }
        
        if result.get("error"):
            chat_test_result["error_message"] = result["result"]
        
        return chat_test_result
        
    except Exception as e:
        logger.error(f"❌ Error testing chat workflow: {str(e)}")
        return {
            "test_passed": False,
            "test_query": test_query,
            "error_message": str(e),
            "execution_time": 0,
            "sources_found": 0,
            "context_chunks": 0
        }

# Legacy endpoints for backward compatibility
@router.post("/chat/log", response_model=ChatLogResponse, status_code=201)
async def log_chat_message(chat_message: ChatMessage):
    """Log a chat message to the database (legacy endpoint)"""
    try:
        # Validate stack exists
        stack = await StackDB.get_stack_by_id(chat_message.stack_id)
        if not stack:
            raise HTTPException(
                status_code=404,
                detail=f"Stack with ID {chat_message.stack_id} not found"
            )
        
        # Prepare data for database
        chat_data = {
            "id": str(uuid.uuid4()),
            "stack_id": chat_message.stack_id,
            "user_query": chat_message.user_query,
            "assistant_response": chat_message.assistant_response,
            "execution_time": chat_message.execution_time,
            "sources_used": chat_message.sources_used or [],
            "context_chunks_count": chat_message.context_chunks_count or 0
        }
        
        # Insert into database
        supabase = get_supabase()
        result = supabase.table("chat_logs").insert(chat_data).execute()
        
        if not result.data:
            raise HTTPException(
                status_code=500,
                detail="Failed to log chat message"
            )
        
        logged_message = result.data[0]
        logger.info(f"✅ Logged chat message for stack: {chat_message.stack_id}")
        
        return ChatLogResponse(**logged_message)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error logging chat message: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to log chat message: {str(e)}"
        )

@router.post("/chat/history", response_model=List[ChatLogResponse])
async def get_chat_history(history_request: ChatHistoryRequest):
    """Get chat history for a stack"""
    try:
        # Validate stack exists
        stack = await StackDB.get_stack_by_id(history_request.stack_id)
        if not stack:
            raise HTTPException(
                status_code=404,
                detail=f"Stack with ID {history_request.stack_id} not found"
            )
        
        # Query chat logs
        supabase = get_supabase()
        result = supabase.table("chat_logs").select("*").eq(
            "stack_id", history_request.stack_id
        ).order("created_at", desc=True).range(
            history_request.offset, 
            history_request.offset + history_request.limit - 1
        ).execute()
        
        chat_logs = result.data or []
        
        return [ChatLogResponse(**log) for log in chat_logs]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error retrieving chat history for stack {history_request.stack_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve chat history: {str(e)}"
        )

@router.get("/chat/{stack_id}/stats")
async def get_chat_statistics(stack_id: str):
    """Get chat statistics for a stack"""
    try:
        # Validate stack exists
        stack = await StackDB.get_stack_by_id(stack_id)
        if not stack:
            raise HTTPException(
                status_code=404,
                detail=f"Stack with ID {stack_id} not found"
            )
        
        supabase = get_supabase()
        
        # Get total message count
        count_result = supabase.table("chat_logs").select(
            "id", count="exact"
        ).eq("stack_id", stack_id).execute()
        
        total_messages = count_result.count or 0
        
        # Get recent messages for analysis
        recent_result = supabase.table("chat_logs").select(
            "execution_time", "sources_used", "context_chunks_count", "created_at"
        ).eq("stack_id", stack_id).order(
            "created_at", desc=True
        ).limit(100).execute()
        
        recent_logs = recent_result.data or []
        
        # Calculate statistics
        if recent_logs:
            execution_times = [log["execution_time"] for log in recent_logs if log["execution_time"]]
            avg_execution_time = sum(execution_times) / len(execution_times) if execution_times else 0
            
            total_sources_used = sum(
                len(log.get("sources_used", [])) for log in recent_logs
            )
            
            total_context_chunks = sum(
                log.get("context_chunks_count", 0) for log in recent_logs
            )
            
            messages_with_sources = sum(
                1 for log in recent_logs if log.get("sources_used") and len(log["sources_used"]) > 0
            )
            
            messages_with_context = sum(
                1 for log in recent_logs if log.get("context_chunks_count", 0) > 0
            )
        else:
            avg_execution_time = 0
            total_sources_used = 0
            total_context_chunks = 0
            messages_with_sources = 0
            messages_with_context = 0
        
        # Get workflow information
        try:
            workflow_data = await WorkflowDB.get_workflow_by_stack_id(stack_id)
            if workflow_data:
                nodes = workflow_data.get("nodes", {})
                node_types = {}
                for node_data in nodes.values():
                    node_type = node_data.get("type", "unknown")
                    node_types[node_type] = node_types.get(node_type, 0) + 1
                
                workflow_stats = {
                    "total_nodes": len(nodes),
                    "node_types": node_types,
                    "has_llm": "llmEngine" in node_types,
                    "has_knowledge_base": "knowledgeBase" in node_types
                }
            else:
                workflow_stats = {"total_nodes": 0, "node_types": {}}
        except:
            workflow_stats = {"total_nodes": 0, "node_types": {}}
        
        stats = {
            "stack_id": stack_id,
            "total_messages": total_messages,
            "recent_messages_analyzed": len(recent_logs),
            "average_execution_time": round(avg_execution_time, 2),
            "total_sources_used": total_sources_used,
            "total_context_chunks_used": total_context_chunks,
            "messages_with_web_sources": messages_with_sources,
            "messages_with_document_context": messages_with_context,
            "usage_percentages": {
                "with_web_sources": round((messages_with_sources / len(recent_logs)) * 100, 1) if recent_logs else 0,
                "with_document_context": round((messages_with_context / len(recent_logs)) * 100, 1) if recent_logs else 0
            },
            "workflow_info": workflow_stats
        }
        
        return stats
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting chat statistics for stack {stack_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get chat statistics: {str(e)}"
        )

@router.delete("/chat/{stack_id}/clear")
async def clear_chat_history(stack_id: str):
    """Clear all chat history for a stack"""
    try:
        # Validate stack exists
        stack = await StackDB.get_stack_by_id(stack_id)
        if not stack:
            raise HTTPException(
                status_code=404,
                detail=f"Stack with ID {stack_id} not found"
            )
        
        # Delete all chat logs for the stack
        supabase = get_supabase()
        result = supabase.table("chat_logs").delete().eq("stack_id", stack_id).execute()
        
        deleted_count = len(result.data) if result.data else 0
        
        logger.info(f"🗑️ Cleared {deleted_count} chat messages for stack: {stack_id}")
        
        return {
            "message": f"Cleared chat history for stack {stack_id}",
            "deleted_messages": deleted_count
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error clearing chat history for stack {stack_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to clear chat history: {str(e)}"
        )

@router.get("/chat/{chat_id}", response_model=ChatLogResponse)
async def get_chat_message(chat_id: str):
    """Get a specific chat message by ID"""
    try:
        supabase = get_supabase()
        result = supabase.table("chat_logs").select("*").eq("id", chat_id).execute()
        
        if not result.data:
            raise HTTPException(
                status_code=404,
                detail=f"Chat message with ID {chat_id} not found"
            )
        
        chat_log = result.data[0]
        return ChatLogResponse(**chat_log)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error retrieving chat message {chat_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve chat message: {str(e)}"
        )

@router.delete("/chat/message/{chat_id}")
async def delete_chat_message(chat_id: str):
    """Delete a specific chat message"""
    try:
        supabase = get_supabase()
        
        # Check if message exists
        check_result = supabase.table("chat_logs").select("id").eq("id", chat_id).execute()
        
        if not check_result.data:
            raise HTTPException(
                status_code=404,
                detail=f"Chat message with ID {chat_id} not found"
            )
        
        # Delete the message
        result = supabase.table("chat_logs").delete().eq("id", chat_id).execute()
        
        if not result.data:
            raise HTTPException(
                status_code=500,
                detail="Failed to delete chat message"
            )
        
        logger.info(f"🗑️ Deleted chat message: {chat_id}")
        
        return {"message": f"Chat message {chat_id} deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error deleting chat message {chat_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete chat message: {str(e)}"
        )