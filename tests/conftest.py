"""
Pytest fixtures and configuration for tests.
"""
import asyncio
import pytest
import pytest_asyncio
from typing import AsyncGenerator, Generator
from uuid import uuid4
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool
from httpx import AsyncClient, ASGITransport

from src.config.database import Base
from src.main import app
from src.domains.flights.models import Flight
from src.domains.seats.models import Seat, SeatStatus
from src.domains.passengers.models import Passenger
from src.domains.checkin.models import CheckIn, CheckInStatus
from src.domains.baggage.models import Baggage


# Test database URL (SQLite for simplicity)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def test_engine():
    """Create a test database engine."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session."""
    async_session = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )

    async with async_session() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture(scope="function")
async def client(test_engine) -> AsyncGenerator[AsyncClient, None]:
    """Create a test HTTP client."""
    # Override the database session dependency
    async def override_get_db():
        async_session = async_sessionmaker(
            test_engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        async with async_session() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    # Mock Redis
    mock_redis = AsyncMock()
    mock_redis.get = AsyncMock(return_value=None)
    mock_redis.setex = AsyncMock(return_value=True)
    mock_redis.delete = AsyncMock(return_value=1)
    mock_redis.scan_iter = AsyncMock(return_value=iter([]))
    mock_redis.ping = AsyncMock(return_value=True)
    mock_redis.pipeline = MagicMock(return_value=mock_redis)
    mock_redis.zremrangebyscore = AsyncMock(return_value=0)
    mock_redis.zadd = AsyncMock(return_value=1)
    mock_redis.zcard = AsyncMock(return_value=1)
    mock_redis.expire = AsyncMock(return_value=True)
    mock_redis.execute = AsyncMock(return_value=[0, 1, 1, True])

    app.state.redis = mock_redis

    from src.config.database import get_db_session
    app.dependency_overrides[get_db_session] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()


# Factory fixtures for creating test data

@pytest_asyncio.fixture
async def sample_flight(db_session: AsyncSession) -> Flight:
    """Create a sample flight."""
    flight = Flight(
        id=uuid4(),
        flight_number="SH101",
        departure_airport="JFK",
        arrival_airport="LAX",
        departure_time=datetime.utcnow() + timedelta(hours=6),
        arrival_time=datetime.utcnow() + timedelta(hours=12),
        aircraft_type="Boeing 737",
        created_at=datetime.utcnow()
    )
    db_session.add(flight)
    await db_session.flush()
    return flight


@pytest_asyncio.fixture
async def sample_passenger(db_session: AsyncSession) -> Passenger:
    """Create a sample passenger."""
    passenger = Passenger(
        id=uuid4(),
        first_name="John",
        last_name="Doe",
        email=f"john.doe.{uuid4().hex[:6]}@example.com",
        phone="+1234567890",
        booking_reference="ABC123",
        created_at=datetime.utcnow()
    )
    db_session.add(passenger)
    await db_session.flush()
    return passenger


@pytest_asyncio.fixture
async def sample_seat(db_session: AsyncSession, sample_flight: Flight) -> Seat:
    """Create a sample seat."""
    seat = Seat(
        id=uuid4(),
        flight_id=sample_flight.id,
        seat_number="12A",
        seat_class="economy",
        status=SeatStatus.AVAILABLE.value,
        created_at=datetime.utcnow()
    )
    db_session.add(seat)
    await db_session.flush()
    return seat


@pytest_asyncio.fixture
async def held_seat(
    db_session: AsyncSession,
    sample_flight: Flight,
    sample_passenger: Passenger
) -> Seat:
    """Create a seat that is held."""
    seat = Seat(
        id=uuid4(),
        flight_id=sample_flight.id,
        seat_number="12B",
        seat_class="economy",
        status=SeatStatus.HELD.value,
        held_by=sample_passenger.id,
        held_at=datetime.utcnow(),
        hold_expires_at=datetime.utcnow() + timedelta(seconds=120),
        created_at=datetime.utcnow()
    )
    db_session.add(seat)
    await db_session.flush()
    return seat


@pytest_asyncio.fixture
async def confirmed_seat(
    db_session: AsyncSession,
    sample_flight: Flight,
    sample_passenger: Passenger
) -> Seat:
    """Create a seat that is confirmed."""
    seat = Seat(
        id=uuid4(),
        flight_id=sample_flight.id,
        seat_number="12C",
        seat_class="economy",
        status=SeatStatus.CONFIRMED.value,
        confirmed_by=sample_passenger.id,
        confirmed_at=datetime.utcnow(),
        created_at=datetime.utcnow()
    )
    db_session.add(seat)
    await db_session.flush()
    return seat


@pytest_asyncio.fixture
async def sample_checkin(
    db_session: AsyncSession,
    sample_flight: Flight,
    sample_passenger: Passenger,
    held_seat: Seat
) -> CheckIn:
    """Create a sample check-in."""
    checkin = CheckIn(
        id=uuid4(),
        passenger_id=sample_passenger.id,
        flight_id=sample_flight.id,
        seat_id=held_seat.id,
        status=CheckInStatus.IN_PROGRESS.value,
        started_at=datetime.utcnow(),
        created_at=datetime.utcnow()
    )
    db_session.add(checkin)
    await db_session.flush()
    return checkin


@pytest_asyncio.fixture
async def checkin_with_baggage(
    db_session: AsyncSession,
    sample_checkin: CheckIn
) -> tuple[CheckIn, Baggage]:
    """Create a check-in with baggage."""
    baggage = Baggage(
        id=uuid4(),
        checkin_id=sample_checkin.id,
        weight_kg=20.0,
        excess_fee=0.0,
        fee_paid=False,
        created_at=datetime.utcnow()
    )
    db_session.add(baggage)
    await db_session.flush()
    await db_session.refresh(sample_checkin)
    return sample_checkin, baggage


@pytest_asyncio.fixture
async def flight_with_seats(db_session: AsyncSession) -> tuple[Flight, list[Seat]]:
    """Create a flight with multiple seats."""
    flight = Flight(
        id=uuid4(),
        flight_number="SH202",
        departure_airport="LAX",
        arrival_airport="ORD",
        departure_time=datetime.utcnow() + timedelta(hours=8),
        arrival_time=datetime.utcnow() + timedelta(hours=12),
        aircraft_type="Airbus A320",
        created_at=datetime.utcnow()
    )
    db_session.add(flight)
    await db_session.flush()

    seats = []
    for row in range(1, 4):
        for col in ["A", "B", "C"]:
            seat = Seat(
                id=uuid4(),
                flight_id=flight.id,
                seat_number=f"{row}{col}",
                seat_class="economy",
                status=SeatStatus.AVAILABLE.value,
                created_at=datetime.utcnow()
            )
            db_session.add(seat)
            seats.append(seat)

    await db_session.flush()
    return flight, seats

