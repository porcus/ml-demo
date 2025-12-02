from typing import List

from fastapi import APIRouter

from app.models.application_generation import GenerateApplicationsRequest
from app.models.applications import Application
from app.services.application_generator import generate_applications

router = APIRouter(prefix="/applications", tags=["applications"])


@router.post("/generate", response_model=List[Application])
def generate_applications_endpoint(req: GenerateApplicationsRequest) -> List[Application]:
    """
    Generate synthetic application data using either a Python-based generator
    or a local LLM (via LM Studio), depending on `generation_strategy`.
    """
    return generate_applications(req)
