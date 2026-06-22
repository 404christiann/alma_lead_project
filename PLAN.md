# Implementation Plan: Lead Management App (Alma Take-Home)

**Stack:** FastAPI · Next.js · Postgres (local Docker) · MinIO (local Docker) · Resend
**No external services.** `docker compose up` is the only setup step.

---

## 1. Component Breakdown

### Backend (`/backend`, FastAPI)

**`app/main.py` — App entrypoint**
- Owns: FastAPI app instance, CORS middleware, router registration, global exception handlers (`DuplicateLeadError`→409, `FileValidationError`→422, `IllegalTransitionError`→409, `LeadNotFoundError`→404, `StorageError`→500, `InvalidCredentialsError`→401), `GET /health`, lifespan hook (MinIO `ensure_bucket` with retry/backoff).
- Does NOT own: business logic, DB/storage internals, route bodies.

**`app/config.py` — Settings**
- Owns: `pydantic-settings` `Settings` reading all env vars; `@lru_cache get_settings()`.
- Does NOT own: I/O, business-rule validation.

**`app/db.py` — Postgres connection pool**
- Owns: `psycopg2.pool.ThreadedConnectionPool` constructed from `DATABASE_URL`; `get_db_conn()` FastAPI dependency that yields a connection and returns it to the pool on teardown.
- Does NOT own: query logic, auth.

**`app/models/lead.py` — Domain enums/constants**
- Owns: `LeadStatus` enum (`PENDING`, `REACHED_OUT`), `ALLOWED_EXTENSIONS`, `ALLOWED_MIME_TYPES`, `EXTENSION_TO_MIME`, `can_transition()`.
- Does NOT own: serialization, persistence.

**`app/schemas/lead.py` — Pydantic API contracts**
- Owns: `LeadCreate`, `LeadOut`, `LeadListItem`, `StatusUpdateIn`, `ErrorResponse`. Field validators (strip names, lowercase email).
- Does NOT own: file-byte handling, DB row mapping.

**`app/schemas/auth.py` — Auth contracts**
- Owns: `LoginIn` (email + password), `TokenOut` (access_token + token_type).
- Does NOT own: hashing, token issuance.

**`app/services/file_validator.py` — File validation**
- Owns: size check, extension allow-list, `python-magic` MIME sniffing, MIME-vs-extension cross-check. Raises `FileValidationError`.
- Does NOT own: storage, persistence.

**`app/services/storage_service.py` — MinIO (S3-compatible) wrapper**
- Owns: dual boto3 clients — *internal* (`endpoint_url=MINIO_ENDPOINT_URL`) for uploads/deletes, *presign* (`endpoint_url=MINIO_PUBLIC_URL`) for minting presigned GET URLs. Path generation `{lead_id}/{sanitized_filename}`. `ensure_bucket()`. Raises `StorageError`.
- Does NOT own: MIME validation, DB writes, compensation logic.

**`app/services/email_service.py` — Resend wrapper**
- Owns: `send_prospect_confirmation()`, `send_attorney_notification()`. Catches all exceptions, logs, returns `bool`. Never raises.
- Does NOT own: when to send, retries.

**`app/repositories/lead_repository.py` — Lead data access**
- Owns: `insert_lead`, `get_lead_by_id`, `list_leads`, `update_resume_info`, `update_status`, `delete_lead`. Maps Postgres `23505` → `DuplicateLeadError`. Accepts `psycopg2` connection.
- Does NOT own: HTTP concerns, email, storage, transition rules.

**`app/repositories/attorney_repository.py` — Attorney data access**
- Owns: `get_by_email(conn, email) -> dict | None`. Accepts `psycopg2` connection.
- Does NOT own: password hashing, token issuance.

**`app/exceptions.py` — Domain exceptions (canonical home)**
- Owns: `DuplicateLeadError`, `LeadNotFoundError`, `FileValidationError`, `StorageError`, `InvalidCredentialsError`, `IllegalTransitionError`. All are plain `Exception` subclasses with no logic. Imported by repositories, services, routes, and `main.py` global handlers from this single module.
- Does NOT own: HTTP status mapping (that lives in `main.py` handlers).

