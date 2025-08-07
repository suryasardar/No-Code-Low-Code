from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class DocumentUpload(BaseModel):
    stack_id: str
    file_name: str
    content_type: str

class DocumentResponse(BaseModel):
    id: str
    stack_id: str
    file_url: str
    file_name: Optional[str]
    file_size: Optional[int]
    embedding_id: str
    created_at: datetime

class DocumentDelete(BaseModel):
    document_id: str

class DocumentChunk(BaseModel):
    id: str
    text: str
    metadata: dict
    similarity_score: Optional[float] = None

class DocumentSearchRequest(BaseModel):
    stack_id: str
    query: str
    top_k: int = Field(default=5, ge=1, le=20)
    similarity_threshold: float = Field(default=0.7, ge=0.0, le=1.0)

class DocumentSearchResponse(BaseModel):
    chunks: List[DocumentChunk]
    total_found: int