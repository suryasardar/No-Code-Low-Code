from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Depends
from typing import List, Optional
import uuid
import os
from api.models.document import (
    DocumentResponse, DocumentDelete, DocumentSearchRequest, 
    DocumentSearchResponse, DocumentChunk
)
from db.supabase import DocumentsDB, StackDB, get_supabase
from services.document_processor import get_document_processor
from services.embeddings_service import get_embeddings_service
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/documents/upload", response_model=DocumentResponse, status_code=201)
async def upload_document(
    file: UploadFile = File(...),
    stack_id: str = Form(...),
    api_key: Optional[str] = Form(None),
    embedding_model: str = Form("text-embedding-3-large")
):
    """Upload and process a PDF document"""
    try:
        # Debug logging
        logger.info(f"=== DOCUMENT UPLOAD STARTED ===")
        logger.info(f"Stack ID: {stack_id}")
        logger.info(f"File: {file.filename}, Content Type: {file.content_type}")
        logger.info(f"Embedding Model: {embedding_model}")
        
        # Validate UUID format
        import re
        uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'
        if not re.match(uuid_pattern, stack_id, re.IGNORECASE):
            logger.error(f"Invalid UUID format: {stack_id}")
            raise HTTPException(
                status_code=400,
                detail=f"Invalid stack_id format: '{stack_id}'. Expected UUID format"
            )
        
        # Validate stack exists
        logger.info("Validating stack existence...")
        stack = await StackDB.get_stack_by_id(stack_id)
        if not stack:
            logger.error(f"Stack not found: {stack_id}")
            raise HTTPException(
                status_code=404,
                detail=f"Stack with ID {stack_id} not found"
            )
        logger.info(f"Stack found: {stack.get('name', 'Unknown')}")
        
        # Validate file type
        if not file.filename:
            raise HTTPException(status_code=400, detail="No filename provided")
            
        file_extension = file.filename.lower()
        supported_extensions = ['.pdf', '.txt', '.doc', '.docx']
        
        if not any(file_extension.endswith(ext) for ext in supported_extensions):
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type. Supported types: {', '.join(supported_extensions)}"
            )
        
        # Read file content
        logger.info("Reading file content...")
        file_content = await file.read()
        file_size = len(file_content)
        
        if file_size == 0:
            raise HTTPException(status_code=400, detail="Empty file uploaded")
        
        if file_size > 50 * 1024 * 1024:  # 50MB limit
            raise HTTPException(status_code=400, detail="File too large. Maximum size: 50MB")
            
        logger.info(f"File size: {file_size / 1024:.1f} KB")
        
        # Process document
        logger.info("Processing document...")
        try:
            document_processor = get_document_processor()
            clean_text, chunks = await document_processor.process_document(
                file_content=file_content,
                file_name=file.filename,
                stack_id=stack_id
            )
            logger.info(f"Document processed: {len(chunks)} chunks created")
        except Exception as e:
            logger.error(f"Document processing failed: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to process document: {str(e)}"
            )
        
        # Upload file to Supabase storage
        logger.info("Uploading to Supabase storage...")
        try:
            supabase = get_supabase()
            file_path = f"documents/{stack_id}/{uuid.uuid4()}_{file.filename}"
            
            storage_result = supabase.storage.from_("documents").upload(
                path=file_path,
                file=file_content,
                file_options={"content-type": file.content_type or "application/pdf"}
            )
            
            if hasattr(storage_result, 'error') and storage_result.error:
                logger.error(f"Storage error: {storage_result.error}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to upload file to storage: {storage_result.error}"
                )
            
            logger.info(f"File uploaded to storage: {file_path}")
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Storage upload exception: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Storage upload failed: {str(e)}"
            )
        
        # Get file URL
        try:
            file_url_obj = supabase.storage.from_("documents").get_public_url(file_path)
            file_url = file_url_obj.public_url if hasattr(file_url_obj, 'public_url') else str(file_url_obj)
            logger.info(f"File URL generated: {file_url}")
        except Exception as e:
            logger.error(f"Failed to get file URL: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to get file URL: {str(e)}"
            )
        
        # Get API key if not provided
        if not api_key:
            logger.info("No API key provided, checking workflow configuration...")
            try:
                from db.supabase import WorkflowDB, APIKeysDB
                from services.encryption import decrypt_api_keys_dict
                
                workflow = await WorkflowDB.get_workflow_by_stack_id(stack_id)
                if workflow:
                    encrypted_keys = await APIKeysDB.get_api_keys_by_workflow_id(workflow["id"])
                    if encrypted_keys and "knowledge" in encrypted_keys:
                        decrypted_keys = decrypt_api_keys_dict(encrypted_keys)
                        api_key = decrypted_keys.get("knowledge")
                        logger.info("Using API key from workflow configuration")
            except Exception as e:
                logger.warning(f"Failed to get API key from workflow: {str(e)}")
        
        if not api_key:
            logger.error("No API key available for embeddings")
            raise HTTPException(
                status_code=400,
                detail="API key required for embeddings. Provide api_key parameter or configure in workflow."
            )
        
        # Generate embeddings
        logger.info("Generating embeddings...")
        try:
            embeddings_service = get_embeddings_service()
            embedding_id = await embeddings_service.embed_documents(
                stack_id=stack_id,
                chunks=chunks,
                api_key=api_key,
                model=embedding_model
            )
            logger.info(f"Embeddings generated successfully: {embedding_id}")
        except Exception as e:
            logger.error(f"Embeddings generation failed: {str(e)}")
            
            # Clean up uploaded file on embedding failure
            try:
                supabase.storage.from_("documents").remove([file_path])
                logger.info("Cleaned up uploaded file after embedding failure")
            except:
                pass
                
            raise HTTPException(
                status_code=500,
                detail=f"Failed to generate embeddings: {str(e)}"
            )
        
        # Save document metadata to database
        logger.info("Saving document metadata...")
        try:
            document = await DocumentsDB.save_document(
                stack_id=stack_id,
                file_url=file_url,
                embedding_id=embedding_id,
                file_name=file.filename,
                file_size=file_size
            )
            
            if not document:
                logger.error("Database save returned None")
                raise HTTPException(
                    status_code=500,
                    detail="Failed to save document metadata - database returned None"
                )
                
            logger.info(f"Document metadata saved successfully: {document.get('id', 'Unknown ID')}")
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Database save failed: {str(e)}")
            
            # Clean up on database failure
            try:
                supabase.storage.from_("documents").remove([file_path])
                await embeddings_service.delete_document_chunks(stack_id, embedding_id)
                logger.info("Cleaned up storage and embeddings after database failure")
            except:
                pass
                
            raise HTTPException(
                status_code=500,
                detail=f"Failed to save document metadata: {str(e)}"
            )
        
        logger.info(f"=== DOCUMENT UPLOAD COMPLETED SUCCESSFULLY ===")
        logger.info(f"Document ID: {document.get('id')}")
        logger.info(f"File: {file.filename}")
        logger.info(f"Chunks: {len(chunks)}")
        
        # Return DocumentResponse
        return DocumentResponse(**document)
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"Unexpected error during upload: {str(e)}")
        logger.exception("Full traceback:")
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error during upload: {str(e)}"
        )

        
 