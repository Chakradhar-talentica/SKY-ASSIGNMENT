"""
Custom exception classes for the application.
Each exception maps to a specific HTTP status code.
"""
from typing import Optional, Dict, Any


class SkyHighException(Exception):
    """Base exception for all application exceptions."""

    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = 400,
        details: Optional[Dict[str, Any]] = None
    ):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)


class SeatNotFoundError(SkyHighException):
    """Raised when a seat is not found."""

    def __init__(self, seat_id: str):
        super().__init__(
            code="SEAT_NOT_FOUND",
            message=f"Seat with ID {seat_id} not found",
            status_code=404,
            details={"seat_id": seat_id}
        )


class SeatNotAvailableError(SkyHighException):
    """Raised when trying to hold a seat that's not available."""

    def __init__(self, seat_id: str, current_status: str, seat_number: str = None):
        super().__init__(
            code="SEAT_NOT_AVAILABLE",
            message=f"Seat {seat_number or seat_id} is not available (current status: {current_status})",
            status_code=409,
            details={"seat_id": seat_id, "current_status": current_status}
        )


class SeatAlreadyHeldError(SkyHighException):
    """Raised when a seat is already held by another passenger."""

    def __init__(self, seat_id: str, held_by: str = None):
        super().__init__(
            code="SEAT_ALREADY_HELD",
            message="Seat is already held by another passenger",
            status_code=409,
            details={"seat_id": seat_id, "held_by": held_by}
        )


class SeatHoldExpiredError(SkyHighException):
    """Raised when trying to confirm a seat whose hold has expired."""

    def __init__(self, seat_id: str):
        super().__init__(
            code="SEAT_HOLD_EXPIRED",
            message="Seat hold has expired. Please select the seat again.",
            status_code=410,
            details={"seat_id": seat_id}
        )


class SeatLockError(SkyHighException):
    """Raised when unable to acquire lock on a seat (concurrent access)."""

    def __init__(self, seat_id: str):
        super().__init__(
            code="SEAT_LOCK_ERROR",
            message="Unable to acquire seat lock. Another transaction is in progress.",
            status_code=409,
            details={"seat_id": seat_id}
        )


class UnauthorizedSeatOperationError(SkyHighException):
    """Raised when a passenger tries to operate on a seat they don't hold."""

    def __init__(self, seat_id: str, passenger_id: str):
        super().__init__(
            code="UNAUTHORIZED_SEAT_OPERATION",
            message="You are not authorized to perform this operation on this seat",
            status_code=403,
            details={"seat_id": seat_id, "passenger_id": passenger_id}
        )


class FlightNotFoundError(SkyHighException):
    """Raised when a flight is not found."""

    def __init__(self, flight_id: str):
        super().__init__(
            code="FLIGHT_NOT_FOUND",
            message=f"Flight with ID {flight_id} not found",
            status_code=404,
            details={"flight_id": flight_id}
        )


class PassengerNotFoundError(SkyHighException):
    """Raised when a passenger is not found."""

    def __init__(self, passenger_id: str):
        super().__init__(
            code="PASSENGER_NOT_FOUND",
            message=f"Passenger with ID {passenger_id} not found",
            status_code=404,
            details={"passenger_id": passenger_id}
        )


class CheckInNotFoundError(SkyHighException):
    """Raised when a check-in is not found."""

    def __init__(self, checkin_id: str):
        super().__init__(
            code="CHECKIN_NOT_FOUND",
            message=f"Check-in with ID {checkin_id} not found",
            status_code=404,
            details={"checkin_id": checkin_id}
        )


class CheckInAlreadyExistsError(SkyHighException):
    """Raised when a passenger tries to check in twice for the same flight."""

    def __init__(self, passenger_id: str, flight_id: str):
        super().__init__(
            code="CHECKIN_ALREADY_EXISTS",
            message="Passenger has already started check-in for this flight",
            status_code=409,
            details={"passenger_id": passenger_id, "flight_id": flight_id}
        )


class InvalidCheckInStateError(SkyHighException):
    """Raised when a check-in operation is invalid for the current state."""

    def __init__(self, checkin_id: str, current_status: str, required_status: str = None):
        message = f"Check-in is in {current_status} state"
        if required_status:
            message += f", but must be in {required_status} state for this operation"
        super().__init__(
            code="INVALID_CHECKIN_STATE",
            message=message,
            status_code=400,
            details={"checkin_id": checkin_id, "current_status": current_status}
        )


class PaymentRequiredError(SkyHighException):
    """Raised when payment is required to proceed."""

    def __init__(self, checkin_id: str, amount: float):
        super().__init__(
            code="PAYMENT_REQUIRED",
            message=f"Payment of ${amount:.2f} is required for excess baggage",
            status_code=402,
            details={"checkin_id": checkin_id, "amount": amount}
        )


class PaymentFailedError(SkyHighException):
    """Raised when a payment fails."""

    def __init__(self, reason: str = "Payment processing failed"):
        super().__init__(
            code="PAYMENT_FAILED",
            message=reason,
            status_code=422,
            details={"reason": reason}
        )


class RateLimitExceededError(SkyHighException):
    """Raised when rate limit is exceeded."""

    def __init__(self, limit: int, window_seconds: int, retry_after: int = None):
        super().__init__(
            code="RATE_LIMIT_EXCEEDED",
            message=f"Rate limit exceeded. Maximum {limit} requests per {window_seconds} seconds.",
            status_code=429,
            details={
                "limit": limit,
                "window_seconds": window_seconds,
                "retry_after": retry_after
            }
        )

