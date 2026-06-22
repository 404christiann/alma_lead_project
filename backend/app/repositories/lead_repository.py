import psycopg2
from uuid import UUID

from app.exceptions import DuplicateLeadError, LeadNotFoundError
from app.models.lead import LeadStatus
from app.schemas.lead import LeadCreate


def insert_lead(conn, data: LeadCreate) -> dict:
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO leads (first_name, last_name, email)
                VALUES (%s, %s, %s)
                RETURNING *
                """,
                (data.first_name, data.last_name, data.email),
            )
            conn.commit()
            return _row_to_dict(cur)
    except psycopg2.errors.UniqueViolation:
        conn.rollback()
        raise DuplicateLeadError("A lead with this email already exists")
    except Exception:
        conn.rollback()
        raise


def get_lead_by_id(conn, lead_id: UUID) -> dict | None:
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM leads WHERE id = %s", (str(lead_id),))
        row = cur.fetchone()
        if row is None:
            return None
        return _row_to_dict(cur, row)


def list_leads(conn, status: LeadStatus | None = None) -> list[dict]:
    with conn.cursor() as cur:
        if status is None:
            cur.execute("SELECT * FROM leads ORDER BY created_at DESC")
        else:
            cur.execute(
                "SELECT * FROM leads WHERE status = %s ORDER BY created_at DESC",
                (str(status),),
            )
        rows = cur.fetchall()
        return [_row_to_dict(cur, row) for row in rows]


def update_resume_info(
    conn,
    lead_id: UUID,
    path: str,
    filename: str,
    content_type: str,
) -> dict:
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE leads
            SET resume_path = %s, resume_filename = %s, resume_content_type = %s
            WHERE id = %s
            RETURNING *
            """,
            (path, filename, content_type, str(lead_id)),
        )
        conn.commit()
        return _row_to_dict(cur)


def update_status(conn, lead_id: UUID, new_status: LeadStatus) -> dict:
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE leads
            SET status = %s, status_updated_at = now()
            WHERE id = %s
            RETURNING *
            """,
            (str(new_status), str(lead_id)),
        )
        conn.commit()
        if cur.rowcount == 0:
            raise LeadNotFoundError("Lead not found")
        return _row_to_dict(cur)


def delete_lead(conn, lead_id: UUID) -> None:
    with conn.cursor() as cur:
        cur.execute("DELETE FROM leads WHERE id = %s", (str(lead_id),))
        conn.commit()


def _row_to_dict(cur, row=None) -> dict:
    if row is None:
        row = cur.fetchone()
    cols = [desc[0] for desc in cur.description]
    return dict(zip(cols, row))
