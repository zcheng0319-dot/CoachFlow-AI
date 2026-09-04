from datetime import date, datetime, timedelta
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

LEVEL_MAP = {
    "初学者": "beginner",
    "有基础": "foundation",
    "体校水平": "intermediate",
    "省队水平": "advanced",
}

LEVEL_MAP.update({
    "初学者": "初学者",
    "有基础": "有基础",
    "体校水平": "体校水平",
    "省队水平": "省队水平",
})


class RecommendationRequest(BaseModel):
    age: int = Field(ge=1, description="孩子年龄，单位为岁。")
    level: Literal["初学者", "有基础", "体校水平", "省队水平"] = Field(
        description="孩子当前的乒乓球水平，可选：初学者、有基础、体校水平、省队水平。"
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


class CreateFollowupRequest(BaseModel):
    content: str = Field(
        min_length=1,
        max_length=300,
        description="需要业务人员后续执行的具体跟进任务，例如“沟通价格顾虑并介绍更匹配的课程方案”。",
    )
    due_date: date = Field(description="计划跟进日期，格式 YYYY-MM-DD。")


class RecordInteractionRequest(BaseModel):
    lead_id: int
    channel: Literal["wechat", "phone", "in_store"]
    content: str = Field(min_length=1, max_length=1000)


class UpsertLeadRequest(BaseModel):
    parent_name: str = Field(min_length=1, max_length=100)
    child_name: str | None = Field(default=None, max_length=100)
    child_age: int | None = Field(default=None, ge=1)
    level: Literal["初学者", "有基础", "体校水平", "省队水平"] | None = None
    preferred_time: str | None = Field(default=None, max_length=100)


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


class RecordInteractionResponse(BaseModel):
    written: bool
    reason: Literal["low_information", "duplicate"] | None = None
    interaction_id: int | None = None
    lead_id: int | None = None
    channel: Literal["wechat", "phone", "in_store"] | None = None
    content: str | None = None


class UpsertLeadResponse(BaseModel):
    created: bool
    reason: Literal["existing_lead", "ambiguous_identity", "insufficient_information"] | None = None
    lead_id: int | None = None


class FollowupResponse(BaseModel):
    id: int
    lead_id: int
    content: str
    due_date: str
    status: Literal["pending"]
    created_at: str


class LeadDetailResponse(BaseModel):
    lead: LeadResponse
    trials: list[TrialResponse]
    interactions: list[InteractionResponse]
    followups: list[FollowupResponse]


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


class CourseScheduleItem(BaseModel):
    schedule: str
    coach: str
    remaining_capacity: int
    available: bool


class CourseInfoResponse(BaseModel):
    course_name: str
    price: int
    schedule: list[CourseScheduleItem]
    coach: list[str]
    remaining_capacity: int
    available: bool


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


LOW_INFORMATION_CONTENT = {
    "你好", "您好", "好的", "好", "行", "可以", "收到", "谢谢", "感谢",
    "嗯", "嗨", "嗨嗨", "哈", "明白", "知道了", "ok", "hello", "hi", "hey", "thanks", "thx",
}


def normalize_content(content: str) -> str:
    return " ".join(content.split())


def is_low_information(content: str) -> bool:
    compact = "".join(character for character in content.casefold() if character.isalnum())
    return not compact or compact in LOW_INFORMATION_CONTENT


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


@app.post(
    "/leads",
    operation_id="upsert_lead",
    summary="创建明确的新招生线索",
    description="仅在没有同名家长和孩子的现有 Lead 时创建新的 CRM 线索。",
    tags=["Agent Tools"],
    response_model=UpsertLeadResponse,
    response_model_exclude_none=True,
)
def upsert_lead(request: UpsertLeadRequest):
    parent_name = normalize_content(request.parent_name)
    child_name = normalize_content(request.child_name) if request.child_name else None
    preferred_time = normalize_content(request.preferred_time) if request.preferred_time else None

    if not parent_name:
        raise HTTPException(status_code=422, detail="Parent name must not be empty")
    if not child_name:
        return {"created": False, "reason": "ambiguous_identity"}

    with get_connection() as conn:
        existing = conn.execute("""
            SELECT id FROM leads
            WHERE parent_name = ? AND child_name = ?
            ORDER BY id
            LIMIT 1
        """, (parent_name, child_name)).fetchone()
        if existing:
            return {"created": False, "reason": "existing_lead", "lead_id": existing["id"]}

        if request.child_age is None or request.level is None:
            return {"created": False, "reason": "insufficient_information"}

        lead_id = conn.execute("""
            INSERT INTO leads (parent_name, child_name, child_age, level, preferred_time, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            parent_name,
            child_name,
            request.child_age,
            request.level,
            preferred_time,
            "new",
            datetime.now().isoformat(timespec="seconds"),
        )).lastrowid

    return {"created": True, "lead_id": lead_id}


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
        followups = conn.execute(
            "SELECT * FROM followups WHERE lead_id = ? ORDER BY due_date, id", (lead_id,)
        ).fetchall()
    return {
        "lead": dict(lead),
        "trials": [dict(row) for row in trials],
        "interactions": [dict(row) for row in interactions],
        "followups": [dict(row) for row in followups],
    }


@app.post(
    "/interactions",
    operation_id="record_interaction",
    summary="记录有效客户互动",
    description="为已有 Lead 写入一条经基础质量校验的 CRM 互动事实。",
    tags=["Agent Tools"],
    response_model=RecordInteractionResponse,
    response_model_exclude_none=True,
)
def record_interaction(request: RecordInteractionRequest):
    content = normalize_content(request.content)
    if not content:
        raise HTTPException(status_code=422, detail="Content must not be empty")

    with get_connection() as conn:
        if not conn.execute("SELECT 1 FROM leads WHERE id = ?", (request.lead_id,)).fetchone():
            raise HTTPException(status_code=404, detail="Lead not found")
        if is_low_information(content):
            return {"written": False, "reason": "low_information"}

        now = datetime.now()
        cutoff = (now - timedelta(minutes=10)).isoformat(timespec="seconds")
        duplicate = conn.execute("""
            SELECT 1 FROM interactions
            WHERE lead_id = ? AND channel = ? AND content = ? AND created_at >= ?
            LIMIT 1
        """, (request.lead_id, request.channel, content, cutoff)).fetchone()
        if duplicate:
            return {"written": False, "reason": "duplicate"}

        interaction_id = conn.execute(
            "INSERT INTO interactions (lead_id, channel, content, created_at) VALUES (?, ?, ?, ?)",
            (request.lead_id, request.channel, content, now.isoformat(timespec="seconds")),
        ).lastrowid

    return {
        "written": True,
        "interaction_id": interaction_id,
        "lead_id": request.lead_id,
        "channel": request.channel,
        "content": content,
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
        [dict(row) for row in candidates], LEVEL_MAP[request.level], request.preferred_days, request.max_price
    )}


@app.get(
    "/courses/info",
    operation_id="get_course_info",
    summary="获取指定课程的当前信息",
    description="根据课程名称获取课程价格、班级时间、教练与当前剩余名额。这是只读查询，不会写入数据库。",
    tags=["Agent Tools"],
    response_model=CourseInfoResponse,
)
def course_info(course_name: str):
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT courses.name AS course_name, courses.price, classes.weekday,
                   classes.start_time, coaches.name AS coach_name,
                   classes.capacity - classes.enrolled AS remaining_capacity
            FROM courses
            JOIN classes ON classes.course_id = courses.id
            JOIN coaches ON coaches.id = classes.coach_id
            WHERE courses.name = ?
            ORDER BY classes.id
        """, (course_name,)).fetchall()

    if not rows:
        raise HTTPException(status_code=404, detail="Course not found")

    schedule = [
        {
            "schedule": f"{row['weekday']} {row['start_time']}",
            "coach": row["coach_name"],
            "remaining_capacity": row["remaining_capacity"],
            "available": row["remaining_capacity"] > 0,
        }
        for row in rows
    ]
    return {
        "course_name": rows[0]["course_name"],
        "price": rows[0]["price"],
        "schedule": schedule,
        "coach": list(dict.fromkeys(row["coach_name"] for row in rows)),
        "remaining_capacity": sum(row["remaining_capacity"] for row in rows),
        "available": any(row["remaining_capacity"] > 0 for row in rows),
    }


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


@app.post(
    "/leads/{lead_id}/followups",
    operation_id="create_followup",
    summary="创建跟进任务",
    description="为指定招生线索创建一条待处理的 CRM 跟进任务。该写操作必须在上层 Human-in-the-loop 工作流确认后调用。",
    tags=["Agent Tools"],
    response_model=FollowupResponse,
)
def create_followup(
    request: CreateFollowupRequest,
    lead_id: int = Path(description="CoachFlow CRM 中的招生线索 ID。"),
):
    with get_connection() as conn:
        if not conn.execute("SELECT 1 FROM leads WHERE id = ?", (lead_id,)).fetchone():
            raise HTTPException(status_code=404, detail="Lead not found")
        followup_id = conn.execute(
            "INSERT INTO followups (lead_id, content, due_date, created_at) VALUES (?, ?, ?, ?)",
            (lead_id, request.content, request.due_date.isoformat(), datetime.now().isoformat(timespec="seconds")),
        ).lastrowid
        followup = conn.execute("SELECT * FROM followups WHERE id = ?", (followup_id,)).fetchone()
    return dict(followup)
