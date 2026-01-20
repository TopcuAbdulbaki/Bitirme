"""
VLM Model Handler
Handles image analysis using LM Studio or Transformers.
"""
import json
import base64
import aiohttp
from typing import Optional, Union
from abc import ABC, abstractmethod
from dataclasses import dataclass

from ..config import LM_STUDIO_HOST, LM_STUDIO_MODEL, PRODUCTION_MODEL, MODEL_MODE


# System prompt for image analysis
VLM_SYSTEM_PROMPT = """You are an image analysis assistant specialized in news media.

For each image provided, analyze and respond in JSON format:

{
    "description": "Brief description of what the image shows",
    "objects": ["list", "of", "detected", "objects"],
    "sentiment": "positive/negative/neutral",
    "relevance": "high/medium/low"
}

Guidelines:
- Focus on newsworthy elements (people, events, locations)
- Identify any text, logos, or symbols visible
- Assess emotional tone of the image
- Determine relevance to news content
- Be objective and factual

Output ONLY valid JSON, no additional text."""


@dataclass
class ImageAnalysisResult:
    """Result from VLM analysis."""
    minio_path: Optional[str]
    original_url: Optional[str]
    description: str
    objects: list
    sentiment: str
    relevance: str
    error: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {
            'minio_path': self.minio_path,
            'original_url': self.original_url,
            'description': self.description,
            'objects': self.objects,
            'sentiment': self.sentiment,
            'relevance': self.relevance,
            'error': self.error
        }


class BaseVLMHandler(ABC):
    """Abstract base class for VLM handlers."""
    
    @abstractmethod
    async def analyze_image(self, image_data: Union[bytes, str], context: str = "") -> ImageAnalysisResult:
        """Analyze a single image."""
        pass
    
    @abstractmethod
    async def is_available(self) -> bool:
        """Check if the model is available."""
        pass


