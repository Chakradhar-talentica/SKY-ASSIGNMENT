# Chat History - Design Journey with AI Assistant

This document chronicles the design journey and key decisions made while building the SkyHigh Core Digital Check-In System with AI assistance.

---

## Session 1: Initial Requirements Analysis

### Conversation Summary

**User Request:** Build a production-style submission for an airline digital check-in system with FastAPI.

**AI Analysis:**
The requirements were analyzed and broken down into core components:
1. Seat lifecycle management (AVAILABLE → HELD → CONFIRMED)
2. Time-bound seat holds (120 seconds)
3. Conflict-free concurrent seat assignment
4. Baggage validation with payment flow
5. High-performance seat map access
6. Rate limiting for abuse protection

### Key Decision: Architecture Choice

**Options Evaluated:**

| Architecture | Pros | Cons |
|--------------|------|------|
| Microservices | Independent scaling, isolation | Complex, overkill for this scope |
| Modular Monolith | Simple, clear boundaries, easy to maintain | Limited scaling options |
| Simple Monolith | Very simple | Hard to maintain, no separation |

**Decision:** Modular Monolith was chosen because:
- Appropriate for project scope and beginner-friendliness
- Clear domain boundaries make code understandable
- Can evolve to microservices if needed later
- Single deployment unit simplifies operations

---

## Session 2: Database Design

### Conversation Summary

**Topic:** How to design the database schema for seat management with concurrency support.

### Key Decision: Locking Strategy

**Options Evaluated:**

| Strategy | Behavior | Use Case |
|----------|----------|----------|
| Optimistic Locking | Version-based conflict detection | Low contention scenarios |
| Pessimistic (FOR UPDATE) | Wait for lock release | Background jobs |
| Pessimistic (FOR UPDATE NOWAIT) | Immediate failure on lock conflict | User-facing APIs |
| Pessimistic (SKIP LOCKED) | Skip locked rows | Queue processing |

**Decision:** `SELECT FOR UPDATE NOWAIT` was chosen because:
- Provides immediate feedback to users when seat is contested
- Prevents request pile-up during high traffic
- Simple to implement with SQLAlchemy
- Clear semantics: try to lock, fail fast if can't

**Implementation Pattern:**
```python
# Atomic seat hold with NOWAIT
stmt = select(Seat).where(
    Seat.id == seat_id,
    Seat.status == SeatStatus.AVAILABLE
).with_for_update(nowait=True)

seat = await session.execute(stmt)
```

---

## Session 3: Seat Hold Expiration

### Conversation Summary

**Topic:** How to reliably expire seat holds after 120 seconds.

### Key Decision: Expiration Mechanism

**Options Evaluated:**

| Approach | Pros | Cons |
|----------|------|------|
| Database job/cron | Simple, reliable | Delay up to cron interval |
| Delayed task per hold | Precise timing | High task volume |
| Redis TTL with callback | Very precise | Complex setup |
| Hybrid (delayed + periodic) | Best of both | Slightly more complex |

**Decision:** Hybrid approach was chosen:
1. **Primary:** Schedule a Celery delayed task when hold is created (runs after 120s)
2. **Fallback:** Periodic cleanup job every 30 seconds catches any missed expirations

**Rationale:**
- Delayed task provides precise 120-second guarantee
- Periodic cleanup handles edge cases (worker crash, task lost)
- Both are simple to implement with Celery
- Redundancy increases reliability

---

## Session 4: Caching Strategy

### Conversation Summary

**Topic:** How to achieve P95 < 1 second for seat map queries while maintaining accuracy.

### Key Decision: Cache Implementation

**Options Evaluated:**

| Strategy | Hit Rate | Consistency | Complexity |
|----------|----------|-------------|------------|
| No cache | N/A | Perfect | Simple |
| Read-through | High | Good | Medium |
| Cache-aside with TTL | High | Eventually consistent | Medium |
| Write-through | High | Strong | Complex |

**Decision:** Cache-aside with TTL and invalidation:
- **TTL:** 30 seconds for seat maps
- **Invalidation:** Clear cache on any seat status change
- **Fallback:** If Redis is down, go directly to database

**Rationale:**
- Seat map is read-heavy, cache provides major performance benefit
- 30-second TTL balances freshness vs performance
- Explicit invalidation on writes keeps data reasonably fresh
- Graceful degradation maintains availability

---

## Session 5: Rate Limiting

