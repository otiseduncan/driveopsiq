"""
AI-related routes and endpoints.
"""
from typing import Any, List, Optional, AsyncGenerator
import asyncio
import json

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.security import get_current_user, RateLimiter
from app.models.user import User
from app.schemas.ai import (
    ChatRequest,
    ChatResponse,
    ChatMessage,
    ChatRole,
    CompletionRequest,
    CompletionResponse,
    EmbeddingRequest,
    EmbeddingResponse,
    ModelInfo,
    AIProvider,
)

router = APIRouter()

# Rate limiter for AI endpoints (10 requests per minute per user)
ai_rate_limiter = RateLimiter(calls=10, period=60)


async def get_openai_client():
    """Get OpenAI client instance."""
    if not settings.openai_api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="OpenAI API not configured",
        )
    
    try:
        import openai
        return openai.AsyncOpenAI(api_key=settings.openai_api_key)
    except ImportError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="OpenAI library not installed",
        )


async def get_anthropic_client():
    """Get Anthropic client instance."""
    if not settings.anthropic_api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Anthropic API not configured",
        )
    
    try:
        import anthropic
        return anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    except ImportError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Anthropic library not installed",
        )


def check_rate_limit(user_id: int):
    """Check rate limit for user."""
    if not ai_rate_limiter.is_allowed(str(user_id)):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Please try again later.",
        )


