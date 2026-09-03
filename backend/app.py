from datetime import date

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from .db import get_connection
from .logic import recommend_courses, score_lead


app = FastAPI()


class RecommendationRequest(BaseModel):
    age: int
    level: str
    preferred_days: list[str]
    max_price: int | None = None


class LeadScoreRequest(BaseModel):
    course_fit: float = Field(ge=0, le=1)
    purchase_intent: float = Field(ge=0, le=1)
    as_of: date | None = None


def get_rows(query):
    with get_connection() as conn:
        return [dict(row) for row in conn.execute(query).fetchall()]


@app.get("/")
def root():
    return {"name": "CoachFlow AI", "status": "prototype"}


@app.get("/health")
def health():
    with get_connection() as conn:
        conn.execute("SELECT COUNT(*) FROM coaches").fetchone()
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


@app.post("/courses/recommend")
def course_recommendation(request: RecommendationRequest):
    with get_connection() as conn:
        candidates = conn.execute("""
            SELECT classes.id AS class_id, courses.id AS course_id, courses.name AS course_name,
                   courses.level, courses.price, coaches.id AS coach_id, coaches.name AS coach_name,
                   classes.weekday, classes.start_time, classes.capacity, classes.enrolled
            FROM classes
            JOIN courses ON courses.id = classes.course_id
            JOIN coaches ON coaches.id = classes.coach_id
            WHERE courses.age_min <= ? AND courses.age_max >= ? AND classes.enrolled < classes.capacity
        """, (request.age, request.age)).fetchall()
    return {"recommendations": recommend_courses(
        [dict(row) for row in candidates], request.level, request.preferred_days, request.max_price
    )}


@app.post("/leads/{lead_id}/score")
def lead_score(lead_id: int, request: LeadScoreRequest):
    with get_connection() as conn:
        if not conn.execute("SELECT 1 FROM leads WHERE id = ?", (lead_id,)).fetchone():
            raise HTTPException(status_code=404, detail="Lead not found")
        trial = conn.execute("""
            SELECT rating FROM trials WHERE lead_id = ? AND status = 'completed'
            ORDER BY trial_time DESC, id DESC LIMIT 1
        """, (lead_id,)).fetchone()
        interaction = conn.execute("""
            SELECT created_at FROM interactions WHERE lead_id = ? ORDER BY created_at DESC LIMIT 1
        """, (lead_id,)).fetchone()
        interaction_count = conn.execute(
            "SELECT COUNT(*) FROM interactions WHERE lead_id = ?", (lead_id,)
        ).fetchone()[0]
    result = score_lead(
        trial["rating"] if trial else None,
        interaction["created_at"] if interaction else None,
        interaction_count,
        request.course_fit,
        request.purchase_intent,
        request.as_of,
    )
    return {"lead_id": lead_id, **result}
