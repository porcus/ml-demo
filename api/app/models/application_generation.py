from pydantic import BaseModel, Field
from typing import Literal, Optional


class GenerateApplicationsRequest(BaseModel):
    total_count: int = Field(..., gt=0, le=1000)
    manual_count: int = Field(..., ge=0)
    manual_approved_count: int = Field(..., ge=0)
    generation_strategy: Literal["llm", "python"] = "llm"
    seed: Optional[int] = None

    def validate_counts(self) -> None:
        if self.manual_count > self.total_count:
            raise ValueError(
                f"manual_count ({self.manual_count}) cannot exceed total_count ({self.total_count})"
            )
        if self.manual_approved_count > self.manual_count:
            raise ValueError(
                f"manual_approved_count ({self.manual_approved_count}) cannot exceed manual_count ({self.manual_count})"
            )