**`app/api/deps.py` — FastAPI dependencies**
- Owns: `get_current_attorney()` — extracts Bearer token, decodes JWT with `JWT_SECRET`/`JWT_ALGORITHM`, returns claims dict. Raises `HTTPException(status_code=401)` directly on any failure (missing header, bad token, expired). Does NOT raise `InvalidCredentialsError`.
- Does NOT own: login flow, password validation.

**`app/services/auth_service.py` — Token issuance**
- Owns: `create_access_token(attorney_id: UUID, email: str) -> str` — encodes `{"sub": str(attorney_id), "email": email, "exp": datetime.utcnow() + timedelta(minutes=JWT_EXPIRE_MINUTES)}` with `JWT_SECRET`/`JWT_ALGORITHM`. Single callable seam for unit-testing token claims.
- Does NOT own: credential validation, bcrypt.

**`app/api/routes_auth.py` — Auth routes**
- Owns: `POST /api/auth/login` — validates credentials via `attorney_repository`, bcrypt-checks password, calls `auth_service.create_access_token()`. Raises `InvalidCredentialsError` (→401 via global handler) on missing attorney or failed bcrypt check.
- Does NOT own: session storage, refresh tokens.

**`app/api/routes_leads.py` — Lead routes**
- Owns: `POST /api/leads` (public), `GET /api/leads` (protected), `GET /api/leads/{id}` (protected), `PATCH /api/leads/{id}/status` (protected). Orchestrates validate → insert → upload → update-resume-info → (compensate on failure) → email.
- Does NOT own: low-level DB/storage/JWT internals.

**`backend/migrations/` — SQL migration files**
- `001_create_leads.sql` — leads table, indexes, trigger.
- `002_create_attorneys.sql` — attorneys table.
- `003_seed_attorney.sql` — inserts the seeded attorney (bcrypt hash generated at setup time).
- Mounted into the Postgres container at `/docker-entrypoint-initdb.d/` — runs automatically on first start.

**`backend/tests/` — Pytest suite**
- Owns: unit tests (validator, `can_transition`, schema validators, presign host check) + integration tests (routes with mocked repo/storage/email; auth route with real bcrypt).
- Does NOT own: production code.

---

### Frontend (`/frontend`, Next.js App Router + TypeScript)

**`lib/api.ts`** — Typed fetch wrapper to FastAPI. Owns: `login()`, `submitLead()`, `listLeads()`, `getLead()`, `markReachedOut()`; attaches Bearer token from in-memory store; maps 409→`DuplicateLeadError`, 401→`UnauthorizedError`. Does NOT own UI or token storage.

**`lib/auth.ts`** — Client-side auth state. Owns: `getToken()` (reads localStorage), `setToken(token)` (writes localStorage **and** a non-httpOnly cookie named `alma_token` so `middleware.ts` can read it), `clearToken()` (clears both). No external SDK.

**`types/lead.ts`** — Shared TS types mirroring backend schemas.

**`app/page.tsx`** — Public intake form page. Owns layout only.

**`components/IntakeForm.tsx`** — Controlled form, client-side validation, multipart submit, success/error/duplicate UI state machine. Does NOT own auth.

**`app/login/page.tsx` + `components/LoginForm.tsx`** — Calls `api.login()`; stores token via `lib/auth.ts` (`setToken` writes both localStorage and cookie); redirects to `/dashboard`. Does NOT own lead data.

**`app/dashboard/page.tsx`** — Protected. Owns lead-list fetch, status filter state. Does NOT own detail.

**`app/dashboard/[id]/page.tsx`** — Owns lead detail, presigned resume download link, `MarkReachedOutButton` (shown only when `status === "PENDING"`).

**`components/LeadTable.tsx`, `StatusFilter.tsx`, `StatusBadge.tsx`, `MarkReachedOutButton.tsx`** — Presentational units. Own their slice only.

**`middleware.ts`** — Guards `/dashboard/*`; reads the `alma_token` cookie (set by `setToken`); redirects to `/login` if absent or empty.

---

### Root

