# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## Project

Full-stack lead management app built as a take-home assignment for Alma. Prospects submit a public intake form; attorneys review leads in a protected dashboard and mark them as reached out.

**Stack:** FastAPI · Next.js (App Router, TypeScript) · Postgres · MinIO · Resend
**Constraint:** Fully local — `docker compose up` is the only setup step. No external services required at runtime.

---

## Repo Structure

```
/
├── backend/               FastAPI app
│   ├── app/
│   │   ├── main.py        App entrypoint, CORS, global exception handlers, lifespan
│   │   ├── config.py      pydantic-settings Settings + get_settings()
│   │   ├── db.py          psycopg2 connection pool + get_db_conn() dependency
│   │   ├── exceptions.py  All domain exceptions (canonical home)
│   │   ├── models/
│   │   │   └── lead.py    LeadStatus enum, can_transition(), allow-lists
│   │   ├── schemas/
│   │   │   ├── lead.py    LeadCreate, LeadOut, LeadListItem, StatusUpdateIn, ErrorResponse
│   │   │   └── auth.py    LoginIn, TokenOut
│   │   ├── services/
│   │   │   ├── auth_service.py      create_access_token()
│   │   │   ├── file_validator.py    validate_resume(), sanitize_filename()
│   │   │   ├── storage_service.py   MinIO dual-client wrapper
│   │   │   └── email_service.py     Resend wrapper (never raises)
│   │   ├── repositories/
│   │   │   ├── lead_repository.py
│   │   │   └── attorney_repository.py
│   │   └── api/
│   │       ├── deps.py              get_current_attorney()
│   │       ├── routes_auth.py       POST /api/auth/login
│   │       └── routes_leads.py      POST/GET/PATCH /api/leads
│   ├── migrations/
│   │   ├── 001_create_leads.sql
│   │   ├── 002_create_attorneys.sql
│   │   └── 003_seed_attorney.sql
│   ├── tests/
│   │   ├── conftest.py              Shared fixtures + env var setup
│   │   ├── unit/                    Pure function tests (no I/O)
│   │   └── integration/             Route tests with mocked deps
│   └── pytest.ini
├── frontend/              Next.js 16 app (App Router, TypeScript, Tailwind)
│   ├── app/
│   │   ├── layout.tsx
│   │   ├── page.tsx               Public intake form
│   │   ├── login/page.tsx         Attorney login
│   │   └── dashboard/
│   │       ├── page.tsx           Lead list + filter
│   │       └── [id]/page.tsx      Lead detail + resume + mark reached out
│   ├── components/
│   │   ├── IntakeForm.tsx
│   │   ├── LoginForm.tsx
│   │   ├── LeadTable.tsx
│   │   ├── StatusBadge.tsx
│   │   ├── StatusFilter.tsx
│   │   └── MarkReachedOutButton.tsx
│   ├── lib/
│   │   ├── auth.ts                getToken/setToken/clearToken (localStorage + cookie)
│   │   └── api.ts                 submitLead, listLeads, getLead, markReachedOut
│   ├── types/lead.ts
│   ├── middleware.ts               Guards /dashboard/* — reads alma_token cookie
│   ├── __tests__/                 Jest + Testing Library (19 tests, all passing)
│   ├── jest.config.ts
│   ├── jest.setup.ts
│   └── .env.local                 NEXT_PUBLIC_API_URL=http://localhost:8000
├── PLAN.md                Full implementation plan (source of truth)
├── SUMMARY.md             Original assignment summary
└── SYSTEM_DESIGN.md       (required deliverable — not yet written)
```

---

## Key Design Decisions

Refer to `PLAN.md` for full rationale. Critical decisions:

- **No external services at runtime.** Postgres and MinIO run as Docker containers. Resend is the only outbound call (email) and is non-blocking — failures are logged, never returned as errors.
- **MinIO dual-client presign strategy.** `get_upload_client()` uses `MINIO_ENDPOINT_URL=http://minio:9000` (internal). `get_presign_client()` uses `MINIO_PUBLIC_URL=http://localhost:9000` (browser-reachable). SigV4 signs the host — never post-process presigned URLs. This is the highest-risk implementation detail.
- **All domain exceptions live in `app/exceptions.py`.** `DuplicateLeadError`, `LeadNotFoundError`, `FileValidationError`, `StorageError`, `InvalidCredentialsError`, `IllegalTransitionError`. Nowhere else.
- **`get_current_attorney()` raises `HTTPException(401)` directly.** It never raises `InvalidCredentialsError`. The login route raises `InvalidCredentialsError` → caught by the global handler → 401.
- **`validate_resume()` is the single gate for all file rejections.** No inline size check in the route. Returns `(validated_extension, sniffed_mime)`.
- **`sniffed_mime` (not client-supplied content-type) is passed to `upload_resume()` and stored in `resume_content_type`.** Client headers are untrusted.
- **Lead insert happens before upload** (storage path requires `lead_id`). Compensation on failure: upload error → `delete_lead`; `update_resume_info` error → `delete_object` + `delete_lead`.
- **`status_updated_at` defaults to `now()` at insert** (same as `created_at`). It is updated explicitly on PENDING → REACHED_OUT transition. Transition is one-way; re-marking REACHED_OUT returns 409.
- **`setToken()` in `lib/auth.ts`** writes both `localStorage["alma_token"]` and `document.cookie "alma_token=..."`. `middleware.ts` reads the cookie (localStorage is not accessible in Next.js middleware).
- **`list_leads()` returns rows ordered `created_at DESC`.**

---

## HTTP Contract

