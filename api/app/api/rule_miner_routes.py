from typing import List
from fastapi import APIRouter
from pydantic import BaseModel

from app.models.applications import Application
from app.models.rule_miner_models import RuleMinerResponse
from app.services.rule_miner import mine_rules

router = APIRouter(prefix="/rules", tags=["rules"])


class RuleMinerRequest(BaseModel):
    applications: List[Application]


@router.post("/mine", response_model=RuleMinerResponse)
def mine_rules_endpoint(req: RuleMinerRequest) -> RuleMinerResponse:
    return mine_rules(req.applications)