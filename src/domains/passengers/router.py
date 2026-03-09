"""
Passenger API router.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from src.config.database import get_db_session
from src.domains.passengers.models import Passenger
from src.domains.passengers.repository import PassengerRepository
from src.domains.passengers.schemas import PassengerCreate, PassengerResponse
from src.common.exceptions import PassengerNotFoundError

router = APIRouter(prefix="/passengers", tags=["Passengers"])


@router.post("", response_model=PassengerResponse, status_code=201)
async def create_passenger(
    passenger_data: PassengerCreate,
    session: AsyncSession = Depends(get_db_session)
):
    """
    Create a new passenger.
    """
    repository = PassengerRepository(session)
    passenger = Passenger(
        first_name=passenger_data.first_name,
        last_name=passenger_data.last_name,
        email=passenger_data.email,
        phone=passenger_data.phone,
        booking_reference=passenger_data.booking_reference
    )
    passenger = await repository.create(passenger)
    return PassengerResponse.model_validate(passenger)


@router.get("/{passenger_id}", response_model=PassengerResponse)
async def get_passenger(
    passenger_id: UUID,
    session: AsyncSession = Depends(get_db_session)
):
    """
    Get a passenger by ID.
    """
    repository = PassengerRepository(session)
    passenger = await repository.get_by_id(passenger_id)
    if not passenger:
        raise PassengerNotFoundError(str(passenger_id))
    return PassengerResponse.model_validate(passenger)