| Method | Path | Auth | Success | Failures |
|--------|------|------|---------|---------|
| POST | `/api/auth/login` | None | 200 TokenOut | 401, 422 |
| POST | `/api/leads` | None | 201 LeadOut | 409, 422, 500 |
| GET | `/api/leads` | Bearer | 200 LeadListItem[] | 401, 422 |
| GET | `/api/leads/{id}` | Bearer | 200 LeadOut | 401, 404, 422 |
| PATCH | `/api/leads/{id}/status` | Bearer | 200 LeadOut | 401, 404, 409, 422 |
| GET | `/health` | None | 200 | — |

---

## Running Tests

**Backend:**
```bash
cd backend
pip install -r requirements.txt   # includes pytest, pytest-asyncio, python-jose, bcrypt
pytest                             # all tests (186 passing)
pytest tests/unit/                 # unit tests only
pytest tests/integration/          # integration tests only
pytest tests/unit/test_models.py   # single file
pytest -k "test_can_transition"    # single test by name
```

**Frontend:**
```bash
cd frontend
npm install
npm test                           # Jest, 19 tests passing
npm run typecheck                  # tsc --noEmit
npm run build                      # production build
```

---

## Environment Variables

All required vars (see `.env.example` when created):

```
DATABASE_URL              postgresql://user:pass@postgres:5432/dbname
JWT_SECRET                (min 32 chars, keep secret)
JWT_ALGORITHM             HS256
JWT_EXPIRE_MINUTES        480
RESEND_API_KEY            re_...
ATTORNEY_EMAIL            recipient for new-lead notifications
RESEND_FROM_EMAIL         sender address (verify domain for real delivery)
MINIO_ENDPOINT_URL        http://minio:9000        (internal Docker)
MINIO_PUBLIC_URL          http://localhost:9000    (browser-reachable)
MINIO_ACCESS_KEY
MINIO_SECRET_KEY
MINIO_BUCKET              resumes
PRESIGNED_URL_TTL_SECONDS 3600
CORS_ORIGINS              ["http://localhost:3000"]
MAX_FILE_BYTES            10485760
```

Frontend only needs: `NEXT_PUBLIC_API_URL=http://localhost:8000`

---

## Build Order (from PLAN.md)

| Phase | What | Why first |
|-------|------|-----------|
| P1 | SQL migrations, docker-compose, Settings | Everything derives from the schema |
| P2 | models, file_validator, schemas | Pure/I/O-free — first testable layer |
| P3 | repositories, storage_service, email_service, db | Isolate I/O before wiring routes |
| P4 | routes_auth, routes_leads, deps, main | POST first (unauth), then auth dep, then protected routes |
| P5 | Frontend intake form | E2E test of POST flow |
| P6 | Frontend auth + dashboard list | Requires P4 GET + seeded attorney |
| P7 | Lead detail + resume download + Mark Reached Out | Requires P4 PATCH + P6 |
| P8 | Compose finalize, README, SYSTEM_DESIGN.md, integration tests | Requires all services complete |

---

## Known Gotchas (resolved)

- **`python-magic` arm64 incompatibility** — Homebrew at `/usr/local` is x86_64; Python is arm64. Use `filetype` (pure Python) instead. `filetype.guess(b"PK\x03\x04"...)` returns `"application/zip"` for DOCX bytes — `EXTENSION_TO_MIME[".docx"]` must include `"application/zip"`.
- **Python 3.11 StrEnum `str()` behavior** — `str(LeadStatus.PENDING)` returns `"LeadStatus.PENDING"`, not `"PENDING"`. Fixed with `def __str__(self): return self.value` on the enum.
- **`Header(None)` not `Header(...)`** — If `authorization` is a required Header, FastAPI returns 422 before the function runs, blocking the 401 path. Must be `Optional`.
- **`PydanticValidationError` global handler** — Manually calling `LeadCreate(...)` inside a route raises `pydantic_core.ValidationError` which FastAPI does NOT auto-wrap as 422. Added explicit `@app.exception_handler(PydanticValidationError)`.
- **Module-level imports in routes** — Use `from app.services import file_validator` then `file_validator.validate_resume(...)`, not `from app.services.file_validator import validate_resume`. The latter breaks `unittest.mock.patch`.
- **Next.js 16 `params` is a Promise** — In client components, use `const { id } = use(params)`. In server components, `await params`.
- **Next.js 16 `middleware.ts` deprecation** — Build warns to rename to `proxy.ts`. File still works; rename when upgrading.
- **jsdom v24 HTML5 validation blocks form submit in tests** — Add `noValidate` to React forms; otherwise `required` on file inputs prevents jsdom from firing the submit event when files are set via `userEvent.upload`. Also read the file from `input.files` directly rather than `new FormData(form)` since jsdom's FormData doesn't capture file inputs.

---

## Deliverables Checklist

- [x] `backend/` — FastAPI app
- [x] `frontend/` — Next.js app
- [x] `docker-compose.yml` — single `docker compose up` brings up everything
- [x] `backend/migrations/` — 3 SQL files auto-run by Postgres on first start
- [x] `backend/requirements.txt` + `backend/Dockerfile`
- [x] `frontend/Dockerfile` + `frontend/.dockerignore`
- [x] `.env.example` — all vars with working local defaults
- [x] `README.md` — local run instructions (required by assignment)
- [ ] `SYSTEM_DESIGN.md` — component diagram, data flows, trade-offs (required by assignment)
- [ ] Public GitHub repository

## Verified Working (2026-06-22)
- Prospect submits intake form → lead created, confirmation email sent to prospect, notification sent to attorney
- Attorney logs in at /login → redirected to dashboard → lead appears
- Attorney clicks lead → detail view + resume download link
- Mark as Reached Out → status transitions, button disappears
