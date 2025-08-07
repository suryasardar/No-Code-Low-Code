from fastapi import APIRouter, HTTPException, Depends
from typing import List
from api.models.workflow import StackCreate, StackResponse
from db.supabase import StackDB
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/stack", response_model=StackResponse, status_code=201)
async def create_stack(stack_data: StackCreate):
    """Create a new workflow stack"""
    try:
        # Create stack in database
        stack = await StackDB.create_stack(
            name=stack_data.name,
            description=stack_data.description
        )
        
        if not stack:
            raise HTTPException(
                status_code=500, 
                detail="Failed to create stack"
            )
        
        logger.info(f"Created new stack: {stack['id']} - {stack['name']}")
        return StackResponse(**stack)
        
    except Exception as e:
        logger.error(f"Error creating stack: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create stack: {str(e)}"
        )

@router.get("/stack", response_model=List[StackResponse])
async def get_all_stacks():
    """Get all workflow stacks"""
    try:
        stacks = await StackDB.get_all_stacks()
        
        # Convert to response models
        return [StackResponse(**stack) for stack in stacks]
        
    except Exception as e:
        logger.error(f"Error retrieving stacks: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve stacks: {str(e)}"
        )

@router.get("/stack/{stack_id}", response_model=StackResponse)
async def get_stack_by_id(stack_id: str):
    """Get a specific stack by ID"""
    try:
        stack = await StackDB.get_stack_by_id(stack_id)
        
        if not stack:
            raise HTTPException(
                status_code=404,
                detail=f"Stack with ID {stack_id} not found"
            )
        
        return StackResponse(**stack)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving stack {stack_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve stack: {str(e)}"
        )

@router.delete("/stack/{stack_id}")
async def delete_stack(stack_id: str):
    """Delete a stack and all associated data"""
    try:
        # Check if stack exists
        stack = await StackDB.get_stack_by_id(stack_id)
        if not stack:
            raise HTTPException(
                status_code=404,
                detail=f"Stack with ID {stack_id} not found"
            )
        
        # Note: Due to CASCADE constraints in database schema,
        # deleting stack will automatically delete associated workflows,
        # documents, and API keys
        from db.supabase import get_supabase
        client = get_supabase()
        
        result = client.table("stack").delete().eq("id", stack_id).execute()
        
        if not result.data:
            raise HTTPException(
                status_code=500,
                detail="Failed to delete stack"
            )
        
        logger.info(f"Deleted stack: {stack_id} - {stack['name']}")
        
        return {"message": f"Stack {stack_id} deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting stack {stack_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete stack: {str(e)}"
        )

@router.get("/stack/{stack_id}/stats")
async def get_stack_statistics(stack_id: str):
    """Get statistics for a stack"""
    try:
        # Check if stack exists
        stack = await StackDB.get_stack_by_id(stack_id)
        if not stack:
            raise HTTPException(
                status_code=404,
                detail=f"Stack with ID {stack_id} not found"
            )
        
        from db.supabase import get_supabase, WorkflowDB, DocumentsDB
        
        # Get workflow info
        workflow = await WorkflowDB.get_workflow_by_stack_id(stack_id)
        
        # Get documents info
        documents = await DocumentsDB.get_documents_by_stack_id(stack_id)
        
        # Get embeddings stats
        from services.embeddings_service import get_embeddings_service
        embeddings_service = get_embeddings_service()
        embeddings_stats = embeddings_service.get_collection_stats(stack_id)
        
        stats = {
            "stack_id": stack_id,
            "stack_name": stack["name"],
            "has_workflow": workflow is not None,
            "total_documents": len(documents),
            "total_embeddings": embeddings_stats.get("total_chunks", 0),
            "workflow_nodes": len(workflow.get("nodes", {})) if workflow else 0,
            "workflow_edges": len(workflow.get("edges", {})) if workflow else 0,
            "created_at": stack["created_at"],
            "documents": [
                {
                    "id": doc["id"],
                    "file_name": doc.get("file_name", ""),
                    "created_at": doc["created_at"]
                }
                for doc in documents
            ]
        }
        
        return stats
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting stack statistics {stack_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get stack statistics: {str(e)}"
        )