"""
LLM Model Handler
Handles text analysis using LM Studio or Transformers.
"""
import json
import aiohttp
from typing import Optional, Union
from abc import ABC, abstractmethod
from dataclasses import dataclass

from ..config import LM_STUDIO_HOST, LM_STUDIO_MODEL, PRODUCTION_MODEL, MODEL_MODE


# System prompt for text analysis
LLM_SYSTEM_PROMPT = """You are a news analysis assistant specialized in sentiment classification.

Analyze the provided news article and VLM image analysis results.
Respond in JSON format:

{
    "summary": "2-3 sentence summary of the article",
    "sentiment": -1,
    "sentiment_label": "negative",
    "keywords": ["keyword1", "keyword2", "keyword3"],
    "entities": {
        "countries": ["Country1"],
        "organizations": ["Org1"],
        "people": ["Person1"]
    },
    "category": "politics/economy/sports/technology/other",
    "relevance_to_topic": "high/medium/low"
}

Sentiment scoring:
- 1 = Positive (good news, achievements, progress)
- 0 = Neutral (factual reporting, no emotional bias)
- -1 = Negative (conflict, crisis, criticism, tragedy)

Guidelines:
- Consider both text content and image analysis
- Extract key entities mentioned
- Classify into appropriate category
- Be objective in sentiment assessment
- Focus on facts, not opinions

Output ONLY valid JSON, no additional text."""


@dataclass
class TextAnalysisResult:
    """Result from LLM analysis."""
    summary: str
    sentiment: int  # -1, 0, 1
    sentiment_label: str
    keywords: list
    entities: dict
    category: str
    relevance_to_topic: str
    error: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {
            'summary': self.summary,
            'sentiment': self.sentiment,
            'sentiment_label': self.sentiment_label,
            'keywords': self.keywords,
            'entities': self.entities,
            'category': self.category,
            'relevance_to_topic': self.relevance_to_topic,
            'error': self.error
        }


class BaseLLMHandler(ABC):
    """Abstract base class for LLM handlers."""
    
    @abstractmethod
    async def analyze_text(self, text: str, vlm_results: list = None) -> TextAnalysisResult:
        """Analyze text content."""
        pass
    
    @abstractmethod
    async def is_available(self) -> bool:
        """Check if the model is available."""
        pass


