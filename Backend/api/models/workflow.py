from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
from datetime import datetime
import uuid

# Node Models
class NodeBase(BaseModel):
    id: str
    type: str
    position: Dict[str, float]
    data: Dict[str, Any]

class UserQueryNode(NodeBase):
    type: str = "userQuery"

class KnowledgeBaseNode(NodeBase):
    type: str = "knowledgeBase"

class LLMEngineNode(NodeBase):
    type: str = "llmEngine"

class WebSearchNode(NodeBase):
    type: str = "webSearch"

class OutputNode(NodeBase):
    type: str = "output"

# Edge Models
class Edge(BaseModel):
    id: str
    source: str
    target: str
    sourceHandle: Optional[str] = None
    targetHandle: Optional[str] = None
    type: Optional[str] = "default"

# Stack Models
class StackCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)

class StackResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime] = None

# API Keys Model
class APIKeys(BaseModel):
    llm: Optional[str] = None
    knowledge: Optional[str] = None  # For embeddings
    websearch: Optional[str] = None

# Workflow Models
class WorkflowSave(BaseModel):
    stack_id: str
    nodes: Dict[str, Any]
    edges: Dict[str, Any]
    api_keys: Optional[APIKeys] = None

class WorkflowResponse(BaseModel):
    id: str
    stack_id: str
    nodes: Dict[str, Any]
    edges: Dict[str, Any]
    created_at: datetime
    updated_at: Optional[datetime] = None

# Execution Models
class WorkflowExecutionRequest(BaseModel):
    stack_id: str
    query: str

class WorkflowExecutionResponse(BaseModel):
    result: str
    execution_time: float
    sources_used: Optional[List[str]] = None
    context_chunks: Optional[List[str]] = None

# Node Configuration Models
class UserQueryConfig(BaseModel):
    placeholder: str = "Write your query here"

class KnowledgeBaseConfig(BaseModel):
    files: List[str] = []
    embedding_model: str = "text-embedding-3-large"
    api_key: Optional[str] = None

class LLMConfig(BaseModel):
    model: str = "gpt-4o-mini"
    api_key: Optional[str] = None
    temperature: float = 0.75
    prompt: str = "You are a helpful AI assistant."
    web_search_enabled: bool = False

class WebSearchConfig(BaseModel):
    provider: str = "serpapi"  # or "brave"
    api_key: Optional[str] = None

class OutputConfig(BaseModel):
    format: str = "text"

# Node data mapping
NODE_CONFIG_MAPPING = {
    "userQuery": UserQueryConfig,
    "knowledgeBase": KnowledgeBaseConfig,
    "llmEngine": LLMConfig,
    "webSearch": WebSearchConfig,
    "output": OutputConfig
}

# Workflow validation
class WorkflowValidator:
    @staticmethod
    def validate_workflow(nodes: Dict, edges: Dict) -> bool:
        """Validate workflow structure"""
        node_ids = set(nodes.keys())
        
        # Check if edges reference valid nodes
        for edge_id, edge_data in edges.items():
            if edge_data["source"] not in node_ids or edge_data["target"] not in node_ids:
                return False
        
        # Check for required node types
        node_types = [nodes[node_id]["type"] for node_id in nodes]
        
        # Must have at least one UserQuery node
        if "userQuery" not in node_types:
            return False
        
        # Must have at least one Output node
        if "output" not in node_types:
            return False
        
        return True
    
    @staticmethod
    def get_execution_flow(nodes: Dict, edges: Dict) -> List[str]:
        """Determine execution flow from UserQuery to Output"""
        # Find UserQuery node
        user_query_nodes = [node_id for node_id, node in nodes.items() 
                           if node["type"] == "userQuery"]
        
        if not user_query_nodes:
            return []
        
        # Build adjacency list from edges
        graph = {}
        for edge_data in edges.values():
            source = edge_data["source"]
            target = edge_data["target"]
            if source not in graph:
                graph[source] = []
            graph[source].append(target)
        
        # Perform DFS to find path to output
        def dfs(node_id, path, visited):
            if node_id in visited:
                return []
            
            visited.add(node_id)
            current_path = path + [node_id]
            
            if nodes.get(node_id, {}).get("type") == "output":
                return current_path
            
            for neighbor in graph.get(node_id, []):
                result = dfs(neighbor, current_path, visited.copy())
                if result:
                    return result
            
            return []
        
        return dfs(user_query_nodes[0], [], set())