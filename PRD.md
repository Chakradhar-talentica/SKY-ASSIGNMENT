# SkyHigh Core – Digital Check-In System
## Product Requirements Document (PRD)

---

## 1. Executive Summary

SkyHigh Airlines requires a robust, high-performance digital check-in backend system to handle peak-hour traffic at airports. The system must enable passengers to select seats, add baggage, and complete check-in while ensuring no seat conflicts, handling temporary reservations, and supporting baggage fee processing.

---

## 2. Problem Statement

During popular flight check-in windows, hundreds of passengers simultaneously attempt to:
- Browse available seats
- Select and reserve seats
- Add baggage to their booking
- Complete the check-in process

Current challenges:
- **Seat conflicts**: Multiple passengers may attempt to select the same seat
- **Abandoned reservations**: Passengers start but don't complete check-in, blocking seats
- **Peak load handling**: System must remain responsive under heavy concurrent usage
- **Overweight baggage**: Additional fees must be collected before check-in completion
- **Abuse prevention**: System must detect and prevent malicious access patterns

---

## 3. Goals

| Goal | Description | Success Metric |
|------|-------------|----------------|
| **No seat conflicts** | Only one passenger can successfully reserve a seat | Zero duplicate seat assignments |
| **Fast check-in** | Responsive seat map and quick operations | P95 seat map load < 1 second |
| **Temporary holds** | Reserve seats for limited time | 120-second hold with auto-release |
| **Baggage validation** | Enforce weight limits with payment flow | 100% enforcement of 25kg limit |
| **Scalability** | Handle hundreds of concurrent users | Support 500+ concurrent check-ins |
| **Reliability** | System remains consistent under load | Zero data inconsistencies |

---

## 4. Target Users

### 4.1 Primary Users
- **Passengers**: Travelers using self-service kiosks or mobile apps to check in
- **Airport Staff**: Agents who may need to assist passengers or view system status

### 4.2 System Users
- **Integration Systems**: Other airline systems that consume check-in data
- **Operations Team**: Staff monitoring system health and performance

---

## 5. Functional Requirements

### 5.1 Seat Availability & Lifecycle Management

**FR-1.1**: Each seat must have one of three states: `AVAILABLE`, `HELD`, or `CONFIRMED`

**FR-1.2**: State transitions follow this lifecycle:
```
AVAILABLE → HELD → CONFIRMED
     ↑         |
     └─────────┘ (timeout/release)
```

**FR-1.3**: Business rules:
- A seat can only be held if currently `AVAILABLE`
- A seat in `HELD` state is exclusive to one passenger
- A `CONFIRMED` seat can never change state
- Only the passenger who holds a seat can confirm it

### 5.2 Time-Bound Seat Hold

**FR-2.1**: When a passenger selects a seat, reserve it for exactly **120 seconds**

**FR-2.2**: During the hold period:
- No other passenger can hold or confirm the same seat
- The holding passenger can confirm or release the seat

**FR-2.3**: If check-in is not completed within 120 seconds:
- The seat automatically becomes `AVAILABLE`
- The passenger must re-select if they wish to continue

**FR-2.4**: This behavior must work reliably even during high traffic

### 5.3 Conflict-Free Seat Assignment

**FR-3.1**: If multiple passengers attempt to reserve the same seat simultaneously, only one reservation succeeds

**FR-3.2**: The system must guarantee:
- No race conditions resulting in duplicate assignments
- Consistent behavior regardless of request volume
- Immediate feedback on reservation success/failure

### 5.4 Baggage Validation & Payment Flow

**FR-4.1**: Maximum allowed baggage weight is **25kg**

**FR-4.2**: If baggage exceeds the limit:
- Check-in enters `WAITING_FOR_PAYMENT` status
- Passenger must pay additional baggage fee
- Check-in continues only after successful payment

**FR-4.3**: Check-in statuses:
- `IN_PROGRESS`: Check-in started, seat held
- `WAITING_FOR_PAYMENT`: Overweight baggage, payment required
- `COMPLETED`: Check-in finished successfully

### 5.5 Seat Map Performance

**FR-5.1**: Seat map browsing is the most frequently accessed feature

**FR-5.2**: Performance requirements:
- P95 response time under 1 second
- Support hundreds of concurrent users
- Near real-time accuracy of seat availability

---

## 6. Non-Functional Requirements (NFRs)

### 6.1 Performance

| Metric | Requirement |
|--------|-------------|
| Seat map P95 latency | < 1 second |
| Seat hold P95 latency | < 500ms |
| Concurrent users | 500+ simultaneous |
| Throughput | 1000+ requests/second |

### 6.2 Reliability

- **Availability**: 99.9% uptime
- **Data consistency**: Strong consistency for seat assignments
- **Fault tolerance**: Graceful degradation under load

### 6.3 Scalability

- Horizontal scaling capability for API servers
- Database connection pooling
- Caching layer for read-heavy operations

### 6.4 Security

- Rate limiting to prevent abuse
- Input validation on all endpoints
- Protection against common attack vectors

### 6.5 Maintainability

- Modular architecture with clear separation of concerns
- Comprehensive logging
- Health check endpoints
- Test coverage ≥ 80%

---

## 7. Constraints

- Must use PostgreSQL as primary database
- Must use Redis for caching and rate limiting
- Must be deployable via Docker Compose
- Must provide OpenAPI specification

---

## 8. Success Criteria

1. ✅ Zero duplicate seat assignments under concurrent load
2. ✅ Held seats automatically release after 120 seconds
3. ✅ Seat map loads in under 1 second (P95)
4. ✅ Overweight baggage triggers payment flow
5. ✅ Rate limiting prevents abuse
6. ✅ Test coverage ≥ 80%
7. ✅ All required documentation complete

---

## 9. Out of Scope

- Frontend/UI implementation
- Real payment gateway integration (simulated only)
- Flight booking (assumes booking already exists)
- Boarding pass generation
- Multi-language support

---

## 10. Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Database lock contention | Slow seat selection | Use NOWAIT locks with retry logic |
| Cache inconsistency | Stale seat data | TTL-based invalidation + event-driven updates |
| Worker failure | Orphaned holds | Periodic cleanup job as fallback |
| Redis downtime | Rate limiting disabled | Graceful degradation, allow requests |

---

## Document History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-03-09 | SkyHigh Team | Initial PRD |