### Conversation Summary

**Topic:** How to prevent abuse and protect the seat hold endpoint.

### Key Decision: Rate Limiting Approach

**Options Evaluated:**

| Algorithm | Precision | Burst Handling | Complexity |
|-----------|-----------|----------------|------------|
| Fixed window | Low | Poor (thundering herd) | Simple |
| Sliding window | High | Good | Medium |
| Token bucket | High | Excellent | Complex |
| Leaky bucket | High | Good | Complex |

**Decision:** Sliding window counter with Redis:
- Simple to implement and understand
- Good precision for our use case
- Handles bursts reasonably well

**Rate Limits Configured:**
| Endpoint | Limit | Window |
|----------|-------|--------|
| Seat map | 100 | 60s |
| Seat hold | 10 | 60s |
| Check-in operations | 20 | 60s |

---

## Session 6: Baggage and Payment Flow

### Conversation Summary

**Topic:** How to implement the baggage validation and payment pause workflow.

### Key Decision: State Machine Design

**Check-in States:**
```
IN_PROGRESS → WAITING_FOR_PAYMENT → COMPLETED
      ↓                                  ↑
      └──────────────────────────────────┘
      (if no excess baggage)
```

**Implementation:**
- Check-in starts in `IN_PROGRESS`
- When baggage is added and exceeds 25kg, calculate fee and set `WAITING_FOR_PAYMENT`
- Payment must be processed before check-in can complete
- Once payment succeeds, status returns to `IN_PROGRESS`
- Final seat confirmation sets status to `COMPLETED`

**Rationale:**
- Simple state machine is easy to understand and debug
- Each state has clear meaning and valid transitions
- Payment service is simulated but interface is realistic

---

## Session 7: Testing Strategy

### Conversation Summary

**Topic:** How to achieve 80%+ test coverage with meaningful tests.

### Key Decision: Test Categories

**Test Pyramid:**
```
        /\
       /  \     E2E Tests (few)
      /----\
     /      \   Integration Tests (some)
    /--------\
   /          \ Unit Tests (many)
  /------------\
```

**Priority Tests:**
1. **Concurrency:** Multiple users trying to hold same seat
2. **Seat lifecycle:** All state transitions
3. **Hold expiration:** Automatic release after 120s
4. **Baggage validation:** Weight limits and fee calculation
5. **Payment flow:** Fee payment unlocks check-in

**Tools:**
- Pytest for test framework
- pytest-asyncio for async tests
- pytest-cov for coverage reporting
- Factory pattern for test data

---

## Session 8: Docker Configuration

### Conversation Summary

**Topic:** How to structure Docker Compose for easy local development.

### Key Decision: Container Architecture

**Services:**
1. **app:** FastAPI application
2. **postgres:** PostgreSQL database
3. **redis:** Redis for cache and broker
4. **celery-worker:** Background task processor
5. **celery-beat:** Periodic task scheduler

**Network:** All services on single bridge network for simplicity

**Health Checks:** Added for postgres and redis to ensure dependencies are ready

---

## Summary of Trade-offs

| Decision | Trade-off | Why This Choice |
|----------|-----------|-----------------|
| Modular monolith | Scalability vs Simplicity | Appropriate for scope, can evolve |
| FOR UPDATE NOWAIT | User waits vs Fast failure | Better UX with immediate feedback |
| 30s cache TTL | Freshness vs Performance | Good balance for seat browsing |
| Hybrid expiration | Complexity vs Reliability | Ensures no orphaned holds |
| Sliding window rate limit | Precision vs Simplicity | Good enough for abuse prevention |

---

## AI Assistance Value

The AI assistant helped with:
1. **Architecture decisions:** Evaluating options with pros/cons
2. **Code generation:** Creating boilerplate and domain logic
3. **Best practices:** Suggesting patterns like repository, dependency injection
4. **Documentation:** Generating comprehensive docs with diagrams
5. **Testing:** Creating test cases for edge cases
6. **Troubleshooting:** Debugging configuration issues

---

## Lessons Learned

1. **Start with clear requirements:** Breaking down the problem statement helped identify all components needed
2. **Choose appropriate complexity:** A modular monolith was right for this scope
3. **Test concurrent scenarios:** Race conditions need explicit testing
4. **Document decisions:** Future readers (including yourself) will thank you
5. **Use diagrams:** Mermaid diagrams make architecture clear