- `docker-compose.yml` — Orchestrates `postgres`, `minio`, `minio-init`, `backend`, `frontend` with `depends_on` + healthchecks. Does NOT own secret values.
- `.env.example` — All env vars with placeholders.
- `README.md` — `docker compose up`, open `localhost:3000`, default attorney credentials.
- `SYSTEM_DESIGN.md` — Required deliverable per assignment. Covers: component diagram, data flow narrative, storage strategy, auth flow, trade-offs made.

---

## 2. Data Flow

### Flow A — Prospect submits the intake form

1. User fills `IntakeForm`. Client validates: non-empty trimmed names, email regex, extension in allow-list, size ≤ 10 MB.
2. `IntakeForm` builds `FormData`, POSTs to `${NEXT_PUBLIC_API_URL}/api/leads` (no auth header).
3. FastAPI `POST /api/leads` parses multipart `first_name`, `last_name`, `email`, `resume` (`UploadFile`).
4. Read resume bytes from `UploadFile`. Pass directly to `file_validator.validate_resume(filename, content_type, data, MAX_FILE_BYTES)` — this is the **single gate** for all file rejections: oversize, bad extension, bad magic-byte MIME, MIME/extension mismatch. Any failure → raises `FileValidationError` → **422**. Returns `(validated_extension, sniffed_mime)`.
5. `LeadCreate` validates names (stripped, non-empty) and email (valid + lowercased); failure → **422**.
6. **Insert first** (storage path requires `lead_id`): `lead_repository.insert_lead(conn, data)` — Postgres `23505` violation → `DuplicateLeadError` → **409**. Row exists with UUID; `resume_*` columns still `NULL`.
7. `storage_service.upload_resume(lead_id, filename, data, sniffed_mime)` uploads to MinIO at `resumes/{lead_id}/{sanitized_filename}` via the **internal** client. `sniffed_mime` (from step 4) is used as `content_type` — not the client-supplied `UploadFile.content_type`, which is untrusted.
   - On `StorageError`: `lead_repository.delete_lead(conn, lead_id)` → return **500**.
8. `lead_repository.update_resume_info(conn, lead_id, path, filename, sniffed_mime)` — stores `sniffed_mime` in `resume_content_type`.
   - On failure: best-effort `storage_service.delete_object(path)` + `delete_lead(conn, lead_id)` → return **500**.
9. `storage_service.create_presigned_url(path)` via **presign** client → `resume_url`.
10. `email_service.send_prospect_confirmation(email, first_name)` and `send_attorney_notification(ATTORNEY_EMAIL, lead)`. Failures logged, not raised.
11. Return **201** with `LeadOut`. Frontend shows success; **409** → "A lead with this email already exists."; **422** → field/file message.

### Flow B — Attorney logs in

1. Attorney opens `/login`, enters email + password, submits `LoginForm`.
2. `api.login(email, password)` POSTs `{ email, password }` to `POST /api/auth/login`.
3. `attorney_repository.get_by_email(conn, email)` — not found or `bcrypt.checkpw()` fails → `InvalidCredentialsError` → **401**.
4. `auth_service.create_access_token(attorney["id"], attorney["email"])` → signed JWT string → `TokenOut`.
5. Frontend stores token via `lib/auth.ts`; redirects to `/dashboard`.

### Flow C — Attorney marks a lead REACHED_OUT

1. Attorney on `/dashboard/[id]`; status is `PENDING`, `MarkReachedOutButton` renders.
2. `api.markReachedOut(id, token)` calls `PATCH /api/leads/{id}/status` with body `{ "status": "REACHED_OUT" }` and `Authorization: Bearer <token>`.
3. `get_current_attorney` decodes JWT with `JWT_SECRET`/`JWT_ALGORITHM`; invalid/expired → **401**.
4. `lead_repository.get_lead_by_id(conn, id)` — `None` → **404** (`LeadNotFoundError`).
5. `can_transition(current, REACHED_OUT)` — already `REACHED_OUT` → **409** (`IllegalTransitionError`).
6. `lead_repository.update_status(conn, id, REACHED_OUT)` sets `status` + `status_updated_at = now()`.
7. Mint fresh `resume_url` from `resume_path` via presign client.
8. Return **200** with updated `LeadOut`. Frontend hides button; badge flips to "Reached Out".

