from fastapi import APIRouter, HTTPException, Query
from app.models.summarize_models import SummarizeRequest, SummarizeResponse
from app.services.summarize_service import summarize_text

router = APIRouter(prefix="/summarize", tags=["summarize"])


@router.post("", response_model=SummarizeResponse)
def summarize(
    request: SummarizeRequest,
    provider: str = Query("openai", pattern="^(openai|lmstudio)$"),
    lmstudio_model: str | None = Query(None, description="Required if provider=lmstudio"),
) -> SummarizeResponse:
    if not request.text or not request.text.strip():
        raise HTTPException(status_code=400, detail="Text must not be empty")

    try:
        summary = summarize_text(
            text=request.text,
            provider=provider,  # type: ignore[arg-type]
            lmstudio_model=lmstudio_model,
        )
    except Exception as ex:
        raise HTTPException(status_code=500, detail=str(ex))

    return SummarizeResponse(summary=summary)


