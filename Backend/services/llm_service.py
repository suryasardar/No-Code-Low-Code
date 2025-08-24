import openai
import google.generativeai as genai
from typing import List, Dict, Optional, AsyncGenerator
import asyncio
import json
# import re

class LLMService:
    def __init__(self):
        self.openai_models = [
            "gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"
        ]
        self.gemini_models = [
            "gemini-1.5-pro", "gemini-1.5-flash", "gemini-pro"
        ]
    
    def detect_api_key_type(self, api_key: str) -> str:
        """Detect API key type based on format"""
        if not api_key:
            return "unknown"
        
        # Google API keys start with AIzaSy
        if api_key.startswith("AIzaSy"):
            return "gemini"
        
        # OpenAI API keys start with sk-
        if api_key.startswith("sk-"):
            return "openai"
        
        # Default to openai for backward compatibility
        return "openai"
    
    async def generate_openai_response(self, messages: List[Dict], api_key: str,
                                     model: str = "gpt-4o-mini", temperature: float = 0.75,
                                     max_tokens: Optional[int] = None, stream: bool = False) -> str:
        """Generate response using OpenAI models"""
        client = openai.AsyncOpenAI(api_key=api_key)
        
        try:
            if stream:
                response = ""
                stream_response = await client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    stream=True
                )
                
                async for chunk in stream_response:
                    if chunk.choices[0].delta.content:
                        response += chunk.choices[0].delta.content
                
                return response
            else:
                response = await client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens
                )
                return response.choices[0].message.content
                
        except Exception as e:
            raise ValueError(f"OpenAI API error: {e}")
    
    async def generate_gemini_response(self, messages: List[Dict], api_key: str,
                                     model: str = "gemini-1.5-flash", temperature: float = 0.75) -> str:
        """Generate response using Gemini models"""
        genai.configure(api_key=api_key)
        
        try:
            # Convert messages to Gemini format
            gemini_messages = self.convert_to_gemini_format(messages)
            
            model_instance = genai.GenerativeModel(model)
            
            generation_config = genai.types.GenerationConfig(
                temperature=temperature,
                max_output_tokens=2048,
            )
            
            response = await model_instance.generate_content_async(
                gemini_messages,
                generation_config=generation_config
            )
            
            return response.text
            
        except Exception as e:
            raise ValueError(f"Gemini API error: {e}")
    
    def convert_to_gemini_format(self, messages: List[Dict]) -> List[Dict]:
        """Convert OpenAI message format to Gemini format"""
        gemini_messages = []
        
        for message in messages:
            role = message["role"]
            content = message["content"]
            
            if role == "system":
                # Gemini doesn't have system role, prepend to first user message
                continue
            elif role == "user":
                gemini_messages.append({
                    "role": "user",
                    "parts": [content]
                })
            elif role == "assistant":
                gemini_messages.append({
                    "role": "model",
                    "parts": [content]
                })
        
        # Add system message to first user message if exists
        system_messages = [m["content"] for m in messages if m["role"] == "system"]
        if system_messages and gemini_messages:
            system_prompt = "\n".join(system_messages)
            first_user_msg = gemini_messages[0]["parts"][0]
            gemini_messages[0]["parts"][0] = f"{system_prompt}\n\n{first_user_msg}"
        
        return gemini_messages
    
    async def generate_response(self, query: str, context: Optional[str] = None,
                              api_key: str = "", model: str = "gpt-4o-mini",
                              temperature: float = 0.75, system_prompt: str = "",
                              web_search_results: Optional[str] = None) -> str:
        """Generate response with context and web search results"""
        
        # Build system message
        if not system_prompt:
            system_prompt = "You are a helpful AI assistant."
        
        if web_search_results:
            system_prompt += f"\n\nYou have access to the following web search results:\n{web_search_results}"
        
        # Build user message
        user_message = query
        if context:
            user_message = f"Context from documents:\n{context}\n\nQuery: {query}"
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]
        
        # Detect API key type and choose appropriate service
        api_key_type = self.detect_api_key_type(api_key)
        
        # Override model selection based on API key type if auto-detection is needed
        if api_key_type == "gemini" and model in self.openai_models:
            # If we have a Gemini key but OpenAI model requested, use Gemini model
            model = "gemini-1.5-flash"
            print(f"🔄 Auto-switched to Gemini model due to Gemini API key")
        elif api_key_type == "openai" and model in self.gemini_models:
            # If we have OpenAI key but Gemini model requested, use OpenAI model
            model = "gpt-4o-mini"
            print(f"🔄 Auto-switched to OpenAI model due to OpenAI API key")
        
        # Generate response with appropriate service
        if api_key_type == "gemini" or model in self.gemini_models:
            return await self.generate_gemini_response(
                messages, api_key, model, temperature
            )
        else:
            return await self.generate_openai_response(
                messages, api_key, model, temperature
            )

# Global instance
llm_service = LLMService()

def get_llm_service() -> LLMService:
    """Get LLM service instance"""
    return llm_service