from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator
from .logging_config import setup_json_logging
from .routers import health

setup_json_logging()
app = FastAPI(title="SyferStack API", version="1.0.0")

# Set up Prometheus instrumentation before adding routes
instrumentator = Instrumentator()
instrumentator.instrument(app).expose(app, include_in_schema=False)

# Include routers after instrumentation
app.include_router(health.router)
