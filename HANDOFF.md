# Handoff: Alma Lead Management App

## What Was Built
Full-stack lead management app for an Alma take-home assignment. Prospects submit a
public intake form (name, email, résumé); attorneys review leads in a protected
dashboard and mark them as reached out. Confirmation emails go to both parties on
submission.

**Stack:** FastAPI · Next.js 16 (App Router) · Postgres · MinIO · Resend  
**Constraint:** fully local — `docker compose up` is the only setup step.

---

## Key Design Decisions

| Decision | Why |
|---|---|
| **MinIO dual-client presign strategy** | SigV4 signs the hostname. Internal client uses `http://minio:9000` for uploads; a separate presign client uses `http://localhost:9000` so the browser can reach the URL. Never post-process a presigned URL string — the signature will break. |
| **Lead insert before upload** | MinIO path requires `lead_id`. Two-stage compensation on failure: upload error → `delete_lead`; `update_resume_info` error → `delete_object` + `delete_lead`. |
| **`filetype` over `python-magic`** | `python-magic` requires `libmagic` via Homebrew at `/usr/local`, which is x86_64; Python is arm64. `filetype` is pure Python. `.doc` (OLE2) isn't recognized by `filetype`, so `file_validator._sniff_mime` adds a manual magic-byte fallback (`\xD0\xCF\x11\xE0…`). |
| **Sniffed MIME, not client content-type** | Client headers are untrusted. `validate_resume()` is the single gate; it returns `(ext, sniffed_mime)` which flows all the way to MinIO. |
| **Email is non-blocking** | `email_service` catches all exceptions, logs, returns `bool`. A Resend failure never surfaces to the prospect. |
| **`setToken` writes both localStorage and cookie** | Next.js `middleware.ts` runs on the edge and can't read `localStorage`. The cookie (`alma_token`) is what guards `/dashboard/*`. |

---

## Known Limitations
- **Single attorney account** — seeded at migration time; no UI to add more.
- **No token refresh** — JWT expires in 8 h; user must re-login.
- **No lead pagination** — `list_leads` returns all rows. Will degrade with volume.
- **Resend sandbox** — unverified sender domains deliver only to the Resend account owner. Set `RESEND_FROM_EMAIL` to `onboarding@resend.dev` locally.
- **No audit trail** — status transitions aren't logged beyond `status_updated_at`.

---

## Running Tests

```bash
cd backend
pip3 install -r requirements.txt
python3 -m pytest                      # 220 tests, ~4 s
python3 -m pytest tests/unit/          # pure functions, no I/O
python3 -m pytest tests/integration/   # routes with mocked deps

cd ../frontend
npm install && npm test                # Jest, 19 tests
```

---

## What the Next Engineer Must Know

1. **All domain exceptions live in `app/exceptions.py`** — don't add new ones elsewhere; the global handlers in `main.py` won't catch them.
2. **Import services at module level in routes** — `from app.services import file_validator` then `file_validator.validate_resume(...)`. Direct function imports (`from app.services.file_validator import validate_resume`) break `unittest.mock.patch`.
3. **`get_current_attorney` raises `HTTPException(401)` directly** — it never raises `InvalidCredentialsError`. That exception is only for the login route.
4. **Next.js 16 `params` is a `Promise`** — use `const { id } = use(params)` in client components, `await params` in server components.
5. **Migrations run once** — Postgres only executes `/docker-entrypoint-initdb.d/` scripts on a fresh volume. To re-run migrations: `docker compose down -v && docker compose up`.
6. **The `.doc` OLE2 fallback is intentional** — `_sniff_mime()` in `file_validator.py` manually checks the first 8 bytes when `filetype.guess()` returns `None`. Don't remove it; real `.doc` uploads will break.
