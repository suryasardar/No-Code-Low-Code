from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn
import os
from dotenv import load_dotenv

from api.routes import stack, workflow, documents, chat
from db.supabase import init_supabase

load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize Supabase connection
    await init_supabase()
    yield
    # Cleanup if needed

app = FastAPI(
    title="Intelligent Workflow Backend System",
    description="Backend system for visual workflow construction with LLMs and document processing",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure based on your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(stack.router, prefix="/api", tags=["stack"])
app.include_router(workflow.router, prefix="/api", tags=["workflow"])
app.include_router(documents.router, prefix="/api", tags=["documents"])
app.include_router(chat.router, prefix="/api", tags=["chat"])

@app.get("/")
async def root():
    return {"message": "Intelligent Workflow Backend System API", "status": "running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )