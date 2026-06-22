# Alma Lead Management

Full-stack lead management app built as a take-home assignment. Prospects submit a public intake form; attorneys review leads in a protected dashboard and mark them as reached out.

**Stack:** FastAPI · Next.js 16 · Postgres · MinIO · Resend

---

## Prerequisites

Docker and Docker Compose are the only dependencies.

**macOS:**
```bash
brew install --cask docker
open -a Docker          # launch Docker Desktop; wait for the whale icon in the menu bar
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt-get update
sudo apt-get install -y docker.io docker-compose-plugin
sudo systemctl enable --now docker
sudo usermod -aG docker $USER   # log out and back in after this
```

**Windows:**
Download and install [Docker Desktop for Windows](https://www.docker.com/products/docker-desktop/), then launch it from the Start menu.

**Verify Docker is running before continuing:**
```bash
docker version
docker compose version
```

Both commands should print version numbers without errors.

---

## Running Locally

**1. Clone the repo and copy the environment file:**

```bash
git clone <repo-url>
cd alma_lead_project
cp .env.example .env
```

The default `.env` values work out of the box for local development. No edits required.

**2. Start all services:**

```bash
docker compose up --build
```

This starts Postgres, MinIO, the FastAPI backend, and the Next.js frontend. On first run, Postgres automatically applies the migrations and seeds the attorney account.

**3. Open the app:**

| Service | URL |
|---|---|
| Prospect intake form | http://localhost:3000 |
| Attorney login | http://localhost:3000/login |
| API docs (Swagger) | http://localhost:8000/docs |
| MinIO console | http://localhost:9001 |

---

## Default Credentials

**Attorney login:**
```
Email:    attorney@alma.com
Password: alma2024
```

**MinIO console** (to browse uploaded résumés):
```
Username: minioadmin
Password: minioadmin
```

---

## How It Works

1. A prospect fills out the intake form at `/` — name, email, and résumé upload (PDF, DOC, DOCX, JPG, PNG, up to 10 MB).
2. On submission, confirmation emails are sent to the prospect and the attorney via Resend. Email delivery is non-blocking — the form succeeds even if the email call fails.
3. The attorney logs in at `/login` and is redirected to the dashboard.
4. The dashboard lists all leads with their current status (`PENDING` or `REACHED OUT`). Leads can be filtered by status.
5. Clicking a lead opens the detail view with a presigned download link for the résumé.
6. The attorney clicks **Mark as Reached Out** to transition the lead. This action is one-way and cannot be undone.

---

## Running Tests

**Backend (186 tests):**

```bash
cd backend
pip3 install -r requirements.txt
python3 -m pytest
```

**Frontend (19 tests):**

```bash
cd frontend
npm install
npm test
```

---

## Re-running Migrations

Postgres only runs the migration scripts on a fresh volume. To reset the database:

```bash
docker compose down -v
docker compose up --build
```

> **Warning:** This deletes all data including submitted leads and uploaded résumés.

---

## Email Configuration

By default, `RESEND_FROM_EMAIL` is set to `onboarding@resend.dev`, which works without domain verification but only delivers to the Resend account owner's email. To receive emails at `ATTORNEY_EMAIL`, update `RESEND_FROM_EMAIL` in `.env` to a domain you've verified in your [Resend dashboard](https://resend.com/domains).
