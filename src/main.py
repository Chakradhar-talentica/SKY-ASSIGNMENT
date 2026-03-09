"""
SkyHigh Core - Digital Check-In System
Main FastAPI application entry point.
"""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import redis.asyncio as redis

from src.config.settings import get_settings
from src.config.database import init_db, close_db
from src.common.exceptions import SkyHighException
from src.common.middleware.rate_limiter import RateLimiterMiddleware

# Import routers
from src.domains.flights.router import router as flights_router
from src.domains.seats.router import router as seats_router
from src.domains.passengers.router import router as passengers_router
from src.domains.checkin.router import router as checkin_router
from src.domains.baggage.router import router as baggage_router
from src.domains.payments.router import router as payments_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan - startup and shutdown events."""
    # Startup
    logger.info("Starting SkyHigh Core API...")

    # Initialize database
    await init_db()
    logger.info("Database initialized")

    # Initialize Redis
    try:
        app.state.redis = redis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True
        )
        await app.state.redis.ping()
        logger.info("Redis connected")
    except Exception as e:
        logger.warning(f"Redis connection failed: {e}. Continuing without cache.")
        app.state.redis = None

    yield

    # Shutdown
    logger.info("Shutting down SkyHigh Core API...")

    # Close Redis
    if app.state.redis:
        await app.state.redis.close()
        logger.info("Redis connection closed")

    # Close database
    await close_db()
    logger.info("Database connection closed")


# Create FastAPI app
app = FastAPI(
    title="SkyHigh Core - Digital Check-In System",
    description="""
    Backend API for airline self-check-in system.
    
    ## Features
    - Seat selection with conflict-free booking
    - Time-bound seat holds (120 seconds)
    - Baggage validation with payment flow
    - High-performance seat map access
    
    ## Seat Lifecycle
    - **AVAILABLE**: Seat can be selected
    - **HELD**: Temporarily reserved (120 seconds)
    - **CONFIRMED**: Permanently assigned
    """,
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add rate limiting middleware
app.add_middleware(
    RateLimiterMiddleware,
    enabled=settings.rate_limit_enabled
)


# Exception handlers
@app.exception_handler(SkyHighException)
async def skyhigh_exception_handler(request: Request, exc: SkyHighException):
    """Handle custom SkyHigh exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details
            }
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions."""
    logger.exception(f"Unexpected error: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred",
                "details": {"error": str(exc)} if settings.debug else {}
            }
        }
    )


# Health check endpoint
@app.get("/health", tags=["Health"])
async def health_check(request: Request):
    """
    Health check endpoint.

    Returns the health status of the service and its dependencies.
    """
    health = {
        "status": "healthy",
        "database": "unknown",
        "redis": "unknown"
    }

    # Check database
    try:
        from src.config.database import engine
        from sqlalchemy import text
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        health["database"] = "connected"
    except Exception as e:
        health["database"] = "disconnected"
        health["status"] = "degraded"
        logger.error(f"Database health check failed: {e}")

    # Check Redis
    try:
        if request.app.state.redis:
            await request.app.state.redis.ping()
            health["redis"] = "connected"
        else:
            health["redis"] = "not configured"
    except Exception as e:
        health["redis"] = "disconnected"
        health["status"] = "degraded"
        logger.error(f"Redis health check failed: {e}")

    return health


# Admin endpoint for seeding demo data
@app.post("/api/v1/admin/seed", tags=["Admin"])
async def seed_demo_data(request: Request):
    """
    Seed the database with demo data.

    Creates sample flights, seats, and passengers for testing.
    """
    from src.config.database import async_session_factory
    from src.domains.flights.models import Flight
    from src.domains.seats.models import Seat, SeatStatus
    from src.domains.passengers.models import Passenger
    from datetime import datetime, timedelta
    import uuid

    async with async_session_factory() as session:
        try:
            # Create demo flights
            flights_data = [
                {
                    "flight_number": "SH101",
                    "departure_airport": "JFK",
                    "arrival_airport": "LAX",
                    "departure_time": datetime.utcnow() + timedelta(hours=6),
                    "arrival_time": datetime.utcnow() + timedelta(hours=12),
                    "aircraft_type": "Boeing 737"
                },
                {
                    "flight_number": "SH202",
                    "departure_airport": "LAX",
                    "arrival_airport": "ORD",
                    "departure_time": datetime.utcnow() + timedelta(hours=8),
                    "arrival_time": datetime.utcnow() + timedelta(hours=12),
                    "aircraft_type": "Airbus A320"
                },
                {
                    "flight_number": "SH303",
                    "departure_airport": "ORD",
                    "arrival_airport": "MIA",
                    "departure_time": datetime.utcnow() + timedelta(hours=10),
                    "arrival_time": datetime.utcnow() + timedelta(hours=14),
                    "aircraft_type": "Boeing 757"
                }
            ]

            flights_created = 0
            seats_created = 0

            for flight_data in flights_data:
                flight = Flight(**flight_data)
                session.add(flight)
                await session.flush()
                flights_created += 1

                # Create seats for each flight (6 rows, 6 seats per row)
                seat_classes = ["first", "business", "economy"]
                for row in range(1, 7):
                    seat_class = seat_classes[0] if row <= 1 else (seat_classes[1] if row <= 2 else seat_classes[2])
                    for col in ["A", "B", "C", "D", "E", "F"]:
                        seat = Seat(
                            flight_id=flight.id,
                            seat_number=f"{row}{col}",
                            seat_class=seat_class,
                            status=SeatStatus.AVAILABLE.value
                        )
                        session.add(seat)
                        seats_created += 1

            # Create demo passengers
            passengers_data = [
                {
                    "first_name": "John",
                    "last_name": "Doe",
                    "email": f"john.doe.{uuid.uuid4().hex[:6]}@example.com",
                    "phone": "+1234567890",
                    "booking_reference": "ABC123"
                },
                {
                    "first_name": "Jane",
                    "last_name": "Smith",
                    "email": f"jane.smith.{uuid.uuid4().hex[:6]}@example.com",
                    "phone": "+0987654321",
                    "booking_reference": "XYZ789"
                },
                {
                    "first_name": "Bob",
                    "last_name": "Wilson",
                    "email": f"bob.wilson.{uuid.uuid4().hex[:6]}@example.com",
                    "phone": "+1122334455",
                    "booking_reference": "DEF456"
                }
            ]

            passengers_created = 0
            for passenger_data in passengers_data:
                passenger = Passenger(**passenger_data)
                session.add(passenger)
                passengers_created += 1

            await session.commit()

            return {
                "message": "Demo data seeded successfully",
                "flights_created": flights_created,
                "seats_created": seats_created,
                "passengers_created": passengers_created
            }

        except Exception as e:
            await session.rollback()
            logger.error(f"Failed to seed demo data: {e}")
            return JSONResponse(
                status_code=500,
                content={"error": {"code": "SEED_FAILED", "message": str(e)}}
            )


# Include routers
app.include_router(flights_router, prefix="/api/v1")
app.include_router(seats_router, prefix="/api/v1")
app.include_router(passengers_router, prefix="/api/v1")
app.include_router(checkin_router, prefix="/api/v1")
app.include_router(baggage_router, prefix="/api/v1")
app.include_router(payments_router, prefix="/api/v1")


# Root endpoint
@app.get("/", tags=["Root"])
async def root():
    """Root endpoint - API information."""
    return {
        "name": "SkyHigh Core - Digital Check-In System",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }

