
from supabase import create_client, Client
from typing import Optional, Dict, List, Any
import os
import uuid
from datetime import datetime

class SupabaseClient:
    def __init__(self):
        self.client: Optional[Client] = None
        
    async def init_client(self):
        """Initialize Supabase client"""
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        
        if not url or not key:
            raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set")
            
        self.client = create_client(url, key)
        
    def get_client(self) -> Client:
        """Get Supabase client instance"""
        if not self.client:
            raise RuntimeError("Supabase client not initialized")
        return self.client

# Global instance
supabase_client = SupabaseClient()

async def init_supabase():
    """Initialize Supabase connection"""
    await supabase_client.init_client()

def get_supabase() -> Client:
    """Get Supabase client"""
    return supabase_client.get_client()

class StackDB:
    @staticmethod
    async def create_stack(name: str, description: str) -> Dict:
        """Create a new stack"""
        client = get_supabase()
        
        data = {
            "id": str(uuid.uuid4()),
            "name": name,
            "description": description
        }
        
        result = client.table("stack").insert(data).execute()
        return result.data[0] if result.data else None
    
    @staticmethod
    async def get_all_stacks() -> List[Dict]:
        """Get all stacks"""
        client = get_supabase()
        result = client.table("stack").select("*").order("created_at", desc=True).execute()
        return result.data
    
    @staticmethod
    async def get_stack_by_id(stack_id: str) -> Optional[Dict]:
        """Get stack by ID"""
        client = get_supabase()
        result = client.table("stack").select("*").eq("id", stack_id).execute()
        return result.data[0] if result.data else None

class WorkflowDB:
    @staticmethod
    async def save_workflow(stack_id: str, nodes: Dict, edges: Dict) -> Dict:
        """Save or update workflow"""
        client = get_supabase()
        
        # Check if workflow exists for this stack
        existing = client.table("workflow").select("*").eq("stack_id", stack_id).execute()
        
        if existing.data:
            # Update existing workflow
            workflow_id = existing.data[0]["id"]
            result = client.table("workflow").update({
                "nodes": nodes,
                "edges": edges
            }).eq("id", workflow_id).execute()
        else:
            # Create new workflow
            data = {
                "id": str(uuid.uuid4()),
                "stack_id": stack_id,
                "nodes": nodes,
                "edges": edges
            }
            result = client.table("workflow").insert(data).execute()
        
        return result.data[0] if result.data else None
    
    @staticmethod
    async def get_workflow_by_stack_id(stack_id: str) -> Optional[Dict]:
        """Get workflow by stack ID"""
        client = get_supabase()
        result = client.table("workflow").select("*").eq("stack_id", stack_id).execute()
        return result.data[0] if result.data else None

class APIKeysDB:
    @staticmethod
    async def save_api_keys(workflow_id: str, encrypted_keys: Dict[str, str]) -> List[Dict]:
        """Save encrypted API keys"""
        client = get_supabase()
        
        # Delete existing keys for this workflow
        client.table("api_keys").delete().eq("workflow_id", workflow_id).execute()
        
        # Insert new keys
        keys_data = []
        for key_type, encrypted_key in encrypted_keys.items():
            key_data = {
                "id": str(uuid.uuid4()),
                "workflow_id": workflow_id,
                "key_type": key_type,
                "encrypted_key": encrypted_key
            }
            keys_data.append(key_data)
        
        if keys_data:
            result = client.table("api_keys").insert(keys_data).execute()
            return result.data
        return []
    
    @staticmethod
    async def get_api_keys_by_workflow_id(workflow_id: str) -> Dict[str, str]:
        """Get encrypted API keys by workflow ID"""
        client = get_supabase()
        result = client.table("api_keys").select("*").eq("workflow_id", workflow_id).execute()
        
        keys_dict = {}
        for key_data in result.data:
            keys_dict[key_data["key_type"]] = key_data["encrypted_key"]
        
        return keys_dict

class DocumentsDB:
    @staticmethod
    async def save_document(
        stack_id: str, 
        file_url: str, 
        embedding_id: str, 
        file_name: str, 
        file_size: int
    ) -> Dict:
        """Save document metadata with all required fields"""
        client = get_supabase()
        
        data = {
            "id": str(uuid.uuid4()),
            "stack_id": stack_id,
            "file_url": file_url,
            "embedding_id": embedding_id,
            "file_name": file_name,
            "file_size": file_size,
            "created_at": datetime.utcnow().isoformat()
        }
        
        try:
            result = client.table("documents").insert(data).execute()
            
            if hasattr(result, 'error') and result.error:
                raise Exception(f"Database error: {result.error}")
                
            if not result.data or len(result.data) == 0:
                raise Exception("No data returned from database insert")
                
            return result.data[0]
            
        except Exception as e:
            logger.error(f"Database error in save_document: {str(e)}")
            raise
    
    @staticmethod
    async def get_documents_by_stack_id(stack_id: str) -> List[Dict]:
        """Get documents by stack ID"""
        client = get_supabase()
        
        try:
            result = client.table("documents").select("*").eq("stack_id", stack_id).order("created_at", desc=True).execute()
            
            if hasattr(result, 'error') and result.error:
                raise Exception(f"Database error: {result.error}")
                
            return result.data or []
            
        except Exception as e:
            logger.error(f"Database error in get_documents_by_stack_id: {str(e)}")
            raise
    
    @staticmethod
    async def delete_document(document_id: str) -> bool:
        """Delete document by ID"""
        client = get_supabase()
        
        try:
            result = client.table("documents").delete().eq("id", document_id).execute()
            
            if hasattr(result, 'error') and result.error:
                raise Exception(f"Database error: {result.error}")
                
            return result.data and len(result.data) > 0
            
        except Exception as e:
            logger.error(f"Database error in delete_document: {str(e)}")
            raise