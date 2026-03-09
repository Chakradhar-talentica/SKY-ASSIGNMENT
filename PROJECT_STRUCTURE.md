# Project Structure

This document explains the folder structure and purpose of each module in the SkyHigh Core project.

## Root Directory

```
skyhigh-core/
├── src/                    # Source code
├── tests/                  # Test files
├── migrations/             # Alembic database migrations
├── docker-compose.yml      # Docker services configuration
├── Dockerfile              # Application container definition
├── requirements.txt        # Python dependencies
├── alembic.ini            # Alembic configuration
├── pytest.ini             # Pytest configuration
├── .env.example           # Environment variables template
├── PRD.md                 # Product Requirements Document
├── README.md              # Project overview and setup guide
├── PROJECT_STRUCTURE.md   # This file
├── WORKFLOW_DESIGN.md     # Flow diagrams and database schema
├── ARCHITECTURE.md        # Architecture documentation
├── API-SPECIFICATION.yml  # OpenAPI specification
└── CHAT_HISTORY.md        # AI assistant conversation summary
```

## Source Code (`src/`)

### Main Entry Point

```
src/
├── main.py                # FastAPI application entry point
│                          # - Creates app instance
│                          # - Registers routers
│                          # - Sets up middleware
│                          # - Configures exception handlers
```

### Configuration (`src/config/`)

```
src/config/
├── __init__.py
├── settings.py            # Application settings
│                          # - Environment variable loading
│                          # - Pydantic BaseSettings
│                          # - Database, Redis, app configs
│
└── database.py            # Database configuration
                           # - SQLAlchemy async engine
                           # - Session factory
                           # - Base model class
```

### Common Utilities (`src/common/`)

```
src/common/
├── __init__.py
├── exceptions.py          # Custom exception classes
│                          # - SeatNotAvailableError
│                          # - SeatAlreadyHeldError
│                          # - PaymentRequiredError
│                          # - RateLimitExceededError
│
├── responses.py           # Standardized API responses
│                          # - Success response format
│                          # - Error response format
│
├── dependencies.py        # FastAPI dependencies
│                          # - Database session dependency
│                          # - Redis client dependency
│                          # - Current user dependency
│
└── middleware/
    ├── __init__.py
    └── rate_limiter.py    # Rate limiting middleware
                           # - Redis-based sliding window
                           # - Per-endpoint configuration
                           # - IP-based rate limiting
```

### Domain Modules (`src/domains/`)

Each domain follows a consistent structure:

```
domain/
├── __init__.py
├── models.py              # SQLAlchemy models (database tables)
├── schemas.py             # Pydantic schemas (request/response)
├── repository.py          # Database operations (CRUD)
├── service.py             # Business logic
├── router.py              # API endpoints
└── tasks.py               # Background tasks (if any)
```

#### Seats Domain (`src/domains/seats/`)

```
src/domains/seats/
├── __init__.py
├── models.py              # Seat model
│                          # - seat_id, flight_id, seat_number
│                          # - status (AVAILABLE/HELD/CONFIRMED)
│                          # - held_by, held_at, hold_expires_at
│                          # - confirmed_by, confirmed_at
│
├── schemas.py             # Seat schemas
│                          # - SeatResponse, SeatMapResponse
│                          # - HoldSeatRequest, HoldSeatResponse
│
├── repository.py          # Seat database operations
│                          # - get_seat_map() - fetch all seats for flight
│                          # - hold_seat() - atomic hold with FOR UPDATE
│                          # - confirm_seat() - confirm held seat
│                          # - release_seat() - release held seat
│                          # - expire_holds() - release expired holds
│
├── service.py             # Seat business logic
│                          # - Orchestrates repository operations
│                          # - Handles cache invalidation
│                          # - Triggers background tasks
│
├── router.py              # Seat API endpoints
│                          # - GET /flights/{id}/seats
│                          # - POST /seats/{id}/hold
│                          # - POST /seats/{id}/release
│                          # - POST /seats/{id}/confirm
│
└── tasks.py               # Seat background tasks
                           # - expire_seat_hold() - delayed task
                           # - cleanup_expired_holds() - periodic task
```

#### Flights Domain (`src/domains/flights/`)

