import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions
import openai
import google.generativeai as genai
import os
from typing import List, Dict, Optional, Tuple
import uuid
import asyncio
import httpx

class EmbeddingsService:
    def __init__(self):
        self.chroma_client = None
        self.collections = {}
        self.initialize_chroma()
    
    def initialize_chroma(self):
        """Initialize ChromaDB client with better error handling"""
        try:
            # Use persistent client for production
            chroma_host = os.getenv("CHROMADB_HOST", "localhost")
            chroma_port = int(os.getenv("CHROMADB_PORT", "8001"))
            
            # Try to connect to ChromaDB server, fallback to persistent local
            try:
                self.chroma_client = chromadb.HttpClient(
                    host=chroma_host,
                    port=chroma_port,
                    settings=Settings(anonymized_telemetry=False)
                )
                # Test connection
                self.chroma_client.heartbeat()
                print("✅ Connected to ChromaDB server")
            except Exception as server_error:
                print(f"⚠️ ChromaDB server connection failed: {server_error}")
                # Fallback to persistent local client
                self.chroma_client = chromadb.PersistentClient(
                    path="./chroma_data",
                    settings=Settings(anonymized_telemetry=False)
                )
                print("✅ Using local ChromaDB persistent client")
        except Exception as e:
            print(f"❌ ChromaDB initialization failed: {e}")
            raise RuntimeError(f"Failed to initialize ChromaDB: {e}")
    
    def get_collection(self, stack_id: str) -> chromadb.Collection:
        """Get or create collection for a stack with better naming"""
        collection_name = f"stack_{stack_id.replace('-', '_')}"
        
        if collection_name not in self.collections:
            try:
                # Try to get existing collection
                collection = self.chroma_client.get_collection(collection_name)
                print(f"📁 Retrieved existing collection: {collection_name}")
            except:
                # Create new collection with metadata
                collection = self.chroma_client.create_collection(
                    name=collection_name,
                    metadata={
                        "stack_id": stack_id,
                        "created_by": "embeddings_service",
                        "version": "2.0"
                    }
                )
                print(f"📁 Created new collection: {collection_name}")
            
            self.collections[collection_name] = collection
        
        return self.collections[collection_name]
    
    async def generate_openai_embeddings(self, texts: List[str], api_key: str, 
                                       model: str = "text-embedding-3-large") -> List[List[float]]:
        """Generate embeddings using OpenAI with better error handling"""
        if not texts:
            return []
            
        client = openai.AsyncOpenAI(api_key=api_key)
        
        try:
            # Process in batches to avoid rate limits
            batch_size = 100  # OpenAI limit
            all_embeddings = []
            
            for i in range(0, len(texts), batch_size):
                batch = texts[i:i + batch_size]
                print(f"🔄 Processing OpenAI embedding batch {i//batch_size + 1}/{(len(texts) + batch_size - 1)//batch_size}")
                
                response = await client.embeddings.create(
                    input=batch,
                    model=model
                )
                
                batch_embeddings = [embedding.embedding for embedding in response.data]
                all_embeddings.extend(batch_embeddings)
                
                # Small delay to respect rate limits
                if len(texts) > batch_size:
                    await asyncio.sleep(0.1)
            
            print(f"✅ Generated {len(all_embeddings)} OpenAI embeddings")
            return all_embeddings
            
        except Exception as e:
            print(f"❌ OpenAI embedding error: {e}")
            raise ValueError(f"Failed to generate OpenAI embeddings: {e}")
    
    async def generate_gemini_embeddings(self, texts: List[str], api_key: str,
                                       model: str = "models/embedding-001") -> List[List[float]]:
        """Generate embeddings using Google Gemini with better rate limiting"""
        if not texts:
            return []
            
        genai.configure(api_key=api_key)
        
        try:
            embeddings = []
            total_texts = len(texts)
            
            for i, text in enumerate(texts):
                if i > 0 and i % 10 == 0:  # Progress update every 10 embeddings
                    print(f"🔄 Gemini embedding progress: {i}/{total_texts}")
                
                try:
                    result = genai.embed_content(
                        model=model,
                        content=text,
                        task_type="retrieval_document"
                    )
                    embeddings.append(result['embedding'])
                    
                    # Rate limiting for Gemini (15 requests per minute)
                    if i > 0 and i % 10 == 0:  # Every 10 requests
                        await asyncio.sleep(1)  # 1 second delay
                        
                except Exception as single_error:
                    print(f"⚠️ Failed to embed text {i}: {single_error}")
                    # Use a zero vector as fallback
                    fallback_embedding = [0.0] * 768  # Standard embedding size
                    embeddings.append(fallback_embedding)
            
            print(f"✅ Generated {len(embeddings)} Gemini embeddings")
            return embeddings
            
        except Exception as e:
            print(f"❌ Gemini embedding error: {e}")
            raise ValueError(f"Failed to generate Gemini embeddings: {e}")
    
    async def embed_documents(self, stack_id: str, chunks: List[Dict], 
                            api_key: str, model: str = "text-embedding-3-large") -> str:
        """Embed document chunks and store in ChromaDB with better processing"""
        if not chunks:
            print("⚠️ No chunks provided for embedding")
            return ""
        
        collection = self.get_collection(stack_id)
        
        # Generate a unique embedding ID for this document/batch
        embedding_id = str(uuid.uuid4())
        
        # Extract texts and prepare metadata
        texts = []
        metadatas = []
        ids = []
        
        for chunk in chunks:
            # Get text content (handle multiple possible field names)
            text_content = chunk.get("text", chunk.get("content", ""))
            if not text_content or not text_content.strip():
                continue
                
            texts.append(text_content)
            
            # Prepare metadata with embedding_id for easy deletion
            chunk_metadata = chunk.get("metadata", {}).copy()
            chunk_metadata["embedding_id"] = embedding_id
            chunk_metadata["text_length"] = len(text_content)
            chunk_metadata["word_count"] = len(text_content.split())
            metadatas.append(chunk_metadata)
            
            ids.append(chunk.get("id", str(uuid.uuid4())))
        
        if not texts:
            print("⚠️ No valid text content found in chunks")
            return ""
        
        try:
            print(f"🚀 Starting embedding process for {len(texts)} chunks")
            print(f"📊 Model: {model}, API Key type: {'Gemini' if api_key.startswith('AIzaSy') else 'OpenAI'}")
            
            # Generate embeddings based on model type
            if model.startswith("text-embedding"):
                embeddings = await self.generate_openai_embeddings(texts, api_key, model)
            elif model.startswith("models/embedding"):
                embeddings = await self.generate_gemini_embeddings(texts, api_key, model)
            else:
                raise ValueError(f"Unsupported embedding model: {model}")
            
            if len(embeddings) != len(texts):
                raise ValueError(f"Embedding count mismatch: {len(embeddings)} embeddings for {len(texts)} texts")
            
            # Store in ChromaDB
            print(f"💾 Storing {len(embeddings)} embeddings in ChromaDB...")
            collection.add(
                embeddings=embeddings,
                documents=texts,
                metadatas=metadatas,
                ids=ids
            )
            
            print(f"✅ Successfully embedded {len(chunks)} chunks with embedding_id: {embedding_id}")
            
            # Verify storage
            stored_count = collection.count()
            print(f"📊 Total chunks in collection: {stored_count}")
            
            return embedding_id
            
        except Exception as e:
            print(f"❌ Failed to embed documents: {e}")
            raise ValueError(f"Failed to embed documents: {e}")
    
    async def search_similar_chunks(self, stack_id: str, query: str, 
                                  api_key: str, model: str = "text-embedding-3-large",
                                  top_k: int = 5, similarity_threshold: float = 0.5) -> List[Dict]:
        """Search for similar chunks with improved formatting and filtering"""
        collection = self.get_collection(stack_id)
        
        # Check if collection has any data
        collection_count = collection.count()
        if collection_count == 0:
            print(f"⚠️ No embeddings found in collection for stack {stack_id}")
            return []
        
        print(f"🔍 Searching {collection_count} chunks with query: '{query[:50]}...'")
        
        try:
            # Generate query embedding
            if model.startswith("text-embedding"):
                query_embeddings = await self.generate_openai_embeddings([query], api_key, model)
            elif model.startswith("models/embedding"):
                query_embeddings = await self.generate_gemini_embeddings([query], api_key, model)
            else:
                raise ValueError(f"Unsupported embedding model: {model}")
            
            if not query_embeddings:
                raise ValueError("Failed to generate query embedding")
                
            query_embedding = query_embeddings[0]
            
            # Search similar chunks with increased top_k to allow for filtering
            search_k = min(top_k * 2, collection_count)  # Search more than needed
            
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=search_k,
                include=["documents", "metadatas", "distances"]
            )
            
            # Format and filter results
            chunks = []
            if results["documents"] and results["documents"][0]:
                print(f"📊 Found {len(results['documents'][0])} raw results")
                
                for i, (doc, metadata, distance) in enumerate(zip(
                    results["documents"][0],
                    results["metadatas"][0], 
                    results["distances"][0]
                )):
                    # Convert distance to similarity score (ChromaDB uses L2 distance)
                    # Better similarity calculation
                    similarity_score = max(0.0, 1.0 / (1.0 + distance))
                    # similarity_score = max(0.0, 1.0 - (distance / 2.0))

                    print(f"  Result {i+1}: similarity={similarity_score:.3f}, distance={distance:.3f}")
                    
                    if similarity_score >= similarity_threshold:
                        chunk_data = {
                            "id": results["ids"][0][i],
                            "text": doc,                    # Primary field
                            "content": doc,                # Compatibility field  
                            "source": metadata.get("file_name", "Document"),
                            "metadata": metadata,
                            "similarity_score": similarity_score,
                            "score": similarity_score,     # Compatibility field
                            "distance": distance,
                            "section": metadata.get("section_type", "unknown"),
                            "technical": metadata.get("contains_technical_terms", False)
                        }
                        chunks.append(chunk_data)
            
            # Sort by similarity score (highest first) and limit to top_k
            chunks = sorted(chunks, key=lambda x: x["similarity_score"], reverse=True)[:top_k]
            
            print(f"✅ Returning {len(chunks)} chunks after filtering (threshold: {similarity_threshold})")
            
            # Debug: Print chunk summary
            if chunks:
                print("📄 Chunk summary:")
                for i, chunk in enumerate(chunks):
                    section = chunk.get("section", "unknown")
                    technical = chunk.get("technical", False)
                    score = chunk.get("similarity_score", 0)
                    preview = chunk.get("text", "")[:100]
                    print(f"  {i+1}. [{section}] {'(Tech)' if technical else ''} Score:{score:.3f} - {preview}...")
            
            return chunks
            
        except Exception as e:
            print(f"❌ Failed to search chunks: {e}")
            raise ValueError(f"Failed to search chunks: {e}")
    
    async def delete_document_chunks(self, stack_id: str, embedding_id: str) -> bool:
        """Delete document chunks by embedding ID with better error handling"""
        try:
            collection = self.get_collection(stack_id)
            
            # Find chunks with matching embedding_id in metadata
            print(f"🗑️ Looking for chunks with embedding_id: {embedding_id}")
            
            results = collection.get(include=["metadatas"])
            
            # Filter chunks that match the embedding_id
            chunks_to_delete = []
            if results["ids"]:
                for i, metadata in enumerate(results["metadatas"]):
                    if metadata and metadata.get("embedding_id") == embedding_id:
                        chunks_to_delete.append(results["ids"][i])
            
            if chunks_to_delete:
                collection.delete(ids=chunks_to_delete)
                print(f"✅ Deleted {len(chunks_to_delete)} chunks with embedding_id: {embedding_id}")
                return True
            else:
                print(f"⚠️ No chunks found with embedding_id: {embedding_id}")
                return False
            
        except Exception as e:
            print(f"❌ Failed to delete document chunks: {e}")
            raise ValueError(f"Failed to delete document chunks: {e}")
    
    def get_collection_stats(self, stack_id: str) -> Dict:
        """Get detailed statistics about a collection"""
        try:
            collection = self.get_collection(stack_id)
            count = collection.count()
            
            # Get sample of metadata to analyze
            if count > 0:
                sample_results = collection.get(
                    limit=min(10, count),
                    include=["metadatas"]
                )
                
                # Analyze sections and technical content
                sections = {}
                technical_count = 0
                
                for metadata in sample_results.get("metadatas", []):
                    if metadata:
                        section = metadata.get("section_type", "unknown")
                        sections[section] = sections.get(section, 0) + 1
                        if metadata.get("contains_technical_terms", False):
                            technical_count += 1
                
                return {
                    "total_chunks": count,
                    "collection_name": collection.name,
                    "stack_id": stack_id,
                    "sections_found": sections,
                    "technical_chunks_sample": technical_count,
                    "sample_size": len(sample_results.get("metadatas", []))
                }
            else:
                return {
                    "total_chunks": 0,
                    "collection_name": collection.name,
                    "stack_id": stack_id,
                    "sections_found": {},
                    "technical_chunks_sample": 0,
                    "sample_size": 0
                }
            
        except Exception as e:
            return {"error": str(e)}
    
    
    

# Global instance
embeddings_service = EmbeddingsService()

def get_embeddings_service() -> EmbeddingsService:
    """Get embeddings service instance"""
    return embeddings_service