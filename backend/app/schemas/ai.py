"""
AI-related Pydantic schemas for request/response validation.
"""
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field


class AIProvider(str, Enum):
    """Supported AI providers."""
    
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    HUGGINGFACE = "huggingface"
    COHERE = "cohere"


class ChatRole(str, Enum):
    """Chat message roles."""
    
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


class ChatMessage(BaseModel):
    """Schema for chat messages."""
    
    role: ChatRole = Field(..., description="Message role")
    content: str = Field(..., description="Message content")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "role": "user",
                "content": "Hello, how can you help me today?",
            }
        }
    }


class ChatRequest(BaseModel):
    """Schema for chat completion request."""
    
    model: str = Field(..., description="AI model to use")
    messages: List[ChatMessage] = Field(..., min_length=1, description="List of chat messages")
    temperature: Optional[float] = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description="Sampling temperature (0.0 to 2.0)",
    )
    max_tokens: Optional[int] = Field(
        default=None,
        ge=1,
        le=32000,
        description="Maximum number of tokens to generate",
    )
    stream: bool = Field(default=False, description="Whether to stream the response")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "model": "gpt-4",
                "messages": [
                    {"role": "user", "content": "What is the capital of France?"}
                ],
                "temperature": 0.7,
                "max_tokens": 150,
                "stream": False,
            }
        }
    }


class ChatResponse(BaseModel):
    """Schema for chat completion response."""
    
    message: ChatMessage = Field(..., description="AI response message")
    model: str = Field(..., description="AI model used")
    usage: Optional[Dict[str, int]] = Field(None, description="Token usage information")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "message": {
                    "role": "assistant",
                    "content": "The capital of France is Paris.",
                },
                "model": "gpt-4",
                "usage": {
                    "prompt_tokens": 15,
                    "completion_tokens": 8,
                    "total_tokens": 23,
                },
            }
        }
    }


class CompletionRequest(BaseModel):
    """Schema for text completion request."""
    
    model: str = Field(..., description="AI model to use")
    prompt: str = Field(..., description="Text prompt")
    temperature: Optional[float] = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description="Sampling temperature (0.0 to 2.0)",
    )
    max_tokens: Optional[int] = Field(
        default=100,
        ge=1,
        le=32000,
        description="Maximum number of tokens to generate",
    )
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "model": "gpt-3.5-turbo-instruct",
                "prompt": "The future of AI is",
                "temperature": 0.8,
                "max_tokens": 100,
            }
        }
    }


class CompletionResponse(BaseModel):
    """Schema for text completion response."""
    
    text: str = Field(..., description="Generated text")
    model: str = Field(..., description="AI model used")
    usage: Optional[Dict[str, int]] = Field(None, description="Token usage information")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "text": "The future of AI is bright and full of possibilities...",
                "model": "gpt-3.5-turbo-instruct",
                "usage": {
                    "prompt_tokens": 5,
                    "completion_tokens": 95,
                    "total_tokens": 100,
                },
            }
        }
    }


class EmbeddingRequest(BaseModel):
    """Schema for embedding generation request."""
    
    input: Union[str, List[str]] = Field(..., description="Text input to embed")
    model: Optional[str] = Field(
        default="text-embedding-ada-002",
        description="Embedding model to use",
    )
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "input": "This is a sample text to embed",
                "model": "text-embedding-ada-002",
            }
        }
    }


class EmbeddingResponse(BaseModel):
    """Schema for embedding generation response."""
    
    embeddings: List[List[float]] = Field(..., description="Generated embeddings")
    model: str = Field(..., description="Embedding model used")
    usage: Optional[Dict[str, int]] = Field(None, description="Token usage information")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "embeddings": [[0.1, 0.2, 0.3, "..."]],
                "model": "text-embedding-ada-002",
                "usage": {
                    "prompt_tokens": 8,
                    "total_tokens": 8,
                },
            }
        }
    }


class ModelInfo(BaseModel):
    """Schema for AI model information."""
    
    id: str = Field(..., description="Model ID")
    name: str = Field(..., description="Model display name")
    provider: AIProvider = Field(..., description="AI provider")
    description: Optional[str] = Field(None, description="Model description")
    max_tokens: Optional[int] = Field(None, description="Maximum context length")
    supports_streaming: bool = Field(default=False, description="Whether model supports streaming")
    pricing: Optional[Dict[str, float]] = Field(None, description="Pricing information")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "gpt-4",
                "name": "GPT-4",
                "provider": "openai",
                "description": "Most capable GPT-4 model",
                "max_tokens": 8192,
                "supports_streaming": True,
                "pricing": {
                    "input_tokens_per_1k": 0.03,
                    "output_tokens_per_1k": 0.06,
                },
            }
        }
    }


class ImageGenerationRequest(BaseModel):
    """Schema for image generation request."""
    
    prompt: str = Field(..., description="Image generation prompt")
    model: Optional[str] = Field(default="dall-e-3", description="Image generation model")
    size: Optional[str] = Field(
        default="1024x1024",
        description="Image size",
        pattern=r"^(256x256|512x512|1024x1024|1792x1024|1024x1792)$",
    )
    quality: Optional[str] = Field(
        default="standard",
        description="Image quality",
        pattern=r"^(standard|hd)$",
    )
    n: Optional[int] = Field(default=1, ge=1, le=4, description="Number of images to generate")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "prompt": "A beautiful sunset over mountains",
                "model": "dall-e-3",
                "size": "1024x1024",
                "quality": "standard",
                "n": 1,
            }
        }
    }


class ImageGenerationResponse(BaseModel):
    """Schema for image generation response."""
    
    images: List[str] = Field(..., description="Generated image URLs")
    model: str = Field(..., description="Image generation model used")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "images": ["https://example.com/generated_image.png"],
                "model": "dall-e-3",
            }
        }
    }


class ConversationHistory(BaseModel):
    """Schema for conversation history."""
    
    id: str = Field(..., description="Conversation ID")
    title: Optional[str] = Field(None, description="Conversation title")
    messages: List[ChatMessage] = Field(..., description="Conversation messages")
    model: str = Field(..., description="AI model used")
    created_at: str = Field(..., description="Creation timestamp")
    updated_at: str = Field(..., description="Last update timestamp")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "conv_123456",
                "title": "Discussion about AI",
                "messages": [
                    {"role": "user", "content": "What is artificial intelligence?"},
                    {"role": "assistant", "content": "Artificial intelligence (AI) is..."},
                ],
                "model": "gpt-4",
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:05:00Z",
            }
        }
    }