---

## 3. Key Functions / Modules with Signatures

### DB Schema

**`001_create_leads.sql`**
```sql
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE leads (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  first_name          TEXT NOT NULL CHECK (char_length(trim(first_name)) > 0),
  last_name           TEXT NOT NULL CHECK (char_length(trim(last_name)) > 0),
  email               TEXT NOT NULL,
  resume_path         TEXT,
  resume_filename     TEXT,
  resume_content_type TEXT,
  status              TEXT NOT NULL DEFAULT 'PENDING'
                        CHECK (status IN ('PENDING', 'REACHED_OUT')),
  status_updated_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT leads_email_unique UNIQUE (email)
);

CREATE INDEX idx_leads_status     ON leads(status);
CREATE INDEX idx_leads_created_at ON leads(created_at DESC);

CREATE OR REPLACE FUNCTION set_updated_at() RETURNS TRIGGER AS $$
BEGIN NEW.updated_at = now(); RETURN NEW; END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_leads_updated_at
  BEFORE UPDATE ON leads
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();
```

**`002_create_attorneys.sql`**
```sql
CREATE TABLE attorneys (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email         TEXT NOT NULL UNIQUE,
  password_hash TEXT NOT NULL,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

**`003_seed_attorney.sql`**
```sql
-- password_hash generated via: python -c "import bcrypt; print(bcrypt.hashpw(b'<password>', bcrypt.gensalt()).decode())"
-- Replace both values before first run; document in README.
INSERT INTO attorneys (email, password_hash) VALUES (
  'attorney@example.com',
  '$2b$12$PLACEHOLDER_HASH_REPLACE_ME'
);
```

### Storage (MinIO — local Docker container)

- Bucket: `resumes` (private, no public policy).
- Path: `{lead_id}/{sanitized_filename}`.
- **Dual-client presign strategy:** internal client (`MINIO_ENDPOINT_URL=http://minio:9000`) for uploads/deletes; presign client (`MINIO_PUBLIC_URL=http://localhost:9000`) for `generate_presigned_url`. SigV4 signs the host — never post-process the URL string.
- TTL: 3600s. Never cached in DB. Minted fresh on every `GET /api/leads/{id}` and `POST /api/leads` response.

**`docker-compose.yml` (full):**
```yaml
services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: ${POSTGRES_DB}
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./backend/migrations:/docker-entrypoint-initdb.d
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER}"]
      interval: 5s
      timeout: 3s
      retries: 12

  minio:
    image: minio/minio:latest
    ports:
      - "9000:9000"
      - "9001:9001"
    environment:
      MINIO_ROOT_USER: ${MINIO_ACCESS_KEY}
      MINIO_ROOT_PASSWORD: ${MINIO_SECRET_KEY}
    command: server /data --console-address ":9001"
    volumes:
      - minio_data:/data
    healthcheck:
      test: ["CMD", "mc", "ready", "local"]
      interval: 5s
      timeout: 3s
      retries: 12

  minio-init:
    image: minio/mc:latest
    depends_on:
      minio:
        condition: service_healthy
    entrypoint: >
      /bin/sh -c "
      mc alias set local http://minio:9000 ${MINIO_ACCESS_KEY} ${MINIO_SECRET_KEY} &&
      mc mb --ignore-existing local/${MINIO_BUCKET}
      "

  backend:
    build: ./backend
    ports:
      - "8000:8000"
    env_file: .env
    depends_on:
      postgres:
        condition: service_healthy
      minio-init:
        condition: service_completed_successfully

  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    env_file: .env
    depends_on:
      - backend

volumes:
  postgres_data:
  minio_data:
```

---

### Backend Signatures

