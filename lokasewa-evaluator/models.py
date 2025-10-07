# AI Model Configuration
# Change model names here to switch models across all agents

class AIModels:
    """
    Central configuration for all AI models used in the system.
    Change model names here to switch providers/models across all agents.
    """
    
    # OCR Agent Models
    OCR_PRIMARY = "gemini-2.5-pro"  # Google AI Studio
    OCR_FALLBACK = "google/gemini-2.5-pro"  # OpenRouter fallback
    
    # Ideal Answer Generator
    IDEAL_ANSWER = "openai/gpt-oss-120b"  # OpenRouter GPT OSS 120B
    
    # Pro Agent (Student Advocate)
    PRO_AGENT = "x-ai/grok-4-fast"  # OpenRouter Grok 4 Fast
    
    # Cons Agent (Constructive Critic) 
    CONS_AGENT = "x-ai/grok-4-fast"  # OpenRouter Grok 4 Fast
    
    # Synthesizer Agent (Final Evaluator)
    SYNTHESIZER = "openai/gpt-oss-20b"  # OpenRouter GPT OSS 20B


class ModelProviders:
    """
    API provider configurations
    """
    GOOGLE_AI_STUDIO = "google_ai_studio"
    OPENROUTER = "openrouter"


class ModelSettings:
    """
    Model-specific settings like temperature, max_tokens, etc.
    """
    
    # Default settings for all models
    DEFAULT_TEMPERATURE = 0.3
    DEFAULT_MAX_TOKENS = 4000
    
    # Model-specific overrides
    MODEL_CONFIGS = {
        # OCR needs lower temperature for accuracy
        AIModels.OCR_PRIMARY: {
            "temperature": 0.1,
            "max_tokens": 2000
        },
        AIModels.OCR_FALLBACK: {
            "temperature": 0.1, 
            "max_tokens": 2000
        },
        
        # Ideal Answer needs creativity
        AIModels.IDEAL_ANSWER: {
            "temperature": 0.4,
            "max_tokens": 3000
        },
        
        # Pro Agent - encouraging tone
        AIModels.PRO_AGENT: {
            "temperature": 0.3,
            "max_tokens": 2500
        },
        
        # Cons Agent - analytical
        AIModels.CONS_AGENT: {
            "temperature": 0.2,
            "max_tokens": 2500
        },
        
        # Synthesizer needs balance
        AIModels.SYNTHESIZER: {
            "temperature": 0.3,
            "max_tokens": 4000
        }
    }
    
    @classmethod
    def get_config(cls, model_name):
        """Get configuration for a specific model"""
        return cls.MODEL_CONFIGS.get(model_name, {
            "temperature": cls.DEFAULT_TEMPERATURE,
            "max_tokens": cls.DEFAULT_MAX_TOKENS
        })


# Easy model switching - change these if you want to test different models
def get_ocr_models():
    """Returns tuple of (primary_model, fallback_model) for OCR"""
    return AIModels.OCR_PRIMARY, AIModels.OCR_FALLBACK

def get_ideal_answer_model():
    """Returns model for ideal answer generation"""
    return AIModels.IDEAL_ANSWER

def get_debate_models():
    """Returns tuple of (pro_model, cons_model) for debate agents"""
    return AIModels.PRO_AGENT, AIModels.CONS_AGENT

def get_synthesizer_model():
    """Returns model for final synthesis"""
    return AIModels.SYNTHESIZER