class LMStudioHandler(BaseVLMHandler):
    """
    Handler for LM Studio (local development).
    Uses OpenAI-compatible API.
    """
    
    def __init__(self):
        self.base_url = LM_STUDIO_HOST
        self.model = LM_STUDIO_MODEL
        print(f"[VLM] LM Studio handler initialized: {self.base_url}")
    
    async def is_available(self) -> bool:
        """Check if LM Studio is running."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/v1/models", timeout=5) as resp:
                    return resp.status == 200
        except:
            return False
    
    async def analyze_image(self, image_data: Union[bytes, str], context: str = "") -> ImageAnalysisResult:
        """
        Analyze image using LM Studio.
        
        Args:
            image_data: Base64 encoded image or raw bytes
            context: Optional context about the news article
        """
        try:
            # Convert bytes to base64 if needed
            if isinstance(image_data, bytes):
                image_b64 = base64.b64encode(image_data).decode('utf-8')
            else:
                image_b64 = image_data
            
            # Prepare message with image
            messages = [
                {"role": "system", "content": VLM_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}
                        },
                        {
                            "type": "text",
                            "text": f"Analyze this news image. Context: {context}" if context else "Analyze this news image."
                        }
                    ]
                }
            ]
            
            # Call LM Studio API
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/v1/chat/completions",
                    json={
                        "model": self.model,
                        "messages": messages,
                        "max_tokens": 500,
                        "temperature": 0.3
                    },
                    timeout=aiohttp.ClientTimeout(total=90)
                ) as resp:
                    if resp.status != 200:
                        error_text = await resp.text()
                        return ImageAnalysisResult(
                            minio_path=None, original_url=None,
                            description="", objects=[], sentiment="neutral", relevance="low",
                            error=f"API error: {error_text}"
                        )
                    
                    result = await resp.json()
            
            # Parse response
            content = result['choices'][0]['message']['content']
            
            # Try to parse as JSON
            try:
                parsed = json.loads(content)
                return ImageAnalysisResult(
                    minio_path=None,
                    original_url=None,
                    description=parsed.get('description', ''),
                    objects=parsed.get('objects', []),
                    sentiment=parsed.get('sentiment', 'neutral'),
                    relevance=parsed.get('relevance', 'medium')
                )
            except json.JSONDecodeError:
                # If not valid JSON, use content as description
                return ImageAnalysisResult(
                    minio_path=None, original_url=None,
                    description=content[:500], objects=[], sentiment="neutral", relevance="medium"
                )
                
        except Exception as e:
            return ImageAnalysisResult(
                minio_path=None, original_url=None,
                description="", objects=[], sentiment="neutral", relevance="low",
                error=str(e)
            )


class TransformersHandler(BaseVLMHandler):
    """
    Handler for Hugging Face Transformers (production).
    Loads model locally on GPU.
    """
    
    def __init__(self):
        self.model = None
        self.processor = None
        self.model_name = PRODUCTION_MODEL
        self._loaded = False
        print(f"[VLM] Transformers handler initialized (model not loaded yet)")
    
    def load_model(self):
        """Load model into memory (call once at startup)."""
        if self._loaded:
            return
        
        try:
            from transformers import AutoModelForVision2Seq, AutoProcessor
            import torch
            
            device = "cuda" if torch.cuda.is_available() else "cpu"
            print(f"[VLM] Loading model on {device}...")
            
            # Use AutoModelForVision2Seq for Qwen2/Qwen3 VL compatibility
            self.model = AutoModelForVision2Seq.from_pretrained(
                self.model_name,
                dtype=torch.float16 if device == "cuda" else torch.float32,
                device_map="auto",
                trust_remote_code=True  # Required for Qwen3
            )
            self.processor = AutoProcessor.from_pretrained(
                self.model_name,
                trust_remote_code=True
            )
            
            self._loaded = True
            print(f"[VLM] Model loaded: {self.model_name}")
            
        except Exception as e:
            print(f"[VLM] Failed to load model: {e}")
            raise
    
    async def is_available(self) -> bool:
        """Check if model is loaded."""
        return self._loaded
    
    async def analyze_image(self, image_data: Union[bytes, str], context: str = "") -> ImageAnalysisResult:
        """Analyze image using Transformers."""
        if not self._loaded:
            self.load_model()
        
        try:
            from PIL import Image
            import io
            import torch
            
            # Convert to PIL Image
            if isinstance(image_data, bytes):
                image = Image.open(io.BytesIO(image_data))
            else:
                # Assume base64
                image_bytes = base64.b64decode(image_data)
                image = Image.open(io.BytesIO(image_bytes))
            
            # Prepare prompt
            prompt = f"{VLM_SYSTEM_PROMPT}\n\nAnalyze this news image. Context: {context}" if context else f"{VLM_SYSTEM_PROMPT}\n\nAnalyze this news image."
            
            # Process
            inputs = self.processor(
                text=prompt,
                images=image,
                return_tensors="pt"
            ).to(self.model.device)
            
            # Generate
            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    max_new_tokens=500,
                    do_sample=True,
                    temperature=0.3
                )
            
            response = self.processor.decode(outputs[0], skip_special_tokens=True)
            
            # Parse JSON from response
            try:
                # Find JSON in response
                start = response.find('{')
                end = response.rfind('}') + 1
                if start >= 0 and end > start:
                    parsed = json.loads(response[start:end])
                    return ImageAnalysisResult(
                        minio_path=None, original_url=None,
                        description=parsed.get('description', ''),
                        objects=parsed.get('objects', []),
                        sentiment=parsed.get('sentiment', 'neutral'),
                        relevance=parsed.get('relevance', 'medium')
                    )
            except:
                pass
            
            return ImageAnalysisResult(
                minio_path=None, original_url=None,
                description=response[:500], objects=[], sentiment="neutral", relevance="medium"
            )
            
        except Exception as e:
            return ImageAnalysisResult(
                minio_path=None, original_url=None,
                description="", objects=[], sentiment="neutral", relevance="low",
                error=str(e)
            )


def get_vlm_handler() -> BaseVLMHandler:
    """Factory function to get appropriate VLM handler."""
    if MODEL_MODE == 'transformers':
        return TransformersHandler()
    return LMStudioHandler()