```python
# config.py
class Settings(BaseSettings):
    DATABASE_URL: str              # postgresql://user:pass@postgres:5432/dbname
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 480  # 8 hours
    RESEND_API_KEY: str
    ATTORNEY_EMAIL: str            # attorney notification recipient
    RESEND_FROM_EMAIL: str
    MINIO_ENDPOINT_URL: str        # http://minio:9000  (internal)
    MINIO_PUBLIC_URL: str          # http://localhost:9000  (browser-reachable)
    MINIO_ACCESS_KEY: str
    MINIO_SECRET_KEY: str
    MINIO_BUCKET: str = "resumes"
    PRESIGNED_URL_TTL_SECONDS: int = 3600
    CORS_ORIGINS: list[str]        # ["http://localhost:3000"]
    MAX_FILE_BYTES: int = 10_485_760

@lru_cache
def get_settings() -> Settings: ...

# db.py
pool: psycopg2.pool.ThreadedConnectionPool  # module-level, init in lifespan

def get_db_conn() -> Generator[psycopg2.extensions.connection, None, None]:
    """Yields a connection from the pool; returns it on exit."""

# models/lead.py
class LeadStatus(str, Enum):
    PENDING = "PENDING"
    REACHED_OUT = "REACHED_OUT"

ALLOWED_EXTENSIONS: frozenset[str]   # {".pdf", ".doc", ".docx", ".png", ".jpg", ".jpeg"}
ALLOWED_MIME_TYPES: frozenset[str]
EXTENSION_TO_MIME: dict[str, frozenset[str]]

def can_transition(current: LeadStatus, target: LeadStatus) -> bool:
    """True only for PENDING -> REACHED_OUT."""

# schemas/auth.py
class LoginIn(BaseModel):
    email: EmailStr
    password: str

class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"

# schemas/lead.py
class LeadCreate(BaseModel):
    first_name: str    # validator: strip; non-empty
    last_name: str     # validator: strip; non-empty
    email: EmailStr    # validator: strip + lowercase

class LeadOut(BaseModel):
    id: UUID
    first_name: str
    last_name: str
    email: EmailStr
    status: LeadStatus
    status_updated_at: datetime
    created_at: datetime
    resume_filename: str | None
    resume_url: str | None  # presigned, minted fresh each GET; None only pre-upload

class LeadListItem(BaseModel):
    id: UUID
    first_name: str
    last_name: str
    email: EmailStr
    status: LeadStatus
    created_at: datetime
    status_updated_at: datetime

class StatusUpdateIn(BaseModel):
    status: LeadStatus

class ErrorResponse(BaseModel):
    detail: str

# exceptions.py  ← canonical home for ALL domain exceptions
class DuplicateLeadError(Exception): ...
class LeadNotFoundError(Exception): ...
class FileValidationError(Exception): ...
class StorageError(Exception): ...
class InvalidCredentialsError(Exception): ...
class IllegalTransitionError(Exception): ...

# services/auth_service.py
def create_access_token(attorney_id: UUID, email: str) -> str:
    """Encodes {"sub": str(attorney_id), "email": email,
    "exp": utcnow() + timedelta(minutes=JWT_EXPIRE_MINUTES)}
    with JWT_SECRET / JWT_ALGORITHM. Returns signed JWT string."""

# services/file_validator.py
def validate_resume(
    filename: str,
    content_type: str,
    data: bytes,
    max_bytes: int,
) -> tuple[str, str]:
    """Returns (validated_extension, sniffed_mime).
    Raises FileValidationError → 422 on: oversize; bad extension;
    bad magic-byte MIME; MIME/extension mismatch."""

# services/storage_service.py
class StorageError(Exception): ...

def get_upload_client(settings: Settings) -> "boto3.client": ...
def get_presign_client(settings: Settings) -> "boto3.client": ...

def ensure_bucket(s3: "boto3.client", bucket: str) -> None:
    """Idempotent. Retries with backoff. Raises StorageError on exhaustion."""

def sanitize_filename(filename: str) -> str:
    """Strip path separators (/ and \\), replace whitespace runs with '_',
    preserve file extension, truncate stem so total length ≤ 255 chars."""

def upload_resume(
    s3: "boto3.client", bucket: str, lead_id: UUID,
    filename: str, data: bytes, content_type: str,
) -> str:
    """Returns object key. Raises StorageError on failure."""

def delete_object(s3: "boto3.client", bucket: str, path: str) -> None:
    """Best-effort. Logs failures, never raises."""

def create_presigned_url(
    s3: "boto3.client", bucket: str, path: str,
    expires_in_seconds: int = 3600,
) -> str:
    """s3 MUST be the presign client (MINIO_PUBLIC_URL)."""

# services/email_service.py
def send_prospect_confirmation(to_email: str, first_name: str) -> bool: ...
def send_attorney_notification(attorney_email: str, lead: LeadOut) -> bool: ...

# repositories/lead_repository.py
# (imports DuplicateLeadError, LeadNotFoundError from app.exceptions)

def insert_lead(conn: Connection, data: LeadCreate) -> dict: ...
def get_lead_by_id(conn: Connection, lead_id: UUID) -> dict | None: ...
def list_leads(conn: Connection, status: LeadStatus | None = None) -> list[dict]:
    """Returns rows ordered created_at DESC. Optional status filter."""
def update_resume_info(
    conn: Connection, lead_id: UUID,
    path: str, filename: str, content_type: str,
) -> dict: ...
def update_status(conn: Connection, lead_id: UUID, new_status: LeadStatus) -> dict:
    """Raises LeadNotFoundError if 0 rows affected."""
def delete_lead(conn: Connection, lead_id: UUID) -> None: ...

# repositories/attorney_repository.py
def get_by_email(conn: Connection, email: str) -> dict | None:
    """Returns {'id', 'email', 'password_hash'} or None."""

# api/deps.py
# (imports nothing from exceptions — raises HTTPException directly)

async def get_current_attorney(
    authorization: str = Header(...),
) -> dict:
    """Splits 'Bearer <token>'. jwt.decode(token, JWT_SECRET,
    algorithms=[JWT_ALGORITHM]). Returns claims dict {"sub", "email", "exp"}.
    Raises HTTPException(status_code=401) directly on: missing header,
    bad format, invalid signature, expired token. Never raises InvalidCredentialsError."""

# api/routes_auth.py
@router.post("/api/auth/login", response_model=TokenOut)
async def login(
    body: LoginIn,
    conn: Connection = Depends(get_db_conn),
) -> TokenOut:
    """get_by_email → bcrypt.checkpw → auth_service.create_access_token → TokenOut.
    Raises InvalidCredentialsError (→401 via global handler) if attorney not found
    or bcrypt.checkpw returns False."""

# api/routes_leads.py
@router.post("/api/leads", status_code=201, response_model=LeadOut)
async def create_lead(
    first_name: str = Form(...),
    last_name: str = Form(...),
    email: str = Form(...),
    resume: UploadFile = File(...),
    conn: Connection = Depends(get_db_conn),
) -> LeadOut: ...

@router.get("/api/leads", response_model=list[LeadListItem])
async def list_leads_route(
    status: LeadStatus | None = Query(None),
    attorney: dict = Depends(get_current_attorney),
    conn: Connection = Depends(get_db_conn),
) -> list[LeadListItem]: ...

@router.get("/api/leads/{lead_id}", response_model=LeadOut)
async def get_lead_route(
    lead_id: UUID,
    attorney: dict = Depends(get_current_attorney),
    conn: Connection = Depends(get_db_conn),
) -> LeadOut: ...

@router.patch("/api/leads/{lead_id}/status", response_model=LeadOut)
async def update_status_route(
    lead_id: UUID,
    body: StatusUpdateIn,
    attorney: dict = Depends(get_current_attorney),
    conn: Connection = Depends(get_db_conn),
) -> LeadOut: ...
```

