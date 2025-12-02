from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from app.api.summarize_routes import router as summarize_router
from app.api.rule_miner_routes import router as rules_router
from app.api.rules_decide_routes import router as rules_decide_router
from app.api.applications_generate_routes import router as applications_generate_router

#from .models.summarize_models import SummarizeRequest, SummarizeResponse
#from .services.summarize_service import summarize_text

app = FastAPI(
    title = "AI Demo API",
    version = "0.1.0",
    description = "Minimal FastAPI app"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health_check() -> dict:
    """
    Simple healthcheck endpoint
    """
    return {"status": "ok"}

# Mount routers
app.include_router(summarize_router, prefix="/api")
app.include_router(rules_router, prefix="/api")
app.include_router(rules_decide_router, prefix="/api")
app.include_router(applications_generate_router, prefix="/api")

