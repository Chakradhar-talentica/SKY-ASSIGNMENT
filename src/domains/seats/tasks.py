"""
Celery tasks for seat management.
"""
import logging
from src.workers.celery_app import celery_app
from src.config.database import async_session_factory
from src.domains.seats.service import SeatService
import asyncio

logger = logging.getLogger(__name__)


def run_async(coro):
    """Helper to run async code in Celery tasks."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(name="expire_seat_hold")
def expire_seat_hold(seat_id: str):
    """
    Expire a specific seat hold.
    This task is scheduled when a seat is held and runs after 120 seconds.
    """
    logger.info(f"Expiring seat hold for seat {seat_id}")

    async def _expire():
        from uuid import UUID
        async with async_session_factory() as session:
            try:
                service = SeatService(session)
                result = await service.expire_seat_hold(UUID(seat_id))
                await session.commit()
                if result:
                    logger.info(f"Seat {seat_id} hold expired successfully")
                return result
            except Exception as e:
                logger.error(f"Failed to expire seat hold {seat_id}: {e}")
                await session.rollback()
                raise

    return run_async(_expire())


@celery_app.task(name="cleanup_expired_holds")
def cleanup_expired_holds():
    """
    Cleanup all expired seat holds.
    This is a periodic task that runs as a fallback.
    """
    logger.info("Running expired holds cleanup")

    async def _cleanup():
        async with async_session_factory() as session:
            try:
                service = SeatService(session)
                count = await service.cleanup_expired_holds()
                await session.commit()
                logger.info(f"Cleaned up {count} expired holds")
                return count
            except Exception as e:
                logger.error(f"Failed to cleanup expired holds: {e}")
                await session.rollback()
                raise

    return run_async(_cleanup())


def schedule_seat_hold_expiration(seat_id: str, delay_seconds: int = 120):
    """
    Schedule a seat hold expiration task.
    Called when a seat is held.
    """
    expire_seat_hold.apply_async(
        args=[seat_id],
        countdown=delay_seconds
    )
    logger.info(f"Scheduled hold expiration for seat {seat_id} in {delay_seconds} seconds")