class LMStudioHandler(BaseLLMHandler):
    """
    Handler for LM Studio (local development).
    Uses OpenAI-compatible API.
    """
    
    def __init__(self):
        self.base_url = LM_STUDIO_HOST
        self.model = LM_STUDIO_MODEL
        print(f"[LLM] LM Studio handler initialized: {self.base_url}")
    
    async def is_available(self) -> bool:
        """Check if LM Studio is running."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/v1/models", timeout=5) as resp:
                    return resp.status == 200
        except:
            return False
    
    async def analyze_text(self, text: str, vlm_results: list = None) -> TextAnalysisResult:
        """
        Analyze text using LM Studio.
        
        Args:
            text: Article text content
            vlm_results: Optional list of VLM analysis results
        """
        try:
            # Build context with VLM results
            vlm_context = ""
            if vlm_results:
                vlm_context = "\n\nImage Analysis Results:\n"
                for i, result in enumerate(vlm_results):
                    vlm_context += f"Image {i+1}: {result.get('description', 'No description')}\n"
                    vlm_context += f"  - Objects: {', '.join(result.get('objects', []))}\n"
                    vlm_context += f"  - Sentiment: {result.get('sentiment', 'unknown')}\n"
            
            # Prepare message
            user_content = f"Analyze this news article:\n\n{text[:4000]}{vlm_context}"
            
            messages = [
                {"role": "system", "content": LLM_SYSTEM_PROMPT},
                {"role": "user", "content": user_content}
            ]
            
            # Call LM Studio API
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/v1/chat/completions",
                    json={
                        "model": self.model,
                        "messages": messages,
                        "max_tokens": 800,
                        "temperature": 0.3
                    },
                    timeout=aiohttp.ClientTimeout(total=180)
                ) as resp:
                    if resp.status != 200:
                        error_text = await resp.text()
                        return self._error_result(f"API error: {error_text}")
                    
                    result = await resp.json()
            
            # Parse response
            content = result['choices'][0]['message']['content']
            return self._parse_response(content)
                
        except Exception as e:
            return self._error_result(str(e))
    
    def _parse_response(self, content: str) -> TextAnalysisResult:
        """Parse JSON response from model."""
        try:
            # Find JSON in response
            start = content.find('{')
            end = content.rfind('}') + 1
            if start >= 0 and end > start:
                parsed = json.loads(content[start:end])
                return TextAnalysisResult(
                    summary=parsed.get('summary', ''),
                    sentiment=parsed.get('sentiment', 0),
                    sentiment_label=parsed.get('sentiment_label', 'neutral'),
                    keywords=parsed.get('keywords', []),
                    entities=parsed.get('entities', {}),
                    category=parsed.get('category', 'other'),
                    relevance_to_topic=parsed.get('relevance_to_topic', 'medium')
                )
        except json.JSONDecodeError:
            pass
        
        # Fallback if parsing fails
        return TextAnalysisResult(
            summary=content[:200],
            sentiment=0, sentiment_label="neutral",
            keywords=[], entities={},
            category="other", relevance_to_topic="medium"
        )
    
    def _error_result(self, error: str) -> TextAnalysisResult:
        """Create error result."""
        return TextAnalysisResult(
            summary="", sentiment=0, sentiment_label="neutral",
            keywords=[], entities={}, category="other",
            relevance_to_topic="low", error=error
        )


class TransformersHandler(BaseLLMHandler):
    """
    Handler for Hugging Face Transformers (production).
    """
    
    def __init__(self):
        self.model = None
        self.tokenizer = None
        self.model_name = PRODUCTION_MODEL
        self._loaded = False
        print(f"[LLM] Transformers handler initialized (model not loaded yet)")
    
    def load_model(self):
        """Load model into memory."""
        if self._loaded:
            return
        
        try:
            from transformers import AutoModelForCausalLM, AutoTokenizer
            import torch
            
            device = "cuda" if torch.cuda.is_available() else "cpu"
            print(f"[LLM] Loading model on {device}...")
            
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_name,
                torch_dtype=torch.float16 if device == "cuda" else torch.float32,
                device_map="auto"
            )
            
            self._loaded = True
            print(f"[LLM] Model loaded: {self.model_name}")
            
        except Exception as e:
            print(f"[LLM] Failed to load model: {e}")
            raise
    
    async def is_available(self) -> bool:
        """Check if model is loaded."""
        return self._loaded
    
    async def analyze_text(self, text: str, vlm_results: list = None) -> TextAnalysisResult:
        """Analyze text using Transformers."""
        if not self._loaded:
            self.load_model()
        
        try:
            import torch
            
            # Build prompt
            vlm_context = ""
            if vlm_results:
                vlm_context = "\n\nImage Analysis Results:\n"
                for i, result in enumerate(vlm_results):
                    vlm_context += f"Image {i+1}: {result.get('description', '')}\n"
            
            prompt = f"{LLM_SYSTEM_PROMPT}\n\nAnalyze this news article:\n\n{text[:4000]}{vlm_context}"
            
            inputs = self.tokenizer(prompt, return_tensors="pt").to(self.model.device)
            
            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    max_new_tokens=800,
                    do_sample=True,
                    temperature=0.3,
                    pad_token_id=self.tokenizer.eos_token_id
                )
            
            response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            
            # Extract just the generated part
            response = response[len(prompt):]
            
            return self._parse_response(response)
            
        except Exception as e:
            return self._error_result(str(e))
    
    def _parse_response(self, content: str) -> TextAnalysisResult:
        """Parse JSON response."""
        try:
            start = content.find('{')
            end = content.rfind('}') + 1
            if start >= 0 and end > start:
                parsed = json.loads(content[start:end])
                return TextAnalysisResult(
                    summary=parsed.get('summary', ''),
                    sentiment=parsed.get('sentiment', 0),
                    sentiment_label=parsed.get('sentiment_label', 'neutral'),
                    keywords=parsed.get('keywords', []),
                    entities=parsed.get('entities', {}),
                    category=parsed.get('category', 'other'),
                    relevance_to_topic=parsed.get('relevance_to_topic', 'medium')
                )
        except:
            pass
        
        return TextAnalysisResult(
            summary=content[:200], sentiment=0, sentiment_label="neutral",
            keywords=[], entities={}, category="other", relevance_to_topic="medium"
        )
    
    def _error_result(self, error: str) -> TextAnalysisResult:
        return TextAnalysisResult(
            summary="", sentiment=0, sentiment_label="neutral",
            keywords=[], entities={}, category="other",
            relevance_to_topic="low", error=error
        )


def get_llm_handler() -> BaseLLMHandler:
    """Factory function to get appropriate LLM handler."""
    if MODEL_MODE == 'transformers':
        return TransformersHandler()
    return LMStudioHandler()
