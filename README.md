# SkyHigh Core – Digital Check-In System

A high-performance backend service for airline self-check-in built with FastAPI, PostgreSQL, and Redis.

## Features

- ✅ **Conflict-free seat selection** – Database-level locking prevents double bookings
- ✅ **Time-bound seat holds** – 2-minute temporary reservations with auto-release
- ✅ **Baggage validation** – Weight limit enforcement with payment flow
- ✅ **High-performance seat map** – Redis caching for sub-second response times
- ✅ **Rate limiting** – Protection against abusive access patterns
- ✅ **Comprehensive testing** – 80%+ code coverage

## Tech Stack

- **Framework**: FastAPI
- **Database**: PostgreSQL with SQLAlchemy 2.x
- **Cache**: Redis
- **Task Queue**: Celery with Redis broker
- **Migrations**: Alembic
- **Testing**: Pytest

## Quick Start

### Prerequisites

- Docker and Docker Compose installed
- Git

### 1. Clone and Setup

```bash
cd skyhigh-core
cp .env.example .env
```

### 2. Start All Services

```bash
docker-compose up --build
```

This starts:
- FastAPI application on `http://localhost:8000`
- PostgreSQL on port `5432`
- Redis on port `6379`
- Celery worker for background tasks
- Celery beat for scheduled tasks

### 3. Run Database Migrations

In a new terminal:

```bash
docker-compose exec app alembic upgrade head
```

### 4. Seed Demo Data (Optional)

```bash
curl -X POST http://localhost:8000/api/v1/admin/seed
```

### 5. Access the API

- **API Documentation**: http://localhost:8000/docs
- **Alternative Docs**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health

## Development Setup

### Local Development (without Docker)

1. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Start PostgreSQL and Redis (via Docker):
```bash
docker-compose up -d postgres redis
```

4. Run migrations:
```bash
alembic upgrade head
```

5. Start the application:
```bash
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

6. Start Celery worker (new terminal):
```bash
celery -A src.workers.celery_app worker --loglevel=info
```

7. Start Celery beat (new terminal):
```bash
celery -A src.workers.celery_app beat --loglevel=info
```

## Running Tests

### Quick Test Run (No Docker Required)

Tests use SQLite in-memory database, so you can run them without Docker:

```bash
# Step 1: Make sure you're in the project directory
cd skyhigh-core

# Step 2: Install test dependencies
pip install pytest pytest-asyncio pytest-cov httpx aiosqlite email-validator

# Step 3: Run all tests
python -m pytest tests/ -v

# Step 4: Run with coverage
python -m pytest tests/ --cov=src --cov-report=term-missing
```

### Run All Tests

```bash
# Using Docker
docker-compose exec app pytest

# Local
pytest
```

### Run with Coverage Report

```bash
# Generate coverage report
pytest --cov=src --cov-report=html --cov-report=term-missing

# View HTML report
open htmlcov/index.html
```

### Run Specific Test Categories

```bash
# Unit tests only
pytest tests/unit/

# Integration tests only
pytest tests/integration/

# Specific test file
pytest tests/unit/test_seat_service.py -v
```

## API Endpoints

### Health & Status
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |

### Flights
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/flights` | List all flights |
| GET | `/api/v1/flights/{id}` | Get flight details |

### Seats
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/flights/{flight_id}/seats` | Get seat map |
| POST | `/api/v1/seats/{seat_id}/hold` | Hold a seat |
| POST | `/api/v1/seats/{seat_id}/release` | Release held seat |
| POST | `/api/v1/seats/{seat_id}/confirm` | Confirm seat |

### Check-in
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/checkin/start` | Start check-in |
| GET | `/api/v1/checkin/{id}` | Get check-in status |
| POST | `/api/v1/checkin/{id}/complete` | Complete check-in |

### Baggage
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/checkin/{id}/baggage` | Add baggage |
| GET | `/api/v1/checkin/{id}/baggage` | Get baggage info |

### Payments
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/checkin/{id}/pay` | Process payment |

### Admin
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/admin/seed` | Seed demo data |

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql+asyncpg://...` |
| `REDIS_URL` | Redis connection string | `redis://localhost:6379/0` |
| `SEAT_HOLD_DURATION_SECONDS` | Seat hold timeout | `120` |
| `MAX_BAGGAGE_WEIGHT_KG` | Maximum baggage weight | `25` |
| `RATE_LIMIT_REQUESTS` | Rate limit per window | `100` |
| `RATE_LIMIT_WINDOW_SECONDS` | Rate limit window | `60` |

## Project Structure

See [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) for detailed explanation.

## Architecture

See [ARCHITECTURE.md](ARCHITECTURE.md) for system design documentation.

## Workflow Design

See [WORKFLOW_DESIGN.md](WORKFLOW_DESIGN.md) for flow diagrams and database schema.

## API Specification

See [API-SPECIFICATION.yml](API-SPECIFICATION.yml) for OpenAPI specification.

## Troubleshooting

### Database Connection Issues

```bash
# Check if PostgreSQL is running
docker-compose ps postgres

# View PostgreSQL logs
docker-compose logs postgres
```

### Redis Connection Issues

```bash
# Check if Redis is running
docker-compose ps redis

# Test Redis connection
docker-compose exec redis redis-cli ping
```

### Worker Not Processing Tasks

```bash
# Check worker logs
docker-compose logs celery-worker

# Restart worker
docker-compose restart celery-worker
```

### Reset Everything

```bash
# Stop all containers and remove volumes
docker-compose down -v

# Rebuild and start fresh
docker-compose up --build
```

## License

MIT License - See LICENSE file for details.

