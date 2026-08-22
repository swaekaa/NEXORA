# NEXORA — Security Policy

**Version:** 1.0  
**Date:** August 22, 2026

---

## Non-Negotiable Security Rules

### Secrets
- ALL secrets in `.env` only — never in source code
- `.env` in `.gitignore` — never committed
- Required secrets: `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET`, `RAZORPAY_WEBHOOK_SECRET`, `LLM_API_KEY`, `DATABASE_URL`

### Razorpay Key Secret
- NEVER returned to frontend (even in CORS-allowlisted response)
- Used ONLY for: Razorpay API auth, payment signature verification
- `RAZORPAY_KEY_ID` (not secret) returned to frontend for Checkout initialization

### Webhook Security
- Signature verified BEFORE body is parsed
- Uses HMAC-SHA256 with `RAZORPAY_WEBHOOK_SECRET` (different from KEY_SECRET)
- Use `hmac.compare_digest()` not `==` (constant-time, prevents timing attacks)
- Raw body used for verification (never parsed JSON)

### Payment State
- NEVER trust frontend payment state
- Agreement only marked PAID after webhook verification
- Payment amount re-verified on every financial state transition

### LLM Safety
- All LLM tool outputs validated against Pydantic schemas
- LLM cannot call Razorpay APIs directly
- LLM cannot modify agreement financial fields directly
- LLM chain-of-thought never stored in audit log

### Database
- PostgreSQL with password auth
- No raw SQL in application code — SQLAlchemy ORM only
- Monetary values as NUMERIC(18,2), never FLOAT
- Audit events are append-only (no application-level UPDATE/DELETE on audit_events)

---

## Authentication (MVP)

MVP uses simple API key for merchant endpoints:
- Key stored as PBKDF2-SHA256 hash in DB
- Transmitted via `X-NEXORA-API-KEY` header (HTTPS only in production)
- Design allows drop-in replacement with JWT or OAuth2

---

## Future Security Additions (Post-MVP)
- JWT with short-lived tokens
- Rate limiting on all public endpoints
- API request signing for agent-to-agent calls
- TLS mutual authentication for agent communication
- Field-level encryption for sensitive agreement data
