from datetime import date
from typing import Literal

from fastapi import FastAPI, HTTPException, Path
from pydantic import BaseModel, Field

from .db import get_connection
from .logic import recommend_courses, score_lead


app = FastAPI(
    title="CoachFlow AI Tools",
    description="CoachFlow AI 少儿乒乓球培训业务工具 API",
    version="0.1.0",
)


class RecommendationRequest(BaseModel):
    age: int = Field(ge=1, description="孩子年龄，单位为岁。")
    level: Literal["beginner", "foundation", "intermediate", "advanced"] = Field(
        description="孩子当前乒乓球水平。beginner=零基础或入门，foundation=基础，intermediate=进阶，advanced=竞赛或高阶。"
    )
    preferred_days: list[str] = Field(min_length=1, description="家长可接受的上课星期，例如 [\"周六\", \"周日\"]。")
    max_price: int | None = Field(
        default=None, ge=0, description="可接受的课程总预算，单位人民币元；为空表示暂不限制预算。"
    )


class LeadScoreRequest(BaseModel):
    course_fit: float = Field(
        ge=0, le=1, description="AI 根据家长需求与课程匹配情况提取的课程匹配度，0 表示完全不匹配，1 表示高度匹配。"
    )
    purchase_intent: float = Field(
        ge=0, le=1, description="AI 根据咨询和试听历史提取的购买意向强度，0 表示几乎无购买意向，1 表示购买意向非常强。"
    )
    as_of: date | None = Field(
        default=None, description="评分参考日期，用于计算最近互动时间；测试时建议显式传入以保证评分可复现。"
    )


def get_rows(query):
    with get_connection() as conn:
        return [dict(row) for row in conn.execute(query).fetchall()]


@app.get("/", include_in_schema=False)
def root():
    return {"name": "CoachFlow AI", "status": "prototype"}


@app.get("/health", include_in_schema=False)
def health():
    with get_connection() as conn:
        conn.execute("SELECT COUNT(*) FROM coaches").fetchone()
    return {"status": "ok"}


@app.get("/coaches", include_in_schema=False)
def coaches():
    return get_rows("SELECT * FROM coaches ORDER BY id")


@app.get("/courses", include_in_schema=False)
def courses():
    return get_rows("SELECT * FROM courses ORDER BY id")


@app.get("/classes", include_in_schema=False)
def classes():
    return get_rows("""
        SELECT classes.id, courses.name AS course_name, coaches.name AS coach_name,
               weekday, start_time, capacity, enrolled, capacity - enrolled AS remaining
        FROM classes
        JOIN courses ON courses.id = classes.course_id
        JOIN coaches ON coaches.id = classes.coach_id
        ORDER BY classes.id
    """)


@app.get(
    "/leads",
    operation_id="list_leads",
    summary="获取招生线索列表",
    description="获取 CoachFlow CRM 中全部招生线索的基础信息。需要查看某位家长的试听或互动记录时，再调用 get_lead_detail。",
    tags=["Agent Tools"],
)
def leads():
    return get_rows("SELECT * FROM leads ORDER BY id")


@app.get(
    "/leads/{lead_id}",
    operation_id="get_lead_detail",
    summary="获取招生线索详情",
    description="根据 lead_id 获取指定招生线索的基础信息、试听记录和历史互动，供意向判断、课程推荐和跟进分析使用。",
    tags=["Agent Tools"],
)
def lead_detail(lead_id: int = Path(description="CoachFlow CRM 中的招生线索 ID。")):
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


@app.post(
    "/courses/recommend",
    operation_id="recommend_courses",
    summary="推荐合适课程班级",
    description="根据孩子年龄、乒乓球水平、可上课日期和预算，对当前可报名班级执行确定性排序，并返回最多 3 个候选。",
    tags=["Agent Tools"],
)
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


@app.post(
    "/leads/{lead_id}/score",
    operation_id="score_lead",
    summary="计算招生线索评分",
    description="结合数据库事实以及 AI 提取的课程匹配度和购买意向，计算 0-100 的确定性招生线索评分。",
    tags=["Agent Tools"],
)
def lead_score(request: LeadScoreRequest, lead_id: int = Path(description="CoachFlow CRM 中的招生线索 ID。")):
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