**HTTP contract:**
- `POST /api/auth/login` → **200** `TokenOut` | **401** (bad credentials)
- `POST /api/leads` → **201** | **409** (dup email) | **422** (bad fields/file) | **500** (storage failure)
- `GET /api/leads` → **200** | **401**
- `GET /api/leads/{id}` → **200** | **401** | **404**
- `PATCH /api/leads/{id}/status` → **200** | **401** | **404** | **409** (illegal transition)

---

### Frontend Signatures

```ts
// types/lead.ts
export type LeadStatus = "PENDING" | "REACHED_OUT";

export interface LeadOut {
  id: string;
  first_name: string;
  last_name: string;
  email: string;
  status: LeadStatus;
  status_updated_at: string;
  created_at: string;
  resume_filename: string | null;
  resume_url: string | null;
}

export interface LeadListItem {
  id: string;
  first_name: string;
  last_name: string;
  email: string;
  status: LeadStatus;
  created_at: string;
  status_updated_at: string;
}

// lib/auth.ts
export function getToken(): string | null;
// reads localStorage key "alma_token"

export function setToken(token: string): void;
// writes localStorage key "alma_token" AND sets document.cookie "alma_token=<token>; path=/"
// (non-httpOnly so middleware.ts can read it)

export function clearToken(): void;
// deletes localStorage key "alma_token" AND sets cookie "alma_token=; Max-Age=0; path=/"

// lib/api.ts
export class DuplicateLeadError extends Error {}
export class UnauthorizedError extends Error {}

export async function login(email: string, password: string): Promise<void>;
// POST /api/auth/login -> stores token via setToken(); throws UnauthorizedError on 401

export async function submitLead(form: FormData): Promise<LeadOut>;
// no auth header; 409 -> DuplicateLeadError

export async function listLeads(status?: LeadStatus): Promise<LeadListItem[]>;
export async function getLead(id: string): Promise<LeadOut>;
export async function markReachedOut(id: string): Promise<LeadOut>;
// above three: attach Bearer token from getToken(); 401 -> UnauthorizedError -> redirect /login

// components/IntakeForm.tsx
// No props. State: "idle" | "submitting" | "success" | "error" | "duplicate"

// components/LoginForm.tsx
// No props. Calls api.login(); on success redirects to /dashboard.

// components/LeadTable.tsx
export interface LeadTableProps { leads: LeadListItem[]; }

// components/StatusFilter.tsx
export interface StatusFilterProps {
  value: "ALL" | LeadStatus;
  onChange: (v: "ALL" | LeadStatus) => void;
}

// components/StatusBadge.tsx
export interface StatusBadgeProps { status: LeadStatus; }

// components/MarkReachedOutButton.tsx
export interface MarkReachedOutButtonProps {
  leadId: string;
  onSuccess: (updated: LeadOut) => void;
}
```

