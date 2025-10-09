#!/usr/bin/env python3
"""
SyferStack Backend startup script.
"""
import asyncio
import uvicorn
from app.core.config import settings

if __name__ == "__main__":
    print(f"🚀 Starting {settings.app_name} v{settings.app_version}")
    print(f"🌍 Environment: {'Development' if settings.is_development else 'Production'}")
    print(f"🔗 Server: http://{settings.host}:{settings.port}")
    
    if settings.debug:
        print("📚 API Docs: http://localhost:8000/docs")
        print("📖 ReDoc: http://localhost:8000/redoc")
    
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
        log_level="debug" if settings.debug else "info",
        access_log=settings.debug,
    )