@router.get("/models", response_model=List[ModelInfo])
async def get_available_models() -> Any:
    """
    Get list of available AI models.
    
    Returns:
        List[ModelInfo]: Available models information
    """
    models = []
    
    # OpenAI models
    if settings.openai_api_key:
        models.extend([
            ModelInfo(
                id="gpt-4",
                name="GPT-4",
                provider=AIProvider.OPENAI,
                description="Most capable GPT-4 model",
                max_tokens=8192,
                supports_streaming=True,
                pricing={"input_tokens_per_1k": 0.03, "output_tokens_per_1k": 0.06}
            ),
            ModelInfo(
                id="gpt-4-turbo-preview",
                name="GPT-4 Turbo",
                provider=AIProvider.OPENAI,
                description="Latest GPT-4 Turbo model with improved capabilities",
                max_tokens=128000,
                supports_streaming=True,
                pricing={"input_tokens_per_1k": 0.01, "output_tokens_per_1k": 0.03}
            ),
            ModelInfo(
                id="gpt-3.5-turbo",
                name="GPT-3.5 Turbo",
                provider=AIProvider.OPENAI,
                description="Fast and efficient model for most tasks",
                max_tokens=16385,
                supports_streaming=True,
                pricing={"input_tokens_per_1k": 0.001, "output_tokens_per_1k": 0.002}
            ),
        ])
    
    # Anthropic models
    if settings.anthropic_api_key:
        models.extend([
            ModelInfo(
                id="claude-3-opus-20240229",
                name="Claude 3 Opus",
                provider=AIProvider.ANTHROPIC,
                description="Most capable Claude model",
                max_tokens=200000,
                supports_streaming=True,
                pricing={"input_tokens_per_1k": 0.015, "output_tokens_per_1k": 0.075}
            ),
            ModelInfo(
                id="claude-3-sonnet-20240229",
                name="Claude 3 Sonnet",
                provider=AIProvider.ANTHROPIC,
                description="Balanced Claude model",
                max_tokens=200000,
                supports_streaming=True,
                pricing={"input_tokens_per_1k": 0.003, "output_tokens_per_1k": 0.015}
            ),
            ModelInfo(
                id="claude-3-haiku-20240307",
                name="Claude 3 Haiku",
                provider=AIProvider.ANTHROPIC,
                description="Fast and efficient Claude model",
                max_tokens=200000,
                supports_streaming=True,
                pricing={"input_tokens_per_1k": 0.00025, "output_tokens_per_1k": 0.00125}
            ),
        ])
    
    if not models:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No AI providers configured",
        )
    
    return models


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Chat with AI model.
    
    Args:
        request: Chat request data
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        ChatResponse: AI response
        
    Raises:
        HTTPException: If model not available or rate limit exceeded
    """
    check_rate_limit(current_user.id)
    
    try:
        if request.model.startswith("gpt"):
            # OpenAI chat completion
            client = await get_openai_client()
            
            # Convert messages to OpenAI format
            messages = [
                {"role": msg.role, "content": msg.content}
                for msg in request.messages
            ]
            
            response = await client.chat.completions.create(
                model=request.model,
                messages=messages,
                max_tokens=request.max_tokens,
                temperature=request.temperature,
                stream=False,
            )
            
            return ChatResponse(
                message=ChatMessage(
                    role=ChatRole.ASSISTANT,
                    content=response.choices[0].message.content,
                ),
                model=request.model,
                usage={
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens,
                },
            )
        
        elif request.model.startswith("claude"):
            # Anthropic chat completion
            client = await get_anthropic_client()
            
            # Convert messages to Anthropic format
            messages = []
            system_message = None
            
            for msg in request.messages:
                if msg.role == "system":
                    system_message = msg.content
                else:
                    messages.append({
                        "role": msg.role,
                        "content": msg.content,
                    })
            
            response = await client.messages.create(
                model=request.model,
                max_tokens=request.max_tokens or 1024,
                temperature=request.temperature,
                system=system_message,
                messages=messages,
            )
            
            return ChatResponse(
                message=ChatMessage(
                    role=ChatRole.ASSISTANT,
                    content=response.content[0].text,
                ),
                model=request.model,
                usage={
                    "prompt_tokens": response.usage.input_tokens,
                    "completion_tokens": response.usage.output_tokens,
                    "total_tokens": response.usage.input_tokens + response.usage.output_tokens,
                },
            )
        
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported model: {request.model}",
            )
    
    except Exception as e:
        if isinstance(e, HTTPException):
            raise
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AI service error: {str(e)}",
        )


@router.post("/chat/stream")
async def chat_stream(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """
    Stream chat with AI model.
    
    Args:
        request: Chat request data
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        StreamingResponse: Streaming AI response
        
    Raises:
        HTTPException: If model not available or rate limit exceeded
    """
    check_rate_limit(current_user.id)
    
    async def generate_stream() -> AsyncGenerator[str, None]:
        try:
            if request.model.startswith("gpt"):
                # OpenAI streaming
                client = await get_openai_client()
                
                messages = [
                    {"role": msg.role, "content": msg.content}
                    for msg in request.messages
                ]
                
                stream = await client.chat.completions.create(
                    model=request.model,
                    messages=messages,
                    max_tokens=request.max_tokens,
                    temperature=request.temperature,
                    stream=True,
                )
                
                async for chunk in stream:
                    if chunk.choices[0].delta.content:
                        yield f"data: {json.dumps({'content': chunk.choices[0].delta.content})}\n\n"
                
                yield "data: [DONE]\n\n"
            
            elif request.model.startswith("claude"):
                # Anthropic streaming
                client = await get_anthropic_client()
                
                messages = []
                system_message = None
                
                for msg in request.messages:
                    if msg.role == "system":
                        system_message = msg.content
                    else:
                        messages.append({
                            "role": msg.role,
                            "content": msg.content,
                        })
                
                async with client.messages.stream(
                    model=request.model,
                    max_tokens=request.max_tokens or 1024,
                    temperature=request.temperature,
                    system=system_message,
                    messages=messages,
                ) as stream:
                    async for text in stream.text_stream:
                        yield f"data: {json.dumps({'content': text})}\n\n"
                
                yield "data: [DONE]\n\n"
            
            else:
                yield f"data: {json.dumps({'error': f'Unsupported model: {request.model}'})}\n\n"
        
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
    
    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


@router.post("/completion", response_model=CompletionResponse)
async def completion(
    request: CompletionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Generate text completion.
    
    Args:
        request: Completion request data
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        CompletionResponse: Completion response
        
    Raises:
        HTTPException: If model not available or rate limit exceeded
    """
    check_rate_limit(current_user.id)
    
    try:
        if request.model.startswith("gpt"):
            client = await get_openai_client()
            
            response = await client.completions.create(
                model=request.model,
                prompt=request.prompt,
                max_tokens=request.max_tokens,
                temperature=request.temperature,
            )
            
            return CompletionResponse(
                text=response.choices[0].text,
                model=request.model,
                usage={
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens,
                },
            )
        
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Completion not supported for model: {request.model}",
            )
    
    except Exception as e:
        if isinstance(e, HTTPException):
            raise
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AI service error: {str(e)}",
        )


@router.post("/embeddings", response_model=EmbeddingResponse)
async def create_embeddings(
    request: EmbeddingRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Generate embeddings for text.
    
    Args:
        request: Embedding request data
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        EmbeddingResponse: Embedding response
        
    Raises:
        HTTPException: If model not available or rate limit exceeded
    """
    check_rate_limit(current_user.id)
    
    try:
        client = await get_openai_client()
        
        response = await client.embeddings.create(
            model=request.model or "text-embedding-ada-002",
            input=request.input,
        )
        
        return EmbeddingResponse(
            embeddings=[data.embedding for data in response.data],
            model=response.model,
            usage={
                "prompt_tokens": response.usage.prompt_tokens,
                "total_tokens": response.usage.total_tokens,
            },
        )
    
    except Exception as e:
        if isinstance(e, HTTPException):
            raise
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AI service error: {str(e)}",
        )