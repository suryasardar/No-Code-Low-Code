from fastapi import APIRouter, HTTPException, Depends
from api.models.workflow import (
    WorkflowSave, WorkflowResponse, WorkflowExecutionRequest, 
    WorkflowExecutionResponse, WorkflowValidator
)
from db.supabase import WorkflowDB, APIKeysDB, StackDB
from services.encryption import encrypt_api_keys_dict
from services.workflow_engine import get_workflow_orchestrator
from utils.helpers import WorkflowAnalyzer
import logging
import time

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/workflow", response_model=WorkflowResponse, status_code=201)
async def save_workflow(workflow_data: WorkflowSave):
    """Save or update workflow configuration"""
    try:
        # Validate stack exists
        stack = await StackDB.get_stack_by_id(workflow_data.stack_id)
        if not stack:
            raise HTTPException(
                status_code=404,
                detail=f"Stack with ID {workflow_data.stack_id} not found"
            )
        
        # Validate workflow structure
        if not WorkflowValidator.validate_workflow(workflow_data.nodes, workflow_data.edges):
            raise HTTPException(
                status_code=400,
                detail="Invalid workflow structure. Must have UserQuery and Output nodes."
            )
        
        # Save workflow
        workflow = await WorkflowDB.save_workflow(
            stack_id=workflow_data.stack_id,
            nodes=workflow_data.nodes,
            edges=workflow_data.edges
        )
        
        if not workflow:
            raise HTTPException(
                status_code=500,
                detail="Failed to save workflow"
            )
        
        workflow_id = workflow["id"]
        
        # Save encrypted API keys if provided
        if workflow_data.api_keys:
            api_keys_dict = {}
            
            if workflow_data.api_keys.llm:
                api_keys_dict["llm"] = workflow_data.api_keys.llm
            if workflow_data.api_keys.knowledge:
                api_keys_dict["knowledge"] = workflow_data.api_keys.knowledge
            if workflow_data.api_keys.websearch:
                api_keys_dict["websearch"] = workflow_data.api_keys.websearch
            
            if api_keys_dict:
                encrypted_keys = encrypt_api_keys_dict(api_keys_dict)
                await APIKeysDB.save_api_keys(workflow_id, encrypted_keys)
        
        logger.info(f"Saved workflow for stack: {workflow_data.stack_id}")
        
        return WorkflowResponse(**workflow)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error saving workflow: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to save workflow: {str(e)}"
        )

@router.get("/workflow/{stack_id}", response_model=WorkflowResponse)
async def get_workflow_by_stack_id(stack_id: str):
    """Get workflow configuration by stack ID"""
    try:
        workflow = await WorkflowDB.get_workflow_by_stack_id(stack_id)
        
        if not workflow:
            raise HTTPException(
                status_code=404,
                detail=f"No workflow found for stack {stack_id}"
            )
        
        return WorkflowResponse(**workflow)
        
    except HTTPException:
       raise
    except Exception as e:
        import traceback
        error_msg = f"Exception: {str(e)}\nTraceback: {traceback.format_exc()}"
        logger.error(f"Error saving workflow: {error_msg}")
        raise HTTPException(
            status_code=500,
            detail=error_msg
        )

@router.post("/workflow/execute", response_model=WorkflowExecutionResponse)
async def execute_workflow(execution_request: WorkflowExecutionRequest):
    """Execute workflow with user query"""
    try:
        from services.workflow_engine import get_workflow_orchestrator
        
        orchestrator = get_workflow_orchestrator()
        
        # Execute the workflow
        result = await orchestrator.execute_workflow(
            stack_id=execution_request.stack_id,
            query=execution_request.query
        )
        
        return WorkflowExecutionResponse(
            result=result["result"],
            execution_time=result["execution_time"],
            sources_used=result.get("sources_used", []),
            context_chunks=result.get("context_chunks", [])
        )
        
    except Exception as e:
        logger.error(f"Error executing workflow: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to execute workflow: {str(e)}"
        )
    """Execute workflow with user query"""
    try:
        # Validate stack exists
        stack = await StackDB.get_stack_by_id(execution_request.stack_id)
        if not stack:
            raise HTTPException(
                status_code=404,
                detail=f"Stack with ID {execution_request.stack_id} not found"
            )
        
        # Get workflow orchestrator and execute
        orchestrator = get_workflow_orchestrator()
        result = await orchestrator.execute_workflow(
            stack_id=execution_request.stack_id,
            query=execution_request.query
        )
        
        if result.get("error"):
            raise HTTPException(
                status_code=500,
                detail=result["result"]
            )
        
        return WorkflowExecutionResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error executing workflow for stack {execution_request.stack_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to execute workflow: {str(e)}"
        )



    """Test workflow configuration with a simple query"""
    try:
        test_query = "Hello, this is a test query to validate the workflow configuration."
        
        execution_request = WorkflowExecutionRequest(
            stack_id=stack_id,
            query=test_query
        )
        
        # Execute test
        orchestrator = get_workflow_orchestrator()
        result = await orchestrator.execute_workflow(stack_id, test_query)
        
        # Check if execution was successful
        test_result = {
            "test_passed": not result.get("error", False),
            "execution_time": result.get("execution_time", 0),
            "flow_executed": result.get("execution_flow", []),
            "sources_used": len(result.get("sources_used", [])),
            "context_chunks": len(result.get("context_chunks", [])),
            "test_query": test_query,
            "test_response": result.get("result", "")[:200] + "..." if len(result.get("result", "")) > 200 else result.get("result", "")
        }
        
        if result.get("error"):
            test_result["error_message"] = result["result"]
        
        return test_result
        
    except Exception as e:
        logger.error(f"Error testing workflow for stack {stack_id}: {str(e)}")
        return {
            "test_passed": False,
            "error_message": str(e),
            "execution_time": 0,
            "test_query": test_query if 'test_query' in locals() else ""
        }