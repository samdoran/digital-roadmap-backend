from fastapi import FastAPI

from app.v1.endpoints import v1_router

# Initialize FastAPI app
app = FastAPI()

# Include the routers under versioned paths
app.include_router(v1_router, prefix="/v1")
