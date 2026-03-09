"""
Flight API router.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from uuid import UUID
from datetime import date

from src.config.database import get_db_session
from src.domains.flights.service import FlightService
from src.domains.flights.schemas import FlightResponse, FlightListResponse

router = APIRouter(prefix="/flights", tags=["Flights"])


@router.get("", response_model=FlightListResponse)
async def list_flights(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    departure_date: Optional[date] = None,
    departure_airport: Optional[str] = None,
    session: AsyncSession = Depends(get_db_session)
):
    """
    List all flights with optional filters.
    """
    service = FlightService(session)
    flights, total = await service.get_flights(
        limit=limit,
        offset=offset,
        departure_date=departure_date,
        departure_airport=departure_airport
    )

    return FlightListResponse(
        flights=[FlightResponse.model_validate(f) for f in flights],
        total=total,
        limit=limit,
        offset=offset
    )


@router.get("/{flight_id}", response_model=FlightResponse)
async def get_flight(
    flight_id: UUID,
    session: AsyncSession = Depends(get_db_session)
):
    """
    Get a specific flight by ID.
    """
    service = FlightService(session)
    flight = await service.get_flight(flight_id)
    return FlightResponse.model_validate(flight)

