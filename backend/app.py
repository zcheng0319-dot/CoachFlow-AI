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


class LeadResponse(BaseModel):
    id: int
    parent_name: str
    child_name: str
    child_age: int
    level: str
    preferred_time: str | None
    status: str
    created_at: str


class TrialResponse(BaseModel):
    id: int
    lead_id: int
    class_id: int
    trial_time: str
    status: str
    rating: float | None
    note: str | None


class InteractionResponse(BaseModel):
    id: int
    lead_id: int
    channel: str
    content: str
    created_at: str


class LeadDetailResponse(BaseModel):
    lead: LeadResponse
    trials: list[TrialResponse]
    interactions: list[InteractionResponse]


class RecommendationBreakdown(BaseModel):
    age: int
    level: int
    schedule: int
    price: int
    availability: int


class RecommendationItem(BaseModel):
    class_id: int
    course_id: int
    course_name: str
    coach_id: int
    coach_name: str
    weekday: str
    start_time: str
    price: int
    remaining: int
    score: int
    score_breakdown: RecommendationBreakdown


class RecommendationResponse(BaseModel):
    recommendations: list[RecommendationItem]


class LeadScoreBreakdown(BaseModel):
    trial_rating: int
    recency: int
    interaction_frequency: int
    course_fit: int
    purchase_intent: int


class LeadScoreResponse(BaseModel):
    lead_id: int
    score: int
    level: Literal["high", "medium", "low"]
    breakdown: LeadScoreBreakdown


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
    response_model=list[LeadResponse],
)
def leads():
    return get_rows("SELECT * FROM leads ORDER BY id")


@app.get(
    "/leads/{lead_id}",
    operation_id="get_lead_detail",
    summary="获取招生线索详情",
    description="根据 lead_id 获取指定招生线索的基础信息、试听记录和历史互动，供意向判断、课程推荐和跟进分析使用。",
    tags=["Agent Tools"],
    response_model=LeadDetailResponse,
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
    response_model=RecommendationResponse,
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
    response_model=LeadScoreResponse,
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
