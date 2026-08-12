# API & Third-Party Integration Protocol (`Iris api`)

## Trigger
Activate when building or modifying third-party integrations (NICE CXone, WhatsApp, Payment Gateways, Webhooks, or REST/gRPC endpoints). Command: `Iris api`.

## 1. Webhook Security & Idempotency
- **Signature Verification**: Always validate incoming webhook HTTP headers/signatures (e.g., HMAC-SHA256) before processing any payload.
- **Idempotency Guard**: Store `event_id` or `idempotency_key` in a dedicated tracking table with a unique index. Skip already-processed events cleanly with `200 OK`.
- **Async Ingestion**: Fast-return `200 OK` to the provider within 500ms; push payload processing to background workers/queues.

## 2. Vendor Resilience & Retry Patterns
- **Exponential Backoff**: Implement exponential backoff with random jitter for failed HTTP requests.
- **Rate Limit Handling**: Respect `Retry-After` and `HTTP 429` status codes. Never loop aggressively against external vendor endpoints.
- **Circuit Breaker**: Auto-pause outbound requests if consecutive vendor failures exceed threshold to prevent resource exhaustion.

## 3. Secret Protection & Token Lifecycle
- **Encrypted Storage**: Store vendor client secrets, access keys, and tokens encrypted at rest using AES-256 (`AI::encryptKey` pattern).
- **Proactive Token Refresh**: Cache auth tokens with expiration windows. Refresh 5 minutes before expiration to avoid mid-operation 401s.
- **Zero Raw Secrets in Logs**: Sanitize headers (`Authorization`, `X-API-Key`) and sensitive request/response bodies before passing to `Logger`.
