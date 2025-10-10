import time, os
from fastapi import APIRouter
router = APIRouter(tags=["health"])
START_TIME = time.time()

@router.get("/health")
def health():
    return {
        "status": "ok",
        "service": "syferstack-backend",
        "version": os.getenv("APP_VERSION", "1.0.0"),
        "uptime": round(time.time() - START_TIME, 2),
    }