from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.resources.router import router as resources_router
from app.resources.auth import router as auth_router

app = FastAPI(
    title="PasteurHub API",
    description="Intelligent vaccine recommendation system for travel health",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8501",
        "http://localhost:80",
        "http://127.0.0.1:8501",
        "*"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Auth endpoints at /auth/*
app.include_router(auth_router)

# Other endpoints stay under /resources/*
app.include_router(resources_router)


@app.get("/", include_in_schema=False)
def read_root():
    return {
        "message": "PasteurHub API is running",
        "docs": "/docs",
        "version": "1.0.0"
    }


@app.get("/health", include_in_schema=False)
def health_check():
    return {"status": "healthy"}
