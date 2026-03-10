# OLIMPO Backend API Contract v1

Base URL

https://olimpo-backend.onrender.com

## Endpoints

### SYSTEM

GET /

Returns API status.

---

### AUTH

POST /auth/google

Authenticates user using Google OAuth token.

Returns JWT access token.

---

### BOOTSTRAP

GET /bootstrap

Returns system configuration required by the mobile app.

Includes:

- product catalog
- markets
- helios configuration

---

### MODELS

POST /models/run

Executes analytical models.

Supported models:

- epsilon
- sigma
- poseidon

---

### SUBSCRIPTIONS

GET /subscriptions/status

Returns:

- subscription status
- active plan
- entitlements

---

### BILLING

POST /billing/google/verify

Verifies Google Play purchase tokens.

Ensures subscription validity.
