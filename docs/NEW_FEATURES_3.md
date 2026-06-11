# SoukPilot AI — New Features (Multitenancy + Super-Admin)

## Overview

Two feature branches merged into `main` after the stretch phase:

- **`feat/multitenancy`** — Full multi-tenant architecture: every user belongs to a business, every row is scoped to that business, JWT carries the tenant identity.
- **`feat/super-admin`** — 2-tier admin system: a superadmin role that sits above all tenants, with a standalone management portal.

---

## Feature 1: Full Multi-Tenant Architecture

### What it does

Transforms SoukPilot from a single-owner local tool into a proper SaaS platform.
Each business that registers gets its own isolated data silo — products, orders,
invoices, reports, and all other records are completely separate between tenants.

### How it works

**Database:** A `users` table links every account to a `business_id`. The JWT
token issued on login embeds that `business_id`.

**API layer:** A `get_current_user` FastAPI dependency extracts `business_id`
from every request's Bearer token. Every service call receives `business_id` and
appends it to every query as a `WHERE business_id = :bid` filter — no cross-tenant
data leakage is possible even if an API endpoint has a bug.

**Registration flow:**
1. `POST /api/auth/register` creates a `Business` + `User(role=owner)` atomically in one transaction
2. Returns a JWT with `business_id` and `role` embedded
3. Frontend stores the token and uses it for all subsequent requests

**Login flow:**
1. `POST /api/auth/login` looks up the user in the DB, verifies bcrypt hash
2. Returns a JWT — all requests from that point are scoped to that business

### New tables

| Table | Purpose |
|---|---|
| `users` | `username`, `hashed_password`, `role`, `business_id` FK |
| `widget_tokens` | Per-business embeddable chat widget tokens |

### New / changed files

| File | Change |
|---|---|
| `backend/app/models/user.py` | New `User` model |
| `backend/app/models/business.py` | `Business` model (was single-row, now multi-tenant) |
| `backend/app/core/deps.py` | `get_current_user` dep — decodes JWT, returns `CurrentUser(username, business_id, role)` |
| `backend/app/core/security.py` | `create_access_token`, `hash_password`, `verify_password` |
| `backend/app/api/auth.py` | `/register` + `/login` endpoints |
| `backend/alembic/versions/0005_users.py` | Migration: creates `users` table |

---

## Feature 2: 2-Tier Super-Admin System

### What it does

Adds a `superadmin` role above all tenant owners. The superadmin can:

- **List all tenants** with owner username, registration date, and live counts (users, products, orders)
- **View per-tenant usage stats** — orders by status, invoices by status, inventory health, revenue total, AI insights generated, documents indexed, user breakdown
- **Create a new tenant** (business + owner account) from the admin portal
- **Delete a tenant** and all associated data (cascade delete in correct FK order)

The superadmin has no `business_id` — they are outside the tenant model entirely.

### Architecture: 2-tier role system

```
superadmin  ─── no business_id ─── accesses /api/admin/* only
                                     (get_current_superadmin dep)

owner/staff ─── business_id = N ─── accesses all business routes
                                     (get_current_user dep)
```

The two dependency functions are completely separate:
- `get_current_superadmin` — checks `role == "superadmin"`, raises 403 otherwise
- `get_current_user` — checks `business_id` is non-null, raises 401 if missing (blocks superadmin tokens from leaking into business routes)

### Super-admin API (`/api/admin/*`)

| Method | Endpoint | What it does |
|---|---|---|
| `GET` | `/api/admin/tenants` | List all businesses with owner, counts |
| `POST` | `/api/admin/tenants` | Create business + owner account |
| `DELETE` | `/api/admin/tenants/{id}` | Cascade-delete tenant and all data |
| `GET` | `/api/admin/tenants/{id}/stats` | Detailed per-tenant usage stats |

### Per-tenant stats response

