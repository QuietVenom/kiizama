from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.api.deps import get_current_active_superuser
from app.features.ig_scrapper.schemas import InstagramPostSchema
from app.features.openai.classes import (
    IG_OPENAI_REQUEST,
    InstagramProfileAnalysisInput,
    deserialize_profile_analysis_response,
    serialize_profile_analysis_payload,
)
from app.features.openai.classes.openai_system_prompts import (
    SYSTEM_PROMPT_IG_OPENAI_REQUEST,
)
from app.features.openai.service import OpenAIService

router = APIRouter(prefix="/openai", tags=["openai"])


class InstagramProfileInput(BaseModel):
    username: str
    biography: str | None = None
    follower_count: int | None = None
    posts: list[InstagramPostSchema] = Field(default_factory=list)


class InstagramAIRequest(BaseModel):
    """Payload for testing the Instagram OpenAI classifier."""

    profiles: list[InstagramProfileInput]


class InstagramAIResult(BaseModel):
    username: str
    categories: list[str]
    roles: list[str]


class InstagramAIResponse(BaseModel):
    results: list[InstagramAIResult]


@router.post(
    "/instagram",
    response_model=InstagramAIResponse,
    dependencies=[Depends(get_current_active_superuser)],
)
async def run_instagram_ai(request: InstagramAIRequest):
    if not request.profiles:
        raise HTTPException(status_code=400, detail="profiles cannot be empty")

    # Build batch payload from validated profiles
    inputs = [
        InstagramProfileAnalysisInput(**profile.model_dump())
        for profile in request.profiles
    ]
    serialized = serialize_profile_analysis_payload(inputs)

    req_kwargs = IG_OPENAI_REQUEST.to_function_kwargs()
    req_kwargs["prompt"] = json.dumps(serialized, ensure_ascii=False)
    # Ensure system prompt present (template already sets it, but keep explicit)
    req_kwargs["system_prompt"] = req_kwargs.get(
        "system_prompt", SYSTEM_PROMPT_IG_OPENAI_REQUEST
    )

    service = OpenAIService()
    try:
        text = await asyncio.to_thread(
            service.execute,
            "create_response",
            function_kwargs=req_kwargs,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=502, detail=f"OpenAI call failed: {exc}"
        ) from exc

    try:
        if not text or not str(text).strip():
            raise ValueError("Empty response text")
        raw = json.loads(text)
        parsed = deserialize_profile_analysis_response(raw)
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"Failed to parse OpenAI response: {exc}"
        ) from exc

    return InstagramAIResponse(
        results=[
            InstagramAIResult(
                username=res.username,
                categories=res.categories,
                roles=res.roles,
            )
            for res in parsed.results
        ]
    )


__all__ = ["router"]
