from fastapi import FastAPI, HTTPException

from .db import get_connection


app = FastAPI()


def get_rows(query):
    with get_connection() as conn:
        return [dict(row) for row in conn.execute(query).fetchall()]


@app.get("/")
def root():
    return {"name": "CoachFlow AI", "status": "prototype"}


@app.get("/health")
def health():
    with get_connection() as conn:
        conn.execute("SELECT 1").fetchone()
    return {"status": "ok"}


@app.get("/coaches")
def coaches():
    return get_rows("SELECT * FROM coaches ORDER BY id")


@app.get("/courses")
def courses():
    return get_rows("SELECT * FROM courses ORDER BY id")


@app.get("/classes")
def classes():
    return get_rows("""
        SELECT classes.id, courses.name AS course_name, coaches.name AS coach_name,
               weekday, start_time, capacity, enrolled, capacity - enrolled AS remaining
        FROM classes
        JOIN courses ON courses.id = classes.course_id
        JOIN coaches ON coaches.id = classes.coach_id
        ORDER BY classes.id
    """)


@app.get("/leads")
def leads():
    return get_rows("SELECT * FROM leads ORDER BY id")


@app.get("/leads/{lead_id}")
def lead_detail(lead_id: int):
    with get_connection() as conn:
        lead = conn.execute("SELECT * FROM leads WHERE id = ?", (lead_id,)).fetchone()
        if not lead:
            raise HTTPException(status_code=404, detail="Lead not found")
        trials = conn.execute("SELECT * FROM trials WHERE lead_id = ? ORDER BY id", (lead_id,)).fetchall()
        interactions = conn.execute(
            "SELECT * FROM interactions WHERE lead_id = ? ORDER BY created_at", (lead_id,)
        ).fetchall()
    return {
        "lead": dict(lead),
        "trials": [dict(row) for row in trials],
        "interactions": [dict(row) for row in interactions],
    }
