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