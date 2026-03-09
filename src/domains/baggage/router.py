"""
Baggage API router.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from src.config.database import get_db_session
from src.domains.baggage.service import BaggageService
from src.domains.baggage.schemas import AddBaggageRequest, BaggageResponse, BaggageListResponse

router = APIRouter(tags=["Baggage"])


@router.post("/checkin/{checkin_id}/baggage", response_model=BaggageListResponse, status_code=201)
async def add_baggage(
    checkin_id: UUID,
    request_body: AddBaggageRequest,
    session: AsyncSession = Depends(get_db_session)
):
    """
    Add baggage to a check-in.

    Maximum allowed weight is 25kg. If total baggage weight exceeds this limit,
    an excess fee will be calculated and the check-in status will change to
    WAITING_FOR_PAYMENT.

    Excess fee: $10 per kg over the limit.
    """
    service = BaggageService(session)
    return await service.add_baggage(checkin_id, request_body.weight_kg)


@router.get("/checkin/{checkin_id}/baggage", response_model=BaggageListResponse)
async def get_baggage(
    checkin_id: UUID,
    session: AsyncSession = Depends(get_db_session)
):
    """
    Get all baggage for a check-in.
    """
    service = BaggageService(session)
    return await service.get_baggage(checkin_id)