```json
{
  "orders":   { "total": 45, "by_status": { "fulfilled": 28, "pending": 5, ... }, "last_at": "..." },
  "invoices": { "total": 12, "by_status": { "processed": 8, "failed": 2, ... }, "last_at": "..." },
  "products": { "total": 30, "low_stock": 5 },
  "revenue_total": 15430.50,
  "ai":       { "insights_generated": 87, "documents_indexed": 42 },
  "users":    { "total": 3, "by_role": { "owner": 1, "staff": 2 } },
  "last_activity_at": "2026-06-10T..."
}
```

### Frontend: `/superadmin` page

A standalone page — completely separate from the regular app shell (no sidebar).
Matching dark glassmorphism style.

**Login view:** Dedicated login form. On success, `role` in the response is checked — non-superadmin tokens are rejected with an error message. Token stored as `soukpilot_admin_token` (separate from regular `soukpilot_token`).

**Dashboard view:**
- Tenant table: ID, name, owner username, registration date, user/product/order counts
- **▼ Stats** toggle per row — expands an inline 6-card stats panel (orders, invoices, inventory, revenue, AI usage, users) with color-coded status chips
- **+ Add Tenant** inline form
- Two-step delete confirmation per row

Regular users who accidentally log in at `/login` with superadmin credentials are automatically redirected to `/superadmin`.

### Migration 0006

```sql
-- Make business_id nullable (superadmin has NULL)
ALTER TABLE users ALTER COLUMN business_id DROP NOT NULL;

-- Seed superadmin account
INSERT INTO users (business_id, username, hashed_password, role)
VALUES (NULL, 'superadmin', '<bcrypt hash of superadmin2024>', 'superadmin')
ON CONFLICT (username) DO NOTHING;
```

Default credentials: `superadmin` / `superadmin2024` — **change in production**.

### New / changed files

| File | Change |
|---|---|
| `backend/app/models/user.py` | `business_id` now nullable; role comment updated |
| `backend/app/core/security.py` | `create_access_token` now accepts `Optional[int]` business_id and `role` param; role embedded in JWT |
| `backend/app/core/deps.py` | `CurrentUser.business_id` is `Optional[int]`; added `get_current_superadmin`; `get_current_user` rejects null-business_id tokens |
| `backend/app/api/auth.py` | `TokenResponse` gains `role` field; login returns role in response |
| `backend/app/api/admin.py` | New — tenant management router |
| `backend/app/services/admin_service.py` | New — list/create/delete/stats business logic |
| `backend/alembic/versions/0006_superadmin.py` | New — nullable business_id + superadmin seed |
| `frontend/src/App.tsx` | `/superadmin` route added as standalone public route |
| `frontend/src/pages/SuperAdmin.tsx` | New — standalone superadmin portal (login + dashboard) |
| `frontend/src/services/api.ts` | `adminApi`, `TenantInfo`, `TenantStats` types; `adminHttp` instance using separate token |
| `frontend/src/pages/Login.tsx` | Redirects superadmin logins to `/superadmin`; disabled browser autofill |

---

## Feature 3: Drift Detection

### What it does

Detects when the distribution of incoming orders has shifted significantly from
the historical baseline — an early warning that customer behaviour, product mix,
or data quality has changed in ways that may affect AI extraction accuracy.

### How it works

- Uses Population Stability Index (PSI) computed over configurable baseline and recent windows
- Categorises result as `stable` / `warning` / `alert` with per-feature breakdown
- Runs on demand (`POST /api/drift/run`) or can be triggered on a schedule

### New / changed files

| File | Change |
|---|---|
| `backend/app/models/drift.py` | `DriftSignal` model |
| `backend/app/ai/drift.py` | PSI computation logic |
| `backend/app/services/drift_service.py` | Orchestration: fetch data, compute PSI, persist result |
| `backend/app/api/drift.py` | `GET /api/drift/latest`, `POST /api/drift/run` |
| `backend/alembic/versions/0004_drift_signals.py` | Migration: `drift_signals` table |
