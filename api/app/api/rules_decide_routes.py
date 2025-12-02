from typing import List
from fastapi import APIRouter
from pydantic import BaseModel

from app.models.applications import Application
from app.models.rules import RuleCandidate
from app.models.profiles import DecisionProfile
from app.models.decisions import ApplicationDecisionResult
from app.services.decision_engine import run_decision_engine

router = APIRouter(prefix="/rules", tags=["rules"])


class DecisionEngineRequest(BaseModel):
    applications: List[Application]
    profiles: List[DecisionProfile]


@router.post("/decide", response_model=List[ApplicationDecisionResult])
def decide(req: DecisionEngineRequest) -> List[ApplicationDecisionResult]:
    return run_decision_engine(
        applications=req.applications,
        profiles=req.profiles,
    )