**Frontend env vars:** `NEXT_PUBLIC_API_URL=http://localhost:8000` only. No external SDK keys.

---

## 4. Build Order

**P1 — Schema + compose + config (foundation)**
Write all three SQL migration files (`001`, `002`, `003`), `docker-compose.yml`, `.env.example`, `app/config.py`. Postgres migrations auto-run on first `docker compose up` via `/docker-entrypoint-initdb.d`.
*Rationale:* data contract and orchestration must exist before any code can run or be tested.
*Deps:* none.

**P2 — Backend pure units**
`models/lead.py`, `file_validator.py`, `schemas/lead.py`, `schemas/auth.py`.
*Rationale:* I/O-free — first testable layer; failing tests can be written now.
*Deps:* P1.

**P3 — Repository + service wrappers**
`db.py` (connection pool), `lead_repository.py`, `attorney_repository.py`, `storage_service.py` (dual clients, `ensure_bucket`), `email_service.py`.
*Rationale:* isolates I/O behind clean interfaces so routes are testable with mocks.
*Deps:* P1, P2.

**P4 — Auth route + lead routes + app wiring**
`routes_auth.py` (`POST /api/auth/login` with bcrypt), `deps.py` (`get_current_attorney`), `routes_leads.py` (POST first — full orchestration chain, then GET, then PATCH), `main.py` (CORS, exception handlers, lifespan bucket bootstrap).
*Rationale:* auth route must exist before protected routes; POST lead unblocks frontend intake immediately.
*Deps:* P3.

**P5 — Frontend public intake form**
`types/lead.ts`, `lib/api.submitLead`, `IntakeForm`, `app/page.tsx`.
*Rationale:* E2E exercise of the prospect flow against the live POST endpoint.
*Deps:* P4 POST.