```
src/domains/flights/
├── __init__.py
├── models.py              # Flight model
│                          # - flight_id, flight_number
│                          # - departure, arrival
│                          # - departure_time, arrival_time
│
├── schemas.py             # Flight schemas
├── repository.py          # Flight database operations
├── service.py             # Flight business logic
└── router.py              # Flight API endpoints
```

#### Check-in Domain (`src/domains/checkin/`)

```
src/domains/checkin/
├── __init__.py
├── models.py              # CheckIn model
│                          # - checkin_id, passenger_id, flight_id
│                          # - seat_id, status
│                          # - Status: IN_PROGRESS, WAITING_FOR_PAYMENT, COMPLETED
│
├── schemas.py             # CheckIn schemas
│                          # - StartCheckInRequest
│                          # - CheckInStatusResponse
│
├── repository.py          # CheckIn database operations
├── service.py             # CheckIn business logic
│                          # - Orchestrates seat hold + baggage + payment
│                          # - State machine transitions
│
└── router.py              # CheckIn API endpoints
                           # - POST /checkin/start
                           # - GET /checkin/{id}
                           # - POST /checkin/{id}/complete
```

#### Baggage Domain (`src/domains/baggage/`)

```
src/domains/baggage/
├── __init__.py
├── models.py              # Baggage model
│                          # - baggage_id, checkin_id
│                          # - weight_kg, excess_fee
│
├── schemas.py             # Baggage schemas
├── service.py             # Baggage business logic
│                          # - Weight validation (max 25kg)
│                          # - Fee calculation
│
└── router.py              # Baggage API endpoints
```

#### Payments Domain (`src/domains/payments/`)

```
src/domains/payments/
├── __init__.py
├── models.py              # Payment model
│                          # - payment_id, checkin_id
│                          # - amount, status, paid_at
│
├── schemas.py             # Payment schemas
├── service.py             # Payment business logic
│                          # - Simulated payment processing
│
└── router.py              # Payment API endpoints
```

#### Passengers Domain (`src/domains/passengers/`)

```
src/domains/passengers/
├── __init__.py
├── models.py              # Passenger model
│                          # - passenger_id, name, email
│                          # - booking_reference
│
├── schemas.py             # Passenger schemas
├── repository.py          # Passenger database operations
└── router.py              # Passenger API endpoints
```

### Cache Layer (`src/cache/`)

```
src/cache/
├── __init__.py
└── seat_map_cache.py      # Redis caching for seat maps
                           # - get_cached_seat_map()
                           # - set_seat_map_cache()
                           # - invalidate_seat_map_cache()
                           # - TTL-based expiration
```

### Background Workers (`src/workers/`)

```
src/workers/
├── __init__.py
├── celery_app.py          # Celery application configuration
│                          # - Redis as broker and backend
│                          # - Task autodiscovery
│
└── beat_schedule.py       # Periodic task scheduling
                           # - Cleanup expired holds every 30 seconds
```

## Tests (`tests/`)

```
tests/
├── __init__.py
├── conftest.py            # Pytest fixtures
│                          # - Test database setup
│                          # - Test client
│                          # - Sample data factories
│
├── unit/                  # Unit tests
│   ├── __init__.py
│   ├── test_seat_service.py
│   ├── test_checkin_service.py
│   ├── test_baggage_service.py
│   └── test_payment_service.py
│
└── integration/           # Integration tests
    ├── __init__.py
    ├── test_seat_api.py
    ├── test_checkin_api.py
    ├── test_concurrent_booking.py
    └── test_rate_limiting.py
```

## Migrations (`migrations/`)

```
migrations/
├── env.py                 # Alembic environment configuration
├── script.py.mako         # Migration template
└── versions/              # Migration files
    └── 001_initial.py     # Initial database schema
```

## Key Design Decisions

### 1. Modular Monolith
- Each domain is self-contained with its own models, schemas, services
- Easy to understand and maintain
- Can be split into microservices later if needed

### 2. Repository Pattern
- Separates database logic from business logic
- Makes testing easier with mock repositories
- Centralizes query optimization

### 3. Service Layer
- Contains all business logic
- Orchestrates between repositories and external services
- Handles transaction boundaries

### 4. Dependency Injection
- Uses FastAPI's dependency system
- Easy to swap implementations for testing
- Clear separation of concerns

