"""
API client utilities for connecting to different AI services using LangChain
"""

import logging
import asyncio
import aiohttp
from typing import Dict, Any, Optional
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from config import Config
from models import ModelSettings
from schemas import APIResponse

logger = logging.getLogger(__name__)


class LangChainClientFactory:
    """
    Factory for creating LangChain LLM clients with proper configuration
    """
    
    @staticmethod
    def create_google_genai_client(model: str = "gemini-2.5-pro", **kwargs) -> ChatGoogleGenerativeAI:
        """
        Create Google Generative AI client using LangChain
        
        Args:
            model: Model name
            **kwargs: Additional configuration
            
        Returns:
            ChatGoogleGenerativeAI client
        """
        model_config = ModelSettings.get_config(model)
        
        # Note: Gemini model names in langchain-google-genai use different format
        # gemini-2.5-pro is correct for vision capabilities
        return ChatGoogleGenerativeAI(
            model=model,
            google_api_key=Config.GOOGLE_AI_STUDIO_API_KEY,
            temperature=model_config.get("temperature", 0.1),
            max_tokens=model_config.get("max_tokens", 4000),
            timeout=Config.API_TIMEOUT,
            max_retries=2,
            **kwargs
        )
    
    @staticmethod
    def create_openrouter_client(model: str = "x-ai/grok-4-fast", **kwargs) -> ChatOpenAI:
        """
        Create OpenRouter client using LangChain's OpenAI-compatible interface
        
        Args:
            model: Model name
            **kwargs: Additional configuration
            
        Returns:
            ChatOpenAI client configured for OpenRouter
        """
        model_config = ModelSettings.get_config(model)
        
        return ChatOpenAI(
            model=model,
            openai_api_key=Config.OPENROUTER_API_KEY,
            openai_api_base=Config.OPENROUTER_BASE_URL,
            temperature=model_config.get("temperature", 0.3),
            max_tokens=model_config.get("max_tokens", 4000),
            timeout=Config.API_TIMEOUT,
            max_retries=2,
            default_headers={
                "HTTP-Referer": "https://localhost:7860",
                "X-Title": "Lokasewa Evaluator"
            },
            **kwargs
        )


class UnifiedLLMClient:
    """
    Unified client that provides LangChain LLMs for all agents
    """
    
    def __init__(self):
        self.factory = LangChainClientFactory()
    
    async def get_ocr_llm(self) -> ChatGoogleGenerativeAI:
        """Get LLM for OCR (Gemini with vision)"""
        from models import get_ocr_models
        primary_model, _ = get_ocr_models()
        return self.factory.create_google_genai_client(primary_model)
    
    async def get_ideal_answer_llm(self) -> ChatOpenAI:
        """Get LLM for ideal answer generation"""
        from models import get_ideal_answer_model
        model = get_ideal_answer_model()
        return self.factory.create_openrouter_client(model)
    
    async def get_pro_agent_llm(self) -> ChatOpenAI:
        """Get LLM for pro agent"""
        from models import get_debate_models
        pro_model, _ = get_debate_models()
        return self.factory.create_openrouter_client(pro_model)
    
    async def get_cons_agent_llm(self) -> ChatOpenAI:
        """Get LLM for cons agent"""
        from models import get_debate_models
        _, cons_model = get_debate_models()
        return self.factory.create_openrouter_client(cons_model)
    
    async def get_synthesizer_llm(self) -> ChatOpenAI:
        """Get LLM for synthesizer"""
        from models import get_synthesizer_model
        model = get_synthesizer_model()
        return self.factory.create_openrouter_client(model)


# Global client instance
llm_client = UnifiedLLMClient()


# Convenience functions for backward compatibility
async def call_ocr_model(prompt: str, image_data: str) -> APIResponse:
    """
    Call OCR model using LangChain
    
    Args:
        prompt: Text prompt
        image_data: Base64 encoded image
        
    Returns:
        APIResponse with results
    """
    try:
        llm = await llm_client.get_ocr_llm()
        
        # Create message with image
        message = HumanMessage(
            content=[
                {"type": "text", "text": prompt},
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{image_data}"}
                }
            ]
        )
        
        logger.info(f"OCR: Calling Gemini with prompt ({len(prompt)} chars) and image ({len(image_data)} chars)")
        response = await llm.ainvoke([message])
        logger.info(f"OCR: Gemini response received ({len(response.content)} chars)")
        
        # Check if response is empty or too short
        if not response.content or len(response.content.strip()) < 5:
            logger.warning(f"OCR: Gemini returned very short/empty response: '{response.content}'")
            return APIResponse(
                success=False,
                error=f"Gemini returned insufficient text (length: {len(response.content if response.content else 0)}). The image may be unclear, too low quality, or contain no readable text.",
                api_source="google_ai_studio"
            )
        
        return APIResponse(
            success=True,
            data={"content": response.content, "raw_response": response},
            tokens_used=response.response_metadata.get("token_usage", {}).get("total_tokens", 0),
            api_source="google_ai_studio"
        )
    except Exception as e:
        logger.error(f"OCR model error: {str(e)}", exc_info=True)
        return APIResponse(
            success=False,
            error=f"OCR failed: {str(e)}",
            api_source="google_ai_studio"
        )


async def call_ideal_answer_model(prompt: str) -> APIResponse:
    """Call ideal answer model using LangChain"""
    try:
        llm = await llm_client.get_ideal_answer_llm()
        response = await llm.ainvoke(prompt)
        
        return APIResponse(
            success=True,
            data={"content": response.content, "raw_response": response},
            tokens_used=response.response_metadata.get("token_usage", {}).get("total_tokens", 0),
            api_source="openrouter"
        )
    except Exception as e:
        logger.error(f"Ideal answer model error: {str(e)}")
        return APIResponse(
            success=False,
            error=str(e),
            api_source="openrouter"
        )


async def call_pro_agent_model(prompt: str) -> APIResponse:
    """Call pro agent model using LangChain"""
    try:
        llm = await llm_client.get_pro_agent_llm()
        response = await llm.ainvoke(prompt)
        
        return APIResponse(
            success=True,
            data={"content": response.content, "raw_response": response},
            tokens_used=response.response_metadata.get("token_usage", {}).get("total_tokens", 0),
            api_source="openrouter"
        )
    except Exception as e:
        logger.error(f"Pro agent model error: {str(e)}")
        return APIResponse(
            success=False,
            error=str(e),
            api_source="openrouter"
        )


async def call_cons_agent_model(prompt: str) -> APIResponse:
    """Call cons agent model using LangChain"""
    try:
        llm = await llm_client.get_cons_agent_llm()
        response = await llm.ainvoke(prompt)
        
        return APIResponse(
            success=True,
            data={"content": response.content, "raw_response": response},
            tokens_used=response.response_metadata.get("token_usage", {}).get("total_tokens", 0),
            api_source="openrouter"
        )
    except Exception as e:
        logger.error(f"Cons agent model error: {str(e)}")
        return APIResponse(
            success=False,
            error=str(e),
            api_source="openrouter"
        )


async def call_synthesizer_model(prompt: str) -> APIResponse:
    """Call synthesizer model using LangChain"""
    try:
        llm = await llm_client.get_synthesizer_llm()
        response = await llm.ainvoke(prompt)
        
        return APIResponse(
            success=True,
            data={"content": response.content, "raw_response": response},
            tokens_used=response.response_metadata.get("token_usage", {}).get("total_tokens", 0),
            api_source="openrouter"
        )
    except Exception as e:
        logger.error(f"Synthesizer model error: {str(e)}")
        return APIResponse(
            success=False,
            error=str(e),
            api_source="openrouter"
        )