**P6 — Frontend auth + dashboard list + filter**
`lib/auth.ts`, `api.login`, `LoginForm`, `app/login/page.tsx`, `middleware.ts`, `app/dashboard/page.tsx`, `LeadTable`, `StatusFilter`, `StatusBadge`.
*Rationale:* requires `POST /api/auth/login` (P4) and `GET /api/leads` (P4).
*Deps:* P4 auth + GET.

**P7 — Lead detail + resume download + Mark Reached Out**
`app/dashboard/[id]/page.tsx`, presigned download link, `MarkReachedOutButton`.
*Rationale:* completes Flow C; depends on PATCH + detail GET and the list view to navigate from.
*Deps:* P4 PATCH + P6.

**P8 — Docker Compose finalize + README + SYSTEM_DESIGN + integration tests**
Finalize `docker-compose.yml` with full `depends_on`/healthchecks. Write `README.md` (single `docker compose up` command, default attorney credentials, MinIO console at `localhost:9001`). Write `SYSTEM_DESIGN.md` (component diagram, data flow narrative, storage strategy, auth flow, trade-offs). Integration tests covering all three flows plus both compensation paths.
*Deps:* P1–P7.

---

## 5. Risks

| # | Risk | Likelihood | Impact | Mitigation |
|---|------|-----------|--------|------------|
| 1 | **MinIO presigned-URL SigV4 host mismatch — `minio:9000` signed vs `localhost:9000` needed by browser** | High | High | Dedicated presign client with `endpoint_url=MINIO_PUBLIC_URL`. Never post-process the URL string. Unit-test that `resume_url` host is `localhost:9000` and that a real HEAD request returns 200. |
| 2 | **Postgres migration ordering — `003_seed_attorney.sql` references bcrypt hash that must be pre-generated** | High | High | Document hash generation command in README. Provide a `scripts/hash_password.py` helper. Consider making the seed a runtime step (`POST /api/internal/seed`) behind an env flag instead. |
| 3 | **CORS — browser is on host, not in Docker network** | High | Medium | `NEXT_PUBLIC_API_URL=http://localhost:8000` (host-mapped). Backend `CORS_ORIGINS=["http://localhost:3000"]`. Test by submitting the intake form from the browser before P5 is marked done. |
| 4 | **Resend sandbox restrictions — unverified domain limits delivery** | High | Medium | Email non-blocking (201 regardless). Use `onboarding@resend.dev` as `RESEND_FROM_EMAIL` locally. Log every Resend API response. Document domain verification for real use. |
| 5 | **Partial-write inconsistency — lead inserted, then MinIO upload fails** | Medium | High | Two-stage compensation: upload failure → `delete_lead`; `update_resume_info` failure → best-effort `delete_object` + `delete_lead`. Integration tests for both paths required. |
| 6 | **MIME spoofing — valid extension wrapping malicious content** | Medium | Medium | `python-magic` magic-byte sniffing + MIME/extension cross-check. Add `libmagic1` to backend Dockerfile — omission silently breaks `python-magic` at runtime. |
| 7 | **Container startup ordering — backend connects to Postgres before it's ready** | Medium | High | `postgres` healthcheck (`pg_isready`) + `backend` `depends_on: postgres: condition: service_healthy`. Pool init in lifespan retries with backoff. |
| 8 | **JWT secret or MinIO credentials in frontend bundle** | Medium | Critical | Only `NEXT_PUBLIC_API_URL` in frontend env. `JWT_SECRET`, `MINIO_ACCESS_KEY`, `MINIO_SECRET_KEY`, `RESEND_API_KEY` are backend-only. `.env` gitignored. Grep built bundle for secret as a final check. |
| 9 | **Email case normalization — `A@x.com` and `a@x.com` treated as different** | Low | Medium | Lowercase in `LeadCreate` validator before insert. Unique constraint is on the already-normalized value. No pre-check SELECT — rely on the atomic DB constraint. |
| 10 | **`list_leads` return order undefined breaks list tests** | Low | Medium | `list_leads` returns rows ordered `created_at DESC` (driven by `idx_leads_created_at`). State this explicitly in the function contract so tests can assert on ordering. |
