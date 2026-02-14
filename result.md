# System Design Review: WebSocket Price Tick Pipeline

---

## Architecture Summary

The current system is a **monolithic synchronous pipeline**:

```
WebSocket → [Tick Processing + Postgres Write + Alert Trigger] → Done
```

A single thread of execution handles ingestion, transformation, persistence, and notification in lockstep. Every tick received    
over the WebSocket is immediately processed, written to Postgres, and any matching alerts are evaluated and fired — all before the
next tick can be handled.

---

## Idempotency Risks

**Severity: High**

1. **Duplicate ticks from the exchange/feed provider**: WebSocket reconnections, upstream retransmissions, or failover to a backup
feed can deliver the same tick twice. There is no mention of deduplication. If ticks lack a unique source-assigned ID (e.g.,      
`exchange_sequence_id`), you have no way to detect duplicates at all.

2. **Duplicate alerts**: Because alerts fire synchronously during tick processing, a replayed tick will re-trigger the same alert.
If alerts send emails, SMS, or webhook calls, users receive duplicate notifications with no guard.

3. **Partial write + retry = double write**: If the Postgres write succeeds but the alert trigger fails and the system retries the
entire operation, you get a duplicate row in Postgres.

**Concrete question to answer**: Does the upstream feed provide a monotonic sequence number or unique tick ID? If not, you need to
synthesize a dedup key from `(symbol, timestamp, price, source)` — but this is fragile with sub-millisecond ticks at the same     
price.

---

## Responsibility Coupling

**Severity: High**

Three fundamentally different concerns are fused into one synchronous call path:

| Concern | Characteristics | Current Coupling |
|---|---|---|
| **Ingestion** | Must be fast, must not drop data, latency-sensitive | Blocked by processing |
| **Persistence** | Needs durability guarantees, can tolerate small latency | Blocked by alert evaluation |
| **Alerting** | Side-effect-heavy (email, SMS, webhooks), can tolerate seconds of delay | Blocks ingestion of next tick |        

**The critical problem**: A slow alert webhook (e.g., a user's endpoint takes 5 seconds to respond) **stalls the entire ingestion 
pipeline**. You stop reading from the WebSocket, the TCP receive buffer fills, and the exchange may disconnect you for being a    
slow consumer.

Additionally, alert logic changes (new rule types, new notification channels) require touching the same code path that handles    
ingestion — a deployment risk.

---

## Backpressure Analysis

**Severity: Critical**

There is **no backpressure mechanism**. The system has exactly one speed: the speed of the slowest component.

- **Normal market**: ~50 ticks/sec across instruments. Postgres can handle this. Alerts are rare. System appears healthy.
- **Market open / high volatility**: 5,000–50,000 ticks/sec. Postgres write latency spikes (connection pool exhaustion, WAL       
pressure). Alert evaluation multiplies per-tick cost. The WebSocket read loop falls behind.
- **Cascade failure**: WebSocket library buffers unread messages in memory → heap grows → GC pauses increase → processing slows   
further → OOM kill or exchange disconnects the session.

**There is no circuit breaker, no queue depth metric, no ability to shed load.**

---

## Ingestion vs Processing Issues

The ingestion boundary does not exist. The WebSocket `on_message` handler **is** the processing pipeline. This means:

1. **You cannot independently scale ingestion and processing.** If you need to process ticks for 10,000 symbols, you cannot add   
processing workers without also adding WebSocket connections (which exchanges rate-limit).

2. **You cannot replay.** If a bug in alert logic corrupts state or misses alerts, there is no tick log to replay from. The data  
goes straight to Postgres, but Postgres is not an efficient replay source for ordered time-series data.

3. **You cannot version processing logic.** Running old and new alert logic side-by-side (shadow mode) is impossible without      
duplicating the entire pipeline.

---

## Failure Scenarios

### Scenario 1: Postgres goes down for 30 seconds
- **Impact**: Every tick is lost for 30 seconds. WebSocket stays connected but the write call throws exceptions. If exceptions    
aren't caught cleanly, the WebSocket connection may also drop.
- **Recovery**: No recovery. Ticks during the outage are gone.

### Scenario 2: Alert webhook target is slow (10s response time)
- **Impact**: Tick processing throughput drops to 0.1 ticks/sec. Thousands of ticks buffer in memory. Likely OOM or disconnect    
within minutes.
- **Recovery**: Requires manual restart. Lost ticks are unrecoverable.

### Scenario 3: WebSocket disconnects during a Postgres transaction
- **Impact**: Current tick may or may not commit (depends on where in the call the disconnect happens). Reconnection logic must   
handle the ambiguous state of the last tick.
- **Recovery**: Without idempotency keys, you either lose or duplicate the in-flight tick.

### Scenario 4: Deployment / restart
- **Impact**: All in-flight ticks are lost. No graceful drain because there's no buffer.
- **Recovery**: Cold restart. Gap in tick data.

### Scenario 5: Poison tick (malformed data, unexpected symbol, NaN price)
- **Impact**: If not caught, crashes the processing loop. All subsequent ticks are lost until restart.
- **Recovery**: Requires code fix and redeploy. No dead-letter mechanism.

---

## Concrete Fixes

### Fix 1: Introduce a durable buffer between ingestion and processing

```
WebSocket → [Ingestion Service] → Kafka/Redis Streams → [Processing Workers] → Postgres
                                                      → [Alert Workers] → Notification Service
```

- **Ingestion service** does one thing: read from WebSocket, assign an ingestion timestamp and sequence number, write to Kafka    
partition (keyed by symbol).
- **Processing workers** consume from Kafka, write to Postgres (with idempotency key = `topic + partition + offset`).
- **Alert workers** consume from the same Kafka topic (separate consumer group), evaluate rules, fire notifications.

**Why Kafka specifically**: Ordered per-partition, replayable, handles back