async def get_openrouter_generation_cost(generation_id: str, max_retries: int = 3, retry_delay: float = 2.0) -> Dict[str, Any]:
    """
    Query OpenRouter's generation endpoint to get actual cost and usage stats
    
    Note: OpenRouter may take a few seconds to make generation data available,
    so we retry with delays if we get a 404.
    
    Args:
        generation_id: The generation ID returned from OpenRouter API response
        max_retries: Maximum number of retry attempts for 404 responses
        retry_delay: Seconds to wait between retries
        
    Returns:
        Dictionary with cost_usd, native_tokens_prompt, native_tokens_completion, etc.
    """
    try:
        url = f"https://openrouter.ai/api/v1/generation?id={generation_id}"
        headers = {
            "Authorization": f"Bearer {Config.OPENROUTER_API_KEY}"
        }
        
        last_error = None
        
        for attempt in range(max_retries):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                        if resp.status == 200:
                            result = await resp.json()
                            data = result.get("data", {})
                            
                            cost_usd = data.get("total_cost", 0.0)
                            cost_npr = cost_usd * Config.USD_TO_NPR_RATE
                            
                            logger.info(f"Generation {generation_id}: ${cost_usd:.6f} USD = रू {cost_npr:.4f} NPR")
                            
                            return {
                                "success": True,
                                "generation_id": generation_id,
                                "cost_usd": cost_usd,
                                "cost_npr": cost_npr,
                                "native_tokens_prompt": data.get("native_tokens_prompt", 0),
                                "native_tokens_completion": data.get("native_tokens_completion", 0),
                                "model": data.get("model", ""),
                                "generation_time": data.get("generation_time", 0),
                            }
                        elif resp.status == 404 and attempt < max_retries - 1:
                            # 404 might mean data not yet available, retry after delay
                            logger.debug(f"Generation {generation_id} not found (attempt {attempt + 1}/{max_retries}), retrying in {retry_delay}s...")
                            await asyncio.sleep(retry_delay)
                            last_error = f"HTTP 404 (not yet available)"
                            continue
                        else:
                            last_error = f"HTTP {resp.status}"
                            logger.warning(f"Failed to fetch cost for {generation_id}: {last_error}")
                            break
                            
            except asyncio.TimeoutError:
                last_error = "Request timeout"
                if attempt < max_retries - 1:
                    logger.debug(f"Timeout fetching {generation_id} (attempt {attempt + 1}/{max_retries}), retrying...")
                    await asyncio.sleep(retry_delay)
                    continue
                break
        
        # All retries failed
        return {
                        "success": False,
                        "generation_id": generation_id,
                        "cost_usd": 0.0,
                        "cost_npr": 0.0,
                        "error": f"HTTP {resp.status}"
                    }
                    
    except Exception as e:
        logger.error(f"Error fetching OpenRouter cost for {generation_id}: {e}")
        return {
            "success": False,
            "generation_id": generation_id,
            "cost_usd": 0.0,
            "cost_npr": 0.0,
            "error": str(e)
        }


def extract_generation_id(response) -> Optional[str]:
    """
    Extract generation ID from LangChain response object
    
    Args:
        response: LangChain response object
        
    Returns:
        Generation ID string or None (gen-XXXXXXXXX format)
    """
    try:
        # LangChain ChatOpenAI response has response_metadata with 'id'
        # NOTE: We want 'id' (starts with 'gen-'), NOT 'system_fingerprint' (starts with 'fp_')
        if hasattr(response, 'response_metadata'):
            metadata = response.response_metadata
            
            # Check 'id' field first - this is the actual generation ID (gen-XXXXX)
            gen_id = metadata.get('id')
            if gen_id and gen_id.startswith('gen-'):
                return gen_id
            
            # Fallback to system_fingerprint only if it looks like a gen ID
            fingerprint = metadata.get('system_fingerprint')
            if fingerprint and fingerprint.startswith('gen-'):
                return fingerprint
        
        # Also check id attribute directly
        if hasattr(response, 'id'):
            response_id = response.id
            if response_id and response_id.startswith('gen-'):
                return response_id
            
        logger.warning(f"No valid generation ID found in response (needs to start with 'gen-')")
        return None
    except Exception as e:
        logger.warning(f"Failed to extract generation ID: {e}")
        return None