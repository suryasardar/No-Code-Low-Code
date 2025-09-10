import fitz  # PyMuPDF
import io
import uuid
from typing import List, Dict, Tuple
import re
from pathlib import Path
from langchain.text_splitter import RecursiveCharacterTextSplitter

class DocumentProcessor:
    def __init__(self):
        # Optimized text splitter for resumes and technical documents
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=400,  # Smaller chunks for better precision
            chunk_overlap=100,  # Good overlap to maintain context
            length_function=len,
            # Better separators for structured documents like resumes
            separators=["\n\n", "\n", ".", "!", "?", ";", ",", " ", ""]
        )
    
    async def extract_text_from_pdf(self, file_content: bytes, file_name: str) -> str:
        """Extract text from PDF file content with better OCR handling"""
        try:
            doc = fitz.open(stream=file_content, filetype="pdf")
            text_content = ""
            
            for page_num in range(doc.page_count):
                page = doc[page_num]
                
                # Try to get text first
                page_text = page.get_text()
                
                # If no text found, try OCR (for image-based PDFs)
                if not page_text.strip():
                    try:
                        # Get page as image and extract text
                        pix = page.get_pixmap()
                        img_data = pix.tobytes("png")
                        # Note: You might want to add OCR here if needed
                        # For now, we'll just note it as an image page
                        page_text = f"[Image content on page {page_num + 1} - text extraction may be incomplete]"
                    except:
                        page_text = f"[Unable to extract text from page {page_num + 1}]"
                
                text_content += f"\n=== PAGE {page_num + 1} ===\n"
                text_content += page_text
            
            doc.close()
            return text_content.strip()
        
        except Exception as e:
            raise ValueError(f"Failed to extract text from PDF {file_name}: {str(e)}")
    
    def clean_text(self, text: str) -> str:
        """Clean and normalize extracted text - optimized for resumes"""
        # Remove excessive whitespace but preserve document structure
        text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)  # Normalize multiple line breaks
        text = re.sub(r'[ \t]+', ' ', text)             # Normalize spaces and tabs
        text = re.sub(r' +\n', '\n', text)              # Remove trailing spaces
        
        # Improve page break handling
        text = re.sub(r'\n=== PAGE \d+ ===\n', '\n\n--- PAGE BREAK ---\n\n', text)
        
        # Preserve more characters for technical terms and special symbols
        # Keep: letters, numbers, spaces, punctuation, technical symbols
        text = re.sub(r'[^\w\s.,!?;:()\[\]{}"\'/\-+#&@%*=<>|~`^]', ' ', text)
        
        # Normalize common resume formatting
        text = text.replace('•', '- ')      # Convert bullets to dashes
        text = text.replace('◦', '- ')      # Convert sub-bullets
        text = text.replace('▪', '- ')      # Convert other bullets
        text = text.replace('→', ' -> ')    # Convert arrows
        text = text.replace('|', ' | ')     # Space out pipes
        
        # Fix common technical term issues
        text = re.sub(r'([a-z])([A-Z])', r'\1 \2', text)  # Add space between camelCase
        text = re.sub(r'(\w)\.([A-Z])', r'\1. \2', text)  # Fix missing spaces after periods
        
        # Remove excessive spaces again after transformations
        text = re.sub(r'  +', ' ', text)
        text = re.sub(r'\n +', '\n', text)
        text = re.sub(r' +\n', '\n', text)
        
        return text.strip()
    
    def create_chunks(self, text: str, metadata: Dict = None) -> List[Dict]:
        """Split text into chunks with enhanced metadata for better retrieval"""
        if not text:
            return []
        
        # Pre-process text to identify sections
        sections = self.identify_resume_sections(text)
        
        # Use LangChain to intelligently split text
        text_chunks = self.text_splitter.split_text(text)
        
        chunks = []
        total_chunks = len(text_chunks)
        
        for i, chunk_text in enumerate(text_chunks):
            chunk_text = chunk_text.strip()
            if not chunk_text:
                continue
                
            # Identify which section this chunk belongs to
            section_info = self.get_section_for_chunk(chunk_text, sections)
            
            # Create enhanced chunk metadata
            chunk_metadata = {
                "chunk_index": i,
                "chunk_size": len(chunk_text.split()),
                "character_count": len(chunk_text),
                "total_chunks": total_chunks,
                "section_type": section_info.get("section", "unknown"),
                "contains_technical_terms": self.contains_technical_terms(chunk_text),
                "word_density": len(chunk_text.split()) / len(chunk_text) if chunk_text else 0
            }
            
            # Add document metadata if provided
            if metadata:
                chunk_metadata.update(metadata)
            
            chunks.append({
                "id": str(uuid.uuid4()),
                "text": chunk_text,
                "content": chunk_text,  # Add both fields for compatibility
                "metadata": chunk_metadata
            })
        
        return chunks
    
    def identify_resume_sections(self, text: str) -> Dict[str, Dict]:
        """Identify different sections in a resume"""
        sections = {}
        
        # Common resume section patterns
        section_patterns = {
            "contact": r"(?i)(email|phone|address|linkedin|github)",
            "summary": r"(?i)(summary|profile|objective|about)",
            "experience": r"(?i)(experience|employment|work|career|position)",
            "education": r"(?i)(education|degree|university|college|school)",
            "skills": r"(?i)(skills|technologies|technical|competencies|tools|programming)",
            "projects": r"(?i)(projects|portfolio|work samples|applications)",
            "certifications": r"(?i)(certifications|certificates|licenses|credentials)",
            "awards": r"(?i)(awards|honors|achievements|recognition)"
        }
        
        lines = text.split('\n')
        current_section = "unknown"
        
        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue
                
            # Check if this line is a section header
            for section_name, pattern in section_patterns.items():
                if re.search(pattern, line) and len(line.split()) <= 5:
                    current_section = section_name
                    sections[current_section] = {
                        "start_line": i,
                        "header": line
                    }
                    break
        
        return sections
    
    def get_section_for_chunk(self, chunk_text: str, sections: Dict) -> Dict:
        """Determine which section a chunk belongs to"""
        # Simple heuristic based on content
        chunk_lower = chunk_text.lower()
        
        if any(term in chunk_lower for term in ['docker', 'kubernetes', 'aws', 'python', 'javascript', 'react', 'node', 'programming', 'development']):
            return {"section": "skills"}
        elif any(term in chunk_lower for term in ['university', 'degree', 'bachelor', 'master', 'phd', 'education']):
            return {"section": "education"}
        elif any(term in chunk_lower for term in ['worked', 'company', 'position', 'role', 'responsibilities']):
            return {"section": "experience"}
        elif any(term in chunk_lower for term in ['project', 'built', 'developed', 'created', 'implemented']):
            return {"section": "projects"}
        else:
            return {"section": "general"}
    
    def contains_technical_terms(self, text: str) -> bool:
        """Check if chunk contains technical terms"""
        technical_terms = [
            'python', 'javascript', 'java', 'react', 'node', 'docker', 'kubernetes',
            'aws', 'azure', 'gcp', 'nginx', 'apache', 'mysql', 'postgresql', 'mongodb',
            'redis', 'elasticsearch', 'git', 'github', 'gitlab', 'ci/cd', 'jenkins',
            'terraform', 'ansible', 'linux', 'ubuntu', 'centos', 'api', 'rest', 'graphql',
            'microservices', 'devops', 'cloud', 'serverless', 'lambda', 'ec2', 's3'
        ]
        
        text_lower = text.lower()
        return any(term in text_lower for term in technical_terms)
    
    async def process_document(self, file_content: bytes, file_name: str, 
                             stack_id: str) -> Tuple[str, List[Dict]]:
        """Process a document and return cleaned text and chunks"""
        try:
            print(f"🔄 Processing document: {file_name}")
            
            # Extract text from PDF
            raw_text = await self.extract_text_from_pdf(file_content, file_name)
            print(f"📄 Extracted {len(raw_text)} characters from PDF")
            
            # Clean the text
            clean_text = self.clean_text(raw_text)
            print(f"🧹 Cleaned text: {len(clean_text)} characters")
            
            # Extract key information for enhanced metadata
            doc_info = self.extract_key_information(clean_text)
            print(f"📊 Document stats: {doc_info['word_count']} words, {doc_info['paragraph_count']} paragraphs")
            
            # Create metadata for the document
            doc_metadata = {
                "file_name": file_name,
                "stack_id": stack_id,
                "total_characters": len(clean_text),
                "document_type": "pdf",
                "word_count": doc_info["word_count"],
                "paragraph_count": doc_info["paragraph_count"],
                "potential_title": doc_info.get("potential_title", ""),
                "processing_timestamp": str(uuid.uuid4())  # For tracking
            }
            
            # Create chunks using optimized text splitter
            chunks = self.create_chunks(clean_text, doc_metadata)
            print(f"✂️ Created {len(chunks)} chunks")
            
            # Debug: Print chunk info
            technical_chunks = sum(1 for chunk in chunks if chunk["metadata"].get("contains_technical_terms", False))
            print(f"🔧 Technical chunks: {technical_chunks}/{len(chunks)}")
            
            # Print sample chunks for debugging
            print("📝 Sample chunks:")
            for i, chunk in enumerate(chunks[:3]):
                content = chunk["text"][:150]
                section = chunk["metadata"].get("section_type", "unknown")
                technical = chunk["metadata"].get("contains_technical_terms", False)
                print(f"  Chunk {i+1} [{section}] {'(Technical)' if technical else ''}: {content}...")
            
            return clean_text, chunks
            
        except Exception as e:
            print(f"❌ Failed to process document {file_name}: {str(e)}")
            raise ValueError(f"Failed to process document {file_name}: {str(e)}")
    
    def extract_key_information(self, text: str) -> Dict:
        """Extract key information from text for metadata"""
        info = {
            "word_count": len(text.split()),
            "character_count": len(text),
            "paragraph_count": len([p for p in text.split('\n\n') if p.strip()]),
        }
        
        # Try to extract potential titles (first few meaningful lines)
        lines = [line.strip() for line in text.split('\n') if line.strip() and len(line.strip()) > 3]
        if lines:
            # Look for name-like patterns in first few lines
            for line in lines[:5]:
                if len(line.split()) <= 4 and any(c.isupper() for c in line):
                    info["potential_title"] = line[:100]
                    break
            else:
                info["potential_title"] = lines[0][:100]
        
        # Extract potential skills section
        skills_section = self.extract_skills_preview(text)
        if skills_section:
            info["skills_preview"] = skills_section
        
        return info
    
    def extract_skills_preview(self, text: str) -> str:
        """Extract a preview of the skills section"""
        text_lower = text.lower()
        
        # Look for skills section
        skills_indicators = ["skills", "technical skills", "technologies", "programming languages", "tools"]
        
        for indicator in skills_indicators:
            start_pos = text_lower.find(indicator)
            if start_pos != -1:
                # Extract ~300 characters after the skills indicator
                preview = text[start_pos:start_pos + 300]
                return preview.replace('\n', ' ').strip()
        
        return ""
    
     

# Global instance
document_processor = DocumentProcessor()

def get_document_processor() -> DocumentProcessor:
    """Get document processor instance"""
    return document_processor