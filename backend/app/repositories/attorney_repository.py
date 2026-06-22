def get_by_email(conn, email: str) -> dict | None:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, email, password_hash FROM attorneys WHERE email = %s",
            (email,),
        )
        row = cur.fetchone()
        if row is None:
            return None
        cols = [desc[0] for desc in cur.description]
        return dict(zip(cols, row))
